# L02-14 — Cloud networking concept: VPC, subnet, routing, peering

| | |
|---|---|
| **Module** | 02 — Computer Networking |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L02-03 — CIDR](L02-03-ip-addressing-cidr.md), [L02-04 — Routing/NAT](L02-04-routing-nat.md), [L02-10 — Security group/NACL](L02-10-firewalls.md) |
| **Label** | — (concept + offline simulator; কোনো cloud resource তৈরি হয় না, খরচ শূন্য) |
| **Tested** | `vpc_sim.py`: ১০টি test পাস — internet gateway, NAT, data tier-এর egress নেই, peering-এর return path, non-transitive peering, public IP ছাড়া IGW, lint-এর ভুল-design সনাক্তকরণ (Python 3.14, Windows)। `lint` ও ৫টি `trace` চালানো হয়েছে — output Section 9-এ। `aws ec2 describe-*` command **কোনো আসল account-এ চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- **VPC** কী: cloud-এর ভেতরে আপনার নিজের private network।
- **Subnet** ও availability zone; public, private ও isolated (data) subnet-এর পার্থক্য আসলে **route table**-এ।
- **Internet gateway**, **NAT gateway**, implicit **local route**।
- **VPC peering** — non-transitive, overlapping CIDR অসম্ভব, return route লাগে; transit gateway-র ধারণা।
- **VPC endpoint** ও private connectivity; **CIDR planning** কেন দিনের প্রথম সিদ্ধান্ত।
- Offline simulator দিয়ে packet-এর পথ trace ও design lint।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

এই module-এ যা শিখেছেন (CIDR, routing, NAT, firewall, load balancer, VPN) — cloud-এ এগুলো সব **API-চালিত, virtual** রূপে আসে। Physical router বা switch নেই; আছে route table, gateway ও security group নামের configuration।

ভুল design-এর পরিণতি দীর্ঘস্থায়ী:

- Database ভুল করে public subnet-এ — Internet থেকে পৌঁছানো যায়।
- সব VPC একই `10.0.0.0/16` দিয়ে তৈরি — পরে peering বা VPN অসম্ভব; migration ছাড়া সমাধান নেই।
- একটি NAT gateway পুরো region-এর জন্য — একটি AZ বন্ধ হলে সব private server-এর বাইরের যোগাযোগ বন্ধ; প্রতি মাসে অপ্রত্যাশিত cross-AZ ও NAT data বিল।
- Peering তৈরি হলো, কিন্তু একদিকের route table-এ route নেই — "connection timeout", সবাই firewall সন্দেহ করেন।

## 3. সহজ ভাষায় পরিচয়

**VPC** (Virtual Private Cloud; Azure-এ VNet, GCP-তে VPC network) = একটি region-এ আপনার নিজের isolated network, একটি CIDR block সহ (যেমন `10.0.0.0/16`)।

**Subnet** = VPC-র CIDR-এর একটি অংশ, **একটি availability zone-এ** (AWS-এ; GCP-তে subnet regional)। Instance subnet-এ থাকে।

**কোনো subnet "public" কিনা তা ঠিক হয় তার route table দিয়ে:**

| Subnet ধরন | Route table-এ `0.0.0.0/0` | Instance-এর public IP | কী থাকে |
|---|---|---|---|
| Public | → **internet gateway** | হ্যাঁ (প্রয়োজন হলে) | Load balancer, NAT gateway, bastion |
| Private | → **NAT gateway** | না | Application server |
| Isolated / data | কোনো default route নেই | না | Database, cache |

**Gateway:**

| Gateway | কাজ | দিক |
|---|---|---|
| Internet gateway (IGW) | Public IP ↔ private IP 1:1 অনুবাদ, Internet-এ পথ | দুই দিকে |
| NAT gateway | Private instance-কে বাইরে যেতে দেয় (masquerade, L02-04) | শুধু বাইরের দিকে শুরু |
| VPC peering | দুটি VPC-কে সরাসরি যুক্ত | দুই দিকে, route লাগে |
| Transit gateway | বহু VPC/VPN-এর কেন্দ্রীয় router (hub) | — |
| VPC endpoint | Cloud service (S3, ECR ইত্যাদি)-তে Internet ছাড়া পৌঁছানো | — |
| VPN / Direct Connect | Office/data center ↔ VPC (L02-11) | — |

