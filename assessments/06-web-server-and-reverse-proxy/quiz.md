# Module 06 Quiz — Web Server and Reverse Proxy

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৭৫ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে tool না চালিয়ে উত্তর দিন, পরে module-এর tool দিয়ে যাচাই করুন।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. Zone-এর apex-এ CNAME কেন রাখা যায় না? বিকল্প কী?
2. DNS migration-এ TTL কখন কমাতে হয়?
3. Negative caching কী?
4. nginx-এর master ও worker process-এর কাজ ও user কী?
5. Event loop ধীর client-এ আটকায় না কেন? কোন কাজ event loop-কে আটকায়?
6. Reverse proxy-তে client প্রতি কয়টি connection লাগে, এবং কেন?
7. `nginx -s reload` কীভাবে connection না কেটে নতুন config চালু করে?
8. server_name মেলানোর ক্রম কী?
9. location মেলানোর ক্রম কী? `^~` কী করে?
10. `root` ও `alias`-এর পার্থক্য কী?
11. `proxy_set_header`-এর inheritance-এর ফাঁদ কী?
12. Upstream keepalive চালু করতে `keepalive N`-এর বাইরে কোন দুটি লাইন লাগে?
13. 502 ও 504-এর পার্থক্য কী?
14. Unix socket-এ connect করতে কোন কোন permission লাগে?
15. systemd socket activation কোন সমস্যার সমাধান করে?
16. nginx কোন response কখনো cache করে না (default)?
17. Cache stampede কী? দুটি প্রতিরোধ বলুন।
18. `ssl_certificate`-এ কোন file দেবেন, এবং কেন?
19. sshd-এ একই keyword দুবার থাকলে কোনটি জেতে? sysctl-এ?
20. `fastcgi_params` ও `fastcgi.conf`-এর পার্থক্য কী?

## Part B — Config reading / output prediction (প্রতিটি ২ নম্বর)

21. Zone file-এর এই লাইন কোন নামে resolve হবে, এবং কেন?

    ```text
    $ORIGIN example.com.
    app  IN CNAME  app.example.com
    ```

22. `Host: shop.example.com`-এর request কোন server-এ যাবে?

    ```nginx
    server { listen 80; server_name ~^(?<s>.+)\.example\.com$; }
    server { listen 80; server_name *.example.com; }
    server { listen 80 default_server; server_name _; return 444; }
    ```

23. `/images/1.jpg` ও `/docs/1.jpg` কোন location-এ যাবে?

    ```nginx
    location /docs/ { … }
    location ^~ /images/ { … }
    location ~* \.(jpg|png)$ { … }
    ```

24. Upstream কোন URI পাবে?

    ```nginx
    location /api { proxy_pass http://app:8000/; }      # request: /api/tasks
    ```

25. এই config-এ `/reports/` location-এ app কোন `Host` header পাবে, এবং কেন?

    ```nginx
    server {
        proxy_set_header Host $host;
        location /reports/ { proxy_set_header X-Mode slow; proxy_pass http://taskflow_app; }
    }
    ```

26. nginx error.log-এ লেখা: `upstream timed out (110: Connection timed out) while reading response header from upstream`। Client কী দেখেছে? প্রথম কোথায় খুঁজবেন?

27. Response-এ `Set-Cookie: session=…` ও `Cache-Control: max-age=600`; config-এ `proxy_cache_valid 200 10m`। Cache হবে? কেন?

28. `ssl_certificate` file-এ প্রথমে intermediate, তারপর leaf। `nginx -t` কী বলবে?

29. Ubuntu-র `sshd_config`-এর প্রথম লাইনে `Include /etc/ssh/sshd_config.d/*.conf`; সেখানে `50-cloud-init.conf`-এ `PasswordAuthentication yes`; main file-এ `PasswordAuthentication no`। Effective মান কী?

30. এই PHP location-এ `/wp-content/uploads/a.jpg/x.php` request এলে কী ঝুঁকি?

    ```nginx
    location ~ \.php$ { include fastcgi.conf; fastcgi_pass unix:/run/php/php8.3-fpm.sock; }
    ```

## Part C — Scenario (প্রতিটি ৪ নম্বর)

31. শুক্রবার সন্ধ্যায় TaskFlow নতুন server-এ সরানো হলো (A record বদল, TTL ৮৬,৪০০), এক ঘণ্টা পরে পুরোনো server বন্ধ। শনিবার অনেক user timeout পাচ্ছেন। কী ভুল হয়েছিল, এবং সঠিক সময়রেখা কী?

32. Flash sale-এ site-এ নতুন connection লাগছে না, CPU ২০%। error.log-এ `Too many open files` ও `worker_connections exceed open file resource limit: 1024`। কারণ ও সমাধান কী? `worker_processes 4`, `worker_connections 4096`, reverse proxy হলে প্রকৃত সর্বোচ্চ client কত?

