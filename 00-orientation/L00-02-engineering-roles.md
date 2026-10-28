# L00-02 — Engineering roles: DevOps, SRE, Platform, Cloud, Security, MLOps, AI Infra

| | |
|---|---|
| **Module** | 00 — Engineering Orientation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২ ঘণ্টা |
| **পূর্বশর্ত** | [L00-01 — DevOps আসলে কী](L00-01-what-is-devops.md) |
| **Label** | — |
| **Tested** | Python code: Python 3.14-এ ৯টি test পাস। Ubuntu-তে চালানো হয়নি (শুধু standard library, Python 3.10+ এ চলার কথা)। |

---

## 1. এই lesson-এ যা শিখবেন

- সাতটি engineering role কী করে: **DevOps, Cloud, Platform, SRE, DevSecOps, MLOps, AI Infrastructure/LLMOps** (এবং নতুন AI-Powered Operations)।
- Role-গুলো কোথায় **মেলে** (overlap) আর কোথায় **আলাদা**।
- প্রতিটি role-এর সাফল্য কীভাবে মাপা হয় এবং on-call দায়িত্ব কেমন।
- Job title কেন প্রতিষ্ঠান ভেদে আলাদা অর্থ বহন করে।
- Python দিয়ে নিজের skill থেকে role fit ও skill gap হিসাব করা — এবং কোন module আগে পড়বেন তা ঠিক করা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Job বিজ্ঞাপনে একই রকম কাজের জন্য পাঁচটি ভিন্ন title দেখা যায়, আবার একই title-এ সম্পূর্ণ ভিন্ন কাজ। ফলে নতুনরা বিভ্রান্ত হন:

- "DevOps শিখব নাকি SRE?" — অথচ দুটোর ভিত্তি প্রায় একই।
- "Kubernetes জানলেই Platform Engineer?" — না, platform মানে অন্য engineer-দের জন্য product বানানো।
- "MLOps মানে কি data scientist?" — না, MLOps মূলত infrastructure ও automation-এর কাজ।

Role-গুলোর **মূল দায়িত্ব** বুঝলে আপনি পারবেন: ঠিক কোন পথে যাবেন বেছে নিতে, job description পড়ে আসল কাজ বুঝতে, এবং interview-এ নিজের দক্ষতা সঠিক ভাষায় তুলে ধরতে।

## 3. সহজ ভাষায় পরিচয়

সব role একটি প্রশ্নের ভিন্ন ভিন্ন অংশের উত্তর দেয়: **"Software কীভাবে দ্রুত, নিরাপদে ও নির্ভরযোগ্যভাবে user-এর কাছে পৌঁছাবে ও চলতে থাকবে?"**

| Role | এক বাক্যে মূল প্রশ্ন |
|---|---|
| **DevOps Engineer** | Code থেকে production পর্যন্ত পথ কীভাবে automated ও দ্রুত করব? |
| **Cloud Engineer** | Cloud-এ infrastructure কীভাবে সঠিক, নিরাপদ ও সাশ্রয়ীভাবে তৈরি করব? |
| **Platform Engineer** | অন্য developer-রা কীভাবে নিজে নিজে (self-service) নিরাপদে deploy করবে? |
| **SRE** | Service কতটা reliable হওয়া উচিত, এবং engineering দিয়ে কীভাবে সেটা নিশ্চিত করব? |
| **DevSecOps / Security Engineer** | পুরো delivery পথ ও workload কীভাবে নিরাপদ রাখব? |
| **MLOps Engineer** | ML model কীভাবে reproducible-ভাবে train, deploy, monitor ও rollback করব? |
| **AI Infrastructure / LLMOps Engineer** | বড় model কীভাবে দক্ষতার সাথে (latency, memory, খরচ) serve ও scale করব? |
| **AI-Powered Operations Engineer** | AI দিয়ে operations কীভাবে দ্রুত করব — নিরাপত্তা না হারিয়ে? |

### কেন এত role তৈরি হলো?

1. **২০০৯–২০১৪:** DevOps আন্দোলন — Dev ও Ops-এর দেয়াল ভাঙা (L00-01)।
2. **২০০৩ থেকে Google-এ, ২০১৬-তে বই আকারে জনপ্রিয়:** SRE — reliability-কে software engineering সমস্যা হিসেবে দেখা।
3. **Cloud-এর বিস্তার:** Cloud Engineer — AWS/Azure/GCP-তে বিশেষজ্ঞ।
4. **Microservice ও Kubernetes-এর জটিলতা:** প্রতিটি team নিজে সব শিখতে পারে না → Platform Engineering।
5. **Supply-chain attack বৃদ্ধি:** security-কে শেষে নয়, শুরু থেকে → DevSecOps।
6. **ML production-এ যাওয়া:** notebook-এর model production-এ টেকে না → MLOps।
7. **LLM-এর যুগ:** GPU, VRAM, token, inference খরচ → AI Infrastructure / LLMOps।

