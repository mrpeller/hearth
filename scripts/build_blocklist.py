#!/usr/bin/env python3
"""Build adblock/blocklist.txt: the ad and tracker domains the DNS ad blocker refuses.

    python3 scripts/build_blocklist.py                      # from EasyList (downloaded)
    python3 scripts/build_blocklist.py --extension PATH      # from an MV3 ad-blocker extension's compiled rules

Only whole-domain rules are used ("||ads.example.com^"), because a DNS blocker can't see
page paths. EasyList is dual-licensed GPLv3 / CC BY-SA 3.0: https://easylist.to
"""
import argparse
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "adblock" / "blocklist.txt"
EASYLIST = ("https://easylist.to/easylist/easylist.txt", "https://easylist.to/easylist/easyprivacy.txt")
DOMAIN_RULE = re.compile(r"\|\|([a-z0-9.-]+\.[a-z]{2,})\^$")


def from_easylist():
    domains = set()
    for url in EASYLIST:
        print(f"Downloading {url}")
        req = urllib.request.Request(url, headers={"User-Agent": "hearth-blocklist"})
        with urllib.request.urlopen(req, timeout=60) as r:
            for line in r.read().decode("utf-8", "ignore").splitlines():
                m = DOMAIN_RULE.match(line.strip())
                if m:
                    domains.add(m.group(1))
    return domains, "EasyList + EasyPrivacy (https://easylist.to)"


def from_extension(folder):
    """Block rules with only requestDomains (no page conditions) from an extension's generated/*.json."""
    domains = set()
    for f in sorted(Path(folder).glob("generated/rules-*.json")):
        for rule in json.loads(f.read_text(encoding="utf-8")):
            cond, action = rule.get("condition", {}), rule.get("action", {}).get("type")
            if action == "block" and cond.get("requestDomains") and not set(cond) - {"requestDomains", "resourceTypes", "excludedResourceTypes"}:
                domains.update(cond["requestDomains"])
    return domains, f"ad-blocker extension at {folder}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--extension", help="folder of an MV3 ad-blocker extension with generated/rules-*.json")
    args = parser.parse_args()
    domains, source = from_extension(args.extension) if args.extension else from_easylist()
    if not domains:
        sys.exit("No domains found.")
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(f"# Built by scripts/build_blocklist.py from {source}\n" + "\n".join(sorted(domains)) + "\n", encoding="utf-8")
    print(f"Wrote {len(domains):,} domains to {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
