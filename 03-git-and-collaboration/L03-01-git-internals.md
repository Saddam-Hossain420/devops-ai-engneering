# L03-01 — Git internals: object, commit, tree, ref

| | |
|---|---|
| **Module** | 03 — Git and Collaboration |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-03 — Filesystem](../01-linux-systems/L01-03-filesystem-hierarchy.md), [L02-01 — hash/checksum-এর ধারণা](../02-computer-networking/L02-01-network-models.md) |
| **Label** | — |
| **Tested** | `git_objects.py`: ৮টি test পাস — temporary directory-তে **আসল `git` 2.54** দিয়ে repository বানিয়ে: hash, HEAD/branch/annotated tag resolve, commit ও tree parse `git ls-tree`-এর সাথে হুবহু, অপরিবর্তিত file-এর blob ভাগাভাগি, Python-এ লেখা object `git cat-file` দিয়ে পড়া, corruption সনাক্তকরণ (Python 3.14, Windows/Git Bash)। Section 9-এর demo আসলে চালানো; author ও তারিখ নির্দিষ্ট বলে hash **যেকোনো machine-এ একই** আসবে। Ubuntu-তে চালানো হয়নি — তবে কোনো OS-নির্ভর অংশ নেই। |

---

## 1. এই lesson-এ যা শিখবেন

- Git আসলে কী: একটি **content-addressable object database** + কিছু **ref** (নাম)।
- চার ধরনের object: **blob**, **tree**, **commit**, **tag**; তাদের hash কীভাবে হিসাব হয়।
- **Ref**: branch, tag, `HEAD` — শুধু একটি commit-এর নাম; symbolic ref।
- Working tree, **index** (staging area), repository — তিনটি জায়গা।
- কেন Git দ্রুত, কেন history নিরাপদ (একটি byte বদলালে সব hash বদলায়), কেন "branch সস্তা"।
- `.git` directory-র গঠন; loose object বনাম packfile।
- Python দিয়ে `git` ছাড়াই `.git` পড়া — `git cat-file`, `ls-tree`, `rev-parse`-এর ভেতরের কাজ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

বেশিরভাগ মানুষ Git ব্যবহার করেন কয়েকটি মুখস্থ command দিয়ে; কিছু ভুল হলে (detached HEAD, "হারিয়ে যাওয়া" commit, force push, merge-এর গোলমাল) ভয় পেয়ে repository মুছে আবার clone করেন — এবং কখনো কখনো আসল কাজ হারান।

Object model বুঝলে:

- "Commit কখনো হারায় না, শুধু নামহীন হয়" — recovery সম্ভব (L03-05)।
- Branch মানে একটি ৪১ byte-এর file — তাই branch তৈরি তাৎক্ষণিক।
- Rebase কেন "নতুন commit" তৈরি করে এবং shared branch-এ কেন বিপজ্জনক (L03-02)।
- CI/CD (Module 06)-এ commit SHA কেন build-এর অপরিবর্তনীয় পরিচয়; container image tag-এ SHA কেন ব্যবহার হয়।
- Supply-chain security-তে signed commit/tag ও SHA pinning (L03-06, Module 19) কেন অর্থবহ।

## 3. সহজ ভাষায় পরিচয়

**Git = একটি key-value store**, যেখানে key = content-এর SHA-1 hash (৪০টি hex অক্ষর), value = content।

| Object | কী রাখে | উদাহরণ |
|---|---|---|
| **blob** | একটি file-এর content (নাম নয়, permission নয়) | `hello\n` |
| **tree** | একটি directory: নাম → (mode, blob বা tree-এর hash) | `hello.txt → ce01362…`, `src/ → f268a4f…` |
| **commit** | একটি root tree + parent commit(s) + author/committer + message | snapshot + ইতিহাস |
| **tag** (annotated) | একটি object-এর দিকে নির্দেশ + tagger + message (+ signature) | `v1.0.0` |

**Ref** = একটি file যার ভেতরে একটি commit hash:

