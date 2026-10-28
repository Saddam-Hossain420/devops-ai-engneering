# L06-06 — Nginx caching ও compression

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L06-04 — Reverse proxy](L06-04-reverse-proxy-upstream.md), [L02-07 — HTTP](../02-computer-networking/L02-07-http.md) |
| **Label** | — |
| **Tested** | `cache_sim.py` ও `gzip_bench.py`: ৮টি test পাস (Python 3.14.5, Windows)। **আসলে মাপা হয়েছে:** gzip level ১/৫/৯-এ চার ধরনের data-র অনুপাত ও গতি (দুই run)। প্রথম সংস্করণের benchmark-এর সংখ্যা ৫ গুণ পর্যন্ত লাফাচ্ছিল — ঠিক করা হয়েছে (Section 9.3)। Cache-এর সিদ্ধান্ত nginx documentation-এর নিয়মের **অনুকরণ**। Stampede-এর সংখ্যা একটি সময়-**model** থেকে, আসল nginx-এর পরিমাপ নয়। nginx-এ কিছু **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- তিন স্তরের cache: browser (`Cache-Control`, `ETag`), proxy (nginx `proxy_cache`), application।
- nginx কখন একটি response cache করে, কতক্ষণ: `X-Accel-Expires` → `Cache-Control` → `Expires` → `proxy_cache_valid`; এবং কখন **কখনো নয়** (`Set-Cookie`, `private`, POST)।
- **সবচেয়ে বিপজ্জনক ভুল:** একজন user-এর ব্যক্তিগত page অন্য user-কে cache থেকে দেওয়া।
- Cache stampede, `proxy_cache_lock`, `proxy_cache_use_stale updating`।
- Static file-এর `expires` ও fingerprinted filename।
- gzip: কোন data compress হয়, কোনটা উল্টো বড় হয়; `gzip_comp_level`-এর বাস্তব trade-off; BREACH।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি জনপ্রিয় page প্রতি সেকেন্ডে ২০০ বার চাওয়া হয়, এবং প্রতিবার application ৮০০ ms-এর database query চালায়। Cache থাকলে ১৯৯টি request nginx নিজেই memory বা disk থেকে দেয়, application একবার কাজ করে।

একইভাবে, ১৬ KB-এর JSON gzip-এ ৭৪৩ byte হয় — mobile network-এ পার্থক্য বিশাল।

কিন্তু দুটোরই উল্টো দিক আছে:

- **ভুল cache:** user A-র "আমার account" page user B পায় — data breach।
- **Stampede:** cache মেয়াদোত্তীর্ণ হওয়ার মুহূর্তে ২০০টি request একসাথে database-এ।
- **অকারণ compression:** JPEG compress করতে CPU খরচ, অথচ file বড় হয়।

## 3. সহজ ভাষায় পরিচয়

```nginx
# http context
proxy_cache_path /var/cache/nginx/taskflow levels=1:2 keys_zone=tf:10m max_size=1g inactive=60m use_temp_path=off;
gzip on;
gzip_types application/json text/css application/javascript image/svg+xml;
gzip_min_length 256;
gzip_comp_level 5;

# location
location /public/ {
    proxy_cache tf;
    proxy_cache_valid 200 1m;
    proxy_cache_valid 404 10s;
    proxy_cache_lock on;
    proxy_cache_use_stale error timeout updating http_500 http_502 http_503;
    proxy_cache_bypass $http_authorization $cookie_session;
    proxy_no_cache     $http_authorization $cookie_session;
    add_header X-Cache-Status $upstream_cache_status always;
    proxy_pass http://taskflow_app;
}
location /static/ {
    expires 1y;                         # filename-এ hash থাকলে (app.3f9a1c.js)
    add_header Cache-Control "public, immutable";
}
```

