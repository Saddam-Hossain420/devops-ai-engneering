# L06-02 — Nginx architecture: master, worker, event loop

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L06-01 — DNS](L06-01-dns-records-domains.md), [L01-08 — Process ও signal](../01-linux-systems/L01-08-processes-signals.md), [L02-05 — TCP/UDP ও socket](../02-computer-networking/L02-05-tcp-udp-sockets.md) |
| **Label** | — |
| **Tested** | `nginx_conf.py` ও `event_loop_demo.py`: ৮টি test পাস (Python 3.14.5, Windows)। আসলে মাপা হয়েছে: ধীর client-দের মধ্যে একটি সাধারণ request-এর সময় — event loop-এ ১.২–১৮ ms, ২০ worker-এর thread pool-এ ২,৬৯৯ ms, এবং ৫০০ ধীর client-এ **৩০ s-এও উত্তর নেই**। লেখার সময় ধরা পড়েছে বন্ধ না করা socket (ResourceWarning)। **nginx এই machine-এ নেই** — Section 9.5-এর `nginx`/`ps`/`ss` command Ubuntu-তে চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- nginx-এর process মডেল: **master** (root, config পড়ে, port bind করে) ও **worker** (unprivileged, request সামলায়)।
- **Event loop** (epoll): একটি worker হাজার connection — কেন thread-per-connection-এর চেয়ে ভালো, এবং কোথায় খারাপ।
- `worker_processes`, `worker_connections`, `worker_rlimit_nofile` — capacity-র হিসাব ও "Too many open files"।
- Config-এর কাঠামো: context (main, events, http, server, location), directive, inheritance, `include`।
- Signal: `nginx -t`, `nginx -s reload` (zero-downtime reload কীভাবে), graceful shutdown।
- Ubuntu-র file layout: `/etc/nginx/nginx.conf`, `sites-available`/`sites-enabled`, `conf.d`, log।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

TaskFlow (L05-13) সরাসরি internet-এ খোলা যায় না। এর কারণ:

- `http.server` ধীর client-এ সহজেই আটকে যায় (Section 9.3)।
- TLS নেই, static file দক্ষভাবে দেয় না।
- এক port-এ একাধিক site বা app চালাতে পারে না।

nginx সামনে বসে এই কাজগুলো করে: হাজার connection ধরে রাখে, TLS শেষ করে, static file দেয়, এবং application-কে শুধু সম্পূর্ণ, যাচাই-করা request পাঠায়।

এর জন্য nginx-এর ভেতরের মডেল বোঝা জরুরি। "এখন কত user সামলাতে পারবে?", "reload-এ কি connection কাটবে?", "`worker_connections exceed open file resource limit`"-এর মানে কী — এসবের উত্তর এই lesson-এ।

## 3. সহজ ভাষায় পরিচয়

```text
$ ps -o pid,user,cmd -C nginx          (Ubuntu, উদাহরণ — চালানো হয়নি)
  PID USER     CMD
  801 root     nginx: master process /usr/sbin/nginx -g daemon on; master_process on;
  802 www-data nginx: worker process
  803 www-data nginx: worker process
```

| Process | User | কাজ |
|---|---|---|
| Master | root | Config পড়া ও যাচাই; port ৮০/৪৪৩ bind (privileged port); worker চালু/বদল; signal গ্রহণ |
| Worker (CPU প্রতি একটি) | `www-data` | Connection accept, request পড়া, response, proxy — সব event loop-এ |
| Cache manager/loader | `www-data` | `proxy_cache` থাকলে disk cache (L06-06) |

