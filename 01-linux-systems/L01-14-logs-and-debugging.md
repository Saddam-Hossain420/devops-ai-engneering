# L01-14 — Log, debugging ও resource inspection (journalctl, strace, lsof)

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-13 — SSH](L01-13-ssh-remote-access.md); [L01-10 — systemd](L01-10-systemd-services.md); [L01-01 — strace](L01-01-linux-architecture.md) |
| **Label** | — |
| **Tested** | `journal_summary.py`: ৪টি test পাস; নমুনা `journalctl -o json`-এ চালানো (Python 3.14, Windows)। নমুনা journal script দিয়ে তৈরি (journald-এর আসল field নাম অনুসরণে)। `journalctl`, `lsof`, `/proc`, `logrotate -d` **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- Ubuntu-তে log কোথায়: **journald**, `/var/log/syslog`, `auth.log`, `kern.log`, application log — এবং Fedora-র পার্থক্য।
- `journalctl`-এর শক্তিশালী filter: unit, boot, priority, সময়, PID, kernel, JSON।
- **Syslog priority** (emerg → debug) ও কেন সঠিক level-এ log করা জরুরি।
- **logrotate** — `create` + signal বনাম `copytruncate`।
- একটি চলমান process ভেতর থেকে দেখা: `/proc/<PID>/` (fd, limits, cwd, environ), `lsof`, `strace -p`।
- **"Too many open files"** — file descriptor leak diagnose।
- Python দিয়ে journal-এর JSON সারাংশ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Incident-এ প্রথম প্রশ্ন: "কী ঘটেছে?" — উত্তর থাকে log-এ। কিন্তু:

- Log ছড়িয়ে আছে অনেক জায়গায়; কোনটি দেখবেন জানতে হয়।
- হাজার হাজার INFO লাইনের মধ্যে একটি গুরুত্বপূর্ণ ERROR হারিয়ে যায়।
- Log rotate ঠিকমতো না হলে disk পূর্ণ (L01-03), বা rotate-এর পরে app পুরোনো (মুছে ফেলা) file-এ লিখতে থাকে।
- কিছু সমস্যা log-এ আসেই না — process নীরবে আটকে আছে; তখন process-কে **ভেতর থেকে** দেখতে হয় (কোন file খোলা, কোন system call-এ আটকে)।

এই lesson L00-06-এর incident timeline ও L01-01-এর strace-কে একসাথে করে একটি পূর্ণ debugging toolkit দেয়।

## 3. সহজ ভাষায় পরিচয়

**Ubuntu-তে log-এর দুই স্তর:**

| উৎস | কোথায় | কী |
|---|---|---|
| **journald** | `journalctl` (binary, `/var/log/journal/`) | systemd service-এর stdout/stderr, kernel, syslog — structured field সহ |
| **rsyslog** | `/var/log/syslog`, `/var/log/auth.log`, `/var/log/kern.log` | journald থেকে text file-এ copy (Ubuntu-তে default চালু) |
| Application নিজে | যেমন `/var/log/nginx/access.log` | App নিজের file লেখে — logrotate দরকার |

> **Fedora-তে:** default-ভাবে শুধু journald — `/var/log/syslog` বা `/var/log/messages` থাকে না (rsyslog install করলে তবে); authentication log দেখুন `journalctl _COMM=sshd` বা `journalctl -t sudo` দিয়ে।

**Syslog priority (০–৭):**

| নং | নাম | কখন |
|---|---|---|
| 0 | emerg | System অচল |
| 1 | alert | এখনই ব্যবস্থা |
| 2 | crit | গুরুতর (যেমন OOM kill) |
| 3 | err | ত্রুটি |
| 4 | warning | সতর্কতা |
| 5 | notice | স্বাভাবিক কিন্তু উল্লেখযোগ্য |
| 6 | info | তথ্য |
| 7 | debug | বিস্তারিত (production-এ সাধারণত বন্ধ) |

`journalctl -p err` = err **ও তার চেয়ে গুরুতর** (০–৩)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### বিমানের black box ও ডাক্তারের পরীক্ষা

