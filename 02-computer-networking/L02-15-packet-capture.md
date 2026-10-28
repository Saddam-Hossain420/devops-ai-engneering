# L02-15 — tcpdump ও Wireshark দিয়ে packet inspection

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-01 — Encapsulation](L02-01-network-models.md), [L02-05 — TCP](L02-05-tcp-udp-sockets.md), [L02-06 — DNS](L02-06-dns.md), [L02-07 — HTTP](L02-07-http.md) |
| **Label** | — |
| **Tested** | `make_pcap.py` ও `pcap_summary.py`: ৭টি test পাস — synthetic pcap (সঠিক IPv4/TCP/UDP checksum যাচাইসহ), tcpdump-শৈলীর output, handshake RTT, retransmission ও RST সনাক্তকরণ, big-endian pcap, VLAN tag, কাটা file ও pcapng প্রত্যাখ্যান (Python 3.14, Windows)। Output Section 9-এ। **এই machine-এ tcpdump/Wireshark নেই**, তাই কোনো আসল capture নেওয়া হয়নি; `sample.pcap` সম্পূর্ণ synthetic। `tcpdump`/`tshark` command Ubuntu-তে চালানো বাকি। |

---

## 1. এই lesson-এ যা শিখবেন

- Packet capture কখন দরকার এবং কোথায় capture নেবেন।
- `tcpdump`: interface, **capture filter (BPF)**, `-nn`, `-w`/`-r`, ring buffer, snaplen।
- tcpdump output পড়া: flags `[S]`, `[S.]`, `[P.]`, `[F.]`, `[R]`, seq/ack, window, length।
- **Wireshark/tshark**: display filter, "Follow TCP stream", expert info, TCP analysis flag।
- Capture-এ চিনবেন: handshake RTT, retransmission, RST, zero window, DNS সমস্যা।
- Capture নেওয়ার **নিরাপত্তা ও নৈতিকতা**: সংবেদনশীল data, অনুমতি।
- Python দিয়ে pcap format নিজে পড়া — tool-এর ভেতরে কী হয় তা বুঝতে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Log বলে application কী **ভেবেছে**; packet capture বলে network-এ **আসলে কী গেছে**। যখন দুই পক্ষ পরস্পরকে দোষ দেয় ("আমরা request পাঠিয়েছি" — "আমরা কিছু পাইনি"), capture নিরপেক্ষ সাক্ষী।

যেসব প্রশ্নের উত্তর শুধু capture দিতে পারে:

- Latency কোথায় — network RTT, server-এর প্রথম byte, নাকি client নিজে দেরি করছে?
- Packet হারাচ্ছে কি (retransmission)?
- কে connection reset করছে (RST কোন দিক থেকে)?
- TLS handshake কোন ধাপে ভাঙছে? DNS query আদৌ যাচ্ছে কিনা?
- MTU black hole (L02-09) — বড় packet যায় কিন্তু ICMP ফেরে না?

## 3. সহজ ভাষায় পরিচয়

**tcpdump** = command-line packet capture (server-এ, SSH-এর মাধ্যমে)। **Wireshark** = GUI দিয়ে বিশ্লেষণ (সাধারণত laptop-এ); **tshark** = Wireshark-এর command-line রূপ। দুটোই **libpcap**-এর উপর এবং **pcap** file-এ লেখে/পড়ে — তাই পরিচিত কৌশল: **server-এ tcpdump দিয়ে file-এ capture → laptop-এ Wireshark দিয়ে বিশ্লেষণ।**

**tcpdump output-এর এক লাইন:**

```text
07:33:20.010450 IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [S.], seq 5000, ack 1001, win 65160, length 0
└── সময় ──────┘    └─ src.port ┘   └─ dst.port ──┘        │       │          │           │          └ payload byte
                                                        flags  sequence   ack number  receive window
```

| Flag | অর্থ |
|---|---|
| `[S]` | SYN — connection শুরু |
| `[S.]` | SYN-ACK (`.` = ACK) |
| `[.]` | শুধু ACK |
| `[P.]` | PUSH + ACK — data সহ |
| `[F.]` | FIN — শেষ |
| `[R]` / `[R.]` | RST — বাতিল/প্রত্যাখ্যান |