```nginx
worker_processes auto;            # সাধারণত CPU core-এর সমান
events { worker_connections 4096; }
http {
    server {                      # virtual host (L06-03)
        location / { … }          # URL অনুযায়ী নিয়ম
    }
}
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্তোরাঁর waiter

- **Thread-per-connection** (Apache prefork-এর মতো) = প্রতিটি টেবিলে একজন waiter, যিনি খদ্দের মেনু পড়া শেষ না করা পর্যন্ত পাশে দাঁড়িয়ে থাকেন। ২০ জন waiter, ২০টি টেবিলে ধীর খদ্দের — ২১তম খদ্দের দরজায় দাঁড়িয়ে।
- **Event loop** (nginx) = একজন waiter পুরো হল সামলান: যে টেবিলে কেউ হাত তুলেছে (event), শুধু সেখানে যান। ধীর খদ্দের মেনু পড়ছেন — waiter অন্যদের সেবা দিচ্ছেন।
- **Master** = ম্যানেজার, যিনি নিজে পরিবেশন করেন না। নতুন মেনু (config) আসলে নতুন waiter-দের দায়িত্ব দেন। পুরোনো waiter-রা হাতের order শেষ করে বিদায় নেন — reload।

### Analogy কোথায় মেলে না

- **একজন waiter যদি রান্নাঘরে গিয়ে রান্না শুরু করেন, পুরো হল অপেক্ষা করে।** Event loop-এ কোনো blocking কাজ (ধীর disk read, ভারী CPU কাজ, blocking DNS lookup) পুরো worker-এর সব connection থামিয়ে দেয়। nginx তাই disk I/O-র জন্য thread pool (`aio threads`) ও নিজস্ব async resolver রাখে। Python-এ event loop লিখলে এই ভুল সহজেই হয়।
- **হলে টেবিলের সংখ্যা অসীম নয়।** প্রতিটি connection একটি file descriptor। OS-এর open-file সীমা (`ulimit -n`, systemd-এর `LimitNOFILE`) `worker_connections`-এর চেয়ে কম হলে আগেই আটকে যায়। Proxy করলে প্রতিটি client **দুটি** connection নেয় (client ↔ nginx ↔ upstream)।
- **নতুন waiter এলে পুরোনো চলে যান — সাথে সাথে নয়।** Reload-এ পুরোনো worker চলমান request শেষ করে বের হয়। কিন্তু দীর্ঘ connection (WebSocket, বড় download) থাকলে পুরোনো worker অনেকক্ষণ থাকতে পারে, ফলে দুই config-এর worker একসাথে চলে, memory দ্বিগুণ হয় (`worker_shutdown_timeout`)।

## 5. Real-world engineering scenario — "Flash sale-এ site দাঁড়িয়ে গেল, CPU ২০%"

**পরিস্থিতি:** একটি flash sale-এ traffic দশ গুণ হলো। Site-এ নতুন connection লাগছিল না, অথচ CPU ২০%, memory অর্ধেক খালি। nginx-এর error log-এ:

```text
[alert] … socket() failed (24: Too many open files) while connecting to upstream
[warn]  … 4096 worker_connections exceed open file resource limit: 1024
```

দ্বিতীয় লাইনটি মাসের পর মাস প্রতিটি restart-এ log হচ্ছিল, কিন্তু কেউ দেখেনি।

**কারণ:** `worker_connections 4096`, কিন্তু systemd-এর default soft limit ১০২৪ open file। Proxy-তে প্রতিটি client = ২টি fd, তাই একটি worker সর্বোচ্চ ~৫০০ client। চারটি worker ≈ ২,০০০ — `nginx_conf.py capacity` ঠিক এই হিসাব দেয় (Section 9.2)।

**সমাধান:**

- `worker_rlimit_nofile 65535;` (main context), অথবা systemd override `LimitNOFILE=65535`।
- Upstream-এর সাথে keepalive (L06-04), যাতে প্রতিটি request-এ নতুন connection না লাগে।
- Load test (Module 18) — sale-এর **আগে**।

**শিক্ষা:** Capacity শুধু CPU ও memory নয় — file descriptor, ephemeral port, upstream-এর connection-ও। আর `[warn]` log পড়ুন।

## 6. Diagram — process ও event loop

```text
                       ┌───────────────── master (root) ─────────────────┐
  SIGHUP (reload) ───► │ config পড়া → nginx -t-এর মতো যাচাই → নতুন worker  │
  SIGQUIT (graceful)   │ :80/:443 socket bind (একবার) → worker-রা উত্তরাধিকার │
                       └───────┬──────────────────────┬──────────────────┘
                     fork      │                      │      fork
              ┌──────── worker 1 (www-data) ──┐   ┌── worker 2 ──┐  … (CPU প্রতি একটি)
              │ epoll_wait() ─► ready events:  │
              │   fd 12 readable → request পড়া│     প্রতিটি worker স্বাধীন;
              │   fd 40 writable → response    │     shared: শুধু listen socket,
              │   fd 51 upstream readable      │     cache zone, limit_req zone
              │ কোনো কাজ blocking নয় ─► আবার    │
              │ epoll_wait()                   │
              └────────────────────────────────┘

 reload: নতুন worker (নতুন config) accept শুরু ─► পুরোনো worker আর accept করে না,
         চলমান request শেষ করে বের হয় ─► কোনো connection কাটা পড়ে না
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Master process | Root; config, bind, worker পরিচালনা |
| Worker process | Unprivileged; request সামলায় |
| Event loop | Ready event-এর অপেক্ষা ও প্রক্রিয়া, blocking নয় |
| epoll / kqueue | Linux / BSD-এর হাজার fd-এর event জানার system call |
| Non-blocking I/O | Data না থাকলে অপেক্ষা না করে সাথে সাথে ফেরত |
| File descriptor (fd) | Process-এর খোলা file/socket-এর নম্বর |
| `worker_connections` | প্রতি worker-এ সর্বোচ্চ connection (client ও upstream মিলিয়ে) |
| Context | `main`, `events`, `http`, `server`, `location` — directive কোথায় বৈধ |
| Inheritance | বাইরের context-এর directive ভেতরে প্রযোজ্য, যদি না ভেতরে আবার ঘোষিত |
| Graceful reload | নতুন config-এ নতুন worker, পুরোনো worker কাজ শেষ করে বিদায় |
| Slowloris | ধীরে header পাঠিয়ে server-এর connection আটকে রাখা আক্রমণ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 কেন master root, worker নয়

