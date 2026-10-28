# L08-05 — Security group ও network ACL

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L08-04 — VPC](L08-04-vpc-subnet-route-gateway.md), [L02-10 — Firewall](../02-computer-networking/L02-10-firewalls.md), [L02-16 — Troubleshooting](../02-computer-networking/L02-16-troubleshooting-toolkit.md) |
| **Label** | 💰 Security group ও NACL চার্জমুক্ত; যে instance বা load balancer-এ লাগাবেন, সেটা চার্জযোগ্য। VPC Reachability Analyzer প্রতি analysis-এ চার্জযোগ্য (pricing page) |
| **Tested** | `sg_reach.py`: ৬টি test পাস (Python 3.14.5, Windows)। Input **হাতে তৈরি** — `describe-security-groups` ও `describe-network-acls`-এর রূপে। মূল্যায়নের নিয়ম (SG stateful ও সব rule একসাথে, NACL stateless ও সংখ্যার ক্রমে, একই subnet-এর ভেতরে NACL নয়) AWS VPC documentation অনুযায়ী। এটা **শেখার জন্য সরল মডেল** — route table, prefix list, VPC Reachability Analyzer-এর সাথে **মেলানো হয়নি**; আসল AWS-এ চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Security group (SG): instance বা ENI-স্তরের stateful firewall, শুধু allow।
- Network ACL (NACL): subnet-স্তরের stateless firewall, numbered allow/deny।
- **SG-এর ভেতরে অন্য SG-এর reference** — IP নয়, ভূমিকা দিয়ে নিয়ম।
- Stateless-এর ফাঁদ: ফেরত traffic-এর ephemeral port।
- কেন firewall-এ আটকানো traffic **timeout** দেয়, "connection refused" নয়।
- `sg_reach.py`: একটি flow কোন ধাপে আটকায়; `audit`: সারা পৃথিবীর জন্য খোলা SSH/DB port।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L08-04-এর route table বলে packet **কোথায় যেতে পারে**; SG ও NACL বলে **যেতে দেওয়া হবে কিনা**। পরিচিত ঘটনা:

- Debug করতে SG-তে "সাময়িক" `22 from 0.0.0.0/0`, যা তিন মাস পরেও রয়ে গেছে।
- Load balancer-এর health check app-এ পৌঁছায় না; target "unhealthy"; সবাই app-এর code দেখছে, অথচ সমস্যা SG-তে।
- কেউ "নিরাপত্তা বাড়াতে" কাস্টম NACL দিল, যেখানে শুধু 443 inbound allow; সব connection timeout — কারণ ফেরত traffic-এর port বন্ধ।
- Database-এর SG-তে একটি মুছে-ফেলা bastion SG-এর reference রয়ে গেছে।

## 3. সহজ ভাষায় পরিচয়

| | Security group | Network ACL |
|---|---|---|
| কোথায় | ENI/instance (load balancer, RDS-ও) | Subnet-এর সীমানা |
| State | **Stateful** — ফেরত নিজে থেকে allowed | **Stateless** — ফেরতের আলাদা নিয়ম |
| নিয়ম | শুধু allow | Allow ও deny |
| ক্রম | সব নিয়ম একসাথে; যেকোনো একটি মিললেই allow | সবচেয়ে ছোট সংখ্যা আগে; প্রথম মিলই চূড়ান্ত |
| Default (নতুন) | Inbound কিছু নয়, outbound সব | Default NACL সব allow; নতুন কাস্টম NACL সব deny |
| Source | CIDR, **অন্য SG**, prefix list | শুধু CIDR |

**Linux-এর তুলনা (L02-10):**

- SG ≈ nftables-এ `ct state established,related accept` + নির্দিষ্ট port allow — connection tracking আছে।
- NACL ≈ conntrack ছাড়া stateless filter — প্রতিটি packet আলাদাভাবে বিচার।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিস ভবনের দুই স্তরের নিরাপত্তা

- **NACL** = তলার প্রবেশদ্বারের রক্ষী। তার হাতে একটি নম্বর-দেওয়া তালিকা; উপর থেকে পড়ে প্রথম যে লাইন মেলে, সেটাই মানে। ভেতরে ঢোকা ও বেরোনো — দুই দিকেই আলাদা তালিকা।
- **SG** = প্রতিটি ঘরের দরজার রিসেপশনিস্ট। তিনি মনে রাখেন কে ভেতরে গেছে, তাই তার ফেরার সময় আবার পরীক্ষা নেই।
- **SG reference** = "এই ঘরে শুধু ALB-এর ব্যাজধারী আসতে পারবে" — নাম দিয়ে নয়, ব্যাজ দিয়ে।

