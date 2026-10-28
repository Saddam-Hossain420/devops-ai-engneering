# Module 03 — Git and Collaboration

**Stage:** 3 · **Lesson:** 6 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Git ভেতর থেকে (object, ref), branch/merge/rebase, remote ও tag, pull request ও code review, ভুল থেকে recovery এবং GitHub Actions-এর ভিত্তি।

## পূর্বশর্ত (Prerequisites)

[01-linux-systems](../01-linux-systems/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Git object model ব্যাখ্যা করা
- Merge vs rebase বেছে নেওয়া ও conflict সমাধান
- Protected branch ও review workflow সেট করা
- reflog/revert/bisect দিয়ে recovery
- প্রথম GitHub Actions workflow লেখা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L03-01 | [Git internals: object, commit, tree, ref](L03-01-git-internals.md) | Intermediate |  | COMPLETED |
| L03-02 | [Branch, merge ও rebase](L03-02-branch-merge-rebase.md) | Beginner |  | COMPLETED |
| L03-03 | [Remote, tag ও semantic versioning](L03-03-remotes-tags-semver.md) | Beginner |  | COMPLETED |
| L03-04 | [Pull request, code review, protected branch, CODEOWNERS](L03-04-pull-requests-review.md) | Beginner |  | COMPLETED |
| L03-05 | [Git recovery: reflog, reset, revert, bisect](L03-05-git-recovery.md) | Intermediate |  | COMPLETED |
| L03-06 | [GitHub Actions fundamentals](L03-06-github-actions-fundamentals.md) | Beginner |  | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `03-git-and-collaboration/LNN-MM-slug.md`

## Labs

Lab folder: [labs/03-git-and-collaboration/](../labs/03-git-and-collaboration/README.md) · Module quiz: [assessments/03-git-and-collaboration/quiz.md](../assessments/03-git-and-collaboration/quiz.md)

- Level A — `.git`-এর ভেতর object অনুসন্ধান (add, commit, amend, tag, gc)
- Level B — branch, conflict, CODEOWNERS, workflow lint, SemVer tag দিয়ে release; GitHub-এ PR
- Level C — পাঁচটি দুর্ঘটনা থেকে recovery: reset, মুছে ফেলা branch, force push, push-হওয়া খারাপ commit, regression

## সংশ্লিষ্ট project

—

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] ইচ্ছাকৃত হারানো commit reflog দিয়ে উদ্ধার
- [ ] PR-ভিত্তিক workflow-তে একটি পরিবর্তন merge

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
