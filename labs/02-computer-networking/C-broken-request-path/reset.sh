#!/usr/bin/env bash
# Lab 02-C cleanup: break-it.sh যা তৈরি করেছে সব মোছে (idempotent — বারবার চালানো নিরাপদ)।
# Usage: sudo bash reset.sh --yes-i-am-in-a-vm
set -uo pipefail

[[ "${1:-}" == "--yes-i-am-in-a-vm" ]] || { echo "refusing: run with --yes-i-am-in-a-vm (VM only)" >&2; exit 2; }
[[ $EUID -eq 0 ]] || { echo "run with sudo" >&2; exit 2; }

systemctl disable --now lab02c-app.service 2>/dev/null
rm -f /etc/systemd/system/lab02c-app.service
systemctl daemon-reload
rm -rf /etc/lab02c /srv/lab02c
# lab-এর tag-যুক্ত লাইন এবং shop.lab-এর যেকোনো লাইন (learner tag মুছে ফেললেও)
sed -i -e '/# lab02c$/d' -e '/[[:space:]]shop\.lab\([[:space:]]\|$\)/d' /etc/hosts
nft delete table inet lab02c 2>/dev/null
echo "lab 02-C removed"
