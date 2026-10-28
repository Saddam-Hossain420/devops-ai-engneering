# L02-12 — Load balancing ও reverse proxy: L4 বনাম L7

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-05 — TCP](L02-05-tcp-udp-sockets.md), [L02-07 — HTTP](L02-07-http.md), [L02-08 — TLS](L02-08-tls-certificates.md) |
| **Label** | — |
| **Tested** | `lb_algorithms.py` ও `mini_proxy.py`: ৮টি test পাস — algorithm (round robin, smooth weighted, least connections, consistent hashing, remap) এবং loopback-এ **আসল HTTP proxy**: একটি বন্ধ backend সহ সমান বণ্টন, X-Forwarded-For ও X-Request-ID, সব বন্ধ → 502, ধীর → 504 (Python 3.14, Windows)। Test চালাতে গিয়ে proxy-র round robin-এ **দুটি আসল bug** ধরা পড়েছে — Section 9.3। Nginx/HAProxy configuration **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Load balancer কেন: scale, availability, zero-downtime deploy।
- **L4** (TCP/UDP, connection স্তরে) বনাম **L7** (HTTP request স্তরে) load balancing।
- Reverse proxy-র কাজ: routing, TLS termination, header যোগ, retry, timeout, buffering।
- Algorithm: round robin, weighted, least connections, hashing, **consistent hashing**।
- **Health check** (active ও passive), connection draining, sticky session।
- X-Forwarded-For, X-Request-ID; retry কখন নিরাপদ।
- Python দিয়ে algorithm simulation ও ছোট L7 reverse proxy; Nginx/HAProxy-র সমতুল্য config।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি server যথেষ্ট নয়: traffic বাড়ে, server crash করে, deploy-এর সময় restart লাগে। কয়েকটি server-এর সামনে একটি **load balancer** বসালে:

- Traffic ভাগ হয় (horizontal scaling)।
- অসুস্থ server-কে বাদ দেওয়া হয় (availability)।
- একে একে server বদলানো যায় user টের না পেয়ে (rolling deploy, Module 16)।
- TLS, compression, rate limit এক জায়গায়।

DevOps-এ load balancer ঘিরে প্রচলিত সমস্যা: health check ভুল path-এ → সব target "unhealthy" → 503; application-এ সব request-এর IP load balancer-এর (X-Forwarded-For না পড়ায়) → rate limit সবাইকে একসাথে আটকায়; retry-এর কারণে একই payment দুবার; cache server যোগ করার পরে cache hit হঠাৎ শূন্যে।

## 3. সহজ ভাষায় পরিচয়

**Load balancer** = client ও একদল backend server-এর মাঝখানে বসে প্রতিটি নতুন কাজ কোন backend-এ যাবে তা ঠিক করে।

**Reverse proxy** = server-এর পক্ষে client-এর request গ্রহণ করে backend-এ পাঠায় (forward proxy উল্টো — client-এর পক্ষে বাইরে যায়)। প্রায় সব L7 load balancer reverse proxy-ও।

| | L4 | L7 |
|---|---|---|
| কী দেখে | IP, port (TCP/UDP) | HTTP method, path, header, cookie |
| সিদ্ধান্তের একক | **Connection** | **Request** |
| TLS | সাধারণত পার করে দেয় (passthrough) | Terminate করে (L02-08) |
| Routing | শুধু port অনুযায়ী | `/api` → api server, `/static` → CDN, header অনুযায়ী canary |
| Overhead | খুব কম | বেশি (HTTP parse) |
| উদাহরণ | AWS NLB, LVS/IPVS, HAProxy `mode tcp`, Kubernetes Service (kube-proxy) | AWS ALB, Nginx, HAProxy `mode http`, Envoy, Kubernetes Ingress/Gateway |
| কখন | Database, gRPC passthrough, non-HTTP, অতি উচ্চ throughput | Web/API, path routing, header যোগ, retry |

**Algorithm:**

