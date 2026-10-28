# L02-04 — Routing table, gateway ও NAT

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L02-03 — IPv4, IPv6, CIDR](L02-03-ip-addressing-cidr.md) |
| **Label** | ⚠️ route পরিবর্তন network বিচ্ছিন্ন করতে পারে — VM console হাতে রাখুন |
| **Tested** | `route_nat.py`: ৭টি test পাস; `lookup` ও `nat` নমুনায় চালানো (Python 3.14, Windows)। চালাতে গিয়ে দুটি সমস্যা ধরা ও ঠিক: Windows-এ stderr-এর encoding, এবং tunnel interface-এ ভুল "ARP" শব্দ। নমুনা `ip route` হাতে তৈরি। `ip route get/add`, `conntrack`, `nft` NAT **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- **Routing table** — kernel কীভাবে ঠিক করে একটি packet কোন দিকে যাবে।
- **Longest prefix match** ও **metric**; **default route** ও **gateway**।
- `ip route`, `ip route get` দিয়ে সিদ্ধান্ত দেখা; অস্থায়ী route যোগ।
- Linux-কে **router** বানানো (`ip_forward`)।
- **NAT**: SNAT/masquerade (ভেতর থেকে বাইরে), DNAT/port forwarding (বাইরে থেকে ভেতরে), **connection tracking**।
- **Port exhaustion** ও cloud NAT gateway।
- Python দিয়ে route lookup ও NAT translation table simulation।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L02-03-এ subnet শিখলেন। কিন্তু একটি packet একটি subnet থেকে আরেকটিতে, বা internet-এ যাবে কীভাবে? প্রতিটি host ও router-কে একটি সিদ্ধান্ত নিতে হয়: "এই গন্তব্যের জন্য কোন interface দিয়ে, কাকে (next hop) পাঠাবো?" — এই সিদ্ধান্তের নিয়মই **routing table**।

আর একটি সমস্যা: private IP (`10.x`, `192.168.x`) internet-এ route হয় না। তাহলে আপনার laptop বা cloud-এর private server internet-এ যায় কীভাবে? **NAT** — পথে private ঠিকানা public ঠিকানায় বদলে দেওয়া।

DevOps-এ: "server internet-এ যেতে পারে না" (NAT gateway/route নেই), "VPN চালু করলে অন্য সব বন্ধ" (default route বদলে গেছে), "container বাইরে যেতে পারে না" (ip_forward/masquerade), "অনেক connection-এ মাঝে মাঝে timeout" (NAT port exhaustion) — সব এই lesson-এর বিষয়।

## 3. সহজ ভাষায় পরিচয়

**Routing table**-এর প্রতিটি লাইন: "এই গন্তব্য-range → এই interface দিয়ে → (ঐচ্ছিক) এই gateway-কে দাও"।

```text
default via 10.0.2.2 dev enp0s3 metric 100        ← বাকি সব কিছু (0.0.0.0/0)
10.0.2.0/24 dev enp0s3 proto kernel scope link    ← সরাসরি যুক্ত subnet (gateway নেই)
10.8.0.0/16 via 192.168.56.254 dev enp0s8         ← নির্দিষ্ট network অন্য router দিয়ে
```

**নিয়ম ১ — longest prefix match:** একাধিক route মিললে সবচেয়ে **নির্দিষ্ট** (বড় `/n`) জেতে। `10.8.4.9` `/16` ও `/24` দুটোতেই পড়লে `/24` জেতে।

**নিয়ম ২ — metric:** একই prefix-এর একাধিক route থাকলে কম metric জেতে (যেমন দুটি default route — Ethernet ও Wi-Fi)।

**Default gateway:** "অন্য কোথাও না মিললে এখানে দাও" — সাধারণত router, যে internet চেনে।

**NAT (Network Address Translation):**

| ধরন | কোথায় | কী বদলায় | উদাহরণ |
|---|---|---|---|
| **SNAT / masquerade** | ভেতর থেকে বাইরে | Source IP (ও port) → public | বাড়ির router, cloud NAT gateway, Docker container-এর internet |
| **DNAT / port forwarding** | বাইরে থেকে ভেতরে | Destination IP/port → private | Router-এর port ৮০ → ভেতরের server; Docker `-p 8080:80` |

