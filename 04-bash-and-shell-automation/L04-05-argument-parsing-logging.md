# L04-05 — Argument parsing, getopts, usage ও logging

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L04-03 — Function](L04-03-functions-reusable-scripts.md), [L04-04 — Error handling](L04-04-error-handling-trap.md) |
| **Label** | — |
| **Tested** | `getopts_demo.sh` ও `backup.sh`: ৯টি test পাস। Test-এ যা যাচাই হয়েছে: `getopts`-এর যুক্ত flag, `--`, প্রথম non-option-এ থামা, দুই রকম error; `backup.sh`-এর CLI > env অগ্রাধিকার, short ও long রূপ, পুনরাবৃত্তিযোগ্য option, আসল tar.gz-এ exclude, `-q`-তেও log file, dry-run-এ কিছু না লেখা, usage error, source-এর ভেতরে dest প্রত্যাখ্যান (GNU Bash 5.3.9, GNU tar, Windows/Git Bash)। **তিনটি আসল bug ধরা পড়েছে** — Section 9.3। Ubuntu-তে চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- `getopts`: short option, value, যুক্ত flag (`-vn`), silent error mode, `OPTIND`, `--`।
- `getopts`-এর সীমা: long option নেই, প্রথম non-option-এ থামে।
- Long option (`--source DIR`, `--source=DIR`) হাতে লেখা `while`/`case` loop দিয়ে।
- **Usage** লেখা: help header থেকেই তৈরি; usage error = exit ২।
- **Configuration-এর অগ্রাধিকার:** command-line > environment > default; `--print-config`।
- **Logging:** level, UTC timestamp, PID, stderr; `-v`/`-q`; log file — console ও file-এর আলাদা level।
- Input normalization (`realpath`) ও নিরাপত্তা-যাচাই।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি script যখন শুধু লেখক নিজে চালান, তখন `$1`, `$2` যথেষ্ট। কিন্তু team-এর tool, cron job বা CI step হলে:

- কে মনে রাখবে, তৃতীয় argument কোনটি? ভুল ক্রমে দিলে source ও dest উল্টে যায়।
- `--help` নেই — documentation পুরোনো wiki-তে।
- ভুল option দিলে চুপচাপ উপেক্ষা হয় (`--dryrun` বানান ভুল, তাই আসল run চলে যায়!)।
- Cron-এ চালালে log কোথায়? Terminal-এ চালালে অতিরিক্ত log।
- Production-এ একটি মান environment থেকে, test-এ command-line থেকে — কোনটি কার্যকর হলো?

ভালো argument parsing ও logging একটি script-কে **নিরাপদ, স্ব-ব্যাখ্যাকারী ও পরিচালনাযোগ্য** tool বানায়।

## 3. সহজ ভাষায় পরিচয়

### `getopts`

```bash
while getopts ':vno:' opt; do      # ':' শুরুতে = error নিজে সামলাব; 'o:' = -o-র value লাগে
  case $opt in
    v) verbose=$((verbose + 1)) ;;
    n) dry_run=1 ;;
    o) output=$OPTARG ;;
    :) echo "-$OPTARG needs a value" >&2; exit 2 ;;
    \?) echo "unknown option -$OPTARG" >&2; exit 2 ;;
  esac
done
shift $((OPTIND - 1))               # বাকি = positional argument
```

| পারে | পারে না |
|---|---|
| `-v -v`, `-vv`, `-vn`, `-o file`, `-ofile`, `--` | `--long` option |
| POSIX — সব shell-এ | Option-কে positional-এর পরে (`a -v`) |

### হাতে লেখা loop (long option)

```bash
while (( $# )); do
  case $1 in
    -s|--source) SOURCE=$2; shift ;;
    --source=*)  SOURCE=${1#*=} ;;        # parameter expansion (L04-02)
    --)          shift; break ;;
    -*)          usage_error "unknown option: $1" ;;
    *)           break ;;
  esac
  shift
done
```

`getopt` (একটি আলাদা util-linux program, `getopts` builtin নয়) long option ও argument-এর ক্রম বদলানো সমর্থন করে, কিন্তু portability ও quoting জটিল। এই lesson হাতে লেখা loop ব্যবহার করে।

### অগ্রাধিকার

```text
default  <  environment variable (BACKUP_DEST)  <  command-line (--dest)
```

