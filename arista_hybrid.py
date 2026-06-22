import asyncio
import aiohttp
import ipaddress
import random
import json
import time
import os
import logging
import sqlite3
import socket
import struct
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional, Set, Any, Tuple
from datetime import datetime
from collections import OrderedDict, defaultdict
import gc
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
import aiosqlite
import redis.asyncio as redis
import numpy as np
import msgpack
from contextlib import asynccontextmanager

try:
    import maxminddb
    HAS_MAXMIND = True
except ImportError:
    HAS_MAXMIND = False

try:
    import uvloop
    HAS_UVLOOP = True
except ImportError:
    HAS_UVLOOP = False

try:
    from prometheus_client import Counter, Histogram, Gauge, start_http_server
    HAS_PROMETHEUS = True
except ImportError:
    HAS_PROMETHEUS = False

if HAS_UVLOOP:
    uvloop.install()

@dataclass
class Config:
    max_workers: int = 80
    queue_size: int = 20000
    batch_size: int = 500
    tcp_timeout: float = 0.3
    max_latency: int = 200
    min_latency: int = 50
    redis_url: str = "redis://localhost:6379"
    db_path: str = "proxies_hybrid.db"
    max_retries: int = 2
    backoff_base: float = 1.0
    ultra_mode: bool = True
    max_output_ips: int = 4000
    retention_days: int = 7
    maxmind_path: str = "GeoLite2-Country.mmdb"
    use_online_fallback: bool = False
    max_geo_batch: int = 50
    max_ports_per_ip: int = 7
    enable_http_test: bool = True
    http_test_timeout: float = 1.0
    http_test_url: str = "http://httpbin.org/ip"
    enable_prometheus: bool = True
    prometheus_port: int = 9090
    enable_uvloop: bool = True
    runner_id: str = None
    ports: List[int] = None
    http_parallel: int = 200
    quality_threshold: int = 200
    geo_thread_pool: int = 4
    tcp_port_parallel: int = 7

    def __post_init__(self):
        if self.ports is None:
            self.ports = [443, 8443, 8080, 80, 2053, 2087, 2096]
        if self.runner_id is None:
            self.runner_id = f"runner-{os.getpid()}-{int(time.time())}"

if HAS_PROMETHEUS:
    SCANNED_IPS = Counter('scanned_ips_total', 'Total IPs scanned')
    ACCEPTED_PROXIES = Counter('accepted_proxies_total', 'Total proxies accepted')
    REJECTED_IPS = Counter('rejected_ips_total', 'Total IPs rejected')
    HTTP_WORKING = Counter('http_working_total', 'Total HTTP working proxies')
    HTTP_FAILED = Counter('http_failed_total', 'Total HTTP failed proxies')
    SCAN_LATENCY = Histogram('scan_latency_seconds', 'Scan latency in seconds', buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0])
    ACTIVE_WORKERS = Gauge('active_workers', 'Number of active workers')
    QUEUE_SIZE = Gauge('queue_size', 'Current queue size')
    PROXY_COUNT = Gauge('proxy_count', 'Total proxies in database')

class PortScheduler:
    def __init__(self, max_concurrent: int = 300):
        self.semaphore = asyncio.Semaphore(max_concurrent)
        self.subnet_semaphores = {}
        self._lock = asyncio.Lock()
        self.connection_window = 0.05
        self.last_connect = defaultdict(float)
    
    async def acquire(self, ip: str):
        async with self.semaphore:
            subnet = ip.rsplit('.', 1)[0]
            async with self._lock:
                if subnet not in self.subnet_semaphores:
                    self.subnet_semaphores[subnet] = asyncio.Semaphore(10)
            async with self.subnet_semaphores[subnet]:
                now = time.time()
                if now - self.last_connect[ip] < self.connection_window:
                    await asyncio.sleep(self.connection_window - (now - self.last_connect[ip]))
                self.last_connect[ip] = time.time()
    
    def reset(self):
        self.subnet_semaphores.clear()
        self.last_connect.clear()