| Algorithm | কীভাবে | কখন |
|---|---|---|
| Round robin | পালাক্রমে | সব backend সমান, request সমান |
| Weighted | ক্ষমতা অনুযায়ী অনুপাত | ভিন্ন আকারের machine, canary (৯৫:৫) |
| Least connections | যার কাজ সবচেয়ে কম | Request-এর সময় অসম (LLM inference, file upload) |
| Hash (IP/header) | একই key → একই backend | Session affinity, cache locality |
| Consistent hashing | Hash ring — backend বদলালে কম key সরে | Distributed cache, sharding |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### সুপারশপের ক্যাশ কাউন্টার

- **Load balancer** = দরজায় দাঁড়ানো কর্মী যিনি ক্রেতাদের কাউন্টারে পাঠান।
- **Round robin** = পালাক্রমে ১, ২, ৩ নম্বর কাউন্টার।
- **Least connections** = যে লাইনে সবচেয়ে কম মানুষ — একজনের ট্রলি ভর্তি থাকলে বাকিরা অন্য লাইনে।
- **Health check** = কাউন্টারের কম্পিউটার বন্ধ হলে সেখানে আর কাউকে না পাঠানো।
- **Connection draining** = কাউন্টার বন্ধ করার আগে "নতুন কেউ নয়, যারা লাইনে আছেন তাদের শেষ করুন"।
- **L4 বনাম L7:** L4 কর্মী শুধু দেখেন "একজন ক্রেতা" — ট্রলিতে কী আছে দেখেন না। L7 কর্মী দেখেন "শুধু ১০টির কম জিনিস → express কাউন্টার" (path/header-ভিত্তিক routing)।

### Analogy কোথায় মেলে না

- ক্রেতা একবার কাউন্টারে গেলে শেষ পর্যন্ত থাকেন। L4-এ **একটি TCP connection** একটি backend-এ থাকে — HTTP/2 বা gRPC-তে একটি connection-এ হাজারো request, সব এক backend-এ যায়, তাই L4 load balancer gRPC-তে অসম বণ্টন দেয় (L7 লাগে)।
- কর্মী সব কাউন্টার এক নজরে দেখেন। আসল load balancer প্রায়ই **একাধিক instance** — প্রতিটির "least connections" হিসাব নিজের, অন্যদের নয়।
- কাউন্টার বন্ধ হলে ক্রেতা নিজে অন্য লাইনে যান। HTTP-তে **retry** load balancer নিজে করতে পারে — কিন্তু POST (payment) retry করলে কাজটা দুবার হতে পারে (L02-07-এর idempotency)।

## 5. Real-world engineering scenario — Cache cluster-এ একটি node যোগ

**পরিস্থিতি:** একটি API ৪টি Redis cache node ব্যবহার করে; client library কোন key কোন node-এ তা ঠিক করে `hash(key) % 4` দিয়ে। Traffic বাড়ায় পঞ্চম node যোগ করা হলো। সাথে সাথে cache hit rate ৯৫% থেকে প্রায় ২০%-এ নেমে গেল, database-এ load ৫ গুণ, latency বেড়ে timeout।

**কারণ:** `% 4` থেকে `% 5` হলে **প্রায় ৮০% key অন্য node-এ** চলে যায় — নতুন node-এ সেগুলো নেই (cache miss), সবাই একসাথে database-এ (thundering herd)। এই lesson-এর simulation-এ আসল সংখ্যা: modulo-তে **৭৯.৬%** key সরেছে; consistent hashing-এ **১৭.৪%** (আদর্শ ২০%)।

**সমাধান:** consistent hashing (ring + virtual node) — একটি node যোগ করলে শুধু ~১/N key সরে। এছাড়া: node যোগ কম traffic-এর সময়ে, cache warm-up, database-এ connection limit ও request coalescing।

**শিক্ষা:** "কোন request কোথায় যাবে" সিদ্ধান্তের algorithm শুধু load বণ্টন নয় — state (cache, session, shard) থাকলে পরিবর্তনের খরচও ঠিক করে।

## 6. Diagram

