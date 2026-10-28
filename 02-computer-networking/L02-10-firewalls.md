# L02-10 — Firewall: nftables, ufw (Fedora-তে firewalld), security group ও NACL

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-03 — CIDR](L02-03-ip-addressing-cidr.md), [L02-05 — TCP, UDP](L02-05-tcp-udp-sockets.md), [L02-09 — ICMP](L02-09-dhcp-icmp-mtu.md) |
| **Label** | 🎩 Fedora-তে firewalld |
| **Tested** | `fw_sim.py`: ৯টি test পাস — rule parse, first-match, stateful conntrack, NACL ephemeral-port ফাঁদ ও rule-number ক্রম, security group, audit (Python 3.14, Windows)। `demo`, `audit`, `eval` চালানো হয়েছে — output Section 9-এ। `ufw`, `nft`, `firewall-cmd`, `conntrack` **Ubuntu/Fedora-তে চালানো হয়নি**; Section 9.3–9.5-এর command শুধু lab VM-এর জন্য। |

---

## 1. এই lesson-এ যা শিখবেন

- Firewall কী সিদ্ধান্ত নেয় এবং কোন তথ্যের ভিত্তিতে (5-tuple, connection state)।
- **Ordered first-match** rule ও **default policy** (default deny)।
- **Stateful** (conntrack) বনাম **stateless** firewall — ফেরত traffic কেন আলাদা।
- Linux-এ স্তর: netfilter (kernel) → **nftables** (আধুনিক) / iptables (পুরোনো) → **ufw** (Ubuntu) / **firewalld** (Fedora)।
- Cloud-এ: **security group** (instance-স্তর, stateful, শুধু allow) বনাম **NACL** (subnet-স্তর, stateless, numbered, allow+deny)।
- Lockout ছাড়া নিরাপদে firewall পরিবর্তন।
- Python simulator দিয়ে rule evaluate ও audit (shadowed rule, internet-এ খোলা sensitive port)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Default-এ একটি server-এ যে service চলছে তা network-এর যে কেউ পৌঁছাতে পারে। Firewall ঠিক করে **কে, কোথা থেকে, কোন port-এ** পৌঁছাতে পারবে।

DevOps-এ দুই দিকেরই incident:

- **অতিরিক্ত খোলা:** Database, Redis, Elasticsearch, Docker API, বা LLM inference API (যেমন Ollama-র ১১৪৩৪) `0.0.0.0/0`-এ খোলা — Internet-এ স্বয়ংক্রিয় scanner মিনিটের মধ্যে খুঁজে পায়। Data leak, ransomware, বা বিনামূল্যে আপনার GPU ব্যবহার।
- **অতিরিক্ত বন্ধ:** নতুন rule-এ নিজের SSH আটকে যাওয়া (lockout); ICMP block-এ PMTUD ভাঙা (L02-09); NACL-এ ফেরত traffic আটকে "connection timeout"।
- **বিভ্রান্তি:** Host firewall, security group, NACL, Kubernetes NetworkPolicy — চারটি স্তর; কোনটিতে আটকাচ্ছে?

## 3. সহজ ভাষায় পরিচয়

**Firewall** = packet-এর বৈশিষ্ট্য দেখে **accept / drop / reject** সিদ্ধান্ত।

| দেখে | উদাহরণ |
|---|---|
| Protocol | tcp, udp, icmp |
| Source/destination IP (CIDR) | `10.0.0.0/8` থেকে |
| Destination port | ২২, ৪৪৩ |
| Interface | `eth0` থেকে আসা |
| **Connection state** | new, established, related, invalid |

**Drop বনাম reject:** drop = নিঃশব্দে ফেলে দেওয়া (client timeout পর্যন্ত অপেক্ষা করে); reject = সাথে সাথে "না" (TCP RST বা ICMP unreachable → client "connection refused" পায়)। Internet-মুখী দিকে সাধারণত drop; internal network-এ reject দ্রুত ব্যর্থতা দেয়, debug সহজ।

