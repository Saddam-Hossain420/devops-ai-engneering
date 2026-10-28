#!/usr/bin/env bash
#
# safe_job.sh — একটি job যা যেভাবেই শেষ হোক (সফল, ব্যর্থ, Ctrl+C, kill) temporary data পরিষ্কার করে
# এবং ফল কখনো আধা-লেখা অবস্থায় রাখে না।
#
# Usage: safe_job.sh [-f STEP] [-s SECONDS] OUTPUT_FILE
#   -f STEP     STEP নম্বর ধাপে ইচ্ছাকৃত ব্যর্থতা (test-এর জন্য; ১-৩)
#   -s SECONDS  ধাপ ২-এ এত সেকেন্ড অপেক্ষা (signal test-এর জন্য)
#
# Exit codes: 0 OK, 1 job failed, 2 usage, 130 SIGINT, 143 SIGTERM
#
set -Eeuo pipefail
readonly SCRIPT_NAME=${0##*/}

log() { local IFS=' '; printf '%s %s[%d]: %s\n' "$(date +%H:%M:%S)" "$SCRIPT_NAME" "$$" "$*" >&2; }

WORKDIR=""
CHILD=""                              # background-এ চালানো child-এর PID
cleanup() {
  local rc=$?                         # EXIT trap-এ ঢোকার মুহূর্তের exit code — প্রথম লাইনেই ধরুন
  trap - EXIT                         # নিজেকে আবার না ডাকে
  if [[ -n $CHILD ]] && kill -0 "$CHILD" 2>/dev/null; then
    kill -TERM "$CHILD" 2>/dev/null || true   # নইলে child অনাথ হয়ে চলতেই থাকে (PPID 1) — আসলে ঘটেছিল
    wait "$CHILD" 2>/dev/null || true
    log "cleanup: stopped child $CHILD"
  fi
  if [[ -n $WORKDIR && -d $WORKDIR ]]; then
    rm -rf -- "$WORKDIR"
    log "cleanup: removed $WORKDIR"
  fi
  log "exit $rc"
  exit "$rc"                          # cleanup-এর নিজের command exit code বদলাবে না
}

on_err() {
  log "ERROR: '$BASH_COMMAND' failed (exit $1) at line $2"
}

on_signal() {  # on_signal <name> <code>
  log "received SIG$1 — stopping"
  exit "$2"                           # EXIT trap চলবে (cleanup)
}

trap cleanup EXIT
trap 'on_err $? $LINENO' ERR
trap 'on_signal INT 130' INT
trap 'on_signal TERM 143' TERM

FAIL_AT=0 SLEEP=0
while getopts ':f:s:h' opt; do
  case $opt in
    f) FAIL_AT=$OPTARG ;;
    s) SLEEP=$OPTARG ;;
    h) sed -n '3,12s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; exit 0 ;;
    *) log "usage error"; exit 2 ;;
  esac
done
shift $((OPTIND - 1))
(( $# == 1 )) || { log "need OUTPUT_FILE"; exit 2; }
OUTPUT=$1

WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/safe_job.XXXXXX")
log "workdir $WORKDIR"
echo "$WORKDIR" > "${OUTPUT}.workdir"    # test-এর জন্য: কোন directory তৈরি হয়েছিল

step() {  # step <n> <description>
  log "step $1: $2"
  (( FAIL_AT != $1 )) || false          # ইচ্ছাকৃত ব্যর্থতা → ERR trap → EXIT trap
}

step 1 "collect data"
seq 1 1000 > "$WORKDIR/data.txt"
step 2 "process"
if (( SLEEP > 0 )); then
  # `sleep` foreground-এ থাকলে signal-এর trap sleep শেষ হওয়া পর্যন্ত অপেক্ষা করে;
  # background + wait হলে wait সাথে সাথে ভেঙে trap চলে
  sleep "$SLEEP" &
  CHILD=$!
  wait "$CHILD"
  CHILD=""
fi
awk '{ s += $1 } END { print s }' "$WORKDIR/data.txt" > "$WORKDIR/result.tmp"
step 3 "publish"
mv -- "$WORKDIR/result.tmp" "$OUTPUT"    # একই filesystem হলে atomic; আধা-লেখা file কখনো দেখা যায় না
log "wrote $OUTPUT: $(cat "$OUTPUT")"
