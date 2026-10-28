# L00-06 — Experiment, log, measurement ও incident analysis দিয়ে শেখা

| | |
|---|---|
| **Module** | 00 — Engineering Orientation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L00-05 — Architecture diagram ও documentation](L00-05-diagrams-and-docs.md) |
| **Label** | — |
| **Tested** | Python code: Python 3.14-এ ৭টি test পাস (একটি আসল local HTTP server integration test সহ)। দুটি tool চালানো হয়েছে **Windows 11**-এ — এই lesson-এর latency সংখ্যা সেখানকার। Ubuntu-তে চালানো হয়নি; সেখানে সংখ্যা ভিন্ন হবে (Section 9.4 দেখুন)। |

---

## 1. এই lesson-এ যা শিখবেন

- কেন DevOps/SRE কাজ শেখার সবচেয়ে কার্যকর পদ্ধতি **experiment** — পড়া বা মুখস্থ নয়।
- **বৈজ্ঞানিক পদ্ধতি** engineering-এ: observation → hypothesis → prediction → experiment → measurement → সিদ্ধান্ত।
- Measurement-এর ফাঁদ: noise, warm-up, timer resolution, ছোট sample, average-এর বিভ্রান্তি।
- **Log পড়া:** structured log, timeline তৈরি, signal বনাম noise।
- **Incident analysis-এর ভিত্তি:** কী ঘটেছে, কখন, কোন পরিবর্তনের পরে।
- **Engineering notebook** — নিজের experiment লিখে রাখার অভ্যাস।
- দুটি Python tool: (১) local HTTP server-এ নিয়ন্ত্রিত latency experiment, (২) log থেকে incident timeline।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

নতুন engineer-দের সবচেয়ে সাধারণ সমস্যা: **অনুমান দিয়ে কাজ করা।**

- "Server slow — RAM বাড়াই।" (আসলে database query ধীর ছিল।)
- "Restart করলাম, ঠিক হয়ে গেছে।" (কারণ জানা গেল না; পরের সপ্তাহে আবার হলো।)
- "এই configuration দ্রুত করবে — blog-এ পড়েছি।" (মাপা হয়নি; আসলে ধীর করেছে।)
- Tutorial-এর command copy করে চালানো — কাজ করলে কেন করল, না করলে কেন না, বোঝা যায় না।

এর সমাধান: প্রতিটি দাবিকে **যাচাইযোগ্য hypothesis** হিসেবে দেখা, এবং data দিয়ে সিদ্ধান্ত নেওয়া। এই repository-র প্রতিটি lab — বিশেষ করে Level C failure lab — এই পদ্ধতির উপর দাঁড়িয়ে। এই lesson সেই পদ্ধতির ভিত্তি।

## 3. সহজ ভাষায় পরিচয়

### Engineering-এ বৈজ্ঞানিক পদ্ধতি

1. **Observation (পর্যবেক্ষণ):** কী দেখছি? "API-র response time সকাল ১০টার পর বেড়েছে।"
2. **Hypothesis (অনুমান):** সম্ভাব্য কারণ, যা ভুল প্রমাণ করা যায়। "১০টার deploy-এর নতুন query ধীর।"
3. **Prediction (পূর্বাভাস):** Hypothesis সত্য হলে কী দেখব? "আগের version-এ rollback করলে latency আগের মতো হবে; database-এর slow query log-এ নতুন query দেখা যাবে।"
4. **Experiment:** নিয়ন্ত্রিতভাবে **একটিমাত্র জিনিস** বদলানো।
5. **Measurement:** আগে ও পরে একইভাবে মাপা।
6. **সিদ্ধান্ত:** Data prediction-এর সাথে মিলল? না মিললে hypothesis বাদ, নতুন hypothesis।

**গুরুত্বপূর্ণ:** একটি ভালো hypothesis **ভুল প্রমাণযোগ্য (falsifiable)**। "কোনো একটা কিছু network-এ সমস্যা করছে" — এটি পরীক্ষা করা যায় না। "DNS lookup-এ ২ সেকেন্ড লাগছে" — এটি `dig` দিয়ে সরাসরি মাপা যায়।

### Log কী?

Program চলার সময় নিজের সম্পর্কে যে লিখিত রেকর্ড রেখে যায়: কখন, কী ঘটল, কতটা গুরুতর। Log হলো system-এর **ডায়েরি** — incident-এর পরে সবচেয়ে বড় প্রমাণের উৎস।

### Measurement কেন গুরুত্বপূর্ণ?

"দ্রুত" বা "ধীর" কোনো সংখ্যা নয়। "p95 latency ৩২০ms থেকে ৯০ms-এ নেমেছে, ২০০ request-এর sample-এ, তিনবার পুনরাবৃত্তি করে" — এটি engineering তথ্য।

