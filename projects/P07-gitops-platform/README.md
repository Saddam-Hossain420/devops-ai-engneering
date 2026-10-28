# P07 — GitOps Platform

**Status:** NOT_STARTED · **Milestone:** 6 · **Track:** B · **পূর্বশর্ত:** Module 16

## লক্ষ্য

Argo CD (বা Flux) দিয়ে Git repository থেকে application-এর desired state পরিচালনা — Git change = controlled rollout।

## Architecture

```text
git (env/dev, env/staging) ──► Argo CD ──reconcile──► cluster
            ▲                                │
            └──── PR-ভিত্তিক promotion ◄─────┘ (drift হলে auto-heal)
```

## Features (scope)

- App-of-apps বা ApplicationSet
- dev → staging promotion PR দিয়ে
- Secret: SOPS বা Sealed Secrets
- Sync wave ও health check

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] Git-এ image tag বদলালে নির্দিষ্ট সময়ে rollout
- [ ] Cluster-এ হাতে পরিবর্তন auto-revert হয়
- [ ] Git revert-এ rollback

## Resource requirements

Project 6-এর cluster।

## Cleanup

Argo CD namespace ও Application মুছে ফেলা, তারপর cluster delete।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