**মূল নিয়ম:**

1. **Rule উপর থেকে নিচে** দেখা হয়; **প্রথম যেটি মেলে সেটিই সিদ্ধান্ত** (host firewall, NACL)।
2. কেউ না মিললে **default policy** — নিরাপদ পছন্দ `drop` (**default deny**: যা স্পষ্টভাবে অনুমোদিত নয় তা নিষিদ্ধ)।
3. **Stateful** firewall মনে রাখে "এই connection আমরাই শুরু করেছি" — উত্তর স্বয়ংক্রিয়ভাবে অনুমোদিত (`ct state established`)।

**চারটি পরিচিত firewall-এর তুলনা:**

| | Host (nftables/ufw/firewalld) | AWS Security Group | AWS NACL |
|---|---|---|---|
| কোথায় | OS kernel-এ | প্রতিটি network interface (instance) | Subnet-এর সীমানায় |
| State | Stateful (সাধারণত) | **Stateful** | **Stateless** |
| Rule ধরন | Accept/drop/reject | **শুধু allow** | Allow ও deny |
| ক্রম | উপর থেকে, first match | ক্রম নেই — যেকোনো allow মিললেই যথেষ্ট | **নম্বর** অনুযায়ী, ছোট আগে |
| Default | আপনি ঠিক করেন | Inbound সব deny, outbound সব allow | Default NACL সব allow; custom NACL সব deny |
| Source হিসেবে আরেকটি group | — | **হ্যাঁ** ("app-sg থেকে") | না, শুধু CIDR |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিস ভবনের নিরাপত্তা

- **NACL** = এলাকার প্রধান গেট — প্রত্যেক গাড়ি **ঢোকা ও বের হওয়া দুইবার** পরীক্ষা, তালিকা নম্বর ধরে ("১০০: নীল গাড়ি ঢুকতে পারবে")। গেটের প্রহরীর স্মৃতি নেই — যে গাড়ি ঢুকল, সে বের হতে চাইলে **আবার** তালিকায় থাকতে হবে।
- **Security group** = প্রতিটি অফিসের দরজার রিসেপশনিস্ট — **শুধু অতিথি তালিকা** (allow) রাখেন, যাকে ঢুকতে দিয়েছেন তাকে বের হতে আবার জিজ্ঞাসা করেন না (stateful)।
- **Host firewall** = অফিসের ভেতরে প্রতিটি ঘরের তালা — শেষ স্তর।
- **Default deny** = তালিকায় নাম না থাকলে প্রবেশ নিষেধ।

### Analogy কোথায় মেলে না

- প্রহরী মানুষ দেখে চিনতে পারেন। Firewall শুধু **ঠিকানা ও port** দেখে — IP জাল করা যায় (বিশেষত UDP-তে), আর একটি অনুমোদিত IP-র machine compromise হলে firewall কিছু করতে পারে না। তাই firewall একমাত্র স্তর নয় — authentication ও encryption (L02-08) লাগে।
- ভবনে "উত্তর" বলে কিছু নেই। Network-এ প্রতিটি TCP connection-এর **দুটি দিক** — client-এর দিকের port এলোমেলো (ephemeral, ৩২৭৬৮–৬০৯৯৯ Linux-এ, L02-05)। Stateless firewall-এ এই এলোমেলো port-গুলোর জন্য rule লাগে — Section 5।
- Application-স্তরের আক্রমণ (SQL injection, prompt injection) port ৪৪৩ দিয়েই আসে — network firewall-এর কাছে এগুলো বৈধ traffic। এর জন্য WAF ও application security (Module 19)।

## 5. Real-world engineering scenario — NACL-এর পরে site বন্ধ

**পরিস্থিতি:** Security audit-এর পরে একজন engineer public subnet-এ কঠোর custom NACL বসালেন: inbound rule 100 = TCP ৪৪৩ allow, outbound rule 100 = TCP ৪৪৩ allow ("শুধু HTTPS")। সাথে সাথে website-এ সব request timeout। Security group ঠিক আছে, instance ঠিক আছে।

