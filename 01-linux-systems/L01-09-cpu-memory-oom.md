# L01-09 — CPU scheduling, virtual memory, swap ও OOM

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-08 — Process, thread, state ও signal](L01-08-processes-signals.md) |
| **Label** | 🖥️ VM সুপারিশকৃত (memory experiment) |
| **Tested** | `mem_report.py`: ৬টি test পাস; `meminfo`, `load`, `oom` নমুনা data-য় চালানো (Python 3.14, Windows)। Windows-এ আসল `/proc` নেই — tool exit 2 দিয়ে স্পষ্ট error দিয়েছে। নমুনা meminfo ও kernel log হাতে তৈরি (আসল format অনুসরণে)। `free`, `top`, `vmstat`, `systemd-run` memory-limit experiment **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- **CPU scheduling:** একাধিক process কীভাবে CPU ভাগ করে; nice ও priority।
- **Load average** — আসলে কী মাপে (এবং কী মাপে না)।
- **Virtual memory:** প্রতিটি process-এর নিজস্ব address space, page, page table।
- **RSS বনাম VSZ**, **page cache**, এবং কেন "free memory কম" প্রায়ই সমস্যা নয় (**MemAvailable**)।
- **Swap** — সুবিধা ও ঝুঁকি; `swappiness`।
- **OOM killer** — কে, কখন, কাকে মারে; system OOM বনাম **cgroup (container) OOM**।
- **PSI (Pressure Stall Information)** — resource চাপের আধুনিক মাপ।
- Python দিয়ে meminfo, load, PSI ও OOM log বিশ্লেষণ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

সবচেয়ে প্রচলিত তিনটি "server ধীর / crash" অভিযোগ:

1. "Memory ৯৫% ব্যবহৃত!" — monitoring-এ লাল, অথচ system ঠিক চলছে। (Page cache — Section 8.2)
2. "Load average ৮, CPU কিন্তু ২০%!" — (D-state I/O wait — Section 8.1)
3. "Service হঠাৎ মারা গেল, log-এ কিছু নেই।" — (OOM killer, exit 137 — Section 5)

এগুলো ভুল ব্যাখ্যা করলে ভুল সমাধান: অপ্রয়োজনে বড় server কেনা (খরচ), বা আসল সমস্যা (memory leak, ধীর disk) অক্ষত রাখা।

## 3. সহজ ভাষায় পরিচয়

**CPU scheduling:** একটি CPU core একসাথে একটিই task চালায়। Kernel-এর **scheduler** খুব দ্রুত (মিলিসেকেন্ডে) task বদলায়, ফলে মনে হয় সব একসাথে চলছে। Linux-এর default scheduler সব runnable task-কে ন্যায্য ভাগ দেওয়ার চেষ্টা করে; **nice** মান (−২০ থেকে +১৯) দিয়ে ভাগে প্রভাব ফেলা যায় — বেশি nice = বেশি "ভদ্র" = কম ভাগ।

**Load average:** গত ১, ৫ ও ১৫ মিনিটে গড়ে কতগুলো task **CPU চাইছিল (R)** বা **uninterruptible I/O-তে আটকে ছিল (D)**। এটি CPU ব্যবহারের শতাংশ নয়। ৪-core machine-এ load ৪ ≈ পূর্ণ ব্যবহার; ৮ = গড়ে অর্ধেক task অপেক্ষায়।

**Virtual memory:** প্রতিটি process মনে করে তার নিজের বিশাল, ধারাবাহিক memory আছে। আসলে kernel সেই "virtual" address-গুলো ছোট ছোট **page**-এ (সাধারণত ৪ KiB) ভাগ করে, প্রয়োজন অনুযায়ী physical RAM-এর page-এর সাথে মেলায় (**page table**)। এতে process-গুলো একে অপরের memory দেখতে পায় না, এবং একই library-র page অনেক process share করতে পারে।

**Swap:** RAM কম পড়লে কম-ব্যবহৃত page disk-এ সরিয়ে রাখার জায়গা।

**OOM killer:** RAM ও swap দুটোই শেষ হলে kernel একটি process বেছে **SIGKILL** দেয় — system বাঁচাতে। Log-এ "Out of memory: Killed process ..."।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### লাইব্রেরির পড়ার টেবিল

