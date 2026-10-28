# L02-02 — Ethernet, MAC address, ARP, switching ও VLAN

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L02-01 — OSI ও TCP/IP model](L02-01-network-models.md) |
| **Label** | — |
| **Tested** | `l2_tool.py`: ৬টি test পাস; `mac`, `neigh`, `vlan` চালানো (Python 3.14, Windows)। নমুনা `ip neigh` output হাতে তৈরি (VirtualBox network-এর ধরন অনুসরণে)। `ip neigh`, `arping`, `bridge fdb`, `tcpdump arp` **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- **Ethernet frame** ও **MAC address**-এর গঠন (unicast/multicast, global/local bit)।
- **Switch** কীভাবে MAC table শিখে frame পাঠায়; **broadcast domain**।
- **ARP** — IP থেকে MAC খোঁজা; ARP cache-এর অবস্থা; gratuitous ARP।
- **VLAN** (802.1Q) — একটি switch-এ একাধিক আলাদা network; access ও trunk port।
- Cloud-এ L2 কেন "লুকানো" থাকে।
- Python দিয়ে MAC বিশ্লেষণ, ARP table audit ও VLAN tag তৈরি/decode।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L02-01-এ দেখেছেন: IP দিয়ে বলা হয় "কোন host"; কিন্তু একটি packet শারীরিকভাবে পাঠাতে **পরের device-এর hardware ঠিকানা** লাগে। একই network-এর দুটি machine কীভাবে একে অপরকে খুঁজে পায়? Router কীভাবে জানে পরের hop কে? এর উত্তর Ethernet ও ARP।

DevOps-এ এর গুরুত্ব:

- "একই subnet-এ, তবু ping হয় না" — প্রায়ই ARP বা VLAN সমস্যা।
- নতুন server-এ পুরোনো server-এর IP দিলে কিছুক্ষণ traffic পুরোনো জায়গায় যায় — ARP cache।
- Docker/Kubernetes-এর network (Module 10, 14) আসলে Linux **bridge** — একটি software switch।
- On-premise data center-এ VLAN দিয়ে production, staging ও management network আলাদা রাখা হয়।

## 3. সহজ ভাষায় পরিচয়

**MAC address:** ৪৮-bit (৬ byte) hardware ঠিকানা, যেমন `08:00:27:5e:1a:c3`।

- প্রথম ৩ byte = **OUI** (নির্মাতা কোম্পানির নম্বর)।
- প্রথম byte-এর সবচেয়ে ছোট bit (**I/G**): ১ = multicast/broadcast, ০ = unicast।
- পরের bit (**U/L**): ১ = locally administered (VM, container, random MAC), ০ = নির্মাতা-প্রদত্ত।
- `ff:ff:ff:ff:ff:ff` = **broadcast** — একই network-এর সবাই।

**Switch:** একটি L2 device যা প্রতিটি frame-এর **source MAC** দেখে শেখে "এই MAC কোন port-এ" (**MAC table**)। পরে সেই MAC-এর জন্য frame শুধু সেই port-এ পাঠায়। অজানা গন্তব্য বা broadcast হলে সব port-এ পাঠায় (flood)।

**Broadcast domain:** যতদূর একটি broadcast frame পৌঁছায় — সাধারণত একটি VLAN বা একটি subnet। Router broadcast পার করে না।

**ARP (Address Resolution Protocol):** "১৯২.১৬৮.৫৬.২০ কার? MAC বলো" — broadcast প্রশ্ন; মালিক unicast উত্তর দেয়; উত্তর **ARP cache**-এ কিছুক্ষণ থাকে।

> IPv6-এ ARP নেই — একই কাজ করে **NDP** (Neighbor Discovery, ICMPv6)। Linux-এ দুটোই `ip neigh` দিয়ে দেখা যায়।

**VLAN:** একটি physical switch-কে logical ভাবে একাধিক আলাদা switch বানানো — প্রতিটি VLAN আলাদা broadcast domain। Frame-এ ৪ byte-এর **802.1Q tag** (VLAN ID ১–৪০৯৪) যোগ হয় যখন একাধিক VLAN একই link (**trunk**) দিয়ে যায়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিস ভবনের ফ্লোর ও ঘোষণা

