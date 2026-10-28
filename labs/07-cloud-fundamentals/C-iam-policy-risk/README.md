# Lab 07-C — একটি ভুল IAM policy-র ঝুঁকি বিশ্লেষণ

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট |
| **Environment** | যেকোনো OS-এ Python 3 — সম্পূর্ণ offline |
| **Label** | — (কোনো cloud account, credential বা API call নেই) |
| **Tested** | `check_c.py` Windows-এ (Python 3.14.5) যাচাই করা: দেওয়া `broken-policy.json`-এ ১৩টি FAIL, একটি reference fixed policy-তে (repo-তে রাখা হয়নি) ALL PASS। Evaluator L07-05-এর সরল `policy_eval.py` — SCP, permission boundary, resource policy ও session policy নেই; **আসল AWS IAM policy simulator-এ মেলানো হয়নি।** |

## Objective

TaskFlow-এর CI deploy role-এ কেউ "দ্রুত কাজ চালাতে" একটি policy লিখেছে: [`broken-policy.json`](broken-policy.json)। আপনার কাজ তিনটি:

1. প্রতিটি statement-এর ঝুঁকি লিখিত বিশ্লেষণ করা — কে কী করতে পারবে, সবচেয়ে খারাপ কী ঘটতে পারে।
2. একটি least-privilege `fixed-policy.json` লেখা, যাতে CI-এর কাজ চলে কিন্তু বিপজ্জনক কিছু না।
3. Tool দিয়ে প্রমাণ করা।

## Prerequisites

- [L07-05 — IAM ও least privilege](../../../07-cloud-fundamentals/L07-05-iam-least-privilege.md) (evaluation logic, NotAction, PassRole, condition)
- [L07-02 — Shared responsibility](../../../07-cloud-fundamentals/L07-02-service-models-shared-responsibility.md) (identity কার দায়িত্ব)

## Environment setup

```bash
mkdir -p ~/lab07c
cd ~/devops-ai-engineering/labs/07-cloud-fundamentals/C-iam-policy-risk
```

Files:

- [`broken-policy.json`](broken-policy.json) — বিশ্লেষণের বিষয় (বদলাবেন না)।
- [`required.json`](required.json) — CI-এর যেসব কাজ চলতেই হবে (৬টি)।
- [`dangerous.json`](dangerous.json) — যেসব কাজ কখনো চলা উচিত নয় (১৩টি)।
- [`check_c.py`](check_c.py) — checker।

## Steps

1. **আগে tool ছাড়া পড়ুন।** `broken-policy.json`-এর পাঁচটি statement-এর প্রতিটির জন্য `~/lab07c/risk-analysis.md`-এ লিখুন:
   - কোন কোন action ও resource এতে ঢোকে;
   - আক্রমণকারী (চুরি-যাওয়া CI token) এ দিয়ে সবচেয়ে খারাপ কী করতে পারে;
   - ঝুঁকির মাত্রা (critical/high/medium)।

   Statement-এর `Sid` হুবহু লিখুন — checker সেগুলো খোঁজে।

2. **একটি ফাঁদ:** `KeepReleases` statement release মোছা আটকানোর জন্য লেখা হয়েছিল। CI role-এর request-এ `aws:MultiFactorAuthPresent` key আদৌ থাকে কি? `Bool` ও `BoolIfExists`-এর পার্থক্য (L07-05) মনে করে লিখুন এই Deny কখন খাটে।

3. **ভাঙা policy-কে tool দিয়ে দেখুন:**

   ```bash
   python3 check_c.py broken-policy.json
   python3 ../../../07-cloud-fundamentals/code/L07-05/policy_lint.py broken-policy.json
   ```

   ধাপ ১-এ যা লিখেছিলেন তার সাথে মেলান। কোনো ঝুঁকি বাদ পড়েছিল? Analysis-এ যোগ করুন — আর যা নিজে ধরতে পারেননি, সেটা আলাদা করে চিহ্নিত করুন।

4. **`~/lab07c/fixed-policy.json` লিখুন।** নিয়ম:
   - শুধু `required.json`-এর কাজগুলো allow; `"Action": "*"`, `s3:*` বা `NotAction` নয়।
   - Resource যতটা সম্ভব নির্দিষ্ট — bucket-এর `releases/` prefix, `/taskflow/ci/` parameter path।
   - `iam:PassRole` শুধু app role-এ, এবং শুধু EC2-কে (`iam:PassedToService` condition)।
   - `ec2:DescribeInstances`-এর resource `*` রাখা চলে (Describe action resource-স্তরে সীমিত করা যায় না) — analysis-এ কারণ লিখুন।

5. **যাচাই:**

   ```bash
   python3 check_c.py ~/lab07c/fixed-policy.json --analysis ~/lab07c/risk-analysis.md
   ```

6. Analysis-এর শেষে **detection** অংশ লিখুন: এই role-এর credential চুরি হলে কোন log বা alert দিয়ে আগে জানবেন (CloudTrail-এর কোন event, budget alert — L07-06)?

## Expected behavior

| Policy | `check_c.py` |
|---|---|
| `broken-policy.json` | ১৩টি FAIL — ১২টি বিপজ্জনক request allowed + ১টি CRITICAL lint |
| আপনার `fixed-policy.json` | ALL CHECKS PASSED, exit 0 |

ভাঙা policy-তে `s3:DeleteObject`-এর উত্তর `allowed by ArtifactsAll` — Deny statement থাকা সত্ত্বেও।

## Verification

```bash
python3 check_c.py ~/lab07c/fixed-policy.json --analysis ~/lab07c/risk-analysis.md; echo "exit=$?"
# ALL CHECKS PASSED, exit=0
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| `ListBucket … releases/` FAIL (denied) | `s3:prefix` condition নেই বা pattern `releases/*` নয়। ListBucket-এর resource bucket, object নয় |
| `ListBucket … prefix ""` FAIL (allowed) | Condition ছাড়া ListBucket — পুরো bucket-এর তালিকা দেখা যায় |
| `PassRole … lambda` FAIL (allowed) | `iam:PassedToService` condition নেই |
| `PutObject` FAIL (denied) | Resource-এ `arn:aws:s3:::taskflow-artifacts/releases/*` (object ARN) দরকার, শুধু bucket ARN নয় |
| `ec2:RunInstances` FAIL | `NotAction` বা `ec2:*` রয়ে গেছে |
| `risk-analysis.md discusses …` FAIL | Sid হুবহু লেখা হয়নি |
| `error: …` exit 2 | JSON-এ comma বা quote-এর ভুল — `python3 -m json.tool fixed-policy.json` |

## Cleanup / reset

কোনো cloud resource তৈরি হয়নি। শুধু `~/lab07c/` আপনার notebook-এ রাখুন বা মুছুন।

## Assessment

1. পাঁচটি statement-এর মধ্যে কোনটি সবচেয়ে বিপজ্জনক, এবং কেন? (ইঙ্গিত: `NotAction` + `PassRole`-এর সমন্বয়।)
2. `KeepReleases` Deny কেন কাজ করেনি? এক শব্দ বদলে কীভাবে কাজ করানো যেত — আর সেটাও কি release মোছা আটকানোর সঠিক উপায়? (S3 versioning ও object lock ভাবুন।)
3. আপনার fixed policy-তে `iam:CreateAccessKey` কেন deny, যদিও কোনো Deny statement নেই?
4. এই checker PASS করলেও আসল AWS-এ policy ভুল হতে পারে — কোন দুটি কারণে?
5. এরকম policy production-এ পৌঁছানো ঠেকাতে কোন process রাখবেন (review, CI-তে lint, Access Analyzer)?
