# L05-12 — Health check ও backup verification tool

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L05-08 — CLI](L05-08-argparse-cli.md), [L05-06 — HTTP client](L05-06-http-client-retry.md), [L05-03 — File](L05-03-files-and-pathlib.md) |
| **Label** | — |
| **Tested** | `healthcheck.py` ও `verify_backup.py`: ৯টি test পাস (gzip CRC-এর regression test সহ — Section 9.5-এর পরবর্তী সংশোধন দেখুন) (Python 3.14.5, Windows)। আসলে চালানো হয়েছে: local HTTP server-এ ৬ ধরনের check; `make_demo_backups.py`-এর **১টি ভালো ও ৬টি ইচ্ছাকৃত নষ্ট backup** (সব কৃত্রিম SQLite data) যাচাই। **একটি গুরুতর bug ধরা পড়েছে:** tool "৪০৪৬ ms" বলছিল, কিন্তু process বের হচ্ছিল ২০.১৫ s পরে (Section 9.4)। আসল production backup বা Linux-এ চালানো **হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Health check-এর স্তর: **liveness** (চলছে?), **readiness** (কাজ নিতে পারে?), এবং end-to-end (user-এর কাজ হচ্ছে?)।
- একাধিক check **সমান্তরালে**, সামগ্রিক **deadline**-সহ — এবং thread pool-এর একটি লুকানো ফাঁদ।
- Check-এর ফল: OK/WARNING/CRITICAL/UNKNOWN; "check-ই চলেনি" আর "service খারাপ"-এর পার্থক্য।
- **Backup যাচাইয়ের সিঁড়ি:** আছে → আকার → বয়স → checksum → archive পড়া যায় → বিষয়বস্তু → আসল restore → application-স্তরের check।
- নিরাপদ extract: path traversal, symlink, `tarfile` data filter।
- কেন "backup সফল" log বিশ্বাস করবেন না।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

**Health check ছাড়া:** service-এর process চলছে, কিন্তু database-এর সাথে connection নেই। Load balancer তবুও traffic পাঠাচ্ছে, আর প্রতিটি request 500 পাচ্ছে।

**Backup যাচাই ছাড়া:** "Backup job প্রতিদিন সফল" — এক বছর পরে restore-এর দিন দেখা গেল:

- File-গুলো অর্ধেক upload হওয়া।
- অথবা খালি (`pg_dump` ব্যর্থ, কিন্তু `gzip` সফল)।
- অথবা ভুল database-এর।
- অথবা restore-এর পরে "database disk image is malformed"।

শিল্পে একটি প্রচলিত কথা আছে: **"যে backup থেকে restore পরীক্ষা করা হয়নি, সেটা backup নয় — একটা আশা।"**

## 3. সহজ ভাষায় পরিচয়

```bash
python3 healthcheck.py checks.json --deadline 10          # exit 0/1/2/3 — monitoring-এর রীতি
python3 verify_backup.py /var/backups/db/db-20261027T0300Z.tar.gz \
    --max-age-h 26 --min-bytes 1024 --expect taskflow.db --sqlite taskflow.db
```

| Backup যাচাইয়ের ধাপ | কী ধরে | কী **ধরে না** |
|---|---|---|
| Size | খালি/অর্ধেক file | ভুল বিষয়বস্তু |
| Age | Job বন্ধ হয়ে গেছে | — |
| Checksum (`.sha256`) | Transfer/storage-এ নষ্ট হওয়া | **Backup নেওয়ার সময়ই** ভুল ছিল |
| Archive পড়া | কাটা gzip, CRC, ভাঙা tar | Data ঠিক কিনা |
| Contents | গুরুত্বপূর্ণ file নেই | File-এর ভেতরের অবস্থা |
| Test restore | Extract-এর সমস্যা, path traversal | Application data-র অখণ্ডতা |
| Application check (SQLite `integrity_check`) | Database-এর ভেতরের দুর্নীতি | ব্যবসায়িক যুক্তি (row সংখ্যা যুক্তিসঙ্গত?) |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অগ্নিনির্বাপক যন্ত্র ও fire drill

