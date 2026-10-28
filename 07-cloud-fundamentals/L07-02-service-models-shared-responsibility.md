# L07-02 — IaaS, PaaS, SaaS ও shared responsibility model

| | |
|---|---|
| **Module** | 07 — Cloud Fundamentals |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২ ঘণ্টা |
| **পূর্বশর্ত** | [L07-01 — Virtualization](L07-01-virtualization-hypervisor.md) |
| **Label** | — |
| **Tested** | `responsibility.py`: ৫টি test পাস (Python 3.14.5, Windows)। Test matrix-এর মৌলিক নিয়ম যাচাই করে — যেমন data ও identity সবসময় customer-এর, এবং stack-এ ওপরে উঠলে customer-এর দায় কখনো বাড়ে না। Matrix provider-দের প্রকাশিত diagram-এর **সাধারণ রূপ** — নির্দিষ্ট service-এর সীমারেখা ভিন্ন হতে পারে। কোনো cloud resource তৈরি হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Service model: on-premises, IaaS, PaaS, FaaS (serverless), SaaS — প্রতিটিতে আপনি কী নিয়ন্ত্রণ করেন, কী ছেড়ে দেন।
- **Shared responsibility model:** "cloud-এর নিরাপত্তা" (provider) বনাম "cloud-এ নিরাপত্তা" (আপনি)।
- যা **সবসময় আপনার:** identity, data, configuration, endpoint — এমনকি SaaS-এও।
- প্রচলিত ভুল ধারণা: "cloud provider backup নেয়", "managed মানে নিরাপদ", "outage হলে provider দায়ী"।
- TaskFlow-কে কোন model-এ চালাবেন — operational খরচ ও নিয়ন্ত্রণের হিসাব।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Cloud-এর বেশিরভাগ গুরুতর data breach provider-এর infrastructure ভেঙে হয় না — হয় **customer-এর ভুল configuration** থেকে:

- Public storage bucket।
- Internet-এ খোলা database।
- Leak হওয়া access key।

"আমরা cloud-এ আছি, তাই নিরাপদ" — এই ভুল ধারণা থেকে কেউ নিজের দায়িত্বের অংশ দেখেই না।

উল্টো দিকে, কোন কাজ provider করে তা জানলে অকারণ কাজও বাঁচে। PaaS-এ OS patch আপনার কাজ নয় — সেই সময় অন্য কোথাও দেওয়া যায়।

## 3. সহজ ভাষায় পরিচয়

| Model | আপনি পান | আপনি সামলান | উদাহরণ |
|---|---|---|---|
| On-premises | সব নিয়ন্ত্রণ | সব — বিদ্যুৎ থেকে app | নিজের server room |
| IaaS | VM, network, disk | OS থেকে উপরে সব | EC2, Compute Engine, Azure VM |
| PaaS | Runtime/platform | Code, config, data | App Engine, Elastic Beanstalk, managed DB (RDS) |
| FaaS (serverless) | Function চালানোর পরিবেশ | Function code, permission | Lambda, Cloud Functions |
| SaaS | পুরো application | Configuration, user, data | Gmail, Slack, GitHub |

`python3 responsibility.py matrix` — এই repo-র matrix (Section 9.1)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### খাবারের ব্যবস্থা — "Pizza as a Service"

| | নিজে রান্না | Ready dough কেনা | Home delivery | রেস্তোরাঁয় খাওয়া |
|---|---|---|---|---|
| Model | On-prem | IaaS | PaaS | SaaS |
| চুলা, গ্যাস | আপনি | আপনি | দোকান | দোকান |
| রান্না | আপনি | আপনি | দোকান | দোকান |
| টেবিল, খাওয়া | আপনি | আপনি | আপনি | দোকান |

### Analogy কোথায় মেলে না

