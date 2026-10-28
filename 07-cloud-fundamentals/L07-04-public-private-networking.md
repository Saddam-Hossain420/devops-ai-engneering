# L07-04 — Public বনাম private networking

| | |
|---|---|
| **Module** | 07 — Cloud Fundamentals |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-14 — VPC](../02-computer-networking/L02-14-cloud-networking.md), [L02-03 — CIDR](../02-computer-networking/L02-03-ip-addressing-cidr.md), [L07-03 — Region/AZ](L07-03-regions-zones-fault-domains.md) |
| **Label** | — |
| **Tested** | `subnet_plan.py`: ৪টি test পাস (Python 3.14.5, Windows)। Test প্রতিটি পরিকল্পনায় যাচাই করে: subnet-গুলো overlap করে না, সব VPC-র ভেতরে, এবং reserved address বাদ দিয়েও যথেষ্ট host। এই lesson-এর code-এ test কোনো নতুন bug পায়নি; লেখার সময় শুধু allocation loop-এর অপ্রয়োজনীয় অংশ পরিষ্কার করা হয়েছে। কোনো cloud resource তৈরি হয়নি, কোনো API call নেই। |

---

## 1. এই lesson-এ যা শিখবেন

- Public, private ও isolated subnet: কে internet থেকে পৌঁছাতে পারে, কে internet-এ যেতে পারে।
- Internet gateway, NAT gateway, private endpoint — প্রতিটির ভূমিকা ও খরচের গঠন।
- **VPC CIDR পরিকল্পনা:** on-prem/অন্য VPC-র সাথে overlap এড়ানো, ভবিষ্যতের জায়গা, provider-এর reserved address।
- Multi-AZ subnet layout — প্রতিটি tier প্রতিটি AZ-এ।
- Bastion বনাম session manager বনাম VPN — private server-এ কীভাবে পৌঁছাবেন।
- Egress খরচ: কেন "private subnet + NAT" সস্তা নাও হতে পারে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L06-08-এ server-এর ভেতরে port বন্ধ করেছি। Cloud-এ তার আগে একটি শক্ত স্তর আছে: **network-এর নকশা**। Database এমন subnet-এ থাকলে যার internet-এর route-ই নেই, তাহলে ভুল firewall rule থাকলেও internet থেকে পৌঁছানো যায় না।

ভুল নকশার দাম পরে দিতে হয় এবং পরিবর্তন কঠিন:

- VPC-র CIDR অফিসের network-এর সাথে overlap করে — VPN চালু করতে পুরো VPC নতুন করে বানাতে হয়।
- `/24` VPC-তে শুরু, Kubernetes আসার পরে IP শেষ।
- সব server public subnet-এ, প্রত্যেকের public IP — scan ও brute-force-এর লক্ষ্য।
- Private subnet-এর NAT দিয়ে terabyte-এর data object storage-এ যায় — NAT-এর বিল application-এর চেয়ে বড়।

## 3. সহজ ভাষায় পরিচয়

| Subnet ধরন | Default route | Internet থেকে ভেতরে | ভেতর থেকে internet | কী রাখবেন |
|---|---|---|---|---|
| Public | Internet gateway | সম্ভব (public IP + security group) | সরাসরি | Load balancer, NAT gateway, (bastion) |
| Private | NAT gateway | না | NAT দিয়ে (outbound) | App server |
| Isolated | নেই (শুধু local) | না | না | Database, cache |

