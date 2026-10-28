# L02-01 — OSI ও TCP/IP model

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [Module 01](../01-linux-systems/README.md) সম্পূর্ণ (বিশেষ করে [L01-01 — system call](../01-linux-systems/L01-01-linux-architecture.md)) |
| **Label** | — |
| **Tested** | `packet_layers.py`: ৬টি test পাস, যার একটি **RFC 1071-এর নিজস্ব উদাহরণ**-এর checksum (`0x220d`) হুবহু মিলিয়েছে; demo ও hexdump চালানো (Python 3.14, Windows)। `tcpdump`, `ip`, `ss` command **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- কেন network-কে **layer**-এ ভাগ করা হয়।
- **OSI model** (৭ layer) ও **TCP/IP model** (৪ layer) — কোনটি কোথায় কাজে লাগে।
- **Encapsulation** ও **decapsulation** — data নামার সময় header যোগ, ওঠার সময় খোলা।
- প্রতিটি layer-এর **address** (port, IP, MAC) ও **unit** (segment, packet, frame)।
- Troubleshooting-এ layer-ভিত্তিক চিন্তা: "কোন layer-এ ভাঙছে?"
- Python দিয়ে নিজের হাতে TCP/IPv4/Ethernet header তৈরি ও byte-by-byte বিশ্লেষণ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি web request-এ অনেক জিনিস জড়িত: browser, operating system, Wi-Fi বা cable, router, ISP, data center-এর switch, load balancer, server। যদি প্রতিটি program-কে এই সব একসাথে জানতে হতো, তাহলে Wi-Fi থেকে cable-এ গেলেই browser নতুন করে লিখতে হতো।

**Layering** সমস্যাটিকে ভাগ করে: প্রতিটি layer একটি নির্দিষ্ট কাজ করে এবং শুধু উপরের ও নিচের layer-এর সাথে নির্দিষ্ট interface দিয়ে কথা বলে। ফলে HTTP জানে না নিচে Wi-Fi না fiber; Ethernet জানে না উপরে HTTP না SSH।

DevOps-এ এর সরাসরি ব্যবহার: incident-এ "site কাজ করছে না" থেকে দ্রুত **কোন layer** — DNS (application), port বন্ধ (transport), route নেই (network), cable/VLAN (link)। L00-06-এর বৈজ্ঞানিক পদ্ধতি network-এ মানে layer ধরে hypothesis। পুরো Module 02 এই কাঠামোর উপর দাঁড়িয়ে, এবং L02-17-এ একটি request-এর পূর্ণ যাত্রায় সব layer একসাথে দেখবেন।

## 3. সহজ ভাষায় পরিচয়

| OSI layer | নাম | কাজ | উদাহরণ | Address / unit |
|---|---|---|---|---|
| 7 | Application | User-এর program-এর ভাষা | HTTP, DNS, SSH | — / message |
| 6 | Presentation | Format, encoding, encryption | TLS (আংশিক), UTF-8 | |
| 5 | Session | Session পরিচালনা | (বাস্তবে app/TLS-এর ভেতরে) | |
| 4 | Transport | Process থেকে process, নির্ভরযোগ্যতা | TCP, UDP | **port** / segment (TCP), datagram (UDP) |
| 3 | Network | Network পেরিয়ে host থেকে host, routing | IP, ICMP | **IP address** / packet |
| 2 | Data link | একই link-এ পরের device পর্যন্ত | Ethernet, Wi-Fi, ARP | **MAC address** / frame |
| 1 | Physical | Bit-কে signal-এ | Cable, radio, fiber | — / bit |

**TCP/IP model** (Internet-এর আসল নকশা) — চারটি layer:

```text
 TCP/IP                   OSI
 Application        ←→    7 + 6 + 5
 Transport          ←→    4
 Internet           ←→    3
 Link (network access) ←→ 2 + 1
```

বাস্তবে আমরা **TCP/IP-ই ব্যবহার করি**, কিন্তু কথা বলার সময় OSI-র **নম্বর** (L4 load balancer, L7 proxy, L2 switch) সর্বজনীন।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### চিঠি ও খামের ভেতরে খাম

ঢাকার একটি অফিসের কর্মী চট্টগ্রামের অফিসের একজনকে চিঠি পাঠাচ্ছেন:

1. **L7:** চিঠির বিষয়বস্তু ("সভা সোমবার")।
2. **L4:** ভেতরের খামে লেখা "Accounts বিভাগ, টেবিল ৩" — কোন **বিভাগ/মানুষ** (port: কোন program)।
3. **L3:** বাইরের খামে **অফিসের ঠিকানা** — শহর, রাস্তা (IP: কোন host)।
4. **L2:** কুরিয়ার কোম্পানির ব্যাগে লেবেল: "পরের ধাপ: ঢাকা হাব → কুমিল্লা হাব" — শুধু **পরের হাব পর্যন্ত** (MAC: পরের device)।
5. **L1:** ট্রাক, রাস্তা।

প্রতিটি হাবে কুরিয়ার ব্যাগের লেবেল (L2) **বদলায়**, কিন্তু খামের ঠিকানা (L3) **একই থাকে**। গন্তব্যে খাম খোলা হয় বাইরে থেকে ভেতরে — decapsulation।

### Analogy কোথায় মেলে না

- চিঠি একবারে যায়। Network-এ বড় data **অনেক ছোট packet-এ ভাগ** হয়, আলাদা পথে যেতে পারে, ভিন্ন ক্রমে পৌঁছাতে পারে — TCP আবার সাজায় (L02-05)।
- খামের ঠিকানা কখনো বদলায় না। Network-এ **NAT** (L02-04) পথে IP ঠিকানাও বদলে দেয় — বাড়ির router আপনার private IP-কে public IP-তে বদলায়।
- চিঠির খাম হাতে লেখা। Header-গুলো নির্দিষ্ট আকারের byte field — এই lesson-এর Python code সেই byte-গুলো নিজে তৈরি করে।

## 5. Real-world engineering scenario — "Website খোলে না" — কোন layer?

**পরিস্থিতি:** Monitoring alert: `https://app.example.com` timeout। কোথা থেকে শুরু করবেন?

**Layer ধরে যাচাই (নিচ থেকে উপরে বা উপর থেকে নিচে — দুইভাবেই চলে):**

| Layer | প্রশ্ন | Command (L02-16-এ বিস্তারিত) | ব্যর্থ হলে কী বোঝায় |
|---|---|---|---|
| L7 (DNS) | নামটি IP-তে resolve হয়? | `dig +short app.example.com` | DNS record/resolver সমস্যা |
| L3 | IP-তে পৌঁছানো যায়? | `ping`, `mtr` | Route, firewall (ICMP), host down |
| L4 | Port খোলা? | `nc -vz IP 443` | Service চলছে না বা firewall |
| L6/L7 (TLS) | Certificate ঠিক? | `openssl s_client -connect IP:443 -servername app.example.com` | Certificate মেয়াদ/নাম |
| L7 (HTTP) | Application উত্তর দেয়? | `curl -v https://app.example.com/health` | App error (5xx), proxy |

**উদাহরণ ফল:** DNS ঠিক, ping ঠিক, কিন্তু `nc -vz IP 443` → "Connection timed out" → **L4**: port-এ পৌঁছানো যাচ্ছে না, তবে host জীবিত। পরের hypothesis: firewall/security group ৪৪৩ বন্ধ (L02-10), অথবা load balancer-এর পেছনে service নেই। এভাবে সম্ভাবনা দ্রুত কমে।

**শিক্ষা:** Layer model হলো troubleshooting-এর **checklist** — প্রতিটি পরীক্ষা একটি layer-কে "সন্দেহের তালিকা" থেকে বাদ দেয়।

## 6. Diagram — encapsulation

