# Lab 04-B — Log archive + backup: locking, dry-run, timer ও test

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ৯০–১২০ মিনিট |
| **Environment** | Ubuntu VM (systemd timer অংশের জন্য); বাকি অংশ Git Bash-এও |
| **Label** | ⚠️ Part 3 একটি user-level systemd timer তৈরি করে — শেষে cleanup ধাপ অনুসরণ করুন |

## Objective

এই module-এর সব কৌশল একসাথে প্রয়োগ করে একটি **production-যোগ্য `archive_logs.sh`** লিখুন। এটি L04-02 থেকে L04-06-এর mini-project-এর সম্মিলিত রূপ। পরে L04-06-এর `backup_safe.sh` দিয়ে archive-এর backup নিয়ে একটি timer-এ চালান।

## Prerequisites

- Lesson: L04-01 থেকে L04-07; [L01-11 — systemd timer](../../../01-linux-systems/L01-11-scheduling-jobs.md)

## Environment setup

```bash
mkdir -p ~/lab04b/{logs,archive,backups} && cd ~/lab04b
for d in 01 02 03; do printf 'line\n%.0s' {1..50} > "logs/app-2026-09-$d.log"; done
printf 'x\n' > "logs/worker 2026-09-04.log"      # নামে space
touch -d '40 days ago' logs/*.log                # Git Bash-এ কাজ না করলে Step 1-এ --days 0 দিন
touch logs/current.log                           # আজকের — archive হবে না
```

## Steps

### Part 1 — `archive_logs.sh` লেখা

1. [`script_template.sh`](../../../04-bash-and-shell-automation/code/L04-01/script_template.sh) থেকে শুরু করে `archive_logs.sh` লিখুন, যাতে নিচের সবগুলো থাকে:
   - `--dir`, `--dest`, `--days N`, `--execute` (**default dry-run**), `-v`/`-q`, `--help` (L04-05)।
   - `find -print0` দিয়ে N দিনের পুরোনো `*.log` (L04-02)।
   - নামের তারিখ অনুযায়ী `archive/YYYY-MM.tar.gz` (parameter expansion)।
   - Temp-এ লেখা → `tar -t` দিয়ে যাচাই → atomic `mv`; শুধু তারপর মূল log মোছা (L04-04, L04-06)।
   - Lock (`flock`, না থাকলে `mkdir` fallback); ব্যস্ত হলে exit ৭৫।
   - `trap` দিয়ে cleanup; ERR trap-এ লাইন নম্বর।
2. **Dry-run যাচাই:** `bash archive_logs.sh --dir logs --dest archive --days 30` — কী করবে তা দেখায়, কিছু বদলায় না (`ls logs` আগের মতো)।
3. **আসল run:** `--execute` — archive তৈরি হয়, পুরোনো log মোছে, `current.log` থাকে।
4. **Idempotency:** আবার চালান — কিছু করার নেই, exit ০।

### Part 2 — Test

5. Python unittest (এই repository-র রীতি) অথবা bats দিয়ে অন্তত পাঁচটি test:
   - dry-run কিছু বদলায় না;
   - space-যুক্ত নাম;
   - যাচাই ব্যর্থ হলে মূল log থাকে (নকল `tar` দিয়ে — L04-06-এর পদ্ধতি);
   - একসাথে দুটি run → ৭৫;
   - usage error → ২।
6. `shlint_mini.py` (এবং Ubuntu-তে `shellcheck`) — শূন্য finding।

### Part 3 — Timer ও backup (Ubuntu VM)

7. `~/.config/systemd/user/lab04b-archive.service` ও `.timer` (প্রতিদিন) তৈরি করুন:
   - service আগে `archive_logs.sh --execute` চালাবে, তারপর `backup_safe.sh -s ~/lab04b/archive -d ~/lab04b/backups -k 3`;
   - `systemctl --user daemon-reload && systemctl --user enable --now lab04b-archive.timer`।
8. `systemctl --user start lab04b-archive.service` দিয়ে একবার হাতে চালিয়ে `journalctl --user -u lab04b-archive -n 20` দেখুন।

## Expected behavior

- Dry-run: শুধু পরিকল্পনা ছাপে।
- `--execute`: `archive/2026-09.tar.gz`-এ চারটি file (space-যুক্ত নামসহ); `logs/`-এ শুধু `current.log`।
- দ্বিতীয় run: "nothing to do"।
- Timer: journal-এ দুটি ধাপের log; `backups/`-এ একটি archive-এর backup।

## Verification

```bash
tar -tzf ~/lab04b/archive/2026-09.tar.gz           # ৪টি log
ls ~/lab04b/logs                                   # current.log
python3 -m unittest -v                             # আপনার test, সব পাস
systemctl --user list-timers | grep lab04b         # (Ubuntu)
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `touch -d` কাজ করে না | পুরোনো বা ভিন্ন `touch` | `--days 0` দিয়ে পরীক্ষা |
| Timer চলে না | `daemon-reload` হয়নি, বা user session নেই | `loginctl enable-linger $USER` (VM-এ) |
| Archive-এ নাম ভাঙা | Unquoted variable | L04-02; `find -print0` + `tar --null -T -` |
| `flock` নেই | Git Bash | `mkdir` fallback (L04-06) |

## Cleanup / reset

```bash
systemctl --user disable --now lab04b-archive.timer 2>/dev/null
rm -f ~/.config/systemd/user/lab04b-archive.{service,timer} && systemctl --user daemon-reload
rm -rf ~/lab04b
```

## Assessment

1. আপনার script-এর প্রতিটি নিরাপত্তা-বৈশিষ্ট্য কোন lesson থেকে, এবং কোন ভুল আটকায়?
2. Dry-run ও আসল run যে একই পথে যায়, তা কীভাবে নিশ্চিত করলেন (L04-06 Section 9.3)?
3. কোন অংশ Python-এ লিখলে ভালো হতো (L04-08)?
