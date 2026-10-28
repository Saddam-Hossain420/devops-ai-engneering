# L04-06 — Safe ও idempotent script: locking, temp file, dry-run

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L04-04 — Error handling ও trap](L04-04-error-handling-trap.md), [L04-05 — Argument parsing](L04-05-argument-parsing-logging.md) |
| **Label** | — |
| **Tested** | `backup_safe.sh`: ৬টি test পাস — অপরিবর্তিত source-এ skip ও পরিবর্তনে নতুন backup, একসাথে দুটি run-এ দ্বিতীয়টির exit ৭৫, stale lock দখল, **dry-run-এর rotation পরিকল্পনা আসল run-এর সাথে হুবহু মেলা**, tar ব্যর্থ হলে আধা-লেখা file/lock/fingerprint না থাকা, usage (GNU Bash 5.3.9, GNU tar, Windows/Git Bash)। এই machine-এ `flock` নেই — **শুধু `mkdir` fallback test হয়েছে**; `flock` পথ Ubuntu-তে চালানো হয়নি। লেখার সময় dry-run-এর একটি bug ধরা পড়েছে — Section 9.3। |

---

## 1. এই lesson-এ যা শিখবেন

- **Idempotency:** একই script বারবার চালালে ফল একই, ক্ষতি নেই।
- **Locking:** একসাথে দুটি run আটকানো — `flock` (kernel lock) ও portable `mkdir` lock; stale lock।
- **নিরাপদ temp file:** `mktemp`, অনুমান-অযোগ্য নাম, permission।
- **Atomic publish:** একই filesystem-এ temp → যাচাই → `mv`।
- **Dry-run যা সত্যিই আসল run-এর মতো আচরণ করে।**
- নিরাপদ rotation: শুধু নিজের file, শুধু সফল run-এর পরে।
- Exit code ৭৫ (`EX_TEMPFAIL`) — "পরে আবার চেষ্টা করুন"।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Production-এ script একবার চলে না — cron প্রতি ঘণ্টায়, retry ব্যর্থতার পরে, মানুষ ভুল করে দুবার, এবং কখনো আগের run শেষ হওয়ার আগেই পরের run শুরু হয়। তখন:

- দুটি backup একই file-এ লেখে — corrupt archive।
- Script অর্ধেক কাজ করে মারা যায় (OOM, reboot) — পরের run আধা-অবস্থা থেকে বিভ্রান্ত হয়।
- আধা-লেখা file "সর্বশেষ backup" হিসেবে দেখা যায়, এবং restore-এর দিন ব্যর্থ হয়।
- Rotation নতুন backup সফল হওয়ার আগেই পুরোনোগুলো মুছে দেয় — তারপর নতুনটাও ব্যর্থ।
- Dry-run বলে "২টি মুছব", আসল run মোছে ৩টি।

Idempotent ও নিরাপদ script এই সব পরিস্থিতিতেও সঠিক অবস্থায় থাকে। Configuration management (Ansible, Module 08) ও Kubernetes reconciliation (Module 14)-এর মূল ধারণা এটাই।

## 3. সহজ ভাষায় পরিচয়

| ধারণা | মানে | এই lesson-এর code-এ |
|---|---|---|
| Idempotent | বারবার চালালে অতিরিক্ত প্রভাব নেই | Source-এর fingerprint অপরিবর্তিত → skip |
| Mutual exclusion | একসাথে একটিই | `flock` বা `mkdir` lock; অন্যটি exit ৭৫ |
| Atomic | পুরোটা হয় বা কিছুই না | `.partial.XXXXXX` → `tar -t` যাচাই → `mv` |
| Safe temp | অনুমান-অযোগ্য নাম, শুধু owner-এর অধিকার | `mktemp` |
| Dry-run | কিছু না বদলে **ঠিক কী করবে** দেখানো | `run()` wrapper + একই হিসাব |
| Safe rotation | নিজের pattern, সফলতার পরে | `$NAME-*.tar.gz`, `rotate` শেষে |

**Idempotent কাজের উদাহরণ:**

