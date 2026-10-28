# Module 13 — Ansible and Configuration Management

**Stage:** 7 · **Lesson:** 9 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Configuration management ও Terraform-এর সাথে দায়িত্বের পার্থক্য, inventory, playbook, variable, template, handler, role, Vault, idempotency testing এবং application deploy।

## পূর্বশর্ত (Prerequisites)

[06-web-server-and-reverse-proxy](../06-web-server-and-reverse-proxy/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Terraform বনাম Ansible-এর সীমা ব্যাখ্যা
- Idempotent role লেখা
- Vault দিয়ে secret
- Clean server থেকে app deploy ও health verify

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L13-01 | Configuration management: Terraform বনাম Ansible | Beginner |  | NOT_STARTED |
| L13-02 | Inventory ও ad-hoc command | Beginner |  | NOT_STARTED |
| L13-03 | Playbook ও module | Beginner |  | NOT_STARTED |
| L13-04 | Variable, fact ও Jinja2 template | Intermediate |  | NOT_STARTED |
| L13-05 | Loop, conditional ও handler | Intermediate |  | NOT_STARTED |
| L13-06 | Role ও collection | Intermediate |  | NOT_STARTED |
| L13-07 | Ansible Vault ও secret | Intermediate |  | NOT_STARTED |
| L13-08 | Idempotency, check mode ও Molecule testing | Advanced |  | NOT_STARTED |
| L13-09 | Ansible দিয়ে application deploy | Advanced | 🔗 | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `13-ansible-and-configuration-management/LNN-MM-slug.md`

## Labs

Lab folder: `labs/13-ansible-and-configuration-management/`

- Level A — container-কে target করে ad-hoc command
- Level B — Nginx + app role
- Level C — configuration drift detect ও fix

## সংশ্লিষ্ট project

[P05-ansible-configuration](../projects/P05-ansible-configuration/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 5: দ্বিতীয় run-এ changed=0

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
