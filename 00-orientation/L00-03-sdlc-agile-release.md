# L00-03 — SDLC, Agile, Scrum, Kanban ও release management

| | |
|---|---|
| **Module** | 00 — Engineering Orientation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L00-02 — Engineering roles](L00-02-engineering-roles.md) |
| **Label** | — |
| **Tested** | Python code: Python 3.14-এ ৭টি test পাস। Ubuntu-তে চালানো হয়নি (শুধু standard library)। |

---

## 1. এই lesson-এ যা শিখবেন

- **SDLC** (Software Development Life Cycle) — software তৈরির ধাপগুলো।
- **Waterfall** বনাম **Agile** — কেন পরিবর্তন এলো।
- **Scrum** (sprint-ভিত্তিক) ও **Kanban** (প্রবাহ-ভিত্তিক) — কীভাবে কাজ করে, কখন কোনটি।
- Flow metric: **cycle time, throughput, WIP** এবং **Little's Law**।
- **Release management:** versioning (SemVer), release ও deploy-এর পার্থক্য, release train, feature flag, changelog।
- Python দিয়ে একটি team-এর flow metric হিসাব করা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Software তৈরি একটি জটিল কাজ: অনেক মানুষ, বদলানো চাহিদা, অনিশ্চয়তা। কোনো পদ্ধতি না থাকলে:

- কেউ জানে না কে কী করছে, কোনটা আগে।
- একসাথে অনেক কাজ শুরু হয়, কোনোটাই শেষ হয় না।
- Customer যা চেয়েছিলেন আর যা পেলেন তা মেলে না — জানা যায় মাস পরে।
- Release কবে হবে কেউ বলতে পারে না; হলে কী গেল তারও হিসাব থাকে না।

SDLC, Agile পদ্ধতি ও release management এই বিশৃঙ্খলাকে **পূর্বানুমেয় প্রক্রিয়ায়** রূপ দেয়। DevOps engineer হিসেবে আপনার pipeline, environment ও release automation এই প্রক্রিয়ারই অংশ — তাই process না বুঝলে automation ভুল জায়গায় করবেন।

## 3. সহজ ভাষায় পরিচয়

### SDLC কী?

Software-এর জীবনচক্রের ধাপ:

```text
Requirement → Design → Implementation (code) → Testing → Deployment → Maintenance/Operations
   (কী চাই)   (কীভাবে)      (বানানো)           (যাচাই)     (চালু করা)      (চালানো ও উন্নতি)
```

প্রতিটি পদ্ধতি (Waterfall, Agile) এই একই ধাপগুলো ব্যবহার করে — পার্থক্য হলো **কতবার ও কত বড় আকারে** এই চক্র ঘোরে।

### Waterfall

প্রতিটি ধাপ একবারে, পুরোপুরি শেষ করে পরের ধাপে যাওয়া। যেমন ৬ মাস requirement ও design, ৬ মাস coding, ৩ মাস testing, তারপর release।

- **কখন ভালো:** চাহিদা খুব স্থির ও আগে থেকে জানা, পরিবর্তন খুব ব্যয়বহুল (যেমন কিছু hardware বা নিয়ন্ত্রিত শিল্প)।
- **সমস্যা:** customer প্রথম কাজ করা software দেখেন এক বছরেরও বেশি পরে। ততদিনে চাহিদা বদলে গেছে, ভুল বোঝাবুঝি দেরিতে ধরা পড়ে।

### Agile

২০০১ সালের **Agile Manifesto**-র মূল কথা — ছোট ছোট অংশে কাজ, ঘন ঘন কাজ করা software দেখানো, পরিবর্তনকে স্বাগত জানানো। Manifesto-র চারটি মূল্যবোধ (সংক্ষেপে বাংলায়):

1. Process ও tool-এর চেয়ে **মানুষ ও তাদের পারস্পরিক যোগাযোগ** বেশি গুরুত্বপূর্ণ।
2. বিশাল documentation-এর চেয়ে **কাজ করা software** বেশি গুরুত্বপূর্ণ।
3. চুক্তি নিয়ে দর-কষাকষির চেয়ে **customer-এর সাথে সহযোগিতা** বেশি গুরুত্বপূর্ণ।
4. পরিকল্পনা আঁকড়ে থাকার চেয়ে **পরিবর্তনে সাড়া দেওয়া** বেশি গুরুত্বপূর্ণ।