| Idempotent | Idempotent নয় |
|---|---|
| `mkdir -p dir` | `mkdir dir` (দ্বিতীয়বার error) |
| `ln -sfn target link` | `echo "x" >> file` (প্রতিবার আরেক লাইন) |
| "এই লাইন না থাকলে যোগ করো" | `useradd bob` |
| `systemctl enable --now svc` | counter বাড়ানো |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ব্যাংকের লকার রুম

- **Lock** = লকার রুমে একসাথে একজন: ঢোকার সময় দরজায় "ব্যস্ত" ঝোলানো। অন্যজন এলে "পরে আসুন" (exit ৭৫)।
- **Stale lock** = কেউ "ব্যস্ত" ঝুলিয়ে চলে গেছেন, ভেতরে কেউ নেই — প্রহরী যাচাই করে (PID জীবিত?) সরিয়ে দেন।
- **Atomic publish** = নতুন দলিল প্রথমে আলাদা খামে প্রস্তুত, যাচাই, তারপর একবারে লকারে — লকারে কখনো অর্ধেক দলিল থাকে না।
- **Idempotency** = লকারে যা আছে তা আগেরটার সাথে হুবহু একই হলে নতুন copy রাখা হয় না।
- **Dry-run** = "আজ কী কী করব" তালিকা, যেটা আসল কাজের সাথে হুবহু মেলে।

### Analogy কোথায় মেলে না

- "ব্যস্ত" ফলক মানুষ দেখে বোঝে। **`mkdir` lock**-এ stale যাচাই ও সরানোর মাঝে race আছে: দুটি process একসাথে "stale" দেখলে একটি অন্যটির নতুন lock মুছে দিতে পারে। **`flock`** kernel-এর lock — process মারা গেলে (SIGKILL-ও) file descriptor বন্ধ হয়, এবং lock নিজে থেকেই মুক্ত হয়। Stale lock বলে কিছু থাকে না। তাই Linux-এ `flock` প্রথম পছন্দ, আর `mkdir` শুধু fallback।
- লকার রুমের দরজা সব জায়গা থেকে দেখা যায়। `flock` **একই machine-এর** process-দের মধ্যে কাজ করে; NFS বা একাধিক server-এ নির্ভরযোগ্য নয়। Distributed lock লাগলে database বা consul/etcd-এর মতো ব্যবস্থা লাগে (Module 18)।
- খাম বদলাতে সময় লাগে না। `mv` শুধু **একই filesystem-এ** atomic — অন্য disk-এ হলে copy + delete, অর্থাৎ মাঝপথে অর্ধেক file। তাই temp file dest-এর **একই directory-তে**।

## 5. Real-world engineering scenario — "Restore-এর দিন সর্বশেষ backup ভাঙা"

**পরিস্থিতি:** Database backup cron প্রতি ঘণ্টায়। Data বাড়তে থাকায় backup-এর সময় ৫০ মিনিট থেকে ৭০ মিনিটে গেল। এখন পরের run আগেরটা শেষ হওয়ার আগেই শুরু হয়, এবং দুটিই `backup-latest.tar.gz`-এ লেখে। পাশাপাশি rotation script প্রতি রাতে "৭ দিনের পুরোনো সব" মোছে — কোনো যাচাই ছাড়া।

একদিন restore-এর দরকার হলো। `backup-latest.tar.gz` corrupt — দুটি process-এর লেখা মিশে গেছে। আগের দিনেরগুলো rotation মুছে দিয়েছে, কারণ নতুনগুলো "আছে" বলে ধরা হয়েছিল।

**এই lesson-এর প্রতিটি ব্যবস্থা একটি করে ভুল আটকায়:**

| ভুল | প্রতিরোধ |
|---|---|
| দুটি run একসাথে | Lock; দ্বিতীয়টি exit ৭৫ ও alert |
| একই নামে লেখা | Timestamp-যুক্ত নাম; আগে থাকলে error |
| আধা-লেখা file | `.partial` → `tar -t` যাচাই → atomic `mv` |
| যাচাইহীন rotation | শুধু নতুন backup সফল হওয়ার পরে, সবচেয়ে নতুন N টি রেখে |
| Backup-এর সময় বাড়ছে, কেউ জানে না | Log-এ সময়; monitoring (Module 17) |

