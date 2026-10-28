#!/usr/bin/env python3
"""responsibility.py — shared responsibility model: কোন স্তর কার দায়িত্ব, service model অনুযায়ী; incident-এ কে কাজ করবে।

  python3 responsibility.py matrix
  python3 responsibility.py who --layer os --model paas
  python3 responsibility.py incidents sample-incidents.json --model iaas

Matrix provider-দের প্রকাশিত shared responsibility model-এর সাধারণ রূপ (AWS/Azure/Google-এর diagram-এর মিল);
নির্দিষ্ট service-এ সীমারেখা আলাদা হতে পারে — সবসময় সেই service-এর documentation দেখুন।
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MODELS = ["on-prem", "iaas", "paas", "faas", "saas"]
P, C, S = "provider", "customer", "shared"
# layer → প্রতিটি model-এ কে (MODELS-এর ক্রমে)
MATRIX: dict[str, list[str]] = {
    "physical":     [C, P, P, P, P],     # data center, hardware, power
    "network-infra": [C, P, P, P, P],    # physical network, hypervisor network
    "hypervisor":   [C, P, P, P, P],
    "network-config": [C, C, S, S, P],   # firewall/security group, routing — আপনার VPC
    "os":           [C, C, P, P, P],     # OS patch, kernel
    "runtime":      [C, C, S, P, P],     # Python/Node version, middleware; PaaS-এ version বাছাই আপনার
    "application":  [C, C, C, C, P],     # নিজের code ও তার dependency
    "resilience":   [C, C, C, S, S],     # একটি AZ/region গেলেও workload চলবে কিনা — architecture আপনার (L07-03)
    "configuration": [C, C, C, C, C],    # app/service-এর setting — SaaS-এও (sharing, retention)
    "identity":     [C, C, C, C, C],     # কে access পাবে, MFA, key — সবসময় আপনার
    "data":         [C, C, C, C, C],     # data-র শ্রেণিবিভাগ, backup নীতি, encryption-এর সিদ্ধান্ত
    "endpoint":     [C, C, C, C, C],     # user-এর laptop/phone
}


def who(layer: str, model: str) -> str:
    if layer not in MATRIX:
        raise KeyError(f"unknown layer {layer!r} (known: {', '.join(MATRIX)})")
    if model not in MODELS:
        raise KeyError(f"unknown model {model!r} (known: {', '.join(MODELS)})")
    return MATRIX[layer][MODELS.index(model)]


def customer_layers(model: str) -> list[str]:
    return [layer for layer in MATRIX if who(layer, model) in (C, S)]


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Shared responsibility model.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("matrix")
    w = sub.add_parser("who")
    w.add_argument("--layer", required=True)
    w.add_argument("--model", required=True)
    i = sub.add_parser("incidents")
    i.add_argument("file", type=Path)
    i.add_argument("--model", required=True)
    a = ap.parse_args(argv)
    try:
        if a.cmd == "matrix":
            print(f"{'layer':<16}" + "".join(f"{m:<10}" for m in MODELS))
            for layer, row in MATRIX.items():
                print(f"{layer:<16}" + "".join(f"{r:<10}" for r in row))
            print(f"{'customer+shared':<16}" + "".join(f"{len(customer_layers(m)):<10}" for m in MODELS))
        elif a.cmd == "who":
            print(who(a.layer, a.model))
        else:
            incidents = json.loads(a.file.read_text(encoding="utf-8"))
            for inc in incidents:
                print(f"{who(inc['layer'], a.model):<9} {inc['layer']:<15} {inc['incident']}")
    except (KeyError, OSError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
