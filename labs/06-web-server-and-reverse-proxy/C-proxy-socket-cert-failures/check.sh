#!/usr/bin/env bash
# Lab 06-C verification — exit 0 = ALL CHECKS PASSED.   Usage: sudo bash check.sh
set -uo pipefail

[[ -f /etc/lab06c/.lab06c ]] || { echo "Lab 06-C is not set up (run break-it.sh)" >&2; exit 2; }
CA=/etc/lab06c/pki/root.crt
URL=https://taskflow.example.com:8443
CURL=(curl -s --max-time 5 --cacert "$CA" --resolve taskflow.example.com:8443:127.0.0.1)
fail=0
pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }

nginx -t >/dev/null 2>&1 && pass "nginx -t" || bad "nginx -t fails: $(nginx -t 2>&1 | tail -1)"

systemctl is-active --quiet lab06c-app.service && pass "lab06c-app.service active" \
  || bad "lab06c-app.service is not active (journalctl -u lab06c-app)"

sock=/run/lab06c/app.sock
if [[ -S $sock ]]; then
  mode=$(stat -c '%a %G' "$sock")
  [[ $mode == "660 www-data" ]] && pass "socket $sock is 660 group www-data" \
    || bad "socket $sock is '$mode' (nginx's www-data needs group rw)"
else
  bad "socket $sock does not exist (what does the app actually create? ls /run/lab06c)"
fi

days_left=$(echo | openssl s_client -connect 127.0.0.1:8443 -servername taskflow.example.com 2>/dev/null \
  | openssl x509 -noout -checkend $((7*86400)) >/dev/null 2>&1 && echo ok || echo expiring)
[[ $days_left == ok ]] && pass "served certificate valid for more than 7 days" \
  || bad "served certificate is expired or expires within 7 days"

code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' "$URL/health")
[[ $code == 200 ]] && pass "GET $URL/health → 200 (TLS verified)" || bad "GET /health → '$code' (curl -v to see why)"

code=$("${CURL[@]}" -o /dev/null -w '%{http_code}' -X POST -H 'Content-Type: application/json' \
  -d '{"title": "lab 06-C"}' "$URL/tasks")
[[ $code == 201 ]] && pass "POST /tasks → 201" || bad "POST /tasks → '$code'"

if [[ $fail -eq 0 ]]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
exit $fail
