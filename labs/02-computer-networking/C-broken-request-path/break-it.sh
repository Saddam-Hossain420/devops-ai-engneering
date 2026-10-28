#!/usr/bin/env bash
# Lab 02-C: `curl http://shop.lab:8080/health`-এর পথে তিনটি ভিন্ন স্তরে তিনটি ইচ্ছাকৃত ব্যর্থতা তৈরি করে।
# ⚠️ শুধু snapshot-যুক্ত VM-এ। /etc/hosts-এ একটি লাইন, একটি nftables table, একটি systemd unit,
#    /etc/lab02c ও /srv/lab02c তৈরি করে। সব কিছু "lab02c" দিয়ে চিহ্নিত; reset.sh সব মোছে।
# Usage: sudo bash break-it.sh --yes-i-am-in-a-vm
set -euo pipefail

[[ "${1:-}" == "--yes-i-am-in-a-vm" ]] || { echo "refusing: run with --yes-i-am-in-a-vm (VM only)" >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 2; }
command -v nft >/dev/null || { echo "nft not found: sudo apt install nftables" >&2; exit 2; }
command -v python3 >/dev/null || { echo "python3 not found" >&2; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"

install -d -m 0755 /srv/lab02c /etc/lab02c
install -m 0644 "$HERE/app.py" /srv/lab02c/app.py

# ব্যর্থতা ৩ (সবচেয়ে ভেতরে): app ভুল loopback address-এ শোনে
printf 'LAB_BIND=127.0.0.2\nLAB_PORT=8080\n' > /etc/lab02c/app.env

cat > /etc/systemd/system/lab02c-app.service <<'EOF'
[Unit]
Description=Lab 02-C health app

[Service]
DynamicUser=yes
EnvironmentFile=/etc/lab02c/app.env
ExecStart=/usr/bin/python3 /srv/lab02c/app.py
Restart=on-failure
NoNewPrivileges=yes
ProtectSystem=strict
ProtectHome=yes
EOF
systemctl daemon-reload
systemctl restart lab02c-app.service

# ব্যর্থতা ১ (সবচেয়ে বাইরে): নাম ভুল IP-তে resolve হয় (TEST-NET-1, কোথাও পৌঁছায় না)
sed -i '/# lab02c$/d' /etc/hosts
echo "192.0.2.123 shop.lab  # lab02c" >> /etc/hosts

# ব্যর্থতা ২ (মাঝে): port 8080-এ আসা সব packet নিঃশব্দে drop
nft delete table inet lab02c 2>/dev/null || true
nft add table inet lab02c
nft add chain inet lab02c input '{ type filter hook input priority -10; policy accept; }'
nft add rule inet lab02c input tcp dport 8080 drop

echo "lab 02-C is broken. Goal: curl -s http://shop.lab:8080/health returns {\"status\": \"ok\"} in < 1 s."
