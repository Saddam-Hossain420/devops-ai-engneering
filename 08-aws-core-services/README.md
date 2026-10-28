# Module 08 — AWS Core Services

**Stage:** 4 · **Lesson:** 12 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

AWS account নিরাপত্তা, CLI ও temporary credential, IAM, VPC, security group, EC2, EBS/EFS, S3, ELB, Route 53, CloudWatch এবং cost cleanup। 💰 সব lab-এ cost ও cleanup নির্দেশ আছে।

## পূর্বশর্ত (Prerequisites)

[05-python-for-infrastructure](../05-python-for-infrastructure/README.md), [07-cloud-fundamentals](../07-cloud-fundamentals/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Root account সুরক্ষা ও budget alert
- Temporary credential ও profile ব্যবহার
- VPC + EC2 + ALB architecture তৈরি
- boto3 দিয়ে read-only inventory script
- সব resource পরিষ্কারভাবে মুছে ফেলা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L08-01 | AWS account safety: root user, MFA, budget alert | Beginner | 💰 | NOT_STARTED |
| L08-02 | AWS CLI, profile, temporary credential ও boto3 | Intermediate | 💰 | NOT_STARTED |
| L08-03 | IAM: policy, role, instance profile | Intermediate | 💰 | NOT_STARTED |
| L08-04 | VPC design: subnet, route table, gateway | Intermediate | 💰 | NOT_STARTED |
| L08-05 | Security group ও network ACL | Intermediate | 💰 | NOT_STARTED |
| L08-06 | EC2 | Intermediate | 💰 | NOT_STARTED |
| L08-07 | EBS ও EFS | Intermediate | 💰 | NOT_STARTED |
| L08-08 | S3 | Intermediate | 💰 | NOT_STARTED |
| L08-09 | Elastic Load Balancing | Intermediate | 💰 | NOT_STARTED |
| L08-10 | Route 53 | Intermediate | 💰 | NOT_STARTED |
| L08-11 | CloudWatch | Intermediate | 💰 | NOT_STARTED |
| L08-12 | Tagging, Cost Explorer ও resource cleanup automation | Intermediate | 💰 | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `08-aws-core-services/LNN-MM-slug.md`

## Labs

Lab folder: `labs/08-aws-core-services/`

- Level A — S3 bucket ও IAM policy
- Level B — VPC + EC2 + ALB-এ continuous project
- Level C — security group ভুলের কারণে timeout diagnose

## সংশ্লিষ্ট project

[P04-aws-terraform-infrastructure](../projects/P04-aws-terraform-infrastructure/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Budget alert সক্রিয়
- [ ] Lab শেষে cleanup script চালিয়ে zero orphaned resource

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
