# L08-04 — VPC design: subnet, route table, gateway

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L07-04 — Public বনাম private networking](../07-cloud-fundamentals/L07-04-public-private-networking.md), [L02-14 — Cloud networking](../02-computer-networking/L02-14-cloud-networking.md), [L08-02 — CLI](L08-02-aws-cli-profiles-temporary-credentials-boto3.md) |
| **Label** | 💰 VPC, subnet, route table ও internet gateway নিজে সাধারণত চার্জমুক্ত। **NAT gateway ও public IPv4 address (Elastic IP সহ) ঘণ্টা অনুযায়ী চার্জযোগ্য**, NAT-এ data-ও — চালুর আগে VPC pricing page দেখুন, এবং lab শেষে মুছুন |
| **Tested** | `vpc_audit.py` ও `vpc_commands.py`: ৮টি test পাস (Python 3.14.5, Windows)। Input **হাতে তৈরি** — `describe-subnets`/`describe-route-tables`/`describe-nat-gateways`/`describe-internet-gateways`-এর রূপে। তৈরি করা bash script `bash -n`-এ (Git Bash) syntax যাচাই করা হয়েছে, কিন্তু **AWS-এ চালানো হয়নি।** |

---

## 1. এই lesson-এ যা শিখবেন

- AWS VPC-র অংশ: CIDR, subnet (একটি AZ-এ), route table, internet gateway (IGW), NAT gateway, VPC endpoint।
- **একটি subnet public না private, তা ঠিক করে তার route table** — নাম নয়।
- Main route table-এর ফাঁদ ও explicit association।
- NAT gateway: কোথায় বসে, AZ-নির্ভরতা, খরচ।
- L07-04-এর subnet plan থেকে AWS CLI script (`vpc_commands.py`) এবং তৈরি VPC যাচাই (`vpc_audit.py`)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L07-04-এ কাগজে নকশা হয়েছে: তিন স্তর, দুই-তিন AZ, overlap-হীন CIDR। AWS-এ সেটা বাস্তবায়নে ভুলের জায়গা অনেক:

- "private" নামের subnet-এ ভুল route table, তাই database internet থেকে দেখা যায়।
- NAT gateway private subnet-এ বসানো, তাই কিছুই বাইরে যায় না, আর error-ও দেয় না।
- কেউ main route table-এ IGW route যোগ করল, ফলে association-হীন সব subnet হঠাৎ public।
- NAT মুছে ফেলা হলো, route রয়ে গেল (`blackhole`), আর app-এর update নীরবে timeout হতে লাগল।

Console-এ ক্লিক করে এগুলো চোখে পড়ে না। `vpc_audit.py` route table থেকে প্রতিটি subnet-এর আসল চরিত্র বের করে।

## 3. সহজ ভাষায় পরিচয়

| অংশ | কাজ | Linux-এ সমতুল্য (L02-13) |
|---|---|---|
| VPC | নিজের private network, একটি region-এ | একটি network namespace-এর জগৎ |
| Subnet | VPC-র CIDR-এর অংশ, **একটি AZ-এ** | Bridge-এ যুক্ত একটি segment |
| Route table | Subnet-এর packet কোথায় যাবে | `ip route` |
| `local` route | VPC-র ভেতরে সব subnet-এ পৌঁছানো (মোছা যায় না) | Connected route |
| Internet gateway | Public IP-সহ instance-এর internet পথ (দুই দিকে) | Host-এর uplink + 1:1 NAT |
| NAT gateway | Private subnet-এর শুধু বাইরের দিকের পথ | `iptables -t nat … MASQUERADE` |
| Gateway endpoint (S3) | NAT ছাড়া S3-এ যাওয়ার route | — |

| Subnet-এর ধরন | Route table-এ `0.0.0.0/0` | উদাহরণ |
|---|---|---|
| Public | → `igw-…` | Load balancer, NAT gateway, bastion |
| Private | → `nat-…` (বা firewall/TGW) | App server |
| Isolated | নেই | Database |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### একটি অফিস ভবন

- **VPC** = ভবন।
- **Subnet** = একেকটি তলা — প্রতিটি তলা একটিমাত্র ভবন-অংশে (AZ)।
- **Route table** = প্রতিটি তলার লিফটের বোতাম — কোন বোতাম চাপলে কোথায় যাবে।
- **IGW** = প্রধান দরজা।
- **NAT** = পিছনের ডাক-কক্ষ — ভেতর থেকে চিঠি পাঠানো যায়, বাইরের কেউ এই পথে ঢুকতে পারে না।

