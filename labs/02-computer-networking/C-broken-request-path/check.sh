#!/usr/bin/env bash
# Lab 02-C verification (read-only)। প্রতিটি স্তর আলাদা যাচাই, শেষে end-to-end।
# Usage: sudo bash check.sh   (nft পড়তে sudo লাগে)   exit 0 = PASS
set -uo pipefail

fail=0
pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }

ip=$(getent hosts shop.lab | awk '{print $1; exit}')
[[ "$ip" == "127.0.0.1" ]] && pass "DNS: shop.lab → 127.0.0.1 (getent, as the app sees it)" \
                          || bad "DNS: shop.lab → ${ip:-<nothing>}"

if nft list table inet lab02c 2>/dev/null | grep -q 'dport 8080 drop'; then
  bad "firewall: a rule still drops tcp/8080"
else
  pass "firewall: nothing drops tcp/8080"
fi

listen=$(ss -Hltn 'sport = :8080' | awk '{print $4}')
case "$listen" in
  127.0.0.1:8080) pass "socket: app listens on 127.0.0.1:8080 only" ;;
  0.0.0.0:8080|\*:8080|\[::\]:8080) bad "socket: app listens on all interfaces ($listen) — more exposure than needed" ;;
  "") bad "socket: nothing listens on port 8080" ;;
  *) bad "socket: app listens on $listen" ;;
esac

systemctl is-active --quiet lab02c-app.service && pass "service: lab02c-app is active" || bad "service: lab02c-app is not active"

out=$(curl -s -o /tmp/lab02c-body -w '%{http_code} %{time_total}' --max-time 3 http://shop.lab:8080/health)
code=${out%% *}
secs=${out##* }
if [[ "$code" == "200" ]] && grep -q '"ok"' /tmp/lab02c-body && awk -v t="$secs" 'BEGIN{exit !(t < 1)}'; then
  pass "end-to-end: HTTP 200 in ${secs}s"
else
  bad "end-to-end: HTTP ${code:-000} in ${secs:-?}s"
fi
rm -f /tmp/lab02c-body

(( fail == 0 )) && echo "ALL CHECKS PASSED" || echo "some checks failed"
exit "$fail"
