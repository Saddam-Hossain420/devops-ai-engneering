# Module 08 Labs — AWS Core Services

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — S3 bucket ও IAM policy](A-s3-bucket-iam-policy/README.md) | A — Fundamentals | নিরাপদ bucket (BPA, TLS-only, versioning, lifecycle), app-এর least-privilege policy (৩ allow, ৮ deny), presigned URL-এর মেয়াদ, সম্পূর্ণ cleanup | ৯০ মিনিট | L08-01 – L08-03, L08-08 |
| [B — TaskFlow: VPC + EC2 + ALB](B-taskflow-vpc-ec2-alb/README.md) | B — Integrated | নিজের VPC (NAT ছাড়া), দুই AZ-এ private EC2 (user data-য় TaskFlow), ALB; Module 08-এর চারটি tool দিয়ে ২৪টি check; cleanup | ৩–৪ ঘণ্টা | L08-04 – L08-12 |
| [C — Security group ভুলে timeout](C-sg-timeout-diagnosis/README.md) | C — Failure and Recovery | `Target.Timeout` incident: পুরোনো SG reference + stateless NACL-এর ফেরত পথ — একটি অন্যটিকে লুকায়; ন্যূনতম fix ও লিখিত diagnosis | ৬০–৯০ মিনিট | L08-05, L08-09 |

**Environment ও খরচ:**

- **Lab A ও B আসল AWS account-এ, চার্জযোগ্য।** শুরুর আগে L08-01-এর budget alert চালু রাখুন; একই দিনে শেষ করে cleanup করুন (L08-12)। দামের সংখ্যা এই course-এ দেওয়া হয়নি — pricing page দেখুন।
- **Lab C সম্পূর্ণ offline**, কোনো খরচ নেই।
- তিনটি checker Windows-এ reference solution (repo-তে নেই) ও ইচ্ছাকৃত ভুল input দিয়ে যাচাই করা। **Lab A ও B আসল AWS-এ চালানো হয়নি।**

**Module 08-এর completion criteria:**

- "Budget alert সক্রিয়" → L08-01 (Lab A ও B-এর পূর্বশর্ত)।
- "VPC + EC2 + ALB architecture তৈরি" → Lab B।
- "Lab শেষে cleanup script চালিয়ে zero orphaned resource" → Lab A ও B-এর `--after-cleanup` এবং `inventory.py`।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [08-aws-core-services/PROGRESS.md](../../08-aws-core-services/PROGRESS.md)-এর Module assessment table আপডেট করুন।
