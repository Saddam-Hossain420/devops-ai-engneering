# L02-17 — Browser থেকে database পর্যন্ত: একটি request-এর পূর্ণ যাত্রা

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | Module 02-এর L02-01 থেকে L02-16 |
| **Label** | — |
| **Tested** | `request_journey.py`: ৬টি test পাস — loopback-এ client → L7 proxy → app → SQLite পুরো stack: একই request ID চারটি hop-এ, 404, database ধীর → 504 (এবং app-এর "নষ্ট" কাজ), app বন্ধ → 502, database error → 500 (client-এ বিস্তারিত ফাঁস নয়) (Python 3.14, Windows)। চারটি scenario চালানো হয়েছে — output Section 9-এ। Test-এ **তিনটি আসল bug** ধরা পড়েছে — Section 9.3। Browser DevTools ও Ubuntu-তে Nginx-সহ সংস্করণ **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Browser-এ একটি URL লেখা থেকে database-এর row ফেরত আসা পর্যন্ত **প্রতিটি ধাপ** — এবং কোন lesson কোন ধাপ ব্যাখ্যা করেছে।
- প্রতিটি hop-এর **সময় বাজেট**: DNS, TCP, TLS, proxy, app, database।
- **Request ID** দিয়ে বহু service-এর log জোড়া দেওয়া — distributed tracing-এর ভিত্তি।
- Failure কোন hop-এ হলে client কী দেখে: 502, 504, 500, timeout।
- **Connect timeout বনাম read timeout**, এবং timeout-এর পরেও backend-এ কাজ চলতে থাকা ("wasted work")।
- Python দিয়ে পুরো ছোট stack চালিয়ে fault injection।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

এই module-এ প্রতিটি স্তর আলাদা শিখেছেন। কিন্তু production-এ সমস্যা কখনো "শুধু DNS" বা "শুধু TCP" লেবেল নিয়ে আসে না — আসে "checkout page ধীর"। তখন প্রয়োজন:

- পুরো পথের একটি মানসিক মানচিত্র — কোন কোন hop আছে।
- প্রতিটি hop-এর সময় কত হওয়া স্বাভাবিক।
- একটি request-এর সব log একসাথে খুঁজে পাওয়ার উপায়।
- কোন error code কোন hop থেকে আসে তা জানা।

এটি Module 02-এর **Milestone 2** ("Network ও HTTP request flow")-এর কেন্দ্রীয় lesson, এবং Module 17 (observability)-এর distributed tracing-এর প্রস্তুতি।

## 3. সহজ ভাষায় পরিচয়

**`https://shop.example.com/items/1` — পূর্ণ যাত্রা:**

| # | ধাপ | কী ঘটে | Lesson |
|---|---|---|---|
| ১ | URL parse | scheme, host, port, path | L02-07 |
| ২ | DNS | browser cache → OS (`/etc/hosts`, systemd-resolved) → recursive resolver → authoritative | L02-06 |
| ৩ | Route | Default gateway, NAT, ISP, Internet | L02-03, L02-04 |
| ৪ | TCP handshake | SYN, SYN-ACK, ACK (১ RTT) | L02-05 |
| ৫ | TLS handshake | SNI, certificate verify, key exchange (TLS 1.3: ১ RTT) | L02-08 |
| ৬ | HTTP request | Method, path, header, cookie; HTTP/2-তে stream | L02-07 |
| ৭ | CDN / edge | Cache hit হলে এখানেই শেষ | L02-07 |
| ৮ | Firewall / SG | Cloud-এর সীমানায় অনুমতি | L02-10, L02-14 |
| ৯ | Load balancer / reverse proxy | TLS termination, routing, X-Request-ID, X-Forwarded-For | L02-12 |
| ১০ | App server | Business logic, authentication | (Module 04, 05) |
| ১১ | Database | Connection pool, query, index | (Module 05) |
| ১২ | উত্তর ফেরত | একই পথে উল্টো — প্রতিটি hop log লেখে | L02-15, L02-16 |

**সময় বাজেট (একটি সাধারণ ধারণা — আপনার system-এ মেপে দেখুন):**

```text
DNS (cache miss)      ০–১০০ ms   (cache-এ: ~০)
TCP connect           ১ RTT      (একই শহর ~৫ ms, মহাদেশ পার ~১৫০ ms)
TLS                   ১ RTT      (TLS 1.3; resume হলে কম)
Proxy                 < ১ ms
App                   ৫–৫০ ms    (business logic)
Database query        < ১০ ms    (index থাকলে)
```

