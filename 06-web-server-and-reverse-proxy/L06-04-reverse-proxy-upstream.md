# L06-04 — Reverse proxy ও upstream

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L06-03 — Server block](L06-03-nginx-server-blocks.md), [L05-13 — TaskFlow API](../05-python-for-infrastructure/L05-13-taskflow-api-v01.md), [L02-12 — Load balancing](../02-computer-networking/L02-12-load-balancing.md) |
| **Label** | Needs L05-13 |
| **Tested** | `proxy_uri.py`, `proxy_lint.py`, `error_explainer.py`: ৯টি test পাস (Python 3.14.5, Windows)। `proxy_pass`-এর URI নিয়মের test nginx documentation-এর উদাহরণ দিয়ে। **আসল পরিমাপ:** TaskFlow-এ প্রতি request-এ নতুন connection ১৫২–১৭৪ req/s, একটি keep-alive connection ~২,২৬০ req/s (দুই run)। `sample-error.log` nginx-এর বার্তার রূপে **হাতে বানানো**, আসল nginx-এর log নয়। nginx এই machine-এ নেই — Section 9.6 **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Reverse proxy কী করে, এবং TaskFlow-কে কেন সরাসরি নয়, nginx-এর পেছনে রাখা হয়।
- `proxy_pass`-এর URI নিয়ম — **trailing slash**-এর তিনটি ক্লাসিক ভুল।
- `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`, `X-Request-ID` — কেন, এবং `proxy_set_header`-এর inheritance ফাঁদ।
- `upstream` block: একাধিক server, `max_fails`/`fail_timeout`, **keepalive** (এবং তার দুটি বাধ্যতামূলক শর্ত)।
- Timeout (`proxy_connect_timeout`, `proxy_read_timeout`), `proxy_next_upstream`, `client_max_body_size`।
- **502, 504, 413, 499** — error.log পড়ে কারণ নির্ণয়।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L06-02-এ দেখা গেছে, TaskFlow-এর `http.server` ধীর client-এ সহজে আটকে যায়। আর L05-13-এ বলা হয়েছিল, এটা শুধু `127.0.0.1`-এ শোনে। Reverse proxy দুটোরই সমাধান:

- **nginx internet-এর মুখোমুখি:** ধীর client, TLS (L06-07), body-র সীমা, rate limit (L06-08) সব সে সামলায়।
- **Application শুধু localhost-এ:** nginx-এর কাছ থেকে সম্পূর্ণ, যাচাই-করা request পায়।
- **এক নাম, অনেক backend:** `/api` এক service-এ, `/static` disk থেকে, পরে একাধিক app instance-এ load balancing।

কিন্তু proxy একটি নতুন স্তর, তাই নতুন ব্যর্থতার ধরন আনে:

- Application ভুল client IP দেখে (সবাই `127.0.0.1`)।
- ভুল URL পায় (`//tasks`)।
- আর ব্যর্থতা দেখায় অস্পষ্ট "502 Bad Gateway" হিসেবে।

## 3. সহজ ভাষায় পরিচয়

```nginx
upstream taskflow_app {
    server 127.0.0.1:8000 max_fails=3 fail_timeout=10s;
    keepalive 16;
}
server {
    listen 80;
    server_name taskflow.example.com;
    location / {
        proxy_pass http://taskflow_app;
        proxy_http_version 1.1;               # keepalive-এর জন্য বাধ্যতামূলক
        proxy_set_header Connection "";       # ঐ
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 30s;
    }
}
```

| Status | কে বানায় | সাধারণ অর্থ |
|---|---|---|
| 502 Bad Gateway | nginx | Upstream-এ পৌঁছানো গেল না বা ভাঙা উত্তর দিল (refused, crash, socket permission) |
| 504 Gateway Timeout | nginx | Upstream সময়মতো connect বা উত্তর দিল না |
| 413 Content Too Large | nginx | Body `client_max_body_size`-এর বেশি |
| 499 (শুধু log-এ) | nginx | Client উত্তরের আগেই চলে গেছে |
| 500/503 | সাধারণত application | App-এর নিজের error (nginx শুধু পৌঁছে দেয়) |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের অভ্যর্থনা ও পিয়ন