```text
internet ⇄ IGW ⇄ [public: LB, NAT] ─► [private: app] ─► [isolated: db]
                         ▲ outbound only     │
                         └───────────────────┘   app → NAT → internet (package update, external API)
 object storage ← private endpoint ← private/isolated (NAT ছাড়া, internet ছাড়া)
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিস ভবন

- **Public subnet** = রিসেপশন — রাস্তা থেকে ঢোকা যায়।
- **Private subnet** = অফিসের ঘর — বাইরে থেকে কেউ সরাসরি ঢুকতে পারে না। কর্মীরা পিয়নকে (NAT) দিয়ে বাইরে চিঠি পাঠাতে পারেন।
- **Isolated subnet** = ভল্ট — বাইরের সাথে কোনো যোগাযোগ নেই।
- **Private endpoint** = ভবনের ভেতর দিয়ে পাশের গুদামে যাওয়ার নিজস্ব করিডর — রাস্তায় না নেমেই।
- **CIDR পরিকল্পনা** = ঘরের নম্বর — অন্য শাখার সাথে একই নম্বর হলে চিঠি ভুল জায়গায় যায়।

### Analogy কোথায় মেলে না

- **পিয়ন শুধু চিঠি পাঠায়, উত্তর আনে না।** NAT stateful: ভেতর থেকে শুরু হওয়া connection-এর উত্তর ফেরত আসে, কিন্তু বাইরে থেকে নতুন connection শুরু করা যায় না। "Private" মানে "outbound নেই" নয় — compromised app NAT দিয়ে data বাইরে পাঠাতে পারে। Outbound নিয়ন্ত্রণ আলাদা বিষয় (egress firewall, proxy — Module 19)।
- **ঘরের নম্বর পরে বদলানো যায়।** VPC-র CIDR ও subnet-এর আকার সাধারণত তৈরির পরে বদলানো যায় না (কিছু provider secondary CIDR যোগ করতে দেয়)। ভুল পরিকল্পনা মানে migration।
- **পিয়নের কোনো খরচ নেই।** NAT gateway-র ঘণ্টা-প্রতি চার্জ এবং **প্রতি GB data processing** চার্জ আছে। Private subnet থেকে object storage-এ বড় data NAT দিয়ে গেলে সেই চার্জ লাগে। Private endpoint (gateway endpoint) দিয়ে গেলে প্রায়ই তা এড়ানো যায় — provider-এর pricing page দেখুন (L07-06)।

## 5. Real-world engineering scenario — "VPN চালু করা যাচ্ছে না"

**পরিস্থিতি:** একটি startup দ্রুত শুরু করতে default পরামর্শ মেনে VPC-র CIDR `10.0.0.0/16` নিল, এবং সব server রাখল public subnet-এ। এক বছর পরে:

1. একটি বড় client-এর অফিসের network-এর সাথে site-to-site VPN দরকার। Client-এর network `10.0.0.0/20` — overlap। Routing অস্পষ্ট, তাই VPN অসম্ভব।
2. Security audit-এ: database-এর public IP আছে। Security group ঠিক ছিল, কিন্তু একটি ভুল rule-এই সব খুলে যেত।
3. Kubernetes চালু করার পরিকল্পনায় হিসাব: pod-প্রতি একটি IP হলে `/24` subnet কয়েক দিনেই শেষ।

**সমাধান:** নতুন VPC, পরিকল্পিত CIDR `10.20.0.0/16` (অফিস, staging ও ভবিষ্যতের network এড়িয়ে), তিন স্তর × তিন AZ, এবং migration — কয়েক সপ্তাহের কাজ। `subnet_plan.py` দিয়ে প্রথম ভুলটা আগেই ধরা যেত (আসল output):

```text
error: VPC 10.0.0.0/16 overlaps office-vpn 10.0.0.0/20 — peering/VPN routing will be ambiguous; pick another range
```

**শিক্ষা:** CIDR পরিকল্পনা প্রথম দিনের কাজ, এবং সেটা কোম্পানির সব network-এর একটি তালিকা (IPAM) থেকে করুন। Default range (`10.0.0.0/16`, `172.31.0.0/16`) সবাই নেয় — তাই সংঘাতের সম্ভাবনা বেশি।

## 6. Diagram — TaskFlow-এর VPC (10.20.0.0/16)

```text
 ┌──────────────────────────── VPC 10.20.0.0/16 ─────────────────────────────┐
 │        AZ a                   AZ b                   AZ c                   │
 │ public   10.20.13.128/26     10.20.13.192/26      10.20.14.0/26            │ ← LB, NAT GW
 │ app      10.20.0.0/22        10.20.4.0/22         10.20.8.0/22             │ ← TaskFlow (private)
 │ data     10.20.12.0/25       10.20.12.128/25      10.20.13.0/25            │ ← DB (isolated)
 │ বাকি ৯৪% — ভবিষ্যতের জন্য (Kubernetes, নতুন service)                        │
 └─────────────────────────────────────────────────────────────────────────────┘
 route tables:
   public   0.0.0.0/0 → IGW
   app      0.0.0.0/0 → NAT GW (একই AZ-এর — AZ-এর মধ্যে traffic ও SPOF এড়াতে)
   data     শুধু local (+ object storage-এর private endpoint)
 avoid: office-vpn 10.0.0.0/16 · staging-vpc 10.21.0.0/16
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| VPC / VNet | Cloud-এ নিজের আলাদা virtual network |
| Subnet | VPC-র অংশ, একটি AZ-এ (সাধারণত) |
| Internet gateway (IGW) | VPC ও internet-এর মধ্যে দরজা |
| NAT gateway | Private subnet-এর outbound-only internet access |
| Private endpoint | Provider-এর service-এ internet ছাড়া পৌঁছানো |
| Route table | Subnet-এর traffic কোথায় যাবে |
| Elastic/public IP | Internet থেকে পৌঁছানোর address |
| Bastion / jump host | Private server-এ ঢোকার একমাত্র দরজা |
| Session manager | Agent-ভিত্তিক shell access, inbound port ছাড়া |
| IPAM | IP address-এর কেন্দ্রীয় পরিকল্পনা ও হিসাব |
| Egress | ভেতর থেকে বাইরে যাওয়া traffic (এবং তার খরচ) |
| Reserved address | Provider প্রতিটি subnet-এ নিজে রাখে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Reserved address

