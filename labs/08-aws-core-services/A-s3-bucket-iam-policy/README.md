# Lab 08-A — S3 bucket ও IAM policy

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৯০ মিনিট |
| **Environment** | আপনার AWS account (L08-01-এর budget চালু) + AWS CLI v2 + Python 3 |
| **Label** | 💰 একটি ছোট S3 bucket ও কয়েকটি request — সাধারণত সামান্য, কিন্তু শূন্য নয়; S3 pricing দেখুন। Lab শেষে সম্পূর্ণ মুছুন |
| **Tested** | `check_a.py` Windows-এ যাচাই করা: একটি reference folder-এ (repo-তে নেই) ALL PASS; চওড়া policy, versioning নেই ও মেয়াদোত্তীর্ণ URL-এ 200 দেওয়া folder-এ ৮টি FAIL; `--after-cleanup` খালি তালিকায় PASS। **আসল AWS account-এ lab চালানো হয়নি** — command-গুলো L08-08 ও L08-03-এর, সেখানেও আসল AWS-এ চালানো হয়নি। |

## Objective

TaskFlow-এর upload-এর জন্য একটি নিরাপদ bucket ও তার জন্য least-privilege policy বানানো, তারপর প্রমাণ করা:

- bucket public নয়, TLS-only, versioned, lifecycle-সহ;
- app শুধু `u/*`-এ পড়তে-লিখতে পারে, আর কিছু নয়;
- presigned URL মেয়াদের পরে কাজ করে না;
- শেষে কিছুই রয়ে যায়নি।

## Prerequisites

- [L08-01](../../../08-aws-core-services/L08-01-account-safety-root-mfa-budget.md) (budget চালু), [L08-02](../../../08-aws-core-services/L08-02-aws-cli-profiles-temporary-credentials-boto3.md) (SSO profile)
- [L08-03 — IAM role](../../../08-aws-core-services/L08-03-iam-policy-role-instance-profile.md), [L08-08 — S3](../../../08-aws-core-services/L08-08-s3.md)
- [L07-05 — least privilege](../../../07-cloud-fundamentals/L07-05-iam-least-privilege.md)

## Environment setup

```bash
export AWS_PROFILE=learn-admin AWS_REGION=ap-south-1
ACCT=$(aws sts get-caller-identity --query Account --output text)
B=lab08-uploads-$ACCT
mkdir -p ~/lab08a/s3/$B
L=~/devops-ai-engineering/08-aws-core-services/code
cd ~/devops-ai-engineering/labs/08-aws-core-services/A-s3-bucket-iam-policy
```

File: [`check_a.py`](check_a.py)।

## Steps

1. **Budget আছে কিনা দেখুন:** `aws budgets describe-budgets --account-id $ACCT` — না থাকলে L08-01।

2. **Bucket (L08-08 Section 9.3):**
   - তৈরি;
   - `put-bucket-tagging` (`Project=lab08`);
   - versioning;
   - TLS-only policy (`$L/L08-08/sample/bucket-policy-tls-only.json`, `BUCKET` বদলে);
   - lifecycle (`$L/L08-08/sample/lifecycle-good.json`)।

3. **App policy লিখুন:** `~/lab08a/app-policy.json`। কাজ:
   - `u/*` prefix-এ `GetObject` ও `PutObject`;
   - `ListBucket` শুধু `u/` prefix-এ (`s3:prefix` condition)।

   কোনো `s3:*`, `Delete*`, bucket-স্তরের কাজ নয়। আগে offline যাচাই:

   ```bash
   python3 ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-05/policy_lint.py ~/lab08a/app-policy.json
   aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY --policy-document file://$HOME/lab08a/app-policy.json
   ```

4. **Role-এ লাগান:** L08-03-এর `taskflow-app` role না থাকলে বানান (`trust-ec2.json`)। তারপর:

   ```bash
   aws iam put-role-policy --role-name taskflow-app --policy-name uploads --policy-document file://$HOME/lab08a/app-policy.json
   ```

