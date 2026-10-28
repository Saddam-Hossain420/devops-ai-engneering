# L08-12 — Tagging, Cost Explorer ও resource cleanup automation

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L07-06 — Cost, budget, tagging](../07-cloud-fundamentals/L07-06-cost-budget-tagging-cleanup.md), [L08-02 — inventory.py](L08-02-aws-cli-profiles-temporary-credentials-boto3.md), L08-04 – L08-11-এর resource |
| **Label** | 💰 Cost Explorer API-র প্রতিটি request চার্জযোগ্য (console-এর দেখা নয়); tag ও Resource Groups Tagging API নিজে চার্জমুক্ত। **এই lesson-এর মূল উদ্দেশ্য খরচ বন্ধ করা** — cleanup শেষে কোনো চার্জযোগ্য resource থাকবে না |
| **Tested** | `cleanup_plan.py` ও `ce_report.py`: ৭টি test পাস (Python 3.14.5, Windows)। **তৈরি করা cleanup script একটি নকল `aws` command (প্রতিটি call log করে) দিয়ে Git Bash-এ আসলে চালানো হয়েছে** — dry-run-এ কোনো মোছার call নেই, ভুল account-এ থামে, মোছার ক্রম নির্ভরতা মানে, আগেই-মুছে-যাওয়া volume-এ থামে না। Input হাতে তৈরি; **Cost Explorer-এর সংখ্যা বানানো, কোনো আসল বিল নয়।** আসল AWS-এ চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Tagging-এর নিয়ম: কোন tag, কে দেবে, কীভাবে বাধ্যতামূলক করা যায়।
- Cost allocation tag চালু করা — এবং কেন আগের খরচে tag থাকে না।
- Cost Explorer: service ও tag অনুযায়ী খরচ; "EC2 - Other" আসলে কী।
- **Cleanup automation:** Resource Groups Tagging API → নির্ভরতার ক্রমে মোছা → যাচাই।
- নিরাপদ মোছার নীতি: dry-run ডিফল্ট, account guard, `prod`-এর মতো tag প্রত্যাখ্যান, idempotent।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Module 08-এ আপনি বানিয়েছেন: VPC, subnet, IGW, NAT, EIP, SG, EC2, volume, snapshot, ALB, target group, bucket, alarm, SNS, log group। হাতে মুছতে গেলে তিনটি ঘটনা প্রায় নিশ্চিত:

1. **ক্রম ভুল** — VPC মুছতে গেলে `DependencyViolation`, কারণ ENI বা SG আছে। হাল ছেড়ে দিলে অর্ধেক resource থেকে যায়।
2. **কিছু ভুলে যাওয়া** — বিশেষ করে NAT, EIP, snapshot, অন্য region।
3. **ভুল জিনিস মোছা** — ভুল account বা profile-এ (L08-02-এর ঘটনা)।

L07-06-এ নীতিটা শিখেছেন (খোঁজা → মালিক → dry-run → মোছা)। এখানে AWS-এ তার automation।

## 3. সহজ ভাষায় পরিচয়

| Tag | উদ্দেশ্য | উদাহরণ |
|---|---|---|
| `Project` | কোন কাজের অংশ — cleanup-এর চাবি | `lab08` |
| `Owner` | কাকে জিজ্ঞাসা করবেন | `ana` |
| `Environment` | prod/dev/lab — ঝুঁকির মাত্রা | `lab` |
| `CostCenter` | বিল কার খাতায় | `learning` |
| `Expires` | কবে মোছা যাবে (YYYY-MM-DD, L07-06) | `2026-11-30` |

| Tool | কী দেয় |
|---|---|
| Resource Groups Tagging API (`get-resources`) | একটি tag-এর সব (সমর্থিত) resource-এর ARN — region-প্রতি |
| Cost Explorer (`get-cost-and-usage`) | Service/tag অনুযায়ী খরচ, দিন বা মাস ধরে |
| Budgets (L08-01) | সীমা ও alert |
| `inventory.py` (L08-02) | কী চলছে — tag থাকুক বা না থাকুক |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### বাসা বদলের সময় বাক্সে লেবেল

