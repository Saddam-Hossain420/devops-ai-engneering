# L06-09 — PHP-FPM ও WordPress deployment

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L06-08 — Hardening](L06-08-linux-server-hardening.md), [L06-05 — Unix socket ও systemd](L06-05-app-process-socket-systemd.md), [L06-03 — Server block](L06-03-nginx-server-blocks.md) |
| **Label** | — |
| **Tested** | `fcgi_client.py`, `php_fastcgi_demo.py`, `fpm_pool_calc.py`, `wp_nginx_lint.py`: ৭টি test পাস (Python 3.14.5, Windows)। **আসলে চালানো হয়েছে:** নিজের লেখা FastCGI client দিয়ে local `php-cgi` (PHP 8.5.11, FastCGI mode)-এর সাথে কথা বলা — সঠিক request, `SCRIPT_FILENAME` বাদ, এবং upload-করা "ছবি" PHP হিসেবে চলে যাওয়া (`cgi.fix_pathinfo=1`)। এখানে PHP-FPM-এর বদলে `php-cgi` ব্যবহার হয়েছে, কারণ Windows-এ PHP-FPM নেই — protocol একই, কিন্তু `security.limit_extensions` (শুধু FPM-এর সুরক্ষা) এখানে পরীক্ষা হয়নি। WordPress, MySQL ও nginx **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- FastCGI: nginx ও PHP-FPM-এর মধ্যে protocol — `fastcgi_pass`, `SCRIPT_FILENAME`, params।
- PHP-FPM pool: user, socket, `pm` (static/dynamic/ondemand), **`pm.max_children` memory থেকে হিসাব**।
- WordPress-এর nginx config: front controller (`try_files … /index.php?$args`), static file, upload-এর আকার।
- তিনটি ক্লাসিক ভুল — **আসলে ঘটিয়ে দেখা**: `fastcgi_params` বনাম `fastcgi.conf`, `cgi.fix_pathinfo`-এর upload-execution, PHP file download হয়ে যাওয়া।
- WordPress-এর নিরাপত্তা: uploads-এ PHP নিষেধ, `wp-config.php`, file permission, আপডেট, `xmlrpc.php`।
- কেন এই module-এ PHP — TaskFlow Python, কিন্তু বাস্তবের বিপুল সংখ্যক server-এ এই stack চলে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

WordPress web-এর একটি বড় অংশ চালায় (W3Techs-এর মতো জরিপে প্রায়ই ৪০%-এর বেশি website উল্লেখ করা হয়)। DevOps/SRE হিসেবে আপনাকে প্রায় নিশ্চিতভাবে কোনো না কোনো সময় একটি PHP application চালাতে বা উদ্ধার করতে হবে।

PHP-র মডেল TaskFlow থেকে ভিন্ন: nginx নিজে PHP চালায় না, প্রতিটি `.php` request **FastCGI** দিয়ে PHP-FPM process pool-এ পাঠায়। এই সীমানায় সবচেয়ে বেশি ভুল হয়:

- `.php` file browser-এ **download** হয় — source code ও database password সহ।
- "File not found" / "No input file specified" — `SCRIPT_FILENAME` নেই।
- **Upload-করা ছবি PHP হিসেবে চলে** — আক্রমণকারী server-এর নিয়ন্ত্রণ পায়।
- Traffic spike-এ `pm.max_children` বেশি হওয়ায় memory শেষ, OOM killer MySQL মেরে ফেলে।

## 3. সহজ ভাষায় পরিচয়

```nginx
location / {
    try_files $uri $uri/ /index.php?$args;          # file না থাকলে WordPress-এর front controller
}
location ~ \.php$ {
    try_files $uri =404;                            # file সত্যিই আছে কিনা
    include fastcgi.conf;                           # SCRIPT_FILENAME সহ
    fastcgi_pass unix:/run/php/php8.3-fpm.sock;
}
location ~* /wp-content/uploads/.*\.php$ { deny all; }
```

```ini
; /etc/php/8.3/fpm/pool.d/blog.conf
[blog]
user = blog
group = blog
listen = /run/php/blog.sock
listen.owner = www-data
listen.group = www-data
pm = dynamic
pm.max_children = 20          ; memory থেকে হিসাব (fpm_pool_calc.py)
pm.max_requests = 500         ; memory leak-এর বিরুদ্ধে process নবায়ন
security.limit_extensions = .php
```

