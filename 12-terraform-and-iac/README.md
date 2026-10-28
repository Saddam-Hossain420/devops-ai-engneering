# Module 12 — Terraform and Infrastructure as Code

**Stage:** 7 · **Lesson:** 12 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

IaC কেন, Terraform workflow, state ও remote state, dependency, module, environment, testing, import ও drift, secret leakage প্রতিরোধ এবং AWS infrastructure — প্রথমে local provider দিয়ে খরচ ছাড়া।

## পূর্বশর্ত (Prerequisites)

[08-aws-core-services](../08-aws-core-services/README.md), [11-ci-cd-and-release-engineering](../11-ci-cd-and-release-engineering/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- State-এর ভূমিকা ও ঝুঁকি ব্যাখ্যা
- Reusable module লেখা ও version করা
- Drift detect ও import
- AWS VPC/EC2 Terraform দিয়ে তৈরি ও ধ্বংস

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L12-01 | Infrastructure as Code কেন | Beginner |  | NOT_STARTED |
| L12-02 | Terraform workflow: init, plan, apply (local provider দিয়ে) | Beginner |  | NOT_STARTED |
| L12-03 | Provider, resource, data source, variable, output | Intermediate |  | NOT_STARTED |
| L12-04 | Terraform state ভেতর থেকে | Intermediate |  | NOT_STARTED |
| L12-05 | Remote state, locking ও state security | Advanced | 💰 | NOT_STARTED |
| L12-06 | Resource dependency ও lifecycle | Intermediate |  | NOT_STARTED |
| L12-07 | Module ও module versioning | Intermediate |  | NOT_STARTED |
| L12-08 | Environment ও workspace | Intermediate |  | NOT_STARTED |
| L12-09 | Testing ও validation: terraform test, tflint, checkov | Intermediate |  | NOT_STARTED |
| L12-10 | Existing infrastructure import ও drift detection | Advanced |  | NOT_STARTED |
| L12-11 | Secret handling ও state leakage প্রতিরোধ | Advanced |  | NOT_STARTED |
| L12-12 | Terraform দিয়ে AWS VPC ও EC2 | Advanced | 💰 | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `12-terraform-and-iac/LNN-MM-slug.md`

## Labs

Lab folder: `labs/12-terraform-and-iac/`

- Level A — local/random provider দিয়ে workflow
- Level B — module দিয়ে multi-environment
- Level C — হাতে পরিবর্তন করে drift detect

## সংশ্লিষ্ট project

[P04-aws-terraform-infrastructure](../projects/P04-aws-terraform-infrastructure/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 4 plan/apply/destroy নিরাপদভাবে, cleanup checklist সহ

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