| Response | nginx cache করবে? |
|---|---|
| `Cache-Control: max-age=60` | হ্যাঁ, ৬০ s |
| `Cache-Control: private` / `no-store` / `no-cache` | না |
| `Set-Cookie` আছে | না (default) |
| কোনো header নেই, `proxy_cache_valid 200 1m` | হ্যাঁ, ১ মিনিট |
| POST | না |
| `X-Accel-Expires: 30` + `max-age=600` | হ্যাঁ, **৩০ s** (X-Accel-Expires জেতে) |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্তোরাঁর আগে বানানো খাবার

- **Cache** = জনপ্রিয় পদ আগে থেকে বানিয়ে উষ্ণ রাখা — প্রতি order-এ নতুন রান্না নয়।
- **TTL** = কতক্ষণ পর্যন্ত বানানো খাবার পরিবেশনযোগ্য।
- **Stampede** = দুপুর ১টায় বানানো খাবার শেষ, আর ৫০ জন একসাথে এলেন — ৫০ জন রাঁধুনি একই পদ ৫০ বার রাঁধতে শুরু করলেন।
- **`proxy_cache_lock`** = একজন রাঁধুনি রাঁধেন, বাকিরা অপেক্ষা করেন।
- **`use_stale updating`** = নতুনটা রান্না হওয়ার সময় একটু আগের বানানোটা দিয়ে দেওয়া।

### Analogy কোথায় মেলে না

- **রেস্তোরাঁর খাবার সবার জন্য এক।** কিন্তু অনেক page user-ভেদে আলাদা (নাম, account, cart)। Cache-এর **key** (`proxy_cache_key`, default `$scheme$proxy_host$request_uri`) user-কে আলাদা করে না। তাই user-নির্দিষ্ট response cache হলে প্রথম user-এর page সবাই পায়। এটা analogy-তে নেই এমন একটি বাস্তব বিপদ — Section 5।
- **রান্না পুরোনো হলে গন্ধে বোঝা যায়।** Stale data দেখে বোঝা যায় না। Cache-এ পুরোনো দাম বা পুরোনো অনুমতি নীরবে চলতে থাকে — invalidation-এর পরিকল্পনা লাগে।
- **একজন রাঁধুনির অপেক্ষা মানে সবাই অপেক্ষা।** `proxy_cache_lock`-এ upstream-এ একটিই call যায়, কিন্তু বাকিরা ততক্ষণ অপেক্ষা করে (model-এ median ৭৭৫ ms)। `use_stale updating` তাদের সাথে সাথে পুরোনো copy দেয় — দ্রুত, কিন্তু কিছুক্ষণ পুরোনো data।

## 5. Real-world engineering scenario — "সবাই অন্য একজনের account দেখছে"

**পরিস্থিতি:** Traffic কমাতে একজন engineer `location /` জুড়ে `proxy_cache` চালু করলেন। সাথে দিলেন `proxy_ignore_headers Set-Cookie Cache-Control;` — কারণ "application সব কিছুতে `no-cache` দেয়, তাই cache কাজ করছিল না"।

কয়েক মিনিটের মধ্যে support-এ খবর এল: user-রা লগইন করে অন্য একজনের নাম, ঠিকানা ও order history দেখছেন। প্রথম user-এর `/account` page (তাঁর session cookie-সহ) cache-এ গিয়েছিল, এবং পরের সবাই সেটাই পেলেন — Set-Cookie-সহ, অর্থাৎ তাঁর **session**-ও।

`cache_sim.py` দিয়ে একই সিদ্ধান্ত (আসল output):

```text
--header 'Set-Cookie: session=abc' --valid 200=10m   NO CACHE  ← response has Set-Cookie (per-user data) — never cached unless ignored
--header 'Cache-Control: private, max-age=60'        NO CACHE  ← Cache-Control: private
```

nginx-এর default নিয়মগুলোই রক্ষা করছিল। `proxy_ignore_headers` সেই রক্ষাকবচ খুলে দিয়েছে।

**সঠিক পদ্ধতি:**