### Analogy কোথায় মেলে না

- **রক্ষী "না" বললে ফিরিয়ে দেন, আপনি জানেন।** SG বা NACL packet নীরবে ফেলে দেয়। Client কোনো উত্তর পায় না, অপেক্ষা করে, তারপর **timeout**। "Connection refused" মানে উল্টো — packet host-এ পৌঁছেছে, কিন্তু সেই port-এ কেউ শুনছে না (L02-16)। এই পার্থক্যই প্রথম diagnosis।
- **রক্ষী ফেরার পথে আপনাকে চেনেন।** NACL চেনে না। Server-এর উত্তর client-এর ephemeral port-এ (যেমন 50000) যায়, তাই সেই port-এর নিয়ম দুই subnet-এর NACL-এই লাগে।
- **একই তলার ঘরে যেতে রক্ষী লাগে।** NACL শুধু subnet-এর সীমানায়; একই subnet-এর দুটি instance-এর মধ্যে NACL প্রযোজ্য নয় (test-এ যাচাই)।

## 5. Real-world engineering scenario — "সব timeout, কিন্তু SG ঠিক আছে"

Security review-এর পরে একজন engineer public subnet-এ কাস্টম NACL লাগালেন: inbound শুধু 443 allow, outbound সব allow। কয়েক মিনিটে ALB-এর সব target unhealthy, user-রা 502/504 পেতে লাগল। SG বদলায়নি।

`sg_reach.py` দিয়ে ALB → app flow — নমুনার NACL-এ এই পরিবর্তন করে (public subnet-এর নতুন NACL `acl-public-new`) আসল output:

```text
DROP   flow
         ok  source SG egress to 10.20.16.5:8000: sg-alb ← sg-app
         ok  source NACL outbound: acl-public-new rule 100 allow
         ok  destination NACL inbound: acl-app rule 100 allow
         ok  destination SG inbound from 10.20.0.10: sg-app ← sg-alb
         ok  return: destination NACL outbound to port 50000: acl-app rule 100 allow
         XX  return: source NACL inbound on port 50000: acl-public-new rule * deny
         → client sees a TIMEOUT (dropped silently), not 'connection refused'
1 flow(s), 0 unexpected
```

একই পরিস্থিতি `test_stateless_return_path`-এ স্থায়ীভাবে যাচাই হয়।

**কারণ:** app-এর উত্তর ALB-এর ephemeral port-এ ফিরছে, আর public subnet-এর নতুন NACL তা inbound-এ আটকাচ্ছে।

**সমাধান:** inbound-এ `1024-65535` allow (VPC CIDR বা যেখান থেকে উত্তর আসে)।

**শিক্ষা:**

- NACL-এর পরিবর্তন সবচেয়ে বেশি অপ্রত্যাশিত timeout ঘটায়।
- প্রধান নিয়ন্ত্রণ SG-তে রাখুন; NACL মোটা দাগের guardrail হিসেবে (যেমন একটি CIDR পুরো ব্লক)।

## 6. Diagram — packet-এর পথে পরীক্ষা