- **Health check** = নিয়মিত টহল: "দরজা খোলা? আলো জ্বলছে? Alarm-এ ব্যাটারি আছে?"
- **Deadline** = টহলদার এক ঘরে আটকে গেলে বাকি ভবনের রিপোর্ট দেরিতে আসে না — "ওই ঘর: অজানা" লিখে এগিয়ে যান।
- **Backup আছে** = দেয়ালে অগ্নিনির্বাপক যন্ত্র ঝুলছে।
- **Checksum** = যন্ত্রের seal অক্ষত।
- **Test restore** = fire drill — সত্যিই যন্ত্র চালিয়ে দেখা ফোম বের হয় কিনা।
- **Application check** = ফোম আগুন নেভায় কিনা।

### Analogy কোথায় মেলে না

- Seal অক্ষত থাকলে যন্ত্র ঠিক থাকার সম্ভাবনা বেশি। **Checksum শুধু বলে "file বদলায়নি" — শুরু থেকেই ভুল থাকলে checksum-ও ভুলটাকেই "সঠিক" বলবে।** Section 9.2-এ path traversal-ওয়ালা ও নষ্ট-database-ওয়ালা backup দুটোরই checksum PASS করেছে।
- Fire drill-এ ভবন খালি করা নিরাপদ। **Test restore অবশ্যই আলাদা জায়গায়** (temp directory, আলাদা instance) — production database-এর ওপর restore মানে নিজেই দুর্যোগ ঘটানো। আর অনিরাপদ archive extract করলে restore-ই `../../etc/…`-এ লিখতে পারে।
- টহলদার আটকে গেলে অন্য কেউ এগিয়ে যান। **Python-এর thread pool-এ "আটকে যাওয়া" check পুরো program-কে শেষে আটকে রাখে** — deadline রিপোর্টে মানা হলেও process বের হয় না (Section 9.4)।

## 5. Real-world engineering scenario — "Backup সফল, restore অসম্ভব"

**পরিস্থিতি:** Nightly job:

```bash
pg_dump mydb | gzip > /backup/db-$(date +%F).sql.gz && aws s3 cp /backup/… s3://…
```

`set -o pipefail` ছিল না। এক রাতে `pg_dump` authentication-এ ব্যর্থ হলো, কিন্তু `gzip` একটি খালি stream সফলভাবে compress করল (৩০ byte)। Pipeline-এর exit code হলো gzip-এর ০, তাই upload-ও সফল, আর monitoring-এ সবুজ। তিন সপ্তাহ ধরে প্রতিরাতে ৩০ byte-এর "backup"।

**এই lesson-এর ধাপগুলো কোথায় ধরত:**

- `size`: ৩০ byte < `--min-bytes` → FAIL, **প্রথম রাতেই।**
- `restore` + application check: খালি dump থেকে কোনো table নেই → FAIL।
- `healthcheck`-এর `file_age`: job পুরো বন্ধ হলে ধরত (এখানে প্রযোজ্য নয়)।

**আরেকটি ঘটনা (Section 9.2-এর 07):** archive ঠিক, checksum ঠিক, extract ঠিক — কিন্তু database file-এর একটি page নষ্ট। শুধু `PRAGMA integrity_check` ধরেছে।

**শিক্ষা:** Backup job-এর exit code নয়, **restore-এর ফল** হলো সাফল্যের মাপকাঠি। Verification আলাদা job, আলাদা alert।

## 6. Diagram

