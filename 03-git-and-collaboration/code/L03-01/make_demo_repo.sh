#!/usr/bin/env bash
# L03-01 demo repository — নির্দিষ্ট author ও তারিখ, তাই যেকোনো machine-এ commit hash হুবহু একই।
# Usage: bash make_demo_repo.sh /tmp/git-demo      (directory আগে থেকে থাকলে script থামবে)
# আপনার global Git config ব্যবহার হয় না: GIT_CONFIG_GLOBAL একটি খালি file-এ।
set -euo pipefail

DEST=${1:?usage: bash make_demo_repo.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists" >&2; exit 2; }
mkdir -p "$DEST"
cd "$DEST"
: > .empty-gitconfig
export GIT_CONFIG_GLOBAL="$PWD/.empty-gitconfig" GIT_CONFIG_NOSYSTEM=1 \
       GIT_AUTHOR_NAME="Lab User" GIT_AUTHOR_EMAIL=lab@example.com \
       GIT_COMMITTER_NAME="Lab User" GIT_COMMITTER_EMAIL=lab@example.com \
       GIT_AUTHOR_DATE=2026-01-01T00:00:00+0000 GIT_COMMITTER_DATE=2026-01-01T00:00:00+0000

git init -q -b main demo
cd demo
echo "hello" > hello.txt
mkdir src
printf 'print("v1")\n' > src/app.py
git add .
git commit -q -m "first commit"
printf 'print("v2")\n' > src/app.py
git commit -q -am "change app"
git tag -a v1.0.0 -m "first release"
git log --oneline
echo "demo repository: $PWD   (expected: bea3fb5 change app / cf32167 first commit)"