```text
.git/HEAD               ref: refs/heads/main        ← symbolic ref: "আমি এখন main-এ"
.git/refs/heads/main    bea3fb54176f2a536b3…         ← branch = একটি commit-এর নাম
.git/refs/tags/v1.0.0   0fd922b533218620fe4…         ← tag object-এর hash
```

**তিনটি জায়গা:**

| জায়গা | কী | Command |
|---|---|---|
| Working tree | Disk-এ আপনার file | edit |
| Index (staging) | পরের commit-এর প্রস্তুত snapshot (`.git/index`) | `git add` |
| Repository | Object database ও ref (`.git/objects`, `.git/refs`) | `git commit` |

`git add` file-কে **blob হিসেবে এখনই** object database-এ লেখে (Section 9-এ নিজে দেখবেন); `git commit` index থেকে tree তৈরি করে, তারপর commit object, তারপর branch-এর ref সরায়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### গ্রন্থাগারের archive

- **Blob** = একটি পৃষ্ঠার ফটোকপি; গায়ে একটি ছাপ (hash) যা পৃষ্ঠার লেখা থেকে হিসাব করা — একই লেখা হলে একই ছাপ, তাই একই পৃষ্ঠা দুবার রাখা হয় না।
- **Tree** = একটি সূচিপত্র: "অধ্যায় ১ = ছাপ X-এর পৃষ্ঠা, পরিশিষ্ট = সূচি Y"।
- **Commit** = একটি সংস্করণের রসিদ: "এই দিন, এই ব্যক্তি, এই সূচিপত্র, আগের সংস্করণ ছিল রসিদ Z"।
- **Branch** = একটি বুকমার্ক — "সর্বশেষ খসড়া এই রসিদে"। বুকমার্ক সরানো সহজ; রসিদ বদলায় না।
- **Tag** = স্থায়ী লেবেল — "প্রকাশিত সংস্করণ ১.০"।

### Analogy কোথায় মেলে না

- গ্রন্থাগারে একটি পৃষ্ঠা সংশোধন করা যায়। Git-এ object **অপরিবর্তনীয়** — content বদলালে hash বদলায়, তাই এটা নতুন object। "Commit বদলানো" (`--amend`, rebase) আসলে নতুন commit তৈরি করে বুকমার্ক সরানো; পুরোনোটা কিছুদিন থেকে যায়।
- রসিদ হারালে সংস্করণ হারায়। Git-এ কোনো ref নির্দেশ না করলেও commit object সাথে সাথে মোছে না — reflog ও garbage collection-এর সময়সীমা পর্যন্ত থাকে (L03-05)।
- ফটোকপির ছাপ শুধু শনাক্ত করে। Git-এর hash **শৃঙ্খল**: commit-এর hash-এ tree ও parent-এর hash আছে — পুরোনো কোনো file-এর একটি byte বদলালে তার পরের **সব** commit-এর hash বদলে যায়। তাই একটি commit SHA পুরো ইতিহাসের সত্যতা নিশ্চিত করে।

## 5. Real-world engineering scenario — "Production-এ কোন code চলছে?"

**পরিস্থিতি:** Production-এ একটি bug। Deploy dashboard বলছে image tag `latest`; developer বলছেন "main-এর সর্বশেষটা"; কিন্তু main-এ গত দুই ঘণ্টায় ৫টি merge হয়েছে, এবং একজন মনে করেন hotfix branch থেকে deploy হয়েছিল।

**সমস্যা:** branch ও `latest` **চলমান নাম** — এরা সময়ের সাথে অন্য commit নির্দেশ করে। কোন commit deploy হয়েছিল তার কোনো অপরিবর্তনীয় রেকর্ড নেই।

**সমাধান (Module 06 ও 10-এর ভিত্তি):**

