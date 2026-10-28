# L07-03 — Region, availability zone ও fault domain

| | |
|---|---|
| **Module** | 07 — Cloud Fundamentals |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L07-02 — Shared responsibility](L07-02-service-models-shared-responsibility.md), [L02-12 — Load balancing](../02-computer-networking/L02-12-load-balancing.md) |
| **Label** | — |
| **Tested** | `availability.py`: ৬টি test পাস (Python 3.14.5, Windows)। বিশ্লেষণী হিসাব Monte Carlo simulation-এর সাথে মেলানো হয়েছে (৪ লাখ trial-এ পার্থক্য ০.০০০১-এর কম)। লেখার সময় **আমার একটি ভুল ধারণা** ধরা পড়েছে (Section 9.3)। সব availability সংখ্যা উদাহরণের **অনুমান**, কোনো provider-এর SLA নয়। কোনো cloud resource তৈরি হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Region, availability zone (AZ), edge location — কী, এবং কেন আলাদা।
- **Fault domain:** কোন জিনিসগুলো একসাথে ব্যর্থ হয় — rack, AZ, region, provider, নিজের deploy।
- Availability-র হিসাব: serial (গুণ), parallel redundancy, এবং **correlated failure** — কেন "দুটি server = দ্বিগুণ নিরাপদ" প্রায়ই ভুল।
- "Nines" ও বছরে downtime।
- Single point of failure (SPOF) খোঁজা।
- Multi-AZ বনাম multi-region: খরচ, latency, জটিলতা, data residency।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L06-এর শেষে TaskFlow একটি VM-এ চলছে। সেই VM-এর host, rack, বা পুরো AZ বন্ধ হলে service বন্ধ। কতটা redundancy যথেষ্ট, এবং কোথায় রাখবেন?

ভুল redundancy সবচেয়ে বিপজ্জনক — খরচ হয়, কিন্তু সুরক্ষা দেয় না:

- **দুটি app server একই AZ-এ** — AZ বন্ধ হলে দুটোই বন্ধ।
- **Load balancer দুই AZ-এ, database একটিতে।**
- **Backup একই region-এ** — region-ব্যাপী ঘটনায় backup-ও যায়।

Fault domain বোঝা মানে প্রশ্ন করা: "এই দুটি জিনিস কি একই কারণে একসাথে ব্যর্থ হতে পারে?"

## 3. সহজ ভাষায় পরিচয়

| স্তর | কী | একসাথে ব্যর্থ হয় |
|---|---|---|
| Host / rack | একটি physical server / তাক | Host-এর hardware, rack-এর বিদ্যুৎ ও switch |
| Availability Zone | এক বা একাধিক data center, আলাদা বিদ্যুৎ, cooling ও network | AZ-এর বিদ্যুৎ, বন্যা, network |
| Region | একটি ভৌগোলিক এলাকায় কয়েকটি AZ, নিজেদের মধ্যে কম latency-র link | Region-ব্যাপী control plane বা software সমস্যা, বড় দুর্যোগ |
| Provider | একটি cloud company | Global service-এর ভুল (DNS, IAM, ভুল config push) |
| নিজের deploy | আপনার code ও config | সব জায়গায় একই ভুল release |