এবং নিয়মিত **restore পরীক্ষা** (Module 18) — একমাত্র প্রমাণ যে backup কাজ করে।

**শিক্ষা:** "এটা একবারে একবারই চলবে" — এই অনুমান production-এ মিথ্যা। Script নিজেই নিশ্চিত করবে।

## 6. Diagram — `backup_safe.sh`-এর প্রবাহ

```text
 parse & validate (realpath; dest ⊄ source)            exit 2 on usage error
        │
 trap cleanup EXIT  (partial file মোছা, mkdir-lock মুক্ত)
        │
 acquire_lock ── flock আছে? ── হ্যাঁ ── exec 9>DEST/.lock; flock -n 9 ──── ব্যস্ত → exit 75
        │                     না ─── mkdir DEST/.lock.d ── ব্যর্থ → PID জীবিত? → exit 75
        │                                                          মৃত → stale lock সরানো → আবার mkdir
 fingerprint(source) == .last-fingerprint && !force ──► "unchanged — nothing to do", exit 0
        │
 dry-run? ──► would create …; rotate(pending=1) শুধু দেখায়; exit 0
        │
 PARTIAL=$(mktemp DEST/.partial.XXXXXX) → tar → tar -t (যাচাই) → chmod 640 → mv → archive
        │
 .last-fingerprint (atomic) → rotate: সবচেয়ে নতুন KEEP টি রাখা (শুধু NAME-*.tar.gz)
        │
 exit 0 → cleanup (lock মুক্ত)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Idempotency | পুনরাবৃত্তিতে একই ফল |
| Mutual exclusion | একসাথে একটিই |
| `flock` | File descriptor-এর উপর kernel advisory lock |
| Advisory lock | সব অংশগ্রহণকারী মানলেই কাজ করে |
| Stale lock | মৃত process-এর রেখে যাওয়া lock |
| Race condition | ঘটনার ক্রমের উপর নির্ভরশীল ভুল |
| TOCTOU | Time-of-check to time-of-use — পরীক্ষা ও ব্যবহারের মাঝে অবস্থা বদলানো |
| `mktemp` | অনুমান-অযোগ্য নামে নিরাপদ temp file/directory |
| Atomic rename | `mv` একই filesystem-এ |
| Fingerprint | Content-এর সংক্ষিপ্ত পরিচয় (hash) |
| `EX_TEMPFAIL` (৭৫) | সাময়িক ব্যর্থতা — retry যোগ্য |
| Rotation | পুরোনো file সরানো, নির্দিষ্ট সংখ্যা রাখা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 `flock`

```bash
exec 9>"$DEST/.lock"          # file descriptor 9 খোলা (file তৈরি হয় যদি না থাকে)
flock -n 9 || exit 75         # -n: অপেক্ষা নয়, সাথে সাথে ব্যর্থ
# ... কাজ ...                 # script শেষ হলে (যেভাবেই হোক) fd 9 বন্ধ → lock মুক্ত
```

- Lock file মুছে দেবেন না: অন্য process সেই inode-এ অপেক্ষা করতে পারে; নতুন file আলাদা inode। Lock file থাকা ক্ষতিকর নয়।
- `flock -w 30 9` = সর্বোচ্চ ৩০ সেকেন্ড অপেক্ষা।
- Cron-এ এক লাইনে: `flock -n /run/lock/backup.lock backup.sh ...`।
- systemd timer (L01-11) নিজেই একই service-এর দুটি instance একসাথে চালায় না — এটিও একটি বিকল্প।

### 8.2 `mkdir` fallback-এর সীমা

`mkdir` atomic — একই নামে দুজন একসাথে তৈরি করলে একজনই সফল হয়। কিন্তু stale lock সরানোর অংশে TOCTOU race আছে:

1. A ও B দুজনেই দেখে PID মৃত।
2. A সরায় ও নতুন lock নেয়।
3. B তারপর A-র নতুন lock সরায় এবং নিজে নেয়।

এখন দুজনেই চলছে। এই script-এ ঝুঁকি কম (stale অবস্থা বিরল এবং cron-এর ব্যবধান বড়), কিন্তু শূন্য নয়। তাই Linux-এ `flock` আগে চেষ্টা করা হয় — এই lesson-এর test এই machine-এ (`flock` নেই) শুধু fallback পথ যাচাই করেছে।

### 8.3 `mktemp` ও `/tmp`-এর নিরাপত্তা

`/tmp/backup.$$` অনুমানযোগ্য: অন্য user আগে থেকে সেই নামে একটি symlink বানিয়ে রাখতে পারে, যা `/etc/passwd`-কে নির্দেশ করে। Root script লিখলে সেখানেই লিখবে (symlink attack)।

`mktemp` এলোমেলো নাম ব্যবহার করে, `O_EXCL` দিয়ে তৈরি করে (আগে থাকলে ব্যর্থ), এবং permission দেয় ৬০০ (file) বা ৭০০ (directory)। এই script temp file dest-এর ভেতরেই রাখে — atomic `mv`-এর জন্য, এবং dest-এর permission-ই নিরাপত্তা দেয়।

### 8.4 Fingerprint

`find -printf '%P\t%s\t%T@\n' | sort | sha256sum` — প্রতিটি file-এর আপেক্ষিক path, আকার ও mtime থেকে একটি hash। `sort` দেয় স্থির ক্রম; `LC_ALL=C` locale-নির্ভর sort এড়ায়।

সীমা: content বদলেছে কিন্তু আকার ও mtime একই থাকলে ধরা পড়বে না (বিরল; `touch -r` দিয়ে ইচ্ছাকৃতভাবে সম্ভব)। কঠোর প্রয়োজনে content hash ব্যবহার করুন (ধীর)। rsync একই trade-off করে (default: size + mtime)।

### 8.5 Dry-run-এর নীতি

Dry-run কেবল "কিছু চালাবো না" নয় — **একই সিদ্ধান্তের পথ** দিয়ে যেতে হবে। শুধু শেষ ধাপে আসল পরিবর্তনের বদলে ছাপাতে হবে। যে হিসাব আসল run-এর অবস্থার উপর নির্ভর করে (যেমন rotation-এ নতুন backup-টি), dry-run-এ সেটা অনুমান করে যোগ করতে হবে (Section 9.3)।

## 9. Practical demonstration

### 9.1 পাঁচটি পরিস্থিতি

File: [`code/L04-06/backup_safe.sh`](code/L04-06/backup_safe.sh)

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-06
S=$PWD/backup_safe.sh; T=$(mktemp -d); mkdir -p "$T/app"; echo v1 > "$T/app/a.txt"
bash "$S" -s "$T/app" -d "$T/bk"                                    # ১. প্রথম backup
bash "$S" -s "$T/app" -d "$T/bk"                                    # ২. অপরিবর্তিত
bash "$S" -f -H 3 -s "$T/app" -d "$T/bk" 2>/dev/null & p=$!; sleep 1
bash "$S" -f -s "$T/app" -d "$T/bk"; echo "second exit=$?"; wait $p  # ৩. একসাথে দুটি
mkdir "$T/bk/.lock.d"; echo 999999 > "$T/bk/.lock.d/pid"
bash "$S" -f -s "$T/app" -d "$T/bk"                                 # ৪. stale lock
bash "$S" -f -k 2 -n -s "$T/app" -d "$T/bk"                         # ৫. rotation dry-run
```