- **MAC address** = প্রতিটি কর্মীর ডেস্ক নম্বর (একই ফ্লোরে খোঁজার জন্য)। **IP** = কর্মীর নাম ও বিভাগ।
- **Switch** = ফ্লোরের পিয়ন, যিনি মনে রাখেন কোন ডেস্ক কোন কোণে — প্রথমবার না জানলে সবাইকে জিজ্ঞেস করেন।
- **ARP** = ফ্লোরে মাইকে ঘোষণা: "করিম সাহেব (IP), আপনার ডেস্ক নম্বর কত?" — করিম সাহেব শুধু ঘোষণাকারীকে উত্তর দেন। সবাই ঘোষণাটি শোনেন (broadcast)।
- **VLAN** = একই ভবনে কাচের দেয়াল দিয়ে আলাদা অফিস — Accounts-এর মাইক ঘোষণা HR শোনে না।
- **Router** = ভবনের রিসেপশন: অন্য ভবনের কাউকে চাইলে রিসেপশনে দেন।

### Analogy কোথায় মেলে না

- মাইকে ঘোষণা শুনে কেউ মিথ্যা উত্তর দিলে সাধারণত ধরা পড়ে। ARP-এ **কোনো authentication নেই** — যে কেউ "আমিই router" উত্তর দিতে পারে (**ARP spoofing**) এবং traffic নিজের দিকে টেনে নিতে পারে। Switch-এর security feature (Dynamic ARP Inspection) ও encryption (TLS) এর প্রতিকার।
- ডেস্ক নম্বর স্থায়ী। VM ও container-এর MAC software দিয়ে তৈরি ও বদলানো যায় — তাই U/L bit ১।
- কাচের দেয়াল চোখে দেখা যায়। VLAN ভুল configure করলে (ভুল port ভুল VLAN-এ) কোনো সতর্কতা ছাড়াই দুটি machine "একই subnet-এ" থেকেও একে অপরকে পায় না।

## 5. Real-world engineering scenario — "IP বদলালাম, traffic পুরোনো server-এ যাচ্ছে"

**পরিস্থিতি:** Database failover: পুরোনো primary server বন্ধ, নতুন server-এ একই virtual IP (`192.168.56.50`) বসানো হলো। App server-গুলোর কিছু ঠিকমতো নতুন server-এ যাচ্ছে, কিছু কয়েক মিনিট ধরে timeout।

**কারণ:** App server-গুলোর **ARP cache**-এ `192.168.56.50 → পুরোনো MAC` রয়ে গেছে। পুরোনো server বন্ধ, তাই সেই MAC-এ পাঠানো frame কেউ নেয় না। Cache entry মেয়াদ শেষ (STALE → probe → FAILED) না হওয়া পর্যন্ত সমস্যা।

**সমাধান:** নতুন server IP নেওয়ার সময় **gratuitous ARP** পাঠায় — "এখন থেকে ১৯২.১৬৮.৫৬.৫০ আমার (নতুন MAC)" — শুনে সবাই cache আপডেট করে। Keepalived/VRRP জাতীয় failover tool এটি স্বয়ংক্রিয়ভাবে করে; হাতে করলে `arping -U`।

**Diagnosis (app server-এ):**

```bash
ip neigh show 192.168.56.50          # কোন MAC, কী অবস্থা
sudo arping -c 3 -I enp0s8 192.168.56.50   # এখন কে উত্তর দেয়
```

**শিক্ষা:** "একই IP" মানেই "একই machine" নয় — L3 ঠিকানার নিচে L2 mapping আছে, যা cache হয়।

## 6. Diagram

### ARP ও switch-এর শেখা

```text
 Host A 192.168.56.10 (MAC aa)             Switch MAC table           Host B 192.168.56.20 (MAC bb)
   │                                        (শুরুতে খালি)                    │
   │ ARP request (broadcast ff:ff:..):       learn: aa → port 1               │
   │ "Who has 192.168.56.20? Tell .10"  ──►  flood সব port-এ  ───────────────►│
   │                                                                          │ cache: .10 → aa
   │                                         learn: bb → port 2               │
   │◄──────────────────────── ARP reply (unicast to aa): ".20 is at bb" ───────│
   │ cache: .20 → bb                                                          │
   │ ══ এখন IP packet, Ethernet dst = bb ══►  table থেকে সরাসরি port 2 ──────►│
```

