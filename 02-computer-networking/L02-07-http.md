# L02-07 — HTTP/1.1, HTTP/2 ও HTTP/3

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L02-05 — TCP, UDP, socket](L02-05-tcp-udp-sockets.md), [L02-06 — DNS](L02-06-dns.md) |
| **Label** | — |
| **Tested** | `http_raw.py`: ৭টি test পাস — loopback-এ Python `http.server` দিয়ে keep-alive, chunked, redirect, 404, HEAD ও CLI (Python 3.14, Windows)। `demo` ও **`http://example.com/`-এ আসল request** চালানো হয়েছে (২০২৬-১০-২৬) — output Section 9-এ। `curl` দিয়ে HTTP/2 ও HTTP/3 যাচাই **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- HTTP message-এর গঠন: request line, header, খালি লাইন, body।
- Method, status code, গুরুত্বপূর্ণ header (Host, Content-Length, Transfer-Encoding, Connection, Cache-Control, Location)।
- Body-র শেষ কীভাবে বোঝা যায়: **Content-Length**, **chunked**, connection বন্ধ।
- **Keep-alive** — একটি TCP connection-এ বহু request।
- HTTP/1.1 → HTTP/2 (binary, multiplexing) → HTTP/3 (QUIC, UDP-র উপর) — কোন সমস্যা কে সমাধান করে।
- Python দিয়ে socket-এ raw HTTP পাঠিয়ে protocol নিজের চোখে দেখা।
- `curl -v` দিয়ে diagnosis।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

প্রায় প্রতিটি service-to-service কথোপকথন, API, health check, webhook, container registry, Kubernetes API server, LLM inference endpoint — সব HTTP-র উপর। Incident-এ যা দেখবেন:

- `502 Bad Gateway`, `504 Gateway Timeout` — proxy ও backend-এর মধ্যে কী হলো?
- Load balancer health check ব্যর্থ — কোন status code, কোন path?
- Redirect loop, ভুল `Host` header-এ ভুল site।
- Keep-alive timeout-এর অমিলে মাঝে মাঝে `connection reset` (L02-05-এর কথা)।
- Streaming response (LLM token streaming = chunked বা SSE) proxy-তে আটকে যাওয়া।

Protocol না বুঝলে এগুলো "রহস্যময়"; বুঝলে `curl -v` দেখেই অর্ধেক উত্তর।

## 3. সহজ ভাষায় পরিচয়

HTTP = **request–response** protocol, text-ভিত্তিক (HTTP/1.1), সাধারণত TCP-র উপর (port ৮০; TLS সহ ৪৪৩ = HTTPS, L02-08)।

```text
GET /hello HTTP/1.1          ← request line: method, path, version
Host: api.example.com        ← header (নাম: মান)
User-Agent: curl/8.5.0
                             ← খালি লাইন (\r\n) = header শেষ
                             ← body (GET-এ সাধারণত নেই)

HTTP/1.1 200 OK              ← status line
Content-Type: text/plain
Content-Length: 6
                             ← খালি লাইন
hello                        ← body (ঠিক ৬ byte)
```

**Method:**

| Method | অর্থ | Safe? | Idempotent? |
|---|---|---|---|
| GET | পড়া | হ্যাঁ | হ্যাঁ |
| HEAD | GET-এর মতো, body ছাড়া | হ্যাঁ | হ্যাঁ |
| POST | তৈরি/কাজ করানো | না | **না** |
| PUT | পুরোটা প্রতিস্থাপন | না | হ্যাঁ |
| PATCH | আংশিক পরিবর্তন | না | না (সাধারণত) |
| DELETE | মোছা | না | হ্যাঁ |

**Idempotent** = একাধিকবার করলেও ফল একই — **retry নিরাপদ কিনা** তা নির্ধারণ করে (Module 15, 20)।