১০২৪-এর নিচের port-এ bind করতে privilege লাগে, এবং TLS private key পড়তেও। Master এগুলো একবার করে, তারপর worker-রা `user www-data`-তে চলে। ফলে worker-এ কোনো bug থাকলেও আক্রমণকারী root পায় না (L01-04-এর least privilege)।

### 8.2 Event loop

প্রতিটি worker সব socket non-blocking রাখে, এবং `epoll_wait()` দিয়ে জিজ্ঞেস করে "কোনগুলো প্রস্তুত?"। ধীর client-এর socket-এ data না এলে সে তালিকায় আসেই না — কোনো thread তার জন্য বসে থাকে না। তাই হাজার idle connection-এর খরচ শুধু কিছু memory (buffer), কোনো thread বা stack নয়।

`event_loop_demo.py` একই ধারণা Python-এর `selectors` দিয়ে দেখায় (Section 9.3)।

### 8.3 Capacity-র হিসাব

```text
max connections = worker_processes × min(worker_connections, open-file limit)
max clients ≈ max connections / 2          (reverse proxy — প্রতিটি client-এর একটি upstream connection)
```

Static file-এ client প্রতি ১টি। Keepalive connection idle থাকলেও একটি slot নেয়।

Open-file সীমা `worker_rlimit_nofile` (nginx নিজে বাড়ায়) বা systemd-এর `LimitNOFILE`। আর kernel-এর `fs.file-max`/`fs.nr_open`।

### 8.4 Reload ও signal