**Local route:** প্রতিটি route table-এ স্বয়ংক্রিয় route "VPC CIDR → local" — VPC-র ভেতরের সব subnet একে অপরকে route-এ পায় (ঠেকাতে চাইলে security group/NACL)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### গেটেড আবাসিক এলাকা

- **VPC** = দেয়ালঘেরা এলাকা, নিজের রাস্তার নম্বর-পদ্ধতি (CIDR)।
- **Subnet** = এলাকার ভেতরের ব্লক; প্রতিটি ব্লক একটি নির্দিষ্ট অংশে (AZ)।
- **Route table** = প্রতিটি ব্লকের মোড়ের দিকনির্দেশক ফলক: "বাইরে যেতে → প্রধান গেট" বা "→ ডেলিভারি অফিস"।
- **Internet gateway** = প্রধান গেট — যাদের নিজস্ব বাইরের ঠিকানা (public IP) আছে তারা আসা-যাওয়া করে।
- **NAT gateway** = ডেলিভারি অফিস — ভেতরের বাসিন্দারা বাইরে চিঠি পাঠান অফিসের ঠিকানা দিয়ে; উত্তর অফিসে আসে, অফিস পৌঁছে দেয়; কিন্তু বাইরের কেউ সরাসরি বাসিন্দার কাছে প্রথমে চিঠি পাঠাতে পারে না।
- **Peering** = পাশের এলাকার সাথে একটি সরাসরি রাস্তা।

### Analogy কোথায় মেলে না

- দুই এলাকার রাস্তার নম্বর একই হলেও মানুষ গুলিয়ে ফেলে না। Network-এ **overlapping CIDR = একই ঠিকানা দুই জায়গায়** — router সিদ্ধান্ত নিতে পারে না; peering তৈরিই করা যায় না।
- পাশের এলাকা (B) দিয়ে তৃতীয় এলাকায় (C) হেঁটে যাওয়া যায়। **VPC peering transitive নয়** — A↔B ও B↔C থাকলেও A থেকে C যাওয়া যায় না; অনেক VPC হলে transit gateway।
- রাস্তা দুই দিকেই ব্যবহার হয়। Peering-এর route **প্রতিটি দিকের route table-এ আলাদা করে** যোগ করতে হয় — একদিকে ভুলে গেলে packet যায়, উত্তর আসে না (Section 9-এর `metrics-1`)।

## 5. Real-world engineering scenario — "Peering আছে, তবু timeout"

**পরিস্থিতি:** `prod` VPC-র application server-গুলোকে `shared` VPC-র monitoring server-এ (`metrics-1`, `10.1.3.10`) metric পাঠাতে হবে। Peering `prod-shared` তৈরি ও accept করা হয়েছে; prod-এর private route table-এ `10.1.0.0/16 → pcx` route আছে। `tools-1` (`10.1.2.10`)-এ connection কাজ করে, কিন্তু `metrics-1`-এ timeout।

**Diagnosis:** দুই দিকের পথ আলাদা করে ভাবুন।

```text
api-1 → metrics-1 : prod 'private' route table: 10.1.0.0/16 → pcx  ✓
metrics-1 → api-1 : shared 'metrics' route table: 10.0.10.5-এর জন্য কোনো route নেই ✗
```

Security group ঠিক থাকলেও SYN পৌঁছায়, কিন্তু SYN-ACK ফেরার পথ নেই। `tools` subnet-এর route table-এ `10.0.0.0/16 → pcx` ছিল, `metrics` subnet-এর আলাদা route table-এ ছিল না।

**সমাধান:** `metrics` route table-এ `10.0.0.0/16 → pcx-prod-shared`। দীর্ঘমেয়াদে: route table Terraform-এ (Module 07), এবং একটি পরীক্ষা যা দুই দিকের route যাচাই করে — এই lesson-এর `vpc_sim.py trace`-এর মতো, অথবা cloud-এর নিজস্ব reachability analyzer।

