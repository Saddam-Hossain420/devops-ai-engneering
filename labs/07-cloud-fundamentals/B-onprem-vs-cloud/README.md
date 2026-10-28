# Lab 07-B — On-prem বনাম cloud architecture তুলনা

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ২–২.৫ ঘণ্টা |
| **Environment** | যেকোনো OS-এ Python 3 — সম্পূর্ণ offline |
| **Label** | — (কোনো cloud account বা resource নেই) |
| **Tested** | `check_b.py` Windows-এ (Python 3.14.5) যাচাই করা: ভুল সংখ্যা ও অসম্পূর্ণ `decision.md`-এ ৭টি FAIL; একটি reference folder-এ (repo-তে রাখা হয়নি) ALL PASS। **সব খরচ `example-prices.json`-এর উদাহরণ-দামে — আসল নয়।** Availability-র সংখ্যা আপনার অনুমান, কোনো provider-এর SLA নয়। |

## Objective

TaskFlow-কে একটি অফিসের server room-এ (on-prem) চালানো, না cloud-এ multi-AZ — দুটি নকশা **একই পদ্ধতিতে** তুলনা করে একটি লিখিত সিদ্ধান্ত নেওয়া:

- Availability: L07-03-এর `availability.py`।
- Cloud খরচ: L07-06-এর `cost_estimate.py`।
- On-prem খরচ: নিজের লেখা অনুমান (TCO)।

Checker সংখ্যাগুলো নিজে আবার হিসাব করে মেলায় — তাই সংখ্যা tool চালিয়েই পেতে হবে।

## Prerequisites

- [L07-02 — Shared responsibility](../../../07-cloud-fundamentals/L07-02-service-models-shared-responsibility.md)
- [L07-03 — Region/AZ/fault domain](../../../07-cloud-fundamentals/L07-03-regions-zones-fault-domains.md)
- [L07-04 — Networking](../../../07-cloud-fundamentals/L07-04-public-private-networking.md)
- [L07-06 — Cost](../../../07-cloud-fundamentals/L07-06-cost-budget-tagging-cleanup.md)

## Environment setup

```bash
mkdir -p ~/lab07b
cd ~/devops-ai-engineering/labs/07-cloud-fundamentals/B-onprem-vs-cloud
C=../../../07-cloud-fundamentals/code
```

File: [`check_b.py`](check_b.py)।

## Steps

1. **On-prem availability** — `~/lab07b/onprem-avail.json` (L07-03-এর spec format):
   - একটি server room = একটি fault domain। সব instance-এর `azs`-এ একই label দিন (যেমন `"room"`)।
   - `az_availability`-তে room-এর বিদ্যুৎ, cooling ও internet link মিলিয়ে নিজের অনুমান। কেন এই সংখ্যা, `decision.md`-তে লিখুন।
   - Tier: lb, app (২টি server), db।

2. **Cloud availability** — `~/lab07b/cloud-avail.json`:
   - কমপক্ষে দুটি AZ।
   - কোনো single point of failure নয় (`availability.py`-র `SPOF` লাইন যেন না আসে)।
   - L07-03-এর `two-az.json` দেখে নিজে লিখুন — copy নয়, নিজের tier ও সংখ্যা।

3. চালান এবং downtime (মিনিট/বছর) লিখে রাখুন:

   ```bash
   python3 $C/L07-03/availability.py ~/lab07b/onprem-avail.json ~/lab07b/cloud-avail.json --simulate 200000
   ```

   ছোট downtime-এর ক্ষেত্রে মিনিটে রূপান্তর: `(1 − availability) × 525960`।

4. **Cloud খরচ** — `~/lab07b/cloud-arch.json` (L07-06-এর format)। Prod-এর সাথে dev ও CI রাখুন, প্রতিটি resource-এ `env`। তারপর:

   ```bash
   python3 $C/L07-06/cost_estimate.py ~/lab07b/cloud-arch.json --prices $C/L07-06/example-prices.json
   ```

   চাইলে provider-এর pricing calculator থেকে নিজের `real-prices.json` বানান (region, তারিখ ও link সহ)। Checker-এ সেই file-ই দিন।