প্রথম request-এ DNS + TCP + TLS = কয়েকটি RTT; keep-alive (L02-07) পরের request থেকে এগুলো বাঁচায়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অনলাইনে খাবার অর্ডার

- ঠিকানা খোঁজা (DNS) → রেস্তোরাঁয় ফোন সংযোগ (TCP) → পরিচয় যাচাই (TLS) → অর্ডার বলা (HTTP) → রিসেপশন (proxy) অর্ডার রান্নাঘরে পাঠায় → রাঁধুনি (app) ভাঁড়ার (database) থেকে উপকরণ আনেন → খাবার ফেরত।
- **অর্ডার নম্বর** (request ID) = প্রতিটি ধাপে একই নম্বর লেখা — "অর্ডার #৪৮২ কোথায় আটকে আছে?" প্রশ্নের উত্তর দেওয়া যায়।
- **504** = রিসেপশন ১০ মিনিট অপেক্ষা করে বলল "রান্নাঘর উত্তর দিচ্ছে না" — কিন্তু রাঁধুনি হয়তো এখনো রান্না করছেন (wasted work)।
- **502** = রিসেপশন রান্নাঘরে ফোনই করতে পারল না।

### Analogy কোথায় মেলে না

- রেস্তোরাঁয় অর্ডার বাতিল হলে রাঁধুনিকে জানানো হয়। HTTP-তে proxy timeout দিলে **backend সাধারণত জানে না** — কাজ চালিয়ে যায়, database-এ load দেয়, শেষে উত্তর পাঠাতে গিয়ে দেখে কেউ নেই। এই lesson-এর `db-slow` scenario-তে ঠিক এটাই দেখা যায়। প্রতিকার: deadline propagation (proxy-র অবশিষ্ট সময় header-এ পাঠানো), database query timeout, client cancel হলে কাজ থামানো।
- রেস্তোরাঁয় একটি অর্ডার একটি পথে যায়। আধুনিক system-এ একটি request প্রায়ই **বহু service-এ fan-out** করে (auth, inventory, price, recommendation) — মোট latency = সবচেয়ে ধীর শাখা, এবং p99 দ্রুত খারাপ হয়।
- খাবার একবারে আসে। Network-এ উত্তর stream হতে পারে (chunked, L02-07) — LLM token streaming-এ প্রথম byte দ্রুত, শেষ byte অনেক পরে; "latency" কোনটি মাপছেন তা স্পষ্ট করুন (TTFB বনাম total)।

## 5. Real-world engineering scenario — "Checkout ধীর, কিন্তু সব service-এর latency ভালো"

**পরিস্থিতি:** Dashboard-এ checkout API-র p99 ৩ সেকেন্ড। কিন্তু app team-এর metric বলছে handler-এর p99 ১২০ ms; database team-এর query p99 ২০ ms। সবাই বলছেন "আমাদের দিক ঠিক আছে"।

**Request ID দিয়ে একটি ধীর request অনুসরণ:**

```text
client      total 3050 ms, ttfb 3040 ms
proxy       upstream_ms 3020
app         ms 115, db_ms 18
```

Proxy ৩০২০ ms অপেক্ষা করেছে, অথচ app নিজে ১১৫ ms-এ কাজ শেষ করেছে → **ফাঁকটি proxy ও app-এর মাঝে**: হয় connection স্থাপনে (connect), নয়তো app-এর request queue-তে (app ব্যস্ত, request গ্রহণ করতে দেরি — handler-এর timer শুরু হয় request গ্রহণের পরে)।

**তদন্ত:** app-এর worker সংখ্যা ৪, প্রতিটি worker একটি ধীর external call-এ আটকে থাকলে নতুন request listen queue-তে অপেক্ষা করে (L02-05-এর backlog)। `ss -ltn`-এ Recv-Q উঁচু; `nstat`-এ ListenOverflows।

**সমাধান:** worker সংখ্যা/async, external call-এ timeout, এবং **app-এ request গ্রহণের সময় থেকে নয়, proxy-র দেওয়া timestamp থেকে queue time মাপা** (যেমন `X-Request-Start` header)।