**আসল output (সংক্ষেপিত; এই machine-এ `flock` নেই, তাই mkdir fallback):**

```text
20:05:00Z INFO  backup_safe.sh[1358]: lock acquired (mkdir fallback)
20:05:00Z INFO  backup_safe.sh[1358]: created /tmp/.../bk/app-20261026T200500Z.tar.gz

20:05:01Z INFO  backup_safe.sh[1386]: source unchanged since last backup — nothing to do

20:05:02Z ERROR backup_safe.sh[1410]: another backup of /tmp/.../bk is running (pid 1401)
second exit=75
first exit=0

20:05:06Z WARN  backup_safe.sh[1442]: removing stale lock (pid 999999 is not running)
20:05:06Z INFO  backup_safe.sh[1442]: lock acquired (mkdir fallback)
20:05:07Z INFO  backup_safe.sh[1442]: created /tmp/.../bk/app-20261026T200506Z.tar.gz
```

- দ্বিতীয় run **কিছুই করেনি**, exit ০ — cron প্রতি ঘণ্টায় চালালেও অপরিবর্তিত data-র অপ্রয়োজনীয় copy জমে না।
- একসাথে দুটি run-এ দ্বিতীয়টি exit ৭৫, এবং কোন PID lock ধরে আছে তা জানায়।
- মৃত PID-এর lock নিরাপদে দখল হয়েছে।