```text
 healthcheck.py checks.json --deadline D
   ├─ thread(daemon) ─ http  api      ──► OK       HTTP 200 in 68 ms
   ├─ thread(daemon) ─ http  degraded ──► CRITICAL body lacks '"ok"'
   ├─ thread(daemon) ─ http  slow     ──► (D পেরিয়ে গেছে) → UNKNOWN "not finished within deadline"
   ├─ thread(daemon) ─ tcp   db-port  ──► CRITICAL timeout
   ├─ thread(daemon) ─ disk  /        ──► OK 37.6%
   └─ thread(daemon) ─ file_age backup──► OK 0.0 h
   join(বাকি সময়) … D-তে থামা → worst() = CRITICAL → exit 2   (daemon: process সাথে সাথে বের হয়)

 verify_backup.py db-…tar.gz
   size → age → checksum(.sha256) → archive(সব member পড়া, unsafe path?) → contents
        → restore (tempdir, filter="data") → sqlite PRAGMA integrity_check → RESTORABLE / NOT VERIFIED
   (প্রতিটি ধাপ চলে; প্রথম ব্যর্থতায় থামে না — একবারে সব সমস্যা দেখা যায়)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Liveness | Process চলছে ও সাড়া দিচ্ছে |
| Readiness | নতুন কাজ নিতে প্রস্তুত (dependency ঠিক আছে) |
| Synthetic check | User-এর মতো request পাঠিয়ে end-to-end যাচাই |
| Deadline | সব check-এর মোট সময়সীমা |
| Daemon thread | Main thread শেষ হলে যার জন্য অপেক্ষা করা হয় না |
| RPO / RTO | কত data হারানো সহনীয় / কত দ্রুত ফেরত আসতে হবে (Module 30) |
| Checksum / sidecar | File-এর hash; পাশে আলাদা `.sha256` file |
| Path traversal | Archive-এর `../` দিয়ে target-এর বাইরে লেখা |
| `tarfile` data filter | Python ৩.১২+-এ নিরাপদ extract নীতি |
| Test restore | Backup থেকে আলাদা জায়গায় আসল পুনরুদ্ধার |
| `PRAGMA integrity_check` | SQLite-এর নিজস্ব অখণ্ডতা যাচাই |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 কেন thread, এবং কেন daemon

Health check-এর বেশিরভাগ সময় যায় network-এর অপেক্ষায় (I/O)। Python-এ I/O-র অপেক্ষার সময় GIL ছেড়ে দেওয়া হয়, তাই thread-এ সমান্তরাল চালানো কার্যকর।

`ThreadPoolExecutor` সুবিধাজনক, কিন্তু তার worker thread **non-daemon**। `concurrent.futures` interpreter বন্ধের সময় (`atexit`) সব worker-এর শেষের অপেক্ষা করে। `shutdown(wait=False, cancel_futures=True)` শুধু **শুরু না হওয়া** কাজ বাতিল করে; চলমান কাজ থামায় না।

ফলে ২০ s ঝুলে থাকা HTTP check থাকলে report ৪ s-এ ছাপা হয়, কিন্তু process বের হয় ২০ s-এ। তাই `healthcheck.py` নিজে daemon thread + `join(বাকি সময়)` ব্যবহার করে।

**মূল্য:** daemon thread হঠাৎ বন্ধ হয় — তাই check-এর ভেতরে এমন কিছু করা যাবে না যা মাঝপথে থামলে ক্ষতি হয় (file লেখা ইত্যাদি)। Health check শুধু পড়ে, তাই এখানে নিরাপদ।

### 8.2 Status-এর অর্থ

- **CRITICAL:** service খারাপ — connection refused, ভুল status, body-তে প্রত্যাশিত লেখা নেই।
- **UNKNOWN:** আমরা জানি না — deadline পেরিয়েছে, অথবা check-এর code-এ bug।

দুটো আলাদা রাখলে on-call বুঝতে পারেন সমস্যা service-এ নাকি monitoring-এ। সামগ্রিক status গুরুত্বের ক্রমে (L05-08-এর `SEVERITY`)।

### 8.3 Archive যাচাই কীভাবে

- gzip প্রতিটি stream-এর শেষে CRC-32 ও দৈর্ঘ্য রাখে। এটা যাচাই হয় **শুধু compressed stream-এর একদম শেষ পর্যন্ত পড়লে**।
- **ফাঁদ:** `tarfile` tar-এর end-of-archive চিহ্নে থেমে যায়, gzip-এর শেষের CRC trailer পড়েই না। তাই প্রতিটি member-এর data পুরো পড়াও যথেষ্ট নয় — এর পরে `tar.fileobj`-কেও শেষ পর্যন্ত পড়তে হয় (Section 9.5)।
- কাটা file-এ `EOFError: Compressed file ended before the end-of-stream marker was reached`।
- Bit flip compressed কাঠামোয় পড়লে zlib-এর error। Literal data-তে পড়লে শুধু CRC ধরে: `BadGzipFile: CRC check failed`।
- `tarfile.open(..., "r:*")` সব compression চেষ্টা করে। তাই bit-flip-এর error-এ gz, bz2, xz, **zst** (Python ৩.১৪-এ নতুন) — সব পদ্ধতির ব্যর্থতার তালিকা আসে।

### 8.4 নিরাপদ extract

পুরোনো `tar.extractall()` archive-এর `../../etc/cron.d/x` নামের member-কে target-এর বাইরে লিখতে পারত (CVE-2007-4559 — বহু বছরের পুরোনো, বহু project-এ প্রভাবিত)।

Python ৩.১২ থেকে `filter="data"` এগুলো আটকায়:

- absolute path ও `..`;
- বাইরের দিকে symlink;
- device file;
- setuid bit।

Python ৩.১৪-এ এটাই default। `verify_backup.py` filter-এর ওপর নির্ভর করার **আগেই** নিজে member-এর নাম পরীক্ষা করে FAIL দেয়। কারণ এমন backup অস্বাভাবিক — হয়তো কেউ ইচ্ছাকৃতভাবে বদলেছে।

> **Fedora-তে:** কোনো পার্থক্য নেই। systemd timer দিয়ে verification চালানো (L01-11) দুই distro-তে একই। SELinux-এ backup directory-র context (`restorecon`) লাগতে পারে।

## 9. Practical demonstration

Files:

- [`code/L05-12/healthcheck.py`](code/L05-12/healthcheck.py)।
- [`verify_backup.py`](code/L05-12/verify_backup.py)।
- [`make_demo_backups.py`](code/L05-12/make_demo_backups.py) (কৃত্রিম backup; শুধু খালি directory-তে লেখে)।
- [`test_l05_12.py`](code/L05-12/test_l05_12.py)।

### 9.1 Demo backup তৈরি

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-12
python3 make_demo_backups.py /tmp/backup-demo
for f in /tmp/backup-demo/*.tar.gz; do
  echo "=== $(basename "$f")"
  python3 verify_backup.py "$f" --min-bytes 1000 --expect taskflow.db --sqlite taskflow.db; echo "exit=$?"
done
```

