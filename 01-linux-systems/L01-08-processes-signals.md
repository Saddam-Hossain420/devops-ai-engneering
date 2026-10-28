# L01-08 — Process, thread, process state ও signal

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-07 — Pipe ও text tools](L01-07-pipes-text-tools.md) |
| **Label** | — (সব signal নিজের তৈরি process-এ) |
| **Tested** | ৬টি test-এর ৪টি পাস (Python 3.14, Windows); **২টি signal test skip** — Windows-এ POSIX signal নেই, Ubuntu-তে চলবে। `ps_tree.py` নমুনা data-য় ও `graceful_worker.py` (signal ছাড়া, স্বাভাবিক শেষ) Windows-এ চালানো হয়েছে। `ps`, `kill`, `pstree`, `/proc` command **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। `sample-ps.txt` হাতে তৈরি। |

---

## 1. এই lesson-এ যা শিখবেন

- **Program বনাম process বনাম thread।**
- Process কীভাবে জন্মায় (`fork`/`clone` + `execve`) ও মরে (`exit` + parent-এর `wait`)।
- **PID, PPID**, process tree, PID 1-এর বিশেষ দায়িত্ব।
- **Process state:** R, S, D, T, Z — কোনটি স্বাভাবিক, কোনটি বিপদের সংকেত।
- **Zombie** ও **orphan** process।
- **Signal:** SIGTERM, SIGKILL, SIGHUP, SIGINT — কে পাঠায়, কে ধরতে পারে।
- **Graceful shutdown** — কেন service-কে SIGTERM সঠিকভাবে সামলাতে হয় (systemd, Docker, Kubernetes)।
- Python: process tree analyzer ও signal-aware worker।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Production-এর অনেক incident process-এর আচরণ থেকে আসে:

- Deploy-এর সময় service বন্ধ হলো — অর্ধেক লেখা data নষ্ট, কারণ process SIGTERM উপেক্ষা করেছে এবং ১০ সেকেন্ড পরে SIGKILL খেয়েছে।
- `ps`-এ শত শত `<defunct>` process — PID শেষ হয়ে নতুন process তৈরি করা যাচ্ছে না।
- একটি process `kill -9`-এও মরে না — কারণ D state-এ (NFS server উত্তর দিচ্ছে না)।
- Load average ১০, অথচ CPU প্রায় খালি — D state-এর process load-এ গোনা হয় (L01-09)।

Process ও signal বোঝা মানে এসব দেখে **সঠিক কারণ** বলতে পারা, এবং নিজের service এমনভাবে লেখা যাতে সেগুলো না ঘটে।

## 3. সহজ ভাষায় পরিচয়

- **Program** = disk-এর একটি file (যেমন `/usr/bin/python3`) — নিষ্ক্রিয়।
- **Process** = সেই program-এর একটি চলমান instance: নিজস্ব memory, খোলা file, PID, owner (UID), environment, current directory। একই program থেকে অনেক process হতে পারে (nginx-এর worker-গুলো)।
- **Thread** = একটি process-এর ভেতরে একাধিক execution প্রবাহ, যারা **একই memory** share করে। Linux kernel thread-কেও আলাদা "task" হিসেবে schedule করে।
- **PID** = process-এর নম্বর; **PPID** = যে process তাকে তৈরি করেছে (parent)।
- **Signal** = একটি process-কে পাঠানো ছোট asynchronous বার্তা — "বন্ধ হও", "reload করো", "থামো"।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্টুরেন্টের রান্নাঘর

