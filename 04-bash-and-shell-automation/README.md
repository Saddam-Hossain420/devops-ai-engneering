# Module 04 — Bash and Shell Automation

**Stage:** 3 · **Lesson:** 8 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Production-যোগ্য Bash script: strict mode ও তার সীমা, variable/array, function, error handling ও trap, argument parsing, locking, dry-run, ShellCheck ও bats testing এবং কখন Python-এ যেতে হবে।

## পূর্বশর্ত (Prerequisites)

[01-linux-systems](../01-linux-systems/README.md), [03-git-and-collaboration](../03-git-and-collaboration/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Strict mode-এর আচরণ ও সীমাবদ্ধতা ব্যাখ্যা
- trap দিয়ে cleanup ও error handling
- Idempotent, dry-run সমর্থিত script লেখা
- ShellCheck ও bats দিয়ে যাচাই

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L04-01 | [Bash script-এর গঠন ও strict mode (এবং এর সীমাবদ্ধতা)](L04-01-script-structure-strict-mode.md) | Beginner |  | COMPLETED |
| L04-02 | [Variable, array ও parameter expansion](L04-02-variables-arrays-expansion.md) | Beginner |  | COMPLETED |
| L04-03 | [Function ও reusable script](L04-03-functions-reusable-scripts.md) | Beginner |  | COMPLETED |
| L04-04 | [Error handling ও trap](L04-04-error-handling-trap.md) | Intermediate |  | COMPLETED |
| L04-05 | [Argument parsing, getopts, usage ও logging](L04-05-argument-parsing-logging.md) | Intermediate |  | COMPLETED |
| L04-06 | [Safe ও idempotent script: locking, temp file, dry-run](L04-06-safe-idempotent-scripts.md) | Intermediate |  | COMPLETED |
| L04-07 | [ShellCheck ও bats দিয়ে testing](L04-07-shellcheck-bats-testing.md) | Intermediate |  | COMPLETED |
| L04-08 | [কখন Bash, কখন Python](L04-08-bash-or-python.md) | Beginner |  | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `04-bash-and-shell-automation/LNN-MM-slug.md`

## Labs

Lab folder: [labs/04-bash-and-shell-automation/](../labs/04-bash-and-shell-automation/README.md) · Module quiz: [assessments/04-bash-and-shell-automation/quiz.md](../assessments/04-bash-and-shell-automation/quiz.md)

- Level A — quoting ও expansion: আগে অনুমান, তারপর যাচাই
- Level B — log archive + backup script: lock, dry-run, atomic, test, systemd timer
- Level C — চারটি ফাঁদযুক্ত ভাঙা script debug ও repair (`bash -x`, trap, linter)

## সংশ্লিষ্ট project

[P01-linux-ops-toolkit](../projects/P01-linux-ops-toolkit/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] ShellCheck-clean একটি backup script, bats test সহ

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
