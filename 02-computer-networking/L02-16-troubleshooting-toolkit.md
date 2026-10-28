# L02-16 — Troubleshooting toolkit: dig, curl, ss, ip, traceroute, mtr

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | L02-01 থেকে L02-15 (এই lesson আগের সবকিছু একটি পদ্ধতিতে জোড়া দেয়) |
| **Label** | — |
| **Tested** | `netcheck.py`: ৭টি test পাস — loopback-এ সব স্তর PASS, HTTP 503, connection refused, plain-HTTP port-এ TLS, `.invalid` নামে DNS ব্যর্থতা, error শ্রেণিবিভাগ, JSON output (Python 3.14, Windows)। **আসল endpoint-এ চালানো হয়েছে** (২০২৬-১০-২৭): `example.com` (HTTP ও HTTPS), `expired.badssl.com`, `.invalid` নাম, বন্ধ local port; এবং Windows `tracert` ১.১.১.১ পর্যন্ত — output Section 9-এ। `dig`, `ss`, `ip`, `traceroute`, `mtr` **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- একটি **স্তরভিত্তিক পদ্ধতি**: নিচ থেকে উপরে (বা উপর থেকে নিচে), প্রতিটি স্তরে একটি প্রশ্ন ও একটি tool।
- প্রতিটি tool কী প্রশ্নের উত্তর দেয়: `ip`, `ping`, `dig`, `ss`, `nc`, `curl`, `openssl`, `traceroute`, `mtr`, `tcpdump`, `nstat`।
- Error message থেকে স্তর চেনা: "Name or service not known", "Connection refused", "timed out", "No route to host", "certificate verify failed", 502/504।
- **traceroute ও mtr সঠিকভাবে পড়া** — মাঝের hop-এর latency spike প্রায়ই বিভ্রান্তিকর।
- Python দিয়ে একটি স্তরভিত্তিক checker যা প্রথম ব্যর্থ স্তর দেখায় ও পরের command সুপারিশ করে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

"Site কাজ করছে না" — এই অভিযোগের পেছনে এই module-এর যেকোনো স্তর থাকতে পারে। অভিজ্ঞতাহীন engineer এলোমেলোভাবে চেষ্টা করেন: server restart, firewall বন্ধ, DNS cache flush — কখনো কাজ হয়, কেন হলো জানা যায় না, এবং প্রায়ই নতুন সমস্যা তৈরি হয়।

অভিজ্ঞ engineer **স্তর ধরে প্রমাণ** খোঁজেন: "নাম resolve হয়? → TCP connect হয়? → TLS ঠিক? → HTTP উত্তর কী?" প্রথম যে স্তরে ব্যর্থ, সমস্যা সেখানে বা তার নিচে। এতে:

- Incident-এর সময় কমে (MTTR, L00-01-এর DORA metric)।
- সঠিক team-কে সঠিক প্রমাণ সহ ডাকা যায় ("DNS ঠিক, TCP SYN-এর উত্তর নেই, এই capture দেখুন")।
- Postmortem-এ timeline সঠিক হয় (L00-06)।

## 3. সহজ ভাষায় পরিচয়

**স্তর ও প্রশ্ন:**

| স্তর | প্রশ্ন | Tool (Ubuntu) | Lesson |
|---|---|---|---|
| Local interface | আমার IP, link up? | `ip -br addr`, `ip link` | L02-02, L02-03 |
| Route | এই গন্তব্যে কোন পথে যাব? | `ip route get IP` | L02-04 |
| DNS | নাম → কোন IP? | `dig`, `getent hosts`, `resolvectl` | L02-06 |
| Reachability | Host-এ পৌঁছানো যায়? | `ping`, `traceroute`, `mtr` | L02-09 |
| TCP | Port-এ connect হয়? কে শুনছে? | `nc -zv`, `ss -ltnp`, `ss -tan` | L02-05 |
| Firewall | কোথাও আটকাচ্ছে? | `nft list ruleset`, SG/NACL, flow logs | L02-10, L02-14 |
| TLS | Certificate, chain, নাম ঠিক? | `openssl s_client` | L02-08 |
| HTTP | Status, header, timing? | `curl -v`, `curl -w` | L02-07, L02-12 |
| Packet | আসলে কী যাচ্ছে-আসছে? | `tcpdump` | L02-15 |
| Counter | Loss, retransmission, drop? | `nstat`, `ip -s link` | L02-05, L02-15 |