**Status code শ্রেণি:** `1xx` তথ্য, `2xx` সফল, `3xx` redirect, `4xx` client-এর ভুল, `5xx` server-এর ভুল।

| Code | কখন দেখবেন |
|---|---|
| 200 / 201 / 204 | OK / তৈরি হয়েছে / body নেই |
| 301 / 302 / 304 | স্থায়ী / অস্থায়ী redirect / cache-এরটা এখনো বৈধ |
| 400 / 401 / 403 / 404 | ভুল request / পরিচয় দাও / অনুমতি নেই / নেই |
| 429 | Rate limit — ধীরে |
| 500 | Application crash/exception |
| 502 | Proxy backend থেকে **অবৈধ/কোনো উত্তর পায়নি** (backend বন্ধ, connection refused) |
| 503 | Service সাময়িক অনুপলব্ধ (overload, maintenance, কোনো healthy backend নেই) |
| 504 | Proxy backend-এর উত্তরের **অপেক্ষায় timeout** |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্তোরাঁয় অর্ডার

- **Request** = অর্ডার slip: কী চাই (method + path), কোন টেবিল (Host), বিশেষ নির্দেশ (header), সাথে কিছু দিলে (body)।
- **Response** = খাবার সহ রসিদ: "পরিবেশিত" (200), "এই খাবার নেই" (404), "রান্নাঘরে আগুন" (500), "ওয়েটার রান্নাঘর থেকে কিছু আনতে পারেনি" (502), "রান্নাঘর অনেকক্ষণ চুপ" (504)।
- **Keep-alive** = একই ওয়েটারকে বারবার অর্ডার — প্রতিবার নতুন ওয়েটার ডাকতে হয় না (TCP handshake বাঁচে)।
- **HTTP/1.1-এর সমস্যা:** একজন ওয়েটার একসাথে একটাই অর্ডার নিয়ে যান — আগেরটা না এলে পরেরটা নয় (head-of-line blocking)। **HTTP/2** = একই ওয়েটার একসাথে অনেক অর্ডার নেন, যেটা আগে হয় সেটা আগে আনেন।

### Analogy কোথায় মেলে না

- ওয়েটার মনে রাখেন আপনি কে। HTTP **stateless** — প্রতিটি request স্বাধীন; "আপনি কে" প্রতিবার cookie/token দিয়ে জানাতে হয়।
- HTTP/2-এও সব অর্ডার একটি TCP connection-এ — একটি packet হারালে TCP **সব** stream থামিয়ে রাখে (TCP-স্তরের head-of-line blocking)। এই সমস্যার জন্যই **HTTP/3 UDP-র উপর QUIC** ব্যবহার করে — যেখানে প্রতিটি stream-এর loss স্বাধীন।

## 5. Real-world engineering scenario — মাঝে মাঝে 502

**পরিস্থিতি:** Nginx (reverse proxy) → Python backend (Gunicorn)। Traffic কম থাকার সময় দিনে কয়েকবার এলোমেলো `502 Bad Gateway`। Log-এ: `upstream prematurely closed connection` / `connection reset by peer`।

**Diagnosis:**

1. 502 = proxy backend থেকে বৈধ উত্তর পায়নি। Backend crash? না — একই সময়ে অন্য request ঠিক আছে।
2. Pattern: idle সময়ের পরের **প্রথম** request-এ বেশি।
3. Nginx upstream keep-alive connection pool রাখে (idle timeout ৬০ সেকেন্ড)। Backend-এর keep-alive timeout **৫ সেকেন্ড**।
4. ঘটনা: backend ৫ সেকেন্ড পরে idle connection বন্ধ করে (FIN পাঠায়)। ঠিক সেই মুহূর্তে Nginx পুরোনো connection-এ নতুন request পাঠায় → reset → 502। (L02-05-এর connection lifecycle।)

