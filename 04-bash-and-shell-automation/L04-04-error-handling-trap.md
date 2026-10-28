# L04-04 — Error handling ও trap

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L04-03 — Function ও reusable script](L04-03-functions-reusable-scripts.md), [L01-08 — Process ও signal](../01-linux-systems/L01-08-processes-signals.md) |
| **Label** | — |
| **Tested** | `trap_demo.sh` ও `safe_job.sh`: ৬টি test পাস — ERR trap-এ line, command ও call stack (`set -E` সহ ও ছাড়া), সফল, ব্যর্থ ও **SIGTERM** — তিন ক্ষেত্রেই temp directory পরিষ্কার, exit code বহাল, আধা-লেখা output নেই, এবং **background child অনাথ হয়নি** (GNU Bash 5.3.9, Windows/Git Bash; signal bash-এর ভেতর থেকে পাঠানো)। প্রথম সংস্করণে **child process অনাথ হয়ে চলতেই থাকছিল** — আসলে দেখা গেছে, ঠিক করা হয়েছে (Section 9.3)। Ubuntu-তে চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- `trap` কী এবং কোন কোন "ঘটনা" ধরা যায়: `EXIT`, `ERR`, `INT`, `TERM`, `HUP`।
- **EXIT trap দিয়ে cleanup** — যেভাবেই script শেষ হোক।
- **ERR trap** দিয়ে কোন লাইনে, কোন command, কোন function-এর ভেতরে ব্যর্থ হলো — `set -E`-এর ভূমিকা।
- Signal-এ সঠিক exit code (১৩০, ১৪৩) ও graceful shutdown।
- Cleanup-এর ভেতরে exit code হারানো এড়ানো।
- **Background child process অনাথ হওয়া** — এবং তা আটকানো।
- Atomic publish: আধা-লেখা ফল কখনো দেখা যাবে না।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L04-01-এ দেখেছি `set -e` script থামায়, কিন্তু **নিঃশব্দে** এবং **অগোছালো অবস্থায়**:

- `/tmp`-এ temp file জমতে থাকে (disk ভরে যায় — L01-12)।
- আধা-লেখা config বা backup থেকে যায় — পরের process সেটাকেই সঠিক মনে করে পড়ে।
- Lock file থেকে যায় — পরের run "already running" বলে কখনো চলে না (L04-06)।
- Log-এ শুধু "failed" — কোন লাইনে, কেন, তার কোনো সূত্র নেই।
- Ctrl+C বা systemd-এর stop (SIGTERM, L01-10)-এ script-এর background কাজ চলতে থাকে।

`trap` এই সমস্যাগুলোর সমাধান: "যা-ই ঘটুক, শেষে এটা করো।"

## 3. সহজ ভাষায় পরিচয়

```bash
trap 'command' EVENT...
```

| Event | কখন চলে | সাধারণ ব্যবহার |
|---|---|---|
| `EXIT` | Script শেষ হলে — সফল, `exit`, `set -e`, বা signal-এর পরে | Cleanup (temp, lock) |
| `ERR` | কোনো command ব্যর্থ হলে (`set -e`-এর নিয়ম মেনে) | কোথায় ব্যর্থ — log |
| `INT` | Ctrl+C (SIGINT) | Graceful stop, exit ১৩০ |
| `TERM` | `kill`, `systemctl stop` (SIGTERM) | Graceful stop, exit ১৪৩ |
| `HUP` | Terminal বন্ধ / reload-এর রীতি | Config reload (L01-08) |
| — | **SIGKILL (৯) কখনো ধরা যায় না** | — |

**Exit code-এর রীতি:** signal N-এ মৃত্যু = ১২৮ + N। ফলে SIGINT (২) = ১৩০, SIGTERM (১৫) = ১৪৩, SIGKILL (৯) = ১৩৭ (L01-06)।

**কাঠামো:**

