# L06-03 — Nginx server block (virtual host)

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L06-02 — Nginx architecture](L06-02-nginx-architecture.md), [L06-01 — DNS](L06-01-dns-records-domains.md) |
| **Label** | — |
| **Tested** | `server_select.py`: ৮টি test পাস (Python 3.14.5, Windows)। প্রত্যাশিত ফল nginx documentation-এর নিজস্ব উদাহরণ থেকে নেওয়া (server_name precedence ও location-এর A–E উদাহরণ)। লেখার সময় **একটি code bug, একটি ভুল test প্রত্যাশা, PCRE বনাম Python regex-এর পার্থক্য, এবং Git Bash-এর path রূপান্তর** ধরা পড়েছে (Section 9.4)। **আসল nginx-এ যাচাই হয়নি** (এই machine-এ নেই) — Section 9.5 Ubuntu-তে চালাতে হবে। |

---

## 1. এই lesson-এ যা শিখবেন

- এক IP, এক port-এ অনেক website: `server` block ও `Host` header।
- `listen` ও `server_name`: nginx কোন server বাছে — exact, wildcard, regex, **default_server**।
- `location` নির্বাচন: `=`, prefix, `^~`, regex (`~`, `~*`) — এবং কেন ক্রম গুরুত্বপূর্ণ।
- `root`, `index`, `try_files`, `return`; static site সার্ভ করা।
- Ubuntu-র `sites-available`/`sites-enabled` রীতি; একটি নিরাপদ catch-all server।
- Hidden file (`.git`, `.env`) সুরক্ষা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি server-এ `example.com` (static site), `taskflow.example.com` (API), আর customer-দের `*.example.com` চালাতে চান — সবই port ৮০/৪৪৩-এ। nginx প্রতিটি request-এর `Host` header দেখে ঠিক server block বেছে নেয়।

বাছাইয়ের নিয়ম না জানলে কয়েকটি বিপজ্জনক ব্যাপার ঘটে:

- **IP দিয়ে আসা bot বা ভুল DNS-এর request** অজান্তে "প্রথম" site-এ যায় — হয়তো admin panel।
- `location`-এর ক্রম ভুল হলে image-এর cache নিয়ম বা hidden-file-এর `deny` কাজ করে না।
- `/.git/config` বা `/.env` internet থেকে download করা যায় — একটি সাধারণ, গুরুতর ফাঁস।

## 3. সহজ ভাষায় পরিচয়

```nginx
server {
    listen 80;
    server_name example.com www.example.com;
    root /var/www/example;
    index index.html;

    location / {
        try_files $uri $uri/ =404;      # file → directory → 404
    }
    location ~ /\. { deny all; }        # .git, .env, .htpasswd
}
```

**Server নির্বাচন (একই `listen`-এর ভেতরে):**

| ক্রম | ধরন | উদাহরণ |
|---|---|---|
| ১ | Exact | `www.example.com` |
| ২ | দীর্ঘতম leading wildcard | `*.example.com` |
| ৩ | দীর্ঘতম trailing wildcard | `mail.*` |
| ৪ | Regex, config-এর ক্রমে প্রথম | `~^(?<env>dev\|staging)\.example\.net$` |
| ৫ | `default_server` (না থাকলে প্রথম server) | — |

**Location নির্বাচন:**

| ক্রম | ধরন | অর্থ |
|---|---|---|
| ১ | `location = /x` | Exact; মিললে সাথে সাথে শেষ |
| ২ | Prefix (`location /x`) | দীর্ঘতমটি মনে রাখা |
| ৩ | `location ^~ /x` | দীর্ঘতম prefix এটা হলে regex দেখা হয় না |
| ৪ | Regex `~` / `~*` | Config-এর ক্রমে **প্রথম** মিল |
| ৫ | — | কোনো regex না মিললে ২-এর দীর্ঘতম prefix |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### একটি ভবনের অভ্যর্থনা ডেস্ক

- এক ঠিকানায় (IP:port) অনেক অফিস। খামের ওপরে অফিসের নাম (`Host`) দেখে receptionist ঠিক অফিসে পাঠান (`server_name`)।
- নাম না থাকলে বা অচেনা নাম — একটি নির্দিষ্ট "অজ্ঞাত চিঠি" বাক্সে (`default_server`)।
- অফিসের ভেতরে বিভাগ: হিসাব, মানবসম্পদ (`location`)।