| File | কী আছে |
|---|---|
| `/etc/nginx/fastcgi.conf` | সব param, **`SCRIPT_FILENAME` সহ** |
| `/etc/nginx/fastcgi_params` | একই, কিন্তু **`SCRIPT_FILENAME` ছাড়া** (Ubuntu/Debian) |
| `/etc/nginx/snippets/fastcgi-php.conf` | Ubuntu-র snippet: split_path_info + `try_files` + `fastcgi.conf` |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অনুবাদক দপ্তর

- nginx = অভ্যর্থনা ডেস্ক — সাধারণ কাগজ (ছবি, CSS) নিজেই দেয়।
- `.php` = অনুবাদ লাগবে এমন কাগজ — অনুবাদক দপ্তরে (PHP-FPM) পাঠানো হয়।
- **FastCGI params** = সাথের চিরকুট: "কোন file, কোন ভাষা, কার জন্য"।
- **`SCRIPT_FILENAME`** = চিরকুটে লেখা file-এর আসল ঠিকানা। না থাকলে অনুবাদক বলেন "কোন file? খুঁজে পাচ্ছি না"।
- **Pool-এর `max_children`** = কতজন অনুবাদক একসাথে কাজ করবেন।

### Analogy কোথায় মেলে না

- **অনুবাদক কাগজ পড়ার আগে ধরন দেখেন।** PHP `cgi.fix_pathinfo=1` (PHP-এর default) হলে `/uploads/avatar.jpg/x.php` পেয়ে "`x.php` নেই, তাহলে বাম দিকের অস্তিত্বশীল অংশ — `avatar.jpg` — চালাই" করে। এই lesson-এ আসলে ঘটেছে: একটি ".jpg" file-এর ভেতরের PHP code চলে গেছে। কোনো সতর্ক অনুবাদক এটা করতেন না। প্রতিরোধ nginx-এর `try_files $uri =404` এবং FPM-এর `security.limit_extensions = .php` — দুই স্তরে।
- **অনুবাদক বাড়ালে কাজ দ্রুত হয়।** প্রতিটি PHP-FPM process ৩০–১০০ MB memory নেয়। `max_children` বেশি রাখলে spike-এ RAM শেষ হয়, swap শুরু হয়, এবং সবাই ধীর হয়ে যায় — অথবা OOM killer database মেরে ফেলে। কম রাখলে request queue-তে অপেক্ষা করে (নিয়ন্ত্রিত ব্যর্থতা)। বেশি সবসময় ভালো নয়।
- **কাগজ ভুল দপ্তরে গেলে ফেরত আসে।** nginx-এ PHP location-এ না মিললে (যেমন `location ~ \.php$` ভুল ক্রমে, বা অন্য prefix location আগে জিতল — L06-03), nginx `.php` file **static file হিসেবে download করিয়ে দেয়** — `wp-config.php`-এর database password সহ।

## 5. Real-world engineering scenario — "Blog-এর ছবির folder থেকে crypto miner"

**পরিস্থিতি:** একটি পুরোনো WordPress site। Server-এর CPU ১০০%, এবং `ps`-এ `www-data`-র মালিকানায় একটি অচেনা process। তদন্তে পাওয়া গেল:

1. একটি পুরোনো plugin-এর upload form file-এর extension যাচাই করত, কিন্তু বিষয়বস্তু নয়। আক্রমণকারী `avatar.jpg` নামে PHP code upload করেছিল।
2. nginx config একটি পুরোনো tutorial থেকে: `location ~ \.php$ { include fastcgi_params; fastcgi_param SCRIPT_FILENAME …; fastcgi_pass …; }` — `try_files $uri =404` নেই।
3. `cgi.fix_pathinfo` default (১), এবং pool-এ `security.limit_extensions` খালি করে দেওয়া হয়েছিল (একটি plugin-এর জন্য)।
4. আক্রমণকারী request করল `/wp-content/uploads/2026/10/avatar.jpg/x.php`। nginx `.php`-এ শেষ দেখে FPM-এ পাঠাল, আর PHP `x.php` না পেয়ে `avatar.jpg` চালাল।

`php_fastcgi_demo.py`-এ একই ঘটনা (আসল output, কৃত্রিম file):