**Error message → স্তর:**

| Message | স্তর | প্রথম সন্দেহ |
|---|---|---|
| `Could not resolve host` / `Name or service not known` / `getaddrinfo failed` | DNS | নাম ভুল, resolver, `/etc/hosts` |
| `Connection refused` | TCP — host পৌঁছানো গেছে | Port-এ কিছু শুনছে না, ভুল bind address, firewall REJECT |
| `Connection timed out` | TCP/network | Firewall DROP, SG/NACL, route, host বন্ধ |
| `No route to host` / `Network is unreachable` | Routing | Route নেই, VPN বন্ধ, ICMP unreachable |
| `certificate verify failed` / `has expired` / `Hostname mismatch` | TLS | Chain, মেয়াদ, SAN |
| `502` / `504` | Proxy-র পেছনে | Backend বন্ধ / ধীর |
| ছোট চলে, বড় ঝোলে | MTU | PMTUD black hole |

**Refused বনাম timed out** — সবচেয়ে মূল্যবান পার্থক্য: refused মানে packet **পৌঁছেছে** এবং কেউ "না" বলেছে (RST); timeout মানে **কোনো উত্তরই আসেনি** — পথে কেউ নিঃশব্দে ফেলে দিচ্ছে।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ডাক্তারের রোগনির্ণয়

- ডাক্তার একসাথে সব ওষুধ দেন না। প্রথমে vital sign (তাপমাত্রা, রক্তচাপ), তারপর নির্দিষ্ট পরীক্ষা — প্রতিটি ফল পরের পরীক্ষা ঠিক করে।
- **স্তরভিত্তিক checklist** = triage protocol।
- **netcheck.py** = প্রাথমিক screening — কোথায় সমস্যা তা দ্রুত বলে, চিকিৎসা নয়।
- **tcpdump** = MRI — শক্তিশালী, কিন্তু প্রথম ধাপ নয়।

### Analogy কোথায় মেলে না

- রোগী একটি শরীর। Network-এ **দুই প্রান্ত ও মাঝের পথ** — client-এর দিক থেকে "সব ঠিক" মানে server-এর দিক থেকে ঠিক নয় (L02-14-এর return route)। প্রায়ই দুই প্রান্ত থেকে পরীক্ষা দরকার।
- রোগের লক্ষণ সাধারণত স্থির থাকে। Network সমস্যা প্রায়ই **মাঝে মাঝে** (intermittent) — একবার পরীক্ষায় ধরা পড়ে না; বারবার পরিমাপ (mtr, loop-এ netcheck, monitoring) লাগে।
- পরীক্ষা নিজে রোগীর অবস্থা বদলায় না। Network-এ কিছু "পরীক্ষা" অবস্থা বদলায়: DNS cache flush, connection restart, firewall rule বদলে দেখা — প্রমাণ নষ্ট হয়। আগে পর্যবেক্ষণ ও নথিভুক্তি, পরে পরিবর্তন।

## 5. Real-world engineering scenario — "Deploy-এর পরে API timeout"

**পরিস্থিতি:** নতুন অঞ্চলে service deploy করা হলো। Load balancer-এর health check সফল, কিন্তু অন্য একটি VPC-র client বলছে সব request timeout।

**স্তর ধরে (client থেকে):**

```bash
python3 netcheck.py https://api.new-region.internal/health --timeout 3
# PASS dns   → 10.3.10.25
# FAIL tcp   10.3.10.25:443 timeout
# next: packets dropped on the way (firewall DROP, security group, NACL, route) ...
```

1. DNS ঠিক — নাম সঠিক IP-তে যাচ্ছে।
2. TCP **timeout** (refused নয়) → packet পৌঁছাচ্ছে না বা উত্তর ফিরছে না।
3. `ip route get 10.3.10.25` client-এ: VPN/peering route আছে।
4. Server-এর পাশে capture (L02-15): `tcpdump -ni eth0 'tcp port 443 and host CLIENT_IP'` — **SYN আসছে, SYN-ACK যাচ্ছে**।
5. তাহলে ফেরার পথ: নতুন VPC-র route table-এ client VPC-র CIDR-এর route নেই (L02-14-এর `metrics-1`-এর মতো)। LB health check সফল কারণ LB একই VPC-তে।