**দুই ধরনের filter (প্রায়ই গুলিয়ে যায়):**

| | Capture filter (BPF) | Display filter (Wireshark) |
|---|---|---|
| কখন | Capture-এর **সময়** — যা মেলে না তা কখনো সংরক্ষিত হয় না | Capture-এর **পরে** — শুধু দেখানো বদলায় |
| Syntax | `host 10.0.0.10 and tcp port 443` | `ip.addr == 10.0.0.10 && tcp.port == 443` |
| কোথায় | `tcpdump`, `dumpcap -f` | Wireshark, `tshark -Y` |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### CCTV footage

- **Log** = কর্মচারীর লেখা রিপোর্ট: "সকাল ১০টায় মাল পাঠিয়েছি"।
- **Packet capture** = দরজার CCTV: আসলে কে কখন কী নিয়ে বের হলো, সেকেন্ডের হিসাবে।
- **Capture filter** = ক্যামেরা শুধু পেছনের দরজায় তাক করা — সামনের দরজার ঘটনা কোনোদিন জানা যাবে না।
- **Display filter** = সব footage রেকর্ড আছে, শুধু লাল গাড়ির অংশ খুঁজে দেখা।
- **কোথায় ক্যামেরা** = কোন interface/host-এ capture — client-এর দিক বনাম server-এর দিক ভিন্ন গল্প বলতে পারে।

### Analogy কোথায় মেলে না

- CCTV-তে সব দেখা যায়। **TLS (L02-08)-এর ভেতরের HTTP capture-এ দেখা যায় না** — শুধু handshake, SNI, আকার ও সময়। Content দেখতে application-স্তরের log, অথবা নিজের lab-এ `SSLKEYLOGFILE` (Section 8.3)।
- CCTV নিরপেক্ষ। Capture **যেখানে নেওয়া হয় সেখানকার** দৃশ্য: client-এর NIC-এ দেখা packet হয়তো পথে হারিয়েছে, server-এ পৌঁছায়নি। দুই প্রান্তে একসাথে capture প্রায়ই উত্তর দেয়।
- CCTV দেখা সাধারণত কারো ক্ষতি করে না। Packet capture-এ **অন্যের password, token, cookie, ব্যক্তিগত data** থাকতে পারে — capture নিজেই একটি সংবেদনশীল file।

## 5. Real-world engineering scenario — "API মাঝে মাঝে ২০০ ms ধীর"

**পরিস্থিতি:** একটি internal API-র p50 latency ১ ms, কিন্তু p99 ২০০ ms-এর বেশি। Application profiling-এ কিছু নেই; server-এর CPU কম।

**Capture (server-এ, শুধু ঐ port, সীমিত আকারে):**

```bash
sudo tcpdump -ni eth0 -s 128 -w /tmp/api.pcap 'tcp port 80' -c 20000
python3 pcap_summary.py /tmp/api.pcap --analyze-only
```

এই lesson-এর synthetic `sample.pcap` ঠিক এই ধরনের একটি ঘটনা অনুকরণ করে:

```text
07:33:20.010600 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [P.], seq 1001, ack 5001, win 64240, length 41
07:33:20.215000 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [P.], seq 1001, ack 5001, win 64240, length 41
- RETRANSMISSION 10.0.0.5:51514 → 10.0.0.10:80 seq 1001 length 41 — packet or its ACK was lost
```

একই seq ও length — প্রথম packet (বা তার ACK) হারিয়েছে; client ~২০০ ms অপেক্ষা করে আবার পাঠিয়েছে (Linux-এ minimum retransmission timeout ২০০ ms)। Handshake RTT ০.৪৫ ms — তাই এটি দূরত্বের সমস্যা নয়, **loss**।

**পরের ধাপ:** কোথায় হারাচ্ছে? `ip -s link` (interface error/drop), `nstat -az | grep -i retrans`, switch/NIC counter, অন্য প্রান্তে একসাথে capture। আসল ঘটনায় কারণ হতে পারে: ত্রুটিপূর্ণ cable/NIC, ভরা queue, overloaded virtual switch, conntrack table full (L02-10)।

