# Module 04 Progress — Bash and Shell Automation

Content status: `NOT_STARTED` · `IN_PROGRESS` · `COMPLETED` · `NEEDS_REVISION` (Claude update করবে)  
Learner status: Not started · In progress · Practiced · Assessment passed · Project completed · Needs revision (আপনি update করবেন)

| ID | Lesson | Content | Learner | Required files | Validation | Prerequisites | Next |
|---|---|---|---|---|---|---|---|
| L04-01 | [Bash script-এর গঠন ও strict mode (এবং এর সীমাবদ্ধতা)](L04-01-script-structure-strict-mode.md) | COMPLETED | Not started | `L04-01-script-structure-strict-mode.md`, `code/L04-01/strict_mode_demo.sh`, `script_template.sh`, `test_l04_01.py` | 8 unit test pass (Bash 5.3, ১৮টি strict-mode case); template-এর IFS bug ধরা ও ঠিক; Ubuntu Bash 5.2-এ চালানো হয়নি | L03-06 | L04-02 |
| L04-02 | [Variable, array ও parameter expansion](L04-02-variables-arrays-expansion.md) | COMPLETED | Not started | `L04-02-variables-arrays-expansion.md`, `code/L04-02/expansion_lab.sh`, `rename_ext.sh`, `test_l04_02.py` | 7 unit test pass (Bash 5.3; নামে newline/space/শুরুতে - সহ rename); demo-র [@]/[*] ভুল ধরা ও ঠিক; Ubuntu-তে চালানো হয়নি | L04-01 | L04-03 |
| L04-03 | [Function ও reusable script](L04-03-functions-reusable-scripts.md) | COMPLETED | Not started | `L04-03-functions-reusable-scripts.md`, `code/L04-03/lib/common.sh`, `disk_check.sh`, `sample-df.txt`, `test_l04_03.py` | 9 unit test pass; আসল df-এ parser bug ও to_bytes-এর array bug ধরা ও ঠিক; Ubuntu-র আসল df-এ চালানো হয়নি | L04-02 | L04-04 |
| L04-04 | [Error handling ও trap](L04-04-error-handling-trap.md) | COMPLETED | Not started | `L04-04-error-handling-trap.md`, `code/L04-04/trap_demo.sh`, `safe_job.sh`, `test_l04_04.py` | 6 unit test pass (সফল/ব্যর্থ/SIGTERM-এ cleanup, child বন্ধ /proc দিয়ে যাচাই); অনাথ child bug আসলে দেখা ও ঠিক; Ubuntu-তে চালানো হয়নি | L04-03 | L04-05 |
| L04-05 | [Argument parsing, getopts, usage ও logging](L04-05-argument-parsing-logging.md) | COMPLETED | Not started | `L04-05-argument-parsing-logging.md`, `code/L04-05/getopts_demo.sh`, `backup.sh`, `test_l04_05.py` | 9 unit test pass (আসল tar.gz); ৩টি bug ধরা ও ঠিক (quiet log file, path normalization, tar host:path); Ubuntu-তে চালানো হয়নি | L04-04 | L04-06 |
| L04-06 | [Safe ও idempotent script: locking, temp file, dry-run](L04-06-safe-idempotent-scripts.md) | COMPLETED | Not started | `L04-06-safe-idempotent-scripts.md`, `code/L04-06/backup_safe.sh`, `test_backup_safe.py` | 6 unit test pass (mkdir lock fallback, idempotency, rotation dry-run=real, tar failure); dry-run rotation bug ধরা ও ঠিক; flock পথ Ubuntu-তে চালানো হয়নি | L04-05 | L04-07 |
| L04-07 | [ShellCheck ও bats দিয়ে testing](L04-07-shellcheck-bats-testing.md) | COMPLETED | Not started | `L04-07-shellcheck-bats-testing.md`, `code/L04-07/shlint_mini.py`, `run_checks.sh`, `shellcheckrc`, `sample-bad.sh`, `tests/backup_safe.bats`, `tests/rename_ext.bats`, `test_l04_07.py` | 10 test (7 pass, 3 opt-in skip); shlint_mini L04-01 template-এর SC2155 bug ধরেছে; ShellCheck ও bats এই machine-এ নেই ও install-এর অনুমতি মেলেনি — চালানো হয়নি, Ubuntu-তে বাকি | L04-06 | L04-08 |
| L04-08 | [কখন Bash, কখন Python](L04-08-bash-or-python.md) | COMPLETED | Not started | `L04-08-bash-or-python.md`, `code/L04-08/gen_log.py`, `top_errors.sh`, `top_errors.py`, `test_l04_08.py`; labs A/B/C (`labs/04-bash-and-shell-automation/`, Lab C-এর break-it/check/reset.sh); module quiz | 4 unit test pass (Bash বনাম Python, ২ লক্ষ লাইনে সময় মাপা); দুটি ভুল প্রত্যাশা ও Python regex bug নথিভুক্ত; Lab C break→fix→check ALL PASSED (Windows); Ubuntu-তে চালানো হয়নি | L04-07 | L05-01 |

## Module assessment

| Assessment | Score | তারিখ |
|---|---|---|
| [Module quiz](../assessments/04-bash-and-shell-automation/quiz.md) | — | — |
| [Level A lab](../labs/04-bash-and-shell-automation/A-quoting-expansion/README.md) | — | — |
| [Level B lab](../labs/04-bash-and-shell-automation/B-backup-with-locking/README.md) | — | — |
| [Level C lab](../labs/04-bash-and-shell-automation/C-broken-script/README.md) | — | — |