```text
serial (সবগুলো লাগবে):      A = A1 × A2 × A3                       ← যত অংশ, তত কম
parallel (যেকোনো একটি):     A = 1 − (1 − A1)(1 − A2)               ← শুধু যদি ব্যর্থতা স্বাধীন হয়!
৯৯.৯% ≈ ৮.৮ ঘণ্টা/বছর · ৯৯.৯৯% ≈ ৫৩ মিনিট · ৯৯.৯৯৯% ≈ ৫ মিনিট
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ডিম ও ঝুড়ি

- একটি server = সব ডিম একটি ঝুড়িতে।
- দুটি server = দুটি ঝুড়ি।
- **একই AZ-এ দুটি server** = দুটি ঝুড়ি, কিন্তু একই তাকে। তাক ভাঙলে দুটোই পড়ে।
- **দুই AZ** = দুই ঘরের দুই তাকে।
- **দুই region** = দুই বাড়িতে।

### Analogy কোথায় মেলে না

- **ঝুড়ির ভাঙা স্বাধীন ঘটনা মনে হয়।** বাস্তবে ব্যর্থতা প্রায়ই correlated: একই AZ, একই software version, একই dependency (DNS, IAM), একই ভুল deploy। Parallel redundancy-র `1 − (1−A)²` formula এই correlation উপেক্ষা করে। এই lesson-এর হিসাবে, একই AZ-এ দুটি instance-এর জন্য naive formula বলে বছরে ১৯ মিনিট downtime — সঠিক হিসাব **৯ ঘণ্টা** (Section 9.2)।
- **বেশি ঝুড়ি = বেশি নিরাপদ।** প্রতিটি নতুন অংশ নতুন ব্যর্থতার পথও আনে: load balancer, replication, failover-এর logic। Failover-এর code নিজেই ভাঙতে পারে, এবং সাধারণত ভাঙে ঠিক যখন দরকার। তাই test না করা redundancy আসলে redundancy নয় (Module 18/30)।
- **ডিমের ঝুড়ি দূরে রাখা বিনামূল্যে।** AZ-এর মধ্যে data transfer-এ খরচ ও latency আছে; region-এর মধ্যে আরও বেশি। Multi-region-এ data consistency ও data residency আইনের প্রশ্নও আসে।

## 5. Real-world engineering scenario — "দুটি server ছিল, তবুও সব বন্ধ"

**পরিস্থিতি:** TaskFlow-কে "highly available" করতে একটি load balancer ও দুটি app VM যোগ করা হলো, এবং database একটি VM-এ। খরচ প্রায় তিন গুণ। এক রাতে একটি AZ-এর power বিভ্রাটে পুরো service দুই ঘণ্টা বন্ধ রইল।

**কারণ:** Console-এ instance তৈরির সময় default subnet নেওয়া হয়েছিল, ফলে সব কিছু (LB node, দুটি app, DB) একই AZ-এ। `availability.py same-az-pair.json`-এর আসল output:

```text
Two app VMs behind a load balancer — but both in AZ a: availability 0.997876 (99.7876%) ≈ downtime 18.6 h/year
  SPOF: lb: 1 instance(s), all needed — any instance failure is an outage
  SPOF: app: all 2 instances in AZ a — one AZ failure takes the tier down
  SPOF: db: 1 instance(s), all needed — any instance failure is an outage