NAT-এর পেছনে **connection tracking (conntrack)**: kernel মনে রাখে কোন ভেতরের connection কোন বাইরের port-এ map হয়েছে, যাতে উত্তর ফিরে সঠিক host-এ যায়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের ডাক বিভাগ ও রিসেপশন

- **Routing table** = ডাক বিভাগের দেয়ালে টাঙানো নির্দেশ: "চট্টগ্রাম → বাস ১; চট্টগ্রাম-আগ্রাবাদ → বিশেষ কুরিয়ার; বাকি সব → প্রধান ডাকঘর"। সবচেয়ে নির্দিষ্ট নির্দেশ আগে দেখা হয়।
- **Default gateway** = "প্রধান ডাকঘর" — যা জানা নেই তা সেখানে।
- **SNAT** = অফিসের সব চিঠি বাইরে যায় **অফিসের ঠিকানায়** (প্রেরকের নিজের ডেস্ক নম্বর নয়), রিসেপশনিস্ট খাতায় লেখেন কোন চিঠি কার। উত্তর এলে খাতা দেখে সঠিক ডেস্কে পাঠান।
- **DNAT** = বাইরের কেউ "অফিসের অভিযোগ বিভাগ"-এ লিখলে রিসেপশন নির্দিষ্ট ডেস্কে পাঠায়।

### Analogy কোথায় মেলে না

- রিসেপশনিস্টের খাতা অসীম লম্বা হতে পারে। NAT-এর **port সংখ্যা সীমিত** (প্রতি public IP ও গন্তব্যে ~৬৪,০০০), আর conntrack table-এর আকারও সীমিত — অনেক connection-এ নতুন connection ব্যর্থ হয় (Section 5)।
- খাতায় না থাকা অযাচিত চিঠিও রিসেপশন হয়তো খুলে দেখেন। NAT-এ table-এ না থাকা **অযাচিত inbound packet সাধারণত drop হয়** — এটি পার্শ্বফল হিসেবে কিছুটা সুরক্ষা দেয়, কিন্তু NAT **firewall নয়** (L02-10)।
- ডাক বিভাগের নির্দেশ মানুষ বিবেচনা করে পড়েন। Kernel শুধু নিয়ম মানে: ভুল route যোগ করলে (যেমন VPN-এর `/1` route) চুপচাপ সব traffic ভুল দিকে যায়।

## 5. Real-world engineering scenario — "মাঝে মাঝে বাইরের API-তে timeout"

**পরিস্থিতি:** Private subnet-এর ৫০টি worker একটি NAT gateway দিয়ে একটি বাইরের payment API (`203.0.113.80:443`)-তে প্রচুর ছোট connection খোলে। Peak সময়ে কিছু request "connection timeout"; API provider বলছে তারা কিছুই পাচ্ছে না।

**কারণ:** NAT gateway-এর একটি public IP থেকে একই গন্তব্য IP:port-এ একসাথে যত connection সম্ভব, তা **source port**-এর সংখ্যায় সীমিত। প্রতিটি connection শেষ হলেও কিছুক্ষণ (TIME_WAIT, L02-05) port ধরে রাখে। নতুন connection-এর জন্য port না পেলে drop — **SNAT port exhaustion**।

এই lesson-এর simulation (মাত্র ৪টি port দিয়ে ব্যাপারটি দেখানো):

```text
192.168.1.10:51000 → 93.184.215.14:443  becomes  203.0.113.7:61000 → ...
...
192.168.1.12:40000 → 203.0.113.80:443  becomes  203.0.113.7:61003 → ...
ERROR NAT port exhaustion: no free port for 192.168.1.13:40001 → 203.0.113.80:443
```

**সমাধান:** connection **পুনর্ব্যবহার** (HTTP keep-alive / connection pool — L01-14-এর fd leak-এর আত্মীয়), NAT gateway-এ আরো public IP, বা গন্তব্য service-এ private connectivity। Cloud NAT gateway-এর নির্দিষ্ট সীমা ও metric (যেমন port allocation error) provider-এর documentation-এ আছে — Module 08।

