# L07-06 — Cloud cost model, budget, tagging ও cleanup

| | |
|---|---|
| **Module** | 07 — Cloud Fundamentals |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L07-03 — Region/AZ](L07-03-regions-zones-fault-domains.md), [L07-04 — Networking](L07-04-public-private-networking.md) |
| **Label** | — |
| **Tested** | `cost_estimate.py` ও `tag_audit.py`: ৬টি test পাস (Python 3.14.5, Windows)। **সব দাম `example-prices.json`-এর — অনুশীলনের জন্য বানানো গোল সংখ্যা, কোনো provider-এর আসল দাম নয়।** Tool-টি প্রতিটি output-এ এই সতর্কতা দেখায়। Inventory হাতে তৈরি। কোনো cloud account, billing API বা resource ব্যবহার হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Cloud-এর বিলের অংশ: compute (ঘণ্টা/সেকেন্ড), storage (GB-মাস), data transfer (egress, AZ-এর মধ্যে), managed service, request।
- লুকানো খরচ: NAT-এর data processing, বন্ধ instance-এর disk, অনাথ volume ও IP, পুরোনো snapshot, log ingestion।
- Pricing model: on-demand, reserved/savings plan, spot — কখন কোনটা।
- **Budget ও alert:** forecast-ভিত্তিক, ধাপে ধাপে।
- **Tagging:** owner, env, cost-center, expires — কেন বাধ্যতামূলক।
- **Cleanup:** খোঁজা → মালিককে জিজ্ঞাসা → dry-run → মোছা।
- Lab শেষে resource মোছা — এই course-এর প্রতিটি cloud lab-এর নিয়ম।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Cloud-এ প্রতিটি API call টাকা খরচ করতে পারে, এবং বিল আসে মাসের শেষে। পরিচিত ঘটনা:

- শিক্ষার্থী lab শেষে একটি বড় instance মুছতে ভুলে গেলেন — এক মাস পরে বিল।
- Test-এর জন্য বানানো ৫০০ GB disk-এর instance "বন্ধ" করা হলো, মোছা হলো না — disk-এর বিল চলতেই থাকল।
- Production-এর চেয়ে dev ও CI-এর খরচ বেশি, কারণ সেগুলো রাতে ও সপ্তাহান্তেও চলে।
- ফাঁস হওয়া key দিয়ে কেউ অন্য region-এ GPU instance চালাল (L07-05) — budget alert না থাকায় জানা গেল বিল আসার পরে।

এই course-এর পরের module-গুলোতে (০৮ থেকে) আসল cloud ব্যবহার হবে। তার আগে খরচের মডেল, alert ও cleanup-এর অভ্যাস তৈরি হওয়া জরুরি।

## 3. সহজ ভাষায় পরিচয়

| খরচের ধরন | একক | উদাহরণ | প্রায়ই ভুলে যাওয়া হয় |
|---|---|---|---|
| Compute | instance-ঘণ্টা/সেকেন্ড | VM, managed DB | Dev/CI সারাক্ষণ চালু |
| Storage | GB-মাস | Disk, object storage, snapshot | বন্ধ instance-এর disk, পুরোনো snapshot |
| Data transfer | GB | Internet-এ egress, AZ/region-এর মধ্যে | NAT, AZ-এর মধ্যে replication |
| Managed component | ঘণ্টা + GB | NAT gateway, load balancer | ব্যবহার না থাকলেও ঘণ্টার চার্জ |
| Request/API | প্রতি মিলিয়ন | Object storage request, function call | — |
| IP address | ঘণ্টা | Public IPv4 | অনাথ IP |

**Pricing model:**

- **On-demand** — নমনীয়, সবচেয়ে দামি।
- **Commitment** (reserved/savings) — ১–৩ বছরের প্রতিশ্রুতিতে ছাড়, স্থির load-এর জন্য।
- **Spot/preemptible** — বড় ছাড়, কিন্তু যেকোনো সময় কেড়ে নেওয়া হতে পারে — stateless/batch কাজের জন্য।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### বিদ্যুৎ ও পানির বিল