### 9.2 Ubuntu-তে `flock`

```bash
bash backup_safe.sh -s ~/app -d /tmp/bk           # log-এ "lock acquired (flock)"
# অন্য terminal-এ একই সময়ে:
bash backup_safe.sh -f -s ~/app -d /tmp/bk; echo $?   # 75
ls -l /tmp/bk/.lock                                # lock file থাকে — স্বাভাবিক
kill -9 <প্রথম run-এর PID>                          # SIGKILL — trap চলে না…
bash backup_safe.sh -f -s ~/app -d /tmp/bk            # …তবু lock মুক্ত: kernel fd বন্ধ করেছে
```

(এই repository-তে চালানো হয়নি — উপরের আচরণ `flock(1)`-এর documented আচরণ অনুযায়ী প্রত্যাশিত।)

### 9.3 লেখার সময় ধরা পড়া bug: dry-run আসল run-এর চেয়ে কম দেখাচ্ছিল

তিনটি backup থাকা অবস্থায় `-k 2`:

- Dry-run বলেছিল **১টি** মুছবে।
- আসল run মুছেছিল **২টি**।

কারণ: আসল run প্রথমে নতুন backup তৈরি করে (মোট ৪), তারপর rotation; dry-run নতুনটি তৈরি করে না, তাই গুনেছিল ৩।

সমাধান: `rotate 1` — dry-run-এ "pending" নতুন backup গণনায় যোগ। এখন dry-run ২টি দেখায়, এবং আসল run-এর পরে ২টি থাকে। Test `test_dry_run_rotation_matches_real` পরিকল্পনা ও বাস্তব দুটোই মেলায়।

**শিক্ষা:** যে dry-run আসল run-এর চেয়ে কম ক্ষতি দেখায়, তা না থাকার চেয়েও খারাপ — মানুষ তার উপর ভরসা করে "নিরাপদ" ধরে নেয়।

### 9.4 ব্যর্থতার পরে কিছু থেকে যায় না

Test-এ PATH-এ একটি নকল `tar` বসানো হয়, যা সবসময় ব্যর্থ হয়। ফল:

- exit ১।
- `.partial.*` নেই, lock নেই।
- `.last-fingerprint` লেখা হয়নি — ব্যর্থ run পরের run-কে "অপরিবর্তিত" বলে বিভ্রান্ত করবে না।

