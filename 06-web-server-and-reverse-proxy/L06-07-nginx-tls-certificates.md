# L06-07 — Nginx-এ TLS ও certificate

| | |
|---|---|
| **Module** | 06 — Web Server and Reverse Proxy |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L02-08 — TLS ও certificate](../02-computer-networking/L02-08-tls-certificates.md), [L06-04 — Reverse proxy](L06-04-reverse-proxy-upstream.md), [L06-01 — DNS (CAA)](L06-01-dns-records-domains.md) |
| **Label** | — |
| **Tested** | `pki_lab.py`, `cert_expiry.py`, `tls_conf_lint.py`: ৭টি test পাস (Python 3.14.5, OpenSSL 3.5.6, Windows)। **আসলে চালানো হয়েছে:** lab PKI (root → intermediate → server, এবং একটি সত্যিকারের মেয়াদোত্তীর্ণ certificate), loopback-এ TLS server-এর সাথে পাঁচটি deployment ভুল, এবং `example.com` ও `expired.badssl.com`-এর live মেয়াদ। লেখার সময় দুটি bug ধরা পড়েছে (Section 9.4)। nginx ও certbot-এ **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- nginx-এ HTTPS: `listen 443 ssl`, `ssl_certificate` (**fullchain**), `ssl_certificate_key`, `ssl_protocols`, HTTP → HTTPS redirect, HSTS।
- Certificate chain: root → intermediate → leaf; কেন intermediate না পাঠালে browser চলে কিন্তু `curl`/API client ব্যর্থ হয়।
- পাঁচটি deployment ভুল — **আসলে ঘটিয়ে দেখা**: intermediate বাদ, ভুল ক্রম, মেয়াদোত্তীর্ণ, ভুল key, ভুল নাম।
- Let's Encrypt ও ACME: HTTP-01 বনাম DNS-01, certbot, auto-renewal, CAA (L06-01)।
- **মেয়াদ নজরদারি:** কেন "auto-renew আছে" যথেষ্ট নয়।
- TLS session cache, HTTP/2, OCSP stapling — সংক্ষেপে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L06-04 পর্যন্ত TaskFlow চলছে plain HTTP-তে — password, token, data সব network-এ খোলা। HTTPS এখন ঐচ্ছিক নয়: browser HTTP site-কে "Not secure" দেখায়, HTTP/2 কার্যত HTTPS-নির্ভর, আর অনেক API client শুধু HTTPS-এ কথা বলে।

কিন্তু TLS-এর সবচেয়ে সাধারণ outage **cryptography-র ভুল নয় — operational ভুল:**

- **Certificate-এর মেয়াদ শেষ।** Auto-renewal নীরবে ব্যর্থ হয়েছিল, কেউ জানত না।
- **Intermediate বাদ পড়েছে।** Browser-এ ঠিক দেখায় (cache থেকে intermediate আনে), কিন্তু mobile app ও partner-এর API integration ভেঙে যায়।
- **Renewal-এর পরে nginx reload হয়নি।** Disk-এ নতুন certificate, অথচ memory-তে পুরোনোটা চলছে।

## 3. সহজ ভাষায় পরিচয়

```nginx
server {                                  # port 80: শুধু redirect (+ ACME challenge)
    listen 80;
    server_name taskflow.example.com;
    location /.well-known/acme-challenge/ { root /var/www/certbot; }
    location / { return 301 https://$host$request_uri; }
}
server {
    listen 443 ssl;
    http2 on;
    server_name taskflow.example.com;
    ssl_certificate     /etc/letsencrypt/live/taskflow.example.com/fullchain.pem;   # leaf + intermediate
    ssl_certificate_key /etc/letsencrypt/live/taskflow.example.com/privkey.pem;
    ssl_protocols TLSv1.2 TLSv1.3;
    add_header Strict-Transport-Security "max-age=31536000" always;
    …
}
```