- **Program** = রেসিপি বই। **Process** = একজন রাঁধুনি সেই রেসিপি অনুযায়ী এখন রান্না করছেন — নিজের চুলা, বাসন, উপকরণ (memory, file) নিয়ে।
- **Thread** = একই রাঁধুনির দুই হাত একই চুলা ও উপকরণ ব্যবহার করে একসাথে দুটি কাজ করছে। শেয়ার করা জিনিসে সাবধান না হলে দুই হাত একে অপরের কাজ নষ্ট করে (race condition)।
- **Parent/child** = প্রধান রাঁধুনি সহকারী নিয়োগ করেন; সহকারী কাজ শেষে রিপোর্ট দেন (exit status), প্রধান রাঁধুনি সেটি গ্রহণ করেন (`wait`)।
- **Zombie** = সহকারী কাজ শেষ করে বাড়ি চলে গেছেন, কিন্তু তাঁর নাম-লেখা রিপোর্ট কার্ড টেবিলে পড়ে আছে কারণ প্রধান রাঁধুনি কখনো পড়েননি। কার্ডগুলো জায়গা নিচ্ছে।
- **SIGTERM** = ম্যানেজার: "রেস্টুরেন্ট বন্ধ হচ্ছে, হাতের খাবার শেষ করে চুলা নিভিয়ে যান।" **SIGKILL** = হঠাৎ বিদ্যুৎ বন্ধ — চুলায় যা ছিল তাই।

### Analogy কোথায় মেলে না

- সহকারী চলে গেলে কার্ড শুধু টেবিলে থাকে। Zombie আসলে প্রায় কোনো resource নেয় না (memory মুক্ত) — শুধু **process table-এর একটি entry ও PID**। সমস্যা হয় যখন হাজারে হাজারে জমে PID শেষ হয়।
- রাঁধুনি চাইলে বিদ্যুৎ বন্ধের নির্দেশ উপেক্ষা করতে পারেন না — এটি মেলে: **SIGKILL ও SIGSTOP ধরা, আটকানো বা উপেক্ষা করা যায় না**। কিন্তু SIGTERM উপেক্ষা করা *যায়* — ভালো service তা করে না।
- প্রধান রাঁধুনি চলে গেলে সহকারীরা বেকার হন। Linux-এ parent মরে গেলে child **orphan** হয় এবং PID 1 (বা নির্ধারিত "subreaper") তাদের দত্তক নেয়।

## 5. Real-world engineering scenario — deploy-এ data নষ্ট

**পরিস্থিতি:** একটি Python worker queue থেকে কাজ নিয়ে database-এ লেখে। প্রতিটি deploy-এর পরে কিছু কাজ "অর্ধেক" অবস্থায় পাওয়া যায়।

**ঘটনার ক্রম:**

1. Deploy pipeline `systemctl restart worker` চালায় (Kubernetes হলে Pod মুছে নতুন তৈরি)।
2. systemd worker-কে **SIGTERM** পাঠায় এবং অপেক্ষা করে (default timeout প্রায় ৯০ সেকেন্ড; Kubernetes-এ termination grace period default ৩০ সেকেন্ড)।
3. Worker-এর code-এ SIGTERM handler নেই। Python-এর default আচরণে SIGTERM পেলে process সঙ্গে সঙ্গে শেষ হয় — চলমান transaction মাঝপথে।
4. ফলাফল: অর্ধেক লেখা data।

**আরেকটি রূপ:** worker shell script দিয়ে চালু হয় — `bash start.sh` যা ভেতরে `python3 worker.py` চালায়। SIGTERM যায় **bash**-এ, bash সেটি child python-এ পাঠায় না; timeout শেষে SIGKILL → exit **137** (L01-06)। Container-এ এটি খুব সাধারণ — সমাধান `exec python3 worker.py` (bash-এর জায়গায় python নিজেই PID হয়ে যায়)।

**সঠিক সমাধান:** এই lesson-এর `graceful_worker.py`-এর মতো — SIGTERM-এ নতুন কাজ নেওয়া বন্ধ, চলমান কাজ শেষ, তারপর exit 0।

**Diagnosis:** `journalctl -u worker` — "Stopping..." থেকে "Stopped" পর্যন্ত সময়; exit status 143 বা 137; `State 'stop-sigterm' timed out. Killing.` বার্তা।

## 6. Diagram

### Process-এর জীবনচক্র