```text
 Sender                                                              Receiver
 ┌────────────────────────────────────────┐
 │ L7  HTTP: "GET / HTTP/1.1 ..."   37 B  │                    ▲ app পায় শুধু HTTP
 ├────────────────────────────────────────┤                    │
 │ L4  [TCP hdr 20B][      HTTP       ]   │  segment           │ TCP header খোলা (port দিয়ে কোন process)
 ├────────────────────────────────────────┤                    │
 │ L3  [IP hdr 20B][TCP][    HTTP     ]   │  packet            │ IP header খোলা (আমার IP? checksum ঠিক?)
 ├────────────────────────────────────────┤                    │
 │ L2  [Eth 14B][IP][TCP][  HTTP  ][FCS]  │  frame             │ Ethernet header খোলা (আমার MAC?)
 ├────────────────────────────────────────┤                    │
 │ L1  10110010... (signal)               │  bits ────────────►┘
 └────────────────────────────────────────┘
       প্রতিটি router-এ: L2 খোলা ও নতুন L2 লাগানো; L3 header-এর TTL এক কমে
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Protocol | যোগাযোগের নিয়ম (format, ক্রম, অর্থ) |
| Layer | নির্দিষ্ট দায়িত্বের একটি স্তর |
| Encapsulation | উপরের layer-এর data-র সামনে নিজের header যোগ |
| Decapsulation | গ্রাহকের দিকে header খুলে উপরে পাঠানো |
| Header | Data-র সামনে নিয়ন্ত্রণ তথ্য (address, length, checksum) |
| PDU | Protocol Data Unit — layer অনুযায়ী নাম: segment/packet/frame |
| Port | Host-এর ভেতরে কোন program (L4) — ০–৬৫৫৩৫ |
| IP address | Network-এ host-এর logical ঠিকানা (L3) |
| MAC address | একটি network interface-এর hardware ঠিকানা (L2) |
| Hop | Packet-এর পথে একটি router অতিক্রম |
| TTL | IP packet কতগুলো hop যেতে পারবে; প্রতিটি router এক কমায় |
| Checksum | Data বদলে গেছে কিনা ধরার সংখ্যা |
| MTU | একটি link-এ সর্বোচ্চ packet আকার (Ethernet-এ সাধারণত ১৫০০ byte, L02-09) |
| Ethertype | Ethernet frame-এর ভেতরে কোন protocol (০x০৮০০ = IPv4, ০x৮৬DD = IPv6) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 কোথায় কোন layer চলে (Linux-এ)

| Layer | কোথায় |
|---|---|
| L7 | User space — browser, curl, Nginx, Python program |
| L4, L3 | **Kernel** — TCP/IP stack (L01-01: `socket`, `connect`, `send` system call) |
| L2 | Kernel driver + network card |
| L1 | Network card hardware |

তাই একটি Python program `socket.send(b"GET / ...")` করলে শুধু L7 data দেয়; kernel TCP, IP ও Ethernet header যোগ করে। এই lesson-এর `packet_layers.py` শেখার জন্য সেই কাজটি নিজে user space-এ করে দেখায়।

### 8.2 Header-এর মূল field

**IPv4 header (২০ byte, option ছাড়া):** version ও header length, total length, identification, flags (DF = "fragment কোরো না", L02-09), **TTL**, protocol (৬ = TCP, ১৭ = UDP, ১ = ICMP), **header checksum**, **source IP**, **destination IP**।

**TCP header (২০ byte, option ছাড়া):** **source port**, **destination port**, sequence number, acknowledgment number, header length, **flags** (SYN, ACK, FIN, RST, PSH), window, checksum, urgent pointer। বিস্তারিত L02-05।

**Ethernet header (১৪ byte):** destination MAC, source MAC, ethertype। শেষে ৪ byte **FCS** (CRC — card তৈরি ও যাচাই করে)।

### 8.3 Checksum কীভাবে কাজ করে (Internet checksum, RFC 1071)

1. Data-কে ১৬-bit শব্দে ভাগ করুন।
2. সব যোগ করুন; ১৬ bit-এর বেশি হলে উপচে পড়া অংশ নিচে যোগ করুন ("end-around carry")।
3. ফলের সব bit উল্টে দিন (one's complement)।

গ্রাহক checksum field সহ পুরো header যোগ করলে ফল **শূন্য** (complement-এর পরে) হওয়া উচিত — না হলে data নষ্ট। TCP checksum-এ IP ঠিকানাসহ একটি "pseudo-header" যোগ হয়, যাতে ভুল host-এ পৌঁছানো segment-ও ধরা পড়ে।

এই checksum শুধু দুর্ঘটনাজনিত পরিবর্তন ধরে — **ইচ্ছাকৃত পরিবর্তন নয়** (আক্রমণকারী checksum-ও আবার হিসাব করতে পারে)। Integrity-র জন্য TLS (L02-08)।

### 8.4 Overhead

ছোট payload-এ header-এর অংশ বড়: ৩৭ byte HTTP-তে ৫৪ byte header (এই lesson-এর আসল হিসাব) — ৫৯%। বড় payload (১৪৬০ byte) হলে অনুপাত ~৪%। এজন্য অনেক ছোট request (chatty API) network-এ অদক্ষ — batching ও HTTP/2-এর একটি কারণ (L02-07)।

## 9. Practical demonstration

### 9.1 Python দিয়ে encapsulation

File: [`code/L02-01/packet_layers.py`](code/L02-01/packet_layers.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-01
python3 packet_layers.py --hexdump
```