- **On-demand** = মিটারে যত ব্যবহার, তত বিল।
- **Reserved** = বছরের চুক্তিতে কম দর — ব্যবহার না করলেও দিতে হয়।
- **Spot** = রাতের সস্তা বিদ্যুৎ, কিন্তু সরবরাহকারী চাইলে বন্ধ করে দেয়।
- **Tag** = প্রতিটি ঘরের আলাদা মিটার — কোন ঘর কত খরচ করছে।
- **Budget alert** = মাসের মাঝামাঝি "বিল এখনই গত মাসের ৮০%"-এর বার্তা।

### Analogy কোথায় মেলে না

- **সুইচ বন্ধ করলে মিটার থামে।** Cloud-এ instance "stop" করলে compute থামে, কিন্তু **disk, public IP ও snapshot-এর বিল চলতে থাকে**। নমুনা inventory-তে ৫০০ GB-এর একটি disk একটি বন্ধ instance-এ যুক্ত (Section 9.2)।
- **ঘরে কে আছে সবাই জানে।** Cloud account-এ resource বানানো এত সহজ যে কেউ জানেই না কোনটা কার। Tag ছাড়া resource (`i-mystery`, নাম "test-do-not-delete") কেউ মুছতে সাহস পায় না, এবং চিরকাল বিল চলে।
- **বিল মাসে একবার, অবাক হওয়ার কিছু নেই।** Cloud-এ খরচ মিনিটে বাড়তে পারে (চুরি-যাওয়া key, ভুল autoscaling loop)। আর billing data নিজেও কয়েক ঘণ্টা দেরিতে আসে — তাই alert আসে সমস্যা শুরুর পরে। Budget alert একটি জাল, প্রতিরোধ নয় (প্রতিরোধ: L07-05-এর IAM, অপ্রয়োজনীয় region বন্ধ)।

## 5. Real-world engineering scenario — "Production-এর চেয়ে dev বেশি খরচ করে"

**পরিস্থিতি:** TaskFlow-এর মাসিক বিল বাড়তেই থাকছে। Finance জানতে চাইল কেন। কোনো tag নেই, তাই কেউ বলতে পারল না কোন খরচ কিসের।

`cost_estimate.py` দিয়ে architecture-এর হিসাব (**উদাহরণ-দামে**, আসল output):

```text
⚠️  EXAMPLE PRICES ONLY — invented round numbers for practice, NOT any provider's real price. …
total per month: 717.25 USD (example)
by env: ci 243.60, dev 161.30, prod 312.35
largest line: ci-runner compute large-vm — 33% of the total
```

**Non-prod (CI ও dev) মোট খরচের ৫৬%।** সবচেয়ে বড় একক লাইন সারাক্ষণ চালু একটি বড় CI runner। Dev ও CI-কে কর্মদিবসে ১২ ঘণ্টা চালালে (`--schedule-dev 12x22`):

```text
total per month: 470.27 USD (example)   (non-prod scheduled 12x22)
by env: ci 94.48, dev 63.44, prod 312.35
```

মোট ৩৪% কম — production-এ কোনো পরিবর্তন ছাড়াই।

তারপর `tag_audit.py` আরও খুঁজে পেল:

- মেয়াদোত্তীর্ণ demo server;
- বন্ধ load-test instance-এর ৫০০ GB disk;
- একটি অনাথ ২০০ GB volume;
- একটি অব্যবহৃত public IP;
- এক বছরের পুরোনো ৩০০ GB snapshot।

**শিক্ষা:**

- খরচ বোঝার প্রথম ধাপ tag; দ্বিতীয় ধাপ "কোনটা সারাক্ষণ চলছে, অথচ দরকার নেই"।
- Production optimize করার আগে non-prod দেখুন — প্রায়ই সেখানে সহজ সঞ্চয়।

## 6. Diagram — খরচ নিয়ন্ত্রণের চক্র

