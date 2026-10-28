# L05-03 — File, directory ও pathlib

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L05-02 — Python fundamentals](L05-02-python-fundamentals-type-hints.md), [L01-03 — Filesystem hierarchy](../01-linux-systems/L01-03-filesystem-hierarchy.md) |
| **Label** | — |
| **Tested** | `fs_tools.py`: ১০টি test-এর ৮টি পাস, ২টি skip (Python 3.14.5, Windows)। আসলে চালানো হয়েছে: scratchpad-এ বানানো একটি নমুনা tree-তে `largest`, `older-than` (dry-run ও `--delete`), `du`; এবং এই repo-তে `largest`। **Skip হওয়া দুটি test:** symlink (Windows-এ privilege লাগে — `WinError 1314`) ও অপঠনযোগ্য directory (POSIX permission)। এ দুটি Ubuntu-তে চলার কথা, কিন্তু **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- `pathlib.Path`: path জোড়া, অংশ আলাদা করা, পড়া/লেখা — string জোড়ার বদলে।
- Directory walk: `Path.rglob`, `os.walk`, `os.scandir` — কোনটা কখন; **symlink loop** ও **permission error** সামলানো।
- File-এর metadata: size, mtime, mode (`stat`)।
- **Atomic write:** temp file → `fsync` → `os.replace` — config file কখনো অর্ধেক লেখা থাকবে না।
- নিরাপদ মোছা: dry-run default, শুধু regular file, পরিষ্কার সারাংশ।
- Encoding ও newline: `encoding="utf-8"` সবসময় লিখুন।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Disk ভরে যাওয়া সবচেয়ে সাধারণ incident-গুলোর একটি (L01-12)। রাত ৩টায় on-call engineer-এর প্রশ্ন থাকে: "কোন file বড়? কোনগুলো পুরোনো ও মোছা নিরাপদ?" Shell-এ `find … -mtime +14 -delete` এক লাইনের কাজ — কিন্তু ভুল path বা ভুল pattern দিলে এক লাইনেই সর্বনাশ।

দ্বিতীয় সমস্যা: একটি script config file লেখার মাঝখানে crash করল, বা disk ভরে গেল। Service restart-এর সময় পেল অর্ধেক config, ফলে সে আর চালু হলো না।

এই lesson-এর tool তদন্তকে নিরাপদ করে (dry-run, symlink অনুসরণ নয়) এবং লেখাকে atomic।

## 3. সহজ ভাষায় পরিচয়

```python
from pathlib import Path

log_dir = Path("/var/log") / "app"           # '/' দিয়ে জোড়া — OS অনুযায়ী সঠিক separator
p = log_dir / "app.log.1.gz"
p.name, p.stem, p.suffix, p.parent            # 'app.log.1.gz', 'app.log.1', '.gz', /var/log/app
p.exists(), p.is_file(), p.stat().st_size
text = Path("config.json").read_text(encoding="utf-8")
for f in log_dir.glob("*.gz"): ...            # এক স্তর; rglob = সব স্তর
Path("out").mkdir(parents=True, exist_ok=True)
```

| কাজ | পুরোনো (`os.path`) | `pathlib` |
|---|---|---|
| জোড়া | `os.path.join(a, b)` | `a / b` |
| নাম | `os.path.basename(p)` | `p.name` |
| Extension | `os.path.splitext(p)[1]` | `p.suffix` |
| পড়া | `open(p).read()` | `p.read_text(encoding=…)` |
| খোঁজা | `glob.glob(…)` | `p.glob(…)`, `p.rglob(…)` |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### গুদাম পরিষ্কার

- **`largest`** = গুদামে ঢুকে প্রথমে দেখা কোন বাক্স সবচেয়ে বেশি জায়গা নিয়েছে।
- **`older-than` dry-run** = মেয়াদ পেরোনো বাক্সে প্রথমে শুধু লাল স্টিকার লাগানো। ফেলে দেওয়া হয় পরে, তালিকা দেখে নিশ্চিত হয়ে (`--delete`)।
- **Symlink অনুসরণ না করা** = "পাশের গুদামে দেখুন" লেখা চিরকুট পেলে সেখানে যাওয়া নয় — নইলে নিজের গুদামের বাইরের জিনিস ফেলে দেওয়ার ঝুঁকি, বা দুই চিরকুট একে অপরকে দেখালে অনন্ত ঘোরা।
- **Atomic write** = নতুন তাক পাশে পুরো সাজিয়ে তারপর এক ধাক্কায় পুরোনোটার জায়গায় বসানো। ক্রেতা কখনো অর্ধেক-খালি তাক দেখেন না।