### Analogy কোথায় মেলে না

- **অজ্ঞাত চিঠি কোথায় যাবে, তা কেউ ঠিক না করলে nginx নিজে "প্রথম" অফিস বেছে নেয়** — config-এ যেটা প্রথম load হয়। Ubuntu-তে `sites-enabled`-এর file-এর বর্ণানুক্রম! নতুন একটি file (`00-admin.conf`) যোগ করলে নীরবে সব অজ্ঞাত traffic সেখানে যেতে পারে। তাই স্পষ্ট catch-all `default_server` রাখুন।
- **বিভাগ খোঁজা "সবচেয়ে মিল" দিয়ে নয়।** Regex location config-এর **ক্রমে প্রথম** মিলটি জেতে, এমনকি দীর্ঘতর prefix থাকলেও। `^~` এই ক্রমকে বাতিল করে। Receptionist-এর মতো "সবচেয়ে উপযুক্ত" নয় — নিয়ম যান্ত্রিক।
- **খামের নাম যে কেউ লিখতে পারে।** `Host` header client নিয়ন্ত্রণ করে। `curl -H 'Host: admin.internal' http://<IP>/` দিয়ে আক্রমণকারী internal নামের server block-এ পৌঁছাতে পারে, যদি সেটা public interface-এ listen করে। Internal site আলাদা `listen 127.0.0.1` বা আলাদা interface-এ রাখুন।

## 5. Real-world engineering scenario — "IP দিয়ে admin panel খুলে গেল"

**পরিস্থিতি:** একটি server-এ দুটি site — `shop.example.com` ও `admin.example.com` (শুধু office-এর জন্য, কিন্তু একই nginx-এ)। কেউ `default_server` রাখেননি। `sites-enabled`-এ file দুটি `admin.conf` ও `shop.conf` — বর্ণানুক্রমে admin প্রথম।

Internet-এর scanner সরাসরি IP দিয়ে request পাঠায় (`Host: 203.0.113.5`)। কোনো server_name মেলেনি, তাই nginx প্রথম server — **admin** — বেছে নিল। Scanner admin-এর login page index করল, এবং brute-force শুরু হলো।

**সমাধান (`sites.conf`-এর প্রথম block):**

```nginx
server {
    listen 80 default_server;
    listen [::]:80 default_server;
    server_name _;
    return 444;            # nginx-এর বিশেষ code: কোনো response ছাড়াই connection বন্ধ
}
```

সাথে admin site-কে `listen 10.0.0.5:443` (internal interface) বা VPN-এ রাখা, এবং `allow`/`deny`।

`server_select.py` দিয়ে যাচাই (আসল output):

```text
$ server_select.py sites.conf --host 198.51.100.7
server   sites.conf:4  ← default_server (no server_name matched)
return   444  ← server-level return runs before location matching
```

**শিক্ষা:** "কোনো নাম না মিললে কী হবে" — এটা একটি স্পষ্ট সিদ্ধান্ত হওয়া উচিত, config-এর ক্রমের দুর্ঘটনা নয়।

## 6. Diagram — একটি request-এর পথ