**শিক্ষা:** p99-এর "রহস্যময়" ২০০ ms প্রায়ই TCP retransmission timeout। Capture ছাড়া এটা প্রমাণ করা কঠিন।

## 6. Diagram — কোথায় capture নেবেন

```text
 client ──► [client NIC] ── switch/router ── LB ── [server NIC] ──► server process
              ▲ capture A                            ▲ capture B
                                                     ▲ capture C: container-এর veth (L02-13)

 A-তে SYN আছে, B-তে নেই            → পথে (firewall/SG/route) আটকাচ্ছে
 B-তে SYN, SYN-ACK আছে; A-তে SYN-ACK নেই → ফেরার পথে আটকাচ্ছে (L02-14-এর return route)
 B-তে request আছে, উত্তর দেরিতে      → server/application ধীর
 দুই প্রান্তে retransmission           → মাঝে loss
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| libpcap / pcap / pcapng | Capture library / পুরোনো ও সরল file format / নতুন, বহু-interface format |
| Snaplen (`-s`) | প্রতিটি packet-এর কত byte রাখা হবে |
| BPF | Kernel-এ capture filter চালানোর ব্যবস্থা |
| Promiscuous mode | নিজের নয় এমন frame-ও capture |
| Ring buffer (`-C`, `-W`, `-G`) | নির্দিষ্ট আকারের file ঘুরিয়ে লেখা |
| Display filter | Wireshark-এ দেখানোর filter |
| Follow TCP stream | একটি connection-এর পুরো কথোপকথন |
| Retransmission | হারানো segment আবার পাঠানো |
| Duplicate ACK | Receiver একই ACK বারবার — ফাঁক আছে |
| Zero window | Receiver-এর buffer ভরা — "থামো" |
| RTT | Round-trip time; handshake-এ SYN → SYN-ACK |
| `SSLKEYLOGFILE` | TLS session key log — lab-এ decrypt করতে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 pcap file format

```text
Global header (24 byte): magic a1b2c3d4 | version 2.4 | timezone | sigfigs | snaplen | linktype (1 = Ethernet)
প্রতি packet: record header (16 byte: সেকেন্ড, মাইক্রোসেকেন্ড, captured length, original length) + frame byte
```

Magic-এর byte ক্রম থেকে বোঝা যায় file little- নাকি big-endian-এ লেখা; `a1b23c4d` হলে nanosecond timestamp। `pcap_summary.py` এই চারটিই পড়ে। Linux-এ `tcpdump -i any` হলে linktype ১১৩ (Linux "cooked" header — Ethernet header-এর বদলে)। Wireshark-এর default `.pcapng` — এটি ভিন্ন format; tool এটি চিনে স্পষ্ট বার্তা দেয়।

### 8.2 Capture filter-এর গুরুত্ব

ব্যস্ত server-এ filter ছাড়া capture দ্রুত disk ভরায় ও CPU খায়, এবং kernel buffer ভরে packet **হারায়** ("packets dropped by kernel" — tcpdump শেষে দেখায়)। নিয়ম: যত সংকীর্ণ filter সম্ভব, `-s` দিয়ে শুধু header (যেমন ১২৮ byte) যদি payload না লাগে, এবং `-c`/`-G`/`-W` দিয়ে সীমা।

```bash
tcpdump -ni eth0 'host 10.0.0.10 and tcp port 443'
tcpdump -ni any 'udp port 53'                                   # DNS
tcpdump -ni eth0 'tcp[tcpflags] & (tcp-syn|tcp-rst) != 0'        # শুধু SYN ও RST — connection সমস্যা
tcpdump -ni eth0 'icmp[icmptype] == 3'                           # unreachable / frag needed (L02-09)
tcpdump -ni eth0 -w /var/tmp/cap-%H%M.pcap -G 300 -W 12 -s 256 'port 443'   # ৫ মিনিটের ১২টি file, ঘুরিয়ে
```

### 8.3 Encrypted traffic

HTTPS-এ capture-এ দেখা যায়: IP, port, TCP-র আচরণ, TLS ClientHello-র **SNI** (কোন hostname), certificate (TLS 1.2-এ; 1.3-এ encrypted), আকার ও সময়। Content নয়। নিজের lab-এ client-কে `SSLKEYLOGFILE=/tmp/keys.log` দিয়ে চালালে (curl, Firefox, Chrome সমর্থন করে) Wireshark সেই file দিয়ে decrypt করতে পারে — production-এ কখনো নয়, key log file নিজেই secret।

### 8.4 Wireshark-এর বিশ্লেষণ

- Display filter: `tcp.analysis.retransmission`, `tcp.analysis.zero_window`, `tcp.flags.reset == 1`, `dns.flags.rcode != 0`, `http.response.code >= 500`, `tls.handshake.type == 1`।
- Statistics → Conversations (কে কার সাথে কত), I/O Graph (সময় অনুযায়ী), TCP Stream Graph।
- Analyze → Expert Information — সব সতর্কতা এক জায়গায়।
- tcpdump-এর default output-এ seq **relative** (প্রথমটি ০/১ ধরে), `-S` দিলে absolute — এই lesson-এর tool absolute দেখায়, তাই এটি `tcpdump -S`-এর মতো।

## 9. Practical demonstration

### 9.1 Synthetic pcap তৈরি ও পড়া

Files: [`code/L02-15/make_pcap.py`](code/L02-15/make_pcap.py), [`pcap_summary.py`](code/L02-15/pcap_summary.py), [`sample.pcap`](code/L02-15/sample.pcap) (**synthetic** — হাতে বানানো ১৫টি packet; কোনো আসল traffic নয়)।

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-15
python3 make_pcap.py sample.pcap        # repository-তে আগে থেকেই আছে; আবার তৈরি করলে হুবহু একই
python3 pcap_summary.py sample.pcap; echo "exit=$?"
```