Manifesto নিজেই বলে: ডান দিকের জিনিসগুলোরও মূল্য আছে, তবে বাম দিকের জিনিসগুলোকে বেশি মূল্য দেওয়া হয়। অর্থাৎ Agile মানে "documentation নেই" নয়।

### Agile ও DevOps-এর সম্পর্ক

Agile development team-কে ছোট অংশে দ্রুত software **তৈরি** করতে শেখালো। কিন্তু তৈরি software production-এ **পৌঁছাতে** তখনো মাস লাগত — Ops-এর দেয়াল ছিল। **DevOps সেই Agile-এর চেতনাকে deployment ও operations পর্যন্ত বাড়িয়ে দিল।** তাই DevOps ছাড়া Agile অর্ধেক কাজ।

### Scrum

Agile-এর সবচেয়ে প্রচলিত একটি framework। কাজ হয় নির্দিষ্ট দৈর্ঘ্যের **sprint**-এ (সাধারণত ১–৪ সপ্তাহ, বেশিরভাগ ২ সপ্তাহ)।

- **Role:** Product Owner (কী বানাতে হবে, অগ্রাধিকার), Scrum Master (process সহজ করা, বাধা দূর করা), Developers (বানানো — tester, ops সহ সবাই)।
- **Event:** Sprint Planning → Daily Scrum (১৫ মিনিট) → Sprint Review (কাজ দেখানো) → Sprint Retrospective (process উন্নতি)।
- **Artifact:** Product Backlog (সব কাজের অগ্রাধিকার তালিকা), Sprint Backlog (এই sprint-এর কাজ), Increment (sprint শেষে ব্যবহারযোগ্য অংশ)।

### Kanban

কোনো নির্দিষ্ট sprint নেই। কাজ একটি board-এ ধারাবাহিকভাবে প্রবাহিত হয়। মূল নিয়ম:

1. **কাজ দৃশ্যমান করা** (board: To do → In progress → Review → Done)।
2. **WIP (Work In Progress) সীমা** — একটি column-এ একসাথে সর্বোচ্চ কতটি কাজ থাকতে পারবে।
3. **Flow মাপা ও উন্নত করা** — cycle time, throughput।

**কখন Kanban:** কাজ অনিয়মিত আসে ও অগ্রাধিকার দ্রুত বদলায় — যেমন operations, support, platform team, SRE। এজন্য DevOps/SRE team-এ Kanban খুব প্রচলিত।

### এটি না থাকলে কী সমস্যা হতো?

"সবাই সব কাজ একসাথে শুরু করে" — ফলে কোনো কাজ শেষ হয় না, context switching-এ সময় নষ্ট হয়, আর কেউ বলতে পারে না কোন কাজ কবে শেষ হবে।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### WIP limit — রেস্টুরেন্টের রান্নাঘর

একজন রাঁধুনি একসাথে ১০টি order শুরু করলেন। সবগুলো চুলায় আধা-রান্না, কোনোটাই পরিবেশন হচ্ছে না, কিছু পুড়ে যাচ্ছে। যদি তিনি একসাথে মাত্র ৩টি রান্না করতেন (WIP limit = ৩), প্রতিটি দ্রুত শেষ হতো এবং customer আগে খাবার পেতেন — যদিও শুনতে মনে হয় "কম কাজ করছেন"।

**মূল শিক্ষা:** কাজ **শুরু** করা নয়, কাজ **শেষ** করাই মূল্য দেয়। "Stop starting, start finishing."

### Sprint — সাপ্তাহিক বাজারের তালিকা

প্রতি দুই সপ্তাহে একবার বসে ঠিক করা হয় এই সময়ে কী কী করা হবে (sprint planning), শেষে দেখা হয় কী হলো (review) এবং পরেরবার কীভাবে আরো ভালো করা যায় (retrospective)।

### Analogy কোথায় মেলে না