**সমাধান:** **upstream (backend)-এর keep-alive timeout proxy-র চেয়ে বেশি** রাখুন, যেন সবসময় proxy আগে বন্ধ করে। যেমন backend ৬৫ সেকেন্ড, proxy ৬০। একই নিয়ম cloud load balancer → backend-এ (ALB-এর idle timeout default ৬০ সেকেন্ড; backend-এর তার চেয়ে বেশি রাখার পরামর্শ AWS documentation-এ আছে)।

**শিক্ষা:** HTTP-র অনেক "এলোমেলো" error আসলে নিচের TCP connection-এর জীবনচক্র। Status code-কে যে স্তর তৈরি করেছে (backend নাকি proxy) সেটা আগে বের করুন — response-এর `Server` header ও proxy log এখানে কাজে লাগে।

## 6. Diagram — তিন প্রজন্ম

```text
HTTP/1.1  (text, TCP)               HTTP/2  (binary frames, TCP)          HTTP/3  (QUIC, UDP)
┌──────────────────────┐            ┌──────────────────────┐              ┌──────────────────────┐
│ req1 ──────► resp1   │            │ stream1 ▓▓  ▓▓       │              │ stream1 ▓▓  ▓▓       │
│ req2 ──────► resp2   │ একটার পর   │ stream3   ▓▓  ▓▓     │ একসাথে,      │ stream3   ▓▓  ▓▓     │ stream-এর loss
│ (বা ৬টি connection)  │ একটা       │ stream5 ▓   ▓▓       │ interleaved  │ stream5 ▓   ▓▓       │ স্বাধীন
├──────────────────────┤            ├──────────────────────┤              ├──────────────────────┤
│ TLS (ঐচ্ছিক)         │            │ TLS (কার্যত বাধ্যতামূলক) │            │ QUIC (TLS 1.3 অন্তর্ভুক্ত) │
├──────────────────────┤            ├──────────────────────┤              ├──────────────────────┤
│ TCP                  │            │ TCP — একটি loss = সব │              │ UDP                  │
└──────────────────────┘            │ stream থামে          │              └──────────────────────┘
                                    └──────────────────────┘
Header: plain text, পুনরাবৃত্ত        HPACK compression                      QPACK compression
Connection setup: TCP + TLS          TCP + TLS                              ১ RTT (বা 0-RTT resume)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Request / status line | প্রথম লাইন — method/path/version বা version/code/reason |
| Header | `নাম: মান` metadata; নাম case-insensitive |
| Host header | একই IP-তে বহু site (virtual hosting) — HTTP/1.1-এ বাধ্যতামূলক |
| Content-Length | Body কত byte |
| Transfer-Encoding: chunked | আগে আকার না জেনে টুকরো টুকরো পাঠানো (streaming) |
| Keep-alive / persistent connection | একটি TCP connection-এ বহু request |
| Idempotent | বারবার করলে একই ফল — retry নিরাপদ |
| Reverse proxy | Client-এর সামনে বসে backend-এ forward করে (Nginx, Envoy, ALB) |
| Head-of-line blocking | সামনেরটা আটকে থাকলে পেছনের সবাই আটকে |
| Multiplexing | একই connection-এ একসাথে বহু stream |
| ALPN | TLS handshake-এ কোন HTTP version চলবে তার আলোচনা |
| QUIC | UDP-ভিত্তিক transport — HTTP/3-এর ভিত্তি |
| `Alt-Svc` | "আমি অন্য protocol-এও (যেমন h3) আছি" ঘোষণা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Body কোথায় শেষ?

TCP একটি byte stream (L02-05) — message-এর সীমানা নেই। HTTP/1.1 তিন উপায়ে বলে দেয়:

1. **`Content-Length: N`** — ঠিক N byte পড়ো।
2. **`Transfer-Encoding: chunked`** — প্রতিটি টুকরো `<hex আকার>\r\n<data>\r\n`, শেষে `0\r\n\r\n`। Server-কে আগে মোট আকার জানতে হয় না — streaming, বড় file, LLM token stream।
3. **কোনোটিই নেই** — connection বন্ধ হলে body শেষ (HTTP/1.0 শৈলী; keep-alive অসম্ভব)।

ব্যতিক্রম: `HEAD`-এর উত্তর, `204`, `304`, `1xx`-এ **কখনো body থাকে না**, Content-Length থাকলেও। এটি ভুল বুঝলে parser পরের response-এর byte body হিসেবে পড়ে ফেলে।

> নিরাপত্তা: Content-Length ও chunked দুটোই থাকলে proxy ও backend ভিন্নভাবে ব্যাখ্যা করতে পারে — **HTTP request smuggling** আক্রমণের মূল। RFC 9112 বলে chunked প্রাধান্য পায় এবং এমন request সন্দেহজনক।

### 8.2 Keep-alive

HTTP/1.1-এ connection default-এ খোলা থাকে (`Connection: close` না বললে)। লাভ: TCP handshake (১ RTT) ও TLS handshake (১–২ RTT) প্রতিবার বাঁচে। দুই পক্ষেরই idle timeout থাকে — Section 5-এর সমস্যা এখান থেকে।

### 8.3 HTTP/2 ও HTTP/3

- **HTTP/2:** একই অর্থ (method, header, status), কিন্তু binary frame-এ। এক connection-এ বহু stream; header compression। Browser-এ কার্যত শুধু TLS-এর উপর (ALPN `h2`)। gRPC HTTP/2-এর উপর (Module 15)।
- **HTTP/3:** QUIC (UDP ৪৪৩)। দ্রুত connection setup, stream-ভিত্তিক loss recovery, network বদলালেও (Wi-Fi → mobile) connection টিকে থাকে (connection ID)। Server `Alt-Svc: h3=":443"` header দিয়ে জানায়; client পরের বার চেষ্টা করে। **Firewall-এ UDP ৪৪৩ বন্ধ থাকলে চুপচাপ HTTP/2-এ ফিরে যায়।**

Application-এর দৃষ্টিতে তিনটিই "HTTP"; পার্থক্য transport ও performance-এ।

## 9. Practical demonstration

File: [`code/L02-07/http_raw.py`](code/L02-07/http_raw.py)

### 9.1 Local demo — network ছাড়া

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-07
python3 http_raw.py demo
```