- **RAM** = পড়ার টেবিল (দ্রুত, সীমিত); **disk** = তাক (বড়, ধীর)।
- **Page cache** = আগে পড়া বই টেবিলের কোণে রেখে দেওয়া — আবার লাগলে তাকে যেতে হয় না। নতুন পাঠকের জায়গা লাগলে লাইব্রেরিয়ান এগুলো তাকে ফেরত দেন। টেবিল "ভরা" দেখালেও আসলে জায়গা খালি করা সহজ — এটাই **MemAvailable**।
- **Swap** = কারো খোলা বই (নোট সহ) সাময়িকভাবে তাকে সরিয়ে রাখা — আবার লাগলে আনতে সময় লাগে।
- **OOM killer** = টেবিল ও তাক দুটোই ভরা; লাইব্রেরিয়ান একজন পাঠককে (সবচেয়ে বেশি জায়গা নেওয়া, কম গুরুত্বপূর্ণ) বের করে দেন — নোটিশ ছাড়াই।
- **Scheduler** = একটি কম্পিউটার কয়েকজন পাঠক পালা করে ব্যবহার করছেন, প্রত্যেকে কয়েক মিনিট।

### Analogy কোথায় মেলে না

- লাইব্রেরিতে প্রতিটি পাঠক সত্যিকারের বই পান। Virtual memory-তে process যত memory **চায়** (VSZ) তার অনেকটাই হয়তো কখনো আসল RAM পায় না — kernel "ধার" দেয় (overcommit), ব্যবহার হলে তবেই দেয়। তাই সব process-এর VSZ যোগ করলে RAM-এর চেয়ে অনেক বেশি হতে পারে — এটি স্বাভাবিক।
- লাইব্রেরিয়ান বের করার আগে সতর্ক করতে পারেন। OOM killer **SIGKILL** দেয় — process কিছু লেখার সুযোগ পায় না; তাই application log-এ কিছুই থাকে না, শুধু kernel log-এ।
- Swap-এ রাখা বই আনতে কয়েক মিনিট লাগে; disk-এর তুলনায় RAM-এর গতির পার্থক্য আরো অনেক বেশি (বহু গুণ) — swap-এ নির্ভরশীল system **অত্যন্ত ধীর** হয়ে যায় ("thrashing")।

## 5. Real-world engineering scenario — "service নীরবে মারা যায়"

**পরিস্থিতি:** TaskFlow API প্রতিদিন দুপুরের দিকে হঠাৎ restart হয়। Application log-এ কোনো error নেই — শেষ লাইন স্বাভাবিক একটি request।

**Diagnosis:**

1. `systemctl status taskflow` → `Main process exited, code=killed, status=9/KILL` — SIGKILL (L01-06-এ ১৩৭)।
2. কে পাঠালো? Kernel log:
   ```bash
   journalctl -k --since today | grep -i -E "out of memory|oom"
   ```
3. দুই ধরনের বার্তা হতে পারে (নমুনা — [`sample-kernel.log`](code/L01-09/sample-kernel.log)):
   ```text
   Out of memory: Killed process 4821 (python3) ... anon-rss:6815744kB ...
   Memory cgroup out of memory: Killed process 5530 (taskflow-api) ... anon-rss:262144kB ...
   ```
   - প্রথমটি **পুরো system**-এর memory শেষ — অন্য কোনো process (একটি ৬.৫ GiB-এর python3 script) কারণ, taskflow নয়।
   - দ্বিতীয়টি **cgroup limit** — taskflow-এর নিজের সীমা (systemd `MemoryMax=` বা container-এর `--memory`) ২৫৬ MiB-এ পৌঁছেছে।
4. দ্বিতীয়টি হলে: সীমা কি খুব কম, নাকি **memory leak** (দিনে ক্রমাগত বাড়ে)? `ps -o rss` বা monitoring দিয়ে সময়ের সাথে RSS দেখুন (Module 17)।