- শুধু নির্দিষ্ট public path-এ cache (`/public/`, `/static/`)।
- Authentication থাকলে bypass ও no_cache (`$http_authorization`, `$cookie_session`)।
- Application-কেই সঠিক `Cache-Control` দিতে দেওয়া।
- `X-Cache-Status` header দিয়ে যাচাই।
- TaskFlow নিজে প্রতিটি response-এ `Cache-Control: no-store` দেয় (L05-13) — নিরাপদ default।

**শিক্ষা:** Cache configuration একটি security সিদ্ধান্ত। `proxy_ignore_headers` লেখার আগে থামুন।

## 6. Diagram — cache-এর সিদ্ধান্ত ও অবস্থা

```text
 request GET /public/stats
   │ proxy_cache_bypass শর্ত সত্য? (Authorization, session cookie) ── হ্যাঁ ─► BYPASS → upstream
   │ key = $scheme$proxy_host$request_uri ── cache-এ আছে?
   │      ├─ আছে, fresh ───────────────────────────────────────────► HIT (upstream-এ যায় না)
   │      ├─ আছে, expired ─┬─ use_stale updating ─► STALE (পুরোনো) + background-এ একজন upstream-এ (UPDATING)
   │      │                └─ নইলে ─► EXPIRED → upstream (lock on হলে একজনই, বাকিরা অপেক্ষা)
   │      └─ নেই ─────────────────────────────────────────────────► MISS → upstream
   ▼
 upstream response → cache করা যাবে?
   POST? Set-Cookie? Cache-Control private/no-store/no-cache? Vary:*? proxy_no_cache? ── হ্যাঁ ─► রাখা হয় না
   TTL = X-Accel-Expires ▸ Cache-Control s-maxage/max-age ▸ Expires ▸ proxy_cache_valid
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| `proxy_cache_path` / `keys_zone` | Disk-এ cache-এর জায়গা / key-এর জন্য shared memory |
| Cache key | কোন request "একই" — default scheme + host + URI |
| TTL / freshness | কতক্ষণ cache-এর copy বৈধ |
| `$upstream_cache_status` | HIT, MISS, EXPIRED, STALE, UPDATING, BYPASS, REVALIDATED |
| Cache stampede / dog-pile | মেয়াদোত্তীর্ণের মুহূর্তে একসাথে বহু upstream call |
| `proxy_cache_lock` | একই key-এর জন্য একটিই upstream request |
| Stale-while-revalidate | পুরোনো copy দিয়ে background-এ নতুন আনা |
| `Vary` | কোন request header-এ response বদলায় (`Accept-Encoding`) |
| Fingerprinted asset | Filename-এ hash — বদলালে নতুন নাম, তাই দীর্ঘ cache নিরাপদ |
| gzip / Brotli | Text compression (Brotli-র জন্য nginx-এ আলাদা module) |
| BREACH | Compression + secret + user-নিয়ন্ত্রিত input থেকে secret অনুমানের আক্রমণ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 nginx-এর cache সিদ্ধান্ত

nginx documentation অনুযায়ী:

- `X-Accel-Expires` সবচেয়ে উপরে (application nginx-কে সরাসরি বলে)।
- তারপর `Cache-Control`। `no-store`, `no-cache`, `private` বা `max-age=0` থাকলে cache নয়।
- তারপর `Expires`।
- কিছু না থাকলে `proxy_cache_valid`।
- `Set-Cookie` থাকলে default-এ cache হয় না।
- `Vary: *` হলে হয় না।

`proxy_ignore_headers` এগুলোকে উপেক্ষা করাতে পারে — শক্তিশালী, এবং বিপজ্জনক।

`cache_sim.py decide` এই ক্রম অনুকরণ করে। এটা nginx নয় — Exercise ১-এ আসল nginx-এর `X-Cache-Status`-এর সাথে মেলান।

### 8.2 Stampede-এর model

`cache_sim.py stampede` একটি সরল সময়ের model: ২০০ জন ৫০ ms-এর মধ্যে আসেন; entry মেয়াদোত্তীর্ণ; upstream ৮০০ ms নেয়।

| কৌশল | Upstream call | Median অপেক্ষা |
|---|---|---|
| কিছু নয় | ২০০ | ৮০০ ms |
| `proxy_cache_lock on` | ১ | ৭৭৫ ms |
| `use_stale updating` | ১ | ০ ms |

এটা model-এর হিসাব, nginx-এ মাপা নয়। আসল nginx-এ `proxy_cache_lock_timeout` (default ৫ s) পেরোলে অপেক্ষমাণরাও upstream-এ যায়।

### 8.3 gzip কীভাবে

DEFLATE পুনরাবৃত্ত অংশ খুঁজে ছোট reference দিয়ে বদলায়। তাই:

- JSON-এর একই key বারবার → ৯৫% ছোট।
- এলোমেলো বা আগে-compressed data (JPEG, PNG, ZIP, video) → সামান্য **বড়** হয় (header ও block-এর overhead)।
- খুব ছোট response → header-এর ১৮ byte-এর কারণে বড় হয়।

তাই `gzip_types`-এ শুধু text-ধরনের type, আর `gzip_min_length`।

`Vary: Accept-Encoding` দরকার (`gzip_vary on;`), যাতে CDN বা অন্য cache gzip ও সাধারণ copy আলাদা রাখে।

### 8.4 BREACH

HTTPS-এর ভেতরেও response-এর **আকার** দেখা যায়। যদি একই response-এ থাকে:

- একটি secret (CSRF token), এবং
- user-নিয়ন্ত্রিত input (search query);

তাহলে আক্রমণকারী বারবার অনুমান পাঠিয়ে আকার কমা দেখে secret বের করতে পারে। প্রতিরোধ:

- Secret ও user input একই compressed response-এ না রাখা;
- প্রতি request-এ token-এর masking;
- প্রয়োজনে ওই endpoint-এ compression বন্ধ।

> **Fedora-তে:** `proxy_cache_path`-এর directory-তে SELinux context `httpd_cache_t` লাগে (`/var/cache/nginx` default-এ ঠিক থাকে; অন্য জায়গায় `semanage fcontext` + `restorecon`)।

## 9. Practical demonstration

Files: [`code/L06-06/cache_sim.py`](code/L06-06/cache_sim.py), [`gzip_bench.py`](code/L06-06/gzip_bench.py), [`test_l06_06.py`](code/L06-06/test_l06_06.py)।

### 9.1 Cache-এর সিদ্ধান্ত — আসল output

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-06
python3 cache_sim.py decide --header 'Cache-Control: max-age=60'
python3 cache_sim.py decide --header 'X-Accel-Expires: 30' --header 'Cache-Control: max-age=600'
python3 cache_sim.py decide --req-header 'Authorization: Bearer x' --no-cache-if Authorization --valid 200=10m
```