**শিক্ষা:** প্রতিটি hop নিজের অংশ মাপে; **hop-গুলোর মাঝের ফাঁক** কেউ মাপে না — request ID দিয়ে সব hop-এর সময় পাশাপাশি রাখলেই ফাঁক দেখা যায়। এটাই distributed tracing-এর মূল ধারণা (Module 17-এ OpenTelemetry)।

## 6. Diagram — এই lesson-এর stack ও timing

```text
 client (browser-এর ভূমিকা)
   │ ① getaddrinfo("localhost")          dns_ms
   │ ② TCP connect → proxy                connect_ms
   │ ③ GET /items/1 ──────────────────────────────────────┐   ttfb_ms (③ থেকে প্রথম byte)
   ▼                                                      │
 edge proxy (L7)   X-Request-ID তৈরি, X-Forwarded-For       │
   │ ④ connect → app (CONNECT_TIMEOUT 3 s)  ── ব্যর্থ → 502 │   upstream_ms
   │ ⑤ request, উত্তরের অপেক্ষা (READ_TIMEOUT 1 s) ─ পেরোলে → 504
   ▼                                                      │
 app server        log: {"hop":"app","rid":…,"ms":…,"db_ms":…}
   │ ⑥ SELECT name FROM items WHERE id = ?   (parameterized)
   ▼                                                      │
 SQLite database   log: {"hop":"db","rid":…,"ms":…}        │
   └──────────── উত্তর একই পথে ফেরত ──────────────────────┘

 একটি request-এর সব log: grep / log system-এ rid দিয়ে খোঁজা
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Hop | পথের একটি component |
| Request ID / correlation ID | একটি request-এর সব log জোড়ার ID |
| Distributed tracing | Request-এর পূর্ণ পথ ও প্রতিটি অংশের সময় (trace, span) |
| Latency budget | প্রতিটি hop-কে মোট সময়ের কত অংশ দেওয়া |
| TTFB | প্রথম byte পর্যন্ত সময় |
| Connect timeout / read timeout | Connection স্থাপনের সীমা / উত্তরের অপেক্ষার সীমা |
| Wasted work | Client চলে যাওয়ার পরেও backend-এর কাজ |
| Deadline propagation | অবশিষ্ট সময় পরের hop-কে জানানো |
| Fan-out | একটি request থেকে বহু downstream call |
| Queue time | Request গৃহীত হওয়ার আগে অপেক্ষা |
| Structured log | JSON-এর মতো machine-readable log |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Request ID-র জীবনচক্র

1. প্রথম hop (edge proxy/LB) ID তৈরি করে, যদি আগে থেকে না থাকে (বিশ্বস্ত সীমানা থেকে এলে গ্রহণ)।
2. প্রতিটি downstream call-এ header-এ পাঠানো হয়।
3. প্রতিটি hop প্রতিটি log লাইনে ID লেখে।
4. Client-কে response header-এ ফেরত — user বা support ticket-এ "request ID: …" দিলে সরাসরি খোঁজা যায়।
5. Error body-তেও ID (এই lesson-এর 500/502/504-এ) — internal বিবরণ নয়।

Standard: W3C **Trace Context** (`traceparent` header) — OpenTelemetry এটি ব্যবহার করে (Module 17)।

### 8.2 কোন hop কোন error দেয়

| Client দেখে | উৎস | এই lesson-এর scenario |
|---|---|---|
| DNS error | Client-এর resolver | (L02-16-এ) |
| Connection refused/timeout | Client → edge | (L02-16-এ) |
| 502 | Proxy: backend-এ connect ব্যর্থ / অবৈধ উত্তর | `app-down` |
| 504 | Proxy: backend-এর উত্তরে timeout | `db-slow` |
| 500 | App নিজে (exception, DB error) — proxy শুধু পার করে | `db-error` |
| 404 | App: resource নেই — DB ঠিক | `/items/99` |

### 8.3 Connect timeout বনাম read timeout

দুটি আলাদা প্রশ্ন: "backend কি জীবিত?" (connect — ছোট রাখুন, ১–৩ s) এবং "backend কি এই কাজ সময়মতো শেষ করবে?" (read — কাজের প্রকৃতি অনুযায়ী)। একটি timeout দিয়ে দুটো মেশালে ভুল error code আসে — এই lesson-এ আসলেই ঘটেছিল (Section 9.3)।

### 8.4 Timeout-এর ক্রম

Client timeout > proxy read timeout > app-এর downstream timeout > database query timeout — ভেতরের স্তর আগে হাল ছাড়বে, যেন বাইরের স্তর অর্থপূর্ণ error পায় এবং wasted work কমে। উল্টো হলে (database ৩০ s, proxy ১ s) `db-slow`-এর মতো: proxy আগেই 504 দেয়, database আরো ২৯ সেকেন্ড কাজ করে।

## 9. Practical demonstration

File: [`code/L02-17/request_journey.py`](code/L02-17/request_journey.py)

### 9.1 স্বাভাবিক যাত্রা

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-17
python3 request_journey.py
```