```text
fix_pathinfo=1  /uploads/avatar.jpg/x.php (path-info trick) → 200   fake jpeg UPLOADED FILE EXECUTED AS PHP
fix_pathinfo=0  /uploads/avatar.jpg/x.php (path-info trick) → 404   No input file specified.
```

**প্রতিরক্ষার স্তর** (যেকোনো একটি থাকলেই ঘটনা ঘটত না):

- nginx: `try_files $uri =404;` PHP location-এ — file-টি `x.php` নামে নেই, তাই 404।
- nginx: uploads-এ `.php` deny।
- PHP: `cgi.fix_pathinfo=0`; FPM: `security.limit_extensions = .php`।
- Filesystem: uploads directory-তে PHP চালানোর দরকারই নেই।
- আপডেট: দুর্বল plugin।

**শিক্ষা:** একটি স্তরের ওপর ভরসা নয় — defense in depth (L06-08)। আর copy-করা tutorial config `wp_nginx_lint.py`-এর মতো কিছু দিয়ে যাচাই করুন।

## 6. Diagram — একটি WordPress request

```text
 GET /2026/10/hello-world/
   │ nginx: location / → try_files $uri $uri/ /index.php?$args
   │        file নেই → internal redirect /index.php?…
   ▼
 location ~ \.php$
   │ try_files $uri =404           ← /index.php আছে ✔  (avatar.jpg/x.php হলে: নেই → 404)
   │ include fastcgi.conf           ← SCRIPT_FILENAME=/var/www/wordpress/index.php, QUERY_STRING, …
   │ fastcgi_pass unix:/run/php/php8.3-fpm.sock
   ▼
 PHP-FPM master (root) ── pool "blog" (user blog) ── worker ১…max_children
   │ worker: index.php → WordPress → MySQL (127.0.0.1:3306 / socket)
   ▼
 FastCGI STDOUT: "Status: 200\r\nContent-Type: text/html\r\n\r\n<html>…"  ─► nginx ─► client

 FastCGI record: [version 1 | type | request id | content length | padding] + content (৮-byte aligned)
   BEGIN_REQUEST → PARAMS… → PARAMS(খালি) → STDIN(খালি)  ⇄  STDOUT… STDERR… END_REQUEST
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| FastCGI | Web server ও application process-এর মধ্যে binary protocol, দীর্ঘজীবী process |
| PHP-FPM | PHP-র FastCGI Process Manager — pool, worker, নিয়ন্ত্রণ |
| Pool | একই user ও নিয়মের worker-এর দল (প্রতি site আলাদা রাখা ভালো) |
| `pm` | Process manager mode: static / dynamic / ondemand |
| `pm.max_children` | একসাথে সর্বোচ্চ worker |
| `pm.max_requests` | এতগুলো request-এর পরে worker নবায়ন |
| `SCRIPT_FILENAME` | কোন PHP file চালাতে হবে (disk path) |
| `PATH_INFO` | Script-এর পরের অংশ (`/x.php/extra`) |
| `cgi.fix_pathinfo` | PHP-র path অনুমান — ১ হলে বিপজ্জনক আচরণ |
| `security.limit_extensions` | FPM কোন extension চালাবে |
| Front controller | সব request একটি file-এ (`index.php`), যা routing করে |
| `wp-config.php` | WordPress-এর config — DB password, salt |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 FastCGI protocol

প্রতিটি record-এ ৮ byte header: version, type, request id, content length, padding — content ৮-byte সীমায় শেষ হয়। Params name-value জোড়ায় যায়; দৈর্ঘ্য ১২৮-এর কম হলে ১ byte, নইলে ৪ byte (উঁচু bit set)।

`fcgi_client.py` ঠিক এটুকুই করে, এবং nginx-এর `fastcgi.conf`-এর মতো params পাঠায়। ফলে nginx ছাড়াই PHP-FPM-কে সরাসরি পরীক্ষা করা যায় — debugging-এ খুব কাজের: "সমস্যা nginx-এ, নাকি PHP-তে?"

### 8.2 `fastcgi_params` বনাম `fastcgi.conf`

ঐতিহাসিক কারণে Ubuntu/Debian-এ দুটো file আছে। `fastcgi.conf` = `fastcgi_params` + `SCRIPT_FILENAME $document_root$fastcgi_script_name`।

পুরোনো tutorial `include fastcgi_params;` লেখে কিন্তু `SCRIPT_FILENAME` যোগ করতে ভুলে যায়। ফল: PHP উত্তর দেয় `No input file specified.`, এবং nginx দেখায় 404। এই lesson-এ আসলে দেখা গেছে।

### 8.3 Pool-এর আকার

```text
pm.max_children ≈ (মোট RAM − OS − nginx − MySQL − অন্যান্য) × 0.9 / গড় PHP process memory
```

গড় process memory মাপুন — `ps -o rss= -C php-fpm8.3` — এবং peak-এর জন্য ২০% বাড়ান। `fpm_pool_calc.py` এই হিসাব করে, এবং খুব কম memory-তে স্পষ্ট error দেয় (৫১২ MB, ৪৫০ reserved → "not enough")।

**Mode:**

- `ondemand` — কম traffic-এর site; idle-এ memory ফেরত।
- `dynamic` — সাধারণ।
- `static` — স্থির উচ্চ load।

### 8.4 WordPress-এর নিরাপত্তার মূল বিষয়

- **File owner:** web server-এর user নয়। আলাদা `blog` user, আর `www-data` শুধু পড়ে। `wp-content/uploads` ছাড়া কোথাও লেখার অনুমতি নয় (`DISALLOW_FILE_EDIT`)।
- **`wp-config.php`:** `0640`, web root-এর বাইরে রাখা যায়।
- **Core, plugin, theme আপডেট** — বেশিরভাগ ঘটনার মূল কারণ পুরোনো plugin।
- **`xmlrpc.php`** brute-force-এর জনপ্রিয় লক্ষ্য — দরকার না হলে বন্ধ।
- **Login-এ rate limit** (L06-08-এর `limit_req`)।

> **Fedora-তে:** `dnf install php-fpm`; pool `/etc/php-fpm.d/www.conf`, socket `/run/php-fpm/www.sock`, user `apache` (default)। SELinux: WordPress-কে uploads-এ লিখতে `httpd_sys_rw_content_t` context, network-এ যেতে `httpd_can_network_connect_db`।

## 9. Practical demonstration

Files:

- [`code/L06-09/fcgi_client.py`](code/L06-09/fcgi_client.py), [`php_fastcgi_demo.py`](code/L06-09/php_fastcgi_demo.py)।
- [`fpm_pool_calc.py`](code/L06-09/fpm_pool_calc.py), [`wp_nginx_lint.py`](code/L06-09/wp_nginx_lint.py)।
- [`wordpress.conf`](code/L06-09/wordpress.conf) (ঠিক) ও [`wordpress-broken.conf`](code/L06-09/wordpress-broken.conf) (ভুলসহ)।
- [`test_l06_09.py`](code/L06-09/test_l06_09.py)।

### 9.1 আসল PHP-এর সাথে FastCGI — আসল output

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-09
python3 php_fastcgi_demo.py           # php-cgi লাগে (Ubuntu: sudo apt install php-cgi)
```

