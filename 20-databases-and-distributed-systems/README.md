# Module 20 — Databases and Distributed Systems

**Stage:** 12 · **Lesson:** 10 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

PostgreSQL, transaction ও isolation, index ও query plan, connection pooling, backup/PITR, replication, Redis caching, distributed systems-এর consistency ও failure mode এবং object storage।

## পূর্বশর্ত (Prerequisites)

[09-docker-and-containers](../09-docker-and-containers/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- EXPLAIN দিয়ে slow query বিশ্লেষণ
- Backup ও restore যাচাই
- Isolation anomaly প্রদর্শন
- Cache invalidation trade-off ব্যাখ্যা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L20-01 | Database fundamentals | Beginner |  | NOT_STARTED |
| L20-02 | PostgreSQL operation | Intermediate |  | NOT_STARTED |
| L20-03 | Transaction, ACID ও isolation level | Intermediate |  | NOT_STARTED |
| L20-04 | Index ও query planning | Intermediate |  | NOT_STARTED |
| L20-05 | Connection pooling | Intermediate |  | NOT_STARTED |
| L20-06 | Backup, restore ও point-in-time recovery | Intermediate |  | NOT_STARTED |
| L20-07 | Replication ও high availability | Advanced |  | NOT_STARTED |
| L20-08 | Redis ও caching pattern | Intermediate |  | NOT_STARTED |
| L20-09 | Distributed system: consistency, replication, partitioning, failure mode | Advanced |  | NOT_STARTED |
| L20-10 | Object storage ও data lifecycle | Intermediate |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `20-databases-and-distributed-systems/LNN-MM-slug.md`

## Labs

Lab folder: `labs/20-databases-and-distributed-systems/`

- Level A — transaction ও isolation experiment
- Level B — Postgres + PgBouncer + Redis
- Level C — replica lag ও restore drill

## সংশ্লিষ্ট project

[P02-production-web-app](../projects/P02-production-web-app/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Backup থেকে restore পরীক্ষা সফল ও নথিভুক্ত

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