### Analogy কোথায় মেলে না

- **তলার নামই তার চরিত্র।** AWS-এ subnet-এর নাম "private-db" হলেও route table-এ IGW থাকলে সেটা public। নাম শুধু label (Section 9.3-এ main table-এর উদাহরণ)।
- **ডাক-কক্ষ যেকোনো তলায় বসানো যায়।** NAT gateway-কে **public** subnet-এ বসাতে হয়, কারণ তাকেও IGW দিয়ে বাইরে যেতে হয়। Private subnet-এ বসালে সে নিজেই বাইরে যেতে পারে না।
- **পুরোনো বোতাম চাপলে কিছু হয় না, এবং সেটা বোঝা যায়।** মুছে-ফেলা NAT-এর route `blackhole` হয়ে থাকে; packet নীরবে হারায়, ফলে client timeout পায় — error নয়।

## 5. Real-world engineering scenario — "এক AZ-এর NAT"

TaskFlow-এর খরচ কমাতে team দুই AZ-এর জন্য একটিমাত্র NAT gateway রাখল (AZ a-তে)। কয়েক মাস পরে AZ a-তে সমস্যা হলো। Load balancer AZ b-তে traffic সরাল, কিন্তু AZ b-এর app server-গুলো payment API-তে (internet) যেতে পারল না — তাদের NAT ছিল AZ a-তে।

`vpc_audit.py` এটা আগে থেকেই বলছিল (হাতে তৈরি নমুনার আসল output):

```text
WARN      subnet-app-b     uses nat-a in ap-south-1a — if that AZ fails this subnet loses internet; cross-AZ data is billed
```

**শিক্ষা:**

- এক NAT = সস্তা, কিন্তু একটি AZ-নির্ভরতা (L07-03-এর correlated failure)।
- AZ-প্রতি NAT = বেশি খরচ, কিন্তু স্বাধীন।
- সিদ্ধান্তটি সচেতনভাবে নিন এবং লিখে রাখুন। Lab-এ এক NAT বা NAT ছাড়া চলে; production-এ AZ-প্রতি।

## 6. Diagram — TaskFlow VPC (দুই AZ)

```text
 VPC 10.20.0.0/16 (ap-south-1)                         igw-0lab
 ┌───────────────── AZ a ─────────────┐ ┌──────────── AZ b ────────────┐      │
 │ public-a 10.20.0.0/24  [rtb-public]│ │ public-b 10.20.1.0/24 [rtb-public]│◄───┘ 0.0.0.0/0 → igw
 │   ALB node, nat-a (EIP)            │ │   ALB node, (nat-b?)               │
 │ app-a 10.20.16.0/20 [rtb-private-a]│ │ app-b 10.20.32.0/20 [rtb-private-b]│ 0.0.0.0/0 → nat-a / nat-b
 │   EC2 (no public IP)               │ │   EC2                              │
 │ data-a 10.20.48.0/24 [rtb-data]    │ │ data-b …                          │ শুধু local
 └────────────────────────────────────┘ └────────────────────────────────────┘
  rtb-main: শুধু local — কোনো subnet implicit-ভাবে এখানে নয়
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| CIDR block | VPC-র address range — IPv4-এ /16 থেকে /28 |
| Reserved address | প্রতি subnet-এ ৫টি (network, router, DNS, ভবিষ্যৎ, broadcast) |
| Main route table | Association-হীন subnet-এর ডিফল্ট table |
| Explicit association | Subnet ↔ route table-এর সরাসরি সংযোগ |
| Blackhole route | Target মুছে গেছে; packet ফেলে দেওয়া হয় |
| Elastic IP | স্থির public IPv4 — চার্জযোগ্য |
| `MapPublicIpOnLaunch` | Subnet-এ নতুন instance স্বয়ংক্রিয়ভাবে public IP পায় কিনা |
| Gateway endpoint | S3/DynamoDB-এর জন্য route-ভিত্তিক private পথ |
| Default VPC | প্রতিটি region-এ AWS-এর তৈরি VPC, সব subnet public |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Route নির্বাচন

Route table-এ longest prefix match (L02-04): `10.20.0.0/16 → local` সবসময় `0.0.0.0/0`-এর আগে জেতে। তাই VPC-র ভেতরের traffic কখনো NAT বা IGW-এ যায় না।

### 8.2 IGW ও public IP

IGW নিজে NAT করে: instance-এর private IP ↔ তার public IP (1:1)। Public subnet-এ থাকলেও **public IP ছাড়া** instance internet-এ যেতে পারে না। আর public IP থাকলেও route table-এ IGW না থাকলে পারে না — দুটোই লাগে।

### 8.3 NAT gateway

- Zonal resource; একটি public subnet-এ বসে; public NAT-এর জন্য Elastic IP লাগে।
- শুধু বাইরের দিকে connection শুরু করা যায়।
- চার্জ: ঘণ্টা + প্রতি GB processed (pricing page)।
- S3-এর বড় traffic-এর জন্য gateway endpoint ব্যবহার করুন — NAT-এর data processing চার্জ এড়ানো যায় (L07-04)।

### 8.4 Main route table

নতুন subnet বানালে সে main table পায়। কেউ main table-এ IGW route যোগ করলে association-হীন সব subnet public হয়ে যায়। নিয়ম:

- Main table শুধু `local`।
- প্রতিটি subnet-এর explicit association।

`vpc_audit.py` implicit association-এ WARN দেয়, আর main-এ internet route থাকলে CRITICAL।

### 8.5 Default VPC

প্রতিটি region-এ default VPC থাকে, যার সব subnet public ও auto public IP। Tutorial সেখানে instance চালায়। এই course-এ নিজের VPC — নিয়ন্ত্রণ ও শেখার জন্য।

> **Fedora-তে:** কোনো পার্থক্য নেই — AWS CLI। Local তুলনার জন্য L02-13-এর `ip netns` lab দুই distro-তেই চলে।

## 9. Practical demonstration

Files:

- [`code/L08-04/vpc_audit.py`](code/L08-04/vpc_audit.py)
- [`vpc_commands.py`](code/L08-04/vpc_commands.py)
- [`sample-plan.json`](code/L08-04/sample-plan.json)
- [`sample/`](code/L08-04/sample/) — হাতে তৈরি describe-* output
- [`test_l08_04.py`](code/L08-04/test_l08_04.py)

### 9.1 Plan → script — আসল output (local)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-04
python3 ../../../07-cloud-fundamentals/code/L07-04/subnet_plan.py sample-plan.json --json > subnets-plan.json
python3 vpc_commands.py subnets-plan.json --vpc-cidr 10.20.0.0/16 --region ap-south-1 --name lab08 --nat single > create-vpc.sh
bash -n create-vpc.sh && echo SYNTAX-OK
```

