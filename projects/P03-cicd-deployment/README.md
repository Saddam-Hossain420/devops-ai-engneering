# P03 — Automated CI/CD Deployment

**Status:** NOT_STARTED · **Milestone:** 4 · **Track:** A, D · **পূর্বশর্ত:** Module 03, Module 11

## লক্ষ্য

GitHub Actions pipeline যা test → build → scan → versioned image publish → test environment-এ deploy → verify করে।

## Architecture

```text
push/PR ──► lint+test ──► build image ──► scan ──► publish (ghcr, sha+semver tag)
                                                      │
                               tag v* ────────────────┴──► deploy (test env, approval) ──► smoke test ──► rollback on fail
```

## Features (scope)

- Pull request-এ শুধু CI; main/tag-এ CD
- Dependency cache
- Commit SHA ও semver দিয়ে immutable image tag
- Environment protection ও manual approval
- OIDC (cloud deploy হলে) — long-lived key নয়
- Smoke test ব্যর্থ হলে আগের version-এ rollback

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] ইচ্ছাকৃত ভাঙা test merge আটকায়
- [ ] Critical vulnerability থাকলে publish থামে
- [ ] Deploy-এর পরে smoke test pass
- [ ] Rollback workflow কাজ করে ও audit trail থাকে

## Resource requirements

GitHub account (free tier), GHCR। Test environment: local VM বা free-tier।

## Cleanup

পুরোনো image tag ও test environment মুছে ফেলার নির্দেশ README-তে।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