**সমাধান:** return route যোগ; Terraform-এ, এবং deploy pipeline-এ cross-VPC `netcheck` যোগ যেন পরের বার আগেই ধরা পড়ে।

**শিক্ষা:** "Timeout" দেখলে **দুই দিকের পথ** ভাবুন; health check-এর সফলতা শুধু তার নিজের পথ প্রমাণ করে।

## 6. Diagram — সিদ্ধান্ত-বৃক্ষ

```text
                          "কাজ করছে না"
                               │
                     ┌─────────▼──────────┐   না → `getent hosts`, dig @resolver, /etc/hosts
                     │ নাম resolve হয়?     ├──────────────────────────────────────────────►
                     └─────────┬──────────┘
                               │ হ্যাঁ
                     ┌─────────▼──────────┐   refused → server-এ ss -ltnp, bind address
                     │ TCP connect হয়?     ├── timeout → route, SG/NACL/firewall, দুই প্রান্তে tcpdump
                     └─────────┬──────────┘   unreachable → ip route get, VPN/peering
                               │ হ্যাঁ
                     ┌─────────▼──────────┐   না → openssl s_client -servername; chain/expiry/SAN
                     │ TLS handshake ঠিক?  ├──────────────────────────────────────────────►
                     └─────────┬──────────┘
                               │ হ্যাঁ
                     ┌─────────▼──────────┐   4xx → request ভুল/auth; 5xx → app/proxy log
                     │ HTTP status?        ├── 502/504 → proxy → backend পথ (L02-12)
                     └─────────┬──────────┘
                               │ 2xx, কিন্তু ধীর/অনিয়মিত
                     curl -w timing, mtr (loss), tcpdump (retransmission), MTU (বড় response?)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Layered troubleshooting | স্তর ধরে প্রমাণ সংগ্রহ |
| Refused / timeout / unreachable | RST পাওয়া / কোনো উত্তর নয় / route বা ICMP unreachable |
| TTFB | Time to first byte |
| Hop | পথের একটি router |
| traceroute | TTL বাড়িয়ে প্রতিটি hop খোঁজা |
| mtr | traceroute + ping একসাথে, ধারাবাহিক পরিসংখ্যান |
| ICMP rate limiting / deprioritization | Router নিজের ICMP উত্তর কম অগ্রাধিকারে দেয় |
| Intermittent | মাঝে মাঝে ঘটা সমস্যা |
| Synthetic check | নির্দিষ্ট সময় অন্তর কৃত্রিম request দিয়ে যাচাই |
| MTTR | সমস্যা সমাধানের গড় সময় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 traceroute

TTL = ১ দিয়ে packet পাঠায় → প্রথম router TTL শূন্য করে "time exceeded" (ICMP type ১১, L02-09) ফেরত দেয় — সেটাই hop ১। তারপর TTL = ২, ৩… গন্তব্যে পৌঁছালে গন্তব্য উত্তর দেয়।

- Linux `traceroute` default-এ UDP (উঁচু port), `-I` ICMP, `-T -p 443` **TCP SYN** — firewall-এর পেছনের service-এর পথে TCP সবচেয়ে বাস্তবসম্মত।
- Windows `tracert` ICMP echo ব্যবহার করে।

**পড়ার নিয়ম:**

1. মাঝের একটি hop-এ বেশি latency কিন্তু **পরের hop-গুলো স্বাভাবিক** → ঐ router ICMP উত্তর দিতে দেরি করে (control plane-এ কম অগ্রাধিকার), আসল traffic নয়। সমস্যা নয়।
2. একটি hop থেকে শুরু করে **সব পরের hop-এ** latency/loss বেশি → সেখানেই আসল সমস্যা।
3. `* * *` মাঝে, কিন্তু পরে hop দেখা যায় → ঐ router উত্তর দেয় না, সমস্যা নয়।
4. Asymmetric routing — ফেরার পথ ভিন্ন হতে পারে; traceroute শুধু যাওয়ার পথ দেখায়।

### 8.2 mtr

প্রতিটি hop-এ ধারাবাহিক probe — loss% ও latency-র গড়/সর্বোচ্চ/stdev। Report mode (`mtr -rwbzc 100 HOST`) ticket-এ লাগানোর উপযুক্ত। একই পড়ার নিয়ম প্রযোজ্য: **loss যদি শেষ hop পর্যন্ত টিকে না থাকে, তা আসল loss নয়।**

### 8.3 `ss`, `ip`, `dig`, `curl` — সবচেয়ে কাজের option

```bash
ip -br addr                      # সংক্ষেপে সব interface ও IP
ip route get 10.3.10.25          # এই গন্তব্যের জন্য kernel কোন route, কোন source IP বাছবে
ip -s link show eth0             # RX/TX error, drop
ss -ltnp                         # কে কোন TCP port-এ শুনছে (process সহ)
ss -tan state established '( dport = :5432 )'   # নির্দিষ্ট গন্তব্যের connection
ss -s                            # সারাংশ — TIME-WAIT/CLOSE-WAIT সংখ্যা (L02-05)
dig +short NAME; dig NAME @8.8.8.8; dig +trace NAME
getent hosts NAME                # application যা দেখে (L02-06)
nc -zv HOST PORT                 # শুধু TCP connect পরীক্ষা
curl -sv -o /dev/null URL        # header ও TLS
curl -s -o /dev/null -w 'dns %{time_namelookup} tcp %{time_connect} tls %{time_appconnect} ttfb %{time_starttransfer} total %{time_total} code %{http_code}\n' URL
curl --resolve api.example.com:443:10.3.10.25 https://api.example.com/   # DNS বাদ দিয়ে নির্দিষ্ট IP-তে
nstat -az | grep -Ei 'retrans|listendrop|overflow'   # kernel counter
```

`curl --resolve` বিশেষভাবে কার্যকর: DNS পরিবর্তনের আগেই নতুন server পরীক্ষা, বা load balancer-এর পেছনের নির্দিষ্ট backend।

### 8.4 netcheck.py কীভাবে একই কাজ করে

`getaddrinfo` (application-এর মতো resolution, `/etc/hosts` সহ) → প্রতিটি address-এ TCP connect (refused/timeout/unreachable শ্রেণিবিভাগ) → `ssl` handshake (verify সহ) → HTTP status line পর্যন্ত (TTFB)। প্রতিটি ধাপের সময় আলাদা — `curl -w`-এর মতো — এবং ব্যর্থতার স্তর অনুযায়ী পরের command।

## 9. Practical demonstration

### 9.1 netcheck — আসল endpoint

File: [`code/L02-16/netcheck.py`](code/L02-16/netcheck.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-16
python3 netcheck.py https://example.com/
python3 netcheck.py https://expired.badssl.com/
python3 netcheck.py https://does-not-exist.invalid/
python3 netcheck.py http://127.0.0.1:9/
```