- **Log** = বিমানের flight recorder: কী ঘটেছে তার ধারাবাহিক রেকর্ড। দুর্ঘটনার পরে প্রথম প্রমাণ।
- **Priority** = রেকর্ডে "সাধারণ", "সতর্কতা", "জরুরি" চিহ্ন — জরুরিগুলো আগে পড়া হয়।
- **logrotate** = পুরোনো রেকর্ড আর্কাইভে সরানো, যাতে recorder ভরে না যায়।
- **`/proc`, `lsof`, `strace`** = রোগী এখনো জীবিত — ডাক্তার সরাসরি পরীক্ষা করেন (রক্তচাপ, নাড়ি) রেকর্ড পড়ার বদলে।

### Analogy কোথায় মেলে না

- Black box সব রেকর্ড করে। Application log শুধু তা-ই রাখে যা developer লিখতে বলেছেন — **লেখা না থাকলে log-এ নেই**। তাই "log-এ কিছু নেই" মানে "কিছু ঘটেনি" নয় (L01-09-এর OOM kill app-এর log-এ আসে না)।
- Black box-এর সময় একটি ঘড়ির। বহু server-এর log মেলাতে সব server-এর ঘড়ি NTP দিয়ে মেলানো ও UTC ব্যবহার জরুরি (L00-06)।
- ডাক্তারের পরীক্ষা রোগীকে কষ্ট দেয় না। `strace -p` চলমান process-কে **উল্লেখযোগ্যভাবে ধীর** করে — production-এ অল্প সময়ের জন্য।

## 5. Real-world engineering scenario — "Too many open files"

**পরিস্থিতি:** TaskFlow API কয়েক দিন চলার পরে নতুন request-এ `OSError: [Errno 24] Too many open files`। Restart করলে ঠিক হয়, কয়েক দিন পরে আবার।

**Diagnosis:**

```bash
PID=$(systemctl show -p MainPID --value taskflow)
ls /proc/$PID/fd | wc -l                       # এখন কতগুলো fd খোলা
grep "Max open files" /proc/$PID/limits        # সীমা কত
sudo lsof -p $PID | awk '{print $5}' | sort | uniq -c | sort -rn   # fd-এর ধরন (REG, IPv4, sock ...)
```

উদাহরণ ফল: ১০২৪ সীমা, ১০২১ খোলা, তার মধ্যে ৯৮০টি `IPv4` socket upstream service-এর দিকে `ESTABLISHED`/`CLOSE_WAIT` অবস্থায়।

**কারণ:** Code প্রতিটি request-এ নতুন HTTP connection খোলে কিন্তু response পড়ার পরে বন্ধ করে না — **file descriptor leak**। `CLOSE_WAIT` মানে অন্য পক্ষ বন্ধ করেছে, আমরা করিনি (L02-05-এ TCP state বিস্তারিত)।

**ভুল সমাধান:** শুধু সীমা ১০২৪ থেকে ১০০০০০ করা — সমস্যা দেরিতে আসবে, যাবে না।
**সঠিক সমাধান:** Code-এ connection বন্ধ বা connection pool (Python-এ `with` / session পুনর্ব্যবহার, Module 05); এবং প্রকৃত চাহিদা অনুযায়ী systemd-এ `LimitNOFILE=` (L01-10)।

**শিক্ষা:** Restart লক্ষণ সারায়, কারণ নয়। `/proc` ও `lsof` দিয়ে চলমান অবস্থার **প্রমাণ** সংগ্রহ করুন, তারপর restart।

## 6. Diagram — log-এর প্রবাহ ও debugging-এর পথ

