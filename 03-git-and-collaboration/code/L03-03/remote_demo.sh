#!/usr/bin/env bash
# L03-03 demo: একটি local bare repository-কে "origin" (যেমন GitHub) ধরে দুই developer — alice ও bob।
# clone, push, fetch বনাম pull, remote-tracking branch, non-fast-forward rejection, tag push, ls-remote।
# নির্দিষ্ট author/তারিখ → hash যেকোনো machine-এ একই; global Git config ব্যবহার হয় না; network লাগে না।
# Usage: bash remote_demo.sh /tmp/remote-demo
set -euo pipefail

DEST=${1:?usage: bash remote_demo.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists" >&2; exit 2; }
mkdir -p "$DEST"; cd "$DEST"
: > .empty-gitconfig
export GIT_CONFIG_GLOBAL="$PWD/.empty-gitconfig" GIT_CONFIG_NOSYSTEM=1 GIT_COMMITTER_NAME=Lab GIT_COMMITTER_EMAIL=lab@example.com
t=0
commit() {  # commit <author> <message> — প্রতিবার এক মিনিট এগোনো সময়
  t=$((t + 60))
  GIT_AUTHOR_NAME="$1" GIT_AUTHOR_EMAIL="$1@example.com" \
  GIT_AUTHOR_DATE="@$((1767225600 + t)) +0000" GIT_COMMITTER_DATE="@$((1767225600 + t)) +0000" \
    git commit -q -m "$2"
}

git init -q --bare -b main origin.git
git clone -q origin.git alice 2>/dev/null
cd alice
echo "v1" > app.txt; git add .; commit alice "feat: first version"
git push -q origin main
cd ..
git clone -q origin.git bob
echo "== remotes and tracking (bob)"
git -C bob remote -v
git -C bob branch -vv

echo; echo "== alice pushes a fix; bob has not fetched yet"
cd alice; echo "v1 fixed" > app.txt; git add .; commit alice "fix: correct output"; git push -q origin main; cd ..
git -C bob status -sb | head -1
echo "-- after git fetch (nothing in bob's working tree changes):"
git -C bob fetch -q
git -C bob status -sb | head -1
git -C bob log --oneline --all

echo; echo "== bob commits on his (fetched but not merged) main → push is rejected"
cd bob
echo "notes" > notes.txt; git add .; commit bob "docs: add notes"
git push origin main 2>&1 | sed -n '1,3p' || true
echo "-- bob: git pull --rebase, then push"
GIT_COMMITTER_DATE="@1767226500 +0000" git pull -q --rebase origin main
git push -q origin main
git log --oneline
cd ..

echo; echo "== release tag"
cd alice
git pull -q --ff-only
GIT_COMMITTER_DATE="@1767226600 +0000" git tag -a v1.0.0 -m "release 1.0.0"
git push -q origin v1.0.0
cd ..
git ls-remote origin.git
