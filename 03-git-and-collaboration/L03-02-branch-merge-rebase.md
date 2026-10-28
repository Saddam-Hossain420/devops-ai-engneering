# L03-02 — Branch, merge ও rebase

| | |
|---|---|
| **Module** | 03 — Git and Collaboration |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L03-01 — Git internals](L03-01-git-internals.md) |
| **Label** | — |
| **Tested** | `graph.py` ও `conflict_markers.py`: ৭টি test পাস — merge base ও ahead/behind **আসল `git merge-base --all` ও `git rev-list --left-right --count`-এর সাথে মেলানো**, fast-forward, diverged এবং criss-cross history (দুটি merge base), conflict marker (diff3 style সহ, markdown underline-এ false positive নেই) (Python 3.14, Git 2.54, Windows/Git Bash)। `merge_vs_rebase.sh` demo আসলে চালানো — author/তারিখ নির্দিষ্ট বলে hash যেকোনো machine-এ একই। Ubuntu-তে চালানো হয়নি (OS-নির্ভর অংশ নেই)। |

---

## 1. এই lesson-এ যা শিখবেন

- Branch ও `HEAD` commit graph-এ কীভাবে সরে।
- **Fast-forward**, **three-way merge** ও **merge base**।
- **Rebase**: commit "নতুন করে বসানো" — কেন hash বদলায়, এবং **shared branch-এ rebase নয়** নিয়ম।
- Merge বনাম rebase বনাম squash — কখন কোনটি।
- **Conflict** কেন হয়, marker কীভাবে পড়বেন, নিরাপদে সমাধান ও `--abort`।
- Trunk-based development ও ছোট, স্বল্পস্থায়ী branch-এর গুরুত্ব।
- Python দিয়ে merge base হিসাব ও CI-তে conflict marker ধরা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একাধিক মানুষ (ও CI bot, dependency updater, AI agent) একই code-এ একসাথে কাজ করেন। Branch প্রত্যেককে আলাদা জায়গা দেয়; merge/rebase সেই কাজ আবার একত্র করে।

ভুল বোঝাপড়ার পরিণতি:

- Shared branch-এ rebase করে force push → সহকর্মীর commit "হারিয়ে গেছে", তাঁর local history অমিল (L03-05-এ উদ্ধার)।
- Conflict marker (`<<<<<<<`) ভুলে commit হয়ে production config ভেঙেছে।
- সপ্তাহব্যাপী দীর্ঘ feature branch → merge-এর দিন শত শত conflict, ভুল সমাধান, bug।
- "Merge commit আবর্জনা" বনাম "rebase বিপজ্জনক" নিয়ে team-এর অনন্ত বিতর্ক — অথচ নিয়ম সরল।

## 3. সহজ ভাষায় পরিচয়

L03-01 থেকে: branch = একটি commit-এর নাম; `HEAD` = "আমি এখন কোন branch-এ"। নতুন commit করলে **বর্তমান branch-এর নাম সামনে সরে**।

**Merge-এর তিন পরিস্থিতি** (`git merge feature`, main-এ দাঁড়িয়ে):

| পরিস্থিতি | কী ঘটে | ফল |
|---|---|---|
| main feature-এর পূর্বপুরুষ (main সরেনি) | **Fast-forward** — main-এর নাম feature-এর জায়গায় সরে | নতুন commit নেই, সরল রেখা |
| দুই branch-ই সরেছে (diverged) | **Three-way merge** — merge base, main ও feature তিনটি তুলনা | দুই parent-যুক্ত **merge commit** |
| একই লাইন দুই দিকে বদলেছে | **Conflict** — Git সিদ্ধান্ত নিতে পারে না | মানুষকে সমাধান করতে হয় |

**Rebase** (`git rebase main`, feature-এ দাঁড়িয়ে): feature-এর প্রতিটি commit-এর **পরিবর্তন** main-এর মাথার উপর একে একে আবার প্রয়োগ করে **নতুন commit** তৈরি — তারপর feature-এর নাম নতুন শেষ commit-এ সরে। ফল: সরল ইতিহাস, কিন্তু **নতুন hash**।

