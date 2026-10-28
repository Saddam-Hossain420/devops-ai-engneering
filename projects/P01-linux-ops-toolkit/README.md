# P01 — Linux Server Operations Toolkit

**Status:** NOT_STARTED · **Milestone:** 1 · **Track:** A, C · **পূর্বশর্ত:** Module 01, Module 04, Module 05

## লক্ষ্য

একটি Linux server-এর স্বাস্থ্য দ্রুত যাচাই ও সাধারণ operational কাজ automate করার Bash + Python toolkit।

## Architecture

```text
operator ──► ops-toolkit CLI (Python)
                 ├── health      : CPU, memory, disk, load, failed systemd unit
                 ├── logs        : journald/log file থেকে error pattern ও top offender
                 ├── disk        : বড় directory/file, inode ব্যবহার
                 ├── services    : নির্দিষ্ট service-এর status ও restart count
                 └── backup-verify : backup archive-এর checksum ও restore test (temp dir-এ)
          systemd timer ──► health --json ──► log / alert hook
```

## Features (scope)

- `health`, `logs`, `disk`, `services`, `backup-verify` subcommand
- Human-readable ও `--json` output
- Exit code: 0 = ঠিক, 1 = warning, 2 = critical (monitoring-এ ব্যবহারযোগ্য)
- Bash wrapper script (ShellCheck-clean)
- systemd service + timer unit file
- সম্পূর্ণ read-only — কোনো কিছু মুছে বা পরিবর্তন করে না

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] `pytest` সব test পাস
- [ ] `shellcheck` কোনো warning নেই
- [ ] পূর্ণ disk simulate (loop/tmpfs-এ) করলে `disk` critical দেয়
- [ ] Backup archive-এ একটি byte বদলালে `backup-verify` ব্যর্থ হয়
- [ ] Timer প্রতি ৫ মিনিটে চলে এবং `journalctl -u` এ ফল দেখা যায়

## Resource requirements

যেকোনো Ubuntu machine/VM, Python 3.11+। ২ GB RAM যথেষ্ট।

## Cleanup

`systemctl disable --now ops-toolkit.timer` এবং unit file মুছে `systemctl daemon-reload`।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