### এটি না থাকলে কী হতো?

ভুল সমাধানে সময় ও টাকা নষ্ট, একই incident বারবার, এবং আত্মবিশ্বাস ছাড়া সিদ্ধান্ত।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ডাক্তারের রোগনির্ণয়

রোগী বলছেন "জ্বর"। ভালো ডাক্তার:

1. লক্ষণ শোনেন ও মাপেন (তাপমাত্রা, রক্তচাপ) — **observation ও measurement**।
2. সম্ভাব্য কারণের তালিকা করেন (ভাইরাস, ব্যাকটেরিয়া, ডেঙ্গু) — **hypothesis**।
3. পরীক্ষা দেন যা কারণগুলো আলাদা করতে পারে (রক্ত পরীক্ষা) — **experiment**।
4. ফল দেখে সিদ্ধান্ত — **data-ভিত্তিক সিদ্ধান্ত**।
5. রোগীর ইতিহাস দেখেন: "জ্বর কবে শুরু? তার আগে কী হয়েছিল?" — **timeline ও log**।

খারাপ ডাক্তার সব রোগীকে একই ওষুধ দেন — যেমন খারাপ engineer সব সমস্যায় server restart করেন।

### Analogy কোথায় মেলে না

- মানুষের শরীরে experiment সীমিত ও নৈতিকভাবে সংবেদনশীল। Software-এ আমরা **নিরাপদ disposable environment-এ ইচ্ছাকৃতভাবে system ভাঙতে পারি** (Level C lab, chaos engineering) — এটি engineering-এর বিশাল সুবিধা।
- রোগী একজন। Production-এ একই সাথে লাখো request — তাই একটি request নয়, **বণ্টন (distribution)** মাপতে হয়: p50, p95, p99।
- ডাক্তারের যন্ত্র সাধারণত নির্ভুল। Software measurement-এ **মাপার যন্ত্র নিজেই ফলাফল প্রভাবিত করতে পারে** (timer resolution, monitoring overhead) — এই lesson-এর practical-এ নিজেই দেখবেন।

## 5. Real-world engineering scenario — একটি deploy-এর পরে error spike

**পরিস্থিতি:** TaskFlow API-তে ১৪:০৩-এ version 1.4.0 deploy হলো। ১৪:০৪ থেকে user-রা error পাচ্ছেন। ১৪:০৭-এ rollback হলো। পরদিন আপনাকে incident analysis করতে বলা হলো। আপনার কাছে শুধু application log।

**জড়িত component:** API, database connection pool, একটি upstream service।

**Engineer-এর পদ্ধতি:**

1. **Timeline তৈরি** — প্রতি মিনিটে error সংখ্যা ও হার। কখন শুরু, কখন শেষ?
2. **পরিবর্তনের সাথে মেলানো** — শুরুর ঠিক আগে কী ঘটেছিল? (Log-এ "deploy finished" ১৪:০৩:৩০।)
3. **Error-এর ধরন** — কোন message সবচেয়ে বেশি? ("db connection pool exhausted" ১২ বার, "upstream timeout" ৫ বার।)
4. **Hypothesis:** "1.4.0-এ প্রতিটি request বেশি database connection ধরে রাখে, pool শেষ হয়ে যায়; ধীর query-র কারণে upstream timeout-ও হচ্ছে।"
5. **Prediction ও যাচাই:** staging-এ 1.4.0 চালিয়ে load দিলে pool exhaustion হওয়া উচিত; 1.3.2-এ নয়।
6. **সিদ্ধান্ত ও action item** — postmortem-এ (Module 18)।

**কী ভুল হতে পারত:** Timeline না দেখে শুধু "database সমস্যা" ধরে database server বড় করা — খরচ বাড়ত, কারণ (code পরিবর্তন) থেকেই যেত।

Section 9.2-এ ঠিক এই log-এর উপর tool চালাবেন।

## 6. Diagram

### Experiment loop

```text
   ┌──────────────┐
   │ Observation  │  "latency বেড়েছে"
   └──────┬───────┘
          ▼
   ┌──────────────┐
   │ Hypothesis   │  "X কারণে" — ভুল প্রমাণযোগ্য
   └──────┬───────┘
          ▼
   ┌──────────────┐
   │ Prediction   │  "X সত্য হলে Y দেখব"
   └──────┬───────┘
          ▼
   ┌──────────────┐     একটি variable বদলাও
   │ Experiment   │     বাকি সব স্থির রাখো
   └──────┬───────┘
          ▼
   ┌──────────────┐     একাধিকবার, একই পদ্ধতিতে
   │ Measurement  │     বণ্টন (p50/p95/p99), শুধু গড় নয়
   └──────┬───────┘
          ▼
   ┌──────────────┐  মিলেছে → সিদ্ধান্ত + notebook-এ লেখা
   │ Conclusion   │  মেলেনি → hypothesis বাদ ──┐
   └──────────────┘                           │
          ▲                                   │
          └───────────────────────────────────┘
```

