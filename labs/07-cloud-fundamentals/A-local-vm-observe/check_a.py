#!/usr/bin/env python3
"""Lab 07-A verification — host ও guest-এর virt_probe.py JSON এবং আপনার observations.json মেলানো (offline)।

  python3 check_a.py ~/lab07a/host.json ~/lab07a/guest.json ~/lab07a/observations.json

যাচাই: guest সত্যিই VM (Linux, hypervisor চেনা গেছে); host ও guest আলাদা machine; guest-এর logical CPU = ঘোষিত vCPU;
overcommit-এর অনুপাত L07-01-এর overcommit()-এর সাথে মেলে; steal মাপ দুটি (idle ও busy) /proc/stat-এর রূপে;
snapshot নেওয়া হয়েছে।
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "07-cloud-fundamentals" / "code" / "L07-01"))
import virt_probe as vp  # noqa: E402

STEAL_KEYS = {"user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"}


def logical_cpus(probe: dict) -> int | None:
    for line in probe.get("evidence", []):
        m = re.search(r"logical CPUs: (\d+)", line)
        if m:
            return int(m.group(1))
    return None


def steal_ok(d: object) -> bool:
    return isinstance(d, dict) and STEAL_KEYS <= set(d) and abs(sum(d[k] for k in STEAL_KEYS) - 100) <= 1.0


def check(host: dict, guest: dict, obs: dict) -> list[tuple[bool, str]]:
    out = []
    out.append((guest.get("platform") == "linux", f"guest.json comes from Linux (platform={guest.get('platform')})"))
    out.append((guest.get("virtualized") is True and bool(guest.get("hypervisor")),
                f"guest is detected as a VM (hypervisor={guest.get('hypervisor')})"))
    out.append((guest.get("container") is None, "guest.json is from the VM itself, not a container inside it"))
    out.append((host.get("evidence") != guest.get("evidence"), "host.json and guest.json are different machines"))
    if host.get("virtualized") is True:
        out.append((bool(obs.get("nested_note")), "host is itself a VM — observations.nested_note explains nesting"))

    vms = obs.get("vms") or []
    out.append((bool(vms) and all({"name", "vcpus", "ram_gb"} <= set(v) for v in vms),
                "observations.vms lists every running VM with name, vcpus, ram_gb"))
    if vms:
        guest_cpus = logical_cpus(guest)
        out.append((guest_cpus == vms[0]["vcpus"], f"guest sees {guest_cpus} CPU(s) = vms[0].vcpus ({vms[0]['vcpus']})"))
        want = vp.overcommit(obs["host_cores"], sum(v["vcpus"] for v in vms),
                             obs["host_ram_gb"], sum(v["ram_gb"] for v in vms))
        for key in ("vcpu_per_pcpu", "memory_overcommit"):
            got = obs.get(key)
            out.append((isinstance(got, (int, float)) and abs(got - want[key]) <= 0.01,
                        f"observations.{key} = {got} matches overcommit() ({want[key]})"))
    host_cpus = logical_cpus(host)
    out.append((host_cpus is None or obs.get("host_cores") == host_cpus,
                f"observations.host_cores = {obs.get('host_cores')} matches host.json ({host_cpus})"))
    out.append((steal_ok(obs.get("steal_idle")), "steal_idle is a 'virt_probe.py steal' result"))
    out.append((steal_ok(obs.get("steal_busy")), "steal_busy is a 'virt_probe.py steal' result"))
    if steal_ok(obs.get("steal_idle")) and steal_ok(obs.get("steal_busy")):
        out.append((obs["steal_busy"]["idle"] < obs["steal_idle"]["idle"],
                    "the busy measurement really was under load (idle% dropped)"))
    out.append((obs.get("snapshot_taken") is True, "a snapshot of the clean VM was taken"))
    return out


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    ap.add_argument("host", type=Path)
    ap.add_argument("guest", type=Path)
    ap.add_argument("observations", type=Path)
    a = ap.parse_args()
    try:
        host, guest, obs = (json.loads(p.read_text(encoding="utf-8")) for p in (a.host, a.guest, a.observations))
        results = check(host, guest, obs)
    except (OSError, json.JSONDecodeError, KeyError, TypeError, ZeroDivisionError) as exc:
        print(f"error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    for ok, label in results:
        print(("PASS  " if ok else "FAIL  ") + label)
    failed = sum(not ok for ok, _ in results)
    print("ALL CHECKS PASSED" if not failed else f"{failed} CHECK(S) FAILED")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
