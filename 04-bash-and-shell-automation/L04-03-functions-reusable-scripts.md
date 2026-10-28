# L04-03 — Function ও reusable script

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L04-02 — Variable, array ও expansion](L04-02-variables-arrays-expansion.md) |
| **Label** | — |
| **Tested** | `lib/common.sh` ও `disk_check.sh`: ৯টি test পাস — library সরাসরি চালানো প্রত্যাখ্যান ও দুবার source নিরাপদ, `join_by`, `to_bytes`, `is_true`, `require_cmd`, log level, `retry` (সফল ও হার মানা), threshold ও exit code, space-যুক্ত mount ও source (GNU Bash 5.3.9, Windows/Git Bash)। **এই machine-এর আসল `df` দিয়ে চালাতে গিয়ে parser-এর একটি bug ও library-র একটি bug ধরা পড়েছে** — Section 9.3। Ubuntu-র আসল `df`-এ চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Bash function-এর গঠন: argument (`$1`, `$@`), **return code** বনাম **output (stdout)**।
- `local`-এর গুরুত্ব — default-এ সব variable global।
- একটি **library** (`lib/common.sh`): source করা, দুবার source হওয়া থেকে সুরক্ষা, সরাসরি চালানো থেকে সুরক্ষা।
- সাধারণ helper: log level, `die`, `require_cmd`, backoff সহ `retry`।
- Function ও `set -e`-এর সম্পর্ক (L04-01-এর case ৬)।
- Monitoring-ধাঁচের check script ও তার exit code চুক্তি।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি team-এর ২০টি script, প্রতিটিতে নিজের মতো `log()`, `die()`, "command আছে কিনা" পরীক্ষা — কোনোটি stdout-এ log লেখে, কোনোটি exit code ভুল দেয়, কোনোটি retry-তে অসীম loop। একটি bug ঠিক করতে ২০ জায়গায় যেতে হয়।

Function ও library দেয়:

- **একবার লেখা, সব জায়গায় একই আচরণ।**
- আলাদাভাবে test করা যায় (এই lesson-এর ৯টি test)।
- Script ছোট ও পাঠযোগ্য হয় — `main` পড়েই বোঝা যায় কী করে।

## 3. সহজ ভাষায় পরিচয়

```bash
greet() {                    # function সংজ্ঞা
  local name=$1              # প্রথম argument; local = শুধু এই function-এ
  printf 'hello, %s\n' "$name"    # "ফেরত মান" = stdout-এ লেখা
  [[ -n $name ]]             # return code = শেষ command-এর status (০ = সফল)
}

msg=$(greet "Rina")          # output ধরা
if greet ""; then ...; fi    # return code দিয়ে সিদ্ধান্ত
```

| ধারণা | Bash-এ |
|---|---|
| Argument | `$1`, `$2`, `"$@"`, `$#` |
| "Return value" (data) | stdout-এ লিখুন, `$(f)` দিয়ে ধরুন |
| সফলতা/ব্যর্থতা | `return N` (০–২৫৫) বা শেষ command-এর status |
| Local variable | `local x` — না দিলে global, অন্য function-এর variable নষ্ট হয় |
| Library | `source file.sh` — একই shell-এ function যোগ |

**`return` বনাম `exit`:** `return` শুধু function শেষ করে; `exit` পুরো script শেষ করে। Library-তে `exit` সতর্কভাবে ব্যবহার করুন — সেটা caller-এর script বন্ধ করে দেবে (`die`-এর ক্ষেত্রে ইচ্ছাকৃত)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রান্নাঘরের রেসিপি কার্ড

- **Function** = একটি রেসিপি কার্ড: "ভাত রান্না — চাল (argument) দাও, ভাত (output) পাবে, পুড়ে গেলে লাল কার্ড (return code)"।
- **Library** = রেসিপির বই — প্রতিটি রান্নায় নতুন করে লেখার দরকার নেই।
- **`local`** = রেসিপির নিজের বাটি — অন্য রান্নার বাটির সাথে মিশে যায় না।

### Analogy কোথায় মেলে না