**আসল output:**

```text
07:33:20.000000 IP 10.0.0.5.40000 > 10.0.0.2.53: UDP, length 33
07:33:20.000800 IP 10.0.0.2.53 > 10.0.0.5.40000: UDP, length 49
07:33:20.010000 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [S], seq 1000, win 64240, length 0
07:33:20.010450 IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [S.], seq 5000, ack 1001, win 65160, length 0
07:33:20.010500 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [.], seq 1001, ack 5001, win 64240, length 0
07:33:20.010600 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [P.], seq 1001, ack 5001, win 64240, length 41
07:33:20.215000 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [P.], seq 1001, ack 5001, win 64240, length 41
07:33:20.215400 IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [.], seq 5001, ack 1042, win 64240, length 0
07:33:20.216000 IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [P.], seq 5001, ack 1042, win 64240, length 41
07:33:20.216100 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [.], seq 1042, ack 5042, win 64240, length 0
07:33:20.216200 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [F.], seq 1042, ack 5042, win 64240, length 0
07:33:20.216500 IP 10.0.0.10.80 > 10.0.0.5.51514: Flags [F.], seq 5042, ack 1043, win 64240, length 0
07:33:20.216600 IP 10.0.0.5.51514 > 10.0.0.10.80: Flags [.], seq 1043, ack 5043, win 64240, length 0
07:33:20.300000 IP 10.0.0.5.51600 > 10.0.0.10.5432: Flags [S], seq 9000, win 64240, length 0
07:33:20.300300 IP 10.0.0.10.5432 > 10.0.0.5.51600: Flags [R.], seq 0, ack 9001, win 0, length 0

15 packets (15 IPv4), protocols {'UDP': 2, 'TCP': 13}
top talkers: 10.0.0.5 → 10.0.0.10 (8), 10.0.0.10 → 10.0.0.5 (5), 10.0.0.5 → 10.0.0.2 (1)
- handshake 10.0.0.5:51514 → 10.0.0.10:80  RTT 0.45 ms
- RETRANSMISSION 10.0.0.5:51514 → 10.0.0.10:80 seq 1001 length 41 — packet or its ACK was lost
- RST 10.0.0.10:5432 → 10.0.0.5:51600 — connection refused/aborted (closed port, firewall reject, or app crash)
exit=1
```

