#!/usr/bin/env bash
#
# backup_safe.sh — নিরাপদ ও idempotent backup: lock, atomic publish, যাচাই, অপরিবর্তিত হলে skip, rotation।
#
# Usage: backup_safe.sh -s SOURCE -d DEST [-k KEEP] [-n] [-f] [-q]
#   -s DIR    source directory
#   -d DIR    backup directory (dest)
#   -k N      সবচেয়ে নতুন N টি backup রাখা (default 7; 0 = rotation বন্ধ)
#   -n        dry-run: কী করত দেখায়, কিছু বদলায় না
#   -f        force: source অপরিবর্তিত হলেও নতুন backup
#   -q        quiet
#   -H SECS   lock ধরে এত সেকেন্ড অপেক্ষা (শুধু test/demo-র জন্য)
#
# Exit codes: 0 OK (নতুন backup বা অপরিবর্তিত বলে skip), 1 error, 2 usage, 75 অন্য run চলছে (আবার চেষ্টা করুন)
#
set -Eeuo pipefail
readonly SCRIPT_NAME=${0##*/}
readonly EX_TEMPFAIL=75     # sysexits.h — "সাময়িক ব্যর্থতা, পরে আবার চেষ্টা করুন"

QUIET=0
log() { (( QUIET )) && [[ $1 == INFO ]] && return 0; local IFS=' '; printf '%s %-5s %s[%d]: %s\n' "$(date -u +%H:%M:%SZ)" "$1" "$SCRIPT_NAME" "$$" "${*:2}" >&2; }
die() { log ERROR "$1"; exit "${2:-1}"; }
run() {  # dry-run-সচেতন
  if (( DRY_RUN )); then local c; printf -v c '%q ' "$@"; log INFO "dry-run: ${c% }"; else "$@"; fi
}

SOURCE="" DEST="" KEEP=7 DRY_RUN=0 FORCE=0 HOLD=0
while getopts ':s:d:k:nfqH:h' opt; do
  case $opt in
    s) SOURCE=$OPTARG ;; d) DEST=$OPTARG ;; k) KEEP=$OPTARG ;;
    n) DRY_RUN=1 ;; f) FORCE=1 ;; q) QUIET=1 ;; H) HOLD=$OPTARG ;;
    h) sed -n '3,16s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; exit 0 ;;
    :) die "-$OPTARG needs a value" 2 ;;
    *) die "unknown option -$OPTARG" 2 ;;
  esac
