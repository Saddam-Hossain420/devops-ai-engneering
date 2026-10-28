# Module 00 Quiz — Engineering Orientation

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৪৫ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর নিচের answer key দেখুন। Practical অংশের জন্য terminal লাগবে।

মোট নম্বর: ৫০ (Part A ১৫ + Part B ২০ + Part C ১৫)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. DevOps-কে সবচেয়ে সঠিকভাবে বর্ণনা করে কোনটি?
   (ক) Docker ও Kubernetes চালানোর job (খ) Dev ও Ops-কে একটি ভাগ করা, feedback-চালিত প্রক্রিয়া হিসেবে দেখা (গ) Ops team বাদ দেওয়া (ঘ) একটি CI tool
2. DORA-র কোন দুটি metric স্থিতিশীলতা মাপে?
3. Batch size বড় হলে deploy-এর ঝুঁকি কেন বাড়ে — এক বাক্যে।
4. CALMS-এর "M" কী?
5. SRE ও DevOps-এর সম্পর্ক এক বাক্যে।
6. Platform Engineer-এর "customer" কে?
7. MLOps engineer ও data scientist-এর দায়িত্বের মূল পার্থক্য কী?
8. Scrum-এর তিনটি role কী?
9. Kanban-এ WIP limit-এর উদ্দেশ্য কী?
10. SemVer-এ API থেকে একটি field মুছে ফেললে কোন অংশ বাড়বে?
11. Deploy ও release-এর পার্থক্য কী?
12. "Build once, deploy many" কেন গুরুত্বপূর্ণ?
13. C4 model-এর "container" কি Docker container? ব্যাখ্যা করুন।
14. ADR গৃহীত হওয়ার পরে সিদ্ধান্ত বদলালে কী করবেন?
15. VM snapshot কি backup? কেন?

## Part B — Calculation ও analysis (প্রতিটি ৪ নম্বর)

16. একটি team-এর ৮টি deploy-এর lead time (ঘণ্টা): 2, 30, 4, 5, 3, 48, 6, 4। Median ও average বের করুন। কোনটি report করবেন এবং কেন?
17. একটি team-এর গড় WIP ১২, throughput প্রতিদিন ২টি কাজ। গড় cycle time কত? WIP ৬-এ নামালে (throughput একই) কত হবে?
18. একটি page ৩০টি backend call করে, প্রতিটির ১% সম্ভাবনা ধীর হওয়ার। অন্তত একটি ধীর হওয়ার সম্ভাবনা কত? (0.99³⁰ ≈ 0.74)
19. Version 3.9.4-এ একটি bug fix ও একটি নতুন optional parameter একসাথে release হলো। নতুন version কী?
20. একটি latency experiment একবার চালিয়ে দেখা গেল নতুন configuration ৮ms দ্রুত। এই ফলে আস্থা রাখার আগে কী কী করবেন? (অন্তত তিনটি)

## Part C — Practical (terminal-এ করুন)

21. (৫ নম্বর) [`00-orientation/code/L00-04`](../../00-orientation/code/L00-04/envconfig.py)-এর `envconfig.py` ব্যবহার করে দেখান যে production-এ `APP_APP__LOG_LEVEL=debug` validation-এ FAIL করে। Command ও আসল output লিখুন। Password কীভাবে দিলেন যাতে history-তে না থাকে?
22. (৫ নম্বর) [`L00-06`-এর `incident_timeline.py`](../../00-orientation/code/L00-06/incident_timeline.py) দিয়ে [Lab C-এর log](../../labs/00-orientation/C-incident-analysis/incident.log) বিশ্লেষণ করে incident window ও সবচেয়ে বেশি আসা error লিখুন। Traffic spike কেন কারণ নয়, এক বাক্যে।
23. (৫ নম্বর) [`L00-05`-এর `adr.py`](../../00-orientation/code/L00-05/adr.py) দিয়ে একটি temporary directory-তে দুটি ADR তৈরি করে দ্বিতীয়টি দিয়ে প্রথমটি supersede করুন (মোট তিনটি ADR)। `list` ও `lint`-এর আসল output লিখুন।