**আসল output (২০২৬-১০-২৭, Windows, লেখকের home network; সময় ও IP আপনার ক্ষেত্রে ভিন্ন হবে):**

```text
PASS  dns       70.6 ms  example.com → 104.20.23.154, 172.66.147.243
PASS  tcp        6.9 ms  connected to 104.20.23.154:443
PASS  tls       22.3 ms  TLSv1.3, certificate valid 60 more days
PASS  http      47.2 ms  HTTP/1.1 200 OK  (time to first byte)
```

```text
PASS  dns       65.8 ms  expired.badssl.com → 104.154.89.105
PASS  tcp      275.3 ms  connected to 104.154.89.105:443
FAIL  tls      277.4 ms  certificate has expired
next: openssl s_client -connect HOST:PORT -servername HOST; check chain, name, expiry (L02-08)
```

```text
FAIL  dns        5.1 ms  does-not-exist.invalid: getaddrinfo failed
next: dig NAME; resolvectl status; getent hosts NAME; cat /etc/hosts  (L02-06)
```

```text
PASS  dns        1.6 ms  127.0.0.1 → 127.0.0.1
FAIL  tcp     2033.7 ms  127.0.0.1:9 refused ([WinError 10061] No connection could be made because the target machine actively refused it)
next: nothing listening or a firewall REJECT: on the server `ss -ltnp | grep PORT`; check bind address (L02-05, L02-10)
```

**পর্যবেক্ষণ:**