**আসল output (Windows, loopback; সংখ্যা প্রতিবার ভিন্ন):**

```text
GET /items/1 → 200  request-id 858bb4932343
  client: dns 1.5 ms | tcp connect 15.9 ms | time to first byte 16.9 ms | total 34.5 ms
  {"hop": "db", "query": "SELECT ... FROM items", "ms": 0.3, "ok": true}
  {"hop": "app", "path": "/items/1", "status": 200, "ms": 1.1, "db_ms": 0.3, "response_delivered": true}
  {"hop": "proxy", "path": "/items/1", "status": 200, "upstream_ms": 16.0}

GET /items/2 → 200  request-id 191ab1248e85
  client: dns 0.3 ms | tcp connect 12.7 ms | time to first byte 17.7 ms | total 30.9 ms
  ...
GET /items/99 → 404  request-id bb79d55f4c64
  client: dns 0.3 ms | tcp connect 13.4 ms | time to first byte 2.7 ms | total 16.6 ms
  {"hop": "db", "query": "SELECT ... FROM items", "ms": 0.3, "ok": true}
  {"hop": "app", "path": "/items/99", "status": 404, "ms": 0.9, "db_ms": 0.3, "response_delivered": true}
  {"hop": "proxy", "path": "/items/99", "status": 404, "upstream_ms": 2.0}
```

**Section 5-এর পদ্ধতিতে পড়ুন:**

- `/items/1`: database ০.৩ ms, app ১.১ ms, কিন্তু proxy-র upstream ১৬ ms → **~১৫ ms proxy ও app-এর মাঝে** (নতুন TCP connection স্থাপন; এই Windows machine-এ loopback connect মাঝে মাঝে ১২–১৬ ms নেয় — client-এর `tcp connect`-এও একই)। App-এর নিজের metric দেখে এই ১৫ ms খুঁজে পাওয়া যেত না।
- `/items/99`: একই দ্রুত পথ (connect ফাঁক নেই, ২ ms) — 404 মানে database ঠিক, শুধু row নেই।
- প্রথম request-এ DNS ১.৫ ms, পরে ০.৩ ms — OS-স্তরের cache।
- **প্রতিটি request-এর সব hop একই request-id দিয়ে খুঁজে পাওয়া গেছে।**

### 9.2 Fault injection

```bash
python3 request_journey.py --fault db-slow
python3 request_journey.py --fault app-down
python3 request_journey.py --fault db-error
```

**আসল output:**

```text
GET /items/1 → 504  request-id 1a25c1f43959
  client: dns 1.5 ms | tcp connect 0.3 ms | time to first byte 1001.2 ms | total 1003.2 ms
  {"hop": "proxy", "path": "/items/1", "status": 504, "upstream_ms": 1000.3}
  {"hop": "db", "query": "SELECT ... FROM items", "ms": 1500.8, "ok": true}
  {"hop": "app", "path": "/items/1", "status": 200, "ms": 1501.4, "db_ms": 1500.8, "response_delivered": false}
```

```text
GET /items/1 → 502  request-id fc706b2c4f77
  client: dns 2.6 ms | tcp connect 0.4 ms | time to first byte 2021.6 ms | total 2024.8 ms
  {"hop": "proxy", "path": "/items/1", "status": 502, "upstream_ms": 2020.7}
```

```text
GET /items/1 → 500  request-id 95c356288d9a
  client: dns 1.8 ms | tcp connect 0.3 ms | time to first byte 2.2 ms | total 4.4 ms
  {"hop": "db", "ms": 0.2, "ok": false, "error": "no such table: missing_table"}
  {"hop": "app", "path": "/items/1", "status": 500, "ms": 0.9, "db_ms": 0.2, "response_delivered": true}
  {"hop": "proxy", "path": "/items/1", "status": 500, "upstream_ms": 1.6}
```