stderr-এ:

```text
note: --nat single creates NAT gateway(s) + Elastic IP(s) — billed per hour and per GB from creation until deleted; see the VPC pricing page
```

`create-vpc.sh`-এর অংশ:

```bash
VPC=$(aws ec2 create-vpc --cidr-block 10.20.0.0/16 --tag-specifications 'ResourceType=vpc,Tags=[{Key=Name,Value=lab08},{Key=Project,Value=lab08}]' --output text --query Vpc.VpcId)
...
NAT_A=$(aws ec2 create-nat-gateway --subnet-id "$PUBLIC_A" --allocation-id "$EIP_A" --tag-specifications 'ResourceType=natgateway,...' --output text --query NatGateway.NatGatewayId)
aws ec2 wait nat-gateway-available --nat-gateway-ids "$NAT_A"
...
aws ec2 create-route --route-table-id "$RT_APP_B" --destination-cidr-block 0.0.0.0/0 --nat-gateway-id "$NAT_A" >/dev/null
```

- প্রতিটি resource-এ `Project=lab08` tag (test-এ যাচাই) — L08-12-এর cleanup এটা দিয়ে খোঁজে।
- NAT ছাড়া (`--nat none`, default) app subnet-এর internet থাকে না। Lab B-তে package দরকার হলে কী করবেন, সেখানে আলোচনা আছে।

### 9.2 তৈরি ও যাচাই (আপনার account-এ — চালানো হয়নি)

```bash
export AWS_PROFILE=learn-admin
bash create-vpc.sh                       # 💰 --nat single/per-az হলে NAT-এর ঘণ্টা শুরু
V=$(aws ec2 describe-vpcs --filters Name=tag:Project,Values=lab08 --query 'Vpcs[0].VpcId' --output text)
F="--filters Name=vpc-id,Values=$V"
aws ec2 describe-subnets $F > subnets.json
aws ec2 describe-route-tables $F > route-tables.json
aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=$V > nat-gateways.json
aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=$V > internet-gateways.json
python3 vpc_audit.py subnets.json route-tables.json nat-gateways.json internet-gateways.json
```

`--nat single` বাছলে প্রত্যাশা: একটি WARN (app-b → nat-a, cross-AZ), কোনো CRITICAL নয়।

### 9.3 Audit — আসল output (হাতে তৈরি নমুনায়)