### এটি না বুঝলে কী সমস্যা হয়?

ভুল দক্ষতার পেছনে সময় যায়। যেমন কেউ SRE হতে চান, কিন্তু শুধু CI/CD tool শিখছেন — অথচ SRE interview-এ প্রশ্ন আসবে SLO, incident, Linux performance ও system design নিয়ে।

## 4. বাস্তব জীবনের উদাহরণ (analogy) — একটি হাসপাতাল

একটি বড় হাসপাতাল ভাবুন:

| হাসপাতালে | Engineering-এ | কেন মিল |
|---|---|---|
| ভবন, বিদ্যুৎ, পানি, লিফট তৈরি ও রক্ষণাবেক্ষণ | **Cloud Engineer** | মৌলিক infrastructure |
| রোগী ভর্তি থেকে ছুটি পর্যন্ত প্রক্রিয়া দ্রুত ও সুশৃঙ্খল করা | **DevOps Engineer** | প্রবাহ (flow) ও automation |
| ডাক্তারদের জন্য প্রস্তুত operation theatre, standard kit, সহজ booking system | **Platform Engineer** | অন্যদের জন্য self-service সুবিধা |
| ICU-র monitoring, জরুরি সাড়া, "কত শতাংশ রোগী ১০ মিনিটে চিকিৎসা পাবে" লক্ষ্য | **SRE** | reliability লক্ষ্য, incident response |
| প্রবেশাধিকার নিয়ন্ত্রণ, ওষুধের নিরাপত্তা, সংক্রমণ প্রতিরোধ | **DevSecOps** | প্রতিটি ধাপে নিরাপত্তা |
| নতুন রোগনির্ণয় পদ্ধতি যাচাই করে নিয়মিত চিকিৎসায় আনা ও ফলাফল পর্যবেক্ষণ | **MLOps** | model-কে production-এ আনা ও monitor |
| দামি MRI/CT machine-এর scheduling, ক্ষমতা ও খরচ ব্যবস্থাপনা | **AI Infrastructure** | দামি GPU resource-এর দক্ষ ব্যবহার |

### Analogy কোথায় মেলে না

- হাসপাতালে প্রতিটি পদে সাধারণত আলাদা মানুষ, আলাদা লাইসেন্স। Software-এ **একজন মানুষ প্রায়ই একাধিক role** পালন করেন — বিশেষ করে ছোট প্রতিষ্ঠানে একজন "DevOps Engineer"-ই cloud, CI/CD, monitoring, security সব করেন।
- হাসপাতালের পদের সীমা আইন দিয়ে নির্ধারিত। Software role-এর সীমা **প্রতিষ্ঠান ভেদে আলাদা** — এক কোম্পানির "SRE" অন্য কোম্পানির "DevOps Engineer"-এর কাজই করেন।
- Software-এ সবকিছু code দিয়ে automate করার সুযোগ আছে — হাসপাতালের বেশিরভাগ কাজ শারীরিক।

## 5. Real-world engineering scenario — একটি incident-এ কে কী করে

**পরিস্থিতি:** একটি fintech কোম্পানি। শুক্রবার সন্ধ্যায় payment API-র latency হঠাৎ ১০ গুণ বেড়ে গেল। প্রতিষ্ঠানে প্রায় ২০০ engineer, তাই role-গুলো আলাদা।

**ঘটনার ক্রম ও কার দায়িত্ব:**

1. **Alert:** SLO burn-rate alert fire করল — "payment API-র ৯৯.৯% request ৩০০ms-এর মধ্যে" লক্ষ্য ভাঙছে। Alert ও SLO design করেছিলেন **SRE**। On-call SRE page পেলেন।
2. **Triage:** SRE dashboard দেখে বুঝলেন latency শুরু হয়েছে ১৮:০২-এ। Deployment history দেখালো ১৮:০০-তে একটি নতুন version deploy হয়েছে। Pipeline ও deployment history তৈরি করেছিলেন **DevOps/Platform** team।
3. **Mitigation:** SRE platform-এর self-service rollback button চাপলেন। ৩ মিনিটে আগের version ফিরে এলো, latency স্বাভাবিক। এই এক-ক্লিক rollback সম্ভব হয়েছে **Platform Engineer**-দের তৈরি golden path-এর কারণে।
4. **Root cause:** নতুন version-এ একটি fraud-detection ML model আপডেট হয়েছিল, যার inference সময় অনেক বেশি। **MLOps Engineer** দেখলেন model registry-তে evaluation gate ছিল শুধু accuracy-র জন্য, latency-র জন্য নয়।
5. **Capacity:** নতুন model বড়, তাই GPU-তে চালানো দরকার কিনা — সেই হিসাব করলেন **AI Infrastructure Engineer** (memory, throughput, খরচ)।
6. **Security প্রশ্ন:** Rollback-এর পরে **DevSecOps** যাচাই করলেন পুরোনো version-এ কোনো জানা vulnerability ফিরে এসেছে কিনা।
7. **Cloud:** আলোচনায় বেরোলো GPU node pool দরকার। **Cloud Engineer** Terraform দিয়ে নতুন node pool-এর design ও cost estimate করলেন।
8. **Postmortem:** SRE blameless postmortem লিখলেন। Action item: model evaluation gate-এ latency যোগ (MLOps), canary deployment বাধ্যতামূলক (Platform)।

