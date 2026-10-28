# L00-01 — DevOps আসলে কী: culture, feedback loop ও DORA metrics

| | |
|---|---|
| **Module** | 00 — Engineering Orientation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা (পড়া + practice) |
| **পূর্বশর্ত** | নেই — এটি প্রথম lesson |
| **Label** | — (কোনো বিশেষ hardware বা cloud লাগবে না) |
| **Tested** | Python code: Python 3.14-এ test চালানো হয়েছে (৭টি test পাস)। Ubuntu 24.04-এর Python 3.12-এও চলার কথা (শুধু standard library), তবে সেখানে চালিয়ে দেখা হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- DevOps কোনো tool বা job title নয় — এটি একটি **কাজের পদ্ধতি ও culture**।
- Development ও Operations আলাদা থাকলে কী সমস্যা হয়।
- **Feedback loop** কী এবং কেন ছোট ও দ্রুত feedback loop গুরুত্বপূর্ণ।
- DevOps-এর মূল নীতি: **CALMS** এবং **Three Ways**।
- Software delivery কীভাবে মাপা হয়: **DORA metrics**।
- Python দিয়ে নিজে DORA metric হিসাব করা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একসময় (এবং এখনো অনেক প্রতিষ্ঠানে) software তৈরি ও চালানো দুটি আলাদা team-এর কাজ ছিল:

- **Development (Dev) team:** নতুন feature লেখে। তাদের লক্ষ্য **পরিবর্তন** — যত দ্রুত সম্ভব নতুন জিনিস দেওয়া।
- **Operations (Ops) team:** server চালায়, service সচল রাখে। তাদের লক্ষ্য **স্থিতিশীলতা** — কিছু যেন না ভাঙে।

দুই team-এর লক্ষ্য একে অপরের বিপরীত। পরিবর্তন মানেই ঝুঁকি, তাই Ops পরিবর্তন আটকাতে চায়। Dev চায় দ্রুত release। ফলাফল:

- Release হয় মাসে বা তিন মাসে একবার, বিশাল আকারে। কিছু ভাঙলে কোন পরিবর্তনটা দায়ী বোঝা কঠিন।
- Dev code "ছুড়ে দেয়" Ops-এর কাছে ("wall of confusion"); production-এ কী ঘটে তা Dev দেখে না।
- সমস্যা হলে দোষারোপ: "আমার machine-এ তো চলছিল!" বনাম "তোমার code server ভেঙেছে!"
- হাতে করা deployment — প্রতিবার আলাদা, ভুলপ্রবণ, রাত জেগে করতে হয়।

**DevOps এই বিভাজন ভাঙে।** একই team (বা ঘনিষ্ঠভাবে কাজ করা team) software তৈরি করে, deploy করে, চালায় এবং production থেকে শেখে। Automation, measurement ও ভাগ করা দায়িত্ব দিয়ে **দ্রুততা ও স্থিতিশীলতা একসাথে** পাওয়া যায়।

## 3. সহজ ভাষায় পরিচয়

**DevOps আসলে কী?**
DevOps হলো software তৈরি (Development) ও চালানো (Operations)-কে একটি ধারাবাহিক, ভাগ করা প্রক্রিয়া হিসেবে দেখার পদ্ধতি। এর তিনটি অংশ: **মানুষ ও culture**, **process**, এবং **automation tool**। Tool সবচেয়ে কম গুরুত্বপূর্ণ।

**কেন তৈরি হয়েছিল?**
২০০৯ সালের দিকে কিছু engineer দেখালেন যে Dev ও Ops একসাথে কাজ করলে দিনে বহুবার নিরাপদে deploy করা সম্ভব। "DevOps" শব্দটি তখন জনপ্রিয় হয়।

**কোন সমস্যা সমাধান করে?**
ধীর ও ঝুঁকিপূর্ণ release, দোষারোপের culture, এবং user-এর কাছ থেকে শিখতে দেরি হওয়া।

**এটি না থাকলে কী হতো?**
প্রতিটি release একটি বড় ঘটনা হতো। সমস্যা ধরতে সপ্তাহ লাগত। একটি bug fix user-এর কাছে পৌঁছাতে মাস লাগত।

**বাস্তবে কখন ব্যবহার হয়?**
প্রায় সব আধুনিক software প্রতিষ্ঠানে — ছোট startup থেকে বড় bank পর্যন্ত। তবে "DevOps করছি" দাবি আর আসলে করা এক জিনিস নয়। শুধু Jenkins বা Kubernetes install করলেই DevOps হয় না।

### একটি সাধারণ ভুল ধারণা

> "DevOps engineer = যে Docker, Kubernetes, CI/CD চালায়।"