### এই lesson-এর latency experiment-এর গঠন

```text
  latency_experiment.py (একটি process)
  ┌──────────────────────────────────────────────────────┐
  │  main thread: client                                  │
  │    perf_counter() ── GET /work?ms=5 ──┐               │
  │    perf_counter() ◄── 200 ok ─────────┤               │
  │                                       ▼               │
  │  server thread: ThreadingHTTPServer 127.0.0.1:<port>  │
  │    sleep(ms) → response (বা /flaky-তে কখনো 500)       │
  └──────────────────────────────────────────────────────┘
        শুধু loopback interface — বাইরের network-এ কিছু যায় না
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Hypothesis | যাচাইযোগ্য অনুমান — কী কারণে কী ঘটছে |
| Falsifiable | পরীক্ষা দিয়ে ভুল প্রমাণ করা সম্ভব |
| Control / baseline | তুলনার জন্য অপরিবর্তিত অবস্থা |
| Variable | Experiment-এ যা ইচ্ছাকৃতভাবে বদলানো হয় |
| Noise | মাপের এলোমেলো ওঠানামা যা আসল পরিবর্তনের সাথে সম্পর্কিত নয় |
| Warm-up | মাপা শুরুর আগে কয়েকবার চালানো, যাতে প্রথম দিকের অস্বাভাবিক ধীরতা বাদ যায় |
| Sample size | কতবার মাপা হয়েছে |
| Percentile (p50/p95/p99) | সাজানো মানের মধ্যে যে মানের নিচে ৫০/৯৫/৯৯% পড়ে |
| Standard deviation (stdev) | মানগুলো গড় থেকে কতটা ছড়ানো |
| Tail latency | p99-এর মত উপরের দিকের latency — সবচেয়ে ধীর অভিজ্ঞতা |
| Structured log | নির্দিষ্ট key=value বা JSON format-এর log, যা program সহজে parse করতে পারে |
| Log level | গুরুত্বের মাত্রা: DEBUG, INFO, WARN, ERROR |
| Timeline | ঘটনাগুলো সময়ের ক্রমে সাজানো — incident analysis-এর মেরুদণ্ড |
| Correlation vs causation | একসাথে ঘটা মানেই একটি অন্যটির কারণ নয় |
| Loopback (127.0.0.1) | শুধু নিজের machine-এর ভেতরের network interface |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 ভালো measurement-এর নিয়ম

1. **একবারে একটি variable বদলান।** দুটি জিনিস একসাথে বদলালে কোনটির প্রভাব, জানবেন না।
2. **একাধিকবার মাপুন** — একবারের মাপ noise হতে পারে। পুরো experiment কয়েকবার পুনরাবৃত্তি করুন।
3. **Warm-up বাদ দিন** — প্রথম request-এ connection তৈরি, cache খালি, code load — এগুলো স্বাভাবিক অবস্থা নয়।
4. **বণ্টন দেখুন, শুধু গড় নয়** — p50 সাধারণ অভিজ্ঞতা; p95/p99 সবচেয়ে খারাপ অভিজ্ঞতা, যা user বেশি মনে রাখে।
5. **পরিবেশ লিখে রাখুন** — OS, CPU, অন্য কী চলছিল, version। অন্য machine-এ ফল আলাদা হতে পারে।
6. **প্রত্যাশা আগে লিখুন** — data দেখার পরে "ব্যাখ্যা" বানানো সহজ; আগে prediction লিখলে নিজেকে ঠকানো কঠিন।

### 8.2 কেন p99 গুরুত্বপূর্ণ — একটি হিসাব

একটি web page লোড করতে ধরুন ২০টি আলাদা backend request লাগে। প্রতিটির p99 = ১ সেকেন্ড, মানে প্রতিটি request-এর ১% সম্ভাবনা ধীর হওয়ার।

Page-এর **অন্তত একটি** request ধীর হওয়ার সম্ভাবনা:

```text
1 − (0.99)²⁰ = 1 − 0.818 = 0.182 ≈ 18%
```

- (0.99)²⁰ = সব ২০টি request দ্রুত হওয়ার সম্ভাবনা (প্রতিটি স্বাধীন ধরে)।
- 1 থেকে বাদ দিলে = অন্তত একটি ধীর হওয়ার সম্ভাবনা।

অর্থাৎ "মাত্র ১%" tail latency প্রায় **প্রতি ৫ জনে ১ জন** user-এর page ধীর করে। এজন্য SRE-রা p99 গুরুত্ব দিয়ে দেখেন (Module 17, 18)।

### 8.3 Log-এর গঠন ও কেন structured log

Unstructured log:

```text
Oct 20 14:04:00 Error!! DB pool empty for user 42 :(
```

Structured log (এই lesson-এর format):

```text
2026-10-20T14:04:00Z level=ERROR msg="db connection pool exhausted" request_id=0031
```

Structured log-এর সুবিধা:

- **Timestamp** ISO 8601 ও UTC (`Z`) — বিভিন্ন server-এর log একই সময় অক্ষে মেলানো যায়।
- **Level** নির্দিষ্ট মানে — filter করা সহজ।
- **msg** স্থির text — একই ধরনের error গণনা করা যায় (variable অংশ আলাদা field-এ রাখা উচিত)।
- **request_id** — একটি request-এর সব log line একসাথে খোঁজা যায় (Module 17-এ trace)।

### 8.4 Correlation বনাম causation

Incident analysis-এ সবচেয়ে বড় ফাঁদ: "deploy-এর পরে error বেড়েছে, তাই deploy-ই কারণ।" প্রায়ই সত্য — কিন্তু সবসময় নয়। হয়তো ঠিক একই সময়ে traffic দ্বিগুণ হয়েছিল, বা database-এর backup চলছিল। তাই:

- একাধিক উৎস মেলান (deploy log, traffic metric, infrastructure event)।
- Hypothesis দিয়ে prediction করুন এবং পরীক্ষা করুন (rollback-এ কি ঠিক হলো? staging-এ কি পুনরুৎপাদন হয়?)।

### 8.5 Engineering notebook

প্রতিটি experiment-এর জন্য এই কাঠামো ব্যবহার করুন (আপনার `~/devops-notebook/`-এ):

```markdown
## Experiment: <শিরোনাম> — <তারিখ>

- Environment: <OS, version, machine, অন্য কী চলছিল>
- Observation: <কী দেখেছি>
- Hypothesis: <ভুল প্রমাণযোগ্য অনুমান>
- Prediction: <hypothesis সত্য হলে কী দেখব — data দেখার আগে লেখা>
- Method: <কী বদলালাম, কী স্থির রাখলাম, কতবার মাপলাম>
- Commands: <হুবহু command>
- Results: <আসল output, কপি করা — বানানো নয়>
- Conclusion: <prediction মিলল? কী শিখলাম?>
- Next question: <এরপর কী জানতে চাই>
```

## 9. Practical demonstration

### 9.1 Latency experiment

File: [`code/L00-06/latency_experiment.py`](code/L00-06/latency_experiment.py)

**Notebook-এ আগে লিখুন:**

- Hypothesis: "server-এ কৃত্রিম কাজ ৫ms থেকে ২৫ms করলে p50 latency প্রায় ২০ms বাড়বে।"
- Prediction: p50-এর পার্থক্য ≈ +২০ms; p95-এর পার্থক্যও কাছাকাছি।

**চালান:**

```bash
cd 00-orientation/code/L00-06
python3 latency_experiment.py --baseline-ms 5 --variant-ms 25 --requests 200
```

Script কী করে:

- নিজের ভেতরে `127.0.0.1`-এ (loopback — শুধু এই machine) একটি HTTP server চালায়; port OS বেছে দেয় (`port 0`)।
- প্রতিটি endpoint-এ ৫টি warm-up + ২০০টি মাপা request পাঠায়।
- শেষে server বন্ধ করে। কোনো file লেখে না, বাইরের network ব্যবহার করে না।

**এই repository-তে Windows 11-এ তিনবার চালিয়ে পাওয়া আসল ফল (`--requests 200`):**

| Run | baseline p50 | variant p50 | p50 পার্থক্য | baseline p95 | variant p95 |
|---|---|---|---|---|---|
| 1 | 16.7 | 40.6 | +23.9 | 32.4 | 52.1 |
| 2 | 18.6 | 39.1 | +20.5 | 32.7 | 51.0 |
| 3 | 17.0 | 42.4 | +25.4 | 31.8 | 51.7 |

(সব মান millisecond-এ।)

**ব্যাখ্যা:**

- Prediction (+২০ms) মোটামুটি মিলেছে: +২০.৫ থেকে +২৫.৪ — **তিনবারেই একই দিকে, একই মাত্রায়।** তাই সিদ্ধান্তে আস্থা রাখা যায়।
- কিন্তু একটি **অপ্রত্যাশিত পর্যবেক্ষণ**: baseline-এ server মাত্র ৫ms অপেক্ষা করে, অথচ p50 প্রায় ১৭ms! কেন? Section 9.4 দেখুন — এটি measurement নিয়েই একটি শিক্ষা।
- প্রতিটি run-এ সংখ্যা সামান্য আলাদা — এটাই **noise**। একবারের run দেখে সিদ্ধান্ত নিলে ভুল হতে পারত।

### 9.2 Failure rate experiment

```bash
python3 latency_experiment.py --baseline-ms 5 --variant-ms 5 --fail-percent 10 --requests 100
```

Variant endpoint ১০% সম্ভাবনায় HTTP 500 দেয়। **একটি আসল run-এ (Windows 11)** variant-এর `error_rate_percent` এসেছিল **13.0** — ১০ নয়।

**কেন?** ১০০টি request-এ ঠিক ১০টি ব্যর্থ হবে এমন নিশ্চয়তা নেই — যেমন ১০০ বার মুদ্রা ছুঁড়লে ঠিক ৫০টি head আসে না। ছোট sample-এ এলোমেলো ওঠানামা বেশি। `--requests 1000` দিয়ে চালালে হার সাধারণত ১০%-এর কাছাকাছি আসবে। **শিক্ষা:** ছোট sample-এর শতাংশে বেশি আস্থা রাখবেন না।

একই run-এ baseline p50 (19.0) variant p50 (7.6)-এর চেয়ে **বেশি** এসেছিল, যদিও দুটোতেই ৫ms কাজ। এটি আবারও noise ও timer-এর প্রভাব — একবারের তুলনা থেকে "variant দ্রুত" সিদ্ধান্ত নেওয়া ভুল হতো।

### 9.3 Incident timeline

File: [`code/L00-06/incident_timeline.py`](code/L00-06/incident_timeline.py) · Data: [`sample-app.log`](code/L00-06/sample-app.log) (Section 5-এর incident-এর কাল্পনিক log, ১২১ লাইন, একটি ইচ্ছাকৃত ভাঙা লাইন সহ)

```bash
python3 incident_timeline.py sample-app.log
```

শুধু log file পড়ে, কিছু লেখে না।

**এই repository-তে চালিয়ে পাওয়া আসল output:**

```text
minute    INFO  WARN  ERROR   err%
14:00       11     1      0     0%
14:01       12     0      0     0%
14:02       12     0      0     0%
14:03       12     0      0     0%
14:04        4     1      7    58%  <--
14:05        4     5      3    25%  <--
14:06        3     2      7    58%  <--
14:07       12     0      0     0%
14:08       12     0      0     0%
14:09       11     1      0     0%

parsed lines: 120   skipped (unparsable): 1
first ERROR : 14:04:00  upstream timeout after 2000ms
last ERROR  : 14:06:55  db connection pool exhausted
top errors  :
   12 × db connection pool exhausted
    5 × upstream timeout after 2000ms
incident window (err% >= 20): 14:04 → 14:06
```

**Timeline-এর সাথে পরিবর্তন মেলান:**

```bash
grep -n "deploy\|rollback" sample-app.log
```

```text
38:2026-10-20T14:03:00Z level=INFO msg="deploy started version=1.4.0" request_id=0025
44:2026-10-20T14:03:30Z level=INFO msg="deploy finished version=1.4.0" request_id=002b
86:2026-10-20T14:07:00Z level=INFO msg="rollback to version=1.3.2" request_id=0055
```

`grep -n` = মিলে যাওয়া লাইন, লাইন নম্বর সহ; `\|` = "অথবা"। এটি শুধু পড়ে।

**Timeline:**

```text
14:03:30  deploy finished 1.4.0
14:04:00  প্রথম ERROR (৩০ সেকেন্ড পরে)
14:04–06  error rate 25–58%
14:06:55  শেষ ERROR
14:07:00  rollback to 1.3.2  →  error 0%
```

**সিদ্ধান্ত:** deploy-এর পরে error শুরু, rollback-এর সাথে শেষ — শক্ত correlation। Rollback-এ সমস্যা চলে যাওয়া causation-এর পক্ষে জোরালো প্রমাণ (একটি পরীক্ষিত prediction)। তবে **কেন** 1.4.0 pool শেষ করল তা log বলে না — staging-এ পুনরুৎপাদন করে খুঁজতে হবে।

### 9.4 Measurement নিয়ে শিক্ষা: ৫ms কেন ১৭ms?

Baseline-এ server মাত্র ৫ms `sleep` করে, তবু p50 ≈ ১৭ms। সম্ভাব্য hypothesis:

1. **Timer resolution:** OS-এর scheduler একটি নির্দিষ্ট সময়-খণ্ডে (tick) thread জাগায়। Windows-এ এই খণ্ড ঐতিহাসিকভাবে প্রায় ১৫.৬ms হতে পারে, তাই ৫ms `sleep` আসলে আরো বেশি সময় নিতে পারে। Linux-এ high-resolution timer সাধারণত অনেক সূক্ষ্ম।
2. HTTP ও Python-এর overhead (request parse, thread switch)।

**Prediction:** hypothesis ১ সত্য হলে Ubuntu-তে একই experiment-এ baseline p50 ৫ms-এর অনেক কাছাকাছি আসবে।

> এটি **এখনো যাচাই হয়নি** — এই repository Windows-এ লেখা হয়েছে। এটাই আপনার Exercise ১: Ubuntu-তে চালিয়ে hypothesis পরীক্ষা করুন এবং notebook-এ ফল লিখুন।

**বড় শিক্ষা:** মাপার যন্ত্র (এখানে OS timer) নিজেই ফলাফল প্রভাবিত করে। তাই সংখ্যার সাথে environment লিখে রাখা বাধ্যতামূলক, এবং ভিন্ন machine-এর সংখ্যা সরাসরি তুলনা করা যায় না।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l00_06.py`](code/L00-06/test_l00_06.py)-এর ৭টি test: percentile ও summary, **আসল local server চালিয়ে** `/work` ও `/flaky` endpoint (100% ও 0% failure), log line parse (ঠিক ও ভাঙা), error rate ও incident window, sample log-এর ফল, ও missing file-এ exit code ২।