**শিক্ষা:** কোনো একটি role একা সমস্যাটি পুরো সমাধান করতে পারত না। প্রতিটি role অন্যের কাজের উপর নির্ভরশীল। আর ছোট কোম্পানিতে এই আটটি ধাপ হয়তো **একজন বা দুজন** মানুষই করতেন।

**কী ভুল হতে পারত:** Rollback ব্যবস্থা না থাকলে mitigation-এ ঘণ্টা লাগত। SLO না থাকলে alert হয় আসতই না, নয়তো এত বেশি noisy alert যে কেউ গুরুত্ব দিত না।

## 6. Diagram — role-গুলোর overlap

```text
                    ┌─────────────────────────────────────────┐
                    │      Shared foundation (সবার জন্য)       │
                    │ Linux · Networking · Git · Bash · Python │
                    │       Containers · Troubleshooting       │
                    └────────────────────┬────────────────────┘
                                         │
      ┌────────────────┬─────────────────┼───────────────────┬──────────────────┐
      ▼                ▼                 ▼                   ▼                  ▼
 ┌─────────┐     ┌──────────┐      ┌──────────┐        ┌───────────┐      ┌──────────┐
 │ DevOps  │◄───►│  Cloud   │◄────►│ Platform │        │    SRE    │      │DevSecOps │
 │ CI/CD,  │     │ AWS, IaC,│      │ IDP,     │        │ SLO,      │      │ IAM, scan│
 │automation│    │ network  │      │ golden   │        │ incident, │      │ supply   │
 └────┬────┘     └──────────┘      │ path, K8s│        │ capacity  │      │ chain    │
      │                            └────┬─────┘        └─────┬─────┘      └────┬─────┘
      │        ┌────────────────────────┴────────────────────┴─────────────────┘
      │        │  Kubernetes · Observability · IaC · Security — সবার মধ্যে ভাগ করা
      ▼        ▼
 ┌──────────┐     ┌──────────────────┐     ┌────────────────────────┐
 │  MLOps   │────►│ AI Infra/LLMOps  │────►│ AI-Powered Operations  │
 │ pipeline,│     │ GPU, serving,    │     │ agent, MCP, safe       │
 │ registry │     │ latency, cost    │     │ automation, triage     │
 └──────────┘     └──────────────────┘     └────────────────────────┘
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| On-call | নির্দিষ্ট সময়ে production সমস্যা দেখা দিলে সাড়া দেওয়ার দায়িত্ব (রাতেও হতে পারে) |
| Toil | হাতে করা, পুনরাবৃত্তিমূলক, automate-যোগ্য কাজ যা স্থায়ী মূল্য তৈরি করে না |
| SLO (Service Level Objective) | Reliability-র লক্ষ্য, যেমন "৯৯.৯% request সফল" (Module 18-এ বিস্তারিত) |
| Internal Developer Platform (IDP) | Developer-দের জন্য self-service tool ও workflow-এর সমষ্টি |
| Golden path | Platform team-এর সুপারিশকৃত, পরীক্ষিত পথ (যেমন নতুন service তৈরির template) |
| Shift left | Security বা testing-কে delivery-র শেষ থেকে শুরুর দিকে সরানো |
| Model registry | যাচাইকৃত ML model-এর version-সহ catalog |
| Inference | Train করা model দিয়ে নতুন input-এ উত্তর তৈরি করা |
| T-shaped engineer | অনেক বিষয়ে মৌলিক জ্ঞান (T-এর আনুভূমিক দাগ) + এক-দুটি বিষয়ে গভীর দক্ষতা (উল্লম্ব দাগ) |

## 8. ভেতরে কীভাবে কাজ করে — প্রতিটি role বিস্তারিত

### 8.1 DevOps Engineer

- **মূল কাজ:** CI/CD pipeline, build ও deployment automation, environment তৈরি, container, monitoring setup।
- **দৈনন্দিন:** pipeline ভাঙলে ঠিক করা, নতুন service-এর deployment যোগ, Dockerfile উন্নত করা, deploy সময় কমানো।
- **সাফল্যের মাপ:** DORA metrics (L00-01) — deploy frequency, lead time, change failure rate, recovery time।
- **On-call:** প্রায়ই আছে (pipeline ও deploy সমস্যা)।
- **সাধারণ tool:** Git, GitHub Actions/GitLab CI, Docker, Terraform, Ansible, Kubernetes, Prometheus।
- **সতর্কতা:** অনেক কোম্পানিতে "DevOps Engineer" মানে আসলে "সব infrastructure কাজের একজন মানুষ"। Title দেখে নয়, job description পড়ে কাজ বুঝুন।

### 8.2 Cloud Engineer

- **মূল কাজ:** Cloud account, network (VPC), IAM, compute, storage, managed service design ও তৈরি।
- **দৈনন্দিন:** Terraform দিয়ে resource তৈরি, IAM policy, cost review, cloud migration।
- **সাফল্যের মাপ:** security posture, cost efficiency, infrastructure reproducibility।
- **DevOps-এর সাথে পার্থক্য:** DevOps-এর ফোকাস delivery **প্রবাহ**; Cloud Engineer-এর ফোকাস **infrastructure foundation**।

### 8.3 Platform Engineer

- **মূল কাজ:** Internal Developer Platform তৈরি — অন্য engineer-রাই এর **customer**।
- **দৈনন্দিন:** service template, self-service deployment, Kubernetes cluster ব্যবস্থাপনা, developer documentation, platform API।
- **সাফল্যের মাপ:** developer কত দ্রুত নতুন service চালু করতে পারে, platform adoption, developer satisfaction, platform-এর নিজের reliability।
- **মূল মানসিকতা:** "Platform as a product" — developer-দের প্রয়োজন শোনা, roadmap, documentation। শুধু tool install করা platform engineering নয়।

### 8.4 Site Reliability Engineer (SRE)

- **মূল ধারণা:** Google-এর ভাষায়, SRE হলো "software engineer-কে operations-এর কাজ দিলে যা হয়"।
- **মূল কাজ:** SLI/SLO নির্ধারণ, error budget, incident response, postmortem, capacity planning, toil automation, performance।
- **সাফল্যের মাপ:** SLO পূরণ, MTTR (recovery সময়), toil কমানো, incident-এর পুনরাবৃত্তি কমা।
- **On-call:** কেন্দ্রীয় দায়িত্ব।
- **Error budget-এর ধারণা (সংক্ষেপে):** ৯৯.৯% SLO মানে ০.১% ব্যর্থতা গ্রহণযোগ্য। Budget বাকি থাকলে দ্রুত feature release; শেষ হলে reliability কাজে মনোযোগ। এভাবে "দ্রুততা বনাম স্থিতিশীলতা" বিতর্ক সংখ্যা দিয়ে মীমাংসা হয় (Module 18)।
- **DevOps-এর সাথে সম্পর্ক:** অনেকে বলেন "SRE হলো DevOps নীতির একটি নির্দিষ্ট বাস্তবায়ন"। DevOps বলে *কী* (দ্রুত feedback, ভাগ করা দায়িত্ব); SRE বলে *কীভাবে মাপব ও প্রয়োগ করব*।

### 8.5 DevSecOps / Security Engineer

- **মূল কাজ:** Threat modeling, IAM ও least privilege, pipeline-এ security scan, secret management, supply-chain security, cloud security posture, security incident response।
- **সাফল্যের মাপ:** vulnerability fix-এর সময়, critical misconfiguration সংখ্যা, security incident-এর সংখ্যা ও প্রভাব।
- **Shift left:** শেষে একবার security audit নয় — প্রতিটি pull request-এ স্বয়ংক্রিয় check।
- **সতর্কতা:** Scanner চালানো মানেই নিরাপত্তা নয়। Scanner শুধু জানা pattern ধরে (Module 19)।

### 8.6 MLOps Engineer

- **মূল কাজ:** ML experiment tracking, data ও model versioning, training pipeline, model registry, model serving, drift monitoring, retraining ও rollback।
- **Data Scientist-এর সাথে পার্থক্য:** Data scientist model **তৈরি** করেন (কোন algorithm, কোন feature)। MLOps engineer সেই model-কে **নির্ভরযোগ্যভাবে production-এ চালানোর ব্যবস্থা** করেন।
- **সাফল্যের মাপ:** model deploy-এর সময়, reproducibility, production model-এর মান বজায় থাকা, rollback সময়।
- **বিশেষ চ্যালেঞ্জ:** সাধারণ software-এ code বদলালে আচরণ বদলায়। ML-এ **data বদলালেও** আচরণ বদলায় — code একই থাকলেও model খারাপ হতে পারে (data drift)।

### 8.7 AI Infrastructure / LLMOps Engineer

- **মূল কাজ:** GPU cluster, model serving engine (vLLM, TGI, llama.cpp), inference optimization, quantization, batching, autoscaling, token-ভিত্তিক cost ও capacity planning, LLM observability।
- **সাফল্যের মাপ:** latency (time to first token, p95), throughput (tokens/sec), GPU utilization, cost per 1000 tokens।
- **বিশেষ চ্যালেঞ্জ:** GPU দামি ও সীমিত; একটি ভুল configuration-এ মাসে হাজার ডলার নষ্ট। Memory হিসাব না করে model চালালে OOM।

### 8.8 AI-Powered Operations Engineer (উদীয়মান role)

- **মূল কাজ:** AI agent ও MCP tool দিয়ে incident triage, log summarization, runbook retrieval — কিন্তু কঠোর নিরাপত্তা সীমার মধ্যে।
- **মূল নীতি:** প্রথমে read-only; যেকোনো পরিবর্তনে human approval; prompt injection থেকে সুরক্ষা; audit trail।
- **সতর্কতা:** এটি নতুন ক্ষেত্র। Title ও প্রত্যাশা এখনো স্থির নয় — এই role-এর জন্য আগে SRE ও security-র ভিত্তি শক্ত করা জরুরি।

### 8.9 Role তুলনা সারণি

| Role | মূল customer | প্রধান output | সাফল্যের মাপ | On-call |
|---|---|---|---|---|
| DevOps | Development team | Pipeline, automation | DORA metrics | প্রায়ই |
| Cloud | Engineering org | Cloud infrastructure | Security, cost, reproducibility | মাঝে মাঝে |
| Platform | Developer (internal) | Self-service platform | Adoption, developer speed | Platform-এর জন্য |
| SRE | End user (reliability) | SLO, automation, postmortem | SLO, MTTR, toil | কেন্দ্রীয় |
| DevSecOps | পুরো org | Secure pipeline, policy | Vuln fix সময়, posture | Security incident |
| MLOps | Data scientist, product | ML pipeline, serving | Reproducibility, model মান | Model service |
| AI Infra | ML/product team | GPU platform, serving | Latency, throughput, cost/token | Serving |
| AI Ops | Operations team | Safe AI assistant | Triage সময়, নিরাপত্তা | — |

### 8.10 প্রতিষ্ঠানের আকার অনুযায়ী বাস্তবতা

| প্রতিষ্ঠান | বাস্তব চিত্র |
|---|---|
| Startup (৫–৩০ জন) | একজন "DevOps Engineer" সব করেন: cloud, CI/CD, monitoring, security, কখনো database |
| মাঝারি (৫০–৫০০) | DevOps/Platform team ও কয়েকজন SRE; security আলাদা team |
| বড় (১০০০+) | প্রতিটি role-এর আলাদা team; platform একটি internal product |

তাই shared foundation (Linux, networking, scripting, container) **সব role-এর জন্য অপরিহার্য** — এজন্যই এই repository-র প্রথম অংশ সবার জন্য একই।

## 9. Practical demonstration — নিজের role fit হিসাব

### ধাপ ১ — Model দেখুন

File: [`code/L00-02/roles.json`](code/L00-02/roles.json)

এতে আছে:

- `skills` — ১৭টি skill এলাকা।
- `modules` — প্রতিটি skill কোন module শেখায়।
- `roles` — প্রতিটি role-এর জন্য কোন skill কতটা গুরুত্বপূর্ণ (weight ১ = সহায়ক, ২ = গুরুত্বপূর্ণ, ৩ = অপরিহার্য)।

> **সতর্কতা:** এই weight শেখার সুবিধার জন্য তৈরি একটি **সরলীকৃত model**, কোনো official standard নয়। বাস্তবে প্রতিটি job description আলাদা। Exercise-এ আপনি নিজে weight বদলে দেখবেন।

### ধাপ ২ — নিজের skill rate করুন

`sample-skills.json` copy করে নিজের file বানান:

```bash
cd 00-orientation/code/L00-02
cp sample-skills.json my-skills.json
nano my-skills.json     # বা যেকোনো editor
```

`cp` একটি নতুন file তৈরি করে; মূল sample অপরিবর্তিত থাকে। `my-skills.json` আপনার ব্যক্তিগত file, Git-এ commit করার দরকার নেই।

Rating scale (সৎ থাকুন — এটি শুধু আপনার জন্য):

| মান | অর্থ |
|---|---|
| 0 | জানি না |
| 1 | নাম জানি, ধারণা আছে |
| 2 | গাইড দেখে করতে পারি |
| 3 | স্বাধীনভাবে করতে পারি |
| 4 | অন্যকে শেখাতে ও জটিল সমস্যা troubleshoot করতে পারি |

### ধাপ ৩ — Script চালান

```bash
python3 role_fit.py my-skills.json
```

Script শুধু দুটি JSON file পড়ে এবং terminal-এ ফল দেখায়। কিছু লেখে না, network ব্যবহার করে না।

**এই repository-তে sample data দিয়ে চালিয়ে পাওয়া আসল output** (`sample-skills.json` — একজন web developer-এর কাল্পনিক rating):

```text
Role fit (weighted, 0-100%):
  Site Reliability Engineer               26.2%  #####
  MLOps Engineer                          23.6%  ####
  AI-Powered Operations Engineer          22.1%  ####
  Cloud / Platform Engineer               21.9%  ####
  DevSecOps Engineer                      20.0%  ####
  DevOps Engineer                         19.6%  ###
  AI Infrastructure / LLMOps Engineer     10.0%  ##