**শিক্ষা:** "Killed" দেখলে আগে **কোন scope**-এর OOM তা আলাদা করুন — সমাধান সম্পূর্ণ ভিন্ন (system-এ অন্য process সীমিত করা বনাম নিজের leak ঠিক করা বা সীমা বাড়ানো)।

## 6. Diagram

### Virtual থেকে physical memory

```text
 process A (virtual address space)          physical RAM (page frames)
 ┌──────────────────────────┐               ┌────────────┐
 │ code (python3)      ─────┼──────────────►│ frame 120  │◄──── process B-ও একই
 │ libc.so             ─────┼──────────────►│ frame 121  │      library page share করে
 │ heap (data)         ─────┼──────────────►│ frame 340  │
 │ heap (কখনো ছোঁয়নি)       │ (page নেই — VSZ-এ গোনা, RSS-এ না)
 │ stack               ─────┼──────────────►│ frame 512  │
 └──────────────────────────┘               │ page cache │◄──── disk file-এর copy
            page table (kernel রাখে)          │ (reclaimable)│
                                             └────────────┘
                                              swap (disk) ◄── কম-ব্যবহৃত anon page
```

### Memory-র হিসাব (`free -h`-এর column)

```text
 total ─┬─ used (application-এর anonymous memory ইত্যাদি)
        ├─ buff/cache (page cache — চাহিদা হলে মুক্ত হয়)
        └─ free (সম্পূর্ণ অব্যবহৃত — Linux ইচ্ছা করে কম রাখে)
 available ≈ free + পুনরুদ্ধারযোগ্য cache  ← এটাই দেখুন
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Scheduler | কোন task কখন কোন CPU-তে চলবে ঠিক করে |
| Context switch | এক task থেকে অন্য task-এ CPU বদল |
| nice / priority | Scheduling-এ ভাগের আপেক্ষিক অধিকার (−20 বেশি, +19 কম) |
| Load average | ১/৫/১৫ মিনিটে গড় R + D task সংখ্যা |
| I/O wait (`wa`) | CPU অলস কারণ task I/O-র অপেক্ষায় |
| Virtual memory | Process-এর নিজস্ব address space, kernel physical-এ map করে |
| Page | Memory-র একক (সাধারণত ৪ KiB) |
| RSS | Resident Set Size — এখন RAM-এ থাকা memory |
| VSZ | Virtual size — reserve করা মোট address space |
| Page cache | Disk file-এর RAM copy; reclaimable |
| MemAvailable | নতুন কাজের জন্য swap ছাড়া আনুমানিক কত RAM পাওয়া যাবে |
| Swap | RAM-এর page disk-এ রাখার জায়গা |
| Thrashing | অবিরাম swap in/out — system প্রায় অচল |
| OOM killer | Memory শেষ হলে kernel একটি process SIGKILL করে |
| `oom_score_adj` | কোন process-কে OOM-এ মারার অগ্রাধিকার সমন্বয় (−1000 থেকে +1000) |
| cgroup memory limit | একদল process-এর memory সর্বোচ্চ সীমা (systemd, container) |
| PSI | Pressure Stall Information — resource-এর অভাবে task কত সময় আটকে ছিল |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Load average-এর ফাঁদ

Linux-এ load-এ **D state**-এর task-ও গোনা হয় (অনেক অন্য Unix-এ শুধু CPU)। তাই:

- Load উঁচু + CPU `us`/`sy` উঁচু → সত্যিই CPU-bound।
- Load উঁচু + CPU কম + `wa` উঁচু → **I/O bottleneck** (ধীর disk, NFS) — বড় CPU কিনে লাভ নেই।

```bash
vmstat 1 5      # r = runnable, b = blocked (D), us/sy/id/wa = CPU-র ভাগ
```

### 8.2 কেন "free" কম থাকে

Linux অব্যবহৃত RAM-কে **নষ্ট** মনে করে — তাই disk থেকে পড়া file page cache-এ রাখে। ফলে কয়েক দিন চলা server-এ `free` প্রায় সবসময় কম। প্রশ্ন হলো: **নতুন process-এর জন্য কতটা পাওয়া যাবে** → `MemAvailable` (kernel ৩.১৪+)। Monitoring alert `MemAvailable`-এর উপর হওয়া উচিত, `MemFree`-এর উপর নয়।

### 8.3 Swap ও swappiness

- Swap না থাকলে memory শেষ হওয়ামাত্র OOM — অপ্রত্যাশিত মৃত্যু।
- অনেক swap থাকলে system ধীর হতে হতে অচল — "আধা-মৃত" অবস্থা, যা অনেক সময় দ্রুত মৃত্যুর চেয়ে খারাপ।
- `vm.swappiness` (০–২০০; Ubuntu-তে default সাধারণত ৬০) — cache ছাড়া বনাম anon page swap করার ঝোঁক।
- বাস্তব সিদ্ধান্ত workload অনুযায়ী: database server-এ সাধারণত কম swappiness; Kubernetes node-এ ঐতিহাসিকভাবে swap বন্ধ রাখা হতো (নতুন version-এ swap সমর্থন আসছে — Module 14-এ বর্তমান অবস্থা দেখবেন)।

> **Fedora-তে:** default-ভাবে **zram** (RAM-এর ভেতরে compressed swap) চালু থাকে — `swapon --show`-এ `/dev/zram0` দেখবেন। Ubuntu-তে সাধারণত `/swap.img` file।

### 8.4 OOM killer কাকে বেছে নেয়

প্রতিটি process-এর একটি **`oom_score`** (`/proc/<PID>/oom_score`) — মূলত কত memory ব্যবহার করছে, `oom_score_adj` দিয়ে সমন্বিত। সর্বোচ্চ score-এর process মরে। গুরুত্বপূর্ণ service (যেমন sshd) রক্ষা করতে কম `oom_score_adj` দেওয়া হয়; systemd-এ `OOMScoreAdjust=`।

cgroup limit থাকলে OOM **সেই group-এর ভেতরেই** হয় — বাকি system অক্ষত। এটাই container ও systemd-এর memory limit-এর মূল সুবিধা: একটি service-এর leak পুরো server ডোবায় না।

### 8.5 PSI — আধুনিক মাপ

`/proc/pressure/{cpu,memory,io}`:

```text
some avg10=1.50 avg60=0.40 avg300=0.10 total=123456
full avg10=0.20 avg60=0.05 avg300=0.00 total=9999
```

- `some` = অন্তত একটি task resource-এর অভাবে কত শতাংশ সময় আটকে ছিল।
- `full` = সব (non-idle) task একসাথে আটকে ছিল — সত্যিকারের অচলতা।

"Memory ৯০%"-এর চেয়ে "memory pressure-এ ১০% সময় নষ্ট" অনেক বেশি অর্থবহ — systemd-oomd ও আধুনিক monitoring এটি ব্যবহার করে।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 CPU ও load

```bash
nproc                       # CPU core সংখ্যা
uptime                      # load average
cat /proc/loadavg
top -b -n 1 | head -15      # batch mode, একবার
vmstat 1 5
```

Load কৃত্রিমভাবে বাড়িয়ে দেখুন (নিজের VM-এ, ৬০ সেকেন্ড):

```bash
for i in $(seq "$(nproc)"); do timeout 60 sh -c 'while :; do :; done' & done
sleep 30; uptime
wait
```

**nice-এর প্রভাব:**

```bash
nice -n 19 sh -c 'timeout 20 sh -c "while :; do :; done"' &
timeout 20 sh -c 'while :; do :; done' &
top -b -n 1 | grep -E 'PID| sh$' | head      # NI column ও %CPU তুলনা (একই core-এ প্রতিযোগিতা হলে)
wait
```

Python tool — File: [`code/L01-09/mem_report.py`](code/L01-09/mem_report.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-09
python3 mem_report.py load            # আপনার আসল /proc/loadavg, nproc অনুযায়ী
```