1. Build-এর সময় `git rev-parse HEAD` থেকে পূর্ণ commit SHA নিন।
2. Image tag-এ SHA (`registry/app:bea3fb54176f…`) বা SHA-সহ version (`1.4.2+bea3fb5`)।
3. Application নিজে `/version` endpoint-এ SHA দেখায়; log-এর প্রতিটি লাইনে build SHA।
4. Release-এ annotated (প্রয়োজনে signed) tag।

এখন "কোন code চলছে" প্রশ্নের উত্তর: `git show bea3fb5` — অস্পষ্টতা নেই, কারণ object model নিশ্চিত করে যে এই SHA-এর পেছনের content কেউ পরে বদলাতে পারবে না।

**শিক্ষা:** Branch ও tag হলো মানুষের জন্য নাম; **commit SHA হলো সত্য**। Deploy, audit ও rollback-এ SHA ব্যবহার করুন।

## 6. Diagram — demo repository-র object graph

```text
 refs/heads/main ──┐        refs/tags/v1.0.0 ──► tag 0fd922b ("first release")
 HEAD ─(ref: main)─┤                                  │ object
                   ▼                                  ▼
           commit bea3fb5 "change app" ◄──────────────┘
             │ tree            │ parent
             ▼                 ▼
        tree 6cd15a1      commit cf32167 "first commit"
         ├─ hello.txt ─┐     │ tree
         └─ src/ ──┐   │     ▼
                   │   │  tree 25a376f
     tree f268a4f ◄┘   │   ├─ hello.txt ─┐
       └─ app.py ──┐   │   └─ src/ → tree a14f10e
                   ▼   ▼                   └─ app.py → blob c471b2f  print("v1")
       blob 3d6edeb   blob ce01362 "hello\n"  ◄── দুই commit-এর tree একই blob ভাগ করে
       print("v2")
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Object database | `.git/objects` — সব blob, tree, commit, tag |
| Content-addressable | Content-এর hash-ই তার ঠিকানা |
| SHA-1 / SHA-256 | Object ID-র hash algorithm (নতুন repository-তে SHA-256 ঐচ্ছিক) |
| Blob / tree / commit / tag | File content / directory / snapshot + ইতিহাস / নামযুক্ত চিহ্ন |
| Ref | Commit-এর নাম (branch, tag, remote-tracking) |
| Symbolic ref | অন্য ref-কে নির্দেশ করে (`HEAD` → `refs/heads/main`) |
| Detached HEAD | HEAD সরাসরি একটি commit-এ, কোনো branch-এ নয় |
| Index / staging area | পরের commit-এর প্রস্তুত অবস্থা |
| Loose object / packfile | আলাদা zlib file / অনেক object delta-compressed একসাথে |
| packed-refs | অনেক ref এক file-এ (`git gc`-এর পরে) |
| Lightweight / annotated tag | শুধু ref / নিজস্ব object (tagger, message, signature) |
| Plumbing / porcelain | নিম্নস্তরের command (`cat-file`) / দৈনন্দিন command (`commit`) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Hash হিসাব

```text
blob-এর ID = SHA-1( "blob " + <byte সংখ্যা> + "\0" + <content> )
"hello\n" → SHA-1("blob 6\0hello\n") = ce013625030ba8dba906f756967f9e9ca394464a
```

এই হিসাব যেকোনো machine-এ একই — তাই `git hash-object` ও এই lesson-এর Python function একই উত্তর দেয়। File `.git/objects/ce/013625…`-এ zlib দিয়ে compress করে রাখা হয় (প্রথম দুই অক্ষর directory — একটি directory-তে লক্ষ লক্ষ file এড়াতে)।

### 8.2 Tree ও commit-এর গঠন

Tree (binary): প্রতিটি entry `"<mode> <name>\0<20 byte raw hash>"`। Mode: `100644` সাধারণ file, `100755` executable, `120000` symlink, `040000` directory (tree), `160000` submodule। **Git শুধু execute bit রাখে** — পূর্ণ Linux permission (L01-04) নয়; owner/group-ও নয়।

Commit (text):

```text
tree 6cd15a1ef9c8c1b6cf7861f76f1ae3d8b60b3e43
parent cf3216773155357b4fdb0f8c9f1c75e64ac5d74b
author Lab User <lab@example.com> 1767225600 +0000
committer Lab User <lab@example.com> 1767225600 +0000