done
shift $((OPTIND - 1))
(( $# == 0 )) || die "unexpected argument: $1" 2
[[ -n $SOURCE && -n $DEST ]] || die "-s SOURCE and -d DEST are required" 2
[[ -d $SOURCE ]] || die "source is not a directory: $SOURCE" 2
[[ $KEEP =~ ^[0-9]+$ ]] || die "-k must be a non-negative integer" 2
SOURCE=$(realpath -- "$SOURCE")
DEST=$(realpath -m -- "$DEST")
[[ $DEST != "$SOURCE" && $DEST != "$SOURCE"/* ]] || die "dest must not be inside source" 2
NAME=$(basename -- "$SOURCE")

# ---- cleanup: lock ও আধা-লেখা file — যেভাবেই শেষ হোক (L04-04) -----------------
LOCK_DIR="" PARTIAL=""
cleanup() {
  local rc=$?
  trap - EXIT
  [[ -n $PARTIAL && -e $PARTIAL ]] && rm -f -- "$PARTIAL" && log INFO "removed partial $PARTIAL"
  [[ -n $LOCK_DIR && -d $LOCK_DIR ]] && rm -rf -- "$LOCK_DIR"
  exit "$rc"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# ---- locking -------------------------------------------------------------------
acquire_lock() {
  run mkdir -p -- "$DEST"
  (( DRY_RUN )) && return 0
  if command -v flock >/dev/null 2>&1; then
    # flock: kernel-এর lock — process মারা গেলে (SIGKILL-ও) fd বন্ধ হয়, lock নিজে মুক্ত হয়
    exec 9>"$DEST/.lock"
    flock -n 9 || die "another backup of $DEST is running" "$EX_TEMPFAIL"
    log INFO "lock acquired (flock)"
    return 0
  fi
  # Fallback (flock নেই — যেমন Git Bash): mkdir atomic — একই সময়ে শুধু একজন সফল হয়
  local dir="$DEST/.lock.d" pid
  if ! mkdir -- "$dir" 2>/dev/null; then
    pid=$(cat -- "$dir/pid" 2>/dev/null || true)
    if [[ $pid =~ ^[0-9]+$ ]] && kill -0 "$pid" 2>/dev/null; then
      die "another backup of $DEST is running (pid $pid)" "$EX_TEMPFAIL"
    fi
    log WARN "removing stale lock (pid ${pid:-unknown} is not running)"
    rm -rf -- "$dir"
    mkdir -- "$dir" || die "lost the race for the lock" "$EX_TEMPFAIL"
  fi
  LOCK_DIR=$dir
  echo "$$" > "$dir/pid"
  log INFO "lock acquired (mkdir fallback)"
}

# ---- idempotency: source-এর fingerprint (path, size, mtime) -------------------------
fingerprint() {
  (cd -- "$SOURCE" && find . -type f -printf '%P\t%s\t%T@\n' | LC_ALL=C sort | sha256sum | cut -d' ' -f1)
}

rotate() {  # rotate [pending] — pending: এখনো তৈরি হয়নি কিন্তু হবে এমন backup-এর সংখ্যা (dry-run)
  local pending=${1:-0}
  (( KEEP > 0 )) || return 0
  local -a all
  # নাম-এ UTC timestamp, তাই নামের ক্রম = সময়ের ক্রম; শুধু নিজের pattern (অন্য file কখনো নয়)
  mapfile -t all < <(find "$DEST" -maxdepth 1 -type f -name "$NAME-*.tar.gz" -printf '%f\n' | LC_ALL=C sort)
  # dry-run-এ নতুন backup-টিও গণনায় — নইলে পরিকল্পনা আসল run-এর চেয়ে কম মোছা দেখাত (আসলে ঘটেছিল)
  local extra=$(( ${#all[@]} + pending - KEEP )) f
  (( extra > ${#all[@]} )) && extra=${#all[@]}
  (( extra > 0 )) || return 0
  for f in "${all[@]:0:extra}"; do
    run rm -f -- "$DEST/$f"
    (( DRY_RUN )) || log INFO "rotated out $f"
  done
}

main() {
  acquire_lock
  (( HOLD > 0 )) && sleep "$HOLD"

  local fp last=""
  fp=$(fingerprint)
  [[ -f $DEST/.last-fingerprint ]] && last=$(<"$DEST/.last-fingerprint")
  if [[ $fp == "$last" ]] && (( ! FORCE )); then
    log INFO "source unchanged since last backup — nothing to do"
    return 0
  fi

  local archive="$DEST/$NAME-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"
  if (( DRY_RUN )); then
    log INFO "dry-run: would create $archive"
    rotate 1
    return 0
  fi
  [[ -e $archive ]] && die "already exists: $archive (two runs in the same second?)"
  # একই directory-তে temp → mv atomic (একই filesystem); লুকানো নাম, অন্য tool যেন অর্ধেক file না দেখে
  PARTIAL=$(mktemp "$DEST/.partial.XXXXXX")
  tar --force-local -czf "$PARTIAL" -C "$(dirname -- "$SOURCE")" "$NAME"
  tar --force-local -tzf "$PARTIAL" >/dev/null || die "archive verification failed"
  chmod 0640 -- "$PARTIAL"
  mv -- "$PARTIAL" "$archive"
  PARTIAL=""
  echo "$fp" > "$DEST/.last-fingerprint.tmp" && mv -- "$DEST/.last-fingerprint.tmp" "$DEST/.last-fingerprint"
  log INFO "created $archive"
  printf '%s\n' "$archive"
  rotate                                          # শুধু নতুন backup সফল হওয়ার পরে
}

main