```bash
cleanup() { local rc=$?; trap - EXIT; rm -rf -- "$WORKDIR"; exit "$rc"; }
trap cleanup EXIT
trap 'echo "failed at line $LINENO: $BASH_COMMAND" >&2' ERR
trap 'exit 143' TERM          # signal-এ exit → EXIT trap চলে
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রান্নাঘরের নিয়ম: "বের হওয়ার আগে চুলা বন্ধ"

- **EXIT trap** = দরজার পাশে লেখা নিয়ম: রান্না শেষ হোক, পুড়ে যাক, বা ফোন এসে বের হতে হোক — চুলা বন্ধ, গ্যাস বন্ধ।
- **ERR trap** = কিছু পুড়লে খাতায় লেখা: কোন ধাপে, কোন পাত্রে।
- **SIGTERM** = কেউ বলল "দশ মিনিটে রান্নাঘর বন্ধ" — গুছিয়ে বের হওয়ার সময় আছে।
- **SIGKILL** = হঠাৎ বিদ্যুৎ চলে গেল — কোনো নিয়ম মানার সুযোগ নেই।

### Analogy কোথায় মেলে না

- রান্নাঘরে চুলা বন্ধ করা একজনের কাজ। Script-এর **child process** (background-এ চালানো `sleep`, `rsync`, `tar`) নিজের মতো চলে — parent চলে গেলে তারা **অনাথ** হয়ে চলতেই থাকে, যদি না স্পষ্টভাবে বন্ধ করা হয় (Section 9.3-এ আসলে ঘটেছে)।
- নিয়ম লেখা থাকলেই মানা হয়। Bash-এ **foreground command** চলার সময় signal এলে trap **command শেষ হওয়া পর্যন্ত অপেক্ষা করে** — ১ ঘণ্টার `rsync` চললে Ctrl+C-এর trap ১ ঘণ্টা পরে চলবে। সমাধান: background-এ চালিয়ে `wait` (`wait` signal-এ সাথে সাথে ভাঙে)।
- বিদ্যুৎ চলে গেলে কিছু করার নেই, তবে আমরা জানি। SIGKILL বা OOM-এ (L01-09) trap চলে না, তাই cleanup **পরের run-এর শুরুতেও** করতে হয় (stale lock বা temp খোঁজা — L04-06)।

## 5. Real-world engineering scenario — "Disk ভরে গেল /tmp-এর কারণে"

**পরিস্থিতি:** একটি report job প্রতি ১৫ মিনিটে চলে। প্রতিবার `/tmp/report.$$`-এ ২ GB intermediate data লেখে, শেষে `rm`। একটি database query মাঝে মাঝে timeout হয় → `set -e` script থামায় → `rm` কখনো চলে না। তিন দিন পরে `/tmp` ভরে গেল; একই server-এর web application session লিখতে না পেরে সবার জন্য ব্যর্থ হলো।

**কারণ:** cleanup ছিল script-এর **শেষ লাইনে**, trap-এ নয়।

**সমাধান:**

```bash
WORKDIR=$(mktemp -d)                      # অনুমানযোগ্য নাম নয় (security — L04-06)
trap 'rm -rf -- "$WORKDIR"' EXIT          # প্রথমেই, কাজ শুরুর আগে
```

এবং monitoring: `/tmp`-এর ব্যবহার (L04-03-এর `disk_check.sh`)। systemd service হলে `PrivateTmp=yes` (L01-10) — service বন্ধ হলে তার `/tmp` নিজেই মুছে যায়।

**শিক্ষা:** Cleanup কখনো "শেষে মনে করে করা" কাজ নয়। Resource তৈরির **সাথে সাথে** trap বসান।

## 6. Diagram — একটি script-এর তিন রকম সমাপ্তি

```text
 start ── trap cleanup EXIT ── mktemp -d ── step1 ── step2 ── step3 ── mv result → OUTPUT
                                              │         │
          সফল ─────────────────────────────────┼─────────┼──────────────► EXIT trap → cleanup → exit 0
          ব্যর্থ (set -e)                      ✗         │
            ERR trap: "line 62: false"  ───────┘         │                 EXIT trap → cleanup → exit 1
          SIGTERM (systemctl stop / kill) ───────────────┘
            TERM trap: exit 143 ─────────────────────────────────────────► EXIT trap → kill child → cleanup → exit 143
          SIGKILL / OOM ─────────────────────────────────────────────────► কোনো trap নয়: temp থেকে যায়
                                                                             (পরের run-এ পরিষ্কার — L04-06)
 OUTPUT কেবল সফল পথেই তৈরি হয় (mv) — অন্য কোনো পথে আধা-লেখা file দেখা যায় না
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| `trap` | ঘটনা (signal/pseudo-signal) ঘটলে চালানোর command |
| EXIT / ERR | Bash-এর pseudo-signal — শেষ / ব্যর্থতা |
| `set -E` (errtrace) | ERR trap function ও subshell-এ উত্তরাধিকার পায় |
| `$BASH_COMMAND` | এই মুহূর্তে চলমান command |
| `$LINENO`, `BASH_LINENO`, `FUNCNAME` | লাইন নম্বর ও call stack |
| `trap - EXIT` | Trap সরানো |
| Orphan process | Parent মারা যাওয়া child (PPID ১ বা subreaper) |
| `kill -0 PID` | Process আছে কিনা পরীক্ষা (signal পাঠায় না) |
| `wait` | Child শেষ হওয়ার অপেক্ষা; signal-এ ভাঙে |
| Atomic rename | একই filesystem-এ `mv` — পুরোটা হয় বা কিছুই না |
| Graceful shutdown | Signal পেয়ে গুছিয়ে বন্ধ হওয়া |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 EXIT trap-এ exit code হারানো