**শিক্ষা:** "Connection timeout" = packet বা উত্তর কোথাও হারাচ্ছে। Cloud-এ পাঁচটি জায়গা দেখুন — **দুই দিকের** route table, security group, NACL (stateless, L02-10), এবং host firewall।

## 6. Diagram — একটি সাধারণ তিন-স্তরের VPC

```text
Region ─────────────────────────────────────────────────────────────────────────────
 VPC prod 10.0.0.0/16                                                     Internet
 ┌─────────────── AZ a ───────────────┐ ┌─────────────── AZ b ───────────┐    ▲
 │ public 10.0.0.0/24  [ALB] [NAT-a]──┼─┼────────────────────────────────┼─► IGW
 │   rt: 0.0.0.0/0 → igw              │ │ public 10.0.1.0/24 [ALB] [NAT-b]│
 │ app    10.0.10.0/24 [api-1]        │ │ app 10.0.11.0/24 [api-2]        │
 │   rt: 0.0.0.0/0 → NAT-a            │ │   rt: 0.0.0.0/0 → NAT-b  (প্রতি AZ-এ NAT)
 │       10.1.0.0/16 → pcx ───────────┼─┼──────────────┐                 │
 │ data   10.0.20.0/24 [db primary]   │ │ data 10.0.21.0/24 [db standby]  │
 │   rt: (শুধু local)                 │ │   rt: (শুধু local)               │
 └────────────────────────────────────┘ └──────────────┼─────────────────┘
                                                       ▼ peering (দুই দিকে route)
 VPC shared 10.1.0.0/16  [tools-1] [metrics-1]   rt: 10.0.0.0/16 → pcx
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Region / AZ | ভৌগোলিক এলাকা / তার ভেতরে আলাদা data center গোষ্ঠী |
| VPC / VNet | Cloud-এ আপনার private network |
| Subnet | VPC CIDR-এর অংশ, একটি AZ-এ (AWS) |
| Route table | Subnet-এর packet কোথায় যাবে |
| Local route | VPC-র ভেতরের implicit route |
| Internet gateway | Public IP-সহ instance-এর Internet পথ |
| NAT gateway | Private instance-এর শুধু-বাইরের পথ |
| Elastic / public IP | Instance-এর Internet ঠিকানা |
| VPC peering | দুই VPC-র সরাসরি সংযোগ — non-transitive |
| Transit gateway | বহু network-এর কেন্দ্রীয় router |
| VPC endpoint / PrivateLink | Cloud service-এ private পথ |
| Flow logs | কোন connection accept/reject হলো তার log |
| Reachability analyzer | Configuration থেকে পথ বিশ্লেষণের cloud tool |
| Egress | বাইরের দিকের traffic (প্রায়ই বিলযুক্ত) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Route table-এর সিদ্ধান্ত

Subnet-এর route table-এ longest prefix match (L02-04) — local route সবসময় আছে। Target হতে পারে igw, nat, pcx, tgw, vpce, ENI ইত্যাদি। কোনো route না মিললে packet ফেলে দেওয়া হয়। Target-এর resource মুছে গেলে route "blackhole" অবস্থায় থাকে।

### 8.2 Internet gateway বনাম NAT gateway

- IGW instance-এর private IP-কে তার নিজস্ব public IP-তে 1:1 অনুবাদ করে — তাই **public IP ছাড়া instance public subnet-এ থাকলেও Internet-এ যেতে পারে না**।
- NAT gateway নিজে public subnet-এ বসে, নিজের public IP দিয়ে বহু private instance-এর connection masquerade করে (L02-04-এর port exhaustion এখানেও প্রাসঙ্গিক)। NAT gateway একটি AZ-এর resource — **প্রতি AZ-এ একটি** রাখলে AZ outage-এ শুধু ঐ AZ প্রভাবিত, এবং cross-AZ data খরচ নেই।
- IPv6-এ NAT নেই; "egress-only internet gateway" শুধু বাইরের দিকের connection অনুমতি দেয়।

### 8.3 Peering-এর তিন নিয়ম

1. CIDR overlap করা যাবে না।
2. Non-transitive — B-এর মাধ্যমে C-তে বা B-এর IGW/NAT দিয়ে Internet-এ যাওয়া যায় না।
3. দুই দিকের route table-এ route + দুই দিকের security group-এ অনুমতি।

অনেক VPC (প্রতিটি team/environment-এর জন্য) হলে mesh peering অচল (N VPC-তে N(N−1)/2 সংযোগ) → **transit gateway** (hub-and-spoke)।

### 8.4 CIDR planning

- প্রতিটি VPC-কে organization-ব্যাপী অনন্য range দিন (যেমন prod `10.0.0.0/16`, staging `10.1.0.0/16`, dev `10.2.0.0/16`, office VPN `10.100.0.0/16`) — একটি IPAM spreadsheet/tool।
- Subnet যথেষ্ট বড় রাখুন: Kubernetes-এ (AWS VPC CNI) প্রতিটি pod একটি VPC IP নেয় — `/24` (২৫১টি ব্যবহারযোগ্য) দ্রুত ফুরিয়ে যায় (L02-03-এর cloud-reserved ৫টি address)।
- পরে যোগ করার জায়গা রাখুন (তৃতীয় AZ, নতুন tier)।
- `docker0`-এর `172.17.0.0/16` বা অন্য tool-এর default range-এর সাথে সংঘর্ষ এড়ান।

### 8.5 অন্য cloud-এ

GCP-তে VPC **global**, subnet regional, route ও firewall rule VPC-স্তরে; Azure-এ VNet ও subnet-এ NSG, UDR (user-defined route)। ধারণা একই — বিস্তারিত Module 08-এ।

## 9. Practical demonstration

File: [`code/L02-14/vpc_sim.py`](code/L02-14/vpc_sim.py), [`sample-vpcs.json`](code/L02-14/sample-vpcs.json) — **হাতে তৈরি উদাহরণ**: `prod` (৫টি subnet, একটি NAT), `shared` (peered), `dev` (prod-এর একই CIDR — ইচ্ছাকৃত ভুল)।

### 9.1 Design lint

```bash
cd ~/devops-ai-engineering/02-computer-networking/code/L02-14
python3 vpc_sim.py lint sample-vpcs.json; echo "exit=$?"
```

**আসল output:**

```text
ERROR shared peers with both dev and prod, whose CIDRs overlap (10.0.0.0/16) — shared cannot route to both; plan non-overlapping CIDRs up front
WARN  prod: NAT gateway nat-a serves subnets in AZs ['a', 'b'] — one AZ outage cuts egress for all, and cross-AZ traffic is billed; use one NAT per AZ
3 VPC(s), 8 subnet(s), 2 finding(s)
exit=1
```

প্রথম finding: dev ও shared-এর মধ্যে নিজে কোনো overlap নেই (তাই peering তৈরি হয়ে যায়), কিন্তু shared-এর কাছে `10.0.0.0/16` এখন দুটি জায়গায় — ঠিক Section 2-এর "সবাই একই range" সমস্যা। এই lint লেখার সময় প্রথমে শুধু সরাসরি overlap খোঁজা হচ্ছিল; test-এ ধরা পড়ল যে আসল সমস্যাটি পরোক্ষ — তাই আলাদা check যোগ হয়েছে।

### 9.2 Packet-এর পথ trace

```bash
python3 vpc_sim.py trace sample-vpcs.json --from web-1 --to 1.1.1.1
python3 vpc_sim.py trace sample-vpcs.json --from api-2 --to 1.1.1.1
python3 vpc_sim.py trace sample-vpcs.json --from db-1  --to 1.1.1.1
python3 vpc_sim.py trace sample-vpcs.json --from api-1 --to 10.1.2.10
python3 vpc_sim.py trace sample-vpcs.json --from api-1 --to 10.1.3.10
```

**আসল output:**

```text
web-1 10.0.0.10 in prod-public-a (prod, AZ a)
  → route table 'public': 1.1.1.1 matches 0.0.0.0/0 → igw
  → internet gateway: 10.0.0.10 ↔ its public IP (1:1 NAT) → internet
