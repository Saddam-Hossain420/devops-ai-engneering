# L05-13 — Continuous project শুরু: প্রথম Python web API

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৪ ঘণ্টা |
| **পূর্বশর্ত** | এই module-এর L05-01 থেকে L05-12, [L01-10 — systemd service](../01-linux-systems/L01-10-systemd-services.md), [L00-05 — Diagram ও ADR](../00-orientation/L00-05-diagrams-and-docs.md) |
| **Label** | — |
| **Tested** | `taskflow_api.py` (TaskFlow API v0.1): ১০টি integration test পাস (Python 3.14.5, Windows)। আসলে চালানো হয়েছে: process হিসেবে চালু করে `curl` দিয়ে ১৮টি request (CRUD ও ১০ ধরনের ভুল input); localhost-এ throughput মাপা হয়েছে। `ruff`-এর security নিয়ম (`S`) ৫টি finding দিয়েছিল, সব ঠিক করা হয়েছে (Section 9.4)। **SIGTERM-এ graceful shutdown-এর test শুধু POSIX-এ চলে — এখানে (Windows) চালানো হয়নি।** Ubuntu-তে systemd unit হিসেবে **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Continuous project **TaskFlow API v0.1** — এই course-এর বাকি অংশ এই application-এর ওপর গড়ে উঠবে।
- REST-ধাঁচের resource নকশা: `/tasks`, status code, `Location` header, error-এর একই format।
- Input validation-এর স্তর: Content-Type, body-র আকার, JSON, schema, অজানা field।
- Operability: `/health` বনাম `/ready`, request id, এক লাইনে JSON access log, env config, graceful shutdown।
- SQLite: thread-প্রতি connection, WAL, schema version, parameterized query — dynamic SQL ছাড়া।
- এই module-এর প্রতিটি lesson কোথায় কাজে লাগল।
- কেন `http.server` production নয়, এবং পরের ধাপগুলো কী।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

এ পর্যন্ত tool-গুলো আলাদা আলাদা ছিল। বাস্তবে DevOps/SRE কাজের কেন্দ্রে থাকে একটি **চলমান service** — তাকে deploy করতে হয়, পর্যবেক্ষণ করতে হয়, scale করতে হয়, নিরাপদ রাখতে হয়, এবং ভাঙলে ঠিক করতে হয়।

পরের module-গুলোর প্রতিটি দক্ষতা — nginx, Docker, CI/CD, Terraform, Kubernetes, monitoring, security, ML — একটি **একই** application-এ প্রয়োগ হবে। ফলে ধারাবাহিকতা থাকে, এবং প্রতিটি পরিবর্তনের প্রভাব তুলনা করা যায়।

সেজন্য application-টা ছোট হলেও **operable** হতে হবে প্রথম দিন থেকেই:

- কেমন আছে, বলতে পারে (`/health`, `/ready`)।
- কী করছে, বলে (JSON log, request id)।
- ভুল input-এ ভেঙে পড়ে না।
- বন্ধ করার সময় চলমান কাজ নষ্ট করে না।

## 3. সহজ ভাষায় পরিচয়

| Endpoint | কাজ | সফল | সাধারণ ভুল |
|---|---|---|---|
| `GET /health` | Process সাড়া দিচ্ছে (liveness) | 200 | — |
| `GET /ready` | Database ব্যবহারযোগ্য (readiness) | 200 | 503 |
| `GET /tasks?done=&limit=&offset=` | তালিকা, filter, pagination | 200 | 400 (ভুল query) |
| `POST /tasks` | নতুন task | 201 + `Location` | 415, 400, 413, 422 |
| `GET /tasks/{id}` | একটি task | 200 | 404 |
| `PATCH /tasks/{id}` | আংশিক বদল | 200 | 404, 422 |
| `DELETE /tasks/{id}` | মোছা | 204 | 404 |