- `example.com`: TCP মাত্র ৭ ms (কাছের CDN edge), DNS ৭০ ms (প্রথমবার, cache-এ ছিল না) — **latency-র বড় অংশ DNS-এ**। সাথে সাথে আবার চালালে DNS ৬ ms হয়েছিল (`http://` পরীক্ষায় দেখা) — cache (L02-06)।
- `expired.badssl.com`: TCP ২৭৫ ms — server দূরে (CDN নয়)। স্তরগুলো আলাদা সময় দেখায় বলেই "ধীর" কোথায় তা বোঝা যায়।
- `.invalid` (RFC 6761 অনুযায়ী কখনো resolve হয় না) — DNS-এই থেমেছে; পরের স্তর পরীক্ষাই হয়নি।
- বন্ধ local port: **refused**, কিন্তু Windows-এ ২ সেকেন্ড পরে (L02-12-এ একই ঘটনা দেখা গেছে)। Linux-এ সাধারণত সাথে সাথে।

### 9.2 traceroute — আসল পথ (Windows `tracert`)

```text
> tracert -d -h 8 -w 800 1.1.1.1
Tracing route to 1.1.1.1 over a maximum of 8 hops

  1     4 ms     3 ms     3 ms  192.168.0.1
  2     5 ms     6 ms    65 ms  10.224.0.1
  3    16 ms     4 ms     5 ms  172.31.28.253
  4     5 ms     6 ms    70 ms  172.21.147.5
  5    10 ms     5 ms     5 ms  172.31.110.85
  6    24 ms     7 ms    71 ms  103.21.43.10
  7     4 ms     *        *     1.1.1.1
  8     *        *        *     Request timed out.

Trace complete.
```

(২০২৬-১০-২৭-এ আসলে চালানো; লেখকের home network।)

**Section 8.1-এর নিয়মে পড়ুন:**

- Hop ১ = home router (L02-09-এ path MTU ১৪৮০ ফেরত দিয়েছিল এই router-ই)।
- Hop ২–৫ private address (`10.x`, `172.16–31.x`, L02-03) — ISP-এর ভেতরের network; ISP-স্তরের NAT/CGNAT থাকতে পারে।
- Hop ২, ৪, ৬-এ একটি করে ৬৫–৭১ ms মান, কিন্তু **পরের hop ও গন্তব্যে ৪–৫ ms** → এগুলো router-এর ICMP উত্তরে দেরি, আসল latency নয়। ভুল পড়লে "ISP ধীর" সিদ্ধান্ত হতো।
- Hop ৭-এ গন্তব্য একবার ৪ ms-এ উত্তর দিয়েছে, পরের দুটি probe-এ উত্তর নেই — গন্তব্যের ICMP rate limiting। Hop ৮ অর্থহীন (গন্তব্যে পৌঁছানোর পরে)।
- মোট: ৭টি hop, ~৫ ms — Cloudflare-এর কাছের node।

### 9.3 Ubuntu-তে একই কাজ

```bash
sudo apt install dnsutils traceroute mtr-tiny netcat-openbsd
traceroute -n 1.1.1.1
sudo traceroute -n -T -p 443 example.com     # TCP SYN দিয়ে — firewall-বান্ধব
mtr -rwbzc 50 1.1.1.1                         # report mode, ৫০টি probe
python3 netcheck.py https://example.com/ --json | python3 -m json.tool
```