```text
  parent (bash, PID 1803)
     │ fork()/clone()  ──► child (PID 1990): parent-এর copy
     │                         │ execve("/usr/bin/ps")  ──► memory-তে নতুন program
     │                         │ ... চলে ...
     │                         │ exit(0)
     │                         ▼
     │                    ZOMBIE (Z): শুধু PID ও exit status রয়ে গেছে
     │ wait()/waitpid()  ◄──── exit status নেয়
     ▼                         ▼
  চলতে থাকে                 সম্পূর্ণ মুছে যায় (reaped)
```

### Process state

```text
                ┌──── CPU পায় ────┐
                ▼                 │
  তৈরি ──► R (runnable) ──────────┘
            │    ▲
   I/O বা   │    │ ঘটনা ঘটল
   অপেক্ষা ▼    │
        S (interruptible sleep)   ← signal-এ জাগে; বেশিরভাগ process এখানে
        D (uninterruptible sleep) ← disk/NFS I/O; signal (SIGKILL-ও) অপেক্ষা করে
            │
   SIGSTOP/ │ SIGCONT
   Ctrl+Z   ▼
        T (stopped)
            │
     exit   ▼
        Z (zombie) ──► parent wait() ──► শেষ
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Process | চলমান program-এর instance, নিজস্ব memory ও resource সহ |
| Thread | একই process-এর ভেতরে memory share করা execution প্রবাহ |
| PID / PPID | Process ID / parent-এর PID |
| `fork` / `clone` | বর্তমান process-এর copy তৈরি (Linux-এ `clone` মূল system call) |
| `execve` | Process-এর ভেতরে নতুন program load (PID একই থাকে) |
| `wait` | Parent child-এর exit status সংগ্রহ করে |
| Zombie | শেষ হয়েছে কিন্তু parent এখনো `wait` করেনি |
| Orphan | Parent আগে মারা গেছে; PID 1 দত্তক নেয় |
| PID 1 / init | প্রথম user-space process (Ubuntu-তে systemd); orphan reap করে |
| Signal | Process-কে পাঠানো asynchronous বার্তা |
| Signal handler | Signal এলে চালানোর জন্য program-এর নিজস্ব function |
| Graceful shutdown | চলমান কাজ শেষ করে পরিষ্কারভাবে বন্ধ হওয়া |
| Load average | R + D state-এর গড় task সংখ্যা (L01-09) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 প্রধান signal

| Signal | নং | Default | কে পাঠায় / কখন | ধরা যায়? |
|---|---|---|---|---|
| SIGHUP | 1 | শেষ | Terminal বন্ধ; প্রচলিতভাবে "config reload" (nginx, sshd) | হ্যাঁ |
| SIGINT | 2 | শেষ | Ctrl+C | হ্যাঁ |
| SIGQUIT | 3 | core dump | Ctrl+\ | হ্যাঁ |
| SIGKILL | 9 | শেষ | `kill -9`, OOM killer, timeout-এর পরে systemd/Docker | **না** |
| SIGSEGV | 11 | core dump | অবৈধ memory access | হ্যাঁ (সাধারণত উচিত নয়) |
| SIGPIPE | 13 | শেষ | বন্ধ pipe-এ লেখা | হ্যাঁ |
| SIGTERM | 15 | শেষ | `kill` (default), `systemctl stop`, `docker stop`, Kubernetes | হ্যাঁ — **ধরা উচিত** |
| SIGCHLD | 17 | উপেক্ষা | Child শেষ হলে parent-কে | হ্যাঁ |
| SIGCONT / SIGSTOP | 18 / 19 | চালু / থামা | Job control | SIGSTOP **না** |

(নম্বর Linux x86-64-এর; architecture ভেদে কিছু আলাদা — সবসময় নাম ব্যবহার করুন: `kill -TERM`।)

### 8.2 Graceful shutdown-এর নিয়ম

1. SIGTERM handler-এ শুধু একটি flag সেট করুন (handler-এ ভারী কাজ ঝুঁকিপূর্ণ)।
2. Main loop flag দেখে নতুন কাজ নেওয়া বন্ধ করে।
3. চলমান কাজ শেষ, connection বন্ধ, buffer flush।
4. Exit 0।
5. সবকিছু **timeout-এর মধ্যে** (systemd `TimeoutStopSec`, Kubernetes `terminationGracePeriodSeconds`) — না হলে SIGKILL।

### 8.3 Zombie কেন জমে ও সমাধান

Zombie জমে যখন parent `wait` করে না (bug)। Zombie-কে `kill` করে লাভ নেই — সে ইতিমধ্যে মৃত! সমাধান:

- Parent-এর bug ঠিক করা (`SIGCHLD` handle বা নিয়মিত `wait`)।
- Parent-কে restart/kill করা → zombie-রা orphan → PID 1 তাদের reap করে।

Container-এ PID 1 প্রায়ই আপনার app (systemd নয়) — app zombie reap না করলে জমে। তাই container-এ `tini` বা `docker run --init` (Module 09)।

### 8.4 D state

Disk বা network filesystem-এর I/O-র মাঝে process D state-এ যায় — kernel I/O শেষ না হওয়া পর্যন্ত signal deliver করে না, **SIGKILL-ও নয়**। স্বাভাবিকভাবে মাইক্রোসেকেন্ড থাকে; দীর্ঘ সময় D মানে ব্যর্থ disk, ঝুলে থাকা NFS server, বা storage সমস্যা। `cat /proc/<PID>/stack` (root) বা `cat /proc/<PID>/wchan` দিয়ে কোথায় আটকে আছে দেখা যায়।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 Process দেখা

```bash
ps -ef | head                        # সব process, full format
ps -eo pid,ppid,stat,user,comm --forest | head -30   # tree আকারে
pstree -p | head                     # সুন্দর tree, PID সহ
cat /proc/$$/status | head -12       # $$ = বর্তমান shell-এর PID
ls /proc/$$/task                     # এই process-এর thread (task) তালিকা
ps -eLf | head                       # -L: প্রতিটি thread আলাদা লাইনে
```

> **Fedora-তে:** একই command; `pstree` না থাকলে `sudo dnf install psmisc` (Ubuntu-তে `psmisc` সাধারণত আগে থেকেই থাকে)।

### 9.2 Process tree analyzer

File: [`code/L01-08/ps_tree.py`](code/L01-08/ps_tree.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-08
ps -eo pid,ppid,stat,user,comm --no-headers > /tmp/ps.txt
python3 ps_tree.py /tmp/ps.txt | head -40
```