| Command | Signal | কী হয় |
|---|---|---|
| `nginx -t` | — | Config syntax ও file যাচাই; কিছু চালায় না |
| `nginx -s reload` / `systemctl reload nginx` | HUP | যাচাই সফল হলে নতুন worker; ব্যর্থ হলে পুরোনো config-এই চলতে থাকে |
| `nginx -s quit` | QUIT | Graceful: চলমান request শেষ, তারপর বন্ধ |
| `nginx -s stop` | TERM | দ্রুত বন্ধ |
| `kill -USR1` | USR1 | Log file আবার খোলা (logrotate — L01-14) |

**নিয়ম:** সবসময় আগে `nginx -t`, তারপর reload। `restart` নয় — restart সব connection কেটে দেয়।

### 8.5 Inheritance-এর একটি ফাঁদ

কিছু "array" ধরনের directive (`add_header`, `proxy_set_header`) ভেতরের context-এ একটিও ঘোষিত হলে, বাইরের **সবগুলো হারিয়ে যায়** — যোগ হয় না। `server`-এ `add_header Strict-Transport-Security …` আর একটি `location`-এ `add_header Cache-Control …` দিলে, সেই location-এ HSTS আর থাকে না। এটা L06-06 ও L06-07-এ আবার আসবে।

> **Fedora-তে:** `dnf install nginx`; config `/etc/nginx/nginx.conf` + `conf.d/*.conf` (`sites-available`/`sites-enabled` নেই)। Worker user `nginx` (Ubuntu-তে `www-data`)। SELinux: nginx-কে upstream-এ connect করতে `setsebool -P httpd_can_network_connect 1` লাগে (L01-17)।

## 9. Practical demonstration

Files:

- [`code/L06-02/nginx_conf.py`](code/L06-02/nginx_conf.py)।
- [`sample-nginx.conf`](code/L06-02/sample-nginx.conf) + [`conf.d/taskflow.conf`](code/L06-02/conf.d/taskflow.conf) (হাতে তৈরি)।
- [`event_loop_demo.py`](code/L06-02/event_loop_demo.py)।
- [`test_l06_02.py`](code/L06-02/test_l06_02.py)।