- **Tag** = প্রতিটি বাক্সে "রান্নাঘর — রহিম — ভঙ্গুর"।
- **Cost Explorer** = মাস শেষে কোন ঘরের জিনিস সরাতে কত খরচ হলো।
- **Cleanup script** = লেবেল দেখে ঠিক ক্রমে খালি করা: আগে তাক থেকে জিনিস, তারপর তাক, শেষে আলমারি।

### Analogy কোথায় মেলে না

- **লেবেলহীন বাক্স চোখে পড়ে।** AWS-এ tag-হীন resource tag-ভিত্তিক cleanup-এ অদৃশ্য — সেটাই সবচেয়ে বেশি দিন বিল তোলে। তাই tag-এর পাশাপাশি `inventory.py`-এর মতো tag-নিরপেক্ষ তালিকা লাগে।
- **জিনিস সরালে খরচ শেষ।** কিছু resource-এর বিল মোছার পরেও খানিক আসে (আংশিক ঘণ্টা), আর Cost Explorer-এর data দেরিতে আসে। তাই যাচাই হলো `inventory.py`-এ শূন্য — বিলের জন্য পরের দিন অপেক্ষা করে নয়।
- **লেবেল পরে লাগালেও চলে।** Cost allocation tag চালু করার **আগের** খরচে সেই tag দেখা যায় না। প্রথম দিন থেকেই tag ও চালু।

## 5. Real-world engineering scenario — "Lab শেষ, বিল চলছে"

Module 08-এর lab শেষে একজন শিক্ষার্থী console-এ instance ও ALB মুছলেন। পরের মাসে Cost Explorer (হাতে তৈরি সংখ্যা, আসল বিল নয়; `ce_report.py`-এর আসল output):

```text
== by-service.json  [হাতে তৈরি — `aws ce get-cost-and-usage`-এর রূপে; সংখ্যাগুলো বানানো, কোনো আসল বিল বা দাম নয়]
period 2026-10-01: total 21.77 USD
       9.80   45.0%  EC2 - Other  (+717% vs 2026-09-01)
       5.00   23.0%  Amazon Elastic Compute Cloud - Compute  (+22% vs 2026-09-01)
       3.40   15.6%  Amazon Virtual Private Cloud  (new)
       2.60   11.9%  Elastic Load Balancing  (new)
       0.90    4.1%  AmazonCloudWatch  (+200% vs 2026-09-01)
== by-project.json  [হাতে তৈরি — …]
period 2026-10-01: total 21.77 USD
      13.40   61.6%  Project$lab08  (+163% vs 2026-09-01)
       8.37   38.4%  Project$  ← UNTAGGED  (+1422% vs 2026-09-01)
untagged: 8.37 USD = 38% of the period — find owners (tag_audit.py, inventory.py)
```

**পড়া:**

- **"EC2 - Other"** — instance-এর বাইরের EC2-সম্পর্কিত খরচ: EBS volume ও snapshot, NAT gateway, data transfer ইত্যাদি। Instance মুছলেও এগুলো থাকে।
- **VPC service-এর খরচ** — public IPv4 address (EIP সহ) এখানে আসে।
- **৩৮% untagged** — console-এ হাতে বানানো কিছু।

**সমাধান:** tag-ভিত্তিক cleanup (`cleanup_plan.py`), তারপর `inventory.py --all-regions` দিয়ে tag-হীন বাকিগুলো।

## 6. Diagram — cleanup pipeline