5. **On-prem খরচের অনুমান** — কমপক্ষে চারটি অংশ:
   - hardware-এর মাসিক ভাগ (কত বছরে amortise);
   - বিদ্যুৎ ও cooling;
   - network ও internet link;
   - মানুষের সময় (patch, hardware বদল, রাতের call);
   - offsite backup।

   প্রতিটির উৎস বা যুক্তি লিখুন। সংখ্যা বানাতে হলে স্পষ্ট লিখুন "অনুমান"।

6. **`~/lab07b/comparison.json`:**

   ```json
   {
     "prices_file": "example-prices.json (EXAMPLE, not real)",
     "cloud_monthly": 0,
     "cloud_downtime_min_per_year": 0,
     "onprem_downtime_min_per_year": 0,
     "onprem_monthly": 0,
     "onprem_assumptions": ["…", "…", "…", "…"],
     "decision": "cloud | onprem | hybrid"
   }
   ```

7. **`~/lab07b/decision.md`** — তিনটি heading হুবহু:
   - `## Decision` — কোনটা, কেন। Shared responsibility-র কোন দায়িত্ব কার কাছে যায় (L07-02)।
   - `## Risks` — বেছে নেওয়া নকশার ঝুঁকি (vendor lock-in, খরচ বাড়া, data residency, দক্ষতা)।
   - `## What would change my mind` — কোন সংখ্যা কতটা বদলালে সিদ্ধান্ত উল্টাবে।

   Example দাম ব্যবহার করলে স্পষ্ট লিখুন যে দামগুলো উদাহরণ — সিদ্ধান্ত চূড়ান্ত নয়।

8. যাচাই করুন (নিচে)।

## Expected behavior

- On-prem নকশায় `availability.py` SPOF দেখাবে (একটি room = সব tier-এর একই fault domain); cloud নকশায় দেখাবে না।
- Cloud-এর downtime কম হবে — কিন্তু খরচ বেশি হতে পারে। দুটো পাশাপাশি রেখে সিদ্ধান্ত নেওয়াই lab-এর উদ্দেশ্য; "cloud সবসময় ভালো" উত্তর নয়।

## Verification

```bash
python3 check_b.py ~/lab07b --prices $C/L07-06/example-prices.json; echo "exit=$?"
# ALL CHECKS PASSED, exit=0
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| `on-prem spec models one site` FAIL | `azs`-এ একাধিক label — একটি room-এর ভেতরের দুটি rack আলাদা AZ নয় (একই বিদ্যুৎ ও link) |
| `no single point of failure` FAIL | কোনো tier-এ একটি মাত্র instance, বা সব instance এক AZ-এ |
| `cloud_downtime … matches` FAIL | Availability থেকে মিনিটে রূপান্তরের ভুল, বা spec বদলে আবার চালানো হয়নি |
| `cloud_monthly … matches` FAIL | Checker-এ ও tool-এ ভিন্ন prices file, বা `--schedule-dev`-এর সংখ্যা লেখা হয়েছে (checker schedule-ছাড়া হিসাব করে) |
| `error: KeyError: "no price for type …"` | Arch-এর `type` prices file-এ নেই |
| `error: FileNotFoundError` | পাঁচটি file-এর কোনোটি নেই, বা নাম ভিন্ন |

## Cleanup / reset

কোনো resource তৈরি হয়নি। `~/lab07b/` notebook-এ রাখুন — Module 08-এ আসল দামে আবার হিসাব করবেন।

## Assessment

1. On-prem নকশায় দ্বিতীয় app server যোগ করলে downtime কতটা কমল? কেন খুব বেশি নয়?
2. Cloud খরচের কোন লাইন সবচেয়ে বড়? On-prem হিসাবে তার সমতুল্য কী?
3. On-prem-এর কোন খরচ সবচেয়ে বেশি ভুলে যাওয়া হয়? আপনার অনুমানে সবচেয়ে অনিশ্চিত কোনটা?
4. কোন ধরনের workload-এ on-prem বা hybrid যুক্তিসঙ্গত?
5. `decision.md`-এর "What would change my mind" থেকে একটি সংখ্যা বদলে দেখান যে সিদ্ধান্ত সত্যিই উল্টায়।