change app
```

Merge commit-এ দুটি (বা বেশি) `parent` লাইন; প্রথম commit-এ কোনোটি নেই। Author = যিনি লিখেছেন, committer = যিনি commit তৈরি করেছেন (rebase/cherry-pick-এ ভিন্ন হয়)।

### 8.3 কেন branch সস্তা ও history নিরাপদ

- Branch তৈরি = একটি ৪১ byte file লেখা। কোনো file copy হয় না।
- অপরিবর্তিত file ও directory পরের commit-এ **একই blob/tree** ভাগ করে (diagram-এ `hello.txt`) — তাই প্রতিটি commit পূর্ণ snapshot হলেও জায়গা কম লাগে; packfile আবার পার্থক্য (delta) হিসেবে compress করে।
- Hash শৃঙ্খলের কারণে commit SHA পুরো ইতিহাসের fingerprint। (SHA-1-এর তাত্ত্বিক collision দুর্বলতার জবাবে Git collision-detection ব্যবহার করে এবং SHA-256 object format আনছে।)

### 8.4 `.git` directory

```text
.git/
├── HEAD                 বর্তমান branch (symbolic ref) বা commit (detached)
├── config               repository-র config (remote, branch tracking)
├── index                staging area (binary)
├── objects/             object database (xx/yyyy… loose, pack/ packfile)
├── refs/heads/          local branch
├── refs/tags/           tag
├── refs/remotes/        remote-tracking branch (L03-03)
├── packed-refs          gc-র পরে একত্রিত ref
├── logs/                reflog — প্রতিটি ref কোথায় কোথায় ছিল (L03-05)
└── hooks/               client-side hook script
```

## 9. Practical demonstration

Files: [`code/L03-01/git_objects.py`](code/L03-01/git_objects.py), [`make_demo_repo.sh`](code/L03-01/make_demo_repo.sh) (নির্দিষ্ট author ও তারিখ দিয়ে demo repository — আপনার global Git config ব্যবহার করে না)।

### 9.1 Hash নিজের হাতে

```bash
cd ~/devops-ai-engineering/03-git-and-collaboration/code/L03-01
bash make_demo_repo.sh /tmp/git-demo
export GIT_CONFIG_GLOBAL=/tmp/git-demo/.empty-gitconfig      # এই terminal-এ demo-র config
cd /tmp/git-demo/demo
T=~/devops-ai-engineering/03-git-and-collaboration/code/L03-01/git_objects.py
git hash-object hello.txt
python3 $T hash hello.txt
```

**আসল output (Windows/Git Bash-এ চালানো; author/তারিখ নির্দিষ্ট বলে আপনার machine-এও হুবহু একই হওয়া উচিত):**

```text
bea3fb5 change app
cf32167 first commit
demo repository: /tmp/git-demo/demo   (expected: bea3fb5 change app / cf32167 first commit)
ce013625030ba8dba906f756967f9e9ca394464a
ce013625030ba8dba906f756967f9e9ca394464a
```

আলাদা একটি repository-তে `git add`-এর আগে-পরে (একই সেশনে চালানো):

```text
$ find .git/objects -type f | wc -l      # নতুন repo, hello.txt তৈরি, add-এর আগে
0
$ git add hello.txt; find .git/objects -type f
.git/objects/ce/013625030ba8dba906f756967f9e9ca394464a
```

`git add`-ই blob লেখে — commit-এর আগেই।

### 9.2 Ref ও commit

```bash
python3 $T refs
python3 $T cat HEAD
```

**আসল output:**

```text
HEAD                           ref: refs/heads/main
refs/heads/main                bea3fb54176f2a536b323b25459e437551c1b09a
refs/tags/v1.0.0               0fd922b533218620fe4d9bd103747b8531e2c379
commit bea3fb54176f2a536b323b25459e437551c1b09a (211 bytes)
tree 6cd15a1ef9c8c1b6cf7861f76f1ae3d8b60b3e43
parent cf3216773155357b4fdb0f8c9f1c75e64ac5d74b
author Lab User <lab@example.com> 1767225600 +0000
committer Lab User <lab@example.com> 1767225600 +0000