```text
fix_pathinfo=1  correct SCRIPT_FILENAME                    → 200              TaskFlow blog: PHP 8.5.11, p=1
fix_pathinfo=1  SCRIPT_FILENAME missing (fastcgi_params)   → 404 Not Found    No input file specified.
fix_pathinfo=1  /uploads/avatar.jpg/x.php (path-info trick) → 200              fake jpeg UPLOADED FILE EXECUTED AS PHP
fix_pathinfo=0  correct SCRIPT_FILENAME                    → 200              TaskFlow blog: PHP 8.5.11, p=1
fix_pathinfo=0  SCRIPT_FILENAME missing (fastcgi_params)   → 404 Not Found    No input file specified.
fix_pathinfo=0  /uploads/avatar.jpg/x.php (path-info trick) → 404 Not Found    No input file specified.
```

- মোট সময় ০.৮৮ s — দুবার php-cgi চালু ও ছয়টি FastCGI request।
- `avatar.jpg`-এর শুরুতে আসল JPEG-এর magic bytes (`FF D8 FF E0`) আছে, তবুও PHP ভেতরের `<?php … ?>` অংশ চালিয়েছে।
- প্রথম run-এ সেই binary byte terminal-এ গিয়ে আবর্জনা দেখাচ্ছিল; এখন output থেকে বাদ দেওয়া হয়।