REACHABLE

api-2 10.0.11.5 in prod-app-b (prod, AZ b)
  → route table 'private': 1.1.1.1 matches 0.0.0.0/0 → nat:nat-a
  → NAT gateway nat-a in prod-public-a (AZ a): source 10.0.11.5 → NAT's public IP
  → internet gateway → internet (replies come back through the NAT; inbound connections from the internet are not possible)
REACHABLE

db-1 10.0.20.7 in prod-data-a (prod, AZ a)
  → route table 'data': no route to 1.1.1.1 → dropped
NOT REACHABLE

api-1 10.0.10.5 in prod-app-a (prod, AZ a)
  → route table 'private': 10.1.2.10 matches 10.1.0.0/16 → pcx:prod-shared
  → via peering prod-shared into shared, subnet shared-tools
  → return route in 'tools' via prod-shared ✓ — delivered
REACHABLE

api-1 10.0.10.5 in prod-app-a (prod, AZ a)
  → route table 'private': 10.1.3.10 matches 10.1.0.0/16 → pcx:prod-shared
  → via peering prod-shared into shared, subnet shared-metrics
  → return path broken: shared-metrics's route table 'metrics' has no route for 10.0.10.5 → replies never come back (one-way)
NOT REACHABLE
```

- `api-2` (AZ b) AZ a-র NAT ব্যবহার করে — lint-এর WARN-এর বাস্তব রূপ।
- `db-1`-এর কোনো egress নেই — data tier-এর জন্য এটাই চাওয়া (package update-এর জন্য VPC endpoint বা অন্য পদ্ধতি)।
- শেষটি Section 5-এর ঘটনা।

### 9.3 আসল cloud-এ (read-only, নিজের account-এ — **কোনো resource তৈরি করে না**)

AWS CLI configure করা থাকলে (Module 08), শুধু পড়ার command:

```bash
aws ec2 describe-vpcs --query 'Vpcs[].{id:VpcId,cidr:CidrBlock}' --output table
aws ec2 describe-subnets --query 'Subnets[].{id:SubnetId,cidr:CidrBlock,az:AvailabilityZone,vpc:VpcId}' --output table
aws ec2 describe-route-tables --query 'RouteTables[].{id:RouteTableId,routes:Routes[].[DestinationCidrBlock,GatewayId,NatGatewayId,VpcPeeringConnectionId]}'
aws ec2 describe-nat-gateways --query 'NatGateways[].{id:NatGatewayId,subnet:SubnetId,state:State}'
aws ec2 describe-vpc-peering-connections
```

Exercise ৪-এ এই output থেকে `vpc_sim.py`-এর JSON তৈরি করবেন।

⚠️ **খরচ:** VPC, subnet, route table, internet gateway, peering নিজে সাধারণত বিনামূল্যে; কিন্তু **NAT gateway ঘণ্টা ও প্রতি GB processed data অনুযায়ী বিল হয়** এবং ভুলে চালু রাখা NAT gateway মাসে উল্লেখযোগ্য খরচ তৈরি করে; public IPv4 address-ও বিলযুক্ত; cross-AZ ও inter-region data transfer বিলযুক্ত। কিছু তৈরির আগে provider-এর বর্তমান pricing page দেখুন — Module 08-এ budget alarm সহ।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_vpc_sim.py`](code/L02-14/test_vpc_sim.py)-এর ১০টি test: public instance → IGW, private → NAT (অন্য AZ), data tier-এ egress নেই কিন্তু VPC-র ভেতরে আছে, peering-এর return path, non-transitive, public IP ছাড়া IGW, sample lint (দুটি finding), সরাসরি overlap, ভাঙা design (subnet বাইরে, NAT ভুল subnet-এ, অস্তিত্বহীন NAT, public IP-র route নেই), CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `routes()` local route যোগ | প্রতিটি table-এ VPC CIDR → local | AWS-এর implicit route |
| `lookup` longest prefix | L02-04-এর একই নিয়ম | Cloud route table-ও তাই |
| `trace` igw শাখায় public IP পরীক্ষা | IGW শুধু 1:1 অনুবাদ করে | Public subnet ≠ Internet access |
| NAT শাখায় NAT-এর subnet-এর route | NAT নিজে IGW-র উপর নির্ভরশীল | ভুল subnet-এ NAT = অকেজো |
| pcx শাখা: peer CIDR + return route | Non-transitive ও দুই দিক | Section 5 |
| lint: peer-দের পারস্পরিক overlap | পরোক্ষ সমস্যা | Test-এ ধরা পড়া design ভুল |
| lint: NAT-এর AZ সংখ্যা | Availability + খরচ | প্রতি AZ-এ NAT |