```bash
TASKFLOW_DB=/tmp/taskflow.db python3 taskflow_api.py
curl -s -X POST 127.0.0.1:8000/tasks -H 'Content-Type: application/json' -d '{"title": "write runbook"}'
```

**Error সবসময় একই রূপে:**

```json
{"error": {"code": "invalid_title", "message": "title must be a non-empty string", "request_id": "d5a2edf0d6d847bc"}}
```

`code` machine-এর জন্য (client যুক্তি), `message` মানুষের জন্য, `request_id` log-এ খোঁজার জন্য।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্তোরাঁর order counter

- **`POST /tasks`** = নতুন order নেওয়া; রসিদে order নম্বর (`Location: /tasks/7`)।
- **Validation** = counter-এ কর্মী order পড়ে নিশ্চিত হন: মেনুতে আছে? পরিমাণ যুক্তিসঙ্গত? ভুল হলে সাথে সাথে বলেন, রান্নাঘরে পাঠান না।
- **`/health`** = "দোকান খোলা?"; **`/ready`** = "রান্নাঘর order নিতে পারবে?" — দোকান খোলা থাকলেও গ্যাস ফুরিয়ে যেতে পারে।
- **Request id** = order নম্বর — অভিযোগ এলে রান্নাঘর, cashier, delivery সবার খাতায় একই নম্বর।
- **Graceful shutdown** = বন্ধের সময় নতুন order নেওয়া বন্ধ, কিন্তু যা রান্না হচ্ছে তা শেষ করে পরিবেশন।

### Analogy কোথায় মেলে না

- কর্মী অদ্ভুত order দেখে প্রশ্ন করেন। **API প্রশ্ন করতে পারে না** — শুধু গ্রহণ বা প্রত্যাখ্যান। তাই প্রত্যাখ্যানের বার্তা এমন হতে হবে যাতে client নিজে বুঝে ঠিক করতে পারে (`code` + `message`)।
- রেস্তোরাঁয় একজন খদ্দের একবারে একটি order দেন। **API-তে হাজার client একসাথে, কেউ কেউ ক্ষতিকর** — ১০ MB-এর "order" (413), `'); DROP TABLE` (parameterized query), অথবা হাজারটি সমান্তরাল connection। সীমা আগে থেকে ঠিক করতে হয়।
- রান্নাঘর বন্ধ হলে খদ্দের চলে যান। **Load balancer `/ready`-এর 503 দেখে traffic সরায়** — কিন্তু `/health`-ও 503 দিলে orchestrator process restart করে। Database বন্ধ বলে API restart করলে কিছুই ঠিক হয় না, শুধু বাড়তি চাপ পড়ে। তাই দুটি endpoint আলাদা।

## 5. Real-world engineering scenario — "Deploy-এর প্রতিটি সময় ৩০ সেকেন্ডের 502"

**পরিস্থিতি:** একটি team প্রতিটি deploy-এ দেখত, প্রায় ৩০ সেকেন্ড user-রা 502 পাচ্ছে। কারণ তিনটি:

1. Deploy script পুরোনো process-কে `SIGKILL` দিত। চলমান request মাঝপথে কাটা পড়ত, এবং database transaction অর্ধেক থেকে যেত।
2. নতুন process চালু হওয়ার সাথে সাথেই load balancer traffic পাঠাত, যদিও database connection তখনো প্রস্তুত নয়। `/health` সব সময় 200 দিত।
3. Error-এর সময় log-এ শুধু "500" — কোন request, কোন user, কিছুই জানা যেত না।

**TaskFlow v0.1-এ ভিত্তি:**

- **SIGTERM → graceful:** নতুন connection বন্ধ, চলমান request শেষ, তারপর exit 0। systemd-এর `TimeoutStopSec` (L01-10) এই সময় দেয়।
- **`/ready`** database যাচাই করে। Load balancer বা Kubernetes readiness probe (Module 14) শুধু তখনই traffic পাঠাবে।
- **Request id + JSON log:** প্রতিটি error-এ `request_id`; client-কেও `X-Request-ID` header-এ ফেরত দেওয়া হয়, তাই support ticket থেকে সরাসরি log-এ যাওয়া যায়।

