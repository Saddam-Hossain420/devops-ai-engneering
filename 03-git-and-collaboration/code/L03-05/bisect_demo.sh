#!/usr/bin/env bash
# L03-05 demo: ৩২টি commit-এর ইতিহাসে কোথায় bug ঢুকেছে — `git bisect run` স্বয়ংক্রিয়ভাবে খোঁজে।
# Bug: commit 21-এ add() ভুল হয়ে যায় (a - b)। Test script exit 0 = good, 1 = bad।
# নির্দিষ্ট author/তারিখ → hash যেকোনো machine-এ একই।
# Usage: bash bisect_demo.sh /tmp/bisect-demo
set -euo pipefail

DEST=${1:?usage: bash bisect_demo.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists" >&2; exit 2; }
PY=""
for c in python3 python; do   # Windows-এ "python3" Microsoft Store-এর stub হতে পারে — সত্যিই চলে কিনা যাচাই
  if command -v "$c" >/dev/null && "$c" -c 'import sys' >/dev/null 2>&1; then PY=$c; break; fi
done
[[ -n "$PY" ]] || { echo "python not found" >&2; exit 2; }
mkdir -p "$DEST"; cd "$DEST"
: > .empty-gitconfig
export GIT_CONFIG_GLOBAL="$PWD/.empty-gitconfig" GIT_CONFIG_NOSYSTEM=1 \
       GIT_AUTHOR_NAME="Lab User" GIT_AUTHOR_EMAIL=lab@example.com \
       GIT_COMMITTER_NAME="Lab User" GIT_COMMITTER_EMAIL=lab@example.com

git init -q -b main repo; cd repo
for n in $(seq 1 32); do
  if (( n < 21 )); then op="+"; else op="-"; fi
  printf 'def add(a, b):\n    return a %s b\n\n# change %d\n' "$op" "$n" > calc.py
  git add .
  GIT_AUTHOR_DATE="@$((1767225600 + n * 60)) +0000" GIT_COMMITTER_DATE="@$((1767225600 + n * 60)) +0000" \
    git commit -q -m "change $n"
done
# test script repository-র বাইরে — bisect চলাকালীন checkout-এ হারাবে না
cat > ../check_add.py <<'EOF'
import sys
sys.path.insert(0, ".")
from calc import add
sys.exit(0 if add(2, 3) == 5 else 1)
EOF

echo "== HEAD is broken: add(2, 3) = $("$PY" -B -c 'from calc import add; print(add(2,3))')"
GOOD=$(git rev-list --max-parents=0 HEAD)
git bisect start HEAD "$GOOD" >/dev/null
# -B: bytecode cache (.pyc) লেখা নয় — নইলে দ্রুত checkout-এ একই সেকেন্ড ও একই আকারের file-এ
# Python পুরোনো .pyc চালাতে পারে এবং bisect ভুল commit দেখায় (এই demo লেখার সময় আসলে ঘটেছিল)
git bisect run "$PY" -B ../check_add.py > ../bisect.log 2>&1
grep "is the first bad commit" ../bisect.log
git log -1 --format="   → %s (%an, %ad)" --date=short refs/bisect/bad
echo "steps: $(grep -c '^running' ../bisect.log) test runs for 32 commits (log2(32) = 5)"
git bisect reset >/dev/null 2>&1