---

<details>
<summary><strong>Answer key (নিজে উত্তর দেওয়ার পরে খুলুন)</strong></summary>

**Part A**

1. (খ)
2. Change failure rate ও failed deployment recovery time।
3. অনেক পরিবর্তন একসাথে গেলে অন্তত একটিতে সমস্যা থাকার সম্ভাবনা বেশি, এবং কোনটি দায়ী খুঁজতে সময় লাগে।
4. Measurement।
5. DevOps নীতি বলে কী করতে হবে (ভাগ করা দায়িত্ব, দ্রুত feedback); SRE তার একটি নির্দিষ্ট, মাপযোগ্য বাস্তবায়ন (SLO, error budget)।
6. প্রতিষ্ঠানের ভেতরের developer-রা।
7. Data scientist model তৈরি করেন; MLOps engineer সেটিকে reproducibly train, deploy, monitor ও rollback করার ব্যবস্থা তৈরি করেন।
8. Product Owner, Scrum Master, Developers।
9. একসাথে চলমান কাজ সীমিত রেখে কাজ দ্রুত শেষ করা (cycle time কমানো) এবং bottleneck দৃশ্যমান করা।
10. MAJOR (breaking change)।
11. Deploy = code production-এ চালু; release = feature user-এর জন্য উন্মুক্ত (feature flag দিয়ে আলাদা করা যায়)।
12. Staging-এ যা পরীক্ষিত, production-এ হুবহু তা-ই যায়; আলাদা build-এ পার্থক্য ঢুকতে পারে।
13. না। C4 container মানে চলমান অংশ বা data store (API, DB); সেটি Docker-এ চলতেও পারে, না-ও পারে।
14. নতুন ADR লিখে পুরোনোটিকে "Superseded by ADR-NNNN" করুন; পুরোনো text বদলাবেন না।
15. না। সাধারণত একই disk-এ থাকে; host disk নষ্ট হলে দুটোই যায়।

**Part B**

16. সাজানো: 2, 3, 4, 4, 5, 6, 30, 48। Median = (4+5)/2 = **4.5 ঘণ্টা**। Average = 102/8 = **12.75 ঘণ্টা**। Median report করুন — দুটি অস্বাভাবিক দীর্ঘ মান (30, 48) average-কে বিকৃত করেছে; সাথে p85/p95 দিলে tail-ও দেখা যায়।
17. Cycle time = WIP ÷ throughput = 12 ÷ 2 = **6 দিন**; WIP ৬ হলে 6 ÷ 2 = **3 দিন**।
18. 1 − 0.74 = **0.26 ≈ 26%**।
19. **3.10.0** (নতুন feature → MINOR বাড়ে, PATCH শূন্য হয়)।
20. যেকোনো তিনটি: একাধিকবার পুনরাবৃত্তি; warm-up বাদ; বড় sample; p50 ছাড়াও p95/p99 দেখা; একবারে একটি variable বদলানো নিশ্চিত করা; environment ও অন্য load লিখে রাখা; prediction আগে লেখা।

**Part C — গ্রহণযোগ্য উত্তরের মূল বৈশিষ্ট্য**

21. `read -rs -p ... APP_DATABASE__PASSWORD; export APP_DATABASE__PASSWORD`, তারপর `APP_APP__LOG_LEVEL=debug python3 envconfig.py validate prod` → `FAIL  app.log_level must not be debug in prod`, exit 1।
22. Window `09:09 → 09:11` (threshold 20%); শীর্ষ error "db connection pool exhausted" (১৭ বার)। Spike-এর মিনিটগুলোতে (০৯:০৫–০৯:০৭) request বেশি কিন্তু error ০%; error শুরু config পরিবর্তনের পরে এবং config ফেরত আনার পরে শেষ।
23. `list`-এ তিনটি ADR, যার একটির status `Superseded by ADR-000N`; `lint` → `3 ADR(s), 0 problem(s)`।

</details>
