#!/usr/bin/env bash
# L03-05 demo: তিনটি দুর্ঘটনা ও উদ্ধার — reset --hard, branch মুছে ফেলা, shared branch-এ খারাপ commit (revert)।
# নির্দিষ্ট author/তারিখ → hash যেকোনো machine-এ একই; global config ব্যবহার হয় না।
# Usage: bash recovery_demo.sh /tmp/recovery-demo
set -euo pipefail

DEST=${1:?usage: bash recovery_demo.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists" >&2; exit 2; }
HERE="$(cd "$(dirname "$0")" && pwd)"
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
t=0
tick() { t=$((t + 60)); export GIT_AUTHOR_DATE="@$((1767225600 + t)) +0000" GIT_COMMITTER_DATE="@$((1767225600 + t)) +0000"; }
commit() { tick; git commit -q "$@"; }

git init -q -b main repo; cd repo
for n in 1 2 3 4; do echo "step $n" >> work.txt; git add .; commit -m "step $n"; done
echo "== start"; git log --oneline

echo; echo "== accident 1: git reset --hard HEAD~2 (two commits 'gone')"
tick; git reset -q --hard HEAD~2
git log --oneline
echo "-- reflog:"
git reflog -5
echo "-- lost_commits.py:"
"$PY" "$HERE/lost_commits.py" || true
echo "-- recover: git reset --hard HEAD@{1}"
tick; git reset -q --hard 'HEAD@{1}'
git log --oneline -1

echo; echo "== accident 2: delete an unmerged branch"
git switch -q -c experiment
echo "idea" > idea.txt; git add .; commit -m "experiment: promising idea"
git switch -q main
out=$(git branch -D experiment); echo "$out"       # branch-এর নিজের reflog-ও মুছে যায়!
"$PY" "$HERE/lost_commits.py" || true
sha=$(sed -n 's/.*(was \([0-9a-f]*\)).*/\1/p' <<<"$out")   # "(was 2759ef6)." — বার্তাতেই SHA
tick; git branch experiment "$sha"
echo "-- restored: $(git log --oneline -1 experiment)"

echo; echo "== accident 3: a bad commit is already on shared main → revert (no history rewrite)"
echo "DEBUG=true  # oops" > config.txt; git add .; commit -m "chore: enable debug"
tick; git revert --no-edit HEAD >/dev/null
git log --oneline -3
echo "-- config.txt exists after revert? $([[ -e config.txt ]] && echo yes || echo no)"