### 9.2 সাতটি backup — আসল output (সংক্ষেপিত)

```text
=== 01-good
PASS  size      1605 bytes (min 1000)
PASS  age       1.0 h old (from name; max 26.0 h)
PASS  checksum  sha256 matches
PASS  archive   2 members readable
PASS  contents  all expected files present
PASS  restore   extracted 2 files to a temp dir
PASS  sqlite    integrity_check=ok, tables=1
result: RESTORABLE                                                   exit=0

=== 02-truncated   (checksum বানানোর পরে অর্ধেক কাটা — অসম্পূর্ণ upload)
FAIL  size      805 bytes (min 1000)
FAIL  checksum  sha256 mismatch: expected ca7e800b236b…, got 93c17fb63780…
FAIL  archive   EOFError: Compressed file ended before the end-of-stream marker was reached
FAIL  contents  not verified: archive unreadable (saw 1 member names)
FAIL  restore   skipped: archive unreadable

=== 03-bitflip   (মাঝখানের একটি byte উল্টানো)
FAIL  checksum  sha256 mismatch: …
FAIL  archive   ReadError: file could not be opened successfully:
                - method gz: ReadError('zlib error: Error -3 while decompressing data: invalid distance too far back')
                - method bz2 … xz … zst … tar: ReadError('invalid header')

=== 04-traversal   (archive-এ "../../outside.txt")
PASS  checksum  sha256 matches                          ← checksum নিরাপত্তা প্রমাণ করে না
FAIL  archive   unsafe member '../../outside.txt'

=== 05-missing-db
FAIL  size      167 bytes (min 1000)
FAIL  contents  missing: taskflow.db
FAIL  sqlite    taskflow.db not in archive

=== 06-stale   (৩ দিন পুরোনো নাম)
FAIL  age       73.0 h old (from name; max 26.0 h)        ← বাকি সব PASS

=== 07-corrupt-db   (database-এর দ্বিতীয় page-এ ২০০ byte শূন্য)
PASS  size / age / checksum / archive / contents / restore
FAIL  sqlite    DatabaseError: database disk image is malformed
```