```text
 service stdout/stderr ─┐
 kernel (printk) ────────┼──► journald ──► /var/log/journal/ (binary, indexed)  ──► journalctl
 syslog() call ──────────┘        │
                                  └──► rsyslog (Ubuntu) ──► /var/log/syslog, auth.log, kern.log
 app নিজে file লেখে ───────────────────────────────────► /var/log/app/*.log ──► logrotate

 Debugging ক্রম (incident-এ):
   1. journalctl -u svc -b -p warning         ← কী ঘটেছে (ইতিহাস)
   2. journalctl -k / dmesg                   ← kernel কিছু বলেছে? (OOM, disk error)
   3. /proc/PID/{status,limits,fd}, lsof      ← এখন অবস্থা কী (জীবিত process)
   4. strace -p PID (সংক্ষিপ্ত)                 ← এই মুহূর্তে কোন system call-এ
   5. প্রমাণ সংরক্ষণ → তারপর mitigation (restart/rollback)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| journald | systemd-এর structured log service |
| rsyslog | Traditional syslog daemon; text file-এ log লেখে |
| Priority / severity | Log-এর গুরুত্ব (০ emerg – ৭ debug) |
| Boot ID | প্রতিটি boot-এর পরিচয়; `journalctl -b -1` = আগের boot |
| logrotate | Log file ঘোরানো, compress ও পুরোনো মুছে ফেলার tool |
| `copytruncate` | File copy করে মূলটি খালি করা — app-এর সহযোগিতা ছাড়া, কিন্তু কিছু লাইন হারাতে পারে |
| `create` + signal | নতুন file তৈরি করে app-কে signal দেওয়া যাতে নতুন file খোলে |
| File descriptor limit | Process একসাথে কতগুলো fd খুলতে পারে (`ulimit -n`, `LimitNOFILE=`) |
| `lsof` | কোন process কোন file/socket খুলে রেখেছে |
| `dmesg` | Kernel ring buffer-এর বার্তা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 journalctl-এর মূল filter

```bash
journalctl -u nginx                         # একটি unit
journalctl -u nginx -u taskflow             # একাধিক (OR)
journalctl -b                               # এই boot; -b -1 আগের boot
journalctl -p warning                       # warning ও গুরুতর
journalctl --since "2026-10-26 09:00" --until "09:30"
journalctl --since "15 min ago"
journalctl -k                               # kernel (dmesg-এর মতো, কিন্তু ইতিহাস সহ)
journalctl _PID=2211                        # নির্দিষ্ট PID
journalctl _COMM=sshd                       # নির্দিষ্ট program
journalctl -f                               # follow (tail -f)
journalctl -o json --since today            # যন্ত্র-পাঠযোগ্য
journalctl --disk-usage                     # journal কত জায়গা নিচ্ছে
```

একসাথে: `journalctl -u taskflow -b -p err --since "1 hour ago" --no-pager`।

### 8.2 logrotate: দুই পদ্ধতি

**`create` + signal (সুপারিশকৃত, app সমর্থন করলে):**

1. `app.log` → `app.log.1` নাম বদল (rename — app-এর খোলা fd এখনো সেই inode-এ লিখছে, L01-03)।
2. নতুন খালি `app.log` তৈরি।
3. App-কে signal (প্রচলিত SIGHUP বা USR1) → app পুরোনো fd বন্ধ করে নতুন `app.log` খোলে।

**`copytruncate`:** `app.log`-এর copy নিয়ে মূল file-কে শূন্যে truncate — app কিছু জানে না, একই fd-তে লিখতে থাকে। সহজ, কিন্তু copy ও truncate-এর মাঝে লেখা লাইন **হারাতে পারে**।

এই lesson-এর [`taskflow-logrotate.conf`](code/L01-14/taskflow-logrotate.conf) প্রথম পদ্ধতি ব্যবহার করে। আর সবচেয়ে সহজ পথ: app **stdout-এ log করুক** (L01-10) — journald নিজেই আকার ও rotation সামলায়, logrotate লাগেই না।

### 8.3 `/proc/<PID>/` — জীবিত process-এর জানালা

| Path | কী জানায় |
|---|---|
| `status` | State, memory (VmRSS), threads, UID |
| `limits` | fd, process, memory ইত্যাদির সীমা |
| `fd/` | প্রতিটি খোলা file descriptor (symlink — কোন file/socket) |
| `cwd` | Current working directory (L01-01-এর relative path রহস্য) |
| `exe` | কোন binary চলছে (মুছে ফেলা হলে `(deleted)`) |
| `environ` | Environment (`\0`-separated; শুধু owner/root) — secret থাকতে পারে ⚠️ |
| `cmdline` | Command line argument |
| `wchan`, `stack` | কোথায় অপেক্ষা করছে (D state-এ, L01-08) |

### 8.4 Log level ঠিক রাখা

- সব কিছু ERROR হলে কিছুই ERROR নয় (alert fatigue, Module 17)।
- স্বাভাবিক user ভুল (ভুল password, 404) সাধারণত WARNING/INFO — ERROR নয়।
- ERROR-এ যথেষ্ট context: কোন request, কোন dependency, কী চেষ্টা করা হয়েছিল — কিন্তু **secret বা personal data নয়**।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 Log-এর জায়গা চেনা

```bash
ls -lh /var/log/ | head -20
journalctl --disk-usage
journalctl -b -p err --no-pager | tail -20
journalctl -k -b --no-pager | tail -10
sudo tail -5 /var/log/auth.log            # Ubuntu (rsyslog)
journalctl -u ssh --since today --no-pager | tail -5
```

> **Fedora-তে:** `/var/log/auth.log` নেই — `journalctl -u sshd --since today`।

### 9.2 Journal-এর সারাংশ — Python

File: [`code/L01-14/journal_summary.py`](code/L01-14/journal_summary.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-14
journalctl -o json --since "1 hour ago" > /tmp/journal.jsonl
python3 journal_summary.py /tmp/journal.jsonl
python3 journal_summary.py sample-journal.jsonl --max-priority 3; echo "exit=$?"
```

