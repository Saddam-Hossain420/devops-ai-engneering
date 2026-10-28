# P09 — Secure Software Delivery

**Status:** NOT_STARTED · **Milestone:** 8 · **Track:** D · **পূর্বশর্ত:** Module 11, Module 19

## লক্ষ্য

Pipeline-এ dependency ও container scanning, IaC check, SBOM, image signing ও verification এবং least-privilege permission।

## Architecture

```text
PR ──► SAST + dependency scan + secret scan ──► build ──► SBOM ──► image scan
     ──► sign (cosign) ──► publish ──► admission policy: শুধু signed image
```

## Features (scope)

- Workflow-এ `permissions:` সর্বনিম্ন
- SBOM (SPDX/CycloneDX) artifact
- Keyless বা key-ভিত্তিক signing
- Kyverno/OPA policy
- প্রতিটি scanner কী ধরে না তার লিখিত ব্যাখ্যা

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] Unsigned image cluster-এ reject হয়
- [ ] Critical CVE থাকলে pipeline থামে (exception process সহ)
- [ ] Commit-এ secret থাকলে block

## Resource requirements

GitHub, kind cluster।

## Cleanup

Test image ও signature মুছে ফেলার নির্দেশ।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
