#!/usr/bin/env bash
#
# run_checks.sh — Module 04-এর সব shell script-এ static check ও test: ShellCheck, bats, shlint_mini।
# যে tool নেই সেটা স্পষ্টভাবে SKIP বলে — কখনো চুপচাপ "pass" নয়।
#
# Usage: run_checks.sh [--strict | --skip-external]
#   --strict          কোনো tool অনুপস্থিত হলেও ব্যর্থ (CI-তে, যেখানে সব tool থাকার কথা)
#   --skip-external   ShellCheck ও bats থাকলেও না চালানো (শুধু shlint_mini ও bash -n)
#
# Exit codes: 0 সব চলেছে ও পাস, 1 কোনো check ব্যর্থ (বা --strict-এ tool নেই), 2 usage
#
set -Eeuo pipefail

STRICT=0 SKIP_EXTERNAL=0
case ${1:-} in
  "") ;;
  --strict) STRICT=1 ;;
  --skip-external) SKIP_EXTERNAL=1 ;;
  *) echo "usage: run_checks.sh [--strict | --skip-external]" >&2; exit 2 ;;
esac

HERE=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
CODE_DIR=$(cd -- "$HERE/.." && pwd)
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null && "$c" -c 'import sys' >/dev/null 2>&1; then PY=$c; break; fi
done

# tests/ ও sample-*.sh (ইচ্ছাকৃত ভুলে ভরা fixture) বাদ
mapfile -d '' scripts < <(find "$CODE_DIR" -type f -name '*.sh' -not -path '*/tests/*' -not -name 'sample-*' -print0 | sort -z)
echo "checking ${#scripts[@]} script(s) under $CODE_DIR"

rc=0 missing=0
section() { printf '\n== %s\n' "$1"; }

section "ShellCheck"
if (( SKIP_EXTERNAL )); then
  echo "SKIP shellcheck: --skip-external"
elif command -v shellcheck >/dev/null; then
  shellcheck --version | sed -n '2p'
  # -x: source করা library-ও; --rcfile: এই lesson-এর নমুনা configuration
  shellcheck -x --rcfile "$HERE/shellcheckrc" "${scripts[@]}" && echo "PASS shellcheck" || { echo "FAIL shellcheck"; rc=1; }
else
  echo "SKIP shellcheck: not installed (Ubuntu: sudo apt install shellcheck; Fedora: sudo dnf install ShellCheck)"
  missing=1
fi

section "bats"
if (( SKIP_EXTERNAL )); then
  echo "SKIP bats: --skip-external"
elif command -v bats >/dev/null; then
  bats --version
  bats "$HERE/tests" && echo "PASS bats" || { echo "FAIL bats"; rc=1; }
else
  echo "SKIP bats: not installed (Ubuntu: sudo apt install bats; Fedora: sudo dnf install bats)"
  missing=1
fi

section "shlint_mini (learning linter — not a ShellCheck replacement)"
if [[ -n $PY ]]; then
  "$PY" "$HERE/shlint_mini.py" "${scripts[@]}" && echo "PASS shlint_mini" || { echo "FAIL shlint_mini"; rc=1; }
else
  echo "SKIP shlint_mini: python not found"
  missing=1
fi

section "bash -n (syntax)"
syntax_fail=0
for s in "${scripts[@]}"; do bash -n "$s" || { echo "syntax error: $s"; syntax_fail=1; }; done
(( syntax_fail )) && rc=1 || echo "PASS bash -n"

if (( STRICT && missing )); then
  echo "FAIL --strict: some tools are missing"
  rc=1
fi
exit "$rc"
