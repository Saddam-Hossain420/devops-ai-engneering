# L03-05 — Git recovery: reflog, reset, revert, bisect

| | |
|---|---|
| **Module** | 03 — Git and Collaboration |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L03-01 — Git internals](L03-01-git-internals.md), [L03-02 — Branch, merge ও rebase](L03-02-branch-merge-rebase.md) |
| **Label** | ⚠️ DESTRUCTIVE command (`reset --hard`, `reflog expire`, `gc`) — শুধু demo/temporary repository-তে অনুশীলন করুন |
| **Tested** | `lost_commits.py` ও দুটি demo script: ৭টি test পাস। Temporary repository-তে আসল git দিয়ে যাচাই করা হয়েছে: `reset --hard` (একটি tip), মুছে ফেলা branch ও উদ্ধার, reflog expire-এর পরে `fsck`-এ খুঁজে পাওয়া, CLI exit code, `bisect run`-এ change 21, recovery demo। (Python 3.14, Git 2.54, Windows/Git Bash।) Demo লেখার সময় **bisect ভুল commit দেখিয়েছিল** — Python-এর stale bytecode cache; কারণ ও সমাধান Section 9.3-এ। Ubuntu-তে চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- **Reflog**: প্রতিটি ref কোথায় কোথায় ছিল তার local ডায়েরি — "হারানো" commit খোঁজার প্রথম জায়গা।
- `reset`-এর তিন রূপ (`--soft`, `--mixed`, `--hard`) — কোনটি কী বদলায়, কোনটি কী মুছে ফেলে।
- `restore` ও `switch` — আধুনিক, কম বিপজ্জনক command।
- **Revert** বনাম reset: shared history-তে কেন revert।
- **Bisect**: binary search দিয়ে কোন commit bug এনেছে তা খোঁজা, স্বয়ংক্রিয়ভাবে (`bisect run`)।
- কী **সত্যিই** হারায়: commit না করা পরিবর্তন, reflog expire ও gc-র পরে।
- Python দিয়ে reflog বিশ্লেষণ করে হারানো commit খোঁজা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Git-এর ভুল প্রায়ই আতঙ্ক তৈরি করে: "`reset --hard` দিয়ে দুই দিনের কাজ গেল", "ভুল branch মুছে ফেলেছি", "rebase-এর পরে সব উল্টে গেছে", "production-এ কোন commit-এ bug ঢুকল জানি না"। আতঙ্কে মানুষ আরো ধ্বংসাত্মক কাজ করেন — repository মুছে আবার clone, `--force` push।

সত্যটা হলো: L03-01 অনুযায়ী commit object অপরিবর্তনীয়, এবং কোনো ref নির্দেশ না করলেও **তাৎক্ষণিকভাবে মোছে না**। Reflog সাধারণত ৯০ দিন (unreachable entry ৩০ দিন) মনে রাখে। তাই commit করা কাজ প্রায় সবসময় উদ্ধারযোগ্য। এই lesson উদ্ধারের পদ্ধতি এবং কোথায় সত্যিই ঝুঁকি আছে তা শেখায়।

DevOps-এর দৈনন্দিন কাজেও এগুলো লাগে:

- **Production rollback:** খারাপ commit revert করে deploy (Module 06, 16)।
- **Regression খোঁজা:** "গত সপ্তাহে ঠিক ছিল" — bisect।
- **Incident-এর পরে:** কোন পরিবর্তন সমস্যা আনল তার প্রমাণ।

## 3. সহজ ভাষায় পরিচয়

### Reset — branch-কে অন্য commit-এ সরানো

| | Branch (HEAD) সরে | Index (staging) | Working tree | ঝুঁকি |
|---|---|---|---|---|
| `git reset --soft X` | হ্যাঁ | অপরিবর্তিত | অপরিবর্তিত | কম — পরিবর্তনগুলো staged থাকে |
| `git reset X` (`--mixed`) | হ্যাঁ | X-এর মতো | অপরিবর্তিত | কম — পরিবর্তন unstaged থাকে |
| `git reset --hard X` | হ্যাঁ | X-এর মতো | **X-এর মতো** | **উঁচু — commit না করা পরিবর্তন মুছে যায়, ফেরানো যায় না** |

Commit করা কাজ `--hard`-এর পরেও reflog-এ থাকে। **Commit না করা কাজ থাকে না** (শুধু `git add` করা থাকলে blob থাকে — Section 8.3)।