**শিক্ষা:** Zero-downtime deploy-এর দায় শুধু deploy tool-এর নয়, application-এরও। Signal সামলানো, readiness ও traceability application-কেই দিতে হয়।

## 6. Diagram — TaskFlow v0.1

```text
 client (curl / পরে browser, nginx)
    │  HTTP/1.1  127.0.0.1:8000
    ▼
 ThreadingHTTPServer  ── প্রতিটি connection একটি thread
    │
 Handler._dispatch()
    ├─ _begin(): X-Request-ID (বৈধ হলে রাখা, নইলে নতুন), সময় শুরু
    ├─ _route():  /health · /ready · /tasks · /tasks/{id}
    │     └─ _json_body(): Content-Type (415) → Content-Length (411/413) → JSON (400)
    │     └─ validate_task(): object? অজানা field? title 1..200? done bool?  (422)
    ├─ Store (sqlite3, প্রতি কাজে নতুন connection, parameterized SQL, WAL)
    │        taskflow.db  ── PRAGMA user_version = 1 (schema version)
    ├─ ApiError → {"error": {code, message, request_id}}  (+ Allow on 405)
    ├─ sqlite3.Error → 503 ; অন্য exception → 500 (traceback শুধু log-এ)
    └─ _send(): X-Request-ID, nosniff, no-store, Server: taskflow → JSON access log (stderr)

 SIGTERM/SIGINT → server.shutdown() (আলাদা thread) → server_close() (চলমান request join) → exit 0

 পরের ধাপ:  Module 06 nginx (TLS, proxy) → 09 Docker → 11 CI → 14 Kubernetes → 17 metrics → 20 PostgreSQL …
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Resource | API-র "বস্তু" (task), URL দিয়ে চেনা |
| Idempotent method | GET, PUT, DELETE — বারবার করলে একই অবস্থা (L05-06) |
| 201 + `Location` | নতুন resource তৈরি, এবং কোথায় পাওয়া যাবে |
| 415 / 413 / 422 | ভুল media type / body খুব বড় / বোঝা গেছে কিন্তু অবৈধ |
| Readiness / liveness | Traffic নেওয়ার যোগ্য / process জীবিত (L05-12) |
| Graceful shutdown | নতুন কাজ বন্ধ, চলমান কাজ শেষ, তারপর বের হওয়া |
| Parameterized query | SQL-এ মান `?` দিয়ে আলাদা পাঠানো — injection নয় |
| WAL | SQLite-এর write-ahead log — পাঠক লেখককে আটকায় না |
| Schema version | Database কাঠামোর version (`PRAGMA user_version`) |
| Pagination | `limit`/`offset` দিয়ে অংশ অংশ তালিকা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 এই module কোথায় কাজে লাগল

| Lesson | TaskFlow-এ |
|---|---|
| L05-01 | Stdlib-only — venv থাকলেও কোনো dependency নেই; পরে `pyproject.toml` |
| L05-02 | `@dataclass(frozen=True) Config`, type hint |
| L05-04 | (পরে) migration/backup command |
| L05-05 | Env config + validation, ভুল মানে শুরুই হয় না |
| L05-06 | HTTP semantics, idempotency, status code |
| L05-07 | JSON log, request id, exception শুধু log-এ |
| L05-08 | Exit code; config error-এ `SystemExit` বার্তা |
| L05-09 | Integration test — আসল server, আসল socket, temp DB |
| L05-10 | `.env.example`, secret নেই; পরে `*_FILE` |
| L05-12 | `/health` ও `/ready` |

### 8.2 `ThreadingHTTPServer` ও SQLite

প্রতিটি connection একটি thread। `sqlite3` connection thread-এর মধ্যে ভাগ করা নিরাপদ নয়, তাই `Store` প্রতিটি কাজে নতুন connection খোলে। খরচ সামান্য, কারণ file local।

- **WAL mode:** একজন লেখার সময় অন্যরা পড়তে পারে।
- **`busy_timeout`:** দুজন একসাথে লিখলে দ্বিতীয়জন ৫ s পর্যন্ত অপেক্ষা করে, সাথে সাথে "database is locked" দেয় না।
- ৪০টি সমান্তরাল POST-এ সব id অনন্য — test-এ যাচাই করা।

### 8.3 Graceful shutdown

Signal handler-এর ভেতর থেকে সরাসরি `server.shutdown()` ডাকলে deadlock হয়। কারণ `shutdown()` অপেক্ষা করে `serve_forever()` loop থামার, আর signal handler চলছে সেই একই main thread-এ। তাই আলাদা thread থেকে ডাকা হয়।

`daemon_threads=False` + `block_on_close=True` মানে `server_close()` চলমান request-এর thread শেষ হওয়া পর্যন্ত অপেক্ষা করে।

Windows-এ `SIGTERM` handler কার্যকর নয় (`terminate()` সরাসরি process বন্ধ করে)। তাই graceful test শুধু POSIX-এ চলে।

### 8.4 Validation-এর ক্রম

সস্তা ও নিরাপদ যাচাই আগে:

1. Content-Type।
2. Content-Length (বড় হলে body **পড়াই হয় না**, connection বন্ধ)।
3. JSON parse।
4. Schema।

অজানা field প্রত্যাখ্যান করা হয় (L05-05-এর typo-নীতি)। Client `"titel"` পাঠালে চুপচাপ উপেক্ষা না করে 422 দেওয়া হয়। `done`-এ শুধু JSON `true`/`false` — `"yes"` বা `1` নয়।

### 8.5 কেন `http.server` production নয়

Python documentation নিজেই সতর্ক করে যে `http.server` production-এর জন্য উপযুক্ত নয়: শুধু মৌলিক নিরাপত্তা যাচাই করে, slow client-এর বিরুদ্ধে সুরক্ষা নেই, এবং TLS নেই।

তাই:

- এখানে শুধু `127.0.0.1`-এ শোনে।
- Module 06-এ nginx সামনে বসবে (TLS, timeout, body limit, rate limit)।
- পরে production-মানের application server আসবে — সেই সিদ্ধান্ত ADR-এ লেখা হবে।

> **Fedora-তে:** কোনো পার্থক্য নেই। systemd unit (L01-10-এর `taskflow-demo.service`-এর মতো) দুই distro-তেই চলে। Fedora-তে SELinux-এর কারণে service-কে non-standard port-এ bind করতে `semanage port` লাগতে পারে (L01-17); ৮০০০ সাধারণত `http_port_t`-এর অংশ নয়।

## 9. Practical demonstration

Files:

- [`code/L05-13/taskflow_api.py`](code/L05-13/taskflow_api.py)।
- [`.env.example`](code/L05-13/.env.example)।
- [`test_l05_13.py`](code/L05-13/test_l05_13.py)।

### 9.1 চালানো ও smoke test — আসল output

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-13
TASKFLOW_DB=/tmp/taskflow.db python3 taskflow_api.py 2> /tmp/taskflow.log &
H=127.0.0.1:8000
curl -s -i $H/health
curl -s -X POST $H/tasks -H 'Content-Type: application/json' -H 'X-Request-ID: demo-001' -d '{"title": "write runbook"}' -i
curl -s "$H/tasks?done=false"
curl -s -X PATCH $H/tasks/1 -H 'Content-Type: application/json' -d '{"done": true}'
```