```text
                           ┌───────────── L7 load balancer / reverse proxy ─────────────┐
 client ── HTTPS ─────────►│ TLS terminate → HTTP parse → route by path/header           │
 (203.0.113.7)             │   /api/*    → api pool  [least_conn]                        │
                           │   /static/* → static pool                                   │
                           │ + X-Forwarded-For: 203.0.113.7, X-Request-ID: 9f2c…         │
                           │ + health check (active: GET /healthz; passive: errors)      │
                           └──────┬──────────────┬──────────────┬────────────────────────┘
                                  ▼              ▼              ✗ (ejected)
                               api-1          api-2          api-3

 L4 (TCP) load balancer: client ─ TCP ─► [IP:port দেখে একটি backend বাছে] ─ একই TCP stream ─► backend
                          (TLS ও HTTP অপরিবর্তিত পার হয়; backend client-এর IP দেখতে পারে বা PROXY protocol)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Load balancer | কাজ backend-দের মধ্যে ভাগ করে |
| Reverse / forward proxy | Server-এর পক্ষে / client-এর পক্ষে |
| L4 / L7 | Transport স্তরে / application (HTTP) স্তরে |
| Backend / upstream / target | যে server আসল কাজ করে |
| Pool / target group | একদল backend |
| Active health check | LB নিজে নিয়মিত `/healthz` চেক করে |
| Passive health check / outlier ejection | আসল traffic-এর error দেখে সাময়িক বাদ |
| Connection draining / deregistration delay | বাদ দেওয়ার আগে চলমান কাজ শেষ করতে দেওয়া |
| Sticky session / affinity | একই client সবসময় একই backend-এ |
| Consistent hashing | Ring-ভিত্তিক hash — পরিবর্তনে কম key সরে |
| X-Forwarded-For / -Proto | আসল client IP / আসল scheme |
| X-Request-ID | একটি request-এর trace ID — সব log-এ একই |
| PROXY protocol | L4 LB-এর client IP backend-এ পাঠানোর header |
| Thundering herd | একসাথে বহু request একই resource-এ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Health check

- **Active:** LB প্রতি কয়েক সেকেন্ডে `GET /healthz` — পরপর N বার ব্যর্থ হলে unhealthy, M বার সফল হলে আবার healthy (flapping এড়াতে)।
- **Passive:** আসল request-এ connection error/5xx দেখে সাময়িক বাদ (এই lesson-এর proxy এটাই করে)।
- **Health endpoint কী যাচাই করবে?** শুধু process জীবিত কিনা (liveness) নাকি dependency-ও (readiness)? Database একটু ধীর হলেই সব backend unhealthy ঘোষণা করলে পুরো service বন্ধ — cascading failure। সাধারণ নিয়ম: LB health check হালকা ও নিজস্ব অবস্থা-ভিত্তিক; dependency সমস্যা application নিজে সামলাবে (Module 14-এ readiness/liveness)।

### 8.2 Retry ও timeout

- Connection-ই হয়নি (refused) → অন্য backend-এ retry **নিরাপদ** — request backend-এ পৌঁছায়নি।
- Request পাঠানোর পরে timeout → backend হয়তো কাজ করছে; retry করলে দ্বিগুণ load বা দ্বিগুণ কাজ। শুধু idempotent method-এ, সীমিত সংখ্যায়, এবং retry budget সহ (Module 15)।
- এই lesson-এর proxy: connection error-এ retry (idempotent method-এ), timeout-এ সরাসরি 504।

### 8.3 Client IP ও request ID

L7 proxy নতুন TCP connection খোলে, তাই backend-এর চোখে source IP = proxy। আসল IP `X-Forwarded-For`-এ। **সতর্কতা:** client নিজেও এই header পাঠাতে পারে — backend শুধু **বিশ্বস্ত proxy-র যোগ করা** অংশ বিশ্বাস করবে (rightmost বিশ্বস্ত hop)। `X-Request-ID` প্রথম proxy তৈরি করে, সব hop-এর log-এ একই ID — L02-17 ও Module 17-এর distributed tracing-এর ভিত্তি।

### 8.4 Kubernetes ও cloud

- Kubernetes `Service` (ClusterIP) = kube-proxy-র iptables/IPVS বা eBPF দিয়ে **L4** load balancing; `Ingress`/`Gateway API` = **L7** (Module 14)।
- AWS: NLB (L4, static IP, অতি দ্রুত), ALB (L7, path/host routing, WAF); GCP/Azure-এ সমতুল্য (Module 08)।
- Cross-zone load balancing ও এর data transfer খরচ।

## 9. Practical demonstration

### 9.1 Algorithm তুলনা

File: [`code/L02-12/lb_algorithms.py`](code/L02-12/lb_algorithms.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-12
python3 lb_algorithms.py compare
python3 lb_algorithms.py remap --from 4
python3 lb_algorithms.py remap --from 10
```

