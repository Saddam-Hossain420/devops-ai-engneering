# L02-03 — IPv4, IPv6, CIDR ও subnetting

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা (হাতে হিসাব অনুশীলন সহ) |
| **পূর্বশর্ত** | [L02-02 — Ethernet, ARP, VLAN](L02-02-ethernet-arp-vlan.md) |
| **Label** | — |
| **Tested** | `subnet_calc.py`: ৮টি test পাস; `info`, `split`, `overlap`, `contains`, `plan` চালানো (Python 3.14, Windows)। `ip addr`, `ipcalc` **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- IPv4 ঠিকানার গঠন: ৩২ bit, network অংশ ও host অংশ।
- **CIDR** notation (`/24`), **netmask**, **wildcard**।
- **হাতে subnet হিসাব** — network, broadcast, usable range, host সংখ্যা।
- Private (RFC 1918), public, loopback, link-local, CGNAT ও documentation range।
- **IPv6**: ১২৮ bit, লেখার নিয়ম, `/64`, global ও link-local।
- Cloud VPC-র subnet **পরিকল্পনা** ও **overlap**-এর বিপদ।
- Python-এর `ipaddress` দিয়ে subnet calculator ও VPC planner।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

প্রতিটি device-এর একটি ঠিকানা দরকার, এবং router-কে জানতে হবে কোন ঠিকানা "কাছে" (একই network) আর কোনটি "দূরে" (অন্য router-এর দিকে)। প্রতিটি ঠিকানা আলাদা করে মনে রাখা অসম্ভব — তাই ঠিকানাগুলো **block**-এ ভাগ: "১০.০.১.০ থেকে ১০.০.১.২৫৫ — এই পুরো block ঐ দিকে।" এই block-ই **subnet**, আর `10.0.1.0/24` তার সংক্ষিপ্ত লেখা।

DevOps/Cloud-এ subnetting দৈনন্দিন কাজ:

- AWS VPC তৈরিতে CIDR বেছে নিতে হয় — পরে বদলানো কঠিন।
- দুটি VPC বা office network-এর range **overlap** করলে পরে peering/VPN জুড়তে পারবেন না — খুব প্রচলিত ও ব্যয়বহুল ভুল।
- Kubernetes-এ Pod ও Service-এর CIDR, Docker-এর bridge network (Module 10, 14) — সব subnet।
- Firewall/security group-এর নিয়ম CIDR-এ লেখা (L02-10)।

## 3. সহজ ভাষায় পরিচয়

**IPv4 ঠিকানা** = ৩২ bit, ৪টি ৮-bit অংশ (**octet**), দশমিকে: `192.168.1.77`। প্রতিটি octet ০–২৫৫।

**CIDR `/n`** = প্রথম `n` bit network-এর, বাকি `32 − n` bit host-এর।

| CIDR | Netmask | ঠিকানা সংখ্যা | ব্যবহারযোগ্য host |
|---|---|---|---|
| /16 | 255.255.0.0 | ৬৫,৫৩৬ | ৬৫,৫৩৪ |
| /20 | 255.255.240.0 | ৪,০৯৬ | ৪,০৯৪ |
| /24 | 255.255.255.0 | ২৫৬ | ২৫৪ |
| /26 | 255.255.255.192 | ৬৪ | ৬২ |
| /28 | 255.255.255.240 | ১৬ | ১৪ |
| /30 | 255.255.255.252 | ৪ | ২ |
| /32 | 255.255.255.255 | ১ | ১ (একটি host) |

**সূত্র:** ঠিকানা = ২^(৩২ − n); ব্যবহারযোগ্য = সেই সংখ্যা − ২ (প্রথমটি **network address**, শেষটি **broadcast**)। ব্যতিক্রম: /৩১ (point-to-point link, দুটিই ব্যবহারযোগ্য) ও /৩২।

**বিশেষ range:**