**নমুনা data ([`sample-ps.txt`](code/L01-08/sample-ps.txt), হাতে তৈরি) দিয়ে আসল output:**

```bash
python3 ps_tree.py sample-ps.txt; echo "exit=$?"
```

```text
systemd (1) [Ss] root
├─ systemd-journald (412) [Ss] root
├─ sshd (655) [Ss] root
│  └─ sshd (1800) [Ss] root
│     └─ sshd (1802) [S] sami
│        └─ bash (1803) [Ss] sami
│           └─ ps (1990) [R+] sami
├─ nginx (901) [Ss] root
│  ├─ nginx (902) [S] www-data
│  └─ nginx (903) [S] www-data
├─ taskflow-api (1200) [Ss] app
│  ├─ python3 (1201) [Sl] app
│  ├─ python3 (1250) [Z] app
│  ├─ python3 (1251) [Z] app
│  └─ python3 (1252) [Z] app
└─ rsync (2100) [D] root

states:
  D    1  uninterruptible sleep (সাধারণত disk/NFS I/O; signal-এও জাগে না)
  I    1  idle kernel thread
  R    1  running / runnable (CPU-তে বা queue-তে)
  S   12  interruptible sleep (কিছুর অপেক্ষায় — সবচেয়ে সাধারণ)
  Z    3  zombie (শেষ হয়েছে, parent এখনো exit status নেয়নি)
ZOMBIE: 3 zombie child(ren) of taskflow-api (1200) — parent does not wait(); fix/restart the parent
D-STATE: rsync (2100) is in uninterruptible I/O wait — check disk/NFS
exit=1
```