| File | কী আছে | কে পড়ে |
|---|---|---|
| `fullchain.pem` | Leaf + intermediate (এই ক্রমে) | nginx `ssl_certificate` |
| `privkey.pem` | Private key — root, `0600` | nginx master (root) |
| `cert.pem` | শুধু leaf | **nginx-এ নয়** (chain অসম্পূর্ণ) |
| `chain.pem` | শুধু intermediate | `ssl_trusted_certificate` (OCSP stapling) |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### পরিচয়পত্র ও সত্যায়ন

- **Leaf certificate** = আপনার পরিচয়পত্র।
- **Intermediate CA** = যে অফিস পরিচয়পত্র ইস্যু করেছে, তার নিজের সত্যায়িত কাগজ।
- **Root CA** = সরকার, যাকে সবাই আগে থেকেই বিশ্বাস করে (OS/browser-এর trust store)।
- **Fullchain** = দেখানোর সময় পরিচয়পত্রের সাথে ইস্যুকারী অফিসের সত্যায়নও দেখানো।
- **মেয়াদ** = পরিচয়পত্রের মেয়াদ।

### Analogy কোথায় মেলে না

- **দারোয়ান নিজে কখনো কখনো ইস্যুকারী অফিসের কাগজ খুঁজে আনেন।** Browser-রা অনুপস্থিত intermediate cache থেকে বা AIA URL থেকে নিজে আনে। তাই developer browser-এ test করে বলেন "ঠিক আছে", অথচ `curl`, Python `requests`, Java, Android-এর পুরোনো version ব্যর্থ হয়। Section 9.1-এ ঠিক এটাই: `unable to get local issuer certificate`। কেউ "চোখে দেখে" এই ভুল ধরতে পারে না।
- **পরিচয়পত্রের মেয়াদ বছরের পর বছর।** Let's Encrypt-এর certificate ৯০ দিনের, এবং শিল্প আরও ছোট মেয়াদের দিকে যাচ্ছে। হাতে নবায়ন অসম্ভব — automation বাধ্যতামূলক। আর automation নীরবে ব্যর্থ হয়।
- **পরিচয়পত্র বদলালে পকেটে নতুনটা থাকে।** nginx চালু হওয়ার সময় certificate memory-তে load করে। Disk-এর file বদলালেও reload না করা পর্যন্ত পুরোনোটাই দেখায়। Certbot-এর `--deploy-hook "systemctl reload nginx"` এই কাজের জন্য।

## 5. Real-world engineering scenario — "শনিবার সকালে সব API integration বন্ধ"

**পরিস্থিতি:** TaskFlow-এর certificate Let's Encrypt-এর, এবং certbot timer চালু। তিন মাস পরে এক শনিবার partner-দের সব API call ব্যর্থ: `certificate has expired`।

**তদন্তে তিনটি স্তরের ব্যর্থতা:**