- **রেস্তোরাঁয় খেলে শুধু খাওয়াটাই আপনার।** SaaS-এও আপনার data, কে access পাবে, এবং sharing setting-এর দায় পুরো আপনার। একটি SaaS document "link থাকলে যে কেউ দেখতে পাবে" setting-এ রাখলে, সেটা provider-এর ভুল নয়। খাবারের analogy-তে এর কোনো সমতুল্য নেই।
- **রেস্তোরাঁর রান্নাঘরে আগুন লাগলে আপনার রাতের খাবার শেষ, কিছু করার নেই।** Cloud-এ provider-এর data center বা একটি AZ বন্ধ হলে hardware ঠিক করা তাদের কাজ। কিন্তু **আপনার service চালু থাকবে কিনা**, তা আপনার architecture-এর ওপর নির্ভর করে (multi-AZ — L07-03)। এই repo-র matrix-এ তাই `resilience` আলাদা layer, এবং IaaS/PaaS-এ customer-এর।
- **খাবারের দোকান আপনার বাসি খাবার রেখে দেয় না।** অনেকে ধরে নেন provider-ই data-র backup রাখে। বেশিরভাগ service-এ backup চালু করা, retention ঠিক করা, এবং **restore পরীক্ষা** করা আপনার কাজ (L05-12)।

## 5. Real-world engineering scenario — "Managed database, তবুও data হারাল"

**পরিস্থিতি:** একটি team TaskFlow-এর database managed service-এ (PaaS) সরিয়ে নিশ্চিন্ত হলো: "এখন provider সব দেখবে"। ছয় মাস পরে তিনটি ঘটনা:

1. Migration script-এর ভুলে production table মুছে গেল। Automated backup-এর retention ছিল default (কয়েক দিন), আর ভুলটা ধরা পড়ল এক সপ্তাহ পরে — backup ততদিনে নেই।
2. Debug-এর জন্য security group-এ database port সাময়িকভাবে `0.0.0.0/0`-এ খোলা হয়েছিল, এবং বন্ধ করা হয়নি।
3. Database engine-এর major version-এর support শেষের notice বারবার এসেছিল, কেউ পড়েনি। শেষে provider জোর করে upgrade করল, এবং একটি query ভেঙে গেল।

`responsibility.py incidents --model paas`-এর ফল:

```text
customer  data            ভুল করে production table মুছে ফেলা, backup নেই
shared    network-config  Database port 0.0.0.0/0 থেকে খোলা security group
shared    runtime         Runtime-এর Python version-এর support শেষ (EOL)
```

তিনটির একটিও provider-এর একার দায় নয়।

**শিক্ষা:** Managed service **কাজ** কমায়, **দায়** নয়। প্রতিটি নতুন service-এ জিজ্ঞাসা করুন: backup ও retention কে ঠিক করে, network-এ কে পৌঁছাতে পারে, version upgrade কে ও কখন করে।

## 6. Diagram