**পড়তে শিখুন:**

- SSH login-এর chain: `sshd (root)` → `sshd (sami)` → `bash` → `ps` — আপনার নিজের session।
- nginx: root master, `www-data` worker — privilege separation (L01-05)।
- `STAT`-এর অতিরিক্ত অক্ষর: `s` = session leader, `l` = multi-threaded, `+` = foreground, `<` = উচ্চ priority।
- `kthreadd` (PID 2) ও kernel thread PID 1-এর tree-তে নেই — তাদের parent PPID 0 (kernel); `--root 2` দিয়ে দেখুন।

### 9.3 Signal পাঠানো ও exit code (নিজের process-এ)

```bash
sleep 300 &                  # background-এ
jobs -l                      # job নম্বর ও PID
kill -STOP %1; ps -o pid,stat,comm -p $!     # T state
kill -CONT %1; ps -o pid,stat,comm -p $!     # আবার S
kill -TERM %1; wait %1; echo "exit: $?"      # 143
```

### 9.4 Graceful worker

File: [`code/L01-08/graceful_worker.py`](code/L01-08/graceful_worker.py)

```bash
python3 graceful_worker.py --job-seconds 2 &
sleep 3
kill -HUP %1                 # reload — বন্ধ হবে না
sleep 1
kill -TERM %1                # চলমান job শেষ করে বন্ধ
wait %1; echo "exit: $?"     # 0
```

প্রত্যাশিত গঠন (Ubuntu-তে; উদাহরণ, PID ভিন্ন):

```text
[worker 4321] started
[worker 4321] job 1 done
[worker 4321] SIGHUP: reloading config (#1)
[worker 4321] got SIGTERM, finishing current job
[worker 4321] job 2 done
[worker 4321] clean shutdown after 2 job(s)
exit: 0
```

এখন তুলনা — SIGKILL:

```bash
python3 graceful_worker.py --job-seconds 2 &
sleep 1; kill -KILL %1; wait %1; echo "exit: $?"    # 137, "clean shutdown" নেই
```

**এই repository-তে Windows-এ চালানো আসল output (signal ছাড়া, `--max-jobs 2`):**

```text
[worker 31616] started
[worker 31616] job 1 done
[worker 31616] job 2 done
[worker 31616] clean shutdown after 2 job(s)
exit=0
```

### 9.5 Zombie নিজে তৈরি করুন (শিক্ষার জন্য, নিরাপদ)

