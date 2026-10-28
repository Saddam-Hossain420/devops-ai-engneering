# Lab 08-B — TaskFlow: VPC + EC2 + ALB

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ৩–৪ ঘণ্টা (এক বসায় শেষ করে মুছুন) |
| **Environment** | আপনার AWS account + AWS CLI v2 + Python 3 + Git Bash/Linux shell |
| **Label** | 💰 চার্জযোগ্য: **ALB** (ঘণ্টা + LCU + তার public IPv4), **দুটি EC2** (`t3.micro`) ও তাদের EBS, CloudWatch alarm (ঐচ্ছিক)। NAT ব্যবহার হয় না (user data-য় app embed — L08-06)। দাম EC2/ELB pricing page-এ দেখুন; শুরুর আগে budget alert চালু রাখুন, এবং **একই দিনে cleanup** |
| **Tested** | `check_b.py` Windows-এ যাচাই করা: একটি reference set-এ (repo-তে নেই) ২৪টি check ALL PASS; ইচ্ছাকৃত ভুল (public subnet-এ instance, IMDSv1, SSH 0.0.0.0/0, health check `/`, একটি unhealthy target) দেওয়া set-এ ১১টি FAIL। **আসল AWS-এ lab চালানো হয়নি** — Module 08-এর সব command সেখানেও "চালানো হয়নি" চিহ্নিত। |

## Objective

TaskFlow API (L05-13)-কে AWS-এ production-ধাঁচের নকশায় চালানো:

```text
internet ─80─► ALB (public-a, public-b; sg-alb)
                 └─8000─► EC2 app-a (AZ a) ─┐  private/isolated subnet, public IP নেই,
                 └─8000─► EC2 app-b (AZ b) ─┘  IMDSv2, instance profile, sg-app ← sg-alb
```

তারপর Module 08-এর সব tool দিয়ে প্রমাণ, এবং সম্পূর্ণ cleanup।

## Prerequisites

[L08-01](../../../08-aws-core-services/L08-01-account-safety-root-mfa-budget.md) থেকে [L08-12](../../../08-aws-core-services/L08-12-tagging-cost-explorer-cleanup.md) — বিশেষ করে:

- L08-04 (VPC script)
- L08-05 (SG)
- L08-06 (user data, run-instances)
- L08-09 (ALB)
- L08-12 (cleanup)

## Environment setup

```bash
export AWS_PROFILE=learn-admin AWS_REGION=ap-south-1
ACCT=$(aws sts get-caller-identity --query Account --output text)
C=~/devops-ai-engineering/08-aws-core-services/code
mkdir -p ~/lab08b && cd ~/lab08b
```

File: [`check_b.py`](check_b.py)।

## Steps

প্রতিটি resource-এ `Project=lab08` tag — L08-04/L08-06/L08-09-এর command-গুলো তাই করে।

1. **VPC (NAT ছাড়া):**

   ```bash
   python3 ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-04/subnet_plan.py $C/L08-04/sample-plan.json --json > plan.json
   python3 $C/L08-04/vpc_commands.py plan.json --vpc-cidr 10.20.0.0/16 --region $AWS_REGION --name lab08 > create-vpc.sh
   less create-vpc.sh && bash create-vpc.sh
   ```

   Subnet id-গুলো `describe-subnets --filters Name=tag:Name,Values=lab08-public-a` ইত্যাদি দিয়ে variable-এ নিন।

2. **Security group** — L08-05 Section 9.3: `lab08-alb` (80 from 0.0.0.0/0), `lab08-app` (8000 from `lab08-alb`)। SSH নয়।

3. **Role + instance profile** — L08-03 Section 9.2 (`taskflow-app`, `trust-ec2.json`)।

4. **দুটি instance** — L08-06 Section 9.1–9.2:
   - `make_user_data.py`;
   - `run-instances`-এ `--subnet-id` app-a ও app-b, `--security-group-ids` `lab08-app`;
   - `HttpTokens=required`;
   - console output-এ `taskflow healthy` দেখুন।

5. **ALB + target group** — L08-09 Section 9.3:
   - দুটি instance register;
   - `deregistration_delay` ৩০;
   - `wait target-in-service`।

6. **Health:** `curl -s http://$DNS/health > ~/lab08b/health.txt`