| Range | কী |
|---|---|
| `10.0.0.0/8`, `172.16.0.0/12`, `192.168.0.0/16` | **Private** (RFC 1918) — internet-এ route হয় না, NAT দরকার (L02-04) |
| `127.0.0.0/8` | Loopback — নিজের machine |
| `169.254.0.0/16` | Link-local — DHCP ব্যর্থ হলে স্বয়ংক্রিয়; cloud metadata (`169.254.169.254`) |
| `100.64.0.0/10` | Shared/CGNAT (ISP-র ভেতরে) |
| `192.0.2.0/24`, `198.51.100.0/24`, `203.0.113.0/24` | Documentation — উদাহরণে ব্যবহারের জন্য (এই repository-ও ব্যবহার করে) |

**IPv6** = ১২৮ bit, hex-এ ৮টি group: `2001:0db8:abcd:0012:0000:0000:0000:0001` → সংক্ষেপে `2001:db8:abcd:12::1` (শুরুর শূন্য বাদ, একটানা শূন্য group-এর জায়গায় একবার `::`)। সাধারণ subnet = **/64** (এক LAN-এ ১৮ quintillion ঠিকানা)। `fe80::/10` = link-local (প্রতিটি interface-এ স্বয়ংক্রিয়); `fd00::/8` = ULA (private-এর মতো); `::1` = loopback।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### শহর, এলাকা ও বাড়ির নম্বর

`192.168.1.77/24`:

- প্রথম ২৪ bit (`192.168.1`) = **এলাকার নাম** — একই এলাকার সবাই এই অংশ share করে।
- শেষ ৮ bit (`77`) = **বাড়ির নম্বর** — এলাকার ভেতরে আলাদা।
- `/24` বলে "এলাকার নাম কত অক্ষরের"। `/16` হলে এলাকা বড় (`192.168`), বাড়ির নম্বরের জন্য বেশি অক্ষর।
- **Network address** (`.0`) = এলাকার সাইনবোর্ড, **broadcast** (`.255`) = এলাকার মাইক — কোনোটিই কারো বাড়ি নয়।
- **Subnetting** = একটি বড় এলাকাকে ছোট ছোট মহল্লায় ভাগ করা।

### Analogy কোথায় মেলে না

- এলাকার নাম ও বাড়ির নম্বরের সীমা সবসময় একটি পরিষ্কার জায়গায় (দশমিক বিন্দুতে) নয় — `/26`-এ সীমা একটি octet-এর **মাঝখানে**, তাই **binary**-তে হিসাব লাগে (Section 8.1)।
- একই নামের দুটি এলাকা দুই শহরে থাকতে পারে, কোনো সমস্যা নেই। Network-এ দুটি **private** network-এ একই range (যেমন দুই কোম্পানিতেই `10.0.0.0/16`) থাকা ঠিক আছে — কিন্তু **যেদিন তাদের জুড়তে চাইবেন** (merger, VPN, VPC peering), router জানবে না কোন `10.0.5.7` — এটাই overlap সমস্যা (Section 5)।

## 5. Real-world engineering scenario — VPC overlap

**পরিস্থিতি:** একটি startup দুই বছর আগে AWS-এ VPC বানিয়েছিল `10.0.0.0/16` দিয়ে (default পরামর্শ)। এখন একটি data team-এর আলাদা VPC-ও `10.0.0.0/16`, আর অফিসের VPN network `10.0.128.0/17`। নতুন প্রয়োজন: তিনটিকে যুক্ত করা।

**সমস্যা:** Overlapping range-এর মধ্যে routing সম্ভব নয় — AWS VPC peering overlapping CIDR-এ তৈরিই হয় না; VPN-এ গন্তব্য অস্পষ্ট।

```bash
python3 subnet_calc.py overlap 10.0.0.0/16 10.0.128.0/17 192.168.0.0/16
```

```text
OVERLAP 10.0.0.0/16 ↔ 10.0.128.0/17
1 overlap(s)
```

**সমাধানের বিকল্প (সবই ব্যয়বহুল):** একটি network re-address (সব server, configuration বদলানো), NAT-এর জটিল স্তর, বা PrivateLink জাতীয় service-স্তরের সংযোগ।