### Revert — নতুন commit যা পুরোনোটার উল্টো

`git revert X` একটি **নতুন** commit তৈরি করে যা X-এর পরিবর্তন বাতিল করে। History পুনর্লিখন হয় না, তাই shared/protected branch-এ নিরাপদ (L03-02-এর সোনালি নিয়ম)।

| পরিস্থিতি | Command |
|---|---|
| শুধু local, push হয়নি | `reset` (বা `commit --amend`, `rebase -i`) |
| Push হয়ে গেছে, অন্যরা নিয়েছেন | **`revert`** |

### Reflog — ref-এর ডায়েরি

```text
07e763f HEAD@{0}: reset: moving to HEAD~2
3b30c0c HEAD@{1}: commit: step 4          ← "হারানো" commit এখানে
93d77c5 HEAD@{2}: commit: step 3
```

`HEAD@{1}` = "HEAD এক ধাপ আগে কোথায় ছিল"। প্রতিটি branch-এর নিজস্ব reflog আছে (`main@{1}`)। Reflog **local**, কখনো push হয় না।

### Bisect — binary search

"`v1.4` ঠিক ছিল, এখন ভাঙা, মাঝে ২০০টি commit।" Bisect মাঝের commit checkout করে, আপনি (বা script) বলেন good নাকি bad, এবং প্রতিবার পরিসর অর্ধেক হয়: ২০০টি commit → প্রায় ৮টি পরীক্ষা।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### গাড়ির dashcam ও odometer

- **Reflog** = গাড়ির dashcam: আপনি কোথায় কোথায় গিয়েছিলেন তার রেকর্ড, এমনকি ভুল মোড়ও। ভুল মোড় নিলে দেখে আগের জায়গায় ফিরতে পারেন।
- **Reset** = GPS-এ "এখান থেকে নতুন যাত্রা" বলা — ঠিকানা বদলায়। `--hard` = গাড়ির ভেতরের সব জিনিসও ফেলে দেওয়া।
- **Revert** = ভুল পথে গিয়ে আবার একই পথে ফিরে আসা — যাত্রার রেকর্ডে দুটোই থাকে, কিন্তু আপনি আগের অবস্থানে।
- **Bisect** = "কোন মোড়ে টায়ার পাংচার হলো?" — মাঝপথের জায়গায় গিয়ে দেখা, তারপর অর্ধেক অর্ধেক করে খোঁজা।

### Analogy কোথায় মেলে না

- Dashcam-এর রেকর্ড চিরস্থায়ী হতে পারে। Reflog-এর **মেয়াদ আছে** (default ৯০/৩০ দিন), এবং `git gc` পরে unreachable object মুছে দেয়। উদ্ধার যত দ্রুত, তত নিশ্চিত।
- Dashcam সব গাড়িতে একই। Reflog **শুধু আপনার clone-এ** — সহকর্মীর হারানো commit আপনার reflog-এ নেই (L03-02-এর force push ঘটনা: উদ্ধার তাঁর machine থেকে)। নতুন clone-এর reflog খালি থাকে।
- পাংচার একটি নির্দিষ্ট মোড়ে হয়। Bug কখনো কখনো দুটি পরিবর্তনের মিলনে আসে, বা পরিবেশের উপর নির্ভর করে (data, config, cache)। তখন bisect ভুল বা অস্থির ফল দেয় — Section 9.3-এ ঠিক এমন একটি আসল উদাহরণ আছে।

## 5. Real-world engineering scenario — "Friday-র deploy-এর পরে checkout ভাঙা"

**পরিস্থিতি:** Friday-তে ৪০টি PR merge হয়ে deploy হয়েছে। Saturday সকালে alert: checkout-এর একটি edge case-এ ভুল total দেখাচ্ছে। Rollback-এর আগে জানতে হবে কোন পরিবর্তন দায়ী।

**ধাপ:**

1. **তাৎক্ষণিক প্রশমন:** আগের release image-এ rollback (Module 16)। Git history-তে হাত না দিয়ে, deploy system দিয়ে।
2. **কারণ খোঁজা:** ভাঙা আচরণ ধরে এমন একটি test লেখা (`test_checkout_edge_case.py`), তারপর:

   ```bash
   git bisect start HEAD v2.7.0          # bad, good
   git bisect run python3 -m pytest -q tests/test_checkout_edge_case.py
   ```

   ৪০টি commit-এ প্রায় ৬টি পরীক্ষা, এবং স্বয়ংক্রিয়ভাবে দায়ী commit পাওয়া যায়।