Cron বা systemd-এ environment-এ মান রাখা যায় (`EnvironmentFile=`, L01-10); এককালীন পরিবর্তন command-line-এ।

### Logging-এর নিয়ম

- **stderr-এ** লিখুন — stdout শুধু ফলের জন্য (L04-01)।
- UTC ISO timestamp, level, script নাম ও PID রাখুন।
- `-v` বেশি, `-q` কম। Log file-এ console-এর filter প্রযোজ্য নয়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্তোরাঁর অর্ডার ফর্ম

- **Positional argument** (`$1 $2 $3`) = মুখে বলা অর্ডার: "দুটো, বড়, ঝাল ছাড়া" — কোনটি কোন বিষয়ের, অনুমান করতে হয়।
- **Named option** (`--size large --count 2`) = ছাপানো ফর্মের ঘর — ক্রম ভুল হলেও অর্থ স্পষ্ট।
- **Usage/help** = ফর্মের পেছনের নির্দেশিকা।
- **Environment variable** = নিয়মিত গ্রাহকের "সবসময় যেমন খাই" — আলাদা করে না বললে সেটাই।
- **Log** = রান্নাঘরের খাতা: কোন অর্ডার, কখন, কে নিল।

### Analogy কোথায় মেলে না

- ফর্মে ভুল ঘর পূরণ করলে ওয়েটার জিজ্ঞাসা করেন। Script-এ **অজানা option চুপচাপ উপেক্ষা** করলে ভুল কাজ চলে যায় (`--dryrun` বানান ভুল → আসল run)। তাই অজানা option-এ সবসময় exit ২ — কখনো উপেক্ষা নয়।
- ফর্মের মান মানুষ পড়ে বোঝে। Script-এ মান **যাচাই ও normalize** না করলে ভুল ব্যাখ্যা হয়: `./backups` আর `/srv/app/backups` একই জায়গা হতে পারে, এবং এক রূপে যাচাই পাস করে অন্য রূপে ব্যর্থ হয় (Section 9.3-এর আসল bug)।
- খাতায় সব লেখা থাকে। Log-এ `-q` দিলে terminal-এ কিছু দেখা যায় না, কিন্তু cron-এ সেটাই একমাত্র রেকর্ড — তাই file-এ level আলাদা রাখতে হয়।

## 5. Real-world engineering scenario — "Dry-run বানান ভুল, production data মুছে গেল"

**পরিস্থিতি:** একটি cleanup script:

```bash
DRY_RUN=0
for arg in "$@"; do
  [[ $arg == --dry-run ]] && DRY_RUN=1
done
```

একজন engineer production-এ "নিরাপদে" দেখতে চাইলেন কী মুছবে: `cleanup.sh --dryrun`। বানান ভুল option চুপচাপ উপেক্ষিত হলো। Script আসল মোছা চালিয়ে দিল।

**তিনটি সমস্যা:**

1. অজানা option উপেক্ষা।
2. বিপজ্জনক কাজই default (dry-run না দিলে আসল মোছা)।
3. কী করবে তার কোনো সারাংশ ও নিশ্চিতকরণ নেই।

**সমাধান:**

- কঠোর parsing: অজানা option-এ exit ২ (এই lesson-এর `backup.sh`)।
- বিপজ্জনক কাজে উল্টো default: `--execute` না দিলে শুধু dry-run (L04-06)।
- কাজের আগে `--print-config` বা সারাংশ, এবং interactive হলে নিশ্চিতকরণ।

**শিক্ষা:** Parser-এর কঠোরতা একটি নিরাপত্তা বৈশিষ্ট্য। ভুল input-এ "যতটা পারি করি" নয় — থামুন, এবং স্পষ্টভাবে বলুন কেন।

## 6. Diagram — একটি invocation-এর যাত্রা

