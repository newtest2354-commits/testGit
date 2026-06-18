import asyncio
import heapq
import ipaddress
import time
import random
import os
import logging
from itertools import islice

from net import tcp_check, tls_handshake, https_check
import stream

LIMIT_PER_URL = 10000
OUTPUT_LIMIT = 4000

class URLTCPLimiter:
    def __init__(self, limit=100):
        self.sem = asyncio.Semaphore(limit)

    async def run(self, coro):
        async with self.sem:
            return await coro

class AdaptiveConfig:
    def __init__(self):
        self.tls_timeout = 0.7
        self.total_timeout = 2.3
        self.tcp_samples = []
        self.tls_samples = []
        self.alpha = 0.3

    def update_tcp(self, latency):
        self.tcp_samples.append(latency)
        if len(self.tcp_samples) > 200:
            self.tcp_samples.pop(0)

    def update_tls(self, latency):
        self.tls_samples.append(latency)
        if len(self.tls_samples) > 200:
            self.tls_samples.pop(0)

        if len(self.tls_samples) > 20:
            s = sorted(self.tls_samples)
            p95 = s[int(len(s) * 0.95)]

            if p95 > 800:
                self.tls_timeout = min(1.5, self.tls_timeout * 1.1)
                self.total_timeout = min(4.0, self.total_timeout * 1.1)
            elif p95 < 250:
                self.tls_timeout = max(0.3, self.tls_timeout * 0.9)
                self.total_timeout = max(1.5, self.total_timeout * 0.9)

            self.tls_timeout = max(0.3, min(1.5, self.tls_timeout))
            self.total_timeout = max(1.5, min(4.0, self.total_timeout))

class OutputStore:
    def __init__(self, path):
        self.path = path
        self.latencies = {}
        self.timestamps = {}
        self.lock = asyncio.Lock()
        self.save_lock = asyncio.Lock()
        self._last_save = 0
        self._save_interval = 30
        self._load()

    def _load(self):
        import json

        if not os.path.exists(self.path):
            return

        try:
            with open(self.path, "r") as f:
                data = json.load(f)

            now = time.time()
            loaded = 0

            for ip, item in data.items():
                latency = float(item["latency"])
                ts = float(item["timestamp"])

                if now - ts < 7 * 86400:
                    self.latencies[ip] = latency
                    self.timestamps[ip] = ts
                    loaded += 1

            logging.info(f"Loaded {loaded} IPs from store")

        except Exception as e:
            logging.warning(f"Failed to load store: {e}")

    async def _save_unlocked(self):
        async with self.save_lock:
            import json

            tmp = self.path + ".tmp"

            data = {
                ip: {
                    "latency": self.latencies[ip],
                    "timestamp": self.timestamps[ip]
                }
                for ip in self.latencies
            }

            with open(tmp, "w") as f:
                json.dump(data, f)

            os.replace(tmp, self.path)

    async def add(self, ip, latency):
        async with self.lock:
            now = time.time()

            ts = self.timestamps.get(ip)

            if ts and now - ts < 7 * 86400:
                return

            self.timestamps[ip] = now
            self.latencies[ip] = latency

            if len(self.latencies) > OUTPUT_LIMIT:
                oldest_ip = min(self.timestamps.items(), key=lambda x: x[1])[0]
                self.latencies.pop(oldest_ip, None)
                self.timestamps.pop(oldest_ip, None)

            if now - self._last_save > self._save_interval:
                self._last_save = now
                asyncio.create_task(self._save_unlocked())

    async def add_async(self, ip, latency):
        await self.add(ip, latency)

    def export_to_file(self, path):
        import json
        now = time.time()

        valid = sorted(
            ((self.latencies[ip], ip) for ip in self.latencies if now - self.timestamps.get(ip, 0) < 7 * 86400),
            key=lambda x: x[0]
        )

        with open(path, "w") as f:
            for lat, ip in valid[:OUTPUT_LIMIT]:
                f.write(f"{ip},{lat:.2f}\n")

        logging.info(f"Exported {len(valid[:OUTPUT_LIMIT])} IPs to {path}")

        tmp = self.path + ".tmp"
        data = {}
        for ip in self.latencies:
            if now - self.timestamps[ip] < 7 * 86400:
                data[ip] = {
                    "latency": self.latencies[ip],
                    "timestamp": self.timestamps[ip]
                }
        with open(tmp, "w") as f:
            json.dump(data, f)
        os.replace(tmp, self.path)