**প্রতিরোধ:** শুরুতেই একটি **IP address plan** — প্রতিটি environment/team/region-এর জন্য আলাদা, non-overlapping block (যেমন `10.10.0.0/16` dev, `10.20.0.0/16` staging, `10.30.0.0/16` prod), কেন্দ্রীয়ভাবে নথিভুক্ত (IPAM)। এই lesson-এর `plan` ও `overlap` command সেই অভ্যাসের ছোট রূপ।

## 6. Diagram — একটি VPC-র subnet পরিকল্পনা

```text
 VPC 10.20.0.0/16 (65,536 ঠিকানা)
 ├── public    (internet-facing load balancer, NAT gateway)
 │     az-a 10.20.0.0/20    az-b 10.20.16.0/20   az-c 10.20.32.0/20
 ├── private   (application server)
 │     az-a 10.20.48.0/20   az-b 10.20.64.0/20   az-c 10.20.80.0/20
 ├── database  (DB, কোনো internet route নেই)
 │     az-a 10.20.96.0/20   az-b 10.20.112.0/20  az-c 10.20.128.0/20
 └── অব্যবহৃত: 10.20.144.0 – 10.20.255.255  ← ভবিষ্যতের জন্য (নতুন tier, Kubernetes Pod CIDR)
```

প্রতিটি tier তিনটি AZ-এ (L07-03, fault domain)। পুরো /16 ভাগ না করে জায়গা রেখে দেওয়া — পরে বাড়ানো সম্ভব।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Octet | IPv4-এর ৮-bit অংশ |
| Prefix / CIDR | `/n` — network অংশের bit সংখ্যা |
| Netmask | Network অংশে ১, host অংশে ০ (যেমন 255.255.255.0) |
| Wildcard mask | Netmask-এর উল্টো (০.০.০.২৫৫) — কিছু firewall/ACL-এ ব্যবহৃত |
| Network address | Subnet-এর প্রথম ঠিকানা (সব host bit ০) |
| Broadcast address | শেষ ঠিকানা (সব host bit ১) |
| Subnetting | বড় network-কে ছোট ভাগে ভাগ |
| Supernetting / summarization | ছোটগুলো মিলিয়ে বড় route (`10.0.0.0/22` = চারটি /24) |
| RFC 1918 | Private IPv4 range |
| CGNAT | ISP-স্তরের NAT, `100.64.0.0/10` |
| Link-local | একই link-এ শুধু (IPv4 169.254/16, IPv6 fe80::/10) |
| IPAM | IP Address Management — কেন্দ্রীয় পরিকল্পনা ও রেকর্ড |
| Dual-stack | একই সাথে IPv4 ও IPv6 |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 হাতে subnet হিসাব — `192.168.1.77/26`

**ধাপ ১ — শেষ octet binary-তে** (প্রথম তিনটি পুরোপুরি network-এ):

```text
77 = 64 + 8 + 4 + 1 = 0100 1101
```

**ধাপ ২ — /২৬ মানে শেষ octet-এর প্রথম ২ bit network-এ** (২৪ + ২ = ২৬):

```text
 77     = 01 | 001101
 mask   = 11 | 000000   = 192   → netmask 255.255.255.192
```

**ধাপ ৩ — network address = host bit সব ০:** `01 000000` = ৬৪ → **192.168.1.64**

**ধাপ ৪ — broadcast = host bit সব ১:** `01 111111` = ১২৭ → **192.168.1.127**

**ধাপ ৫ — usable:** .৬৫ থেকে .১২৬ → ২^৬ − ২ = **৬২টি**

**শর্টকাট (block size):** ২৫৬ − ১৯২ = **৬৪** → subnet শুরু হয় ০, ৬৪, ১২৮, ১৯২-এ। ৭৭ পড়ে ৬৪–১২৭ block-এ।

এই lesson-এর tool ঠিক এই ফল দেয় (Section 9.1)।

### 8.2 একই subnet কিনা — host-এর সিদ্ধান্ত

Host নিজের IP ও mask দিয়ে গন্তব্যের network বের করে (bitwise AND): মিললে local (সরাসরি ARP, L02-02), না মিললে gateway। ভুল mask দিলে ভুল সিদ্ধান্ত — একটি প্রচলিত "আধা-কাজ করা network" সমস্যা।

### 8.3 Cloud-এ সংরক্ষিত ঠিকানা

