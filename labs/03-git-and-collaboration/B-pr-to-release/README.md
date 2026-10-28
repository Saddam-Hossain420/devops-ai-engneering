# Lab 03-B — Branch থেকে release: PR workflow ও semantic version

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ৯০–১২০ মিনিট |
| **Environment** | Git, Bash, Python ৩.১০+; Part 2-এর জন্য বিনামূল্যের GitHub account ও `gh` CLI |
| **Label** | — (Part 1 সম্পূর্ণ local; Part 2 নিজের practice repository-তে) |

## Objective

একটি ছোট project-কে **পুরো collaboration চক্রের** মধ্য দিয়ে নিয়ে যাওয়া:

- Feature branch → conflict সমাধান → code owner অনুযায়ী reviewer → CI-যোগ্য workflow (lint পরিষ্কার) → merge → Conventional Commits থেকে পরের version → annotated tag → push।

প্রতিটি ধাপ এই module-এর tool দিয়ে যাচাই করা হবে।

## Prerequisites

- Lesson: [L03-02](../../../03-git-and-collaboration/L03-02-branch-merge-rebase.md), [L03-03](../../../03-git-and-collaboration/L03-03-remotes-tags-semver.md), [L03-04](../../../03-git-and-collaboration/L03-04-pull-requests-review.md), [L03-06](../../../03-git-and-collaboration/L03-06-github-actions-fundamentals.md)

## Environment setup

```bash
M=~/devops-ai-engineering/03-git-and-collaboration/code
mkdir -p ~/lab03b && cd ~/lab03b
git init -q --bare -b main origin.git
git clone -q origin.git app && cd app
# এই lab-এ নিজের নাম/email ব্যবহার করুন (git config --global user.name ...), অথবা:
git config user.name "Your Name"; git config user.email "you@example.com"
```

## Steps

### Part 1 — local (bare repository-কে remote ধরে)

1. **ভিত্তি:**
   - `app.py` (একটি `add()` function) ও `test_app.py` (unittest) লিখুন।
   - `.github/CODEOWNERS` বানান (`*` → `@you`, `/.github/` → `@security-team`)।
   - `.github/workflows/ci.yml` হিসেবে [`sample-good-workflow.yml`](../../../03-git-and-collaboration/code/L03-06/sample-good-workflow.yml) রাখুন।
   - Commit `chore: initial`, তারপর push ও `git tag -a v0.1.0 -m "v0.1.0"` এবং `git push origin v0.1.0`।
2. **দুটি branch, একই লাইন:**
   - `feat/multiply` branch-এ `multiply()` যোগ করুন এবং `add()`-এর docstring বদলান: commit `feat: add multiply`।
   - `fix/add-types` branch-এ একই docstring অন্যভাবে বদলান: commit `fix: validate add() inputs`।
3. **সম্পর্ক যাচাই:** `python3 $M/L03-02/graph.py main feat/multiply` — fast-forward সম্ভব?
4. **প্রথম merge:** `fix/add-types` → main (`git merge --ff-only`)।
5. **Conflict:**
   - `feat/multiply`-কে main-এর উপর rebase করুন — conflict হবে।
   - সমাধান করুন, তারপর `python3 $M/L03-02/conflict_markers.py $(git ls-files)` exit 0 না আসা পর্যন্ত চালান।
   - `python3 -m unittest`, তারপর `git rebase --continue`।
6. **Review-এর প্রস্তুতি:**
   - `python3 $M/L03-04/codeowners.py review .github/CODEOWNERS --base main` — কার review লাগবে?
   - `python3 $M/L03-04/codeowners.py lint .github/CODEOWNERS --require .github/workflows/`
   - `python3 $M/L03-06/workflow_lint.py .github/workflows/ci.yml`
7. **Merge ও release:**
   - `feat/multiply` merge করুন (fast-forward)।
   - `python3 $M/L03-03/semver.py next --repo .` → প্রত্যাশিত `0.2.0`।
   - Annotated tag তৈরি করে push করুন: `git push origin main v0.2.0`।
   - `git ls-remote ../origin.git` চালান।

### Part 2 — GitHub-এ (নিজের practice repository)

8. GitHub-এ একটি নতুন private repository তৈরি করুন, এবং `git remote add github git@github.com:YOU/lab03b.git` দিয়ে push করুন।
9. L03-04 Section 9.5 অনুযায়ী `main`-এ protection চালু করুন। `gh api` দিয়ে JSON নিয়ে `protection_check.py` চালান।
10. একটি নতুন `feat/divide` PR খুলুন (`gh pr create`) → CI সবুজ হওয়ার অপেক্ষা (`gh pr checks --watch`) → squash merge → tag `v0.3.0` push করুন।

## Expected behavior

- Step 3: diverged নয়, কারণ `fix/add-types` এখনো merge হয়নি → fast-forward সম্ভব।
- Step 5: একটি conflict; সমাধানের পরে marker check exit 0, এবং test পাস।
- Step 6: workflow change থাকলে `@security-team`-এর review দরকার দেখায়; workflow lint `0 finding(s)`।
- Step 7: `next version: 0.2.0 (minor)`; `ls-remote`-এ `refs/tags/v0.2.0` ও `^{}`।

## Verification

```bash
git -C ~/lab03b/app log --oneline --graph --all | head -10
git -C ~/lab03b/app describe --tags                       # v0.2.0 (বা Part 2-এর পরে v0.3.0)
(cd ~/lab03b/app && python3 $M/L03-02/conflict_markers.py $(git ls-files)); echo "exit=$?"   # 0
git ls-remote ~/lab03b/origin.git | grep -c 'refs/tags/v0.2.0'   # 2 (tag ও ^{})
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| Rebase-এ conflict, কোনটি "ours" বুঝছি না | Rebase-এ ours/theirs উল্টো | L03-02 Section 8.2; `git diff --merge` |
| `semver.py next` বলছে "no release tag" | Tag push হয়নি বা `v` ছাড়া নাম | `git tag -l`; `vX.Y.Z` নাম ব্যবহার করুন |
| `next` version প্রত্যাশার চেয়ে কম | Commit message convention মানেনি | `git log --format=%s v0.1.0..` দেখুন |
| GitHub push: `Permission denied (publickey)` | SSH key | L01-13; `ssh -T git@github.com` |
| Required check "expected" | Workflow-এর job নাম ও protection-এর নাম ভিন্ন | L03-04 troubleshooting |

## Cleanup / reset

```bash
rm -rf ~/lab03b      # GitHub repository আলাদাভাবে মুছুন (Settings → Danger zone), যদি আর না লাগে
```

## Assessment

1. আপনার repository-র graph-এর screenshot বা `git log --graph` output, প্রতিটি commit-এর ধরন সহ।
2. Conflict-এ কোন সিদ্ধান্ত নিলেন এবং কেন? Test কীভাবে সিদ্ধান্ত যাচাই করল?
3. `0.2.0` কেন `0.1.1` নয়? কোন commit কী অবদান রাখল?
4. (Part 2) Protection-এর কোন setting আপনার একক-ব্যক্তির repository-তে চালু রাখা সম্ভব হয়নি, এবং team-এ কীভাবে হতো?