```bash
cleanup() { rm -rf "$WORKDIR"; }   # ভুল: script-এর exit code = rm-এর exit code (০)!
```

ব্যর্থ script cleanup-এর পরে "সফল" (০) দেখাতে পারে — CI বা systemd ব্যর্থতা ধরবে না। তাই `safe_job.sh`-এর `cleanup()`:

1. **প্রথম লাইনেই** `local rc=$?`।
2. `trap - EXIT` — `exit` আবার EXIT trap ডাকবে না।
3. কাজ শেষে `exit "$rc"`।

### 8.2 ERR trap ও `set -E`

ERR trap default-এ function-এর ভেতরে **উত্তরাধিকার পায় না**। `set -E` না থাকলে function-এর ভেতরে ব্যর্থতায় trap চলে না — script তবু `set -e`-এ থামে, কিন্তু **কিছুই বলে না** (Section 9.1-এর `without-E`)। ERR trap-ও `set -e`-এর মতো `if`, `&&`, `||`-এর ভেতরে চলে না।

### 8.3 Signal ও foreground command

Bash একটি foreground command চলার সময় signal পেলে trap চালায় **সেই command শেষ হওয়ার পরে**। দীর্ঘ কাজের জন্য:

```bash
long_task & CHILD=$!
wait "$CHILD"            # signal এলে wait সাথে সাথে ফেরে → trap চলে
```

তারপর cleanup-এ child-কে বন্ধ করতে হবে (Section 9.3)। বিকল্প: process group-এ signal পাঠানো (`kill -- -$$`, সতর্কতার সাথে), বা systemd-এর `KillMode=control-group` (default) — service stop-এ পুরো cgroup বন্ধ হয় (L01-10, L01-16)।

### 8.4 Atomic publish

ফল প্রথমে temp file-এ লিখুন, তারপর **একই filesystem-এ** `mv` করুন। Rename atomic: পাঠক হয় পুরোনো file দেখে, নয় নতুন সম্পূর্ণ file — মাঝামাঝি কিছু কখনো নয়। ভিন্ন filesystem-এ `mv` আসলে copy + delete, তাই atomic নয় — temp file তাই target-এর একই directory-তে রাখা ভালো (L04-06)।

## 9. Practical demonstration

### 9.1 ERR trap — `set -E` সহ ও ছাড়া

File: [`code/L04-04/trap_demo.sh`](code/L04-04/trap_demo.sh)

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-04
bash trap_demo.sh with-E; echo "exit=$?"
bash trap_demo.sh without-E; echo "exit=$?"
```

**আসল output:**

```text
deploy starting
grep: /nonexistent/app.conf: No such file or directory
ERR trap: exit 2 at trap_demo.sh:16 running: grep -q '^port=' "$file"
  at load_config() trap_demo.sh:16
  at deploy() trap_demo.sh:21
  at main() trap_demo.sh:32
exit=2