**আসল output (সংক্ষেপিত; port ও Date প্রতিবার ভিন্ন):**

```text
>>> sent
GET /hello HTTP/1.1\r\n
Host: 127.0.0.1:56740\r\n
User-Agent: http_raw/1.0\r\n
\r\n
<<< HTTP/1.1 200 OK
    Server: BaseHTTP/0.6 Python/3.14.5
    Date: Mon, 26 Oct 2026 15:46:59 GMT
    Content-Type: text/plain; charset=utf-8
    Content-Length: 6
    body (6 bytes): b'hello\n'

>>> sent
GET /chunked HTTP/1.1\r\n
...
<<< HTTP/1.1 200 OK
    ...
    Transfer-Encoding: chunked
    body (19 bytes): b'line 1\nline 2\ndone\n'

...
<<< HTTP/1.1 301 Moved Permanently
    ...
    Location: /hello

>>> sent
POST /hello HTTP/1.1\r\n
Host: 127.0.0.1:53285\r\n
User-Agent: http_raw/1.0\r\n
Content-Length: 10\r\n
\r\n
name=rahim
<<< HTTP/1.1 201 Created
    ...
    body (13 bytes): b'got 10 bytes\n'

...
<<< HTTP/1.1 404 Not Found

all 5 requests reused ONE TCP connection (local port 56741)
```

**পর্যবেক্ষণ:**