### VLAN trunk

```text
  ┌─ Switch 1 ─────────┐        trunk (802.1Q tag সহ)        ┌─ Switch 2 ─────────┐
  │ port1 VLAN10 (web) │══════ [tag 10] / [tag 20] frames ════│ port1 VLAN10 (web) │
  │ port2 VLAN20 (db)  │                                      │ port2 VLAN20 (db)  │
  └────────────────────┘                                      └────────────────────┘
   access port: tag ছাড়া frame; switch নিজে VLAN ঠিক করে        VLAN10 ↔ VLAN20: router (L3) ছাড়া যোগাযোগ নেই
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Frame | L2-এর data unit |
| MAC address | ৪৮-bit hardware ঠিকানা |
| OUI | MAC-এর প্রথম ৩ byte, নির্মাতার পরিচয় |
| Unicast / multicast / broadcast | একজন / একটি দল / সবাই |
| Switch / MAC table | L2 device / কোন MAC কোন port-এ |
| Flooding | অজানা গন্তব্যে সব port-এ পাঠানো |
| Broadcast domain | Broadcast যতদূর পৌঁছায় |
| ARP / ARP cache | IP → MAC খোঁজা / সাময়িক mapping |
| Gratuitous ARP | নিজে থেকে "এই IP আমার" ঘোষণা |
| ARP spoofing | মিথ্যা ARP উত্তর দিয়ে traffic টানা |
| NDP | IPv6-এর neighbor discovery (ARP-এর বদলে) |
| VLAN / 802.1Q | Logical L2 network / VLAN tag standard |
| Access / trunk port | এক VLAN, tag ছাড়া / বহু VLAN, tag সহ |
| Bridge | Software switch (Linux bridge, docker0) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Linux neighbor (ARP) cache-এর অবস্থা

| State | অর্থ |
|---|---|
| REACHABLE | সম্প্রতি নিশ্চিত — ব্যবহারযোগ্য |
| STALE | পুরোনো; ব্যবহার হবে, কিন্তু পরে যাচাই করা হবে |
| DELAY / PROBE | যাচাই চলছে |
| FAILED | উত্তর আসেনি — host নেই, ভুল VLAN/subnet, বা firewall |
| INCOMPLETE | ARP পাঠানো হয়েছে, উত্তরের অপেক্ষা |
| PERMANENT | হাতে বসানো static entry |

### 8.2 একই subnet নাকি router?

Host packet পাঠানোর আগে দেখে (L02-04-এ বিস্তারিত): গন্তব্য IP কি আমার subnet-এ?

- **হ্যাঁ** → সরাসরি গন্তব্যের MAC (ARP করে)।
- **না** → **default gateway**-এর MAC (ARP করে router-এর জন্য) — packet-এর IP header-এ গন্তব্য IP-ই থাকে, Ethernet header-এ router-এর MAC। (L02-01: router-এ L2 বদলায়, L3 থাকে।)

তাই ভুল subnet mask দিলে host ভাবতে পারে দূরের machine "local", এবং ARP করে উত্তর পায় না → FAILED।

### 8.3 VLAN tag-এর গঠন (৪ byte)

```text
 | TPID 0x8100 (16 bit) | PCP (3 bit) | DEI (1) | VID (12 bit) |
 উদাহরণ: VLAN 20, priority 5 → 81 00 | 101 0 000000010100 → 81 00 a0 14