5. **Presigned URL:**

   ```bash
   echo hello > /tmp/a.txt && aws s3 cp /tmp/a.txt s3://$B/u/42/a.txt
   eval "$(aws configure export-credentials --format env)"
   URL=$(python3 $L/L08-08/presign.py --bucket $B --key u/42/a.txt --region $AWS_REGION --expires 60 --profile-env)
   echo "before: $(curl -s -o /dev/null -w '%{http_code}' "$URL")" > ~/lab08a/presign-results.txt
   sleep 70
   echo "after: $(curl -s -o /dev/null -w '%{http_code}' "$URL")" >> ~/lab08a/presign-results.txt
   ```

6. **Setting সংগ্রহ:**

   ```bash
   for x in public-access-block:get-public-access-block policy:get-bucket-policy versioning:get-bucket-versioning \
            lifecycle:get-bucket-lifecycle-configuration ownership:get-bucket-ownership-controls; do
     aws s3api ${x#*:} --bucket $B > ~/lab08a/s3/$B/${x%%:*}.json || true
   done
   aws s3api get-bucket-tagging --bucket $B > ~/lab08a/bucket-tagging.json
   ```

7. **যাচাই:** `python3 check_a.py ~/lab08a --bucket $B`

8. **Cleanup:**
   - Bucket-এর সব version মুছে bucket মুছুন (L08-08 Section 9.3, বা L08-12-এর `cleanup_plan.py`)।
   - `aws iam delete-role-policy --role-name taskflow-app --policy-name uploads`।
   - Role অন্য কোথাও না লাগলে সেটাও মুছুন (L08-03-এর ক্রম)।

   তারপর:

   ```bash
   aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=lab08 > ~/lab08a/after-cleanup.json
   python3 check_a.py ~/lab08a --bucket $B --after-cleanup
   ```

## Expected behavior

| যাচাই | ফল |
|---|---|
| `s3_audit` | `ok` (INFO চলবে) |
| Policy | ৩টি allowed, ৮টি denied |
| Presigned URL | `before: 200`, `after: 403` |
| Cleanup-এর পরে | Project=lab08-এর কোনো resource নেই |

## Verification

```bash
python3 check_a.py ~/lab08a --bucket $B; echo "exit=$?"                     # ALL CHECKS PASSED, 0
python3 check_a.py ~/lab08a --bucket $B --after-cleanup; echo "exit=$?"     # cleanup-এর পরে
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| `allowed: s3:ListBucket … u/42/` FAIL | ListBucket-এর resource bucket ARN (object নয়), condition `StringLike` `u/*` |
| `denied: s3:ListBucket prefix ""` FAIL | Condition ছাড়া ListBucket |
| `s3_audit: … versioning` FAIL | `get-bucket-versioning` খালি — versioning চালু হয়নি |
| `after: 200` | `sleep` মেয়াদের চেয়ে কম, বা `--expires` বড় |
| `before: 403` | Region ভুল, ঘড়ির পার্থক্য, বা `export-credentials` চালানো হয়নি (L08-08-এর troubleshooting) |
| `after-cleanup`-এ ARN রয়ে গেছে | Bucket-এ পুরোনো version; বা tagging API-র দেরি — কয়েক মিনিট পরে আবার |

## Cleanup / reset

Step 8। শেষে `python3 $L/L08-02/inventory.py --regions $AWS_REGION --summary` — কোনো `s3-bucket` নেই। Local: `rm -rf ~/lab08a` (ঐচ্ছিক — notebook-এ রাখতে পারেন)।

## Assessment

1. App policy-তে `s3:ListBucket`-এর resource কেন bucket ARN, আর `GetObject`-এর কেন object ARN?
2. Bucket-এর TLS-only Deny statement থাকলে, app policy-র Allow থাকা সত্ত্বেও HTTP request কেন ব্যর্থ হয়?
3. Presigned URL যে credential দিয়ে sign হয়েছে, তার permission বাতিল করলে URL-এর কী হয়?
4. Versioned bucket মুছতে `aws s3 rm --recursive` কেন যথেষ্ট নয়?
5. `checker`-এর ৮টি deny-request-এর কোনটি আপনার প্রথম খসড়ায় ব্যর্থ হয়েছিল, কেন?