33. প্রতিটি deploy-এ ~৩ সেকেন্ড 502 (`Connection refused`), এবং কখনো তারপর `no live upstreams`। তিনটি পরিবর্তন প্রস্তাব করুন।

34. Partner-দের API integration হঠাৎ `unable to get local issuer certificate` দিচ্ছে, অথচ browser-এ site ঠিক। কী ঘটেছে? কীভাবে যাচাই করবেন, এবং ভবিষ্যতে কী ঠেকাবে?

35. একজন engineer traffic কমাতে `location /`-এ `proxy_cache` চালু করে `proxy_ignore_headers Set-Cookie Cache-Control;` দিলেন। কী ঘটতে পারে? সঠিক পদ্ধতি কী?

---

## Answer key

<details><summary>Part A</summary>

1. CNAME-এর নামে অন্য কোনো record থাকতে পারে না (RFC 1034), আর apex-এ সবসময় SOA ও NS থাকে। বিকল্প: A/AAAA, বা provider-এর ALIAS/CNAME flattening।
2. পরিবর্তনের অন্তত পুরোনো TTL পরিমাণ সময় **আগে** (মার্জিনসহ), যাতে পুরোনো দীর্ঘ TTL-এর cache শেষ হয়ে নতুন কম TTL ছড়ায়।
3. "নামটি নেই" (NXDOMAIN) উত্তরও cache হয় — SOA-র শেষ field (minimum/negative TTL) পর্যন্ত (RFC 2308)।
4. Master (root): config পড়া, port bind, worker পরিচালনা, signal। Worker (`www-data`): event loop-এ request সামলায়।
5. Non-blocking socket ও epoll: data না আসা socket-এর জন্য কোনো thread অপেক্ষা করে না। Blocking কাজ (ধীর disk I/O, ভারী CPU, blocking DNS) পুরো worker-কে আটকায়।
6. দুটি: client ↔ nginx ও nginx ↔ upstream। প্রতিটি একটি fd ও `worker_connections`-এর একটি slot।
7. Master নতুন config যাচাই করে নতুন worker চালু করে; পুরোনো worker আর accept করে না, চলমান request শেষ করে বের হয়। যাচাই ব্যর্থ হলে পুরোনো config-ই চলে।
8. Listen মেলানো → exact → দীর্ঘতম `*.x` → দীর্ঘতম `x.*` → config-ক্রমে প্রথম regex → `default_server` (না থাকলে প্রথম server)।
9. `=` exact → দীর্ঘতম prefix মনে রাখা → সেটা `^~` হলে থামা → config-ক্রমে প্রথম regex → না মিললে দীর্ঘতম prefix। `^~` দীর্ঘতম prefix হলে regex দেখা বন্ধ করে।
10. `root`-এ URI-এর পুরো path যোগ হয়; `alias`-এ location-এর মেলা অংশ বদলে যায় (slash অমিলে traversal-এর ঝুঁকি)।
11. ভেতরের context-এ একটিও `proxy_set_header` দিলে বাইরের সবগুলো বাদ পড়ে (যোগ হয় না)।
12. `proxy_http_version 1.1;` ও `proxy_set_header Connection "";`।
13. 502: upstream-এ পৌঁছানো যায়নি বা ভাঙা উত্তর (refused, crash, socket permission)। 504: connect বা উত্তর সময়মতো আসেনি।
14. Socket file-এ write ও path-এর প্রতিটি directory-তে execute (search)।
15. systemd socket ধরে রাখে; app restart-এর সময় নতুন connection backlog-এ অপেক্ষা করে, "Connection refused" হয় না। সাথে app-এর নিজের bind-এর অনুমতি লাগে না।
16. GET/HEAD ছাড়া অন্য method, `Set-Cookie`, `Cache-Control: private/no-store/no-cache`, `Vary: *`, `X-Accel-Expires: 0`।
17. মেয়াদোত্তীর্ণের মুহূর্তে বহু request একসাথে upstream-এ যাওয়া। প্রতিরোধ: `proxy_cache_lock on`, `proxy_cache_use_stale updating`।
18. `fullchain.pem` (leaf + intermediate, leaf আগে) — নইলে intermediate না জানা client যাচাই করতে পারে না।
19. sshd: প্রথম পাওয়া মান (Include তার অবস্থানে পড়া হয়)। sysctl (`--system`): পরে পড়া মান।
20. `fastcgi.conf`-এ `SCRIPT_FILENAME` আছে; `fastcgi_params`-এ নেই। শুধু params include করলে "No input file specified."।

</details>

<details><summary>Part B</summary>