```text
CACHE     ttl=60s  ← Cache-Control: max-age=60
CACHE     ttl=30s  ← X-Accel-Expires (highest priority)
NO CACHE  ttl=0s  ← proxy_no_cache: request has Authorization
--valid 200=10m                               CACHE     ttl=600s  ← proxy_cache_valid for 200
--valid 200=10m --header 'Cache-Control: no-cache'   NO CACHE  ← Cache-Control: no-cache
--method POST --valid any=10m                 NO CACHE  ← method POST not in proxy_cache_methods
--status 404 --valid 200=10m                  NO CACHE  ← no caching headers and no proxy_cache_valid for 404
--header 'Vary: *' --valid 200=1m             NO CACHE  ← Vary: * — not cacheable
```

### 9.2 Stampede — আসল output (model)

```bash
python3 cache_sim.py stampede --clients 200 --upstream-ms 800
```

```text
200 clients within 50 ms on an expired entry, upstream takes 800 ms
  no lock                upstream calls  200   median wait    800 ms   max wait    800 ms
  proxy_cache_lock on    upstream calls    1   median wait  775.1 ms   max wait    800 ms
  use_stale updating     upstream calls    1   median wait    0.0 ms   max wait    800 ms
```

### 9.3 gzip — আসল পরিমাপ