```

VID ১২ bit → ০–৪০৯৫; ০ ও ৪০৯৫ সংরক্ষিত → ব্যবহারযোগ্য **১–৪০৯৪**। PCP = QoS priority (০–৭)। এই lesson-এর tool ঠিক এই bit হিসাব করে।

### 8.4 Cloud-এ L2

AWS VPC-এর মতো cloud network-এ broadcast নেই; ARP-এর উত্তর **cloud-এর hypervisor নিজে** দেয় (proxy) — আপনার VM কোনো আসল L2 broadcast domain-এ নেই। তাই on-premise-এর gratuitous-ARP-ভিত্তিক failover cloud-এ কাজ করে না; সেখানে API দিয়ে IP সরানো হয় (Elastic IP, Module 08)। এটি L2-এর জ্ঞান cloud-এ কেন আলাদা — তার গুরুত্বপূর্ণ উদাহরণ।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 L2 পর্যবেক্ষণ

```bash
ip -br link                         # interface ও MAC
ip neigh                            # ARP/NDP cache
ip neigh show dev enp0s8 nud stale  # শুধু stale entry (interface নাম নিজের মতো বদলান)
bridge link 2>/dev/null; bridge fdb show | head    # bridge থাকলে (যেমন docker0) তার MAC table
```

**ARP নিজে দেখুন:**

```bash
GW=$(ip route | awk '/default/ {print $3; exit}')
sudo ip neigh flush dev "$(ip route | awk '/default/ {print $5; exit}')"   # ⚠️ cache খালি (নিরীহ, আবার শিখবে)
sudo tcpdump -i any -nn -c 4 arp &
ping -c 1 "$GW"
wait
```

উদাহরণ:

```text
ARP, Request who-has 10.0.2.2 tell 10.0.2.15, length 28
ARP, Reply 10.0.2.2 is-at 52:55:0a:00:02:02, length 46
```

**arping (L2-তে ping):**

```bash
sudo apt install -y iputils-arping         # Fedora-তে: iputils (arping সাধারণত আছে)
sudo arping -c 2 -I enp0s8 192.168.56.1    # ICMP block থাকলেও ARP সাধারণত উত্তর দেয়
```

### 9.2 Python tool

File: [`code/L02-02/l2_tool.py`](code/L02-02/l2_tool.py)

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-02
python3 l2_tool.py mac 52-54-00-AB-CD-EF
ip neigh > /tmp/neigh.txt && python3 l2_tool.py neigh /tmp/neigh.txt
python3 l2_tool.py neigh sample-neigh.txt; echo "exit=$?"
python3 l2_tool.py vlan --vid 20 --pcp 5
python3 l2_tool.py vlan --decode 8100a014
```

**আসল output (repository-তে চালানো):**

```text
mac                    52:54:00:ab:cd:ef
oui                    52:54:00
broadcast              False
multicast              False
locally_administered   True
```

`52:54:00` হলো QEMU/KVM-এর VM-এর জন্য প্রচলিত prefix — locally administered (০x৫২ = ০১০১ ০০**১**০ → U/L bit ১)।

```text
  192.168.56.1                 enp0s8 0a:00:27:00:00:12 REACHABLE
  192.168.56.20                enp0s8 08:00:27:5e:1a:c3 STALE
  192.168.56.30                enp0s8 -                 FAILED
  10.0.2.2                     enp0s3 52:55:0a:00:02:02 REACHABLE
  10.0.2.3                     enp0s3 52:55:0a:00:02:02 STALE
  fe80::a00:27ff:fe5e:1ac3     enp0s8 08:00:27:5e:1a:c3 STALE
WARN 192.168.56.30 on enp0s8: FAILED — ARP-এর উত্তর নেই (host down, ভুল subnet বা VLAN?)
WARN 52:55:0a:00:02:02 claims 2 IPv4 addresses ['10.0.2.2', '10.0.2.3'] — proxy/router হতে পারে, নয়তো ARP spoofing সন্দেহ করুন
exit=1
8100a014
VLAN 20  priority (PCP) 5  DEI 0
```

**Finding ব্যাখ্যা — false positive চিনুন:** দ্বিতীয় সতর্কতাটি VirtualBox-এর NAT network-এর স্বাভাবিক আচরণ — virtual gateway (১০.০.২.২) ও virtual DNS (১০.০.২.৩) একই virtual device, তাই একই MAC। Tool সঠিকভাবে "সন্দেহ" বলেছে, কিন্তু প্রেক্ষাপট জেনে আপনি সিদ্ধান্ত নেন — L01-05-এর sudoers audit-এর মতো। আর লক্ষ্য করুন IPv6 link-local ঠিকানা (`fe80::...`) একই MAC-এ থাকা স্বাভাবিক, তাই tool সেটি গোনে না।

### 9.3 VLAN interface তৈরি (⚠️ VM-এ, অস্থায়ী)

```bash
sudo ip link add link enp0s8 name enp0s8.20 type vlan id 20
sudo ip addr add 192.168.20.10/24 dev enp0s8.20
sudo ip link set enp0s8.20 up
ip -d link show enp0s8.20               # "vlan protocol 802.1Q id 20"
sudo ip link del enp0s8.20              # সরিয়ে ফেলা
```

