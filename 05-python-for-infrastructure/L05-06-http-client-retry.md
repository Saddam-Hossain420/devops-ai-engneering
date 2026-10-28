# L05-06 — HTTP client ও API: timeout, retry, error handling

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-04 — subprocess](L05-04-subprocess-safely.md), [L02-07 — HTTP](../02-computer-networking/L02-07-http.md) |
| **Label** | — |
| **Tested** | `http_client.py` + `flaky_server.py`: ১১টি test পাস (Python 3.14.5, Windows)। সব request গেছে **শুধু 127.0.0.1-এর local server-এ**, internet-এ কোনো request যায়নি। আসলে চালানো হয়েছে: 503-এর retry, 429 + Retry-After, 404, timeout, বন্ধ port, এবং Idempotency-Key। **দুটি আসল bug ধরা পড়েছে** (Section 9.4)। Linux-এর connection-refused আচরণ **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- HTTP call-এ **timeout সবসময়** — না দিলে কী হয়।
- কোন ব্যর্থতায় retry করবেন (503, 429, connection error), কোনটায় কখনো নয় (400, 401, 404)।
- **Exponential backoff + full jitter** — কেন শুধু "১ সেকেন্ড পরে আবার" বিপজ্জনক।
- `Retry-After` header মানা।
- **Idempotency:** POST retry করলে দুটি order হতে পারে; `Idempotency-Key` দিয়ে সমাধান।
- stdlib `urllib` দিয়ে সব কিছু, এবং `requests`-এর সাথে তুলনা।
- Test-এর জন্য ইচ্ছাকৃতভাবে ভুল আচরণ করা local server।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Ops tool সারাক্ষণ API ডাকে: cloud provider, monitoring, Slack webhook, internal service। Network কখনো পুরো নির্ভরযোগ্য নয়।

- **Timeout না দেওয়া:** `urllib.request.urlopen(url)` default-এ socket-এর global timeout ব্যবহার করে, যা সাধারণত **অসীম**। একটি আটকে যাওয়া server আপনার deploy script-কে ঘণ্টার পর ঘণ্টা ধরে রাখে।
- **Retry না করা:** এক সেকেন্ডের 503-এ পুরো deploy ব্যর্থ।
- **ভুলভাবে retry করা:**
  - ১০০০টি client একসাথে ব্যর্থ হয়ে প্রতি সেকেন্ডে একসাথে retry করে। সবে সেরে ওঠা server আবার পড়ে যায় (**retry storm / thundering herd**)।
  - POST retry করে দুবার charge করা হয়।

## 3. সহজ ভাষায় পরিচয়

| পরিস্থিতি | Retry? | কেন |
|---|---|---|
| Connection refused / reset, timeout | হ্যাঁ (idempotent হলে) | অস্থায়ী হতে পারে |
| 502, 503, 504 | হ্যাঁ | Gateway/server সাময়িক সমস্যা |
| 429 Too Many Requests | হ্যাঁ, `Retry-After` মেনে | Server বলছে "ধীরে" |
| 400, 401, 403, 404, 422 | **না** | আবার পাঠালেও একই ফল — আপনার request-এ ভুল |
| 500 | সাধারণত না (বা খুব সতর্কভাবে) | প্রায়ই bug, অস্থায়ী নয় |
| POST (Idempotency-Key ছাড়া) | **না** | দুবার কাজ হতে পারে |

