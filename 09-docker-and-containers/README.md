# Module 09 — Docker and Containers

**Stage:** 5 · **Lesson:** 14 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Container বনাম VM, Docker architecture ও OCI, image ও layer, Dockerfile, multi-stage build, digest, config/secret, health check, logging, security, registry ও scanning, Docker Compose এবং multi-container ও WordPress stack।

## পূর্বশর্ত (Prerequisites)

[01-linux-systems](../01-linux-systems/README.md), [02-computer-networking](../02-computer-networking/README.md), [05-python-for-infrastructure](../05-python-for-infrastructure/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Container-কে namespace + cgroup হিসেবে ব্যাখ্যা
- ছোট, non-root, multi-stage image তৈরি
- Compose দিয়ে proxy + API + DB + cache stack
- Container crash/OOM/health check failure debug

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L09-01 | Container বনাম virtual machine | Beginner |  | NOT_STARTED |
| L09-02 | Docker architecture: daemon, containerd, runc, OCI | Intermediate |  | NOT_STARTED |
| L09-03 | Image, layer ও registry | Beginner |  | NOT_STARTED |
| L09-04 | Dockerfile fundamentals | Beginner |  | NOT_STARTED |
| L09-05 | Multi-stage build ও image optimization | Intermediate |  | NOT_STARTED |
| L09-06 | Tag, immutable digest ও image provenance | Intermediate |  | NOT_STARTED |
| L09-07 | Environment variable, configuration ও secret | Intermediate |  | NOT_STARTED |
| L09-08 | Health check, restart policy ও resource limit | Intermediate |  | NOT_STARTED |
| L09-09 | Container logging ও debugging | Intermediate |  | NOT_STARTED |
| L09-10 | Container security: non-root, capability, read-only filesystem | Intermediate |  | NOT_STARTED |
| L09-11 | Container registry ও image scanning | Intermediate |  | NOT_STARTED |
| L09-12 | Docker Compose | Beginner |  | NOT_STARTED |
| L09-13 | Multi-container application: frontend, backend, database, reverse proxy | Intermediate | Needs L05-13 | NOT_STARTED |
| L09-14 | WordPress/PHP stack in Docker Compose | Intermediate |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `09-docker-and-containers/LNN-MM-slug.md`

## Labs

Lab folder: `labs/09-docker-and-containers/`

- Level A — layer ও cache পর্যবেক্ষণ
- Level B — continuous project-এর multi-container stack
- Level C — health check failure, memory limit OOM, ভুল env var

## সংশ্লিষ্ট project

[P02-production-web-app](../projects/P02-production-web-app/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 2 সম্পূর্ণ ও সব service healthy
- [ ] Image scan report ও ব্যাখ্যা

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