**Diagnosis:** NAT gateway-এর error metric; host-এ `ss -tan state time-wait | wc -l` (L02-05); application-এ connection pool ব্যবহার হচ্ছে কিনা।

## 6. Diagram

### Routing সিদ্ধান্ত (host-এ)

```text
 packet → dst 10.8.4.9
          │
          ▼  routing table-এ সব মিল খোঁজো
   0.0.0.0/0     ✓ (/0)
   10.8.0.0/16   ✓ (/16)
   10.8.4.0/24   ✓ (/24)   ← longest prefix → জেতে
          │
          ▼
   dev wg0, gateway নেই (on-link) → wg0 interface দিয়ে পাঠাও
```

### SNAT ও reply পথ

```text
 192.168.1.10:51000 ─► [NAT gateway / router]  ─► internet ─► 93.184.215.14:443
   src 192.168.1.10:51000    rewrite src → 203.0.113.7:61000
                             conntrack: (192.168.1.10:51000 ↔ 61000, dst 93.184.215.14:443)
 reply:  93.184.215.14:443 → 203.0.113.7:61000
                             conntrack lookup → dst rewrite → 192.168.1.10:51000
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Routing table | গন্তব্য-range → interface/next hop-এর নিয়ম |
| Next hop / gateway | পরের router |
| Default route | `0.0.0.0/0` — অন্য কিছু না মিললে |
| Longest prefix match | সবচেয়ে নির্দিষ্ট route জেতে |
| Metric | একই prefix-এ অগ্রাধিকার (কম = ভালো) |
| On-link / directly connected | Gateway ছাড়া সরাসরি |
| `ip_forward` | Linux অন্যের packet এক interface থেকে অন্যটিতে পাঠাবে কিনা |
| Blackhole route | Packet নীরবে ফেলে দেওয়া |
| Policy routing | Source বা mark অনুযায়ী আলাদা routing table (`ip rule`) |
| SNAT / masquerade | Source ঠিকানা বদল (masquerade = interface-এর বর্তমান IP) |
| DNAT / port forwarding | Destination ঠিকানা বদল |
| conntrack | Kernel-এর connection tracking table |
| Port exhaustion | NAT-এর ব্যবহারযোগ্য source port শেষ |
| Asymmetric routing | যাওয়া ও আসার পথ আলাদা — stateful firewall/NAT ভাঙে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Linux route lookup

Kernel প্রতিটি বাইরে যাওয়া packet-এর জন্য (cache সহ) routing table-এ longest prefix match করে। নির্দিষ্ট গন্তব্যের জন্য kernel-এর আসল সিদ্ধান্ত দেখার সবচেয়ে নির্ভরযোগ্য উপায়:

```bash
ip route get 8.8.8.8
```

উদাহরণ: `8.8.8.8 via 10.0.2.2 dev enp0s3 src 10.0.2.15 uid 1000` — কোন gateway, কোন interface, কোন **source IP** ব্যবহার হবে। এই lesson-এর Python `lookup` একই নিয়ম অনুকরণ করে (policy routing ছাড়া)।

### 8.2 Linux-কে router বানানো

ডিফল্টভাবে Linux অন্যের packet forward করে না (নিরাপত্তা)। Router/NAT gateway বানাতে:

```bash
sysctl net.ipv4.ip_forward                  # 0 = বন্ধ
sudo sysctl -w net.ipv4.ip_forward=1        # ⚠️ অস্থায়ী (reboot-এ ফেরে)
```

স্থায়ী: `/etc/sysctl.d/99-forward.conf`-এ `net.ipv4.ip_forward=1`। Docker নিজে এটি চালু করে — তাই Docker install-এর পরে host forwarding শুরু করে (firewall বিবেচনা, L02-10)।

### 8.3 NAT — nftables দিয়ে (Ubuntu ও Fedora উভয়ে)

```text
table ip nat {
  chain postrouting {
    type nat hook postrouting priority srcnat;
    oifname "enp0s3" ip saddr 192.168.56.0/24 masquerade      # SNAT: ভেতরের subnet → বাইরের interface-এর IP
  }
  chain prerouting {
    type nat hook prerouting priority dstnat;
    iifname "enp0s3" tcp dport 8080 dnat to 192.168.56.20:80   # DNAT: port forwarding
  }
}
```

`postrouting` = route সিদ্ধান্তের পরে (source বদল), `prerouting` = route সিদ্ধান্তের আগে (destination বদল — যাতে বদলানো ঠিকানায় route হয়)। পুরো firewall L02-10-এ।

### 8.4 conntrack-এর সীমা

`/proc/sys/net/netfilter/nf_conntrack_max` — সর্বোচ্চ tracked connection। পূর্ণ হলে kernel log-এ `nf_conntrack: table full, dropping packet` — ব্যস্ত NAT/firewall host-এ পরিচিত incident।

## 9. Practical demonstration (Ubuntu VM — console হাতে রাখুন)

### 9.1 পর্যবেক্ষণ

```bash
ip route
ip -6 route
ip route get 8.8.8.8
ip route get 192.168.56.1
ip rule                                   # policy routing নিয়ম (সাধারণত তিনটি default)
```

### 9.2 Route lookup — Python

File: [`code/L02-04/route_nat.py`](code/L02-04/route_nat.py) · নমুনা: [`sample-routes.txt`](code/L02-04/sample-routes.txt) (দুটি default, VPN `wg0`, docker0, blackhole)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-04
ip -4 route > /tmp/routes.txt
python3 route_nat.py lookup /tmp/routes.txt 8.8.8.8 "$(ip -4 route | awk '/default/ {print $3; exit}')"
python3 route_nat.py lookup sample-routes.txt 8.8.8.8 10.8.4.9 10.8.9.9 192.168.56.77 198.51.100.5
```