change app
```

`v1.0.0`-এর ref commit-কে নয়, **tag object**-কে (`0fd922b`) নির্দেশ করে — annotated tag নিজেই একটি object। `git cat-file -p v1.0.0`:

```text
object bea3fb54176f2a536b323b25459e437551c1b09a
type commit
tag v1.0.0
tagger Lab User <lab@example.com> 1767225600 +0000

first release
```

### 9.3 পুরো গাছ

```bash
python3 $T walk HEAD
python3 $T walk $(git rev-parse HEAD~1)
```

**আসল output:**

```text
commit bea3fb5417  "change app"
  tree   6cd15a1ef9  (root tree)
    blob   ce01362503  hello.txt  (6 bytes)
    tree   f268a4f664  src/
      blob   3d6edeb28d  app.py  (12 bytes)

commit cf32167731  "first commit"
  tree   25a376f09f  (root tree)
    blob   ce01362503  hello.txt  (6 bytes)
    tree   a14f10ebcf  src/
      blob   c471b2f5ec  app.py  (12 bytes)
```

- `hello.txt` দুই commit-এ একই blob `ce01362503` — copy নয়, ভাগাভাগি।
- `app.py` বদলেছে → নতুন blob → তার parent `src/` tree নতুন → root tree নতুন → commit নতুন। পরিবর্তন **নিচ থেকে উপরে** hash শৃঙ্খলে ছড়ায়।

### 9.4 Packfile

```bash
git count-objects -v | head -2
git gc -q
git count-objects -v | sed -n '1,5p'
python3 $T cat HEAD; echo "exit=$?"
```

**আসল output:**

```text
count: 10
size: 0
count: 0
size: 0
in-pack: 10
packs: 1
size-pack: 2
error: bea3fb54176f2a536b323b25459e437551c1b09a: not a loose object (packed? try `git cat-file -p bea3fb54176f2a536b323b25459e437551c1b09a`)
exit=2
```

১০টি loose object (৩ blob — `hello.txt` ও `app.py`-এর দুই সংস্করণ; ৪ tree; ২ commit; ১ tag) `git gc`-এর পরে একটি packfile-এ। এই lesson-এর tool শুধু loose object পড়ে এবং সেটা স্পষ্টভাবে বলে — আসল কাজে `git cat-file` সবসময় দুটোই পড়ে। Ref-ও `packed-refs`-এ চলে যায় (tool সেটা পড়তে পারে)।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_git_objects.py`](code/L03-01/test_git_objects.py)-এর ৮টি test: পরিচিত hash (খালি blob `e69de29…`), binary tree parse, **আসল git-এর সাথে তুলনা** (hash, HEAD/branch/annotated tag resolve, commit-এর tree/parent/author, `git ls-tree`-এর হুবহু output), অপরিবর্তিত file-এর blob ভাগাভাগি, Python-এ লেখা blob `git cat-file`-এ পড়া, এবং পরিবর্তিত object file-এ hash না মেলায় corruption ধরা।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `hash_object` | `"<type> <size>\0"` + content-এর SHA-1 | Git-এর object ID নিয়ম |
| `read_object` hash পুনঃযাচাই | পড়ার পরে আবার hash | Disk corruption বা হস্তক্ষেপ ধরা (`git fsck`-এর মূল ধারণা) |
| `write_object` আগে থাকলে লেখে না | — | Object অপরিবর্তনীয়, idempotent |
| `parse_tree` binary | mode, name, raw ২০ byte | Tree text নয় — `git cat-file -p` সুন্দর করে দেখায় |
| `resolve` symbolic ref ও packed-refs | `HEAD` → branch → sha | `git rev-parse`-এর সরল রূপ |
| `peel` | Annotated tag → commit | `v1.0.0^{commit}`-এর মতো |
| Packfile-এ স্পষ্ট error | — | Tool-এর সীমা লুকানো নয় |

