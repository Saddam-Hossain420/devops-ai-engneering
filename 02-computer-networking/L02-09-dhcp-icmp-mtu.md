# L02-09 — DHCP, ICMP, MTU ও path MTU discovery

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L02-03 — IP addressing](L02-03-ip-addressing-cidr.md), [L02-05 — TCP, UDP](L02-05-tcp-udp-sockets.md) |
| **Label** | — |
| **Tested** | `mtu_calc.py`: ৭টি test পাস (Python 3.14, Windows)। **আসল path MTU পরীক্ষা** চালানো হয়েছে (২০২৬-১০-২৬, Windows `ping -f -l`, লেখকের home network → ১.১.১.১): DF সহ ১৪৭২ byte ব্যর্থ, binary search-এ সর্বোচ্চ ১৪৫২ → path MTU **১৪৮০** — output Section 9.2-এ। Linux-এর `ping -M do`, `tracepath`, `ip link set mtu`, `dhclient`/`networkctl` **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- **DHCP**: একটি machine কীভাবে IP, gateway, DNS পায় — DORA, lease, T1/T2।
- **ICMP**: network-এর "error ও diagnostic বার্তা" — echo, destination unreachable, time exceeded, fragmentation needed।
- **MTU** ও **MSS**: একটি packet সর্বোচ্চ কত বড় হতে পারে এবং কেন tunnel-এ কমে।
- **Fragmentation** ও **Path MTU Discovery (PMTUD)**; ICMP block করলে কেন "black hole"।
- `ping -M do -s`, `tracepath` দিয়ে path MTU বের করা।
- VXLAN, WireGuard, PPPoE, AWS jumbo frame-এর MTU হিসাব।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

এই তিনটি protocol চোখের আড়ালে থাকে, কিন্তু ভুল হলে উদ্ভট incident তৈরি করে:

- **DHCP:** নতুন VM বা container host-এ IP আসে না; lease শেষে হঠাৎ IP বদলায়; ভুল DNS server বিতরণ।
- **ICMP:** "নিরাপত্তার জন্য" সব ICMP block — ফলে `ping` তো চলেই না, PMTUD-ও ভাঙে।
- **MTU:** সবচেয়ে বিভ্রান্তিকর symptom — **ছোট request কাজ করে, বড়টা ঝুলে থাকে।** SSH login হয় কিন্তু `ls` বড় directory-তে আটকে যায়; `curl` header পায় কিন্তু body আসে না; VPN-এ কিছু site খোলে, কিছু খোলে না; Kubernetes overlay network-এ pod-to-pod-এ বড় response timeout।

## 3. সহজ ভাষায় পরিচয়

### DHCP — ঠিকানা ধার দেওয়া

নতুন machine network-এ এলে তার IP নেই। সে broadcast করে, DHCP server উত্তর দেয় — চার ধাপে (**DORA**):

```text
Client (0.0.0.0, UDP 68)                          DHCP server (UDP 67)
   │── Discover (broadcast) "কেউ IP দেবে?" ────────────►│
   │◄─ Offer "192.168.1.50 নাও, gateway .1, DNS .1, ২৪ ঘণ্টা" ─│
   │── Request (broadcast) "আমি .50 নিচ্ছি" ───────────►│  (broadcast — অন্য server-রা জানুক)
   │◄─ Ack "নিশ্চিত" ─────────────────────────────────────│
```

IP একটি **lease** — নির্দিষ্ট সময়ের ধার। **T1** (৫০%) এ client একই server-এর কাছে নবায়ন চায়; না পেলে **T2** (৮৭.৫%) এ যেকোনো server-কে; মেয়াদ শেষে IP ছেড়ে দেয়।

DHCP শুধু IP নয়, দেয়: subnet mask, gateway (L02-04), DNS server (L02-06), search domain, NTP, MTU ইত্যাদি।

### ICMP — network-এর বার্তাবাহক

ICMP (IP protocol ১; IPv6-এ ICMPv6) data বহন করে না, **network-এর অবস্থা জানায়**:

| Type | নাম | কে পাঠায়, কখন | Tool |
|---|---|---|---|
| 8 / 0 | Echo request / reply | | `ping` |
| 3 | Destination unreachable | Router/host — পথ নেই, port বন্ধ (UDP) | |
| 3 code 4 | **Fragmentation needed** (IPv6: Packet Too Big) | Router — "packet বড়, DF set, আমার MTU এত" | PMTUD |
| 11 | Time exceeded | Router — TTL শূন্য হয়েছে | `traceroute`, `mtr` |
| 5 | Redirect | Router — "অন্য gateway ব্যবহার করো" | (সাধারণত বন্ধ রাখা হয়) |

IPv6-এ ICMPv6 আরো মৌলিক: neighbor discovery (ARP-এর বদলে, L02-02) ও router advertisement এর উপর চলে। **IPv6-এ ICMPv6 block = network ভাঙা।**

### MTU ও MSS

**MTU** (Maximum Transmission Unit) = একটি link-এ সর্বোচ্চ IP packet-এর আকার। Ethernet-এ সাধারণত **১৫০০** byte।

```text
|<───────────────────────── MTU 1500 ─────────────────────────>|
| IPv4 header 20 | TCP header 20 | data (MSS) 1460              |
| IPv4 header 20 | ICMP 8        | ping payload 1472            |
```

**MSS** (Maximum Segment Size) = TCP segment-এ সর্বোচ্চ data = MTU − ৪০ (IPv4)। Handshake-এ (SYN) দুই পক্ষ নিজেদের MSS জানায়।

**Tunnel = packet-এর উপর আরেকটি header** → ভেতরের MTU কমে:

| Encapsulation | Overhead | ১৫০০-এর ভেতরে |
|---|---|---|
| PPPoE (কিছু broadband) | 8 | 1492 |
| VXLAN (Kubernetes overlay, Flannel ইত্যাদি) | 50 | 1450 |
| WireGuard (IPv6 underlay ধরে) | 80 | **1420** (default) |
| GRE | 24 | 1476 |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### সুড়ঙ্গ আর ট্রাক