```python
from http_client import request
r = request("https://api.example.com/v1/status", timeout=5, retries=3)
if r.ok:
    data = r.json()
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ব্যস্ত অফিসে ফোন করা

- **Timeout** = ৩০ সেকেন্ড রিং হলে ফোন রেখে দেওয়া — সারাদিন কানে ধরে বসে না থাকা।
- **Retry** = লাইন ব্যস্ত হলে আবার চেষ্টা করা।
- **Backoff** = প্রথমবার ১ মিনিট পরে, তারপর ২, তারপর ৪ — বারবার একটানা ফোন না করা।
- **Jitter** = সবাই ঠিক "১ মিনিট পরে" ফোন করলে আবার একসাথে লাইন ব্যস্ত হয়। তাই প্রত্যেকে ০–১ মিনিটের মধ্যে এলোমেলো সময়ে ফোন করেন।
- **Retry-After** = রিসেপশনিস্ট বললেন "১০ মিনিট পরে ফোন করুন" — তখন নিজের হিসাব নয়, তাঁর কথা মানা।
- **৪০৪** = "এই নামে কেউ এখানে কাজ করেন না" — বারবার ফোন করে লাভ নেই।

### Analogy কোথায় মেলে না

- ফোনে "হ্যালো" শুনলে বোঝেন কথা পৌঁছেছে। **HTTP-তে timeout মানে "জানি না":** request হয়তো server-এ পৌঁছে কাজ শেষ হয়েছে, শুধু response হারিয়েছে। তাই POST-এর timeout-এর পরে retry = হয়তো দ্বিতীয় order। ফোনে এই অনিশ্চয়তা নেই।
- ফোনে একজন মানুষ একবারে একটি কল করেন। **Software-এ হাজার client একই নিয়মে চলে** — একজনের ছোট "আবার চেষ্টা" হাজার গুণ হয়ে server-এ আঘাত করে। তাই jitter ব্যক্তির জন্য নয়, সমষ্টির জন্য।
- ফোনের retry-তে খরচ শুধু আপনার সময়। **Retry-এর স্তর গুণ হয়:** client ৩ বার × load balancer ৩ বার × service ৩ বার = database-এ ২৭টি request। Retry একটিমাত্র স্তরে রাখুন (Module 28-এর service mesh-এ আবার আসবে)।

## 5. Real-world engineering scenario — "Deploy script ৬ ঘণ্টা ঝুলে রইল"

**পরিস্থিতি:** Deploy script প্রতিটি নতুন instance-এর `/health` দেখে, তারপর load balancer-এ যোগ করে:

```python
resp = urllib.request.urlopen(f"http://{ip}:8080/health")        # timeout নেই
```

একটি instance-এর kernel-এ সমস্যা: TCP connection স্থাপন হয়, কিন্তু application কখনো উত্তর দেয় না। Script ছয় ঘণ্টা আটকে রইল (OS-এর TCP keepalive পর্যন্ত), deploy pipeline-ও আটকে রইল, এবং অন্য সব release থেমে গেল।

পরের সপ্তাহে কেউ "সমাধান" দিলেন `timeout=5`, এবং ব্যর্থ হলে `while True:` loop-এ প্রতি সেকেন্ডে retry। এক বিভ্রাটের পরে ৫০টি instance-এর script একসাথে health endpoint-এ চাপ দিল, ফলে সবে চালু হওয়া service আবার overload হলো।

**সঠিক পদ্ধতি:** timeout (connect ও read), সীমিত retry, exponential backoff + jitter, `Retry-After` মানা, এবং শেষে স্পষ্ট ব্যর্থতা (exit ২) যাতে pipeline এগোতে পারে বা rollback করতে পারে।

**শিক্ষা:** "ব্যর্থ হলে কী করব" প্রশ্নের তিনটি অংশ: কতক্ষণ অপেক্ষা (timeout), কতবার (retries), কত ফাঁকে (backoff + jitter)।

## 6. Diagram — retry-এর সিদ্ধান্ত

```text
 request(GET /flaky)
     │
     ├─ attempt 1 ──► 503 ─┐  retry যোগ্য? (status ∈ {429,502,503,504} ও method idempotent)
     │                     │      হ্যাঁ → Retry-After আছে? ── হ্যাঁ → সেই সময় (সীমার বেশি হলে থামো)
     │                     │                              └─ না  → random(0, min(cap, base·2^attempt))
     │   sleep 0.10s ◄─────┘
     ├─ attempt 2 ──► 503 ─► sleep 0.70s
     ├─ attempt 3 ──► 200 ✔  Response(status=200, attempts=3, history=[…])
     │
     ├─ 404 ───────────────► সাথে সাথে ফেরত (retry নয়)
     └─ timeout/refused ───► retry … শেষে RequestFailedError (exit 2)

 full jitter (base 0.5, cap 4):  attempt 0: 0–0.5s  1: 0–1s  2: 0–2s  3: 0–4s  4: 0–4s
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Timeout | সর্বোচ্চ অপেক্ষা; connect ও read আলাদা হতে পারে |
| Retry | ব্যর্থ request আবার পাঠানো |
| Exponential backoff | প্রতিবার অপেক্ষা দ্বিগুণ |
| Jitter | অপেক্ষায় এলোমেলোতা, যাতে client-রা একসাথে না ফেরে |
| Thundering herd / retry storm | একসাথে বিপুল retry-তে server আবার পড়ে যাওয়া |
| Idempotent | একবার বা বহুবার করলে একই ফল (GET, PUT, DELETE) |
| Idempotency key | Client-এর দেওয়া অনন্য ID; server duplicate চিনে আগের ফল ফেরত দেয় |
| `Retry-After` | Server-এর বলা অপেক্ষার সময় (সেকেন্ড বা তারিখ) |
| Circuit breaker | বারবার ব্যর্থ হলে কিছুক্ষণ request পাঠানোই বন্ধ (Module 18) |
| Retry budget | মোট request-এর সর্বোচ্চ কত শতাংশ retry হতে পারে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 `urlopen`-এর timeout

