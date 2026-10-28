# L02-05 — TCP, UDP, port, socket ও connection state

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L02-04 — Routing ও NAT](L02-04-routing-nat.md); [L01-14 — fd leak](../01-linux-systems/L01-14-logs-and-debugging.md) |
| **Label** | — (সব কিছু loopback-এ) |
| **Tested** | ৭টি test পাস — **আসল loopback TCP/UDP socket** দিয়ে echo, connection refused ও latency (Python 3.14, Windows; ResourceWarning-কে error ধরে)। Latency সংখ্যা Windows-এ আসলে মাপা — খুব noisy (Section 9.3)। নমুনা `ss -tan` script দিয়ে তৈরি। `ss`, `tcpdump`, `nc` **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- **Port** ও **socket** — একটি host-এ বহু program কীভাবে network share করে।
- **TCP**: connection, **3-way handshake**, sequence/ACK, retransmission, flow control, **4-way close**।
- **UDP**: connection ছাড়া datagram — কখন ভালো।
- **TCP state**: LISTEN, ESTABLISHED, TIME_WAIT, CLOSE_WAIT ... — কোনটি স্বাভাবিক, কোনটি bug-এর সংকেত।
- "Connection refused" বনাম "connection timed out" — কী আলাদা বোঝায়।
- Python দিয়ে আসল TCP/UDP server-client, refused ও handshake latency; `ss` output বিশ্লেষণ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

IP (L02-03, L02-04) packet-কে host পর্যন্ত পৌঁছায় — কিন্তু:

- Host-এ চলছে SSH, Nginx, PostgreSQL — packet কোন **program**-এর? → **port**।
- IP packet হারাতে পারে, ক্রম বদলাতে পারে, দুবার আসতে পারে — web page বা database query-র জন্য এটি অগ্রহণযোগ্য। → **TCP** নির্ভরযোগ্যতা যোগ করে।
- কিছু কাজে (DNS query, voice, game) নির্ভরযোগ্যতার চেয়ে গতি জরুরি → **UDP**।

DevOps-এ TCP state পড়তে পারা incident-এ সরাসরি কাজে লাগে: CLOSE_WAIT জমা = application bug; TIME_WAIT জমা = অতিরিক্ত ছোট connection; SYN_SENT আটকে = firewall/route; "refused" = service চলছে না; "timeout" = পথে কিছু drop করছে।

## 3. সহজ ভাষায় পরিচয়

**Port:** ০–৬৫৫৩৫ সংখ্যা যা host-এর ভেতরে program চিহ্নিত করে।

| পরিসর | নাম | উদাহরণ |
|---|---|---|
| ০–১০২৩ | Well-known (খুলতে root/`CAP_NET_BIND_SERVICE` লাগে, L01-16) | ২২ SSH, ৫৩ DNS, ৮০ HTTP, ৪৪৩ HTTPS |
| ১০২৪–৪৯১৫১ | Registered | ৩৩০৬ MySQL, ৫৪৩২ PostgreSQL, ৬৩৭৯ Redis |
| ৪৯১৫২–৬৫৫৩৫ (Linux default ৩২৭৬৮–৬০৯৯৯) | Ephemeral — client-এর জন্য OS-এর অস্থায়ী port | |

**Socket:** একটি connection-এর endpoint — kernel-এর একটি object, program-এর কাছে একটি file descriptor (L01-01)। একটি TCP connection চিহ্নিত হয় **৫টি মান** দিয়ে (**5-tuple**): protocol, source IP, source port, destination IP, destination port। তাই একটি server port (৪৪৩)-এ হাজার হাজার connection একসাথে থাকতে পারে — প্রতিটির client IP/port আলাদা।

**TCP বনাম UDP:**