```text
 ALB (sg-alb, subnet-pub-a)                                app EC2 (sg-app, subnet-app-a)
   │ ① sg-alb egress: tcp 8000 → sg-app?                         ▲
   │ ② NACL(pub) outbound: 10.20.16.5:8000?                      │ ④ sg-app inbound: 8000 from sg-alb?
   └──────────────── subnet boundary ──────────► ③ NACL(app) inbound: from 10.20.0.10 :8000?
                                                                 │
   ⑥ NACL(pub) inbound: from 10.20.16.5 → port 50000?  ◄── ⑤ NACL(app) outbound: → 10.20.0.10:50000?
   (SG ফেরত পথে আবার পরীক্ষা করে না — stateful)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Stateful | Connection মনে রাখে; ফেরত traffic নিজে থেকে allowed |
| Stateless | প্রতিটি packet আলাদা বিচার |
| Ephemeral port | Client-এর সাময়িক port (Linux 32768–60999; ELB ও NAT-এর জন্য AWS 1024–65535 সুপারিশ করে) |
| SG reference | Source/destination হিসেবে অন্য SG — সেই SG-যুক্ত ENI-এর private IP |
| Rule `*` | NACL-এর শেষ নিয়ম (32767) — কিছু না মিললে deny |
| ENI | Elastic Network Interface — SG আসলে এখানে লাগে |
| Prefix list | CIDR-এর নামযুক্ত তালিকা (যেমন AWS service-এর) |
| SSM Session Manager | Port 22 খোলা ছাড়াই shell |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 SG reference

`sg-app inbound: tcp 8000 from sg-alb` মানে: যেকোনো ENI, যাতে `sg-alb` লাগানো, তার private IP থেকে আসা traffic। ALB নতুন node আনলে বা IP বদলালেও নিয়ম কাজ করে। CIDR-এর বদলে এটাই সঠিক উপায়।

### 8.2 NACL মূল্যায়ন

Rule number-এর ক্রমে পড়া হয়, প্রথম মিলই চূড়ান্ত। নমুনার `acl-app`-এ rule 90 (deny 22) rule 110-এর (allow 1024–65535) আগে, তাই SSH আটকায়।

কিন্তু rule 110 ফেরত traffic-এর জন্য লেখা হলেও **internet থেকে 8000 port-এর নতুন connection-ও allow করে** — কারণ 8000 সেই পরিসরে পড়ে। নমুনার output-এ `internet → app 8000` NACL পার হয়ে শুধু SG-তে থামে। Stateless filter "উত্তর" ও "নতুন request" আলাদা করতে পারে না।

### 8.3 Timeout বনাম refused

| Client দেখে | মানে | কোথায় খুঁজবেন |
|---|---|---|
| Timeout | Packet কোথাও নীরবে হারিয়েছে | SG, NACL, route table (L08-04), host firewall |
| Connection refused | Host-এ পৌঁছেছে, port-এ কেউ নেই | App চলছে? কোন address-এ bind (`ss -ltnp`)? |
| TLS/HTTP error | Network ঠিক, app-স্তরের সমস্যা | Log |

### 8.4 SSH-এর বিকল্প

SSM Session Manager-এ inbound port খুলতে হয় না। লাগে:

- instance profile-এ `AmazonSSMManagedInstanceCore`;
- SSM agent (Ubuntu-র AWS AMI-তে সাধারণত আগে থেকে থাকে);
- SSM endpoint-এ outbound (NAT বা VPC interface endpoint)।

L08-06-এ ব্যবহার হবে।

> **Fedora-তে:** কোনো পার্থক্য নেই। Instance-এর ভেতরে host firewall ভিন্ন হতে পারে — Ubuntu-তে `ufw`, Fedora-তে `firewalld` — এবং সেটাও timeout ঘটাতে পারে (L02-10)।

## 9. Practical demonstration

Files:

- [`code/L08-05/sg_reach.py`](code/L08-05/sg_reach.py)
- [`sample/security-groups.json`](code/L08-05/sample/security-groups.json), [`sample/network-acls.json`](code/L08-05/sample/network-acls.json), [`sample/flows.json`](code/L08-05/sample/flows.json) — হাতে তৈরি
- [`test_l08_05.py`](code/L08-05/test_l08_05.py)

### 9.1 Flow check — আসল output (হাতে তৈরি নমুনায়)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-05
python3 sg_reach.py check sample/security-groups.json sample/network-acls.json --flows sample/flows.json
```

```text
ALLOW  internet → ALB 443  ✓ as expected
         ok  destination NACL inbound: acl-default rule 100 allow
         ok  destination SG inbound from 198.51.100.7: sg-alb 0.0.0.0/0
         ok  return: destination NACL outbound to port 50000: acl-default rule 100 allow
ALLOW  ALB → app 8000  ✓ as expected
         ok  source SG egress to 10.20.16.5:8000: sg-alb ← sg-app
         …
DROP   internet → app 8000 (bypass ALB)  ✓ as expected
         ok  destination NACL inbound: acl-app rule 110 allow
         XX  destination SG inbound from 198.51.100.7: no rule
         → client sees a TIMEOUT (dropped silently), not 'connection refused'
DROP   internet → app SSH  ✓ as expected
         XX  destination NACL inbound: acl-app rule 90 deny
         → client sees a TIMEOUT (dropped silently), not 'connection refused'
ALLOW  app → db 5432  ✓ as expected
         …
DROP   ALB → db 5432  ✓ as expected
         XX  source SG egress to 10.20.48.9:5432: no rule
         → client sees a TIMEOUT (dropped silently), not 'connection refused'
6 flow(s), 0 unexpected
```

`ALB → db` আটকায় ALB-এর নিজের egress-এ — `sg-alb`-এর outbound শুধু `sg-app`-এর 8000-এ। Egress সীমিত রাখা দ্বিতীয় স্তরের সুরক্ষা।

### 9.2 SG audit — আসল output

```bash
python3 sg_reach.py audit sample/security-groups.json; echo "exit=$?"
```