`timeout=` socket-এর প্রতিটি blocking operation-এ প্রযোজ্য — connect, এবং প্রতিটি read আলাদাভাবে। তাই এটা **মোট সময়ের সীমা নয়:** server প্রতি ৪ সেকেন্ডে এক byte পাঠালে ৫ সেকেন্ডের timeout কখনো ঘটবে না।

মোট সময়ের সীমা চাইলে deadline হিসাব করে প্রতিটি attempt-এ বাকি সময় দিন — এটি exercise ৩।

### 8.2 `HTTPError` একই সাথে exception ও response

4xx/5xx-এ `urlopen` `HTTPError` তোলে, কিন্তু সেটা একটা response-ও — `.code`, `.headers`, `.read()` আছে। এর ভেতরের connection **বন্ধ করতে হয়** (`with exc:`)। নইলে retry loop-এ connection জমে, এবং Python `ResourceWarning` দেয় (Section 9.4)।

### 8.3 Full jitter

AWS Architecture Blog-এর বিশ্লেষণ অনুযায়ী তিনটি কৌশলের তুলনা:

- **"Equal jitter":** অর্ধেক নির্দিষ্ট, অর্ধেক এলোমেলো।
- **"Decorrelated jitter":** আগের delay-এর ওপর ভিত্তি করে এলোমেলো।
- **"Full jitter":** `random(0, min(cap, base·2^n))`। মোট কাজ ও সময়ে সাধারণত ভালো, সহজও। এই tool সেটাই ব্যবহার করে।

### 8.4 Idempotency key

Client একটি অনন্য key (UUID) পাঠায়। Server প্রথমবার কাজ করে key-সহ ফল জমা রাখে; একই key আবার এলে **আবার কাজ না করে** জমা রাখা ফল ফেরত দেয়। Stripe-এর মতো payment API এভাবেই কাজ করে।

`flaky_server.py`-এর `/orders` এটাই অনুকরণ করে (Section 9.3)।

### 8.5 `urllib` বনাম `requests` / `httpx`

| | `urllib` (stdlib) | `requests` | `httpx` |
|---|---|---|---|
| Install | লাগে না | লাগে | লাগে |
| Connection pool | না | হ্যাঁ (`Session`) | হ্যাঁ |
| Retry | নিজে লিখতে হয় | `urllib3.Retry` adapter | transport retry (connect) |
| Async | না | না | হ্যাঁ |

ছোট ops script ও bootstrap tool-এর জন্য (যেখানে pip নেই) `urllib`। বড় application-এ `requests`/`httpx` — কিন্তু timeout ও retry-র নিয়ম একই।

> **Fedora-তে:** কোনো পার্থক্য নেই। Corporate proxy থাকলে `urllib` `HTTPS_PROXY`/`NO_PROXY` env var মানে — দুই distro-তেই।

## 9. Practical demonstration

Files: [`code/L05-06/http_client.py`](code/L05-06/http_client.py), [`flaky_server.py`](code/L05-06/flaky_server.py), [`test_l05_06.py`](code/L05-06/test_l05_06.py)।