এটি শুধু host-এর দিকে tag যোগ করে; অন্য প্রান্তে (switch/অন্য VM) একই VLAN না থাকলে যোগাযোগ হবে না। `ip` দিয়ে করা পরিবর্তন reboot-এ হারায় — স্থায়ী configuration Netplan-এ (Module 06/ পরবর্তী lesson)।

> **Fedora-তে:** একই `ip` command; স্থায়ী configuration NetworkManager (`nmcli connection add type vlan ...`)।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_l2_tool.py`](code/L02-02/test_l2_tool.py)-এর ৬টি test: MAC format normalize ও ভুল প্রত্যাখ্যান, broadcast/multicast/local bit (Docker-এর `02:42:...` সহ), neighbor parse ("router" flag সহ) ও audit, VLAN encode/decode, সংরক্ষিত VID ও ভুল TPID প্রত্যাখ্যান, CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `re.sub(r"[^0-9a-fA-F]", "", text)` | বিভিন্ন MAC format একরূপ | `-`, `:`, `.` (Cisco) — সব প্রচলিত |
| `first & 0x01` / `& 0x02` | I/G ও U/L bit | MAC-এর ধরন |
| `NEIGH_RE` | `ip neigh`-এর লাইন, `lladdr` ও `router` ঐচ্ছিক | FAILED entry-তে MAC থাকে না |
| IPv4-only duplicate check | `":" not in ip` | IPv6 link-local একই MAC-এ স্বাভাবিক |
| `(pcp << 13) \| (dei << 12) \| vid` | TCI-র ১৬ bit | 802.1Q গঠন |
| VID ১–৪০৯৪ যাচাই | | ০ ও ৪০৯৫ সংরক্ষিত |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| ARP flush-এর পরে ping-এর সময় tcpdump | Request (broadcast) ও Reply (unicast) |
| `l2_tool.py vlan --vid 20 --pcp 5` | `8100a014` |
| নিজের `ip neigh` audit | সম্ভবত কোনো সতর্কতা নেই, বা ব্যাখ্যাযোগ্য |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| একই subnet-এ ping হয় না, ARP FAILED | Host বন্ধ, ভুল VLAN, ভুল subnet mask | `ip neigh`, `tcpdump arp` — reply আসে? | Mask/VLAN ঠিক |
| IP সরানোর পরে traffic পুরোনো জায়গায় | ARP cache | `ip neigh show IP` | Gratuitous ARP (`arping -U`), বা cache flush |
| "Duplicate address detected" / মাঝে মাঝে সংযোগ | দুটি machine একই IP | `arping -D IP` (duplicate detection) | একটির IP বদলান |
| VLAN interface-এ যোগাযোগ নেই | অন্য প্রান্তে VLAN/trunk নেই | `tcpdump -e -i enp0s8 vlan` | Switch/VM-এ trunk configure |
| VM clone-এর পরে network অদ্ভুত | একই MAC দুটি VM-এ | `ip link` উভয়ে | Hypervisor-এ নতুন MAC generate |

## 13. Security, performance ও cost বিবেচনা

- **Security:** ARP-এ authentication নেই — ARP spoofing/man-in-the-middle সম্ভব একই L2-এ; প্রতিকার: switch-এ DAI/port security, network segmentation (VLAN), এবং সব কিছুতে encryption (TLS) যাতে traffic টানলেও পড়া না যায়। VLAN নিরাপত্তা-সীমা হিসেবে ব্যবহার হলে trunk configuration সঠিক রাখুন ("VLAN hopping" আক্রমণ)। Packet capture শুধু নিজের network-এ।
- **Performance:** বড় broadcast domain-এ ARP ও broadcast traffic বাড়ে — বড় network-কে VLAN/subnet-এ ভাগ করা হয়।
- **Cost:** On-premise-এ VLAN দিয়ে আলাদা physical switch ছাড়াই segmentation — সাশ্রয়ী।

## 14. Hands-on exercise

1. নিজের VM-এর প্রতিটি interface-এর MAC `l2_tool.py mac` দিয়ে বিশ্লেষণ করুন — কোনটি locally administered?
2. দুটি VM থাকলে একটিতে `sudo tcpdump -e -nn arp` চালিয়ে অন্যটি থেকে প্রথমবার ping করুন — ARP request ও reply-এর MAC লিখুন।
3. `arping -D` দিয়ে একটি অব্যবহৃত IP-তে duplicate detection চালান — কী ফল, কেন?
4. `l2_tool.py`-তে `oui` lookup যোগ করুন একটি ছোট local table থেকে (যেমন `08:00:27` → VirtualBox, `52:54:00` → QEMU/KVM, `02:42` prefix → Docker)। Test লিখুন।
5. `docker0` bridge থাকলে (Module 09-এর পরে) `bridge fdb show br docker0` দেখে container-এর MAC চিনুন।

## 15. Mini-project — "L2 health" অংশ

L02-01-এর layer checklist-এ L2 অংশ যোগ করুন: interface up কিনা, MAC, gateway-এর ARP অবস্থা (REACHABLE?), FAILED entry, duplicate IP সন্দেহ। `l2_tool.py neigh`-এর output দিয়ে একটি ছোট Bash wrapper লিখুন যা gateway-এর ARP FAILED হলে exit 1 দেয় — Project 1-এর network check-এর অংশ।

## 16. Interview প্রশ্ন

1. ARP কীভাবে কাজ করে? কেন broadcast request ও unicast reply?
2. Switch ও router-এর পার্থক্য কী?
3. Gratuitous ARP কী এবং failover-এ কেন দরকার?
4. VLAN কী? Access ও trunk port-এর পার্থক্য?
5. ARP spoofing কী এবং কীভাবে প্রতিরোধ করা যায়?
6. দূরের IP-তে packet পাঠাতে host কোন MAC ব্যবহার করে?
7. Cloud VPC-তে L2 কীভাবে আলাদা?

## 17. Self-assessment প্রশ্ন

1. অফিস-ফ্লোর analogy কোথায় মেলে না?
2. `0x52`-এর U/L bit হাতে বের করুন।
3. VLAN ২০, priority ৫-এর tag `8100a014` কীভাবে হলো, bit ধরে দেখান।
4. Section 5-এ কিছু app server কাজ করছিল, কিছু করছিল না — কেন?
5. নমুনার দ্বিতীয় সতর্কতা কেন false positive?
6. Cloud-এ gratuitous ARP-ভিত্তিক failover কেন কাজ করে না?

## 18. সংক্ষিপ্ত সারাংশ

- MAC = ৪৮-bit L2 ঠিকানা; I/G ও U/L bit; broadcast `ff:ff:..`।
- Switch source MAC থেকে শেখে; অজানা/broadcast-এ flood; broadcast domain = VLAN/subnet।
- ARP: IP → MAC (broadcast প্রশ্ন, unicast উত্তর), cache-এ থাকে; gratuitous ARP failover-এ; authentication নেই।
- দূরের গন্তব্যে gateway-এর MAC; L2 প্রতি hop-এ বদলায়।
- VLAN = logical আলাদা L2; 802.1Q ৪-byte tag, VID ১–৪০৯৪; cloud-এ L2 hypervisor-নিয়ন্ত্রিত।

## 19. Completion checklist

- [ ] `ip -br link`, `ip neigh`, `bridge fdb` পড়তে পারি
- [ ] tcpdump-এ ARP request/reply নিজে দেখেছি
- [ ] `l2_tool.py`-এর তিনটি command চালিয়েছি ও false positive ব্যাখ্যা করেছি
- [ ] (VM-এ) VLAN interface তৈরি ও মুছেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- RFC 826 — Ethernet Address Resolution Protocol: https://www.rfc-editor.org/rfc/rfc826
- RFC 4861 — Neighbor Discovery for IPv6: https://www.rfc-editor.org/rfc/rfc4861
- RFC 5227 — IPv4 Address Conflict Detection (gratuitous ARP): https://www.rfc-editor.org/rfc/rfc5227
- `ip-neighbour(8)`: https://man7.org/linux/man-pages/man8/ip-neighbour.8.html
- `arping(8)` (iputils): https://man7.org/linux/man-pages/man8/arping.8.html
- IEEE 802.1Q (VLAN) standard overview: https://standards.ieee.org/

---

**পরের lesson:** L02-03 — IPv4, IPv6, CIDR ও subnetting