```bash
python3 -c '
import os, time
pid = os.fork()
if pid == 0:
    os._exit(0)          # child সঙ্গে সঙ্গে শেষ
time.sleep(30)           # parent wait() করে না
' &
sleep 1
ps -o pid,ppid,stat,comm --ppid $!     # child: Z <defunct>
wait                                   # ৩০ সেকেন্ড পরে parent শেষ → PID 1 zombie reap করে
```

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_l01_08.py`](code/L01-08/test_l01_08.py)-এর ৬টি test: ps parse (space-যুক্ত comm সহ), tree গঠন, zombie ও D-state সতর্কতা, CLI exit code, এবং **Linux-এ** আসল subprocess-এ SIGHUP + SIGTERM পাঠিয়ে graceful exit 0 এবং SIGKILL-এ "clean shutdown" না হওয়া যাচাই (Windows-এ এই ২টি skip)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `line.split(None, 4)` | সর্বোচ্চ ৫ ভাগ | কিছু process নামে space থাকে |
| `render_tree()` recursive | Parent → children | `pstree`-এর মতো |
| `Counter(p.ppid for zombie)` | কোন parent কতগুলো zombie রাখছে | সমাধান parent-এ — তাই parent চিহ্নিত করা জরুরি |
| `signal.signal(SIGTERM, on_term)` | Handler বসানো | Default (সঙ্গে সঙ্গে মৃত্যু) বদলানো |
| Handler শুধু flag সেট | `stop_requested = True` | Handler-এ জটিল কাজ (I/O, lock) deadlock বা অসংগতি তৈরি করতে পারে |
| ছোট `sleep(0.05)` loop | Signal দ্রুত লক্ষ্য করা | দীর্ঘ blocking call-এ flag দেরিতে দেখা হয় |
| `flush=True` | Output সঙ্গে সঙ্গে | Pipe-এ buffering-এ মৃত্যুর আগের log হারিয়ে যায় |
| Test: `returncode == -SIGKILL` | Python-এ negative মান = signal-এ মৃত্যু | Shell-এ একই জিনিস 128+9 = 137 |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `kill -TERM` sleep-এ | exit 143 |
| `graceful_worker.py` + SIGTERM | "clean shutdown", exit 0 |
| `graceful_worker.py` + SIGKILL | exit 137, shutdown বার্তা নেই |
| Zombie demo | `Z <defunct>`, ৩০ সেকেন্ড পরে অদৃশ্য |
| `python3 -m unittest -v` (Ubuntu) | `Ran 6 tests`, `OK` (skip নেই) |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `kill -9`-এও process মরে না | D state, বা আগে থেকেই zombie | `ps -o stat -p PID` | D: storage/NFS সমস্যা খুঁজুন; Z: parent ঠিক করুন |
| শত শত `<defunct>` | Parent wait করে না | `ps -eo ppid,stat \| awk '$2 ~ /Z/'` | Parent restart; code ঠিক; container-এ `--init` |
| Stop-এ ৯০ সেকেন্ড লাগে, তারপর 137 | SIGTERM handle হয় না বা shell wrapper | `journalctl -u svc` | Handler যোগ; script-এ `exec` |
| Ctrl+C-তে script থামে, কিন্তু child চলতে থাকে | Child আলাদা process group / background | `pstree -p` | Script-এ `trap` দিয়ে child বন্ধ (L04-04) |
| Terminal বন্ধ করলে program মরে যায় | SIGHUP | — | `nohup`, `tmux`, বা systemd service (L01-10) |
| `kill: (PID) - Operation not permitted` | অন্য user-এর process | `ps -o user -p PID` | নিজের process-এ; প্রয়োজনে `sudo` |

## 13. Security, performance ও cost বিবেচনা

- **Security:** অন্য user-এর process-এ signal পাঠানো যায় না (root ছাড়া)। `/proc/<PID>/environ` ও `cmdline` থেকে secret ফাঁস হতে পারে — command line-এ password দেবেন না। `kill -9` অভ্যাস নয়; আগে TERM, অপেক্ষা, তারপর KILL।
- **Performance:** Thread memory share করে — তৈরি সস্তা কিন্তু synchronization জটিল; process আলাদা — নিরাপদ কিন্তু ভারী। Python-এর GIL-এর কারণে CPU-ভারী কাজে multiprocessing (Module 05)। প্রতিটি request-এ নতুন process (`fork`) ব্যয়বহুল — server-গুলো worker pool রাখে।
- **Cost:** Ungraceful shutdown = হারানো কাজ, retry, data মেরামত — deploy যত ঘন (L00-01), তত বড় খরচ।

## 14. Hands-on exercise

1. `ps -eo pid,ppid,stat,comm --sort=-pcpu | head` — CPU-তে সবচেয়ে বেশি কে? `--sort=-rss` দিয়ে memory।
2. `graceful_worker.py`-কে একটি shell wrapper (`run.sh`: `python3 graceful_worker.py`) দিয়ে চালান, wrapper-এ SIGTERM দিন। কী হয়? তারপর `exec python3 ...` দিয়ে আবার চেষ্টা করুন। পার্থক্য notebook-এ লিখুন।
3. `ps_tree.py`-তে `--user USER` filter যোগ করুন। Test লিখুন।
4. `strace -f -e trace=clone,execve,wait4 bash -c 'ls >/dev/null'` (L01-01) — fork/exec/wait নিজের চোখে দেখুন।
5. `cat /proc/1/status | grep -E 'Name|Threads'` ও `cat /proc/<nginx-master-PID>/status` তুলনা করুন।

## 15. Mini-project — stop-time tester

একটি script লিখুন যা একটি command চালায়, N সেকেন্ড পরে SIGTERM পাঠায়, কত সময়ে exit হলো এবং exit code কী তা মাপে; একটি timeout-এর পরে SIGKILL পাঠায় এবং report করে "graceful" না "killed"। নিজের worker ও একটি সাধারণ `sleep` দিয়ে পরীক্ষা করুন। এটি systemd (L01-10) ও Kubernetes-এর termination আচরণের ছোট simulation।

## 16. Interview প্রশ্ন

1. Process ও thread-এর পার্থক্য কী?
2. `fork` ও `exec` কী? `bash`-এ `ls` চালালে কী ঘটে?
3. Zombie process কী, কীভাবে তৈরি হয়, কীভাবে সরাবেন? `kill -9` কেন কাজ করে না?
4. SIGTERM ও SIGKILL-এর পার্থক্য কী? কেন সবসময় আগে SIGTERM?
5. D state কী এবং কেন process kill হয় না?
6. Container-এ PID 1 কেন বিশেষ? `exec` কেন গুরুত্বপূর্ণ?
7. Graceful shutdown কীভাবে implement করবেন?

## 17. Self-assessment প্রশ্ন

1. রান্নাঘর analogy-তে zombie ও orphan; analogy কোথায় মেলে না?
2. Process-এর জীবনচক্র (fork → exec → exit → wait) নিজের ভাষায়।
3. Section 5-এর দুটি রূপে SIGTERM কেন worker-এ পৌঁছায়নি বা কাজে লাগেনি?
4. নমুনা ps-এ কোন process দুটি সমস্যার এবং কেন?
5. Signal handler-এ শুধু flag সেট করা কেন ভালো?
6. Signal test Windows-এ skip কেন, এবং Ubuntu-তে কী যাচাই করবে?

## 18. সংক্ষিপ্ত সারাংশ

- **Program** file; **process** চলমান instance (PID, memory, fd); **thread** একই memory share করে।
- জন্ম `fork/clone + execve`; মৃত্যু `exit` + parent-এর `wait`; না নিলে **zombie**; parent মরলে **orphan** → PID 1।
- State: R, S (স্বাভাবিক), **D** (I/O-তে আটকে, kill হয় না), T, **Z**।
- **SIGTERM** ভদ্র অনুরোধ — ধরুন ও graceful shutdown করুন; **SIGKILL** ধরা যায় না (137)। Shell wrapper-এ `exec`।

## 19. Completion checklist

- [ ] `ps --forest`, `pstree -p`, `/proc/$$/status` দিয়ে নিজের session-এর tree দেখেছি
- [ ] STOP/CONT/TERM/KILL নিজের process-এ পাঠিয়ে state ও exit code দেখেছি
- [ ] `graceful_worker.py` SIGHUP ও SIGTERM দিয়ে চালিয়েছি; SIGKILL-এর সাথে তুলনা
- [ ] Zombie তৈরি ও reap হওয়া দেখেছি
- [ ] Ubuntu-তে `python3 -m unittest -v`-এ ৬টি test পাস (skip নেই)
- [ ] Exercise ২ (wrapper বনাম exec) শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `signal(7)`: https://man7.org/linux/man-pages/man7/signal.7.html
- `ps(1)` (STAT code-এর তালিকা "PROCESS STATE CODES"-এ): https://man7.org/linux/man-pages/man1/ps.1.html
- `fork(2)`, `execve(2)`, `wait(2)`: https://man7.org/linux/man-pages/man2/fork.2.html
- `proc(5)` — `/proc/<pid>/status`: https://man7.org/linux/man-pages/man5/proc.5.html
- Python `signal` module: https://docs.python.org/3/library/signal.html
- systemd `KillMode=`/`TimeoutStopSec=` (`systemd.kill(5)`): https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html

---

**পরের lesson:** L01-09 — CPU scheduling, virtual memory, swap ও OOM