**সীমা:** এখানে PHP-FPM নয়, `php-cgi` (Windows-এ FPM নেই)। FPM-এ `security.limit_extensions = .php` (default) থাকলে তৃতীয় case-টি FPM-ই প্রত্যাখ্যান করত — অর্থাৎ FPM-এ এই আক্রমণের জন্য দুটি default-ই বদলানো লাগে। Ubuntu-তে FPM-এ পরীক্ষা করুন (exercise ১)।

### 9.2 WordPress config lint — আসল output

```bash
python3 wp_nginx_lint.py wordpress-broken.conf; echo "exit=$?"
python3 wp_nginx_lint.py wordpress.conf; echo "exit=$?"
```

```text
ERROR   wordpress-broken.conf:12 php-no-file-check        PHP location without 'try_files $uri =404;' — /uploads/x.jpg/y.php may run x.jpg as PHP …
ERROR   wordpress-broken.conf:12 no-script-filename       SCRIPT_FILENAME not set — 'include fastcgi_params' alone lacks it … → PHP answers 'No input file specified.'
WARNING -                    uploads-php-allowed      no 'location ~* /wp-content/uploads/.*\.php$ { deny all; }' — defense in depth for uploads
WARNING -                    dotfiles-allowed         no deny for dotfiles (.git, .env, .htaccess)
WARNING -                    upload-size              client_max_body_size not set — media uploads over 1m get 413
WARNING wordpress-broken.conf:8 no-front-controller      location / should have 'try_files $uri $uri/ /index.php?$args;' (pretty permalinks)
6 finding(s)
exit=1

0 finding(s)
exit=0
```

**লেখার সময় ধরা পড়া:** প্রথম run-এ lint দুটি file-এই `include file not found: fastcgi_params` দিয়ে থেমে গেল। L06-02-এর parser include-কে config file-এর directory-র সাপেক্ষে খোঁজে। কিন্তু site file-এর `include fastcgi.conf` আসলে nginx-এর prefix (`/etc/nginx`)-এর সাপেক্ষে। আর lint-এর জন্য include-এর বিষয়বস্তু নয়, **কোন file include হচ্ছে** — সেটাই প্রশ্ন। এখন include expand করা হয় না।

### 9.3 Pool-এর আকার — আসল output

```bash
python3 fpm_pool_calc.py --ram-mb 2048 --reserved-mb 700 --avg-proc-mb 60
printf '51200 58368 61440 49152\n' | python3 fpm_pool_calc.py --ram-mb 1024 --reserved-mb 600 --rss-stdin
python3 fpm_pool_calc.py --ram-mb 512 --reserved-mb 450 --avg-proc-mb 60
```

```text
php_budget_mb          1213
pm                     dynamic
pm.max_children        20
pm.start_servers       5
pm.min_spare_servers   2
pm.max_spare_servers   10
pm.max_requests        500

measured 4 processes, mean RSS 53.8 MB → using 64.5 MB
php_budget_mb          382

error: only 56 MB for PHP — not enough for 2 workers of 60 MB
```

(দ্বিতীয় উদাহরণের RSS সংখ্যাগুলো হাতে লেখা উদাহরণ — Ubuntu-তে `ps -o rss= -C php-fpm8.3` থেকে আসল মান দিন।)

### 9.4 Ubuntu-তে WordPress (চালানো হয়নি)

```bash
sudo apt install php8.3-fpm php8.3-mysql php8.3-xml php8.3-mbstring mariadb-server
sudo mysql -e "CREATE DATABASE blog; CREATE USER 'blog'@'localhost' IDENTIFIED BY '<দীর্ঘ এলোমেলো password>'; GRANT ALL ON blog.* TO 'blog'@'localhost';"
# WordPress download — wordpress.org থেকে, checksum যাচাই করে (https://wordpress.org/download/)
sudo cp wordpress.conf /etc/nginx/sites-available/blog.conf && sudo ln -s ../sites-available/blog.conf /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
python3 fcgi_client.py 127.0.0.1:9000 --script /var/www/wordpress/index.php --root /var/www/wordpress   # FPM-কে সরাসরি (listen TCP হলে)
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: blog.example.com' http://127.0.0.1/wp-content/uploads/x.jpg/y.php   # 404/403
curl -s -o /dev/null -w '%{http_code}\n' -H 'Host: blog.example.com' http://127.0.0.1/wp-config.php                     # 403
```

### 9.5 Test

