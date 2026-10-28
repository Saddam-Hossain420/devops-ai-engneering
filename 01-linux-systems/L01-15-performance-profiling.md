# L01-15 — Performance profiling: top, vmstat, iostat, pidstat, perf

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-14 — Log ও debugging](L01-14-logs-and-debugging.md); [L01-09 — CPU ও memory](L01-09-cpu-memory-oom.md) |
| **Label** | 🖥️ VM (`perf` VM-এ সীমিত হতে পারে) |
| **Tested** | ৫টি test পাস; `use_check.py` নমুনা vmstat/iostat-এ চালানো; `slow_app.py` **cProfile দিয়ে আসলে profile ও তিনবার সময় মাপা হয়েছে** (Python 3.14, Windows — সংখ্যা সেখানকার)। নমুনা vmstat/iostat হাতে তৈরি (sysstat-এর column নাম অনুসরণে)। `top`, `vmstat`, `iostat`, `pidstat`, `perf` **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- Performance তদন্তের পদ্ধতি — অনুমান নয়: **USE method** (Utilization, Saturation, Errors)।
- "প্রথম ৬০ সেকেন্ড" checklist: `uptime`, `vmstat`, `mpstat`, `pidstat`, `iostat`, `free`, `sar`।
- System-স্তর (কোন resource শেষ) বনাম application-স্তর (code-এর কোথায় সময় যায়) — **profiling**।
- `perf` ও flame graph-এর ধারণা; Python-এ `cProfile`।
- কেন optimization-এর আগে মাপতে হয় — এবং **workload-এর আকার** কীভাবে ফলাফল বদলায় (এই lesson-এ আসলে দেখা গেছে)।
- Python দিয়ে vmstat/iostat থেকে USE table।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

"Server ধীর" — সবচেয়ে অস্পষ্ট অভিযোগ। ভুল পদ্ধতি: অনুমান করে কিছু বদলানো ("CPU বাড়াই", "cache যোগ করি")। ফলাফল: খরচ বাড়ে, সমস্যা থাকে।

Performance সমস্যা দুই স্তরে:

1. **System:** কোনো resource (CPU, memory, disk, network) শেষ বা অপেক্ষায় — **USE method** দিয়ে কয়েক মিনিটে চিহ্নিত।
2. **Application:** resource যথেষ্ট, কিন্তু code অদক্ষ — **profiler** দেখায় কোন function-এ সময় যায়।

DevOps/SRE-র কাজ প্রথমটি দ্রুত চিহ্নিত করা এবং দ্বিতীয়টির জন্য developer-কে **প্রমাণ** (profile) দেওয়া।

## 3. সহজ ভাষায় পরিচয়

**USE method** (Brendan Gregg): প্রতিটি resource-এর জন্য তিনটি প্রশ্ন —

| প্রশ্ন | অর্থ | উদাহরণ |
|---|---|---|
| **U**tilization | কত শতাংশ সময় ব্যস্ত? | CPU ৯০%, disk `%util` ১০০% |
| **S**aturation | কাজ কি অপেক্ষায় জমছে? | Run queue > CPU সংখ্যা, disk queue, swap |
| **E**rrors | কোনো ত্রুটি? | Disk I/O error, network drop |

Resource-এর তালিকা ধরে হাঁটলে কিছু বাদ পড়ে না।

**Profiling** = program চলার সময় কোন function কতবার ডাকা হলো ও কত সময় নিল তা মাপা। দুই ধরন:

- **Deterministic** (যেমন Python-এর `cProfile`): প্রতিটি function call মাপে — সঠিক, কিন্তু overhead বেশি।
- **Sampling** (যেমন `perf`, `py-spy`): প্রতি কয়েক মিলিসেকেন্ডে "এখন কোথায়?" দেখে — overhead কম, production-এ নিরাপদ।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্টুরেন্টের ভিড়

রেস্টুরেন্টে খাবার আসতে দেরি:

- **Utilization:** রাঁধুনি কত সময় ব্যস্ত? (১০০% হলে আর জায়গা নেই)
- **Saturation:** অর্ডারের লাইন কত লম্বা? (রাঁধুনি ৯০% ব্যস্ত কিন্তু লাইন নেই = ঠিক আছে; ৮০% কিন্তু লাইন বাড়ছে = সমস্যা)
- **Errors:** কতগুলো অর্ডার ভুল বা পুড়ে গেছে?
- রাঁধুনি, চুলা, ফ্রিজ, waiter — প্রতিটির জন্য তিনটি প্রশ্ন। হয়তো রাঁধুনি অলস, কারণ ফ্রিজ (disk) থেকে উপকরণ আনতেই সময় যাচ্ছে।
- **Profiling** = একজন রাঁধুনির কাজ stopwatch দিয়ে মাপা: পেঁয়াজ কাটায় ৪০%, রান্নায় ২০% — তখন বোঝা যায় নতুন চুলা নয়, ভালো ছুরি দরকার।

### Analogy কোথায় মেলে না

- রাঁধুনি অপেক্ষা করলে চোখে পড়ে। CPU "অলস" দেখালেও আসলে **I/O wait**-এ আটকে থাকতে পারে (`wa`) — `top`-এ CPU কম দেখে "সব ঠিক" ভাবা সাধারণ ভুল (Section 5)।
- রেস্টুরেন্টে ভিড় ধীরে বাড়ে। Computer-এ utilization ৭০% থেকে ৯০%-এ গেলে **অপেক্ষার সময় অনুপাতিক নয়, বহুগুণ বাড়ে** (queueing theory, L00-03-এর Little's Law-এর আত্মীয়) — তাই saturation আসার আগে utilization-এ সতর্কতা।

## 5. Real-world engineering scenario — "CPU ৮২%, তাই বড় server?"

**পরিস্থিতি:** Monitoring-এ CPU ৮২%, API ধীর। প্রস্তাব: দুই গুণ CPU-র instance। SRE আগে USE table চাইলেন।

**নমুনা data-য় (এই lesson-এর [`sample-vmstat.txt`](code/L01-15/sample-vmstat.txt), [`sample-iostat.txt`](code/L01-15/sample-iostat.txt)) আসল ফল:**

```text
resource     check                                 value  verdict
CPU          utilization                             82%  WARN
CPU          saturation (run queue/cpu)             0.45  ok
CPU          iowait                                  64%  CRIT
Memory       saturation (swap in+out)                0/s  ok
Tasks        blocked in I/O (b)                      5.0  CRIT
Disk sda     utilization                            100%  CRIT
Disk sda     saturation (queue)                    37.05  CRIT
Disk sda     latency (max r/w await)             63.8 ms  WARN
```

**ব্যাখ্যা:** "CPU ৮২%"-এর **৬৪% আসলে iowait** — CPU কাজ করছে না, disk-এর অপেক্ষায়। Run queue কম (CPU-র জন্য লাইন নেই)। Disk ১০০% ব্যস্ত, queue-তে ~৩৭টি request, প্রতিটি ৬০ ms-এর বেশি। **Bottleneck = disk।** বড় CPU কিনলে টাকা যেত, সমস্যা থাকত।

**পরের ধাপ:** কোন process disk পড়ছে? `pidstat -d 1` বা `iotop` → হয়তো একটি index-ছাড়া database query পুরো table পড়ছে (Module 20), বা backup job (L01-11) ব্যবসায়িক সময়ে চলছে।

## 6. Diagram — তদন্তের পথ

```text
 "ধীর" অভিযোগ
     │
     ▼
 ১. System-স্তর: USE (প্রথম ৬০ সেকেন্ড)
     uptime → vmstat 1 → mpstat -P ALL 1 → pidstat 1 → iostat -xz 1 → free -m → sar -n DEV 1
     │
     ├── কোনো resource saturated? ──yes──► কোন process? (pidstat, iotop, ss) ──► কারণ ঠিক / capacity
     │
     no (resource যথেষ্ট, তবু ধীর)
     ▼
 ২. Application-স্তর: profiling
     perf top / perf record (native) · py-spy / cProfile (Python) · flame graph
     │
     ▼
 ৩. Hotspot ঠিক → আবার মাপুন (একই workload, একাধিকবার — L00-06)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| USE method | প্রতিটি resource-এর Utilization, Saturation, Errors পরীক্ষা |
| Utilization | Resource কত শতাংশ সময় ব্যস্ত |
| Saturation | অপেক্ষায় জমে থাকা কাজ |
| iowait (`wa`) | CPU অলস কারণ task I/O-র অপেক্ষায় |
| steal (`st`) | VM-এ hypervisor CPU অন্য VM-কে দিয়েছে (cloud-এ গুরুত্বপূর্ণ) |
| `%util` (iostat) | Device কত শতাংশ সময় ব্যস্ত (SSD/NVMe-তে parallelism-এর কারণে ১০০% মানেই সীমা নয়) |
| `aqu-sz` | গড় request queue দৈর্ঘ্য |
| `r_await` / `w_await` | গড় read/write latency (ms), queue-র সময় সহ |
| Profiler | কোন code-এ কত সময় যায় মাপার tool |
| Sampling profiler | নির্দিষ্ট সময় পরপর stack দেখে — কম overhead |
| Flame graph | Stack sample-এর চিত্র: চওড়া = বেশি সময় |
| Hotspot | যে code সবচেয়ে বেশি সময় নেয় |
| `tottime` / `cumtime` (cProfile) | Function নিজে / sub-call সহ মোট সময় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 "প্রথম ৬০ সেকেন্ড" — প্রতিটি command কী দেখায়

| Command | দেখায় | কী খুঁজবেন |
|---|---|---|
| `uptime` | Load average | Trend (L01-09) |
| `dmesg -T \| tail` / `journalctl -k -n 20` | Kernel বার্তা | OOM, disk/network error (**E**rrors) |
| `vmstat 1` | r, b, swap, io, CPU ভাগ | `r` > CPU, `b` > 0, `si/so` > 0, `wa`, `st` |
| `mpstat -P ALL 1` | প্রতি core | একটি core ১০০% (single-thread bottleneck) |
| `pidstat 1` | প্রতি process CPU | কোন process |
| `pidstat -d 1` | প্রতি process disk I/O | কে disk পড়ছে/লিখছে |
| `iostat -xz 1` | প্রতি disk | `%util`, `aqu-sz`, `await` |
| `free -m` | Memory | available (L01-09) |
| `sar -n DEV 1` | Network throughput | Interface-এর সীমা |
| `sar -n TCP,ETCP 1` | TCP connection ও retransmit | Network সমস্যা (Module 02) |

`mpstat`, `pidstat`, `iostat`, `sar` আসে **sysstat** package থেকে। প্রথম লাইন (বা প্রথম report) **boot থেকে গড়** — বর্তমান অবস্থার জন্য পরের লাইনগুলো দেখুন; এই lesson-এর Python tool এজন্যই প্রথমটি বাদ দেয়।

### 8.2 `perf` — Linux-এর native profiler

```bash
sudo perf top                          # এই মুহূর্তে CPU কোন function-এ (system-wide)
sudo perf record -F 99 -g -p PID -- sleep 30   # একটি process, ৩০ সেকেন্ড, call graph সহ
sudo perf report                       # ফল
```

`-F 99` = প্রতি সেকেন্ডে ৯৯ বার sample (১০০ নয় — অন্য পর্যায়ক্রমিক কাজের সাথে lockstep এড়াতে)। Flame graph তৈরিতে Brendan Gregg-এর FlameGraph script বা আধুনিক tool ব্যবহৃত হয়।

Python-এর মতো interpreted language-এ `perf` শুধু interpreter-এর C function দেখায়, Python function নয় (Python ৩.১২+-এ perf support আছে, সক্রিয় করতে হয়)। সহজতর: **py-spy** (sampling, চলমান process-এ, code বদল ছাড়া) বা development-এ **cProfile**।

> VM ও cloud-এ hardware performance counter সীমিত থাকতে পারে — `perf` কিছু event দেখাতে না পারলে software event (`-e cpu-clock`) ব্যবহার করুন।

### 8.3 Optimization-এর নিয়ম

1. **মাপুন আগে** — "কোথায় ধীর" অনুমান প্রায়ই ভুল।
2. **বাস্তব workload** — ছোট input-এ startup খরচই প্রাধান্য পায় (Section 9.3-এ আসলে দেখা গেছে)।
3. **Algorithm আগে, micro-optimization পরে** — O(n²) → O(n) বড় লাভ; loop-এর ভেতরে ছোট কৌশল সামান্য।
4. **আবার মাপুন** — একই পদ্ধতি, একাধিকবার (L00-06)।

## 9. Practical demonstration

### 9.1 System-স্তর (Ubuntu VM)

```bash
sudo apt install -y sysstat            # mpstat, pidstat, iostat, sar
uptime
vmstat 1 5
mpstat -P ALL 1 3
pidstat 1 3
iostat -xz 1 3
```

> **Fedora-তে:** `sudo dnf install -y sysstat`।

**Disk চাপ তৈরি করে দেখুন (⚠️ VM-এ, ~১ GB লেখে, পরে মুছে ফেলে):**

```bash
dd if=/dev/zero of=/tmp/io-test bs=1M count=1024 oflag=direct status=progress &
iostat -xz 1 5
wait; rm -f /tmp/io-test
```

`oflag=direct` = page cache এড়িয়ে সরাসরি disk-এ (L01-09) — নাহলে cache-এ লিখে "দ্রুত" দেখাত।

### 9.2 USE table — Python

File: [`code/L01-15/use_check.py`](code/L01-15/use_check.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-15
vmstat 1 6 > /tmp/vmstat.txt
iostat -x 1 3 > /tmp/iostat.txt
python3 use_check.py --vmstat /tmp/vmstat.txt --iostat /tmp/iostat.txt --cpus "$(nproc)"
python3 use_check.py --vmstat sample-vmstat.txt --iostat sample-iostat.txt --cpus 4; echo "exit=$?"
```

নমুনার আসল output Section 5-এ। Errors-এর জন্য tool স্পষ্টভাবে "manual" বলে — `journalctl -k`, `ip -s link` (network error counter, Module 02) আলাদা দেখতে হয়; কোনো tool সব বলে দেয় না।

### 9.3 Application profiling — cProfile

File: [`code/L01-15/slow_app.py`](code/L01-15/slow_app.py) — duplicate ID খোঁজার দুটি version: O(n²) ও O(n)।

```bash
python3 -m cProfile -s tottime slow_app.py --n 20000 | head -12
```

**এই repository-তে (Windows, Python 3.14) চালিয়ে পাওয়া আসল output:**

```text
889 duplicate ids; report length 6613
         123251 function calls (122953 primitive calls) in 1.394 seconds

   Ordered by: internal time

   ncalls  tottime  percall  cumtime  percall filename:lineno(function)
        1    1.353    1.353    1.354    1.354 slow_app.py:21(find_duplicates_slow)
    20000    0.005    0.000    0.009    0.000 random.py:245(_randbelow_with_getrandbits)
    20000    0.005    0.000    0.014    0.000 random.py:294(randrange)
        3    0.003    0.001    0.003    0.001 {built-in method _imp.create_dynamic}
        1    0.003    0.003    0.017    0.017 slow_app.py:16(make_ids)
```

১.৩৯৪ সেকেন্ডের মধ্যে ১.৩৫৩ সেকেন্ড (≈৯৭%) একটি function-এ — **hotspot স্পষ্ট**।

**সময় মাপা (তিনবার, পুরো process):**

| Version | Run ১ | Run ২ | Run ৩ |
|---|---|---|---|
| `--n 20000` (slow) | 1403 ms | 1400 ms | 1395 ms |
| `--n 20000 --fast` | 79 ms | 70 ms | 71 ms |

Fast version ≈ ২০ গুণ দ্রুত, এবং তার ৭০ ms-এর বেশিরভাগই Python startup।

**একটি সৎ শিক্ষা (এই repository লেখার সময় ঘটেছে):** প্রথমে `--n 3000` দিয়ে profile করা হয়েছিল — slow function মাত্র ২৯ ms, যেখানে Python startup ও `argparse` import প্রায় ২৪ ms; পুরো process-এর সময় slow ৯৭ ms বনাম fast ৬৮ ms — পার্থক্য "সামান্য" মনে হচ্ছিল। ছোট input-এ সমস্যা লুকিয়ে ছিল। **বাস্তবসম্মত আকারের workload** দিয়ে মাপা জরুরি — production-এর data ছোট lab data-র মতো আচরণ করে না।

> L00-06-এর মতো: এই সংখ্যা Windows-এর। Ubuntu-তে মান আলাদা হবে, কিন্তু অনুপাত (hotspot-এর অংশ, slow/fast পার্থক্য) একই রকম হওয়া উচিত — নিজে মেপে যাচাই করুন।

**Production-এ চলমান Python process (code বদল ছাড়া):**

```bash
pipx install py-spy                    # অথবা venv-এ pip install py-spy
python3 slow_app.py --n 60000 &
sudo py-spy top --pid $!               # top-এর মতো, function অনুযায়ী
sudo py-spy record -o profile.svg --pid $!   # flame graph (SVG)
```

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_l01_15.py`](code/L01-15/test_l01_15.py)-এর ৫টি test: vmstat-এর boot গড় বাদ, iostat column নাম দিয়ে parse ও প্রথম block বাদ, নমুনার USE verdict (CPU utilization-এর প্রত্যাশিত মান প্রথমে আমি ভুল লিখেছিলাম — idle-এর গড় ১৭.৬ → ৮২.৪%, code সঠিক ছিল), CLI exit code, ও slow/fast version একই ফল দেয়।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| Header `r b` খুঁজে column নাম দিয়ে dict | Version-নিরপেক্ষ | vmstat-এর column (যেমন `gu`) version-ভেদে বদলায় |
| `rows[1:]` / `blocks[1:]` | Boot থেকে গড় বাদ | বর্তমান অবস্থা দেখতে |
| iostat-এ `aqu-sz` বা পুরোনো `avgqu-sz` | দুই নাম | sysstat version পার্থক্য |
| `max(r_await, w_await)` | খারাপটি | Latency-তে সবচেয়ে খারাপ অভিজ্ঞতা গুরুত্বপূর্ণ |
| Errors = "manual" | | সৎ: এই input-এ error তথ্য নেই |
| `x in ids[i+1:]` (slow) | প্রতিবার নতুন slice + linear search | ইচ্ছাকৃত O(n²) |
| `seen` set (fast) | O(1) membership | একই ফল, O(n) |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `dd ... oflag=direct` চলাকালীন `iostat` | `%util` উঁচু, `wa` বাড়ে |
| `use_check.py` নমুনায় | Disk CRIT, CPU saturation ok |
| `cProfile` n=20000 | `find_duplicates_slow` শীর্ষে |
| `python3 -m unittest -v` | `Ran 5 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| CPU উঁচু কিন্তু CPU বাড়িয়ে লাভ নেই | iowait বা steal | `vmstat` `wa`, `st` | Disk/VM host তদন্ত |
| একটি core ১০০%, বাকি অলস | Single-threaded code | `mpstat -P ALL` | Parallelism বা algorithm |
| `iostat`-এ NVMe ১০০% `%util` কিন্তু ঠিক চলছে | Parallel device-এ `%util` বিভ্রান্তিকর | `aqu-sz`, `await` | Latency ও queue দেখুন |
| `perf: command not found` / event নেই | Package বা VM সীমা | — | `linux-tools-$(uname -r)` (Ubuntu); `-e cpu-clock` |
| Profile-এ startup প্রাধান্য পায় | Input ছোট | মোট সময় বনাম hotspot | বাস্তব আকারের workload |
| `sar` data নেই | sysstat collection বন্ধ | `/etc/default/sysstat` | `ENABLED="true"` ও service চালু (Ubuntu) |

> **Fedora-তে:** `perf` package নাম `perf`; Ubuntu-তে `linux-tools-common` ও `linux-tools-$(uname -r)`।

## 13. Security, performance ও cost বিবেচনা

- **Security:** `perf` ও `py-spy`-এর জন্য উচ্চ অধিকার লাগে (process-এর memory পড়ে) — production-এ নিয়ন্ত্রিতভাবে; `kernel.perf_event_paranoid` sysctl এটি নিয়ন্ত্রণ করে।
- **Performance:** Profiler নিজে overhead যোগ করে (cProfile উল্লেখযোগ্য, sampling কম) — profile-এর সময় absolute মান স্বাভাবিকের চেয়ে বেশি হতে পারে; **অনুপাত** দেখুন।
- **Cost:** ভুল bottleneck-এ upgrade = অপচয় (Section 5); সঠিক diagnosis-এ প্রায়ই code বা configuration পরিবর্তনই যথেষ্ট — rightsizing (Module 29)।

## 14. Hands-on exercise

1. `stress-ng` (install করে) দিয়ে CPU, memory ও I/O আলাদাভাবে চাপ দিন; প্রতিবার USE table তৈরি করে কোন সারি লাল হয় দেখুন।
2. `slow_app.py`-কে n = ১০০০, ৫০০০, ১০০০০, ২০০০০ দিয়ে চালিয়ে slow version-এর সময় লিখুন — সময় কি n²-এর অনুপাতে বাড়ে? (n দ্বিগুণ → সময় ≈ চার গুণ?)
3. `py-spy record` দিয়ে flame graph তৈরি করে ব্রাউজারে খুলুন — কোন অংশ সবচেয়ে চওড়া?
4. `use_check.py`-তে `--sar-net` option যোগ করুন (`sar -n DEV`-এর output থেকে প্রতি interface `rxkB/s`, `txkB/s`)। Test লিখুন।
5. `mpstat -P ALL 1`-এ একটি single-threaded CPU loop (`python3 -c 'while True: pass'`) চালিয়ে দেখুন একটি core ১০০%।

## 15. Mini-project — "first 60 seconds" script

একটি Bash script লিখুন যা Section 8.1-এর command-গুলো নির্দিষ্ট সময় ধরে চালিয়ে output একটি timestamped folder-এ (`~/devops-notebook/incidents/perf-YYYYMMDD-HHMM/`) সংরক্ষণ করে, তারপর `use_check.py` দিয়ে সারাংশ দেয়। Incident-এর সময় প্রমাণ সংগ্রহের জন্য (L01-14-এর "restart-এর আগে প্রমাণ")। এটি Project 1-এর `perf` subcommand-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. USE method কী? CPU, memory ও disk-এর জন্য প্রতিটির একটি metric বলুন।
2. Server ধীর — প্রথম ৬০ সেকেন্ডে কোন command চালাবেন?
3. CPU ৮০% দেখাচ্ছে — এটি কি CPU bottleneck? কীভাবে নিশ্চিত হবেন?
4. `%util` ১০০% কিন্তু NVMe disk — সমস্যা কি?
5. Deterministic ও sampling profiler-এর পার্থক্য কী? Production-এ কোনটি?
6. Flame graph কীভাবে পড়বেন?
7. Optimization-এর আগে কেন মাপতে হয়? একটি উদাহরণ দিন।

## 17. Self-assessment প্রশ্ন

1. রেস্টুরেন্ট analogy কোথায় মেলে না?
2. Section 5-এ bottleneck কীভাবে চিহ্নিত হলো, কোন তিনটি সংখ্যা দিয়ে?
3. `--n 3000`-এ পার্থক্য সামান্য দেখাল কেন?
4. cProfile-এ `tottime` ও `cumtime`-এর পার্থক্য।
5. vmstat/iostat-এর প্রথম লাইন কেন বাদ?
6. `perf record -F 99` কেন ১০০ নয়?

## 18. সংক্ষিপ্ত সারাংশ

- অনুমান নয় — **USE method**: প্রতিটি resource-এর utilization, saturation, errors।
- **প্রথম ৬০ সেকেন্ড**: uptime, kernel log, vmstat, mpstat, pidstat, iostat, free, sar।
- "CPU উঁচু" প্রায়ই iowait/steal — saturation ও latency দেখুন।
- Resource যথেষ্ট তবু ধীর → **profiling**: perf (native), py-spy/cProfile (Python), flame graph।
- বাস্তব আকারের workload, algorithm আগে, আবার মাপুন।

## 19. Completion checklist

- [ ] sysstat install করে "প্রথম ৬০ সেকেন্ড"-এর সব command চালিয়েছি
- [ ] `dd oflag=direct` দিয়ে disk চাপ ও `iostat`-এ দেখেছি
- [ ] নিজের vmstat/iostat দিয়ে USE table
- [ ] `slow_app.py` cProfile ও (সম্ভব হলে) py-spy দিয়ে profile; n²-এর বৃদ্ধি মেপেছি
- [ ] `python3 -m unittest -v`-এ ৫টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Brendan Gregg — The USE Method: https://www.brendangregg.com/usemethod.html
- Brendan Gregg — Linux Performance (৬০ সেকেন্ড ও tool map): https://www.brendangregg.com/linuxperf.html
- Brendan Gregg — Flame Graphs: https://www.brendangregg.com/flamegraphs.html
- sysstat (iostat, mpstat, pidstat, sar): https://sysstat.github.io/
- `perf` wiki: https://perf.wiki.kernel.org/
- Python profilers (`cProfile`): https://docs.python.org/3/library/profile.html
- py-spy: https://github.com/benfred/py-spy

---

**পরের lesson:** L01-16 — Namespace, cgroup ও Linux capability