**বিশ্লেষণ** (`fw_sim.py demo` ঠিক এটাই দেখায়):

```text
Client 203.0.113.7:51514 ──► server 10.0.1.20:443     inbound: dport 443 → rule 100 ALLOW ✓
Server 10.0.1.20:443 ──► client 203.0.113.7:51514     outbound: dport 51514 → rule 100 মেলে না
                                                       → rule * DENY ✗
```

NACL **stateless** — উত্তরটি একটি স্বাধীন packet, যার destination port client-এর **ephemeral port** (৫১৫১৪), ৪৪৩ নয়।

**সমাধান:** outbound-এ TCP ১০২৪–৬৫৫৩৫ allow (client OS অনুযায়ী ephemeral range ভিন্ন হয়)। এবং পুনর্বিবেচনা: সূক্ষ্ম নিয়ন্ত্রণ **security group**-এ রাখুন (stateful, পরিচালনা সহজ); NACL মোটা দাগের নিয়মে (যেমন একটি পরিচিত খারাপ CIDR deny) ব্যবহার করুন।

**শিক্ষা:** Stateless filter-এ সবসময় **দুই দিক** ভাবুন। এবং firewall পরিবর্তন production-এ আগে staging-এ পরীক্ষা ও rollback পরিকল্পনা সহ।

## 6. Diagram — স্তরগুলো ও Linux-এর packet পথ