Provider প্রতিটি subnet-এর কিছু address নিজে রাখে (network, router, DNS, ভবিষ্যৎ, broadcast) — AWS documentation অনুযায়ী ৫টি। তাই `/26` (৬৪টি) subnet-এ ব্যবহারযোগ্য ৫৯টি।

`subnet_plan.py` `reserved_per_subnet` দিয়ে এই হিসাব করে: ৫৯ host `/26`-এ আঁটে, কিন্তু ৬০ host-এর জন্য `/25` লাগে (test-এ যাচাই)। অন্য provider-এ সংখ্যা ভিন্ন — documentation দেখুন।

### 8.2 Allocation

বড় subnet আগে, প্রতিটি AZ-এ একই আকার। প্রতিটি নতুন subnet নেওয়া হয় সবচেয়ে ছোট যে free block-এ সেটা আঁটে (best fit), prefix-এর সীমায় aligned। ফলে বড় block ভবিষ্যতের জন্য অক্ষত থাকে।

### 8.3 Private server-এ প্রবেশ

| পদ্ধতি | Inbound port | ঝুঁকি | মন্তব্য |
|---|---|---|---|
| Public IP + SSH | ২২ সবার জন্য | উচ্চ | এড়ান |
| Bastion host | Bastion-এ ২২ (IP-সীমিত) | মাঝারি | Bastion নিজেই harden করতে হয় (L06-08) |
| Session manager (agent) | কোনোটি নয় | কম | IAM দিয়ে নিয়ন্ত্রণ, audit log |
| VPN | VPN-এর port | কম-মাঝারি | পুরো network-এ প্রবেশ — segmentation দরকার |

### 8.4 Egress-এর পথ

- **Public subnet:** IGW দিয়ে সরাসরি।
- **Private subnet:** NAT দিয়ে, এবং NAT-এর data processing চার্জ।
- **Provider-এর নিজের service** (object storage, container registry): private endpoint দিয়ে internet ছাড়াই — নিরাপত্তা ও খরচ দুই দিকেই ভালো।
- **AZ-এর বাইরের NAT:** প্রতিটি AZ-এ আলাদা NAT না রাখলে AZ-এর মধ্যে data transfer-এর চার্জ, আর NAT-এর AZ বন্ধ হলে সব private subnet-এর outbound বন্ধ (L07-03-এর SPOF)।

> **Fedora-তে:** কোনো পার্থক্য নেই — ধারণাগত। Local-এ একই ধারণা network namespace দিয়ে L02-13-এ দেখা হয়েছে।

## 9. Practical demonstration

Files:

- [`code/L07-04/subnet_plan.py`](code/L07-04/subnet_plan.py)।
- [`taskflow-vpc.json`](code/L07-04/taskflow-vpc.json), [`conflict-vpc.json`](code/L07-04/conflict-vpc.json), [`tiny-vpc.json`](code/L07-04/tiny-vpc.json) (হাতে তৈরি)।
- [`test_l07_04.py`](code/L07-04/test_l07_04.py)।

### 9.1 TaskFlow-এর পরিকল্পনা — আসল output

```bash
cd ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-04
python3 subnet_plan.py taskflow-vpc.json
```

```text
tier       type      az   cidr               usable
app        private   a    10.20.0.0/22       1019
app        private   b    10.20.4.0/22       1019
app        private   c    10.20.8.0/22       1019
data       isolated  a    10.20.12.0/25      123
data       isolated  b    10.20.12.128/25    123
data       isolated  c    10.20.13.0/25      123
public     public    a    10.20.13.128/26    59
public     public    b    10.20.13.192/26    59
public     public    c    10.20.14.0/26      59

route (private): 0.0.0.0/0 → NAT gateway in a public subnet (শুধু outbound; NAT-এর data খরচ)
route (isolated): শুধু VPC-র local route (internet নেই; object storage-এ private endpoint)
route (public): 0.0.0.0/0 → internet gateway (public IP থাকলে ingress সম্ভব)
note: unallocated: 61888 addresses (94% of the VPC) kept for growth
```