deploy starting
grep: /nonexistent/app.conf: No such file or directory
exit=2
```

`set -E` সহ: কোন file, কোন লাইন, কোন command এবং পুরো call stack (`main` → `deploy` → `load_config`) — incident-এর সময় সরাসরি কাজে লাগে। `set -E` ছাড়া: script একই exit code নিয়ে থেমেছে, কিন্তু **কোনো সূত্র ছাড়াই**। দুটোতেই `grep`-এর আসল exit code (২) বহাল আছে।

### 9.2 Cleanup — সফল, ব্যর্থ, SIGTERM

File: [`code/L04-04/safe_job.sh`](code/L04-04/safe_job.sh)

```bash
T=$(mktemp -d)
bash safe_job.sh "$T/out.txt"; echo "exit=$?"
bash safe_job.sh -f 2 "$T/out2.txt"; echo "exit=$?"
bash safe_job.sh -s 37 "$T/out3.txt" & pid=$!; sleep 1.5; kill -TERM $pid; wait $pid; echo "exit=$?"
```

**আসল output (সংক্ষেপিত; সময়, PID ও path ভিন্ন হবে):**

```text
safe_job.sh[2004]: workdir /tmp/safe_job.6RY54n
safe_job.sh[2004]: step 1: collect data
safe_job.sh[2004]: step 2: process
safe_job.sh[2004]: step 3: publish
safe_job.sh[2004]: wrote /tmp/tmp.f2Nuqbh4Hf/out.txt: 500500
safe_job.sh[2004]: cleanup: removed /tmp/safe_job.6RY54n
safe_job.sh[2004]: exit 0
exit=0

safe_job.sh[2030]: step 2: process
safe_job.sh[2030]: ERROR: 'false' failed (exit 1) at line 62
safe_job.sh[2030]: cleanup: removed /tmp/safe_job.V8vyP4
safe_job.sh[2030]: exit 1
exit=1                                   (out2.txt তৈরি হয়নি)

safe_job.sh[757]: step 2: process
safe_job.sh[757]: received SIGTERM — stopping
safe_job.sh[757]: cleanup: stopped child 768
safe_job.sh[757]: cleanup: removed /tmp/safe_job.obRTLG
safe_job.sh[757]: exit 143
exit=143
```

তিন রকম সমাপ্তি, তিনটিতেই temp directory পরিষ্কার এবং সঠিক exit code (০, ১, ১৪৩)। ব্যর্থ বা বাধাপ্রাপ্ত run-এ output file **তৈরিই হয়নি**।

### 9.3 প্রথম সংস্করণের bug: অনাথ child

প্রথম সংস্করণে ধাপ ২ ছিল `sleep "$SLEEP" & wait $!` — signal-এ `wait` ভাঙে, trap চলে, script বেরিয়ে যায়। কিন্তু SIGTERM-এর পরে process তালিকা দেখাল:

```text
 This pc     737       1 ?        01:56:12 sleep 37