| | Merge | Rebase | Squash merge |
|---|---|---|---|
| History | যেমন ঘটেছে তেমন (শাখাসহ) | সরল রেখা, যেন পরপর লেখা | Feature-এর সব commit একটি commit-এ |
| পুরোনো commit-এর hash | অপরিবর্তিত | **বদলায়** | Feature-এর commit main-এ আসে না |
| Shared branch-এ নিরাপদ? | হ্যাঁ | **না** (force push লাগে) | হ্যাঁ (main-এ) |
| Revert | Merge commit revert (`-m 1`) | প্রতিটি commit আলাদা | একটি commit revert — সহজ |

**সোনালি নিয়ম:** যে commit অন্যরা ইতিমধ্যে নিয়েছেন (push করা shared branch), সেটি rebase/amend করবেন না। নিজের local, push-না-করা বা শুধু নিজের branch rebase করা নিরাপদ।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### একটি যৌথ রেসিপি বই

- **Branch** = বইয়ের একটি photocopy নিয়ে নিজের পরীক্ষা — মূল বই অপরিবর্তিত।
- **Fast-forward** = আপনি copy নিয়ে কাজ করার সময় কেউ মূল বইয়ে কিছু লেখেননি — আপনার পাতাগুলোই এখন মূল বইয়ের পরের পাতা।
- **Merge** = দুজনেই নতুন পাতা লিখেছেন; সম্পাদক একটি "একত্রীকরণ পাতা" যোগ করেন যেখানে লেখা "এই দুই ধারা এখানে মিলল"।
- **Rebase** = আপনি নিজের পাতাগুলো মূল বইয়ের সর্বশেষ পাতার পরে **আবার নতুন করে লেখেন** — বিষয়বস্তু একই, কিন্তু নতুন কাগজ, নতুন পৃষ্ঠা নম্বর।
- **Conflict** = দুজনেই একই রেসিপির লবণের পরিমাণ বদলেছেন — সম্পাদককে বেছে নিতে হবে।

### Analogy কোথায় মেলে না

- কাগজে আবার লিখলে পুরোনো পাতা থেকে যায় কেউ ফেলে না দিলে। Git-এ rebase-এর পরে পুরোনো commit-গুলো নামহীন হয় — reflog-এ কিছুদিন থাকে, তারপর garbage collection মুছে দেয় (L03-05)।
- রেসিপির "conflict" মানুষ অর্থ বুঝে মেলান। Git **শুধু লাইন** তুলনা করে — conflict ছাড়া merge হলেও অর্থগত বিরোধ থাকতে পারে (একজন function-এর নাম বদলালেন, অন্যজন পুরোনো নামে নতুন call যোগ করলেন — Git খুশি, build ভাঙা)। তাই merge-এর পরে **CI test** অপরিহার্য।
- বই একটি; repository-র অনেক copy (প্রত্যেকের clone) — rebase করা branch push করলে অন্যদের copy-র সাথে ইতিহাস মেলে না (L03-03)।

## 5. Real-world engineering scenario — "Force push-এর পরে সহকর্মীর কাজ উধাও"

**পরিস্থিতি:** রিয়া ও তানভীর একই `feature/payments` branch-এ কাজ করছেন। রিয়া main-এর সাথে মেলাতে `git rebase main` করে `git push --force` দিলেন। তানভীর এর মধ্যে দুটি commit push করেছিলেন — সেগুলো রিয়ার local branch-এ ছিল না, তাই force push remote থেকে মুছে দিল। পরে তানভীর `git pull` করে অদ্ভুত duplicate commit ও conflict পেলেন।

**কী ভুল:**

1. Shared branch-এ rebase (সোনালি নিয়ম ভাঙা)।
2. `--force` অন্যের কাজ যাচাই না করে overwrite করে।

**উদ্ধার:** তানভীরের local clone-এ তাঁর commit আছে (`git reflog`) — সেখান থেকে push (L03-05)। Server-এর ref log বা অন্য কারো clone-ও উৎস হতে পারে।

**প্রতিরোধ:**

- Shared branch-এ merge (`git pull --no-rebase` বা `git merge main`); অথবা প্রত্যেকে নিজের branch।
- Force দরকার হলে **`git push --force-with-lease`** — remote branch আপনার শেষ দেখা অবস্থা থেকে বদলে গেলে push প্রত্যাখ্যান করে।
- `main`-এ protected branch: force push নিষেধ (L03-04)।
- ছোট, স্বল্পস্থায়ী branch (এক-দুই দিন) — rebase/merge-এর দরকার ও ঝুঁকি দুটোই কমে।