- **Reverse proxy** = অভ্যর্থনা ডেস্ক। দর্শনার্থী সরাসরি অফিসে ঢোকেন না — ডেস্ক কাগজ নিয়ে ভেতরে পাঠায়, উত্তর এনে দেয়।
- **`X-Forwarded-For`** = কাগজে লেখা "আবেদনকারী: অমুক, ঠিকানা: …" — নইলে ভেতরের অফিস ভাবত সব আবেদন অভ্যর্থনা ডেস্ক নিজেই করেছে।
- **Keepalive** = ডেস্ক ও অফিসের মধ্যে খোলা দরজা। প্রতিটি কাগজের জন্য দরজা খোলা-বন্ধ নয়।
- **502** = ভেতরের অফিস বন্ধ বা কেউ সাড়া দিচ্ছে না। **504** = অফিস কাগজ নিয়েছে, কিন্তু উত্তর দিতে অনেক দেরি।

### Analogy কোথায় মেলে না

- **কাগজে "আবেদনকারী"-র নাম যে কেউ লিখতে পারে।** Client নিজেই `X-Forwarded-For: 1.2.3.4` পাঠাতে পারে। `$proxy_add_x_forwarded_for` সেটার পেছনে আসল IP **যোগ করে**, মুছে দেয় না। তাই application-এর উচিত শুধু বিশ্বস্ত proxy-র যোগ করা অংশ বিশ্বাস করা (সবচেয়ে ডানের entry; nginx-এর `real_ip_header` + `set_real_ip_from`)। নইলে rate limit বা IP-ভিত্তিক নিয়ম বাইপাস হয়।
- **ডেস্কের ক্লার্ক কাগজের ঠিকানা নিজের মতো বদলায় না — nginx বদলায়।** `proxy_pass`-এ URI অংশ থাকলে location-এর মেলা অংশ বদলে যায়। একটি `/`-এর জন্য `/api/tasks` হয়ে যেতে পারে `//tasks` (Section 9.1)।
- **দরজা খোলা রাখতে চাইলেই খোলা থাকে না।** `keepalive 16;` লিখলেও nginx default-এ upstream-এর সাথে HTTP/1.0 ও `Connection: close` পাঠায়, ফলে keepalive কাজই করে না — যদি না `proxy_http_version 1.1` ও `Connection ""` দেওয়া হয়। কোনো error বা সতর্কতা আসে না। মাপা পার্থক্য ~১৩ গুণ (Section 9.4)।

## 5. Real-world engineering scenario — "ছুটির দিনে ৫০২-এর ঝড়, অথচ app সুস্থ"

**পরিস্থিতি:** TaskFlow-এর পেছনে প্রতিদিন রাত ২টায় কয়েক মিনিট 502। Application-এর health check সবুজ, log-এ কোনো error নেই।

`error_explainer.py` দিয়ে error.log পড়া হলো (Section 9.3-এর রূপের লাইন):

```text
502  connect() failed (111: Connection refused)    ← ২টি
502  no live upstreams                             ← তারপর
```

**তদন্ত:**

1. রাত ২টায় logrotate চলে, এবং app-এর `postrotate` app-কে **restart** করে (reload নয়)। কয়েক সেকেন্ড port বন্ধ।
2. সেই সময়ের request-গুলো refused। Upstream-এ `max_fails` default (১), তাই একটি ব্যর্থতাতেই server ১০ s-এর জন্য "dead" চিহ্নিত হলো — ফলে "no live upstreams", যদিও app ২ s পরেই ফিরে এসেছিল।
3. সাথে `proxy_pass http://localhost:8000`: প্রতিটি request প্রথমে `[::1]:8000`-এ refused হয়ে তারপর `127.0.0.1`-এ যাচ্ছিল। ফলে error.log আরও শব্দে ভরা, আর failure-এর গণনা দ্রুত বাড়ছিল।

**সমাধান:**

- App-এ graceful reload, বা systemd socket activation (L06-05)।
- `upstream`-এ `127.0.0.1`, সাথে `max_fails=3 fail_timeout=10s`।
- `proxy_next_upstream error timeout` — একাধিক instance থাকলে অন্যটিতে।
- Log-এ `$upstream_status` ও `$upstream_connect_time`।