- রান্নার সময় মোটামুটি নির্দিষ্ট (ভাত ২০ মিনিট)। Software-এর কাজের সময় **অনেক বেশি অনিশ্চিত** — একটি "ছোট" bug কখনো ১০ মিনিট, কখনো ৩ দিন। এজন্য আমরা গড়ের বদলে **percentile** (যেমন "৮৫% কাজ ১০ দিনের মধ্যে") দিয়ে পূর্বাভাস দিই।
- রান্নাঘরে একটি খাবার শেষ মানে শেষ। Software-এ কাজ "Done" হলেও production-এ গিয়ে নতুন সমস্যা তৈরি করতে পারে — তাই "Done" এর সংজ্ঞায় test ও deploy অন্তর্ভুক্ত থাকা উচিত।

## 5. Real-world engineering scenario — Platform team-এর জ্যাম

**পরিস্থিতি:** একটি ৫ জনের platform team। Developer-রা অভিযোগ করছেন: "নতুন database চাইলে ৩ সপ্তাহ লাগে।"

**তদন্ত (data দিয়ে):**

1. Team-এর board-এ ২৫টি কাজ "In progress" — প্রতি জনে গড়ে ৫টি।
2. গত মাসে শেষ হয়েছে ২০টি কাজ (throughput ≈ ০.৬৭/দিন, ৩০ দিনে)।
3. **Little's Law** দিয়ে গড় cycle time = WIP ÷ throughput = ২৫ ÷ ০.৬৭ ≈ **৩৭ দিন**। Developer-দের অভিযোগ data দিয়ে নিশ্চিত হলো।

**সমাধান:**

- WIP limit চালু: In progress-এ সর্বোচ্চ ১০টি।
- Throughput একই থাকলে নতুন cycle time ≈ ১০ ÷ ০.৬৭ ≈ **১৫ দিন** — শুধু কম কাজ একসাথে করে।
- বারবার আসা অনুরোধ (নতুন database) automate করে self-service করা (Platform engineering, Module 16)।

**কী ভুল হতে পারে:** WIP limit মানতে গিয়ে জরুরি incident কাজও আটকে গেলে — তাই আলাদা "expedite" lane রাখা হয়, যেখানে সীমা আলাদা।

**Engineer কীভাবে diagnose করবেন:** অনুভূতি নয়, data — board-এর ইতিহাস থেকে প্রতিটি কাজের শুরু ও শেষ তারিখ নিয়ে cycle time ও WIP হিসাব (ঠিক এই lesson-এর script যা করে)।

## 6. Diagram

### Scrum cycle

```text
 Product Backlog ──► Sprint Planning ──► Sprint Backlog
       ▲                                     │
       │                                     ▼
       │                         ┌─── Sprint (১–৪ সপ্তাহ) ───┐
       │                         │  Daily Scrum (প্রতিদিন)    │
       │                         └────────────┬───────────────┘
       │                                      ▼
       └──── Retrospective ◄──── Sprint Review ◄──── Increment (ব্যবহারযোগ্য)
```

### Kanban board ও flow

```text
 ┌──────────┬───────────────┬──────────────┬──────────────┬────────┐
 │  To do   │ In progress   │   Review     │  Deploying   │  Done  │
 │          │  (WIP ≤ 3)    │  (WIP ≤ 2)   │  (WIP ≤ 1)   │        │
 ├──────────┼───────────────┼──────────────┼──────────────┼────────┤
 │ W-14     │ W-11          │ W-12         │ W-10         │ W-01…  │
 │ W-15     │ W-13          │              │              │        │
 │ W-16     │               │              │              │        │
 └──────────┴───────────────┴──────────────┴──────────────┴────────┘
             │◄──────────────── cycle time ────────────────►│
```

