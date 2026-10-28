#!/usr/bin/env bash
# Lab 01-C verification (read-only): service চালু এবং heartbeat গত ১০ সেকেন্ডে লেখা হয়েছে কিনা।
# Usage: sudo bash check.sh   (labc user হিসেবে config পড়া যাচাইয়ে sudo লাগে)   exit 0 = PASS
set -uo pipefail

fail=0
pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }

systemctl is-active --quiet lab-c.service && pass "lab-c.service is active" || bad "lab-c.service is not active"
[[ -x /srv/lab-c/run.sh ]] && pass "run.sh is executable" || bad "run.sh is not executable"
sudo -u labc test -r /etc/lab-c/config.ini 2>/dev/null && pass "labc can read config" || bad "labc cannot read config"

hb=/srv/lab-c/data/heartbeat.log
if [[ -f "$hb" ]]; then
  age=$(( $(date +%s) - $(stat -c %Y "$hb") ))
  (( age <= 10 )) && pass "heartbeat updated ${age}s ago" || bad "heartbeat is ${age}s old"
else
  bad "no heartbeat file"
fi

used=$(df --output=pcent /srv/lab-c/data 2>/dev/null | tail -1 | tr -dc '0-9')
[[ -n "$used" && "$used" -lt 90 ]] && pass "data filesystem ${used}% used" || bad "data filesystem ${used:-?}% used"

(( fail == 0 )) && echo "ALL CHECKS PASSED" || echo "some checks failed"
exit "$fail"