| | TCP | UDP |
|---|---|---|
| Connection | আছে (handshake) | নেই |
| নির্ভরযোগ্যতা | হারানো data আবার পাঠায়, ক্রম ঠিক রাখে | কোনো নিশ্চয়তা নেই |
| Flow/congestion control | আছে | নেই (app নিজে) |
| Overhead | বেশি (২০+ byte header, handshake) | কম (৮ byte header) |
| ব্যবহার | HTTP/1–2, SSH, database | DNS, video/voice, game, QUIC/HTTP3 (L02-07) |
| Message সীমা | নেই — **byte stream** | আছে — প্রতিটি datagram আলাদা |

**3-way handshake:** client `SYN` → server `SYN-ACK` → client `ACK` → ESTABLISHED। এক round trip (RTT) খরচ — দূরের server-এ এটিই latency-র বড় অংশ।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### TCP = ফোন কল, UDP = পোস্টকার্ড

- **TCP:** ফোন করেন ("হ্যালো?" — SYN), অপর প্রান্ত "হ্যালো, শুনছি" (SYN-ACK), আপনি "ঠিক আছে" (ACK) — তারপর কথা। কিছু না শুনলে "আবার বলুন" (retransmission)। শেষে দুজনেই "রাখছি" বলেন (FIN)।
- **UDP:** পোস্টকার্ড পাঠান — পৌঁছালো কিনা জানেন না; দশটি পাঠালে ভিন্ন ক্রমে পৌঁছাতে পারে।
- **Port** = অফিসের extension নম্বর; **IP** = অফিসের মূল নম্বর।

### Analogy কোথায় মেলে না

- ফোনে কথা বাক্যে বাক্যে আসে। TCP **byte stream** — আপনি দুবার `send("hello")` করলে অপর প্রান্ত একবারে `"hellohello"` পেতে পারে, বা `"hel"` + `"lohello"`। Message-এর সীমা application-কে নিজে ঠিক করতে হয় (length prefix, newline, HTTP header)। এটি নতুনদের সবচেয়ে প্রচলিত socket bug — এই lesson-এর test-এ ৯০০০ byte পাঠিয়ে একাধিক `recv` চক্র যাচাই করা হয়েছে।
- কল কেটে গেলে দুজনেই জানেন। TCP-তে এক পক্ষ নীরবে হারিয়ে গেলে (power off, NAT timeout) অন্য পক্ষ **অনেকক্ষণ জানতে না-ও পারে** — তাই keepalive ও application timeout।
- পোস্টকার্ড হারালে কেউ জানে না। UDP-র উপর তৈরি protocol (DNS, QUIC) নিজেরা timeout ও retry যোগ করে।

## 5. Real-world engineering scenario — "Refused" বনাম "timed out" বনাম "CLOSE_WAIT"

**পরিস্থিতি ১ — "Connection refused":** `curl http://10.20.0.9:8000` → তাৎক্ষণিক "Connection refused"। মানে host-এ **পৌঁছানো গেছে**, kernel **RST** ফেরত দিয়েছে কারণ port-এ কেউ **listen করছে না** — service বন্ধ, ভুল port, বা শুধু `127.0.0.1`-এ bind করা (বাইরে থেকে দেখা যায় না)। Firewall-ও কখনো ইচ্ছাকৃত reject করে RST দেয়।

**পরিস্থিতি ২ — "Connection timed out":** কয়েক সেকেন্ড অপেক্ষা, তারপর timeout। SYN গেছে, কোনো উত্তর আসেনি — পথে কিছু **নীরবে drop** করছে: firewall/security group (L02-10), route নেই (L02-04), host বন্ধ। `ss`-এ client-এর দিকে `SYN-SENT` দেখা যায়।

**পরিস্থিতি ৩ — CLOSE_WAIT জমছে:** API server-এর `ss -tan`-এ শত শত `CLOSE-WAIT` — নমুনায় ৬২টি, সব `127.0.0.1:8000`-এর দিকে:

```text
WARN 62 CLOSE-WAIT — application socket বন্ধ করছে না (leak); peers [('127.0.0.1', 62)]
```