```text
HTTP/1.1 200 OK
Server: taskflow
X-Request-ID: 75988a2b87304e74
X-Content-Type-Options: nosniff
Cache-Control: no-store
Content-Type: application/json; charset=utf-8
Content-Length: 37

{"status": "ok", "version": "0.1.0"}

HTTP/1.1 201 Created
X-Request-ID: demo-001
Location: /tasks/1
…
{"id": 1, "title": "write runbook", "done": false, "created_at": "2026-10-27T03:18:45+00:00", "updated_at": "2026-10-27T03:18:45+00:00"}

{"items": [{"id": 1, "title": "write runbook", "done": false, …}], "total": 1, "limit": 50, "offset": 0}

{"id": 1, "title": "write runbook", "done": true, "created_at": "2026-10-27T03:18:45+00:00", "updated_at": "2026-10-27T03:18:46+00:00"}
```

(প্রথম run-এ `Server: taskflow ` — শেষে একটি অতিরিক্ত space ছিল; Section 9.4।)

### 9.2 ভুল input — আসল output (প্রতিটির শেষে HTTP status)

```text
{"title": ""}                    → invalid_title           [422]
-d 'title=x' (form)              → unsupported_media_type  [415]
{"title": "x", "owner": "ana"}   → unknown field(s): owner [422]
{"title": "x", "done": "yes"}    → invalid_done            [422]
'{bad json'                      → invalid JSON: Expecting property name enclosed in double quotes: line 1 column 2 (char 1)  [400]
?limit=1000                      → limit must be an integer 1..100  [400]
DELETE /tasks/2                  → [204]   তারপর GET /tasks/2 → not_found [404]
PUT /tasks                       → method_not_allowed      [405]
/tasks/1%27%20OR%201=1           → no route                [404]
20 KB title                      → body larger than 16384 bytes  [413]
```

