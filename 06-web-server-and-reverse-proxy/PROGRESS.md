# Module 06 Progress — Web Server and Reverse Proxy

Content status: `NOT_STARTED` · `IN_PROGRESS` · `COMPLETED` · `NEEDS_REVISION` (Claude update করবে)  
Learner status: Not started · In progress · Practiced · Assessment passed · Project completed · Needs revision (আপনি update করবেন)

| ID | Lesson | Content | Learner | Required files | Validation | Prerequisites | Next |
|---|---|---|---|---|---|---|---|
| L06-01 | [DNS record ও domain configuration](L06-01-dns-records-domains.md) | COMPLETED | Not started | `L06-01-dns-records-domains.md`, `code/L06-01/zone_lint.py`, `example-zone.txt`, `test_l06_01.py` | 8 test pass; নমুনা zone-এর 6 error ধরা; ipaddress.is_private ফাঁদ ধরা ও ঠিক; getaddrinfo-তে আসল lookup; dig/named-checkzone চালানো হয়নি | L05-13 | L06-02 |
| L06-02 | [Nginx architecture: master, worker, event loop](L06-02-nginx-architecture.md) | COMPLETED | Not started | `L06-02-nginx-architecture.md`, `code/L06-02/nginx_conf.py`, `sample-nginx.conf`, `conf.d/taskflow.conf`, `event_loop_demo.py`, `test_l06_02.py` | 8 test pass; event loop বনাম thread pool মাপা (1.2 ms বনাম 2.7 s; 500 slow-এ 30 s-এ উত্তর নেই); unclosed socket ধরা ও ঠিক; nginx নেই — Ubuntu command চালানো হয়নি | L06-01 | L06-03 |
| L06-03 | [Nginx server block (virtual host)](L06-03-nginx-server-blocks.md) | COMPLETED | Not started | `L06-03-nginx-server-blocks.md`, `code/L06-03/server_select.py`, `sites.conf`, `test_l06_03.py` | 8 test pass (nginx documentation-এর উদাহরণ); PCRE named group, Host normalization bug, ভুল test প্রত্যাশা, Git Bash path conversion ধরা; আসল nginx-এ যাচাই হয়নি | L06-02 | L06-04 |
| L06-04 | [Reverse proxy ও upstream](L06-04-reverse-proxy-upstream.md) | COMPLETED | Not started | `L06-04-reverse-proxy-upstream.md`, `code/L06-04/proxy_uri.py`, `proxy_lint.py`, `error_explainer.py`, `keepalive_bench.py`, `taskflow.conf`, `taskflow-broken.conf`, `sample-error.log`, `test_l06_04.py` | 9 test pass (nginx doc উদাহরণ); keepalive মাপা: 152–174 বনাম ~2260 req/s; sample-error.log হাতে বানানো; nginx-এ চালানো হয়নি | L06-03, L05-13 | L06-05 |
| L06-05 | [Application process, port, unix socket ও systemd service](L06-05-app-process-socket-systemd.md) | COMPLETED | Not started | `L06-05-app-process-socket-systemd.md`, `code/L06-05/bind_probe.py`, `socket_check.py`, `layout-home.json`, `layout-run.json`, `taskflow_serve.py`, `taskflow.socket`, `taskflow.service`, `test_l06_05.py` | 10 test: 8 pass, 2 skip (POSIX unix socket ও socket activation); Windows bind আচরণ মাপা (0.0.0.0 + 127.0.0.1 একসাথে bind); systemd-এ চালানো হয়নি | L06-04 | L06-06 |
| L06-06 | [Nginx caching ও compression](L06-06-caching-compression.md) | COMPLETED | Not started | `L06-06-caching-compression.md`, `code/L06-06/cache_sim.py`, `gzip_bench.py`, `test_l06_06.py` | 8 test pass; gzip level 1/5/9 আসলে মাপা (level 9 সবসময় ছোট নয়); benchmark-এর অস্থিরতা ধরা ও ঠিক; cache সিদ্ধান্ত nginx নিয়মের অনুকরণ, stampede model; nginx-এ চালানো হয়নি | L06-05 | L06-07 |
| L06-07 | [Nginx-এ TLS ও certificate](L06-07-nginx-tls-certificates.md) | COMPLETED | Not started | `L06-07-nginx-tls-certificates.md`, `code/L06-07/pki_lab.py`, `cert_expiry.py`, `tls_conf_lint.py`, `taskflow-tls.conf`, `taskflow-tls-broken.conf`, `test_l06_07.py` | 7 test pass; lab PKI-তে 5টি deployment ভুল আসলে চালানো (OpenSSL 3.5); live expiry check; stem-collision ও redirect false positive ধরা ও ঠিক; nginx/certbot-এ চালানো হয়নি | L06-06 | L06-08 |
| L06-08 | [Linux server hardening](L06-08-linux-server-hardening.md) | COMPLETED | Not started | `L06-08-linux-server-hardening.md`, `code/L06-08/harden_audit.py`, `sample-root/`, `test_l06_08.py` | 6 test pass (হাতে তৈরি sample-root); read-only audit; sshd first-value-wins/cloud-init ফাঁদ দেখানো; Windows path separator ঠিক; আসল Ubuntu-তে চালানো হয়নি (VM label) | L06-07 | L06-09 |
| L06-09 | [PHP-FPM ও WordPress deployment](L06-09-php-fpm-wordpress.md) | COMPLETED | Not started | `L06-09-php-fpm-wordpress.md`, `code/L06-09/fcgi_client.py`, `php_fastcgi_demo.py`, `fpm_pool_calc.py`, `wp_nginx_lint.py`, `wordpress.conf`, `wordpress-broken.conf`, `test_l06_09.py` | 7 test pass; নিজের FastCGI client দিয়ে আসল php-cgi 8.5-এ তিন পরিস্থিতি (upload-execution সহ) চালানো; PHP-FPM নয় (Windows) — limit_extensions পরীক্ষা হয়নি; WordPress/nginx চালানো হয়নি | L06-08 | L07-01 |

## Module assessment

| Assessment | Score | তারিখ |
|---|---|---|
| [Module quiz](../assessments/06-web-server-and-reverse-proxy/quiz.md) | — | — |
| [Level A lab](../labs/06-web-server-and-reverse-proxy/A-static-site-server-blocks/README.md) | — | — |
| [Level B lab](../labs/06-web-server-and-reverse-proxy/B-taskflow-behind-nginx-tls/README.md) | — | — |
| [Level C lab](../labs/06-web-server-and-reverse-proxy/C-proxy-socket-cert-failures/README.md) | — | — |