3. **সমাধান:** দায়ী commit-এর `git revert` দিয়ে PR → CI → deploy। Main protected, তাই reset নয়।
4. **Postmortem:** নতুন test স্থায়ীভাবে suite-এ যোগ (regression test)।

**শিক্ষা:** Bisect ততটাই ভালো যতটা ভালো test। একটি দ্রুত, নির্ভরযোগ্য, deterministic test লিখতে পারলে খোঁজার কাজ যন্ত্র করে দেয়।

## 6. Diagram — reset, revert ও reflog

```text
শুরু:            A ─ B ─ C ─ D   ← main (HEAD)

reset --hard B:  A ─ B           ← main
                      └ C ─ D    (নামহীন — reflog-এ main@{1} = D)
উদ্ধার:          git reset --hard main@{1}   বা   git branch rescue D

revert D:        A ─ B ─ C ─ D ─ D'   ← main      (D' = D-র উল্টো; history অক্ষত, push নিরাপদ)

bisect (৮টি commit, ১টি bad):
   good ● ● ● ● ● ● ● ✗ bad
              ▲ ১ম পরীক্ষা (মাঝখান)
                    ▲ ২য়
                       ▲ ৩য়  → log2(8) = ৩ ধাপে দায়ী commit
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Reflog | Local ref-এর অবস্থানের ইতিহাস |
| `HEAD@{n}` / `main@{n}` | n ধাপ আগের অবস্থান |
| `HEAD~n` / `HEAD^2` | n-তম পূর্বপুরুষ / merge-এর দ্বিতীয় parent |
| Reset soft/mixed/hard | Branch সরানো + index/working tree কতটা বদলাবে |
| Revert | উল্টো পরিবর্তনের নতুন commit |
| Restore | File-কে নির্দিষ্ট অবস্থায় ফেরানো (`git restore`) |
| Dangling / unreachable commit | কোনো ref নির্দেশ করে না |
| `git fsck` | Object database-এর অখণ্ডতা ও unreachable object খোঁজা |
| `git gc` | Garbage collection — packing ও unreachable object মোছা |
| Bisect | Binary search দিয়ে দায়ী commit খোঁজা |
| Regression | আগে কাজ করত, এখন করে না |
| Stash | Commit না করে কাজ সাময়িক সরিয়ে রাখা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Reflog কোথায় থাকে

`.git/logs/HEAD` ও `.git/logs/refs/heads/<branch>` — প্রতিটি লাইন: পুরোনো sha, নতুন sha, কে, কখন, কেন। **Branch মুছলে তার নিজের reflog-ও মুছে যায়** — কিন্তু HEAD-এর reflog-এ সেই commit থাকে (যদি checkout করা হয়েছিল)। Demo-তে এটা দেখা যায়: `experiment` মুছে ফেলার পরে commit-টি `HEAD@{1}`-এ পাওয়া গেছে। `git branch -D`-এর বার্তায় SHA থাকে (`was 2759ef6`) — সেটাই দ্রুততম উদ্ধারের সূত্র।

### 8.2 কখন সত্যিই হারায়

| পরিস্থিতি | উদ্ধারযোগ্য? |
|---|---|
| Commit করা, তারপর reset/rebase/branch মোছা | হ্যাঁ — reflog (মেয়াদ পর্যন্ত) |
| Reflog expire হয়েছে কিন্তু `gc` হয়নি | হ্যাঁ — `git fsck` (এই lesson-এর `--fsck`) |
| `git add` করা কিন্তু commit নয়, তারপর `reset --hard` | আংশিক — blob থাকে (`git fsck --lost-found`), file-এর নাম নয় |
| কখনো add/commit হয়নি, তারপর `reset --hard` / `checkout -- file` / `restore` | **না** (editor-এর local history বা backup ছাড়া) |
| `gc --prune=now`-এর পরে unreachable | না |
| অন্যের machine-এ ছিল, আপনার কাছে নয় | শুধু তাঁর clone বা server থেকে |

**নিয়ম:** ঝুঁকিপূর্ণ কাজের আগে commit (বা `git stash`) করুন, অথবা একটি backup branch রাখুন: `git branch backup/before-rebase`।

### 8.3 `restore` ও `switch` — নিরাপদ নতুন command

পুরোনো `git checkout` একসাথে branch বদলায় **ও** file মুছে ফেলে, যা বিভ্রান্তিকর। Git 2.23 থেকে আলাদা command আছে:

```bash
git switch feature                 # branch বদল
git restore file.txt               # working tree-এর পরিবর্তন বাতিল (⚠️ ফেরানো যায় না)
git restore --staged file.txt      # unstage (পরিবর্তন থাকে)
git restore --source=HEAD~3 file.txt   # পুরোনো সংস্করণ আনা
```

### 8.4 Bisect-এর শর্ত

- Test-এর exit code: ০ = good, ১–১২৭ = bad (১২৫ বাদে), ১২৫ = skip (build হয় না এমন commit)।
- Test **deterministic** হতে হবে — network, সময়, random বা cache-এর উপর নির্ভর করলে ভুল ফল আসে।
- Test script repository-র **বাইরে** রাখুন (বা checkout-এ বদলায় না এমন জায়গায়), কারণ bisect প্রতিবার পুরোনো commit checkout করে।
- শেষে অবশ্যই `git bisect reset`, নইলে detached HEAD-এ থেকে যাবেন।

## 9. Practical demonstration

Files: [`code/L03-05/lost_commits.py`](code/L03-05/lost_commits.py), [`recovery_demo.sh`](code/L03-05/recovery_demo.sh), [`bisect_demo.sh`](code/L03-05/bisect_demo.sh)। নির্দিষ্ট author/তারিখ ব্যবহার করে, global config ছাড়া, নিজের temporary directory-তে।

### 9.1 তিনটি দুর্ঘটনা ও উদ্ধার

```bash
cd ~/devops-ai-engineering/03-git-and-collaboration/code/L03-05
bash recovery_demo.sh /tmp/recovery-demo
```

**আসল output:**

```text
== start
3b30c0c step 4
93d77c5 step 3
07e763f step 2
a41e833 step 1