**Cycle time** = কাজ "In progress"-এ ঢোকা থেকে "Done" পর্যন্ত। **Lead time** (L00-01-এর DORA lead time থেকে আলাদা অর্থে, Kanban-এ) = অনুরোধ আসা থেকে Done পর্যন্ত। একই শব্দ ভিন্ন context-এ ভিন্ন অর্থ — সবসময় সংজ্ঞা স্পষ্ট করুন।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| SDLC | Software তৈরি থেকে চালানো পর্যন্ত জীবনচক্রের ধাপ |
| Iteration | চক্রের একবার পুরো ঘোরা — ছোট অংশে requirement থেকে কাজ করা software |
| Sprint | Scrum-এ নির্দিষ্ট দৈর্ঘ্যের iteration |
| Backlog | অগ্রাধিকার অনুযায়ী সাজানো ভবিষ্যৎ কাজের তালিকা |
| User story | User-এর দৃষ্টিতে চাহিদা: "একজন \<user\> হিসেবে আমি \<কাজ\> চাই, যাতে \<লাভ\>" |
| Definition of Done (DoD) | কাজ কখন "শেষ" ধরা হবে তার চুক্তি (যেমন: test পাস, review, staging-এ deploy) |
| WIP (Work In Progress) | শুরু হয়েছে কিন্তু শেষ হয়নি এমন কাজের সংখ্যা |
| WIP limit | একসাথে সর্বোচ্চ কতটি কাজ চলতে পারবে |
| Cycle time | একটি কাজ শুরু থেকে শেষ হতে কত সময় |
| Throughput | নির্দিষ্ট সময়ে কতগুলো কাজ শেষ হয় |
| Percentile (p85) | সাজানো মানের মধ্যে যে মানের নিচে ৮৫% পড়ে |
| Release | নতুন version বা feature user-এর জন্য উন্মুক্ত করা |
| SemVer | `MAJOR.MINOR.PATCH` version নম্বরের নিয়ম |
| Feature flag | Code deploy হয়ে আছে কিন্তু feature চালু/বন্ধ করা যায় configuration দিয়ে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Little's Law — flow-এর মৌলিক সূত্র

Queueing theory-র একটি সূত্র (John Little, ১৯৬১):

```text
গড় WIP = Throughput × গড় Cycle time
```

- **গড় WIP:** গড়ে কতটি কাজ একসাথে চলছে।
- **Throughput:** প্রতি দিনে কতটি কাজ শেষ হয়।
- **গড় Cycle time:** একটি কাজ গড়ে কত দিন লাগে।

সাজিয়ে লিখলে: `গড় Cycle time = গড় WIP ÷ Throughput`

**উদাহরণ:** WIP = ৬, throughput = ২ কাজ/দিন → cycle time = ৬ ÷ ২ = ৩ দিন। Throughput না বদলে WIP ৩-এ নামালে cycle time = ৩ ÷ ২ = ১.৫ দিন।

**শর্ত:** সূত্রটি একটি **স্থিতিশীল system**-এ দীর্ঘ সময়ের গড়ে খাটে — যেখানে কাজ ঢোকা ও বের হওয়ার হার মোটামুটি সমান, এবং শুরু হওয়া কাজ ফেলে রাখা হয় না। ছোট সময় বা অস্থির system-এ হিসাব ও মাপা মান কিছুটা আলাদা হবে (practical-এ দেখবেন)।

**কেন DevOps-এ গুরুত্বপূর্ণ:** একই সূত্র server-এও খাটে! একটি web server-এ গড়ে চলমান request = request rate × গড় response time। যেমন ২০০ request/সেকেন্ড × ০.০৫ সেকেন্ড = গড়ে ১০টি request একসাথে চলছে। Module 18 (capacity planning)-এ এটি আবার আসবে।

### 8.2 কেন গড়ের বদলে percentile দিয়ে পূর্বাভাস

Cycle time-এর বণ্টন সাধারণত **skewed** — বেশিরভাগ কাজ দ্রুত, কিছু খুব ধীর। কেউ জিজ্ঞেস করলেন "এই কাজ কবে শেষ হবে?" — গড় বললে প্রায় অর্ধেক সময় ভুল হবেন। p85 বললে: "৮৫% সম্ভাবনায় X দিনের মধ্যে।" এটি সৎ ও কার্যকর পূর্বাভাস।

**Nearest-rank percentile হিসাবের পদ্ধতি:**

1. মানগুলো ছোট থেকে বড় সাজান।
2. Rank = ⌈p ÷ 100 × n⌉ (⌈ ⌉ মানে উপরের দিকে পূর্ণসংখ্যা)।
3. সেই rank-এর মানই percentile।

অন্য পদ্ধতিও আছে (যেমন interpolation), যেগুলো সামান্য ভিন্ন ফল দেয়। Tool ব্যবহারের সময় কোন পদ্ধতি তা জানা দরকার।

### 8.3 Release management

**Deploy বনাম Release:**

| | Deploy | Release |
|---|---|---|
| কী | নতুন code production server-এ চালু | Feature user-এর জন্য উন্মুক্ত |
| কে নিয়ন্ত্রণ করে | Engineering (pipeline) | Product/business সিদ্ধান্ত |
| আলাদা করার উপায় | — | Feature flag, gradual rollout |