- **db-slow:** proxy ১ সেকেন্ডে 504 দিয়েছে; কিন্তু log-এর ক্রম দেখুন — proxy-র লাইন **আগে**, তারপর database ১৫০০ ms-এ শেষ, app status 200 কিন্তু `response_delivered: false`। User error পেয়েছেন, অথচ database ও app পুরো কাজ করেছে — **wasted work**। Load-এর সময় এটি আরো খারাপ: ধীর database-এ retry আরো load যোগ করে।
- **app-down:** 502, কিন্তু **২ সেকেন্ড পরে** — Windows-এ বন্ধ loopback port-এ connect ~২ সেকেন্ড পরে refused হয় (L02-12, L02-16-এ একই পর্যবেক্ষণ)। Linux-এ সাধারণত তাৎক্ষণিক।
- **db-error:** database-এর আসল error (`no such table`) শুধু log-এ; client-এর body-তে `{"error": "database error", "request_id": ...}` — internal বিবরণ ফাঁস হয়নি, কিন্তু support request ID দিয়ে log খুঁজে পাবে।

### 9.3 Test-এ ধরা পড়া তিনটি bug (আসল ঘটনা)

1. **SQLite connection খোলা থেকে গিয়েছিল:** `with sqlite3.connect(path) as db:` শুধু transaction commit করে, connection বন্ধ **করে না** (Python-এর একটি পরিচিত ফাঁদ)। `-W error::ResourceWarning`-এ ধরা পড়েছে, এবং Windows-এ temporary database file locked থাকায় cleanup ব্যর্থ হয়েছিল। সমাধান: স্পষ্ট `close()`।
2. **App বন্ধ থাকলেও 504 আসছিল, 502 নয়:** proxy একটি timeout (১ s) connect ও read দুটোতেই ব্যবহার করছিল; Windows-এ refused connect ২ s নেয়, তাই timeout আগে হচ্ছিল → ভুল error code → on-call engineer ভুল দিকে (ধীর backend) খুঁজতেন। সমাধান: আলাদা connect timeout (৩ s) ও read timeout (১ s) — ঠিক যেমন Nginx-এর `proxy_connect_timeout` ও `proxy_read_timeout`।
3. **Proxy timeout-এর পরে app thread-এ exception:** HTTP/1.1 keep-alive loop মৃত connection-এ পরের request পড়তে গিয়ে `ConnectionAbortedError`। সমাধান: উত্তর পাঠানো ব্যর্থ হলে `close_connection = True`।

Linux-এ ২ ও ৩ নম্বরের আচরণ ভিন্ন হতে পারে (refused তাৎক্ষণিক; বন্ধ socket-এ লেখা kernel buffer-এ সফল দেখাতে পারে, তাই `response_delivered` সেখানে `true` আসতে পারে — এটি শুধু "kernel গ্রহণ করেছে", "client পেয়েছে" নয়)।

### 9.4 Browser ও Ubuntu-তে

