# L05-11 — Log analysis tool তৈরি

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-07 — Logging](L05-07-logging-structured.md), [L04-08 — Bash বনাম Python](../04-bash-and-shell-automation/L04-08-bash-or-python.md), [L01-14 — Log ও debugging](../01-linux-systems/L01-14-logs-and-debugging.md) |
| **Label** | — |
| **Tested** | `logscan.py`: ৮টি test পাস (Python 3.14.5, Windows)। ২ লাখ লাইনের **কৃত্রিম** log-এ (২২.৭ MB, gzip-এ ১.৮৬ MB) আসলে চালানো হয়েছে: সময় ~২.৩ s, tracemalloc-এ peak memory ৭.৩ MiB। Generator-এ ইচ্ছাকৃতভাবে রাখা incident window (০৯:২০–০৯:২৪) tool সঠিকভাবে খুঁজে পেয়েছে। কোনো আসল production log ব্যবহার করা হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Incident-এর সময় log থেকে **দ্রুত উত্তর:** কখন শুরু, কোন endpoint, কোন client, কতটা খারাপ।
- **Streaming:** ২০ GB log-ও লাইন ধরে পড়া, memory-তে পুরোটা নয়; `.gz` সরাসরি।
- **Percentile** (p50/p90/p99) — গড় কেন মিথ্যা বলে; nearest-rank পদ্ধতি।
- **সময়রেখা:** প্রতি মিনিটের error rate ও "spike" নির্ণয়।
- Parse না হওয়া লাইন গোনা — নীরবে বাদ নয়।
- `Counter`, `defaultdict`, `heapq`-এর ব্যবহারিক রূপ।
- কখন নিজের tool, কখন `awk`/`jq`, কখন Loki/Elasticsearch।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

রাত ২টা: "checkout ধীর হয়ে গেছে"। Dashboard নেই, অথবা dashboard বলছে "গড় response time ১০০ ms — সব ঠিক"। আপনার কাছে আছে nginx-এর access log — কয়েক GB, কিছু gzip করা।

যে প্রশ্নগুলোর উত্তর চাই:

1. সমস্যা কখন শুরু ও শেষ হলো (মিনিট পর্যন্ত)?
2. কোন endpoint-এ? সব, নাকি একটি?
3. কতজন user-এর ওপর প্রভাব (5xx-এর হার, p99 latency)?
4. একটি client কি অস্বাভাবিক traffic পাঠাচ্ছে?

`grep | awk | sort | uniq -c` দিয়ে এর কিছু পাওয়া যায় (L04-08)। কিন্তু percentile, সময়-জানালা, gzip ও ভাঙা লাইন একসাথে সামলাতে একটি পরীক্ষিত tool দ্রুত ও নির্ভুল।

## 3. সহজ ভাষায় পরিচয়

```bash
python3 logscan.py /var/log/nginx/access.log /var/log/nginx/access.log.1.gz
python3 logscan.py access.log --since 09:15 --until 09:30 --json | jq '.spike_minutes'
zcat access.log.*.gz | python3 logscan.py -
```

| মাপ | কী বলে | কেন গুরুত্বপূর্ণ |
|---|---|---|
| 5xx rate | Server-এর দোষে ব্যর্থ request-এর অংশ | SLO-এর মূল সূচক (Module 18) |
| p50 latency | "সাধারণ" user-এর অভিজ্ঞতা | |
| p99 latency | সবচেয়ে ধীর ১%-এর অভিজ্ঞতা | ভারী user ও গুরুত্বপূর্ণ request প্রায়ই এখানে |
| প্রতি মিনিটের 5xx | সমস্যা কখন শুরু ও শেষ | Deploy বা পরিবর্তনের সাথে মেলানো |
| Top 5xx path | কোথায় | কোন team, কোন service |
| Top client | কে | Bot, retry storm, abuse |
| Unparsed lines | Parser কতটা দেখতে পায়নি | ১০% unparsed মানে ফল অবিশ্বাস্য |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের জরুরি বিভাগের রেজিস্টার

