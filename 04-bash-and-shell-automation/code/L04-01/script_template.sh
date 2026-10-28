#!/usr/bin/env bash
#
# script_template.sh — নতুন Bash script-এর শুরুর কাঠামো। Copy করে নাম ও কাজ বদলান।
#
# Usage: script_template.sh [-h] [-n] NAME
#   -h   help
#   -n   dry-run: কী করত দেখায়, কিছু বদলায় না
#
# Exit codes: 0 OK, 1 runtime error, 2 usage error
#
set -Eeuo pipefail          # E: ERR trap function-এর ভেতরেও; e: ব্যর্থতায় থামা; u: অজানা variable; pipefail
shopt -s inherit_errexit    # $(...)-এর ভেতরেও set -e (bash ৪.৪+)
IFS=$'\n\t'                 # word splitting শুধু newline/tab-এ (space-যুক্ত নাম নিরাপদ) — তবু সবসময় quote করুন

readonly SCRIPT_NAME=${0##*/}
SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)   # আলাদা লাইনে: readonly x=$(...) ব্যর্থতা লুকায় (SC2155)
readonly SCRIPT_DIR

DRY_RUN=0

usage() {
  sed -n '3,9s/^# \{0,1\}//p' "${BASH_SOURCE[0]}"
}

log() {  # সব diagnostic stderr-এ; stdout শুধু আসল ফলের জন্য (pipe-যোগ্য থাকে)
  local IFS=' '              # "$*" IFS-এর প্রথম অক্ষর দিয়ে জোড়ে — উপরের IFS-এ সেটা newline!
  printf '%s %s: %s\n' "$(date +%H:%M:%S)" "$SCRIPT_NAME" "$*" >&2
}

die() {
  log "ERROR: $*"
  exit 1
}

run() {  # dry-run-সচেতন command চালানো
  if (( DRY_RUN )); then
    local cmd
    printf -v cmd '%q ' "$@"   # quote সহ — copy করে হুবহু চালানো যায়
    log "dry-run: ${cmd% }"
  else
    "$@"
  fi
}

parse_args() {
  local opt
  while getopts ':hn' opt; do
    case $opt in
      h) usage; exit 0 ;;
      n) DRY_RUN=1 ;;
      \?) log "unknown option: -$OPTARG"; usage >&2; exit 2 ;;
    esac
  done
  shift $((OPTIND - 1))
  (( $# == 1 )) || { usage >&2; exit 2; }
  NAME=$1
}

main() {
  parse_args "$@"
  [[ $NAME =~ ^[A-Za-z0-9_-]+$ ]] || die "NAME must be letters, digits, _ or - (got: $NAME)"
  log "starting in $SCRIPT_DIR (dry-run=$DRY_RUN)"
  run mkdir -p -- "/tmp/${NAME}-demo"
  printf 'hello, %s\n' "$NAME"      # আসল output stdout-এ
}

main "$@"