**শিক্ষা:** 502 একটি লক্ষণ, কারণ নয়। error.log-এর বার্তা (refused বনাম timed out বনাম prematurely closed) কারণের দিকে নির্দেশ করে।

## 6. Diagram — request ও response-এর পথ

```text
 client 192.0.2.44 ──► nginx :80  (server_name taskflow.example.com)
                         │ client_max_body_size 32k? ── না → 413 (app পর্যন্ত যায়ই না)
                         │ location / → proxy_pass http://taskflow_app
                         │ headers: Host: taskflow.example.com
                         │          X-Forwarded-For: 192.0.2.44   X-Forwarded-Proto: http
                         │          X-Request-ID: 7f3a…  Connection: ""  (HTTP/1.1)
                         ▼
                upstream taskflow_app ── keepalive pool (খোলা connection reuse)
                         │ connect ≤ 2s ─────── ব্যর্থ: refused → 502 / timeout → 504
                         ▼
                   TaskFlow 127.0.0.1:8000
                         │ উত্তর ≤ 30s ───────── না → 504 (read timeout)
                         │ উত্তর ছাড়াই বন্ধ ───── 502 (prematurely closed)
                         ▼
 client ◄── nginx (status, body)   access log: rt=0.012 urt=0.010 uct=0.000 us=200 rid=7f3a…
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Reverse proxy | Client-এর হয়ে নয়, server-এর হয়ে সামনে বসা proxy |
| Upstream | nginx যে backend-এ পাঠায় |
| `proxy_pass` | Request কোথায় যাবে (URI অংশসহ বা ছাড়া) |
| `X-Forwarded-For` (XFF) | Proxy চেইনে client IP-র তালিকা |
| `X-Forwarded-Proto` | মূল request http না https |
| Upstream keepalive | nginx ও app-এর মধ্যে connection reuse |
| `max_fails` / `fail_timeout` | কতবার ব্যর্থ হলে কতক্ষণ "dead" |
| `proxy_next_upstream` | কোন ব্যর্থতায় পরের server-এ চেষ্টা |
| `$upstream_response_time` | App-এর উত্তর দেওয়ার সময় (log-এ) |
| Request buffering | nginx পুরো body নিয়ে তারপর upstream-এ পাঠায় |
| 499 | Client উত্তরের আগে connection বন্ধ করেছে (nginx-এর নিজস্ব code) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 `proxy_pass`-এর URI নিয়ম

nginx documentation অনুযায়ী:

- `proxy_pass`-এ host-এর পরে **কোনো URI অংশ থাকলে** (একটি `/` হলেও), location-এর মেলা prefix বাদ দিয়ে সেই URI বসানো হয়।
- **না থাকলে** client-এর URI হুবহু যায়।

| location | proxy_pass | client URI | upstream পায় |
|---|---|---|---|
| `/api/` | `http://app:8000` | `/api/tasks` | `/api/tasks` |
| `/api/` | `http://app:8000/` | `/api/tasks` | `/tasks` |
| `/api` | `http://app:8000/` | `/api/tasks` | **`//tasks`** |
| `/api/` | `http://app:8000/v1` | `/api/tasks` | **`/v1tasks`** |
| `/api` | `http://app:8000/v1/` | `/apiary` | **`/v1/ary`** |

**নিয়ম:** location ও proxy_pass-এর URI — দুটোই `/` দিয়ে শেষ হবে, অথবা দুটোর কোনোটিই নয়।

Regex location-এ URI অংশ দেওয়া যায় না (`nginx -t` error দেয়)। Variable থাকলে URI হুবহু ব্যবহার হয়।

### 8.2 Header ও inheritance

nginx default-এ upstream-এ `Host: $proxy_host` পাঠায় — অর্থাৎ upstream-এর নাম (`taskflow_app`), client-এর নয়। Application যদি redirect বা absolute URL বানায়, তা ভুল হবে।

`proxy_set_header` L06-02-এর inheritance নিয়ম মানে: location-এ **একটি** `proxy_set_header` দিলেই server-স্তরের সবগুলো বাদ পড়ে। `taskflow-broken.conf`-এর `/reports/` ঠিক এই ভুল করে (Section 9.2)।

### 8.3 Keepalive-এর দুটি শর্ত