**নমুনা দিয়ে আসল output:**

```text
8.8.8.8         → 0.0.0.0/0 dev enp0s3 gateway 10.0.2.2 metric 100
10.8.4.9        → 10.8.4.0/24 dev wg0 on-link (no gateway) metric 0
10.8.9.9        → 10.8.0.0/16 dev enp0s8 gateway 192.168.56.254 metric 0
192.168.56.77   → 192.168.56.0/24 dev enp0s8 on-link (no gateway) metric 0
198.51.100.5    → blackhole via 198.51.100.0/24 (packet dropped)
```

- `8.8.8.8`: দুটি default — metric ১০০ (enp0s3) জিতেছে ২০০-এর উপর।
- `10.8.4.9`: `/24` (wg0, VPN tunnel) জিতেছে `/16`-এর উপর — longest prefix।
- `wg0`-এ "ARP" নেই — tunnel interface L3; প্রথম version-এ tool ভুলভাবে "ARP" লিখেছিল, ঠিক করা হয়েছে।

নিজের machine-এ `ip route get` দিয়ে Python-এর সিদ্ধান্ত মিলিয়ে দেখুন।

### 9.3 অস্থায়ী route (⚠️)

```bash
sudo ip route add 203.0.113.0/24 via "$(ip -4 route | awk '/default/ {print $3; exit}')"
ip route get 203.0.113.5
sudo ip route del 203.0.113.0/24
sudo ip route add blackhole 198.51.100.0/24      # এই range-এ সব কিছু ফেলে দাও
ping -c 1 -W 1 198.51.100.5                      # "Network is unreachable" বা ব্যর্থ
sudo ip route del blackhole 198.51.100.0/24
```

⚠️ কখনো `default` route মুছবেন না SSH-এর মাধ্যমে — connection হারাবেন। `ip` দিয়ে route reboot-এ হারায়; স্থায়ী route Netplan-এ (Ubuntu) বা NetworkManager-এ (Fedora)।

### 9.4 NAT simulation ও আসল conntrack

```bash
python3 route_nat.py nat --public 203.0.113.7 --ports 61000-61003 --flows sample-flows.txt; echo "exit=$?"
```

আসল output Section 5-এ: একই private port (৫১০০০) দুটি ভিন্ন host থেকে ভিন্ন public port পেয়েছে; একই flow দ্বিতীয়বার একই port পেয়েছে; ৪টি port শেষে ৫ম নতুন flow ব্যর্থ — exit 1।