== accident 1: git reset --hard HEAD~2 (two commits 'gone')
07e763f step 2
a41e833 step 1
-- reflog:
07e763f HEAD@{0}: reset: moving to HEAD~2
3b30c0c HEAD@{1}: commit: step 4
93d77c5 HEAD@{2}: commit: step 3
07e763f HEAD@{3}: commit: step 2
a41e833 HEAD@{4}: commit (initial): step 1
-- lost_commits.py:
3b30c0c 2026-01-01 step 4
    reflog: main@{1}  (commit: step 4)
    recover: git branch rescue/3b30c0c 3b30c0cff1a5
1 recoverable commit tip(s)
-- recover: git reset --hard HEAD@{1}
3b30c0c step 4

== accident 2: delete an unmerged branch
Deleted branch experiment (was 2759ef6).
2759ef6 2026-01-01 experiment: promising idea
    reflog: HEAD@{1}  (commit: experiment: promising idea)
    recover: git branch rescue/2759ef6 2759ef606911
1 recoverable commit tip(s)
-- restored: 2759ef6 experiment: promising idea

== accident 3: a bad commit is already on shared main → revert (no history rewrite)
0b077ee Revert "chore: enable debug"
6b2587f chore: enable debug
3b30c0c step 4
-- config.txt exists after revert? no
```

**পর্যবেক্ষণ:**

- দুটি commit "হারিয়েছিল", কিন্তু tool একটি **tip** (`3b30c0c`) দেখায় — ঐ একটি branch তৈরি করলে `93d77c5` সহ পুরো চেইন উদ্ধার হয়।
- Branch মুছে ফেলার পরেও commit HEAD-এর reflog-এ ছিল। `git branch -D`-এর বার্তায় SHA নিজেই আছে।
- Revert-এর পরে খারাপ commit history-তে থাকে (audit trail), কিন্তু তার প্রভাব বাতিল হয় — এবং force push লাগে না।

### 9.2 Reflog মুছে গেলেও — `fsck`

একই demo repository-তে (⚠️ শুধু demo-তে — `reflog expire` সত্যিই রেকর্ড মোছে):

```bash
cd /tmp/recovery-demo/repo
export GIT_CONFIG_GLOBAL=/tmp/recovery-demo/.empty-gitconfig
git reset -q --hard HEAD~2
git reflog expire --expire=now --all
python3 ~/devops-ai-engineering/03-git-and-collaboration/code/L03-05/lost_commits.py
python3 ~/devops-ai-engineering/03-git-and-collaboration/code/L03-05/lost_commits.py --fsck
```

**আসল output:**

```text
nothing lost: every reflog commit is still reachable
0b077ee 2026-01-01 Revert "chore: enable debug"
    found by git fsck (not in any reflog)
    recover: git branch rescue/0b077ee 0b077ee3e7f1