প্রতিটি নষ্ট backup কমপক্ষে একটি ধাপে ধরা পড়েছে, এবং **কোনো একক ধাপ সবগুলো ধরেনি**:

- Checksum ০৪ ও ০৭ ছাড়ে।
- Archive ০৫, ০৬, ০৭ ছাড়ে।
- Application check ছাড়া ০৭ অদৃশ্য।

Traversal-এর পরে scratchpad-এ `outside.txt` তৈরি হয়নি — যাচাই করা হয়েছে।

### 9.3 Health check — আসল output

Local HTTP server-এর সাথে (একটি `/slow` endpoint ২০ s ঘুমায়), `--deadline 4`:

```text
OK        api              HTTP 200 in 68 ms  (68.1 ms)
CRITICAL  api-degraded     HTTP 200 but body lacks '"ok"'  (44.6 ms)
UNKNOWN   api-slow         not finished within deadline 4.0s  (0.0 ms)
CRITICAL  db-port          timeout after 1s  (1057.3 ms)
OK        disk             37.6% used  (27.1 ms)
OK        backup-fresh     modified 0.0 h ago  (0.1 ms)
overall: CRITICAL in 4046.0 ms
```

- `api-degraded`: HTTP 200, কিন্তু body বলছে "degraded"। শুধু status code দেখলে OK মনে হতো — **body যাচাই জরুরি।**
- `db-port`: বন্ধ port-এ Windows-এ "refused" নয়, timeout (L05-06-এর পর্যবেক্ষণ)।
- সব check সমান্তরালে চলেছে, তাই মোট সময় ≈ deadline, যোগফল নয়।

### 9.4 আসল bug — report ৪ s, process ২০ s

উপরের output-এর প্রথম সংস্করণে (তখন `ThreadPoolExecutor`) subprocess-এর wall time মাপা হয়েছিল:

```text
overall: CRITICAL in 4046.0 ms
  exit 2 wall 20.15s
```

Report deadline মেনেছে, কিন্তু process বের হয়েছে `/slow`-এর ২০ s শেষ হওয়ার পরে (Section 8.1-এর কারণে)। Cron বা monitoring agent-এর কাছে check-টি ২০ s ধরে ঝুলে থাকত; অনেক agent-এর নিজস্ব timeout-এ তখন পুরো check "timed out" দেখাত, ফলে আমাদের সুন্দর report হারিয়ে যেত।

Daemon thread-এ বদলানোর পরে, একই পরিস্থিতিতে:

```text
UNKNOWN   api-slow         not finished within deadline 4.0s  (0.0 ms)
OK        disk             37.6% used  (0.1 ms)
overall: UNKNOWN in 4016.7 ms
 exit 3 wall 4.12s
```

এখন একটি test (`test_deadline_is_honoured_by_the_process`) process-এর **wall time** মাপে, report-এর সংখ্যা নয়।

### 9.5 আরেকটি সংশোধন — বিভ্রান্তিকর PASS

