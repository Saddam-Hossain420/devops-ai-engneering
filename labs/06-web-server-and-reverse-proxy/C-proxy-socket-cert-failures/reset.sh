#!/usr/bin/env bash
# Lab 06-C cleanup — break-it.sh-এর বানানো সব কিছু মোছে (শুধু lab06c-চিহ্নিত)।   Usage: sudo bash reset.sh
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 2; }
[[ -f /etc/lab06c/.lab06c ]] || { echo "nothing to reset (/etc/lab06c/.lab06c not found)" >&2; exit 2; }

rm -f /etc/nginx/sites-enabled/lab06c.conf /etc/nginx/sites-available/lab06c.conf
nginx -t && systemctl reload nginx
systemctl disable --now lab06c-app.service 2>/dev/null || true
rm -f /etc/systemd/system/lab06c-app.service
systemctl daemon-reload
rm -rf -- /opt/lab06c /etc/lab06c /var/lib/lab06c
echo "Lab 06-C removed"