CLOSE_WAIT মানে: **অন্য পক্ষ** বন্ধ করেছে (FIN পাঠিয়েছে), কিন্তু **আমাদের application** তার socket-এ `close()` করেনি। এটি সবসময় **application bug** — kernel বা network নয়। L01-14-এর "Too many open files"-এর একটি প্রধান কারণ। সমাধান code-এ (`with` block, response পড়ে connection বন্ধ বা pool-এ ফেরত)।

**শিক্ষা:** Error message ও state-এর সঠিক অর্থ জানলে "network সমস্যা" বলে অস্পষ্ট অভিযোগ থেকে সঠিক team ও সঠিক fix-এ দ্রুত পৌঁছানো যায়।

## 6. Diagram

### TCP connection-এর জীবনচক্র

```text
 client                                         server
 CLOSED                                         LISTEN   (bind + listen)
   │ ── SYN (seq=x) ─────────────────────────►  │
 SYN-SENT                                       SYN-RECV
   │ ◄── SYN-ACK (seq=y, ack=x+1) ────────────  │
   │ ── ACK (ack=y+1) ───────────────────────►  │          ← 3-way handshake (১ RTT)
 ESTABLISHED                                    ESTABLISHED  (accept() ফেরত দেয়)
   │ ═══ data ⇄ data (seq/ack, retransmit) ═══  │
   │ ── FIN ─────────────────────────────────►  │   client আগে বন্ধ করল (close())
 FIN-WAIT-1                                     CLOSE-WAIT   ← server app এখনো close() করেনি
   │ ◄── ACK ─────────────────────────────────  │
 FIN-WAIT-2                                     │   (app close() করলে)
   │ ◄── FIN ─────────────────────────────────  LAST-ACK
   │ ── ACK ─────────────────────────────────►  │
 TIME-WAIT (2×MSL অপেক্ষা, Linux-এ ~৬০ সেকেন্ড)   CLOSED
   │
 CLOSED
```

**যে পক্ষ আগে বন্ধ করে, সে TIME-WAIT-এ যায়।** যে পক্ষ বন্ধের উত্তরে close() করে না, সে CLOSE-WAIT-এ আটকে থাকে।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Port | Host-এর ভেতরে program চিহ্নিত করার সংখ্যা |
| Socket | Connection-এর endpoint (kernel object, program-এ fd) |
| 5-tuple | protocol + src IP + src port + dst IP + dst port |
| Ephemeral port | Client-এর জন্য OS-এর অস্থায়ী port |
| `bind` / `listen` / `accept` / `connect` | Server port নেয় / অপেক্ষা / নতুন connection নেয় / client সংযোগ করে |
| Backlog | `accept`-এর অপেক্ষায় থাকা connection-এর সারি |
| 3-way handshake | SYN, SYN-ACK, ACK |
| RTT | Round-trip time — একবার যাওয়া-আসার সময় |
| Sequence / ACK number | Byte-এর ক্রম ও প্রাপ্তি নিশ্চিতকরণ |
| Retransmission | হারানো segment আবার পাঠানো |
| Flow control (window) | গ্রাহক কতটা নিতে পারবে |
| Congestion control | Network-এর ভিড় অনুযায়ী পাঠানোর হার |
| RST | Connection জোর করে বাতিল ("refused"-এর উৎস) |
| TIME_WAIT / CLOSE_WAIT | আগে বন্ধকারীর অপেক্ষা / app close() করেনি |
| Keepalive | নিষ্ক্রিয় connection জীবিত কিনা যাচাই |
| Datagram | UDP-র একক message |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Socket API (L01-01-এর system call)

```text
 server:  socket() → bind(0.0.0.0:8000) → listen(backlog) → accept() ─► নতুন fd প্রতি connection
 client:  socket() → connect(10.20.0.9:8000)   [kernel ephemeral port দেয় ও handshake করে]
 উভয়ে:  send()/recv()  → close()
 UDP:     socket(SOCK_DGRAM) → sendto()/recvfrom()   [connect নেই]
```