**নমুনা ([`sample-journal.jsonl`](code/L01-14/sample-journal.jsonl), একটি ভাঙা লাইন সহ) দিয়ে আসল output:**

```text
entries: 121 (skipped 1)  window: 09:00:08 → 09:30:06 UTC
by priority: crit=1  err=14  warning=23  notice=11  info=72

priority <= 3 (err): 15 entries
    14  taskflow-demo.service
     1  kernel
top messages:
    10  [taskflow-demo.service] db connection refused
     4  [taskflow-demo.service] request failed: upstream timeout
     1  [kernel] Out of memory: Killed process 4821 (python3)
most severe: crit at 09:30:06 [kernel] Out of memory: Killed process 4821 (python3)
exit=1
```

**ব্যাখ্যা:** ৭২টি info লাইনের মধ্যে আসল সংকেত ১৫টি: database connection সমস্যা (taskflow) এবং শেষে একটি kernel OOM kill — দুটি সম্ভবত আলাদা ঘটনা; L00-06-এর timeline পদ্ধতিতে আলাদা করে তদন্ত করতে হবে। "notice" level-এর `Invalid user admin from 203.0.113.50` — SSH brute-force চেষ্টা (L01-13)।

Native সমতুল্য (L01-07-এর `jq` দিয়ে):

```bash
journalctl -o json --since "1 hour ago" -p err | jq -r '._SYSTEMD_UNIT // .SYSLOG_IDENTIFIER' | sort | uniq -c | sort -rn
```

### 9.3 জীবিত process পরীক্ষা

```bash
sleep 600 &                                   # একটি নমুনা process
PID=$!
cat /proc/$PID/status | grep -E 'State|VmRSS|Threads'
ls -l /proc/$PID/fd
ls -l /proc/$PID/cwd
grep "Max open files" /proc/$PID/limits
ulimit -n                                     # এই shell-এর soft limit
sudo lsof -p $PID
sudo lsof -i :22                              # port 22 কে খুলে রেখেছে
kill $PID
```

**fd leak নিজে তৈরি করুন (নিরাপদ, ছোট সীমায়):**

```bash
( ulimit -n 64; python3 -c '
files = []
try:
    while True:
        files.append(open("/dev/null"))
except OSError as e:
    print(len(files), "files opened, then:", e)
' )
```

প্রত্যাশিত (উদাহরণ): `61 files opened, then: [Errno 24] Too many open files: '/dev/null'` — ৬৪ সীমার মধ্যে ০, ১, ২ ও Python-এর নিজের কিছু fd আগে থেকে খোলা। `( ... )` subshell — `ulimit` পরিবর্তন শুধু সেখানেই।

### 9.4 strace দিয়ে আটকে থাকা process

```bash
mkfifo /tmp/lab-fifo                                            # named pipe: কেউ না লেখা পর্যন্ত পাঠক আটকে থাকে
python3 -c 'open("/tmp/lab-fifo").read()' &                    # কেউ না লেখা পর্যন্ত আটকে থাকবে
sudo strace -p $! -e trace=openat 2>&1 | head -3               # কোথায় আটকে? (Ctrl+C)
echo hi > /tmp/lab-fifo                                         # মুক্ত করুন
rm -f /tmp/lab-fifo
```