**শিক্ষা:** Rebase নিজের ইতিহাস গোছানোর tool; ভাগ করা ইতিহাস পুনর্লিখনের tool নয়।

## 6. Diagram — demo-র তিনটি ফল

```text
শুরু (তিনটিতেই একই hash):   A(594043c) ─ B(f3fd872)            ← main
                                           └─ F1(16f42be) ─ F2(219ed10)   ← feature

১. Fast-forward (main সরেনি):
   A ─ B ─ F1(16f42be) ─ F2(219ed10)   ← main, feature            (নতুন commit নেই)

২. Merge (main-এ C যোগ হয়েছে):
   A ─ B ─ C(ce1da30) ───────────── M(b0619e3)   ← main  (দুই parent)
         └─ F1(16f42be) ─ F2(219ed10) ─┘          ← feature   (F1, F2 অপরিবর্তিত)

৩. Rebase তারপর fast-forward:
   A ─ B ─ C(ce1da30) ─ F1'(f12de0f) ─ F2'(d26332e)   ← main, feature
                        (একই পরিবর্তন, নতুন hash; পুরোনো 16f42be/219ed10 এখন নামহীন)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Branch | Commit-এর চলমান নাম |
| HEAD | বর্তমান branch/commit |
| Fast-forward | শুধু নাম সামনে সরানো |
| Merge base | দুই branch-এর সর্বশেষ সাধারণ পূর্বপুরুষ |
| Three-way merge | Base + দুই প্রান্ত তুলনা করে একত্রীকরণ |
| Merge commit | দুই (বা বেশি) parent-যুক্ত commit |
| Rebase | Commit-গুলো অন্য base-এর উপর নতুন করে প্রয়োগ |
| Interactive rebase | `rebase -i` — squash, reorder, edit (শুধু নিজের branch-এ) |
| Squash merge | Branch-এর সব পরিবর্তন একটি commit-এ |
| Cherry-pick | একটি commit-এর পরিবর্তন অন্য branch-এ প্রয়োগ |
| Conflict | একই অংশে দুই দিকে পরিবর্তন |
| `--force-with-lease` | Remote না বদলালেই force push |
| Trunk-based development | ছোট branch, ঘন ঘন main-এ merge |
| Criss-cross merge | দুই branch পরস্পরকে merge করেছে — একাধিক merge base |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Three-way merge

Git তিনটি সংস্করণ নেয়: **base** (merge base), **ours** (বর্তমান branch), **theirs** (যা merge হচ্ছে)। প্রতিটি অংশে:

| base | ours | theirs | ফল |
|---|---|---|---|
| X | X | X | X |
| X | Y | X | Y (শুধু আমরা বদলেছি) |
| X | X | Z | Z (শুধু ওরা বদলেছে) |
| X | Y | Y | Y (দুজনে একই বদল) |
| X | Y | Z | **Conflict** |

তাই merge base গুরুত্বপূর্ণ — base ছাড়া Git জানত না কে কী বদলেছে। এই lesson-এর `graph.py` merge base বের করে: দুই branch-এর common ancestor-দের মধ্যে যারা অন্য কোনো common ancestor-এর পূর্বপুরুষ নয়। Criss-cross history-তে এমন দুটি হতে পারে; Git তখন সেগুলো আগে নিজেরা merge করে একটি virtual base বানায় (`ort` strategy)।

### 8.2 Conflict marker

```text
<<<<<<< HEAD
line2 from main          ← ours (আপনি যে branch-এ আছেন)
=======
line2 from feature       ← theirs
>>>>>>> feature
```

`git config merge.conflictStyle zdiff3` দিলে মাঝে `|||||||` অংশে base-ও দেখায় — "আগে কী ছিল" জানলে সঠিক সমাধান সহজ।

**সমাধানের ধাপ:** `git status` (কোন file) → file edit করে marker মুছে সঠিক content → test চালান → `git add file` → `git commit` (merge) বা `git rebase --continue`। আটকে গেলে `git merge --abort` / `git rebase --abort` — সব শুরুর অবস্থায় ফেরে।

**Rebase-এ ours/theirs উল্টো!** Rebase-এর সময় "ours" = যে base-এর উপর বসানো হচ্ছে (main), "theirs" = আপনার commit — বিভ্রান্তির প্রচলিত উৎস।

### 8.3 Rebase কেন hash বদলায়

Commit-এর hash-এ parent-এর hash আছে (L03-01)। F1-এর parent B থেকে C হলে F1-এর content একই থাকলেও hash নতুন — F1'। তাই পুরো চেইন নতুন। Demo-তে: `219ed10` → `d26332e`।

### 8.4 Branching strategy (সংক্ষেপে)

- **Trunk-based:** main সবসময় deploy-যোগ্য; feature branch ঘণ্টা/দিনের; অসম্পূর্ণ feature **feature flag**-এর পেছনে। Continuous delivery-র জন্য প্রস্তাবিত (DORA গবেষণা, L00-01)।
- **GitFlow:** develop/release/hotfix branch — নির্দিষ্ট release চক্রের software-এ; জটিল, দীর্ঘস্থায়ী branch-এ merge ব্যথা।
- এই repository Module 06-এ trunk-based + PR + CI ব্যবহার করবে (L03-04)।

## 9. Practical demonstration

### 9.1 Merge বনাম rebase — একই শুরু, তিন ফল

File: [`code/L03-02/merge_vs_rebase.sh`](code/L03-02/merge_vs_rebase.sh) (নির্দিষ্ট author/তারিখ; global config ছাড়া)।

```bash
cd ~/devops-ai-engineering/03-git-and-collaboration/code/L03-02
bash merge_vs_rebase.sh /tmp/merge-demo
```

**আসল output:**

```text
== 1. fast-forward (main has not moved)
* 219ed10 F2: feature part 2
* 16f42be F1: feature part 1
* f3fd872 B: add readme
* 594043c A: initial