> **Fedora-তে:** `sudo dnf install bind-utils traceroute mtr nmap-ncat` — `dig` আসে `bind-utils`-এ, `nc` আসে `nmap-ncat`-এ (option সামান্য ভিন্ন)।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_netcheck.py`](code/L02-16/test_netcheck.py)-এর ৭টি test: loopback-এ সব স্তর PASS, HTTP 503 → http স্তরে FAIL, refused → `ss -ltnp` পরামর্শ, plain HTTP port-এ HTTPS → TLS স্তরে FAIL, `.invalid` → শুধু DNS FAIL, error শ্রেণিবিভাগ (refused/timeout/unreachable), JSON output ও ভুল URL।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `getaddrinfo` (dig নয়) | Application-এর মতো resolve | `/etc/hosts`-সহ — L02-06-এর `dig` বনাম `getent` পার্থক্য |
| সব address চেষ্টা | IPv4/IPv6, একাধিক A record | curl/browser-ও তাই করে |
| `classify` errno + Windows code | Refused/timeout/unreachable | Cross-platform: Linux ১১১, Windows ১০০৬১ |
| প্রথম ব্যর্থতায় `return` | পরের স্তর পরীক্ষা নয় | নিচের স্তর ভাঙা থাকলে উপরের ফল অর্থহীন |
| `HINTS` | পরের command + lesson | Runbook-এর প্রথম ধাপ |
| HTTP: শুধু status line | TTFB মাপা | পুরো body দরকার নেই |
| `--json` | Machine-readable | Monitoring/CI (Module 20-এর synthetic check) |

**Python কেন এখানে, কোথায় নয়:** বারবার একই checklist automation, JSON output, CI ও monitoring-এ Python ভালো। Interactive diagnosis-এ `curl`, `dig`, `ss`, `mtr` দ্রুত ও সর্বত্র উপলব্ধ — এই tool সেগুলোর বিকল্প নয়, প্রথম screening।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `netcheck.py https://example.com/` | ৪টি PASS, exit ০ |
| `netcheck.py https://expired.badssl.com/` | TLS FAIL, exit ১ |
| `traceroute -T -p 443` | গন্তব্যে পৌঁছায় (ICMP block থাকলেও) |
| `mtr -r` | শেষ hop-এর loss ০% (বা স্থায়ী loss কোথা থেকে শুরু তা স্পষ্ট) |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | কেন ভুল | সঠিক পদ্ধতি |
|---|---|---|
| `ping` ব্যর্থ → "server বন্ধ" | ICMP প্রায়ই block | TCP দিয়ে পরীক্ষা (`nc -zv`, `netcheck`) |
| traceroute-এর মাঝের spike → "ISP ধীর" | ICMP deprioritization | শেষ hop পর্যন্ত টিকে থাকে কিনা দেখুন |
| `dig` ঠিক → "DNS ঠিক" | Application `/etc/hosts`/nsswitch দেখে | `getent hosts` |
| একবার কাজ করল → "ঠিক হয়ে গেছে" | Intermittent সমস্যা | Loop-এ পরিমাপ, মোট সাফল্যের হার |
| প্রথমেই firewall বন্ধ/restart | প্রমাণ নষ্ট, নতুন ঝুঁকি | আগে পর্যবেক্ষণ, নথি, তারপর পরিবর্তন |
| শুধু client-এর দিক থেকে পরীক্ষা | Return path অদৃশ্য | Server-এর দিকেও capture/log |
| `curl -k` দিয়ে "TLS ঠিক" | Verify বন্ধ | `openssl s_client`, সঠিক CA |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Diagnosis-এর সময় সাময়িকভাবে খোলা firewall rule/SG অবশ্যই বন্ধ করুন (ticket-এ নথিভুক্ত); `curl -v`-এর output-এ Authorization header/cookie থাকে — ticket-এ লাগানোর আগে মুছুন; অন্যের network-এ port scan বা traceroute flood নয় — শুধু নিজের/অনুমতিপ্রাপ্ত system; tool-এ secret (token) argument-এ নয় (shell history, L01-06)।
- **Performance:** `mtr`-এর দীর্ঘ চালনা ও ঘন ঘন synthetic check সামান্য load তৈরি করে — interval যুক্তিসঙ্গত রাখুন।
- **Cost:** Cloud-এ flow logs, traffic mirroring ও synthetic monitoring service বিলযুক্ত; কিন্তু দ্রুত diagnosis-এর সাশ্রয় (MTTR কম) সাধারণত অনেক বড়।

## 14. Hands-on exercise

1. নিজের network থেকে Section 9.1 ও 9.2 চালান; আপনার path-এর hop সংখ্যা, ISP-এর private hop ও কোনো ICMP deprioritization আছে কিনা লিখুন।
2. `netcheck.py`-তে `--resolve HOST:IP` option যোগ করুন (curl-এর মতো) এবং একটি test লিখুন।
3. `netcheck.py`-তে `--repeat N` যোগ করুন: N বার চালিয়ে প্রতিটি স্তরের p50/p95 সময় ও সাফল্যের হার — intermittent সমস্যার জন্য।
4. Ubuntu VM-এ ইচ্ছাকৃতভাবে চারটি সমস্যা তৈরি করুন (প্রতিবার একটি, পরে ফিরিয়ে দিন): `/etc/hosts`-এ ভুল IP, service বন্ধ, `ufw deny` port, নিজের lab CA-র certificate (L02-08)। প্রতিটির `netcheck` output ও কোন native command নিশ্চিত করল তা লিখুন।
5. `mtr -rwbzc 100`-এর output নিয়ে তিন বাক্যে ব্যাখ্যা লিখুন — একজন non-network engineer যেন বোঝেন।