### 9.1 Server চালু (terminal ১)

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-06
python3 flaky_server.py --port 8099          # শুধু 127.0.0.1-এ শোনে
```

### 9.2 Client (terminal ২) — আসল output

```bash
H=http://127.0.0.1:8099
python3 http_client.py $H/flaky --retries 4;  echo "exit=$?"
python3 http_client.py $H/ratelimit;           echo "exit=$?"
python3 http_client.py $H/notfound;            echo "exit=$?"
python3 http_client.py "$H/slow?s=3" --timeout 1 --retries 1; echo "exit=$?"
python3 http_client.py http://127.0.0.1:1/health --retries 2 --timeout 1; echo "exit=$?"
```

```text
  attempt 1: HTTP 503, retry in 0.10s
  attempt 2: HTTP 503, retry in 0.70s
HTTP 200 after 3 attempt(s) in 0.85s
{"status": "ok", "call": 3}
exit=0

  attempt 1: HTTP 429, retry in 1.00s
HTTP 200 after 2 attempt(s) in 1.043s
exit=0

HTTP 404 after 1 attempt(s) in 0.03s
{"error": "not found"}
exit=1

  attempt 1: TimeoutError: timed out, retry in 0.29s
  attempt 2: TimeoutError: timed out
error: GET http://127.0.0.1:8099/slow?s=3 failed after 2 attempt(s): timed out
exit=2

  attempt 1: TimeoutError: timed out, retry in 0.16s
  attempt 2: TimeoutError: timed out, retry in 0.67s
  attempt 3: TimeoutError: timed out