দুটো আলাদা করলে দিনে বহুবার নিরাপদে deploy করা যায়, আর feature চালু হয় যখন business প্রস্তুত।

**Semantic Versioning (SemVer) — `MAJOR.MINOR.PATCH`:**

| অংশ | কখন বাড়বে | উদাহরণ |
|---|---|---|
| MAJOR | পুরোনো ব্যবহারকারীর জন্য ভাঙনশীল পরিবর্তন (breaking change) | 1.4.2 → **2.0.0** (API-র field মুছে ফেলা) |
| MINOR | নতুন feature, পুরোনো ব্যবহার অক্ষত | 1.4.2 → **1.5.0** |
| PATCH | শুধু bug fix | 1.4.2 → **1.4.3** |

`0.y.z` version মানে প্রাথমিক উন্নয়ন — তখন যেকোনো পরিবর্তন হতে পারে। Pre-release: `2.0.0-rc.1`।

**Release-এর ধরন:**

- **Continuous release:** প্রতিটি merge-ই production-এ (web service-এ প্রচলিত)।
- **Release train:** নির্দিষ্ট সময়ে (যেমন প্রতি বৃহস্পতিবার) যা প্রস্তুত তা যায় — mobile app-এ প্রচলিত, কারণ app store review লাগে।
- **Hotfix:** জরুরি fix নির্ধারিত সময়ের বাইরে।

**Release-এর আনুষঙ্গিক:** Changelog (কী বদলালো — এই repository-র [CHANGELOG.md](../CHANGELOG.md) দেখুন), Git tag (`v1.5.0`), release notes, rollback plan, এবং কোন environment-এ কোন version চলছে তার রেকর্ড (L00-04)।

## 9. Practical demonstration — team-এর flow metric

### ধাপ ১ — Data

File: [`code/L00-03/work_items.csv`](code/L00-03/work_items.csv) — একটি কাল্পনিক platform team-এর সেপ্টেম্বর মাসের ১৩টি কাজ।

```bash
cat 00-orientation/code/L00-03/work_items.csv
```

| Column | অর্থ |
|---|---|
| `item_id` | কাজের ID |
| `type` | feature / bug / chore |
| `started` | কাজ শুরু (In progress-এ ঢোকা) |
| `done` | শেষ; খালি = এখনো চলছে |

বাস্তবে এই data আসে Jira, GitHub Projects বা অন্য board tool-এর export থেকে।

### ধাপ ২ — Script চালান

```bash
python3 00-orientation/code/L00-03/flow_metrics.py 00-orientation/code/L00-03/work_items.csv
```

শুধু CSV পড়ে ও হিসাব দেখায়; কিছু লেখে না।

**এই repository-তে চালিয়ে পাওয়া আসল output:**

```text
Period                 : 2026-09-01 → 2026-09-30 (30 days)
Finished items         : 12   (still open: 1)
Throughput             : 0.4 items/day
Cycle time avg / p50   : 4.83 / 3 days
Cycle time p85         : 10 days  (৮৫% কাজ এর মধ্যে শেষ হয়)
Average WIP (measured) : 2.03
Little's Law WIP       : 1.93  (= throughput × avg cycle time)
```

নির্দিষ্ট সময়সীমা:

```bash
python3 00-orientation/code/L00-03/flow_metrics.py 00-orientation/code/L00-03/work_items.csv \
    --start 2026-09-01 --end 2026-09-15
```

### ধাপ ৩ — হাতে যাচাই

**Cycle time** (`done − started + 1`, একই দিনে শেষ = ১ দিন):

| Item | started → done | দিন |
|---|---|---|
| W-01 | 1 → 4 | 4 |
| W-02 | 1 → 1 | 1 |
| W-03 | 2 → 9 | 8 |
| W-04 | 3 → 4 | 2 |
| W-05 | 7 → 8 | 2 |
| W-06 | 8 → 18 | 11 |
| W-07 | 10 → 14 | 5 |
| W-08 | 14 → 14 | 1 |
| W-09 | 15 → 17 | 3 |
| W-10 | 16 → 25 | 10 |
| W-11 | 21 → 22 | 2 |
| W-12 | 22 → 30 | 9 |