**গল্পটি পড়ুন:**

1. DNS: `api.example.com`-এর query ও উত্তর (০.৮ ms)।
2. TCP handshake `[S]` → `[S.]` → `[.]`; seq সংখ্যার যোগ: SYN নিজে ১টি sequence number খায় (১০০০ → ack ১০০১)।
3. HTTP request (৪১ byte) — **২০৪ ms পরে একই seq-এ আবার** = retransmission।
4. Server ACK করে `ack 1042` (১০০১ + ৪১) ও উত্তর পাঠায়।
5. দুই দিকে FIN — graceful close (L02-05)।
6. Port ৫৪৩২-এ SYN → `[R.]` — সেখানে কিছু শুনছে না (L02-05-এর connection refused, wire-এ)।

### 9.2 Ubuntu-তে আসল capture (নিজের VM-এ)

একটি terminal-এ:

```bash
sudo tcpdump -ni any -S -c 20 'tcp port 8000 or udp port 53'
```

অন্য terminal-এ:

```bash
python3 -m http.server 8000 --bind 127.0.0.1 &
curl -s http://127.0.0.1:8000/ >/dev/null
curl -s http://127.0.0.1:8001/      # কেউ নেই → RST
dig +short example.com
kill %1
```

File-এ লিখে বিশ্লেষণ:

```bash
sudo tcpdump -ni any -w /tmp/lab.pcap 'tcp port 8000' -c 50
sudo chown "$USER" /tmp/lab.pcap
python3 pcap_summary.py /tmp/lab.pcap        # linktype 113 (any) — tool সমর্থন করে
tshark -r /tmp/lab.pcap -Y 'tcp.flags.reset == 1'   # sudo apt install tshark
rm /tmp/lab.pcap                              # কাজ শেষে capture মুছুন
```

Container-এর traffic (L02-13): host থেকে `sudo tcpdump -ni vethXXXX` বা `sudo nsenter -t PID -n tcpdump -ni eth0`।

> **Fedora-তে:** `sudo dnf install tcpdump wireshark-cli` (tshark-এর package `wireshark-cli`)। Wireshark GUI-তে capture করতে user-কে `wireshark` group-এ যোগ করতে হয় (Ubuntu-তে install-এর সময় প্রশ্ন করে)।

### 9.3 Test

```bash
python3 -m unittest -v
```

[`test_pcap.py`](code/L02-15/test_pcap.py)-এর ৭টি test: decode (UDP/TCP, flags, payload), **প্রতিটি packet-এর IP ও TCP/UDP checksum সঠিক** (Wireshark-এ ভুল checksum সতর্কতা আসবে না), tcpdump-শৈলীর লাইন হুবহু, বিশ্লেষণ (RTT ০.৪৫ ms, একটি retransmission, RST, RST-এর window ০ zero-window হিসেবে গণ্য নয়), big-endian file, কাটা file ও pcapng প্রত্যাখ্যান, VLAN-tagged frame।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `make_pcap.checksum` | RFC 1071 (L02-01) | IP ও TCP/UDP checksum |
| `l4_checksum` pseudo-header | src, dst, protocol, length | TCP/UDP checksum IP ঠিকানাও ঢাকে |
| `BASE_TS` নির্দিষ্ট | — | বারবার তৈরি করলে হুবহু একই file (test-যোগ্য) |
| `read_pcap` magic map | চার ধরনের header | Endianness ও nanosecond variant |
| `decode` linktype ১/১১৩, `0x8100` | Ethernet, Linux cooked, VLAN | আসল capture-এ এগুলোই আসে |
| `analyze` retransmission key | (দিক, seq, length) আগে দেখা | Wireshark-এর সরল সংস্করণ |
| RST-এ window ০ বাদ | `elif` | Refused connection-কে ভুলে zero window বলা এড়াতে (test-এ নিশ্চিত) |

