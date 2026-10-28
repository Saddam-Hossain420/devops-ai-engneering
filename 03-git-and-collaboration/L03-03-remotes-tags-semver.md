# L03-03 — Remote, tag ও semantic versioning

| | |
|---|---|
| **Module** | 03 — Git and Collaboration |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L03-02 — Branch, merge ও rebase](L03-02-branch-merge-rebase.md) |
| **Label** | — |
| **Tested** | `semver.py`: ৮টি test পাস — semver.org-এর precedence উদাহরণ হুবহু, numeric তুলনা, build metadata উপেক্ষা, অবৈধ version প্রত্যাখ্যান, bump, Conventional Commits শ্রেণিবিভাগ, 0.x নিয়ম, এবং temporary repository-তে আসল `git` tag থেকে পরের version (Python 3.14, Git 2.54, Windows/Git Bash)। `remote_demo.sh` আসলে চালানো — local bare repository-কে remote ধরে, network ছাড়া। GitHub-এর মতো আসল hosted remote ও SSH key দিয়ে push **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- **Remote** কী: অন্য একটি repository-র ঠিকানা + নাম (`origin`)।
- **Remote-tracking branch** (`origin/main`) — remote-এর অবস্থার আপনার local "শেষ দেখা" ছবি।
- `fetch` বনাম `pull` বনাম `push`; **non-fast-forward** rejection কেন হয়।
- **Tag**: lightweight বনাম annotated; tag push; `git describe`।
- **Semantic Versioning** (MAJOR.MINOR.PATCH): কোন পরিবর্তনে কোনটি বাড়ে, pre-release, build metadata, precedence।
- **Conventional Commits** দিয়ে পরের version স্বয়ংক্রিয়ভাবে বের করা।
- HTTPS বনাম SSH remote এবং credential নিরাপত্তা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Git distributed — প্রত্যেকের কাছে পূর্ণ repository। দলগত কাজের জন্য একটি সাধারণ মিলনস্থল লাগে (GitHub, GitLab, নিজের server) — সেটাই remote। আর release-এর জন্য একটি অর্থবহ, তুলনাযোগ্য নাম লাগে — সেটাই version tag।

ভুল বোঝাপড়ার পরিণতি:

- "আমি pull করেছি, তবু পুরোনো code" — আসলে শুধু fetch হয়েছে, বা অন্য branch।
- Push প্রত্যাখ্যাত হলে `--force` — সহকর্মীর কাজ মুছে যায় (L03-02)।
- Version `1.10.0`-কে string sort-এ `1.9.0`-এর আগে রাখা — deploy script পুরোনো version বেছে নেয়।
- "Minor" release-এ breaking change — dependency হিসেবে ব্যবহারকারী সব service ভেঙে যায়।
- Tag local-এ তৈরি হলো কিন্তু push হলো না — CI release build কখনো চলল না।

## 3. সহজ ভাষায় পরিচয়

### Remote

```text
আপনার clone                                   origin (GitHub / bare repo)
  main            ──── git push ────►            main
  origin/main     ◄─── git fetch ────            (remote-এর আসল অবস্থা)
  (শেষ fetch-এর সময়কার ছবি — নিজে থেকে update হয় না)
```

| Command | কী করে | আপনার working tree বদলায়? |
|---|---|---|
| `git fetch` | Remote-এর নতুন object আনে, `origin/*` update | **না** |
| `git pull` | `fetch` + বর্তমান branch-এ merge (বা `--rebase`) | হ্যাঁ |
| `git push` | আপনার commit পাঠায় ও remote-এর branch সরায় | না |

Remote শুধু **fast-forward** push গ্রহণ করে: আপনার push-এর পরে remote branch-কে তার আগের commit-এর বংশধর হতে হবে। অন্য কেউ আগে push করলে আপনার push **rejected (non-fast-forward)** — আগে তাঁর কাজ আনুন।

### Tag

| | Lightweight | Annotated |
|---|---|---|
| কী | শুধু ref (commit-এর নাম) | নিজস্ব object (tagger, তারিখ, message, signature) |
| তৈরি | `git tag v1.0.0` | `git tag -a v1.0.0 -m "..."` (signed: `-s`) |
| ব্যবহার | ব্যক্তিগত চিহ্ন | **Release** |