AWS প্রতিটি subnet-এর **৫টি** ঠিকানা নিজের জন্য রাখে: network, VPC router (+১), DNS (+২), ভবিষ্যৎ ব্যবহার (+৩), এবং শেষটি (broadcast)। তাই /24-এ ২৫১টি, /২৮-এ মাত্র ১১টি। AWS subnet-এর আকার /১৬ থেকে /২৮। (অন্য cloud-এর সংখ্যা আলাদা হতে পারে — তাদের documentation দেখুন।)

### 8.4 IPv6 — কেন এবং কীভাবে আলাদা

- IPv4-এর ~৪৩০ কোটি ঠিকানা শেষ — তাই NAT ও CGNAT। IPv6-এ ঠিকানার অভাব নেই; প্রতিটি device-এর global ঠিকানা সম্ভব।
- IPv6-এ broadcast নেই (multicast), ARP নেই (NDP, L02-02), host নিজে ঠিকানা তৈরি করতে পারে (SLAAC)।
- Subnet সাধারণত /৬৪ — "কতগুলো host" নিয়ে চিন্তা নেই, শুধু কতগুলো subnet।
- Firewall-এ সতর্কতা: IPv4-এ NAT অনিচ্ছাকৃতভাবে "লুকিয়ে" রাখত; IPv6-এ global ঠিকানা মানে firewall নিয়ম অবশ্যই ঠিক থাকতে হবে।

## 9. Practical demonstration

### 9.1 Calculator — Python