```

একটি VM-এর (৫২.৬ ঘণ্টা/বছর) তুলনায় উন্নতি আছে, কিন্তু খরচের অনুপাতে সামান্য। AZ নিজেই ছাদ (ceiling) — app tier-এর availability AZ-এর ৯৯.৯%-এর বেশি হতে পারে না।

**Multi-AZ নকশায়** (`two-az.json`: LB দুই AZ-এ, app চারটি দুই AZ-এ, DB-র replica দুই AZ-এ) একই উপাদানে ≈ বছরে ২ মিনিট, এবং কোনো SPOF নেই।

**শিক্ষা:** Redundancy-র মূল্য তার **স্বাধীনতায়**। প্রতিটি replica-কে জিজ্ঞাসা করুন: "কোন একক ঘটনা এটা ও এর জোড়াকে একসাথে ফেলতে পারে?"

## 6. Diagram

```text
 region (যেমন ap-south-1)
 ┌─────────────────────────────────────────────────────────────────────┐
 │  AZ a                      AZ b                      AZ c             │
 │  ┌──────────────┐          ┌──────────────┐                          │
 │  │ LB node      │          │ LB node      │   ◄── এক নাম (DNS), একাধিক node │
 │  │ app ×2       │          │ app ×2       │                          │
 │  │ DB primary ──┼─sync────►│ DB standby   │   ◄── AZ-এর মধ্যে কম latency     │
 │  └──────────────┘          └──────────────┘                          │
 └─────────────────────────────────────────────────────────────────────┘
          │ async backup / replication (দূরত্বে latency বেশি)
          ▼
 অন্য region — backup, বা DR (Module 30)

 fault domain-এর প্রশ্ন: "কোন একক ঘটনা দুটিকে একসাথে ফেলবে?"
   একই host · একই rack · একই AZ · একই region · একই software version · একই deploy
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Region | ভৌগোলিক এলাকা, কয়েকটি AZ নিয়ে |
| Availability Zone (AZ) | Region-এর ভেতরে আলাদা বিদ্যুৎ/network-এর data center (গুচ্ছ) |
| Edge location / PoP | CDN ও DNS-এর জন্য user-এর কাছাকাছি জায়গা |
| Fault domain | একই কারণে একসাথে ব্যর্থ হওয়া জিনিসের দল |
| Blast radius | একটি ব্যর্থতা কতদূর ছড়ায় |
| SPOF | যার ব্যর্থতায় পুরো system বন্ধ |
| Correlated failure | একাধিক অংশ একই কারণে একসাথে ব্যর্থ |
| N+1 | প্রয়োজনের চেয়ে একটি বেশি |
| Active-active / active-passive | সবাই কাজ করে / একজন অপেক্ষায় |
| SLA / SLO | চুক্তির প্রতিশ্রুতি / নিজের লক্ষ্য (Module 18) |
| Data residency | Data কোন দেশে থাকবে — আইন |
| Anti-affinity | একই দলের instance আলাদা host/AZ-এ রাখার নিয়ম |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 সঠিক হিসাব — AZ-এর অবস্থা ধরে

`availability.py` প্রতিটি AZ-এর চালু/বন্ধ অবস্থার সব combination (2^k) গোনে। প্রতিটি অবস্থায় প্রতিটি tier-এর জন্য শুধু চালু AZ-এর instance থেকে binomial সম্ভাবনা নেয়, তারপর সব tier গুণ করে।

একই AZ-এর instance একসাথে পড়ে, তাই correlation স্বয়ংক্রিয়ভাবে ধরা পড়ে। একই হিসাব Monte Carlo (এলোমেলো অবস্থা, লক্ষবার) দিয়ে যাচাই করা হয়।

### 8.2 Naive formula কোথায় ভুল

`1 − (1−A)ⁿ` ধরে নেয় সব instance স্বাধীন। ভুলটা দুই দিকেই হতে পারে:

- **Redundancy-তে বেশি আশাবাদী:** একই AZ-এর দুটি instance-কে স্বাধীন ধরে।
- **একাধিক tier-এ বেশি হতাশাবাদী:** একই AZ-এর ব্যর্থতা প্রতিটি tier-এ আলাদা গোনে — একই ঘটনা তিনবার।

দুটোই Section 9-এ আসল সংখ্যায় দেখা গেছে।

### 8.3 Region ও AZ-এর বাস্তবতা

- AZ-গুলোর মধ্যে সাধারণত এক অঙ্কের millisecond latency — synchronous database replication সম্ভব।
- Region-এর মধ্যে দশ থেকে শত millisecond — সাধারণত asynchronous, তাই failover-এ কিছু data হারানোর ঝুঁকি (RPO — Module 30)।
- কিছু service "regional" (একাধিক AZ-এ নিজে থেকেই ছড়ানো), কিছু "zonal" (একটি AZ-এ — VM, disk)। Zonal service-এর redundancy আপনার দায় (L07-02-এর `resilience`)।

### 8.4 AZ-এর নাম