**নমুনা মান দিয়ে আসল output (repository-তে চালানো):**

```text
load 2.1 1.5 0.9 | cpus 4 | runnable now 3/512 tasks
OK (load/cpu = 0.53, trend বাড়ছে)
load 7.8 6.9 5.1 | cpus 4 | runnable now 9/700 tasks
OVERLOADED: runnable/D-state task CPU সংখ্যার চেয়ে অনেক বেশি (load/cpu = 1.95, trend বাড়ছে)
```

### 9.2 Memory

```bash
free -h
cat /proc/meminfo | head -20
ps -eo pid,comm,rss,vsz --sort=-rss | head     # rss/vsz KiB-এ
cat /proc/pressure/memory                       # PSI (kernel ৪.২০+ এবং সক্রিয় থাকলে)
swapon --show
cat /proc/sys/vm/swappiness
```

```bash
python3 mem_report.py meminfo                   # আসল
python3 mem_report.py meminfo sample-meminfo.txt
python3 mem_report.py pressure
```

**নমুনা ([`sample-meminfo.txt`](code/L01-09/sample-meminfo.txt)) দিয়ে আসল output:**

```text
total 7.76 GiB | free 0.3 | available 4.88 | cache 4.69 | used 37.1% | swap used 4.1%
OK: 'free' কম দেখালেও অধিকাংশ page cache — দরকার হলে kernel ফেরত নেয়
```