21. `app.example.com.example.com.` — trailing dot নেই, তাই relative, origin যোগ হয়। Load-এ কোনো error হয় না।
22. `*.example.com` (দ্বিতীয়) — leading wildcard regex-এর আগে বিবেচিত হয়, config-ক্রম যাই হোক।
23. `/images/1.jpg` → `^~ /images/` (regex দেখা হয় না)। `/docs/1.jpg` → regex `~* \.(jpg|png)$` (prefix `/docs/` মিললেও regex জেতে)।
24. `//tasks` — location `/api` (slash ছাড়া) বাদ দিয়ে proxy_pass-এর `/` বসে, তাই বাকি `/tasks`-এর আগে আরেকটি `/`।
25. Upstream-এর নাম (`$proxy_host` = `taskflow_app`), client-এর Host নয়। Location-এ নিজের `proxy_set_header` থাকায় server-স্তরের সব বাদ পড়েছে।
26. 504। App request নিয়েছে কিন্তু `proxy_read_timeout`-এর মধ্যে header দেয়নি — app-এর log, সেই request-এর latency/query (request id দিয়ে)।
27. না। `Set-Cookie` থাকায় nginx default-এ cache করে না (per-user data), `max-age` থাকা সত্ত্বেও।
28. `key values mismatch` — প্রথম certificate (intermediate)-এর public key `ssl_certificate_key`-এর সাথে মেলে না; nginx চালু/reload হবে না।
29. `yes` — Include main file-এর শুরুতে, তাই drop-in-এর মান আগে পড়া হয় ও জেতে। যাচাই: `sshd -T`।
30. `try_files $uri =404` নেই। `cgi.fix_pathinfo=1` ও `security.limit_extensions` খালি হলে PHP `a.jpg`-কে PHP হিসেবে চালাতে পারে — upload-করা code execution।

</details>

<details><summary>Part C — মূল্যায়নের মূল বিষয়</summary>

31.
- **ভুল:** TTL আগে কমানো হয়নি; পুরোনো server খুব তাড়াতাড়ি বন্ধ।
- **সময়রেখা:**
  - পরিবর্তনের ≥২৪ ঘণ্টা (+মার্জিন) আগে TTL ৩০০।
  - A record বদল, দুই server-ই চালু।
  - ৫ মিনিটে বেশিরভাগ নতুনে।
  - ২৪ ঘণ্টা পরে (worst case) পুরোনো server-এর access log শূন্য দেখে বন্ধ।
  - TTL আবার বাড়ানো।
- (`zone_lint.py plan`)

32.
- **কারণ:** worker-এর open-file সীমা ১০২৪ < `worker_connections` ৪০৯৬।
- **সমাধান:** `worker_rlimit_nofile`/`LimitNOFILE` বাড়ানো, upstream keepalive, load test।
- **হিসাব:** ৪ × min(৪০৯৬, ১০২৪) = ৪০৯৬ connection; proxy-তে ÷২ ≈ **২০৪৮ client**।

33.
- systemd socket activation (restart-এ socket খোলা থাকে)।
- `upstream`-এ `127.0.0.1` (`localhost` নয়) ও `max_fails=3 fail_timeout=10s`।
- একাধিক instance + `proxy_next_upstream error timeout`, বা graceful reload।
- সাথে `$upstream_status` log।

34.
- **কী ঘটেছে:** `ssl_certificate`-এ শুধু leaf (intermediate বাদ) — সম্ভবত renewal বা হাতে copy-র সময় `cert.pem` দেওয়া হয়েছে। Browser cache/AIA থেকে intermediate আনে, API client আনে না।
- **যাচাই:** `openssl s_client -showcerts`-এ certificate সংখ্যা (২ হওয়া উচিত); `curl` (browser নয়)।
- **প্রতিরোধ:** `fullchain.pem`; `tls_conf_lint.py`; বাইরে থেকে synthetic HTTPS check (`curl`-ভিত্তিক)।

35.
- **কী ঘটতে পারে:** একজন user-এর ব্যক্তিগত page (session cookie-সহ) cache হয়ে সবাইকে দেওয়া — data breach ও session hijack।
- **সঠিক পদ্ধতি:**
  - শুধু public path-এ cache।
  - `proxy_cache_bypass`/`proxy_no_cache` Authorization ও session cookie-তে।
  - App-কে সঠিক `Cache-Control` দিতে দেওয়া।
  - `X-Cache-Status` দিয়ে যাচাই।
  - `proxy_ignore_headers Set-Cookie` নয়।

</details>

## Scoring

| অংশ | নম্বর |
|---|---|
| Part A | ২০ × ১ = ২০ |
| Part B | ১০ × ২ = ২০ |
| Part C | ৫ × ৪ = ২০ |
| **মোট** | **৬০** — pass ≥ ৪২ |

ফল [06-web-server-and-reverse-proxy/PROGRESS.md](../../06-web-server-and-reverse-proxy/PROGRESS.md)-এর Module assessment table-এ লিখুন।