`bind("127.0.0.1", ...)` = শুধু local থেকে; `bind("0.0.0.0", ...)` = সব interface থেকে। "নিজের machine-এ চলে, অন্য machine থেকে refused" — প্রায়ই bind ঠিকানার ভুল।

### 8.2 নির্ভরযোগ্যতার কৌশল

- প্রতিটি byte-এর sequence number; গ্রাহক ACK পাঠায় "এখন পর্যন্ত এই byte পেয়েছি"।
- ACK না এলে timeout-এর পরে retransmission (প্রতিবার timeout দ্বিগুণ — exponential backoff)।
- Window: গ্রাহক জানায় buffer-এ কত জায়গা।
- Congestion control (Linux default CUBIC; BBR বিকল্প): packet হারালে পাঠানোর হার কমায়।

ফলাফল: packet loss-এ TCP **ধীর হয়** কিন্তু data হারায় না — তাই "network slow" প্রায়ই loss/retransmission-এর লক্ষণ (`ss -ti`-তে `retrans`)।

### 8.3 TIME_WAIT কেন আছে এবং কখন সমস্যা

TIME_WAIT নিশ্চিত করে যে (১) শেষ ACK হারালে আবার পাঠানো যায়, (২) পুরোনো connection-এর দেরিতে আসা packet একই 5-tuple-এর নতুন connection-এ মিশে না যায়। স্বাভাবিক ও দরকারি। সমস্যা হয় যখন একটি client একই গন্তব্যে প্রতি সেকেন্ডে হাজার হাজার ছোট connection খোলে-বন্ধ করে — ephemeral port শেষ (L02-04-এর NAT exhaustion-এর আত্মীয়)। সমাধান: **connection reuse** (HTTP keep-alive, pool), kernel tuning নয়।

## 9. Practical demonstration

### 9.1 TCP ও UDP — Python (loopback)

