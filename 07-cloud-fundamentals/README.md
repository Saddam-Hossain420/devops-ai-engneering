# Module 07 — Cloud Fundamentals

**Stage:** 4 · **Lesson:** 6 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Vendor-neutral cloud ধারণা: virtualization, service model, region/AZ, networking, IAM ও cost model — AWS-এ যাওয়ার আগে local Linux উদাহরণ দিয়ে বোঝা।

## পূর্বশর্ত (Prerequisites)

[02-computer-networking](../02-computer-networking/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Hypervisor ও VM ব্যাখ্যা
- Shared responsibility model বোঝা
- Region/AZ দিয়ে fault domain design
- IAM least privilege নীতি প্রয়োগ
- Cloud cost estimate ও cleanup plan

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L07-01 | [Virtualization ও hypervisor](L07-01-virtualization-hypervisor.md) | Beginner |  | COMPLETED |
| L07-02 | [IaaS, PaaS, SaaS ও shared responsibility model](L07-02-service-models-shared-responsibility.md) | Beginner |  | COMPLETED |
| L07-03 | [Region, availability zone ও fault domain](L07-03-regions-zones-fault-domains.md) | Beginner |  | COMPLETED |
| L07-04 | [Public বনাম private networking](L07-04-public-private-networking.md) | Beginner |  | COMPLETED |
| L07-05 | [IAM, identity ও least privilege](L07-05-iam-least-privilege.md) | Intermediate |  | COMPLETED |
| L07-06 | [Cloud cost model, budget, tagging ও cleanup](L07-06-cost-budget-tagging-cleanup.md) | Beginner |  | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `07-cloud-fundamentals/LNN-MM-slug.md`

## Labs

Lab folder: [labs/07-cloud-fundamentals/](../labs/07-cloud-fundamentals/README.md) · Module quiz: [assessments/07-cloud-fundamentals/quiz.md](../assessments/07-cloud-fundamentals/quiz.md)

- Level A — নিজের machine-এ Ubuntu VM: host ও guest-এর `virt_probe.py`, overcommit, load-এ steal, snapshot
- Level B — on-prem বনাম cloud: availability, খরচ (উদাহরণ-দাম + TCO অনুমান) ও লিখিত সিদ্ধান্ত
- Level C — CI deploy role-এর ভুল IAM policy-র ঝুঁকি বিশ্লেষণ → least-privilege fix, tool দিয়ে প্রমাণ

## সংশ্লিষ্ট project

—

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] একটি ছোট architecture-এর cost estimate ও fault-domain analysis

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