`upstream { keepalive N; }` শুধু idle connection-এর pool-এর আকার ঠিক করে। nginx default-এ upstream-এ **HTTP/1.0** বলে এবং `Connection: close` পাঠায়, তাই app প্রতিটি উত্তরের পরে connection বন্ধ করে দেয়। দুটো লাইন লাগে:

```nginx
proxy_http_version 1.1;
proxy_set_header Connection "";
```

### 8.4 Timeout ও retry

- **`proxy_connect_timeout`:** TCP connect — ছোট রাখুন (১–৫ s)। ব্যর্থ হলে 504, অথবা `proxy_next_upstream` থাকলে পরের server।
- **`proxy_read_timeout`:** দুটি পরপর read-এর মাঝের সময়, মোট সময় নয় (L05-06-এর মতো)। ৯০০ s-এর মতো মান দীর্ঘ কাজকে HTTP-তে আটকে রাখে; তার বদলে background job + status endpoint ব্যবহার করুন।
- **`proxy_next_upstream`:** default-এ `error timeout`। nginx non-idempotent request (POST, PATCH) **নিজে আর retry করে না**, যদি upstream-এ পাঠানো হয়ে গিয়ে থাকে (`non_idempotent` না দিলে) — L05-06-এর নীতির সাথে মিল।

> **Fedora-তে:** SELinux default-এ nginx-কে বাইরের TCP connection খুলতে দেয় না। upstream-এ connect-এ `(13: Permission denied) while connecting to upstream` আসবে। সমাধান: `sudo setsebool -P httpd_can_network_connect 1`। `error_explainer.py` এই বার্তা চেনে।

## 9. Practical demonstration

Files:

- [`code/L06-04/proxy_uri.py`](code/L06-04/proxy_uri.py)।
- [`proxy_lint.py`](code/L06-04/proxy_lint.py) (L06-02-এর parser দিয়ে)।
- [`error_explainer.py`](code/L06-04/error_explainer.py)।
- [`keepalive_bench.py`](code/L06-04/keepalive_bench.py)।
- [`taskflow.conf`](code/L06-04/taskflow.conf) (ঠিক) ও [`taskflow-broken.conf`](code/L06-04/taskflow-broken.conf) (ভুলসহ)।
- [`sample-error.log`](code/L06-04/sample-error.log) (হাতে বানানো)।
- [`test_l06_04.py`](code/L06-04/test_l06_04.py)।

### 9.1 URI নিয়ম — আসল output

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-04
python3 proxy_uri.py --table
```

```text
location /api/  proxy_pass http://app:8000        /api/tasks             → /api/tasks
location /api/  proxy_pass http://app:8000/       /api/tasks             → /tasks
location /api   proxy_pass http://app:8000/       /api/tasks             → //tasks
location /api/  proxy_pass http://app:8000/v1/    /api/tasks?done=true   → /v1/tasks?done=true
location /api/  proxy_pass http://app:8000/v1     /api/tasks             → /v1tasks
location /api   proxy_pass http://app:8000/v1/    /apiary                → /v1/ary
```

শেষটি সবচেয়ে বিপজ্জনক: `/apiary` নামের একটি সম্পূর্ণ আলাদা page API-তে চলে গেল, কারণ `location /api` prefix হিসেবে `/apiary`-র সাথেও মেলে।

### 9.2 Proxy lint — আসল output

```bash
python3 proxy_lint.py taskflow-broken.conf; echo "exit=$?"
python3 proxy_lint.py taskflow.conf; echo "exit=$?"
```

```text
WARNING taskflow-broken.conf:3 localhost-upstream         upstream taskflow_app: 'localhost' may resolve to ::1 first; …
ERROR   taskflow-broken.conf:15 keepalive-unused           upstream taskflow_app has keepalive but this location lacks 'proxy_http_version 1.1;' and 'proxy_set_header Connection "";' — connections are not reused
ERROR   taskflow-broken.conf:19 keepalive-unused           (একই, /reports/)
ERROR   taskflow-broken.conf:19 proxy-header-inheritance   location sets its own proxy_set_header, so the server-level ones are dropped: Host, X-Forwarded-For, X-Forwarded-Proto
WARNING taskflow-broken.conf:19 missing-forward-headers    proxy without Host, X-Forwarded-For, X-Forwarded-Proto — …
WARNING taskflow-broken.conf:21 timeout-too-long           proxy_read_timeout 900s — slow upstream ties up connections; prefer async jobs
WARNING -                      default-body-size          client_max_body_size not set — default 1m; larger uploads get 413 from nginx
7 finding(s)
exit=1

