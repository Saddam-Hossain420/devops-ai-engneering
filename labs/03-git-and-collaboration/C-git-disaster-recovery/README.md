# Lab 03-C — Git disaster recovery

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট |
| **Environment** | Git ২.৩০+, Bash, Python ৩.১০+ — Ubuntu, Fedora বা Windows-এর Git Bash, সবখানে চলে |
| **Label** | — (শুধু নিজের তৈরি directory-তে কাজ করে; system বা আপনার global Git config বদলায় না) |
| **Tested** | `break-it.sh` → নিজে সমাধান → `check.sh`: `ALL CHECKS PASSED` (Windows/Git Bash, Git 2.54, ২০২৬-১০-২৭)। সমাধানের সময় যে ফাঁদগুলোতে পড়েছিলাম, সেগুলোই নিচের সূত্রে আছে। |

## Objective

একটি ছোট team-এর repository-তে **পাঁচটি দুর্ঘটনা** ঘটেছে। প্রতিটি থেকে উদ্ধার করতে হবে **history পুনর্লিখন বা force push ছাড়া**, শুধু প্রমাণ দেখে (reflog, log, অন্য clone):

1. হারানো কাজ (`reset --hard`)।
2. মুছে ফেলা branch।
3. Force push-এ মুছে যাওয়া সহকর্মীর commit।
4. Shared branch-এ push হয়ে যাওয়া খারাপ commit।
5. একটি regression — কোন commit-এ ঢুকেছে?

## Prerequisites