- রেসিপি একটি জিনিস ফেরত দেয়। Bash function **দুটি আলাদা চ্যানেলে** ফেরত দেয় — data (stdout) ও status (return code) — এবং এর বাইরে কিছু ফেরত দিতে পারে না। Array ফেরত দিতে হয় newline-বিভক্ত output বা nameref (`local -n`) দিয়ে।
- রেসিপির বাটি নিজে থেকে আলাদা থাকে। Bash-এ `local` **ভুলে গেলে** variable global হয়ে যায় — দুটি function একই `i` ব্যবহার করলে একটি অন্যটির loop নষ্ট করে, কোনো error ছাড়াই।
- রেসিপি বই খুললে রান্না শুরু হয় না। Library source করলে তার **top-level code তখনই চলে** — তাই library-তে শুধু function সংজ্ঞা ও নিরাপদ সেটআপ রাখুন, কোনো কাজ নয়।

## 5. Real-world engineering scenario — "Retry-এর কারণে outage দীর্ঘ হলো"

**পরিস্থিতি:** একটি deploy script প্রতিটি server-এ health check করত:

```bash
until curl -sf "http://$host/health"; do sleep 1; done
```

একটি নতুন release-এ application শুরুই হতে পারছিল না (config ভুল)। Script অসীম loop-এ আটকে গেল — pipeline চলতেই থাকল, কেউ rollback করল না। তার উপর ২০টি server প্রতি সেকেন্ডে health endpoint-এ চাপ দিচ্ছিল।

**সমস্যা:** কোনো সীমা নেই, কোনো backoff নেই, কোনো স্পষ্ট ব্যর্থতা নেই।

**সমাধান (`lib/common.sh`-এর `retry`):**

```bash
retry 5 2 curl -sf --max-time 5 "http://$host/health" || die "health check failed on $host" 1
```

- সর্বোচ্চ ৫ বার; অপেক্ষা ২, ৪, ৮, ১৬ সেকেন্ড (exponential backoff)।
- শেষে স্পষ্ট ব্যর্থতা ও exit code — pipeline থেমে rollback শুরু করতে পারে (Module 16)।
- প্রতিটি চেষ্টা log-এ — পরে বোঝা যায় কী ঘটেছিল।
- বাস্তবে আরো যোগ করুন: **jitter** (এলোমেলো অপেক্ষা), যাতে অনেক client একসাথে retry না করে।

**শিক্ষা:** Retry একটি শক্তিশালী কিন্তু বিপজ্জনক tool। এর **সীমা, backoff ও স্পষ্ট হার** থাকতে হবে। এমন helper library-তে একবার সঠিকভাবে লিখুন।

## 6. Diagram — script ও library

```text
 disk_check.sh                                 lib/common.sh  (source করা, চালানো নয়)
 ┌────────────────────────────┐   source      ┌──────────────────────────────────────┐
 │ set -Eeuo pipefail          │ ───────────►  │ guard: সরাসরি চালালে exit 2           │
 │ source lib/common.sh        │               │ guard: দুবার source হলে return        │
 │ main() {                    │               │ log_debug/info/warn/error → stderr    │
 │   parse args (getopts)      │  ব্যবহার করে  │ die msg [code]                        │
 │   require_cmd df  ──────────┼─────────────► │ require_cmd cmd...                    │
 │   loop: check_line ...      │               │ retry attempts delay cmd...           │
 │   log_info "checked N"  ────┼─────────────► │ is_true, join_by, to_bytes            │
 │   return worst              │               └──────────────────────────────────────┘
 │ }                           │
 │ main "$@"                   │   stdout: "WARNING /var/lib/postgresql (xfs) 84%"  ← ফল
 └────────────────────────────┘   stderr: "2026-...Z INFO disk_check.sh: checked 5"  ← log
                                   exit:   0 OK / 1 WARNING / 2 CRITICAL / 3 UNKNOWN
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Function | নামযুক্ত command-সমষ্টি |
| Positional parameter | `$1`, `$2`, …, `$@`, `$#` |
| Return status | ০–২৫৫; ০ = সফল |
| `local` | Function-এর নিজস্ব variable (dynamic scope) |
| `source` / `.` | অন্য file-এর code বর্তমান shell-এ চালানো |
| Include guard | দুবার source হওয়া আটকানোর variable |
| `BASH_SOURCE` | বর্তমান file-এর path (source হলেও) |
| Nameref (`local -n`) | অন্য variable-এর নামে reference (Bash ৪.৩+) |
| Exponential backoff | প্রতি ব্যর্থতায় অপেক্ষা দ্বিগুণ |
| Jitter | Retry-এর সময়ে এলোমেলোতা |
| Nagios exit code | ০ OK, ১ WARNING, ২ CRITICAL, ৩ UNKNOWN |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Dynamic scope