কিছু provider-এ (যেমন AWS) প্রতিটি account-এর জন্য AZ-এর নাম (`us-east-1a`) এলোমেলোভাবে আসল data center-এ map হয়। তাই দুই account-এর "a" একই জায়গা নাও হতে পারে — একই জায়গা চিনতে AZ ID ব্যবহার করুন। এটা documentation-এর বিষয়, এখানে যাচাই করা হয়নি।

> **Fedora-তে:** কোনো পার্থক্য নেই — ধারণাগত lesson।

## 9. Practical demonstration

Files:

- [`code/L07-03/availability.py`](code/L07-03/availability.py)।
- [`single-vm.json`](code/L07-03/single-vm.json), [`same-az-pair.json`](code/L07-03/same-az-pair.json), [`two-az.json`](code/L07-03/two-az.json) (হাতে তৈরি; সংখ্যা অনুমান)।
- [`test_l07_03.py`](code/L07-03/test_l07_03.py)।

### 9.1 তিনটি নকশা — আসল output

```bash
cd ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-03
python3 availability.py single-vm.json same-az-pair.json two-az.json --compare-naive --simulate 400000
```

```text
TaskFlow v0.1 — one VM (nginx + app + SQLite) in one AZ: availability 0.994005 (99.4005%) ≈ downtime 52.6 h/year
  monte carlo (400000 trials): 0.993895
  SPOF: vm: 1 instance(s), all needed — any instance failure is an outage
Two app VMs behind a load balancer — but both in AZ a: availability 0.997876 (99.7876%) ≈ downtime 18.6 h/year
  naive (independent instances): 0.996867 ≈ 27.5 h/year  ← pessimistic by 531 min/year (ignores which AZ each instance is in)
  monte carlo (400000 trials): 0.997807
  SPOF: lb … · SPOF: app: all 2 instances in AZ a … · SPOF: db …
Multi-AZ: LB nodes, app and database replica in two AZs: availability 0.999996 (99.9996%) ≈ downtime 2 min/year
  monte carlo (400000 trials): 0.999995
```

তিনটি script চালাতে মোট ১.৩ s (৪ লাখ trial × ৩)। Monte Carlo ও বিশ্লেষণী হিসাব ০.০০০১-এর মধ্যে মিলেছে।

### 9.2 শুধু placement-এর প্রভাব — আসল output

একটি tier, instance availability ০.৯৯৫, AZ ০.৯৯৯:

```text
app instances in ['a']            correct 0.9940050 ( 52.6 h/year)   naive 0.9940050 ( 52.6 h/year)
app instances in ['a', 'a']       correct 0.9989750 (  9.0 h/year)   naive 0.9999641 ( 19 min/year)
app instances in ['a', 'b']       correct 0.9999641 ( 19 min/year)   naive 0.9999641 ( 19 min/year)
app instances in ['a', 'b', 'c']  correct 0.9999998 (  0 min/year)   naive 0.9999998 (  0 min/year)
```

Naive formula `['a','a']` ও `['a','b']`-এ **একই সংখ্যা** দেয় — instance কোথায় আছে, তা জানেই না। সঠিক হিসাবে পার্থক্য ৯ ঘণ্টা বনাম ১৯ মিনিট — প্রায় ২৮ গুণ।

### 9.3 আমার ভুল ধারণা

Tool লেখার সময় আমি ধরে নিয়েছিলাম naive formula সবসময় বেশি আশাবাদী, তাই output-এ "overestimates" লিখেছিলাম। কিন্তু `same-az-pair.json`-এ naive এসেছে **কম** (৯৯.৬৯% বনাম ৯৯.৭৯%)। ফলে output-এ একটি অর্থহীন লাইন দেখা গেল: "not higher by -531 min/year"।

কারণ: তিনটি tier-ই AZ a-তে, আর naive প্রতিটি tier-এর হিসাবে AZ-এর ব্যর্থতা আলাদাভাবে গুণ করে — একই ঘটনা তিনবার। একই tier-এর ভেতরের redundancy-তে আশাবাদী, tier-গুলোর মধ্যে হতাশাবাদী। Output এখন দিক (optimistic/pessimistic) বলে।

