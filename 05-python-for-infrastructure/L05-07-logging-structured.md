# L05-07 — Logging, structured log ও exception

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-06 — HTTP client](L05-06-http-client-retry.md), [L04-05 — Argument parsing ও logging (Bash)](../04-bash-and-shell-automation/L04-05-argument-parsing-logging.md), [L01-14 — Log ও debugging](../01-linux-systems/L01-14-logs-and-debugging.md) |
| **Label** | — |
| **Tested** | `logsetup.py`: ১০টি test পাস (Python 3.14.5, Windows)। `demo_job.py` text ও JSON দুই mode-এ চালানো হয়েছে। আসল পরীক্ষায় দেখা গেছে, **সাধারণ thread ও thread pool-এ request id হারিয়ে যায়** (Section 9.3)। প্রথম সংস্করণের text formatter-এ একটি পাঠযোগ্যতার সমস্যা ঠিক করা হয়েছে। journald / log collector-এ পাঠানো **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Python `logging`-এর কাঠামো: logger → filter → handler → formatter; level; logger hierarchy ও `propagate`।
- **Structured logging:** এক লাইনে এক JSON — কেন machine-এর জন্য এটা দরকার।
- **Request/correlation id** `contextvars` দিয়ে — এবং thread-এ পাঠানোর ফাঁদ।
- `log.exception` — traceback-সহ, কিন্তু এক field-এ।
- **Secret redaction:** message, extra field ও traceback থেকে; এবং এর সীমা।
- সাধারণ ভুল: `print`, f-string-এ log, দ্বিগুণ handler, `basicConfig` কাজ না করা, stdout-এ log।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

রাত ৩টায় alert এল: "backup failed"। আপনার হাতে log:

```text
Error!
connection failed
Done
```

কোন database? কোন run? কখন (কোন time zone)? Traceback কোথায়? এদিকে একই সময়ে চলা দশটি job-এর লাইন মিশে আছে, আর এক জায়গায় দেখা যাচ্ছে `password=Prod2024!`।

ভালো log-এর চারটি গুণ:

1. **Context** — কোন request, কোন db।
2. **Machine-readable** — Loki/Elasticsearch-এ খোঁজা যায় (Module 17)।
3. **Correlation** — একই কাজের সব লাইন একটি id দিয়ে খুঁজে পাওয়া।
4. **নিরাপদ** — secret নেই।

## 3. সহজ ভাষায় পরিচয়

```python
import logging
log = logging.getLogger(__name__)          # module-ভিত্তিক নাম: "ops.backup"

log.debug("details")                       # level: DEBUG < INFO < WARNING < ERROR < CRITICAL
log.info("dumped %s", db)                  # ✅ %-style: level বন্ধ থাকলে format-ই হয় না
log.info(f"dumped {db}")                   # ⚠️ সবসময় format হয়; message-এর "template" হারায়
log.info("dumped", extra={"db": db, "size_mb": 120})   # structured field
try:
    ...
except ConnectionError:
    log.exception("backup failed")         # ERROR level + traceback
```

| অংশ | কাজ |
|---|---|
| Logger | নামযুক্ত উৎস (`ops`, `ops.backup`); level-এর প্রথম ছাঁকনি |
| Filter | Record বদলানো বা বাদ দেওয়া (request_id যোগ, redaction) |
| Handler | কোথায় যাবে (stderr, file, syslog) |
| Formatter | কেমন দেখাবে (text বা JSON) |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের রোগী-নোট

- **`print("error")`** = দেয়ালে চক দিয়ে লেখা "রোগী খারাপ" — কোন রোগী, কখন, কে লিখল জানা নেই।
- **Structured log** = ছাপানো চার্ট: সময়, রোগীর ID, মাপা মান, কে লিখলেন — যেকোনো ডাক্তার বা কম্পিউটার পড়তে পারে।
- **Request id** = রোগীর হাতের ব্যান্ডের নম্বর — ল্যাব, ফার্মেসি, ওয়ার্ড সবার নোট সেই নম্বরে জোড়া যায়।
- **Level** = জরুরি অবস্থার মাত্রা — সাধারণ নোট, সতর্কতা, জরুরি।
- **Redaction** = চার্টে রোগীর ব্যাংক PIN লেখা হয় না, এমনকি রোগী মুখে বললেও।