Bash-এর `local` **dynamic scope** অনুসরণ করে: f-এর local variable, f থেকে ডাকা g-ও দেখতে পায় (এবং বদলাতে পারে)। এটা বেশিরভাগ ভাষার (lexical scope) থেকে ভিন্ন। সতর্কতা:

- Helper function-এ নিজের সব variable `local` দিন।
- Caller-এর variable বদলাতে চাইলে স্পষ্টভাবে nameref (`local -n out=$1`) ব্যবহার করুন।

### 8.2 Function ও `set -e`

L04-01-এর case ৬: `if f; then` বা `f || ...`-এ ডাকলে f-এর ভেতরে `set -e` বন্ধ থাকে। তাই গুরুত্বপূর্ণ function নিজেই ব্যর্থতা পরীক্ষা করে `return 1` দেবে — `set -e`-এর উপর নির্ভর করবে না। `disk_check.sh`-এ `check_line ... || rc=$?` লেখা হয়েছে, কারণ non-zero return (WARNING = ১) এখানে ব্যর্থতা নয়, তথ্য। `|| rc=$?` না থাকলে `set -e` script থামিয়ে দিত।

### 8.3 Library-র তিনটি নিরাপত্তা

1. **সরাসরি চালানো নিষেধ:** `[[ ${BASH_SOURCE[0]} == "$0" ]]` সত্য হলে file-টি source না হয়ে চালানো হয়েছে।
2. **Include guard:** `_COMMON_SH_LOADED` — দুবার source হলে `readonly`-র error বা আবার define এড়ায়।
3. **Path:** `source "$(dirname -- "${BASH_SOURCE[0]}")/lib/common.sh"` — script যেকোনো directory থেকে চালানো হোক, library খুঁজে পায় (`source lib/common.sh` শুধু তখনই কাজ করে যখন বর্তমান directory সঠিক)।

### 8.4 Output parsing — ডান দিক থেকে

`df`-এর output-এ প্রথম column (source) ও শেষ column (mount point) দুটোতেই space থাকতে পারে। `read fs type size ...` প্রথম space-এ ভাঙে, ফলে সব column সরে যায়। নির্ভরযোগ্য উপায়গুলো:

- যে অংশে space থাকতে পারে না (সংখ্যা, `NN%`), সেগুলো দিয়ে **regex-এ নোঙর** করা — এই lesson-এর সমাধান।
- Machine-readable output ব্যবহার করা: `findmnt -J`, `df --output`, `lsblk -J`।
- `/proc/self/mountinfo` পড়া, যেখানে space `\040` হিসেবে escape করা (L01-12)।

## 9. Practical demonstration

### 9.1 Library function

Files: [`code/L04-03/lib/common.sh`](code/L04-03/lib/common.sh), [`disk_check.sh`](code/L04-03/disk_check.sh), [`sample-df.txt`](code/L04-03/sample-df.txt) (হাতে তৈরি, Ubuntu-র `df -PT`-এর আকারে)।

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-03
bash lib/common.sh; echo "exit=$?"
bash -c 'source lib/common.sh; source lib/common.sh
  join_by ", " a "b c" d; join_by - solo
  to_bytes 1.5M; to_bytes 2g; to_bytes 512; to_bytes 10XB || echo invalid
  is_true YES && echo yes; is_true 0 || echo no
  require_cmd bash nosuchcmd1 nosuchcmd2; echo rc=$?'