def cidr_to_ips(cidr):
    try:
        net = ipaddress.ip_network(cidr.strip(), strict=False)
    except Exception as e:
        logging.debug(f"Invalid CIDR {cidr}: {e}")
        return

    count = 0
    for ip in net.hosts():
        yield str(ip)
        count += 1
        if count >= LIMIT_PER_URL:
            break

async def tcp_pre_score(ip, cache):
    if not await cache.check_and_claim(ip):
        return None

    ok, lat = await tcp_check(ip, timeout=0.8)
    if not ok:
        return None

    return ip, lat

async def https_final_score(ip, tcp_lat, config):
    ok, https_lat = await tls_handshake(ip, config.total_timeout)

    if not ok:
        return None

    return ip, (tcp_lat + https_lat) / 2

async def process_url(url, queue, cache, config, ips_per_url, tcp_concurrency, tcp_batch_size, tcp_queue_maxsize):
    tcp_heap = []
    ip_count = 0
    url_ips = 0
    MAX_HEAP = 500

    logging.info(f"Processing URL: {url}")

    ip_queue = asyncio.Queue(maxsize=tcp_queue_maxsize)
    tcp_workers = tcp_concurrency

    async def tcp_worker():
        while True:
            try:
                ip = await ip_queue.get()
            except asyncio.CancelledError:
                break

            if ip is None:
                ip_queue.task_done()
                break

            result = await tcp_pre_score(ip, cache)
            ip_queue.task_done()

            if result is not None:
                ip, lat = result
                if len(tcp_heap) < MAX_HEAP:
                    heapq.heappush(tcp_heap, (lat, ip))
                else:
                    heapq.heapreplace(tcp_heap, (lat, ip))

    workers = [asyncio.create_task(tcp_worker()) for _ in range(tcp_workers)]

    async for cidr in stream.stream_urls(url):
        for ip in cidr_to_ips(cidr):
            if ip_count >= ips_per_url:
                break

            await ip_queue.put(ip)
            ip_count += 1
            url_ips += 1
            await asyncio.sleep(0)

        if ip_count >= ips_per_url:
            break

    for _ in range(tcp_workers):
        await ip_queue.put(None)

    await asyncio.gather(*workers, return_exceptions=True)

    logging.info(f"URL {url} processed {url_ips} IPs, {len(tcp_heap)} passed TCP check")

    if tcp_heap:
        k = max(1, len(tcp_heap) // 2)
        best_half = heapq.nsmallest(k, tcp_heap)

        logging.info(f"Running HTTPS check on {len(best_half)} IPs from {url}")

        HTTPS_CONCURRENCY = 100
        sem = asyncio.Semaphore(HTTPS_CONCURRENCY)

        async def safe_https(lat, ip):
            async with sem:
                return await https_final_score(ip, lat, config)

        https_tasks = []
        for lat, ip in best_half:
            https_tasks.append(safe_https(lat, ip))

        final_results = await asyncio.gather(*https_tasks, return_exceptions=True)

        final_results = [
            r for r in final_results
            if isinstance(r, tuple)
        ]

        logging.info(f"URL {url} found {len(final_results)} working IPs")

        for ip, lat in final_results:
            await cache.mark_success(ip)
            await queue.put((lat, ip))
            await asyncio.sleep(0)

async def producer(urls, queue, cache, config, ips_per_url, url_delay, tcp_concurrency, tcp_batch_size, tcp_queue_maxsize):
    sem = asyncio.Semaphore(min(8, max(2, len(urls)//3)))

    async def run_url(url):
        async with sem:
            await process_url(url, queue, cache, config, ips_per_url, tcp_concurrency, tcp_batch_size, tcp_queue_maxsize)
            await asyncio.sleep(url_delay)

    await asyncio.gather(*(run_url(url) for url in urls))
    logging.info("All URLs processed")

async def worker(queue, store, config):
    processed = 0
    while True:
        if queue.qsize() > 7000:
            await asyncio.sleep(0.05)

        item = await queue.get()

        if item is None:
            queue.task_done()
            break

        lat, ip = item

        try:
            await store.add(ip, lat)
            config.update_tls(lat)
            processed += 1
            if processed % 100 == 0:
                logging.info(f"Worker processed {processed} IPs")
        except Exception as e:
            logging.error(f"Worker error: {e}")
        finally:
            queue.task_done()