### Analogy কোথায় মেলে না

- গুদামে বাক্স ফেলে দিলে জায়গা খালি হয়। **Linux-এ কোনো process খোলা রাখা file মুছলে জায়গা খালি হয় না** — যতক্ষণ না process file টি বন্ধ করে (L01-12-এর `lsof +L1`)। তাই "মুছলাম, কিন্তু `df` বদলাল না" — এটি সাধারণ বিভ্রান্তি।
- তাক বদলানো সবসময় সম্ভব। `os.replace` atomic **শুধু একই filesystem-এর ভেতরে।** ভিন্ন mount-এ temp file রাখলে rename ব্যর্থ হয় (`EXDEV`), তাই temp file একই directory-তে বানানো হয়।
- Windows-এ অন্য process target file খোলা রাখলে `os.replace` ব্যর্থ হতে পারে। Linux-এ পুরোনো reader পুরোনো inode পড়তে থাকে, নতুন reader নতুনটা পায়।

## 5. Real-world engineering scenario — "পুরোনো log মুছতে গিয়ে…"

**পরিস্থিতি:** `/var/log/app` ভরে গেছে। একজন engineer লিখলেন:

```bash
find $LOGDIR -name *.gz -mtime +14 -delete
```

তিনটি লুকানো বিপদ:

1. `$LOGDIR` খালি (env var set নেই) হলে `find -name …` বর্তমান directory থেকে খোঁজে — যেটা হয়তো `/`।
2. `*.gz` quote নেই, তাই বর্তমান directory-তে `.gz` file থাকলে shell আগেই expand করে, এবং ভুল pattern যায় (L04-02)।
3. `/var/log/app/archive` একটি symlink, NFS-এ রাখা compliance archive-এর দিকে। `find -L` বা ভুল option দিলে সেখানকার file-ও মুছে যেত।

**এই lesson-এর পদ্ধতি:**

```bash
python3 fs_tools.py older-than /var/log/app --days 14 --pattern '*.gz'          # তালিকা দেখুন
python3 fs_tools.py older-than /var/log/app --days 14 --pattern '*.gz' --delete
```

- Root না থাকলে exit ২।
- Symlink কখনো অনুসরণ করা হয় না।
- Directory মোছা হয় না।
- প্রথমবার শুধু তালিকা ও মোট আকার দেখায়।

**শিক্ষা:** মোছার tool-এ নিরাপদ default হলো তালিকা দেখানো। নিশ্চিত হওয়ার পরেই, স্পষ্ট flag দিয়ে, মোছা হবে। দীর্ঘমেয়াদি সমাধান logrotate (L01-14) বা retention policy — হাতে মোছা নয়।

## 6. Diagram — atomic write