```

**আসল output:**

```text
lib/common.sh is a library: source it, do not run it
exit=2
a, b c, d
solo
1572864
2147483648
512
invalid
yes
no
2026-10-26T19:52:46Z ERROR bash: missing required command(s): nosuchcmd1 nosuchcmd2
rc=1
```

দুবার source করাতেও কোনো error নেই (include guard)। `require_cmd` প্রথম অনুপস্থিত command-এ থামে না — **সবগুলোর** নাম একবারে বলে, যাতে user একবারেই সব install করতে পারেন।

### 9.2 Disk check

```bash
bash disk_check.sh -i sample-df.txt; echo "exit=$?"
LOG_LEVEL=debug bash disk_check.sh -i sample-df.txt -w 95 -c 99; echo "exit=$?"
bash disk_check.sh -w 90 -c 80 -i sample-df.txt; echo "exit=$?"
```

**আসল output:**

```text
OK       / (ext4) 48%
OK       /boot (ext4) 20%
WARNING  /var/lib/postgresql (xfs) 84%
CRITICAL /var/log (ext4) 94%
OK       /mnt/backup disk (ext4) 12%
2026-10-26T19:52:45Z INFO  disk_check.sh: checked 5 filesystem(s), warn=80% crit=90%
exit=2
...
2026-10-26T19:52:07Z DEBUG disk_check.sh: skip /run (tmpfs)
...
exit=0
2026-10-26T19:52:07Z ERROR disk_check.sh: need integer thresholds with WARN < CRIT <= 100 (got 90/80)
exit=3
```

(দ্বিতীয় ও তৃতীয় run একটি আগের সংস্করণ থেকে — space-যুক্ত mount যোগ হওয়ার আগে; format একই।)

- Exit code = সবচেয়ে খারাপ অবস্থা (২ = CRITICAL)। Monitoring system (Module 17) সরাসরি ব্যবহার করতে পারে।
- `tmpfs` ও `overlay` default-এ বাদ — container layer বা RAM disk-এর "ভরা" অবস্থা সাধারণত alert-যোগ্য নয়।
- `/mnt/backup disk` — space-যুক্ত mount point সঠিকভাবে পড়া হয়েছে।

### 9.3 আসল `df`-এ ধরা পড়া দুটি bug

প্রথম সংস্করণে loop ছিল `while read -r fs type size used avail pct mount`। নমুনা file-এ ঠিক কাজ করছিল। কিন্তু এই machine-এর (Windows/Git Bash) আসল `df -PT` চালাতেই ফল এল:

```text
CRITICAL 83% / (Files/Git) 56178848%
```

আসল `df`-এর লাইনটি ছিল:

```text
Filesystem           Type 1024-blocks      Used Available Capacity Mounted on
C:/Program Files/Git ntfs   324094972 267916184  56178788      83% /
```

Source-এর নামে space (`Program Files`) থাকায় সব column এক ঘর করে সরে গেছে। Linux-এও mount point-এর নামে space থাকতে পারে (`/mnt/backup disk`)।

সমাধান: regex দিয়ে লাইন **ডান দিক থেকে নোঙর করা** (Section 8.4)। এখন আসল output:

```text
WARNING  / (ntfs) 83%
OK       /d (ntfs) 38%
```

দ্বিতীয় bug: `to_bytes`-এ unit-এর জন্য associative array-তে খালি key `[""]` রাখা হয়েছিল — Bash বলে `bad array subscript`। `case` দিয়ে ঠিক করা হয়েছে।

**শিক্ষা:** হাতে তৈরি নমুনা দিয়ে test যথেষ্ট নয় — **আসল output-এ** চালান, এবং কঠিন রূপ (space) নমুনায় যোগ করুন। Test `test_source_with_spaces_parses` এখন এই machine-এর আসল লাইনটি দিয়েই regression ধরে।

### 9.4 Ubuntu-তে

```bash
bash disk_check.sh                       # আসল df -PT
bash disk_check.sh -x tmpfs -x squashfs  # snap-এর squashfs mount বাদ (Ubuntu-তে অনেক থাকে)
findmnt -J -o TARGET,FSTYPE,USE%         # machine-readable বিকল্প (util-linux)
```

> **Fedora-তে:** একই script চলে; `snap`-এর squashfs mount সাধারণত থাকে না। Btrfs (Fedora-র default)-এ `df` একটি subvolume-এর জন্য পুরো pool-এর হিসাব দেখায় — সঠিক ছবির জন্য `btrfs filesystem usage /`।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l04_03.py`](code/L04-03/test_l04_03.py)-এর ৯টি test:

- **Library (৬টি):**
  - সরাসরি চালানো প্রত্যাখ্যান ও দুবার source।
  - `join_by` ও `to_bytes`।
  - `is_true` ও `require_cmd` (সব অনুপস্থিত command একবারে)।
  - Log level, এবং stdout-এ কিছু নেই।
  - `retry` তৃতীয় চেষ্টায় সফল (দুটি retry বার্তা)।
  - `retry` হার মানলে শেষ exit code (৭) ফেরত।
- **Disk check (৩টি):**
  - নমুনায় অবস্থা ও exit ২।
  - Threshold অনুযায়ী exit ১/০/৩।
  - Space-যুক্ত source-এর আসল লাইন।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `_log` + `_log_rank` | Level অনুযায়ী filter | `LOG_LEVEL=debug` দিয়ে বিস্তারিত, default-এ শান্ত |
| `date -u +...Z` | UTC ISO timestamp | বিভিন্ন timezone-এর server-এর log মেলানো (Module 17) |
| `require_cmd`-এ array জমানো | সব অনুপস্থিত একবারে | ব্যবহারকারীর সময় বাঁচে |
| `retry`-এ `"$@" && return 0` | Command array হিসেবে | Quote অক্ষত; `eval` নয় |
| `delay=$((delay * 2))` | Exponential backoff | Server-এ চাপ কমে |
| `printf '%s' "$first" "${@/#/$sep}"` | প্রতিটি পরের item-এর আগে separator | Loop ছাড়া join |
| `to_bytes`-এ `awk` | দশমিক গুণ | Bash শুধু integer গাণিতিক জানে |
| `check_line ... \|\| rc=$?` | Non-zero return ধরে রাখা | WARNING/CRITICAL তথ্য, script-এর ব্যর্থতা নয় |
| `main "$@"` ও `return "$worst"` | Script-এর exit = main-এর return | Top-level-এ কোনো আলগা code নেই |

**Bash কেন এখানে, কোথায় নয়:** `df`-এর মতো command-এর output-এর উপর ছোট check ও helper library-তে Bash স্বাভাবিক। Parsing জটিল হলে (Section 9.3 দেখাল এটা কত দ্রুত জটিল হয়) বা JSON লাগলে Python ভালো। L04-08-এ সিদ্ধান্তের নিয়ম।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `bash lib/common.sh` | "is a library", exit ২ |
| `disk_check.sh -i sample-df.txt` | ৫টি filesystem, exit ২ |
| `disk_check.sh -w 90 -c 80 ...` | exit ৩ (UNKNOWN) |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Function-এর পরে অন্য জায়গার variable বদলে গেছে | `local` ভুলে যাওয়া | সব helper variable `local` |
| `return 300` → ৪৪ | Return ০–২৫৫ (mod ২৫৬) | Data stdout-এ, status ছোট সংখ্যায় |
| `x=$(f)`-এ log-ও ধরা পড়ে | Log stdout-এ লেখা | Log সবসময় `>&2` |
| `source: lib/common.sh: No such file` | Relative path, ভিন্ন working directory | `BASH_SOURCE`-ভিত্তিক path |
| Library source করতেই কাজ শুরু | Top-level-এ code | শুধু function সংজ্ঞা |
| WARNING-এ script নিজেই থেমে যায় | `set -e` + non-zero return | `\|\| rc=$?` |
| Column-ভিত্তিক parsing ভুল | Space-যুক্ত field | Regex নোঙর বা machine-readable output |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Library-র path নির্দিষ্ট রাখুন (`BASH_SOURCE`-ভিত্তিক)। `PATH` বা বর্তমান directory থেকে source করলে কেউ নকল library বসাতে পারে।
  - Library file-এর permission: শুধু owner লিখতে পারবে।
  - `retry`-তে secret-যুক্ত command log হলে secret log-এ যায় — এমন ক্ষেত্রে message-এ command-এর বদলে বর্ণনা দিন।
- **Performance:**
  - Function call সস্তা (একই process)। `$(f)` একটি subshell তৈরি করে — loop-এর ভেতরে লক্ষ লক্ষ বার হলে খরচ আছে।
  - `to_bytes`-এর `awk` প্রতিবার একটি process।
- **Cost:**
  - Backoff ছাড়া retry downstream-এর outage দীর্ঘ করে এবং cloud API-তে rate limit বা বিল বাড়ায় (Section 5)।

## 14. Hands-on exercise