- App tier-এ ১০০০ host চাওয়া হয়েছিল; `/22`-এ ১০২৪ − ৫ = ১০১৯।
- পুরো তিন-স্তর × তিন-AZ নকশায় VPC-র মাত্র ৬% লেগেছে।

### 9.2 ভুল পরিকল্পনা — আসল output

```bash
python3 subnet_plan.py conflict-vpc.json; echo "exit=$?"
python3 subnet_plan.py tiny-vpc.json; echo "exit=$?"
```

```text
error: VPC 10.0.0.0/16 overlaps office-vpn 10.0.0.0/20 — peering/VPN routing will be ambiguous; pick another range
exit=1
error: VPC 10.40.0.0/24 has no room left for app in AZ c (/25)
exit=1
```

দ্বিতীয়টি: ৬০ host-এর জন্য reserved সহ `/25` লাগে, আর তিন AZ-এ তিনটি `/25` একটি `/24`-এ (দুটি `/25`) আঁটে না।

### 9.3 Test

```bash
python3 -m unittest -v
```

৪টি test:

- নমুনা পরিকল্পনা: ৯টি subnet, VPC-র ভেতরে, **কোনো জোড়া overlap করে না**, reserved বাদেও যথেষ্ট, প্রতিটি AZ-এ একই আকার।
- Reserved-এর হিসাব (৫৯ → /26, ৬০ → /25, /28-এর সীমা)।
- তিন ধরনের error।
- NAT-এর জন্য public subnet না থাকার সতর্কতা।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `prefix_for(hosts, reserved)` | Reserved সহ prefix | ৫৯ বনাম ৬০-এর পার্থক্য |
| `avoid`-এর overlap যাচাই | On-prem/peer-এর সাথে সংঘাত | Section 5 |
| `is_private` যাচাই | RFC 1918 | Public range VPC-তে নয় |
| বড় আগে, best fit | Aligned, অপচয় কম | বড় block ভবিষ্যতের জন্য |
| `address_exclude` | বাকি জায়গা free list-এ | সঠিক হিসাব |
| `ROUTES` | প্রতিটি ধরনের route-এর উদ্দেশ্য | নকশার দলিল |
| Notes | বাকি জায়গা, NAT-এর পূর্বশর্ত | Pod-এর IP-এর সতর্কতা |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `taskflow-vpc.json` | ৯টি subnet, ৯৪% বাকি |
| `conflict-vpc.json` | overlap error, exit ১ |
| `tiny-vpc.json` | no room, exit ১ |
| `python3 -m unittest -v` | `Ran 4 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | ফল | সমাধান |
|---|---|---|
| Default CIDR (`10.0.0.0/16`) | VPN/peering-এ overlap | IPAM থেকে পরিকল্পিত range |
| খুব ছোট VPC | Container/pod-এ IP শেষ | `/16` বা বড়; secondary CIDR |
| সব কিছু public subnet-এ | প্রতিটি server সরাসরি লক্ষ্য | তিন স্তর |
| Private subnet-এ instance internet পায় না | NAT নেই বা route ভুল | Route table (L02-14-এর `vpc_sim.py trace`) |
| NAT-এর বিল বিশাল | Object storage-এর traffic NAT দিয়ে | Private/gateway endpoint |
| এক NAT সব AZ-এর জন্য | AZ-এর মধ্যে চার্জ + SPOF | প্রতি AZ-এ NAT (খরচ বনাম ঝুঁকি) |
| Reserved address ভুলে subnet ছোট | পরিকল্পনার চেয়ে কম host | Reserved বাদ দিয়ে হিসাব |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Database isolated subnet-এ — route-ই নেই।
  - Network নকশা security group-এর পরিপূরক, বিকল্প নয় (defense in depth)।
  - Private server-এ session manager বা bastion, কখনো public SSH নয়।
  - Outbound নিয়ন্ত্রণও ভাবুন (data exfiltration)।
  - VPC flow log চালু রাখুন (Module 17/19)।
- **Performance:**
  - Private endpoint ও একই-AZ পথ latency কমায়।
  - NAT-এর throughput-এর সীমা আছে — বড় data-য় private endpoint।
- **Cost:**
  - NAT gateway: ঘণ্টা-প্রতি + GB-প্রতি চার্জ।
  - AZ বা region-এর মধ্যে data transfer চার্জ।
  - Internet-এ egress সাধারণত সবচেয়ে বড় network চার্জ।
  - প্রকৃত দাম provider-এর pricing page থেকে নিন; L07-06-এর estimate-এ বসান।

## 14. Hands-on exercise

1. আপনার নিজের (বা কল্পিত) কোম্পানির network-গুলোর তালিকা বানিয়ে `avoid`-এ দিন, এবং একটি সংঘাতহীন VPC পরিকল্পনা করুন।
2. `taskflow-vpc.json`-এ Kubernetes-এর জন্য "pods" tier যোগ করুন (প্রতি AZ-এ ৪০০০ IP)। কতটা জায়গা বাকি থাকে?
3. L02-14-এর `vpc_sim.py`-তে এই পরিকল্পনার subnet ও route table বসিয়ে `trace` দিয়ে যাচাই করুন: app থেকে internet (NAT দিয়ে) পৌঁছায়, data থেকে পৌঁছায় না।
4. `subnet_plan.py`-তে IPv6 সমর্থন যোগ করুন (VPC-কে /56, subnet /64)। IPv6-এ NAT-এর বদলে "egress-only gateway"-এর ধারণা পড়ুন।
5. একটি provider-এর pricing page থেকে NAT gateway-র মূল্যের গঠন (ঘণ্টা + GB) নোট করুন (link সহ, তারিখসহ)। দিনে ১০০ GB object storage-এর traffic NAT দিয়ে গেলে মাসিক খরচ কত?

## 15. Mini-project — Network design doc generator

`network_doc.py plan.json`:

- `subnet_plan.py`-এর ফল থেকে Markdown নকশা-দলিল।
- Mermaid diagram (L00-05)।
- প্রতিটি tier-এর route table, security group-এর প্রস্তাব (কোন tier কোন port-এ কাকে দেবে), এবং egress-এর পথ।

Module 12-এ এই দলিল থেকেই Terraform লেখা হবে।

## 16. Interview প্রশ্ন

1. Public ও private subnet-এর পার্থক্য কী? কোনটা কী দিয়ে নির্ধারিত হয়?
2. NAT gateway কী করে? Private subnet-এর server কি internet-এ যেতে পারে?
3. VPC-র CIDR কীভাবে বাছবেন?
4. Private server-এ কীভাবে নিরাপদে প্রবেশ করবেন?
5. Private endpoint কেন ব্যবহার করবেন?
6. Cloud-এ network-এর কোন কোন খরচ আছে?

## 17. Self-assessment প্রশ্ন

1. অফিস ভবন analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি সমস্যা কী ছিল?
3. ৬০ host-এর জন্য `/26` কেন যথেষ্ট নয়?
4. Isolated subnet ও security group-এর মধ্যে কোনটা বেশি শক্ত সুরক্ষা, এবং কেন?
5. এক NAT সব AZ-এর জন্য রাখার দুটি অসুবিধা কী?

## 18. সংক্ষিপ্ত সারাংশ

- তিন স্তর: public (LB, NAT), private (app), isolated (DB) — প্রতিটি প্রতিটি AZ-এ।
- CIDR পরিকল্পনা প্রথম দিনে, সব network-এর সাথে overlap এড়িয়ে, বড় range ও বাকি জায়গা রেখে।
- Reserved address বাদ দিয়ে subnet-এর আকার।
- Private server-এ session manager/bastion; public SSH নয়।
- NAT ও egress-এর খরচ মনে রাখুন; provider service-এ private endpoint।

## 19. Completion checklist

- [ ] নিজের network-গুলো এড়িয়ে একটি VPC পরিকল্পনা করেছি
- [ ] `vpc_sim.py` দিয়ে পরিকল্পনার reachability যাচাই করেছি
- [ ] NAT-এর খরচের গঠন pricing page থেকে নোট করেছি
- [ ] `python3 -m unittest -v`-এ ৪টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS — VPC user guide (subnets, reserved addresses): https://docs.aws.amazon.com/vpc/latest/userguide/subnet-sizing.html
- AWS — NAT gateways: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- AWS — Gateway endpoints: https://docs.aws.amazon.com/vpc/latest/privatelink/gateway-endpoints.html
- Google Cloud — VPC network overview: https://cloud.google.com/vpc/docs/vpc
- Microsoft Learn — Azure Virtual Network: https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview
- RFC 1918 — Address Allocation for Private Internets: https://www.rfc-editor.org/rfc/rfc1918

---

**পরের lesson:** L07-05 — IAM, identity ও least privilege