## 15. Mini-project — Network troubleshooting runbook

`runbooks/`-এ একটি runbook: "Service unreachable"। Section 6-এর সিদ্ধান্ত-বৃক্ষ, প্রতিটি শাখার command (Ubuntu ও Fedora), প্রত্যাশিত ভালো/খারাপ output, escalation (কোন team, কোন প্রমাণ), এবং `netcheck.py --json`-কে একটি systemd timer-এ (L01-11) চালিয়ে ফল log-এ লেখার setup। Module 2-এর Milestone 2 (request flow) ও Module 17-এর incident response-এ এটি ব্যবহার হবে।

## 16. Interview প্রশ্ন

1. "Website খুলছে না" — কীভাবে ধাপে ধাপে debug করবেন?
2. Connection refused ও connection timed out-এর পার্থক্য কী? প্রতিটিতে কী সন্দেহ করবেন?
3. traceroute কীভাবে কাজ করে? মাঝের hop-এর উচ্চ latency কি সবসময় সমস্যা?
4. `curl` দিয়ে latency কোন ধাপে তা কীভাবে মাপবেন?
5. DNS পরিবর্তনের আগে নতুন server কীভাবে পরীক্ষা করবেন?
6. Intermittent network সমস্যা কীভাবে তদন্ত করবেন?

## 17. Self-assessment প্রশ্ন

1. ডাক্তার analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ LB health check সফল হলেও client timeout কেন?
3. Section 9.2-এর hop ২, ৪, ৬-এর ~৭০ ms কেন সমস্যা নয়?
4. `example.com` check-এ সবচেয়ে বেশি সময় কোন স্তরে গেল এবং কেন?
5. `netcheck.py` কেন প্রথম ব্যর্থতায় থামে?

## 18. সংক্ষিপ্ত সারাংশ

- স্তর ধরে প্রমাণ: DNS → route → TCP → TLS → HTTP → packet; প্রথম ব্যর্থ স্তরে মনোযোগ।
- Error message থেকে স্তর: resolve / refused / timeout / unreachable / certificate / 502-504।
- Refused = পৌঁছেছে, "না"; timeout = কিছুই ফেরেনি — দুই দিকের পথ ভাবুন।
- traceroute/mtr: শুধু শেষ পর্যন্ত টিকে থাকা latency/loss আসল।
- `curl -w`, `curl --resolve`, `ss -ltnp`, `ip route get`, `getent hosts` — সবচেয়ে কাজের কয়েকটি।
- আগে পর্যবেক্ষণ ও নথি, তারপর পরিবর্তন।

## 19. Completion checklist

- [ ] `netcheck.py` চারটি ভিন্ন ফলের জন্য চালিয়েছি
- [ ] নিজের path-এর traceroute/mtr পড়ে ব্যাখ্যা করেছি
- [ ] Ubuntu VM-এ চারটি ইচ্ছাকৃত সমস্যা স্তর ধরে খুঁজেছি (Exercise ৪)
- [ ] Section 6-এর সিদ্ধান্ত-বৃক্ষ মুখস্থ নয়, ব্যাখ্যা করতে পারি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `ip(8)`: https://man7.org/linux/man-pages/man8/ip.8.html
- `ss(8)`: https://man7.org/linux/man-pages/man8/ss.8.html
- `traceroute(8)`: https://man7.org/linux/man-pages/man8/traceroute.8.html
- mtr: https://www.bitwizard.nl/mtr/
- curl — `--write-out` variables: https://everything.curl.dev/usingcurl/verbose/writeout.html
- RFC 6761 — Special-use domain names (`.invalid`): https://www.rfc-editor.org/rfc/rfc6761
- RFC 1393 / traceroute background — Traceroute using an IP option: https://www.rfc-editor.org/rfc/rfc1393

---

**পরের lesson:** L02-17 — Browser থেকে database পর্যন্ত: একটি request-এর পূর্ণ যাত্রা