```text
CRITICAL  sg-app     SSH (22) open to 0.0.0.0/0 — use SSM Session Manager or a source-restricted rule
WARN      sg-db      references sg-old-bastion, not in this input (deleted? another VPC?)
3 security group(s), 2 finding(s)
exit=1
```

SSH NACL-এ আটকে আছে (rule 90), কিন্তু SG-তেও বন্ধ করা উচিত। কেউ NACL বদলালে বা instance অন্য subnet-এ গেলে SG-ই শেষ রক্ষা।

### 9.3 নিজের VPC-তে (চালানো হয়নি)

```bash
V=$(aws ec2 describe-vpcs --filters Name=tag:Project,Values=lab08 --query 'Vpcs[0].VpcId' --output text)
aws ec2 describe-security-groups --filters Name=vpc-id,Values=$V > security-groups.json
aws ec2 describe-network-acls --filters Name=vpc-id,Values=$V > network-acls.json
python3 sg_reach.py audit security-groups.json
python3 sg_reach.py check security-groups.json network-acls.json \
  --src-ip <ALB-এর private IP> --src-sg <sg-alb> --src-subnet <subnet> \
  --dst-ip <EC2-এর private IP> --dst-sg <sg-app> --dst-subnet <subnet> --port 8000
```

Lab B-এর SG বানানো (L08-06/L08-09-এ ব্যবহার):

```bash
ALB_SG=$(aws ec2 create-security-group --group-name lab08-alb --description "ALB" --vpc-id $V \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Project,Value=lab08}]' --query GroupId --output text)
APP_SG=$(aws ec2 create-security-group --group-name lab08-app --description "TaskFlow app" --vpc-id $V \
  --tag-specifications 'ResourceType=security-group,Tags=[{Key=Project,Value=lab08}]' --query GroupId --output text)
aws ec2 authorize-security-group-ingress --group-id $ALB_SG --protocol tcp --port 80 --cidr 0.0.0.0/0
aws ec2 authorize-security-group-ingress --group-id $APP_SG --protocol tcp --port 8000 --source-group $ALB_SG
```

### 9.4 লেখার সময়

Test-এ `copy.replace()` ব্যবহার করেছিলাম — এটা শুধু Python 3.13+-এ আছে, আর ruff ধরেনি (3.14-এ test পাসও করেছিল)। 3.11/3.12-এ ভেঙে যেত। `dataclasses.replace()`-এ বদলানো হয়েছে, এবং repo-তে আর কোথাও নেই (grep দিয়ে যাচাই)।

### 9.5 Test

```bash
python3 -m unittest -v
```

৬টি test:

- নমুনার ৬টি flow।
- **Stateless ফেরত পথ** (Section 5-এর পরিস্থিতি)।
- একই subnet-এ NACL বাদ।
- Rule-এর ক্রম ও protocol।
- IPv6 ও SG reference।
- Audit।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `sg_allows()` | সব rule-এর যেকোনো একটি | SG-তে ক্রম নেই, deny নেই |
| `UserIdGroupPairs` → peer SG | SG reference | IP নয়, ভূমিকা |
| `acl_decides()` sorted by RuleNumber | প্রথম মিলই চূড়ান্ত | NACL-এর নিয়ম |
| `cross = src_subnet != dst_subnet` | একই subnet-এ NACL নয় | Subnet সীমানায় প্রযোজ্য |
| `src_port` (default 50000) | ফেরত পথ | Stateless NACL |
| প্রথম `XX`-এ থামা | Packet সেখানেই হারায় | Diagnosis-এর এক উত্তর |
| "TIMEOUT, not refused" | Symptom | Client-এর দেখা জিনিস থেকে কারণ |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় `check --flows` | `6 flow(s), 0 unexpected`, exit ০ |
| নমুনায় `audit` | ১ CRITICAL, ১ WARN, exit ১ |
| আপনার lab SG | `audit`-এ কোনো CRITICAL নয় |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Timeout | SG/NACL/route | `sg_reach.py check`, তারপর L08-04-এর audit |
| Connection refused | App চলছে না বা `127.0.0.1`-এ bind | `ss -ltnp`; `0.0.0.0`-এ bind |
| কাস্টম NACL-এর পরে সব timeout | Ephemeral port | Inbound ও outbound 1024–65535 |
| ALB health check unhealthy | App SG-তে ALB SG নেই, বা ভুল port | `--source-group` |
| `InvalidPermission.Duplicate` | একই নিয়ম আগেই আছে | `describe-security-groups` |
| SG মুছতে `DependencyViolation` | ENI এখনো ব্যবহার করছে, বা অন্য SG reference করছে | Instance/LB আগে মুছুন; reference সরান |
| IPv6 client আটকে যায় | শুধু `IpRanges`, `Ipv6Ranges` নেই | দুটোই |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Inbound-এ CIDR-এর বদলে SG reference।
  - Egress-ও সীমিত করা যায় (নমুনার `sg-alb`)।
  - SSH নয় — Session Manager।
  - `0.0.0.0/0` শুধু public load balancer-এর 80/443-এ।
  - Audit CI-তে চালান (Module 12-এ Terraform plan-এর ওপর)।