প্রথম সংস্করণে কাটা archive-এর জন্য `PASS contents all expected files present` দেখাচ্ছিল। কাটা অংশের আগে member-এর header পড়া হয়ে গিয়েছিল, তাই নাম পাওয়া গিয়েছিল — কিন্তু data নয়। এখন archive ব্যর্থ হলে contents "not verified"। **শিক্ষা:** verification tool-এ "যাচাই করা যায়নি" কখনো "PASS" নয়।

**পরে ধরা পড়া গুরুতর bug (Module 06-এর পূর্ণ validation-এর সময়, ২০২৬-১০-২৭):**

এই lesson প্রকাশের পরে পুরো repository-র test loop-এ L05-12 হঠাৎ ব্যর্থ হলো:

```text
FAIL: test_each_demo_backup (prefix='03-bitflip')
AssertionError: Lists differ: ['checksum', 'sqlite'] != ['checksum', 'archive', 'contents', 'restore']
```

Bit-flip-এর backup-এ archive **PASS** হয়েছিল, এবং শুধু database-এর integrity check নষ্ট data ধরেছিল। কারণ:

- `tarfile` tar-এর end-of-archive চিহ্নে থামে, gzip-এর শেষের CRC-32 পড়েই না। তাই CRC আসলে কখনো যাচাই হচ্ছিল না।
- আগের run-এ উল্টানো byte-টি compressed কাঠামোয় পড়েছিল (zlib error), তাই কাকতালীয়ভাবে ধরা পড়েছিল।
- এবার `make_demo_backups.py`-এর tar header-এ সময় ভিন্ন, ফলে byte-টি literal data-তে পড়েছে, এবং নষ্ট data নীরবে বেরিয়ে এসেছে।

সমাধানের পরে একই backup:

```text
FAIL  archive   BadGzipFile: CRC check failed 0x972357e8 != 0xfad0d2bd
```

একটি নির্ধারিত regression test যোগ হয়েছে: compression level ০ (stored block)-এ যেকোনো flip literal data-তে পড়ে, তাই শুধু CRC-ই সেটা ধরতে পারে।

**শিক্ষা:**

- এই lesson-এর আগের সংস্করণে লেখা "শেষ পর্যন্ত পড়লেই CRC যাচাই হয়" দাবিটি code-এ সত্য ছিল না। একটি test কাকতালীয়ভাবে পাস করছিল।
- এলোমেলো input (সময়-নির্ভর header) দিয়ে লেখা test একটি run-এ পাস করলেও পরের run-এ ব্যর্থ হতে পারে — আর সেটাই আসল bug দেখিয়ে দিতে পারে।
- Security বা integrity check-এর জন্য নির্ধারিত (deterministic) test লিখুন।

### 9.6 Test

```bash
python3 -m unittest -v
```

৮টি test:

- HTTP-এর তিন রূপ (ok, body-তে লেখা নেই, 404)।
- TCP, disk, file age, অনুপস্থিত file।
- Config validation (duplicate name, অজানা type, অনুপস্থিত field)।
- **Process-এর wall time < ৪.৫ s**, যেখানে deadline ১ s ও slow endpoint ৬ s।
- সাতটি demo backup-এর প্রতিটির **ঠিক কোন ধাপ ব্যর্থ** হওয়া উচিত।
- Traversal বাইরে কিছু লেখে না।
- Unsafe নামের ৬ রূপ।
- Checksum file না থাকা; CLI।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `threading.Thread(daemon=True)` + `join(বাকি)` | সত্যিকারের deadline | Section 9.4 |
| `BoundedSemaphore(workers)` | একসাথে সর্বোচ্চ check | শত check-এ শত connection নয় |
| `except Exception` → UNKNOWN | Check-এর bug | একটি bug পুরো run থামায় না |
| `contains` | Body যাচাই | 200 + "degraded" ধরা |
| `with exc:` (HTTPError) | Connection বন্ধ | L05-06-এর leak |
| `validate()` → exit 64 | ভুল config | Monitoring-এর ০–৩-এর সাথে মেশে না |
| সব ধাপ চলে, প্রথম ব্যর্থতায় থামে না | পূর্ণ চিত্র | একবারে সব সমস্যা |
| Member data পুরো পড়া + `tar.fileobj` শেষ পর্যন্ত | gzip CRC যাচাই | tarfile নিজে trailer পড়ে না (Section 9.5) |
| `unsafe_member` + `filter="data"` | দুই স্তরের সুরক্ষা | Traversal ও অস্বাভাবিক archive |
| `tempfile.TemporaryDirectory` | Restore আলাদা জায়গায়, পরে মোছা | Production-এ কখনো নয় |
| SQLite `mode=ro` URI | Read-only খোলা | যাচাইয়ে বদলানো নয় |
| বয়স নামের timestamp থেকে | `mtime` copy-তে বদলায় | L05-09-এর নিয়ম |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `01-good` | RESTORABLE, exit ০ |
| বাকি ছয়টি | NOT VERIFIED, exit ২, Section 9.2-এর ধাপে FAIL |
| Slow check + `--deadline 4` | ~৪ s-এ process শেষ, exit ৩ |
| ভুল config | exit ৬৪ |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Health check সবুজ, user-রা error পাচ্ছে | শুধু status code বা শুধু liveness | Body/readiness/synthetic check |
| Check program deadline-এর পরেও ঝুলে থাকে | Non-daemon worker thread | Daemon thread; বা subprocess-এ চালিয়ে kill |
| প্রতিটি check-এর timeout আছে, তবুও ধীর | ক্রমানুসারে চালানো | সমান্তরাল + মোট deadline |
| "Backup সফল" কিন্তু file ৩০ byte | Pipeline-এ `pipefail` নেই | `--min-bytes`; `set -o pipefail` (L04-04) |
| Checksum মেলে, restore ব্যর্থ | Backup নেওয়ার সময়ই নষ্ট | Test restore + application check |
| Restore অন্য directory-তে লিখেছে | Path traversal | `filter="data"`; নাম যাচাই |
| Verify job-এ disk ভরে যায় | Restore temp-এ বড় data | পর্যাপ্ত জায়গা; ছোট sample; tmpdir পরিষ্কার |
| বন্ধ port-এ ধীর CRITICAL (Windows) | Windows-এর SYN retry | Check-এর timeout ছোট রাখুন |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Backup-এ production data আছে — verify-এর temp directory-র permission সীমিত রাখুন, এবং কাজ শেষে মুছে ফেলুন (এই tool সবসময় মোছে)।
  - Untrusted archive extract করবেন না, অথবা শুধু `filter="data"` দিয়ে।
  - Health endpoint-এ secret বা ভেতরের বিবরণ দেখাবেন না (L05-10-এর `/debug/env` ঘটনা)।
  - Backup-এর checksum ও backup একই জায়গায় রাখলে আক্রমণকারী দুটোই বদলাতে পারে — checksum আলাদা জায়গায় বা signed রাখুন (Module 19)।
- **Performance:**
  - Health check সস্তা হওয়া উচিত — প্রতি ১০ s-এ ভারী database query চালালে check নিজেই load হয়ে যায়।
  - Backup verify ভারী; দিনে একবার, peak সময়ের বাইরে, এবং আলাদা machine-এ।
- **Cost:**
  - Restore test-এর জন্য cloud instance বা database লাগলে খরচ হয়, কিন্তু না-পরীক্ষিত backup-এর ঝুঁকির তুলনায় তুচ্ছ।
  - S3 থেকে বড় backup download-এ egress খরচ — একই region-এ verify করুন (Module 08, 29)।

## 14. Hands-on exercise