**আসল output:**

```text
round robin         {'app-1': 3333, 'app-2': 3333, 'app-3': 3333}
smooth weighted 5:1:1 first 7 picks: big big small-1 big small-2 big big
consistent hash     {'app-2': 3282, 'app-1': 3771, 'app-3': 2946}
least connections (app-1 busy with a long request): app-2 app-2 app-2 app-2 app-2 app-2

4 → 5 servers, 10000 keys (ideal: 20.0% move)
  modulo hash:     79.6% of keys moved
  consistent hash: 17.4% of keys moved
10 → 11 servers, 10000 keys (ideal: 9.1% move)
  modulo hash:     90.9% of keys moved
  consistent hash: 8.5% of keys moved
```

- Smooth weighted: ভারী server-কে টানা ৫ বার নয়, মাঝে মাঝে হালকাদের দেয় — Nginx-এর algorithm।
- Consistent hash-এর বণ্টন পুরো সমান নয় (৩৭৭১ বনাম ২৯৪৬) — virtual node বাড়ালে আরো সমান হয় (Exercise ১)।
- Least connections: ব্যস্ত app-1-কে এড়ায়। (app-2 ও app-3 সমান হলে প্রথমটি বাছে — বাস্তব implementation-এ tie ভাঙতে round robin বা random মেশানো হয়।)
- Server সংখ্যা যত বেশি, modulo-তে তত বেশি key সরে (৯০.৯%) — Section 5।

### 9.2 Reverse proxy নিজের হাতে

File: [`code/L02-12/mini_proxy.py`](code/L02-12/mini_proxy.py) — তিনটি backend (মাঝেরটি বন্ধ port) ও proxy, সব loopback-এ।

```bash
python3 mini_proxy.py demo
```

**আসল output (Windows; port ও ID প্রতিবার ভিন্ন):**

```text
proxy :55641 -> app-1 :55638, (dead) :55640, app-2 :55639
GET /item/0 -> 200 from app-1  ( 19.3 ms)  XFF=127.0.0.1  request-id=75ad16d7d34e
GET /item/1 -> 200 from app-2  (2049.8 ms)  XFF=127.0.0.1  request-id=b3ae95db792e
GET /item/2 -> 200 from app-1  ( 29.0 ms)  XFF=127.0.0.1  request-id=44c05da3ca56
GET /item/3 -> 200 from app-2  ( 15.2 ms)  XFF=127.0.0.1  request-id=09b9b3042ddb
GET /item/4 -> 200 from app-1  ( 16.4 ms)  XFF=127.0.0.1  request-id=9e56c018e8bb
GET /item/5 -> 200 from app-2  ( 16.0 ms)  XFF=127.0.0.1  request-id=cb1d3e03ade5
all backends dead -> 502 {"error": "no backend reachable", "request_id": "53c2cb7e8156"}
```

**পর্যবেক্ষণ:**

- `/item/1`-এর পালা ছিল বন্ধ backend-এর → connection ব্যর্থ → proxy সেটিকে বাদ দিয়ে app-2-তে retry। Client সফল উত্তর পেয়েছে, কিন্তু **২ সেকেন্ড দেরিতে**। Windows-এ বন্ধ loopback port-এ connect প্রায় ২ সেকেন্ড পরে ব্যর্থ হয় (কয়েকবার চেষ্টা করে); Linux-এ সাধারণত সাথে সাথে "connection refused"। শিক্ষা: **passive health check-এ প্রথম ব্যর্থ request-এর মূল্য একজন user দেয়** — তাই active health check ও ছোট connect timeout দরকার।
- এরপর বন্ধ backend বাদ (eject) — বাকি request app-1 ও app-2-তে সমানভাবে।
- Backend-এর কাছে `X-Forwarded-For` (client IP) ও client-এর কাছে একই `X-Request-ID`।
- কোনো backend না থাকলে 502 (L02-07: "proxy backend থেকে উত্তর পায়নি")।