```text
 সাধারণ লেখা (open("w") → write):
   app.conf  [পুরোনো] ──truncate──► [খালি] ──write…──► [অর্ধেক]  ← এখানে crash/disk full = নষ্ট config
                                                          ↑ এই মুহূর্তে reader অর্ধেক দেখে

 atomic_write:
   1. mkstemp(dir=একই directory)  → .app.conf.x7k2.tmp
   2. write → flush → fsync          (data disk-এ)
   3. chmod (পুরোনো mode রাখা)
   4. os.replace(tmp, app.conf)      ← একটিমাত্র rename: reader দেখে হয় পুরোনো, নয় নতুন
   ব্যর্থ হলে: tmp মুছে ফেলা, app.conf অপরিবর্তিত

 (পুরো durability-র জন্য Linux-এ directory-টিও fsync করা হয় — Section 8.3)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| `Path` | Path-এর object — জোড়া, অংশ, পড়া/লেখা |
| Absolute / relative path | `/` থেকে শুরু / বর্তমান directory থেকে |
| `stat` | File-এর metadata: size, mode, mtime, inode |
| mtime | শেষ পরিবর্তনের সময় |
| Symlink | অন্য path-এর দিকে নির্দেশক |
| `follow_symlinks=False` | Symlink-এর লক্ষ্য নয়, symlink নিজেকে দেখা |
| Atomic | হয় পুরো হবে, নয় কিছুই না — মাঝামাঝি অবস্থা কেউ দেখে না |
| `fsync` | OS-এর buffer থেকে data disk-এ পাঠানো নিশ্চিত করা |
| `os.replace` | Rename; target থাকলে তা প্রতিস্থাপন (একই filesystem-এ atomic) |
| `EXDEV` | ভিন্ন filesystem-এ rename-এর error |
| Dry-run | কী করা হতো তা দেখানো, আসলে না করে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Walk করার তিন উপায়

- **`Path.rglob("*")`** — সহজ।
  - Python ৩.১৩-এর আগে symlink-করা directory-তে ঢোকার আচরণ নির্দিষ্ট ছিল না; ৩.১৩-এ `recurse_symlinks` parameter এসেছে।
  - Permission error-এ কী হয় তা version-ভেদে ভিন্ন।
- **`os.walk(top, onerror=…)`** — default-এ symlink-করা directory-তে ঢোকে না (`followlinks=False`); `onerror` callback দিয়ে error ধরা যায়।
- **`os.scandir`** — সবচেয়ে নিচু স্তর ও দ্রুত।
  - `DirEntry` অনেক সময় আলাদা `stat` system call ছাড়াই file-এর ধরন জানে।
  - `fs_tools.Walker` এটা ব্যবহার করে, নিজের stack দিয়ে: প্রতিটি error এক জায়গায় জমা রাখা যায়, এবং symlink-এর নিয়ম স্পষ্ট থাকে।

### 8.2 বড় directory-তে memory

`largest` সব file-এর তালিকা বানিয়ে sort করে না। `heapq.nlargest(n, …)` শুধু `n`টি রাখে, তাই লক্ষ লক্ষ file-এও memory সামান্য। `Walker.files` একটি generator — file একটা একটা করে আসে।

### 8.3 Atomic write-এর খুঁটিনাটি

- **Temp file একই directory-তে:** তাতে rename একই filesystem-এ হয় (`EXDEV` এড়ায়)।
- **`fsync`:** ছাড়া rename আগে disk-এ পৌঁছে যেতে পারে, data পরে। Power চলে গেলে সেক্ষেত্রে নতুন নামের **খালি** file পাওয়া যায়। এটা ext4-এর পরিচিত আচরণ।
- **Directory-র `fsync`:** rename-কে durable করতে Linux-এ directory-টিও `fsync` করতে হয় (`os.open(dir, os.O_RDONLY)` → `os.fsync`)। এই tool সেটা করে না — Windows-এ এভাবে directory খোলা যায় না। এটি exercise ৩।
- **Permission:** `mkstemp` `0600` mode দেয়। তাই পুরোনো file-এর mode কপি করা হয়, নইলে nginx-এর মতো অন্য user config পড়তে পারবে না।
- **Owner:** owner (uid/gid) কপি করা হয় না — root হিসেবে চালালে নতুন file-এর owner root হবে। প্রয়োজনে `os.chown`।

### 8.4 Encoding

`read_text()`-এ encoding না দিলে Python OS-এর default ব্যবহার করে (Windows-এ cp1252 হতে পারে)। এই repo-তে আগে এর জন্য `UnicodeEncodeError` হয়েছিল (L04-08)। Python ৩.১৫ থেকে UTF-8 mode default হওয়ার কথা (PEP 686) — তবুও স্পষ্টভাবে লিখুন।

> **Fedora-তে:** কোনো পার্থক্য নেই। SELinux context (`ls -Z`) atomic write-এ নতুন file পায় directory-র default context থেকে, পুরোনো file-এর context নয়। Custom context থাকলে `restorecon` লাগতে পারে।

## 9. Practical demonstration

Files: [`code/L05-03/fs_tools.py`](code/L05-03/fs_tools.py), [`test_l05_03.py`](code/L05-03/test_l05_03.py)।

### 9.1 নমুনা tree

Scratchpad-এ একটি ছোট script দিয়ে tree বানানো হয়েছে, `os.utime` দিয়ে নির্দিষ্ট বয়স দিয়ে:

```text
app/a/app.log        1000 B,   0 দিন
app/a/app.log.1.gz   5000 B,  20 দিন
app/a/app.log.2.gz   7000 B,  40 দিন
app/b/big.bin        3 MB,     2 দিন
app/b/c/old.gz       100 B,   90 দিন
app/b/c/new.gz       100 B,    1 দিন
```

### 9.2 চালানো ও আসল output

```bash
python3 fs_tools.py largest app -n 3
python3 fs_tools.py older-than app --days 14 --pattern '*.gz'
python3 fs_tools.py du app -d 1
python3 fs_tools.py older-than app --days 30 --pattern '*.gz' --delete
```

```text
    2.9M  app\b\big.bin
    6.8K  app\a\app.log.2.gz
    4.9K  app\a\app.log.1.gz