- প্রতিটি রোগী আসার সময়, অভিযোগ, অপেক্ষার সময় খাতায় লেখা — **access log**।
- **গড় অপেক্ষা** ২০ মিনিট — শুনতে ভালো। কিন্তু **p99** = ৪ ঘণ্টা: প্রতি ১০০ জনে একজন চার ঘণ্টা বসে ছিলেন। হয়তো তিনিই সবচেয়ে অসুস্থ।
- **প্রতি ঘণ্টার হিসাব** দেখায় সমস্যা রাত ২–৩টায়, যখন একজন ডাক্তার ছুটিতে ছিলেন — **সময়রেখা**।
- **খাতার পাতা একটা একটা করে পড়া** — পুরো বছরের খাতা একসাথে টেবিলে না ছড়িয়ে — **streaming**।
- **অস্পষ্ট লেখার পাতা** আলাদা গোনা — নীরবে বাদ দিলে পরিসংখ্যান মিথ্যা — **unparsed lines**।

### Analogy কোথায় মেলে না

- রেজিস্টারে প্রতিটি রোগী একবার। **Log-এ একই user-এর একটি "কাজ" অনেক request** — একটি page load = ৩০টি request। তাই "১% request ব্যর্থ" মানে "১% user প্রভাবিত" নয়; হয়তো ৩০% user-এর অন্তত একটি request ব্যর্থ হয়েছে।
- রেজিস্টারের সময় একটি ঘড়ির। **Log-এর সময় অনেক server-এর ঘড়ির** — কয়েক সেকেন্ডের পার্থক্যে "কোনটা আগে" ভুল হতে পারে (NTP — L01)। আর access log-এর সময় সাধারণত request **শেষ** হওয়ার, শুরুর নয়।
- রেজিস্টার নিজে ব্যাখ্যা করে না কেন অপেক্ষা হলো। **Access log শুধু লক্ষণ দেখায়** — 503 কেন হলো, তা জানতে upstream-এর application log ও metrics লাগে (Module 17-এর তিন স্তম্ভ)।

## 5. Real-world engineering scenario — "গড় ঠিক আছে, কিন্তু customer রাগী"

**পরিস্থিতি:** Dashboard-এ এক ঘণ্টার গড় latency স্বাভাবিক দেখাচ্ছিল। অথচ support-এ বহু অভিযোগ: "অর্ডার দিতে পারছি না"।

এই lesson-এর কৃত্রিম log ঠিক এই পরিস্থিতি অনুকরণ করে — ৬০ মিনিটের মধ্যে ৫ মিনিট `/api/orders`-এ upstream সমস্যা। `logscan.py` থেকে **আসল output:**

```text
requests    199995  (unparsed lines: 5)
status      {'2xx': 168521, '3xx': 15888, '4xx': 11808, '5xx': 3778}   5xx rate: 0.0189
latency     p50=0.05s p90=0.112s p99=2.333s max=4.999s
top 5xx     /api/orders (2097), / (590), /api/tasks (468), …
SPIKE       09:20  390/3333 requests 5xx
…
SPIKE       09:24  373/3333 requests 5xx
```

কী বোঝা গেল:

- **পুরো ঘণ্টার 5xx rate ১.৯%** — একা দেখলে "সহনীয়"।
- **p50 ০.০৫ s, কিন্তু p99 ২.৩৩ s** — ৫ মিনিটের incident পুরো ঘণ্টার tail টেনে তুলেছে।
- **সময়রেখা:** ঠিক ০৯:২০–০৯:২৪। ওই সময়ে কী deploy বা পরিবর্তন হয়েছিল?
- **Endpoint:** 5xx-এর অর্ধেকের বেশি `/api/orders`-এ।

শুধু incident window দেখলে (`--since 09:19 --until 09:27`) ছবিটা আরো তীক্ষ্ণ — আসল output: ২৬,৬৬৫ request, 5xx rate **৭.৭%**, p99 **৪.৬৮ s**।

**শিক্ষা:** গড় ও পুরো সময়ের হার সমস্যাকে "পাতলা" করে দেয়। Percentile, সময়রেখা ও ভাগ (endpoint অনুযায়ী) — এই তিনটি একসাথে দেখুন।

## 6. Diagram — streaming pipeline