আসল kernel table (Docker বা NAT চালু host-এ):

```bash
sudo apt install -y conntrack
sudo conntrack -L | head
sudo conntrack -C                                 # মোট tracked connection
cat /proc/sys/net/netfilter/nf_conntrack_max
```

> **Fedora-তে:** `sudo dnf install conntrack-tools`। firewalld masquerade: `sudo firewall-cmd --add-masquerade --permanent`।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_route_nat.py`](code/L02-04/test_route_nat.py)-এর ৭টি test: route parse (default, blackhole), longest prefix, metric tie-break, blackhole ও "no route", NAT translation (একই private port ভিন্ন host, একই flow একই port, উত্তরের reverse mapping, অযাচিত inbound drop), port exhaustion, ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `dict(zip(parts[1::2], parts[2::2]))` | `via X dev Y metric Z` জোড়া | `ip route`-এর key-value গঠন; `scope link` জাতীয় অতিরিক্তও নিরাপদে বাদ |
| `min(..., key=(-prefixlen, metric))` | Longest prefix, তারপর কম metric | Kernel-এর মূল নিয়ম |
| `Nat.table` | (src ip, src port, dst) → public port | conntrack-এর মত |
| `Nat.reverse` | (public port, dst) → private | উত্তর ফেরত পাঠানো |
| `free.pop(0)` ও `RuntimeError` | Port pool ও exhaustion | সীমিত resource স্পষ্ট |
| stderr reconfigure | UTF-8 | Windows-এ `→` escape হচ্ছিল — এই repository-তে ধরা পড়েছে |

**সীমাবদ্ধতা:** Policy routing (`ip rule`), multipath, IPv6 ও connection timeout/port পুনর্ব্যবহার simulation-এ নেই।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `ip route get 8.8.8.8` | default gateway দিয়ে |
| Python `lookup` বনাম `ip route get` | একই gateway ও interface |
| Blackhole route-এ ping | ব্যর্থ |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `connect: Network is unreachable` | কোনো মেলা route নেই (default নেই) | `ip route` | Default route/gateway |
| Private server internet-এ যায় না (cloud) | NAT gateway নেই বা route table-এ নেই | Cloud route table | NAT gateway + `0.0.0.0/0` route (Module 08) |
| VPN চালু হলে সব traffic VPN দিয়ে | VPN default বা `/1` route যোগ করেছে | `ip route get 8.8.8.8` | Split tunnel configuration |
| Container বাইরে যেতে পারে না | `ip_forward` বা masquerade নেই, firewall | `sysctl`, `nft list ruleset` | Docker/firewall নিয়ম (Module 10) |
| উত্তর আসে না, packet যায় | Asymmetric routing — উত্তর অন্য পথে | দুই প্রান্তে tcpdump | Route ঠিক করুন |
| `nf_conntrack: table full` | অনেক connection | `conntrack -C`, kernel log | `nf_conntrack_max` বাড়ানো, timeout কমানো, connection reuse |
| বাইরের API-তে মাঝে মাঝে timeout | SNAT port exhaustion | NAT metric, `ss` TIME_WAIT | Connection pool, অতিরিক্ত IP |

## 13. Security, performance ও cost বিবেচনা

- **Security:** NAT firewall নয় — DNAT/port forward দিয়ে খোলা service সরাসরি আক্রমণযোগ্য; IPv6-এ NAT নেই, firewall আবশ্যক। `ip_forward` অপ্রয়োজনে চালু রাখবেন না (host router হয়ে যায়)। Blackhole route দিয়ে আক্রমণকারী range দ্রুত বন্ধ করা যায়।
- **Performance:** conntrack ও NAT-এ CPU ও memory; অনেক ছোট connection-এর বদলে keep-alive।
- **Cost:** Cloud NAT gateway-এ ঘণ্টা ও **প্রতি GB processing** — অনেক data NAT দিয়ে গেলে বড় বিল; S3-এর মত service-এ VPC endpoint দিয়ে NAT এড়ানো যায় (Module 08, 29)।

## 14. Hands-on exercise

1. `ip route get`-এ তিনটি ভিন্ন গন্তব্য (local, gateway, internet) — প্রতিটির `src` IP কী?
2. নিজের routing table-এ আরেকটি default route (বেশি metric) যোগ করে `ip route get` দিয়ে দেখুন কোনটি ব্যবহার হয়; তারপর মুছুন।
3. `route_nat.py lookup`-এ IPv6 support যোগ করুন (`ip -6 route`)। Test লিখুন।
4. দুটি VM থাকলে একটিকে router বানান: `ip_forward` + nftables masquerade; দ্বিতীয়টির default gateway প্রথমটি — দ্বিতীয়টি internet-এ যেতে পারে কিনা যাচাই করুন (⚠️ VM-only, পরে সব ফিরিয়ে আনুন)।
5. `Nat`-এ connection শেষ হলে port ফেরত (`close()`) যোগ করে দেখুন exhaustion কীভাবে বদলায়।

## 15. Mini-project — "internet নেই" runbook

[Runbook template](../templates/runbook-template.md)-এ "Server cannot reach the internet" runbook-এর খসড়া: DNS (L02-06) বনাম routing আলাদা করা (`ping 1.1.1.1` বনাম `ping example.com`), `ip route get`, gateway-এর ARP (L02-02), firewall (L02-10), cloud route table ও NAT gateway, conntrack। Module 08-এ cloud অংশ সম্পূর্ণ হবে।

## 16. Interview প্রশ্ন

1. Longest prefix match কী? একটি উদাহরণ দিন।
2. Default gateway কী? না থাকলে কী হয়?
3. `ip route get` কী দেখায় এবং কেন দরকারি?
4. SNAT ও DNAT-এর পার্থক্য কী?
5. NAT কি firewall? কেন বা কেন নয়?
6. SNAT port exhaustion কী এবং কীভাবে ঠিক করবেন?
7. Private subnet-এর server কীভাবে internet-এ যায় (cloud-এ)?

## 17. Self-assessment প্রশ্ন

1. ডাক বিভাগ analogy কোথায় মেলে না?
2. নমুনায় `10.8.4.9` কেন wg0-এ গেল?
3. দুটি default route-এর মধ্যে কোনটি এবং কেন?
4. NAT reply পথে কীভাবে সঠিক host-এ পৌঁছায়?
5. `postrouting` ও `prerouting`-এ কোন NAT এবং কেন?
6. Section 5-এর তিনটি সমাধান।

## 18. সংক্ষিপ্ত সারাংশ

- Routing table: গন্তব্য → interface/gateway; **longest prefix**, তারপর **metric**; default = শেষ ভরসা।
- `ip route get` = kernel-এর আসল সিদ্ধান্ত।
- Router হতে `ip_forward`; NAT: **SNAT/masquerade** (বাইরে যাওয়া), **DNAT** (port forwarding); **conntrack** মনে রাখে।
- NAT firewall নয়; port ও conntrack সীমিত — exhaustion; connection reuse।

## 19. Completion checklist

- [ ] `ip route`, `ip route get`, `ip rule` পড়েছি
- [ ] Python lookup ও `ip route get` মিলিয়েছি
- [ ] অস্থায়ী ও blackhole route যোগ ও মুছেছি
- [ ] NAT simulation ও `conntrack -L` দেখেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `ip-route(8)`: https://man7.org/linux/man-pages/man8/ip-route.8.html
- `ip-rule(8)` (policy routing): https://man7.org/linux/man-pages/man8/ip-rule.8.html
- nftables wiki — NAT: https://wiki.nftables.org/
- `conntrack(8)`: https://man7.org/linux/man-pages/man8/conntrack.8.html
- Kernel docs — IP sysctl (`ip_forward`): https://docs.kernel.org/networking/ip-sysctl.html
- RFC 3022 — Traditional NAT: https://www.rfc-editor.org/rfc/rfc3022
- AWS — NAT gateways: https://docs.aws.amazon.com/vpc/

---

**পরের lesson:** L02-05 — TCP, UDP, port, socket ও connection state
