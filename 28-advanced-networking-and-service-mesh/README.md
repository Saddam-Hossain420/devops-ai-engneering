# Module 28 — Advanced Networking and Service Mesh

**Stage:** 17 · **Lesson:** 10 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

AWS multi-account, advanced VPC ও hybrid connectivity, identity federation, API gateway, service mesh (Linkerd/Istio), multi-region, advanced DNS/TLS troubleshooting, performance engineering ও cluster migration। সরল architecture প্রতিষ্ঠার পরেই।

## পূর্বশর্ত (Prerequisites)

[08-aws-core-services](../08-aws-core-services/README.md), [12-terraform-and-iac](../12-terraform-and-iac/README.md), [14-kubernetes](../14-kubernetes/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Multi-account landing zone ব্যাখ্যা
- Service mesh-এর খরচ ও মূল্য বিচার
- Multi-region failover design

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L28-01 | AWS multi-account architecture | Advanced | 💰 | NOT_STARTED |
| L28-02 | Advanced VPC: endpoint, private networking, hybrid connectivity | Advanced | 💰 | NOT_STARTED |
| L28-03 | Identity federation ও workload identity | Advanced |  | NOT_STARTED |
| L28-04 | API gateway ও traffic management | Advanced |  | NOT_STARTED |
| L28-05 | Service mesh concept | Advanced |  | NOT_STARTED |
| L28-06 | Linkerd / Istio lab | Advanced | 🧠 | NOT_STARTED |
| L28-07 | Multi-region architecture ও failure domain | Advanced | 💰 | NOT_STARTED |
| L28-08 | Advanced DNS, TLS ও routing troubleshooting | Advanced |  | NOT_STARTED |
| L28-09 | Performance ও capacity engineering | Advanced |  | NOT_STARTED |
| L28-10 | Cluster upgrade ও workload migration | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `28-advanced-networking-and-service-mesh/LNN-MM-slug.md`

## Labs

Lab folder: `labs/28-advanced-networking-and-service-mesh/`

- Level A — mTLS পর্যবেক্ষণ
- Level B — Linkerd দিয়ে traffic split
- Level C — mesh-এ certificate/routing failure

## সংশ্লিষ্ট project

[P13-capstone-production-platform](../projects/P13-capstone-production-platform/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Mesh ছাড়া ও সহ latency/complexity তুলনা report

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