1. `retry`-তে jitter যোগ করুন: প্রতিটি অপেক্ষায় `RANDOM` দিয়ে ০–৫০% যোগ। Test লিখুন (সময় নয়, retry সংখ্যা যাচাই করুন)।
2. `lib/common.sh`-এ `trim()` (শুরু ও শেষের whitespace বাদ) লিখুন, শুধু parameter expansion দিয়ে।
3. `disk_check.sh`-এ `-p` option যোগ করুন — Prometheus textfile format-এ output (`disk_used_percent{mount="/"} 48`)। Mount-এ `"` থাকলে কী করবেন?
4. দুটি function একই global `i` ব্যবহার করলে কী হয়, তার একটি ছোট demo লিখুন। তারপর `local` দিয়ে ঠিক করুন।
5. Ubuntu VM-এ `disk_check.sh` চালান। Snap-এর squashfs mount কয়টি? `-x squashfs` default-এ আছে কেন?

## 15. Mini-project — Team-এর shell library

`lib/common.sh`-কে বাড়িয়ে নিজের team-এর library বানান:

- `confirm` (TTY না থাকলে `ASSUME_YES` env দেখে)।
- `with_lock` (L04-06-এর preview)।
- `version_ge` (`sort -V` দিয়ে)।
- প্রতিটি function-এর জন্য test।

Module 08-এর Ansible-এর বিকল্প হিসেবে নয়, বরং ছোট ops script-এর জন্য।

## 16. Interview প্রশ্ন

1. Bash function কীভাবে মান ফেরত দেয়? `return`-এর সীমা কী?
2. `local` কেন গুরুত্বপূর্ণ? Bash-এর scope কেমন?
3. একটি script সরাসরি চালানো হয়েছে নাকি source করা হয়েছে, তা কীভাবে বুঝবেন?
4. Exponential backoff কী, এবং retry-তে সীমা কেন দরকার?
5. `if f; then`-এ ডাকা function-এর ভেতরে `set -e`-এর কী হয়?
6. Monitoring check-এর exit code রীতি কী?

## 17. Self-assessment প্রশ্ন

1. রেসিপি কার্ড analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর loop-এর তিনটি সমস্যা কী?
3. Section 9.3-এ আসল `df`-এ কী ভুল হয়েছিল, এবং regex-এর কোন অংশ এটা ঠিক করে?
4. `check_line ... || rc=$?` না থাকলে কী হতো?
5. Library-র তিনটি নিরাপত্তা ব্যবস্থা কী?

## 18. সংক্ষিপ্ত সারাংশ

- Function: data stdout-এ, সফলতা return code-এ; সব variable `local`।
- Library: source করা হয়; সরাসরি চালানো ও দুবার source হওয়া থেকে সুরক্ষিত; `BASH_SOURCE`-ভিত্তিক path।
- Log stderr-এ, level ও UTC timestamp সহ; `die` স্পষ্ট exit code দেয়।
- `retry`-তে সীমা, backoff ও স্পষ্ট হার।
- Non-zero return-কে তথ্য হিসেবে ধরতে `|| rc=$?`।
- আসল output-এ test করুন — space-যুক্ত field column-ভিত্তিক parsing ভাঙে।

## 19. Completion checklist

- [ ] `lib/common.sh`-এর প্রতিটি function নিজে ব্যবহার করেছি
- [ ] নিজের machine-এর আসল `df`-এ `disk_check.sh` চালিয়েছি
- [ ] `retry`-তে jitter যোগ করেছি (Exercise ১)
- [ ] `python3 -m unittest -v`-এ ৯টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash Reference Manual — Shell Functions: https://www.gnu.org/software/bash/manual/html_node/Shell-Functions.html
- GNU Bash Reference Manual — Bash Builtins (`source`, `local`): https://www.gnu.org/software/bash/manual/html_node/Bash-Builtins.html
- `df(1)` (GNU coreutils): https://www.gnu.org/software/coreutils/manual/html_node/df-invocation.html
- `findmnt(8)`: https://man7.org/linux/man-pages/man8/findmnt.8.html
- Nagios Plugin Development Guidelines — return codes: https://nagios-plugins.org/doc/guidelines.html
- AWS Architecture Blog — Exponential Backoff And Jitter: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/

---

**পরের lesson:** L04-04 — Error handling ও trap