Script শুধু memory-তে byte তৈরি করে — কিছু পাঠায় না। Address-গুলো উদাহরণ।

**এই repository-তে চালিয়ে পাওয়া আসল output:**

```text
encapsulation (sender, top → bottom):
  L7 application (HTTP)      37 bytes
  L4 TCP header              20 bytes
  L3 IPv4 header             20 bytes
  L2 Ethernet header         14 bytes
  frame total                91 bytes  (header overhead 54 = 59.3%; + 4-byte FCS ও preamble wire-এ যোগ হয়)

decapsulation (receiver, bottom → top):
  L2: 52:54:00:12:34:56 → 52:54:00:ab:cd:ef  ethertype 0x0800 (IPv4)
  L3: 192.168.1.10 → 93.184.215.14  TTL 64  header checksum ok
  L4: port 51544 → 80
  L7: b'GET / HTTP/1.1\r\nHost: example.com\r\n\r\n'

0000  52 54 00 ab cd ef 52 54 00 12 34 56 08 00 45 00  RT....RT..4V..E.
0010  00 4d 1c 46 40 00 40 06 27 ec c0 a8 01 0a 5d b8  .M.F@.@.'.....].
0020  d7 0e c9 58 00 50 00 00 03 e8 00 00 00 01 50 18  ...X.P........P.
0030  fa f0 a8 06 00 00 47 45 54 20 2f 20 48 54 54 50  ......GET / HTTP
0040  2f 31 2e 31 0d 0a 48 6f 73 74 3a 20 65 78 61 6d  /1.1..Host: exam
0050  70 6c 65 2e 63 6f 6d 0d 0a 0d 0a                 ple.com....
```

**Hexdump পড়তে শিখুন (byte offset hex-এ):**

| Byte | মান | অর্থ |
|---|---|---|
| ০–৫ | `52 54 00 ab cd ef` | L2 destination MAC |
| ৬–১১ | `52 54 00 12 34 56` | L2 source MAC |
| ১২–১৩ | `08 00` | Ethertype = IPv4 |
| ১৪ | `45` | IPv4, header ৫ × ৪ = ২০ byte |
| ১৬–১৭ | `00 4d` | Total length = ৭৭ (২০ IP + ২০ TCP + ৩৭ HTTP) |
| ২২ | `40` | TTL = ৬৪ |
| ২৩ | `06` | Protocol = TCP |
| ২৬–২৯ | `c0 a8 01 0a` | Source IP 192.168.1.10 |
| ৩০–৩৩ | `5d b8 d7 0e` | Destination IP |
| ৩৪–৩৫ | `c9 58` | Source port ৫১৫৪৪ |
| ৩৬–৩৭ | `00 50` | Destination port ৮০ |
| ৪৭ | `18` | TCP flags: PSH + ACK |
| ৫৪ থেকে | `47 45 54 ...` | "GET / HTTP/1.1..." |

### 9.2 আসল packet দেখা (Ubuntu VM)

```bash
ip -br addr                    # L3: interface ও IP
ip -br link                    # L2: interface ও MAC
ip route                       # L3: route (L02-04)
ss -tn                         # L4: চলমান TCP connection, port
sudo tcpdump -i any -nn -c 5 port 80 &    # L2-L4 header দেখা (L02-15-এ বিস্তারিত)
curl -s http://example.com > /dev/null
wait
```

উদাহরণ `tcpdump` লাইন:

```text
10:15:02.123 eth0 Out IP 192.168.56.10.51544 > 93.184.215.14.80: Flags [P.], seq 1:76, ack 1, win 502, length 75
```

একই লাইনে L3 (IP), L4 (port, flags `[P.]` = PSH+ACK, seq), L7-এর দৈর্ঘ্য — Python demo-র সাথে মিলিয়ে দেখুন।

> **Fedora-তে:** একই command; `tcpdump` install: `sudo dnf install tcpdump`।

### 9.3 Test

```bash
python3 -m unittest -v
```

[`test_packet_layers.py`](code/L02-01/test_packet_layers.py)-এর ৬টি test: **RFC 1071-এর উদাহরণ** (০x২২০d), বৈধ header-এর checksum শূন্য, প্রতিটি layer-এর আকার, round trip, TCP pseudo-header checksum, এবং TTL বদলালে checksum ভুল ধরা।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `struct.pack("!HHII...")` | Python মান → network byte order-এর byte | `!` = big-endian ("network order") — সব Internet protocol এটি ব্যবহার করে |
| `checksum()` | RFC 1071 | end-around carry ও complement |
| TCP-তে pseudo-header | Source/dest IP যোগ করে checksum | ভুল host-এ যাওয়া segment ধরা |
| `5 << 4` | TCP data offset (৫ × ৪ = ২০ byte) | Header-এর প্রথম ৪ bit |
| `0x4000` | IPv4 flags: DF | Fragment নয় (L02-09) |
| `decode()` | `ihl`, `data_offset` পড়ে header-এর আকার বের করা | Option থাকলে header বড় হতে পারে — ধরে নেওয়া নয়, পড়া |

### Python কেন এখানে, আর কোথায় নয়

বাস্তবে header তৈরি করে **kernel** — program নিজে করে না। Python এখানে শিক্ষার জন্য ভেতরটা দৃশ্যমান করে। বাস্তব packet দেখতে **tcpdump/Wireshark** (L02-15); packet তৈরি ও পরীক্ষায় Python-এর Scapy library জনপ্রিয় (শুধু নিজের lab-এ)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `packet_layers.py` | ৩৭ + ২০ + ২০ + ১৪ = ৯১ byte, checksum ok |
| `--payload ""` | overhead ১০০% |
| `tcpdump`-এর লাইন | IP, port, flags দেখা যায় |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল ধারণা / Symptom | আসলে | কীভাবে যাচাই |
|---|---|---|
| "MAC address দিয়ে internet-এ পৌঁছানো যায়" | MAC শুধু একই link-এ; প্রতিটি router-এ বদলায় | tcpdump-এ দুই প্রান্তের MAC তুলনা |
| "ping কাজ করে, তাই website-ও কাজ করবে" | ping = L3 (ICMP); website = L4 + L7 | `nc -vz`, `curl -v` |
| "ping কাজ করে না, তাই host down" | Firewall ICMP বন্ধ রাখতে পারে | `nc -vz` port-এ চেষ্টা |
| L4 ও L7 load balancer গুলিয়ে ফেলা | L4 port/IP দেখে, L7 HTTP path/header দেখে | L02-12 |
| Byte order ভুল (`struct` `!` ছাড়া) | Little-endian machine-এ ভুল মান | Test |

## 13. Security, performance ও cost বিবেচনা

- **Security:** প্রতিটি layer-এর নিজস্ব আক্রমণ ও সুরক্ষা: L2 (ARP spoofing, L02-02), L3 (IP spoofing, firewall), L4 (SYN flood, port scan), L7 (injection, TLS)। Checksum নিরাপত্তা নয় — integrity ও confidentiality-র জন্য TLS। Packet capture-এ password ও data দেখা যায় (unencrypted protocol-এ) — শুধু নিজের/অনুমোদিত network-এ।
- **Performance:** ছোট message-এ header overhead; latency প্রতিটি hop-এ যোগ হয়।
- **Cost:** Cloud-এ data transfer (বিশেষত internet-এ বা region পেরিয়ে) বিল হয় — header-ও গোনা হয়; chatty protocol খরচ বাড়ায় (Module 29)।

## 14. Hands-on exercise