**সীমাবদ্ধতা:** security group/NACL, transit gateway, endpoint, IPv6, DNS — নেই। এটি ধারণা যাচাইয়ের model; আসল সত্য cloud API ও reachability analyzer।

**Python কেন এখানে, কোথায় নয়:** design-কে data হিসেবে রেখে CI-তে যাচাই (policy-as-code) Python-এর ভালো কাজ। Network তৈরি করবেন Terraform দিয়ে (Module 07) — Python script দিয়ে cloud resource তৈরি করা state ও review-হীন পরিবর্তনের ঝুঁকি।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `lint sample-vpcs.json` | ১ ERROR, ১ WARN, exit ১ |
| `trace --from db-1 --to 1.1.1.1` | NOT REACHABLE (no route) |
| `trace --from api-1 --to 10.1.3.10` | return path broken |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Public subnet-এর instance Internet-এ যায় না | Public IP নেই | Instance-এর বিবরণ | Public IP/Elastic IP, বা NAT ব্যবহার |
| Private instance-এ `apt update` ঝোলে | NAT route নেই, NAT ভুল subnet-এ, NACL-এ ephemeral port | Route table, `vpc_sim.py trace` | Route/NAT ঠিক; NACL (L02-10) |
| Peering-এ timeout | একদিকের route নেই, SG | দুই দিকের route table, flow logs | Return route |
| Peering তৈরি হয় না | CIDR overlap | VPC CIDR তুলনা | নতুন CIDR-এ migration (ব্যয়বহুল) |
| B দিয়ে C-তে যায় না | Non-transitive | — | Transit gateway বা সরাসরি peering |
| মাসের বিলে বড় NAT খরচ | S3/ECR traffic NAT দিয়ে | Cost explorer, flow logs | Gateway endpoint (S3), interface endpoint |
| Pod IP ফুরিয়ে গেছে | ছোট subnet | Subnet-এর available IP | বড় subnet বা secondary CIDR |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Database ও internal service কখনো public subnet-এ নয়; default route শুধু যেখানে দরকার; flow logs চালু (রহস্যময় timeout ও আক্রমণ দুটোর জন্যই); cloud service-এ VPC endpoint (Internet দিয়ে না গিয়ে); security group-এর source হিসেবে security group (L02-10); network design Terraform-এ, review-সহ।
- **Performance:** একই AZ-এ নিবিড় যোগাযোগকারী service (latency কম); jumbo frame (L02-09); NAT gateway-এর bandwidth সীমা ও port exhaustion (L02-04)।
- **Cost:** NAT gateway (ঘণ্টা + GB), public IPv4, cross-AZ ও cross-region transfer, transit gateway attachment — network খরচ প্রায়ই compute-এর পরে দ্বিতীয় বড় অপ্রত্যাশিত বিল। প্রতি AZ-এ NAT availability বাড়ায় কিন্তু ঘণ্টাভিত্তিক খরচও বাড়ায় — dev environment-এ একটি NAT বা NAT instance যুক্তিসঙ্গত trade-off হতে পারে (Module 08-এর cost lesson)।