File: [`code/L02-05/sock_demo.py`](code/L02-05/sock_demo.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-05
python3 sock_demo.py tcp
python3 sock_demo.py udp
python3 sock_demo.py refused
```

**এই repository-তে চালিয়ে পাওয়া আসল output (Windows):**

```text
TCP server listening on 127.0.0.1:63257
reply: b'HELLO OVER TCP'
reply: b'HELLO OVER UDP'
ConnectionRefusedError errno=10061 — port বন্ধ, kernel RST পাঠিয়েছে
```

Port নম্বর প্রতিবার আলাদা (OS দেয়)। **errno ১০০৬১** Windows-এর `WSAECONNREFUSED`; **Linux-এ একই ঘটনায় errno ১১১** (`ECONNREFUSED`) — test দুটোই গ্রহণ করে। আবারও platform পার্থক্য: ধারণা একই, সংখ্যা আলাদা।

**Code-এর গুরুত্বপূর্ণ লাইন:**

| Line | কী করে |
|---|---|
| `srv.bind(("127.0.0.1", 0))` | শুধু loopback, OS খালি port দেয় |
| `srv.listen(16)` | Backlog ১৬ |
| `conn, _ = srv.accept()` | Handshake শেষ connection-এর জন্য **নতুন** socket |
| `while data := conn.recv(4096)` | Byte stream — একাধিকবার পড়া, `b""` = অন্য পক্ষ বন্ধ করেছে |
| `c.shutdown(socket.SHUT_WR)` | "আর পাঠাবো না" — FIN পাঠায়, কিন্তু পড়া চলে |
| UDP-তে `settimeout(3)` | উত্তরের নিশ্চয়তা নেই — timeout ছাড়া চিরকাল অপেক্ষা |

### 9.2 অন্য terminal-এ দেখা (Ubuntu)

```bash
python3 -c 'import socket,time; s=socket.socket(); s.bind(("127.0.0.1",9999)); s.listen(); c,_=s.accept(); time.sleep(60)' &
nc -v 127.0.0.1 9999 &                    # connect করে চুপ
ss -tanp | grep 9999                      # LISTEN ও দুই প্রান্তের ESTAB, process নাম সহ
kill %2                                   # client বন্ধ → server-এর দিকে CLOSE-WAIT (server close() করছে না!)
ss -tan | grep 9999
kill %1
```

| `ss` option | অর্থ |
|---|---|
| `-t` / `-u` | TCP / UDP |
| `-a` | Listening সহ সব |
| `-n` | নাম নয়, সংখ্যা (দ্রুত, DNS নেই) |
| `-p` | Process (অন্য user-এর জন্য sudo) |
| `-l` | শুধু listening |
| `-i` | TCP internal তথ্য (rtt, retrans, cwnd) |

**Handshake নিজের চোখে:**

```bash
sudo tcpdump -i lo -nn -c 6 port 9999 &
python3 -c 'import socket; socket.create_connection(("127.0.0.1",9999)).close()'
```

উদাহরণ: `Flags [S]` (SYN), `Flags [S.]` (SYN-ACK), `Flags [.]` (ACK), তারপর `[F.]` (FIN)। (এর আগে একটি listener চালু রাখুন।)

> **Fedora-তে:** একই command; `nc` আসে `nmap-ncat` package থেকে (Ubuntu-তে `netcat-openbsd`) — option সামান্য আলাদা হতে পারে।

### 9.3 Handshake latency — noise-এর আরেকটি পাঠ

```bash
python3 sock_demo.py latency --n 300
```

**এই repository-তে Windows-এ তিনবার চালানোর আসল ফল:**

| Run | min | p50 | p99 | mean |
|---|---|---|---|---|
| ১ | 156 µs | 11846 µs | 26965 µs | 9818 µs |
| ২ | 135 µs | 9675 µs | 26429 µs | 8671 µs |
| ৩ | 152 µs | 838 µs | 25728 µs | 7876 µs |

**ব্যাখ্যা:** min (~১৫০ µs) স্থির — loopback-এ handshake-এর আসল খরচ এর কাছাকাছি। কিন্তু p50 এক run-এ ৮৩৮ µs, অন্য run-এ ১১.৮ ms — দশ গুণের বেশি পার্থক্য! কারণ সম্ভবত measurement পরিবেশ: একই Python process-এ server thread ও client loop (GIL-এর জন্য পালা), Windows-এর scheduler/timer (L00-06-এর মতো)। **একটি run-এর p50 দেখে "loopback-এ ১২ ms লাগে" সিদ্ধান্ত নেওয়া ভুল হতো।** Ubuntu-তে নিজে তিনবার চালিয়ে তুলনা করুন — এটি Exercise ১।

### 9.4 `ss` সারাংশ — Python

File: [`code/L02-05/ss_summary.py`](code/L02-05/ss_summary.py)

```bash
ss -tan > /tmp/ss.txt && python3 ss_summary.py /tmp/ss.txt
python3 ss_summary.py sample-ss.txt; echo "exit=$?"
```

**নমুনা দিয়ে আসল output:**

```text
     120  TIME-WAIT   আমরা আগে বন্ধ করেছি; পুরোনো packet মোকাবেলায় কিছুক্ষণ অপেক্ষা
      62  CLOSE-WAIT  অন্য পক্ষ বন্ধ করেছে, আমাদের app এখনো close() করেনি
      40  ESTAB       চলমান connection
       4  LISTEN      server অপেক্ষায়
       2  SYN-SENT    আমরা connect চেষ্টা করছি, উত্তর আসেনি (firewall/route?)
listening ports: 22, 80, 8000
WARN 62 CLOSE-WAIT — application socket বন্ধ করছে না (leak); peers [('127.0.0.1', 62)]
WARN 2 SYN-SENT — এই গন্তব্য উত্তর দিচ্ছে না: [('10.20.0.9:5432', 2)]
exit=1
```

দুটি আলাদা সমস্যা: (১) Nginx → local app (`:8000`) connection-এ CLOSE-WAIT — app-এর bug; (২) database `10.20.0.9:5432`-এ SYN উত্তরহীন — firewall/security group বা DB host। ১২০টি TIME-WAIT সীমার নিচে — স্বাভাবিক।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l02_05.py`](code/L02-05/test_l02_05.py)-এর ৭টি test: TCP echo (৯০০০ byte — একাধিক recv চক্র), UDP echo, refused (Linux ও Windows errno), latency নমুনা, `ss` সারাংশ, address split (IPv6 সহ), ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `socket.create_connection(..., timeout=3)` | Client connect, timeout সহ | Timeout ছাড়া ব্যর্থ connect অনেকক্ষণ আটকে থাকে |
| `SO_REUSEADDR` | TIME_WAIT-এ থাকা port-এ আবার bind | Server restart-এ "Address already in use" এড়ায় |
| `with conn:` | শেষে স্বয়ংক্রিয় close | CLOSE_WAIT leak এড়ানোর সঠিক অভ্যাস |
| `split_addr` → `rpartition(":")` | IPv6-এ একাধিক `:` | শেষ `:`-এর পরে port |
| Listening port dedupe | `0.0.0.0:22` ও `[::]:22` একবার | একই service দুই stack-এ |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `sock_demo.py tcp/udp` | বড় হাতের echo |
| `refused` (Linux) | errno ১১১ |
| `ss` experiment-এ client kill | Server-এর দিকে CLOSE-WAIT |
| tcpdump | `[S]`, `[S.]`, `[.]` |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Connection refused | Port-এ কেউ listen করছে না / শুধু 127.0.0.1-এ bind | `ss -ltnp` | Service চালু, bind `0.0.0.0` (প্রয়োজন হলে) |
| Connection timed out | পথে drop (firewall, route, host off) | Client-এ `SYN-SENT`; `mtr` | Firewall/SG/route (L02-10, L02-04) |
| `Address already in use` | অন্য process port-এ / TIME_WAIT | `ss -ltnp 'sport = :8000'` | পুরোনো process বন্ধ; `SO_REUSEADDR` |
| CLOSE-WAIT বাড়ছে | App close() করে না | `ss -tanp state close-wait` | Code fix |
| হাজার হাজার TIME-WAIT, নতুন connection ব্যর্থ | Ephemeral port শেষ | `ss -s`; `sysctl net.ipv4.ip_local_port_range` | Keep-alive/pool |
| Message ভেঙে/জুড়ে আসে | TCP byte stream | — | Framing (length prefix, delimiter) |
| UDP reply কখনো আসে না, program আটকে | Timeout নেই | — | `settimeout` ও retry |