```text
   ┌─────────── estimate (নকশার সময়) ───────────┐
   │ cost_estimate.py — আসল দাম pricing calculator থেকে │
   └──────────────┬─────────────────────────────┘
                  ▼
   tag সহ তৈরি (owner, env, cost-center, expires) ── IaC-এ বাধ্যতামূলক (Module 12)
                  ▼
   budget + alert: 50% · 80% · 100% · forecast 120%   (email/chat — L05-06-এর webhook)
                  ▼
   সাপ্তাহিক: tag_audit.py — missing tag · expired · unattached disk/IP · stopped-instance disk · old snapshot
                  ▼
   মালিককে জিজ্ঞাসা → snapshot/backup দরকার? → dry-run → মোছা → পরের মাসে বিলে যাচাই
                  └──────────────► আবার estimate (right-sizing, schedule, commitment)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| On-demand | ব্যবহার অনুযায়ী, কোনো প্রতিশ্রুতি নেই |
| Reserved / savings plan | ১–৩ বছরের প্রতিশ্রুতিতে ছাড় |
| Spot / preemptible | উদ্বৃত্ত capacity, বড় ছাড়, কেড়ে নেওয়া যায় |
| Egress | Cloud থেকে বাইরে (বা AZ/region-এর মধ্যে) data — চার্জযোগ্য |
| GB-month | এক মাস ধরে এক GB রাখার একক |
| Cost allocation tag | বিল ভাগ করার জন্য tag (চালু করতে হয়) |
| Budget / forecast | সীমা / মাস শেষে কত হবে তার অনুমান |
| Right-sizing | প্রয়োজনের মাপে instance বাছা |
| Orphaned resource | মালিক বা ব্যবহারহীন resource |
| FinOps | Engineering, finance ও business মিলে cloud খরচ পরিচালনা (Module 29) |
| TCO | মোট খরচ — বিল + মানুষের সময় + ঝুঁকি |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 মাসের ঘণ্টা

হিসাবে মাস = গড়ে ৭৩০ ঘণ্টা (৮৭৬০/১২) — অনেক provider-এর calculator-ও এটা ব্যবহার করে। ফেব্রুয়ারি ও ৩১ দিনের মাসে আসল বিল কিছুটা ভিন্ন হয়। Schedule (`12x22` = ২৬৪ ঘণ্টা) শুধু compute-এ প্রযোজ্য; disk প্রতি মাসে পুরো বিল (test-এ যাচাই)।

### 8.2 দামের উৎস

`example-prices.json` জেনেবুঝে বানানো গোল সংখ্যা। প্রতিটি output-এর প্রথম লাইনে সতর্কতা থাকে, এবং test নিশ্চিত করে সতর্কতা কখনো বাদ পড়ে না।

আসল হিসাবের জন্য:

- Provider-এর pricing page বা calculator থেকে **region, তারিখ ও উৎস-link সহ** দাম লিখুন।
- দাম region-ভেদে ও সময়ের সাথে বদলায়।
- নিজের কাজের প্রকৃত ব্যবহার (GB, ঘণ্টা) মাপুন, অনুমান নয়।

### 8.3 Budget alert

- Actual-ভিত্তিক alert ঘটনা ঘটার পরে আসে।
- **Forecast-ভিত্তিক** alert ("এই হারে মাস শেষে ১২০% হবে") আগে সতর্ক করে।
- একাধিক ধাপে রাখুন (৫০/৮০/১০০/১২০%), এবং পাঠান এমন channel-এ যা কেউ দেখে।

Billing data কয়েক ঘণ্টা দেরিতে আসে — real-time সুরক্ষা নয়।

### 8.4 Cleanup-এর নিয়ম

`tag_audit.py` **কিছুই মোছে না** — তালিকা দেয় (L05-03-এর নীতি)। মোছার আগে:

1. মালিককে (tag থেকে) জিজ্ঞাসা।
2. Data থাকলে snapshot বা backup।
3. Dry-run।
4. মোছা।
5. পরের বিলে যাচাই।

Tag-হীন resource-এর মালিক খুঁজতে audit log (কে বানিয়েছে) ব্যবহার করুন। প্রথমে "stop" করে কেউ চিৎকার করে কিনা দেখা ("scream test") — সতর্কতার সাথে।

> **Fedora-তে:** কোনো পার্থক্য নেই — ধারণাগত।

## 9. Practical demonstration

Files:

- [`code/L07-06/cost_estimate.py`](code/L07-06/cost_estimate.py), [`example-prices.json`](code/L07-06/example-prices.json) (**উদাহরণ দাম**), [`taskflow-arch.json`](code/L07-06/taskflow-arch.json)।
- [`tag_audit.py`](code/L07-06/tag_audit.py), [`inventory.json`](code/L07-06/inventory.json) (হাতে তৈরি)।
- [`test_l07_06.py`](code/L07-06/test_l07_06.py)।

### 9.1 খরচের হিসাব — আসল output (উদাহরণ-দামে)

```bash
cd ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-06
python3 cost_estimate.py taskflow-arch.json --prices example-prices.json
```

```text
⚠️  EXAMPLE PRICES ONLY — invented round numbers for practice, NOT any provider's real price. …
resource       env      item                             quantity unit                  cost
ci-runner      ci       compute large-vm                    730.0 instance-hours      233.60
dev-app        dev      compute medium-vm                  1460.0 instance-hours      116.80
db             prod     compute managed-db-small-multi-az   730.0 instance-hours       73.00
nat            prod     nat gateway hours                  1460.0 hours                65.70
app            prod     compute small-vm                   2920.0 instance-hours       58.40
…
app            prod     cross_az_gb                         100.0 GB                    1.00