- প্রতিটি লাইন `\r\n`-এ শেষ; header-এর পরে একটি খালি `\r\n`।
- `/chunked`-এ কোনো Content-Length নেই — parser chunk-গুলো জোড়া দিয়ে ১৯ byte পেয়েছে।
- ৫টি request **একটিই** TCP connection-এ (একই local port) — keep-alive।
- 301-এর উত্তরে `Location` — client নিজে পরের request করবে (curl-এ `-L`)।

### 9.2 Internet-এর আসল server

```bash
python3 http_raw.py get http://example.com/ --show-raw
```

**২০২৬-১০-২৬-এ আসলে চালিয়ে পাওয়া output (সংক্ষেপিত):**

```text
>>> sent
GET / HTTP/1.1\r\n
Host: example.com\r\n
User-Agent: http_raw/1.0\r\n
Connection: close\r\n
\r\n
<<< HTTP/1.1 200 OK
    Content-Type: text/html; charset=utf-8
    Transfer-Encoding: chunked
    Connection: close
    Server: cloudflare
    Age: 89
    cf-cache-status: HIT
    alt-svc: h3=":443"; ma=86400
    body (577 bytes): b'<!doctype html><html lang=en><head>...
```

- `Server: cloudflare`, `cf-cache-status: HIT`, `Age: 89` — উত্তর এসেছে **CDN-এর cache** থেকে (৮৯ সেকেন্ড আগে cache হয়েছে), origin server থেকে নয়। L02-06-এ দেখা IP-গুলোও CDN-এর।
- `alt-svc: h3=":443"` — "আমি HTTP/3-এও আছি" ঘোষণা।
- Body chunked — এখানেও parser কাজ করেছে।
- HTTPS URL দিলে tool exit ২ দেয়: `error: only http:// (HTTPS needs TLS — see L02-08)`।

### 9.3 `curl` — দৈনন্দিন tool (Ubuntu VM)

```bash
curl -v http://example.com/ -o /dev/null          # > পাঠানো, < পাওয়া header; * connection তথ্য
curl -sI https://example.com/                     # শুধু header (HEAD)
curl -s -o /dev/null -w '%{http_code} %{http_version} %{time_connect} %{time_starttransfer} %{time_total}\n' https://example.com/
curl -sL -o /dev/null -w '%{url_effective} %{num_redirects}\n' http://github.com/   # redirect অনুসরণ
curl --http2 -sI https://example.com/ | head -1   # HTTP/2
curl --http3 -sI https://example.com/ | head -1   # HTTP/3 — Ubuntu-র curl build-এ সমর্থন নাও থাকতে পারে
curl -H 'Host: other.example' http://127.0.0.1:8000/   # virtual host পরীক্ষা
```

`-w` timing (`time_connect` = TCP, `time_appconnect` = TLS, `time_starttransfer` = প্রথম byte) — latency কোন ধাপে তা আলাদা করার সবচেয়ে সহজ উপায়।

`nc`/`telnet` দিয়েও raw HTTP:

```bash
printf 'GET / HTTP/1.1\r\nHost: example.com\r\nConnection: close\r\n\r\n' | nc example.com 80
```

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_http_raw.py`](code/L02-07/test_http_raw.py)-এর ৭টি test: request byte হুবহু, header case-insensitive, chunked decode (chunk extension সহ ও পরের byte অক্ষত), **একই connection-এ GET + chunked + POST**, redirect ও 404, HEAD-এ body নেই (501 হলেও), CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `build_request` | Request line + Host + header + `\r\n\r\n` + body | HTTP/1.1-এ Host বাধ্যতামূলক; body থাকলে Content-Length |
| `Connection.buf` | পড়া কিন্তু ব্যবহার-না-হওয়া byte রাখে | Keep-alive-এ পরের response-এর byte আগেই চলে আসতে পারে |
| `decode_chunked` → `(body, used)` | কত byte খরচ হয়েছে ফেরত | বাকি byte পরের response-এর |
| `"incomplete"` + `_fill` | যথেষ্ট data না এলে আরো `recv` | TCP stream — message এক `recv`-এ আসার নিশ্চয়তা নেই |
| HEAD/204/304/1xx | Body পড়ে না | RFC 9112 নিয়ম; নইলে পরের response নষ্ট |
| `protocol_version = "HTTP/1.1"` | Python server-এ keep-alive | Default HTTP/1.0 প্রতিবার বন্ধ করে |
| `start_server` port ০ | OS খালি port দেয় | Test-এ port সংঘর্ষ নেই |

**Python কেন এখানে, কোথায় নয়:** protocol শেখা ও ছোট probe/test-এ ভালো। দৈনন্দিন diagnosis-এ `curl`; application-এ `requests`/`httpx` (HTTP/2, TLS, retry, pool সব সামলায়); production server-এ Python `http.server` **কখনো নয়** (security ও performance-এর জন্য তৈরি নয় — Python documentation নিজেই সতর্ক করে)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `http_raw.py demo` | ৫টি exchange, শেষ লাইনে "ONE TCP connection" |
| `http_raw.py get http://example.com/` | `200 OK`, exit ০ |
| `curl -v` | `>` ও `<` লাইনে Section 9.1-এর মতো গঠন |
| `curl -w` timing | `time_connect` < `time_starttransfer` < `time_total` |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| 502 | Backend বন্ধ/refused/keep-alive race | Proxy error log, `curl` সরাসরি backend-এ | Backend চালু; timeout সামঞ্জস্য (Section 5) |
| 504 | Backend ধীর | Proxy-র timeout বনাম backend-এর সময় | Backend দ্রুত করুন বা timeout বাড়ান — দুটোই ভেবে |
| 503 | Healthy backend নেই/overload | LB target health | Health check path ও code মেলান |
| 400 / ভুল site | Host header ভুল | `curl -v` দেখুন | ঠিক Host / SNI |
| Redirect loop | HTTP→HTTPS redirect আর proxy-র পেছনে app ভাবে সবসময় HTTP | `curl -sIL` | `X-Forwarded-Proto` বিশ্বাস করুন (Module 16) |
| Streaming আটকে থাকে | Proxy buffering | সরাসরি backend-এ বনাম proxy দিয়ে | Proxy buffering বন্ধ (যেমন Nginx `proxy_buffering off`) |
| 413 | Body বেশি বড় | Proxy-র size limit | Limit (যেমন `client_max_body_size`) |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Plain HTTP-তে সব খোলা — password, token, cookie; সবসময় HTTPS (L02-08)। Header-এ secret (Authorization) log-এ যেন না যায় — log redaction। Request smuggling (Content-Length বনাম chunked)। `Server`/`X-Powered-By` header-এ version তথ্য কমান। Input size limit।
- **Performance:** Keep-alive ও connection pool (প্রতিবার handshake ব্যয়বহুল); HTTP/2 multiplexing; compression (`gzip`/`br`); caching header (`Cache-Control`, `ETag`) — CDN cache hit-এ origin-এ কোনো খরচ নেই (Section 9.2-এর `HIT`)।
- **Cost:** Cloud-এ data transfer out-এর বিল — compression ও CDN cache সরাসরি টাকা বাঁচায়; load balancer-এ request/connection অনুযায়ী বিল।

## 14. Hands-on exercise

1. `http_raw.py`-তে `follow_redirects` যোগ করুন (সর্বোচ্চ ৫টি, loop ধরা)। Test-এ `/old` → `/hello`।
2. `DemoHandler`-এ `do_HEAD` যোগ করে test-টি আপডেট করুন — 200 আসবে, body তবুও খালি।
3. `curl -w` দিয়ে তিনটি ভিন্ন site-এর `time_connect`, `time_appconnect`, `time_starttransfer` তুলনা — কোথায় সময় যাচ্ছে?
4. Nginx install করে (`sudo apt install nginx`) local Python backend-এর সামনে বসান; backend বন্ধ করে 502 ও ধীর backend দিয়ে 504 তৈরি করুন। দুই ক্ষেত্রে Nginx error log-এর লাইন লিখে রাখুন।
5. Browser DevTools-এর Network tab-এ "Protocol" column চালু করে কোন site h2/h3 ব্যবহার করে দেখুন।