== 2. merge commit (main moved: C)
*   b0619e3 Merge branch 'feature'
|\
| * 219ed10 F2: feature part 2
| * 16f42be F1: feature part 1
* | ce1da30 C: docs on main
|/
* f3fd872 B: add readme
* 594043c A: initial

== 3. rebase feature onto main, then fast-forward
   feature before rebase: 219ed10
   feature after rebase:  d26332e  (new commits, same changes)
* d26332e F2: feature part 2
* f12de0f F1: feature part 1
* ce1da30 C: docs on main
* f3fd872 B: add readme
* 594043c A: initial

== 4. conflict: both branches change line2
Auto-merging app.txt
CONFLICT (content): Merge conflict in app.txt
Automatic merge failed; fix conflicts and then commit the result.
--- app.txt during conflict:
line1
<<<<<<< HEAD
line2 from main
=======
line2 from feature
>>>>>>> feature
line3
UU app.txt
--- after git merge --abort: 0 changed file(s)
```

**তুলনা করুন:** F1/F2 merge-এ `16f42be`/`219ed10`-ই থাকে; rebase-এ `f12de0f`/`d26332e` — একই পরিবর্তন, নতুন commit। Rebase-এর পরে main-এ merge শুধু fast-forward। `UU` = দুই দিকেই পরিবর্তিত (unmerged)।

### 9.2 দুই branch-এর সম্পর্ক

File: [`code/L03-02/graph.py`](code/L03-02/graph.py) — scenario ২-এ merge-এর আগে রাখা tag `before-merge` দিয়ে:

```bash
python3 graph.py before-merge feature --repo /tmp/merge-demo/merged
python3 graph.py main feature --repo /tmp/merge-demo/merged
```

**আসল output:**

```text
feature is 2 commit(s) ahead and 1 behind before-merge
merge base: f3fd8720dd
diverged: needs a merge commit or a rebase of source onto target

