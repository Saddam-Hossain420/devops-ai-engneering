#!/usr/bin/env bash
# Lab 01-C: একটি disposable service-এ তিনটি ইচ্ছাকৃত ব্যর্থতা তৈরি করে।
# ⚠️ শুধু snapshot-যুক্ত VM-এ। system user, unit, /etc/lab-c, /srv/lab-c ও একটি 1M tmpfs তৈরি করে।
# Usage: sudo bash break-it.sh --yes-i-am-in-a-vm
set -euo pipefail

[[ "${1:-}" == "--yes-i-am-in-a-vm" ]] || { echo "refusing: run with --yes-i-am-in-a-vm (VM only)" >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"

id labc >/dev/null 2>&1 || useradd --system --no-create-home --shell /usr/sbin/nologin labc
install -d -m 0755 /srv/lab-c /etc/lab-c
install -m 0644 "$HERE/app.py" /srv/lab-c/app.py

# ব্যর্থতা ১: ExecStart একটি wrapper script — execute bit নেই
printf '#!/bin/sh\nexec /usr/bin/python3 /srv/lab-c/app.py\n' > /srv/lab-c/run.sh
chmod 0644 /srv/lab-c/run.sh

# ব্যর্থতা ২: config শুধু root পড়তে পারে
printf '[app]\nheartbeat_file = /srv/lab-c/data/heartbeat.log\n' > /etc/lab-c/config.ini
chown root:root /etc/lab-c/config.ini
chmod 0600 /etc/lab-c/config.ini

# ব্যর্থতা ৩: data directory একটি ছোট tmpfs, প্রায় পূর্ণ
install -d -m 0755 /srv/lab-c/data
mountpoint -q /srv/lab-c/data || mount -t tmpfs -o size=1M,mode=0755 tmpfs /srv/lab-c/data
dd if=/dev/zero of=/srv/lab-c/data/filler.bin bs=1K count=1000 status=none 2>/dev/null || true
chown -R labc:labc /srv/lab-c/data

cat > /etc/systemd/system/lab-c.service <<'EOF'
[Unit]
Description=Lab 01-C heartbeat app

[Service]
User=labc
Group=labc
ExecStart=/srv/lab-c/run.sh
Restart=on-failure
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
systemctl daemon-reload
systemctl start lab-c.service || true
echo "lab-c is broken in 3 ways. Start with: systemctl status lab-c; journalctl -u lab-c"
