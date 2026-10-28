#!/usr/bin/env bash
# Lab 03-C verification (read-only)।  Usage: bash check.sh ~/lab03c     exit 0 = PASS
set -uo pipefail

DEST=${1:?usage: bash check.sh DIR}
[[ -f "$DEST/.lab03c" ]] || { echo "not a Lab 03-C directory: $DEST" >&2; exit 2; }
export GIT_CONFIG_GLOBAL="$DEST/.gitconfig-lab" GIT_CONFIG_NOSYSTEM=1
O="$DEST/origin.git"
fail=0
pass() { echo "PASS  $1"; }
bad()  { echo "FAIL  $1"; fail=1; }
# log আগে variable-এ, তারপর grep: `cmd | grep -q` + pipefail-এ grep আগে বেরিয়ে গেলে cmd SIGPIPE (141) পায়
# এবং match পেয়েও শর্ত "ব্যর্থ" হয় — এই check লেখার সময় আসলে ঘটেছিল
subjects() { git -C "$1" log "$2" --format=%s 2>/dev/null; }
has() { grep -qx -- "$2" <<<"$1"; }          # has <text> <exact line>
sha_of() { git -C "$1" log "$2" --format=%H --grep="^$3\$" 2>/dev/null | sed -n 1p; }
ORIGIN_LOG=$(subjects "$O" main)

# ১. সহকর্মীর commit origin/main-এ ফিরেছে, এবং আপনার rename-ও আছে
if has "$ORIGIN_LOG" "feat: audit log" && has "$ORIGIN_LOG" "chore: rename config"; then
  pass "origin/main has both the teammate's 'feat: audit log' and your 'chore: rename config'"
else
  bad "origin/main is missing 'feat: audit log' or 'chore: rename config'"
fi

# ২. খারাপ commit revert হয়েছে — history পুনর্লিখন ছাড়া
debug=$(sha_of "$O" main "feat: enable debug in prod config")
if [[ -n "$debug" ]] && has "$ORIGIN_LOG" 'Revert "feat: enable debug in prod config"'; then
  pass "the bad commit is still in history and has been reverted (no rewrite)"
else
  bad "expected the original 'enable debug' commit AND a Revert commit on origin/main"
fi
grep -q "DEBUG=true" <<<"$(git -C "$O" show main:config.txt 2>/dev/null)" && bad "origin/main config.txt still has DEBUG=true" \
  || pass "origin/main config.txt no longer enables debug"

# ৩. হারানো payment commit দুটি origin/main-এ
if has "$ORIGIN_LOG" "feat: payment retries (1/2)" && has "$ORIGIN_LOG" "feat: payment retries (2/2)"; then
  pass "both payment-retries commits recovered and pushed"
else
  bad "payment-retries commits are not on origin/main"
fi

# ৪. মুছে ফেলা branch ফিরে এসেছে
if has "$(subjects "$DEST/you" hotfix/login)" "fix: login timeout"; then
  pass "branch hotfix/login restored with 'fix: login timeout'"
else
  bad "branch hotfix/login (with 'fix: login timeout') not found in you/"
fi

# ৫. bisect-এর উত্তর
want=$(sha_of "$DEST/calc" main "change 11")
got=$([[ -f "$DEST/bisect-answer.txt" ]] && awk 'NR == 1 {print $1}' "$DEST/bisect-answer.txt")   # প্রথম লাইনের প্রথম শব্দ
if [[ -n "$got" && "$want" == "$got"* && ${#got} -ge 7 ]]; then
  pass "bisect answer is the first bad commit"
else
  bad "bisect-answer.txt missing or not the first bad commit"
fi
git -C "$DEST/calc" bisect log >/dev/null 2>&1 && bad "calc/ is still in a bisect session (git bisect reset)" \
  || pass "no bisect session left open"

(( fail == 0 )) && echo "ALL CHECKS PASSED" || echo "some checks failed"
exit "$fail"