class EventDrivenDialer:
    def __init__(self, scheduler: PortScheduler):
        self.scheduler = scheduler
        self.pending = defaultdict(list)
        self.results = {}
        self._lock = asyncio.Lock()
        self.port_semaphore = asyncio.Semaphore(50)
    
    async def dial_port(self, ip: str, port: int, timeout: float = 0.3) -> Tuple[Optional[int], Optional[float]]:
        await self.scheduler.acquire(ip)
        try:
            start = time.time()
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(ip, port),
                timeout=timeout
            )
            latency = (time.time() - start) * 1000
            writer.close()
            await writer.wait_closed()
            return port, latency
        except:
            return port, None
    
    async def scan_ip_parallel(self, ip: str, ports: List[int], timeout: float = 0.3, min_latency: int = 50, max_latency: int = 200) -> Tuple[Optional[int], Optional[float]]:
        async def check_port(port):
            async with self.port_semaphore:
                p, lat = await self.dial_port(ip, port, timeout)
                return p, lat
        
        tasks = [check_port(p) for p in ports]
        results = await asyncio.gather(*tasks)
        
        best_port = None
        best_latency = None
        
        for port, latency in results:
            if latency is not None and latency <= max_latency:
                if best_latency is None or latency < best_latency:
                    best_latency = latency
                    best_port = port
        
        return best_port, best_latency

