# P08 — Observability and Incident Response

**Status:** NOT_STARTED · **Milestone:** 7 · **Track:** C · **পূর্বশর্ত:** Module 17, Module 18

## লক্ষ্য

Metric, dashboard, log ও trace সহ monitoring stack; SLO-ভিত্তিক alert; runbook; simulated failure-এর postmortem।

## Architecture

```text
app (OTel SDK) ──► OTel Collector ──► Prometheus (metrics) ──► Grafana
                                    ├──► Loki (logs)
                                    └──► Tempo/Jaeger (traces)
   Prometheus rules ──► Alertmanager ──► notification
```

## Features (scope)

- RED dashboard
- SLO ও burn-rate alert
- প্রতিটি alert-এর সাথে runbook link
- অন্তত তিনটি failure simulation
- Postmortem template অনুযায়ী লেখা

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] Failure inject করলে alert fire হয় এবং runbook দিয়ে recover
- [ ] Trace থেকে slow dependency চিহ্নিত
- [ ] Error budget হিসাব report

## Resource requirements

Docker Compose বা kind, 🧠 ৮–১৬ GB RAM।

## Cleanup

Compose/cluster down এবং volume মুছে ফেলা।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
