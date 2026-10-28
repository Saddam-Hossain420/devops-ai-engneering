#!/usr/bin/env python3
"""virt_probe.py — এই machine কি virtual machine? কোন hypervisor? কোন প্রমাণে? (শুধু পড়ে, কিছু বদলায় না)

  python3 virt_probe.py                    # Linux: systemd-detect-virt + DMI + /proc/cpuinfo; Windows: CIM
  python3 virt_probe.py --json
  python3 virt_probe.py overcommit --hosts-cores 32 --vcpus 96 --host-ram-gb 256 --vm-ram-gb 300

প্রমাণের উৎস একাধিক, কারণ একটিও নিশ্চিত নয়: DMI vendor বদলানো যায়, nested virtualization-এ স্তর মিশে যায়,
container (Docker, LXC) VM নয় — systemd-detect-virt দুটোকে আলাদা করে বলে।
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# DMI-র vendor/product-এ যে লেখা থাকলে কোন hypervisor বোঝায় (ছোট হাতে তুলনা)
SIGNATURES = [
    ("kvm", ("qemu", "kvm", "openstack", "red hat")),
    ("amazon", ("amazon ec2",)),
    ("google", ("google compute engine",)),
    ("microsoft", ("microsoft corporation", "virtual machine", "hyper-v")),
    ("vmware", ("vmware",)),
    ("oracle", ("virtualbox", "innotek")),
    ("xen", ("xen",)),
]


@dataclass
class Probe:
    platform: str
    virtualized: bool | None = None          # None = নিশ্চিত নয়
    hypervisor: str | None = None
    container: str | None = None
    evidence: list[str] = field(default_factory=list)


def classify(vendor: str, product: str) -> str | None:
    text = f"{vendor} {product}".lower()
    if "microsoft" in text and "virtual" not in text:     # Surface/Microsoft-এর আসল hardware VM নয়
        return None
    for name, needles in SIGNATURES:
        if any(n in text for n in needles):
            return name
    return None


def probe_linux(root: Path = Path("/")) -> Probe:
    p = Probe("linux")
    dmi = root / "sys/class/dmi/id"
    vendor = (dmi / "sys_vendor").read_text().strip() if (dmi / "sys_vendor").is_file() else ""
    product = (dmi / "product_name").read_text().strip() if (dmi / "product_name").is_file() else ""
    if vendor or product:
        p.evidence.append(f"DMI: vendor={vendor!r} product={product!r}")
    cpuinfo = root / "proc/cpuinfo"
    flag = False
    if cpuinfo.is_file():
        flags = next((ln for ln in cpuinfo.read_text().splitlines() if ln.startswith("flags")), "")
        flag = " hypervisor" in f" {flags.split(':', 1)[-1]} "
        p.evidence.append(f"cpuinfo hypervisor flag: {flag}")
    if root == Path("/") and shutil.which("systemd-detect-virt"):
        vm = subprocess.run(["systemd-detect-virt", "--vm"], capture_output=True, text=True).stdout.strip()
        ct = subprocess.run(["systemd-detect-virt", "--container"], capture_output=True, text=True).stdout.strip()
        p.evidence.append(f"systemd-detect-virt: vm={vm or '-'} container={ct or '-'}")
        if ct and ct != "none":
            p.container = ct
        if vm and vm != "none":
            p.virtualized, p.hypervisor = True, vm
            return p
    guess = classify(vendor, product)
    if guess or flag:
        p.virtualized, p.hypervisor = True, guess or "unknown (hypervisor flag set)"
    elif vendor or product:
        p.virtualized = False
    return p


def probe_windows() -> Probe:
    p = Probe("windows")
    cmd = ("Get-CimInstance Win32_ComputerSystem | "
           "Select-Object Manufacturer,Model,HypervisorPresent | ConvertTo-Json -Compress")
    r = subprocess.run(["powershell", "-NoProfile", "-Command", cmd], capture_output=True, text=True, timeout=60)
    if r.returncode != 0 or not r.stdout.strip():
        p.evidence.append("CIM query failed")
        return p
    info = json.loads(r.stdout)
    vendor, model = info.get("Manufacturer") or "", info.get("Model") or ""
    p.evidence.append(f"CIM: manufacturer={vendor!r} model={model!r} HypervisorPresent={info.get('HypervisorPresent')}")
    guess = classify(vendor, model)
    if guess:
        p.virtualized, p.hypervisor = True, guess
    else:
        p.virtualized = False
        if info.get("HypervisorPresent"):
            # Hyper-V/VBS/WSL2 চালু থাকলে Windows নিজেই root partition-এ চলে — physical machine, কিন্তু hypervisor উপস্থিত
            p.hypervisor = "hypervisor present (this OS is the Hyper-V root partition — host, not a guest)"
    return p


def overcommit(host_cores: int, vcpus: int, host_ram_gb: float, vm_ram_gb: float) -> dict[str, object]:
    cpu_ratio = vcpus / host_cores
    ram_ratio = vm_ram_gb / host_ram_gb
    notes = []
    if cpu_ratio > 4:
        notes.append(f"vCPU:pCPU {cpu_ratio:.1f}:1 — high; expect CPU steal (%st) when guests are busy together")
    if ram_ratio > 1:
        notes.append(f"memory {ram_ratio:.0%} of host — overcommitted RAM means ballooning/swap on the host: "
                     "every guest slows down, unlike CPU overcommit which only shares time")
    return {"vcpu_per_pcpu": round(cpu_ratio, 2), "memory_overcommit": round(ram_ratio, 2), "notes": notes}


def steal_percent(before: str, after: str) -> dict[str, float]:
    """/proc/stat-এর দুটি "cpu …" লাইন থেকে সময়ের ভাগ। steal = hypervisor অন্য guest-কে CPU দিয়েছে, আমরা অপেক্ষায় ছিলাম।"""
    names = ["user", "nice", "system", "idle", "iowait", "irq", "softirq", "steal"]
    a = [int(x) for x in before.split()[1:9]]
    b = [int(x) for x in after.split()[1:9]]
    delta = [y - x for x, y in zip(a, b, strict=True)]
    total = sum(delta) or 1
    return {n: round(100 * d / total, 1) for n, d in zip(names, delta, strict=True)}


def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    argv = sys.argv[1:] if argv is None else argv
    if argv[:1] == ["steal"]:
        stat = Path("/proc/stat")
        if not stat.is_file():
            print("error: /proc/stat not available (Linux only)", file=sys.stderr)
            return 2
        import time
        first = stat.read_text().splitlines()[0]
        time.sleep(float(argv[1]) if len(argv) > 1 else 1.0)
        print(json.dumps(steal_percent(first, stat.read_text().splitlines()[0]), indent=2))
        return 0
    if argv[:1] == ["overcommit"]:
        ap = argparse.ArgumentParser(prog="virt_probe.py overcommit")
        ap.add_argument("--host-cores", type=int, required=True)
        ap.add_argument("--vcpus", type=int, required=True)
        ap.add_argument("--host-ram-gb", type=float, required=True)
        ap.add_argument("--vm-ram-gb", type=float, required=True)
        a = ap.parse_args(argv[1:])
        print(json.dumps(overcommit(a.host_cores, a.vcpus, a.host_ram_gb, a.vm_ram_gb), indent=2, ensure_ascii=False))
        return 0
    ap = argparse.ArgumentParser(description="Is this machine a VM?")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--root", type=Path, default=Path("/"), help="Linux: read DMI/cpuinfo from a copied tree")
    a = ap.parse_args(argv)
    p = probe_windows() if os.name == "nt" and a.root == Path("/") else probe_linux(a.root)
    p.evidence.append(f"python platform: {platform.platform()}; logical CPUs: {os.cpu_count()}")
    if a.json:
        print(json.dumps(asdict(p), indent=2, ensure_ascii=False))
    else:
        state = {True: "VIRTUAL MACHINE", False: "physical (no VM evidence)", None: "unknown"}[p.virtualized]
        print(f"{state}" + (f" — {p.hypervisor}" if p.hypervisor else "") + (f"; container: {p.container}" if p.container else ""))
        for e in p.evidence:
            print(f"  evidence: {e}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