File: [`code/L02-03/subnet_calc.py`](code/L02-03/subnet_calc.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-03
python3 subnet_calc.py info 10.0.1.0/24
python3 subnet_calc.py info 192.168.1.77/26
python3 subnet_calc.py info 2001:db8:abcd::/48
```

**আসল output (repository-তে চালানো):**

```text
network                10.0.1.0/24
version                4
addresses              256
type                   private (RFC 1918 / ULA / documentation)
netmask                255.255.255.0
wildcard               0.0.0.255
broadcast              10.0.1.255
first_usable           10.0.1.1
last_usable            10.0.1.254
usable_hosts           254
usable_in_aws_subnet   251
```

```text
network                192.168.1.64/26
...
netmask                255.255.255.192
wildcard               0.0.0.63
broadcast              192.168.1.127
first_usable           192.168.1.65
```

— Section 8.1-এর হাতের হিসাবের সাথে মিলেছে।

```text
network                2001:db8:abcd::/48
version                6
addresses              1208925819614629174706176
...
/64 subnets inside     65536
```

একটি /৪৮-এর ভেতরে ৬৫,৫৩৬টি /৬৪ subnet (২^(৬৪−৪৮) = ২^১৬)। `2001:db8::/32` documentation range — তাই "private/documentation" দেখাচ্ছে।

### 9.2 ভাগ ও পরিকল্পনা

```bash
python3 subnet_calc.py split 10.0.0.0/16 --new-prefix 18
python3 subnet_calc.py plan 10.20.0.0/16 --azs 3 --prefix 20
python3 subnet_calc.py contains 10.0.1.0/24 10.0.1.77; echo "exit=$?"
```

`plan`-এর আসল output Section 6-এর diagram-এর সাথে মেলে (প্রতিটি /২০-এ AWS-এ ব্যবহারযোগ্য ৪০৯১)।

### 9.3 নিজের machine-এ (Ubuntu VM)

```bash
ip -4 -br addr              # প্রতিটি interface-এর IPv4/CIDR
ip -6 -br addr              # IPv6 (fe80:: link-local সবসময় থাকে)
ip route                    # কোন subnet কোন interface-এ (L02-04)
sudo apt install -y ipcalc && ipcalc 192.168.1.77/26     # native calculator, তুলনার জন্য
```

> **Fedora-তে:** `ipcalc` সাধারণত installed (ভিন্ন implementation — output format আলাদা, যেমন `ipcalc --all-info 192.168.1.77/26`)। তথ্য একই হওয়া উচিত।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_subnet_calc.py`](code/L02-03/test_subnet_calc.py)-এর ৮টি test: /২৪ ও /২৬ (host bit সহ input), /৩১ ও /৩২, CGNAT ও public শ্রেণী, IPv6 /৪৮, split, overlap, VPC plan ও জায়গার অভাব, CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `ipaddress.ip_network(cidr, strict=False)` | `192.168.1.77/26` → `192.168.1.64/26` | User প্রায়ই host ঠিকানা সহ লেখেন |
| `net.hostmask` | Wildcard | |
| `prefixlen <= 30` শর্ত | /৩১, /৩২-এ broadcast/network বাদ নয় | RFC 3021 ও single host |
| `net.subnets(new_prefix=...)` | Split | Standard library-র সঠিক implementation |
| `a.overlaps(b)` | Overlap | একই version-এ তুলনা |
| `plan()`-এ ক্রমানুসারে বরাদ্দ ও জায়গা যাচাই | | পরে বাড়ানোর জন্য বাকি অংশ একসাথে থাকে |
| `CLOUD_RESERVED = 5` | AWS নিয়ম | Documentation-ভিত্তিক constant, অন্য cloud-এ বদলান |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `info 192.168.1.77/26` | network .৬৪, broadcast .১২৭, ৬২ host |
| `overlap 10.0.0.0/8 10.1.0.0/16` | OVERLAP, exit 1 |
| `ipcalc`-এর সাথে তুলনা | একই সংখ্যা |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| একই "subnet"-এ কিছু host পাওয়া যায় না | ভুল mask (/১৬ বনাম /২৪) | দুই host-এর `ip addr` তুলনা | Mask মেলান |
| AWS subnet তৈরি ব্যর্থ | CIDR VPC-র বাইরে বা overlap | `contains`, `overlap` | সঠিক range |
| VPC peering তৈরি হয় না | Overlapping CIDR | `overlap` | Re-address বা অন্য সংযোগ পদ্ধতি |
| Docker container বাইরের একটি network-এ পৌঁছায় না | Docker bridge range (`172.17.0.0/16`) সেই network-এর সাথে overlap | `ip route`, `docker network inspect` | Docker-এর default address pool বদলান (Module 10) |
| `169.254.x.x` ঠিকানা পেয়েছে | DHCP ব্যর্থ | `journalctl` (L02-09) | DHCP server/network |
| IPv6 ঠিকানায় `ssh fe80::1` কাজ করে না | Link-local-এ interface দরকার | — | `ssh fe80::1%enp0s8` |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Firewall/security group-এ যতটা সম্ভব ছোট CIDR (`0.0.0.0/0` শুধু যেখানে সত্যিই দরকার, যেমন public HTTPS)। Database subnet-এ internet route নেই। `169.254.169.254` (cloud metadata) থেকে credential চুরি একটি পরিচিত আক্রমণ (SSRF) — Module 08, 19। IPv6 global ঠিকানায় firewall ভুললে সরাসরি internet থেকে প্রবেশ।
- **Performance:** খুব বড় flat network-এ broadcast বেশি; subnet ভাগ করে নিয়ন্ত্রণ।
- **Cost:** Public IPv4 এখন অনেক cloud-এ ঘণ্টাভিত্তিক বিল হয় — private subnet ও IPv6 খরচ কমায় (Module 29)। Overlap-এর পরে re-addressing-এর engineering খরচ বিশাল।

## 14. Hands-on exercise

1. হাতে হিসাব করে তারপর tool দিয়ে মিলিয়ে দেখুন: `172.16.45.200/20`, `10.10.10.10/29`, `192.168.100.0/22`-এর network, broadcast, usable।
2. `10.0.0.0/22`-কে চারটি /২৪-এ ভাগ করুন; উল্টোভাবে `10.0.0.0/24` থেকে `10.0.3.0/24` একটি route-এ কীভাবে লিখবেন (summarization)?
3. একটি কাল্পনিক কোম্পানির জন্য IP plan: ৩টি environment × ২টি region, প্রতিটি /১৬, অফিস VPN আলাদা — `overlap` দিয়ে যাচাই করে `~/devops-notebook/ip-plan.md`-এ লিখুন।
4. `subnet_calc.py`-তে `summarize` command যোগ করুন (`ipaddress.collapse_addresses`)। Test লিখুন।
5. `2001:db8:abcd:12:0000:0000:0000:0001` ও `2001:db8:0:0:1:0:0:1`-এর সংক্ষিপ্ত রূপ লিখুন; Python-এ `ipaddress.ip_address(...).compressed` দিয়ে যাচাই।