```text
                 on-prem   IaaS      PaaS      FaaS      SaaS
 endpoint        ██████    ██████    ██████    ██████    ██████   ← সবসময় আপনার
 data            ██████    ██████    ██████    ██████    ██████   ← সবসময় আপনার
 identity        ██████    ██████    ██████    ██████    ██████   ← সবসময় আপনার
 configuration   ██████    ██████    ██████    ██████    ██████   ← সবসময় আপনার
 resilience      ██████    ██████    ██████    ▒▒▒▒▒▒    ▒▒▒▒▒▒
 application     ██████    ██████    ██████    ██████    ░░░░░░
 runtime         ██████    ██████    ▒▒▒▒▒▒    ░░░░░░    ░░░░░░
 os              ██████    ██████    ░░░░░░    ░░░░░░    ░░░░░░
 network-config  ██████    ██████    ▒▒▒▒▒▒    ▒▒▒▒▒▒    ░░░░░░
 hypervisor      ██████    ░░░░░░    ░░░░░░    ░░░░░░    ░░░░░░
 network-infra   ██████    ░░░░░░    ░░░░░░    ░░░░░░    ░░░░░░
 physical        ██████    ░░░░░░    ░░░░░░    ░░░░░░    ░░░░░░
                 ██ customer   ▒▒ shared   ░░ provider
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| IaaS | Infrastructure as a Service — VM, disk, network |
| PaaS | Platform as a Service — runtime/platform পরিচালিত |
| FaaS / serverless | Function চালানো; server দেখা যায় না, ব্যবহার অনুযায়ী বিল |
| SaaS | পুরো application ভাড়া |
| Managed service | Provider OS/patch/backup-এর যন্ত্র দেয় (যেমন managed DB) |
| Shared responsibility | Provider ও customer-এর দায়ের ভাগ |
| "Security of the cloud" / "in the cloud" | Provider-এর infrastructure / আপনার ব্যবহার |
| Vendor lock-in | নির্দিষ্ট provider-এর বৈশিষ্ট্যে নির্ভরতা — সরে যাওয়া কঠিন |
| Operational burden | চালু রাখার জন্য নিয়মিত কাজ |
| EOL (end of life) | Version-এর support শেষ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 নিয়ন্ত্রণ বনাম দায়

Stack-এ যত ওপরে যাবেন (IaaS → SaaS), তত কম স্তর আপনার হাতে। সাথে কমে **নিয়ন্ত্রণ**ও: PaaS-এ kernel parameter বদলানো যায় না, FaaS-এ execution সময়ের সীমা থাকে, SaaS-এ feature-এর জন্য অপেক্ষা করতে হয়।

`responsibility.py`-এর test একটি নিয়ম যাচাই করে: কোনো layer-এ customer-এর দায় on-prem থেকে SaaS-এর দিকে কখনো বাড়ে না।

### 8.2 "Shared" মানে কী

PaaS-এ runtime "shared": provider runtime-কে patch করে, কিন্তু কোন version (Python ৩.১০ না ৩.১২) এবং কখন upgrade — সেই সিদ্ধান্ত ও test আপনার।

Network config-ও shared: platform-এর network provider-এর, কিন্তু কে আপনার service-এ পৌঁছাবে তার নিয়ম আপনার।

### 8.3 কোন model বাছবেন — TaskFlow-এর জন্য

| বিকল্প | Model | আপনার কাজ | ভালো | খারাপ |
|---|---|---|---|---|
| VM + nginx + systemd (Module 06) | IaaS | OS patch, nginx, TLS, monitoring | পূর্ণ নিয়ন্ত্রণ, সব শেখা যায় | সব দায় আপনার |
| Container platform (Module 09–14) | PaaS-ধাঁচ / IaaS | Image, config | Portable | Platform নিজেই জটিল |
| Managed DB (Module 20) | PaaS | Schema, backup নীতি, access | Patch/HA provider-এর | খরচ, কম নিয়ন্ত্রণ |
| Serverless function | FaaS | Code, IAM | Idle-এ খরচ প্রায় শূন্য | Cold start, সময়-সীমা, lock-in |

এই course IaaS দিয়ে শুরু করে, যাতে প্রতিটি স্তর বোঝা যায়। Production-এ "যতটা সম্ভব managed" প্রায়ই সঠিক — কিন্তু সচেতনভাবে, দায়ের তালিকা জেনে।

> **Fedora-তে:** কোনো পার্থক্য নেই — ধারণাগত lesson।

## 9. Practical demonstration

Files: [`code/L07-02/responsibility.py`](code/L07-02/responsibility.py), [`sample-incidents.json`](code/L07-02/sample-incidents.json) (হাতে তৈরি ১১টি ঘটনা), [`test_l07_02.py`](code/L07-02/test_l07_02.py)।

### 9.1 Matrix — আসল output

```bash
cd ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-02
python3 responsibility.py matrix
```

```text
layer           on-prem   iaas      paas      faas      saas
physical        customer  provider  provider  provider  provider
network-infra   customer  provider  provider  provider  provider
hypervisor      customer  provider  provider  provider  provider
network-config  customer  customer  shared    shared    provider
os              customer  customer  provider  provider  provider
runtime         customer  customer  shared    provider  provider
application     customer  customer  customer  customer  provider
resilience      customer  customer  customer  shared    shared
configuration   customer  customer  customer  customer  customer
identity        customer  customer  customer  customer  customer
data            customer  customer  customer  customer  customer
endpoint        customer  customer  customer  customer  customer
customer+shared 12        9         8         7         5
```

SaaS-এও ১২টির মধ্যে ৫টি স্তর আপনার।

### 9.2 Incident — একই ঘটনা, ভিন্ন model

```bash
python3 responsibility.py incidents sample-incidents.json --model iaas
```

IaaS-এ ১১টির মধ্যে ৯টি customer-এর। কয়েকটি তুলনা (আসল output থেকে):

```text
model iaas:  customer  os              OpenSSH-এর critical CVE প্রকাশিত, server-এ পুরোনো version
model paas:  provider  os              (একই ঘটনা)
model iaas:  provider  physical        Data center-এ বিদ্যুৎ বিভ্রাট, একটি rack বন্ধ
model iaas:  customer  resilience      একটি availability zone বন্ধ; app-এর সব instance ঐ AZ-এ ছিল
model saas:  customer  configuration   Object storage bucket-এর বিষয়বস্তু সবার জন্য খোলা (public)
```

**লেখার সময় যোগ করা:** প্রথম সংস্করণে `resilience` layer ছিল না। Matrix "বিদ্যুৎ বিভ্রাট = provider" দেখাচ্ছিল, যা ঠিক — কিন্তু সেটা পড়ে মনে হতো outage-এর পুরো দায় provider-এর। তাই দ্বিতীয় ঘটনাটি আলাদা layer-এ রাখা হয়েছে: hardware-এর দায় provider-এর, কিন্তু service টিকে থাকার দায় architecture-এর।

### 9.3 Test

```bash
python3 -m unittest -v
```

৫টি test:

- চারটি layer সব model-এ customer-এর।
- On-prem-এ সব customer-এর।
- **দায় stack-এ ওপরে কখনো বাড়ে না** (প্রতিটি layer)।
- নির্দিষ্ট cell।
- নমুনা ঘটনা সব layer চেনে।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `MATRIX` — layer × model | কে দায়ী | একটি table-এ পুরো ধারণা |
| `S` (shared) | সিদ্ধান্ত আপনার, কাজ provider-এর | Runtime, network config |
| `resilience` layer | Workload-এর টিকে থাকা | Outage-এর ভুল ধারণা |
| `customer_layers` | Customer + shared | Operational burden-এর মাপ |
| Monotonic test | Matrix-এর অভ্যন্তরীণ সামঞ্জস্য | ভুল cell-এ ধরা পড়ে |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `matrix` | শেষ লাইনে ১২ / ৯ / ৮ / ৭ / ৫ |
| `who --layer identity --model saas` | customer |
| `python3 -m unittest -v` | `Ran 5 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল ধারণা | বাস্তবতা | কী করবেন |
|---|---|---|
| "Provider backup রাখে" | প্রায়ই আপনাকে চালু ও retention ঠিক করতে হয় | Backup নীতি + restore test |
| "Managed মানে নিরাপদ" | Network ও identity আপনার | Security group, IAM review |
| "SaaS-এ আমার কিছু করার নেই" | User, sharing, data আপনার | MFA, access review |
| "AZ বন্ধ = provider-এর দোষ, আমার service-ও বন্ধ থাকবে" | Multi-AZ design আপনার | L07-03 |
| "Serverless-এ security নেই" | Function-এর IAM permission আপনার | Least privilege (L07-05) |
| "EOL notice পরে দেখব" | জোর করে upgrade | Version-এর calendar |