চাকরির বাজারে "DevOps Engineer" title প্রচলিত, এবং তাদের কাজে এসব tool আছে। কিন্তু DevOps-এর মূল কথা হলো **team-গুলো কীভাবে একসাথে কাজ করে এবং দ্রুত শেখে**। Tool হলো সেই পদ্ধতি বাস্তবায়নের মাধ্যম।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### Analogy ১: রেস্টুরেন্টের রান্নাঘর

**পুরোনো পদ্ধতি:** রাঁধুনি রান্না করে প্লেট দরজার বাইরে রেখে চলে যান। Waiter খাবার পরিবেশন করেন। Customer বলেন লবণ বেশি — waiter জানেন, কিন্তু রাঁধুনি কখনো জানতে পারেন না। পরের দিনও একই ভুল।

**DevOps পদ্ধতি:** রাঁধুনি ও waiter একই team। Customer-এর প্রতিক্রিয়া মিনিটের মধ্যে রান্নাঘরে পৌঁছায়। রাঁধুনি ছোট ছোট পরিবর্তন করে সঙ্গে সঙ্গে দেখেন ফল কী হলো। রেসিপি লিখিত (automation), তাই যেকোনো রাঁধুনি একই মানের খাবার বানাতে পারেন।

### Analogy ২: গাড়ি চালানো ও feedback

চোখ বন্ধ করে ১০ মিনিট গাড়ি চালিয়ে তারপর চোখ খুলে দেখা — এটা পুরোনো release পদ্ধতি। প্রতি সেকেন্ডে রাস্তা দেখে ছোট ছোট steering সংশোধন — এটা **ছোট feedback loop**। দ্রুত feedback থাকলে ছোট ভুল বড় দুর্ঘটনায় পরিণত হওয়ার আগেই ঠিক করা যায়।

### Analogy কোথায় মেলে না

- রেস্টুরেন্টে প্রতিটি প্লেট আলাদা। Software-এ একটি deploy একসাথে **হাজার-লাখ user**-কে প্রভাবিত করে। তাই পরিবর্তন ধীরে ছড়ানো (canary deployment) ও দ্রুত ফেরত যাওয়ার (rollback) ব্যবস্থা লাগে — রান্নাঘরে এর সরাসরি তুলনা নেই।
- রান্নাঘরে feedback আসে মানুষের মুখে। Software-এ feedback বেশিরভাগ আসে **যন্ত্র থেকে**: automated test, monitoring metric, error log। এগুলো আগে থেকে design করতে হয়।
- গাড়ির analogy-তে একজন চালক। বাস্তবে অনেক team একই system-এ একসাথে পরিবর্তন করে — তাই coordination ও version control দরকার।

## 5. Real-world engineering scenario

**পরিস্থিতি:** একটি e-commerce কোম্পানি। একজন developer checkout page-এর একটি bug ঠিক করেছেন (৩ লাইনের পরিবর্তন)।

**পুরোনো পদ্ধতিতে ঘটনার ক্রম:**

1. Fix লেখা হলো সোমবার।
2. পরবর্তী release window তিন সপ্তাহ পরে। তার আগে আরো ২০০টি পরিবর্তন জমা হলো।
3. Release-এর রাতে Ops team হাতে ২৫টি ধাপের একটি document অনুসরণ করে deploy করলেন।
4. ধাপ ১৭-তে একটি configuration ভুল হলো। Site ২ ঘণ্টা down।
5. ২০০টি পরিবর্তনের মধ্যে কোনটি সমস্যা করছে খুঁজতে আরো ৩ ঘণ্টা।
6. Checkout bug-এর fix user-এর কাছে পৌঁছাল ২২ দিন পরে — এবং পথে নতুন একটি outage।

**DevOps পদ্ধতিতে ঘটনার ক্রম:**

1. Fix লেখা হলো সোমবার সকালে। Pull request খোলা হলো।
2. Automated pipeline: test চলল (৫ মিনিট), একজন সহকর্মী review করলেন (৩০ মিনিট)।
3. Merge হওয়ার পরে pipeline নিজে artifact তৈরি করে প্রথমে ৫% user-এ deploy করল।
4. Monitoring dashboard-এ error rate স্বাভাবিক — pipeline বাকি user-এ deploy করল।
5. Fix user-এর কাছে পৌঁছাল **২ ঘণ্টার মধ্যে**।

**কী ভুল হতে পারে (DevOps-এও):**

- Test দুর্বল হলে pipeline ভাঙা code পার করে দেবে — automation শুধু যা পরীক্ষা করতে বলা হয়েছে তা-ই পরীক্ষা করে।
- Monitoring না থাকলে ৫% user-এর সমস্যা কেউ দেখবে না।
- দ্রুত deploy মানে দ্রুত ভুলও ছড়াতে পারে — তাই rollback অপরিহার্য।

