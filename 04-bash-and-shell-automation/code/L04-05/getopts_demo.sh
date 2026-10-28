#!/usr/bin/env bash
# getopts_demo.sh — getopts কীভাবে argument পড়ে: যুক্ত flag, OPTARG, `--`, ও দুই রকম error।
# Usage: bash getopts_demo.sh [-v]... [-n] [-o FILE] [--] [ARG]...
set -Eeuo pipefail

verbose=0 dry_run=0 output=""
# optstring-এর শুরুর ':' = "silent mode": error নিজে সামলাব
#   অজানা option  → opt='?' ,  OPTARG = সেই অক্ষর
#   value অনুপস্থিত → opt=':' ,  OPTARG = যে option-এর value নেই
while getopts ':vno:' opt; do
  case $opt in
    v) verbose=$((verbose + 1)) ;;          # -v -v বা -vv → ২
    n) dry_run=1 ;;
    o) output=$OPTARG ;;
    :) echo "error: -$OPTARG needs a value" >&2; exit 2 ;;
    \?) echo "error: unknown option -$OPTARG" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))                       # parse হওয়া option বাদ; বাকি positional argument

printf 'verbose=%d dry_run=%d output=[%s] remaining(%d):' "$verbose" "$dry_run" "$output" "$#"
printf ' [%s]' "$@"
printf '\n'
