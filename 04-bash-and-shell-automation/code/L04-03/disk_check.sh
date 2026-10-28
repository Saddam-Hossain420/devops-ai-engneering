#!/usr/bin/env bash
#
# disk_check.sh — filesystem-এর ব্যবহার threshold-এর সাথে তুলনা (monitoring plugin-ধাঁচের)।
#
# Usage: disk_check.sh [-w WARN%] [-c CRIT%] [-i DF_OUTPUT_FILE] [-x FSTYPE]...
#   -w   warning threshold (default 80)
#   -c   critical threshold (default 90)
#   -i   `df -PT`-এর output file থেকে পড়া (test-এর জন্য); না দিলে আসল `df -PT`
#   -x   এই filesystem type বাদ (একাধিকবার দেওয়া যায়; default: tmpfs devtmpfs overlay squashfs)
#
# Exit codes (Nagios/monitoring রীতি): 0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN (input/usage error)
#
set -Eeuo pipefail
readonly SCRIPT_NAME=${0##*/}
# shellcheck source=lib/common.sh
source "$(dirname -- "${BASH_SOURCE[0]}")/lib/common.sh"

usage() { sed -n '3,13s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"; }

check_line() {  # check_line <mount> <type> <pct> → "STATE mount pct%" stdout; return 0/1/2
  local mount=$1 type=$2 pct=$3
  if (( pct >= CRIT )); then
    printf 'CRITICAL %s (%s) %d%%\n' "$mount" "$type" "$pct"; return 2
  elif (( pct >= WARN )); then
    printf 'WARNING  %s (%s) %d%%\n' "$mount" "$type" "$pct"; return 1
  fi
  printf 'OK       %s (%s) %d%%\n' "$mount" "$type" "$pct"
}

main() {
  WARN=80 CRIT=90
  local input="" opt
  local -a exclude=()
  while getopts ':hw:c:i:x:' opt; do
    case $opt in
      h) usage; exit 0 ;;
      w) WARN=$OPTARG ;;
      c) CRIT=$OPTARG ;;
      i) input=$OPTARG ;;
      x) exclude+=("$OPTARG") ;;
      :) log_error "-$OPTARG needs a value"; exit 3 ;;
      *) usage >&2; exit 3 ;;
    esac
  done
  (( ${#exclude[@]} )) || exclude=(tmpfs devtmpfs overlay squashfs)
  [[ $WARN =~ ^[0-9]+$ && $CRIT =~ ^[0-9]+$ ]] && (( WARN < CRIT && CRIT <= 100 )) \
    || { log_error "need integer thresholds with WARN < CRIT <= 100 (got $WARN/$CRIT)"; exit 3; }

  local data
  if [[ -n $input ]]; then
    data=$(<"$input") || exit 3
  else
    require_cmd df || exit 3
    data=$(df -PT)
  fi

  local worst=0 rc line type pct mount skip x checked=0
  # ডান দিক থেকে parse: "<source> <type> <size> <used> <avail> <NN>% <mount>"
  # source ও mount-এ space থাকতে পারে (এই machine-এর আসল df-এ "C:/Program Files/Git") — `read a b c`-এ ভেঙে যেত
  local re='^(.*[^[:space:]])[[:space:]]+([^[:space:]]+)[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+[0-9]+[[:space:]]+([0-9]+)%[[:space:]]+(.+)$'
  while IFS= read -r line; do
    [[ $line == Filesystem* ]] && continue              # header
    if [[ ! $line =~ $re ]]; then
      log_warn "cannot parse df line: $line"
      continue
    fi
    type=${BASH_REMATCH[2]} pct=${BASH_REMATCH[3]} mount=${BASH_REMATCH[4]}
    skip=0
    for x in "${exclude[@]}"; do [[ $type == "$x" ]] && skip=1; done
    (( skip )) && { log_debug "skip $mount ($type)"; continue; }
    rc=0
    check_line "$mount" "$type" "$pct" || rc=$?         # `|| rc=$?` — set -e-এ non-zero return ধরে রাখা
    (( rc > worst )) && worst=$rc
    checked=$((checked + 1))
  done <<< "$data"

  (( checked )) || { log_error "no filesystems checked"; exit 3; }
  log_info "checked $checked filesystem(s), warn=${WARN}% crit=${CRIT}%"
  return "$worst"
}

main "$@"