### Analogy কোথায় মেলে না

- হাতের ব্যান্ড রোগীর সাথে সব ঘরে যায়। **`contextvars`-এর request id নতুন thread-এ নিজে থেকে যায় না** (Section 9.3) — `copy_context()` দিয়ে "ব্যান্ড পরিয়ে দিতে" হয়। Async task-এ যায়, কিন্তু thread-এ নয় (সাধারণ Python build-এ)।
- নোট লেখা নার্সের কাজ, রোগী নিজে লেখেন না। **Log-এ library-গুলোও লেখে** (urllib3, boto3)। তাদের level ও handler-ও নিয়ন্ত্রণ করতে হয়, নইলে debug-এ তারা request header (token সহ) লিখে দিতে পারে।
- চার্টের PIN বাদ দেওয়া মানুষের বিবেচনা। **Redaction regex-ভিত্তিক:** `password=…` ধরে, কিন্তু `"connecting with hunter2"` ধরে না। প্রকৃত সুরক্ষা হলো secret log-এর কাছে পৌঁছাতে না দেওয়া (L05-10) — redaction শেষ রক্ষাকবচ মাত্র।

## 5. Real-world engineering scenario — "Log-এ database password"

**পরিস্থিতি:** একটি migration tool connection ব্যর্থ হলে লিখত:

```python
log.error(f"cannot connect: {dsn}")      # dsn = postgres://app:Prod2024!@db-1/orders
```

Log যেত centralized logging-এ। সেখানে ৪০ জন engineer, একটি third-party vendor-এর support team, ও ৯০ দিনের retention-এর access ছিল। Security audit-এ password পাওয়া গেল, এবং **সব জায়গায় password rotate** করতে এক সপ্তাহ লাগল।

পরে দেখা গেল একই ঘটনা ঘটছিল exception-এর মাধ্যমেও: driver-এর `ConnectionError`-এর message-এ DSN ছিল, আর `log.exception` সেটা traceback-সহ লিখছিল।

**এই lesson-এর স্তরগুলো:**

1. DSN-এ password না রাখা (env/file থেকে আলাদা — L05-10)।
2. Log handler-এ `RedactFilter`: message, extra field, **traceback-এর লেখা** — সব জায়গা থেকে `scheme://user:***@host`।
3. Test: `assertNotIn("s3cr3t-demo", stderr)` (Section 9.4)।
4. Log pipeline-এ (Module 17) দ্বিতীয় স্তরের redaction।

**শিক্ষা:** Log একটি **data store** — তার access, retention ও বিষয়বস্তু database-এর মতোই গুরুত্ব দিয়ে ভাবুন।

## 6. Diagram — একটি log record-এর যাত্রা