## 13. Security, performance ও cost বিবেচনা

- **Security:** নিজের দায়ের তালিকা লিখে রাখুন (RACI) — প্রতিটি service-এর জন্য। Provider-এর compliance report (SOC 2, ISO 27001) শুধু তাদের অংশ প্রমাণ করে।
- **Performance:** Managed service-এর সীমা (connection limit, throughput quota) আগে জানুন; ভেতরে tuning-এর সুযোগ কম।
- **Cost:** IaaS-এ hardware সস্তা, কিন্তু মানুষের সময় দামি। PaaS/SaaS-এ বিল বেশি, কাজ কম। মোট খরচ (TCO) = বিল + operational সময় + ঝুঁকি (L07-06)।

## 14. Hands-on exercise

1. আপনার ব্যবহৃত তিনটি SaaS-এ (email, Git hosting, chat) আপনার দায়ের অংশ লিখুন: MFA, sharing setting, data export।
2. `sample-incidents.json`-এ আরও ৫টি নিজের অভিজ্ঞতা বা খবর থেকে পাওয়া ঘটনা যোগ করে তিন model-এ চালান।
3. একটি managed database service-এর documentation পড়ে লিখুন: backup কে নেয়, retention কত, PITR (point-in-time restore) আছে কিনা, minor ও major upgrade কে করে।
4. TaskFlow-এর জন্য Section 8.3-এর table-এ নিজের পছন্দ ও যুক্তি একটি ADR আকারে লিখুন (L00-05)।
5. `responsibility.py`-এ একটি নতুন model যোগ করুন — "managed Kubernetes" (control plane provider, node/workload customer)। Monotonic test পাস করে কি?

