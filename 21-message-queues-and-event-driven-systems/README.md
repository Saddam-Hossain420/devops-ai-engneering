# Module 21 — Message Queues and Event-Driven Systems

**Stage:** 12 · **Lesson:** 7 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Asynchronous processing, queue বনাম stream, RabbitMQ/Redis queue, Kafka, delivery guarantee, idempotency, retry ও DLQ এবং event-driven architecture কখন দরকার — কখন নয়।

## পূর্বশর্ত (Prerequisites)

[20-databases-and-distributed-systems](../20-databases-and-distributed-systems/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- At-least-once ও idempotent consumer
- Retry ও DLQ design
- Queue বনাম stream বাছাই

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L21-01 | Asynchronous processing কেন | Beginner |  | NOT_STARTED |
| L21-02 | Queue বনাম stream | Intermediate |  | NOT_STARTED |
| L21-03 | RabbitMQ / Redis-ভিত্তিক queue | Intermediate |  | NOT_STARTED |
| L21-04 | Kafka fundamentals | Advanced | 🧠 | NOT_STARTED |
| L21-05 | Delivery guarantee ও idempotency | Advanced |  | NOT_STARTED |
| L21-06 | Retry ও dead-letter queue | Intermediate |  | NOT_STARTED |
| L21-07 | Event-driven architecture: কখন দরকার, কখন নয় | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `21-message-queues-and-event-driven-systems/LNN-MM-slug.md`

## Labs

Lab folder: `labs/21-message-queues-and-event-driven-systems/`

- Level A — Python producer/consumer
- Level B — worker + retry + DLQ
- Level C — duplicate message ও consumer crash

## সংশ্লিষ্ট project

—

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Poison message DLQ-তে যায় এবং reprocess করা যায়

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