## 10. Code-এর ব্যাখ্যা

### latency_experiment.py

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `ThreadingHTTPServer(("127.0.0.1", 0), Handler)` | Loopback-এ server, OS খালি port দেয় | বাইরে থেকে access নেই (নিরাপদ); port conflict হয় না |
| `daemon=True` thread | Server আলাদা thread-এ | Client একই process থেকে request পাঠাতে পারে; main শেষ হলে thread-ও শেষ |
| `stop_server()`: `shutdown()` + `server_close()` | Loop থামানো ও socket বন্ধ | শুধু `shutdown()` করলে listening socket খোলা থাকে — test চলাকালীন এই `ResourceWarning` ধরা পড়েছিল এবং ঠিক করা হয়েছে |
| `random.Random(42)` | নির্দিষ্ট seed | একই input-এ একই failure pattern — experiment পুনরাবৃত্তিযোগ্য |
| `threading.Lock()` | Random generator-এ একসাথে একটি thread | Thread-safe access |
| `time.perf_counter()` | Monotonic, সর্বোচ্চ resolution-এর clock | `time.time()` system clock বদলালে (NTP) লাফ দিতে পারে — duration মাপার জন্য অনুপযুক্ত |
| `warmup` | প্রথম কয়েকটি request বাদ | Connection setup-এর খরচ স্বাভাবিক অবস্থা নয় |
| একই `HTTPConnection` পুনর্ব্যবহার | Keep-alive | প্রতিবার নতুন TCP connection-এর খরচ বাদ (Module 02-এ TCP handshake) |
| `log_message()` override | প্রতিটি request terminal-এ ছাপা বন্ধ | Printing নিজেই সময় নেয় এবং output অপাঠ্য করে |