would delete: app\b\c\old.gz (100B, 90 days)
would delete: app\a\app.log.2.gz (6.8K, 40 days)
would delete: app\a\app.log.1.gz (4.9K, 20 days)
3 files, 11.8K (dry-run; use --delete)

    2.9M  app\b
   12.7K  app\a

deleting: app\b\c\old.gz (100B, 90 days)
deleting: app\a\app.log.2.gz (6.8K, 40 days)
2 files, 6.9K
```

পরে `ls`-এ দেখা গেল `app/a`-তে `app.log` ও `app.log.1.gz`, এবং `app/b/c`-তে `new.gz` (ও খালি থাকলেও directory নিজে) রয়ে গেছে।

- Windows-এ path `\` দিয়ে দেখায় — `pathlib` OS-এর নিয়ম মানে। Ubuntu-তে `/` হবে।
- `du`-এর `12.7K` = 1000 + 5000 + 7000 byte; `b`-এর ভেতরে subdirectory `c`-ও যোগ হয়েছে।
- Dry-run-এর তালিকা পুরোনো থেকে নতুন ক্রমে সাজানো — কোনটা সবচেয়ে পুরোনো, এক নজরে দেখা যায়।
- `du nope` → `error: not a directory: nope`, exit ২।
- এই পুরো repo-তে (~২০০ markdown ও code file) `largest -n 3` চলেছে ০.০৮৫ s-এ। সবচেয়ে বড় file ছিল L00-02 lesson (৪৩.২K)।

### 9.3 Symlink — Windows-এ যা ঘটল

নমুনা tree-তে `app/a/loop → app/b` symlink বানানোর চেষ্টায় এল:

```text
symlink not created: [WinError 1314] A required privilege is not held by the client
```

Windows-এ symlink বানাতে Developer Mode বা admin অধিকার লাগে। তাই symlink test এখানে skip হয়েছে। Ubuntu-তে test টি loop symlink বানায় এবং যাচাই করে `big.bin` একবারই এসেছে কিনা — **চালানো হয়নি**।

### 9.4 Ubuntu-তে (চালানো হয়নি)

```bash
sudo python3 fs_tools.py largest /var/log -n 10
python3 fs_tools.py du /var/lib -d 1           # root ছাড়া: অনেক WARN …: Permission denied, exit 1
sudo python3 fs_tools.py older-than /var/log/journal --days 30   # journal file — journalctl --vacuum-time ব্যবহার করুন, হাতে নয়
```

শেষ উদাহরণটা ইচ্ছাকৃত: `/var/log/journal`-এর মতো কিছু directory নিজস্ব tool দিয়ে পরিচালিত হয় (L01-14)। হাতে মুছবেন না।

### 9.5 Test

```bash
python3 -m unittest -v
```

১০টি test:

- `largest`; `older-than`-এর pattern ও ক্রম; `du`-এর depth।
- Dry-run কিছু মোছে না, `--delete` মোছে কিন্তু directory রাখে।
- Symlink loop *(Windows-এ skip)*।
- অপঠনযোগ্য directory — WARN, কিন্তু crash নয় *(POSIX, non-root; Windows-এ skip)*।
- Atomic write: বিষয়বস্তু, কোনো অবশিষ্ট temp file নেই, permission রাখা।
- Atomic write-এর মাঝে ব্যর্থতা (`os.replace`-কে mock করে "disk full") — পুরোনো বিষয়বস্তু অক্ষত, temp file মুছে ফেলা।
- `human()` ও ভুল root।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `Walker` + নিজের stack | Recursive walk | Recursion limit নেই; error এক জায়গায় |
| `is_dir(follow_symlinks=False)` | Symlink-কে directory হিসেবে না ধরা | Loop ও বাইরের এলাকা এড়ানো |
| `de.stat(follow_symlinks=False)` | Metadata | Symlink-এর লক্ষ্যের নয় |
| দুই স্তরের `except OSError` | Directory বা entry পড়া যায়নি | বাকি walk চলতে থাকে |
| `heapq.nlargest` | শীর্ষ n | Memory O(n) |
| `now` parameter | সময় বাইরে থেকে দেওয়া | Test নির্ভরযোগ্য (L04-06-এর `--now`) |
| `relative_to(root).parts[:depth]` | `du`-এর group | Path-কে string হিসেবে কাটা নয় |
| `mkstemp(dir=path.parent)` | একই filesystem-এ temp | Atomic rename |
| `except BaseException: unlink; raise` | Ctrl-C-তেও temp file পরিষ্কার | অবশিষ্ট `.tmp` জমে না |
| `--delete` না দিলে শুধু তালিকা | নিরাপদ default | Section 5 |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `older-than … ` (flag ছাড়া) | `would delete` + `(dry-run; use --delete)`, কিছু মোছে না |
| `--delete` | শুধু মিলে যাওয়া regular file মোছে |
| ভুল root | exit ২ |
| অপঠনযোগ্য অংশ | stderr-এ `WARN`, exit ১, বাকি ফল ঠিক |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK` (Ubuntu-তে skip ০টি হওয়ার কথা) |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| মুছলাম কিন্তু `df` বদলায়নি | Process file খোলা রেখেছে | `lsof +L1`; service reload বা logrotate `copytruncate` |
| `UnicodeDecodeError` | Encoding দেওয়া নেই বা binary file | `encoding="utf-8"`, প্রয়োজনে `errors="replace"` |
| `OSError: [Errno 18] Invalid cross-device link` | ভিন্ন filesystem-এ rename | Temp একই directory-তে |
| Config-এর permission বদলে গেছে | `mkstemp`-এর `0600` | পুরোনো mode কপি (এই tool করে) |
| Walk অনন্তকাল চলছে | Symlink loop অনুসরণ | `follow_symlinks=False` |
| `PermissionError`-এ পুরো script crash | Error ধরা হয়নি | Per-entry `except OSError` |
| Windows-এ symlink test skip | Privilege নেই | Developer Mode, অথবা Linux-এ চালান |
| `p.glob("**/*.gz")` খুব ধীর | Network filesystem | Scope ছোট করুন; `os.scandir` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Symlink অনুসরণ করে মোছা একটি পরিচিত আক্রমণ-পথ: অন্য user `/tmp`-এ symlink রেখে root-এর cleanup script দিয়ে গুরুত্বপূর্ণ file মুছিয়ে নেয়।
  - Root হিসেবে চালানো cleanup script অবশ্যই `follow_symlinks=False` রাখবে।
  - World-writable directory-তে temp file বানাতে `tempfile.mkstemp` ব্যবহার করুন — নিজে নাম বানাবেন না (race condition)।
  - Secret-ওয়ালা file লিখতে mode `0o600` (`atomic_write(..., mode=0o600)`)।