```bash
python3 gzip_bench.py
```

```text
payload                           bytes   level 1          level 5          level 9
taskflow JSON (100 tasks)         16603      7%   1230 MB/s      4%    452 MB/s      5%    237 MB/s
lesson markdown (UTF-8 text)      29893     48%    433 MB/s     32%    130 MB/s     32%     42 MB/s
random bytes (like JPEG/ZIP)     200000    105%    115 MB/s    100%     51 MB/s    100%     68 MB/s
tiny JSON                            36    150%      9 MB/s    150%      7 MB/s    150%      7 MB/s
```

দ্বিতীয় run-এ গতি ৫–১৫% ভিন্ন, অনুপাত হুবহু একই। আসল byte সংখ্যা (level ১/৫/৬/৯):

```text
taskflow JSON (100 tasks) 16603 [1130, 743, 761, 759]
lesson markdown (UTF-8 text) 29893 [14476, 9625, 9566, 9535]
tiny JSON 36 [54, 54, 54, 54]
```

পর্যবেক্ষণ:

- **Level ৯ সবসময় ছোট নয়:** এই JSON-এ level ৫ (৭৪৩ byte) level ৯-এর (৭৫৯ byte) চেয়ে ছোট, অথচ level ৯ প্রায় দ্বিগুণ ধীর।
- Markdown-এ level ৯ level ৫-এর চেয়ে মাত্র ০.৯% ছোট, কিন্তু ৩ গুণ ধীর। তাই `gzip_comp_level` ৪–৬ সাধারণ পছন্দ। nginx-এর default ১।
- Random bytes ৫% **বড়** হয়েছে (level ১-এ), এবং ছোট JSON ৩৬ থেকে ৫৪ byte — compression উল্টো ফল দিয়েছে।
- Markdown-এ বাংলা UTF-8 (প্রতিটি অক্ষর ৩ byte) ৬৮% ছোট হয়েছে।

**লেখার সময় ঠিক করা:** প্রথম সংস্করণে প্রতিটি case ২০ বার চালানো হতো। ফলে একই JSON-এর level ১-এর গতি এক run-এ ৯৯৪ MB/s, পরের run-এ ২০১ MB/s — ১৬ KB-এ ২০ বার মোট কয়েক মিলিসেকেন্ড, যা timer ও scheduler-এর শব্দে ডুবে যায়। এখন প্রতিটি case কমপক্ষে ০.৩ s চলে। L00-06-এর শিক্ষা: পরিমাপ পুনরাবৃত্তি করে স্থিরতা যাচাই করুন।

### 9.4 Ubuntu-তে (চালানো হয়নি)