```text
Internet
   │
   ▼
┌──────────── VPC ────────────────────────────────────────────┐
│  ┌──── NACL (subnet সীমানা, stateless, numbered) ────────┐  │
│  │   ┌── Security group (ENI, stateful, allow-only) ──┐  │  │
│  │   │  ┌────────── Linux instance ─────────────────┐  │  │  │
│  │   │  │ netfilter hooks:                          │  │  │  │
│  │   │  │  prerouting → [routing] → input → process │  │  │  │
│  │   │  │                     └→ forward → postrouting (router/NAT/container) │
│  │   │  │  process → output → postrouting           │  │  │  │
│  │   │  │  (nftables/ufw/firewalld rule এই hook-এ)  │  │  │  │
│  │   │  │  ┌─ Kubernetes NetworkPolicy / Docker ─┐  │  │  │  │
│  │   │  │  │  (এরাও netfilter/eBPF ব্যবহার করে)  │  │  │  │  │
│  │   │  │  └─────────────────────────────────────┘  │  │  │  │
│  │   │  └───────────────────────────────────────────┘  │  │  │
│  │   └─────────────────────────────────────────────────┘  │  │
│  └────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
একটি packet-কে **প্রতিটি** স্তর পার হতে হবে — যেকোনো একটিতে আটকালে পৌঁছাবে না।
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| 5-tuple | protocol, src IP, src port, dst IP, dst port |
| Accept / drop / reject | অনুমতি / নিঃশব্দে ফেলা / ফেরত "না" |
| Default policy | কোনো rule না মিললে সিদ্ধান্ত |
| Default deny | যা অনুমোদিত নয় তা নিষিদ্ধ |
| Stateful / conntrack | Connection মনে রাখা; উত্তর স্বয়ংক্রিয়ভাবে অনুমোদিত |
| Stateless | প্রতিটি packet স্বাধীন বিচার |
| Ephemeral port | Client-এর অস্থায়ী source port |
| netfilter | Linux kernel-এর packet filtering framework |
| nftables / iptables | netfilter-এর আধুনিক / পুরোনো user-space interface |
| ufw / firewalld | Ubuntu / Fedora-র সহজ front-end |
| Zone (firewalld) | Interface-এর বিশ্বাসের স্তর অনুযায়ী rule-সমষ্টি |
| Security group | Cloud-এ instance-স্তরের stateful firewall |
| NACL | Cloud-এ subnet-স্তরের stateless firewall |
| Shadowed rule | আগের rule সব ক্ষেত্র ঢেকে ফেলায় যে rule কখনো পৌঁছায় না |
| Egress filtering | বের হওয়া traffic নিয়ন্ত্রণ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 netfilter ও conntrack

Linux kernel-এ packet-এর পথে কয়েকটি **hook** (prerouting, input, forward, output, postrouting)। nftables-এর chain এই hook-এ লাগানো থাকে। **conntrack** প্রতিটি flow-এর একটি entry রাখে (`/proc/net/nf_conntrack` বা `conntrack -L`) — তাই `ct state established,related accept` একটি rule-এই সব উত্তর অনুমোদন করে। Conntrack table-এর সীমা আছে (`nf_conntrack_max`); ভরে গেলে নতুন connection drop হয় — dmesg-এ `nf_conntrack: table full`, high-traffic server-এ বাস্তব সমস্যা।

### 8.2 Ubuntu: ufw → nftables

Ubuntu-তে `ufw` একটি সহজ interface; ভেতরে iptables-nft দিয়ে nftables rule তৈরি করে। Default: incoming deny, outgoing allow — কিন্তু **ufw default-এ বন্ধ (inactive)** থাকে।

> **Fedora-তে:** `firewalld` default-এ **চালু** থাকে, **zone**-ভিত্তিক (`public`, `internal`, `trusted`…)। প্রতিটি interface একটি zone-এ; service/port zone-এ যোগ হয়। Command: `firewall-cmd`। ভেতরে nftables। ufw ও firewalld একসাথে চালাবেন না।

### 8.3 Docker ও firewall — একটি গুরুত্বপূর্ণ ফাঁদ

Docker container-এর port publish করলে (`-p 8080:80`) Docker নিজে netfilter-এ NAT ও forward rule যোগ করে, যা **ufw-এর input rule-কে পাশ কাটিয়ে যায়** — ufw-এ port বন্ধ থাকলেও container-এর port Internet থেকে পৌঁছানো যায়। সমাধান: `-p 127.0.0.1:8080:80` (শুধু localhost-এ bind), বা Docker-এর `DOCKER-USER` chain-এ rule (Module 10)। একই কারণে **service-কে প্রয়োজনের বেশি address-এ bind করবেন না** (L02-05-এর `0.0.0.0` বনাম `127.0.0.1`) — firewall দ্বিতীয় স্তর, প্রথম স্তর নয়।

### 8.4 Cloud

- Security group: rule-এর source হতে পারে **আরেকটি security group** — "যেকোনো instance যার উপর `app-sg` আছে" — IP বদলালেও rule ঠিক থাকে। এটাই cloud-এ পছন্দের ধরন (L02-14, Module 08)।
- NACL: rule নম্বর ফাঁক রেখে দিন (১০০, ২০০…) যেন মাঝে নতুন rule ঢোকানো যায়।
- GCP firewall rule ও Azure NSG-ও stateful; বিস্তারিত পার্থক্য Module 08-এ।

## 9. Practical demonstration

File: [`code/L02-10/fw_sim.py`](code/L02-10/fw_sim.py), [`sample-rules.txt`](code/L02-10/sample-rules.txt) (হাতে তৈরি উদাহরণ — একটি GPU inference server, ইচ্ছাকৃত ভুল সহ)। Simulator কোনো আসল firewall স্পর্শ করে না।

### 9.1 Stateful বনাম stateless

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-10
python3 fw_sim.py demo
```

**আসল output:**

```text
client 203.0.113.7:51514 → web server 10.0.1.20:443, then the reply 10.0.1.20:443 → client:51514

Security group (stateful):  request ALLOW;  reply ALLOW automatically (connection tracked)
NACL v1 (outbound only 443)      request ACCEPT (rule 100);  reply DROP (rule * (implicit deny))
NACL v2 (outbound 1024-65535)    request ACCEPT (rule 100);  reply ACCEPT (rule 100)

Host firewall (policy drop, accept established, accept 22):
  unsolicited 93.184.215.14:443 → :40000  DROP   (policy drop  [state new])
  after our outbound connection        ACCEPT (line 2: accept state established  [state established])
```