যোগফল = 58, গড় = 58 ÷ 12 = **4.83** ✔

সাজানো: 1, 1, 2, 2, 2, **3**, 4, 5, 8, 9, **10**, 11

- p50: rank = ⌈0.50 × 12⌉ = 6 → **3** ✔
- p85: rank = ⌈0.85 × 12⌉ = ⌈10.2⌉ = 11 → **10** ✔

লক্ষ্য করুন: গড় (4.83) p50 (3)-এর চেয়ে বেশি — কয়েকটি দীর্ঘ কাজ (W-06, W-10) গড়কে টেনে তুলেছে। এটাই skewed বণ্টন।

**Throughput** = 12 কাজ ÷ 30 দিন = **0.4/দিন** ✔

**মাপা গড় WIP:** প্রতিদিন কতটি কাজ চলছিল তার গড়। সব শেষ হওয়া কাজের মোট "চলমান-দিন" = cycle time-এর যোগফল = 58। এর সাথে W-13 (২৮ থেকে চলছে) সেপ্টেম্বরের ২৮, ২৯, ৩০ — ৩ দিন। মোট 61 ÷ 30 = **2.03** ✔

**Little's Law:** 0.4 × 4.833 = **1.93**। মাপা মান 2.03। পার্থক্য কেন? কারণ মাসের শেষে W-13 শুরু হয়েছে কিন্তু শেষ হয়নি — system পুরোপুরি "স্থিতিশীল" নয় এবং সময়সীমা ছোট। তবু কাছাকাছি — সূত্রটি বাস্তব data-তে ভালো আনুমানিক হিসাব দেয়।

### ধাপ ৪ — Test

```bash
cd 00-orientation/code/L00-03
python3 -m unittest -v
```

[`test_flow_metrics.py`](code/L00-03/test_flow_metrics.py)-এর ৭টি test: একই দিনে শেষ = ১ দিন, খোলা কাজের cycle time নেই, ভুল তারিখ প্রত্যাখ্যান, percentile সঠিক, নির্দিষ্ট দিনের WIP, sample data-র সব metric, এবং ভুল input-এ exit code ২।

## 10. Code-এর ব্যাখ্যা

File: [`code/L00-03/flow_metrics.py`](code/L00-03/flow_metrics.py) · Python 3.10+ · Dependency: নেই

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `Item.cycle_days` (`@property`) | `done − started + 1` | একই দিনের কাজ ০ দিন দেখালে অর্থহীন; property হওয়ায় সবসময় data থেকে হিসাব হয়, আলাদা করে রাখতে হয় না |
| `date.fromisoformat()` | `"2026-09-01"` → date object | ISO তারিখ format; ভুল format হলে স্পষ্ট ValueError |
| `percentile()` | Nearest-rank পদ্ধতি | সহজে হাতে যাচাই করা যায়; সবসময় data-র একটি আসল মান ফেরত দেয় |
| `math.ceil()` | উপরের দিকে পূর্ণসংখ্যা | Nearest-rank সূত্রে ⌈ ⌉ |
| `wip_on()` | নির্দিষ্ট দিনে চলমান কাজ গণনা | শুরু ≤ দিন এবং (খোলা বা শেষ ≥ দিন) |
| `flow_metrics()` | প্রতিদিনের WIP-এর গড় নেয় | এটি **মাপা** WIP; Little's Law-এর **হিসাবকৃত** মানের সাথে তুলনা করতে |
| `type=date.fromisoformat` (argparse) | `--start`-এর মান সরাসরি date-এ রূপান্তর | ভুল তারিখ দিলে argparse নিজেই error দেয় |
| `raise ValueError("no items finished...")` | সময়সীমায় কোনো কাজ শেষ না হলে | শূন্য দিয়ে ভাগ বা খালি তালিকার গড় এড়াতে, স্পষ্ট বার্তা দিতে |

## 11. প্রত্যাশিত ফল ও যাচাই

- Sample data দিয়ে উপরের output হুবহু আসবে।
- `python3 -m unittest -v` → `Ran 7 tests`, `OK`।
- সময়সীমায় কোনো কাজ শেষ না হলে:

```bash
python3 00-orientation/code/L00-03/flow_metrics.py 00-orientation/code/L00-03/work_items.csv --start 2030-01-01 --end 2030-01-31
echo "exit code: $?"
```