**Engineer কীভাবে diagnose করবেন:** কোন deploy কখন হলো (deployment history), ঠিক তার পরে error rate বাড়ল কিনা (metric), কোন commit সেই deploy-এ ছিল (version control)। ছোট deploy হওয়ায় সন্দেহভাজন পরিবর্তন মাত্র একটি বা দুটি।

## 6. Diagram — DevOps feedback loop

```text
        ┌──────────────────────── শেখা ও উন্নতি ◄────────────────────────┐
        │                                                                 │
        ▼                                                                 │
   ┌─────────┐   ┌────────┐   ┌────────┐   ┌─────────┐   ┌─────────┐   ┌──┴──────┐
   │  Plan   │──►│  Code  │──►│ Build  │──►│  Test   │──►│ Release │──►│ Deploy  │
   └─────────┘   └────────┘   └────────┘   └─────────┘   └─────────┘   └────┬────┘
        ▲            ▲  │          │             │                           │
        │            │  └──────────┴─────────────┘                           ▼
        │            │     দ্রুত feedback (মিনিট):                    ┌──────────┐
        │            │     test fail → developer জানেন                │ Operate  │
        │            │                                               └────┬─────┘
        │            │                                                    ▼
        │            │     production feedback (মিনিট–ঘণ্টা):        ┌──────────┐
        └────────────┴──── error, latency, user behavior ◄────────────│ Monitor  │
                                                                     └──────────┘
```

মূল কথা: **বাম থেকে ডানে** কাজ প্রবাহিত হয়, **ডান থেকে বামে** feedback ফেরে। Feedback যত দ্রুত, তত সস্তায় ভুল ঠিক হয়।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Development (Dev) | Software design ও code লেখার কাজ |
| Operations (Ops) | Software production-এ চালানো, সচল রাখা ও সমস্যা সমাধানের কাজ |
| Production | আসল user যে system ব্যবহার করে |
| Deployment | নতুন version production-এ (বা অন্য environment-এ) চালু করা |
| Release | নতুন feature user-এর কাছে উন্মুক্ত করা (deploy হলেও feature flag দিয়ে লুকানো থাকতে পারে) |
| Feedback loop | কাজের ফলাফল থেকে তথ্য ফিরে এসে পরের কাজকে প্রভাবিত করার চক্র |
| Automation | পুনরাবৃত্তিমূলক কাজ যন্ত্রকে দিয়ে করানো — একইভাবে, প্রতিবার |
| Pipeline | Code থেকে production পর্যন্ত automated ধাপের ক্রম |
| Batch size | একবারে কতগুলো পরিবর্তন একসাথে release হয় |
| Rollback | সমস্যাযুক্ত version থেকে আগের ভালো version-এ ফেরা |
| Blameless culture | ভুলের জন্য ব্যক্তিকে নয়, system-এর দুর্বলতাকে খোঁজা |
| Median | সংখ্যাগুলো সাজালে ঠিক মাঝের মান; অস্বাভাবিক বড়/ছোট মানে কম প্রভাবিত হয় |

## 8. ভেতরে কীভাবে কাজ করে — DevOps-এর নীতি

### 8.1 CALMS framework

DevOps-এর পাঁচটি স্তম্ভ মনে রাখার উপায়:

| অক্ষর | নীতি | বাস্তবে কী মানে |
|---|---|---|
| **C** | Culture | ভাগ করা দায়িত্ব; blameless postmortem; Dev production সমস্যা দেখে |
| **A** | Automation | Build, test, deploy, infrastructure — সব যন্ত্রে; হাতে কাজ কমানো |
| **L** | Lean | ছোট batch, waste কমানো, কাজের প্রবাহ মসৃণ রাখা |
| **M** | Measurement | অনুমান নয় — metric দিয়ে সিদ্ধান্ত (যেমন DORA metrics) |
| **S** | Sharing | জ্ঞান, tool, documentation ও শিক্ষা team-এর মধ্যে ভাগ করা |

### 8.2 The Three Ways

*The Phoenix Project* ও *The DevOps Handbook* বই থেকে আসা তিনটি নীতি:

1. **Flow (প্রবাহ):** কাজ Dev থেকে Ops হয়ে user পর্যন্ত দ্রুত ও মসৃণভাবে যাক। কৌশল: ছোট batch, automation, কাজ দৃশ্যমান রাখা।
2. **Feedback:** ডান থেকে বামে দ্রুত তথ্য ফিরুক। কৌশল: automated test, monitoring, alert, user feedback।
3. **Continual learning and experimentation:** ভুল থেকে শেখা, নিরাপদে experiment করা। কৌশল: blameless postmortem, chaos experiment, সময় বরাদ্দ করে উন্নতি।

