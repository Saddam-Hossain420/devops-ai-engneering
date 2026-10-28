#!/usr/bin/env python3
"""`ip -j -d link` JSON থেকে topology: কোন veth কোন bridge-এ, কোন peer কোন namespace-এ।
Container networking debug-এ প্রশ্ন: "এই container-এর veth host-এ কোনটি?"

  ip -j -d link > links.json && python3 netns_inspect.py links.json
  python3 netns_inspect.py sample-links.json        # হাতে তৈরি নমুনা (Docker bridge + lab bridge)

Exit: 0 OK, 1 finding (DOWN bridge member, master নেই এমন veth), 2 input error।
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path


def kind(link: dict) -> str:
    return link.get("linkinfo", {}).get("info_kind", link.get("link_type", "?"))


def topology(links: list[dict]) -> tuple[dict[str, list[dict]], list[dict], list[str]]:
    """(bridge → সদস্য list, master ছাড়া veth list, finding list)।"""
    bridges = {l["ifname"]: [] for l in links if kind(l) == "bridge"}
    loose, findings = [], []
    for l in links:
        if kind(l) != "veth":
            continue
        master = l.get("master")
        if master in bridges:
            bridges[master].append(l)
            if l.get("operstate") == "DOWN":
                findings.append(f"{l['ifname']} on {master} is DOWN — the namespace behind it has no connectivity")
        else:
            loose.append(l)
            findings.append(f"{l['ifname']} is a veth without a bridge master — packets go nowhere unless routed")
    for name, members in bridges.items():
        br = next(l for l in links if l["ifname"] == name)
        if members and "UP" not in br.get("flags", []):
            findings.append(f"bridge {name} is not UP but has {len(members)} member(s)")
    return bridges, loose, findings


def describe_peer(l: dict) -> str:
    """veth-এর অপর প্রান্ত: link_netnsid থাকলে অন্য namespace-এ (container), নইলে একই namespace-এ।"""
    if "link_netnsid" in l:
        return f"peer ifindex {l.get('link_index', '?')} in netns id {l['link_netnsid']}"
    return f"peer {l.get('link', '?')} in this namespace"


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Show bridge/veth topology from `ip -j -d link`.")
    ap.add_argument("file", type=Path)
    args = ap.parse_args(argv)
    try:
        links = json.loads(args.file.read_text(encoding="utf-8"))
        if not isinstance(links, list):
            raise ValueError("expected a JSON list (output of ip -j -d link)")
        bridges, loose, findings = topology(links)
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    addrs: dict[str, list[str]] = defaultdict(list)
    for l in links:
        for a in l.get("addr_info", []):
            addrs[l["ifname"]].append(f"{a['local']}/{a['prefixlen']}")
    for name, members in bridges.items():
        print(f"bridge {name} {' '.join(addrs[name]) or ''}".rstrip())
        for m in members:
            print(f"  └─ {m['ifname']:<14} {m.get('operstate', '?'):<5} {describe_peer(m)}")
    for l in loose:
        print(f"(no bridge) {l['ifname']} {describe_peer(l)}")
    for f in findings:
        print(f"- {f}")
    return 1 if findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