### incident_timeline.py

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `LINE_RE` regex | Timestamp, level, msg আলাদা করে | Structured log-এর গঠন জানা থাকলে parse নির্ভরযোগ্য |
| `parse_line()` → `None` | ভাঙা লাইনে পুরো program থামে না | বাস্তব log-এ ভাঙা লাইন থাকে (truncation, multi-line stack trace); কতগুলো skip হলো তা report করা হয় |
| `errors="replace"` | অবৈধ byte-এ crash নয় | Log-এ কখনো binary বা ভুল encoding থাকে |
| `defaultdict(Counter)` | মিনিট অনুযায়ী level গণনা | সহজ ও দ্রুত aggregation |
| `incident_window()` | Threshold ছাড়ানো প্রথম ও শেষ মিনিট | Incident-এর শুরু ও শেষ নির্ধারণ — postmortem-এর timeline |

## 11. প্রত্যাশিত ফল ও যাচাই

| Command | প্রত্যাশিত |
|---|---|
| `latency_experiment.py --baseline-ms 5 --variant-ms 25` | variant p50 baseline-এর চেয়ে মোটামুটি ২০ms বেশি (সঠিক সংখ্যা machine অনুযায়ী) |
| `incident_timeline.py sample-app.log` | উপরের output হুবহু (data নির্দিষ্ট) |
| `incident_timeline.py nothing.log` | `error: file not found`, exit 2 |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Latency সংখ্যা প্রতিবার আলাদা | Noise — স্বাভাবিক | ৩–৫ বার চালান | পার্থক্য noise-এর চেয়ে বড় ও একই দিকে কিনা দেখুন |
| Baseline অপ্রত্যাশিতভাবে ধীর | Timer resolution, অন্য program CPU নিচ্ছে | `top` দিয়ে load দেখুন (Module 01) | অন্য ভারী কাজ বন্ধ রেখে মাপুন; environment লিখে রাখুন |
| `skipped (unparsable)` অনেক বেশি | Log format আলাদা | `head` দিয়ে কয়েকটি লাইন দেখুন | Regex format-এর সাথে মেলান |
| Incident window `none` | Threshold বেশি | `--threshold 10` দিয়ে চালান | Threshold-এর যুক্তি notebook-এ লিখুন |
| Timeline-এর সময় অন্য log-এর সাথে মেলে না | Timezone আলাদা | Timestamp-এ `Z` বা offset দেখুন | সব log UTC-তে রাখুন |