## 15. Mini-project — HTTP probe

`http_raw.py` ও `curl -w`-এর ধারণা মিলিয়ে একটি probe script: URL-এর তালিকা নিয়ে প্রতিটির status, redirect সংখ্যা, connect/first-byte/total সময় ও `Server` header বের করে table দেখায়; কোনোটি 5xx বা নির্দিষ্ট latency-র বেশি হলে exit ১। HTTPS-এর জন্য `urllib.request` বা L02-08-এর পরে `ssl`। এটি Module 20-এর synthetic monitoring ও L02-17-এর request-flow lesson-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. 502, 503 ও 504-এর পার্থক্য কী? প্রতিটিতে প্রথমে কোথায় দেখবেন?
2. HTTP/1.1-এ response body-র শেষ কীভাবে বোঝা যায়?
3. Keep-alive কী এবং proxy-backend timeout কেন মেলাতে হয়?
4. HTTP/2 কোন সমস্যা সমাধান করে? HTTP/3 কেন UDP-তে?
5. Idempotent method কী এবং retry-এর সাথে সম্পর্ক কী?
6. `curl` দিয়ে কোন ধাপে latency তা কীভাবে বের করবেন?
7. Host header কেন প্রয়োজন?

## 17. Self-assessment প্রশ্ন

1. রেস্তোরাঁ analogy কোথায় মেলে না (দুটি বিষয়)?
2. Section 5-এ 502 কেন idle সময়ের পরে বেশি হতো?
3. `Connection.buf` না থাকলে keep-alive-এ কী ভুল হতো?
4. HEAD-এর উত্তরে Content-Length থাকলেও body পড়া কেন ভুল?
5. Section 9.2-এ উত্তর origin থেকে নয়, CDN থেকে এসেছে — কীভাবে বুঝলেন?

## 18. সংক্ষিপ্ত সারাংশ

- HTTP/1.1 = text message: start line, header, খালি লাইন, body; stateless।
- Body-র শেষ: Content-Length, chunked, বা connection বন্ধ।
- Keep-alive একটি connection-এ বহু request; proxy-র চেয়ে backend-এর idle timeout বেশি রাখুন।
- 502 = backend থেকে বৈধ উত্তর নেই, 503 = অনুপলব্ধ, 504 = timeout।
- HTTP/2 = binary + multiplexing (TCP-র উপর); HTTP/3 = QUIC (UDP)।
- `curl -v` ও `-w` timing প্রধান diagnosis tool।

## 19. Completion checklist

- [ ] `http_raw.py demo` চালিয়ে keep-alive ও chunked নিজে দেখেছি
- [ ] `curl -v` ও `-w` timing চালিয়েছি
- [ ] 502 ও 504 নিজে তৈরি করে log দেখেছি (Exercise ৪)
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 9110 — HTTP semantics: https://www.rfc-editor.org/rfc/rfc9110
- RFC 9112 — HTTP/1.1: https://www.rfc-editor.org/rfc/rfc9112
- RFC 9113 — HTTP/2: https://www.rfc-editor.org/rfc/rfc9113
- RFC 9114 — HTTP/3: https://www.rfc-editor.org/rfc/rfc9114
- RFC 9000 — QUIC: https://www.rfc-editor.org/rfc/rfc9000
- MDN — HTTP: https://developer.mozilla.org/en-US/docs/Web/HTTP
- curl manual: https://curl.se/docs/manpage.html
- Python `http.server`: https://docs.python.org/3/library/http.server.html

---

**পরের lesson:** L02-08 — TLS, certificate ও HTTPS