- Browser DevTools → Network → একটি request → **Timing** tab: DNS lookup, Initial connection, SSL, Waiting (TTFB), Content download — Section 3-এর ধাপগুলোই।
- `curl -w` (L02-16) দিয়ে একই ভাঙন।
- Ubuntu VM-এ: L02-12-এর Nginx-কে proxy হিসেবে বসিয়ে (`proxy_set_header X-Request-ID $request_id;`, access log-এ `$request_id`) এই lesson-এর app অংশের সামনে রাখুন; Nginx log ও app log একই ID দিয়ে মেলান (Exercise ৩)।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_request_journey.py`](code/L02-17/test_request_journey.py)-এর ৬টি test: স্বাভাবিক request-এ চারটি hop-এ একই ID ও সময়ের সম্পর্ক, 404, db-slow → 504 ও app-এর সফল কিন্তু অপ্রয়োজনীয় কাজ, app-down → 502 (শুধু client ও proxy hop), db-error → 500 ও log-এ বিস্তারিত, CLI।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `Log.write(hop=…, rid=…)` | Structured JSON log | Machine-readable, rid দিয়ে খোঁজা |
| Proxy-তে `uuid4` | ID না থাকলে তৈরি | প্রথম hop-এর দায়িত্ব |
| `CONNECT_TIMEOUT` / `READ_TIMEOUT` | আলাদা সীমা | 502 বনাম 504 সঠিক |
| `create_function("pause")` | SQL-এর ভেতরে delay | ধীরতা database-এ ঘটে, app-এ নয় — বাস্তবসম্মত |
| Parameterized query `?` | User input আলাদা | SQL injection প্রতিরোধ (Module 19) |
| 500-এর body-তে শুধু ID | Internal error client-এ নয় | তথ্য ফাঁস প্রতিরোধ |
| `response_delivered` | উত্তর পাঠানো গেছে কিনা | Wasted work দৃশ্যমান |
| `Stack` context manager | চালু ও সম্পূর্ণ cleanup | Test-এ ও CLI-তে একই |

**Python কেন এখানে, কোথায় নয়:** পুরো ধারণা এক file-এ, test-যোগ্য — শেখার জন্য আদর্শ। বাস্তবে: Nginx/Envoy proxy, production app framework, আসল database এবং OpenTelemetry দিয়ে স্বয়ংক্রিয় trace (Module 17)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `request_journey.py` | 200, 200, 404; প্রতিটিতে db/app/proxy log একই ID-তে |
| `--fault db-slow` | 504 ~১ s-এ; app `response_delivered: false` |
| `--fault app-down` | 502, শুধু proxy log |
| `--fault db-error` | 500; client body-তে internal error নেই |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | পরিণতি | সঠিক পদ্ধতি |
|---|---|---|
| প্রতিটি service আলাদা ID বানায় | Log জোড়া যায় না | Edge-এ একবার, তারপর propagate |
| শুধু handler-এর সময় মাপা | Queue ও connect সময় অদৃশ্য | Edge থেকে timestamp, trace |
| একটি timeout সবকিছুতে | ভুল error code | Connect ও read আলাদা |
| বাইরের timeout ভেতরের চেয়ে ছোট | Wasted work, retry storm | ভেতরের স্তর আগে হাল ছাড়বে |
| 500-এর body-তে stack trace | তথ্য ফাঁস | শুধু ID; বিস্তারিত log-এ |
| Log-এ password/token | Secret ফাঁস | Redaction (L00-04-এর masking) |
| Average latency দেখা | p99-এর সমস্যা লুকায় | Percentile (L00-06) |

## 13. Security, performance ও cost বিবেচনা

- **Security:** প্রতিটি hop-এর নিজস্ব নিয়ন্ত্রণ — TLS (edge ও ভেতরে mTLS), firewall/SG, authentication app-এ, database-এ least privilege user; request ID বা header-এ user-এর ব্যক্তিগত তথ্য নয়; client-এর পাঠানো X-Request-ID/X-Forwarded-For শুধু বিশ্বস্ত সীমানা থেকে গ্রহণ; error-এ internal বিবরণ নয়।
- **Performance:** RTT গুনুন — প্রতিটি নতুন connection-এ DNS + TCP + TLS; keep-alive ও connection pool (proxy → app, app → database); CDN cache; database index; timeout-এর সঠিক ক্রম; fan-out-এ p99।
- **Cost:** প্রতিটি hop একটি বিল — CDN, LB, compute, database, cross-AZ traffic (L02-14); wasted work সরাসরি compute ও database খরচ; log volume (প্রতিটি hop-এর log) observability খরচ বাড়ায় — sampling (Module 17)।

## 14. Hands-on exercise

1. `request_journey.py`-তে proxy ও app-এর মাঝে keep-alive connection pool যোগ করুন (L02-07-এর `Connection`); `/items/1`-এর ১৫ ms ফাঁক কি দূর হয়?
2. Deadline propagation: proxy `X-Deadline-Ms` header-এ অবশিষ্ট সময় পাঠাবে; app সেটি database query-র আগে পরীক্ষা করবে এবং সময় না থাকলে সাথে সাথে 503 দেবে। `db-slow`-এ wasted work কমে কিনা test লিখুন।
3. Ubuntu VM-এ Nginx (L02-12-এর config + `$request_id` access log-এ) এই app-এর সামনে বসিয়ে একটি request-এর Nginx ও app log মেলান।
4. Browser-এ তিনটি ভিন্ন website-এর DevTools Timing লিখে রাখুন; কোথায় সবচেয়ে বেশি সময় যায়?
5. একটি fan-out scenario: app দুটি downstream (inventory, price) একসাথে ডাকে, একটি মাঝে মাঝে ধীর — ১০০ request-এ p50 ও p99 মাপুন।

## 15. Mini-project — Milestone 2: request flow walkthrough

Milestone 2-এর acceptance: একটি document (`architecture/` বা নিজের notebook-এ) যেখানে নিজের lab-এর (Ubuntu VM: Nginx → Python app → SQLite/PostgreSQL) একটি request-এর **প্রতিটি ধাপ** — command-এর আসল output সহ — DNS (`dig`), TCP (`ss`), TLS (`openssl s_client`, নিজের CA দিয়ে), HTTP (`curl -v -w`), proxy log, app log, database query — সব একই request ID দিয়ে জোড়া, একটি packet capture (L02-15) সহ। তারপর `--fault`-এর তিনটি পরিস্থিতি আসল stack-এ তৈরি করে প্রতিটির symptom ও সঠিক diagnosis লিখুন। Module 02-এর [Lab C](../labs/02-computer-networking/C-broken-request-path/README.md) এই কাজের নির্দেশিত সংস্করণ।

## 16. Interview প্রশ্ন

1. Browser-এ একটি URL লিখে Enter চাপলে কী কী ঘটে? (যত গভীরে সম্ভব)
2. 502, 503, 504, 500 — কোন component থেকে আসে?
3. Distributed system-এ একটি request-এর log কীভাবে খুঁজবেন?
4. Connect timeout ও read timeout কেন আলাদা?
5. Timeout-এর পরে backend কাজ চালিয়ে গেলে কী সমস্যা? কীভাবে কমাবেন?
6. প্রতিটি service-এর latency ভালো, কিন্তু end-to-end ধীর — কোথায় খুঁজবেন?

## 17. Self-assessment প্রশ্ন

1. খাবার অর্ডার analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 9.1-এ `/items/1`-এর ১৫ ms কোথায় গেল এবং কীভাবে বুঝলেন?
3. `db-slow`-এ proxy-র log database-এর আগে কেন?
4. Section 9.3-এর দ্বিতীয় bug production-এ কী ক্ষতি করত?
5. Section 3-এর ১২টি ধাপের প্রতিটির জন্য একটি করে diagnosis command বলুন।

## 18. সংক্ষিপ্ত সারাংশ

- একটি request: DNS → route → TCP → TLS → HTTP → CDN/firewall → LB/proxy → app → database → ফেরত।
- Request ID edge-এ একবার তৈরি, সব hop-এ propagate ও log — hop-এর **মাঝের ফাঁক** দেখার একমাত্র উপায়।
- 502 = connect ব্যর্থ, 504 = উত্তরে timeout, 500 = app; connect ও read timeout আলাদা।
- Timeout-এর ক্রম: ভেতরের স্তর আগে; নইলে wasted work।
- Error-এ ID দিন, internal বিবরণ নয়।
- Module 02-এর সব lesson এই এক যাত্রার অংশ।

## 19. Completion checklist

- [ ] `request_journey.py`-এর চারটি scenario চালিয়ে প্রতিটি log ব্যাখ্যা করতে পারি
- [ ] Section 3-এর ১২টি ধাপ ও প্রতিটির lesson মুখে বলতে পারি
- [ ] Browser DevTools Timing ও `curl -w` তুলনা করেছি
- [ ] Milestone 2 mini-project / Lab C শুরু করেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- MDN — Navigation and resource timings: https://developer.mozilla.org/en-US/docs/Web/API/Performance_API/Navigation_and_resource_timings
- W3C Trace Context: https://www.w3.org/TR/trace-context/
- OpenTelemetry — Observability primer: https://opentelemetry.io/docs/concepts/observability-primer/
- Nginx `ngx_http_proxy_module` (timeouts): https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- Python `sqlite3` (context manager behavior): https://docs.python.org/3/library/sqlite3.html#sqlite3-connection-context-manager
- Google SRE Book — Handling overload: https://sre.google/sre-book/handling-overload/

---

**পরের lesson:** L03-01 — Git internals: object, commit, tree, ref (Module 02 সম্পূর্ণ — তার আগে [Module 02 labs](../labs/02-computer-networking/README.md) ও [quiz](../assessments/02-computer-networking/quiz.md))