error: GET http://127.0.0.1:1/health failed after 3 attempt(s): timed out
exit=2
```

পর্যবেক্ষণ:

- **503:** delay ০.১০ ও ০.৭০ — এলোমেলো, কিন্তু সীমার ভেতরে (০–০.৫, ০–১.০)। আপনার চালানোয় সংখ্যা ভিন্ন হবে।
- **429:** ঠিক ১.০০ s — server-এর `Retry-After: 1`, jitter নয়।
- **404:** একবারই, retry নেই; exit ১ (HTTP error) বনাম exit ২ (network)।
- **বন্ধ port-এ "timed out", "refused" নয়।** Windows-এ বন্ধ port-এ `ConnectionRefusedError` আসতে আলাদাভাবে মাপা সময় লেগেছে **২.০৪ s** (Windows প্রত্যাখ্যানের পরেও কয়েকবার SYN পাঠায়)। তাই ১ s timeout আগে শেষ হলো। Linux-এ সাধারণত সাথে সাথে `ConnectionRefusedError` আসে (চালানো হয়নি)। একই code, ভিন্ন OS, ভিন্ন error — debugging-এর সময় মনে রাখুন।

### 9.3 Idempotency-Key — আসল output

একই server-এ তিনবার key ছাড়া POST, তারপর তিনবার একই key দিয়ে:

```text
no key: {'id': 1}
no key: {'id': 2}
no key: {'id': 3}
same key: {'id': 4}
same key: {'id': 4}
same key: {'id': 4}
```

Key ছাড়া প্রতিটি "retry" নতুন order বানিয়েছে। Key-সহ, server একটিই বানিয়েছে।

### 9.4 লেখার সময় ধরা পড়া দুটি bug

1. **Connection leak:** প্রথম test run-এ এল `ResourceWarning: Implicitly cleaning up <HTTPError 503: 'Service Unavailable'>`। Retry-র আগে error response-এর connection বন্ধ করা হচ্ছিল না। দীর্ঘ চলা process-এ (monitoring daemon) এভাবে file descriptor শেষ হয়ে যায়। সমাধান: `with exc:`। এখন `python3 -W error::ResourceWarning -m unittest` পরিষ্কার।
2. **ruff N818 ও UP041:**
   - Exception-এর নাম `Error` দিয়ে শেষ হওয়া উচিত → `RequestFailedError`।
   - `socket.timeout` Python ৩.১০ থেকে `TimeoutError`-এর alias মাত্র, তাই বাদ।

### 9.5 Test

```bash
python3 -m unittest -v
```

১১টি test, প্রতিটি নিজের local server-এ (OS-নির্বাচিত port):

- Retry-তে সফল; সীমা শেষে শেষ response।
- `Retry-After` মানা; খুব দীর্ঘ `Retry-After`-এ অপেক্ষা না করা।
- 404 retry নয়; key ছাড়া POST retry নয়।
- Idempotency key।
- Timeout (মোট < ১.৮ s)।
- বন্ধ port।
- Backoff-এর সীমা।
- `Retry-After`-এর দুই format।

Backoff-এর `sleep` inject করা হয়, তাই test আসলে ঘুমায় না। মোট সময় ~৭ s, যার বেশিরভাগ Windows-এর বন্ধ-port-এর ২ s × ৩।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `IDEMPOTENT`, `may_retry` | POST-এ retry নয় (key ছাড়া) | Duplicate কাজ এড়ানো |
| `RETRY_STATUS` | 429/502/503/504 | অস্থায়ী ব্যর্থতা |
| `with exc: exc.read()` | Error response পড়ে বন্ধ | Connection leak নয় |
| `retry_after_seconds` | সেকেন্ড বা HTTP তারিখ | RFC 9110-এর দুই রূপ |
| `max_retry_after` | খুব দীর্ঘ অপেক্ষা নয় | "১ ঘণ্টা পরে আসুন"-এ script ঝুলবে না |
| `backoff_delay(..., rng)` | Full jitter | RNG inject করে test |
| `sleep=` parameter | Inject করা যায় | Test দ্রুত, নির্ভরযোগ্য |
| `history` | প্রতিটি চেষ্টার বিবরণ | Log ও debugging |
| `User-Agent` | নিজের পরিচয় | Server log-এ কে ডাকছে বোঝা যায় |
| Exit ০/১/২ | সফল / HTTP error / network | Pipeline আলাদা সিদ্ধান্ত নিতে পারে |
| `serve(0)` | OS-এর খালি port | সমান্তরাল test-এ port সংঘাত নেই |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `/flaky --retries 4` | ২টি 503-এর পরে 200, exit ০ |
| `/ratelimit` | ১.০০ s অপেক্ষা, তারপর 200 |
| `/notfound` | ১ attempt, exit ১ |
| `/slow?s=3 --timeout 1` | `RequestFailedError`, exit ২ |
| `python3 -m unittest -v` | `Ran 11 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Script অনির্দিষ্টকাল ঝুলে থাকে | Timeout নেই | প্রতিটি call-এ `timeout=` |
| Timeout সত্ত্বেও দীর্ঘ সময় | Timeout প্রতি-read, মোট নয় | Deadline হিসাব |
| Duplicate order/charge | POST retry | Idempotency-Key, বা POST retry নয় |
| বিভ্রাটের পরে server আবার পড়ে যায় | Jitter ছাড়া retry | Full jitter, সীমিত retry |
| 401-এ বারবার চেষ্টা, account lock | 4xx retry | 4xx (429 ছাড়া) retry নয় |
| `ResourceWarning` / fd শেষ | Error response বন্ধ নয় | `with exc:` |
| `CERTIFICATE_VERIFY_FAILED` | CA bundle নেই বা proxy | সঠিক CA; **verify বন্ধ নয়** |
| Proxy-র পেছনে কাজ করে না | `HTTPS_PROXY` | Env var ও `NO_PROXY` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - TLS যাচাই কখনো বন্ধ নয় (`ssl._create_unverified_context` নয়)।
  - Token header-এ পাঠান, URL-এ নয় — URL log-এ থাকে।
  - `history`/log-এ `Authorization` header লিখবেন না।
  - বাইরের URL নিলে SSRF-এর ঝুঁকি: `169.254.169.254` (cloud metadata) ও internal address নিষেধ করুন (Module 19)।
  - Response-এর আকারের সীমা দিন।
- **Performance:**
  - `urllib` প্রতিবার নতুন connection খোলে (TLS handshake খরচ)। অনেক call হলে `requests.Session`/`httpx.Client`-এর connection pool ব্যবহার করুন।
  - সমান্তরাল call-এ thread pool বা async (L05-12)।
- **Cost:**
  - Cloud API-তে rate limit ও প্রতি-request খরচ থাকতে পারে; retry storm বিল বাড়ায়।
  - NAT gateway দিয়ে বাইরের traffic-এর data processing খরচ (Module 08)।
  - Retry budget রাখুন।

