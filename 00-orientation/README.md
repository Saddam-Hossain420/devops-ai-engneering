# Module 00 — Engineering Orientation

**Stage:** 0 · **Lesson:** 7 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

DevOps আসলে কী, বিভিন্ন engineering role-এর দায়িত্ব কোথায় মেলে আর কোথায় আলাদা, software কীভাবে idea থেকে production-এ যায়, এবং experiment ও measurement দিয়ে কীভাবে শিখতে হয় — এই module সেই মানসিক কাঠামো তৈরি করে। শেষে Ubuntu lab environment প্রস্তুত হবে।

## পূর্বশর্ত (Prerequisites)

নেই — এখান থেকেই শুরু

## Learning outcomes

এই module শেষে আপনি পারবেন:

- DevOps-কে tool নয়, culture ও feedback loop হিসেবে ব্যাখ্যা করতে পারা
- DevOps, SRE, Platform, Cloud, Security, MLOps, AI Infra role-এর পার্থক্য বলতে পারা
- SDLC, Agile, Scrum, Kanban ও environment promotion বুঝতে পারা
- Architecture diagram ও ADR লিখতে পারা
- নিজের Ubuntu lab environment ও engineering notebook প্রস্তুত করা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L00-01 | [DevOps আসলে কী: culture, feedback loop ও DORA metrics](L00-01-what-is-devops.md) | Beginner |  | COMPLETED |
| L00-02 | [Engineering roles: DevOps, SRE, Platform, Cloud, Security, MLOps, AI Infra](L00-02-engineering-roles.md) | Beginner |  | COMPLETED |
| L00-03 | [SDLC, Agile, Scrum, Kanban ও release management](L00-03-sdlc-agile-release.md) | Beginner |  | COMPLETED |
| L00-04 | [Environments: development, testing, staging, production](L00-04-environments.md) | Beginner |  | COMPLETED |
| L00-05 | [Architecture diagram ও technical documentation (C4, ADR, docs-as-code)](L00-05-diagrams-and-docs.md) | Beginner |  | COMPLETED |
| L00-06 | [Experiment, log, measurement ও incident analysis দিয়ে শেখা](L00-06-learning-by-experiment.md) | Beginner |  | COMPLETED |
| L00-07 | [Lab environment setup: Ubuntu (VM/native/WSL2), Python venv, notebook](L00-07-lab-environment-setup.md) | Beginner | 🖥️ | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `00-orientation/LNN-MM-slug.md`

## Labs

Lab folder: [labs/00-orientation/](../labs/00-orientation/README.md) · Module quiz: [assessments/00-orientation/quiz.md](../assessments/00-orientation/quiz.md)

- Level A — DORA metric হিসাব করা
- Level B — একটি ছোট team-এর delivery process diagram ও ADR লেখা
- Level C — একটি কাল্পনিক failed deployment-এর timeline থেকে incident analysis

## সংশ্লিষ্ট project

—

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] DORA metric calculator চালিয়ে ব্যাখ্যা করা
- [ ] নিজের lab environment-এর verification script সফলভাবে চলা

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