## 13. Security, performance ও cost বিবেচনা

- **Security:** খোলা port = attack surface — অপ্রয়োজনীয় service বন্ধ, internal service `127.0.0.1` বা private interface-এ bind। SYN flood (অনেক অসম্পূর্ণ handshake) — kernel-এর SYN cookie (`net.ipv4.tcp_syncookies`) ও upstream সুরক্ষা। UDP-তে source spoof সহজ — amplification আক্রমণে ব্যবহৃত (খোলা DNS resolver ইত্যাদি)। Port scan শুধু নিজের/অনুমোদিত system-এ।
- **Performance:** প্রতিটি নতুন TCP connection-এ ১ RTT handshake (+ TLS-এ আরো, L02-08) — দূরের server-এ connection reuse বড় লাভ; packet loss TCP throughput অনেক কমায়।
- **Cost:** অপ্রয়োজনীয় connection churn CPU, NAT port ও load balancer-এর connection খরচ বাড়ায় (cloud LB-তে connection-ভিত্তিক বিল থাকতে পারে)।

## 14. Hands-on exercise

1. Ubuntu-তে `sock_demo.py latency --n 300` তিনবার চালিয়ে Section 9.3-এর Windows সংখ্যার সাথে তুলনা করুন। কোন সংখ্যা স্থির, কোনটি noisy?
2. Section 9.2-এর experiment-এ client-এর বদলে server আগে বন্ধ করুন — কোন প্রান্তে TIME-WAIT দেখা যায়?
3. `sock_demo.py`-তে একটি length-prefixed message protocol যোগ করুন (৪-byte length + data) যাতে দুটি message আলাদা থাকে। Test লিখুন।
4. `ss -ti dst 1.1.1.1` (একটি HTTPS connection চলাকালীন) — `rtt`, `retrans`, `cwnd` পড়ুন।
5. `ss_summary.py`-তে "সবচেয়ে বেশি connection-এর remote peer" যোগ করুন।