Server-এর log-এ প্রতিটির জন্য এক লাইন:

```text
{"ts": "2026-10-27T03:18:45.363+00:00", "level": "info", "msg": "request", "method": "GET", "path": "/health", "status": 200, "duration_ms": 0.14, "request_id": "75988a2b87304e74", "client": "127.0.0.1"}
```

### 9.3 `localhost` বনাম `127.0.0.1` — আসল পরিমাপ

Demo-র সময় প্রতিটি `curl localhost:8000` ~০.২ s নিচ্ছিল, অথচ server-এর log-এ `duration_ms` ছিল ০.১৪–১.৮৭। আলাদা করে মাপা হলো:

```text
localhost: total 0.210056s connect 0.209200s
127.0.0.1: total 0.001210s connect 0.000474s
```

`localhost` আগে IPv6 `::1`-এ resolve হয়। Server শুধু `127.0.0.1`-এ শুনছে, তাই প্রথম চেষ্টা প্রত্যাখ্যাত হয়, এবং Windows-এ সেই প্রত্যাখ্যানে সময় লাগে (L05-06)। তারপর IPv4-এ সফল।

**শিক্ষা:** Latency মাপার সময় client-এর দিক (DNS, connect) ও server-এর দিক (`duration_ms`) আলাদা করুন। নইলে "API ধীর" ভেবে ভুল জায়গায় খুঁজবেন। Section 9.1-এর command তাই `127.0.0.1` ব্যবহার করে।

### 9.4 লেখার সময় ঠিক করা সমস্যা

`ruff check --select S` (bandit-এর নিয়ম) প্রথম সংস্করণে ৫টি finding দিয়েছিল:

- **২টি `assert` (S101):** L05-09-এই বলা হয়েছে, `python -O` দিলে assert মুছে যায়। স্পষ্ট `raise`-এ বদলানো হয়েছে।
- **৩টি f-string-এ গড়া SQL (S608):** `WHERE` অংশ ও `UPDATE`-এর column তালিকা। Key-গুলো নির্দিষ্ট তালিকা থেকে আসত, তাই আসল injection ছিল না। তবুও সমাধান হিসেবে **dynamic SQL পুরো বাদ** দেওয়া হলো:
  - `WHERE ?1 IS NULL OR done = ?1`।
  - `SET title = COALESCE(?, title)`।
  - এখন প্রতিটি query একটি স্থির string — review সহজ, ভবিষ্যতের পরিবর্তনে ঝুঁকিও নেই।