**সীমাবদ্ধতা:** IPv6, IP fragment, SACK, out-of-order, duplicate ACK বিশ্লেষণ নেই; বড় file-এ পুরোটা memory-তে পড়ে।

**Python কেন এখানে, কোথায় নয়:** format বোঝা ও ছোট নির্দিষ্ট প্রশ্নের automation (যেমন CI-তে "retransmission > X% হলে fail")-এ ভালো। আসল বিশ্লেষণে Wireshark/tshark — হাজারো protocol dissector ও পরিপক্ব TCP analysis; বড় file-এ `tshark`-এর field export বা `scapy`/`dpkt`।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `pcap_summary.py sample.pcap` | ১৫ packet, RTT ০.৪৫ ms, ১টি retransmission, ১টি RST, exit ১ |
| Wireshark-এ `sample.pcap`, filter `tcp.analysis.retransmission` | packet ৭ চিহ্নিত |
| Ubuntu-তে closed port-এ curl | tcpdump-এ `[S]` তারপর `[R.]` |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `tcpdump: eth0: No such device` | Interface নাম ভিন্ন | `ip link` | সঠিক নাম বা `-i any` |
| কিছুই capture হয় না | ভুল interface/filter; traffic loopback-এ | Filter সরিয়ে দেখুন | `-i lo` বা `-i any` |
| `packets dropped by kernel` | Filter খুব প্রশস্ত, buffer ছোট | tcpdump-এর শেষের সারাংশ | সংকীর্ণ filter, `-s`, `-B` |
| Wireshark-এ সব checksum ভুল | Checksum offload (NIC-এ হিসাব হয়) | নিজের পাঠানো packet-এ শুধু | স্বাভাবিক — validation বন্ধ রাখুন |
| Capture-এ HTTP দেখা যায় না | HTTPS | Port ৪৪৩, TLS | Application log বা lab-এ key log |
| Disk ভরে গেছে | Ring buffer ছাড়া দীর্ঘ capture | `df -h` | `-C`/`-G` + `-W` |
| pcapng পড়ে না | Format ভিন্ন | file magic | `editcap -F pcap` |

## 13. Security, performance ও cost বিবেচনা

- **Security ও নৈতিকতা:** শুধু **নিজের বা অনুমতিপ্রাপ্ত** system-এ capture — অন্যের network-এ capture আইনত ও নীতিগতভাবে নিষিদ্ধ হতে পারে। Capture file-এ password, token, cookie, PII থাকতে পারে — permission `600`, কাজ শেষে মুছুন, কখনো Git-এ নয় (এই repository-র `.gitignore`-এ `*.pcap` যোগ করা হয়েছে, শুধু synthetic নমুনা ব্যতিক্রম), ticket-এ attach করার আগে sanitize। `tcpdump` চালাতে root/`CAP_NET_RAW` লাগে — production-এ কে capture করতে পারে তা নিয়ন্ত্রিত ও audit-যোগ্য হওয়া উচিত।
- **Performance:** ব্যস্ত server-এ প্রশস্ত capture CPU ও disk-এ চাপ দেয় — সংকীর্ণ filter, ছোট snaplen, সীমিত সময়।
- **Cost:** Cloud-এ traffic mirroring service ও capture-এর storage বিলযুক্ত; প্রায়ই flow logs (L02-14) যথেষ্ট এবং সস্তা — full capture শেষ উপায়।

## 14. Hands-on exercise

1. `sample.pcap` Wireshark-এ খুলুন (laptop-এ): Follow TCP Stream, Expert Information, Statistics → Conversations। Tool-এর output-এর সাথে মেলান।
2. `make_pcap.py`-তে একটি zero-window ঘটনা যোগ করুন (server `win 0` সহ ACK), এবং `pcap_summary.py` সেটি ধরে কিনা test লিখুন।
3. Ubuntu VM-এ Section 9.2; তারপর L02-09-এর `ping -M do -s 1473` চালিয়ে `tcpdump 'icmp'`-এ "frag needed" বার্তা দেখুন।
4. L02-13-এর `netns_lab.sh` চালিয়ে `tcpdump -ni br-lab` — red → blue ping-এর ARP request/reply ও ICMP দেখুন।
5. `curl https://example.com` capture করে `tshark -Y 'tls.handshake.type == 1' -T fields -e tls.handshake.extensions_server_name` — SNI বের করুন। Encryption-এর পরেও কী কী তথ্য দেখা যায় তার তালিকা লিখুন।

