# Module 11 — CI/CD and Release Engineering

**Stage:** 6 · **Lesson:** 14 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

CI/CD ধারণা, GitHub Actions গভীরে, build/test/cache, artifact versioning, registry publish, environment approval, OIDC, deployment strategy, DB migration, verification ও rollback, SBOM এবং end-to-end pipeline।

## পূর্বশর্ত (Prerequisites)

[03-git-and-collaboration](../03-git-and-collaboration/README.md), [09-docker-and-containers](../09-docker-and-containers/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Pipeline-এর প্রতিটি stage-এর trigger ও failure propagation ব্যাখ্যা
- OIDC দিয়ে key-ছাড়া cloud access
- Rolling/blue-green/canary বেছে নেওয়া
- Automated rollback

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L11-01 | Continuous Integration, Delivery ও Deployment | Beginner |  | NOT_STARTED |
| L11-02 | GitHub Actions: trigger, job, step, runner | Intermediate |  | NOT_STARTED |
| L11-03 | Build ও test stage | Intermediate |  | NOT_STARTED |
| L11-04 | Dependency caching ও build optimization | Intermediate |  | NOT_STARTED |
| L11-05 | Artifact versioning ও immutable artifact | Intermediate |  | NOT_STARTED |
| L11-06 | Container registry-তে publish | Intermediate |  | NOT_STARTED |
| L11-07 | Environment protection ও manual approval | Intermediate |  | NOT_STARTED |
| L11-08 | Secret management ও OIDC | Advanced |  | NOT_STARTED |
| L11-09 | Deployment strategy: rolling, blue-green, canary, recreate | Intermediate |  | NOT_STARTED |
| L11-10 | Database migration strategy | Advanced |  | NOT_STARTED |
| L11-11 | Smoke test, release verification ও rollback | Intermediate |  | NOT_STARTED |
| L11-12 | Supply-chain security ও SBOM | Advanced |  | NOT_STARTED |
| L11-13 | Reusable workflow, notification ও audit trail | Intermediate |  | NOT_STARTED |
| L11-14 | End-to-end pipeline: build → test → scan → publish → deploy → verify | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `11-ci-cd-and-release-engineering/LNN-MM-slug.md`

## Labs

Lab folder: `labs/11-ci-cd-and-release-engineering/`

- Level A — প্রথম CI workflow
- Level B — build → scan → publish → deploy → verify
- Level C — ভাঙা pipeline-এর failing stage খুঁজে ঠিক করা

## সংশ্লিষ্ট project

[P03-cicd-deployment](../projects/P03-cicd-deployment/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 3 pipeline সবুজ এবং ইচ্ছাকৃত ভাঙা test pipeline আটকায়

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