7. **Describe output সংগ্রহ:**

   ```bash
   V=$(aws ec2 describe-vpcs --filters Name=tag:Project,Values=lab08 --query 'Vpcs[0].VpcId' --output text)
   F="--filters Name=vpc-id,Values=$V"
   aws ec2 describe-subnets $F > subnets.json
   aws ec2 describe-route-tables $F > route-tables.json
   aws ec2 describe-nat-gateways --filter Name=vpc-id,Values=$V > nat-gateways.json
   aws ec2 describe-internet-gateways --filters Name=attachment.vpc-id,Values=$V > internet-gateways.json
   aws ec2 describe-security-groups $F > security-groups.json
   aws ec2 describe-network-acls $F > network-acls.json
   aws ec2 describe-instances --filters Name=tag:Project,Values=lab08 Name=instance-state-name,Values=running > instances.json
   aws elbv2 describe-load-balancers --names lab08-alb > load-balancers.json
   aws elbv2 describe-target-groups --names lab08-app > tg.json
   TG=$(python3 -c "import json;print(json.load(open('tg.json'))['TargetGroups'][0]['TargetGroupArn'])")
   aws elbv2 describe-target-group-attributes --target-group-arn "$TG" > tg-attrs.json
   aws elbv2 describe-target-health --target-group-arn "$TG" > health.json
   ```

8. **যাচাই:** `python3 ~/devops-ai-engineering/labs/08-aws-core-services/B-taskflow-vpc-ec2-alb/check_b.py ~/lab08b`

9. **(ঐচ্ছিক) Resilience পরীক্ষা:** একটি instance stop করুন। ALB-এর পেছনে `curl` loop চালিয়ে দেখুন কত সেকেন্ড error আসে (L08-09-এর হিসাবের সাথে মেলান), তারপর start।

10. **Cleanup** — L08-12 Section 9.3:
    - `cleanup_plan.py` → dry-run → `EXECUTE=yes`;
    - IAM role/instance profile হাতে;
    - তারপর:

    ```bash
    aws resourcegroupstaggingapi get-resources --tag-filters Key=Project,Values=lab08 > ~/lab08b/after-cleanup.json
    python3 …/check_b.py ~/lab08b --after-cleanup
    python3 $C/L08-02/inventory.py --regions $AWS_REGION --summary
    ```

## Expected behavior

| যাচাই | ফল |
|---|---|
| `check_b.py` | ২৪টি check (দুটি instance-এ) ALL PASS |
| `curl http://DNS/health` | `{"status": "ok", "version": "0.1.0"}` |
| একটি instance বন্ধ | কয়েক সেকেন্ড পরে সব request অন্যটিতে (≈ interval × unhealthy threshold) |
| Cleanup-এর পরে | কোনো `Project=lab08` resource নেই; inventory খালি |

**একটি সীমা:** দুটি instance-এর নিজস্ব SQLite — একটিতে বানানো task অন্যটিতে দেখা যায় না (L08-06 Section 8.1)। এটা প্রত্যাশিত। Managed database পরে।

## Verification

```bash
python3 check_b.py ~/lab08b; echo "exit=$?"                     # ALL CHECKS PASSED, 0
python3 check_b.py ~/lab08b --after-cleanup; echo "exit=$?"     # cleanup-এর পরে
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ | Tool |
|---|---|---|
| `ALB (subnet-…) → i-…:8000` FAIL | SG reference বা NACL | `sg_reach.py check` (L08-05) |
| Target `Target.Timeout` | একই | `tg_health.py` (L08-09) |
| Target `Target.FailedHealthChecks` | App চলেনি — console output-এ `sha256sum` বা `healthy` নেই | `get-console-output` (L08-06) |
| `private subnet, no public IP` FAIL | Instance public subnet-এ, বা subnet-এ auto public IP | `vpc_audit.py` (L08-04) |
| `internet → i-…:22 blocked` FAIL | SG-তে SSH খোলা — routing-এ পৌঁছানো না গেলেও নিয়মটাই ভুল | `sg_reach.py audit` |
| `vpc_audit: … blackhole` | পুরোনো চেষ্টার মুছে-যাওয়া NAT-এর route | Route মুছুন |
| `delete-vpc`: `DependencyViolation` | ALB-এর ENI এখনো | Cleanup script-এর `retry` অপেক্ষা করে |

## Cleanup / reset

Step 10। **একই দিনে** — ALB ও EC2 ঘণ্টা অনুযায়ী চার্জ হয়। পরের দিন Cost Explorer বা Budget-এ দেখুন খরচ থেমেছে (L08-12)।

## Assessment

1. Instance-গুলোর public IP নেই, NAT-ও নেই — তবু ALB কীভাবে পৌঁছায়, আর instance কীভাবে app পেল?
2. `check_b.py` ALB-এর **প্রতিটি** subnet থেকে flow পরীক্ষা করে। কোন ভুলে শুধু একটি AZ-এর ALB node থেকে timeout হতো?
3. Step 9-এ মাপা সময় L08-09-এর `interval × unhealthy threshold`-এর সাথে মিলল? না মিললে কেন?
4. এই নকশায় এখনো কোন single point of failure আছে (L07-03)? খরচ বাড়িয়ে কীভাবে দূর করবেন?
5. পুরো lab-এর খরচের কোন উপাদান সবচেয়ে বড় হওয়ার কথা — pricing page দেখে, তারিখ ও region সহ লিখুন।