### 9.3 Test-এ ধরা পড়া দুটি bug (আসল ঘটনা)

এই proxy লেখার সময় test প্রথমবার fail করেছিল:

1. **সব request app-1-এ:** প্রতিটি request-এ round-robin iterator-কে N ঘর এগোনো হচ্ছিল (N = backend সংখ্যা), ফলে শুরুর বিন্দু কখনো বদলায়নি। Output-এ ৬টির ৬টিই app-1। দুটি backend থাকলেও load balancing হচ্ছিল না, অথচ **সব request সফল** — শুধু status code দেখে monitoring করলে এটা ধরা পড়ত না।
2. **অসম বণ্টন (২:৪):** প্রথম bug ঠিক করার পরে বাদ পড়া backend rotation-এ থেকে গিয়েছিল; তার পালা এলে পাশের backend (app-2) পেত — ফলে app-2 দ্বিগুণ load। বাস্তব LB-তেও এই প্রভাব দেখা যায়: একটি backend বাদ পড়লে তার "প্রতিবেশী"-র উপর চাপ। সমাধান: rotation শুধু সুস্থ backend-দের মধ্যে।

শিক্ষা: load balancer-এর **প্রতি-backend request সংখ্যা** একটি metric হিসেবে দেখুন (Module 17), শুধু error rate নয়।

### 9.4 Nginx ও HAProxy (Ubuntu VM)

দুটি backend (`python3 -m http.server 8001` ও `8002`, ভিন্ন directory থেকে) চালিয়ে:

```bash
sudo apt install nginx
sudo tee /etc/nginx/conf.d/lab-lb.conf >/dev/null <<'EOF'
upstream lab_app {
    least_conn;
    server 127.0.0.1:8001 max_fails=2 fail_timeout=10s;
    server 127.0.0.1:8002 max_fails=2 fail_timeout=10s;
    keepalive 16;
}
server {
    listen 8080;
    location / {
        proxy_pass http://lab_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Request-ID $request_id;
        proxy_connect_timeout 1s;
        proxy_read_timeout 30s;
        proxy_next_upstream error timeout;   # শুধু idempotent request-এ (Nginx default-এ POST retry করে না)
    }
}
EOF
sudo nginx -t && sudo systemctl reload nginx
for i in $(seq 6); do curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:8080/; done
# একটি backend বন্ধ করে আবার চালান; /var/log/nginx/error.log দেখুন
```

HAProxy-তে একই কাজ (`/etc/haproxy/haproxy.cfg`-এ যোগ):

```text
frontend lab_fe
    bind :8081
    mode http
    default_backend lab_be
backend lab_be
    mode http
    balance roundrobin
    option httpchk GET /
    server app1 127.0.0.1:8001 check inter 2s fall 2 rise 2
    server app2 127.0.0.1:8002 check inter 2s fall 2 rise 2
```

`sudo haproxy -c -f /etc/haproxy/haproxy.cfg` দিয়ে যাচাই, তারপর reload। HAProxy-তে `check` = **active** health check।