```text
 aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=lab08   (region-প্রতি)
        │ tagged.json (ARN + tag)
        ▼
 cleanup_plan.py --tag Project=lab08 --account 1111… --region ap-south-1
   guards: tag মান prod/main/shared নয় · প্রতিটি ARN-এ tag আছে · account/region মেলে
        │ cleanup.sh
        ▼
 bash cleanup.sh            → DRY-RUN: …   (শুধু describe/list)
 EXECUTE=yes bash cleanup.sh
   sts get-caller-identity == 1111… ? নইলে exit 2
   ALB → TG → EC2 (wait) → NAT (wait) → EIP → volume (না থাকলে skip) → snapshot
   → SG refs revoke → SG (retry) → IGW detach/delete → subnet (retry) → route table (main বাদ) → VPC (retry)
   → S3 (সব version) → alarm → SNS → log group
        ▼
 inventory.py --all-regions --summary  → শুধু প্রত্যাশিত (বা কিছুই না)
 manual: IAM role/instance profile, Route 53 zone, অজানা type
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Cost allocation tag | Billing-এ চালু করা tag — Cost Explorer-এ group করা যায় |
| AWS-generated tag | `aws:createdBy` ইত্যাদি — AWS নিজে দেয় (চালু করতে হয়) |
| Tag policy | Organizations-এ tag-এর নাম/মানের নিয়ম |
| `aws:RequestTag` condition | IAM/SCP-তে tag ছাড়া তৈরি আটকানো |
| Resource Groups Tagging API | Service-নিরপেক্ষ tag অনুসন্ধান |
| "EC2 - Other" | EBS, NAT, data transfer ইত্যাদি — instance-এর compute নয় |
| `DependencyViolation` | অন্য resource এখনো ব্যবহার করছে |
| Idempotent cleanup | বারবার চালালেও নিরাপদ; ইতিমধ্যে মোছা জিনিসে থামে না |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 নির্ভরতার ক্রম

VPC মোছা যায় শুধু তখন, যখন তার ভেতরে কোনো ENI, subnet, IGW বা non-default SG নেই। ENI তৈরি করে ALB, NAT ও EC2। তাই:

- আগে ওগুলো, এবং `wait` দিয়ে সত্যিই চলে যাওয়া পর্যন্ত অপেক্ষা।
- ALB বা NAT মোছার পরেও তাদের ENI কয়েক মিনিট থাকতে পারে — তাই subnet, SG ও VPC-তে `retry` (১৫ s × ১২)।

### 8.2 Security group-এর পারস্পরিক reference

`sg-alb` egress → `sg-app`, আর `sg-app` ingress ← `sg-alb`। একটিকে মুছতে গেলে অন্যটির rule আটকায়।

Script আগে **সবগুলোর** reference-যুক্ত rule revoke করে (`describe-security-group-rules` → `ReferencedGroupInfo`), তারপর মোছে। প্রথম সংস্করণে একটির revoke-এর পরেই তাকে মুছতে যেত — test-এর ক্রম-যাচাইয়ে ধরা পড়েছে।

### 8.3 নিরাপত্তার স্তর

| স্তর | কী আটকায় |
|---|---|
| Tag মান `prod`, `production`, `main`, `shared`… প্রত্যাখ্যান | ভুল tag দিয়ে বড় জিনিস মোছা |
| প্রতিটি ARN-এ সেই tag আছে কিনা | ভুল input file |
| ARN-এর account/region | অন্য জায়গার resource |
| Runtime-এ `sts get-caller-identity` | ভুল profile/credential (L08-02-এর ঘটনা) |
| ডিফল্ট dry-run | না পড়ে চালানো |
| Volume আছে কিনা আগে দেখা | `set -e`-এ অর্ধেক cleanup |

### 8.4 Tag বাধ্যতামূলক করা

- IAM বা SCP-তে `aws:RequestTag/Project` condition দিলে tag ছাড়া `RunInstances` ইত্যাদি deny হয়।
- `--tag-specifications` (L08-04–L08-06-এর script-গুলো) তৈরির মুহূর্তেই tag দেয়।
- Module 12-এ Terraform-এর `default_tags` একই কাজ করে।

> **Fedora-তে:** কোনো পার্থক্য নেই — bash ও AWS CLI।

## 9. Practical demonstration

Files:

- [`code/L08-12/cleanup_plan.py`](code/L08-12/cleanup_plan.py), [`ce_report.py`](code/L08-12/ce_report.py)
- [`sample/tagged.json`](code/L08-12/sample/tagged.json) (হাতে তৈরি ARN), [`sample/by-service.json`](code/L08-12/sample/by-service.json), [`sample/by-project.json`](code/L08-12/sample/by-project.json) (**বানানো সংখ্যা**)
- [`test_l08_12.py`](code/L08-12/test_l08_12.py)

### 9.1 Plan ও dry-run — আসল output (নকল `aws` দিয়ে চালানো)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-12
python3 cleanup_plan.py sample/tagged.json --tag Project=lab08 --account 111122223333 --region ap-south-1 > cleanup.sh
```

stderr:

```text
manual: arn:aws:ssm:ap-south-1:111122223333:parameter/lab08/db-password (no automatic rule)
```