0 finding(s)
exit=0
```

`taskflow-broken.conf` `nginx -t` পাস করবে এবং বাইরে থেকে "কাজ করবে" — তবুও সাতটি লুকানো সমস্যা। `localhost`-এর সতর্কতাটি L05-13-এর আসল পরিমাপ থেকে এসেছে: সেখানে `localhost` ০.২১ s, আর `127.0.0.1` ০.০০০৫ s।

### 9.3 Error.log থেকে কারণ — আসল output

```bash
python3 error_explainer.py sample-error.log --summary
```

```text
summary:
     2 × 502     upstream process is not listening (down, crashed, wrong port, or bound to another address)
     1 × 502     every server in the upstream block is marked failed (max_fails reached)
     1 × 504     app accepted the request but answered slower than proxy_read_timeout
     1 × 413     request body larger than client_max_body_size
     1 × 502     nginx worker (www-data) cannot open the unix socket — socket/directory permissions
     1 × 502     app closed the connection without a response — crash, worker killed (OOM), or protocol mismatch
     1 × (not recognised)
```

প্রতিটি লাইনের বিস্তারিততে request, upstream ও "next" পদক্ষেপ থাকে। `--summary` ছাড়া চালিয়ে দেখুন।

**সতর্কতা:** `sample-error.log` হাতে বানানো, nginx-এর বার্তার রূপে। আসল log-এ চালিয়ে tool-এর pattern যাচাই করা বাকি — exercise ১।

### 9.4 Keepalive কেন — আসল পরিমাপ

```bash
python3 keepalive_bench.py --requests 1000
```

```text
new connection per request   1000 requests in   5.75 s  →     174 req/s,  5.75 ms each
one keep-alive connection    1000 requests in   0.44 s  →    2265 req/s,  0.44 ms each
```

দ্বিতীয় run-এ: ১৫২ বনাম ২,২৫৮ req/s। এক machine-এর ভেতরে, localhost-এ পার্থক্য ~১৩ গুণ। Network-এ (ভিন্ন host, TLS) পার্থক্য আরও বেশি।

### 9.5 লেখার সময়

এই lesson-এর code-এ test নতুন কোনো logic bug পায়নি। একটি পুরোনো ফাঁদ আবার এসেছে: `keepalive_bench.py` প্রথম run-এ `UnicodeEncodeError: 'charmap' codec can't encode character '→'` দিয়ে crash করল — Windows-এর stdout cp1252। L04-08 থেকে প্রতিটি tool-এ যে `reconfigure(encoding="utf-8")` রাখা হয়, এখানে ভুলে বাদ পড়েছিল।

### 9.6 Ubuntu-তে (চালানো হয়নি)

```bash
# TaskFlow চালু (L05-13), তারপর:
sudo cp taskflow.conf /etc/nginx/sites-available/taskflow.conf
sudo ln -s /etc/nginx/sites-available/taskflow.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
curl -s -H 'Host: taskflow.example.com' http://127.0.0.1/health
tail -1 /var/log/nginx/taskflow.access.log           # rt=… urt=… us=200 rid=…

# ব্যর্থতা দেখা:
sudo systemctl stop taskflow                          # বা app-এর process বন্ধ
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: taskflow.example.com' http://127.0.0.1/tasks   # 502
sudo tail -3 /var/log/nginx/error.log | python3 error_explainer.py -
head -c 40000 /dev/zero | curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: taskflow.example.com' \
     -H 'Content-Type: application/json' --data-binary @- http://127.0.0.1/tasks            # 413
```

### 9.7 Test

```bash
python3 -m unittest -v
```

৯টি test:

- `proxy_pass`-এর documentation উদাহরণ।
- তিনটি slash ফাঁদ।
- Regex location ও variable।
- Broken নমুনার ঠিক ছয় ধরনের finding; ভালো নমুনা পরিষ্কার।
- Inheritance।
- Keepalive-এর শর্ত।
- Error.log-এর প্রতিটি লাইনের status।
- Connect বনাম read timeout।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `upstream_uri` — `uri_part` | host:port-এর পরের অংশ | URI অংশ আছে কিনা — একটি `/` হলেও |
| Regex location + URI → error | nginx-এর নিজের নিয়ম | `nginx -t` এটা প্রত্যাখ্যান করে |
| `headers_in` local বনাম inherited | একটিও local থাকলে inherited বাদ | nginx-এর array directive-এর নিয়ম |
| `keepalive-unused` | upstream-এর keepalive + location-এর দুটি শর্ত | নীরবে অকার্যকর keepalive |
| `localhost-upstream` | IPv6-এর ফাঁদ | L05-13-এর পরিমাপ |
| `error_explainer` — pattern তালিকা | nginx-এর বার্তা → status ও কারণ | "connecting" বনাম "reading" timeout আলাদা |
| `keepalive_bench` — একই process-এ TaskFlow | Network-এর শব্দ ছাড়া পার্থক্য | Connection setup-এর খরচ আলাদা করা |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `proxy_uri.py --table` | `//tasks`, `/v1tasks`, `/v1/ary` সহ ছয় লাইন |
| `proxy_lint.py taskflow-broken.conf` | ৭টি finding, exit ১ |
| `proxy_lint.py taskflow.conf` | ০, exit ০ |
| `keepalive_bench.py` | keep-alive কয়েক গুণ দ্রুত |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| App-এ 404, nginx-এ 200 নয় | `proxy_pass`-এর slash-এ URI বদলেছে | `proxy_uri.py`; upstream-এর access log |
| App সব request-এ `127.0.0.1` দেখে | XFF পাঠানো হয়নি বা app পড়ে না | `proxy_set_header X-Forwarded-For`; app-এ বিশ্বস্ত proxy |
| Redirect `http://taskflow_app/…`-এ যায় | `Host` পাঠানো হয়নি | `proxy_set_header Host $host` |
| 502, `Connection refused` | App চলছে না বা ভুল port | `ss -ltnp`; `systemctl status` |
| 504 শুধু কিছু endpoint-এ | ধীর query | App profiling; timeout নয়, কাজ ছোট করুন |
| 502, `no live upstreams` | `max_fails` | প্রথম ব্যর্থতা খুঁজুন; `fail_timeout` |
| 413 বড় upload-এ | `client_max_body_size` 1m default | শুধু সেই location-এ বাড়ান |
| HTTPS-এ app ভাবে http | `X-Forwarded-Proto` নেই | Header + app-এ বিশ্বাস (L06-07) |
| Fedora-তে সব 502, `Permission denied` | SELinux | `httpd_can_network_connect` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - App শুধু `127.0.0.1` বা unix socket-এ (L06-05) — সরাসরি পৌঁছানো যায় না।
  - XFF বিশ্বাসের নিয়ম: শুধু বিশ্বস্ত proxy-র যোগ করা অংশ।
  - `client_max_body_size` ছোট রাখুন।
  - Upstream-এর ভেতরের error page বা header (`Server: …`) ফাঁস না করতে `proxy_hide_header`, `proxy_intercept_errors`।
  - `X-Request-ID` দিয়ে nginx ও app-এর log জোড়া (L05-07)।
- **Performance:**
  - Upstream keepalive (মাপা ~১৩ গুণ)।
  - `proxy_buffering on` (default) — ধীর client app-কে আটকায় না।
  - ছোট connect timeout।
  - `$upstream_response_time` log করুন — "nginx ধীর নাকি app?"-এর উত্তর।
- **Cost:**
  - Keepalive ও buffering-এর কারণে একই hardware-এ বেশি request।
  - একাধিক app instance load balancing-এ — ছোট instance বেশি সংখ্যায় ও horizontal scaling (Module 07/14)।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.6 চালান। আসল error.log-এর লাইনে `error_explainer.py` চালিয়ে দেখুন — কোনো বার্তা চেনেনি কি? Pattern যোগ করুন।
