# Module 16 — GitOps and Platform Engineering

**Stage:** 9 · **Lesson:** 10 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

GitOps নীতি, Argo CD ও Flux, promotion, secret, drift correction, Internal Developer Platform, golden path, policy as code, multi-cluster ও platform ownership।

## পূর্বশর্ত (Prerequisites)

[11-ci-cd-and-release-engineering](../11-ci-cd-and-release-engineering/README.md), [15-helm-and-kubernetes-packaging](../15-helm-and-kubernetes-packaging/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Reconciliation loop ব্যাখ্যা
- Git change থেকে controlled rollout
- Environment promotion design
- Golden path template তৈরি

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L16-01 | GitOps principle ও reconciliation loop | Intermediate |  | NOT_STARTED |
| L16-02 | Argo CD | Intermediate |  | NOT_STARTED |
| L16-03 | Flux | Intermediate |  | NOT_STARTED |
| L16-04 | Environment জুড়ে application promotion | Advanced |  | NOT_STARTED |
| L16-05 | GitOps-এ secret management | Advanced |  | NOT_STARTED |
| L16-06 | Drift correction ও reconciliation | Intermediate |  | NOT_STARTED |
| L16-07 | Internal Developer Platform, golden path ও service template | Advanced |  | NOT_STARTED |
| L16-08 | Policy as Code | Advanced |  | NOT_STARTED |
| L16-09 | Multi-environment ও multi-cluster deployment | Advanced | 🧠 | NOT_STARTED |
| L16-10 | Platform reliability, ownership ও developer experience | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `16-gitops-and-platform-engineering/LNN-MM-slug.md`

## Labs

Lab folder: `labs/16-gitops-and-platform-engineering/`

- Level A — Argo CD install ও sync
- Level B — dev → staging promotion
- Level C — cluster-এ হাতে পরিবর্তন করে drift correction

## সংশ্লিষ্ট project

[P07-gitops-platform](../projects/P07-gitops-platform/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 7: Git commit-এ rollout, হাতে পরিবর্তন auto-revert

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
