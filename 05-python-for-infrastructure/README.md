# Module 05 — Python for Infrastructure

**Stage:** 3 · **Lesson:** 13 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Infrastructure automation-এর জন্য Python: environment, file, subprocess, JSON/YAML, HTTP API, logging, CLI, testing, secret handling, log analysis ও health check tool। শেষে continuous project-এর প্রথম web API তৈরি হয়।

## পূর্বশর্ত (Prerequisites)

[04-bash-and-shell-automation](../04-bash-and-shell-automation/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- venv ও dependency pin দিয়ে reproducible environment
- subprocess ও HTTP নিরাপদভাবে (timeout, retry) ব্যবহার
- Structured logging ও exception handling
- pytest দিয়ে unit ও integration test
- Continuous project-এর প্রথম API চালানো

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L05-01 | [Python environment: version, venv, pip, pyproject](L05-01-python-environment.md) | Beginner |  | COMPLETED |
| L05-02 | [Ops-এর জন্য Python fundamentals ও type hint](L05-02-python-fundamentals-type-hints.md) | Beginner |  | COMPLETED |
| L05-03 | [File, directory ও pathlib](L05-03-files-and-pathlib.md) | Beginner |  | COMPLETED |
| L05-04 | [subprocess নিরাপদভাবে চালানো](L05-04-subprocess-safely.md) | Intermediate |  | COMPLETED |
| L05-05 | [JSON, YAML ও configuration processing](L05-05-json-yaml-config.md) | Beginner |  | COMPLETED |
| L05-06 | [HTTP client ও API: timeout, retry, error handling](L05-06-http-client-retry.md) | Intermediate |  | COMPLETED |
| L05-07 | [Logging, structured log ও exception](L05-07-logging-structured.md) | Intermediate |  | COMPLETED |
| L05-08 | [argparse দিয়ে CLI tool](L05-08-argparse-cli.md) | Beginner |  | COMPLETED |
| L05-09 | [pytest দিয়ে unit ও integration testing](L05-09-pytest-testing.md) | Intermediate |  | COMPLETED |
| L05-10 | [Secret ও configuration: env var, .env, secret manager](L05-10-secrets-and-config.md) | Intermediate |  | COMPLETED |
| L05-11 | [Log analysis tool তৈরি](L05-11-log-analysis-tool.md) | Intermediate |  | COMPLETED |
| L05-12 | [Health check ও backup verification tool](L05-12-healthcheck-backup-verify.md) | Intermediate |  | COMPLETED |
| L05-13 | [Continuous project শুরু: প্রথম Python web API](L05-13-taskflow-api-v01.md) | Intermediate |  | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `05-python-for-infrastructure/LNN-MM-slug.md`

## Labs

Lab folder: [labs/05-python-for-infrastructure/](../labs/05-python-for-infrastructure/README.md) · Module quiz: [assessments/05-python-for-infrastructure/quiz.md](../assessments/05-python-for-infrastructure/quiz.md)

- Level A — pathlib, json ও subprocess: ১৫টি experiment, আগে অনুমান তারপর যাচাই
- Level B — TaskFlow-এর JSON access log-এর report tool (test + grader) ও health check
- Level C — চারটি ফাঁদযুক্ত API sync tool: hang, ভাঙা JSON, HTML 502, 503, অপ্রাপ্য API

## সংশ্লিষ্ট project

[P01-linux-ops-toolkit](../projects/P01-linux-ops-toolkit/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Log analyzer ও health checker test সহ
- [ ] Continuous project v0.1 চালু ও test পাস

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