1 recoverable commit tip(s)
```

Reflog খালি থাকায় সাধারণ খোঁজে কিছু পাওয়া যায়নি, কিন্তু object তখনো database-এ আছে। `git fsck`-এর **dangling** commit-ই tip। `git gc --prune=now` চালালে এটাও চলে যেত।

### 9.3 Bisect — এবং একটি আসল ফাঁদ

```bash
bash bisect_demo.sh /tmp/bisect-demo
```

**আসল output:**

```text
== HEAD is broken: add(2, 3) = -1
1108b67bedc19d0d98dbd89ed3023e9be3f224d7 is the first bad commit
   → change 21 (Lab User, 2026-01-01)
steps: 5 test runs for 32 commits (log2(32) = 5)
```

৩২টি commit-এ ৫টি test চালিয়ে bug আনা commit (change 21) পাওয়া গেছে।

**এই demo লেখার সময় যা আসলে ঘটেছিল:** প্রথম সংস্করণে bisect উত্তর দিয়েছিল **"change 16"** — ভুল। কারণ: test `from calc import add` করে, আর Python `calc.py`-এর compiled bytecode `__pycache__`-এ রাখে। Python cache বৈধ কিনা যাচাই করে source file-এর mtime (সেকেন্ডে) ও আকার দিয়ে। Bisect খুব দ্রুত checkout করে, তাই change 15 ও change 16-এর `calc.py` **একই সেকেন্ডে, একই আকারে** লেখা হয়েছিল। Python ভেবেছিল file বদলায়নি এবং পুরোনো (ভুল) bytecode চালিয়েছিল।

সমাধান হিসেবে test `python -B` দিয়ে চালানো হয়েছে, যাতে bytecode cache লেখাই না হয়।

**শিক্ষা:** Bisect-এর test-কে প্রতিটি commit-এ **পরিষ্কার অবস্থা থেকে** চলতে হবে। Build cache, `__pycache__`, `node_modules`, compiled artifact বা Docker layer cache — সবই এমন ভুল ফল দিতে পারে। প্রয়োজনে প্রতিটি ধাপে `git clean -fdx` (⚠️ untracked file মুছে দেয়) বা আলাদা build directory ব্যবহার করুন।

### 9.4 দৈনন্দিন উদ্ধার-command (Ubuntu-তে একই)

```bash
git reflog -20                            # প্রথম কাজ: কোথায় ছিলাম
git branch rescue HEAD@{3}                # নিরাপদ উদ্ধার: আগে branch, পরে সিদ্ধান্ত
git reset --soft HEAD~1                   # শেষ commit বাতিল, পরিবর্তন staged থাকে
git commit --amend                        # শেষ commit-এর message/content ঠিক (push-এর আগে)
git revert <sha>                          # shared branch-এ
git revert -m 1 <merge-sha>               # merge commit revert
git stash push -m "wip"; git stash list; git stash pop
git restore --staged file; git restore file
git fsck --no-reflogs | grep dangling     # শেষ চেষ্টা
git config --global gc.reflogExpire 180.days   # (ঐচ্ছিক) বেশিদিন মনে রাখা
```

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l03_05.py`](code/L03-05/test_l03_05.py)-এর ৭টি test:

- **`lost_commits.py`:** কিছু না হারালে খালি ফল; `reset --hard`-এ একটি tip; মুছে ফেলা branch ও rescue-এর পরে আবার খালি; `reflog expire`-এর পরে `fsck`-এ পাওয়া; exit code ০/১/২।
- **Demo script:** `bisect_demo.sh` → change 21 ও ৫ ধাপ; `recovery_demo.sh` → branch উদ্ধার ও revert।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `git log -g --all` | সব ref-এর reflog | একটি branch-এর reflog নয়, সব জায়গায় খোঁজা |
| `rev-list --all` | বর্তমানে পৌঁছানো commit | "Lost" = reflog-এ আছে − পৌঁছানো যায় |
| Tip filter (`merge-base --is-ancestor`) | পূর্বপুরুষ বাদ | একটি branch-ই পুরো চেইন উদ্ধার করে |
| `fsck --no-reflogs` "dangling" | Reflog-এর বাইরের tip | `--unreachable` দিলে পুরো চেইন আসত |
| শুধু command ছাপে, চালায় না | — | উদ্ধারের সিদ্ধান্ত মানুষের; tool read-only |
| Demo-তে Python খোঁজা যাচাইসহ | `python3 -c 'import sys'` | Windows-এ Microsoft Store-এর `python3` stub চলে না — demo লেখার সময় আসলে ধরা পড়েছে |
| Bisect-এ `python -B` | Bytecode cache নয় | Section 9.3-এর ভুল ফল |

**Python কেন এখানে, কোথায় নয়:** reflog ও fsck-এর output মেলানো, tip বের করা ও রিপোর্ট করা script-এর কাজ। উদ্ধার নিজে `git branch` বা `git reset` দিয়ে করুন — একটি command, পূর্ণ নিয়ন্ত্রণ।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `recovery_demo.sh` | তিনটি দুর্ঘটনা ও উদ্ধার, Section 9.1-এর hash |
| Reflog expire-এর পরে `--fsck` | একটি dangling tip |
| `bisect_demo.sh` | `change 21`, ৫ ধাপ |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom / ভুল | কেন সমস্যা | সঠিক পদ্ধতি |
|---|---|---|
| আতঙ্কে repository মুছে আবার clone | Local reflog ও অপুশড commit চিরতরে হারায় | আগে `git reflog` |
| Shared branch-এ `reset` + force push | অন্যদের history ভাঙে | `revert` |
| `reset --hard` দিয়ে "পরিষ্কার" | Commit না করা কাজ ফেরানো যায় না | আগে `git stash` বা commit |
| Bisect অদ্ভুত ফল দেয় | Test deterministic নয় / cache | Clean build, `-B`, flaky test ঠিক করা |
| Bisect শেষে detached HEAD | `bisect reset` ভুলে যাওয়া | `git bisect reset` |
| Merge revert করতে গিয়ে error | Parent নির্দিষ্ট নয় | `git revert -m 1 <merge>` |
| Revert-এর পরে branch আবার merge করলে পরিবর্তন আসে না | Git মনে করে আগেই merge হয়েছে | "Revert the revert" (`git revert <revert-sha>`) |
| `HEAD@{1}` shell-এ কাজ করে না | Brace expansion (কিছু shell-এ) | Quote: `'HEAD@{1}'` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Secret commit হলে reset বা revert যথেষ্ট নয় — blob history ও অন্যদের clone-এ থাকে। **Rotate করুন** (L03-01)।
  - Force push ও reflog expire প্রমাণ মুছে দিতে পারে, তাই protected branch চালু রাখুন এবং server-side audit log দেখুন।
  - Revert-ভিত্তিক rollback audit trail রাখে, যা compliance-এর জন্য প্রয়োজন।
- **Performance:**
  - Bisect O(log n) — test যত দ্রুত, তত দ্রুত উত্তর।
  - বড় repository-তে bisect-এ build সময়ই প্রধান খরচ — CI-র build artifact cache ব্যবহার করুন (সঠিক cache key সহ!)।
- **Cost:**
  - দ্রুত সঠিক root cause = কম MTTR (L00-01)।
  - Rollback ও revert-এর প্রক্রিয়া আগে থেকে অনুশীলন করা থাকলে incident-এর সময় ভুলের খরচ কমে।

## 14. Hands-on exercise