## 14. Hands-on exercise

1. `sample-vpcs.json` ঠিক করুন: dev-এর নতুন CIDR (`10.2.0.0/16`), AZ b-তে দ্বিতীয় NAT, `metrics`-এ return route — `lint` শূন্য finding দেবে এবং সব trace REACHABLE (শুধু `db-1 → internet` ছাড়া)।
2. `vpc_sim.py`-তে transit gateway target (`tgw:NAME`) যোগ করুন: tgw-এর নিজস্ব route table থাকবে; peering-এর মতো non-transitive নয়। Test লিখুন।
3. L02-03-এর `subnet_calc.py plan` দিয়ে একটি VPC-র জন্য ৩ AZ × ৩ tier subnet পরিকল্পনা করুন, তারপর সেই পরিকল্পনা `vpc_sim.py`-এর JSON-এ রূপান্তর করে lint চালান।
4. AWS account থাকলে (শুধু read-only): Section 9.3-এর command চালিয়ে default VPC-র JSON তৈরি করে `lint` চালান। Default VPC-র সব subnet কি public?
5. নিজের organization-এর (বা কাল্পনিক) জন্য একটি CIDR allocation table লিখুন: ৪টি environment × ৩টি region + office VPN + Kubernetes pod range।

## 15. Mini-project — VPC design review checklist + tool