```text
 TCP connection → 203.0.113.5:80
   │
   ├─ ১. listen মেলানো: কোন server-গুলো *:80 / 203.0.113.5:80-এ শোনে?
   │
   ├─ ২. Host: www.Example.COM.:80  → normalize → www.example.com
   │      exact? ── হ্যাঁ ─► server "example.com www.example.com"
   │      নইলে *.x (দীর্ঘতম) → x.* (দীর্ঘতম) → regex (প্রথম) → default_server
   │
   ├─ ৩. server-স্তরের return/rewrite?  ── হ্যাঁ ─► সেখানেই উত্তর (যেমন 444, 301)
   │
   └─ ৪. URI /static/logo.png
          = exact?            না
          prefix-এর দীর্ঘতম:  "/static/" (^~)  ─► regex দেখা হয় না ─► expires 7d
          (^~ না হলে: regex ~* \.(png|…)$ প্রথম মিল ─► expires 30d)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Virtual host / server block | এক IP:port-এ একাধিক site |
| `Host` header | Client কোন নামের site চায় (HTTP/1.1-এ বাধ্যতামূলক) |
| `default_server` | কোনো নাম না মিললে কোন server |
| `server_name _` | প্রথাগত "অসম্ভব" নাম — catch-all-এ |
| `return 444` | nginx-এর নিজস্ব: response ছাড়া connection বন্ধ |
| `location` modifier | `=`, `^~`, `~`, `~*`, (নেই = prefix) |
| `try_files` | ক্রমানুসারে file খোঁজা, শেষে fallback |
| `root` বনাম `alias` | URI path যোগ হয় / location-এর অংশ বদলে যায় |
| SNI | TLS-এ server নাম জানানো — HTTPS-এ server বাছাইয়ে লাগে (L06-07) |
| `sites-available` / `sites-enabled` | Ubuntu: সব config / চালু config (symlink) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Listen আগে, নাম পরে

nginx প্রথমে connection যে address:port-এ এসেছে, তার সাথে `listen` মেলায়। শুধু সেই server-গুলোর মধ্যে `server_name` খোঁজে। ফলে `listen 127.0.0.1:80`-এর server কখনো public IP-এর request পায় না — Host যাই হোক। Internal site আলাদা রাখার সবচেয়ে শক্ত উপায় এটাই।

### 8.2 Host-এর normalization

nginx `Host`-কে ছোট হাতের অক্ষরে নেয়, port বাদ দেয়, এবং শেষের dot বাদ দেয়। তাই `WWW.Example.COM.:80` ও `www.example.com` একই।

### 8.3 Regex: PCRE

nginx PCRE ব্যবহার করে। Named capture `(?<env>…)` পরে `$env` variable হিসেবে ব্যবহার করা যায় (`root /var/www/$env;`)। Python-এর `re`-তে একই জিনিসের রূপ `(?P<env>…)` — tool-টি রূপান্তর করে (Section 9.4)।

### 8.4 `root` বনাম `alias`, এবং `try_files`

```nginx
location /static/ { root  /srv/app; }          # /static/a.css → /srv/app/static/a.css
location /static/ { alias /srv/app/assets/; }  # /static/a.css → /srv/app/assets/a.css
```

`alias`-এ trailing slash না মিললে (`location /static` + `alias /srv/assets/`) path traversal-এর পরিচিত ঝুঁকি আছে (`/static../secret`)। Location ও alias দুটোতেই `/` রাখুন।

`try_files $uri $uri/ =404;` না দিলে, কিছু configuration-এ অনুপস্থিত file-এর request application-এ চলে যায়। এখানে স্পষ্ট 404।

> **Fedora-তে:** `sites-available`/`sites-enabled` নেই — `/etc/nginx/conf.d/*.conf`। Default server block `/etc/nginx/nginx.conf`-এর ভেতরেই। Static file-এর directory-তে SELinux context `httpd_sys_content_t` লাগে (`restorecon -Rv /var/www`) — নইলে 403।

## 9. Practical demonstration

Files:

- [`code/L06-03/server_select.py`](code/L06-03/server_select.py) — L06-02-এর parser ব্যবহার করে।
- [`sites.conf`](code/L06-03/sites.conf) (হাতে তৈরি, পাঁচটি site)।
- [`test_l06_03.py`](code/L06-03/test_l06_03.py)।

### 9.1 Site তালিকা

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-03
python3 server_select.py sites.conf --list
```

```text
sites.conf:4     listen *:80 default, [::]:80 default server_name _
sites.conf:12    listen *:80                     server_name example.com www.example.com
sites.conf:36    listen *:80                     server_name taskflow.example.com
sites.conf:45    listen *:80                     server_name *.example.com
sites.conf:52    listen *:80                     server_name ~^(?<env>dev|staging)\.example\.net$
```

### 9.2 নির্বাচন — আসল output

```text
--host www.example.com --uri /
server   sites.conf:12  ← server_name www.example.com (exact)
location = /  (sites.conf:18)  ← exact match (=)

--host example.com --uri /about.html
location /  (sites.conf:21)  ← longest prefix (no regex matched)

--host example.com --uri /static/logo.png
location ^~ /static/  (sites.conf:24)  ← longest prefix with ^~ (regex not checked)
           expires 7d;

--host example.com --uri /img/logo.PNG
location ~* \.(png|jpg|jpeg|gif|svg)$  (sites.conf:27)  ← first matching regex (~*)

--host example.com --uri /.env
location ~ /\.  (sites.conf:30)  ← first matching regex (~)
           deny all;

--host taskflow.example.com --uri /tasks?done=true
location /  (sites.conf:39)  ← longest prefix (no regex matched)
           proxy_pass http://127.0.0.1:8000;

--host shop.example.com
server   sites.conf:45  ← server_name *.example.com (leading wildcard)
return   302 https://example.com/  ← server-level return runs before location matching

--host staging.example.net
server   sites.conf:52  ← server_name ~^(?<env>dev|staging)\.example\.net$ (regex)
```

**লক্ষ করুন `/static/logo.png`:**

- `^~ /static/` আছে বলে image-এর regex (৩০ দিন) দেখাই হয়নি — ৭ দিন প্রযোজ্য।
- `^~` সরালে regex জিতবে।
- এই পার্থক্য `nginx -t` ধরবে না, কারণ দুটোই বৈধ config।

### 9.3 Documentation-এর উদাহরণ (test)

nginx documentation-এর location উদাহরণ (A–E) test-এ হুবহু:

| URI | Location |
|---|---|
| `/` | A (`= /`) |
| `/index.html` | B (`/`) |
| `/documents/document.html` | C (`/documents/`) |
| `/images/1.gif` | D (`^~ /images/`) |
| `/documents/1.jpg` | E (regex — prefix C-এর চেয়েও আগে) |

শেষটি সবচেয়ে বিস্ময়কর: `/documents/` prefix মিললেও regex জেতে।

### 9.4 লেখার সময় যা ধরা পড়েছে

1. **PCRE বনাম Python:** প্রথম run-এই `re.PatternError: unknown extension ?<e`। nginx-এর `(?<env>…)` Python বোঝে না। `pcre()` এখন রূপান্তর করে, lookbehind `(?<=`/`(?<!` অক্ষত রেখে।
2. **Code-এর bug:** `Host: WWW.Example.ORG.:80` মিলছিল না। আমি আগে শেষের dot মুছে পরে port কাটছিলাম — `.:80`-এ শেষ অক্ষর `0`, তাই dot থেকে যাচ্ছিল। এখন আগে port, পরে dot।
3. **ভুল test প্রত্যাশা:** `www.foo.example.org`-এর জন্য লিখেছিলাম `*.www.example.org`। কিন্তু এই নাম `.www.example.org`-এ শেষ হয় না। সঠিক উত্তর `*.example.org` — tool ঠিক ছিল।
4. **Git Bash:** `--uri /` চালালে `location` মিলছিল না। কারণ:

   ```text
   $ python -c "import sys; print(sys.argv[1:])" --uri / --uri /about.html --uri '/tasks?done=true'
   ['--uri', 'C:/Program Files/Git/', '--uri', 'C:/Program Files/Git/about.html', '--uri', '/tasks?done=true']
   ```

   MSYS `/`-দিয়ে শুরু argument-কে Windows path বানায় (কিন্তু `?`-যুক্ত argument-কে নয় — তাই কিছু case কাজ করছিল, যা বিভ্রান্তি বাড়িয়েছিল)। `MSYS_NO_PATHCONV=1`। L05-08-এর একই ফাঁদ।

### 9.5 Ubuntu-তে (চালানো হয়নি)

```bash
sudo mkdir -p /var/www/example && echo '<h1>example</h1>' | sudo tee /var/www/example/index.html
sudo cp sites.conf /etc/nginx/sites-available/lab06.conf
sudo ln -s /etc/nginx/sites-available/lab06.conf /etc/nginx/sites-enabled/
sudo rm /etc/nginx/sites-enabled/default        # Ubuntu-র নিজের default_server-এর সাথে সংঘাত
sudo nginx -t && sudo systemctl reload nginx

curl -s -H 'Host: www.example.com' http://127.0.0.1/            # <h1>example</h1>
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: www.example.com' http://127.0.0.1/.env   # 403
curl -sv http://127.0.0.1/ 2>&1 | tail -2                       # 444: "Empty reply from server"
curl -s -o /dev/null -w '%{http_code} %{redirect_url}\n' -H 'Host: shop.example.com' http://127.0.0.1/
```

প্রতিটির ফল `server_select.py`-এর উত্তরের সাথে মেলান। না মিললে tool-এর একটি bug পেয়েছেন — অথবা Section 8-এর এমন কোনো নিয়ম, যা tool জানে না।

### 9.6 Test

```bash
python3 -m unittest -v
```

৮টি test:

- server_name-এর precedence (documentation-এর ক্রম)।
- `default_server` বনাম প্রথম server; Host normalization।
- `.example.com` ও listen port।
- PCRE named group।
- `listen`-এর রূপ (`[::]:443 ssl default_server`)।
- Location-এর A–E উদাহরণ।
- Regex-এর config-ক্রম।
- নমুনা sites-এর CLI।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `parse_listen` | `80`, `ip:port`, `[::]:443 ssl default_server` | listen-এর সব সাধারণ রূপ |
| নির্দিষ্ট IP আগে, তারপর `*` | listen মেলানো | Section 8.1 |
| `name_match` → (শ্রেণি, দৈর্ঘ্য) | Exact/wildcard/regex | একটি rank-এ তুলনা |
| `rank = (klass, -length, index)` | ছোট rank জেতে | দীর্ঘতম wildcard; regex-এ config-ক্রম |
| `.example.com` | apex + wildcard | nginx-এর বিশেষ রূপ |
| `pcre()` | `(?<n>` → `(?P<n>` | PCRE ≠ Python re |
| Server-স্তরের `return` আগে | Rewrite phase | `*.example.com`-এর 302 |
| `select_location` | `=` → prefix/`^~` → regex → prefix | documentation-এর অ্যালগরিদম |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `--host 198.51.100.7` | catch-all, `return 444` |
| `--uri /.env` | `deny all` location |
| `--uri /static/logo.png` | `^~ /static/`, regex নয় |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| ভুল site দেখাচ্ছে | Host মেলেনি → default/প্রথম server | `default_server` স্পষ্ট; `server_name` যাচাই |
| `duplicate default server for 0.0.0.0:80` | দুই জায়গায় `default_server` | Ubuntu-র `sites-enabled/default` মুছুন |
| `conflicting server name … ignored` (warn) | একই নাম দুই server-এ | একটি রাখুন — দ্বিতীয়টি উপেক্ষিত |
| Image-এর cache নিয়ম কাজ করছে না | `^~` prefix regex আটকাচ্ছে | Location-এর ক্রম/modifier দেখুন |
| `/.git/config` download হয় | Hidden file সুরক্ষা নেই | `location ~ /\. { deny all; }` |
| 403 static file-এ | Permission বা SELinux | `namei -l /var/www/…`; Fedora-তে `restorecon` |
| `alias`-এ অদ্ভুত path | Trailing slash অমিল | দুটোতেই `/` |
| Windows-এ `/` path অদ্ভুত | Git Bash path conversion | `MSYS_NO_PATHCONV=1` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Catch-all `default_server` (444) — IP-scan ও অজানা Host-কে কিছু দেখায় না।
  - Internal site আলাদা listen address-এ।
  - Hidden file `deny`।
  - Directory listing (`autoindex`) বন্ধ।
  - Host header বিশ্বাস করবেন না — application-এ absolute URL বানাতে কনফিগার করা নাম ব্যবহার করুন, `Host` নয় (host header injection)।
- **Performance:**
  - Exact ও wildcard নাম hash table-এ, তাই দ্রুত। Regex প্রতিটি request-এ ক্রমানুসারে চলে — অনেক regex থাকলে ধীর। `server_names_hash_bucket_size` লম্বা নামে বাড়াতে হতে পারে।
  - Static file nginx থেকে দিন (`sendfile`), application থেকে নয়।
- **Cost:**
  - এক server-এ অনেক ছোট site চালানো সস্তা।
  - কিন্তু একটি site-এর traffic spike সবগুলোকে প্রভাবিত করে (noisy neighbour) — বড় হলে আলাদা করুন (Module 07)।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.5 চালিয়ে প্রতিটি `curl`-এর ফল `server_select.py`-এর সাথে মেলান।
2. `sites.conf` থেকে `default_server` সরিয়ে `--host 198.51.100.7` আবার চালান। কোন site পেলেন? Ubuntu-তে একই জিনিস `curl`-এ দেখুন।
3. `^~ /static/` থেকে `^~` সরান। `/static/logo.png`-এর জন্য কী বদলাল, এবং কেন?
4. `server_select.py`-এ nested location সমর্থন যোগ করুন (`location /api/ { location ~ \.json$ { … } }`)। Documentation পড়ে নিয়ম ঠিক করুন।
5. Section 4-এর Host header আক্রমণ local-এ পুনরুৎপাদন করুন: একটি "internal" server_name-এর block বানিয়ে `curl -H 'Host: internal.lab' http://127.0.0.1/`। তারপর সেটাকে `listen 127.0.0.2:80`-এ সরিয়ে আবার চেষ্টা করুন।

## 15. Mini-project — Site inventory ও policy check

`site_audit.py /etc/nginx/nginx.conf` (L06-02-এর parser দিয়ে):

- প্রতিটি server_name-এর তালিকা।
- প্রতিটি listen-এ `default_server` আছে কিনা।
- Hidden-file deny আছে কিনা।
- `autoindex on` কোথায়।
- একই নাম একাধিক server-এ।
- JSON ও exit code।

Lab 06-A-তে ও L06-08-এর hardening audit-এ এটা কাজে লাগবে।

## 16. Interview প্রশ্ন

1. nginx একাধিক site-এর মধ্যে কীভাবে request ভাগ করে?
2. কোনো server_name না মিললে কী হয়? কীভাবে নিয়ন্ত্রণ করবেন?
3. `location` matching-এর ক্রম ব্যাখ্যা করুন। `^~` কী করে?
4. `root` ও `alias`-এর পার্থক্য কী?
5. Host header injection কী?
6. HTTPS-এ server block কীভাবে বাছা হয় (TLS handshake-এর সময় Host header জানা থাকে না)?

## 17. Self-assessment প্রশ্ন

1. Receptionist analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ admin panel কেন খুলে গেল?
3. `/documents/1.jpg` কেন regex-এ গেল, prefix-এ নয়?
4. Host normalization-এর bug কী ছিল?
5. PCRE ও Python regex-এর কোন পার্থক্য tool-কে ভাঙাচ্ছিল?

## 18. সংক্ষিপ্ত সারাংশ

- Listen আগে, তারপর Host: exact → `*.x` → `x.*` → regex (ক্রমে) → `default_server`।
- সবসময় স্পষ্ট catch-all `default_server` (444)।
- Location: `=` → দীর্ঘতম prefix (`^~` হলে থামা) → প্রথম regex → prefix।
- Hidden file deny, `try_files … =404`, `alias`-এ slash।
- Internal site আলাদা listen address-এ; Host header বিশ্বাস নয়।

## 19. Completion checklist

- [ ] `server_select.py` দিয়ে ১০টি request-এর গন্তব্য অনুমান করে মিলিয়েছি
- [ ] (Ubuntu) একই request `curl`-এ মিলিয়েছি
- [ ] Catch-all default server বানিয়েছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nginx — Server names: https://nginx.org/en/docs/http/server_names.html
- nginx — How nginx processes a request: https://nginx.org/en/docs/http/request_processing.html
- nginx — `location` directive: https://nginx.org/en/docs/http/ngx_http_core_module.html#location
- nginx — `try_files`: https://nginx.org/en/docs/http/ngx_http_core_module.html#try_files
- nginx — `alias`: https://nginx.org/en/docs/http/ngx_http_core_module.html#alias
- Python — `re` (named groups): https://docs.python.org/3/library/re.html

---

**পরের lesson:** L06-04 — Reverse proxy ও upstream