- **MTU** = রাস্তার উচ্চতা-সীমা। ১৫০০ সেমি পর্যন্ত ট্রাক চলতে পারে।
- **Tunnel** (VXLAN, WireGuard) = ট্রাককে একটি বড় container-এ তুলে নেওয়া — container-এর দেয়ালের জন্য ভেতরে ট্রাক এখন ১৪৫০ পর্যন্ত।
- **Fragmentation** = বড় মাল ভেঙে কয়েকটি ছোট ট্রাকে পাঠানো; গন্তব্যে আবার জোড়া। একটি ট্রাক হারালে **পুরো মাল বাতিল**।
- **DF (Don't Fragment)** = "ভাঙা যাবে না" লেখা মাল। সুড়ঙ্গ ছোট হলে প্রহরী ফেরত পাঠান — "**এখানে উচ্চতা-সীমা ১৪০০**" চিঠি দিয়ে (ICMP fragmentation needed)। প্রেরক পরের বার ছোট করে পাঠায় = **PMTUD**।
- **ICMP block** = প্রহরীর চিঠি পথে ফেলে দেওয়া। প্রেরক কিছু জানে না, বারবার একই বড় মাল পাঠায়, প্রতিবার নিঃশব্দে হারায় = **PMTUD black hole**।

### Analogy কোথায় মেলে না

- ট্রাক ড্রাইভার রাস্তার সীমা আগে দেখে নিতে পারেন। Network-এ প্রেরক **পথের MTU আগে জানে না** — শুধু নিজের interface-এর MTU জানে; পথের মাঝের সংকীর্ণতা জানে শুধু ICMP-এর মাধ্যমে।
- IPv6-এ পথের router **কখনো fragment করে না** — সবসময় "Packet Too Big" ফেরত পাঠায়। তাই IPv6-এ PMTUD বাধ্যতামূলক, এবং ICMPv6 block আরো মারাত্মক।
- ছোট মাল (TCP handshake, ছোট HTTP request) সবসময় পৌঁছায় — তাই সমস্যা "আংশিক" দেখায়, পুরো রাস্তা বন্ধ মনে হয় না।

## 5. Real-world engineering scenario — VPN-এ "অর্ধেক কাজ করে"

**পরিস্থিতি:** Office-এর WireGuard VPN দিয়ে developer-রা internal service-এ যান। Health check (`/healthz`, ছোট JSON) কাজ করে, SSH login হয়, কিন্তু: `git clone` মাঝপথে ঝুলে থাকে, dashboard-এর বড় page খোলে না, `scp` ০% এ আটকে থাকে।

**Diagnosis:**

1. ছোট কাজ করে, বড় না → **MTU সন্দেহ** (প্রথম প্রশ্ন সবসময় এটাই হওয়া উচিত)।
2. DF সহ বিভিন্ন আকারে ping (VPN-এর ভেতর দিয়ে):

   ```bash
   ping -M do -s 1472 -c 2 10.8.0.1    # 100% loss, কোনো ICMP error-ও নেই
   ping -M do -s 1392 -c 2 10.8.0.1    # কাজ করে
   tracepath 10.8.0.1                  # pmtu দেখায় (ICMP চললে)
   ```

3. দেখা গেল: Client-এর WireGuard interface-এ কেউ MTU **১৫০০** set করেছিলেন (default 1420-এর বদলে)। আর VPN server-এর সামনের cloud firewall/security group-এ **সব ICMP block** — তাই "fragmentation needed" কখনো client-এ পৌঁছায় না। TCP বড় segment পাঠায়, সেগুলো পথে drop হয়, retransmit-ও একই আকারের → black hole।

**সমাধান (দুটিই):**

- Interface MTU ঠিক করা: `MTU = 1420` (WireGuard config), বা হিসাব করে (`mtu_calc.py tunnel`)।
- ICMP type 3 code 4 (IPv6: type 2) **allow** করা — PMTUD-এর জন্য অত্যাবশ্যক।
- অতিরিক্ত নিরাপত্তা জাল: router/firewall-এ **MSS clamping** — SYN-এর MSS-কে পথের MTU অনুযায়ী কমিয়ে দেওয়া (nftables-এ `tcp option maxseg size set rt mtu`) — L02-10।

**শিক্ষা:** "ছোট কাজ করে, বড় ঝোলে" = MTU, যতক্ষণ না অন্য কিছু প্রমাণ হয়। এবং "সব ICMP block" একটি নিরাপত্তা নীতি নয়, একটি bug।

## 6. Diagram — PMTUD

```text
Host A (MTU 1500)          Router R1              Router R2 (পরের link MTU 1400)        Host B
     │── 1500, DF=1 ─────────►│── 1500 ─────────────►│  ✗ আঁটবে না
     │                        │                      │
     │◄──────── ICMP type 3 code 4 "Frag needed, next-hop MTU 1400" ─┘
     │ (kernel route cache-এ PMTU 1400 মনে রাখে)
     │── 1400, DF=1 ─────────►│── 1400 ─────────────►│── 1400 ──────────────────────────►│ ✓

ICMP block হলে:
     │── 1500, DF=1 ─────────►│── 1500 ─────────────►│  ✗ drop ── ICMP ──► 🔥 firewall-এ drop
     │   ... timeout ... retransmit 1500 ... drop ... (black hole)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| DHCP / DORA | স্বয়ংক্রিয় IP configuration / Discover-Offer-Request-Ack |
| Lease, T1, T2 | ধারের মেয়াদ, নবায়নের সময় (৫০%, ৮৭.৫%) |
| DHCP relay | অন্য subnet-এর server-এ DHCP পৌঁছে দেয় (broadcast router পার হয় না) |
| Static / reserved IP | Server-এর জন্য নির্দিষ্ট IP (MAC অনুযায়ী reservation) |
| ICMP / ICMPv6 | Network-এর error ও diagnostic বার্তা |
| TTL | Hop সীমা; শূন্য হলে time exceeded |
| MTU | Link-এ সর্বোচ্চ IP packet-এর আকার |
| MSS | TCP segment-এ সর্বোচ্চ data |
| DF bit | Don't Fragment |
| Fragmentation | বড় IPv4 packet টুকরো করা |
| PMTUD | ICMP-এর মাধ্যমে পথের সর্বনিম্ন MTU খোঁজা |
| PLPMTUD | ICMP ছাড়াই probe করে খোঁজা (RFC 8899; packetization layer) |
| Black hole | ICMP drop হওয়ায় বড় packet নিঃশব্দে হারায় |
| MSS clamping | পথের router SYN-এর MSS কমিয়ে দেয় |
| Jumbo frame | ১৫০০-এর বেশি MTU (যেমন ৯০০১) |
| Overlay network | Tunnel দিয়ে তৈরি virtual network (VXLAN) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Ubuntu-তে DHCP

- Ubuntu Server: **netplan** configuration (`/etc/netplan/*.yaml`) → **systemd-networkd** DHCP client চালায়। Desktop: NetworkManager।
- দেখা: `networkctl status ens3` (address, gateway, DNS, lease); `ip addr` — `dynamic` ও `valid_lft` (lease-এর বাকি সময়)।
- Cloud VM-ও DHCP দিয়ে IP পায় — cloud-এর DHCP server আপনার জন্য নির্দিষ্ট private IP দেয়। VM-এর ভেতরে "static IP" hard-code করলে cloud-এর ধারণার সাথে অমিল হতে পারে — cloud console/API-তে configure করুন।

> **Fedora-তে:** server ও desktop দুটোতেই NetworkManager — `nmcli device show`, `nmcli connection show`। Netplan default নয়।

### 8.2 IPv4 fragmentation

Router packet টুকরো করে যদি DF না থাকে। প্রতিটি fragment-এ নিজস্ব IP header; offset ৮-byte এককে, তাই শেষটি ছাড়া প্রতিটির data ৮-এর গুণিতক। গন্তব্য host জোড়া দেয়। সমস্যা:

- একটি fragment হারালে পুরো packet নষ্ট — loss বাড়ে।
- শুধু প্রথম fragment-এ TCP/UDP port থাকে — firewall ও load balancer বিভ্রান্ত হয়।
- Reassembly-তে memory; fragment-ভিত্তিক আক্রমণের ইতিহাস।

তাই আধুনিক TCP stack সবসময় **DF set** করে এবং PMTUD-এর উপর নির্ভর করে। Fragmentation-এর প্রধান শিকার এখন UDP (বড় DNS উত্তর — L02-06-এর TCP fallback-এর কারণ)।

### 8.3 Linux-এ PMTU

- ICMP "frag needed" পেলে kernel ঐ গন্তব্যের জন্য PMTU cache করে: `ip route get 1.1.1.1` → `cache expires ... mtu 1400`।
- `net.ipv4.tcp_mtu_probing` (0 = বন্ধ, 1 = black hole সন্দেহ হলে probe) — ICMP ছাড়াই উদ্ধারের একটি উপায়।
- Interface MTU: `ip link show` (`mtu 1500`), সাময়িক পরিবর্তন `sudo ip link set dev eth0 mtu 1450` (⚠️ remote machine-এ ভুল মান দিলে নিজেকে বিচ্ছিন্ন করতে পারেন — console access রাখুন), স্থায়ী: netplan-এ `mtu:`।

### 8.4 Cloud ও container

- AWS: একই VPC-র ভেতরে instance-এর MTU সাধারণত **৯০০১** (jumbo); Internet gateway, VPN, অনেক peering-এ ১৫০০ বা কম — একই instance থেকে দুই দিকে দুই MTU, PMTUD-এর উপর নির্ভরশীল। Security group-এ ICMP "fragmentation needed" allow করার পরামর্শ AWS documentation-এ আছে।
- Docker bridge-এর MTU default ১৫০০; host-এর MTU কম হলে (VPN-এর ভেতরের VM) container-এ black hole — Docker daemon-এ `mtu` সেট করতে হয় (Module 10)।
- Kubernetes CNI (VXLAN overlay) pod-এর MTU কমিয়ে দেয় (১৪৫০ ইত্যাদি) — CNI-তে ভুল হলে Section 5-এর মতো symptom (Module 14)।

## 9. Practical demonstration

File: [`code/L02-09/mtu_calc.py`](code/L02-09/mtu_calc.py) — শুধু হিসাব, packet পাঠায় না।

### 9.1 হিসাব

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-09
python3 mtu_calc.py mss
python3 mtu_calc.py ping-size
python3 mtu_calc.py tunnel vxlan wireguard4
python3 mtu_calc.py fragment --size 3000
python3 mtu_calc.py pmtud --path 1500,1500,1400,1500
python3 mtu_calc.py lease 86400
```

**আসল output:**

```text
ipv4: MSS 1460  (with TCP timestamps: 1448 data/segment)
ipv6: MSS 1440  (with TCP timestamps: 1428 data/segment)

Linux:   ping -M do -s 1472 HOST
IPv6:    ping -6 -M do -s 1452 HOST
Windows: ping -f -l 1472 HOST

 1500 - vxlan      (50 bytes) = 1450
 1450 - wireguard4 (60 bytes) = 1390
inner MTU 1390  → TCP MSS 1350  → max ping -s 1362

ICMP payload 3000 + header 8 = 3008 bytes over MTU 1500:
  offset     0 (field    0)  data  1480  packet  1500  MF=1
  offset  1480 (field  185)  data  1480  packet  1500  MF=1
  offset  2960 (field  370)  data    48  packet    68  MF=0
3 fragment(s); losing any one loses the whole packet

hops [1500, 1500, 1400, 1500] → path MTU 1400 (found with 14 DF probes; true 1400)

lease 86400s: T1 renew at 43200s, T2 rebind at 75600s, expire at 86400s
```

- VXLAN overlay-এর ভেতরে WireGuard (যেমন Kubernetes-এ encrypted CNI) → মাত্র ১৩৯০।
- `ping -s 3000` = তিনটি fragment; MF (more fragments) flag শেষটিতে ০। IP header-এর offset field ৮-byte এককে (১৪৮০ / ৮ = ১৮৫)।
- PMTUD simulation: binary search-এ ১৪টি probe। `tracepath` একই ধারণা ব্যবহার করে, তবে ICMP-এর দেওয়া next-hop MTU পেলে সরাসরি সেটাই নেয়।

### 9.2 আসল path MTU — একটি বাস্তব আবিষ্কার

এই lesson লেখার সময় লেখকের home network থেকে (Windows, Wi-Fi interface MTU ১৫০০) ১.১.১.১-এ DF সহ ping চালানো হয়েছিল। **আসল output (২০২৬-১০-২৬):**

```text
> ping -n 1 -f -l 1472 1.1.1.1
Pinging 1.1.1.1 with 1472 bytes of data:
Reply from 192.168.0.1: Packet needs to be fragmented but DF set.

> ping -n 1 -f -l 1400 1.1.1.1
Reply from 1.1.1.1: bytes=1400 time=10ms TTL=59
```

Interface ১৫০০ হলেও **home router (১৯২.১৬৮.০.১) নিজেই** ICMP "fragmentation needed" ফেরত পাঠিয়েছে — অর্থাৎ router-এর WAN দিকের MTU ছোট। এরপর একটি shell loop দিয়ে binary search (১৪০০–১৪৬৪-এর মধ্যে, ৬টি probe):

```text
largest DF payload=1452 probes=6 path_mtu=1480
Reply from 1.1.1.1: bytes=1452 time=8ms TTL=59
Packet needs to be fragmented but DF set.                    ← 1453
1480 1.1.1.1                                       192.168.0.1   ← Windows destination cache (netsh)
```

**Path MTU = ১৪৫২ + ২০ + ৮ = ১৪৮০।** Windows নিজেও router-এর ICMP থেকে ১৪৮০ শিখে cache করেছে (`netsh interface ipv4 show destinationcache`) — **PMTUD নিজের চোখে কাজ করতে দেখা।** ১৫০০ − ১৪৮০ = ২০ byte — ISP-এর দিকে কোনো encapsulation (যেমন একটি অতিরিক্ত IPv4 header-এর tunnel) থাকতে পারে; নিশ্চিত কারণ ISP-ই জানে। গুরুত্বপূর্ণ বিষয়: এই network-এ ICMP চলছে বলে TCP নিজে মানিয়ে নেয় — কোনো user কিছু টের পান না। ICMP block থাকলে একই network-এ Section 5-এর symptom দেখা দিত।

**আপনার network-এ ফল ভিন্ন হবে** — ১৫০০ (সাধারণ), ১৪৯২ (PPPoE), বা অন্য কিছু।

### 9.3 Linux-এ একই পরীক্ষা (Ubuntu VM)

```bash
ip link show                               # interface MTU
ping -M do -s 1472 -c 2 1.1.1.1            # DF সহ (Linux syntax)
ping -M do -s 1473 -c 2 1.1.1.1            # "message too long" বা ICMP error
tracepath -n 1.1.1.1                       # প্রতিটি hop ও pmtu
ip route get 1.1.1.1                       # PMTU cache থাকলে "mtu 1480" দেখাবে
networkctl status                          # DHCP থেকে পাওয়া address, gateway, DNS
ip -4 addr show dynamic                    # valid_lft = lease-এর বাকি সময়
sudo tcpdump -ni any icmp                  # অন্য terminal-এ — ICMP বার্তা নিজের চোখে (L02-15)
```

DHCP DORA দেখতে (VM-এ, নিজের lab network-এ):

```bash
sudo tcpdump -ni any -vv port 67 or port 68
# অন্য terminal-এ: sudo networkctl renew ens3    (Ubuntu, systemd-networkd)
```

> **Fedora-তে:** `sudo nmcli connection down ID && sudo nmcli connection up ID` দিয়ে নতুন lease (⚠️ remote session-এ নিজেকে বিচ্ছিন্ন করবেন — শুধু console বা local VM-এ)।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_mtu_calc.py`](code/L02-09/test_mtu_calc.py)-এর ৭টি test: MSS ও ping আকার (১৫০০, AWS ৯০০১), tunnel stack (WireGuard ১৪২০, VXLAN+WireGuard ১৩৯০), fragmentation offset ও ৮-byte alignment, PMTUD search ও "সব ICMP block" ত্রুটি, DHCP T1/T2, CLI।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `TUNNELS` dict | প্রতিটি encapsulation-এর overhead | হিসাব এক জায়গায়, মন্তব্যে ভাঙানো |
| `inner_mtu(stack)` | Tunnel-এর ভেতরে tunnel | বাস্তবে layer জমে (overlay + VPN) |
| `fragments` `// 8 * 8` | Data ৮-এর গুণিতক | IPv4 offset field ৮-byte এককে |
| `pmtud_search(probe)` | Probe function নেয় | Simulation ও আসল ping দুটোতেই একই algorithm (Exercise ২) |
| `probe(lo)` আগে | নিম্নসীমাও ব্যর্থ হলে error | "সব হারাচ্ছে" = MTU নয়, অন্য সমস্যা |
| `lease_timers` | RFC 2131-এর default অনুপাত | DHCP server option দিয়ে বদলানো যায় |

**Python কেন এখানে, কোথায় নয়:** হিসাব ও পরিকল্পনায় (overlay/VPN design) পুনরাবৃত্তিযোগ্য ও testable। আসল packet probe-এ `ping`, `tracepath` — raw ICMP socket-এ root লাগে।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `ping -M do -s 1472` (সাধারণ Ethernet) | Reply; ১৪৭৩-এ error |
| `tracepath` | শেষে `pmtu 1500` (বা আপনার path-এর মান) |
| `networkctl status` | DHCP-র address, gateway, DNS |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| ছোট request কাজ করে, বড় ঝোলে | MTU/PMTUD black hole | DF ping বিভিন্ন আকারে | Interface MTU ঠিক; ICMP frag-needed allow; MSS clamping |
| VPN/overlay-এ উপরের মতো | Tunnel overhead হিসাব হয়নি | `ip link` MTU বনাম `mtu_calc.py tunnel` | সঠিক MTU |
| Container-এ, host-এ নয় | Docker bridge ১৫০০, host কম | Container-এর ভেতরে `ip link` | Docker `mtu` |
| IP নেই (169.254.x.x বা কিছুই না) | DHCP server-এ পৌঁছায় না | `tcpdump port 67 or 68` | Server, relay, VLAN (L02-02) |
| একই IP দুই machine-এ | Static IP DHCP pool-এর ভেতরে | `ip neigh` / ARP conflict | Pool-এর বাইরে বা reservation |
| `ping` চলে না কিন্তু service চলে | ICMP echo block | TCP দিয়ে পরীক্ষা (`curl`, `nc -zv`) | নীতি জানুন — `ping` ব্যর্থতা মানেই host বন্ধ নয় |
| `traceroute`-এ `* * *` | Router time-exceeded পাঠায় না/block | অন্য hop ঠিক থাকলে স্বাভাবিক | সাধারণত সমস্যা নয় |

## 13. Security, performance ও cost বিবেচনা

- **Security:** "সব ICMP block" করবেন না — echo (ping) block করা নীতিগত বিষয়, কিন্তু **frag-needed/packet-too-big ও time-exceeded allow করুন**; ICMPv6-এর প্রয়োজনীয় type সবসময় allow (RFC 4890 নির্দেশিকা)। ICMP redirect গ্রহণ বন্ধ (`net.ipv4.conf.all.accept_redirects=0`)। Rogue DHCP server (ভুল gateway/DNS দিয়ে traffic চুরি) — switch-এ DHCP snooping; cloud-এ provider নিয়ন্ত্রণ করে।
- **Performance:** বড় MTU (jumbo) = কম header overhead ও কম packet প্রতি সেকেন্ড — একই VPC-র ভেতরে throughput বাড়ে; কিন্তু path-এর সবখানে সমর্থন না থাকলে PMTUD-এর উপর নির্ভর। Fragmentation loss ও CPU বাড়ায়।
- **Cost:** সরাসরি নয়; কিন্তু MTU black hole debug করতে প্রায়ই ঘণ্টার পর ঘণ্টা engineer-সময় যায় — symptom চেনাই সবচেয়ে বড় সাশ্রয়।

## 14. Hands-on exercise

1. নিজের network-এ Section 9.2-এর পরীক্ষা Ubuntu-তে (`ping -M do`) — path MTU কত? `tracepath` একই মান দেয়?
2. `pmtud_search`-কে আসল `ping`-এর সাথে যুক্ত করুন: `probe = lambda s: subprocess.run(["ping","-M","do","-c","1","-W","1","-s",str(s-28),host]).returncode == 0`। Simulation ও আসল ফল তুলনা করুন।
3. দুটি network namespace ও veth pair দিয়ে (L02-13-এর preview; শুধু lab VM-এ) একদিকে MTU ১৪০০ set করে black hole তৈরি ও `tcp_mtu_probing=1` দিয়ে উদ্ধার পরীক্ষা করুন।
4. `sudo tcpdump -ni any port 67 or port 68` চালিয়ে VM-এর DHCP renew-এর DORA (বা শুধু Request/Ack — renew-এ Discover হয় না কেন?) লিখুন।
5. নিজের Kubernetes/Docker সেটআপের (থাকলে) interface-গুলোর MTU-র একটি তালিকা — কোনগুলো ১৫০০-এর কম এবং কেন?

## 15. Mini-project — MTU doctor

একটি script: (১) সব interface-এর MTU (`ip -j link` JSON) পড়বে, (২) একটি host-এর path MTU আসল DF ping-এ binary search করবে (Exercise ২), (৩) interface MTU > path MTU হলে ও tunnel interface (wg*, vxlan*, tun*) থাকলে `mtu_calc.py`-এর হিসাব দিয়ে সুপারিশ দেবে, (৪) `ip route get`-এ cached PMTU দেখাবে। Exit ১ যদি অমিল পায়। L02-16-এর troubleshooting toolkit-এ এটি যোগ হবে।

## 16. Interview প্রশ্ন

1. DHCP-র DORA প্রক্রিয়া ব্যাখ্যা করুন। Lease নবায়ন কখন হয়?
2. MTU ও MSS-এর পার্থক্য কী? ১৫০০ MTU-তে MSS কত?
3. Path MTU Discovery কীভাবে কাজ করে এবং black hole কী?
4. "Small requests work, large ones hang" — কীভাবে debug করবেন?
5. সব ICMP block করা কেন খারাপ ধারণা?
6. VXLAN overlay-তে MTU কেন কমে? কত?
7. IPv6-এ fragmentation কীভাবে আলাদা?

## 17. Self-assessment প্রশ্ন

1. সুড়ঙ্গ analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ দুটি ভুল একসাথে ঘটেছিল — কী কী?
3. Section 9.2-এ path MTU ১৪৮০ কীভাবে বের হলো? Windows কোথা থেকে মানটি শিখল?
4. `ping -s 3000` কেন তিনটি fragment এবং শেষটি ৪৮ byte?
5. DHCP Request কেন broadcast?

## 18. সংক্ষিপ্ত সারাংশ

- DHCP = DORA; lease, T1 (৫০%), T2 (৮৭.৫%); IP-র সাথে gateway, DNS, MTU দেয়।
- ICMP = network-এর বার্তা: echo, unreachable, time exceeded, **frag needed**।
- MTU ১৫০০ → MSS ১৪৬০ → ping `-s` ১৪৭২; tunnel overhead বাদ (VXLAN ৫০, WireGuard ৬০/৮০)।
- PMTUD ICMP-এর উপর নির্ভর করে — ICMP block = black hole: "ছোট চলে, বড় ঝোলে"।
- Diagnosis: `ping -M do -s`, `tracepath`, `ip route get`; সমাধান: সঠিক MTU, ICMP allow, MSS clamping।

## 19. Completion checklist

- [ ] নিজের network-এর path MTU বের করেছি
- [ ] `mtu_calc.py` দিয়ে নিজের ব্যবহৃত tunnel-এর MTU হিসাব করেছি
- [ ] `tcpdump` দিয়ে DHCP ও ICMP বার্তা দেখেছি
- [ ] "ছোট চলে, বড় ঝোলে" symptom-এর তিনটি কারণ ও সমাধান বলতে পারি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 2131 — DHCP: https://www.rfc-editor.org/rfc/rfc2131
- RFC 792 — ICMP: https://www.rfc-editor.org/rfc/rfc792
- RFC 1191 — Path MTU Discovery: https://www.rfc-editor.org/rfc/rfc1191
- RFC 8201 — Path MTU Discovery for IPv6: https://www.rfc-editor.org/rfc/rfc8201
- RFC 8899 — Packetization Layer PMTUD: https://www.rfc-editor.org/rfc/rfc8899
- RFC 4890 — ICMPv6 filtering recommendations: https://www.rfc-editor.org/rfc/rfc4890
- Netplan documentation: https://netplan.readthedocs.io/
- AWS — Network MTU for EC2 instances: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/network_mtu.html

---

**পরের lesson:** L02-10 — Firewall: nftables, ufw (Fedora-তে firewalld), security group ও NACL