1. Ubuntu-তে TaskFlow-এর SQLite database-এর backup নিন (`sqlite3 taskflow.db ".backup b.db"` → tar.gz → sha256sum)। `verify_backup.py` দিয়ে যাচাই করে systemd timer-এ দৈনিক চালান।
2. `verify_backup.py`-তে `--min-rows tasks=100` যোগ করুন — application-স্তরের যুক্তিসঙ্গততা যাচাই।
3. `healthcheck.py`-তে `command` ধরনের check যোগ করুন (L05-04-এর `run_cmd`) — যেমন `systemctl is-active nginx`।
4. `ThreadPoolExecutor` সংস্করণটি (Section 8.1) আবার লিখে Section 9.4-এর ২০ s wall time নিজে পুনরুৎপাদন করুন।
5. Section 5-এর pipeline (`pipefail` ছাড়া) একটি ব্যর্থ command দিয়ে পুনরুৎপাদন করুন — যেমন `false | gzip > x.gz; echo $?`। তারপর `--min-bytes` দিয়ে ধরুন।

## 15. Mini-project — Backup verification report

`backup_audit.py /var/backups/*/`:

- প্রতিটি directory-র সবচেয়ে নতুন backup যাচাই।
- RPO লঙ্ঘন (বয়স > ২৪ h)।
- শেষ সফল restore-এর তারিখ একটি state file-এ।
- সাপ্তাহিক Markdown/JSON report।
- কোনো directory "৭ দিনে একবারও RESTORABLE নয়" হলে CRITICAL।

Module 30 (Disaster recovery)-এর restore drill এর ওপর ভিত্তি করবে।

## 16. Interview প্রশ্ন

1. Liveness ও readiness check-এর পার্থক্য কী?
2. Health check-এ কী check করবেন, কী করবেন না?
3. Backup যে কাজ করে, তা কীভাবে নিশ্চিত হবেন?
4. Checksum কী প্রমাণ করে, কী করে না?
5. Archive extract করার সময় কী নিরাপত্তা ঝুঁকি?
6. একাধিক check সমান্তরালে চালালে মোট সময়সীমা কীভাবে নিশ্চিত করবেন?

## 17. Self-assessment প্রশ্ন

1. Fire drill analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ ৩০ byte-এর backup কেন "সফল" হলো?
3. সাতটি demo backup-এর কোনটি কোন ধাপে ধরা পড়ল? কোনটি শুধু একটি ধাপে?
4. Report ৪ s কিন্তু process ২০ s কেন?
5. কাটা archive-এ contents কেন "PASS" দেখাচ্ছিল?

## 18. সংক্ষিপ্ত সারাংশ

- Health check: সমান্তরাল, প্রতিটিতে timeout, মোট deadline (daemon thread), body যাচাই, CRITICAL ≠ UNKNOWN।
- Backup verify: size → age → checksum → archive পুরো পড়া → contents → test restore → application check।
- কোনো একক ধাপ যথেষ্ট নয়; checksum নিরাপত্তা নয়।
- নিরাপদ extract (`filter="data"`), restore সবসময় আলাদা জায়গায়।
- "যাচাই করা যায়নি" কখনো PASS নয়।

## 19. Completion checklist

- [ ] সাতটি demo backup যাচাই করে প্রতিটির কারণ ব্যাখ্যা করতে পারি
- [ ] Health check-এর deadline bug নিজে পুনরুৎপাদন করেছি
- [ ] (Ubuntu) একটি আসল backup-এর দৈনিক verify timer চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `tarfile` (extraction filters): https://docs.python.org/3/library/tarfile.html#extraction-filters
- Python — `concurrent.futures`: https://docs.python.org/3/library/concurrent.futures.html
- Python — `threading` (daemon threads): https://docs.python.org/3/library/threading.html#thread-objects
- SQLite — `PRAGMA integrity_check`: https://www.sqlite.org/pragma.html#pragma_integrity_check
- PEP 706 — Filter for `tarfile.extractall`: https://peps.python.org/pep-0706/
- Kubernetes — Configure liveness, readiness and startup probes: https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/
- Google SRE Book — Data Integrity: https://sre.google/sre-book/data-integrity/

---

**পরের lesson:** L05-13 — Continuous project শুরু: প্রথম Python web API