```text
 BACKUP_DEST=/srv/env backup.sh -s "my app" --dest=./b -x '*.log' -x tmp -q --log-file run.log
        │
 parse_args   default → env (SOURCE, DEST from BACKUP_*) → CLI override
        │      unknown option / missing value / extra argument → usage_error → exit 2
        ▼
 validate     required? source is dir? → realpath both → dest inside source? → exit 2
        ▼
 --print-config?  → print & exit 0
        ▼
 build args array (excludes, --force-local) → dry-run? → print plan, exit 0
        ▼
 tar … → stdout: archive path (machine-readable)
         stderr: "2026-…Z INFO backup.sh[2018]: created …"   (console: -q হলে লুকানো)
         run.log: একই লাইন (file: সবসময় info+)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| `getopts` | Bash/POSIX builtin — short option parsing |
| `OPTARG` / `OPTIND` | বর্তমান option-এর value / পরের argument-এর index |
| Silent mode (`:` শুরুতে) | Error নিজে সামলানো |
| `getopt` (util-linux) | আলাদা program, long option সহ |
| `--` | Option-এর শেষ |
| Usage error | ভুল invocation — exit ২ |
| Configuration precedence | কোন উৎসের মান জেতে |
| Log level | debug < info < warn < error |
| `realpath -m` | Normalized absolute path (অস্তিত্ব না থাকলেও) |
| `--force-local` | GNU tar-কে `host:path` ব্যাখ্যা না করতে বলা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 `getopts`-এর state

`getopts` প্রতিবার ডাকলে `OPTIND` দেখে পরের option পড়ে। Loop শেষ হয় প্রথম non-option বা `--`-এ। তাই `script a -v`-এ `-v` positional থেকে যায় (Section 9.1)। একই function-এ দুবার parse করলে আগে `OPTIND=1` reset করতে হয়।

### 8.2 `need_value`-এর যুক্তি

`--dest` শেষ argument হলে `$2` থাকে না; `set -u`-এ crash হতো। `--dest --dry-run` হলে `--dry-run` dest হয়ে যেত। তাই `need_value`: পরের argument আছে, খালি নয়, এবং `-` দিয়ে শুরু নয়।

সীমা: `-` দিয়ে শুরু হওয়া আসল মান (যেমন dest `-backup`) এই নিয়মে প্রত্যাখ্যাত হয় — তখন `--dest=-backup` রূপ ব্যবহার করুন।

### 8.3 Console বনাম file level

একটিই `LOG_LEVEL` দিয়ে দুই জায়গা নিয়ন্ত্রণ করলে `-q` file-কেও খালি করে (Section 9.3-এর bug)। দুটি আলাদা threshold রাখা হয়েছে:

- Console: `-v`/`-q` অনুযায়ী।
- File: সবসময় info ও তার উপরে।

systemd-এর অধীনে চালালে stderr journald-এ যায় (L01-14) — সেখানে level-ভিত্তিক filter (`journalctl -p warning`) চাইলে structured logging বা `logger -p` বিবেচনা করুন।

### 8.4 Path normalization কেন নিরাপত্তা

"Dest source-এর ভেতরে কিনা" যাচাই string-এর তুলনা। `./backups` বনাম `/srv/app/backups`, বা `a/../a/x` বনাম `a/x` — একই জায়গা, ভিন্ন string। তুলনার আগে **দুটোকেই একই রূপে** (absolute, `..` ছাড়া, symlink resolve করা) আনতে হবে। এই নীতি সব path-ভিত্তিক নিরাপত্তা যাচাইয়ে প্রযোজ্য (path traversal, Module 19)।

## 9. Practical demonstration

### 9.1 `getopts`-এর আচরণ

File: [`code/L04-05/getopts_demo.sh`](code/L04-05/getopts_demo.sh)

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-05
bash getopts_demo.sh -v -v -n -o out.txt a b
bash getopts_demo.sh -vvn -oout.txt -- -file
bash getopts_demo.sh -o; bash getopts_demo.sh -z
bash getopts_demo.sh a -v
```

**আসল output:**

```text
verbose=2 dry_run=1 output=[out.txt] remaining(2): [a] [b]
verbose=2 dry_run=1 output=[out.txt] remaining(1): [-file]
error: -o needs a value
error: unknown option -z
verbose=0 dry_run=0 output=[] remaining(2): [a] [-v]
```

- `-vvn -oout.txt` = আলাদা লেখার সমান।
- `--`-এর পরে `-file` positional (যেমন `-` দিয়ে শুরু file name)।
- শেষ লাইন: `a`-তে getopts থেমেছে, `-v` option হিসেবে পড়া হয়নি।

### 9.2 `backup.sh`

File: [`code/L04-05/backup.sh`](code/L04-05/backup.sh)