একটি markdown checklist (public/private/data ভাগ, প্রতি AZ NAT, CIDR অনন্য, endpoint, flow logs, peering-এর দুই দিক) এবং `vpc_sim.py`-কে বাড়িয়ে একটি `review` command যা checklist-এর প্রতিটি আইটেম PASS/FAIL দেখায়। Module 07-এ Terraform plan-এর JSON থেকে এই model তৈরি করে CI-তে চালানো হবে।

## 16. Interview প্রশ্ন

1. Public ও private subnet-এর আসল পার্থক্য কী?
2. Internet gateway ও NAT gateway-এর পার্থক্য।
3. VPC peering-এর সীমাবদ্ধতা কী কী? কখন transit gateway?
4. Private instance-এ package install হচ্ছে না — কীভাবে debug করবেন?
5. CIDR planning কেন গুরুত্বপূর্ণ? Kubernetes কীভাবে প্রভাব ফেলে?
6. NAT gateway খরচ কমানোর উপায়।
7. একটি তিন-স্তরের highly available VPC design ব্যাখ্যা করুন।

## 17. Self-assessment প্রশ্ন

1. আবাসিক এলাকা analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ `tools-1` কাজ করল কিন্তু `metrics-1` করল না কেন?
3. Public subnet-এ থাকা instance Internet-এ যেতে না পারার কারণ কী হতে পারে?
4. Lint-এর প্রথম finding সরাসরি peering overlap নয় — তবু সমস্যা কেন?
5. প্রতি AZ-এ NAT রাখার দুটি কারণ।

## 18. সংক্ষিপ্ত সারাংশ

- VPC = cloud-এ private network; subnet = এক AZ-এ CIDR-এর অংশ।
- Public/private/data — পার্থক্য route table-এর default route-এ (IGW / NAT / কিছুই নয়)।
- IGW-এর জন্য public IP লাগে; NAT শুধু বাইরের দিকের connection; প্রতি AZ-এ NAT।
- Peering: overlap নয়, transitive নয়, দুই দিকে route।
- CIDR planning দিনের প্রথম সিদ্ধান্ত; NAT ও data transfer প্রধান network খরচ।
- "Timeout" = দুই দিকের route, SG, NACL, host firewall — পাঁচটি জায়গা দেখুন।

## 19. Completion checklist

- [ ] `vpc_sim.py lint` ও পাঁচটি trace ব্যাখ্যা করতে পারি
- [ ] Sample ঠিক করে শূন্য finding পেয়েছি (Exercise ১)
- [ ] একটি ৩-AZ, ৩-tier VPC-র CIDR পরিকল্পনা করেছি
- [ ] NAT gateway ও data transfer খরচের কারণগুলো বলতে পারি
- [ ] `python3 -m unittest -v`-এ ১০টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS — How Amazon VPC works: https://docs.aws.amazon.com/vpc/latest/userguide/how-it-works.html
- AWS — Route tables: https://docs.aws.amazon.com/vpc/latest/userguide/VPC_Route_Tables.html
- AWS — NAT gateways: https://docs.aws.amazon.com/vpc/latest/userguide/vpc-nat-gateway.html
- AWS — VPC peering: https://docs.aws.amazon.com/vpc/latest/peering/what-is-vpc-peering.html
- AWS — Transit gateways: https://docs.aws.amazon.com/vpc/latest/tgw/what-is-transit-gateway.html
- AWS — VPC Reachability Analyzer: https://docs.aws.amazon.com/vpc/latest/reachability/what-is-reachability-analyzer.html
- Google Cloud — VPC overview: https://cloud.google.com/vpc/docs/vpc
- Azure — Virtual Network overview: https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview

---

**পরের lesson:** L02-15 — tcpdump ও Wireshark দিয়ে packet inspection