`free` মাত্র ০.৩ GiB (৪%) — একজন নবীন alarm বাজাতেন। কিন্তু available ৪.৮৮ GiB, ব্যবহৃত মাত্র ৩৭%। হিসাব: (8137600 − 5120800) ÷ 8137600 × 100 = 37.1%।

### 9.3 OOM — নিরাপদভাবে (cgroup limit দিয়ে, ⚠️ শুধু VM-এ)

পুরো system-এর memory শেষ না করে, একটি **ছোট cgroup সীমার ভেতরে** OOM ঘটান:

```bash
sudo systemd-run --scope -p MemoryMax=100M -p MemorySwapMax=0 \
  python3 -c 'x = []
while True: x.append(bytearray(10 * 1024 * 1024))'
echo "exit: $?"
journalctl -k --since "2 min ago" | grep -i "out of memory"
```

| অংশ | অর্থ |
|---|---|
| `systemd-run --scope` | command-কে একটি অস্থায়ী cgroup-এ চালায় |
| `-p MemoryMax=100M` | সেই cgroup-এর memory সীমা (cgroup v2) |
| `-p MemorySwapMax=0` | Swap-এ সরে বাঁচতে না পারে |
| Python loop | প্রতিবার ১০ MiB নিতে থাকে |

প্রত্যাশিত (উদাহরণ): process "Killed", exit 137, kernel log-এ `Memory cgroup out of memory: Killed process ... (python3)`। Script সারা system-এর memory ছোঁয় না — নিরাপদ।

> **Fedora-তে:** একই; Fedora-তে systemd-oomd সক্রিয় থাকে, তাই pressure বাড়লে আগেই ব্যবস্থা নিতে পারে — `journalctl -u systemd-oomd` দেখুন।

**OOM log বিশ্লেষণ:**

```bash
journalctl -k > /tmp/kernel.log
python3 mem_report.py oom /tmp/kernel.log
python3 mem_report.py oom sample-kernel.log; echo "exit=$?"
```

**নমুনা দিয়ে আসল output:**

```text
OOM kill: python3 (pid 4821) anon-rss 6656.0 MiB — whole system
OOM kill: taskflow-api (pid 5530) anon-rss 256.0 MiB — cgroup/container limit
2 OOM kill(s)
exit=1
```

