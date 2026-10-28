# Module 03 Labs — Git and Collaboration

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — Inside `.git`](A-inside-dot-git/README.md) | A — Fundamentals | Object database: add/commit/amend/tag/gc-এর প্রভাব, `git` ও Python tool মিলিয়ে | ৪৫–৬০ মিনিট | L03-01 |
| [B — PR to release](B-pr-to-release/README.md) | B — Integrated | Branch, conflict, CODEOWNERS, workflow lint, SemVer tag; GitHub-এ PR ও protection | ৯০–১২০ মিনিট | L03-02 – L03-04, L03-06 |
| [C — Git disaster recovery](C-git-disaster-recovery/README.md) | C — Failure and Recovery | পাঁচটি দুর্ঘটনা: reset, মুছে ফেলা branch, force push, push-হওয়া খারাপ commit, regression | ৬০–৯০ মিনিট | L03-01 – L03-03, L03-05 |

**Environment:** তিনটি lab-ই শুধু নিজের তৈরি directory-তে কাজ করে। Ubuntu, Fedora বা Windows-এর Git Bash-এ চলে, এবং কোনো VM লাগে না।

- Lab A ও C আপনার global Git config ব্যবহার করে না (আলাদা config file)।
- Lab B-র Part 2 নিজের GitHub practice repository-তে চলে।
- Lab C-এর `reset.sh` শুধু `.lab03c` চিহ্নযুক্ত directory মোছে।

**Module 03-এর completion criteria** ([README](../../03-git-and-collaboration/README.md)):

- "ইচ্ছাকৃত হারানো commit reflog দিয়ে উদ্ধার" → Lab C।
- "PR-ভিত্তিক workflow-তে একটি পরিবর্তন merge" → Lab B Part 2।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [03-git-and-collaboration/PROGRESS.md](../../03-git-and-collaboration/PROGRESS.md)-এর Module assessment table আপডেট করুন।
