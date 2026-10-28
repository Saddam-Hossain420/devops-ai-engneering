# P04 — Infrastructure as Code on AWS

**Status:** NOT_STARTED · **Milestone:** 5 · **Track:** A, B · **পূর্বশর্ত:** Module 07, Module 08, Module 12

## লক্ষ্য

Terraform দিয়ে VPC, subnet, security group, IAM role, EC2 ও ALB — reusable module, remote state ও locking সহ। 💰 Local বিকল্প: Docker provider।

## Architecture

```text
terraform ──► S3 remote state (encrypted, versioned, lockfile)
   modules/network ──► VPC, public/private subnet, route table, NAT (ঐচ্ছিক, 💰)
   modules/compute ──► EC2 (instance profile, no SSH key; SSM)
   modules/lb      ──► ALB + target group + health check
```

## Features (scope)

- dev/staging environment আলাদা
- সব resource-এ tag (Project, Env, Owner, TTL)
- `terraform fmt`, `validate`, `tflint`, `checkov` CI-তে
- State-এ secret না রাখার কৌশল
- Infracost বা হাতে cost estimate

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] `terraform plan` দ্বিতীয়বার no changes
- [ ] Console-এ হাতে পরিবর্তন করলে plan-এ drift ধরা পড়ে
- [ ] ALB DNS-এ app সাড়া দেয়
- [ ] `terraform destroy`-এর পরে cleanup checklist অনুযায়ী zero resource

## Resource requirements

💰 AWS account, budget alert বাধ্যতামূলক। NAT Gateway ও ALB ঘণ্টাভিত্তিক বিল হয় — lab শেষে সঙ্গে সঙ্গে destroy।

## Cleanup

⚠️ `terraform destroy` শুধু নিজে পর্যালোচনা করে চালাবেন। তারপর Cost Explorer ও tag-ভিত্তিক inventory script দিয়ে যাচাই।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