### 8.3 ছোট batch কেন এত গুরুত্বপূর্ণ — একটু হিসাব

ধরুন প্রতিটি পরিবর্তনে সমস্যা থাকার সম্ভাবনা ২% (০.০২), এবং প্রতিটি পরিবর্তন অন্যগুলো থেকে স্বাধীন।

- **১টি পরিবর্তন** release করলে কোনো সমস্যা **না** থাকার সম্ভাবনা = 0.98
- **২০০টি পরিবর্তন** একসাথে release করলে কোনো সমস্যা না থাকার সম্ভাবনা = 0.98²⁰⁰

0.98²⁰⁰ হিসাব করি: ln(0.98) ≈ −0.0202, তাই 200 × (−0.0202) = −4.04, এবং e^(−4.04) ≈ 0.018।

অর্থাৎ বড় release-এ **প্রায় ৯৮% সম্ভাবনা অন্তত একটি সমস্যা থাকবে**। আর সমস্যা হলে ২০০টির মধ্যে কোনটি দায়ী খুঁজতে হবে। ছোট release-এ সমস্যা কম, এবং হলে দায়ী পরিবর্তনটি সহজে চেনা যায়।

> এটি একটি সরলীকৃত model (বাস্তবে পরিবর্তনগুলো পুরোপুরি স্বাধীন নয়), কিন্তু মূল শিক্ষা সঠিক: **batch size যত বড়, ঝুঁকি ও debugging খরচ তত বেশি।**

### 8.4 DORA metrics — delivery কীভাবে মাপা হয়

**DORA (DevOps Research and Assessment)** একটি গবেষণা program, যা বহু বছর ধরে হাজার হাজার প্রতিষ্ঠানের software delivery নিয়ে জরিপ করেছে। তাদের মূল চারটি metric:

| Metric | কী মাপে | ধরন |
|---|---|---|
| **Deployment frequency** | কত ঘন ঘন production-এ deploy হয় | গতি (throughput) |
| **Lead time for changes** | Code commit থেকে production-এ চলা পর্যন্ত সময় | গতি (throughput) |
| **Change failure rate** | কত শতাংশ deploy production-এ সমস্যা তৈরি করে (rollback/hotfix লাগে) | স্থিতিশীলতা |
| **Failed deployment recovery time** | ব্যর্থ deploy-এর পরে service ঠিক হতে কত সময় লাগে | স্থিতিশীলতা |

**DORA গবেষণার সবচেয়ে গুরুত্বপূর্ণ ফলাফল:** গতি ও স্থিতিশীলতা পরস্পরবিরোধী নয়। ভালো পারফর্ম করা team-গুলো **একই সাথে** দ্রুত deploy করে **এবং** কম ব্যর্থ হয়। কারণ ছোট batch, automation ও দ্রুত feedback দুটোকেই উন্নত করে।