Dry-run-এর শুরু (test-এর নকল `aws` দিয়ে চালানো):

```text
DRY-RUN: aws elbv2 delete-load-balancer --load-balancer-arn arn:aws:elasticloadbalancing:ap-south-1:111122223333:loadbalancer/app/lab08-alb/50dc6c495c0c9188
DRY-RUN: aws elbv2 wait load-balancers-deleted --load-balancer-arns …
DRY-RUN: aws elbv2 delete-target-group --target-group-arn …
DRY-RUN: aws ec2 terminate-instances --instance-ids i-app-a
DRY-RUN: aws ec2 wait instance-terminated --instance-ids i-app-a
DRY-RUN: aws ec2 delete-nat-gateway --nat-gateway-id nat-a
…
```

`EXECUTE=yes`-এ নকল `aws` যে call পেয়েছে, তার ক্রম (অংশ):

```text
ec2 revoke-security-group-ingress --group-id sg-alb --security-group-rule-ids sgr-in
ec2 revoke-security-group-egress --group-id sg-alb --security-group-rule-ids sgr-out
ec2 revoke-security-group-ingress --group-id sg-app --security-group-rule-ids sgr-in
ec2 revoke-security-group-egress --group-id sg-app --security-group-rule-ids sgr-out
ec2 delete-security-group --group-id sg-alb
ec2 delete-security-group --group-id sg-app
ec2 describe-internet-gateways --internet-gateway-ids igw-0lab --query …
ec2 detach-internet-gateway --internet-gateway-id igw-0lab --vpc-id vpc-0lab
ec2 delete-internet-gateway --internet-gateway-id igw-0lab
ec2 delete-subnet --subnet-id subnet-pub-a
ec2 delete-subnet --subnet-id subnet-app-a
…
ec2 delete-vpc --vpc-id vpc-0lab
```

Account না মিললে (`999999999999`) script একটিমাত্র call (`sts get-caller-identity`) করে থামে:

```text
refusing: credentials are for account 999999999999, plan is for 111122223333
```

### 9.2 Cost report — আসল output (বানানো সংখ্যায়)

```bash
python3 ce_report.py sample/by-service.json sample/by-project.json
```

Output Section 5-এ।

### 9.3 আপনার account-এ — Module 08-এর সমাপ্তি (চালানো হয়নি)

```bash
export AWS_PROFILE=learn-admin AWS_REGION=ap-south-1
ACCT=$(aws sts get-caller-identity --query Account --output text)
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=lab08 > tagged.json
python3 cleanup_plan.py tagged.json --tag Project=lab08 --account "$ACCT" --region "$AWS_REGION" > cleanup.sh
less cleanup.sh
bash cleanup.sh                       # dry-run — পড়ুন
EXECUTE=yes bash cleanup.sh           # মোছে
# manual: IAM (L08-03-এর ক্রম), Route 53 zone (L08-10), stderr-এর তালিকা
python3 ../L08-02/inventory.py --all-regions --summary      # লক্ষ্য: কোনো resource নেই
aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=lab08 \
  --query 'length(ResourceTagMappingList)'                    # 0 (tagging API কিছুক্ষণ পুরোনো ARN দেখাতে পারে)
```

Cost Explorer (প্রতিটি request চার্জযোগ্য — দিনে একবারই যথেষ্ট):

```bash
aws ce get-cost-and-usage --time-period Start=2026-10-01,End=2026-11-01 --granularity MONTHLY \
  --metrics UnblendedCost --group-by Type=DIMENSION,Key=SERVICE > by-service.json
python3 ce_report.py by-service.json
```

তারিখ নিজের মাসের দিন। Tag অনুযায়ী দেখতে আগে Billing console-এ `Project`-কে cost allocation tag হিসেবে চালু করুন।

### 9.4 লেখার সময়