2. `taskflow-broken.conf`-এর সাতটি finding ঠিক করে `proxy_lint.py`-কে ০-তে আনুন। `nginx -T`-এর সাথে মিলিয়ে দেখুন।
3. TaskFlow-কে XFF বুঝতে শেখান: `TASKFLOW_TRUSTED_PROXIES=127.0.0.1` হলে access log-এর `client` হবে XFF-এর সবচেয়ে ডানের অবিশ্বস্ত entry। Test লিখুন — নকল XFF দিয়ে।
4. দুটি TaskFlow instance (port ৮০০০, ৮০০১) চালিয়ে upstream-এ দুটোই দিন। একটিকে বন্ধ করে ১০০টি request পাঠান — কয়টি ব্যর্থ? `max_fails`/`proxy_next_upstream` বদলে আবার দেখুন।
5. `keepalive_bench.py`-এ TLS যোগ করুন (L02-08-এর মতো local CA)। নতুন connection-এর খরচ কতটা বাড়ে?

## 15. Mini-project — Proxy observability

`upstream_report.py`:

- nginx-এর `upstream_timing` format-এর access log পড়ে (L05-11-এর ধারণা)।
- প্রতিটি upstream status-এর সংখ্যা।
- `rt - urt` (nginx-এর নিজের সময় — ধীর client বা buffering)।
- `uct` (connect সময় — keepalive কাজ করছে কিনা: reuse-এ ~০)।
- p99 `urt` per endpoint।

Lab 06-B-তে TaskFlow-এর সামনে nginx-এর পরে এটা চালানো হবে।

## 16. Interview প্রশ্ন

1. Reverse proxy কেন ব্যবহার করবেন? Forward proxy-র সাথে পার্থক্য কী?
2. 502 ও 504-এর পার্থক্য কী? প্রতিটির তিনটি সম্ভাব্য কারণ বলুন।
3. `proxy_pass http://app/` ও `proxy_pass http://app`-এর পার্থক্য কী?
4. `X-Forwarded-For` কীভাবে কাজ করে? কেন সরাসরি বিশ্বাস করা যায় না?
5. nginx-এ upstream keepalive কীভাবে চালু করবেন?
6. App ধীর না nginx ধীর — কীভাবে বুঝবেন?

## 17. Self-assessment প্রশ্ন

1. অভ্যর্থনা analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি কারণ কী ছিল?
3. `/apiary` কেন API-তে গেল?
4. `keepalive 16;` থাকলেও connection reuse না হওয়ার কারণ কী?
5. "connecting to upstream" ও "reading response header" timeout-এর পার্থক্য কী বলে?

## 18. সংক্ষিপ্ত সারাংশ

- App শুধু localhost-এ; nginx সামনে।
- `proxy_pass`: location ও URI-তে slash মেলান।
- `Host`, `X-Forwarded-For`, `X-Forwarded-Proto` পাঠান; একটি local `proxy_set_header` বাইরের সব মুছে দেয়।
- Keepalive = `keepalive N` + `proxy_http_version 1.1` + `Connection ""`।
- 502/504/413: error.log-এর বার্তা দেখে কারণ; `$upstream_*` log করুন; upstream-এ `127.0.0.1`, `localhost` নয়।

## 19. Completion checklist

- [ ] `proxy_uri.py --table`-এর প্রতিটি লাইন ব্যাখ্যা করতে পারি
- [ ] Keepalive-এর পার্থক্য নিজে মেপেছি
- [ ] (Ubuntu) TaskFlow-কে nginx-এর পেছনে চালিয়ে 502 ও 413 পুনরুৎপাদন করেছি
- [ ] `python3 -m unittest -v`-এ ৯টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nginx — `ngx_http_proxy_module` (`proxy_pass`, `proxy_set_header`, timeouts): https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- nginx — `ngx_http_upstream_module` (`keepalive`, `max_fails`): https://nginx.org/en/docs/http/ngx_http_upstream_module.html
- nginx — `ngx_http_realip_module`: https://nginx.org/en/docs/http/ngx_http_realip_module.html
- nginx — Embedded variables (`$upstream_response_time`, `$request_id`): https://nginx.org/en/docs/varindex.html
- MDN — X-Forwarded-For: https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/X-Forwarded-For
- RFC 9110 — HTTP Semantics (502, 504, 413): https://www.rfc-editor.org/rfc/rfc9110

---

**পরের lesson:** L06-05 — Application process, port, unix socket ও systemd service
