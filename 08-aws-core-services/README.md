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
| L08-01 | [AWS account safety: root user, MFA, budget alert](L08-01-account-safety-root-mfa-budget.md) | Beginner | 💰 | COMPLETED |
| L08-02 | [AWS CLI, profile, temporary credential ও boto3](L08-02-aws-cli-profiles-temporary-credentials-boto3.md) | Intermediate | 💰 | COMPLETED |
| L08-03 | [IAM: policy, role, instance profile](L08-03-iam-policy-role-instance-profile.md) | Intermediate | 💰 | COMPLETED |
| L08-04 | [VPC design: subnet, route table, gateway](L08-04-vpc-subnet-route-gateway.md) | Intermediate | 💰 | COMPLETED |
| L08-05 | [Security group ও network ACL](L08-05-security-groups-nacl.md) | Intermediate | 💰 | COMPLETED |
| L08-06 | [EC2](L08-06-ec2.md) | Intermediate | 💰 | COMPLETED |
| L08-07 | [EBS ও EFS](L08-07-ebs-efs.md) | Intermediate | 💰 | COMPLETED |
| L08-08 | [S3](L08-08-s3.md) | Intermediate | 💰 | COMPLETED |
| L08-09 | [Elastic Load Balancing](L08-09-elastic-load-balancing.md) | Intermediate | 💰 | COMPLETED |
| L08-10 | [Route 53](L08-10-route53.md) | Intermediate | 💰 | COMPLETED |
| L08-11 | [CloudWatch](L08-11-cloudwatch.md) | Intermediate | 💰 | COMPLETED |
| L08-12 | [Tagging, Cost Explorer ও resource cleanup automation](L08-12-tagging-cost-explorer-cleanup.md) | Intermediate | 💰 | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `08-aws-core-services/LNN-MM-slug.md`

## Labs

Lab folder: [labs/08-aws-core-services/](../labs/08-aws-core-services/README.md) · Module quiz: [assessments/08-aws-core-services/quiz.md](../assessments/08-aws-core-services/quiz.md)

- Level A — নিরাপদ S3 bucket ও app-এর least-privilege policy; presigned URL-এর মেয়াদ; সম্পূর্ণ cleanup (💰)
- Level B — TaskFlow: নিজের VPC → দুই AZ-এ private EC2 → ALB; Module 08-এর চারটি tool দিয়ে যাচাই; cleanup (💰)
- Level C — `Target.Timeout` incident: পুরোনো SG reference + NACL-এর ফেরত পথ (offline)

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