## 15. Mini-project — Capture runbook

একটি runbook (`runbooks/`-এর template অনুসরণ করে, Module 17-এ সম্পূর্ণ হবে): "কখন capture নেবেন", অনুমতি ও data handling, প্রস্তুত command (DNS, connection refused, slow response, MTU, TLS), ring buffer সেটআপ, বিশ্লেষণের checklist (`pcap_summary.py` → Wireshark), এবং capture মোছার ধাপ। সাথে একটি wrapper script যা নিরাপদ default (`-s 256`, `-c`, `-G`, output mode `600`) দিয়ে tcpdump চালায়।

## 16. Interview প্রশ্ন

1. Capture filter ও display filter-এর পার্থক্য।
2. tcpdump-এ `[S.]`, `[P.]`, `[R.]` কী বোঝায়?
3. Capture-এ retransmission কীভাবে চিনবেন এবং কী অর্থ?
4. HTTPS traffic capture করলে কী দেখা যায়, কী যায় না?
5. "Client বলছে পাঠিয়েছে, server বলছে পায়নি" — capture দিয়ে কীভাবে প্রমাণ করবেন?
6. Production server-এ capture নেওয়ার সময় কী কী সতর্কতা?

## 17. Self-assessment প্রশ্ন

1. CCTV analogy কোথায় মেলে না (তিনটি বিষয়)?
2. `sample.pcap`-এ server-এর `ack 1042` কীভাবে হিসাব হলো?
3. Retransmission ও RST — দুটিকে tool কীভাবে আলাদা করে চেনে?
4. Section 5-এ সমস্যা কেন "দূরত্ব" নয় বরং "loss"?
5. Real capture কেন repository-তে রাখা যাবে না?

## 18. সংক্ষিপ্ত সারাংশ

- Packet capture = network-এ আসলে কী ঘটেছে তার নিরপেক্ষ সাক্ষী।
- Server-এ `tcpdump -w` (সংকীর্ণ BPF filter, snaplen, সীমা) → laptop-এ Wireshark।
- Flags: `[S]`, `[S.]`, `[.]`, `[P.]`, `[F.]`, `[R]`; seq/ack থেকে কথোপকথন পড়া যায়।
- চিনুন: handshake RTT, retransmission (~২০০ ms লাফ), RST, zero window।
- TLS-এ content নয়, metadata দেখা যায়।
- Capture = সংবেদনশীল data: অনুমতি, `600`, মুছে ফেলা, Git-এ নয়।

## 19. Completion checklist

- [ ] `sample.pcap` tool ও Wireshark দুটো দিয়ে বিশ্লেষণ করেছি
- [ ] Ubuntu-তে আসল capture নিয়ে handshake ও RST দেখেছি
- [ ] Capture ও display filter দুটোই লিখতে পারি
- [ ] Capture file মুছে ফেলেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `tcpdump(1)`: https://www.tcpdump.org/manpages/tcpdump.1.html
- `pcap-filter(7)` (BPF syntax): https://www.tcpdump.org/manpages/pcap-filter.7.html
- pcap file format (draft): https://www.ietf.org/archive/id/draft-ietf-opsawg-pcap-04.html
- Wireshark User's Guide: https://www.wireshark.org/docs/wsug_html_chunked/
- Wireshark display filter reference: https://www.wireshark.org/docs/dfref/
- `tshark(1)`: https://www.wireshark.org/docs/man-pages/tshark.html
- LINKTYPE values (tcpdump.org): https://www.tcpdump.org/linktypes.html

---

**পরের lesson:** L02-16 — Troubleshooting toolkit: dig, curl, ss, ip, traceroute, mtr