**শিক্ষা:** Formula-র ভুল কোন দিকে যাবে, সেটাও অনুমান না করে মেপে দেখুন।

### 9.4 Test

```bash
python3 -m unittest -v
```

৬টি test:

- একটি instance-এ গুণফল।
- একই-AZ জোড়া AZ-এর ছাদ পেরোতে পারে না, এবং naive placement-অন্ধ।
- `min_healthy=2` redundancy নষ্ট করে।
- Monte Carlo মেলে।
- SPOF শনাক্তকরণ (অসম ভাগসহ)।
- Spec validation ও downtime-এর format।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `itertools.product` AZ-অবস্থা | সব combination | Correlation সঠিকভাবে ধরা |
| `tier_up_prob` — শুধু চালু AZ-এর instance | Binomial | AZ বন্ধ = তার সব instance বন্ধ |
| `min_healthy` | কতগুলো লাগবে | Capacity-র জন্য N+1 |
| `naive()` | প্রচলিত formula | তুলনা ও ভুল দেখানো |
| `simulate(seed)` | Monte Carlo | স্বাধীন যাচাই, পুনরুৎপাদনযোগ্য |
| `single_points` | তিন ধরনের SPOF | একক instance, এক AZ, অসম ভাগ |
| `_note` input-এ | "অনুমান, SLA নয়" | সংখ্যার উৎস স্পষ্ট |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `single-vm.json` | ≈ ৫২.৬ h/year, ১টি SPOF |
| `same-az-pair.json` | ≈ ১৮.৬ h/year, ৩টি SPOF |
| `two-az.json` | ≈ ২ min/year, SPOF নেই |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | ফল | সমাধান |
|---|---|---|
| Default subnet-এ সব instance | এক AZ | Subnet/AZ স্পষ্ট বাছাই; anti-affinity |
| LB multi-AZ, DB single | DB-ই SPOF | Managed DB multi-AZ বা replica |
| Redundancy আছে কিন্তু failover test হয়নি | দরকারের সময় ব্যর্থ | Game day (Module 18) |
| দুই AZ-এ ঠিক প্রয়োজনের সমান capacity | একটি AZ গেলে বাকিটা overload | প্রতিটি AZ-এ ≥ মোট load (N+1) |
| Backup একই region-এ | Region-ব্যাপী ঘটনায় হারায় | অন্য region-এ copy |
| SLA-কে নিজের লক্ষ্য ভাবা | SLA শুধু credit দেয়, uptime নয় | নিজের SLO |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Multi-region মানে data একাধিক দেশে থাকতে পারে — data residency আইন (GDPR ইত্যাদি) দেখুন। Replica-তেও একই encryption ও access নীতি।
- **Performance:**
  - User-এর কাছের region (latency)।
  - AZ-এর মধ্যে synchronous replication-এ লেখার latency বাড়ে।
  - একই AZ-এ রাখলে latency কম — কিন্তু resilience কম। এটা একটি trade-off।
- **Cost:**
  - Multi-AZ-এ instance দ্বিগুণ বা তিনগুণ, AZ-এর মধ্যে data transfer-এর খরচ, এবং managed DB-র multi-AZ-এ প্রায় দ্বিগুণ দাম।
  - প্রশ্ন: বছরে downtime-এর এক ঘণ্টার দাম কত? সেই হিসাবে নকশা বাছুন (L07-06, Module 29)।
  - ছোট internal tool-এর জন্য single-AZ + ভালো backup প্রায়ই যুক্তিসঙ্গত।

## 14. Hands-on exercise