শেষ অংশ: একই packet — আমরা আগে connection শুরু না করলে drop, করলে conntrack-এর কারণে accept।

### 9.2 Rule evaluate ও audit

```bash
python3 fw_sim.py eval sample-rules.txt --src 10.20.1.5 --dport 22
python3 fw_sim.py eval sample-rules.txt --src 198.51.100.7 --dport 22
python3 fw_sim.py eval sample-rules.txt --src 198.51.100.7 --dport 11434
python3 fw_sim.py audit sample-rules.txt; echo "exit=$?"
```

**আসল output:**

```text
ACCEPT  by line 6: accept proto tcp dport 22 src 10.0.0.0/8  [state new]
DROP  by policy drop  [state new]
ACCEPT  by line 10: accept proto tcp dport 11434  [state new]

- line 8 CONFLICT (never reached): shadowed by line 6 (accept proto tcp dport 22 src 10.0.0.0/8)
- line 9 redundant: shadowed by line 7 (accept proto tcp dport 80,443)
- line 10: Ollama LLM API (11434) open to the whole internet
8 rules, policy drop, 3 finding(s)
exit=1
```

**তিনটি ভুল:**

1. Line 8-এর উদ্দেশ্য ছিল `10.20.0.0/16`-কে SSH থেকে আটকানো, কিন্তু `10.20.1.5` **accept** হলো — কারণ line 6-এর `10.0.0.0/8` আগে মেলে। **First match wins**: নির্দিষ্ট (সংকীর্ণ) deny rule সবসময় সাধারণ allow-এর **আগে** রাখতে হবে।
2. Line 9 অপ্রয়োজনীয় — ক্ষতিকর নয়, কিন্তু rule set বড় ও বিভ্রান্তিকর করে।
3. LLM inference API সারা Internet-এ খোলা — কেউ বিনামূল্যে আপনার GPU চালাবে, বা model/data নিয়ে যাবে। `src` সীমিত করুন, বা service-কে `127.0.0.1`-এ bind করে authenticated reverse proxy-র পেছনে রাখুন।

Node exporter (৯১০০) monitoring subnet-এ সীমিত বলে audit কিছু বলেনি — সঠিক আচরণ।

### 9.3 Ubuntu: ufw (⚠️ lab VM-এ, console access রেখে)

**Lockout এড়ানোর নিয়ম:** remote machine-এ firewall চালু করার **আগে** SSH allow করুন, এবং VM console (hypervisor/cloud serial console) হাতের কাছে রাখুন।

```bash
sudo ufw status verbose                    # সাধারণত "inactive"
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow from 10.0.0.0/8 to any port 22 proto tcp     # আগে SSH!
sudo ufw allow 80,443/tcp
sudo ufw enable
sudo ufw status numbered                   # নম্বরসহ — ক্রম গুরুত্বপূর্ণ
sudo ufw insert 1 deny from 10.20.0.0/16 to any port 22 proto tcp   # নির্দিষ্ট deny উপরে
sudo ufw delete 3                          # নম্বর দেখে মুছুন
sudo nft list ruleset | less               # ufw আসলে কী তৈরি করল
```

### 9.4 nftables সরাসরি

```bash
sudo nft list ruleset
# একটি ছোট ruleset file (lab VM-এ, ufw বন্ধ রেখে):
cat > /tmp/lab.nft <<'EOF'
table inet lab {
  chain input {
    type filter hook input priority 0; policy drop;
    ct state established,related accept
    ct state invalid drop
    iif lo accept
    ip protocol icmp accept
    meta l4proto ipv6-icmp accept
    tcp dport 22 ip saddr 10.0.0.0/8 accept
    tcp dport { 80, 443 } accept
    counter
  }
}
EOF
sudo nft -c -f /tmp/lab.nft                # -c = শুধু syntax check (dry run)
sudo nft -f /tmp/lab.nft
sudo nft list table inet lab               # counter দেখে কত packet policy-তে গেল
sudo nft delete table inet lab             # lab শেষে সরান
sudo conntrack -L | head                   # conntrack entry (package: conntrack)
```