Top skill gaps for: Site Reliability Engineer (track C)
  - Monitoring, logging, tracing             gap 12  → module 17
  - SLO, incident response, capacity         gap 12  → module 18, 30
  - Networking (TCP/IP, DNS, HTTP, TLS)      gap  9  → module 02, 06
```

নির্দিষ্ট role-এর gap দেখতে:

```bash
python3 role_fit.py my-skills.json --role "DevOps Engineer" --top 5
```

### ধাপ ৪ — ফল ব্যাখ্যা (গুরুত্বপূর্ণ)

Sample-এ SRE সবার উপরে, কিন্তু মাত্র ২৬%। এর মানে **"SRE হওয়ার জন্য প্রস্তুত" নয়** — মানে বর্তমান দক্ষতা (software development ৩, database ২) SRE-র weight-এর সাথে তুলনামূলক বেশি মেলে। সব score কম হওয়া শুরুতে স্বাভাবিক।

**হাতে একটি score যাচাই করুন — DevOps Engineer:**

Fit-এর সূত্র:

```text
fit = Σ (weight × rating) ÷ Σ (weight × 4) × 100
```

- Σ মানে "সবগুলোর যোগফল"।
- লব (উপরে): প্রতিটি skill-এর weight × আপনার rating, তারপর যোগ।
- হর (নিচে): সবকিছুতে সর্বোচ্চ rating ৪ পেলে যা হতো।

DevOps Engineer-এর weight ও sample rating:

| Skill | Weight | Rating | Weight × Rating | Weight × 4 |
|---|---|---|---|---|
| linux | 3 | 2 | 6 | 12 |
| networking | 2 | 1 | 2 | 8 |
| scripting | 3 | 1 | 3 | 12 |
| containers | 3 | 1 | 3 | 12 |
| cicd | 3 | 1 | 3 | 12 |
| iac | 2 | 0 | 0 | 8 |
| kubernetes | 2 | 0 | 0 | 8 |
| cloud | 2 | 0 | 0 | 8 |
| observability | 2 | 0 | 0 | 8 |
| security | 1 | 1 | 1 | 4 |
| **মোট** | | | **18** | **92** |

18 ÷ 92 × 100 = 19.565… → **19.6%** ✔ (output-এর সাথে মিলেছে)

**Gap-এর সূত্র:** `gap = weight × (4 − rating)`। যেমন SRE-তে observability: weight 3, rating 0 → 3 × 4 = **12**। বড় gap = যেখানে উন্নতি করলে fit সবচেয়ে বেশি বাড়বে।

### ধাপ ৫ — Test চালান

```bash
python3 -m unittest -v
```

[`test_role_fit.py`](code/L00-02/test_role_fit.py)-এর ৯টি test যাচাই করে: সূত্র সঠিক কিনা, gap সঠিক ক্রমে আসে কিনা, ভুল rating (৫, −১, ২.৫, "৩") প্রত্যাখ্যান হয় কিনা, `roles.json`-এর সব skill সংজ্ঞায়িত কিনা, এবং ভুল file/role-এ exit code ২।

## 10. Code-এর ব্যাখ্যা

File: [`code/L00-02/role_fit.py`](code/L00-02/role_fit.py) · Python 3.10+ · Dependency: নেই

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `json.load()` | JSON file-কে Python dictionary-তে রূপান্তর | JSON মানুষ ও যন্ত্র দুজনেই পড়তে পারে; configuration-এর জন্য প্রচলিত (Module 05) |
| `validate_ratings()` | অজানা skill ও ০–৪-এর বাইরের মান প্রত্যাখ্যান | Typo (যেমন `"kuberentes"`) চুপচাপ ০ হয়ে গেলে ভুল ফল আসত |
| `isinstance(value, int)` | মান পূর্ণসংখ্যা কিনা | `2.5` বা `"3"` (string) ভুল data |
| `fit_score()` | Weighted গড় শতাংশে | সাধারণ গড়ে "অপরিহার্য" ও "সহায়ক" skill সমান গুরুত্ব পেত |
| `ratings.get(skill, 0)` | Rating না থাকলে ০ | নিরাপদ default: যা জানা নেই তা ০ ধরা |
| `gaps.sort(key=lambda g: (-g[1], g[0]))` | বড় gap আগে; সমান হলে নাম অনুযায়ী | **Deterministic output:** প্রতিবার একই input-এ একই ক্রম — test ও তুলনার জন্য জরুরি |
| `except (json.JSONDecodeError, ValueError)` | ভাঙা JSON বা ভুল মান ধরে স্পষ্ট error | Python-এর লম্বা traceback-এর চেয়ে এক লাইনের বার্তা ব্যবহারকারীর জন্য পরিষ্কার |
| `sys.stdout.reconfigure(encoding="utf-8")` | Output UTF-8-এ | কিছু Windows terminal-এ default encoding UTF-8 নয়; Linux-এ সাধারণত প্রভাব নেই |

## 11. প্রত্যাশিত ফল ও যাচাই

- Sample file দিয়ে উপরের output হুবহু আসবে (data নির্দিষ্ট)।
- নিজের rating দিলে সংখ্যা আলাদা হবে — সেটাই স্বাভাবিক।
- `python3 -m unittest -v` → শেষে `Ran 9 tests` ও `OK`।
- ভুল rating যাচাই:

```bash
echo '{"linux": 7}' > /tmp/bad.json
python3 role_fit.py /tmp/bad.json; echo "exit code: $?"
```

প্রত্যাশিত: `error: invalid input: linux: rating must be an integer 0-4, got 7` এবং `exit code: 2`।

`/tmp`-এ লেখা file reboot-এ মুছে যায় — test data-র জন্য উপযুক্ত জায়গা।

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `error: invalid input: Expecting ',' delimiter` | JSON-এ কমা বাদ পড়েছে বা শেষ item-এর পরে বাড়তি কমা | Error-এ line ও column নম্বর দেখুন | JSON syntax ঠিক করুন; `python3 -m json.tool my-skills.json` দিয়ে যাচাই |
| `unknown skills: kuberentes` | বানান ভুল | `roles.json`-এর `skills` তালিকার সাথে মেলান | সঠিক নাম লিখুন |
| `error: unknown role` | `--role`-এ নাম পুরোপুরি মেলেনি | Output-এর role তালিকা দেখুন | Role নাম quote-এর ভেতরে হুবহু দিন |
| সব score খুব কম | শুরুতে স্বাভাবিক | — | হতাশ হবেন না; প্রতিটি module শেষে আবার চালিয়ে উন্নতি দেখুন |

### ধারণাগত সাধারণ ভুল

- **Title দেখে role বিচার:** একই title-এ ভিন্ন কাজ। সবসময় job description-এর "responsibilities" অংশ পড়ুন।
- **"আমি শুধু X শিখব, foundation লাগবে না":** সব role-এ Linux, networking ও troubleshooting লাগে। Interview-এ এগুলোই প্রথমে আসে।
- **Tool তালিকাকে দক্ষতা ভাবা:** "Kubernetes জানি" নয়, "Pod Pending কেন হয় diagnose করতে পারি" — এটাই দক্ষতা।
- **এই script-এর score-কে চূড়ান্ত সত্য ভাবা:** এটি নিজের ভাবনা গোছানোর tool; weight নিজের লক্ষ্য অনুযায়ী বদলান।

## 13. Security, performance ও cost বিবেচনা

- **Security সব role-এর দায়িত্ব:** DevSecOps আলাদা role হলেও pipeline লেখা DevOps engineer least privilege না মানলে বা MLOps engineer model endpoint খোলা রাখলে security team একা তা ঠেকাতে পারে না।
- **Cost দায়িত্ব:** Cloud ও AI Infra role-এ ভুল সিদ্ধান্তের সরাসরি আর্থিক প্রভাব (Module 29)।
- **এই script:** শুধু local file পড়ে। আপনার skill rating ব্যক্তিগত তথ্য — শেয়ার না করতে চাইলে `my-skills.json` Git-এ যোগ করবেন না।

## 14. Hands-on exercise

1. **নিজের rating:** `my-skills.json` সৎভাবে পূরণ করে script চালান। ফল `~/devops-notebook/L00-02-baseline.md`-এ তারিখ সহ লিখে রাখুন। Module 05, 11 ও 18 শেষে আবার চালিয়ে তুলনা করবেন।
2. **Weight পরিবর্তন:** `roles.json` copy করে (`cp roles.json my-roles.json`) "DevOps Engineer"-এর `security` weight ১ থেকে ৩ করুন। `--model my-roles.json` দিয়ে চালান। DevOps fit কতটা বদলালো? হাতে হিসাব করে মিলিয়ে দেখুন।
3. **নতুন role যোগ:** `my-roles.json`-এ "Database Reliability Engineer" নামে একটি role যোগ করুন (কোন skill-এ কত weight, নিজে যুক্তি দিয়ে ঠিক করুন)। Script চালান। তারপর `test_model_is_consistent` test-টি আপনার file দিয়ে চালানোর জন্য কী বদলাতে হবে ভাবুন।
4. **Code পরিবর্তন:** `role_fit.py`-তে `--json` option যোগ করুন যাতে ranking JSON আকারে আসে। একটি test লিখুন।

## 15. Mini-project — Job description বিশ্লেষণ

যেকোনো job site থেকে তিনটি ভিন্ন title-এর বিজ্ঞাপন নিন (যেমন DevOps Engineer, SRE, MLOps Engineer)। প্রতিটির জন্য `~/devops-notebook/L00-02-jd-analysis.md`-এ লিখুন:

1. Responsibilities-এর প্রতিটি লাইন এই lesson-এর কোন role-এর সাথে মেলে?
2. চাওয়া skill-গুলো `roles.json`-এর কোন skill-এ পড়ে? সেই অনুযায়ী একটি rating-ছাড়া "weights" তৈরি করুন।
3. Title ও আসল কাজ কি মেলে? না মিললে কোথায় অমিল?
4. আপনার `my-skills.json` দিয়ে সেই weight-এ fit হিসাব করুন (নতুন role হিসেবে `my-roles.json`-এ যোগ করে)।
5. তিনটির মধ্যে কোনটিতে আপনার gap সবচেয়ে কম, আর কোন তিনটি module সবচেয়ে বেশি সাহায্য করবে?

## 16. Interview প্রশ্ন

1. DevOps ও SRE-এর পার্থক্য ও সম্পর্ক কী?
2. Platform engineering কী? "Platform as a product" বলতে কী বোঝায়?
3. Data Scientist ও MLOps Engineer-এর দায়িত্বের সীমা কোথায়?
4. Error budget কী, এবং এটি কীভাবে development ও operations-এর মধ্যে সিদ্ধান্ত নিতে সাহায্য করে?
5. "Shift left security" বলতে কী বোঝায়? একটি উদাহরণ দিন।
6. LLM serving-এ সাধারণ web API serving-এর চেয়ে কোন নতুন চ্যালেঞ্জ আসে?
7. ছোট startup-এ একমাত্র infrastructure engineer হলে প্রথম তিন মাসে কোন কাজকে অগ্রাধিকার দেবেন, কেন?

## 17. Self-assessment প্রশ্ন

1. আটটি role-এর প্রতিটির "মূল প্রশ্ন" এক বাক্যে নিজের ভাষায় লিখুন।
2. Section 5-এর payment API incident-এ কোন দুটি role-এর কাজ না থাকলে recovery সবচেয়ে বেশি দেরি হতো? কেন?
3. হাসপাতাল analogy কোথায় software role-এর সাথে মেলে না — দুটি কারণ লিখুন।
4. Sample data দিয়ে "MLOps Engineer"-এর fit (23.6%) হাতে হিসাব করে মিলিয়ে দেখান।
5. কেন shared foundation (Linux, networking, scripting) সব role-এর জন্য একই?
6. আপনার নিজের লক্ষ্য কোন track (A–G)? আপনার baseline output থেকে কোন তিনটি gap আগে পূরণ করবেন?

## 18. সংক্ষিপ্ত সারাংশ

- সব role একই লক্ষ্যের ভিন্ন অংশ: software দ্রুত, নিরাপদে ও নির্ভরযোগ্যভাবে user-এর কাছে পৌঁছানো ও চালানো।
- **DevOps** = delivery প্রবাহ ও automation; **Cloud** = infrastructure foundation; **Platform** = developer-দের জন্য self-service product; **SRE** = মাপযোগ্য reliability; **DevSecOps** = প্রতিটি ধাপে security; **MLOps** = ML-কে production-এ নির্ভরযোগ্য করা; **AI Infra** = দামি model ও GPU দক্ষভাবে serve করা; **AI Ops** = AI দিয়ে নিরাপদে operations।
- Role-এর সীমা প্রতিষ্ঠান ভেদে আলাদা; ছোট প্রতিষ্ঠানে একজনই অনেক role পালন করেন।
- Shared foundation সবার জন্য অপরিহার্য — তারপর specialization।
- Title নয়, দায়িত্ব ও প্রমাণিত দক্ষতা দেখুন।

## 19. Completion checklist

- [ ] আটটি role-এর মূল কাজ ও সাফল্যের মাপ নিজের ভাষায় বলতে পারি
- [ ] `role_fit.py` sample ও নিজের data দিয়ে চালিয়েছি
- [ ] DevOps Engineer-এর fit হাতে হিসাব করে মিলিয়েছি
- [ ] `python3 -m unittest -v` চালিয়ে ৯টি test পাস দেখেছি
- [ ] Exercise ১ (baseline) ও ২ (weight পরিবর্তন) শেষ করেছি
- [ ] Mini-project-এ অন্তত দুটি job description বিশ্লেষণ করেছি
- [ ] নিজের লক্ষ্য track বেছে [LEARNING-TRACKS.md](../LEARNING-TRACKS.md)-এর সাথে মিলিয়েছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট করেছি

## 20. Official documentation ও further reading

- Google SRE books (বিনামূল্যে অনলাইন), বিশেষ করে প্রথম অধ্যায় "Introduction": https://sre.google/books/
- DORA research: https://dora.dev/
- Cloud Native Computing Foundation (Platform Engineering working group ও white paper): https://www.cncf.io/
- Python `json` module: https://docs.python.org/3/library/json.html
- এই repository-র track ব্যাখ্যা: [LEARNING-TRACKS.md](../LEARNING-TRACKS.md)

---

**পরের lesson:** L00-03 — SDLC, Agile, Scrum, Kanban ও release management