1. `two-az.json`-কে তিন AZ-এ বাড়ান। কতটা উন্নতি হয়? খরচ (instance সংখ্যা) কত বাড়ে?
2. `availability.py`-এ "region" স্তর যোগ করুন (AZ-এর ওপরে আরেকটি correlated স্তর)। Region-ব্যাপী ব্যর্থতার সম্ভাবনা ০.৯৯৯৯ ধরে multi-AZ নকশার ছাদ কত হয়?
3. "একই software version" correlation যোগ করুন: একটি ভুল deploy-এর সম্ভাবনা p হলে সব app instance একসাথে পড়ে। Canary release (Module 11) কীভাবে এই সংখ্যা বদলায়?
4. একটি cloud provider-এর documentation থেকে আপনার কাছের region-এ কয়টি AZ আছে, তা লিখুন (link সহ)।
5. TaskFlow-এর জন্য তিনটি নকশা (single VM, same-AZ pair, multi-AZ) তুলনা করে একটি ADR লিখুন — L07-06-এর খরচের হিসাবের সাথে মিলিয়ে।

## 15. Mini-project — Fault-domain review

`fault_review.py inventory.json`:

- প্রতিটি service-এর instance ও তাদের host, AZ, region, version।
- প্রতিটি fault domain-এ (host, AZ, region, version) যদি সেটা বন্ধ হয়, কোন service-গুলো পড়ে যায়।
- "AZ b বন্ধ হলে কী থাকবে?" প্রশ্নের উত্তর।

Module completion-এর "fault-domain analysis" এবং Lab 07-B-তে ব্যবহার হবে।

## 16. Interview প্রশ্ন

1. Region ও availability zone-এর পার্থক্য কী?
2. দুটি server রাখলেই কি availability বাড়ে? কখন বাড়ে না?
3. ৯৯.৯% ও ৯৯.৯৯%-এর পার্থক্য বছরে কত downtime?
4. Correlated failure কী? উদাহরণ দিন।
5. কখন multi-region প্রয়োজন, কখন multi-AZ যথেষ্ট?
6. Single point of failure কীভাবে খুঁজবেন?

## 17. Self-assessment প্রশ্ন

1. ডিম-ঝুড়ি analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ খরচ তিন গুণ হলো, তবুও service বন্ধ — কেন?
3. Naive formula `['a','a']` ও `['a','b']`-এ একই কেন দেয়?
4. `same-az-pair`-এ naive কেন হতাশাবাদী হলো?
5. AZ-এর ছাদ (ceiling) বলতে কী বোঝায়?

## 18. সংক্ষিপ্ত সারাংশ

- Fault domain: যা একসাথে ব্যর্থ হয় — host, rack, AZ, region, provider, deploy।
- Redundancy-র মূল্য স্বাধীনতায়; একই AZ-এর replica AZ-এর ছাদ পেরোতে পারে না।
- Naive parallel formula placement দেখে না — correlation ধরে হিসাব করুন।
- Serial অংশ availability কমায়; প্রতিটি SPOF খুঁজুন।
- Multi-AZ সাধারণ উত্তর; multi-region খরচ, latency ও জটিলতা দেখে সিদ্ধান্ত।

## 19. Completion checklist

- [ ] তিনটি নকশার availability ও SPOF ব্যাখ্যা করতে পারি
- [ ] Naive ও সঠিক হিসাবের পার্থক্য দেখিয়েছি
- [ ] TaskFlow-এর নকশা বাছাইয়ের ADR লিখেছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS — Regions and Availability Zones: https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/using-regions-availability-zones.html
- AWS — Availability Zone IDs: https://docs.aws.amazon.com/ram/latest/userguide/working-with-az-ids.html
- Google Cloud — Geography and regions: https://cloud.google.com/docs/geography-and-regions
- Microsoft Learn — Azure availability zones: https://learn.microsoft.com/en-us/azure/reliability/availability-zones-overview
- AWS Well-Architected — Reliability Pillar: https://docs.aws.amazon.com/wellarchitected/latest/reliability-pillar/welcome.html
- Google SRE Book — Embracing Risk: https://sre.google/sre-book/embracing-risk/

---

**পরের lesson:** L07-04 — Public বনাম private networking