## 15. Mini-project — IPAM sheet

একটি ছোট CSV-ভিত্তিক IPAM: `name,cidr,environment,owner` লাইনগুলোর জন্য একটি Python script যা (১) প্রতিটি CIDR বৈধ কিনা, (২) কোনো overlap আছে কিনা, (৩) প্রতিটি parent block-এ কতটা খালি — রিপোর্ট দেয়। Overlap থাকলে exit 1 (CI-তে gate, L00-04)। Module 12 (Terraform)-এ VPC CIDR এখান থেকেই আসবে।

## 16. Interview প্রশ্ন

1. `/26` subnet-এ কতগুলো host? হিসাব দেখান।
2. Private IP range কী কী? Internet-এ কেন route হয় না?
3. দুটি VPC-র CIDR overlap করলে কী সমস্যা?
4. AWS subnet-এ কতগুলো ঠিকানা সংরক্ষিত এবং কেন?
5. IPv6-এ সাধারণ subnet আকার কত, এবং IPv4-এর সাথে প্রধান পার্থক্য কী?
6. `169.254.169.254` কী এবং কেন security-তে গুরুত্বপূর্ণ?
7. একটি নতুন VPC-র CIDR কীভাবে বেছে নেবেন?

## 17. Self-assessment প্রশ্ন

1. শহর-এলাকা analogy কোথায় মেলে না?
2. `192.168.1.77/26`-এর হিসাব binary-তে ধাপে ধাপে লিখুন।
3. Block size শর্টকাট দিয়ে `10.10.10.10/29`-এর network বের করুন।
4. Section 5-এর overlap কেন বিপজ্জনক এবং প্রতিরোধ কী?
5. /২৮ AWS subnet-এ কতটি ঠিকানা ব্যবহারযোগ্য?
6. IPv6 /৪৮-এ কতটি /৬৪ এবং কেন?

## 18. সংক্ষিপ্ত সারাংশ

- IPv4 ৩২ bit; `/n` = network bit; ঠিকানা = ২^(৩২−n), usable = −২ (network ও broadcast)।
- হাতে হিসাব: binary বা block size শর্টকাট।
- Private (RFC 1918), loopback, link-local (+ cloud metadata), CGNAT, documentation range।
- IPv6 ১২৮ bit, `::` সংক্ষেপ, /৬৪ subnet, ARP-এর বদলে NDP, firewall আরো গুরুত্বপূর্ণ।
- Cloud-এ শুরুতে non-overlapping IP plan; AWS প্রতি subnet-এ ৫টি সংরক্ষিত।

## 19. Completion checklist

- [ ] তিনটি subnet হাতে হিসাব করে tool দিয়ে মিলিয়েছি
- [ ] `split`, `overlap`, `plan` চালিয়েছি
- [ ] নিজের VM-এর `ip addr`/`ip route` থেকে subnet চিনেছি
- [ ] IP plan (Exercise ৩) লিখেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 4632 — CIDR: https://www.rfc-editor.org/rfc/rfc4632
- RFC 1918 — Private IPv4: https://www.rfc-editor.org/rfc/rfc1918
- RFC 6598 — Shared address space (CGNAT): https://www.rfc-editor.org/rfc/rfc6598
- RFC 5737 — IPv4 documentation ranges: https://www.rfc-editor.org/rfc/rfc5737
- RFC 4291 — IPv6 addressing architecture: https://www.rfc-editor.org/rfc/rfc4291
- RFC 3021 — /31 point-to-point: https://www.rfc-editor.org/rfc/rfc3021
- Python `ipaddress`: https://docs.python.org/3/library/ipaddress.html
- AWS VPC — subnet sizing ও reserved addresses: https://docs.aws.amazon.com/vpc/

---

**পরের lesson:** L02-04 — Routing table, gateway ও NAT