### ধারণাগত সাধারণ ভুল

- **একবার মেপে সিদ্ধান্ত।**
- **শুধু গড় দেখা** — tail latency লুকিয়ে যায়।
- **একসাথে অনেক কিছু বদলানো** — কোনটির প্রভাব জানা যায় না।
- **Data দেখার পরে hypothesis বানানো** — নিজের পক্ষপাত নিশ্চিত করা সহজ হয়ে যায়।
- **Correlation-কে causation ভাবা** — সমসাময়িক অন্য পরিবর্তন খুঁজুন।
- **Log না পড়ে restart** — প্রমাণ মুছে যায়; আগে log ও অবস্থা সংরক্ষণ করুন।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Experiment server শুধু `127.0.0.1`-এ — বাইরে থেকে access নেই। Lab-এ server চালালে কখনো `0.0.0.0` (সব interface) বিনা কারণে ব্যবহার করবেন না।
  - Log-এ password, token, personal data লিখবেন না — log অনেক মানুষ ও system পড়ে (Module 17, 19)।
  - বাস্তব production log বিশ্লেষণে বাইরে শেয়ার বা upload করার আগে sensitive তথ্য সরান।
  - Load test শুধু নিজের বা অনুমোদিত system-এ — অন্যের server-এ load দেওয়া আক্রমণের সমতুল্য হতে পারে।