```bash
sudo mkdir -p /var/cache/nginx/taskflow && sudo chown www-data: /var/cache/nginx/taskflow
# Section 3-এর config যোগ করে:
sudo nginx -t && sudo systemctl reload nginx
for i in 1 2 3; do curl -s -o /dev/null -D - -H 'Host: taskflow.example.com' http://127.0.0.1/public/stats | grep -i x-cache; done
#   X-Cache-Status: MISS → HIT → HIT   (app-কে Cache-Control: no-store না দিয়ে, public endpoint-এ)
curl -s -o /dev/null -D - -H 'Host: taskflow.example.com' -H 'Authorization: Bearer x' http://127.0.0.1/public/stats | grep -i x-cache
#   X-Cache-Status: BYPASS
curl -s -H 'Accept-Encoding: gzip' -o /dev/null -w '%{size_download}\n' -H 'Host: taskflow.example.com' http://127.0.0.1/tasks?limit=100
curl -s -o /dev/null -w '%{size_download}\n' -H 'Host: taskflow.example.com' http://127.0.0.1/tasks?limit=100
```

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- অগ্রাধিকার (X-Accel-Expires, s-maxage, Expires, valid)।
- আট রকম "কখনো নয়"।
- TaskFlow-এর `no-store`।
- `proxy_ignore_headers` ও bypass।
- Duration।
- Stampede-এর তিন কৌশল।
- কোন data compress হয়, কোনটা বড় হয়।
- Benchmark function।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `decide()`-এর ক্রম | documentation-এর অগ্রাধিকার | X-Accel-Expires → CC → Expires → valid |
| `set-cookie` আগে যাচাই | Per-user response বাদ | Section 5 |
| `cfg.ignore` | `proxy_ignore_headers` | কী উপেক্ষা হলে কী হয় দেখা |
| `no_cache_if` | `proxy_no_cache $http_authorization` | Authenticated request cache নয় |
| `stampede()` — arrival list | সরল সময়-model | কৌশলগুলোর পার্থক্য সংখ্যায় |
| `bench(min_seconds)` | সময়-ভিত্তিক পুনরাবৃত্তি | ছোট input-এ শব্দ কমানো |
| `mtime=0` | gzip output নির্ধারিত | Header-এ সময় না থাকলে byte-তুলনা স্থির |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `decide --header 'Set-Cookie: …' --valid 200=10m` | NO CACHE |
| `stampede` | ২০০ / ১ / ১ upstream call |
| `gzip_bench.py` | JSON ~৪–৭%, random ≥১০০%, tiny ১৫০% |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| সব সময় `MISS` | App `no-store`/`Set-Cookie` দেয়, বা `proxy_cache` zone ভুল | `X-Cache-Status`; app-এর header |
| একজনের page অন্যজন দেখে | User-নির্দিষ্ট response cache | Bypass/no_cache; `proxy_ignore_headers` সরান |
| পুরোনো data সরছে না | দীর্ঘ TTL, invalidation নেই | ছোট TTL; filename-এ hash; purge (commercial বা নিজের) |
| Cache directory-তে permission error | Owner ভুল | `chown www-data`; Fedora-তে SELinux |
| gzip কাজ করছে না | `gzip_types`-এ `application/json` নেই | যোগ করুন (`text/html` default-এ থাকে) |
| CPU বেশি | উচ্চ `gzip_comp_level` বা image compress | ৪–৬; শুধু text type |
| CDN-এ ভুল encoding | `Vary` নেই | `gzip_vary on` |
| Stampede-এ database পড়ে যায় | Lock/stale নেই | `proxy_cache_lock`, `use_stale updating` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - User-নির্দিষ্ট data cache করবেন না।
  - `proxy_ignore_headers Set-Cookie` প্রায় কখনো নয়।
  - Cache key-এ অপ্রত্যাশিত header (Host-এর ভিন্নতা) — cache poisoning-এর ঝুঁকি; `proxy_cache_key` সচেতনভাবে।
  - BREACH-এর জন্য secret-যুক্ত response-এ সতর্কতা।
- **Performance:**
  - HIT-এ upstream-এর খরচ শূন্য।
  - `use_stale` application বিভ্রাটে-ও সেবা চালু রাখে (`error timeout http_502`)।
  - gzip text-কে ৫০–৯৫% ছোট করে; level ৫ যথেষ্ট।
  - Static file-এ `expires` + fingerprint।
- **Cost:**
  - Egress (বাইরের data transfer) cloud-এ সবচেয়ে বড় খরচগুলোর একটি — compression ও browser cache সরাসরি বিল কমায়।
  - Cache disk-এর আকার (`max_size`) সীমিত রাখুন।
  - CDN (Module 08) cache-কে user-এর কাছে নিয়ে যায়।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.4 চালিয়ে `cache_sim.py`-এর ফলের সাথে `X-Cache-Status` মেলান — অন্তত পাঁচটি case।