```bash
python3 -m unittest -v
```

৭টি test:

- FastCGI record-এর বিন্যাস ও padding।
- Name-value দৈর্ঘ্য (১২৮+ → ৪ byte)।
- nginx-এর মতো params।
- **আসল php-cgi-তে তিনটি পরিস্থিতি** (php-cgi না থাকলে skip)।
- Pool-এর হিসাব।
- Broken ও good config।
- স্পষ্ট `SCRIPT_FILENAME` থাকলে ঠিক।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `record()` — `>BBHHBx` + padding | FastCGI header | Spec অনুযায়ী ৮-byte alignment |
| `name_value` — ১/৪ byte দৈর্ঘ্য | Params encode | দীর্ঘ মান (cookie) সমর্থন |
| BEGIN_REQUEST flags ০ | Request-শেষে connection বন্ধ | সরল client |
| `nginx_params(None, …)` | SCRIPT_FILENAME ছাড়া | `fastcgi_params`-এর ভুল পুনরুৎপাদন |
| `php-cgi -n -d cgi.fix_pathinfo=…` | php.ini উপেক্ষা, নির্দিষ্ট মান | পুনরুৎপাদনযোগ্য |
| `free_port()` + 127.0.0.1 | শুধু loopback | নিরাপদ, সমান্তরাল test |
| `calc()` — ×০.৯, peak-এ +২০% | সতর্ক হিসাব | Spike-এ OOM নয় |
| Lint-এ include expand নয় | কোন file include — সেটাই যাচাই | Prefix-relative include |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `php_fastcgi_demo.py` | fix_pathinfo=1-এ upload চলে, =0-এ 404 |
| `wp_nginx_lint.py wordpress-broken.conf` | ২ error + ৪ warning, exit ১ |
| `fpm_pool_calc.py --ram-mb 2048 …` | max_children ২০ |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `.php` file download হয় | PHP location মেলেনি | Location-এর ক্রম (L06-03); `fastcgi_pass` |
| `No input file specified.` / 404 | `SCRIPT_FILENAME` নেই বা ভুল root | `fastcgi.conf`; `root` ঠিক |
| `File not found.` (FPM) | Path FPM-এর chroot/permission-এ নেই | FPM user-এর পড়ার অনুমতি |
| 502, `connect() to unix:/run/php/… (2)` | FPM চলছে না বা ভিন্ন version-এর socket | `systemctl status php8.3-fpm`; socket নাম |
| 502, `(13: Permission denied)` | `listen.owner/group` | `www-data`; `socket_check.py` (L06-05) |
| `server reached pm.max_children` (FPM log) | Pool পূর্ণ | ধীর request? memory থাকলে বাড়ান |
| Spike-এ সব ধীর, swap | `max_children` বেশি | Memory থেকে হিসাব |
| 413 media upload-এ | `client_max_body_size` + `upload_max_filesize` | দুই জায়গাতেই |
| Permalink-এ 404 | `try_files … /index.php?$args` নেই | Front controller |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `try_files $uri =404` + uploads-এ PHP deny + `security.limit_extensions` + `cgi.fix_pathinfo=0` — চার স্তর।
  - প্রতি site আলাদা pool ও user (একটি site compromise হলে অন্যটি নিরাপদ)।
  - `wp-config.php` সুরক্ষা।
  - আপডেট।
  - Database user-এর শুধু নিজের database-এ অনুমতি।
  - Backup + restore test (L05-12)।
- **Performance:**
  - OPcache চালু (PHP-র compiled code cache)।
  - Static file nginx-এ (`expires`)।
  - Page cache (FastCGI cache বা plugin) — L06-06-এর নিয়মে, logged-in user বাদ দিয়ে।
  - Pool-এর আকার memory থেকে।
- **Cost:**
  - ছোট blog-এ `ondemand` pool + ছোট VM।
  - Managed WordPress hosting-এর সাথে তুলনা: আপনার সময় (আপডেট, নিরাপত্তা) সবচেয়ে বড় খরচ।
  - Compromised site-এর পরিষ্কার করার খরচ অনেক বেশি।

## 14. Hands-on exercise