```bash
T=$(mktemp -d); mkdir -p "$T/my app/logs"; echo data > "$T/my app/config.ini"; echo log > "$T/my app/logs/a.log"
BACKUP_DEST=/env/dest bash backup.sh --source "$T/my app" --print-config
BACKUP_DEST=/env/dest bash backup.sh -s "$T/my app" --dest="$T/cli dest" -x '*.log' --exclude=tmp --print-config
bash backup.sh -n -s "$T/my app" -d "$T/backups"
out=$(bash backup.sh -q --log-file "$T/backup.log" -s "$T/my app" -d "$T/backups" -x '*.log'); tar -tzf "$out"; cat "$T/backup.log"
bash backup.sh --frobnicate; echo "exit=$?"
```

**আসল output (সংক্ষেপিত; path, সময় ও PID ভিন্ন হবে):**

```text
source=/tmp/tmp.v0YVsJB6UQ/my app
dest=/env/dest
...
dest=/tmp/tmp.v0YVsJB6UQ/cli dest
exclude=*.log
exclude=tmp

2026-10-26T20:00:34Z INFO  backup.sh[831]: dry-run: would create /tmp/.../backups/my app-20261026T200034Z.tar.gz
/tmp/.../backups/my app-20261026T200034Z.tar.gz

my app/
my app/config.ini
my app/logs/
2026-10-26T20:01:26Z INFO  backup.sh[2018]: created /tmp/.../backups/my app-20261026T200126Z.tar.gz (1.0K)

2026-10-26T20:00:35Z ERROR backup.sh[857]: unknown option: --frobnicate
Try 'backup.sh --help'.
exit=2
```

- Environment-এর dest প্রথমবার কার্যকর; `--dest=` দিলে CLI জেতে।
- `-x` দুবার দেওয়া যায় (array, L04-02)।
- `*.log` archive-এ নেই।
- `-q`-তে terminal শান্ত, কিন্তু log file-এ রেকর্ড আছে।
- stdout-এ শুধু archive-এর path — `out=$(...)` দিয়ে পরের ধাপে ব্যবহারযোগ্য।

### 9.3 তিনটি আসল bug

1. **`-q` দিলে log file খালি থাকত।** একটিই level দুই জায়গায় প্রযোজ্য ছিল। প্রথম সংস্করণে `cat "$T/backup.log"` বলেছিল `No such file or directory`। সমাধান: আলাদা `FILE_LOG_LEVEL` (Section 8.3)।
2. **Source-এর ভেতরে dest যাচাই এড়ানো যেত।** শুধু source absolute করা হয়েছিল। ফলে source-এর ভেতর থেকে চালানো `-s . -d ./backups` এবং `-d "my app/../my app/x"` দুটোই প্রথম সংস্করণে **গৃহীত হয়েছিল** (আসল output: `dry-run: would create ./backups/...`)। এতে backup নিজের ভেতরেই জমত, এবং প্রতিবার আগের backup-ও archive-এ ঢুকত। সমাধান: দুটোকেই `realpath` দিয়ে normalize করা। এখন দুটোই exit ২।
3. **`tar` path-এর `:`-কে remote host ভাবল।** Test-এ dest ছিল `C:/Users/...` (Windows path), আর GNU tar বলল `Cannot connect to C: resolve failed` — `host:file` রীতি। Linux-এও dest-এ বা নামে `:` থাকলে একই হবে (timestamp-এ `%H:%M:%S` দিলেও)। সমাধান: `--force-local`। যাচাই: `with:colon` নামের directory-তে backup সফল।

**শিক্ষা:** Option parser ও path handling-এ "স্বাভাবিক" input দিয়ে test যথেষ্ট নয় — relative path, `..`, space, `:` ও `-` দিয়ে শুরু হওয়া মান দিয়ে test করুন।

### 9.4 Ubuntu-তে cron/systemd থেকে

```bash
# /etc/default/app-backup  (EnvironmentFile)
BACKUP_SOURCE=/srv/app
BACKUP_DEST=/var/backups/app
```

```ini
# systemd service (L01-10, L01-11)
[Service]
EnvironmentFile=/etc/default/app-backup
ExecStart=/usr/local/bin/backup.sh -q --log-file /var/log/app-backup.log
```

`journalctl -u app-backup` (stderr, warning ও error) এবং `/var/log/app-backup.log` (info-সহ সম্পূর্ণ রেকর্ড)। Log file-এর rotation: logrotate (L01-14)।