2. TaskFlow-এ `GET /public/stats` endpoint যোগ করুন (task-এর মোট সংখ্যা), যা `Cache-Control: public, max-age=30` দেয়। nginx-এ cache করে `ab -n 1000 -c 50` দিয়ে HIT-এর হার মাপুন।
3. `gzip_bench.py`-এ Brotli যোগ করুন (venv-এ `brotli` package)। একই level-এর তুলনায় কতটা ছোট?
4. `cache_sim.py`-এ `proxy_cache_lock_timeout` যোগ করুন: অপেক্ষা `T` ms-এর বেশি হলে অপেক্ষমাণরাও upstream-এ যায়। Upstream ৮ s হলে কী হয়?
5. একটি page-এ CSRF token ও search query একসাথে রেখে BREACH-এর মূল ধারণা দেখুন: query-তে token-এর সঠিক অনুমান দিলে gzip আকার কমে কিনা।

## 15. Mini-project — Cache policy reviewer

`cache_review.py nginx.conf` (L06-02-এর parser দিয়ে):

- `proxy_cache` আছে এমন প্রতিটি location-এ bypass/no_cache (Authorization, session cookie) আছে কিনা।
- `proxy_ignore_headers`-এ Set-Cookie থাকলে error।
- `use_stale`/`lock` না থাকলে warning।
- `gzip_types`-এ image type থাকলে warning।

Lab 06-B ও L06-08-এর audit-এ যোগ হবে।

## 16. Interview প্রশ্ন

1. nginx কোন response cache করে, এবং TTL কীভাবে ঠিক হয়?
2. Cache stampede কী, এবং কীভাবে ঠেকাবেন?
3. User-নির্দিষ্ট page cache হয়ে গেলে কী হয়? কীভাবে প্রতিরোধ করবেন?
4. `Cache-Control: no-cache` ও `no-store`-এর পার্থক্য কী?
5. gzip কোন data-য় লাভ দেয় না? `gzip_comp_level` কত রাখবেন, কেন?
6. BREACH আক্রমণ কী?

## 17. Self-assessment প্রশ্ন

1. রেস্তোরাঁ analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ কোন একটি লাইন রক্ষাকবচ খুলে দিয়েছিল?
3. `proxy_cache_lock` ও `use_stale updating`-এর পার্থক্য কী (model-এর সংখ্যায়)?
4. Level ৯ কেন সবসময় ভালো নয়?
5. Benchmark-এর প্রথম সংস্করণে সংখ্যা কেন লাফাচ্ছিল?

## 18. সংক্ষিপ্ত সারাংশ

- nginx-এর ক্রম: X-Accel-Expires → Cache-Control → Expires → proxy_cache_valid; Set-Cookie/private/POST কখনো নয়।
- শুধু public path cache করুন; authenticated request bypass; `proxy_ignore_headers`-এ সতর্কতা।
- Stampede: `proxy_cache_lock` + `use_stale updating`।
- gzip: text-এ, level ৪–৬, `gzip_min_length`, `gzip_vary`; image/zip নয়।
- Static: fingerprinted filename + দীর্ঘ `expires`।

## 19. Completion checklist

- [ ] ১০টি response-এর cache সিদ্ধান্ত নিজে অনুমান করে `cache_sim.py`-এ মিলিয়েছি
- [ ] gzip benchmark নিজের machine-এ চালিয়ে level বেছে নেওয়ার যুক্তি লিখেছি
- [ ] (Ubuntu) `X-Cache-Status` দিয়ে MISS → HIT → BYPASS দেখেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nginx — `proxy_cache`, `proxy_cache_valid`, `proxy_cache_lock`, `proxy_cache_use_stale`: https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- nginx — `ngx_http_gzip_module`: https://nginx.org/en/docs/http/ngx_http_gzip_module.html
- nginx — `ngx_http_headers_module` (`expires`, `add_header`): https://nginx.org/en/docs/http/ngx_http_headers_module.html
- RFC 9111 — HTTP Caching: https://www.rfc-editor.org/rfc/rfc9111
- RFC 1952 — GZIP file format: https://www.rfc-editor.org/rfc/rfc1952
- MDN — HTTP caching: https://developer.mozilla.org/en-US/docs/Web/HTTP/Caching
- BREACH attack: https://www.breachattack.com/

---

**পরের lesson:** L06-07 — Nginx-এ TLS ও certificate