প্রত্যাশিত: `error: no items finished in the period` এবং `exit code: 2`।

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `Invalid isoformat string` | তারিখ `01/09/2026` format-এ | Error-এ মানটি দেখুন | `YYYY-MM-DD` ব্যবহার করুন |
| `done is before started` | তারিখ উল্টো লেখা | সেই row দেখুন | ঠিক করুন |
| `KeyError: 'started'` | CSV header-এর নাম আলাদা | `head -1 file.csv` | Header `item_id,type,started,done` করুন |
| Little's Law ও মাপা WIP-এ বড় পার্থক্য | ছোট সময়সীমা, বা অনেক কাজ শুরু হয়ে ফেলে রাখা | খোলা কাজের সংখ্যা দেখুন | দীর্ঘ সময়সীমা নিন; পুরোনো খোলা কাজ বন্ধ বা বাতিল করুন |

### ধারণাগত সাধারণ ভুল

- **"Agile মানে পরিকল্পনা বা documentation নেই"** — ভুল। পরিকল্পনা ছোট পরিসরে ও ঘন ঘন হয়।
- **"Scrum করলেই Agile"** — daily meeting করে কিন্তু তিন মাসে একবার release হলে feedback loop বড়ই থেকে যায়।
- **Velocity/story point দিয়ে team তুলনা** — বিভিন্ন team-এর point-এর মাপ আলাদা; L00-01-এর Goodhart's law মনে রাখুন।
- **WIP limit "কম কাজ" মনে করা** — আসলে একই সময়ে বেশি কাজ **শেষ** হয়।
- **Deploy ও release গুলিয়ে ফেলা** — feature flag দিয়ে এদের আলাদা রাখা যায়।

## 13. Security, performance ও cost বিবেচনা

- **Security:** "Definition of Done"-এ security check (dependency scan, secret scan) রাখলে প্রতিটি কাজের সাথে স্বয়ংক্রিয় যাচাই হয়। Security fix-কে আলাদা "expedite" lane-এ রাখা যায়।
- **Release ও security:** SemVer-এ PATCH আপডেট নিরাপদ ধরা হয় — তাই অনেক tool স্বয়ংক্রিয়ভাবে patch আপডেট নেয়। কিন্তু library-র নির্মাতা নিয়ম না মানলে "patch"-এও ভাঙন আসতে পারে — তাই test অপরিহার্য।
- **Cost:** উচ্চ WIP মানে অনেক অর্ধেক-শেষ কাজ — এতে বিনিয়োগ হয়েছে কিন্তু কোনো মূল্য আসেনি। Cloud-এ অর্ধেক-শেষ experiment-এর resource চলতে থাকলে সরাসরি বিলও হয়।
- **এই script:** শুধু local CSV পড়ে; কোনো network বা system পরিবর্তন নেই।

## 14. Hands-on exercise

1. **WIP limit simulation:** `work_items.csv` copy করুন। W-06 ও W-10-এর `started` তারিখ এমনভাবে বদলান যেন তারা আগের কাজ শেষ হওয়ার পরে শুরু হয় (একসাথে কম কাজ)। Script চালিয়ে avg WIP ও cycle time কীভাবে বদলায় দেখুন।
2. **Type অনুযায়ী metric:** `flow_metrics.py`-তে `--type bug` option যোগ করুন যাতে শুধু নির্দিষ্ট type-এর কাজ হিসাব হয়। Bug আর feature-এর p85 তুলনা করুন। একটি test লিখুন।
3. **Little's Law হাতে:** একটি server-এ request rate ৫০/সেকেন্ড, গড় response time ২০০ms। গড়ে কতটি request একসাথে চলছে? Response time দ্বিগুণ হলে কী হবে? (একক মিলাতে ভুলবেন না — ms থেকে সেকেন্ড।)
4. **SemVer অনুশীলন:** version 2.3.7 থেকে নিচের প্রতিটি পরিবর্তনের পরে নতুন version কী হবে?
   (ক) একটি bug fix, (খ) নতুন optional API parameter, (গ) একটি API endpoint মুছে ফেলা, (ঘ) একসাথে একটি bug fix ও একটি নতুন feature।

## 15. Mini-project — নিজের personal Kanban

