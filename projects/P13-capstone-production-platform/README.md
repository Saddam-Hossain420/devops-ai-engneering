# P13 — Capstone Production Platform

**Status:** NOT_STARTED · **Milestone:** 12 · **Track:** সব · **পূর্বশর্ত:** Module 28, Module 29, Module 30, Module 31

## লক্ষ্য

আগের সব দক্ষতা একত্র: IaC, নিরাপদ cloud network, container, CI/CD, Kubernetes (বা যুক্তিসহ সরল বিকল্প), GitOps, observability, secret, backup ও recovery, security check, cost estimate, incident documentation; ঐচ্ছিক ML inference ও AI ops assistant।

## Architecture

```text
Architecture diagram, threat model, ADR set, DR plan, cost estimate —
সব `projects/P13-capstone-production-platform/docs/` এ থাকবে।
```

## Features (scope)

- প্রতিটি architectural decision-এর ADR
- Threat model (STRIDE)
- Deployment ও rollback procedure
- DR plan ও restore drill ফলাফল
- Portfolio README

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] Capstone rubric ([assessments/](../../assessments/README.md)) ≥ 75%
- [ ] Restore drill-এ মাপা RTO/RPO
- [ ] Cost estimate ও cleanup যাচাই

## Resource requirements

Local version বাধ্যতামূলক; 💰 cloud version ঐচ্ছিক।

## Cleanup

Cloud হলে cleanup checklist ও destroy-এর পরে inventory যাচাই।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