> **Fedora-তে:** একই; SELinux-এ service-কে `/var/log/app-backup.log`-এ লিখতে দিতে সঠিক context লাগতে পারে (`restorecon`, L01-17)।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l04_05.py`](code/L04-05/test_l04_05.py)-এর ৯টি test:

- **getopts (৩টি):** যুক্ত flag ও `--`; প্রথম non-option-এ থামা; দুই রকম error।
- **backup (৬টি):**
  - CLI > env।
  - Short ও long রূপ ও পুনরাবৃত্তি।
  - আসল archive-এ exclude ও `-q`-তে log file।
  - Dry-run-এ কিছু তৈরি না হওয়া।
  - পাঁচটি usage error।
  - Relative ও `..`-যুক্ত পথে source-এর ভেতরে dest প্রত্যাখ্যান।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `SOURCE=${BACKUP_SOURCE:-}` আগে, পরে CLI | অগ্রাধিকার | Env default, CLI override |
| `need_value` | Value আছে ও option নয় | `set -u` crash ও ভুল ব্যাখ্যা এড়ায় |
| `--opt=*` শাখা | `${1#*=}` | দুই রূপই সমর্থন |
| `-*) usage_error` | অজানা option-এ exit ২ | Section 5 |
| `EXCLUDES+=(…)` ও `${arr[@]+"${arr[@]}"}` | খালি array নিরাপদে expand | `set -u`-এ খালি array (পুরোনো Bash) |
| `realpath` / `realpath -m` | Normalize | Section 8.4 |
| `--print-config` | চূড়ান্ত মান দেখা | Debug ও audit |
| stdout-এ শুধু archive path | Machine-readable ফল | Pipeline-যোগ্য |
| `--force-local` | `:`-যুক্ত path নিরাপদ | Section 9.3 |

**Bash কেন এখানে, কোথায় নয়:** ১০–১৫টি option পর্যন্ত হাতে লেখা loop ঠিক আছে। এর বেশি, subcommand (`tool backup`, `tool restore`), type-যুক্ত মান বা config file লাগলে Python-এর `argparse` অনেক নিরাপদ ও স্বয়ংক্রিয় help দেয় (L04-08)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `getopts_demo.sh a -v` | `-v` positional হিসেবে থাকে |
| `BACKUP_DEST=x backup.sh -s S --dest=y --print-config` | `dest=…/y` |
| `backup.sh -q --log-file L ...` | terminal নীরব, L-এ INFO |
| `backup.sh -s . -d ./b` (source-এর ভেতরে) | exit ২ |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| ভুল বানানের option চুপচাপ উপেক্ষিত | Parser-এ `*)` শাখা নেই | অজানা option-এ exit ২ |
| `$2: unbound variable` | শেষ option-এর value নেই | `need_value` |
| দ্বিতীয়বার parse কাজ করে না | `OPTIND` reset হয়নি | `OPTIND=1` |
| Option positional-এর পরে কাজ করে না | getopts প্রথম non-option-এ থামে | Option আগে দিন, বা হাতে লেখা loop |
| `-q`-তে log file খালি | একই level | আলাদা file level |
| Path যাচাই এড়ানো যায় | String তুলনা normalize ছাড়া | `realpath` |
| `tar: Cannot connect to X: resolve failed` | Path-এ `:` | `--force-local` |
| Help পুরোনো | Help আলাদা জায়গায় লেখা | Header থেকে `sed` দিয়ে তৈরি |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - কঠোর parsing ও input normalization ব্যবহার করুন।
  - Secret কখনো option-এ নয় (`ps`-এ দেখা যায় ও shell history-তে থাকে) — environment বা `--password-file` দিন।
  - `--print-config`-এ secret mask করুন।
  - Log-এ user input `%q` বা নিরাপদভাবে দেখান।
  - Log file-এর permission (৬৪০) রাখুন।
- **Performance:**
  - Parsing নগণ্য খরচ।
  - Log-এ প্রতি লাইনে `date` একটি process তৈরি করে — অনেক লাইনের log-এ Bash ৫-এর `printf '%(%Y-%m-%dT%H:%M:%S)T'` builtin দ্রুত।
- **Cost:**
  - ভুল option-এ উল্টো কাজের খরচ (Section 5) সবচেয়ে বড়।
  - পরিষ্কার log incident-এর সময় কমায়।

## 14. Hands-on exercise

1. `backup.sh`-এ `--keep N` option যোগ করুন (integer যাচাইসহ; rotation-এর কাজ L04-06-এ)। Test লিখুন: `--keep abc` → exit ২।
2. `log()`-এ `date`-এর বদলে `printf '%(%Y-%m-%dT%H:%M:%SZ)T'` ব্যবহার করুন (`TZ=UTC`)। ১০,০০০ log লাইনে সময় তুলনা করুন।
3. `getopts_demo.sh`-কে একটি function-এর ভেতরে নিয়ে দুবার ডাকুন — দ্বিতীয়বার কী হয়? `local OPTIND` দিয়ে ঠিক করুন।
4. `backup.sh`-এ `--config FILE` যোগ করুন (`KEY=VALUE` লাইন, `source` না করে নিরাপদে parse — কেন `source` বিপজ্জনক?)। অগ্রাধিকার হবে default < config file < env < CLI।
5. util-linux-এর `getopt` দিয়ে একই parser লিখে তুলনা করুন — কোনটি বেশি পাঠযোগ্য?

## 15. Mini-project — Log archiver (তৃতীয় অংশ)

`archive_logs.sh`-এ পূর্ণ CLI যোগ করুন:

- `--dir`, `--days`, `--dest`, `--execute` (default dry-run!), `-v`/`-q`, `--log-file`, `--print-config`, `--help`।
- Environment variable (`ARCHIVE_DIR` ইত্যাদি)।
- Usage error-এ exit ২।
- প্রতিটি option-এর জন্য Python test।

## 16. Interview প্রশ্ন

1. `getopts` ও `getopt`-এর পার্থক্য কী?
2. `getopts`-এ optstring-এর শুরুর `:`-এর অর্থ কী?
3. Long option কীভাবে parse করবেন?
4. অজানা option উপেক্ষা করা কেন বিপজ্জনক?
5. Configuration-এর অগ্রাধিকার কেমন হওয়া উচিত, এবং কেন?
6. Script-এর log কোথায় যাবে? `-q` কী লুকাবে?
7. Path তুলনার আগে normalize কেন জরুরি?

## 17. Self-assessment প্রশ্ন

1. অর্ডার ফর্ম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি সমস্যা কী?
3. Section 9.3-এর তিনটি bug কী, এবং প্রতিটি কোন test ধরে?
4. `need_value`-এর সীমা কী, এবং তার বিকল্প কী?
5. `getopts_demo.sh a -v`-এ `-v` কেন option হিসেবে পড়া হলো না?

## 18. সংক্ষিপ্ত সারাংশ

- `getopts`: short option, যুক্ত flag, silent mode; long option ও ক্রম বদল পারে না।
- Long option: `while`/`case`, `--opt VALUE` ও `--opt=VALUE`, `need_value`, অজানা option-এ exit ২।
- অগ্রাধিকার: default < env < CLI; `--print-config`।
- Log stderr-এ, UTC + level + PID; console ও file-এর level আলাদা।
- Path যাচাইয়ের আগে normalize; `tar --force-local`।
- কঠিন input (relative, `..`, space, `:`, `-`) দিয়ে test করুন।

## 19. Completion checklist

- [ ] `getopts_demo.sh`-এর পাঁচটি ফল ব্যাখ্যা করতে পারি
- [ ] `backup.sh` env ও CLI দুইভাবে চালিয়েছি
- [ ] Section 9.3-এর bug-গুলো নিজে পুনরুৎপাদন করেছি (পুরোনো রূপে)
- [ ] `python3 -m unittest -v`-এ ৯টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash Reference Manual — Bourne Shell Builtins (`getopts`): https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html
- POSIX — Utility Argument Syntax: https://pubs.opengroup.org/onlinepubs/9799919799/basedefs/V1_chap12.html
- `getopt(1)` (util-linux): https://man7.org/linux/man-pages/man1/getopt.1.html
- GNU tar manual — `--force-local`: https://www.gnu.org/software/tar/manual/html_node/local-and-remote-archives.html
- `realpath(1)` (GNU coreutils): https://www.gnu.org/software/coreutils/manual/html_node/realpath-invocation.html
- BashFAQ/035 — How can I handle command-line options?: https://mywiki.wooledge.org/BashFAQ/035

---

**পরের lesson:** L04-06 — Safe ও idempotent script: locking, temp file, dry-run