**Safety net:** remote-এ পরীক্ষা করলে আগে একটি স্বয়ংক্রিয় rollback চালু রাখুন, যেমন `sudo systemd-run --on-active=5m nft delete table inet lab` — সব ঠিক থাকলে timer বাতিল করুন (`systemctl list-timers`, L01-11)।

### 9.5 Fedora: firewalld

> **Fedora-তে:**
>
> ```bash
> sudo firewall-cmd --state
> sudo firewall-cmd --get-active-zones
> sudo firewall-cmd --zone=public --list-all
> sudo firewall-cmd --zone=public --add-service=https              # runtime (reboot-এ হারায়)
> sudo firewall-cmd --zone=public --add-port=8080/tcp
> sudo firewall-cmd --runtime-to-permanent                        # যাচাইয়ের পরে স্থায়ী
> sudo firewall-cmd --zone=public --add-rich-rule='rule family=ipv4 source address=10.0.0.0/8 service name=ssh accept' --permanent
> sudo firewall-cmd --reload
> ```
>
> Runtime বনাম permanent-এর ভাগ নিজেই একটি safety net: runtime-এ পরীক্ষা, ঠিক থাকলে permanent।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_fw_sim.py`](code/L02-10/test_fw_sim.py)-এর ৯টি test: sample parse ও ৫ ধরনের ভুল input, first-match (line 8 কখনো পৌঁছায় না), conntrack, NACL ephemeral ফাঁদ, NACL নম্বর-ক্রম (list-এর ক্রম নয়), security group allow-only, audit-এর তিনটি finding (এবং সীমিত rule-এ false positive নেই), CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `Rule.matches` | প্রতিটি শর্ত; `None` = যেকোনো | nftables-এ উল্লেখ না করা field যেকোনো মান মেলে |
| `HostFirewall.inbound` | প্রথম match → action, নইলে policy | First-match semantics |
| `conntrack` set + `outbound` | প্রত্যাশিত উত্তরের 5-tuple রাখে | Stateful-এর মূল ধারণা |
| `Nacl.check` `sorted(...)` | নম্বর অনুযায়ী | Cloud NACL-এর নিয়ম; শেষে implicit deny |
| `SecurityGroup.allows` `any(...)` | ক্রম অর্থহীন | Allow-only হলে ক্রম ফল বদলায় না |
| `covers(a, b)` | `subnet_of`, port range ⊇, state ⊇ | Shadowed rule খোঁজা |
| `SENSITIVE` | পরিচিত ঝুঁকিপূর্ণ port, LLM API সহ | Internet scanner এগুলোই খোঁজে |

**সীমাবদ্ধতা:** interface, destination, output/forward chain, NAT, rate limit, IPv6-নির্দিষ্ট দিক নেই; `covers` আংশিক overlap ধরে না (শুধু সম্পূর্ণ ঢাকা)। শেখার model — আসল rule-এর সত্য `nft list ruleset` ও cloud API।

**Python কেন এখানে, কোথায় নয়:** rule-এর **policy-as-code audit** (CI-তে security group/ruleset যাচাই) Python-এর উপযুক্ত কাজ (Module 19-এ OPA/Checkov-এর মতো tool)। Packet filtering নিজে kernel-এর কাজ — Python-এ কখনো নয়।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `fw_sim.py audit sample-rules.txt` | ৩টি finding, exit ১ |
| `ufw status numbered` (VM) | SSH rule অন্যগুলোর আগে |
| `nft -c -f` | কোনো output নেই = syntax ঠিক |
| VM-এ অন্য machine থেকে `nc -zv VM 8080` | Firewall-এ বন্ধ থাকলে timeout (drop) বা refused (reject) |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Connection timeout (refused নয়) | কোনো স্তরে drop | প্রতিটি স্তর আলাদা পরীক্ষা: instance-এর ভেতর থেকে `curl localhost`, একই subnet থেকে, বাইরে থেকে | যে স্তরে আটকায় সেখানে rule |
| Connection refused | Firewall reject বা service চলছে না/ভুল address-এ | `ss -ltnp` (L02-05) | Service bind address |
| Request যায়, উত্তর আসে না | Stateless NACL-এ ephemeral port | NACL outbound rule | ১০২৪–৬৫৫৩৫ allow |
| Deny rule কাজ করে না | আগের allow rule shadow করছে | `ufw status numbered`, `fw_sim.py audit` | নির্দিষ্ট deny উপরে |
| ufw-এ বন্ধ, তবু container port খোলা | Docker-এর নিজের rule | বাইরে থেকে পরীক্ষা | `127.0.0.1:` bind বা `DOCKER-USER` |
| নিজের SSH আটকে গেছে | SSH allow-এর আগে deny default | — | Console থেকে ঠিক; ভবিষ্যতে rollback timer |
| মাঝে মাঝে নতুন connection drop | Conntrack table full | `dmesg`, `conntrack -C` বনাম `nf_conntrack_max` | Limit বাড়ান, timeout কমান |
| বড় packet হারায় | ICMP block (L02-09) | DF ping | ICMP frag-needed allow |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Default deny; least privilege (নির্দিষ্ট CIDR বা security group, `0.0.0.0/0` শুধু public web port-এ); admin port (SSH) Internet-এ না খুলে VPN/bastion/SSM-এর মাধ্যমে (L02-11); egress filtering (compromised server কোথায় data পাঠাতে পারবে); defense in depth — bind address + host firewall + security group; rule পরিবর্তন version control-এ ও review-সহ (IaC, Module 07); firewall log (drop counter) monitoring। **কখনো** production-এ পরীক্ষা ছাড়া firewall flush করবেন না।
- **Performance:** nftables set/map দিয়ে হাজারো IP-তে O(1) lookup (লম্বা rule list-এর বদলে); conntrack-এর memory ও table size; খুব high-traffic-এ stateless বা eBPF/XDP-ভিত্তিক filtering।
- **Cost:** Security group ও NACL বিনামূল্যে; managed network firewall/WAF service ঘণ্টা ও data অনুযায়ী বিল (Module 08)। খোলা port দিয়ে compromise বা GPU চুরির খরচ অনেক বেশি।

## 14. Hands-on exercise

1. `sample-rules.txt` ঠিক করুন যেন audit-এ কোনো finding না থাকে, কিন্তু উদ্দেশ্য (10.20.0.0/16-কে SSH থেকে আটকানো) পূরণ হয়। `eval` দিয়ে প্রমাণ করুন।
2. `fw_sim.py`-তে আংশিক overlap সতর্কতা যোগ করুন: পরের rule-এর কিছু অংশ আগের rule-এর বিপরীত action-এ ঢাকা পড়লে "partially shadowed"। Test লিখুন।
3. Ubuntu VM-এ Section 9.3 অনুসরণ করুন; দ্বিতীয় VM থেকে `nc -zv` দিয়ে প্রতিটি rule যাচাই করুন। তারপর একটি port-এ `reject` ও আরেকটিতে `deny` দিয়ে client-এর আচরণ (সময়) তুলনা করুন।
4. Docker থাকলে: `ufw` চালু রেখে `docker run -d -p 8081:80 nginx` — দ্বিতীয় machine থেকে পৌঁছানো যায় কি? তারপর `-p 127.0.0.1:8081:80` দিয়ে আবার। (শেষে container মুছুন।)
5. Fedora VM থাকলে Section 9.5 — runtime rule যোগ করে `--reload` দিন; rule কি টিকে থাকে? কেন?

## 15. Mini-project — Security group linter

একটি JSON file-এ (হাতে তৈরি, AWS `describe-security-groups` output-এর মতো গঠন) কয়েকটি security group। Linter: (১) `0.0.0.0/0` বা `::/0`-এ খোলা sensitive port, (২) সব port খোলা (`-1` protocol), (৩) কোনো instance-এ সংযুক্ত নয় এমন group (ঐচ্ছিক field), (৪) একই rule-এর পুনরাবৃত্তি — finding থাকলে exit ১, যেন CI-তে pull request আটকানো যায়। `fw_sim.py`-এর `SENSITIVE` ও `covers` পুনর্ব্যবহার করুন। Module 07-এ Terraform plan-এর উপর এবং Module 19-এ policy-as-code হিসেবে এটি আবার আসবে।

## 16. Interview প্রশ্ন

1. Stateful ও stateless firewall-এর পার্থক্য কী? AWS-এ কোনটি কোনটি?
2. NACL-এ inbound ৪৪৩ allow করার পরেও site কেন timeout দিতে পারে?
3. Security group-এ rule-এর ক্রম গুরুত্বপূর্ণ কি? NACL-এ?
4. Drop ও reject-এর পার্থক্য এবং কখন কোনটি?
5. Remote server-এ firewall পরিবর্তন করার সময় lockout কীভাবে এড়াবেন?
6. Docker ufw-কে কীভাবে পাশ কাটায়?
7. "Database শুধু app server থেকে" — cloud-এ কীভাবে লিখবেন?
8. Connection timeout হচ্ছে — কোন স্তরে আটকাচ্ছে কীভাবে বের করবেন?

## 17. Self-assessment প্রশ্ন

1. অফিস ভবন analogy কোথায় মেলে না (তিনটি বিষয়)?
2. `sample-rules.txt`-এর line 8 কেন কাজ করে না?
3. `demo`-র শেষ অংশে একই packet দুবার ভিন্ন সিদ্ধান্ত পায় কেন?
4. Ubuntu ও Fedora-র default firewall-এর দুটি পার্থক্য।
5. Lockout এড়ানোর দুটি কৌশল।

## 18. সংক্ষিপ্ত সারাংশ

- Firewall: 5-tuple + state দেখে accept/drop/reject; **first match wins**; **default deny**।
- Stateful (conntrack, security group) উত্তর মনে রাখে; stateless (NACL) দুই দিকেই rule চায় — ephemeral port।
- Linux: netfilter → nftables; Ubuntu-তে ufw (default inactive), Fedora-তে firewalld (default চালু, zone)।
- নির্দিষ্ট deny সাধারণ allow-এর আগে; audit-এ shadowed rule খুঁজুন।
- Defense in depth: সঠিক bind address + host firewall + security group; Docker-এর bypass মনে রাখুন।
- পরিবর্তনের আগে SSH allow, console access, rollback timer।

## 19. Completion checklist

- [ ] `fw_sim.py demo` ব্যাখ্যা করতে পারি (তিনটি অংশ)
- [ ] `sample-rules.txt` ঠিক করেছি (Exercise ১)
- [ ] Ubuntu VM-এ ufw ও nftables lab করেছি, lab table মুছেছি
- [ ] Docker-ufw bypass নিজে দেখেছি (Docker থাকলে)
- [ ] `python3 -m unittest -v`-এ ৯টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- nftables wiki: https://wiki.nftables.org/
- Ubuntu Server — Firewall (ufw): https://documentation.ubuntu.com/server/how-to/security/firewalls/
- `ufw(8)` manpage: https://manpages.ubuntu.com/manpages/noble/man8/ufw.8.html
- firewalld documentation: https://firewalld.org/documentation/
- AWS — Security groups: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- AWS — Network ACLs: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- Docker — Packet filtering and firewalls: https://docs.docker.com/engine/network/packet-filtering-firewalls/

---

**পরের lesson:** L02-11 — SSH tunnel, VPN, WireGuard ও zero-trust connectivity
