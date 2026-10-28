# Module 22 — Data Engineering

**Stage:** 12 · **Lesson:** 7 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Batch ও streaming pipeline, data validation, Airflow/Dagster orchestration, lineage, observability, recovery ও backfill।

## পূর্বশর্ত (Prerequisites)

[05-python-for-infrastructure](../05-python-for-infrastructure/README.md), [21-message-queues-and-event-driven-systems](../21-message-queues-and-event-driven-systems/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Idempotent batch pipeline লেখা
- Data validation gate
- Backfill নিরাপদে চালানো

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L22-01 | Data pipeline concept | Beginner |  | NOT_STARTED |
| L22-02 | Batch pipeline | Intermediate |  | NOT_STARTED |
| L22-03 | Streaming pipeline | Advanced |  | NOT_STARTED |
| L22-04 | Data validation | Intermediate |  | NOT_STARTED |
| L22-05 | Workflow orchestration: Airflow / Dagster | Advanced | 🧠 | NOT_STARTED |
| L22-06 | Data lineage ও pipeline observability | Advanced |  | NOT_STARTED |
| L22-07 | Pipeline recovery ও backfill | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `22-data-engineering/LNN-MM-slug.md`

## Labs

Lab folder: `labs/22-data-engineering/`

- Level A — CSV → validate → Parquet
- Level B — orchestrated pipeline
- Level C — ভাঙা input-এ pipeline fail ও recovery

## সংশ্লিষ্ট project

—

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Validation সহ batch pipeline এবং একটি সফল backfill

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
