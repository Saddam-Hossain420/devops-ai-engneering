#!/usr/bin/env bash
# Lab 03-C: একটি নতুন directory-তে ছোট team-এর Git জগৎ বানিয়ে পাঁচটি দুর্ঘটনা ঘটায়।
#   origin.git  — "GitHub" (bare repository)
#   you/        — আপনার clone (এখানেই বেশিরভাগ দুর্ঘটনা)
#   teammate/   — সহকর্মীর clone
#   calc/       — bisect-এর জন্য আলাদা repository
# System-এ কিছু বদলায় না; শুধু DEST-এর ভেতরে। আপনার global Git config ব্যবহার হয় না
# (DEST/.gitconfig-lab — lab-এর সময় `source DEST/lab-env.sh` করে নিন)।
# Usage: bash break-it.sh ~/lab03c
set -euo pipefail

DEST=${1:?usage: bash break-it.sh DIR}
[[ -e "$DEST" ]] && { echo "refusing: $DEST already exists (reset.sh দিয়ে মুছুন)" >&2; exit 2; }
mkdir -p "$DEST"; DEST=$(cd "$DEST" && pwd); cd "$DEST"
touch .lab03c                               # reset.sh শুধু এই চিহ্নযুক্ত directory মোছে
: > .gitconfig-lab
cat > lab-env.sh <<EOF
# source করুন: lab-এর জন্য আলাদা Git config ও পরিচয়
export GIT_CONFIG_GLOBAL="$DEST/.gitconfig-lab" GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME="You" GIT_AUTHOR_EMAIL=you@example.com GIT_COMMITTER_NAME="You" GIT_COMMITTER_EMAIL=you@example.com
EOF
# shellcheck disable=SC1091
source lab-env.sh
t=0
as() {  # as <name> <git args...> — নির্দিষ্ট সময় ও লেখক দিয়ে git command
  local who=$1; shift
  t=$((t + 60))
  GIT_AUTHOR_NAME="$who" GIT_AUTHOR_EMAIL="$who@example.com" GIT_COMMITTER_NAME="$who" \
  GIT_COMMITTER_EMAIL="$who@example.com" GIT_AUTHOR_DATE="@$((1767225600 + t)) +0000" \
  GIT_COMMITTER_DATE="@$((1767225600 + t)) +0000" git "$@"
}

git init -q --bare -b main origin.git
git clone -q origin.git you 2>/dev/null
cd you
printf 'app\n' > app.txt; printf 'DEBUG=false\n' > config.txt; git add .; as You commit -q -m "chore: initial"
printf 'login\n' > login.txt; git add .; as You commit -q -m "feat: login page"
git push -q origin main
cd ..
git clone -q origin.git teammate
cd teammate
printf 'audit\n' > audit.txt; git add .; as Rina commit -q -m "feat: audit log"
git push -q origin main
cd ../you

# দুর্ঘটনা ১: fetch না করে নিজের commit, push প্রত্যাখ্যাত — তারপর "সমাধান" হিসেবে --force
printf 'APP_NAME=shop\n' > settings.txt; git add .; as You commit -q -m "chore: rename config"
git push -q --force origin main 2>/dev/null

# দুর্ঘটনা ২: shared main-এ একটি খারাপ commit push হয়ে গেছে
printf 'DEBUG=true\n' > config.txt; as You commit -q -am "feat: enable debug in prod config"
git push -q origin main

# দুর্ঘটনা ৩: দুটি commit, তারপর ভুল করে reset --hard
printf 'retry 1\n' > payment.txt; git add .; as You commit -q -m "feat: payment retries (1/2)"
printf 'retry 2\n' >> payment.txt; as You commit -q -am "feat: payment retries (2/2)"
as You reset -q --hard HEAD~2

# দুর্ঘটনা ৪: unmerged branch মুছে ফেলা
git switch -q -c hotfix/login
printf 'timeout=30\n' > login.txt; as You commit -q -am "fix: login timeout"
git switch -q main
git branch -q -D hotfix/login
cd ..

# দুর্ঘটনা ৫: কোন commit add() ভেঙেছে? (১৬টি commit)
git init -q -b main calc
cd calc
for n in $(seq 1 16); do
  if (( n < 11 )); then op="+"; else op="-"; fi
  printf 'def add(a, b):\n    return a %s b\n\n# change %d\n' "$op" "$n" > calc.py
  git add .; as You commit -q -m "change $n"
done
cd ..
cat > check_calc.py <<'EOF'
# bisect-এর test: exit 0 = good, 1 = bad।  চালান: python3 -B ../check_calc.py   (-B: bytecode cache নয়, L03-05)
import sys
sys.path.insert(0, ".")
from calc import add
sys.exit(0 if add(2, 3) == 5 else 1)
EOF

echo "Lab 03-C ready in $DEST"
echo "First:  source $DEST/lab-env.sh"
echo "Then:   cd $DEST/you && git log --oneline --all   — and start investigating."