## 15. Mini-project — Responsibility register

`register.py services.yaml`:

- আপনার project-এর প্রতিটি component (VM, DB, object storage, DNS, email SaaS) ও তার model।
- প্রতিটির জন্য customer-এর দায়গুলো, এবং মালিক (কোন ব্যক্তি/team)।
- শেষ review-এর তারিখ।
- মালিকহীন বা ৯০ দিনের বেশি review-হীন দায় হলে সতর্কতা।

Module 19-এর security program-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. IaaS, PaaS, SaaS-এর পার্থক্য উদাহরণসহ বলুন।
2. Shared responsibility model কী? "Security of the cloud" বনাম "in the cloud"?
3. SaaS ব্যবহার করলেও কোন দায় আপনার থাকে?
4. Managed database ব্যবহারে আপনার কী কী দায়িত্ব?
5. একটি AZ বন্ধ হলে আপনার service বন্ধ হলো — কার দায়?
6. কখন IaaS, কখন PaaS বেছে নেবেন?

## 17. Self-assessment প্রশ্ন

1. Pizza analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি ঘটনার মালিক কে, এবং কীভাবে ঠেকানো যেত?
3. "Shared" মানে কী — runtime-এর উদাহরণে?
4. `resilience` layer কেন যোগ করা হলো?
5. কোন চারটি layer সব model-এ customer-এর?

## 18. সংক্ষিপ্ত সারাংশ

- Stack-এ ওপরে উঠলে কাজ ও নিয়ন্ত্রণ দুটোই কমে।
- Identity, data, configuration, endpoint — সবসময় আপনার।
- Provider-এর outage-এর মেরামত তাদের, কিন্তু service টিকিয়ে রাখার design আপনার।
- Managed service কাজ কমায়, দায় নয় — backup, network, version upgrade।
- প্রতিটি service-এর দায়ের তালিকা ও মালিক লিখে রাখুন।

## 19. Completion checklist

- [ ] Matrix-এর প্রতিটি cell ব্যাখ্যা করতে পারি
- [ ] তিনটি SaaS-এ নিজের দায় লিখেছি
- [ ] TaskFlow-এর model বাছাইয়ের ADR লিখেছি
- [ ] `python3 -m unittest -v`-এ ৫টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS — Shared Responsibility Model: https://aws.amazon.com/compliance/shared-responsibility-model/
- Microsoft Learn — Shared responsibility in the cloud: https://learn.microsoft.com/en-us/azure/security/fundamentals/shared-responsibility
- Google Cloud — Shared responsibilities and shared fate: https://cloud.google.com/architecture/framework/security/shared-responsibility-shared-fate
- NIST SP 800-145 — The NIST Definition of Cloud Computing: https://csrc.nist.gov/pubs/sp/800/145/final

---

**পরের lesson:** L07-03 — Region, availability zone ও fault domain