class HTTPProxyTester:
    def __init__(self, config: Config):
        self.config = config
        self.session = None
        self._lock = asyncio.Lock()
        self.cache = OrderedDict()
        self.cache_size = 5000
    
    async def get_session(self):
        if self.session is None:
            async with self._lock:
                if self.session is None:
                    connector = aiohttp.TCPConnector(limit=200, limit_per_host=50)
                    self.session = aiohttp.ClientSession(connector=connector)
        return self.session
    
    async def test_proxy(self, ip: str, port: int, timeout: float = 1.0) -> bool:
        cache_key = f"{ip}:{port}"
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            return self.cache[cache_key]
        
        try:
            session = await self.get_session()
            proxy_url = f"http://{ip}:{port}"
            async with session.get(
                self.config.http_test_url,
                proxy=proxy_url,
                timeout=timeout
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    result = data.get('origin') == ip
                    self.cache[cache_key] = result
                    self.cache.move_to_end(cache_key)
                    if len(self.cache) > self.cache_size:
                        self.cache.popitem(last=False)
                    if HAS_PROMETHEUS:
                        if result:
                            HTTP_WORKING.inc()
                        else:
                            HTTP_FAILED.inc()
                    return result
        except:
            pass
        
        self.cache[cache_key] = False
        self.cache.move_to_end(cache_key)
        if len(self.cache) > self.cache_size:
            self.cache.popitem(last=False)
        if HAS_PROMETHEUS:
            HTTP_FAILED.inc()
        return False
    
    async def test_batch(self, proxies: List[Dict]) -> List[Dict]:
        if not self.config.enable_http_test or not proxies:
            return proxies
        
        semaphore = asyncio.Semaphore(self.config.http_parallel)
        
        async def test_one(proxy):
            async with semaphore:
                working = await self.test_proxy(proxy['ip'], proxy['port'], self.config.http_test_timeout)
                proxy['http_working'] = working
                return proxy
        
        tasks = [test_one(p) for p in proxies]
        return await asyncio.gather(*tasks)
    
    async def close(self):
        if self.session:
            await self.session.close()

class AsyncTCPBatchScanner:
    def __init__(self, max_concurrent: int = 300):
        self.scheduler = PortScheduler(max_concurrent)
        self.dialer = EventDrivenDialer(self.scheduler)
        self._lock = asyncio.Lock()
        self.results = {}
    
    async def scan_batch(self, ips: List[str], ports: List[int], timeout: float = 0.3, min_latency: int = 50, max_latency: int = 200) -> Dict[str, Tuple[int, float]]:
        self.results = {}
        self.scheduler.reset()
        
        async def scan_one(ip: str):
            best_port, best_latency = await self.dialer.scan_ip_parallel(ip, ports, timeout, min_latency, max_latency)
            if best_latency is not None:
                async with self._lock:
                    self.results[ip] = (best_port, best_latency)
        
        tasks = [scan_one(ip) for ip in ips]
        await asyncio.gather(*tasks)
        return self.results

class AsyncStorage:
    def __init__(self, path: str):
        self.path = path
        self.pool = None
        self._lock = asyncio.Lock()
        self.batch_buffer = []
        self.buffer_lock = asyncio.Lock()
        self.buffer_size = 500
        self.flush_interval = 5.0
        self.last_flush = time.time()

    async def init(self):
        self.pool = await aiosqlite.connect(
            self.path,
            isolation_level=None,
            cached_statements=200
        )
        await self.pool.execute("PRAGMA journal_mode=WAL")
        await self.pool.execute("PRAGMA synchronous=NORMAL")
        await self.pool.execute("PRAGMA cache_size=20000")

        await self.pool.execute("""
            CREATE TABLE IF NOT EXISTS proxies (
                ip TEXT PRIMARY KEY,
                port INTEGER,
                avg_latency REAL,
                last_seen REAL,
                country TEXT,
                created_at REAL,
                http_working BOOLEAN DEFAULT 0
            )
        """)
        await self.pool.execute("CREATE INDEX IF NOT EXISTS idx_latency ON proxies(avg_latency)")
        await self.pool.execute("CREATE INDEX IF NOT EXISTS idx_last_seen ON proxies(last_seen)")
        await self.pool.execute("CREATE INDEX IF NOT EXISTS idx_http ON proxies(http_working)")
        await self.pool.commit()

    async def insert_batch(self, proxies: List[Dict]):
        if not proxies:
            return

        async with self._lock:
            await self.pool.executemany("""
                INSERT OR REPLACE INTO proxies (ip, port, avg_latency, last_seen, country, created_at, http_working)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, [(p["ip"], p["port"], p["avg_latency"], p["last_seen"],
                  p.get("country", "XX"), p.get("created_at", time.time()),
                  1 if p.get("http_working", False) else 0)
                  for p in proxies])
            await self.pool.commit()

    async def insert_fast(self, proxy: Dict):
        async with self.buffer_lock:
            self.batch_buffer.append(proxy)
            now = time.time()
            if len(self.batch_buffer) >= self.buffer_size or (now - self.last_flush) >= self.flush_interval:
                await self.insert_batch(self.batch_buffer)
                self.batch_buffer.clear()
                self.last_flush = now

    async def flush(self):
        async with self.buffer_lock:
            if self.batch_buffer:
                await self.insert_batch(self.batch_buffer)
                self.batch_buffer.clear()

    async def cleanup_old(self, retention_days: int = 7):
        cutoff = time.time() - (retention_days * 24 * 60 * 60)
        async with self._lock:
            await self.pool.execute("DELETE FROM proxies WHERE last_seen < ?", (cutoff,))
            await self.pool.commit()

    async def get_best(self, limit: int = 4000) -> List[Dict]:
        async with self.pool.execute("""
            SELECT ip, port, avg_latency, country, http_working FROM proxies
            WHERE avg_latency > 0
            ORDER BY avg_latency ASC
            LIMIT ?
        """, (limit,)) as cursor:
            rows = await cursor.fetchall()
            return [{"ip": r[0], "port": r[1], "avg_latency": r[2], "country": r[3], "http_working": bool(r[4])}
                    for r in rows]

    async def get_count(self) -> int:
        async with self.pool.execute("SELECT COUNT(*) FROM proxies") as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def close(self):
        if self.pool:
            await self.pool.close()

class LRUCache:
    def __init__(self, maxsize: int = 50000):
        self.cache = OrderedDict()
        self.maxsize = maxsize
        self._lock = asyncio.Lock()
    
    async def get(self, key: str) -> Optional[str]:
        async with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    async def set(self, key: str, value: str):
        async with self._lock:
            self.cache[key] = value
            self.cache.move_to_end(key)
            if len(self.cache) > self.maxsize:
                self.cache.popitem(last=False)
    
    def __len__(self):
        return len(self.cache)

class DistributedGeoEnricher:
    def __init__(self, mmdb_path: str = None, use_online: bool = False, thread_pool: int = 4):
        self.mmdb = None
        self.cache = LRUCache(maxsize=50000)
        self.use_online = use_online
        self.logger = logging.getLogger("DistributedGeo")
        self.provider_stats = defaultdict(lambda: {"success": 0, "fail": 0, "total": 0})
        self.thread_pool = ThreadPoolExecutor(max_workers=thread_pool)
        
        if mmdb_path and os.path.exists(mmdb_path) and HAS_MAXMIND:
            try:
                self.mmdb = maxminddb.open(mmdb_path)
                self.logger.info("MaxMind DB loaded")
            except Exception as e:
                self.logger.warning(f"MaxMind load failed: {e}")
        
        self.providers = [
            ("ip-api.com", self._ip_api_com, 45),
        ]
        
        self.semaphores = {}
        for name, _, limit in self.providers:
            self.semaphores[name] = asyncio.Semaphore(max(1, limit // 10))
        
        self.session = None
        self._session_lock = asyncio.Lock()
        self.batch_cache = {}
    
    async def get_session(self):
        if self.session is None:
            async with self._session_lock:
                if self.session is None:
                    connector = aiohttp.TCPConnector(limit=20, limit_per_host=5)
                    self.session = aiohttp.ClientSession(connector=connector)
        return self.session
    
    async def get_country_batch(self, ips: List[str]) -> Dict[str, str]:
        if not ips:
            return {}
        
        results = {}
        uncached = []
        
        for ip in ips:
            cached = await self.cache.get(ip)
            if cached:
                results[ip] = cached
            else:
                uncached.append(ip)
        
        if not uncached:
            return results
        
        if self.mmdb:
            loop = asyncio.get_event_loop()
            
            def query_mmdb(ip):
                try:
                    data = self.mmdb.get(ip)
                    if data and "country" in data:
                        return ip, data["country"]["iso_code"]
                    return ip, None
                except:
                    return ip, None
            
            mmdb_results = await asyncio.gather(*[
                loop.run_in_executor(self.thread_pool, query_mmdb, ip)
                for ip in uncached
            ])
            
            for ip, country in mmdb_results:
                if country:
                    results[ip] = country
                    await self.cache.set(ip, country)
            
            uncached = [ip for ip in uncached if ip not in results]
        
        if not uncached:
            return results
        
        if not self.use_online:
            for ip in uncached:
                results[ip] = "XX"
                await self.cache.set(ip, "XX")
            return results
        
        geo_chunk_size = 20
        chunks = [uncached[i:i+geo_chunk_size] for i in range(0, len(uncached), geo_chunk_size)]
        
        for chunk in chunks:
            chunk_results = await self._process_http_batch(chunk)
            for ip, country in chunk_results.items():
                results[ip] = country
                await self.cache.set(ip, country)
        
        for ip in uncached:
            if ip not in results:
                results[ip] = "XX"
                await self.cache.set(ip, "XX")
        
        return results
    
    async def _process_http_batch(self, ips: List[str]) -> Dict[str, str]:
        results = {}
        
        for ip in ips:
            for name, provider, _ in self.providers:
                try:
                    async with self.semaphores[name]:
                        country = await provider(ip)
                        if country:
                            results[ip] = country
                            self.provider_stats[name]["success"] += 1
                            break
                        else:
                            self.provider_stats[name]["fail"] += 1
                except:
                    self.provider_stats[name]["fail"] += 1
                    continue
            
            if ip not in results:
                results[ip] = "XX"
                self.provider_stats["fallback"]["fail"] += 1
        
        return results
    
    async def _ip_api_com(self, ip: str) -> Optional[str]:
        try:
            session = await self.get_session()
            async with session.get(f"http://ip-api.com/json/{ip}?fields=status,countryCode", timeout=1.5) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data.get("status") == "success":
                        return data.get("countryCode", "")
        except:
            pass
        return None
    
    def get_stats(self) -> Dict:
        stats = {
            "cache_size": len(self.cache),
            "providers": {}
        }
        for name, data in self.provider_stats.items():
            stats["providers"][name] = dict(data)
        return stats
    
    async def close(self):
        if self.session:
            await self.session.close()
        if self.mmdb:
            self.mmdb.close()
        self.thread_pool.shutdown(wait=False)

class RedisQueue:
    def __init__(self, url: str):
        self.url = url
        self.redis = None
        self.local_queue = asyncio.Queue(maxsize=10000)
        self.connected = False
        self._lock = asyncio.Lock()

    async def init(self):
        try:
            self.redis = redis.from_url(self.url, decode_responses=True)
            await self.redis.ping()
            self.connected = True
            logging.getLogger("RedisQueue").info("Redis connected")
        except Exception as e:
            logging.getLogger("RedisQueue").warning(f"Redis unavailable: {e}")
            self.connected = False

    async def push_event(self, event: Dict[str, Any]):
        if self.connected:
            try:
                await self.redis.lpush("scan_queue", msgpack.packb(event, use_bin_type=True))
                return
            except:
                pass
        
        try:
            await self.local_queue.put(event)
        except asyncio.QueueFull:
            await asyncio.sleep(0.01)

    async def pull_events(self, count: int = 300, block: int = 300) -> List[Tuple[Dict, Optional[str]]]:
        events_with_ids = []
        
        if self.connected:
            try:
                pipe = self.redis.pipeline()
                pipe.lrange("scan_queue", 0, count - 1)
                pipe.ltrim("scan_queue", count, -1)
                results = await pipe.execute()
                messages = results[0]
                if messages:
                    for msg in messages:
                        event_data = msgpack.unpackb(msg, raw=False)
                        events_with_ids.append((event_data, None))
                    return events_with_ids
            except:
                pass

        for _ in range(count):
            try:
                event = await asyncio.wait_for(self.local_queue.get(), timeout=0.05)
                events_with_ids.append((event, None))
            except asyncio.TimeoutError:
                break

        return events_with_ids

    async def get_queue_size(self) -> int:
        if self.connected:
            try:
                size = await self.redis.llen("scan_queue")
                return size + self.local_queue.qsize()
            except:
                pass
        return self.local_queue.qsize()

class ProgressTracker:
    def __init__(self, total: int = 0, interval: int = 10):
        self.total = total
        self.current = 0
        self.interval = interval
        self.start_time = time.time()
        self.last_update = time.time()
        self._lock = asyncio.Lock()

    async def update(self, count: int = 1):
        async with self._lock:
            self.current += count
            now = time.time()
            if now - self.last_update >= self.interval and self.total > 0:
                elapsed = now - self.start_time
                rate = self.current / elapsed if elapsed > 0 else 0
                remaining = (self.total - self.current) / rate if rate > 0 else 0
                logging.getLogger("Progress").info(
                    f"Progress: {self.current}/{self.total} ({self.current/self.total*100:.1f}%) "
                    f"Rate: {rate:.1f}/s ETA: {remaining:.0f}s"
                )
                self.last_update = now

    async def finish(self):
        elapsed = time.time() - self.start_time
        if self.current > 0:
            logging.getLogger("Progress").info(
                f"Completed: {self.current} items in {elapsed:.1f}s ({self.current/elapsed:.1f}/s)"
            )

    def set_total(self, total: int):
        self.total = total

class AdaptiveBatcher:
    def __init__(self, base_batch: int = 500):
        self.base_batch = base_batch
        self.current_batch = base_batch
        self.success_rates = []
        self.window = 20
    
    def update(self, success_count: int, attempted_count: int):
        if attempted_count == 0:
            return
        
        rate = success_count / attempted_count
        self.success_rates.append(rate)
        if len(self.success_rates) > self.window:
            self.success_rates.pop(0)
        
        avg_rate = sum(self.success_rates) / len(self.success_rates) if self.success_rates else 1.0
        
        if avg_rate > 0.5:
            self.current_batch = min(800, int(self.base_batch * 1.3))
        elif avg_rate > 0.2:
            self.current_batch = self.base_batch
        else:
            self.current_batch = max(50, int(self.base_batch * 0.6))
    
    def get_batch_size(self) -> int:
        return int(self.current_batch)

class SharedResources:
    def __init__(self, config: Config):
        self.config = config
        self.queue = RedisQueue(config.redis_url)
        self.storage = AsyncStorage(config.db_path)
        self.geo = DistributedGeoEnricher(config.maxmind_path, config.use_online_fallback, config.geo_thread_pool)
        self._initialized = False
    
    async def init(self):
        if not self._initialized:
            await self.queue.init()
            await self.storage.init()
            self._initialized = True

class HybridWorker:
    def __init__(self, config: Config, worker_id: int, shared: SharedResources, progress: ProgressTracker = None):
        self.config = config
        self.worker_id = worker_id
        self.shared = shared
        self.progress = progress
        self.logger = self._setup_logger()
        self.runner_id = config.runner_id

        self.batcher = AdaptiveBatcher(config.batch_size)
        self.scanner = AsyncTCPBatchScanner(max_concurrent=300)
        self.http_tester = HTTPProxyTester(config) if config.enable_http_test else None

        self.running = True
        self.stats = {"scanned": 0, "accepted": 0, "rejected": 0, "errors": 0}

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger(f"Worker-{self.worker_id}")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
        return logger

    async def scan_batch(self, ips: List[str]) -> List[Dict]:
        if not ips:
            return []

        results = []
        batch_size = self.batcher.get_batch_size()
        
        for i in range(0, len(ips), batch_size):
            batch = ips[i:i+batch_size]
            self.stats["scanned"] += len(batch)
            
            if HAS_PROMETHEUS:
                SCANNED_IPS.inc(len(batch))
            
            try:
                start_time = time.time()
                tcp_results = await self.scanner.scan_batch(
                    batch, self.config.ports, self.config.tcp_timeout, self.config.min_latency, self.config.quality_threshold
                )
                
                if HAS_PROMETHEUS:
                    SCAN_LATENCY.observe(time.time() - start_time)
                
                self.batcher.update(len(tcp_results), len(batch))
                
                if tcp_results:
                    ip_list = list(tcp_results.keys())
                    countries = await self.shared.geo.get_country_batch(ip_list)
                    
                    for ip, (port, latency) in tcp_results.items():
                        if latency < self.config.max_latency:
                            proxy_data = {
                                "ip": ip,
                                "port": port,
                                "avg_latency": latency,
                                "last_seen": time.time(),
                                "country": countries.get(ip, "XX"),
                                "created_at": time.time(),
                                "http_working": False
                            }
                            results.append(proxy_data)
                            self.stats["accepted"] += 1
                            
                            if HAS_PROMETHEUS:
                                ACCEPTED_PROXIES.inc()
                        else:
                            self.stats["rejected"] += 1
                            if HAS_PROMETHEUS:
                                REJECTED_IPS.inc()
                
            except Exception as e:
                self.logger.error(f"Batch error: {e}")
                self.stats["errors"] += 1

            if self.progress:
                await self.progress.update(len(batch))

        if self.http_tester and results:
            results = await self.http_tester.test_batch(results)

        for proxy in results:
            await self.shared.storage.insert_fast(proxy)

        return results

    async def consume_loop(self):
        self.logger.info(f"Worker {self.worker_id} started (PID: {os.getpid()}) (Runner: {self.runner_id})")

        if HAS_PROMETHEUS:
            ACTIVE_WORKERS.inc()

        while self.running:
            try:
                events_with_ids = await self.shared.queue.pull_events(count=300, block=300)

                if not events_with_ids:
                    await asyncio.sleep(0.01)
                    continue

                batch_ips = []
                for event, _ in events_with_ids:
                    if "ip" in event:
                        batch_ips.append(event["ip"])

                if not batch_ips:
                    continue

                results = await self.scan_batch(batch_ips)

                if results:
                    for r in results:
                        await self.shared.queue.push_event({
                            "type": "proxy_found",
                            "data": r
                        })

                if self.stats["accepted"] % 500 == 0:
                    self.logger.info(f"Accepted: {self.stats['accepted']} | Rejected: {self.stats['rejected']} | Errors: {self.stats['errors']}")

            except Exception as e:
                self.logger.error(f"Loop error: {e}")
                await asyncio.sleep(0.5)

        if HAS_PROMETHEUS:
            ACTIVE_WORKERS.dec()

        await self.shared.storage.flush()
        if self.http_tester:
            await self.http_tester.close()

class HybridPipeline:
    def __init__(self, config: Config = None):
        self.config = config or Config()
        self.logger = self._setup_logger()

        self.shared = SharedResources(self.config)
        self.progress = ProgressTracker(interval=10)

        self.workers = []
        self.num_workers = min(multiprocessing.cpu_count() * 2, 16)

        if self.config.enable_prometheus and HAS_PROMETHEUS:
            try:
                start_http_server(self.config.prometheus_port)
                self.logger.info(f"Prometheus metrics exposed on port {self.config.prometheus_port}")
            except Exception as e:
                self.logger.warning(f"Failed to start Prometheus server: {e}")

    def _setup_logger(self) -> logging.Logger:
        logger = logging.getLogger("HybridPipeline")
        logger.setLevel(logging.INFO)
        if not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
            logger.addHandler(handler)
        return logger

    async def fetch_and_push_ips(self):
        self.logger.info("Fetching IPs...")

        sources = [
            "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/cloudflare/cloudflare_plain_ipv4.txt",
            "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/fastly/fastly_plain_ipv4.txt",
            "https://raw.githubusercontent.com/123jjck/cdn-ip-ranges/main/akamai/akamai_plain_ipv4.txt",
            "https://raw.githubusercontent.com/rezakhosh78/RKh-CF-Scanner/main/ip-ranges/iran/Noyan%20Abr%20Arvan%20Co_3.txt",
            "https://raw.githubusercontent.com/rezakhosh78/RKh-CF-Scanner/main/ip-ranges/iran/Pars%20Online.txt"
        ]

        total_ips = 0

        async with aiohttp.ClientSession() as session:
            for url in sources:
                if total_ips >= 10000:
                    break

                try:
                    async with session.get(url, timeout=15) as resp:
                        if resp.status != 200:
                            self.logger.warning(f"Source {url} returned {resp.status}")
                            continue

                        text = await resp.text()

                        def parse_ips(text: str) -> List[str]:
                            import ipaddress
                            ips = []
                            seen = set()
                            for line in text.splitlines():
                                if "/" in line:
                                    try:
                                        net = ipaddress.ip_network(line.strip(), strict=False)
                                        if net.num_addresses > 2:
                                            sample_size = min(10, max(1, int(net.num_addresses / 1000)))
                                            for _ in range(sample_size):
                                                offset = random.randint(1, net.num_addresses - 2)
                                                ip_str = str(net.network_address + offset)
                                                if ip_str not in seen:
                                                    seen.add(ip_str)
                                                    ips.append(ip_str)
                                    except:
                                        pass
                            return ips

                        loop = asyncio.get_event_loop()
                        with ThreadPoolExecutor(max_workers=1) as executor:
                            ips = await loop.run_in_executor(executor, parse_ips, text)

                        self.logger.info(f"Got {len(ips)} IPs from {url}")

                        for ip in ips[:2000]:
                            await self.shared.queue.push_event({
                                "ts": time.time(),
                                "ip": ip,
                                "type": "scan_request",
                                "runner": self.config.runner_id
                            })
                            total_ips += 1

                except Exception as e:
                    self.logger.error(f"Error fetching {url}: {e}")

        self.progress.set_total(total_ips)
        self.logger.info(f"All {total_ips} IPs pushed to queue")

    async def show_progress(self):
        while True:
            try:
                count = await self.shared.storage.get_count()
                self.logger.info(f"Database: {count} proxies stored")
                if HAS_PROMETHEUS:
                    PROXY_COUNT.set(count)
                    queue_size = await self.shared.queue.get_queue_size()
                    QUEUE_SIZE.set(queue_size)
                await asyncio.sleep(30)
            except:
                await asyncio.sleep(30)

    async def run(self):
        self.logger.info("Starting Hybrid Pipeline...")
        self.logger.info(f"Runner ID: {self.config.runner_id}")
        self.logger.info(f"Max output IPs: {self.config.max_output_ips}")
        self.logger.info(f"Retention days: {self.config.retention_days}")
        self.logger.info(f"Workers: {self.num_workers}")
        self.logger.info(f"HTTP Test: {self.config.enable_http_test}")
        self.logger.info(f"Prometheus: {self.config.enable_prometheus}")
        self.logger.info(f"UV Loop: {HAS_UVLOOP}")
        self.logger.info(f"Quality threshold: {self.config.quality_threshold}ms")

        await self.shared.init()

        await self.shared.storage.cleanup_old(self.config.retention_days)

        for i in range(self.num_workers):
            worker = HybridWorker(self.config, i, self.shared, self.progress)
            self.workers.append(worker)

        producer_task = asyncio.create_task(self.fetch_and_push_ips())
        worker_tasks = [asyncio.create_task(w.consume_loop()) for w in self.workers]
        progress_task = asyncio.create_task(self.show_progress())

        try:
            await producer_task

            self.logger.info("Waiting for queue to drain...")

            for _ in range(30):
                queue_size = await self.shared.queue.get_queue_size()
                if queue_size == 0:
                    break
                await asyncio.sleep(1)

            for w in self.workers:
                w.running = False

            await asyncio.sleep(2)
            await asyncio.gather(*worker_tasks, return_exceptions=True)

            await self.progress.finish()

            best = await self.shared.storage.get_best(self.config.max_output_ips)

            self.logger.info(f"Found {len(best)} best proxies")

            with open("proxies_output.txt", "w") as f:
                f.write("IP,Port,Latency(ms),Country,HTTP_Working\n")
                for p in best:
                    f.write(f"{p['ip']},{p['port']},{p['avg_latency']:.0f},{p['country']},{p['http_working']}\n")

            with open("proxies_output.json", "w") as f:
                json.dump(best, f, indent=2)

            count = await self.shared.storage.get_count()
            self.logger.info(f"Output saved to proxies_output.txt ({len(best)} IPs)")
            self.logger.info(f"Total proxies in database: {count}")

            geo_stats = self.shared.geo.get_stats()
            if geo_stats:
                self.logger.info(f"Geo stats: {geo_stats}")

        except KeyboardInterrupt:
            self.logger.info("Shutting down...")
            for w in self.workers:
                w.running = False
        finally:
            await self.shared.storage.close()
            await self.shared.geo.close()

async def main():
    config = Config(
        ultra_mode=True,
        max_workers=80,
        batch_size=500,
        max_output_ips=4000,
        retention_days=7,
        maxmind_path="GeoLite2-Country.mmdb",
        use_online_fallback=False,
        max_ports_per_ip=7,
        enable_http_test=True,
        enable_prometheus=True,
        enable_uvloop=True,
        tcp_timeout=0.3,
        http_test_timeout=1.0,
        http_parallel=200,
        quality_threshold=200,
        geo_thread_pool=4,
        runner_id=f"runner-{os.getpid()}"
    )
    pipeline = HybridPipeline(config)
    await pipeline.run()

if __name__ == "__main__":
    asyncio.run(main())