- **Security group-এর ক্রম।** প্রথম সংস্করণ একটি SG-এর reference revoke করে সাথে সাথে তাকে মুছতে যেত। কিন্তু অন্য SG তখনো তাকে reference করছিল, তাই আসল AWS-এ `DependencyViolation`। এখন আগে সব revoke, তারপর সব delete (test: শেষ revoke < প্রথম delete)।
- **আগেই-মুছে-যাওয়া root volume।** Instance terminate হলে `DeleteOnTermination` volume নিজেই মুছে যায়। পুরোনো script তারপর `delete-volume`-এ `NotFound` পেয়ে `set -e`-এ থেমে যেত — VPC, bucket সব রয়ে যেত। এখন আগে দেখে।
  - প্রথম test এটা ধরতে পারেনি, কারণ নকল `aws`-এর `delete-volume` সফল হতো। নকলটিকে বাস্তবের মতো করার পরে পুরোনো code-এ script rc 254-এ থামে আর log group মোছা হয় না; নতুন code-এ পুরো cleanup শেষ হয়।
- **একটি অতি-নিশ্চিত দাবি নরম করা হয়েছে।** "Tagging API IAM role ও Route 53 zone দেয় না" লিখেছিলাম, কিন্তু এ বিষয়ে আমি নিশ্চিত নই। এখন বলা হয়: script-এর এগুলোর নিয়ম নেই, তাই হাতে মুছতে হবে।

### 9.5 Test

```bash
python3 -m unittest -v
```

৭টি test:

- Dry-run-এ কোনো মোছার call নেই।
- ভুল account-এ থামে।
- Execute-এর ক্রম।
- মুছে-যাওয়া volume-এ থামে না।
- Guard (`prod`, tag-হীন, অন্য region)।
- ARN parsing ও manual।
- Cost report।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `ORDER` | মোছার ক্রম | নির্ভরতা |
| `run()` | `EXECUTE=yes` না হলে শুধু ছাপে | ডিফল্ট dry-run |
| `retry()` | ১৫ s × ১২ | ENI-র দেরি |
| `revoke_sg_refs()` + সব revoke আগে | SG-এর পারস্পরিক বাঁধন | `DependencyViolation` |
| `empty_bucket()` | Version ও delete marker, ১০০০ করে | Versioned bucket (L08-08) |
| Main route table skip | VPC-র সাথে মোছে | মোছা যায় না |
| `FORBIDDEN_VALUES` | `prod` ইত্যাদি | Blast radius |
| `export -f aws` (test) | নকল CLI | Script আসলে চালিয়ে যাচাই |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `cleanup_plan.py` নমুনায় | Script + `manual: …ssm…` |
| `bash cleanup.sh` | শুধু `DRY-RUN:` লাইন |
| নিজের account-এ cleanup-এর পরে | `inventory.py`-এ কোনো lab resource নেই |
| Cost Explorer পরের দিনগুলোতে | Lab-এর service-এর খরচ থেমেছে |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `refusing: credentials are for account …` | ভুল profile | `AWS_PROFILE`; ঠিক আচরণ |
| `delete-vpc`: `DependencyViolation` বারবার | Tag-হীন ENI/endpoint/SG রয়ে গেছে | `aws ec2 describe-network-interfaces --filters Name=vpc-id,Values=…` |
| `delete-security-group`: `DependencyViolation` | অন্য SG (tag-হীন) reference করছে, বা ENI | Reference খুঁজুন: `describe-security-group-rules` |
| `get-resources`-এ কিছু নেই, অথচ বিল আছে | Tag ছাড়া তৈরি, বা অন্য region | `inventory.py --all-regions` |
| Cost Explorer-এ tag-এর group খালি | Cost allocation tag চালু নয়, বা চালুর আগের খরচ | Billing → Cost allocation tags; ২৪ ঘণ্টা পর্যন্ত লাগতে পারে |
| মোছার পরেও `get-resources`-এ ARN | Tagging API-র দেরি | কিছুক্ষণ পরে আবার; `describe-*` দিয়ে নিশ্চিত হোন |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Cleanup role-কে শুধু lab account বা tag-condition-এ সীমিত রাখুন (`aws:ResourceTag/Project`)।
  - Production account-এ এই ধরনের script নয় — আলাদা account (Module 19)।
  - Script নিজে review-যোগ্য text — PR-এ রাখুন।
- **Performance:** `wait` ও `retry`-তে cleanup কয়েক মিনিট লাগে — স্বাভাবিক।
- **Cost:**
  - এই lesson-ই module-এর খরচ বন্ধ করে।
  - Budget (L08-01) রেখে দিন — পরের module-গুলোতেও।
  - Cost Explorer API দিনে একবার; console-এর দেখা চার্জমুক্ত।