Tag স্বয়ংক্রিয়ভাবে push হয় না: `git push origin v1.0.0` (বা `--follow-tags`)।

### Semantic Versioning — `MAJOR.MINOR.PATCH`

| বাড়ান | কখন | উদাহরণ |
|---|---|---|
| **MAJOR** | Breaking change — পুরোনো ব্যবহারকারী ভাঙবে | API endpoint মুছে ফেলা, config key-এর নাম বদল |
| **MINOR** | নতুন feature, backward-compatible | নতুন endpoint |
| **PATCH** | Bug fix, backward-compatible | crash ঠিক করা |

এবং:

- **Pre-release:** `1.0.0-rc.1` < `1.0.0`।
- **Build metadata:** `1.0.0+sha.bea3fb5` — precedence-এ উপেক্ষিত।
- **`0.y.z`:** প্রাথমিক উন্নয়ন — যেকোনো সময় যেকোনো কিছু বদলাতে পারে।

### Conventional Commits

Message-এর প্রথম লাইনে ধরন:

- `feat:` → MINOR
- `fix:` → PATCH
- `feat!:` বা footer-এ `BREAKING CHANGE:` → MAJOR
- `docs:`, `chore:`, `refactor:`, `test:` → release নয়

এভাবে tool নিজেই পরের version বের করতে পারে।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের shared drive ও প্রকাশনা

- **Remote** = অফিসের shared drive-এ রাখা মূল ফাইল; প্রত্যেকের laptop-এ একটি copy।
- **Fetch** = drive-এ কী নতুন আছে দেখে নিজের কাছে নামিয়ে রাখা, কিন্তু নিজের খসড়ায় এখনো না মেশানো।
- **Pull** = নামিয়ে নিজের খসড়ায় মিশিয়ে ফেলা।
- **Push rejected** = আপনি upload করতে গেলেন, কিন্তু অন্য কেউ ইতিমধ্যে নতুন সংস্করণ রেখেছেন — আগে তাঁরটা দেখুন।
- **Tag** = প্রকাশিত সংস্করণের ছাপা copy-তে "সংস্করণ ২.১" লেখা।
- **SemVer** = বইয়ের "দ্বিতীয় সংস্করণ" (বড় পরিবর্তন) বনাম "সংশোধিত মুদ্রণ" (ছাপার ভুল ঠিক)।

### Analogy কোথায় মেলে না

- Shared drive সবসময় সর্বশেষ দেখায়। `origin/main` **শুধু শেষ fetch-এর ছবি** — `git status`-এর "up to date" মানে "শেষ fetch অনুযায়ী" (demo-তে bob ঠিক এটাই দেখে)।
- Drive-এ একটি মূল কপি। Git-এ remote "মূল" শুধু রীতি অনুযায়ী — প্রযুক্তিগতভাবে সব clone সমান, এবং একাধিক remote থাকতে পারে (`origin`, `upstream`)।
- বইয়ের সংস্করণ নম্বর প্রকাশক যা খুশি দেন। SemVer একটি **চুক্তি** — "MINOR-এ কিছু ভাঙবে না"। ভাঙলে নম্বর মিথ্যা বলছে; dependency tool (`^1.4.0`, `~=1.4`) এই চুক্তির উপর ভর করে স্বয়ংক্রিয়ভাবে update নেয়।

## 5. Real-world engineering scenario — "Minor update-এ production ভাঙল"

**পরিস্থিতি:** একটি internal Python library `auth-client` `1.4.2` থেকে `1.5.0` হলো। Changelog-এ লেখা "new: token caching"। কিন্তু এই release-এ default timeout ৩০ থেকে ৫ সেকেন্ড করা হয়েছিল এবং একটি function-এর argument-এর নাম বদলানো হয়েছিল। যেসব service `auth-client>=1.4,<2` ব্যবহার করে, পরের deploy-এ সেগুলো স্বয়ংক্রিয়ভাবে `1.5.0` নিল। ফলে ধীর network-এ authentication timeout হলো, আর একটি service `TypeError`-এ crash করল।

