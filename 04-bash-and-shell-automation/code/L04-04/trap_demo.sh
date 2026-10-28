#!/usr/bin/env bash
# trap_demo.sh — ERR trap কোথায় ও কী জানায়, এবং `set -E` ছাড়া কী হয়।
# Usage: bash trap_demo.sh with-E | without-E
set -euo pipefail

on_err() {  # on_err <exit code> <line>
  local rc=$1 line=$2 i
  echo "ERR trap: exit $rc at ${BASH_SOURCE[1]##*/}:$line running: $BASH_COMMAND" >&2
  for ((i = 1; i < ${#FUNCNAME[@]}; i++)); do        # call stack (0 = on_err নিজে)
    echo "  at ${FUNCNAME[$i]}() ${BASH_SOURCE[$i]##*/}:${BASH_LINENO[$((i - 1))]}" >&2
  done
}

load_config() {
  local file=$1
  grep -q '^port=' "$file"          # file নেই → grep exit 2
  echo "config ok"
}

deploy() {
  load_config /nonexistent/app.conf
}

case ${1:-} in
  with-E)    set -E ;;              # ERR trap function-এর ভেতরেও উত্তরাধিকার পায়
  without-E) ;;
  *) echo "usage: $0 with-E|without-E" >&2; exit 2 ;;
esac
trap 'on_err $? $LINENO' ERR

echo "deploy starting"
deploy
echo "never reached"