1. GitHub Projects (বা কাগজে) একটি board বানান: To do → In progress (WIP ≤ 2) → Done।
2. এই repository-র lesson-গুলোকে কাজ হিসেবে যোগ করুন।
3. প্রতিটি lesson-এর শুরু ও শেষের তারিখ `~/devops-notebook/my-work-items.csv`-এ একই format-এ রাখুন।
4. Module 01 শেষে `flow_metrics.py` চালিয়ে আপনার নিজের cycle time p85 বের করুন — এটি দিয়ে পরের module কতদিনে শেষ হবে তার সৎ পূর্বাভাস দিন।

## 16. Interview প্রশ্ন

1. Waterfall ও Agile-এর মূল পার্থক্য কী? Waterfall কোথায় এখনো যুক্তিসঙ্গত?
2. Agile ও DevOps-এর সম্পর্ক কী?
3. Scrum ও Kanban-এর পার্থক্য কী? একটি SRE team-এর জন্য কোনটি সুপারিশ করবেন, কেন?
4. WIP limit কেন throughput না বাড়িয়েও cycle time কমায়? Little's Law দিয়ে ব্যাখ্যা করুন।
5. Deploy ও release-এর পার্থক্য কী? Feature flag কীভাবে সাহায্য করে?
6. Semantic versioning-এ কখন MAJOR version বাড়াবেন?
7. "এই কাজ কবে শেষ হবে?" — কীভাবে data-ভিত্তিক উত্তর দেবেন?

## 17. Self-assessment প্রশ্ন

1. SDLC-এর ছয়টি ধাপ লিখুন। Waterfall ও Agile-এ এই ধাপগুলোর ব্যবহার কীভাবে আলাদা?
2. Agile Manifesto-র চারটি মূল্যবোধ নিজের ভাষায় লিখুন। কেন "documentation নেই" ব্যাখ্যাটি ভুল?
3. Sample data-য় গড় cycle time p50-এর চেয়ে বেশি কেন?
4. Little's Law-এর হিসাব (1.93) ও মাপা WIP (2.03) কেন একটু আলাদা?
5. রান্নাঘরের analogy কোথায় software কাজের সাথে মেলে না?
6. আপনার আগের WordPress project-গুলোতে কোন release পদ্ধতি ছিল (continuous, train, নাকি অনিয়মিত)? কোনটি ভালো হতো এবং কেন?

## 18. সংক্ষিপ্ত সারাংশ

- **SDLC** = requirement → design → code → test → deploy → operate। পদ্ধতির পার্থক্য হলো চক্র কত ছোট ও কত ঘন।
- **Waterfall** একবারে বড় ধাপে; **Agile** ছোট iteration-এ ঘন feedback। **DevOps** Agile-কে deployment ও operations পর্যন্ত বাড়ায়।
- **Scrum** = নির্দিষ্ট sprint, role ও event। **Kanban** = ধারাবাহিক প্রবাহ, WIP limit, flow metric — operations ও platform team-এ প্রচলিত।
- **Little's Law:** গড় WIP = throughput × গড় cycle time। কম WIP → দ্রুত cycle time।
- পূর্বাভাসে গড় নয়, **percentile** (p85)।
- **Release management:** deploy ≠ release; SemVer `MAJOR.MINOR.PATCH`; changelog, tag, rollback plan।

## 19. Completion checklist

- [ ] `flow_metrics.py` sample data দিয়ে চালিয়েছি
- [ ] Cycle time-এর গড়, p50 ও p85 হাতে হিসাব করে মিলিয়েছি
- [ ] Little's Law ও মাপা WIP-এর পার্থক্য ব্যাখ্যা করতে পারি
- [ ] `python3 -m unittest -v` চালিয়ে ৭টি test পাস দেখেছি
- [ ] Exercise ১, ৩ ও ৪ শেষ করেছি
- [ ] Personal Kanban board শুরু করেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট করেছি

## 20. Official documentation ও further reading

- Agile Manifesto: https://agilemanifesto.org/
- The Scrum Guide (official): https://scrumguides.org/
- Semantic Versioning 2.0.0: https://semver.org/
- Keep a Changelog: https://keepachangelog.com/
- Python `statistics` ও `datetime` module: https://docs.python.org/3/library/statistics.html · https://docs.python.org/3/library/datetime.html

---

**পরের lesson:** L00-04 — Environments: development, testing, staging, production