`strace -p` দেখায় process একটি `openat` (FIFO খোলা)-এ অপেক্ষা করছে — log-এ যা কখনো আসত না।

### 9.5 logrotate — dry run

```bash
sudo install -m 0644 taskflow-logrotate.conf /etc/logrotate.d/taskflow
sudo mkdir -p /var/log/taskflow && sudo touch /var/log/taskflow/app.log
sudo logrotate -d /etc/logrotate.d/taskflow     # -d = debug/dry-run: কী করবে দেখায়, কিছু বদলায় না
sudo rm /etc/logrotate.d/taskflow && sudo rm -r /var/log/taskflow   # cleanup
```

`create 0640 taskflow adm` — `taskflow` user না থাকলে logrotate error দেবে; L01-10-এর service user তৈরি থাকলে কাজ করবে, না থাকলে dry-run-এর বার্তা পড়ে বুঝুন।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_journal_summary.py`](code/L01-14/test_journal_summary.py)-এর ৪টি test: একটি journal লাইন parse, fallback (unit না থাকলে identifier; byte-array message; priority default), নমুনার গণনা ও সবচেয়ে গুরুতর entry, ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `__REALTIME_TIMESTAMP` / 1e6 | microsecond → datetime | journald সময় microsecond-এ রাখে |
| `MESSAGE` list হলে bytes decode | | Non-UTF-8 message journald byte array হিসেবে দেয় |
| `_SYSTEMD_UNIT or SYSLOG_IDENTIFIER` | উৎস | Kernel-এর unit নেই |
| `priority <= max_priority` | "এবং গুরুতর" | journalctl `-p`-এর মতো অর্থ |
| `min(selected, key=(priority, time))` | সবচেয়ে গুরুতর, সমান হলে আগেরটি | Incident-এর প্রথম গুরুতর ঘটনা |
| ভাঙা JSON লাইন গোনা | `skipped` | নীরবে data বাদ নয় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `journalctl -p err -b` | এই boot-এর error |
| fd-leak experiment | Errno 24, ৬৪-এর কাছাকাছি সংখ্যায় |
| `logrotate -d` | কোন file rotate হবে তার পরিকল্পনা, কোনো পরিবর্তন নয় |
| `python3 -m unittest -v` | `Ran 4 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `journalctl` খালি বা পুরোনো boot নেই | Volatile journal | `ls /var/log/journal` | `Storage=persistent` (`journald.conf`) |
| Rotate-এর পরে app-এর log নতুন file-এ আসে না | App পুরোনো fd-তে লিখছে | `lsof -p PID \| grep log` — `(deleted)` বা `.1` | postrotate-এ signal, বা `copytruncate` |
| `Too many open files` | fd leak বা ছোট limit | `/proc/PID/fd` সংখ্যা বনাম limits | Leak ঠিক; প্রয়োজনে `LimitNOFILE=` |
| Log-এ কিছু নেই, অথচ process মরেছে | SIGKILL (OOM) | `journalctl -k`, `systemctl status` | L01-09 |
| `/var/log` বিশাল | Rotation নেই, debug level | `du -sh /var/log/*` | logrotate, level ঠিক, `journalctl --vacuum-size=` |
| Permission denied `/proc/PID/fd` | অন্য user-এর process | — | `sudo` |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Log-এ password, token, personal data লিখবেন না (L01-07-এর masking); log file-এর permission সীমিত (`0640`, group `adm`); `/proc/PID/environ` থেকে secret ফাঁস সম্ভব — secret environment-এর চেয়ে file/credential-এ (L01-10); auth log কেন্দ্রীয়ভাবে রাখুন যাতে আক্রমণকারী মুছতে না পারে (Module 17, 19)।
- **Performance:** Debug-level logging I/O ও CPU খায়; `strace -p` process-কে অনেক ধীর করে।
- **Cost:** Cloud log ingestion প্রতি GB-তে বিল — অপ্রয়োজনীয় INFO/DEBUG কমানো সরাসরি খরচ কমায় (Module 29)।

## 14. Hands-on exercise