1. Ubuntu-তে `php8.3-fpm` চালিয়ে pool-এ `listen = 127.0.0.1:9000` দিন। `fcgi_client.py` দিয়ে Section 9.1-এর তৃতীয় case পরীক্ষা করুন: `security.limit_extensions` default ও খালি — দুই অবস্থায় কী হয়?
2. `wordpress-broken.conf`-এর ছয়টি finding ঠিক করে lint ০-তে আনুন, তারপর `nginx -t`।
3. `fcgi_client.py`-তে POST body (`--data`) সমর্থন যোগ করে একটি PHP form-এ data পাঠান।
4. Ubuntu-তে PHP-FPM-এর `pm.status_path = /status` চালু করে `fcgi_client.py` দিয়ে status পড়ুন। Active/idle process কত?
5. WordPress install করে `ab -n 500 -c 20` দিয়ে home page-এর load test করুন। FPM log-এ `max_children`-এর সতর্কতা আসে কি? `fpm_pool_calc.py`-এর হিসাবের সাথে মেলান।

## 15. Mini-project — PHP site health

`php_site_check.py`:

- `fcgi_client.py` দিয়ে FPM-এর `/ping` ও `/status` (pool health)।
- nginx দিয়ে home page (L05-12-এর health check)।
- `wp_nginx_lint.py`।
- `wp-config.php`-এর permission।
- WordPress core-এর version (wp-includes/version.php থেকে) ও `cert_expiry.py` (L06-07)।
- JSON report ও exit code।

Lab 06-এর বাইরে, বাস্তব legacy site উদ্ধারের প্রথম ধাপ।

## 16. Interview প্রশ্ন

1. nginx কীভাবে PHP চালায়? FastCGI কী?
2. `fastcgi_params` ও `fastcgi.conf`-এর পার্থক্য কী?
3. `cgi.fix_pathinfo` কেন বিপজ্জনক? nginx-এ কীভাবে রক্ষা করবেন?
4. PHP-FPM-এর `pm.max_children` কীভাবে নির্ধারণ করবেন?
5. `.php` file download হয়ে যাচ্ছে — কারণ কী?
6. একটি WordPress server কীভাবে harden করবেন?

## 17. Self-assessment প্রশ্ন

1. অনুবাদক analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর প্রতিরক্ষার পাঁচটি স্তর কী, এবং কোনটি থাকলে ঘটনা ঘটত না?
3. `avatar.jpg/x.php` কেন fix_pathinfo=১-এ চলে, ০-তে চলে না?
4. Lint-এ include expand করা কেন ভুল ছিল?
5. FastCGI record-এ padding কেন?

## 18. সংক্ষিপ্ত সারাংশ

- nginx → FastCGI → PHP-FPM pool; `SCRIPT_FILENAME` (`fastcgi.conf`) অপরিহার্য।
- PHP location: `try_files $uri =404` + uploads-এ PHP deny + `limit_extensions` + `fix_pathinfo=0`।
- WordPress: `try_files $uri $uri/ /index.php?$args`; `wp-config.php` ও dotfile deny; upload-এর আকার।
- `pm.max_children` memory থেকে হিসাব; প্রতি site আলাদা pool ও user।
- `fcgi_client.py` দিয়ে nginx বাদ দিয়ে PHP-FPM-কে সরাসরি পরীক্ষা করুন।

## 19. Completion checklist

- [ ] `php_fastcgi_demo.py`-এর ছয়টি ফল ব্যাখ্যা করতে পারি
- [ ] (Ubuntu) PHP-FPM-এ `security.limit_extensions` পরীক্ষা করেছি
- [ ] WordPress config lint পরিষ্কার করেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- FastCGI Specification: https://fast-cgi.github.io/spec
- nginx — `ngx_http_fastcgi_module`: https://nginx.org/en/docs/http/ngx_http_fastcgi_module.html
- PHP — FastCGI Process Manager (FPM) configuration: https://www.php.net/manual/en/install.fpm.configuration.php
- PHP — `cgi.fix_pathinfo` (php.ini directives): https://www.php.net/manual/en/ini.core.php
- WordPress — Hardening WordPress: https://developer.wordpress.org/advanced-administration/security/hardening/
- WordPress — Nginx (Advanced Administration Handbook): https://developer.wordpress.org/advanced-administration/server/web-server/nginx/
- nginx — PHP FastCGI Example (nginx wiki): https://www.nginx.com/resources/wiki/start/topics/examples/phpfcgi/

---

**পরের lesson:** L07-01 — Virtualization ও hypervisor