feature is 0 commit(s) ahead and 2 behind main
merge base: 219ed1054f
already up to date: target contains source
```

Merge base `f3fd872` = commit B — diagram-এর শাখা বিন্দু। Merge-এর পরে feature-এর মাথা নিজেই merge base (main-এ অন্তর্ভুক্ত)। Git-এর নিজস্ব সমতুল্য: `git merge-base main feature`, `git rev-list --left-right --count feature...main`, `git status -sb` ("ahead 2, behind 1")।

### 9.3 Conflict marker CI check

```bash
python3 conflict_markers.py $(git ls-files)     # যেকোনো repository-তে; exit 1 = marker পাওয়া গেছে
```

`git diff --check`-ও marker ধরে; CI-তে (L03-06) পুরো file-এ একটি check রাখা নিরাপদ জাল।

### 9.4 দৈনন্দিন command (Ubuntu-তে একই)

```bash
git switch -c feature/login            # নতুন branch তৈরি ও সেখানে যাওয়া
git log --oneline --graph --all -15    # পুরো graph
git merge --ff-only feature            # শুধু fast-forward, নইলে ব্যর্থ — নিরাপদ default
git merge --no-ff feature              # সবসময় merge commit (feature-এর সীমানা রাখতে)
git rebase main                        # নিজের branch-এ
git rebase -i HEAD~3                   # নিজের শেষ ৩টি commit গোছানো (push-এর আগে)
git pull --rebase                      # নিজের local commit remote-এর উপরে
git push --force-with-lease            # rebase-এর পরে নিজের branch-এ — শুধু --force নয়
git config --global merge.conflictStyle zdiff3
git config --global rerere.enabled true   # একই conflict-এর সমাধান মনে রাখে
```

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l03_02.py`](code/L03-02/test_l03_02.py)-এর ৭টি test: conflict marker (সাধারণ ও diff3), markdown-এর `=======` underline-এ false positive নেই, এবং temporary repository-তে আসল git-এর সাথে তুলনা: fast-forward, diverged, **criss-cross-এ দুটি merge base**, CLI।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `load_graph` | `git rev-list --all --parents` | Graph পেতে plumbing — `.git` নিজে parse না করে |
| `ancestors` (BFS) | পূর্বপুরুষের set | Merge base ও ahead/behind-এর ভিত্তি |
| `merge_bases` redundant বাদ | Best common ancestor | Criss-cross-এ একাধিক — test-এ git-এর সাথে মিলেছে |
| `advice` | up to date / fast-forward / diverged | `--ff-only` ব্যর্থ হবে কিনা আগে জানা |
| `conflict_markers` ঠিক ৭ অক্ষর ও ক্রম | `=======` শুধু খোলা marker-এর পরে | Markdown heading underline-এ ভুল সতর্কতা নয় |
| Binary file বাদ | প্রথম 8 KB-তে NUL | Image ইত্যাদিতে অর্থহীন match |

**Python কেন এখানে, কোথায় নয়:** graph algorithm বোঝা ও CI check-এ ভালো। বড় repository-তে পুরো graph memory-তে আনা ধীর — বাস্তবে `git merge-base`, `git rev-list`, commit-graph file।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `merge_vs_rebase.sh` | Section 9.1-এর hash হুবহু |
| `graph.py before-merge feature` | ahead 2, behind 1, diverged |
| Conflict-এর পরে `git merge --abort` | `git status` পরিষ্কার |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `fatal: Not possible to fast-forward, aborting.` | Branch diverged | Merge বা rebase সিদ্ধান্ত নিন (`graph.py`) |
| Push প্রত্যাখ্যাত: `non-fast-forward` | Remote-এ নতুন commit | `git pull --rebase` (নিজের branch) বা merge; **`--force` নয়** |
| Rebase-এর পরে push প্রত্যাখ্যাত | History বদলেছে | নিজের branch হলে `--force-with-lease` |
| Conflict সমাধানের পরে build ভাঙা | Marker থেকে গেছে বা ভুল অংশ রাখা | `conflict_markers.py`, test |
| একই conflict বারবার (বারবার rebase-এ) | দীর্ঘ branch | `rerere`; ছোট branch |
| "Merge-এর পরে আমার পরিবর্তন নেই" | Conflict-এ ভুল দিক বেছে নেওয়া (rebase-এ ours/theirs উল্টো) | `git log -p`, reflog থেকে উদ্ধার (L03-05) |
| Merge commit revert করতে `-m` চাইছে | কোন parent-কে মূল ধরবে | `git revert -m 1 <merge>` (সাধারণত main) |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Protected branch-এ force push বন্ধ, merge শুধু review ও CI পাসের পরে (L03-04); merge-এ কেউ চুপচাপ ক্ষতিকর পরিবর্তন লুকাতে পারে ("evil merge") — merge commit-এর diff-ও review করুন (`git show --cc`); rebase-এর পরে signed commit-এর signature নতুন করে করতে হয়।
- **Performance:** ছোট, ঘন ঘন merge = কম conflict, কম review সময়; বড় monorepo-তে merge queue (CI ক্রমানুসারে চালায়)।
- **Cost:** দীর্ঘ branch-এর merge ব্যথা মানে engineer-ঘণ্টা ও deploy বিলম্ব — DORA-র lead time (L00-01) বাড়ায়।

