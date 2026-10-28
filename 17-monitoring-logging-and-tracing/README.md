# Module 17 — Monitoring, Logging and Tracing

**Stage:** 10 · **Lesson:** 11 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Metric, log, trace, profile; Prometheus, PromQL, instrumentation, Grafana, Alertmanager, Loki, OpenTelemetry, RED/USE এবং পূর্ণ monitoring stack।

## পূর্বশর্ত (Prerequisites)

[14-kubernetes](../14-kubernetes/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Python app instrument করা
- PromQL দিয়ে latency percentile ও error rate
- Actionable alert design
- Trace দিয়ে slow request খুঁজে বের করা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L17-01 | Observability: metric, log, trace, profile | Beginner |  | NOT_STARTED |
| L17-02 | Prometheus architecture ও metric type | Intermediate |  | NOT_STARTED |
| L17-03 | PromQL | Intermediate |  | NOT_STARTED |
| L17-04 | Python application instrumentation | Intermediate |  | NOT_STARTED |
| L17-05 | Grafana dashboard | Intermediate |  | NOT_STARTED |
| L17-06 | Alertmanager ও actionable alert design | Intermediate |  | NOT_STARTED |
| L17-07 | Logging pipeline ও structured log (Loki) | Intermediate |  | NOT_STARTED |
| L17-08 | OpenTelemetry ও distributed tracing | Advanced |  | NOT_STARTED |
| L17-09 | RED ও USE method | Intermediate |  | NOT_STARTED |
| L17-10 | Continuous profiling | Advanced |  | NOT_STARTED |
| L17-11 | Deployed application-এর জন্য পূর্ণ monitoring stack | Advanced | 🧠 | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `17-monitoring-logging-and-tracing/LNN-MM-slug.md`

## Labs

Lab folder: `labs/17-monitoring-logging-and-tracing/`

- Level A — Prometheus scrape ও PromQL
- Level B — metrics + logs + traces stack
- Level C — latency spike-এর কারণ trace থেকে খোঁজা

## সংশ্লিষ্ট project

[P08-observability-incident-response](../projects/P08-observability-incident-response/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Monitoring stack চালু এবং simulated failure dashboard ও alert-এ দেখা যায়

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