- Lesson: [L03-01](../../../03-git-and-collaboration/L03-01-git-internals.md), [L03-02](../../../03-git-and-collaboration/L03-02-branch-merge-rebase.md), [L03-03](../../../03-git-and-collaboration/L03-03-remotes-tags-semver.md), [L03-05](../../../03-git-and-collaboration/L03-05-git-recovery.md)
- Tool: [`lost_commits.py`](../../../03-git-and-collaboration/code/L03-05/lost_commits.py)

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/03-git-and-collaboration/C-git-disaster-recovery
bash break-it.sh ~/lab03c
source ~/lab03c/lab-env.sh          # lab-এর আলাদা Git config ও পরিচয় — এই terminal-এ
cd ~/lab03c/you
```

Files: [`break-it.sh`](break-it.sh), [`check.sh`](check.sh), [`reset.sh`](reset.sh)। **Script না পড়ে investigate করুন।**

Lab-এর জগৎ:

| Directory | ভূমিকা |
|---|---|
| `origin.git` | "GitHub" — bare repository |
| `you/` | আপনার clone |
| `teammate/` | সহকর্মী রিনার clone |
| `calc/` | Bisect-এর আলাদা repository; test script `../check_calc.py` |

## Steps

1. Timer চালু করুন।
2. **কোনো কিছু বদলানোর আগে** পর্যবেক্ষণ করুন এবং notebook-এ লিখে রাখুন:

   ```bash
   git log --oneline --graph --all
   git reflog -15
   python3 ~/devops-ai-engineering/03-git-and-collaboration/code/L03-05/lost_commits.py
   git -C ../teammate log --oneline -5
   git -C ../origin.git log --oneline main
   ```

3. প্রতিটি দুর্ঘটনার জন্য: কী হারিয়েছে → কোথায় এখনো আছে → উদ্ধারের সবচেয়ে নিরাপদ পথ।
   - নিয়ম: আগে `git branch rescue/...` করুন, পরে সিদ্ধান্ত নিন।
4. Origin-এ পরিবর্তন শুধু সাধারণ `git push` দিয়ে — **`--force` নিষেধ**।
5. Bisect: `calc/`-এ প্রথম খারাপ commit-এর SHA `~/lab03c/bisect-answer.txt`-এ লিখুন (প্রথম লাইনে)। শেষে `git bisect reset`।
6. যাচাই:

   ```bash
   bash ~/devops-ai-engineering/labs/03-git-and-collaboration/C-git-disaster-recovery/check.sh ~/lab03c
   ```

7. Timer থামান; notebook-এ প্রতিটি দুর্ঘটনার incident note লিখুন।

## Expected behavior

`check.sh`-এ সাতটি PASS ও `ALL CHECKS PASSED`, exit 0। সাতটি check হলো:

- `origin/main`-এ সহকর্মীর `feat: audit log` ও আপনার `chore: rename config` দুটোই আছে।
- `feat: enable debug in prod config` commit history-তে **থেকে গেছে** এবং তার একটি Revert আছে।
- `config.txt`-এ `DEBUG=true` নেই।
- দুটি payment commit `origin/main`-এ আছে।
- `you/`-এ `hotfix/login` branch আছে।
- Bisect-এর উত্তর সঠিক।
- কোনো bisect session খোলা নেই।

## Verification

```bash
bash check.sh ~/lab03c; echo "exit=$?"                       # 0
git -C ~/lab03c/origin.git log --oneline --graph main        # কোনো commit হারায়নি, শুধু যোগ হয়েছে
```

## Troubleshooting (সূত্র — আটকে গেলে একটি একটি করে খুলুন)

<details><summary>সূত্র ১ — reflog-এর সংখ্যা সরে যায়</summary>

`HEAD@{3}` আজ যে commit, একটি `git switch` বা `git branch`-এর পরে সেটা আর `HEAD@{3}` নয় — নতুন entry যোগ হলে সব সংখ্যা সরে। এই lab-এর সমাধান লেখার সময় ঠিক এই ভুলে payment-এর বদলে reset-এর অবস্থান ধরা পড়েছিল। **SHA দেখে উদ্ধার করুন:**

```bash
git log -g --format='%h %gs' | grep payment
```

</details>

<details><summary>সূত্র ২ — সহকর্মীর commit কোথায়?</summary>

Origin-এর ইতিহাস force push-এ বদলে গেছে, কিন্তু রিনার clone-এ তাঁর commit এখনো আছে (`git -C ../teammate log`)। Bare repository-তেও object হয়তো dangling অবস্থায় আছে (`git -C ../origin.git fsck --no-reflogs`)।

</details>

<details><summary>সূত্র ৩ — ⚠️ force push-এর পরে <code>git pull --rebase</code> commit চুপচাপ ফেলে দিতে পারে</summary>

রিনার clone-এ `git pull --rebase` চালালে তাঁর `feat: audit log` **কোনো সতর্কতা ছাড়াই বাদ পড়ে যায়।** এই lab-এর সমাধান লেখার সময় আসলে এটা ঘটেছিল।

কারণ: রিনার `origin/main`-এর reflog-এ ঐ commit একবার ছিল (তিনি নিজেই push করেছিলেন)। Rebase-এর `--fork-point` logic তাই ধরে নেয় যে upstream ইচ্ছা করে commit-টি সরিয়েছে।

নিরাপদ পথ:

- আগে দেখুন: `git fetch` তারপর `git log --oneline origin/main..main` (শুধু আপনার কাছে আছে কী)।
- তারপর `git rebase --no-fork-point origin/main` বা `git cherry-pick <sha>`।

</details>

<details><summary>সূত্র ৪ — খারাপ commit</summary>

এটা ইতিমধ্যে push হয়েছে, অন্যরা নিয়েছেন। `reset` করে force push করলে check fail করবে (এবং বাস্তবে অন্যদের history ভাঙবে)। কোন command নতুন commit যোগ করে পরিবর্তন বাতিল করে? (L03-05)

</details>

<details><summary>সূত্র ৫ — bisect ভুল উত্তর দিচ্ছে?</summary>

Test script `python3 -B` দিয়ে চালান (bytecode cache নয় — L03-05 Section 9.3)। শুরু: `git bisect start HEAD <প্রথম commit>`, তারপর `git bisect run python3 -B ../check_calc.py`।

</details>

## Cleanup / reset

```bash
bash reset.sh ~/lab03c         # শুধু .lab03c চিহ্নযুক্ত directory মোছে
```

আবার অনুশীলন করতে `break-it.sh` আবার চালান। Hash-গুলো প্রতিবার একই থাকে, তাই আগের notes মিলিয়ে দেখতে পারবেন।

## Assessment

1. প্রতিটি দুর্ঘটনা: কী হারিয়েছিল, কোথায় পাওয়া গেল (আসল command ও output), কোন command-এ উদ্ধার, এবং কেন সেটাই সবচেয়ে নিরাপদ।
2. সহকর্মীর commit উদ্ধারের দুটি ভিন্ন উৎস কী কী? কোনটি কখন ব্যর্থ হতে পারে?
3. সূত্র ৩-এর ফাঁদ আপনি কীভাবে আগেভাগে ধরতেন? এটা এড়াতে team-এর জন্য কোন নিয়ম লিখবেন?
4. খারাপ commit-এ `reset` + force push কেন ভুল ছিল, `revert` কেন সঠিক?
5. এই পাঁচটির কোনটি protected branch (L03-04) পুরোপুরি আটকাত?