```bash
python3 vpc_audit.py sample/*.json; echo "exit=$?"
```

```text
subnet           name       az           cidr             kind      via
subnet-pub-a     public-a   ap-south-1a  10.20.0.0/24     public    igw-0lab  [rtb-public]
subnet-app-a     app-a      ap-south-1a  10.20.16.0/20    private   nat-a  [rtb-private-a]
subnet-data-a    data-a     ap-south-1a  10.20.48.0/24    isolated  no default route  [rtb-main (main, implicit)]
subnet-pub-b     public-b   ap-south-1b  10.20.1.0/24     public    igw-0lab  [rtb-public]
subnet-legacy    legacy     ap-south-1b  10.20.200.0/24   isolated  nat-old (blackhole)  [rtb-legacy]
subnet-app-b     app-b      ap-south-1b  10.20.32.0/20    private   nat-a  [rtb-private-b]

CRITICAL  rtb-legacy       blackhole route 0.0.0.0/0 → nat-old (target deleted) — traffic is silently dropped
WARN      subnet-app-b     MapPublicIpOnLaunch=true on a private subnet — instances get public IPs (billed) that cannot be used
WARN      subnet-app-b     uses nat-a in ap-south-1a — if that AZ fails this subnet loses internet; cross-AZ data is billed
WARN      subnet-data-a    uses the main route table implicitly — associate it explicitly (isolated today, changes if someone edits the main table)
6 subnet(s): 1 critical, 3 warning(s)
exit=1
```

Test-এ main table-এ IGW route যোগ করলে `data-a` **public** হয়ে যায় — নাম "data" থাকা সত্ত্বেও।

### 9.4 লেখার সময়

`vpc_commands.py`-এর প্রথম সংস্করণে nested f-string-এ একই quote ছিল। এটা শুধু Python 3.12+-এ চলে, অথচ repo-র ruff লক্ষ্য 3.11। ruff ধরেছে; label আলাদা variable-এ সরানো হয়েছে, output অপরিবর্তিত (diff দিয়ে যাচাই)।

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- নমুনার শ্রেণিবিভাগ ও finding।
- NAT private subnet-এ।
- Main table-এ internet route।
- Detached IGW ও failed NAT।
- Route target-এর ধরন (IPv6, TGW, VGW)।
- প্রতিটি create-এ tag।
- NAT-এর তিন mode।
- ভুল plan প্রত্যাখ্যান।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `merge()` | একাধিক describe file এক dict-এ | Learner আলাদা file রাখে |
| `explicit` বনাম `mains` | Subnet-এর আসল route table | Implicit association-এর ফাঁদ |
| `classify()` | Default route-এর target → ধরন | নাম নয়, route সিদ্ধান্ত নেয় |
| `blackhole` → isolated + CRITICAL | মৃত target | নীরব timeout |
| NAT-এর home subnet-এর ধরন | Private হলে CRITICAL | NAT নিজে বাইরে যেতে পারে না |
| `vpc_commands.py` ছাপে, চালায় না | Review-এর সুযোগ | Account-এ পরিবর্তন সচেতনভাবে |
| `set -euo pipefail` script-এ | প্রথম ভুলে থামে | অর্ধেক-তৈরি VPC কম |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় `vpc_audit.py` | ৬ subnet, ১ critical, ৩ warning, exit ১ |
| `bash -n create-vpc.sh` | কোনো error নেই |
| আপনার VPC (`--nat single`) | কোনো CRITICAL নেই; cross-AZ WARN প্রত্যাশিত |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Public subnet-এর instance-এ internet নেই | Public IP নেই, বা SG/NACL (L08-05) | IP ও route দুটোই দেখুন |
| Private instance `apt update`-এ timeout | NAT নেই, NAT private subnet-এ, বা blackhole | `vpc_audit.py` |
| `InvalidSubnet.Range` | CIDR VPC-র বাইরে বা overlap | L07-04-এর `subnet_plan.py` |
| `The maximum number of addresses has been reached` | Elastic IP quota | অপ্রয়োজনীয় EIP release |
| VPC মুছতে `DependencyViolation` | ENI, NAT, IGW, endpoint রয়ে গেছে | L08-12-এর ক্রম |
| Instance-এর DNS নাম নেই | `enableDnsHostnames` বন্ধ | Script এটা চালু করে |
| NAT "available", কিন্তু traffic যায় না | Route table association ভুল subnet-এ | Audit-এর `via` কলাম |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Database isolated subnet-এ; app private-এ; শুধু load balancer public-এ।
  - Auto public IP শুধু public subnet-এ।
  - VPC Flow Logs (L08-11) দিয়ে reject হওয়া traffic দেখা যায়।