### 9.1 Config parse

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-02
python3 nginx_conf.py dump sample-nginx.conf
python3 nginx_conf.py get sample-nginx.conf proxy_pass
```

**আসল output (সংক্ষেপিত):**

```text
user www-data   # sample-nginx.conf:2
worker_processes auto   # sample-nginx.conf:3
events  {   # sample-nginx.conf:7
  worker_connections 4096   # sample-nginx.conf:8
http  {   # sample-nginx.conf:12
  …
  server  {   # taskflow.conf:2                 ← include conf.d/*.conf থেকে
    listen 80   # taskflow.conf:3
    location / {   # taskflow.conf:5
      proxy_pass http://127.0.0.1:8000   # taskflow.conf:6

http/server/location: proxy_pass http://127.0.0.1:8000   (taskflow.conf:6)
```

ভুল config-এ nginx-এর মতো বার্তা আসে, যেমন `directive 'worker_connections' is not terminated by ';'`। Quote-এর ভেতরের `;`, `#` ও `{}` আক্ষরিক থাকে।

### 9.2 Capacity — Section 5-এর হিসাব

```bash
python3 nginx_conf.py capacity sample-nginx.conf --cpus 4 --nofile 1024
```

```text
{
  "workers": 4,
  "worker_connections": 4096,
  "fd_limit_per_worker": 1024,
  "max_connections": 4096,
  "max_clients_estimate": 2048,
  "proxied": true,
  "notes": ["worker_connections 4096 > open-file limit 1024: workers will hit 'Too many open files' first — raise worker_rlimit_nofile / LimitNOFILE"]
}
```

কাগজে ৪ × ৪০৯৬ = ১৬,৩৮৪ connection, বাস্তবে ৪,০৯৬, এবং proxy-তে ~২,০৪৮ client।

### 9.3 Event loop বনাম thread pool — আসল পরিমাপ

```bash
python3 event_loop_demo.py                       # ২০ ধীর client, ২০ worker
python3 event_loop_demo.py --slow 19 --workers 20
python3 event_loop_demo.py --slow 500 --workers 20
```

```text
20 slow clients, 20 worker threads (threaded), header timeout 3.0s
event     normal request answered in      1.2 ms   (python threads alive: 2)
threaded  normal request answered in   2699.0 ms   (python threads alive: 22)

19 slow clients, 20 worker threads (threaded), header timeout 3.0s
event     normal request answered in     24.4 ms   (python threads alive: 2)
threaded  normal request answered in     13.5 ms   (python threads alive: 21)

500 slow clients, 20 worker threads (threaded), header timeout 3.0s
event     normal request answered in     11.7 ms   (python threads alive: 2)
threaded  normal request NO ANSWER within 30 s   (python threads alive: 22)
```

পর্যবেক্ষণ:

- **Cliff-টা ঠিক worker সংখ্যায়।** ১৯টি ধীর client-এ thread pool-ও দ্রুত, ২০টিতে ২.৭ s (ধীর client-দের header timeout পর্যন্ত)।
- **৫০০ ধীর client** (একজন আক্রমণকারী সহজেই খুলতে পারে) thread pool-কে সম্পূর্ণ অকেজো করেছে: ২৫ দফা × ৩ s = ৭৫ s। Event loop তখনো ~১২ ms।
- Event server-এ thread মাত্র ২টি (main + loop), connection সংখ্যা যাই হোক।
- Event loop-এর সময় একেক run-এ ১–২৪ ms ভিন্ন হয়েছে — Windows-এর scheduling-এর শব্দ; ক্রম (ms বনাম s) স্থির।

এটাই TaskFlow-এর `ThreadingHTTPServer`-এর সামনে nginx রাখার কারণ: nginx পুরো header ও body নিজে সংগ্রহ করে (buffering), তারপর upstream-এ পাঠায় — ধীর client application-এর thread আটকায় না।

### 9.4 লেখার সময় ঠিক করা সমস্যা

Test-এ দেখা গেল `ResourceWarning: unclosed <socket … laddr=('127.0.0.1', 57176) …>`। Server বন্ধের সময় যে connection-গুলো তখনো event loop-এর state-এ ছিল, বা thread pool-এর queue-তে অপেক্ষা করছিল (কখনো শুরুই হয়নি), সেগুলো বন্ধ হচ্ছিল না। এখন দুটোই বন্ধ হয়। `python3 -W error::ResourceWarning -m unittest` পরিষ্কার।

এটা একটি দীর্ঘ-চলা server-এ fd leak-এর ছোট রূপ — Section 5-এর "Too many open files"-এর আরেকটি পথ।

### 9.5 Ubuntu-তে (চালানো হয়নি)

```bash
sudo apt install nginx
ps -o pid,user,cmd -C nginx                      # master root, worker www-data
sudo nginx -T | head -40                         # পুরো effective config (include সহ)
grep -i "open file\|worker_connections" /var/log/nginx/error.log
cat /proc/$(pgrep -f 'nginx: worker' | head -1)/limits | grep 'open files'
sudo nginx -t && sudo systemctl reload nginx     # PID বদলায় শুধু worker-এর
ps -o pid,cmd -C nginx
sudo ss -ltnp 'sport = :80'                      # কোন process port ৮০ ধরে আছে
```

`python3 nginx_conf.py dump /etc/nginx/nginx.conf`-এর ফল `nginx -T`-এর সাথে মিলিয়ে দেখুন।

### 9.6 Test

```bash
python3 -m unittest -v
```

৮টি test:

- Include-সহ নমুনা।
- Quote, comment ও regex।
- nginx-এর মতো ৫ ধরনের error।
- Include glob — খালি glob error নয়, অনুপস্থিত file error।
- Capacity (fd সীমাসহ ও ছাড়া)।
- CLI।
- **ধীর client-এ thread pool আটকায়, event loop নয়।**
- একটি খালি worker যথেষ্ট।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `tokenize` — quoted flag | Quote-এর ভেতরের `;`/`{` আক্ষরিক | `return 200 "{}"` |
| শব্দের মাঝের `#` | Comment নয় | nginx-এর নিয়ম (`a#b` একটি শব্দ) |
| `include` + `glob` | Config-এর directory-র সাপেক্ষে | খালি glob ঠিক আছে, নির্দিষ্ট file না থাকলে error |
| `depth > 10` | Include loop | অনন্ত recursion নয় |
| `capacity()` — `min(wc, rlimit)` | fd সীমা | Section 5 |
| `// 2` proxied | Client প্রতি ২টি connection | Upstream connection |
| `selectors.DefaultSelector` | OS-এর সেরা পদ্ধতি (epoll/kqueue/select) | nginx-এর event loop-এর ছোট রূপ |
| Header timeout দুই server-এ | `client_header_timeout`-এর মতো | ন্যায্য তুলনা |
| বন্ধে বাকি socket close | fd leak নয় | Section 9.4 |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `nginx_conf.py dump sample-nginx.conf` | include-এর server block-সহ tree |
| `capacity --cpus 4 --nofile 1024` | max_connections ৪০৯৬, note-এ সতর্কতা |
| `event_loop_demo.py` | event কয়েক ms, threaded ~২.৭ s |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `Too many open files` | fd সীমা < connection | `worker_rlimit_nofile`, `LimitNOFILE` |
| `bind() to 0.0.0.0:80 failed (98: Address already in use)` | অন্য process (Apache) | `ss -ltnp 'sport = :80'` |
| Reload-এর পরে পরিবর্তন দেখা যাচ্ছে না | `nginx -t` ব্যর্থ, পুরোনো config চলছে | `nginx -t`; `journalctl -u nginx` |
| Reload-এর পরে memory দ্বিগুণ | দীর্ঘ connection-এ পুরোনো worker | `worker_shutdown_timeout` |
| একটি location-এ security header হারিয়ে গেছে | `add_header` inheritance | Header আবার ঘোষণা, বা snippet `include` |
| CPU কম, তবুও ধীর | Blocking কাজ বা upstream ধীর | `$upstream_response_time` log (L06-04) |
| Fedora-তে upstream 502, log-এ `Permission denied` | SELinux | `httpd_can_network_connect` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Worker unprivileged; master-এর root শুধু bind ও key-এর জন্য।
  - `server_tokens off;` (version লুকানো)।
  - Slowloris-ধাঁচের আক্রমণে `client_header_timeout`, `client_body_timeout`, `limit_conn`, `limit_req` (L06-08)।
  - Config file-এর মালিক root, এবং অন্যরা লিখতে পারবে না।
- **Performance:**
  - `worker_processes auto`।
  - `sendfile on` (kernel থেকে সরাসরি file → socket)।
  - Keepalive।
  - Blocking এড়ান।
  - Upstream connection reuse (L06-04)।
- **Cost:**
  - একটি ছোট VM-এ nginx হাজার connection সামলায়। Application server-এর সংখ্যা ও আকার কমানো যায়, কারণ ধীর client-এর বোঝা nginx নেয়।
  - Load test দিয়ে instance-এর আকার ঠিক করুন, অনুমানে নয় (Module 29)।

## 14. Hands-on exercise

1. Ubuntu-তে nginx install করে Section 9.5 চালান। Worker-এর `open files` সীমা কত? `error.log`-এ সতর্কতা আছে কি?
2. `systemctl edit nginx`-এ `LimitNOFILE=65535` দিয়ে reload করুন। Worker-এর `/proc/…/limits` আবার দেখুন — reload-এ বদলাল, নাকি restart লাগল? কেন?
3. `event_loop_demo.py`-এ event server-এর handler-এ `time.sleep(0.5)` (blocking কাজ) যোগ করে ১০টি সাধারণ request একসাথে পাঠান। কী হয়? Section 4-এর প্রথম সতর্কতার সাথে মেলান।
4. `nginx_conf.py`-এ একটি `lint` subcommand যোগ করুন: `add_header` ভেতরের context-এ থাকলে, বাইরের header হারানোর সতর্কতা।
5. TaskFlow (L05-13) চালিয়ে `event_loop_demo.py`-এর মতো ২০০টি ধীর connection খুলুন, এবং একটি `curl /health`-এর সময় মাপুন। (শুধু localhost-এ, নিজের process-এ।)

## 15. Mini-project — nginx config explorer

`nginx_conf.py`-কে বাড়ান:

- `effective` subcommand: একটি নির্দিষ্ট `server_name` ও URL-এর জন্য কোন location মিলবে (L06-03-এর নিয়ম), এবং সেখানে কার্যকর directive-গুলো (inheritance মেনে)।
- `diff old.conf new.conf`: reload-এর আগে কী বদলাচ্ছে।

Lab 06-C-তে ভুল config খুঁজতে এটা কাজে লাগবে।

## 16. Interview প্রশ্ন

1. nginx-এর master ও worker process-এর ভূমিকা কী? কেন আলাদা user?
2. Event-driven architecture কীভাবে হাজার connection সামলায়? এর দুর্বলতা কী?
3. `worker_connections` ও open-file limit-এর সম্পর্ক কী?
4. `nginx -s reload` কীভাবে zero-downtime?
5. Slowloris আক্রমণ কী? nginx কীভাবে রক্ষা করে?
6. `add_header`-এর inheritance-এর সমস্যা কী?

## 17. Self-assessment প্রশ্ন

1. Waiter analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ CPU কম থাকা সত্ত্বেও site কেন দাঁড়াল?
3. ১৯ বনাম ২০টি ধীর client-এ thread pool-এর আচরণে এত বড় পার্থক্য কেন?
4. Proxy-তে client প্রতি দুটি connection কেন?
5. Reload ও restart-এর পার্থক্য কী?

## 18. সংক্ষিপ্ত সারাংশ

- Master (root: config, bind) + worker (unprivileged: event loop)।
- Event loop ধীর client-এ আটকায় না, কিন্তু blocking কাজে পুরো worker থামে।
- Capacity = worker × min(worker_connections, fd সীমা); proxy-তে ÷ ২।
- সবসময় `nginx -t`, তারপর `reload` (restart নয়)।
- `add_header`/`proxy_set_header`-এর inheritance: ভেতরে একটি দিলে বাইরের সব হারায়।

## 19. Completion checklist

- [ ] Event loop বনাম thread pool-এর পরীক্ষা চালিয়ে cliff দেখেছি
- [ ] Capacity হিসাব করতে পারি, fd সীমাসহ
- [ ] (Ubuntu) master/worker, reload-এ PID বদল ও worker-এর limits দেখেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nginx — Beginner's Guide: https://nginx.org/en/docs/beginners_guide.html
- nginx — Controlling nginx (signals, reload): https://nginx.org/en/docs/control.html
- nginx — Core functionality (`worker_processes`, `worker_connections`, `worker_rlimit_nofile`): https://nginx.org/en/docs/ngx_core_module.html
- nginx — Connection processing methods: https://nginx.org/en/docs/events.html
- Python — `selectors`: https://docs.python.org/3/library/selectors.html
- Linux man page — `epoll(7)`: https://man7.org/linux/man-pages/man7/epoll.7.html

---

**পরের lesson:** L06-03 — Nginx server block (virtual host)
