#!/usr/bin/env python3
"""Lab environment checker — এই repository-র lab চালানোর জন্য machine প্রস্তুত কিনা যাচাই করে।

সম্পূর্ণ read-only: শুধু file পড়ে ও `--version` জাতীয় command চালায়, কিছু install বা পরিবর্তন করে না।

যাচাই করে:
  - OS (Ubuntu প্রধান, Fedora সমর্থিত) ও WSL কিনা
  - systemd PID 1 কিনা (systemd lesson-এর জন্য)
  - Python version (>= 3.10) ও virtual environment সক্রিয় কিনা
  - দরকারি tool (git, curl, jq ...) ও ঐচ্ছিক tool (docker ...)
  - RAM, CPU, disk free
  - engineering notebook directory

Usage:
  python3 check_env.py
  python3 check_env.py --json
  python3 check_env.py --notebook ~/devops-notebook
Exit code: 0 = কোনো FAIL নেই, 1 = অন্তত একটি FAIL
"""
from __future__ import annotations

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REQUIRED_TOOLS = ("git", "curl", "jq", "tree", "dig", "ip", "ss")
OPTIONAL_TOOLS = ("docker", "tcpdump", "mtr", "traceroute", "htop", "shellcheck")
MIN_PYTHON = (3, 10)
MIN_RAM_GB = 4.0
MIN_DISK_GB = 20.0


@dataclass(frozen=True)
class Check:
    name: str
    status: str  # PASS / WARN / FAIL / INFO
    detail: str


def parse_os_release(text: str) -> dict[str, str]:
    """/etc/os-release: KEY=value বা KEY="value" লাইন।"""
    data: dict[str, str] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key] = value.strip().strip('"').strip("'")
    return data


def parse_meminfo_gb(text: str) -> float | None:
    """/proc/meminfo-র 'MemTotal:  16314064 kB' → GB (1024³ byte)."""
    for line in text.splitlines():
        if line.startswith("MemTotal:"):
            kb = int(line.split()[1])
            return round(kb / 1024 / 1024, 1)
    return None


def is_wsl(proc_version: str) -> bool:
    return "microsoft" in proc_version.lower()


def check_os(os_release: dict[str, str], system: str) -> Check:
    if system != "Linux":
        return Check("os", "FAIL", f"{system} — lab-গুলো Linux-এর জন্য (Ubuntu সুপারিশকৃত)")
    distro = os_release.get("ID", "unknown")
    pretty = os_release.get("PRETTY_NAME", distro)
    if distro == "ubuntu":
        return Check("os", "PASS", pretty)
    if distro == "fedora":
        return Check("os", "PASS", f"{pretty} (lesson-এর 'Fedora-তে' note অনুসরণ করুন)")
    return Check("os", "WARN", f"{pretty} — Ubuntu/Fedora নয়; command আলাদা হতে পারে")


def check_python(version: tuple[int, int, int], in_venv: bool) -> list[Check]:
    v = ".".join(map(str, version))
    checks = [Check("python", "PASS" if version[:2] >= MIN_PYTHON else "FAIL",
                    f"{v} (minimum {MIN_PYTHON[0]}.{MIN_PYTHON[1]})")]
    checks.append(Check("venv", "PASS" if in_venv else "INFO",
                        "virtual environment সক্রিয়" if in_venv else
                        "venv সক্রিয় নয় — এই script-এর জন্য দরকার নেই, কিন্তু project-এ ব্যবহার করুন"))
    return checks


def check_tools(which=shutil.which) -> list[Check]:
    checks = []
    for tool in REQUIRED_TOOLS:
        path = which(tool)
        checks.append(Check(f"tool:{tool}", "PASS" if path else "FAIL", path or "পাওয়া যায়নি"))
    for tool in OPTIONAL_TOOLS:
        path = which(tool)
        checks.append(Check(f"tool:{tool}", "PASS" if path else "INFO",
                            path or "ঐচ্ছিক — সংশ্লিষ্ট module-এ install হবে"))
    return checks


def check_resources(ram_gb: float | None, cpus: int | None, disk_free_gb: float) -> list[Check]:
    checks = []
    if ram_gb is None:
        checks.append(Check("ram", "WARN", "মাপা যায়নি"))
    else:
        checks.append(Check("ram", "PASS" if ram_gb >= MIN_RAM_GB else "WARN",
                            f"{ram_gb} GB (minimum {MIN_RAM_GB:g}, Kubernetes/observability-তে 8–16 GB)"))
    checks.append(Check("cpu", "PASS" if (cpus or 0) >= 2 else "WARN", f"{cpus} logical CPU"))
    checks.append(Check("disk", "PASS" if disk_free_gb >= MIN_DISK_GB else "WARN",
                        f"{disk_free_gb:.1f} GB free in home (minimum {MIN_DISK_GB:g})"))
    return checks


def read_text(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def tool_version(cmd: list[str]) -> str:
    """'git --version' জাতীয় read-only command-এর প্রথম লাইন।"""
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=5, check=False)
        return (out.stdout or out.stderr).strip().splitlines()[0]
    except (OSError, subprocess.TimeoutExpired, IndexError):
        return ""


def gather(notebook: Path) -> list[Check]:
    system = platform.system()
    checks = [check_os(parse_os_release(read_text("/etc/os-release")), system)]
    if system == "Linux":
        wsl = is_wsl(read_text("/proc/version"))
        checks.append(Check("wsl", "INFO", "WSL — কিছু kernel-level lab-এ VM দরকার হবে" if wsl
                            else "WSL নয় (native বা VM)"))
        pid1 = read_text("/proc/1/comm").strip()
        checks.append(Check("systemd", "PASS" if pid1 == "systemd" else "WARN",
                            f"PID 1 = {pid1 or 'unknown'}"))
    checks += check_python(sys.version_info[:3], sys.prefix != sys.base_prefix)
    checks += check_tools()
    git = tool_version(["git", "--version"])
    if git:
        checks.append(Check("git-version", "INFO", git))
    ram = parse_meminfo_gb(read_text("/proc/meminfo")) if system == "Linux" else None
    disk = shutil.disk_usage(Path.home()).free / 1024**3
    checks += check_resources(ram, os.cpu_count(), disk)
    checks.append(Check("notebook", "PASS" if notebook.is_dir() else "WARN",
                        str(notebook) if notebook.is_dir() else f"{notebook} নেই — init-notebook.sh চালান"))
    return checks


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    p = argparse.ArgumentParser(description="Verify the lab environment (read-only).")
    p.add_argument("--json", action="store_true")
    p.add_argument("--notebook", type=Path, default=Path.home() / "devops-notebook")
    args = p.parse_args(argv)

    checks = gather(args.notebook.expanduser())
    if args.json:
        print(json.dumps([asdict(c) for c in checks], ensure_ascii=False, indent=2))
    else:
        for c in checks:
            print(f"[{c.status:4}] {c.name:16} {c.detail}")
        counts = {s: sum(c.status == s for c in checks) for s in ("PASS", "WARN", "FAIL", "INFO")}
        print("\n" + "  ".join(f"{k}={v}" for k, v in counts.items()))
    return 1 if any(c.status == "FAIL" for c in checks) else 0


if __name__ == "__main__":
    raise SystemExit(main())