## 15. Mini-project — connection health check

Project 1-এর জন্য `conn-check` subcommand-এর নকশা: `ss -tan` থেকে state গণনা, CLOSE-WAIT/TIME-WAIT/SYN-SENT সতর্কতা, প্রতিটি listening port-এর process (`ss -ltnp`), এবং "expected port list" (config file)-এর সাথে তুলনা — অপ্রত্যাশিত listening port পেলে সতর্কতা (security drift, L01-02-এর মতো)।

## 16. Interview প্রশ্ন

1. TCP ও UDP-এর পার্থক্য কী? কখন কোনটি?
2. 3-way handshake ব্যাখ্যা করুন।
3. "Connection refused" ও "connection timed out"-এর পার্থক্য কী বোঝায়?
4. TIME_WAIT কী, কেন আছে, কখন সমস্যা?
5. CLOSE_WAIT অনেক থাকলে কী বোঝায়?
6. একটি server port-এ কীভাবে হাজার হাজার connection সম্ভব?
7. TCP-কে কেন "byte stream" বলা হয় এবং এর ফলে application-এ কী সতর্কতা দরকার?

## 17. Self-assessment প্রশ্ন

1. ফোন-পোস্টকার্ড analogy কোথায় মেলে না?
2. Section 5-এর তিনটি পরিস্থিতির অর্থ ও প্রথম পদক্ষেপ।
3. কোন পক্ষ TIME-WAIT-এ যায় এবং কোন পক্ষ CLOSE-WAIT-এ?
4. Latency-র তিন run-এ min স্থির কিন্তু p50 অস্থির কেন?
5. `bind("127.0.0.1")` ও `bind("0.0.0.0")`-এর পার্থক্য।
6. Linux ও Windows-এ refused-এর errno কত?

## 18. সংক্ষিপ্ত সারাংশ

- Port = host-এর ভেতরে program; connection = 5-tuple; socket = kernel object/fd।
- **TCP:** handshake (১ RTT), sequence/ACK, retransmission, flow ও congestion control — byte stream।
- **UDP:** connection নেই, নিশ্চয়তা নেই, কম overhead — timeout app-এর দায়িত্ব।
- **Refused** = পৌঁছেছে, কেউ শুনছে না (RST); **timeout** = পথে drop।
- **CLOSE_WAIT** = app bug; **TIME_WAIT** = স্বাভাবিক, কিন্তু অতিরিক্ত হলে connection reuse।

## 19. Completion checklist

- [ ] `sock_demo.py`-এর চারটি command চালিয়েছি
- [ ] `ss`-এ নিজে CLOSE-WAIT তৈরি করে দেখেছি
- [ ] tcpdump-এ handshake flag দেখেছি
- [ ] Latency তিনবার মেপে noise বিশ্লেষণ করেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 9293 — TCP: https://www.rfc-editor.org/rfc/rfc9293
- RFC 768 — UDP: https://www.rfc-editor.org/rfc/rfc768
- `ss(8)`: https://man7.org/linux/man-pages/man8/ss.8.html
- `socket(7)`, `tcp(7)`, `udp(7)`: https://man7.org/linux/man-pages/man7/tcp.7.html
- Python `socket`: https://docs.python.org/3/library/socket.html
- Kernel docs — TCP sysctl: https://docs.kernel.org/networking/ip-sysctl.html

---

**পরের lesson:** L02-06 — DNS: recursive resolver, authoritative server ও caching
