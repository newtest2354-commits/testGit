import json
import ipaddress
import pathlib
import requests
import time

OUTPUT_DIR = pathlib.Path("output")

BGPVIEW_SEARCH = "https://api.bgpview.io/search?query_term={}"
RIPE_PREFIXES = "https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS{}"

OUTPUT_DIR.mkdir(exist_ok=True)

with open(
    "companies.json",
    "r",
    encoding="utf-8"
) as f:
    companies = json.load(f)

all_prefixes = set()


def get_asns(company):
    asns = set()

    try:
        r = requests.get(
            BGPVIEW_SEARCH.format(company),
            timeout=30
        )

        data = r.json()

        if "data" not in data:
            return asns

        for item in data["data"].get("asns", []):
            try:
                asns.add(int(item["asn"]))
            except Exception:
                pass

    except Exception as e:
        print(company, e)

    return asns


def get_prefixes(asn):
    prefixes = set()

    try:
        r = requests.get(
            RIPE_PREFIXES.format(asn),
            timeout=30
        )

        data = r.json()

        for item in data["data"]["prefixes"]:
            prefix = item["prefix"]

            if ":" in prefix:
                continue

            try:
                ipaddress.ip_network(
                    prefix,
                    strict=False
                )
                prefixes.add(prefix)
            except Exception:
                pass

    except Exception as e:
        print(f"AS{asn}", e)

    return prefixes


for group_name, company_list in companies.items():

    for company in company_list:

        print("Processing:", company)

        company_prefixes = set()

        asns = get_asns(company)

        for asn in asns:
            company_prefixes.update(
                get_prefixes(asn)
            )

            time.sleep(0.5)

        company_prefixes = sorted(
            company_prefixes,
            key=lambda x: (
                int(
                    ipaddress.ip_network(
                        x,
                        strict=False
                    ).network_address
                ),
                ipaddress.ip_network(
                    x,
                    strict=False
                ).prefixlen
            )
        )

        filename = (
            OUTPUT_DIR /
            f"{company}.txt"
        )

        with open(
            filename,
            "w",
            encoding="utf-8"
        ) as f:
            f.write(
                "\n".join(
                    company_prefixes
                )
            )

        all_prefixes.update(
            company_prefixes
        )

all_prefixes = sorted(
    all_prefixes,
    key=lambda x: (
        int(
            ipaddress.ip_network(
                x,
                strict=False
            ).network_address
        ),
        ipaddress.ip_network(
            x,
            strict=False
        ).prefixlen
    )
)

with open(
    OUTPUT_DIR /
    "ipv4-aggregated.txt",
    "w",
    encoding="utf-8"
) as f:
    f.write(
        "\n".join(
            all_prefixes
        )
    )