```text
 log.info("dumped %s", db, extra={"db": "orders", "size_mb": 120})
   │
   ▼ Logger "ops.backup"  ── level ≥ INFO? না → বাদ (format-ই হয় না — সস্তা)
   │ propagate=True
   ▼ Logger "ops"  (setup_logging এখানে handler রেখেছে; propagate=False → root-এ যায় না)
   │
   ▼ Handler (StreamHandler → stderr)
       ├─ ContextFilter   record.request_id = contextvar.get()   ("job-7f3a")
       ├─ RedactFilter    msg ও extra-তে password/token/... → ***
       └─ Formatter
            JSON: {"ts":"…+00:00","level":"info","logger":"ops.backup","msg":"dumped orders",
                   "request_id":"job-7f3a","db":"orders","size_mb":120}
            Text: 2026-10-27T02:50:49Z INFO [job-7f3a] ops.backup: dumped orders db=orders size_mb=120

 stdout = শুধু program-এর ফল ("failed=1")   ← pipe/jq নিরাপদ
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Logger hierarchy | `ops.backup` হলো `ops`-এর child; record উপরে যায় (`propagate`) |
| Handler | Record-এর গন্তব্য |
| Formatter | Record → text |
| Filter | Record-এ যোগ বা বাদ |
| Structured log | Field-সহ (JSON), শুধু বাক্য নয় |
| JSON Lines / NDJSON | প্রতি লাইনে একটি JSON object |
| Correlation / request id | একই কাজের সব log জোড়ার ID |
| `contextvars` | Thread/async-নিরাপদ "বর্তমান context"-এর মান |
| `log.exception` | ERROR + বর্তমান exception-এর traceback |
| Redaction | Secret মুছে `***` |
| Log level | গুরুত্ব; production-এ সাধারণত INFO |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Level দুই জায়গায়

Logger-এর level প্রথম ছাঁকনি — এখানে বাদ পড়লে record-ই তৈরি হয় না। Handler-এরও level থাকতে পারে, যেমন file-এ DEBUG, কিন্তু console-এ WARNING।

`%`-style argument দিলে message-এর format **শুধু তখনই হয় যখন সত্যিই লেখা হবে** — test-এ যাচাই করা হয়েছে: বন্ধ level-এ `__str__` একবারও ডাকা হয়নি। f-string আগেই format হয়ে যায়।

### 8.2 `basicConfig` ও দ্বিগুণ লাইন

- `logging.basicConfig()` root logger-এ handler যোগ করে, কিন্তু **root-এ আগে থেকে handler থাকলে কিছুই করে না** — কোনো import করা library আগে ডাকলে আপনার config নীরবে উপেক্ষিত হয়।
- আবার নিজের logger-এ handler রেখে `propagate=True` রাখলে প্রতিটি লাইন **দুবার** আসে (নিজের ও root-এর handler)।

`setup_logging` তাই একটি নামযুক্ত logger configure করে, পুরোনো handler সরায়, এবং `propagate=False` রাখে।

### 8.3 `contextvars` ও thread

`ContextVar` প্রতিটি context-এ আলাদা মান রাখে।

- **asyncio:** প্রতিটি task তৈরির সময় বর্তমান context-এর **copy** পায়, তাই request id স্বাভাবিকভাবে যায়।
- **নতুন thread:** **খালি context** দিয়ে শুরু হয় (সাধারণ CPython build-এ; Python ৩.১৪-এর free-threaded build-এ `sys.flags.thread_inherit_context` দিয়ে এটা বদলায়)।

তাই thread pool-এ কাজ পাঠাতে `contextvars.copy_context().run(fn, ...)` ব্যবহার করুন — `demo_job.py` এটাই করে।

### 8.4 Redaction কোথায় হয়

`RedactFilter` handler-এর filter। তাই এই handler দিয়ে যাওয়া সব record-এ প্রযোজ্য, যে logger থেকেই আসুক। Traceback-এর redaction formatter-এ হয়, কারণ traceback তৈরি হয় format-এর সময়।

**সীমা:**

- Regex শুধু পরিচিত রূপ ধরে: `key=value`, `Authorization:`, `scheme://user:pass@`।
- Exception object নিজে বদলায় না। তাই Sentry-র মতো tool সরাসরি exception পাঠালে secret সেখানে যেতে পারে।

> **Fedora-তে:** কোনো পার্থক্য নেই। systemd service-এ stderr সরাসরি journald-এ যায় (L01-14)। JSON লাইন `journalctl -o cat` দিয়ে পড়ে `jq`-তে পাঠানো যায়। Journald-এর নিজস্ব structured field চাইলে `systemd.journal` (python3-systemd package) ব্যবহার করুন।

## 9. Practical demonstration

Files: [`code/L05-07/logsetup.py`](code/L05-07/logsetup.py), [`demo_job.py`](code/L05-07/demo_job.py) (কৃত্রিম backup job; সব "secret" নকল), [`test_l05_07.py`](code/L05-07/test_l05_07.py)।

### 9.1 Text mode (মানুষের জন্য)

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-07
python3 demo_job.py; echo "exit=$?"
```

**আসল output** (traceback-এর মাঝের লাইন বাদ):

```text
2026-10-27T02:50:49Z INFO    [job-7f3a] ops: backup run started dbs=['orders', 'billing'] token=***
2026-10-27T02:50:49Z INFO    [job-7f3a] ops.backup: dumped orders db=orders size_mb=120
2026-10-27T02:50:49Z ERROR   [job-7f3a] ops: backup failed db=billing
Traceback (most recent call last):
  …
    raise ConnectionError("could not connect to postgres://backup:***@10.0.0.5/billing")