**কারণ:** breaking change-কে minor হিসেবে release করা হয়েছিল। এটা মানুষের সিদ্ধান্ত — commit message-এ কোনো চিহ্ন ছিল না।

**সমাধান:**

1. তাৎক্ষণিক: `1.5.1`-এ পুরোনো আচরণ ফিরিয়ে আনা; পরিবর্তনগুলো `2.0.0`-এ।
2. Conventional Commits: `feat!:` বা `BREAKING CHANGE:` footer বাধ্যতামূলক (PR template ও commit lint, L03-04, L03-06)।
3. Version হাতে নয় — `semver.py next`-এর মতো tool commit message থেকে হিসাব করবে।
4. Consumer-রা lock file ব্যবহার করবে (Module 05), এবং dependency update হবে PR হিসেবে, CI test সহ।

**শিক্ষা:** Version নম্বর একটি প্রতিশ্রুতি। Breaking change চিনে নেওয়া ও ঘোষণা করা প্রক্রিয়ার অংশ হওয়া উচিত, স্মৃতির উপর নির্ভর করা নয়।

## 6. Diagram — demo-র remote প্রবাহ

```text
                 origin.git (bare)
            main: 482e464 → 29d2a9b → a1e74ef      tag v1.0.0 → a1e74ef
              ▲ push              ▲ push (rejected, তারপর সফল)
              │                   │
   alice ─────┘                   └───── bob
   482e464 feat: first version          clone (482e464)
   29d2a9b fix: correct output          fetch → origin/main = 29d2a9b, main এখনো 482e464 ("behind 1")
   tag v1.0.0                           commit "docs: add notes" (482e464-এর উপর) → push ✗ non-fast-forward
                                        pull --rebase → a1e74ef (29d2a9b-এর উপর) → push ✓
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Remote | অন্য repository-র নাম + URL |
| `origin` / `upstream` | Clone-এর উৎস / fork-এর মূল project (রীতি) |
| Remote-tracking branch | `origin/main` — remote-এর শেষ দেখা অবস্থা |
| Upstream (tracking) branch | Local branch কোন remote branch অনুসরণ করে |
| Fetch / pull / push | আনা / আনা+মেশানো / পাঠানো |
| Non-fast-forward | Push remote-এর commit মুছে দিত — প্রত্যাখ্যাত |
| Bare repository | Working tree ছাড়া repository (server-এর মতো) |
| Lightweight / annotated tag | শুধু নাম / নিজস্ব object |
| `git describe` | নিকটতম tag + দূরত্ব + hash: `v1.0.0-2-gd9e8a59` |
| SemVer | MAJOR.MINOR.PATCH চুক্তি |
| Pre-release / build metadata | `-rc.1` / `+sha.abc` |
| Conventional Commits | `feat:`, `fix:`, `feat!:` message রীতি |
| Version range | `^1.4.0`, `~=1.4`, `>=1.4,<2` |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Fetch ও refspec

`git fetch origin` remote-এর `refs/heads/*`-কে local `refs/remotes/origin/*`-এ কপি করে (configuration-এ `fetch = +refs/heads/*:refs/remotes/origin/*`)। শুধু object ও ref আসে; আপনার branch অপরিবর্তিত। `git status`-এর "ahead/behind" = আপনার branch বনাম `origin/main` (L03-02-এর `graph.py`-এর একই হিসাব)। মুছে যাওয়া remote branch-এর local ছবি পরিষ্কার করতে `git fetch --prune`।

### 8.2 Push-এর নিয়ম

Remote branch update হয় যদি নতুন commit পুরোনোটার বংশধর হয় (fast-forward)। না হলে rejected — যদি না `--force` দেওয়া হয়, যা remote-এর commit মুছে দেয়। `--force-with-lease` শুধু তখনই force করে যদি remote এখনো আপনার শেষ দেখা অবস্থায় থাকে। Server-side protected branch (L03-04) force push পুরোপুরি নিষেধ করে।

### 8.3 SemVer precedence

1. MAJOR, MINOR, PATCH — **সংখ্যা হিসেবে** তুলনা (`1.10.0 > 1.9.0`)।
2. একই হলে, pre-release থাকা version ছোট (`1.0.0-rc.1 < 1.0.0`)।
3. Pre-release-এর প্রতিটি অংশ বাম থেকে তুলনা হয়। সংখ্যা সংখ্যা হিসেবে তুলনা হয়, আর সংখ্যা সবসময় অক্ষরের চেয়ে ছোট। অংশ বেশি থাকলে বড় (`alpha < alpha.1`)।
4. Build metadata (`+…`) উপেক্ষিত।

Leading zero অবৈধ (`01.0.0`, `1.0.0-01`)। এই lesson-এর `semver.py` semver.org-এর প্রস্তাবিত regex ব্যবহার করে।

### 8.4 HTTPS বনাম SSH remote

- **SSH** (`git@github.com:org/repo.git`): L01-13-এর key; প্রতি machine আলাদা key, passphrase + agent; deploy key (শুধু একটি repository, read-only)।
- **HTTPS**: token (password নয়) + credential helper (OS keychain)। Token **কখনো URL-এ নয়** (`https://user:TOKEN@…`) — `.git/config` ও shell history-তে থেকে যায়।
- CI-তে short-lived token (GitHub Actions-এর `GITHUB_TOKEN`, OIDC — L03-06, Module 19)।

## 9. Practical demonstration

### 9.1 Remote প্রবাহ — network ছাড়া

File: [`code/L03-03/remote_demo.sh`](code/L03-03/remote_demo.sh) — একটি bare repository `origin.git` ও দুটি clone `alice`, `bob`। নির্দিষ্ট author/তারিখ ব্যবহার করে, global config ছাড়া।

```bash
cd ~/devops-ai-engineering/03-git-and-collaboration/code/L03-03
bash remote_demo.sh /tmp/remote-demo
```

**আসল output** (path অংশ ছোট করে দেখানো; hash যেকোনো machine-এ একই হওয়া উচিত):

```text
== remotes and tracking (bob)
origin	/tmp/remote-demo/origin.git (fetch)
origin	/tmp/remote-demo/origin.git (push)
* main 482e464 [origin/main] feat: first version

== alice pushes a fix; bob has not fetched yet
## main...origin/main
-- after git fetch (nothing in bob's working tree changes):
## main...origin/main [behind 1]
29d2a9b fix: correct output
482e464 feat: first version

== bob commits on his (fetched but not merged) main → push is rejected
To /tmp/remote-demo/origin.git
 ! [rejected]        main -> main (non-fast-forward)
error: failed to push some refs to '/tmp/remote-demo/origin.git'
-- bob: git pull --rebase, then push
a1e74ef docs: add notes
29d2a9b fix: correct output
482e464 feat: first version

== release tag
a1e74ef6c34d6cea213e4f16840515d10fca03aa	HEAD
a1e74ef6c34d6cea213e4f16840515d10fca03aa	refs/heads/main
538f0c7735bb6e7017a7be7c63411c2a009c40d1	refs/tags/v1.0.0
a1e74ef6c34d6cea213e4f16840515d10fca03aa	refs/tags/v1.0.0^{}
```

**পর্যবেক্ষণ:**

- Alice push করার পরেও bob-এর status-এ কোনো "behind" নেই, কারণ তার `origin/main` তখনো পুরোনো ছবি। Fetch-এর পরেই `[behind 1]` দেখায়।
- Fetch working tree-কে স্পর্শ করে না।
- Bob-এর push প্রত্যাখ্যাত হয়েছে, কারণ এটা alice-এর `29d2a9b` মুছে দিত। `pull --rebase`-এর পরে bob-এর commit `29d2a9b`-এর উপর বসেছে (নতুন hash `a1e74ef`), এবং push সফল।
- `ls-remote`-এ annotated tag দুইবার দেখা যায়: tag object নিজে (`538f0c7`), এবং `^{}` দিয়ে peeled রূপ, অর্থাৎ যে commit-কে নির্দেশ করে (`a1e74ef`, L03-01)।

### 9.2 SemVer precedence

File: [`code/L03-03/semver.py`](code/L03-03/semver.py)

```bash
python3 semver.py sort 1.0.0 1.10.0 1.9.0 1.0.0-rc.1 1.0.0-beta.11 1.0.0-beta.2 1.0.0-alpha
python3 semver.py compare 1.0.0+build.5 1.0.0+build.9
python3 semver.py compare 1.0 1.0.0; echo "exit=$?"
```

**আসল output:**

```text
1.0.0-alpha
1.0.0-beta.2
1.0.0-beta.11
1.0.0-rc.1
1.0.0
1.9.0
1.10.0
1.0.0+build.5 == 1.0.0+build.9
error: not a semantic version: '1.0'
exit=2
```

`beta.2 < beta.11` (সংখ্যা হিসেবে) ও `1.9.0 < 1.10.0` — সাধারণ string sort দুটোই উল্টো করত। `sort -V` (GNU coreutils) version sort করে, কিন্তু SemVer-এর pre-release নিয়ম পুরোপুরি মানে না।

### 9.3 পরের version — commit থেকে

```bash
python3 semver.py next --current 1.4.2 --message "fix: handle empty input" \
    --message "feat(api): add CSV export" --message "docs: update readme"
python3 semver.py next --current 2.0.0 --message "chore: bump deps"
```

**আসল output:**

```text
  patch  fix: handle empty input
  minor  feat(api): add CSV export
  -      docs: update readme
next version: 1.5.0 (minor)
  -      chore: bump deps
no release needed (no feat/fix/breaking commits)
```

Demo-র alice repository-তে `v1.0.0`-এর পরে দুটি commit (`feat: add search`, `fix: search crash on empty query`) যোগ করে:

```text
$ python3 semver.py next --repo .
latest release tag: v1.0.0; 2 commit(s) since
  patch  fix: search crash on empty query
  minor  feat: add search
next version: 1.1.0 (minor)
$ git describe --tags
v1.0.0-2-gd9e8a59
```

`git describe` দেখায়: tag `v1.0.0` থেকে ২টি commit পরে, বর্তমান commit `d9e8a59` (`g` = git)। এই শেষ দুটি commit-এ নির্দিষ্ট তারিখ দেওয়া হয়নি, তাই এই hash আপনার machine-এ ভিন্ন হবে। Build version হিসেবে এটি কাজে লাগে (L03-01-এর mini-project)।

### 9.4 দৈনন্দিন command (Ubuntu-তে একই)

```bash
git remote -v
git remote add upstream git@github.com:org/project.git     # fork-এর মূল project
git fetch --all --prune
git branch -vv                       # কোন branch কোন remote branch অনুসরণ করে, ahead/behind
git push -u origin feature/login     # প্রথম push + tracking সেট
git log --oneline main..origin/main  # remote-এ আছে, আমার কাছে নেই
git tag -a v1.2.0 -m "release 1.2.0" && git push origin v1.2.0
git tag -l 'v1.*' --sort=-v:refname  # version অনুযায়ী উল্টো ক্রমে
git push origin --delete feature/old # remote branch মোছা (⚠️ অন্যদের জানিয়ে)
```

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_semver.py`](code/L03-03/test_semver.py)-এর ৮টি test: semver.org-এর উদাহরণ ক্রম, numeric তুলনা, build metadata, সাতটি অবৈধ রূপ, bump (pre-release থেকে patch সহ), Conventional Commits (scope, `!`, `BREAKING CHANGE` footer, convention-হীন message), 0.x নিয়ম, এবং আসল git repository-তে `v1.2.0`/`v1.10.0`/`v2.0.0-rc.1` থেকে সঠিক ভিত্তি (`v1.10.0`) বেছে `1.11.0`।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `SEMVER` regex | semver.org-এর প্রস্তাবিত | Leading zero, খালি pre-release অবৈধ |
| `_key` pre-release tuple | `(0, সংখ্যা)` < `(1, অক্ষর)` | Spec-এর তুলনা নিয়ম |
| `build` `compare=False` ও `__eq__` | Metadata উপেক্ষা | Precedence নিয়ম §10 |
| `bump("patch")` pre থেকে | `1.5.0-rc.2` → `1.5.0` | Release candidate থেকে final |
| `classify` | Header regex + footer | Conventional Commits 1.0.0 |
| 0.x-এ major → minor | — | প্রচলিত রীতি (তবে spec-এ বাধ্যতামূলক নয় — team-এর সিদ্ধান্ত) |
| `latest_tag` pre-release বাদ | Release-ই ভিত্তি | `v2.0.0-rc.1` থাকলেও পরের patch `1.x` থেকে |

**Python কেন এখানে, কোথায় নয়:** release automation script-এ ভালো। বাস্তবে প্রতিষ্ঠিত tool আছে, যেমন semantic-release, release-please, commitizen; Python package-এর version তুলনায় `packaging.version` (PEP 440, যা SemVer থেকে কিছুটা আলাদা)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `remote_demo.sh` | Section 9.1-এর hash ও rejected push |
| `semver.py sort` | `1.9.0` < `1.10.0`, `beta.2` < `beta.11` |
| `next --current 1.4.2` (feat + fix) | `1.5.0` |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `! [rejected] main -> main (non-fast-forward)` | Remote-এ নতুন commit | `git pull --rebase` (নিজের কাজ) বা merge; `--force` নয় |
| `git status` "up to date" কিন্তু অন্যরা push করেছেন | Fetch হয়নি | `git fetch` |
| `fatal: The current branch has no upstream branch` | Tracking সেট হয়নি | `git push -u origin BRANCH` |
| Tag CI-তে দেখা যায় না | Tag push হয়নি | `git push origin TAG` |
| `Permission denied (publickey)` | SSH key নেই বা agent-এ নেই | `ssh -T git@github.com`, L01-13 |
| `Authentication failed` (HTTPS) | Password ব্যবহার, token মেয়াদোত্তীর্ণ | Personal access token / credential helper |
| Deleted remote branch এখনো `git branch -r`-এ | পুরোনো ছবি | `git fetch --prune` |
| Release script পুরোনো version নিল | String sort | SemVer-সচেতন sort (`--sort=v:refname`, `semver.py`) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Token কখনো remote URL, script বা log-এ রাখবেন না। Fine-grained, স্বল্পমেয়াদি token ব্যবহার করুন।
  - SSH key-এ passphrase রাখুন; server-এ শুধু-read deploy key ব্যবহার করুন।
  - Release tag sign করুন (`git tag -s`), এবং CI-তে tag-এর signature যাচাই করুন।
  - Tag সরানো (একই নামে অন্য commit) supply-chain ঝুঁকি। Protected tag দিয়ে এটা আটকান; dependency-তে SHA দিয়ে pin করুন (L03-06)।
  - Public repository-তে push-এর আগে secret scanning করুন (Module 19)।
- **Performance:**
  - বড় repository-তে `git clone --depth 1` বা `--filter=blob:none`।
  - `git fetch` শুধু দরকারি branch-এর জন্য।
- **Cost:**
  - Hosted CI-তে প্রতিটি clone-এ সময় যায়। Shallow clone ও cache ব্যবহার করুন।
  - Breaking change লুকানো release-এর খরচ (Section 5) সবচেয়ে বড়।

## 14. Hands-on exercise

1. Demo-র `bob`-এ `git branch -vv`, `git log --oneline --all --graph` চালিয়ে alice-এর tag fetch করুন। `git fetch --tags` দরকার হয় কি?
2. Lightweight ও annotated tag দুটো তৈরি করে `git cat-file -t` দিয়ে পার্থক্য দেখান। `git describe` কোনটি ব্যবহার করে (`--tags` ছাড়া ও সহ)?
3. `semver.py`-তে `--prerelease rc` option যোগ করুন: `next`-এর ফল `1.5.0-rc.1`। এরপর `1.5.0-rc.1` থেকে আবার চালালে `1.5.0-rc.2` আসবে। Test লিখুন।
4. Demo-তে `bob` দিয়ে `--force-with-lease` পরীক্ষা: alice push করার পরে bob fetch ছাড়া `--force-with-lease` দিলে কী হয়? Fetch-এর পরে দিলে কী হয়? (দ্বিতীয়টি কেন বিপজ্জনক হতে পারে?)
5. নিজের GitHub account থাকলে: একটি private repository-তে SSH remote যোগ করে push করুন, এবং `git remote -v`-এ কোনো token নেই তা নিশ্চিত করুন।

## 15. Mini-project — Release script

`release.sh` script-টি এই ধাপগুলো করবে:

1. Working tree পরিষ্কার ও `main`-এ আছে কিনা যাচাই।
2. `git fetch` এবং `origin/main`-এর সাথে মিল আছে কিনা যাচাই।
3. `semver.py next --repo .` দিয়ে version বের করা।
4. `CHANGELOG.md`-এ শেষ tag থেকে commit-এর তালিকা যোগ (feat/fix আলাদা অংশে)।
5. Annotated tag তৈরি।
6. Push শুধু `--yes` flag থাকলে। নইলে dry-run, অর্থাৎ শুধু দেখাবে কী করবে।

L03-06-এ এটি tag-triggered GitHub Actions workflow-এর সাথে যুক্ত হবে।

## 16. Interview প্রশ্ন

1. `git fetch` ও `git pull`-এর পার্থক্য।
2. `origin/main` কী? এটি কখন update হয়?
3. Push "non-fast-forward" বলে প্রত্যাখ্যাত হলে কী করবেন?
4. Annotated ও lightweight tag-এর পার্থক্য; release-এ কোনটি এবং কেন?
5. SemVer-এ MAJOR/MINOR/PATCH কখন বাড়ে? `1.0.0-rc.1` ও `1.0.0`-এর মধ্যে কোনটি নতুন?
6. Conventional Commits কীভাবে release automation সম্ভব করে?
7. HTTPS remote-এ credential নিরাপদে কীভাবে রাখবেন?

## 17. Self-assessment প্রশ্ন

1. Shared drive analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Demo-তে fetch-এর আগে bob-এর status-এ "behind" নেই কেন?
3. `ls-remote`-এ `v1.0.0` দুবার কেন?
4. `1.0.0-beta.11` ও `1.0.0-beta.2` — কোনটি বড়, কেন?
5. Section 5-এর চারটি সমাধান।

## 18. সংক্ষিপ্ত সারাংশ

- Remote = অন্য repository-র নাম; `origin/main` = শেষ fetch-এর ছবি।
- Fetch আনে, pull আনে ও মেশায়, push পাঠায়। Remote শুধু fast-forward নেয়।
- Release-এর জন্য annotated (সম্ভব হলে signed) tag; tag আলাদা করে push করতে হয়।
- SemVer: MAJOR = breaking, MINOR = feature, PATCH = fix। Pre-release < release; তুলনা numeric।
- Conventional Commits → স্বয়ংক্রিয় version → মানুষের ভুল কমে।
- Token কখনো URL-এ নয়; SSH key বা credential helper ব্যবহার করুন।

## 19. Completion checklist

- [ ] `remote_demo.sh` চালিয়ে fetch/pull/push ও rejection ব্যাখ্যা করতে পারি
- [ ] SemVer precedence নিয়ম ও `semver.py sort`-এর ফল ব্যাখ্যা করতে পারি
- [ ] `semver.py next --repo`-এ নিজের commit থেকে version বের করেছি
- [ ] `--force-with-lease`-এর আচরণ পরীক্ষা করেছি (Exercise ৪)
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Pro Git — Working with Remotes: https://git-scm.com/book/en/v2/Git-Basics-Working-with-Remotes
- Pro Git — Tagging: https://git-scm.com/book/en/v2/Git-Basics-Tagging
- `git-push(1)`: https://git-scm.com/docs/git-push
- `git-describe(1)`: https://git-scm.com/docs/git-describe
- Semantic Versioning 2.0.0: https://semver.org/
- Conventional Commits 1.0.0: https://www.conventionalcommits.org/en/v1.0.0/
- GitHub — Managing your personal access tokens: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens

---

**পরের lesson:** L03-04 — Pull request, code review, protected branch, CODEOWNERS