1. `packet_layers.py --payload ""` ও ১৪৬০ byte payload (`--payload "$(printf 'x%.0s' {1..1460})"`) চালিয়ে overhead শতাংশ তুলনা করুন।
2. Hexdump থেকে TCP checksum-এর byte দুটি খুঁজে বের করুন (offset কত?)।
3. `packet_layers.py`-তে UDP support যোগ করুন (৮ byte header: src port, dst port, length, checksum; IP protocol ১৭)। Test লিখুন।
4. Section 5-এর table নিজের ভাষায় লিখে প্রতিটি layer-এর জন্য আরেকটি করে failure উদাহরণ দিন।
5. `sudo tcpdump -i any -nn -c 3 icmp` চালিয়ে `ping -c 1 8.8.8.8` করুন — কোন layer-এর তথ্য দেখছেন?

## 15. Mini-project — layer troubleshooting checklist

`~/devops-notebook/cheatsheet-network-layers.md`-এ একটি checklist বানান: প্রতিটি layer-এর জন্য একটি প্রশ্ন, একটি command, স্বাভাবিক output-এর নমুনা (নিজে চালিয়ে), ও ব্যর্থতার অর্থ। পরের lesson-গুলোতে (DNS, TCP, TLS, firewall) এটি সম্প্রসারিত হবে এবং L02-16-এর troubleshooting toolkit-এর ভিত্তি হবে।

## 16. Interview প্রশ্ন

1. OSI-র ৭টি layer ও TCP/IP-র ৪টি layer বলুন; DevOps-এ কেন OSI নম্বর ব্যবহার হয়?
2. Encapsulation কী? একটি HTTP request-এ কোন কোন header যোগ হয়?
3. MAC ও IP address-এর পার্থক্য কী? Router পেরোলে কোনটি বদলায়?
4. L4 ও L7 load balancer-এর পার্থক্য কী?
5. Website খোলে না — layer ধরে কীভাবে তদন্ত করবেন?
6. TTL কী এবং কেন দরকার?
7. Checksum কি নিরাপত্তা দেয়?

## 17. Self-assessment প্রশ্ন

1. চিঠি-খাম analogy কোথায় মেলে না?
2. Hexdump-এ `00 4d` কেন ৭৭?
3. Checksum-এর তিনটি ধাপ এবং গ্রাহক কীভাবে যাচাই করে।
4. TCP checksum-এ pseudo-header কেন?
5. Linux-এ কোন layer user space-এ, কোনটি kernel-এ?
6. Section 5-এ `nc` timeout দেখে কোন সম্ভাবনা বাদ গেল?

## 18. সংক্ষিপ্ত সারাংশ

- Network layer-এ ভাগ: প্রতিটি layer একটি কাজ করে, নিজের header যোগ করে (**encapsulation**)।
- OSI ৭ layer (ভাষা ও নম্বর), TCP/IP ৪ layer (বাস্তব)।
- Address: port (L4), IP (L3), MAC (L2); unit: segment, packet, frame।
- Router-এ L2 বদলায়, L3 থাকে (TTL কমে) — NAT বাদে।
- Troubleshooting = layer ধরে hypothesis বাদ দেওয়া।

## 19. Completion checklist

- [ ] `packet_layers.py --hexdump` চালিয়ে প্রতিটি header-এর byte চিহ্নিত করেছি
- [ ] `ip`, `ss`, `tcpdump` দিয়ে নিজের machine-এ প্রতিটি layer-এর তথ্য দেখেছি
- [ ] UDP support (Exercise ৩) যোগ করেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] Layer troubleshooting checklist শুরু করেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 1122 — Requirements for Internet Hosts (TCP/IP layer): https://www.rfc-editor.org/rfc/rfc1122
- RFC 791 — Internet Protocol (IPv4): https://www.rfc-editor.org/rfc/rfc791
- RFC 9293 — Transmission Control Protocol: https://www.rfc-editor.org/rfc/rfc9293
- RFC 1071 — Computing the Internet Checksum: https://www.rfc-editor.org/rfc/rfc1071
- Python `struct`: https://docs.python.org/3/library/struct.html
- `ip(8)`: https://man7.org/linux/man-pages/man8/ip.8.html

---

**পরের lesson:** L02-02 — Ethernet, MAC address, ARP, switching ও VLAN