Test লিখতে গিয়ে আরেকটি `:`-এর ফাঁদ ধরা পড়েছে (L04-05-এর মতো): PATH-এ `C:/Users/...` যোগ করলে PATH-এর `:` বিভাজক path-টিকে দুই ভাগ করে দেয়, তাই নকল tar ব্যবহারই হচ্ছিল না এবং test ভুলভাবে "সফল" দেখাচ্ছিল। এখন test নিশ্চিত করে যে নকল tar সত্যিই চলেছে (`fake tar failure` বার্তা)।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_backup_safe.py`](code/L04-06/test_backup_safe.py)-এর ৬টি test:

- অপরিবর্তিত হলে skip, পরিবর্তনে নতুন backup।
- একসাথে দুটি run → ৭৫।
- Stale lock দখল ও শেষে মুক্ত (`flock` থাকলে skip)।
- Dry-run ও আসল rotation হুবহু মেলা।
- tar ব্যর্থ হলে কিছু থেকে যায় না।
- Usage।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `EX_TEMPFAIL=75` | "অন্য run চলছে" | Caller (cron wrapper, systemd) ব্যর্থতা ও "পরে আবার" আলাদা করতে পারে |
| `exec 9>…; flock -n 9` | Kernel lock | Process মরলে নিজে মুক্ত |
| `mkdir` lock + PID + `kill -0` | Portable fallback ও stale যাচাই | `flock` নেই এমন জায়গায় |
| Cleanup-এ partial ও lock | Trap (L04-04) | যেকোনো সমাপ্তিতে পরিষ্কার |
| `mktemp "$DEST/.partial.XXXXXX"` | একই directory, লুকানো নাম | Atomic `mv`; অন্য tool অর্ধেক file তুলবে না |
| `tar -tzf` যাচাই | Archive পড়া যায় কিনা | Publish-এর আগে প্রমাণ |
| `[[ -e $archive ]] && die` | একই নাম আগে থাকলে | Overwrite নয় |
| Fingerprint file-ও `tmp` → `mv` | Atomic | আধা-লেখা fingerprint নয় |
| `rotate` শেষে, শুধু `$NAME-*.tar.gz` | সফলতার পরে, নিজের file | অন্য file কখনো মোছা নয় |
| `rotate 1` dry-run-এ | Pending গণনা | Section 9.3 |

**Bash কেন এখানে, কোথায় নয়:** file, lock ও process-এর কাজে Bash ও coreutils স্বাভাবিক। Distributed lock, retry policy, বা backup-এর পূর্ণ catalog (কোনটি কখন, কত বড়, যাচাই অবস্থা) লাগলে Python বা বিশেষায়িত tool (restic, borg — Module 18) ভালো।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| একই source-এ দ্বিতীয় run | "unchanged", exit ০, নতুন archive নেই |
| একসাথে দুটি run | দ্বিতীয়টি exit ৭৫ |
| `-k 2 -n` | পরিকল্পিত মোছার সংখ্যা = আসল run-এর মোছা |
| tar ব্যর্থ | exit ১, `.partial*`/`.lock*`/fingerprint নেই |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| "another backup running" কিন্তু কেউ চলছে না | `mkdir` lock stale (SIGKILL/reboot) | PID যাচাই (এই script করে); `flock` ব্যবহার করুন |
| দুটি run একসাথে চলেছে | Lock নেই, বা ভিন্ন lock file | একই, নির্দিষ্ট lock path |
| NFS-এ lock কাজ করে না | `flock` local | Central lock বা একটি নির্দিষ্ট host থেকে চালানো |
| `mv` ধীর এবং অর্ধেক file দেখা যায় | ভিন্ন filesystem-এ temp | Temp dest-এর একই directory-তে |
| Dry-run ও আসল ফল ভিন্ন | আলাদা code path | একই পথ, শুধু শেষ ধাপে `run()` |
| Rotation অন্য file মুছেছে | ঢিলেঢালা pattern (`*`) | নির্দিষ্ট prefix ও extension |
| Backup বদলায়নি অথচ নতুন file প্রতিবার | Idempotency নেই | Fingerprint বা content check |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `mktemp` ব্যবহার করুন (symlink attack)।
  - Archive ৬৪০ রাখুন, dest directory ৭৫০ বা ৭০০ — backup-এ প্রায়ই সংবেদনশীল data থাকে।
  - Root হিসেবে চালালে lock file ও dest-এর owner/permission যাচাই করুন।
  - Rotation-এ `rm`-এর আগে pattern ও path যাচাই করুন।
- **Performance:**
  - Fingerprint-এ শুধু metadata (দ্রুত)।
  - বড় data-য় incremental backup (rsync `--link-dest`, restic, borg)।
  - Lock-এর কারণে পরের run দেরিতে হলে exit ৭৫-কে monitor করুন — backup সময় বাড়ার সংকেত।
- **Cost:**
  - অপরিবর্তিত data-র অপ্রয়োজনীয় copy storage বিল বাড়ায় (cloud object storage-এ প্রতি GB)।
  - Rotation ও idempotency সরাসরি খরচ কমায়।
  - সবচেয়ে বড় খরচ ব্যর্থ restore।

## 14. Hands-on exercise

1. Ubuntu VM-এ Section 9.2: `flock` পথ, এবং SIGKILL-এর পরে lock নিজে মুক্ত হওয়া — নিজে দেখুন।
2. `backup_safe.sh`-এ `-w SECS` যোগ করুন: lock-এর জন্য সর্বোচ্চ এত সেকেন্ড অপেক্ষা (`flock -w`; mkdir fallback-এ loop)। Test লিখুন।
3. Section 8.2-এর `mkdir` race পুনরুৎপাদন করুন: দুটি process একসাথে stale lock সরায় (`sleep` বসিয়ে সময় মেলান)। কী ঘটে? কীভাবে কমাবেন?
4. Fingerprint-কে content hash দিয়ে বদলান (`find -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum`)। বড় directory-তে সময়ের পার্থক্য মাপুন।
5. একটি `ensure_line FILE LINE` function লিখুন (idempotent: না থাকলে যোগ, থাকলে কিছু নয়, atomic লেখা)। তিনবার চালিয়ে দেখান যে file একই থাকে।

## 15. Mini-project — Log archiver (শেষ অংশ)

`archive_logs.sh`-এ যোগ করুন:

- `flock` (fallback সহ) ও exit ৭৫।
- Archive temp-এ লিখে যাচাই করে atomic publish।
- মূল log file মোছা শুধু archive যাচাইয়ের পরে।
- Idempotency: একই মাসের archive আগে থাকলে নতুন file শুধু append।
- Dry-run আসল run-এর সাথে মেলে কিনা, তার test।

এটি Project P01-এর অংশ হবে এবং Module 04-এর Lab B-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. Idempotent script কী? উদাহরণ দিন।
2. একই script-এর দুটি instance একসাথে চলা কীভাবে আটকাবেন?
3. `flock` ও lock file/directory-র পার্থক্য কী? Stale lock কী?
4. আধা-লেখা file কীভাবে এড়াবেন? `mv` কখন atomic নয়?
5. `/tmp/myscript.$$` কেন নিরাপদ নয়?
6. ভালো dry-run-এর বৈশিষ্ট্য কী?
7. Backup rotation-এর নিরাপদ নিয়ম কী?

## 17. Self-assessment প্রশ্ন

1. লকার রুম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর পাঁচটি ভুল ও প্রতিরোধ।
3. Section 9.3-এর bug কী ছিল এবং কেন এটা বিপজ্জনক?
4. tar ব্যর্থ হলে fingerprint না লেখা কেন গুরুত্বপূর্ণ?
5. এই machine-এ কোন lock পথ test হয়েছে, কোনটি হয়নি?

## 18. সংক্ষিপ্ত সারাংশ

- Idempotency: অবস্থা যাচাই করে শুধু দরকারি পরিবর্তন।
- Lock: `flock` প্রথম পছন্দ (kernel, নিজে মুক্ত হয়); `mkdir` + PID fallback, race-এর সীমাসহ; ব্যস্ত হলে exit ৭৫।
- `mktemp` dest-এর একই directory-তে → যাচাই → atomic `mv`।
- Trap দিয়ে partial ও lock পরিষ্কার; ব্যর্থ run কোনো "সফল" চিহ্ন রাখবে না।
- Rotation শুধু সফলতার পরে, নির্দিষ্ট pattern-এ।
- Dry-run আসল run-এর একই পথ — পরিকল্পনা ও বাস্তব মিলতে হবে।

## 19. Completion checklist

- [ ] পাঁচটি পরিস্থিতি নিজে চালিয়ে দেখেছি
- [ ] Ubuntu-তে `flock` ও SIGKILL-এর আচরণ যাচাই করেছি (Exercise ১)
- [ ] Section 9.3-এর bug বুঝে নিজের dry-run-এ প্রয়োগ করেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `flock(1)`: https://man7.org/linux/man-pages/man1/flock.1.html
- `flock(2)`: https://man7.org/linux/man-pages/man2/flock.2.html
- `mktemp(1)` (GNU coreutils): https://www.gnu.org/software/coreutils/manual/html_node/mktemp-invocation.html
- `rename(2)` — atomicity: https://man7.org/linux/man-pages/man2/rename.2.html
- `sysexits.h` (exit code 75 = EX_TEMPFAIL): https://man.freebsd.org/cgi/man.cgi?query=sysexits
- BashFAQ/045 — How can I ensure only one instance of a script is running?: https://mywiki.wooledge.org/BashFAQ/045

---

**পরের lesson:** L04-07 — ShellCheck ও bats দিয়ে testing