1. `journalctl -b -1 -p warning` — আগের boot-এ কী সমস্যা ছিল? (Volatile journal হলে প্রথমে persistent করুন।)
2. L01-10-এর `taskflow-demo` চালিয়ে `journalctl -u taskflow-demo -o json -n 3 | jq .` — কোন কোন field আছে?
3. `journal_summary.py`-তে `--since-minutes N` filter যোগ করুন (শেষ entry-র সময় থেকে পিছনে)। Test লিখুন।
4. fd-leak experiment-এ `files` তালিকা থেকে প্রতি ১০টিতে একটি বন্ধ করে (`close()`) দেখুন কতদূর যায়।
5. `sudo lsof +L1` (L01-03) ও `sudo lsof -i -P -n | grep LISTEN` — আপনার VM-এ কোন process কোন port শুনছে?

## 15. Mini-project — Project 1-এর `logs` subcommand

L01-07-এর `access_report.py` ও এই lesson-এর `journal_summary.py` একত্র করে Project 1 toolkit-এর `logs` subcommand-এর নকশা ও প্রথম version লিখুন: `ops-toolkit logs --unit X --since 1h` journal থেকে সারাংশ, `--nginx FILE` access log থেকে, এবং দুটিরই `--json` output। একটি README-তে ব্যবহার ও সীমাবদ্ধতা লিখুন।

## 16. Interview প্রশ্ন

1. একটি systemd service-এর গত এক ঘণ্টার error কীভাবে দেখবেন?
2. journald ও rsyslog-এর সম্পর্ক কী? Fedora-তে পার্থক্য কী?
3. logrotate-এ `copytruncate` কখন ও কেন? ঝুঁকি কী?
4. "Too many open files" — কীভাবে diagnose ও সমাধান করবেন?
5. একটি process আটকে আছে, log-এ কিছু নেই — কী দেখবেন?
6. Log level কীভাবে বেছে নেবেন? সব ERROR হলে সমস্যা কী?

## 17. Self-assessment প্রশ্ন

1. Black box analogy কোথায় মেলে না?
2. Section 5-এ সীমা বাড়ানো কেন ভুল সমাধান?
3. logrotate-এর দুই পদ্ধতির ধাপ ও trade-off।
4. `/proc/PID/cwd` কোন ধরনের রহস্য সমাধানে সাহায্য করে?
5. নমুনা journal-এ কোন দুটি আলাদা সমস্যা চোখে পড়ে?
6. fd-leak experiment-এ ৬৪-এর কম file খোলা গেল কেন?

## 18. সংক্ষিপ্ত সারাংশ

- Ubuntu: journald + rsyslog text file; Fedora: শুধু journald (default)।
- `journalctl -u -b -p --since -k -o json -f` — filter-ই দক্ষতা।
- Priority সঠিক রাখুন; log-এ secret নয়।
- logrotate: `create` + signal (সঠিক) বা `copytruncate` (সহজ, ক্ষতি সম্ভব); সবচেয়ে সহজ — stdout + journald।
- জীবিত process: `/proc/PID/*`, `lsof`, `strace -p` — restart-এর আগে প্রমাণ সংগ্রহ।

## 19. Completion checklist

- [ ] `journalctl`-এর ১০টি filter নিজে চালিয়েছি
- [ ] `journal_summary.py` আসল journal-এ চালিয়েছি
- [ ] `/proc/PID/` ও `lsof` দিয়ে একটি process পরীক্ষা করেছি
- [ ] fd-leak experiment ও strace-এ আটকে থাকা process দেখেছি
- [ ] `logrotate -d` dry-run পড়েছি
- [ ] `python3 -m unittest -v`-এ ৪টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `journalctl(1)`: https://www.freedesktop.org/software/systemd/man/latest/journalctl.html
- `systemd.journal-fields(7)`: https://www.freedesktop.org/software/systemd/man/latest/systemd.journal-fields.html
- `journald.conf(5)`: https://www.freedesktop.org/software/systemd/man/latest/journald.conf.html
- `logrotate(8)`: https://man7.org/linux/man-pages/man8/logrotate.8.html
- `proc(5)`: https://man7.org/linux/man-pages/man5/proc.5.html
- `lsof(8)`: https://man7.org/linux/man-pages/man8/lsof.8.html
- RFC 5424 — syslog severity: https://www.rfc-editor.org/rfc/rfc5424

---

**পরের lesson:** L01-15 — Performance profiling: top, vmstat, iostat, pidstat, perf