ConnectionError: could not connect to postgres://backup:***@10.0.0.5/billing
2026-10-27T02:50:49Z WARNING [job-7f3a] ops: password=*** found in legacy config, please rotate
2026-10-27T02:50:49Z INFO    [job-7f3a] ops: backup run finished failed=1 request=job-7f3a
failed=1
exit=1
```

- `ops.backup`-এর লাইন **অন্য thread থেকে** এসেছে, তবুও `[job-7f3a]` আছে (`copy_context`)।
- Traceback-এ **source code-এর লাইনেও** password `***` হয়েছে — traceback source লাইন দেখায়, আর সেখানে নকল DSN ছিল।
- `token=***` (extra field), `password=***` (message)।
- `debug` লাইন নেই (level INFO)।
- শেষ লাইন `failed=1` stdout-এ, বাকি সব stderr-এ।

### 9.2 JSON mode (machine-এর জন্য)

```bash
python3 demo_job.py --json 2>&1 >/dev/null | head -3
python3 demo_job.py --json 2>&1 >/dev/null | jq -c 'select(.level=="error") | {db, exc_type}'
```

**আসল output (প্রথম দুই লাইন, এবং তৃতীয়টি সংক্ষেপিত):**

```text
{"ts": "2026-10-27T02:50:32.168+00:00", "level": "info", "logger": "ops", "msg": "backup run started", "request_id": "job-7f3a", "dbs": ["orders", "billing"], "token": "***"}
{"ts": "2026-10-27T02:50:32.169+00:00", "level": "info", "logger": "ops.backup", "msg": "dumped orders", "request_id": "job-7f3a", "db": "orders", "size_mb": 120}
{"ts": "…", "level": "error", "logger": "ops", "msg": "backup failed", "request_id": "job-7f3a", "db": "billing", "exc_type": "ConnectionError", "exc": "Traceback (most recent call last):\n  File …"}
```

- পুরো traceback `exc` field-এর ভেতরে, **একটিই লাইনে** (`\n` escape করা)। Multi-line traceback log collector-এ আলাদা আলাদা "log" হয়ে ছড়িয়ে যায় না।
- `jq`-এর লাইনটি এই machine-এ চালানো হয়নি (jq নেই) — উদাহরণ মাত্র।

### 9.3 Thread-এ request id — আসল পরীক্ষা

```python
rid.set("req-42")
threading.Thread(target=...rid.get())             → '-'
ThreadPoolExecutor().submit(rid.get)              → '-'
ThreadPoolExecutor().submit(copy_context().run, rid.get) → 'req-42'
```

**আসল output:**

```text
thread_inherit_context flag: 0
{'thread': '-', 'pool': '-', 'pool+copy_context': 'req-42'}
```

`copy_context` ছাড়া thread-এর সব log-এ request id হতো `-` — অর্থাৎ ঠিক যেখানে কাজটা ব্যর্থ হলো, সেখানেই correlation হারিয়ে যেত।

### 9.4 লেখার সময় যা ঠিক করা হয়েছে

- **Extra field-এর অবস্থান:** প্রথম সংস্করণে text mode-এ `db=billing` traceback-এর **শেষে** বসছিল, ফলে "কোন db?" খুঁজতে traceback পেরিয়ে যেতে হতো। এখন extra field প্রথম লাইনে, traceback পরে। এ নিয়ে test আছে।
- **Demo-র hack:** demo-তে প্রথমে `setup_logging.__globals__["logging"]`-এর মতো একটি অপ্রয়োজনীয় কৌশল ছিল; এখন সাধারণ `logging.getLogger("ops.backup")`। Child logger parent-এর handler আপনাআপনি ব্যবহার করে — এটাই hierarchy-র সুবিধা।

### 9.5 Test

```bash
python3 -m unittest -v
```

১০টি test:

- এক লাইনে এক JSON, UTC।
- Exception এক লাইনে।
- বন্ধ level-এ format হয় না (lazy)।
- দুবার setup-এ দ্বিগুণ লাইন নয়।
- Redaction-এর ৬টি রূপ (নিরীহ "keyboard" বদলায় না)।
- Extra field, nested dict ও traceback-এর redaction।
- Nested request context।
- Thread ও `copy_context`।
- Text mode-এ extra field-এর অবস্থান।
- `demo_job.py`: stdout/stderr ভাগ, সব লাইন JSON, একই request id, কোনো নকল secret নেই।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `_STD_ATTRS` | LogRecord-এর নিজস্ব field-এর তালিকা | বাকিগুলো = `extra` |
| `ContextFilter` | `request_id` যোগ | প্রতিটি লাইনে correlation |
| `RedactFilter` | `getMessage()` format করে redact, `args=None` | Format-এর পরে secret ধরা |
| `redact_value` (recursive) | Nested dict-এর key দেখে | `headers.Authorization` |
| URL pattern `(?=@)` | `user:pass@`-এর password | DSN, git URL |
| `JsonFormatter` — UTC, milliseconds | ISO-8601 | Time zone বিভ্রান্তি নেই, ক্রম ঠিক |
| `json.dumps(default=str)` | অজানা type-এ crash নয় | `Path`, `datetime` extra |
| `propagate=False` | Root-এ দ্বিতীয়বার নয় | দ্বিগুণ লাইন নয় |
| পুরোনো handler সরানো | Idempotent setup | Test ও reload-এ নিরাপদ |
| `request_context` + `reset(token)` | Nesting-এ আগের মান ফেরত | `with`-এর বাইরে পুরোনো id |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `demo_job.py` | সব লাইনে `[job-7f3a]`, `***`, exit ১ |
| `demo_job.py --json 2>/dev/null` | শুধু `failed=1` |
| `--json`-এর প্রতিটি stderr লাইন | বৈধ JSON |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| কোনো log দেখা যায় না | Level WARNING (default) | Logger-এর level ঠিক করুন |
| প্রতিটি লাইন দুবার | নিজের handler + root-এ propagate | `propagate=False` |
| `basicConfig` কাজ করে না | Root-এ আগে থেকে handler | নিজের logger, বা `basicConfig(force=True)` |
| Thread-এর log-এ request id `-` | নতুন thread খালি context পায় | `copy_context().run` |
| Traceback ৩০টি আলাদা log হয়ে গেছে | Multi-line text log | JSON-এ এক field |
| `jq: parse error` | stdout-এ log, বা mixed output | Log stderr-এ, ফল stdout-এ |
| Time ৬ ঘণ্টা ভুল | Local time, zone নেই | UTC + offset |
| Library debug-এ token লিখছে | Root DEBUG | `logging.getLogger("urllib3").setLevel("WARNING")` |
| Log disk ভরিয়ে দিয়েছে | Loop-এ log, rotation নেই | Sampling; logrotate/journald limit (L01-14) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Secret log-এ পৌঁছাতে দেবেন না; redaction শুধু শেষ রক্ষাকবচ।
  - Personal data (email, IP) log করার আগে নীতি দেখুন (GDPR — Module 19)।
  - Log-এ ব্যবহারকারীর input থাকলে **log injection** সম্ভব — নকল লাইন (`\n` দিয়ে)। JSON format এটা আটকায়, কারণ `\n` escape হয়ে যায়।
  - Log-এর access ও retention নিয়ন্ত্রণ করুন।
- **Performance:**
  - `%`-style lazy formatting ব্যবহার করুন।
  - Hot loop-এ DEBUG log বন্ধ রাখলে খরচ প্রায় শূন্য।
  - খুব বেশি log হলে sampling বা rate limiting।
  - Disk/network ধীর হলে `QueueHandler` (আলাদা thread-এ লেখা)।
- **Cost:**
  - Log ingestion-এ সাধারণত প্রতি GB হিসাবে বিল হয় (CloudWatch, Datadog)। প্রতিটি request-এ ৫ KB-এর debug log মানে প্রতিদিন কয়েকশো GB হতে পারে।
  - Level, sampling ও retention cost নিয়ন্ত্রণের প্রধান হাতিয়ার (Module 17, 29)।

## 14. Hands-on exercise

1. `demo_job.py`-তে `copy_context` সরিয়ে দিন। কোন লাইনের request id বদলাল?
2. `RedactFilter`-এ AWS access key-র রূপ (`AKIA[0-9A-Z]{16}`) যোগ করুন, ও test লিখুন। কোন নিরীহ লেখা ভুলবশত ধরা পড়তে পারে?
3. `setup_logging`-এ `--log-file` বিকল্প যোগ করুন: file-এ JSON (DEBUG), console-এ text (INFO) — দুটি handler, ভিন্ন level।
4. Ubuntu-তে `demo_job.py --json`-কে একটি systemd-run unit হিসেবে চালান (`systemd-run --user --wait`), এবং `journalctl --user -o cat | jq` দিয়ে পড়ুন।
5. `QueueHandler` + `QueueListener` দিয়ে একটি ধীর handler (প্রতি লাইনে ১০০ ms `sleep`) আলাদা thread-এ সরান। Program-এর সময়ের পার্থক্য মাপুন।

## 15. Mini-project — Log level-এর runtime পরিবর্তন

`logsetup`-এ যোগ করুন:

- `SIGUSR1` পেলে level DEBUG ↔ INFO টগল, এবং পরিবর্তনটি নিজেই log করা।
- প্রতিটি `request_context`-এর শেষে `duration_ms` সহ একটি "request finished" লাইন।
- শেষে একটি সারাংশ: কোন level-এ কয়টি লাইন।

L05-13-এর TaskFlow API এটা ব্যবহার করবে, এবং Module 17-এ এই log Loki-তে পাঠানো হবে।

## 16. Interview প্রশ্ন

1. Structured logging কী, এবং কেন দরকার?
2. Correlation/request id কী? Distributed system-এ কীভাবে পাঠানো হয়?
3. Log-এ secret যাওয়া কীভাবে ঠেকাবেন?
4. `log.info(f"...")` বনাম `log.info("...%s", x)` — পার্থক্য কী?
5. Log কেন stderr-এ লেখা উচিত?
6. Log-এর cost কীভাবে নিয়ন্ত্রণ করবেন?

## 17. Self-assessment প্রশ্ন

1. হাসপাতাল analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ password দুটি পথে log-এ গিয়েছিল — কোন দুটি?
3. Thread pool-এ request id কেন হারায়, এবং সমাধান কী?
4. JSON log-এ traceback এক লাইনে থাকার সুবিধা কী?
5. দ্বিগুণ log লাইনের কারণ কী?

## 18. সংক্ষিপ্ত সারাংশ

- Named logger, `%`-style message, `extra` field; production-এ JSON, terminal-এ text।
- UTC সময়, request id (`contextvars`; thread-এ `copy_context`)।
- `log.exception` — traceback এক field-এ।
- Redaction message, extra ও traceback-এ — কিন্তু আসল সুরক্ষা হলো secret log-এ না আনা।
- Log stderr-এ, ফল stdout-এ; দ্বিগুণ handler এড়ান।

## 19. Completion checklist

- [ ] Text ও JSON দুই mode-এ `demo_job.py` চালিয়েছি
- [ ] Thread-এ request id হারানো ও `copy_context` দিয়ে সমাধান দেখেছি
- [ ] Redaction-এর সীমা ব্যাখ্যা করতে পারি
- [ ] `python3 -m unittest -v`-এ ১০টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `logging`: https://docs.python.org/3/library/logging.html
- Python — Logging HOWTO: https://docs.python.org/3/howto/logging.html
- Python — Logging Cookbook: https://docs.python.org/3/howto/logging-cookbook.html
- Python — `contextvars`: https://docs.python.org/3/library/contextvars.html
- OWASP — Logging Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Logging_Cheat_Sheet.html
- JSON Lines: https://jsonlines.org/

---

**পরের lesson:** L05-08 — argparse দিয়ে CLI tool