```text
 access.log  access.log.1.gz  (stdin "-")
      │            │  open_any(): প্রথম ২ byte = 1f 8b → gzip (নাম নয়, বিষয়বস্তু)
      └─────┬──────┘
            ▼  lines_from() — generator: একবারে একটি লাইন (memory ≈ ধ্রুব)
        parse(line) ── regex ── ব্যর্থ → unparsed += 1
            │ Request(ip, ts, method, path(query বাদ), status, size, rt)
            ▼  --since/--until ছাঁকনি
        analyze():  Counter(status class, path, 5xx path, ip)
                    per_minute["09:20"] = [total, 5xx]
                    latencies.append(rt)          ← একমাত্র অংশ যা n-এর সাথে বাড়ে
            ▼
        report(): error rate · p50/p90/p99 (nearest-rank, sorted) · top-N · spikes
            ▼
        text বা --json ;  exit 1 যদি spike থাকে
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Access log | প্রতিটি HTTP request-এর এক লাইন |
| Combined log format | nginx/Apache-এর প্রচলিত format (referer, user agent সহ) |
| `$request_time` | nginx-এ request-এর মোট সময় (সেকেন্ড, ms নির্ভুলতা) |
| Streaming | Data একটু একটু করে প্রক্রিয়া; পুরোটা memory-তে নয় |
| Percentile (pN) | N% মান যার সমান বা কম |
| Nearest-rank | Percentile হিসেবে একটি আসল পরিমাপকেই নেওয়া |
| Tail latency | p99/p99.9 — সবচেয়ে ধীর অংশ |
| Error rate | ব্যর্থ request / মোট |
| Spike | স্বাভাবিকের চেয়ে হঠাৎ বেশি |
| Cardinality | একটি field-এর ভিন্ন মানের সংখ্যা (path, IP) |
| Magic bytes | File-এর শুরুর byte দিয়ে format চেনা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Streaming ও memory

`lines_from` একটি generator — file object-এর ওপর `for` loop OS থেকে buffer করে পড়ে, এক লাইন করে দেয়। Counter-গুলোর আকার বাড়ে **ভিন্ন মানের** সংখ্যায় (path, IP), লাইনের সংখ্যায় নয়।

ব্যতিক্রম `latencies` list — প্রতিটি request-এ একটি float। ২ লাখ লাইনে peak memory ছিল ৭.৩ MiB (মাপা)। ১০০ কোটি লাইনে এই list-ই সমস্যা হবে। তখন:

- Histogram bucket (Prometheus-এর মতো — Module 17)।
- বা t-digest / HDR histogram, যা আনুমানিক percentile ধ্রুব memory-তে দেয়।

### 8.2 Percentile — nearest-rank বনাম interpolation

`statistics.quantiles` ও numpy default-এ দুটি পরিমাপের মাঝে **interpolate** করে — এমন মান দিতে পারে যা কোনো request-এ আসলে ঘটেনি। Nearest-rank (`ceil(p/100 × n)`-তম মান) সবসময় একটি আসল পরিমাপ দেয়।

ছোট sample-এ পার্থক্য চোখে পড়ে; বড় sample-এ প্রায় একই। কোন পদ্ধতি ব্যবহার করছেন, তা report-এ বলা ভালো।

### 8.3 Query string বাদ দেওয়া

`/api/tasks?page=2` ও `/api/tasks?page=3` আলাদা গুনলে top-N তালিকা লক্ষ লক্ষ অনন্য URL-এ ভরে যায় — **cardinality বিস্ফোরণ** — এবং memory-ও বাড়ে। Path-এর ভেতরের ID-ও একই সমস্যা (`/users/12345`)। Exercise ৩-এ path normalization।

### 8.4 gzip চেনা

Rotated log-এর নাম `access.log.2.gz`, কিন্তু কখনো compression ছাড়াই `.1`। নামের বদলে প্রথম দুই byte (`1f 8b`) দেখা নির্ভরযোগ্য। `gzip.open(..., "rt")` decompress করতে করতে লাইন দেয় — পুরো file আগে খোলে না। মাপা সময়: plain ও gzip প্রায় সমান (~২.৩ s)।

### 8.5 Regex-এর সতর্কতা

Path-এর ভেতরে escaped quote (`\"`) থাকতে পারে, তাই `(?:[^"\\]|\\.)*?` ব্যবহার করা হয়েছে। L04-08-এ একটি সরল regex space-ওয়ালা path কেটে দিয়েছিল; এখানে `HTTP/x.y"`-এ নোঙর করা।