- **Performance:** SG ও NACL-এর মূল্যায়ন hypervisor-স্তরে, throughput-এ সাধারণত প্রভাব নেই। SG-এর connection tracking-এর সীমা আছে — খুব বেশি connection-এর workload-এ documentation দেখুন।
- **Cost:** নিজে চার্জমুক্ত। কিন্তু খোলা SSH-এ brute force-এর log ingestion (CloudWatch) ও আক্রমণের ঝুঁকি চার্জ বাড়াতে পারে।

## 14. Hands-on exercise

1. `flows.json`-এ একটি flow যোগ করুন: app → internet 443 (package update), `dst_ip` যেকোনো public IP, `src_subnet` app। কী লাগে? (NAT-এর পথে আসলে আরও এক ধাপ আছে; tool সেটা দেখায় না — কেন?)
2. Section 5-এর ভুল NACL নিজে লিখে `check` চালান; তারপর ঠিক করুন।
3. `sg_reach.py audit`-এ নতুন নিয়ম: description ছাড়া inbound rule — WARN।
4. নিজের account-এ lab SG বানিয়ে `audit` ও `check` চালান। একটি সত্যিকারের EC2-এ `nc -zv` দিয়ে timeout বনাম refused নিজে দেখুন (L08-06-এর পরে)।
5. VPC Reachability Analyzer-এর documentation পড়ে লিখুন: এটা `sg_reach.py`-এর চেয়ে কী বেশি দেখে (route, NAT, ENI ইত্যাদি), এবং চার্জ কীভাবে হয়।

## 15. Mini-project — Expected-flow test suite

TaskFlow-এর জন্য একটি `expected-flows.json` — যা allow হওয়া উচিত (ALB → app, app → db) এবং যা কখনো নয় (internet → app, internet → db, ALB → db)। প্রতিটি deploy-এর পরে describe → `sg_reach.py check --flows` CI-তে চলবে। Firewall-এর পরিবর্তন code-এর মতো test পাবে। Lab C এর ভিত্তি।

## 16. Interview প্রশ্ন

1. Security group ও NACL-এর পার্থক্য কী? কখন কোনটা?
2. Stateful ও stateless firewall-এর ব্যবহারিক পার্থক্য কী?
3. Ephemeral port কী? NACL-এ কেন দরকার?
4. Timeout ও connection refused-এর পার্থক্য কী বলে?
5. SG-তে অন্য SG reference করার সুবিধা কী?
6. Port 22 না খুলে instance-এ কীভাবে ঢুকবেন?

## 17. Self-assessment প্রশ্ন

1. রক্ষী-analogy কোথায় মেলে না?
2. নমুনায় internet → app 8000 NACL-এ কেন allowed?
3. একই subnet-এর দুটি instance-এর মধ্যে NACL কেন প্রযোজ্য নয়?
4. ALB → db কোথায় আটকায়, এবং কেন সেটা ভালো?
5. NACL rule `*` কী?

## 18. সংক্ষিপ্ত সারাংশ

- SG: stateful, allow-only, ENI-স্তরে, SG reference — প্রধান নিয়ন্ত্রণ।
- NACL: stateless, numbered, subnet-স্তরে — guardrail; ephemeral port ভুলবেন না।
- আটকানো traffic = timeout; refused = host-এ পৌঁছেছে, port-এ কেউ নেই।
- `sg_reach.py check` দিয়ে flow-এর প্রতিটি ধাপ; `audit` দিয়ে খোলা SSH/DB।

## 19. Completion checklist

- [ ] Lab SG (ALB, app) তৈরি; audit-এ কোনো CRITICAL নেই
- [ ] Section 5-এর NACL ভুল নিজে বানিয়ে ঠিক করেছি (offline)
- [ ] Expected-flow file লিখেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Amazon VPC — Security groups: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-security-groups.html
- Amazon VPC — Network ACLs: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-network-acls.html
- VPC Reachability Analyzer: https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html
- AWS Systems Manager — Session Manager: https://docs.aws.amazon.com/systems-manager/latest/userguide/session-manager.html

---

**পরের lesson:** L08-06 — EC2