Smoke test থেকে আরও দুটি:

- **`Server: taskflow `** — শেষে space, কারণ `version_string()` `server_version + " " + sys_version` জোড়ে। এখন `version_string()` override করা হয়েছে। Default মান (`BaseHTTP/0.6 Python/3.14.5`) আক্রমণকারীকে exact version জানিয়ে দিত।
- **405-এ `Allow` header নেই** — HTTP spec (RFC 9110) অনুযায়ী থাকা উচিত। যোগ করা হয়েছে।

### 9.5 Baseline throughput — আসল পরিমাপ (এই Windows laptop, localhost)

```text
POST /tasks   n=500   workers=1        75 req/s
POST /tasks   n=500   workers=10      284 req/s
GET /tasks/1  n=1000  workers=1       253 req/s
GET /tasks/1  n=1000  workers=10      906 req/s
```

প্রতিটি request-এ নতুন TCP connection, প্রতিটি POST-এ নতুন SQLite connection ও disk-এ commit। এই সংখ্যাগুলো **শুধু তুলনার ভিত্তি:**

- Module 06-এ nginx-এর পেছনে।
- Module 09-এ container-এ।
- Module 20-এ PostgreSQL-এ।

প্রতিটি ধাপে একই মাপ নিয়ে বোঝা যাবে কী বদলাল। আপনার machine-এ সংখ্যা ভিন্ন হবে।

### 9.6 Ubuntu-তে systemd service (চালানো হয়নি)

L01-10-এর unit-এর ওপর ভিত্তি করে:

```ini
[Service]
User=taskflow
Environment=TASKFLOW_DB=/var/lib/taskflow/taskflow.db TASKFLOW_PORT=8000
StateDirectory=taskflow
ExecStart=/usr/bin/python3 /opt/taskflow/taskflow_api.py
KillSignal=SIGTERM
TimeoutStopSec=15
NoNewPrivileges=true
ProtectSystem=strict
ProtectHome=true
```

```bash
sudo systemctl daemon-reload && sudo systemctl start taskflow
curl -s 127.0.0.1:8000/ready
journalctl -u taskflow -o cat | tail -3          # JSON লাইন
sudo systemctl stop taskflow                     # log-এ "shutdown requested" → "stopped"
```

`StateDirectory=` systemd-কে `/var/lib/taskflow` বানিয়ে service user-কে মালিকানা দিতে বলে, তাই `ProtectSystem=strict`-এও database লেখা যায়।

### 9.7 Test

```bash
python3 -m unittest -v
```

১০টি integration test:

- পূর্ণ CRUD জীবনচক্র (trim, `Location`, PATCH-এ অন্য field অপরিবর্তিত, DELETE দুবার)।
- Filter ও pagination।
- Header (`X-Request-ID` ফেরত, `Server: taskflow`, অদ্ভুত id বদলে নতুন)।
- ১০ রকম validation error।
- 415/400/413/405 + `Allow`।
- SQL injection-এর চেষ্টা আক্ষরিক data হিসেবে থাকে।
- ৪০টি সমান্তরাল POST-এ অনন্য id।
- Restart-এর পরে data থাকে।
- ভুল config।
- Process হিসেবে চালু ও বন্ধ (POSIX-এ SIGTERM → exit ০ ও "stopped" log)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `Config.from_env` → `SystemExit` | ভুল config-এ শুরু নয় | Fail fast (L05-05) |
| `Store.connect()` প্রতিবার | Thread-নিরাপদ | sqlite connection ভাগ করা যায় না |
| `PRAGMA user_version` | Schema version | ভবিষ্যতের migration; নতুন DB + পুরোনো app = থামা |
| `CHECK` constraint | Database-স্তরেও নিয়ম | Code-এর bug হলেও অবৈধ data নয় |
| `?1 IS NULL OR done = ?1`, `COALESCE` | স্থির SQL | Dynamic SQL নেই |
| `REQUEST_ID` regex | বাইরের id যাচাই | Log injection, অসীম দৈর্ঘ্য নয় |
| `_json_body` ক্রম | সস্তা যাচাই আগে | বড় body পড়াই হয় না |
| `close_connection = True` (413) | বাকি body উপেক্ষা | Keep-alive-এ পরের request নষ্ট হয় না |
| `except Exception` → 500, log-এ traceback | Client-এ ভেতরের বিবরণ নয় | তথ্য ফাঁস নয়; request id দিয়ে খোঁজা |
| `version_string()` override | `Server: taskflow` | Version ফাঁস নয় |
| `shutdown()` আলাদা thread-এ | Signal handler-এ deadlock নয় | Section 8.3 |
| `block_on_close`, `daemon_threads=False` | চলমান request শেষ হয় | Graceful |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `curl -i 127.0.0.1:8000/health` | 200, `Server: taskflow`, `X-Request-ID` |
| `POST /tasks` | 201 + `Location` |
| Section 9.2-এর ভুল input | প্রতিটিতে নির্দিষ্ট `code` ও status |
| Restart | Data থাকে |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `OSError: [Errno 98] Address already in use` | আগের process চলছে | `ss -ltnp 'sport = :8000'`; অন্য port |
| `database is locked` | দীর্ঘ লেখা, timeout নেই | WAL + `busy_timeout` |
| `localhost` ধীর | IPv6 আগে | `127.0.0.1` ব্যবহার, বা `::`-এ bind |
| অন্য machine থেকে connect হয় না | `127.0.0.1`-এ bind | ইচ্ছাকৃত; nginx-এর পেছনে রাখুন (Module 06) |
| systemd-এ `unable to open database file` | `ProtectSystem=strict` | `StateDirectory=` |
| `415` অথচ JSON পাঠিয়েছি | `Content-Type` header নেই | `-H 'Content-Type: application/json'` |
| বন্ধে চলমান request কাটা পড়ে | SIGKILL | SIGTERM + `TimeoutStopSec` |
| Client 500 পায়, কারণ জানা নেই | — | Response-এর `request_id` দিয়ে log-এ খুঁজুন |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - শুধু `127.0.0.1`-এ শোনে।
  - Body-র সীমা ১৬ KB; অজানা field প্রত্যাখ্যান।
  - Parameterized ও স্থির SQL।
  - Error-এ traceback নয়; `Server` header-এ version নয়; `nosniff`।
  - **এখনো নেই:** authentication, TLS, rate limit, CORS — Module 06 (nginx), 19 (security)।
  - এখনই internet-এ খুলবেন না।
- **Performance:**
  - Baseline (Section 9.5)।
  - Thread-প্রতি-connection মডেল হাজার connection-এ ভেঙে পড়ে।
  - SQLite-এ একসাথে একজনই লিখতে পারে।
  - এগুলো জেনে-বুঝে নেওয়া সীমা — ADR-0001-এর মতো "কেন এখন যথেষ্ট" লিখে রাখুন।
- **Cost:** এখন শূন্য (local)। পরে cloud-এ সবচেয়ে ছোট instance-এ চলবে। Database PostgreSQL-এ নিলে managed database-এর খরচ আসবে (Module 08/20) — সেই সিদ্ধান্তের আগে খরচ হিসাব করা হবে।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.6-এর systemd unit চালান। `systemctl stop`-এর সময় একটি ধীর request চলাকালীন (exercise ৩) graceful shutdown যাচাই করুন।
2. `GET /tasks`-এ `?q=` (title-এ খোঁজা) যোগ করুন — parameterized `LIKE`, এবং `%`/`_` escape। আগে test লিখুন।
3. Debug-এর জন্য `TASKFLOW_SLOW_MS` env যোগ করুন (প্রতিটি request-এ কৃত্রিম delay) এবং graceful shutdown পরীক্ষা করুন।
4. L05-12-এর `healthcheck.py` দিয়ে TaskFlow-এর `/health` ও `/ready` এবং database file-এর বয়স check করুন।
5. L05-11-এর ধারণায় TaskFlow-এর JSON access log থেকে p50/p99 ও status-এর হিসাব বের করুন (`jq` বা Python)।
6. একটি ADR লিখুন (L00-05-এর template): "v0.1-এ SQLite ও stdlib http.server কেন" — বিকল্প, পরিণতি, কখন বদলাবেন।