Referer/user agent ও `$request_time` ঐচ্ছিক রাখা হয়েছে, যাতে common format-ও চলে।

> **Fedora-তে:** nginx-এর log `/var/log/nginx/access.log` (দুই distro-তেই)। Fedora-তে SELinux-এর কারণে অন্য directory-তে log লিখতে context লাগে (L01-17)। Logrotate-এর নিয়ম `/etc/logrotate.d/nginx`। Ubuntu-তে nginx-এর default log format-এ `$request_time` থাকে না — `log_format`-এ যোগ করতে হয় (Module 06)।

## 9. Practical demonstration

Files: [`code/L05-11/logscan.py`](code/L05-11/logscan.py), [`gen_access_log.py`](code/L05-11/gen_access_log.py) (কৃত্রিম log, seed স্থির), [`test_l05_11.py`](code/L05-11/test_l05_11.py)।

### 9.1 Log তৈরি ও বিশ্লেষণ

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-11
python3 gen_access_log.py --lines 200000 > /tmp/access.log
python3 gen_access_log.py --lines 200000 --gzip > /tmp/access.log.gz
wc -c /tmp/access.log /tmp/access.log.gz
time python3 logscan.py /tmp/access.log; echo "exit=$?"
```

**আসল output:**

```text
22751132 access.log
 1856930 access.log.gz

window      2026-10-27T09:00:00+00:00 → 2026-10-27T09:59:59+00:00
requests    199995  (unparsed lines: 5)
status      {'2xx': 168521, '3xx': 15888, '4xx': 11808, '5xx': 3778}   5xx rate: 0.0189
latency     p50=0.05s p90=0.112s p99=2.333s max=4.999s
top paths   / (59830), /api/tasks (49988), /static/app.js (30327), /api/orders (29924), /login (19925)
top 5xx     /api/orders (2097), / (590), /api/tasks (468), /static/app.js (306), /login (212)
top clients 203.0.113.66 (19316), 192.0.2.7 (3250), 192.0.2.22 (3249), 192.0.2.30 (3244), 198.51.100.12 (3220)
SPIKE       09:20  390/3333 requests 5xx
SPIKE       09:21  393/3334 requests 5xx
SPIKE       09:22  417/3333 requests 5xx
SPIKE       09:23  384/3333 requests 5xx
SPIKE       09:24  373/3333 requests 5xx