## 14. Hands-on exercise

1. `flaky_server.py`-এ `/flaky`-কে ১০ বার ব্যর্থ করুন, এবং ১০টি client একসাথে চালান (`xargs -P 10`)। Jitter থাকা ও না থাকা অবস্থায় server log-এ প্রতি সেকেন্ডের request গুনুন।
2. Ubuntu-তে বন্ধ port-এ `http_client.py` চালান। Error-এর ধরন ও সময় Windows-এর সাথে তুলনা করুন।
3. `request`-এ `deadline_s` (মোট সময়ের সীমা) যোগ করুন: প্রতিটি attempt-এর timeout = বাকি সময়ের কম।
4. একটি সাধারণ circuit breaker লিখুন: পরপর ৫ বার ব্যর্থ হলে ৩০ s কোনো request নয়, তারপর একটি "half-open" চেষ্টা।
5. `requests` + `urllib3.util.Retry` দিয়ে একই আচরণ লিখুন (venv-এ)। কোন parameter কোনটার সমতুল্য?

## 15. Mini-project — Webhook notifier

`notify.py --webhook-url-file /etc/notify/url "Deploy finished"`:

- Webhook URL file থেকে পড়া (L05-10 — URL নিজেই secret)।
- JSON POST, `Idempotency-Key` = message-এর hash + মিনিট।
- 429-এ `Retry-After`; ব্যর্থ হলে local file-এ queue রাখা, এবং পরের run-এ আবার পাঠানো।
- কখনো URL log-এ নয়।

Module 17-এর alerting-এ এটা ব্যবহার হবে।

## 16. Interview প্রশ্ন

1. কোন HTTP status-এ retry করবেন, কোনটায় করবেন না? কেন?
2. Exponential backoff ও jitter কী? Jitter না দিলে কী হয়?
3. POST request retry করা কেন ঝুঁকিপূর্ণ? Idempotency key কীভাবে কাজ করে?
4. Timeout না দিলে কী হতে পারে? Connect ও read timeout-এর পার্থক্য।
5. Retry কয়টি স্তরে রাখা উচিত? Retry amplification কী?
6. Circuit breaker কী?

## 17. Self-assessment প্রশ্ন

1. ফোন analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর দুটি ভুল "সমাধান" কী ছিল?
3. 429-এ delay ঠিক ১.০০ কেন, এলোমেলো নয়?
4. Windows-এ বন্ধ port-এ "timed out" কেন এল?
5. `ResourceWarning` bug দীর্ঘ চলা process-এ কী ক্ষতি করত?

## 18. সংক্ষিপ্ত সারাংশ

- প্রতিটি HTTP call-এ timeout।
- Retry শুধু অস্থায়ী ব্যর্থতায় (429/502/503/504, network) ও idempotent request-এ।
- Exponential backoff + full jitter; `Retry-After` মানুন; সীমিত চেষ্টা।
- POST retry-র জন্য Idempotency-Key।
- Error response-ও বন্ধ করুন; log-এ secret নয়।

## 19. Completion checklist

- [ ] Local flaky server-এ পাঁচটি পরিস্থিতি চালিয়ে দেখেছি
- [ ] Idempotency-Key-এর পার্থক্য দেখেছি
- [ ] Ubuntu-তে বন্ধ port-এর আচরণ তুলনা করেছি
- [ ] `python3 -m unittest -v`-এ ১১টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `urllib.request`: https://docs.python.org/3/library/urllib.request.html
- Python — `http.server`: https://docs.python.org/3/library/http.server.html
- RFC 9110 — HTTP Semantics (Retry-After, idempotent methods): https://www.rfc-editor.org/rfc/rfc9110
- RFC 6585 — 429 Too Many Requests: https://www.rfc-editor.org/rfc/rfc6585
- AWS Architecture Blog — Exponential Backoff And Jitter: https://aws.amazon.com/blogs/architecture/exponential-backoff-and-jitter/
- Google SRE Book — Handling Overload: https://sre.google/sre-book/handling-overload/
- Requests documentation: https://requests.readthedocs.io/

---

**পরের lesson:** L05-07 — Logging, structured log ও exception