## 15. Mini-project — TaskFlow v0.2

- `pyproject.toml` (L05-01), `src/taskflow/` package, এবং pytest suite (L05-09)।
- `taskflow` CLI (L05-08): `serve`, `migrate`, `backup` (`sqlite3` `.backup` API → tar.gz → sha256; L05-12-এর `verify_backup.py` দিয়ে যাচাই)।
- `/metrics` endpoint-এ request count ও latency histogram (L05-11 → Module 17-এ Prometheus)।
- `README.md`-এ এক command-এ চালানো, `.env.example`, ও acceptance check।

Project P02-এর শুরু এখান থেকে।

## 16. Interview প্রশ্ন

1. REST API-তে 400, 404, 409, 415, 422-এর পার্থক্য কী?
2. Liveness ও readiness endpoint আলাদা কেন?
3. Graceful shutdown কীভাবে implement করবেন? Kubernetes-এ কী হয়?
4. Request id কীভাবে কাজ করে, এবং client-কে ফেরত দেওয়া কেন?
5. SQL injection কীভাবে ঠেকাবেন? Dynamic SQL কখন লাগে?
6. Python-এর `http.server` কেন production-এ নয়?

## 17. Self-assessment প্রশ্ন

1. রেস্তোরাঁ analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি কারণ এবং TaskFlow-এর তিনটি উত্তর কী?
3. `localhost` কেন ০.২ s নিচ্ছিল?
4. Signal handler থেকে সরাসরি `shutdown()` ডাকলে কী হয়?
5. Bandit-এর ৫টি finding কী ছিল, এবং SQL-এর সমাধান কেন "dynamic SQL বাদ"?

## 18. সংক্ষিপ্ত সারাংশ

- TaskFlow v0.1: stdlib, `/tasks` CRUD, `/health` + `/ready`, error-এর একই format।
- Validation স্তরে স্তরে: Content-Type → আকার → JSON → schema (অজানা field নয়)।
- Operability: request id, JSON log, env config, graceful shutdown।
- SQLite: connection প্রতি কাজে, WAL, schema version, স্থির parameterized SQL।
- Baseline মাপা হয়েছে; সীমা জেনে-বুঝে নেওয়া — পরের module-গুলো এর ওপর গড়বে।

## 19. Completion checklist

- [ ] TaskFlow চালিয়ে CRUD ও ১০টি ভুল input নিজে পরীক্ষা করেছি
- [ ] (Ubuntu) systemd service হিসেবে চালিয়ে graceful stop দেখেছি
- [ ] নিজের machine-এ baseline throughput মেপেছি
- [ ] `python3 -m unittest -v`-এ ১০টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `http.server` (security considerations): https://docs.python.org/3/library/http.server.html
- Python — `sqlite3`: https://docs.python.org/3/library/sqlite3.html
- SQLite — Write-Ahead Logging: https://www.sqlite.org/wal.html
- RFC 9110 — HTTP Semantics: https://www.rfc-editor.org/rfc/rfc9110
- RFC 9457 — Problem Details for HTTP APIs: https://www.rfc-editor.org/rfc/rfc9457
- systemd — `systemd.exec` (StateDirectory): https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- Bandit — security issues: https://bandit.readthedocs.io/

---

**পরের lesson:** L06-01 — DNS record ও domain configuration