- **Performance:** Measurement-এর নিজস্ব overhead আছে; ভারী monitoring production-কে ধীর করতে পারে — sampling ব্যবহার হয় (Module 17)।
- **Cost:** Log সংরক্ষণে খরচ আছে (বিশেষ করে cloud-এ ingest ও retention, Module 29)। প্রয়োজনীয় level-এ log করুন, সব কিছু DEBUG-এ নয়।

## 14. Hands-on exercise

1. **Timer hypothesis যাচাই (Ubuntu-তে):** Section 9.4-এর prediction পরীক্ষা করুন। `--requests 200` দিয়ে তিনবার চালান। Baseline p50 কত? Windows-এর সংখ্যার (≈১৭ms) সাথে তুলনা করে notebook-এ সিদ্ধান্ত লিখুন। (Fedora-তেও একই command।)
2. **Sample size:** `--fail-percent 10` দিয়ে `--requests` ৫০, ২০০, ১০০০ — প্রতিটি তিনবার। error rate কতটা ছড়ায়? Sample বড় হলে কী হয়?
3. **Tail latency তৈরি:** `Handler.do_GET`-এ এমন পরিবর্তন করুন যাতে ৫% request-এ অতিরিক্ত ১০০ms যোগ হয়। p50, p95, p99-এর উপর প্রভাব আগে predict করুন, তারপর মাপুন।
4. **Timeline-এ নতুন তথ্য:** `incident_timeline.py`-তে `--grep` option যোগ করুন যা নির্দিষ্ট message (যেমন "deploy") থাকা লাইনগুলো timeline-এর সাথে দেখায়। Test লিখুন।
5. **p99 হিসাব:** একটি page-এ ৫০টি backend call, প্রতিটির p99 = ধীর। অন্তত একটি ধীর হওয়ার সম্ভাবনা হিসাব করুন। (সংকেত: 0.99⁵⁰ ≈ 0.605)

## 15. Mini-project — নিজের প্রথম experiment report

নিজের পছন্দের একটি প্রশ্ন বেছে নিন এবং Section 8.5-এর notebook কাঠামোয় পূর্ণ report লিখুন। উদাহরণ:

- "Python-এ একই connection পুনর্ব্যবহার (keep-alive) বনাম প্রতিবার নতুন connection — latency-তে কত পার্থক্য?" (`run()` পরিবর্তন করে প্রতিটি request-এ নতুন `HTTPConnection`)
- "`--requests` ১০ বনাম ১০০০ — p99-এর স্থিরতা কেমন?"