**Python কেন এখানে, কোথায় নয়:** object model বোঝা ও `.git` পরীক্ষার জন্য চমৎকার। বাস্তব automation-এ `git` CLI-এর plumbing command (`rev-parse`, `cat-file --batch`, `for-each-ref`) বা libgit2/`pygit2` — packfile, SHA-256, partial clone ইত্যাদি সব সামলায়।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `make_demo_repo.sh` | `bea3fb5 change app`, `cf32167 first commit` |
| `git hash-object hello.txt` ও `git_objects.py hash` | উভয়ে `ce01362…` |
| `walk HEAD` ও `walk HEAD~1` | `hello.txt` একই blob |
| `git gc`-এর পরে `cat` | packed object-এর স্পষ্ট error, exit ২ |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom / ভুল ধারণা | আসলে | কী করবেন |
|---|---|---|
| "Commit-এ file-এর diff থাকে" | Commit পূর্ণ snapshot (tree) রাখে; diff দেখানোর সময় হিসাব হয় | `git cat-file -p HEAD` দেখুন |
| `You are in 'detached HEAD' state` | HEAD সরাসরি commit-এ | নতুন কাজ রাখতে `git switch -c NAME` |
| একই file অথচ hash ভিন্ন (Windows বনাম Linux) | Line ending রূপান্তর (`core.autocrlf`) | `.gitattributes`-এ `* text=auto eol=lf` |
| Permission পরিবর্তন commit হয় না (শুধু `644` বনাম `755`) | Git শুধু execute bit রাখে | Ownership/ACL deploy-এর সময় সেট করুন (Ansible, Module 08) |
| `error: object file ... is empty` | Disk পূর্ণ বা crash-এ corrupt | `git fsck`; remote থেকে পুনরুদ্ধার |
| Repository অনেক বড় | বড় binary commit হয়েছে — history থেকে যায় | Git LFS; history rewrite (সতর্কতার সাথে) |

## 13. Security, performance ও cost বিবেচনা

- **Security:** একবার commit হওয়া secret **history-তে থেকে যায়** — পরের commit-এ file মুছলেও blob থাকে; সমাধান: secret rotate করা (সবচেয়ে জরুরি), তারপর history rewrite (`git filter-repo`) — এবং ধরে নিন কেউ ইতিমধ্যে clone করেছে (Module 19-এ secret scanning)। Commit-এর author field যে কেউ লিখতে পারে — পরিচয় যাচাইয়ের জন্য signed commit/tag (SSH বা GPG signature)। CI-তে action/dependency SHA দিয়ে pin করা (L03-06) এই অপরিবর্তনীয়তার সুবিধা নেয়।
- **Performance:** বড় binary file (model weight, dataset — Module 21, 22) Git-এ নয়: প্রতিটি সংস্করণ পূর্ণ blob; Git LFS, DVC বা object storage। বড় monorepo-তে shallow/partial clone ও sparse checkout।
- **Cost:** Repository আকার CI-এর প্রতিটি clone-এ সময় ও bandwidth — CI-তে `fetch-depth: 1` (যেখানে history দরকার নেই)।

## 14. Hands-on exercise