1. **Renewal ব্যর্থ:** কেউ port 80-এর server-এ `return 301`-কে `location /`-এর বাইরে server-স্তরে সরিয়ে দিয়েছিল। ফলে `/.well-known/acme-challenge/`-ও HTTPS-এ redirect হচ্ছিল, এবং HTTP-01 challenge ব্যর্থ। (Let's Encrypt redirect অনুসরণ করে, কিন্তু HTTPS-এর certificate মেয়াদ শেষের কাছে থাকলে অন্য সমস্যাও দেখা দেয়।) Certbot-এর error শুধু তার log-এ ছিল।
2. **সতর্কতা কেউ দেখেনি:** Let's Encrypt-এর মেয়াদ-সতর্কতার email যেত একজন প্রাক্তন কর্মীর ঠিকানায়।
3. **নজরদারি নেই:** বাইরে থেকে মেয়াদ দেখার কোনো check ছিল না।

**এই lesson-এর প্রতিরোধ:**

- `cert_expiry.py --host taskflow.example.com --warn-days 21 --crit-days 7` monitoring-এ (exit ০/১/২/৩ — L05-08)।
  - এখানে আসল চালানো: `expired.badssl.com` → `CRITICAL -4215.3 days left`।
- `tls_conf_lint.py` port-80-এর redirect ও ACME path যাচাই করে।
- `certbot renew --dry-run` CI বা মাসিক timer-এ।
- `--deploy-hook "systemctl reload nginx"`।

**শিক্ষা:** Auto-renewal একটি system — যেকোনো system-এর মতো এটারও monitoring লাগে। Certificate-এর মেয়াদ বাইরে থেকে মাপুন, ভেতরের script-এর সফলতায় বিশ্বাস করবেন না।

## 6. Diagram — chain যাচাই

```text
 client (trust store: Root CA-গুলো)                         nginx :443
     │ ClientHello (SNI: taskflow.example.com) ─────────────►│ SNI দেখে server block বাছাই (L06-03)
     │◄───────────────── Certificate: [leaf, intermediate] ──│ ssl_certificate = fullchain.pem
     │ যাচাই:
     │   leaf.issuer == intermediate.subject?  signature ঠিক?
     │   intermediate.issuer == Root (trust store-এ)?      ── intermediate না পাঠালে: "unable to get local issuer certificate"
     │   আজ notBefore ≤ now ≤ notAfter?                     ── না: "certificate has expired"
     │   SAN-এ taskflow.example.com আছে?                     ── না: "Hostname mismatch"
     │ (nginx নিজে চালু হওয়ার সময়: প্রথম cert ↔ private key মেলে? ── না: "key values mismatch", nginx -t ব্যর্থ)
     ▼
 TLS 1.3 session ─► HTTP/2 ─► proxy_pass unix socket (L06-05)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Leaf / end-entity certificate | Domain-এর certificate |
| Intermediate CA | Root-এর পক্ষে certificate ইস্যু করে |
| Fullchain | Leaf + intermediate, এই ক্রমে |
| SAN (Subject Alternative Name) | Certificate কোন নামগুলোর জন্য বৈধ |
| SNI | ClientHello-তে কোন নাম চাওয়া হচ্ছে |
| ACME | Certificate স্বয়ংক্রিয়ভাবে নেওয়ার protocol (Let's Encrypt) |
| HTTP-01 / DNS-01 | Domain-এর মালিকানা প্রমাণ — web path / TXT record |
| HSTS | Browser-কে বলা "এই site শুধু HTTPS-এ" |
| OCSP stapling | Server নিজে revocation-এর প্রমাণ সাথে পাঠায় |
| Session resumption | আগের TLS session-এর তথ্যে দ্রুত handshake |
| `KEY_VALUES_MISMATCH` | Certificate-এর public key আর দেওয়া private key মেলে না |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 nginx certificate কীভাবে load করে

`ssl_certificate` file-এর প্রথম certificate হলো leaf, যার public key `ssl_certificate_key`-এর সাথে মিলতে হবে। বাকিগুলো (intermediate) client-কে পাঠানো হয়।

ক্রম উল্টালে প্রথম certificate হয় intermediate, যার key ভিন্ন। ফলে OpenSSL `key values mismatch` দেয়, এবং nginx চালু বা reload হয় না। `nginx -t` এটা ধরে — ভাগ্যক্রমে, কারণ চলমান nginx পুরোনো config-এ চলতে থাকে।

`pki_lab.py` এই একই OpenSSL আচরণ Python-এর `ssl.load_cert_chain`-এ দেখায়।

### 8.2 Intermediate কেন বাদ পড়ে

Certbot-এর `cert.pem` শুধু leaf, `fullchain.pem` দুটোই। পুরোনো tutorial বা অন্য CA-র নির্দেশে আলাদা "CA bundle" file আসে, যা nginx-এ (Apache-র মতো আলাদা directive না থাকায়) leaf-এর **পরে** জুড়ে দিতে হয়: `cat leaf.crt intermediate.crt > fullchain.pem`।

### 8.3 Protocol ও cipher

TLS 1.0/1.1 বাতিল (RFC 8996)। `ssl_protocols TLSv1.2 TLSv1.3;` যথেষ্ট। TLS 1.3-এর cipher suite আলাদা, এবং OpenSSL-এর default-ই নিরাপদ। পুরোনো blog-এর লম্বা `ssl_ciphers` তালিকা প্রায়ই ক্ষতি করে (RC4, 3DES)। Mozilla SSL Configuration Generator-এর "intermediate" profile একটি ভালো শুরু।

### 8.4 HSTS

`Strict-Transport-Security: max-age=…` পাওয়ার পরে browser ওই সময় পর্যন্ত HTTP-তে যায়ই না। Certificate ভাঙলে user "তবুও চালিয়ে যান"-ও পান না। তাই:

- প্রথমে ছোট `max-age` (যেমন ৩০০) দিয়ে শুরু করুন;
- `includeSubDomains` ও `preload` সব subdomain-এ HTTPS নিশ্চিত হওয়ার পরে।

`add_header`-এ `always` না দিলে 4xx/5xx response-এ header যায় না।

> **Fedora-তে:** `dnf install certbot python3-certbot-nginx`। System trust store `/etc/pki/ca-trust/` (`update-ca-trust`); Ubuntu-তে `/usr/local/share/ca-certificates/` + `update-ca-certificates`। SELinux-এ certificate file-এর context `cert_t`।

## 9. Practical demonstration

Files:

- [`code/L06-07/pki_lab.py`](code/L06-07/pki_lab.py), [`cert_expiry.py`](code/L06-07/cert_expiry.py), [`tls_conf_lint.py`](code/L06-07/tls_conf_lint.py)।
- [`taskflow-tls.conf`](code/L06-07/taskflow-tls.conf) (ঠিক) ও [`taskflow-tls-broken.conf`](code/L06-07/taskflow-tls-broken.conf) (ভুলসহ)।
- [`test_l06_07.py`](code/L06-07/test_l06_07.py)।

### 9.1 পাঁচটি deployment ভুল — আসল output

```bash
cd ~/devops-ai-engineering/06-web-server-and-reverse-proxy/code/L06-07
python3 pki_lab.py scenarios
```

```text
fullchain (leaf + intermediate)      → OK TLSv1.3 — notAfter Nov 26 08:10:10 2026 GMT
leaf only — intermediate missing     → VERIFY FAILED: unable to get local issuer certificate
wrong order (intermediate first)     → server refuses to start: KEY_VALUES_MISMATCH
expired leaf                         → VERIFY FAILED: certificate has expired
key does not match certificate       → server refuses to start: KEY_VALUES_MISMATCH
```

- মোট সময় ০.৩ s।
- Client শুধু lab-এর root-কে বিশ্বাস করে, browser-এর মতো।
- মেয়াদোত্তীর্ণ certificate OpenSSL ৩.৫-এর `-not_before 20250101000000Z -not_after 20250201000000Z` দিয়ে আসলেই বানানো।
- Test-এ ষষ্ঠ case: ভুল নাম (`other.example.com`) → `Hostname mismatch`।

### 9.2 মেয়াদ নজরদারি — আসল output

```bash
python3 cert_expiry.py lab-pki/server.crt lab-pki/expired.crt lab-pki/server.key --warn-days 45 --crit-days 7
python3 cert_expiry.py --host example.com:443 --host expired.badssl.com:443
```

```text
WARNING   …/server.crt     30.0 days left (notAfter 2026-11-26 08:11Z)  [28 ms]
CRITICAL  …/expired.crt  -633.3 days left (notAfter 2025-02-01 00:00Z)  [21 ms]
UNKNOWN   …/server.key   cannot read: Could not find certificate from …/server.key  [25 ms]
exit=2

OK        example.com:443                             59.6 days left (notAfter 2026-12-25 22:56Z)  [191 ms]
CRITICAL  expired.badssl.com:443                   -4215.3 days left (notAfter 2015-04-12 23:59Z)  [1081 ms]
exit=2
```

(Live check ২০২৬-১০-২৭-এ। `expired.badssl.com` ইচ্ছাকৃত মেয়াদোত্তীর্ণ certificate-এর একটি public test site।) মেয়াদ পড়ার জন্য live check verification বন্ধ রাখে — নইলে মেয়াদোত্তীর্ণ certificate-এর তারিখই পড়া যেত না।

### 9.3 Config lint — আসল output

```bash
python3 tls_conf_lint.py taskflow-tls-broken.conf; echo "exit=$?"
python3 tls_conf_lint.py taskflow-tls.conf
```

```text
WARNING taskflow-tls-broken.conf:11 maybe-no-chain     ssl_certificate cert.pem: if this is the leaf only, … — use fullchain.pem
WARNING taskflow-tls-broken.conf:12 key-location       private key in /tmp/taskflow.key — keep it under /etc (root, 0600)
ERROR   taskflow-tls-broken.conf:13 old-protocol       ssl_protocols allows TLSv1, TLSv1.1 — use TLSv1.2 TLSv1.3
ERROR   taskflow-tls-broken.conf:14 weak-cipher        ssl_ciphers includes weak suites: HIGH:RC4:3DES
WARNING taskflow-tls-broken.conf:15 server-tokens      server_tokens on reveals the nginx version
WARNING taskflow-tls-broken.conf:16 hsts-not-always    add_header without 'always' is skipped on 4xx/5xx responses
WARNING taskflow-tls-broken.conf:2 no-https-redirect  port-80 server for taskflow.example.com does not redirect to https
7 finding(s)
exit=1

0 finding(s)
```

### 9.4 লেখার সময় ধরা পড়া দুটি bug

1. **File-এর stem দিয়ে dict:** প্রথম run-এ crash হলো: `ssl.SSLError: [X509: NO_CERTIFICATE_OR_CRL_FOUND]`। `{p.stem: p}`-এ `root.crt` ও `root.key` দুটোরই stem `root`, তাই একটি অন্যটিকে মুছে দিচ্ছিল, এবং client trust store হিসেবে **private key** পাচ্ছিল। এখন পুরো file নাম।
2. **Lint-এর false positive:** সঠিক config-এ "no-https-redirect" এসেছিল। Redirect সেখানে `location /`-এর ভেতরে, কারণ ACME challenge-এর path redirect থেকে বাদ রাখতে হয়। Lint শুধু server-স্তরের `return` দেখছিল। এখন পুরো server block খোঁজে, এবং একটি regression test আছে।

দ্বিতীয়টি Section 5-এর গল্পের সাথে সরাসরি যুক্ত: lint "সংশোধন" মেনে redirect server-স্তরে তুলে দিলে ACME challenge ভাঙত।

### 9.5 Ubuntu-তে (চালানো হয়নি)

```bash
# Lab-এ (আসল domain ছাড়া): lab PKI দিয়ে
python3 pki_lab.py create --out /tmp/lab-pki
sudo install -d -m 0750 /etc/nginx/tls
sudo install -m 0644 /tmp/lab-pki/fullchain.pem /etc/nginx/tls/
sudo install -m 0600 /tmp/lab-pki/server.key /etc/nginx/tls/
# taskflow-tls.conf-এর ssl_certificate path বদলে /etc/nginx/tls/… তারপর:
sudo nginx -t && sudo systemctl reload nginx
curl --cacert /tmp/lab-pki/root.crt --resolve taskflow.example.com:443:127.0.0.1 https://taskflow.example.com/health
openssl s_client -connect 127.0.0.1:443 -servername taskflow.example.com -showcerts </dev/null 2>/dev/null | grep -c BEGIN   # 2 = fullchain

# আসল domain থাকলে (Let's Encrypt; খরচ নেই, rate limit আছে — আগে --staging):
sudo certbot --nginx -d taskflow.example.com --staging
sudo certbot renew --dry-run
systemctl list-timers | grep certbot
```

### 9.6 Test

```bash
python3 -m unittest -v
```

৭টি test:

- পাঁচটি scenario।
- ভুল hostname।
- File থেকে মেয়াদ ও exit code (OK / CRITICAL / UNKNOWN)।
- Threshold।
- Broken config-এর সাত finding।
- ভালো config পরিষ্কার (regression)।
- Negate করা দুর্বল cipher (`!RC4`) ঠিক আছে।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `create()` — EC P-256, ৩০ দিন | Lab root/intermediate/leaf | দ্রুত ও আধুনিক; lab-এর জন্য ছোট মেয়াদ |
| `pathlen:0`, `CA:FALSE`, `serverAuth`, SAN | সঠিক extension | আধুনিক client SAN ছাড়া CN দেখে না |
| `-not_before/-not_after` | আসল মেয়াদোত্তীর্ণ cert | OpenSSL ৩.৪+ |
| `serve_once` → `load_cert_chain`-এর error | "Server চালু হয় না" | nginx-এর `nginx -t`-এর সমতুল্য |
| `create_default_context(cafile=root)` | শুধু lab root বিশ্বাস | Intermediate না পাঠালে ব্যর্থ — browser-এর মতো AIA fetch নয় |
| `CERT_NONE` live expiry-তে | মেয়াদোত্তীর্ণ cert-এর তারিখ পড়া | শুধু তারিখের জন্য, ডেটা পাঠানোর জন্য নয় |
| `p.name` key | Stem-এর সংঘাত নয় | Section 9.4 |
| Redirect পুরো server block-এ খোঁজা | Location-এর ভেতরেও বৈধ | ACME path |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `pki_lab.py scenarios` | ১টি OK, ২টি VERIFY FAILED, ২টি refuses to start |
| `cert_expiry.py` মেয়াদোত্তীর্ণ file-এ | CRITICAL, exit ২ |
| `tls_conf_lint.py taskflow-tls-broken.conf` | ৭টি finding, exit ১ |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Browser-এ ঠিক, `curl`/app-এ `unable to get local issuer certificate` | Intermediate নেই | `fullchain.pem`; `openssl s_client -showcerts`-এ ২টি cert |
| `nginx -t`: `key values mismatch` | ভুল key বা chain-এর ক্রম উল্টো | Leaf আগে; `openssl x509 -pubkey` বনাম `openssl pkey -pubout` তুলনা |
| `certificate has expired` | Renewal ব্যর্থ বা reload হয়নি | `certbot renew --dry-run`; deploy hook; মেয়াদ নজরদারি |
| `Hostname mismatch` | SAN-এ নাম নেই, বা SNI-তে ভুল server block | `-d` সব নাম; `server_name` |
| Renewal-এ challenge ব্যর্থ | Port 80 বন্ধ বা ACME path redirect/deny | `location /.well-known/acme-challenge/` |
| HTTPS-এ app ভাবে http, ভুল redirect | `X-Forwarded-Proto` নেই | L06-04 |
| HSTS-এর পরে site খোলা যাচ্ছে না | Certificate ভাঙা + HSTS | Certificate ঠিক করুন; শুরুতে ছোট max-age |
| Certbot নতুন cert দিল কিন্তু পুরোনোটা দেখায় | nginx reload হয়নি | `--deploy-hook "systemctl reload nginx"` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Private key root-মালিকানায় `0600`, কখনো Git-এ নয় (L05-10-এর scanner `private-key` ধরে)।
  - TLS 1.2+; HSTS; CAA (L06-01)।
  - HTTP-তে শুধু redirect ও ACME।
  - Upstream-এ (nginx → app) unix socket, তাই internal TLS লাগে না। ভিন্ন machine-এ গেলে mTLS বিবেচনা (Module 19/28)।
- **Performance:**
  - TLS 1.3-এ এক round-trip-এ handshake।
  - `ssl_session_cache shared:SSL:10m` — resumption।
  - HTTP/2 একটি connection-এ বহু request।
  - ECDSA (P-256) key RSA-র চেয়ে দ্রুত handshake দেয়।
- **Cost:**
  - Let's Encrypt বিনামূল্যে; managed certificate (AWS ACM) load balancer-এ বিনামূল্যে।
  - Certificate-এর মেয়াদ শেষে outage-এর খরচ (SLA, বিশ্বাস) বিশাল।
  - Monitoring-এর খরচ প্রায় শূন্য — এটাই সবচেয়ে ভালো বিনিয়োগ।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.5-এর lab অংশ চালান। `ssl_certificate`-এ `server.crt` (leaf only) দিয়ে `curl` ও browser দুটোতে দেখুন — পার্থক্য কী?
2. `fullchain.pem`-এর ক্রম উল্টে `sudo nginx -t` চালান। Error বার্তা `pki_lab.py`-এর সাথে মেলে কি?
3. `cert_expiry.py`-কে একটি systemd timer-এ (দৈনিক) বসান, এবং L05-12-এর `healthcheck.py`-তে একটি `cert_expiry` ধরনের check যোগ করুন।
4. `tls_conf_lint.py`-এ যোগ করুন: `ssl_stapling on` থাকলে `resolver` ও `ssl_trusted_certificate` আছে কিনা।
5. একটি test domain থাকলে (বা staging-এ) DNS-01 দিয়ে wildcard certificate নিন। HTTP-01-এর সাথে পার্থক্য লিখুন — কোনটা কখন?

## 15. Mini-project — Certificate inventory

`cert_inventory.py`:

- Server-এর সব nginx config (L06-02-এর parser) থেকে `ssl_certificate` path ও `server_name` সংগ্রহ।
- প্রতিটির মেয়াদ, SAN, issuer, chain-এর দৈর্ঘ্য।
- `server_name` SAN-এ আছে কিনা।
- Live check-এর সাথে disk-এর file-এর মেয়াদ মেলানো — না মিললে "reload দরকার"।

Lab 06-C-এর মেয়াদোত্তীর্ণ certificate পরিস্থিতিতে কাজে লাগবে।

## 16. Interview প্রশ্ন

1. Certificate chain কী? Intermediate বাদ পড়লে কী হয়, এবং browser-এ কেন ধরা পড়ে না?
2. nginx-এ `ssl_certificate`-এ কোন file দেবেন, কেন?
3. Let's Encrypt-এর HTTP-01 ও DNS-01-এর পার্থক্য কী?
4. Certificate-এর মেয়াদ শেষের outage কীভাবে ঠেকাবেন?
5. HSTS কী? এর ঝুঁকি কী?
6. `key values mismatch` error-এর দুটি কারণ কী?

## 17. Self-assessment প্রশ্ন

1. পরিচয়পত্র analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ তিনটি স্তরের ব্যর্থতা কী ছিল?
3. পাঁচটি scenario-র কোনগুলো client-এ ব্যর্থ, কোনগুলো server-এ?
4. Live expiry check-এ verification কেন বন্ধ রাখা হয়?
5. `p.stem`-এর bug কী ক্ষতি করছিল?

## 18. সংক্ষিপ্ত সারাংশ

- `ssl_certificate` = fullchain (leaf আগে); key root-এর `0600`।
- TLS 1.2/1.3; port 80 শুধু redirect + ACME; HSTS `always`, ছোট max-age দিয়ে শুরু।
- পাঁচটি সাধারণ ভুল: intermediate বাদ, ভুল ক্রম, ভুল key, মেয়াদ, নাম — client বনাম server-এ কোথায় ধরা পড়ে জানুন।
- Renewal automation + reload hook + **বাইরে থেকে মেয়াদ নজরদারি**।
- Browser-এ ঠিক দেখানো যথেষ্ট প্রমাণ নয় — `curl`/`openssl s_client` দিয়ে যাচাই করুন।

## 19. Completion checklist

- [ ] পাঁচটি scenario চালিয়ে প্রতিটির কারণ ব্যাখ্যা করতে পারি
- [ ] (Ubuntu) lab PKI দিয়ে nginx-এ HTTPS চালিয়েছি ও `openssl s_client`-এ chain দেখেছি
- [ ] মেয়াদ নজরদারি চালু করেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nginx — Configuring HTTPS servers: https://nginx.org/en/docs/http/configuring_https_servers.html
- nginx — `ngx_http_ssl_module`: https://nginx.org/en/docs/http/ngx_http_ssl_module.html
- Let's Encrypt — How it works / Challenge types: https://letsencrypt.org/docs/challenge-types/
- Certbot documentation: https://eff-certbot.readthedocs.io/
- Mozilla — SSL Configuration Generator: https://ssl-config.mozilla.org/
- RFC 8996 — Deprecating TLS 1.0 and TLS 1.1: https://www.rfc-editor.org/rfc/rfc8996
- RFC 6797 — HTTP Strict Transport Security: https://www.rfc-editor.org/rfc/rfc6797
- OpenSSL — `openssl-x509` (`-not_before`, `-not_after`): https://docs.openssl.org/3.5/man1/openssl-x509/

---

**পরের lesson:** L06-08 — Linux server hardening