total per month: 717.25 USD (example)
by env: ci 243.60, dev 161.30, prod 312.35
largest line: ci-runner compute large-vm — 33% of the total
budget alerts (forecast-based): 50% → 358.62 USD (example), 80% → 573.8 USD (example), 100% → 717.25 USD (example), 120% → 860.7 USD (example)
```

উদাহরণ-দামেও একটি গঠনগত শিক্ষা দেখা যায়:

- Production-এ দুটি NAT gateway-র শুধু ঘণ্টার চার্জ (৬৫.৭০) চারটি app server-এর compute-এর (৫৮.৪০) চেয়ে বেশি।
- NAT-এর data processing (৩৬.০০) যোগ করলে NAT সব মিলিয়ে ১০১.৭০।
- Multi-AZ-এর জন্য প্রতি AZ-এ NAT রাখা (L07-04) একটি সচেতন খরচ।

আসল দামে অনুপাত ভিন্ন হতে পারে — নিজে যাচাই করুন (exercise ১)।

### 9.2 Tag ও cleanup audit — আসল output

```bash
python3 tag_audit.py inventory.json --today 2026-10-28; echo "exit=$?"
```

```text
expired                  instance   i-demo-ana               expired 28 day(s) ago (owner: ana)
missing-tags             instance   i-mystery                owner, env, cost-center
stopped-instance-volume  volume     vol-loadtest-7           500 GB still billed while i-loadtest-7 is stopped
missing-tags             volume     vol-orphan-2025          owner, cost-center
unattached-volume        volume     vol-orphan-2025          200 GB billed, attached to nothing
idle-public-ip           public-ip  eip-old-demo             allocated but not associated (often billed)
bad-expires              snapshot   snap-before-migration    expires='next-month' is not YYYY-MM-DD
old-snapshot             snapshot   snap-before-migration    360 days old (300 GB)
11 resources, 8 finding(s): …
nothing was changed — review with the owners, then clean up (dry-run first)
exit=1
```

`expires='next-month'` — মানুষের লেখা আপেক্ষিক তারিখ কখনো "মেয়াদ পেরোয়" না। তাই tag-এর মান যন্ত্রে পড়ার যোগ্য format-এ রাখতে হয় (YYYY-MM-DD), এবং IaC বা policy দিয়ে বাধ্যতামূলক করতে হয়।

### 9.3 লেখার সময়

এই lesson-এর code-এ test নতুন কোনো bug পায়নি। Test-এ সীমারেখার একটি case (মেয়াদের দিনেই resource বৈধ, পরের দিন নয়) ও tag-এর নামের case (`Owner`/`owner`) যাচাই হয়।

### 9.4 Test

```bash
python3 -m unittest -v
```

৬টি test:

- নমুনার মোট (৭১৭.২৫) ও একটি VM-এর ৭৩০ ঘণ্টা।
- **Schedule compute বদলায়, storage নয়**; prod schedule হয় না।
- Schedule-এ ৩০%-এর বেশি সঞ্চয়; অজানা type।
- Budget alert; সতর্কতা সবসময় ছাপা হয়।
- Audit-এর আটটি finding।
- মেয়াদের সীমারেখা ও tag-এর case।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `HOURS_PER_MONTH = 730` | গড় মাস | Calculator-এর রীতি |
| `_warning` print | উদাহরণ-দামের সতর্কতা | বানানো সংখ্যা আসল বলে ভুল নয় |
| `--schedule-dev` শুধু non-prod compute | What-if | Storage বন্ধ হলেও বিল |
| `by env` | Environment-ভিত্তিক ভাগ | Tag-এর মূল্য |
| Forecast-ভিত্তিক alert | ধাপে ধাপে threshold | আগাম সতর্কতা |
| `tag_audit` — read-only | তালিকা, মোছা নয় | মালিকের সম্মতি ও dry-run |
| `expires` YYYY-MM-DD যাচাই | যন্ত্রে-পড়ার-যোগ্য tag | "next-month" কখনো মেয়াদোত্তীর্ণ হয় না |
| Stopped instance-এর volume | লুকানো খরচ | "বন্ধ = বিল নেই" ভুল |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `cost_estimate.py …` | ৭১৭.২৫ (উদাহরণ), প্রথম লাইনে সতর্কতা |
| `--schedule-dev 12x22` | ৪৭০.২৭ (উদাহরণ) |
| `tag_audit.py … --today 2026-10-28` | ৮টি finding, exit ১ |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | ফল | সমাধান |
|---|---|---|
| Lab শেষে resource মোছা হয়নি | মাসের বিল | প্রতিটি lab-এর cleanup checklist; `expires` tag |
| Instance stop = বিল শেষ ভাবা | Disk, IP, snapshot-এর বিল | Terminate + volume মোছা (backup-এর পরে) |
| Budget alert নেই | চুরি বা ভুল দেরিতে ধরা | প্রথম দিনেই budget (Module 08) |
| Tag ঐচ্ছিক | খরচ ভাগ করা যায় না, মালিক অজানা | IaC/policy দিয়ে বাধ্যতামূলক |
| সব কিছুতে reserved | ব্যবহার না হলেও বিল | স্থির load মেপে তারপর |
| Spot-এ database | কেড়ে নিলে data-র ঝুঁকি | শুধু stateless/batch |
| NAT দিয়ে বড় data | Processing চার্জ | Private endpoint (L07-04) |
| বানানো দামকে আসল ভাবা | ভুল সিদ্ধান্ত | Pricing calculator, region, তারিখ |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Budget alert চুরি-যাওয়া credential-এর একটি সংকেতও (হঠাৎ খরচ)।
  - অব্যবহৃত region বন্ধ রাখুন (SCP)।
  - অনাথ resource (পুরোনো snapshot-এ data, public IP) নিরাপত্তার ঝুঁকিও।
  - Cleanup-এর আগে data-র মালিকানা ও retention আইন দেখুন।
- **Performance:**
  - Right-sizing-এ খুব ছোট instance নিলে latency বাড়ে।
  - Spot কেড়ে নিলে capacity কমে।
  - খরচ কমানো ও SLO-র ভারসাম্য রাখুন (L07-03-এর downtime-এর দাম)।
- **Cost:**
  - প্রথমে tag ও visibility, তারপর সহজ জয় (schedule, অনাথ resource), তারপর right-sizing, শেষে commitment।
  - খরচ-সচেতনতা engineering সিদ্ধান্তের অংশ (Module 29)।

## 14. Hands-on exercise

1. একটি provider-এর pricing calculator থেকে `example-prices.json`-এর প্রতিটি দাম আসল মান দিয়ে বদলে `real-prices-<region>-<date>.json` বানান (link সহ)। মোট ও অনুপাত কতটা বদলায়? NAT কি এখনো app-এর চেয়ে বেশি?
2. `cost_estimate.py`-এ commitment যোগ করুন: `"commitment_discount": 0.3` থাকলে prod compute-এ ছাড়।
3. `tag_audit.py`-এ "সাপ্তাহিক report" যোগ করুন: owner অনুযায়ী দল করে Markdown, যাতে প্রত্যেককে তাদের অংশ পাঠানো যায়।
4. L07-03-এর তিনটি নকশার (single VM, same-AZ pair, multi-AZ) খরচ `cost_estimate.py`-এ হিসাব করুন। বছরে ১ ঘণ্টা downtime-এর দাম যদি X হয়, কোন X-এ multi-AZ লাভজনক?
5. নিজের একটি "cloud lab cleanup checklist" লিখুন — Module 08 থেকে প্রতিটি lab-এর শেষে ব্যবহারের জন্য।

## 15. Mini-project — Cost guardrails

- `estimate` (নকশার সময়) + `budget` (alert-এর threshold) + `audit` (সাপ্তাহিক) একটি command-এ: `cloud_guard.py`।
- Output একটি Markdown report:
  - এই মাসের forecast;
  - top ৫ খরচ;
  - tag-হীন resource;
  - cleanup-এর প্রার্থী ও আনুমানিক মাসিক সঞ্চয় (উদাহরণ-দামে)।

Module 08-এর আসল account-এ billing export-এর সাথে যুক্ত হবে, এবং Module 29-এর FinOps-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. Cloud বিলের প্রধান অংশগুলো কী? কোনগুলো প্রায়ই অপ্রত্যাশিত?
2. On-demand, reserved ও spot-এর পার্থক্য; কখন কোনটা?
3. Instance stop করলে কোন খরচ চলতে থাকে?
4. Tagging কেন গুরুত্বপূর্ণ? কোন tag বাধ্যতামূলক রাখবেন?
5. Budget alert কীভাবে configure করবেন? এর সীমা কী?
6. অনাথ resource নিরাপদে কীভাবে পরিষ্কার করবেন?

## 17. Self-assessment প্রশ্ন

1. বিদ্যুৎ-বিল analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ non-prod কেন production-এর চেয়ে বেশি খরচ করছিল?
3. Schedule করলে disk-এর খরচ কেন কমে না?
4. `expires='next-month'` কেন সমস্যা?
5. `example-prices.json`-এর সংখ্যা দিয়ে কোন সিদ্ধান্ত নেওয়া যায় না, এবং কেন?

## 18. সংক্ষিপ্ত সারাংশ

- বিল = compute + storage + data transfer + managed component + request।
- Stop ≠ বিল শেষ; অনাথ disk, IP, snapshot খুঁজুন।
- Tag (owner, env, cost-center, expires — YYYY-MM-DD) প্রথম দিন থেকে বাধ্যতামূলক।
- Forecast-ভিত্তিক budget alert, একাধিক ধাপে; কিন্তু এটা জাল, প্রতিরোধ নয়।
- Cleanup: খোঁজা → মালিক → backup → dry-run → মোছা; আসল দাম সবসময় pricing calculator থেকে।

## 19. Completion checklist

- [ ] TaskFlow-এর নকশার খরচ আসল দামে (link ও তারিখসহ) হিসাব করেছি
- [ ] নমুনা audit-এর প্রতিটি finding-এর cleanup পদক্ষেপ লিখেছি
- [ ] নিজের cloud lab cleanup checklist বানিয়েছি
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS Pricing Calculator: https://calculator.aws/
- AWS — Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- AWS — Cost allocation tags: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html
- Google Cloud Pricing Calculator: https://cloud.google.com/products/calculator
- Microsoft — Azure Pricing Calculator: https://azure.microsoft.com/en-us/pricing/calculator/
- FinOps Foundation — FinOps Framework: https://www.finops.org/framework/

---

**পরের lesson:** L08-01 — AWS account safety: root user, MFA, budget alert