1. `git hash-object`-এর মতো `printf 'blob 6\0hello\n' | sha1sum` দিয়ে hash নিজে হিসাব করুন।
2. Demo repo-তে `chmod +x hello.txt` → `git diff` কী দেখায়? `git ls-tree HEAD` ও নতুন commit-এর পরে mode কী?
3. দুটি ভিন্ন নামে একই content-এর file যোগ করে commit করুন — object কয়টি বাড়ল? কেন?
4. `git_objects.py`-তে একটি `fsck` command যোগ করুন: সব loose object পড়ে hash যাচাই, এবং কোনো tree/commit যে object নির্দেশ করে তা অনুপস্থিত হলে রিপোর্ট। Test লিখুন।
5. `echo "secret=abc" > .env; git add .env; git commit -m oops; git rm .env; git commit -m fix` — `git log -p`-এ ও `git_objects.py walk HEAD~1`-এ secret কোথায় দেখা যায়? (শুধু demo repo-তে, কাল্পনিক secret দিয়ে।)

## 15. Mini-project — "What's deployed" script

একটি script যা একটি repository-র জন্য: বর্তমান commit SHA, branch, সবচেয়ে কাছের tag (`git describe --tags --always --dirty`), working tree পরিষ্কার কিনা, এবং commit-এর সময় — JSON হিসেবে লেখে (`build-info.json`)। Module 06-এর CI pipeline এটি image-এ রাখবে এবং application `/version`-এ দেখাবে (Section 5)।

## 16. Interview প্রশ্ন

1. Git-এর চার ধরনের object কী কী এবং প্রতিটি কী রাখে?
2. Branch আসলে কী? Branch তৈরি কেন এত দ্রুত?
3. `git add` ও `git commit`-এর মধ্যে `.git`-এ কী ঘটে?
4. Lightweight ও annotated tag-এর পার্থক্য।
5. একটি commit-এর SHA কীভাবে পুরো history-র সত্যতা নিশ্চিত করে?
6. ভুলে commit হওয়া secret-এর ক্ষেত্রে কী করবেন?
7. Detached HEAD কী, এবং সেখানে করা কাজ কীভাবে রাখবেন?

## 17. Self-assessment প্রশ্ন

1. গ্রন্থাগার analogy কোথায় মেলে না (তিনটি বিষয়)?
2. `app.py`-এর একটি অক্ষর বদলালে কোন কোন object নতুন হয় (Section 9.3)?
3. `v1.0.0` ref কেন commit-এর বদলে অন্য hash দেখায়?
4. Git কোন file metadata রাখে না?
5. Section 5-এ `latest` tag কেন সমস্যা?

## 18. সংক্ষিপ্ত সারাংশ

- Git = content-addressable object database (blob, tree, commit, tag) + ref।
- Object ID = `"<type> <size>\0" + content`-এর hash; object অপরিবর্তনীয়।
- Commit = পূর্ণ snapshot (root tree) + parent + author + message; hash শৃঙ্খল history-কে tamper-evident করে।
- Branch/tag/HEAD = নাম; commit SHA = সত্য — deploy ও audit-এ SHA ব্যবহার করুন।
- `git add` blob লেখে; `commit` tree ও commit লেখে ও branch সরায়।
- Commit হওয়া secret history-তে থাকে — rotate আগে।

## 19. Completion checklist

- [ ] Demo repository বানিয়ে একই hash পেয়েছি
- [ ] `walk` দিয়ে commit → tree → blob ব্যাখ্যা করতে পারি
- [ ] `.git`-এর প্রধান অংশগুলো চিনি
- [ ] Exercise ৫ করে secret-এর স্থায়িত্ব নিজে দেখেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Pro Git — Git Internals: https://git-scm.com/book/en/v2/Git-Internals-Plumbing-and-Porcelain
- Pro Git — Git Objects: https://git-scm.com/book/en/v2/Git-Internals-Git-Objects
- `git-cat-file(1)`: https://git-scm.com/docs/git-cat-file
- `git-hash-object(1)`: https://git-scm.com/docs/git-hash-object
- `gitrepository-layout(5)`: https://git-scm.com/docs/gitrepository-layout
- Git hash function transition (SHA-256): https://git-scm.com/docs/hash-function-transition

---

**পরের lesson:** L03-02 — Branch, merge ও rebase