## 14. Hands-on exercise

1. Demo-র conflict repository-তে conflict নিজে সমাধান করুন (দুটি পরিবর্তনই রাখুন), commit করুন; `git log --graph` ও `git show --cc HEAD` দেখুন।
2. একই conflict `rebase` দিয়ে করুন — ours/theirs কোনটি কী, লিখে রাখুন।
3. `git rebase -i` দিয়ে demo-র F1 ও F2 একটি commit-এ squash করুন (নিজের local branch-এ)।
4. `graph.py`-তে `--json` output যোগ করুন এবং `check-ff` mode: fast-forward সম্ভব না হলে exit 1 — CI-তে "branch outdated" check হিসেবে। Test লিখুন।
5. Section 5 নিজে পুনরুৎপাদন করুন: একটি bare repository (L03-03-এর preview) ও দুটি clone; একটিতে rebase + `--force`, অন্যটিতে `--force-with-lease` — পার্থক্য লিখুন।

## 15. Mini-project — Team branching policy

এক পাতার `CONTRIBUTING`-অংশ: branch নামকরণ (`feat/`, `fix/`), branch-এর সর্বোচ্চ আয়ু, merge পদ্ধতি (squash নাকি merge commit — কারণসহ), rebase-এর নিয়ম (শুধু নিজের branch, `--force-with-lease`), conflict সমাধানের checklist, এবং `conflict_markers.py` ও `graph.py check-ff`-কে pre-push hook হিসেবে। L03-04-এ protected branch ও CODEOWNERS এর সাথে যুক্ত হবে।

## 16. Interview প্রশ্ন

1. Merge ও rebase-এর পার্থক্য; কখন কোনটি ব্যবহার করবেন?
2. Fast-forward merge কী?
3. Merge base কী এবং three-way merge-এ এর ভূমিকা কী?
4. Rebase কেন commit hash বদলায়?
5. Shared branch-এ rebase কেন বিপজ্জনক? `--force-with-lease` কী সমাধান করে?
6. Merge conflict কীভাবে সমাধান করবেন? সমাধানের পরে কী যাচাই করবেন?
7. Trunk-based development বনাম GitFlow।

## 17. Self-assessment প্রশ্ন

1. রেসিপি বই analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Demo-তে F2-এর hash merge-এ ও rebase-এ কী? কেন ভিন্ন?
3. Three-way merge table-এর কোন সারিতে conflict হয়?
4. Rebase চলাকালীন "ours" কে?
5. Section 5-এর তিনটি প্রতিরোধ ব্যবস্থা।

## 18. সংক্ষিপ্ত সারাংশ

- Branch = চলমান নাম; commit করলে বর্তমান branch সরে।
- Merge: fast-forward (নাম সরানো) বা three-way (merge base + দুই প্রান্ত → merge commit)।
- Rebase: পরিবর্তনগুলো নতুন base-এ নতুন commit হিসেবে — সরল history, নতুন hash।
- সোনালি নিয়ম: shared history rebase নয়; force দরকার হলে `--force-with-lease`।
- Conflict = একই অংশে দুই দিকের পরিবর্তন; সমাধানের পরে marker check ও test।
- ছোট, স্বল্পস্থায়ী branch = কম conflict, দ্রুত delivery।

## 19. Completion checklist

- [ ] Demo চালিয়ে তিনটি ফলের hash ব্যাখ্যা করতে পারি
- [ ] একটি conflict merge ও rebase দুইভাবে সমাধান করেছি
- [ ] `--force-with-lease`-এর আচরণ নিজে দেখেছি (Exercise ৫)
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Pro Git — Basic Branching and Merging: https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging
- Pro Git — Rebasing: https://git-scm.com/book/en/v2/Git-Branching-Rebasing
- `git-merge(1)`: https://git-scm.com/docs/git-merge
- `git-rebase(1)`: https://git-scm.com/docs/git-rebase
- `git-merge-base(1)`: https://git-scm.com/docs/git-merge-base
- `git-rerere(1)`: https://git-scm.com/docs/git-rerere
- Trunk Based Development: https://trunkbaseddevelopment.com/

---

**পরের lesson:** L03-03 — Remote, tag ও semantic versioning
