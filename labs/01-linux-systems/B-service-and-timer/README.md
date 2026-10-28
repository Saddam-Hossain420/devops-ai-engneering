# Lab 01-B — Hardened service and timer

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ৯০ মিনিট |
| **Environment** | Ubuntu VM (systemd), snapshot নিয়ে |
| **Label** | ⚠️ system user, unit file ও `/opt` পরিবর্তন — cleanup ধাপ আছে |

## Objective

Project 1-এর প্রথম production-style অংশ তৈরি: Module 01-এর Python tool দিয়ে একটি **hardened oneshot service + timer** যা প্রতি ৫ মিনিটে memory, load ও disk অবস্থা journal-এ লেখে; তারপর lint, security score, permission audit ও log সারাংশ দিয়ে যাচাই।

## Prerequisites

- Lesson: [L01-04](../../../01-linux-systems/L01-04-users-permissions.md), [L01-10](../../../01-linux-systems/L01-10-systemd-services.md), [L01-11](../../../01-linux-systems/L01-11-scheduling-jobs.md), [L01-12](../../../01-linux-systems/L01-12-storage-lvm.md), [L01-14](../../../01-linux-systems/L01-14-logs-and-debugging.md)

## Environment setup

```bash
CODE=~/devops-ai-engineering/01-linux-systems/code
sudo useradd --system --no-create-home --shell /usr/sbin/nologin opscheck 2>/dev/null || true
sudo install -d -m 0755 /opt/ops-toolkit
sudo install -m 0644 $CODE/L01-09/mem_report.py $CODE/L01-12/storage_report.py /opt/ops-toolkit/
```

## Steps

1. **Unit লিখুন:** `/etc/systemd/system/ops-check.service` — `Type=oneshot`, `User=opscheck`, তিনটি `ExecStart=` (meminfo, load, এবং `df -h /` — শেষটি absolute path `/usr/bin/df`), hardening (`NoNewPrivileges`, `PrivateTmp`, `ProtectSystem=strict`, `ProtectHome`), `MemoryMax=64M`। [L01-11-এর নমুনা](../../../01-linux-systems/code/L01-11/ops-memcheck.service) থেকে শুরু করতে পারেন।
2. **Timer:** `/etc/systemd/system/ops-check.timer` — `OnCalendar=*:0/5`, `Persistent=true`, `RandomizedDelaySec=30`।
3. **Lint ও verify:**

   ```bash
   python3 $CODE/L01-10/unit_lint.py /etc/systemd/system/ops-check.service
   sudo systemd-analyze verify /etc/systemd/system/ops-check.service
   ```

4. **চালু ও পরীক্ষা:**

   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start ops-check.service
   journalctl -u ops-check -n 20 --no-pager
   sudo systemctl enable --now ops-check.timer
   systemctl list-timers ops-check.timer
   ```

5. **Security score:** `systemd-analyze security ops-check.service | tail -1` — notebook-এ লিখুন; একটি hardening option যোগ করে আবার মাপুন।
6. **Permission audit:** `python3 $CODE/L01-04/perm_tool.py audit /opt/ops-toolkit` ও `ls -l /etc/systemd/system/ops-check.*`।
7. **Log সারাংশ (১৫ মিনিট পরে):**

   ```bash
   journalctl -u ops-check -o json --since "20 min ago" > /tmp/j.jsonl
   python3 $CODE/L01-14/journal_summary.py /tmp/j.jsonl --max-priority 6
   ```

## Expected behavior

- `unit_lint.py`-এ কোনো WARN নেই; `verify`-এ error নেই।
- Timer প্রতি ৫ মিনিটে চলে; journal-এ memory/load/disk লাইন।
- Audit-এ world-writable বা setuid file নেই।

## Verification

```bash
systemctl is-enabled ops-check.timer                      # enabled
systemctl show -p Result ops-check.service                 # Result=success
journalctl -u ops-check --since "15 min ago" | grep -c "total"   # ≥ 2 run
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `status=217/USER` | user নেই | setup ধাপ |
| `Read-only file system` | `ProtectSystem=strict`-এ লেখার চেষ্টা | script শুধু stdout-এ লিখুক |
| Timer চলে না | timer enable হয়নি | `enable --now ops-check.timer` |
| Fedora-তে group error | `nogroup` নেই | `Group=` বাদ দিন বা `nobody` |

## Cleanup / reset

```bash
sudo systemctl disable --now ops-check.timer
sudo rm -f /etc/systemd/system/ops-check.{service,timer}
sudo systemctl daemon-reload
sudo rm -r /opt/ops-toolkit
sudo userdel opscheck
```

## Assessment

1. আপনার security score কত ছিল এবং কোন option সবচেয়ে বেশি উন্নতি দিল?
2. `Persistent=true` কোন পরিস্থিতিতে কাজে লাগে — VM বন্ধ রেখে পরীক্ষা করে দেখান।
3. Service কোনো ধাপে ব্যর্থ হলে আপনি কীভাবে জানতেন (L01-11-এর তিনটি প্রশ্ন)?
4. এই setup-কে cron দিয়ে করলে কোন তিনটি সুবিধা হারাতেন?