- **Performance:**
  - `os.scandir` সাধারণত `os.listdir` + `stat`-এর চেয়ে দ্রুত।
  - লক্ষ লক্ষ file থাকলে generator ও `heapq` ব্যবহার করুন।
  - NFS-এ প্রতিটি `stat`-ই network round-trip।
- **Cost:** Cloud disk (EBS/PD) বাড়ানোর আগে `du`/`largest` দিয়ে দেখুন — প্রায়ই সমস্যা কয়েকটি পুরোনো log বা core dump। Disk একবার বাড়ালে সাধারণত আর ছোট করা যায় না (Module 08)।

## 14. Hands-on exercise

1. Ubuntu-তে `python3 -m unittest -v` চালান — skip ০টি হলো কি? Symlink test-এর ফল কী?
2. `atomic_write`-এ Linux-এ directory `fsync` যোগ করুন (`os.name == "posix"` হলে)। কেন Windows-এ বাদ দিতে হয়?
3. `older-than`-এ `--keep N` যোগ করুন: pattern মেলা সবচেয়ে নতুন N টি file কখনো মুছবে না, এমনকি পুরোনো হলেও।
4. একটি file খোলা রেখে (`tail -f`) মুছুন এবং `df`, `lsof +L1` দেখুন (Ubuntu)।
5. `du`-এর ফল `du -sh /var/lib/*`-এর সাথে তুলনা করুন। পার্থক্য কেন? (ইঙ্গিত: apparent size বনাম block, sparse file, hard link।)