শর্ত: hypothesis ও prediction **data দেখার আগে** লেখা, কমপক্ষে তিনবার পুনরাবৃত্তি, environment উল্লেখ, আসল output কপি, এবং সৎ সিদ্ধান্ত (prediction ভুল হলেও)।

## 16. Interview প্রশ্ন

1. Production সমস্যায় আপনার troubleshooting পদ্ধতি ধাপে ধাপে বলুন।
2. Latency মাপতে গড়ের বদলে percentile কেন ব্যবহার করবেন? p99 কেন গুরুত্বপূর্ণ?
3. একটি performance পরিবর্তনের প্রভাব কীভাবে নির্ভরযোগ্যভাবে মাপবেন?
4. Structured logging কী এবং এর সুবিধা কী?
5. Deploy-এর পরে error বেড়েছে — deploy-ই কারণ কিনা কীভাবে নিশ্চিত হবেন?
6. Incident-এর timeline কীভাবে তৈরি করবেন, কোন কোন উৎস থেকে?
7. Duration মাপতে `time.time()` বনাম monotonic clock — পার্থক্য কী?

## 17. Self-assessment প্রশ্ন

1. বৈজ্ঞানিক পদ্ধতির ছয়টি ধাপ একটি নিজের উদাহরণ দিয়ে লিখুন।
2. "Network-এ কিছু সমস্যা" কেন ভালো hypothesis নয়? একটি ভালো বিকল্প লিখুন।
3. Section 9.1-এ তিনবার চালানোর ফল দেখে সিদ্ধান্তে কেন আস্থা রাখা যায়? একবার চালালে কী ঝুঁকি ছিল (Section 9.2-এর উদাহরণ দিয়ে)?
4. ৫ms কাজে ১৭ms latency — দুটি সম্ভাব্য কারণ ও কীভাবে পরীক্ষা করবেন?
5. Sample log-এ deploy ও rollback-এর সময় দেখে কী সিদ্ধান্ত নেওয়া যায়, আর কী নেওয়া যায় না?
6. ডাক্তার analogy কোন তিন জায়গায় software-এর সাথে মেলে না?

## 18. সংক্ষিপ্ত সারাংশ

- শেখা ও troubleshooting দুটোরই ভিত্তি **বৈজ্ঞানিক পদ্ধতি**: observation → ভুল প্রমাণযোগ্য hypothesis → prediction → নিয়ন্ত্রিত experiment → measurement → সিদ্ধান্ত।
- **ভালো measurement:** একটি variable, warm-up, একাধিক run, বণ্টন (p50/p95/p99), environment লিখে রাখা, prediction আগে।
- Noise বাস্তব — এই lesson-এর আসল data-তেই একই experiment-এ ভিন্ন সংখ্যা ও একবারের বিভ্রান্তিকর তুলনা দেখা গেছে।
- **Structured log** ও **timeline** incident analysis-এর মেরুদণ্ড; পরিবর্তনের (deploy) সাথে মিলিয়ে দেখুন। Correlation ≠ causation।
- **Engineering notebook** — প্রতিটি experiment লিখে রাখা দীর্ঘমেয়াদি শেখার সবচেয়ে শক্তিশালী অভ্যাস।

## 19. Completion checklist

- [ ] Latency experiment অন্তত তিনবার চালিয়ে ফল notebook-এ লিখেছি
- [ ] Failure rate experiment-এ ছোট sample-এর ওঠানামা নিজে দেখেছি
- [ ] `incident_timeline.py` চালিয়ে deploy/rollback-এর সাথে timeline মিলিয়েছি
- [ ] `python3 -m unittest -v` চালিয়ে ৭টি test পাস দেখেছি
- [ ] Exercise ১ (Ubuntu-তে timer hypothesis) শেষ করেছি
- [ ] Mini-project: একটি পূর্ণ experiment report লিখেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট করেছি

## 20. Official documentation ও further reading

- Python `http.server`: https://docs.python.org/3/library/http.server.html
- Python `http.client`: https://docs.python.org/3/library/http.client.html
- Python `time.perf_counter`: https://docs.python.org/3/library/time.html#time.perf_counter
- Python `re` (regular expression): https://docs.python.org/3/library/re.html
- Google SRE book — "Monitoring Distributed Systems" ও "Effective Troubleshooting" অধ্যায়: https://sre.google/books/
- এই repository: [troubleshooting/methodology.md](../troubleshooting/methodology.md), [templates/incident-report-template.md](../templates/incident-report-template.md)

---

**পরের lesson:** L00-07 — Lab environment setup: Ubuntu (VM/native/WSL2), Python venv, notebook