1. Demo repository-তে `git rebase -i` দিয়ে দুটি commit squash করুন, তারপর reflog দিয়ে rebase-এর আগের অবস্থায় ফিরুন (`ORIG_HEAD` বা `HEAD@{n}`)।
2. একটি file edit করে `git add` করুন (commit নয়), তারপর `reset --hard`। `git fsck --lost-found`-এর পরে `.git/lost-found/other/`-এ content খুঁজে পান কি? File-এর নাম আছে কি?
3. `bisect_demo.sh`-এর test থেকে `-B` সরিয়ে কয়েকবার চালান — ভুল ফল পুনরুৎপাদন হয় কি? (সময়ের উপর নির্ভর করে — কেন?)
4. `lost_commits.py`-তে `--since 7.days` option যোগ করুন, যাতে শুধু সাম্প্রতিক reflog entry দেখায়। Test লিখুন।
5. একটি merge commit তৈরি করে `git revert -m 1` করুন, তারপর feature branch-এ নতুন commit যোগ করে আবার merge করুন — কী হয়? "Revert the revert" দিয়ে সমাধান করুন।

## 15. Mini-project — "Git emergency" runbook

`runbooks/`-এ একটি runbook, প্রতিটি পরিস্থিতির জন্য symptom → প্রথম read-only command → উদ্ধার → যাচাই:

- ভুল reset
- মুছে ফেলা branch
- ভুল rebase
- Force push-এ হারানো commit
- Commit হওয়া secret
- Production regression (bisect + revert)

শুরুতে একটি বড় অক্ষরের নিয়ম: "কিছু মোছার আগে `git branch backup/<তারিখ>`"। Module 03-এর Lab C এই runbook ব্যবহার করবে।

## 16. Interview প্রশ্ন

1. `git reset --soft`, `--mixed` ও `--hard`-এর পার্থক্য কী?
2. Reset ও revert-এর পার্থক্য; production branch-এ কোনটি এবং কেন?
3. "হারানো" commit কীভাবে উদ্ধার করবেন? কখন তা সম্ভব নয়?
4. Reflog কী, এবং এর সীমাবদ্ধতা কী?
5. `git bisect` কীভাবে কাজ করে? কীভাবে স্বয়ংক্রিয় করবেন?
6. Bisect ভুল commit দেখালে কী কী কারণ থাকতে পারে?
7. Merge commit কীভাবে revert করবেন?

## 17. Self-assessment প্রশ্ন

1. Dashcam analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 9.1-এ দুটি commit হারালেও tool একটি দেখাল কেন?
3. Branch মুছে ফেলার পরে তার reflog কোথায় যায়, এবং commit কোথায় পাওয়া গেল?
4. Section 9.3-এ bisect প্রথমে কেন ভুল ফল দিয়েছিল?
5. কোন পরিস্থিতিতে কাজ সত্যিই হারায়?

## 18. সংক্ষিপ্ত সারাংশ

- Commit করা কাজ প্রায় কখনো সাথে সাথে হারায় না — reflog (local, মেয়াদসহ), তারপর `fsck`, gc পর্যন্ত।
- `reset --hard` শুধু commit না করা কাজের জন্য সত্যিই বিপজ্জনক। ঝুঁকির আগে commit, stash বা backup branch রাখুন।
- Shared history-তে `revert`, local-এ `reset`।
- Bisect = binary search; deterministic, cache-মুক্ত test সহ `bisect run`।
- আতঙ্কে মুছবেন না — আগে `git reflog`, তারপর `git branch rescue`।

## 19. Completion checklist

- [ ] `recovery_demo.sh`-এর তিনটি উদ্ধার নিজে বুঝে চালিয়েছি
- [ ] Reflog expire-এর পরে `fsck` দিয়ে উদ্ধার দেখেছি
- [ ] `bisect run` দিয়ে দায়ী commit খুঁজেছি এবং cache-এর ফাঁদ বুঝেছি
- [ ] Merge commit revert করেছি (Exercise ৫)
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `git-reflog(1)`: https://git-scm.com/docs/git-reflog
- `git-reset(1)`: https://git-scm.com/docs/git-reset
- `git-revert(1)`: https://git-scm.com/docs/git-revert
- `git-bisect(1)`: https://git-scm.com/docs/git-bisect
- `git-fsck(1)`: https://git-scm.com/docs/git-fsck
- `git-restore(1)`: https://git-scm.com/docs/git-restore
- Pro Git — Reset Demystified: https://git-scm.com/book/en/v2/Git-Tools-Reset-Demystified
- Pro Git — Data Recovery: https://git-scm.com/book/en/v2/Git-Internals-Maintenance-and-Data-Recovery
- Python — cached bytecode invalidation: https://docs.python.org/3/reference/import.html#cached-bytecode-invalidation

---

**পরের lesson:** L03-06 — GitHub Actions fundamentals
