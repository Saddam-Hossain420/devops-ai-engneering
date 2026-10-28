# P02 — Production-Style Web Application

**Status:** NOT_STARTED · **Milestone:** 3 · **Track:** A · **পূর্বশর্ত:** Module 05, Module 06, Module 09, Module 10, Module 20

## লক্ষ্য

Continuous project-এর API-কে frontend, PostgreSQL, Redis cache ও Nginx reverse proxy সহ Docker Compose-এ production-style ভাবে চালানো।

## Architecture

```text
browser ──► nginx (TLS, static, reverse proxy) ──► api (Python, non-root)
                                                    ├──► postgres (volume)
                                                    └──► redis (cache)
```

## Features (scope)

- সব service-এ health check
- Named volume-এ persistent DB
- `.env.example` ও secret file দিয়ে configuration
- Structured JSON log
- Non-root, read-only filesystem যেখানে সম্ভব
- এক command-এ start (`make up`) ও আলাদা cleanup (`make down`)

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] `docker compose ps` এ সব service healthy
- [ ] Container restart-এর পরে data থাকে
- [ ] DB বন্ধ করলে API `/health` 503 দেয় এবং log-এ কারণ লেখা থাকে
- [ ] Image-এ কোনো secret নেই (`docker history` ও scan দিয়ে যাচাই)
- [ ] Integration test পাস

## Resource requirements

Docker Engine + Compose plugin, ৪ GB RAM।

## Cleanup

`docker compose down` (data রাখে) / ⚠️ `docker compose down -v` (volume সহ data মুছে দেয়)।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