```

`sleep` এখনো চলছে, **PPID ১** — অনাথ। বাস্তবে এটা হতে পারত একটি ঘণ্টাব্যাপী `rsync` বা `pg_dump`। পরের run আবার শুরু করত, ফলে দুটি একসাথে একই জায়গায় লিখত।

সমাধান:

- Child-এর PID `CHILD`-এ রাখা।
- Cleanup-এ `kill -0` দিয়ে পরীক্ষা, তারপর `kill -TERM` ও `wait`।

এখন একই পরীক্ষায় চলার সময় `sleep 43` ছিল (PID ১২৩), SIGTERM-এর পরে আর নেই। Test `test_sigterm_cleans_up_and_stops_child` `/proc/<pid>/cmdline` পড়ে এটা যাচাই করে।

**যাচাইয়ের সময় দুটি অতিরিক্ত ফাঁদ:**

- `ps -ef | awk '{print $2}'` দিয়ে PID বের করতে গিয়ে ভুল হলো — এই machine-এর user নাম "This pc"-এ space আছে, তাই column সরে যায় (L04-03-এর `df`-এর মতোই)।
- `ps | grep "sleep 41"` আমার নিজের shell-এর command line-ও গুনেছিল।

`/proc/*/cmdline` (NUL-বিভক্ত argument) দ্ব্যর্থহীন।

### 9.4 Ubuntu-তে

```bash
bash safe_job.sh -s 30 /tmp/out.txt &       # তারপর অন্য terminal-এ:
pstree -p $!                               # parent ও child
kill -TERM <pid>                           # trap-এর আচরণ দেখুন
pgrep -a sleep                             # অনাথ নেই তো?
```

systemd service হিসেবে চালালে `systemctl stop`-এ SIGTERM যায়, তারপর `TimeoutStopSec`-এর পরে SIGKILL (L01-10)। Cleanup দ্রুত হতে হবে।

> **Fedora-তে:** একই আচরণ (bash, procps-ng)।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l04_04.py`](code/L04-04/test_l04_04.py)-এর ৬টি test:

- **Trap demo:** `set -E` সহ ERR trap-এ line, command ও stack; ছাড়া নিঃশব্দ — দুটোতেই exit ২।
- **Safe job:**
  - সফল run-এ ফল লেখা ও cleanup।
  - ব্যর্থ run-এ exit ১, output নেই, cleanup।
  - Usage error।
  - SIGTERM-এ exit ১৪৩, cleanup, **child বন্ধ**।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `trap cleanup EXIT` script-এর শুরুতে | Resource তৈরির আগেই | মাঝপথে ব্যর্থ হলেও cleanup |
| `local rc=$?` প্রথম লাইনে | Exit code সংরক্ষণ | Cleanup-এর command-এ হারায় না |
| `trap - EXIT` | পুনরাবৃত্তি বন্ধ | `exit` আবার EXIT trap ডাকে |
| `[[ -n $WORKDIR && -d $WORKDIR ]]` | Variable খালি নয় ও directory | `rm -rf ""` বা ভুল path নয় |
| `on_signal` → `exit 143` | Signal-কে exit-এ রূপান্তর | EXIT trap একই cleanup চালায় |
| `sleep & CHILD=$!; wait` | Signal-এ সাথে সাথে সাড়া | Foreground-এ trap অপেক্ষা করত |
| Cleanup-এ `kill -0` → `kill -TERM` → `wait` | Child বন্ধ | অনাথ process নয় (Section 9.3) |
| `mv result.tmp OUTPUT` শেষে | Atomic publish | আধা-লেখা ফল কখনো দেখা যায় না |
| `on_err`-এ `$BASH_COMMAND`, `$LINENO` | কোথায় ও কী ব্যর্থ | Debug-যোগ্য log |

**Bash কেন এখানে, কোথায় নয়:** process ও signal-কেন্দ্রিক cleanup-এ Bash-এর `trap` সরল ও কার্যকর। জটিল ক্ষেত্রে (অনেক child, timeout, structured error) Python-এর `subprocess`, `signal` ও `try/finally` বা systemd-এর নিজস্ব process management বেশি নির্ভরযোগ্য।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `trap_demo.sh with-E` | ERR trap-এর লাইন ও তিন স্তরের stack, exit ২ |
| `safe_job.sh -f 2 OUT` | exit ১, OUT নেই, workdir মুছে গেছে |
| SIGTERM | exit ১৪৩, child নেই, workdir নেই |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| ব্যর্থ script exit ০ দেখায় | Cleanup-এর শেষ command-এর status | `local rc=$?` ও `exit "$rc"` |
| Ctrl+C-এ সাথে সাথে থামে না | Foreground command শেষের অপেক্ষা | Background + `wait` |
| Script মরার পরেও কাজ চলছে | অনাথ child | PID রেখে cleanup-এ kill; systemd cgroup |
| ERR trap function-এর ভেতরে চলে না | `set -E` নেই | `set -Eeuo pipefail` |
| Trap দুবার চলে | EXIT trap-এর ভেতরে `exit` | `trap - EXIT` |
| `rm -rf ""`-এর ভয় | খালি variable | খালি নয় ও directory কিনা পরীক্ষা; `${VAR:?}` |
| SIGKILL-এর পরে temp থেকে যায় | SIGKILL ধরা যায় না | পরের run-এ পুরোনো temp পরিষ্কার (L04-06) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `mktemp -d`-এর অনুমান-অযোগ্য নাম ও ৭০০ permission ব্যবহার করুন (`/tmp/report.$$` অনুমানযোগ্য — symlink আক্রমণ, L04-06)।
  - Cleanup-এ `rm -rf`-এর আগে path যাচাই করুন।
  - ERR log-এ `$BASH_COMMAND`-এ secret থাকতে পারে (যেমন `curl -H "Authorization: …"`) — secret-যুক্ত command-এ log redaction বা আলাদা বর্ণনা দিন।
- **Performance:**
  - Cleanup দ্রুত রাখুন — systemd-এর stop timeout-এর পরে SIGKILL আসে।
  - দীর্ঘ child-কে TERM দিয়ে কিছুক্ষণ সময় দিন, তারপর প্রয়োজনে KILL।
- **Cost:**
  - Cleanup না হওয়া temp disk ভরায় (Section 5)।
  - অনাথ process CPU ও বিল খায় (cloud-এ চালু থাকা instance-এ ঘণ্টার পর ঘণ্টা)।

## 14. Hands-on exercise

1. `trap_demo.sh`-এ `on_err`-কে বাড়ান: ব্যর্থ command-এর stderr-এর শেষ লাইনও দেখাবে (ইঙ্গিত: command-এর stderr একটি file-এ redirect করুন)।
2. `safe_job.sh`-এ `HUP` trap যোগ করুন — শুধু log করবে ও কাজ চালিয়ে যাবে (L01-08-এর reload ধারণা)।
3. Cleanup-এ child-কে TERM দেওয়ার পরে ৫ সেকেন্ডের মধ্যে না থামলে KILL দিন। একটি child লিখুন যে TERM উপেক্ষা করে (`trap '' TERM`), এবং পরীক্ষা করুন।
4. EXIT trap-এর ভেতর থেকে `local rc=$?` সরিয়ে `safe_job.sh -f 2` চালান — exit code কী আসে? কেন?
5. Ubuntu VM-এ `safe_job.sh`-কে একটি transient systemd unit হিসেবে চালান (`systemd-run --unit=demo bash /path/safe_job.sh -s 60 /tmp/o`), তারপর `systemctl stop demo` এবং `journalctl -u demo` দেখুন।

## 15. Mini-project — Log archiver (দ্বিতীয় অংশ)

L04-02-এর `archive_logs.sh`-এ যোগ করুন:

- EXIT trap-এ temp tar file মোছা।
- ERR trap-এ লাইন ও command log।
- SIGTERM-এ চলমান `tar` বন্ধ করে partial archive মোছা।
- সফল হলে শুধু তখনই আসল file মোছা — archive `tar -t` দিয়ে যাচাইয়ের পরে।

L04-06-এ locking যোগ হবে।

## 16. Interview প্রশ্ন

1. `trap ... EXIT` কখন চলে? SIGKILL-এ চলে কি?
2. Cleanup function-এ exit code কীভাবে হারায়, এবং কীভাবে রক্ষা করবেন?
3. ERR trap function-এর ভেতরে কাজ না করলে কী কারণ?
4. SIGTERM পেলে script কত exit code দেওয়া উচিত, এবং কেন?
5. Script থেমে গেলেও তার child process চলছে — কেন, এবং কীভাবে আটকাবেন?
6. আধা-লেখা output file কীভাবে এড়াবেন?

## 17. Self-assessment প্রশ্ন

1. রান্নাঘর analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ disk কেন ভরে গেল?
3. Section 9.1-এ `without-E` কী দেখায় না?
4. Section 9.3-এর অনাথ process কীভাবে ধরা পড়ল, এবং যাচাইয়ে কোন দুটি ফাঁদ ছিল?
5. `safe_job.sh`-এ output কেন শুধু সফল পথেই দেখা যায়?

## 18. সংক্ষিপ্ত সারাংশ

- `trap cleanup EXIT` resource তৈরির আগেই বসান; cleanup-এ `local rc=$?`, `trap - EXIT`, `exit "$rc"`।
- `set -E` + ERR trap: লাইন, command ও call stack।
- Signal → `exit 128+N` → EXIT trap; দীর্ঘ কাজ background-এ চালিয়ে `wait`।
- Child-এর PID রাখুন, cleanup-এ বন্ধ করুন — নইলে অনাথ।
- Temp-এ লিখে একই filesystem-এ `mv` — atomic publish।
- SIGKILL/OOM-এ কোনো trap নেই — পরের run-এ পরিষ্কারের ব্যবস্থা রাখুন।

## 19. Completion checklist

- [ ] `trap_demo.sh`-এর দুই mode চালিয়ে পার্থক্য ব্যাখ্যা করতে পারি
- [ ] `safe_job.sh`-এর তিন রকম সমাপ্তি নিজে দেখেছি
- [ ] অনাথ child-এর ঘটনা পুনরুৎপাদন ও সমাধান বুঝেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash Reference Manual — Bourne Shell Builtins (`trap`): https://www.gnu.org/software/bash/manual/html_node/Bourne-Shell-Builtins.html
- GNU Bash Reference Manual — Signals: https://www.gnu.org/software/bash/manual/html_node/Signals.html
- GNU Bash Reference Manual — Bash Variables (`BASH_COMMAND`, `FUNCNAME`, `BASH_LINENO`): https://www.gnu.org/software/bash/manual/html_node/Bash-Variables.html
- `signal(7)`: https://man7.org/linux/man-pages/man7/signal.7.html
- `systemd.kill(5)`: https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html
- BashFAQ/062 — How do I create a temporary file securely?: https://mywiki.wooledge.org/BashFAQ/062

---

**পরের lesson:** L04-05 — Argument parsing, getopts, usage ও logging
