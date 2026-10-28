#!/usr/bin/env bash
# L03-02 demo: একই শুরু থেকে তিনটি repository — fast-forward, merge commit, rebase — এবং একটি conflict।
# নির্দিষ্ট author/তারিখ → hash যেকোনো machine-এ একই। আপনার global Git config ব্যবহার হয় না।
# Usage: bash merge_vs_rebase.sh /tmp/merge-demo     (directory আগে থেকে থাকলে থামবে)
set -euo pipefail

DEST=${1:?usage: bash merge_vs_rebase.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists" >&2; exit 2; }
mkdir -p "$DEST"; cd "$DEST"
: > .empty-gitconfig
export GIT_CONFIG_GLOBAL="$PWD/.empty-gitconfig" GIT_CONFIG_NOSYSTEM=1 \
       GIT_AUTHOR_NAME="Lab User" GIT_AUTHOR_EMAIL=lab@example.com \
       GIT_COMMITTER_NAME="Lab User" GIT_COMMITTER_EMAIL=lab@example.com
t=0
commit() {   # প্রতিটি commit-এ এক মিনিট এগোনো সময় — ক্রম স্পষ্ট, hash নির্দিষ্ট
  t=$((t + 60))
  GIT_AUTHOR_DATE="@$((1767225600 + t)) +0000" GIT_COMMITTER_DATE="@$((1767225600 + t)) +0000" git commit -q "$@"
}

base() {  # main: A — B ; feature (B থেকে): F1 — F2 ; main-এ আরো একটি: C (diverged)
  t=0                               # প্রতিটি scenario একই শুরু → A, B, F1, F2-এর hash একই
  git init -q -b main "$1"; cd "$1"
  printf 'line1\nline2\nline3\n' > app.txt; git add .; commit -m "A: initial"
  echo "readme" > README.md; git add .; commit -m "B: add readme"
  git switch -q -c feature
  echo "feature one" > f1.txt; git add .; commit -m "F1: feature part 1"
  echo "feature two" > f2.txt; git add .; commit -m "F2: feature part 2"
  git switch -q main
}

echo "== 1. fast-forward (main has not moved)"
base ff
git merge -q --ff-only feature
git log --oneline --graph
cd ..

echo; echo "== 2. merge commit (main moved: C)"
base merged
echo "docs" > docs.txt; git add .; commit -m "C: docs on main"
git tag before-merge              # graph.py দিয়ে merge-এর আগের অবস্থা দেখার জন্য
GIT_AUTHOR_DATE="@1767226200 +0000" GIT_COMMITTER_DATE="@1767226200 +0000" git merge -q --no-edit feature
git log --oneline --graph
cd ..

echo; echo "== 3. rebase feature onto main, then fast-forward"
base rebased
echo "docs" > docs.txt; git add .; commit -m "C: docs on main"
git switch -q feature
echo "   feature before rebase: $(git rev-parse --short HEAD)"
GIT_COMMITTER_DATE="@1767226200 +0000" git rebase -q main
echo "   feature after rebase:  $(git rev-parse --short HEAD)  (new commits, same changes)"
git switch -q main; git merge -q --ff-only feature
git log --oneline --graph
cd ..

echo; echo "== 4. conflict: both branches change line2"
t=0
git init -q -b main conflict; cd conflict
printf 'line1\nline2\nline3\n' > app.txt; git add .; commit -m "A: initial"
git switch -q -c feature; sed -i 's/line2/line2 from feature/' app.txt; commit -am "F: edit line2"
git switch -q main; sed -i 's/line2/line2 from main/' app.txt; commit -am "M: edit line2"
git merge feature || true
echo "--- app.txt during conflict:"
cat app.txt
git status --short
git merge --abort
echo "--- after git merge --abort: $(git status --short | wc -l) changed file(s)"