## 15. Mini-project — Disk-full triage report

`disk_triage.py /`:

- Mount-ভিত্তিক ব্যবহার (`shutil.disk_usage`)।
- ভরা mount-এ শীর্ষ ১০ directory ও file।
- "মুছে ফেলা কিন্তু খোলা" file (Linux: `/proc/*/fd`-তে `(deleted)` symlink)।
- সুপারিশ, যেমন "journal 2.1 GB → `journalctl --vacuum-size`"।
- **কোনো কিছু মোছে না।** JSON ও text output।

Module 18-এর runbook-এ এটা প্রথম ধাপ হবে।

## 16. Interview প্রশ্ন

1. File মোছার পরেও disk-এর জায়গা খালি হচ্ছে না — কেন, এবং কী করবেন?
2. Config file atomically কীভাবে লিখবেন? `fsync` কেন লাগে?
3. Cleanup script-এ symlink কেন বিপজ্জনক?
4. `os.walk`, `Path.rglob`, `os.scandir`-এর পার্থক্য কী?
5. লক্ষ লক্ষ file থেকে সবচেয়ে বড় ১০টি কম memory-তে কীভাবে বের করবেন?

## 17. Self-assessment প্রশ্ন

1. গুদাম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর `find` command-এর তিনটি বিপদ কী?
3. `mkstemp`-এর পরে `chmod` কেন?
4. `atomic_write`-এ `BaseException` কেন, `Exception` কেন নয়?
5. Windows-এ দুটি test কেন skip হলো?

## 18. সংক্ষিপ্ত সারাংশ

- `pathlib` দিয়ে path; সবসময় `encoding="utf-8"`।
- Walk-এ symlink অনুসরণ নয়; permission error জমা রাখুন, crash করবেন না।
- মোছার tool: dry-run default, শুধু regular file, স্পষ্ট `--delete`।
- Config লেখা: একই directory-তে temp → `fsync` → `os.replace`; mode রাখুন।
- বড় tree-তে generator ও `heapq`।

## 19. Completion checklist

- [ ] নমুনা tree-তে চারটি subcommand চালিয়েছি
- [ ] Atomic write-এর চার ধাপ ব্যাখ্যা করতে পারি
- [ ] Ubuntu-তে symlink ও permission test চালিয়েছি
- [ ] `python3 -m unittest -v`-এ সব test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `pathlib`: https://docs.python.org/3/library/pathlib.html
- Python — `os.scandir` / `os.walk` / `os.replace`: https://docs.python.org/3/library/os.html
- Python — `tempfile`: https://docs.python.org/3/library/tempfile.html
- Python — `heapq`: https://docs.python.org/3/library/heapq.html
- PEP 686 — Make UTF-8 mode default: https://peps.python.org/pep-0686/
- Linux man page — `rename(2)`: https://man7.org/linux/man-pages/man2/rename.2.html
- Linux man page — `fsync(2)`: https://man7.org/linux/man-pages/man2/fsync.2.html

---

**পরের lesson:** L05-04 — subprocess নিরাপদভাবে চালানো