real	0m2.267s
exit=1
```

- **Unparsed ৫:** generator-এ ইচ্ছাকৃত ৫টি ভাঙা লাইন — ঠিক তত।
- **Top client `203.0.113.66`:** মোট traffic-এর ~১০% একটি IP থেকে — বাকিদের প্রায় ৬ গুণ (generator-এ ৮% "ব্যস্ত client")।
- **Exit ১** — spike পাওয়া গেছে। Cron বা CI-তে alert হিসেবে ব্যবহার করা যায়।
- gzip file-এ একই ফল, সময় ~২.৩ s।

### 9.2 Incident window

```bash
python3 logscan.py /tmp/access.log --since 09:19 --until 09:27 --json
```

**আসল ফল (মূল field):** `requests 26665`, `error_rate_5xx 0.0773`, `p50 0.054`, `p90 0.246`, `p99 4.684`, `top_5xx_paths[0] = ["/api/orders", 1839]`, spike মিনিট ৫টি।

### 9.3 Memory — আসল পরিমাপ

```python
tracemalloc.start(); s = logscan.analyze(logscan.lines_from(["access.log"]))
```

```text
analyze: 21.66s, peak traced memory 7.3 MiB, latencies list 199995 floats
```

২২.৭ MB file, কিন্তু peak memory ৭.৩ MiB — যার বেশিরভাগ latency list। (`tracemalloc` প্রতিটি allocation ট্র্যাক করে বলে সময় ~১০ গুণ বেড়েছে; সাধারণ চালানোয় ২.৩ s।)

### 9.4 Windows-এ পাওয়া একটি measurement ফাঁদ

প্রথমে `ls -l … | awk '{print $5}'` দিয়ে file-এর আকার দেখতে গিয়ে **দুটো file-এরই "১৯৭১২১"** এল। কারণ:

- এই machine-এর user নাম "This pc"-এ space আছে, তাই `ls -l`-এ owner দুটি column নিল।
- `$5` হয়ে গেল Windows-এর numeric group id, file-এর আকার নয়।

`wc -c` দিয়ে আসল মান পাওয়া গেল। **শিক্ষা:** `ls` parse করবেন না (L04-02) — `stat -c %s`, `wc -c`, বা Python-এর `Path.stat().st_size`।

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- পূর্ণ লাইন; ভিন্নতা (`$request_time` নেই, size `-`, common format, escaped quote)।
- ৩টি ভাঙা লাইন (অসম্ভব তারিখ, ৪ অঙ্কের status)।
- Nearest-rank percentile।
- Count ও spike (`--min-requests`-এর প্রভাব); সময়-জানালা।
- নাম ছাড়া gzip চেনা।
- **Generator-এর log-এ incident ঠিক ০৯:২০–০৯:২৪-এ**, top 5xx `/api/orders`, top client।
- ভুল file (exit ২) ও ভুল সময়।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `LINE` regex, ঐচ্ছিক অংশসহ | combined/common, `$request_time` | বিভিন্ন server-এর format |
| `(?:[^"\\]\|\\.)*?` | Escaped quote-সহ path | L04-08-এর শিক্ষা |
| `strptime` ব্যর্থ → None | অসম্ভব তারিখ | Crash নয়, unparsed |
| `split("?")[0]` | Query বাদ | Cardinality নিয়ন্ত্রণ |
| `open_any` + magic bytes | gzip চেনা | নাম অবিশ্বাস্য |
| `errors="replace"` | ভাঙা UTF-8 | একটি খারাপ byte-এ পুরো বিশ্লেষণ থামে না |
| `Counter.most_common(n)` | Top-N | ভেতরে `heapq` |
| `per_minute` `[total, 5xx]` | সময়রেখা | Spike ও শুরু/শেষ |
| `--min-requests` | কম traffic-এর মিনিট বাদ | ২-এর মধ্যে ১টি ব্যর্থ = ৫০% — শোরগোল |
| Exit ১ spike-এ | Alert-যোগ্য | Cron/CI-তে ব্যবহার |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| ২ লাখ লাইন | ~১৯৯,৯৯৫ request, unparsed ৫, spike ০৯:২০–০৯:২৪ |
| `.gz` file | একই ফল |
| `--since 09:19 --until 09:27` | 5xx rate ~৭.৭% |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| সব লাইন unparsed | Custom `log_format` | Regex মেলান; `--json` log format বিবেচনা |
| `MemoryError` | `readlines()` বা পুরো file list-এ | Generator; histogram |
| Top path-এ হাজার অনন্য URL | Query/ID | Normalization |
| Percentile ভিন্ন tool-এ ভিন্ন | Interpolation পদ্ধতি | পদ্ধতি উল্লেখ করুন |
| `UnicodeDecodeError` | Log-এ ভাঙা byte | `errors="replace"` |
| সময় ভুল ঘণ্টায় | Time zone (`+0600` বনাম UTC) | `%z` parse; তুলনা UTC-তে |
| Spike মিথ্যা alarm রাতে | কম traffic | `--min-requests` |
| `.1` file binary garbage | নামে `.gz` নেই কিন্তু compressed | Magic bytes |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Access log-এ IP, user agent, কখনো query string-এ token বা email থাকে — personal data। Report শেয়ার করার আগে ভাবুন। Query বাদ দেওয়া নিরাপত্তায়ও সাহায্য করে।
  - Log-এর বিষয়বস্তু untrusted input (যে কেউ path-এ যা খুশি পাঠাতে পারে)। Report HTML-এ দেখালে escape করুন।
  - Log file root-এর; tool-কে `adm` group দিয়ে পড়ার অনুমতি দিন, `sudo` নয় (L01-04)।
- **Performance:**
  - ~৮৭,০০০ লাইন/সেকেন্ড (২ লাখ / ২.৩ s) এক core-এ।
  - বড় হলে: file-ভিত্তিক সমান্তরাল (`multiprocessing`), regex-এর আগে দ্রুত prefilter (`if " 5" in line`), বা PyPy।
  - শত GB প্রতিদিন হলে centralized logging (Module 17)।
- **Cost:**
  - Log storage ও ingestion বড় খরচ।
  - Access log-এর পূর্ণ লাইন রাখার বদলে metrics (counter, histogram) বের করে রাখা অনেক সস্তা — এই tool সেই রূপান্তরেরই ছোট রূপ।
  - Retention নীতি (Module 29)।

## 14. Hands-on exercise

1. Ubuntu-তে nginx install করে `log_format`-এ `$request_time` যোগ করুন। `ab`/`hey` দিয়ে local traffic পাঠিয়ে (শুধু localhost) `logscan.py` চালান।
2. `--by status` বিকল্প যোগ করুন: প্রতিটি status code-এর জন্য আলাদা p99।
3. Path normalization: `/users/12345` → `/users/{id}` (সংখ্যা ও UUID)। Top path কীভাবে বদলায়?
4. `latencies` list-এর বদলে Prometheus-ধাঁচের histogram bucket (০.০০৫, ০.০১, … ১০ s) ব্যবহার করুন। Percentile-এর নির্ভুলতা কতটা কমে? Memory?
5. `multiprocessing.Pool` দিয়ে একাধিক file সমান্তরালে বিশ্লেষণ করে `Stats` জোড়া দিন। ৪টি file-এ সময় মাপুন।

## 15. Mini-project — Incident timeline report

`incident_report.py access.log* --since … --until …`:

- Markdown report: সারাংশ, প্রতি মিনিটের 5xx ও p99-এর ASCII চার্ট, শীর্ষ endpoint ও client, এবং "সমস্যা শুরু" ও "স্বাভাবিক" মিনিট।
- সাথে L05-07-এর JSON application log থেকে একই সময়ের error লাইন (request_id দিয়ে মেলানো)।

Module 18-এর postmortem-এর "timeline" অংশ এখান থেকে তৈরি হবে।

## 16. Interview প্রশ্ন

1. গড় latency কেন বিভ্রান্তিকর? p99 কী বলে?
2. ২০ GB log file Python দিয়ে কীভাবে বিশ্লেষণ করবেন?
3. Percentile হিসাবের পদ্ধতিগুলোর পার্থক্য কী?
4. Log থেকে incident-এর শুরু ও শেষ কীভাবে নির্ণয় করবেন?
5. Cardinality কী, এবং log/metrics-এ কেন সমস্যা?
6. কখন নিজের script, কখন centralized logging?

## 17. Self-assessment প্রশ্ন

1. রেজিস্টার analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ পুরো ঘণ্টা ও incident window-এর সংখ্যাগুলো কী বলে?
3. ২২.৭ MB file-এ memory মাত্র ৭.৩ MiB কেন? কোন অংশ বাড়ে?
4. Nearest-rank কেন বেছে নেওয়া হলো?
5. `ls -l | awk '{print $5}'` এখানে কেন ভুল মান দিল?

## 18. সংক্ষিপ্ত সারাংশ

- Generator দিয়ে streaming; gzip magic bytes দিয়ে চেনা।
- গড় নয়: p50/p90/p99, প্রতি মিনিটের error rate, endpoint অনুযায়ী ভাগ।
- Unparsed লাইন গুনুন ও দেখান।
- Query/ID বাদ দিয়ে cardinality নিয়ন্ত্রণ।
- বড় scale-এ histogram/t-digest ও centralized logging।

## 19. Completion checklist

- [ ] কৃত্রিম log-এ incident window খুঁজে পেয়েছি
- [ ] Incident window ও পুরো ঘণ্টার সংখ্যার পার্থক্য ব্যাখ্যা করতে পারি
- [ ] (Ubuntu) নিজের nginx log-এ চালিয়েছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nginx — `ngx_http_log_module` (log_format, `$request_time`): https://nginx.org/en/docs/http/ngx_http_log_module.html
- Python — `gzip`: https://docs.python.org/3/library/gzip.html
- Python — `collections.Counter`: https://docs.python.org/3/library/collections.html#collections.Counter
- Python — `tracemalloc`: https://docs.python.org/3/library/tracemalloc.html
- Google SRE Book — Monitoring Distributed Systems (latency, percentiles): https://sre.google/sre-book/monitoring-distributed-systems/
- Prometheus — Histograms and summaries: https://prometheus.io/docs/practices/histograms/

---

**পরের lesson:** L05-12 — Health check ও backup verification tool