হিসাব: 6815744 kB ÷ 1024 = 6656 MiB; 262144 ÷ 1024 = 256 MiB — সীমা ঠিক ২৫৬ MiB ছিল, তা স্পষ্ট।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_mem_report.py`](code/L01-09/test_mem_report.py)-এর ৬টি test: meminfo parse (`Active(anon)` জাতীয় নাম সহ) ও শতাংশ, verdict স্তর, loadavg ও verdict, PSI parse, OOM log (system বনাম cgroup), ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `r"^(\w+(?:\(\w+\))?):\s+(\d+)"` | `Active(anon)` জাতীয় key ধরে | বন্ধনী-যুক্ত key সাধারণ `\w+`-এ মেলে না |
| `available = MemAvailable or MemFree` | পুরোনো kernel-এ fallback | ৩.১৪-এর আগে MemAvailable ছিল না |
| `used = total − available` | "আসল" ব্যবহার | `total − free` cache-কে ব্যবহৃত ধরত (ভুল alarm) |
| `load_verdict`: load ÷ cpus | Core অনুযায়ী স্বাভাবিকীকরণ | load ৪ এক core-এ সংকট, ১৬ core-এ নগণ্য |
| Trend: load1 বনাম load15 | বাড়ছে না কমছে | Incident-এ "অবস্থা খারাপ হচ্ছে নাকি সেরে উঠছে" জানা জরুরি |
| `OOM_RE`-এ `Memory cgroup` আলাদা | Scope চেনা | Section 5-এর মূল diagnosis |
| `FileNotFoundError` → "Linux /proc only?" | Windows/macOS-এ স্পষ্ট বার্তা | এই repository-তে সেভাবেই পরীক্ষিত |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `free -h` দীর্ঘ চলা server-এ | `free` কম, `available` যথেষ্ট |
| CPU load experiment | `uptime`-এ load ≈ core সংখ্যা |
| cgroup OOM experiment | exit 137, kernel log-এ "Memory cgroup out of memory" |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Memory alert কিন্তু system ঠিক | MemFree-এর উপর alert | `free -h` available | Alert MemAvailable বা PSI-তে |
| Load উঁচু, CPU কম | D-state / I/O wait | `vmstat 1` (`b`, `wa`), `ps` STAT D | Disk/NFS তদন্ত (L01-15) |
| Process নীরবে মরে, exit 137 | OOM | `journalctl -k \| grep -i oom` | Scope চিহ্নিত করে leak/limit ঠিক |
| System অত্যন্ত ধীর, disk light জ্বলছে | Thrashing | `vmstat` `si`/`so` উঁচু | Memory-ভোগী process খুঁজুন; swap বাড়ানো সমাধান নয় |
| `ps`-এ VSZ বিশাল | Reserve করা, ব্যবহৃত নয় | RSS দেখুন | সাধারণত সমস্যা নয় |
| `/proc/pressure` নেই | পুরোনো kernel বা PSI বন্ধ | `uname -r` | Ubuntu 24.04-এ সাধারণত আছে |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Memory limit ছাড়া একটি compromised বা buggy process পুরো server-কে OOM করতে পারে (denial of service)। প্রতিটি service-এ cgroup limit (systemd `MemoryMax=`, container limit)। Swap-এ sensitive data (key) disk-এ লেখা হতে পারে — encrypted swap বিবেচনা।
- **Performance:** RSS ও PSI দেখে sizing; thrashing এড়াতে swap সীমিত; CPU-ভারী batch কাজ `nice`/cgroup `CPUWeight=`।
- **Cost:** ভুল metric (MemFree) দেখে বড় instance কেনা সরাসরি অপচয়। Rightsizing (Module 29)-এর ভিত্তি এই lesson-এর সঠিক মাপ।

## 14. Hands-on exercise

1. নিজের VM-এ `python3 mem_report.py meminfo` ও `free -h` তুলনা করুন। মান মেলে?
2. একটি বড় file পড়ুন (`cat /usr/lib/x86_64-linux-gnu/*.so* > /dev/null`) এবং আগে-পরে `buff/cache` দেখুন। তারপর `sync; echo 1 | sudo tee /proc/sys/vm/drop_caches` (⚠️ শুধু lab-এ — production-এ performance কমায়) দিয়ে cache খালি করে আবার দেখুন।
3. cgroup OOM experiment `MemoryMax=200M` দিয়ে করুন; Python loop-এ কত MiB-এ মারা গেল print যোগ করে মাপুন।
4. `mem_report.py`-তে `top` command যোগ করুন যা `/proc/*/status` থেকে `VmRSS` পড়ে সবচেয়ে বেশি RSS-এর ৫টি process দেখায় (নিজের process; অন্যদের জন্য permission error সামলান)। Test-এ নমুনা status text ব্যবহার করুন।
5. `cat /proc/$(pgrep -o sshd)/oom_score_adj` — sshd-এর মান কত এবং কেন?

## 15. Mini-project — memory leak detector

একটি script লিখুন যা একটি PID-এর RSS প্রতি ৫ সেকেন্ডে N বার মাপে (`/proc/<PID>/status`), তারপর linear trend (প্রতি মিনিটে কত MiB বাড়ছে) ও "এই হারে X মিনিটে Y MiB সীমায় পৌঁছাবে" অনুমান দেয়। একটি ইচ্ছাকৃত leak-যুক্ত Python process দিয়ে পরীক্ষা করুন। L00-06-এর measurement নীতি (একাধিক নমুনা, noise) প্রয়োগ করুন। এটি Project 1 ও Module 17 (alerting)-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. Load average কী মাপে? ৮-core server-এ load ৪ কি সমস্যা?
2. Load উঁচু কিন্তু CPU usage কম — সম্ভাব্য কারণ?
3. `free`-এ "free" কম কিন্তু "available" বেশি — চিন্তার কিছু আছে?
4. RSS ও VSZ-এর পার্থক্য কী?
5. OOM killer কীভাবে process বেছে নেয়? কোনো process-কে কীভাবে রক্ষা করবেন?
6. Container OOM ও host OOM কীভাবে আলাদা করবেন?
7. Swap রাখা উচিত কি? trade-off কী?
8. PSI কী এবং utilization-এর চেয়ে কেন ভালো সংকেত?

## 17. Self-assessment প্রশ্ন

1. লাইব্রেরি analogy দিয়ে page cache, swap ও OOM; analogy কোথায় মেলে না?
2. নমুনা meminfo-য় used% হাতে হিসাব করুন।
3. Section 5-এর দুটি OOM বার্তার পার্থক্য ও প্রতিটির সমাধান।
4. `systemd-run` experiment কেন পুরো system-এর জন্য নিরাপদ?
5. Fedora-র zram ও Ubuntu-র swap file-এর পার্থক্য।
6. `load_verdict` কেন load-কে CPU সংখ্যা দিয়ে ভাগ করে?

## 18. সংক্ষিপ্ত সারাংশ

- Scheduler CPU ভাগ করে; **nice** দিয়ে প্রভাব। **Load average** = R + D task — CPU% নয়; core দিয়ে ভাগ করে পড়ুন; উঁচু load + কম CPU = I/O।
- **Virtual memory:** প্রতিটি process-এর নিজস্ব address space; **RSS** আসল, **VSZ** reserve।
- **Page cache** reclaimable — **MemAvailable** দেখুন, MemFree নয়।
- **Swap** নিরাপত্তা-জাল কিন্তু thrashing ঝুঁকি; Fedora-তে zram।
- **OOM killer** SIGKILL দেয় (১৩৭); system বনাম **cgroup** OOM আলাদা করুন; প্রতিটি service-এ memory limit।
- **PSI** resource চাপের সবচেয়ে অর্থবহ মাপ।

## 19. Completion checklist

- [ ] `uptime`, `vmstat`, `top`, `free -h`, `/proc/meminfo`, `/proc/pressure/memory` পড়তে পারি
- [ ] CPU load experiment ও nice পরীক্ষা করেছি
- [ ] cgroup OOM নিরাপদে ঘটিয়ে kernel log-এ দেখেছি
- [ ] `mem_report.py`-এর চারটি command চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] Exercise ১ ও ৩ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `proc(5)` — `/proc/meminfo`, `/proc/loadavg`: https://man7.org/linux/man-pages/man5/proc.5.html
- Kernel docs — PSI: https://docs.kernel.org/accounting/psi.html
- Kernel docs — cgroup v2 memory controller: https://docs.kernel.org/admin-guide/cgroup-v2.html
- Kernel docs — `/proc/sys/vm/` (swappiness, overcommit): https://docs.kernel.org/admin-guide/sysctl/vm.html
- `systemd.resource-control(5)` (`MemoryMax=`): https://www.freedesktop.org/software/systemd/man/latest/systemd.resource-control.html
- `systemd-run(1)`: https://www.freedesktop.org/software/systemd/man/latest/systemd-run.html
- `vmstat(8)`: https://man7.org/linux/man-pages/man8/vmstat.8.html

---

**পরের lesson:** L01-10 — systemd: unit, service, target ও journald