> **Version নোট:** পুরোনো রিপোর্টে চতুর্থ metric-এর নাম ছিল "Time to restore service" বা "MTTR"। সাম্প্রতিক রিপোর্টে নাম বদলে "Failed deployment recovery time" করা হয়েছে, এবং নতুন metric (যেমন rework rate) যোগ হয়েছে। Metric-এর নাম, সংজ্ঞা ও performance level-এর সীমা সময়ের সাথে বদলায় — বর্তমান সংজ্ঞা সবসময় [dora.dev](https://dora.dev/) থেকে যাচাই করুন। এই lesson-এ চারটি মূল metric ব্যবহার করা হয়েছে।

**সতর্কতা — metric-এর অপব্যবহার:**

- Metric দিয়ে **ব্যক্তি বা team-কে তুলনা বা শাস্তি দেওয়া** উচিত নয়। তাহলে মানুষ metric-কে "game" করবে (যেমন অর্থহীন ছোট deploy করে frequency বাড়ানো)। একে বলে **Goodhart's law**: কোনো মাপ লক্ষ্য হয়ে গেলে সেটি আর ভালো মাপ থাকে না।
- Metric হলো **নিজের উন্নতি দেখার আয়না**, অন্যের সাথে প্রতিযোগিতার scoreboard নয়।

## 9. Practical demonstration

এই lesson-এর practical: একটি কাল্পনিক team-এর ১০টি deployment-এর record থেকে Python দিয়ে চারটি DORA metric হিসাব করা।

### ধাপ ১ — Data দেখুন

File: [`code/L00-01/deployments.csv`](code/L00-01/deployments.csv)

```bash
# repository root থেকে
cat 00-orientation/code/L00-01/deployments.csv
```

এটি শুধু file পড়ে দেখায়, কিছু পরিবর্তন করে না।

```text
deploy_id,commit_time,deploy_time,failed,restored_time
d01,2026-10-01T09:00:00,2026-10-01T15:00:00,no,
d02,2026-10-02T10:00:00,2026-10-03T11:00:00,no,
d03,2026-10-04T08:30:00,2026-10-04T12:30:00,yes,2026-10-04T13:15:00
...
```

প্রতিটি column-এর অর্থ:

| Column | অর্থ |
|---|---|
| `deploy_id` | Deployment-এর পরিচয় |
| `commit_time` | পরিবর্তনটি কখন commit হয়েছিল |
| `deploy_time` | কখন production-এ deploy হলো |
| `failed` | এই deploy production-এ সমস্যা তৈরি করেছিল কিনা (`yes`/`no`) |
| `restored_time` | ব্যর্থ হলে, কখন service আবার স্বাভাবিক হলো |

বাস্তবে এই তথ্য আসে CI/CD system (যেমন GitHub Actions-এর deployment history), version control (commit সময়) এবং incident tracker থেকে। এখানে হাতে বানানো data ব্যবহার করছি যাতে হিসাব নিজে যাচাই করা যায়।

### ধাপ ২ — Python environment যাচাই

```bash
python3 --version
```

Python 3.10 বা তার বেশি হলেই চলবে। Script শুধু standard library ব্যবহার করে, তাই কিছু install করতে হবে না।

> **Fedora-তে:** একই command। Python 3 Fedora-তে preinstalled থাকে।

### ধাপ ৩ — Script চালান

```bash
python3 00-orientation/code/L00-01/dora_metrics.py 00-orientation/code/L00-01/deployments.csv
```

এই command CSV পড়ে, হিসাব করে terminal-এ দেখায়। কোনো file লেখে না, network ব্যবহার করে না।

**এই repository-তে script চালিয়ে পাওয়া আসল output** (sample data দিয়ে):

```text
Deployments analysed            : 10 (window 18.96 days)
Deployment frequency            : 0.53 per day
Lead time for changes (median)  : 6.5 hours
Change failure rate             : 20.0 %
Failed deploy recovery (median) : 1.88 hours
```

Machine-readable output (অন্য tool-এ পাঠানোর জন্য):

```bash
python3 00-orientation/code/L00-01/dora_metrics.py 00-orientation/code/L00-01/deployments.csv --json
```

### ধাপ ৪ — হাতে হিসাব মিলিয়ে দেখুন (সবচেয়ে গুরুত্বপূর্ণ ধাপ)

Program-এর উপর অন্ধ বিশ্বাস নয়। অন্তত একটি metric হাতে হিসাব করুন।

**Lead time (প্রতিটি deploy-এ commit থেকে deploy পর্যন্ত ঘণ্টা):**

| Deploy | হিসাব | ঘণ্টা |
|---|---|---|
| d01 | ০৯:০০ → ১৫:০০ একই দিন | 6 |
| d02 | ২ অক্টোবর ১০:০০ → ৩ অক্টোবর ১১:০০ | 25 |
| d03 | ০৮:৩০ → ১২:৩০ | 4 |
| d04 | ৬ অক্টোবর ১৪:০০ → ৭ অক্টোবর ১০:০০ | 20 |
| d05 | ০৯:০০ → ১৬:০০ | 7 |
| d06 | ৯ অক্টোবর ১১:০০ → ১৩ অক্টোবর ১১:০০ (৪ দিন) | 96 |
| d07 | ১০:০০ → ১৩:০০ | 3 |
| d08 | ০৯:০০ → ১২:০০ | 3 |
| d09 | ১৭ অক্টোবর ১৩:০০ → ১৮ অক্টোবর ০৯:০০ | 20 |
| d10 | ১০:০০ → ১৪:০০ | 4 |

ছোট থেকে বড় সাজাই: 3, 3, 4, 4, **6, 7**, 20, 20, 25, 96

১০টি সংখ্যা (জোড়), তাই median = মাঝের দুটির গড় = (6 + 7) ÷ 2 = **6.5 ঘণ্টা**। Program-এর সাথে মিলে গেছে। ✔

**Average দিলে কী হতো?** যোগফল = 188, গড় = 18.8 ঘণ্টা। শুধু d06-এর ৯৬ ঘণ্টার জন্য গড় প্রায় তিনগুণ হয়ে গেছে। এজন্য lead time-এ **median** বেশি প্রতিনিধিত্বমূলক। পরে (Module 17) আমরা percentile (p50, p95) শিখব — median আসলে p50।

**Change failure rate:** ১০টির মধ্যে ২টি (d03, d07) failed → 2 ÷ 10 × 100 = **20%**।

**Recovery time:** d03: ১২:৩০ → ১৩:১৫ = 0.75 ঘণ্টা; d07: ১৩:০০ → ১৬:০০ = 3 ঘণ্টা। Median = (0.75 + 3) ÷ 2 = 1.875 → **1.88 ঘণ্টা** (দুই দশমিকে round)।

**Deployment frequency:** প্রথম deploy ১ অক্টোবর ১৫:০০, শেষ deploy ২০ অক্টোবর ১৪:০০ → 18 দিন 23 ঘণ্টা = 18.96 দিন। 10 ÷ 18.96 = **0.53 deploy/দিন** (মোটামুটি প্রতি দুই দিনে একবার)।

### ধাপ ৫ — Test চালান

```bash
cd 00-orientation/code/L00-01
python3 -m unittest -v
```

[`test_dora_metrics.py`](code/L00-01/test_dora_metrics.py) ৭টি পরীক্ষা চালায়: sample data-র সঠিক ফল, কোনো failure না থাকলে কী হয়, খালি data, এবং ভুল data (যেমন commit-এর আগে deploy) প্রত্যাখ্যান করা হয় কিনা।

## 10. Python example — code-এর ব্যাখ্যা

File: [`code/L00-01/dora_metrics.py`](code/L00-01/dora_metrics.py) · Python 3.10+ · Dependency: নেই

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `@dataclass(frozen=True) class Deployment` | একটি deployment-এর data রাখার structure | `frozen=True` মানে তৈরির পরে বদলানো যায় না — হিসাবের মাঝে ভুল করে data বদলে যাওয়া ঠেকায় |
| `parse_row()` | CSV-র একটি row যাচাই করে `Deployment` বানায় | **Input validation:** ভুল data চুপচাপ ভুল metric দেয় — তার চেয়ে স্পষ্ট error অনেক ভালো |
| `datetime.fromisoformat()` | "2026-10-01T09:00:00" লেখাকে সময়-object-এ রূপান্তর | ISO 8601 হলো সময় লেখার আন্তর্জাতিক standard; অস্পষ্টতা নেই |
| `if deploy_time < commit_time: raise ValueError` | অসম্ভব data ধরা | বাস্তব data-তে clock ভুল বা copy-paste ভুল থাকে |
| `window_days = max(..., 1.0)` | মোট সময়কাল দিনে | সব deploy একই সময়ে হলে শূন্য দিয়ে ভাগ হতো — তা ঠেকাতে কমপক্ষে ১ দিন |
| `statistics.median(lead_times)` | মাঝের মান | Average একটি ধীর পরিবর্তনে বিকৃত হয় (উপরে দেখানো হয়েছে) |
| `main()` return `2` | ভুল হলে exit code 2 | Script-এর exit code দিয়ে অন্য script বা CI বুঝতে পারে সফল হলো কিনা (Module 01 ও 04-এ বিস্তারিত) |
| `--json` | machine-readable output | মানুষ পড়বে text, অন্য program পড়বে JSON — একই tool দুটোই দেয় |
| `print(..., file=sys.stderr)` | Error message আলাদা stream-এ | Normal output (stdout) ও error (stderr) আলাদা থাকলে pipe করা সহজ |

## 11. প্রত্যাশিত ফল ও যাচাই

- Script চালালে উপরের পাঁচ লাইনের output আসবে (sample data দিয়ে সংখ্যা হুবহু একই হবে, কারণ data নির্দিষ্ট)।
- `python3 -m unittest -v` চালালে শেষে `OK` ও `Ran 7 tests` দেখাবে।
- ভুল file দিলে: `error: file not found: ...` এবং exit code 2। যাচাই:

```bash
python3 00-orientation/code/L00-01/dora_metrics.py nothing.csv; echo "exit code: $?"
```

`$?` হলো শেষ command-এর exit code। এটি ২ দেখানো উচিত।

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `python3: command not found` | Python install নেই | `which python3` কিছু দেখায় না | Ubuntu: `sudo apt install python3` |
| `error: file not found` | ভুল directory থেকে চালানো | `pwd` দিয়ে বর্তমান directory দেখুন | Repository root থেকে চালান, বা সঠিক path দিন |
| `error: invalid data: ... failed must be yes/no` | CSV-তে `Yes`/`true`/খালি | CSV-র সেই row দেখুন | `yes` বা `no` লিখুন (বড়/ছোট হাতের অক্ষর চলবে) |
| `Invalid isoformat string` | সময় ভুল format-এ (যেমন `01/10/2026`) | error message-এ মানটি দেখুন | `YYYY-MM-DDTHH:MM:SS` format ব্যবহার করুন |
| সংখ্যা অপ্রত্যাশিত | data-তে ভুল সময় | হাতে একটি row হিসাব করুন (ধাপ ৪) | data সংশোধন |

### ধারণাগত সাধারণ ভুল

- **"আমরা Kubernetes ব্যবহার করি, তাই আমরা DevOps"** — tool ব্যবহার culture বা process পরিবর্তন নিশ্চিত করে না।
- **"DevOps মানে Ops team বাদ দেওয়া"** — না। Operations-এর দক্ষতা আরো বেশি দরকার; শুধু বিচ্ছিন্ন silo ভাঙা হয়।
- **"দ্রুত deploy = বেশি ঝুঁকি"** — DORA গবেষণা উল্টোটা দেখায়, যদি সাথে automation ও feedback থাকে।
- **একটি metric একা দেখা** — শুধু deployment frequency বাড়ালে কিন্তু change failure rate-ও বাড়লে উন্নতি হয়নি। চারটি একসাথে দেখতে হয়।

## 13. Security, performance ও cost বিবেচনা

- **Security:** দ্রুত deploy মানে security fix-ও দ্রুত পৌঁছায়। তবে pipeline-এ security check না থাকলে দুর্বল code-ও দ্রুত পৌঁছায়। তাই security pipeline-এর অংশ হতে হবে, শেষে আলাদা "gate" নয় — একে বলে **DevSecOps** (Module 19)।
- **Performance:** ছোট পরিবর্তনে performance সমস্যা (যেমন হঠাৎ ধীর page) কোন পরিবর্তন থেকে এলো তা সহজে চেনা যায়।
- **Cost:** Automation-এ শুরুতে সময় বিনিয়োগ লাগে। কিন্তু হাতে করা deploy, দীর্ঘ outage ও রাত-জাগা release-এর খরচ সাধারণত অনেক বেশি।
- **এই script-এর নিরাপত্তা:** শুধু local file পড়ে, network বা system-এ কিছু করে না। বাস্তব deployment data-য় কোনো secret থাকা উচিত নয়, তবু শেয়ার করার আগে দেখে নিন।

## 14. Hands-on exercise

1. **Data পরিবর্তন:** `deployments.csv`-এর একটি copy বানান (`cp deployments.csv my-team.csv`)। d06-এর `deploy_time` বদলে `2026-10-09T15:00:00` করুন। Lead time-এর median ও average দুটোই হাতে হিসাব করুন, তারপর script দিয়ে মিলিয়ে দেখুন। কোনটি বেশি বদলালো? কেন?
2. **নতুন metric যোগ:** `dora_metrics.py`-তে lead time-এর **average**-ও output-এ যোগ করুন (`statistics.mean`)। Test-এ নতুন একটি assertion যোগ করুন এবং test চালান।
3. **ভুল data:** CSV-তে এমন একটি row যোগ করুন যেখানে `failed=yes` কিন্তু `restored_time` খালি। Script কী বলে? Error message কি যথেষ্ট পরিষ্কার?
4. **নিজের অভিজ্ঞতা:** আপনার WordPress/PHP কাজে শেষ ৫টি deploy মনে করুন (বা অনুমান করুন)। প্রতিটির জন্য commit থেকে live হতে কত সময় লেগেছিল? কোনোটি কি সমস্যা করেছিল? একটি CSV বানিয়ে script চালান।

## 15. Mini-project — "আমার delivery process"

আপনার সর্বশেষ (বা কাল্পনিক) web project-এর deployment process নিয়ে `~/devops-notebook/L00-01-my-process.md` লিখুন:

1. Code থেকে live server পর্যন্ত প্রতিটি ধাপ লিখুন (যেমন: local-এ লেখা → FTP/Git দিয়ে upload → cache clear …)।
2. প্রতিটি ধাপ হাতে নাকি automated চিহ্নিত করুন।
3. কোথায় feedback দেরিতে আসে চিহ্নিত করুন (যেমন: user ভুল জানালে তবেই জানা যায়)।
4. Section 6-এর মতো একটি ASCII diagram আঁকুন।
5. সবচেয়ে বড় তিনটি সমস্যা ও সম্ভাব্য সমাধান লিখুন — এই repository-র কোন module সেগুলো সমাধান শেখাবে?

## 16. Interview প্রশ্ন

1. DevOps কী? এটি কি একটি job title, tool, নাকি অন্য কিছু?
2. Dev ও Ops আলাদা থাকলে কী সমস্যা হয়? একটি বাস্তব উদাহরণ দিন।
3. CALMS-এর প্রতিটি অক্ষর ব্যাখ্যা করুন।
4. DORA-র চারটি মূল metric কী? কোনগুলো গতি আর কোনগুলো স্থিতিশীলতা মাপে?
5. ছোট batch-এ release কেন ঝুঁকি কমায়?
6. আপনার team-এর deployment frequency বাড়াতে বলা হলে প্রথম তিনটি কী পদক্ষেপ নেবেন? কীভাবে নিশ্চিত হবেন যে স্থিতিশীলতা কমছে না?
7. Metric দিয়ে team-কে মূল্যায়ন করার ঝুঁকি কী?

## 17. Self-assessment প্রশ্ন

নিজের ভাষায় লিখে উত্তর দিন (খাতায় বা notebook-এ):

1. Dev ও Ops-এর লক্ষ্য কেন স্বাভাবিকভাবে পরস্পরবিরোধী? DevOps এই সংঘাত কীভাবে কমায়?
2. "Feedback loop ছোট করা" বলতে কী বোঝায়? দুটি উদাহরণ দিন — একটি development পর্যায়ে, একটি production পর্যায়ে।
3. Lead time-এ average-এর বদলে median কেন ব্যবহার করা হলো? আপনার নিজের হিসাব দিয়ে দেখান।
4. ২০০টি পরিবর্তন একসাথে release-এ কোনো সমস্যা না থাকার সম্ভাবনা হিসাব করুন যদি প্রতিটির ঝুঁকি ১% হয়। (সংকেত: 0.99²⁰⁰; ln(0.99) ≈ −0.01005)
5. রেস্টুরেন্ট analogy কোন দুটি জায়গায় software delivery-র সাথে মেলে না?
6. একটি team দাবি করছে তারা দিনে ৫০ বার deploy করে, তাই তারা চমৎকার। আর কোন তথ্য না জেনে আপনি এই দাবি মেনে নেবেন না?

## 18. সংক্ষিপ্ত সারাংশ

- DevOps হলো Development ও Operations-কে একটি ভাগ করা, ধারাবাহিক প্রক্রিয়া হিসেবে দেখা — **culture + process + automation**, যার মধ্যে tool সবচেয়ে কম গুরুত্বপূর্ণ।
- মূল ধারণা **feedback loop**: কাজ বাম থেকে ডানে যায়, তথ্য ডান থেকে বামে ফেরে। যত দ্রুত feedback, তত সস্তায় ভুল ঠিক হয়।
- **ছোট batch** ঝুঁকি কমায় এবং debugging সহজ করে।
- **CALMS** (Culture, Automation, Lean, Measurement, Sharing) ও **Three Ways** (Flow, Feedback, Learning) হলো নীতি।
- **DORA metrics** দিয়ে delivery মাপা হয়: deployment frequency, lead time, change failure rate, failed deployment recovery time। গতি ও স্থিতিশীলতা একসাথে উন্নত করা সম্ভব।
- Metric উন্নতির আয়না — শাস্তির হাতিয়ার নয়।

## 19. Completion checklist

- [ ] `dora_metrics.py` sample data দিয়ে চালিয়েছি এবং output দেখেছি
- [ ] অন্তত lead time ও change failure rate হাতে হিসাব করে মিলিয়েছি
- [ ] `python3 -m unittest -v` চালিয়ে সব test পাস দেখেছি
- [ ] Exercise ১ ও ২ শেষ করেছি (code পরিবর্তন + test)
- [ ] Mini-project: নিজের delivery process-এর document ও diagram লিখেছি
- [ ] Self-assessment-এর ৬টি প্রশ্নের উত্তর নিজের ভাষায় লিখেছি
- [ ] [00-orientation/PROGRESS.md](PROGRESS.md)-এ নিজের learner status আপডেট করেছি

## 20. Official documentation ও further reading

- DORA research program ও metric-এর বর্তমান সংজ্ঞা: https://dora.dev/ (checked: 2026-10-26)
- Google Site Reliability Engineering books (বিনামূল্যে অনলাইন): https://sre.google/books/
- Python `statistics` module: https://docs.python.org/3/library/statistics.html
- Python `csv` module: https://docs.python.org/3/library/csv.html
- বই (ঐচ্ছিক): *The Phoenix Project* (উপন্যাসের আকারে DevOps-এর গল্প), *The DevOps Handbook*, *Accelerate* (DORA গবেষণার পেছনের বিজ্ঞান)

---

**পরের lesson:** L00-02 — Engineering roles: DevOps, SRE, Platform, Cloud, Security, MLOps, AI Infra
