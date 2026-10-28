# Module 04 Labs — Bash and Shell Automation

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — Quoting ও expansion](A-quoting-expansion/README.md) | A — Fundamentals | আগে অনুমান, তারপর যাচাই: word splitting, glob, `-` নাম, strict mode-এর ১৮ case, parameter expansion, array, `"$*"` | ৪৫–৬০ মিনিট | L04-01, L04-02 |
| [B — Backup with locking](B-backup-with-locking/README.md) | B — Integrated | `archive_logs.sh`: dry-run default, lock, atomic, trap; test; systemd timer + `backup_safe.sh` | ৯০–১২০ মিনিট | L04-01 – L04-07 |
| [C — Broken script](C-broken-script/README.md) | C — Failure and Recovery | চারটি ফাঁদযুক্ত report script debug ও repair; চারটি পরিস্থিতির check | ৪৫–৬০ মিনিট | L04-01, L04-02, L04-04, L04-06, L04-07 |

**Environment:**

- Lab A ও C শুধু নিজের directory-তে কাজ করে — Ubuntu, Fedora বা Git Bash-এ চলে। Lab C break → fix → check পুরোটা Windows/Git Bash-এ আসলে চালিয়ে যাচাই করা হয়েছে।
- Lab B-এর Part 3 (systemd timer) Ubuntu VM-এ।

**Module 04-এর completion criterion** "ShellCheck-clean একটি backup script, bats test সহ" → Lab B (Part 2-এ Ubuntu-তে `shellcheck` ও `bats`)।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [04-bash-and-shell-automation/PROGRESS.md](../../04-bash-and-shell-automation/PROGRESS.md)-এর Module assessment table আপডেট করুন।