- **Performance:**
  - একই AZ-এর traffic দ্রুত ও সস্তা।
  - NAT-এর bandwidth সীমা আছে — খুব বড় load-এ একাধিক NAT।
- **Cost:**
  - NAT gateway ও public IPv4 এই module-এর সবচেয়ে সাধারণ "ভুলে-যাওয়া" খরচ।
  - Lab শেষে মুছুন। `inventory.py` (L08-02) দিয়ে `nat-gateway` ও `elastic-ip` নেই, নিশ্চিত হোন।
  - S3 gateway endpoint ব্যবহারে আলাদা চার্জ নেই; interface endpoint চার্জযোগ্য।

## 14. Hands-on exercise

1. নিজের account-এ `--nat none` দিয়ে VPC বানিয়ে audit চালান, তারপর L08-12-এর আগে হাতে মুছুন (Section 12-এর ক্রম)।
2. `vpc_commands.py`-তে `--s3-endpoint` যোগ করুন: `create-vpc-endpoint --vpc-endpoint-type Gateway --service-name com.amazonaws.REGION.s3 --route-table-ids …` (private ও isolated table-এ)।
3. `vpc_audit.py`-তে নতুন নিয়ম: একই VPC-তে দুটি subnet-এর CIDR overlap (input যদি হাতে বদলানো হয়)।
4. Default VPC-র describe output নিয়ে audit চালান। কী দেখেন, এবং কেন production-এ এটা ব্যবহার করবেন না?
5. লিখুন: TaskFlow-এর production-এ AZ-প্রতি NAT, না এক NAT? খরচ (pricing page থেকে, তারিখসহ) ও ঝুঁকি দিয়ে যুক্তি দিন।

## 15. Mini-project — VPC as data

`plan.json` → `vpc_commands.py` → `create-vpc.sh` → describe → `vpc_audit.py` — এই পুরো চক্র একটি Makefile-এ (`make plan`, `make apply`, `make audit`)। Module 12-এ একই VPC Terraform দিয়ে বানানো হবে, এবং audit তখনো একই থাকবে — তুলনা করুন।

## 16. Interview প্রশ্ন

1. Public ও private subnet-এর পার্থক্য AWS-এ কী দিয়ে ঠিক হয়?
2. NAT gateway কোথায় বসে, এবং কেন?
3. Main route table-এর ঝুঁকি কী?
4. প্রতিটি subnet-এ কয়টি address reserved, কোনগুলো?
5. একটি private instance internet-এ যেতে পারছে না — কোন ক্রমে খুঁজবেন?
6. AZ-প্রতি NAT বনাম এক NAT — trade-off কী?

## 17. Self-assessment প্রশ্ন

1. অফিস-ভবন analogy কোথায় মেলে না?
2. Blackhole route কখন তৈরি হয়, client কী দেখে?
3. Public subnet-এ থাকলেও কখন instance internet পায় না?
4. `MapPublicIpOnLaunch=true` private subnet-এ কেন অপচয়?
5. Default VPC-র বৈশিষ্ট্য কী?

## 18. সংক্ষিপ্ত সারাংশ

- Subnet-এর চরিত্র route table ঠিক করে: IGW = public, NAT = private, কিছু না = isolated।
- Main table শুধু local; প্রতিটি subnet explicit।
- NAT public subnet-এ; AZ-নির্ভরতা ও খরচ সচেতনভাবে বাছুন।
- Plan → script (`vpc_commands.py`) → audit (`vpc_audit.py`); প্রতিটি resource-এ Project tag।

## 19. Completion checklist

- [ ] নিজের VPC তৈরি (বা script পর্যন্ত), audit-এ কোনো CRITICAL নেই
- [ ] NAT/EIP ব্যবহার করলে মোছা হয়েছে, `inventory.py`-তে যাচাই
- [ ] Exercise ২ (S3 gateway endpoint) শেষ
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Amazon VPC — How it works: https://docs.aws.amazon.com/vpc/latest/userguide/how-it-works.html
- Amazon VPC — Subnets: https://docs.aws.amazon.com/vpc/latest/userguide/configure-subnets.html
- Amazon VPC — Route tables: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- Amazon VPC — Internet gateways: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Internet_Gateway.html
- Amazon VPC — NAT gateways: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- Amazon VPC pricing: https://aws.amazon.com/vpc/pricing/

---

**পরের lesson:** L08-05 — Security group ও network ACL