## 14. Hands-on exercise

1. Section 9.3 অনুসরণ করে Module 08-এর সব resource মুছুন; `inventory.py`-এ শূন্য দেখান।
2. `cleanup_plan.py`-তে `--regions` যোগ করুন: একাধিক region-এর `get-resources` file একসাথে নিয়ে region-প্রতি অংশ।
3. `ce_report.py`-তে `--granularity DAILY`-এর data থেকে "গতকালের চেয়ে ৫০% বেশি" সতর্কতা যোগ করুন।
4. একটি IAM policy লিখুন যা `Project` tag ছাড়া `ec2:RunInstances` deny করে (`aws:RequestTag/Project` + `Null` condition)। L07-05-এর `policy_eval.py`-তে পরীক্ষা করুন — evaluator `Null` operator সমর্থন করে কি? না করলে যোগ করুন।
5. L07-06-এর `tag_audit.py`-এর input `inventory.py`-র output থেকে বানানোর একটি converter লিখুন।

## 15. Mini-project — Nightly lab sweeper

একটি scheduled job (Module 11-এ CI-তে, বা নিজের machine-এর systemd timer — L01-11):

1. সব region-এ `Project=lab*` ও `Expires < আজ`।
2. Owner-কে email (SNS)।
3. পরের দিন dry-run report।
4. মানুষের অনুমোদনে `EXECUTE=yes`।

কখনো স্বয়ংক্রিয়ভাবে মোছা নয় — L05-03-এর নীতি।

## 16. Interview প্রশ্ন

1. Tagging strategy-তে কোন tag বাধ্যতামূলক রাখবেন, কীভাবে বাধ্য করবেন?
2. Cost allocation tag কী? কেন পুরোনো খরচে দেখা যায় না?
3. "EC2 - Other"-এ কী থাকে?
4. একটি VPC সম্পূর্ণ মোছার সঠিক ক্রম কী? কেন `DependencyViolation` হয়?
5. Cleanup automation-কে কীভাবে নিরাপদ করবেন?
6. Tag-ভিত্তিক cleanup-এর সীমা কী?

## 17. Self-assessment প্রশ্ন

1. বাক্স-লেবেল analogy কোথায় মেলে না?
2. Security group মোছার আগে কী করতে হয়, কেন?
3. Root volume-এর জন্য existence check কেন?
4. Script কোন ছয়টি স্তরে নিজেকে রক্ষা করে?
5. Cleanup "শেষ" — কীভাবে প্রমাণ করবেন?

## 18. সংক্ষিপ্ত সারাংশ

- প্রথম দিন থেকে tag (`Project`, `Owner`, `Expires`) এবং cost allocation tag চালু।
- Cost Explorer: service ও tag; "EC2 - Other" ও untagged-এর অংশ দেখুন।
- Cleanup: tag → plan → dry-run → account guard → নির্ভরতার ক্রমে মোছা → inventory-তে শূন্য।
- Script নকল CLI দিয়ে আসলে চালিয়ে test করা যায় — মোছার code-এর জন্য এটাই ন্যূনতম।

## 19. Completion checklist

- [ ] Module 08-এর সব resource মোছা; `inventory.py`-এ শূন্য (module completion criteria: zero orphaned resource)
- [ ] IAM role/instance profile ও hosted zone হাতে মোছা
- [ ] `Project` cost allocation tag চালু
- [ ] Budget alert এখনো সক্রিয়
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS — Tagging best practices (whitepaper): https://docs.aws.amazon.com/whitepapers/latest/tagging-best-practices/tagging-best-practices.html
- AWS Billing — Cost allocation tags: https://docs.aws.amazon.com/awsaccountbilling/latest/aboutv2/cost-alloc-tags.html
- AWS Cost Explorer: https://docs.aws.amazon.com/cost-management/latest/userguide/ce-what-is.html
- Resource Groups Tagging API — GetResources: https://docs.aws.amazon.com/resourcegroupstagging/latest/APIReference/API_GetResources.html
- Amazon VPC — Delete a VPC: https://docs.aws.amazon.com/vpc/latest/userguide/delete-vpc.html
- AWS Cost Management pricing: https://aws.amazon.com/aws-cost-management/pricing/

---

**পরের lesson:** L09-01 — Container বনাম virtual machine
