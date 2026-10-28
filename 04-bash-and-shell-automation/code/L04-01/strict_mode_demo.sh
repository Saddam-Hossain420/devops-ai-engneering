#!/usr/bin/env bash
# strict_mode_demo.sh — `set -euo pipefail` আসলে কী করে এবং কোথায় চুপচাপ কাজ করে না।
# প্রতিটি case আলাদা child bash-এ চলে; শেষে "REACHED" ছাপা হলে script থামেনি।
# Usage: bash strict_mode_demo.sh            (কিছু বদলায় না; শুধু child shell চালায়)

# এই file নিজে strict mode ব্যবহার করে না — child-দের ফল ধরতে হবে
# shellcheck disable=SC2016  # single-quote-এর ভেতরের $... child bash-এর code — এখানে expand হওয়ার কথা নয়
BASH_BIN=${BASH:-bash}

run_case() {  # run_case <id> <শিরোনাম> <code>
  local id=$1 title=$2 code=$3 out rc
  out=$("$BASH_BIN" -c "$code"$'\necho REACHED' 2>&1)
  rc=$?
  if [[ $out == *REACHED* ]]; then
    printf '%-3s %-58s continued (exit %d)\n' "$id" "$title" "$rc"
  else
    printf '%-3s %-58s STOPPED   (exit %d)\n' "$id" "$title" "$rc"
  fi
}

echo "case title                                                       result"
run_case 1  "no strict mode: failing command"                 'false'
run_case 2  "set -e: failing command"                          'set -e; false'
run_case 3  "set -e: failure inside if-condition"              'set -e; if false; then :; fi'
run_case 4  "set -e: failure on left of && (not last)"         'set -e; false && true'
run_case 5  "set -e: failure on left of || "                   'set -e; false || true'
run_case 6  "set -e: function called as if-condition"          'set -e; f() { false; echo "  (inside f after false)" >&2; }; if f; then :; fi'
run_case 7  "set -e: local x=\$(false) - local masks status"   'set -e; f() { local x=$(false); }; f'
run_case 8  "set -e: x=\$(false) - plain assignment"           'set -e; x=$(false)'
run_case 9  "set -e: false | true (no pipefail)"               'set -e; false | true'
run_case 10 "set -eo pipefail: false | true"                   'set -eo pipefail; false | true'
run_case 11 "set -e: ((count++)) when count=0"                 'set -e; count=0; ((count++))'
run_case 12 "set -e: count=\$((count + 1)) when count=0"       'set -e; count=0; count=$((count + 1))'
run_case 13 "set -u: unset variable"                           'set -u; echo "$UNDEFINED_VAR"'
run_case 14 "set -u: \${VAR:-default}"                         'set -u; echo "${UNDEFINED_VAR:-default}"'
run_case 15 "set -e: \$(false; echo x) - subshell, no inherit"  'set -e; x=$(false; echo after)'
run_case 16 "set -e + inherit_errexit: same"                   'set -e; shopt -s inherit_errexit; x=$(false; echo after)'
run_case 17 "set -eo pipefail: grep -c with zero matches"      'set -eo pipefail; n=$(printf "a\n" | grep -c zzz)'
run_case 18 "set -eo pipefail: yes | head -1 (SIGPIPE)"        'set -eo pipefail; yes | head -1 >/dev/null'
