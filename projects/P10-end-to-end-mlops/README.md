# P10 — End-to-End MLOps

**Status:** NOT_STARTED · **Milestone:** 9 · **Track:** E · **পূর্বশর্ত:** Module 23, Module 24

## লক্ষ্য

ছোট dataset ও CPU-বান্ধব model দিয়ে reproducible training, MLflow tracking, registry, versioned FastAPI inference, monitoring ও rollback।

## Architecture

```text
data (versioned) ──► train.py ──► MLflow (params, metrics, artifact)
     ──► evaluation gate ──► registry (Staging → Production alias)
     ──► FastAPI inference (model version pin) ──► metrics + drift report
     ──► rollback = আগের version-এ alias সরানো
```

## Features (scope)

- Seed ও dependency pin দিয়ে reproducibility
- Quality gate: baseline-এর চেয়ে খারাপ model promote হয় না
- Inference API-তে model version response-এ
- Drift report (Evidently বা নিজের Python)

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] একই commit + data থেকে একই metric
- [ ] খারাপ model gate-এ আটকায়
- [ ] Rollback-এর পরে API পুরোনো version দেয়
- [ ] সব কিছু GPU ছাড়া চলে

## Resource requirements

CPU, ৪–৮ GB RAM।

## Cleanup

MLflow server ও container বন্ধ; `mlruns/` local ও gitignored।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