> **Fedora-তে:** একই package নাম (`sudo dnf install nginx haproxy`); SELinux-এ Nginx-কে অন্য port-এ backend-এ connect করতে দিতে `sudo setsebool -P httpd_can_network_connect 1` লাগে (L01-17), নইলে `502` ও `audit.log`-এ AVC denial।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l02_12.py`](code/L02-12/test_l02_12.py)-এর ৮টি test: round robin ক্রম, smooth weighted-এর হুবহু `aabacaa` ক্রম, least connections, consistent hash স্থিতিশীলতা ও বণ্টন, remap (modulo > ৬০%, ring < ৩০%), এবং proxy: বন্ধ backend সহ ৩:৩ বণ্টন ও header, সব বন্ধ → 502, ধীর backend → 504।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `SmoothWeighted` | `current += weight`, সর্বোচ্চটি বাছে, `-= total` | Nginx algorithm — ভারী server-কে ছড়িয়ে দেয় |
| `ConsistentHash` vnodes ১০০ | প্রতিটি server ring-এ ১০০ বিন্দু | কম vnode = অসম বণ্টন |
| `bisect` | Ring-এ পরের বিন্দু O(log n) | দ্রুত lookup |
| `Pool.candidates` | সুস্থদের মধ্যে rotation, বাদ পড়ারা শেষে | Section 9.3-এর দুটি bug-এর সমাধান |
| `mark_down` + `eject_seconds` | Passive health check | ব্যর্থ backend-এ বারবার চেষ্টা নয় |
| `HOP_BY_HOP` | `Connection` ইত্যাদি forward করা হয় না | এগুলো এক hop-এর জন্য (RFC 9110) |
| Timeout → 504, retry নয় | — | Section 8.2 |
| POST-এ শুধু একটি চেষ্টা | `IDEMPOTENT` set | দ্বিগুণ কাজ এড়াতে |

**Python কেন এখানে, কোথায় নয়:** algorithm বোঝা, simulation ও test-এ ভালো। Production-এ Nginx, HAProxy, Envoy বা cloud LB — event-driven, হাজারো connection, battle-tested। এই proxy প্রতি request-এ নতুন backend connection খোলে, streaming করে না, body পুরো memory-তে পড়ে।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `lb_algorithms.py remap --from 4` | modulo ~৮০%, consistent ~২০% |
| `mini_proxy.py demo` | ৬টি 200, app-1 ও app-2 তিনটি করে, শেষে 502 |
| Nginx lab, একটি backend বন্ধ | সব 200 (retry), error.log-এ `connect() failed` |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| সব target unhealthy, 503 | Health check path/port/expected code ভুল; security group LB-কে আটকায় | Backend থেকে নিজে `curl` health path | Path ও code মেলান; LB-এর SG থেকে allow |
| একটি backend-এ সব load | Sticky session, L4-এ HTTP/2/gRPC long connection, bug | প্রতি-backend request metric | L7, affinity পুনর্বিবেচনা |
| App-এ সব IP একই | X-Forwarded-For পড়া হচ্ছে না | App log | বিশ্বস্ত proxy-র header পড়ুন |
| Deploy-এর সময় কিছু 502 | Draining নেই; backend আগে বন্ধ | Deploy-এর সময়ের log | Deregistration delay, graceful shutdown (L01-08) |
| Payment দুবার | POST retry | LB retry config | Idempotency key, POST retry বন্ধ |
| Cache node যোগের পরে DB overload | Modulo hashing | Cache hit rate | Consistent hashing |
| Fedora-তে Nginx 502, backend ঠিক | SELinux | `ausearch -m avc` | `httpd_can_network_connect` |

## 13. Security, performance ও cost বিবেচনা

- **Security:** LB-তে TLS ও WAF; backend শুধু LB থেকে traffic গ্রহণ করবে (security group source = LB-এর SG, L02-10); X-Forwarded-For spoofing; request size/rate limit; health endpoint-এ সংবেদনশীল তথ্য নয়; LB access log চালু।
- **Performance:** Upstream keep-alive (L02-07); least connections অসম workload-এ (LLM inference — Module 25); ছোট connect timeout; L4 যেখানে L7-এর দরকার নেই; cross-zone balancing বনাম latency।
- **Cost:** Cloud LB-এর ঘণ্টা + LCU/capacity unit অনুযায়ী বিল; cross-AZ data transfer; প্রতিটি ছোট service-এর আলাদা LB-এর বদলে একটি shared L7 LB (host/path routing) অনেক সস্তা (Module 08)।

## 14. Hands-on exercise

1. `ConsistentHash`-এ vnode ১০, ১০০, ১০০০ দিয়ে বণ্টনের standard deviation তুলনা করুন।
2. `mini_proxy.py`-তে active health check thread যোগ করুন (প্রতি ২ সেকেন্ডে `GET /`); প্রথম ব্যর্থ request-এর ২ সেকেন্ডের দেরি কি দূর হয়? Test লিখুন।
3. `mini_proxy.py`-তে least-connections mode যোগ করুন; একটি ধীর backend (`delay=0.5`) ও একটি দ্রুত backend দিয়ে ২০টি সমান্তরাল request-এ round robin-এর সাথে মোট সময় তুলনা।
4. Ubuntu VM-এ Section 9.4-এর Nginx lab; একটি backend বন্ধ করে error log ও `curl` ফল লিখুন; তারপর POST দিয়ে পরীক্ষা করুন — retry হয়?
5. HAProxy-র stats page চালু করে (`stats uri /stats`) health check-এর অবস্থা পরিবর্তন নিজের চোখে দেখুন।

## 15. Mini-project — Canary router

`mini_proxy.py`-কে বাড়িয়ে weighted canary: config-এ `stable: 95, canary: 5`; `X-Canary: always` header থাকলে সবসময় canary; canary-র 5xx rate stable-এর চেয়ে নির্দিষ্ট মাত্রায় বেশি হলে স্বয়ংক্রিয়ভাবে canary-র weight শূন্য ও একটি log বার্তা। এটি Module 16-এর progressive delivery-র ধারণার ছোট সংস্করণ।

## 16. Interview প্রশ্ন

1. L4 ও L7 load balancer-এর পার্থক্য; কখন কোনটি?
2. gRPC traffic L4 load balancer-এ অসমভাবে ছড়ায় কেন?
3. Active ও passive health check; health endpoint-এ dependency check করা কেন ঝুঁকিপূর্ণ হতে পারে?
4. Consistent hashing কী সমস্যা সমাধান করে?
5. Load balancer-এর পেছনে application আসল client IP কীভাবে জানে? কী সতর্কতা?
6. Load balancer কখন retry করা নিরাপদ?
7. Zero-downtime deploy-এ connection draining-এর ভূমিকা।

## 17. Self-assessment প্রশ্ন

1. সুপারশপ analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ cache hit কেন হঠাৎ কমল — সংখ্যা সহ ব্যাখ্যা।
3. `demo`-তে `/item/1` কেন ২ সেকেন্ড নিল এবং কোন উন্নতি এটি কমাবে?
4. Section 9.3-এর দুটি bug কী ছিল এবং কোন metric এগুলো production-এ ধরত?
5. Timeout-এ proxy কেন retry করে না?

## 18. সংক্ষিপ্ত সারাংশ

- Load balancer = scale + availability + নিরাপদ deploy; L7 reverse proxy routing, TLS, header, retry-ও করে।
- L4 = connection স্তরে, দ্রুত; L7 = request স্তরে, বুদ্ধিমান।
- Algorithm: round robin, weighted, least connections, consistent hashing (পরিবর্তনে কম key সরে)।
- Health check: active + passive; draining; retry শুধু নিরাপদ ক্ষেত্রে।
- X-Forwarded-For (বিশ্বস্ত hop থেকে), X-Request-ID সব log-এ।
- প্রতি-backend request সংখ্যা monitor করুন — "সব 200" মানেই load balancing ঠিক নয়।

## 19. Completion checklist

- [ ] `lb_algorithms.py` দিয়ে modulo বনাম consistent hashing নিজে দেখেছি
- [ ] `mini_proxy.py demo` ব্যাখ্যা করতে পারি, Section 9.3-এর bug বুঝেছি
- [ ] Nginx বা HAProxy দিয়ে দুটি backend-এ load balancing ও failover করেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Nginx — HTTP load balancing: https://docs.nginx.com/nginx/admin-guide/load-balancer/http-load-balancer/
- Nginx `ngx_http_upstream_module`: https://nginx.org/en/docs/http/ngx_http_upstream_module.html
- HAProxy documentation: https://docs.haproxy.org/
- Envoy — Load balancing overview: https://www.envoyproxy.io/docs/envoy/latest/intro/arch_overview/upstream/load_balancing/overview
- AWS Elastic Load Balancing: https://docs.aws.amazon.com/elasticloadbalancing/
- RFC 7239 — Forwarded HTTP extension: https://www.rfc-editor.org/rfc/rfc7239
- HAProxy PROXY protocol specification: https://www.haproxy.org/download/2.8/doc/proxy-protocol.txt

---

**পরের lesson:** L02-13 — Network namespace, veth pair ও bridge
