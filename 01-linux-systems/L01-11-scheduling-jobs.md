# L01-11 — cron বনাম systemd timer

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-10 — systemd](L01-10-systemd-services.md) |
| **Label** | ⚠️ timer/crontab install system বদলায় — cleanup ধাপ আছে |
| **Tested** | `cron_explain.py`: ৮টি test পাস ও উদাহরণ চালানো (Python 3.14, Windows)। Unit file দুটি লেখা হয়েছে কিন্তু **install, `systemctl list-timers`, `systemd-analyze calendar`, crontab Ubuntu-তে চালানো হয়নি** — output উদাহরণ। OnCalendar রূপান্তর `systemd-analyze calendar` দিয়ে যাচাই করুন। |

---

## 1. এই lesson-এ যা শিখবেন

- নির্ধারিত সময়ে কাজ (backup, cleanup, report) চালানোর দুটি পদ্ধতি: **cron** ও **systemd timer**।
- Cron expression-এর পাঁচটি field ও বিভ্রান্তিকর **day-of-month/day-of-week OR নিয়ম**।
- Cron-এর পরিবেশ (PATH, shell, mail) — কেন "terminal-এ চলে, cron-এ চলে না"।
- systemd timer: `OnCalendar=`, `OnBootSec=`, `Persistent=`, `RandomizedDelaySec=`।
- **Overlap** (আগের run শেষ না হতেই নতুন run) ও **missed run** সমস্যা।
- Python দিয়ে cron expression ব্যাখ্যা ও পরের run-এর সময় হিসাব।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Server-এ অনেক কাজ পুনরাবৃত্তিমূলক: রাতে backup, ঘণ্টায় log পরিষ্কার, প্রতি ৫ মিনিটে health check, মাসের শুরুতে report। মানুষ মনে রেখে হাতে চালালে ভুল হবে (L00-02-এর **toil**)। Scheduler এই কাজ নিয়মিত, পূর্বানুমেয়ভাবে করে।

কিন্তু scheduler-এর নিজস্ব ফাঁদ আছে: কাজ নীরবে ব্যর্থ হয় (কেউ জানে না backup এক মাস ধরে হচ্ছে না), server বন্ধ থাকলে run বাদ পড়ে, একটি ধীর run শেষ না হতেই পরেরটি শুরু হয়ে সংঘাত, বা সব server একই মুহূর্তে চালিয়ে একটি shared service-কে ডুবিয়ে দেয়।

## 3. সহজ ভাষায় পরিচয়

**cron:** ১৯৭০-এর দশক থেকে Unix-এ। একটি daemon (`cron`) প্রতি মিনিটে **crontab** file দেখে, সময় মিললে command চালায়।

```text
┌───────────── minute (0–59)
│ ┌─────────── hour (0–23)
│ │ ┌───────── day of month (1–31)
│ │ │ ┌─────── month (1–12)
│ │ │ │ ┌───── day of week (0–7; 0 ও 7 = রবিবার)
│ │ │ │ │
*/15 9-17 * * 1-5   /usr/local/bin/healthcheck.sh
```

**systemd timer:** একটি `.timer` unit, যা নির্দিষ্ট সময়ে একটি `.service` unit চালায়। ফলে L01-10-এর সব সুবিধা পাওয়া যায়: journal-এ log, user, resource limit, sandbox, dependency, এবং কোনো run ব্যর্থ হলে status-এ দেখা যায়।

| বিষয় | cron | systemd timer |
|---|---|---|
| Configuration | এক লাইন | দুটি file (.timer + .service) |
| Log | Default-ভাবে mail বা হারিয়ে যায় | journald-এ, `journalctl -u` |
| ব্যর্থতা দেখা | কঠিন | `systemctl status`, `--failed` |
| Server বন্ধ থাকলে বাদ পড়া run | চলে না | `Persistent=true` হলে পরে চলে |
| Resource limit / sandbox | নেই | আছে |
| একসাথে দুই run | হতে পারে | একই service আবার চালু হয় না (active থাকলে) |
| Random delay | নেই | `RandomizedDelaySec=` |
| পরিচিতি / portability | সব Unix-এ | systemd system-এ |

**এই repository-র সুপারিশ:** নতুন কাজ systemd timer-এ; cron পড়তে ও বিদ্যমান system-এ ঠিক করতে জানুন।

> **Fedora-তে:** cron daemon-এর নাম `crond` (package `cronie`), অনেক ক্ষেত্রে default-ভাবে installed নাও থাকতে পারে; Ubuntu-তে `cron` service। systemd timer দুটোতেই একই।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অ্যালার্ম ঘড়ি বনাম ব্যক্তিগত সহকারী

- **cron** = দেয়ালের অ্যালার্ম ঘড়ি: ঠিক সময়ে বাজে। আপনি ঘুমিয়ে থাকলে (server বন্ধ) বাজাটা হারিয়ে যায়। আপনি কাজটা করলেন কিনা ঘড়ি জানে না।
- **systemd timer** = ব্যক্তিগত সহকারী: সময় হলে কাজ শুরু করান, শেষ হলো কিনা খাতায় লেখেন, আপনি অনুপস্থিত থাকলে ফিরে আসার পরে মনে করিয়ে দেন (`Persistent=`), এবং একই কাজ দুবার একসাথে শুরু হতে দেন না।

### Analogy কোথায় মেলে না

- সহকারী কাজের **মান** যাচাই করেন। systemd শুধু exit code দেখে — script ভুল কাজ করে exit 0 দিলে "সফল" মনে হবে। Backup script-এর ভেতরে যাচাই (checksum, restore test) আপনাকেই লিখতে হবে।
- অ্যালার্ম ঘড়ি সবার একটা। একশো server-এর cron একই মিনিটে বাজলে (যেমন `0 0 * * *`) একটি shared backup server বা API-তে একসাথে চাপ — "thundering herd"। এজন্য `RandomizedDelaySec=`।

## 5. Real-world engineering scenario — "backup তো রোজ হয়... তাই না?"

**পরিস্থিতি:** একটি ছোট কোম্পানির database server-এ crontab:

```text
0 2 * * * pg_dump taskflow > /backup/taskflow-$(date +%F).sql
```

ছয় মাস পরে disk নষ্ট। Restore করতে গিয়ে দেখা গেল `/backup`-এ শেষ file চার মাস আগের, এবং সেটিও খালি।

**কী ভুল হয়েছিল (একাধিক):**

1. **`%` cron-এ বিশেষ অক্ষর** — crontab লাইনে `%` মানে newline (stdin)! `$(date +%F)` তাই ভেঙে যায়। `\%` লিখতে হতো।
2. **PATH:** cron-এর PATH ছোট (`/usr/bin:/bin`); `pg_dump` অন্য জায়গায় থাকলে "command not found" — কিন্তু কেউ দেখে না।
3. **Error কোথায় গেল?** cron output mail করে — server-এ mail system নেই, তাই হারিয়ে গেছে।
4. **যাচাই নেই:** খালি file-ও "backup"।
5. **Authentication:** cron-এর environment-এ database password বা `.pgpass` খুঁজে পায়নি।

**systemd timer + ভালো script-এ যা ভিন্ন হতো:** প্রতিটি run journal-এ; ব্যর্থ হলে `systemctl --failed`-এ লাল; script নিজে file-এর আকার ও checksum যাচাই করে exit 1 দিত; monitoring "শেষ সফল backup কখন" দেখে alert দিত (Module 17, 30)।

**শিক্ষা:** Scheduled job-এর জন্য তিনটি প্রশ্ন: (১) চললো কিনা জানবো কীভাবে? (২) ব্যর্থ হলে কে জানবে? (৩) ফলাফল ঠিক কিনা কে যাচাই করবে?

## 6. Diagram — timer কীভাবে service চালায়

```text
 ops-memcheck.timer                         ops-memcheck.service
 ┌─────────────────────────┐   সময় হলে    ┌────────────────────────────┐
 │ OnCalendar=*:0/5         │ ───────────► │ Type=oneshot                │
 │ RandomizedDelaySec=30    │   activate   │ User=nobody, sandbox, limit │
 │ Persistent=true          │              │ ExecStart=... mem_report.py │
 └─────────────────────────┘              └──────────────┬─────────────┘
          ▲                                               │ stdout/stderr
          │ enable (timers.target)                        ▼
      systemctl list-timers                         journald  ──► journalctl -u ops-memcheck
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| crontab | User-এর scheduled command-এর তালিকা (`crontab -e`) |
| `/etc/crontab`, `/etc/cron.d/` | System-wide cron (এখানে user field আছে) |
| `/etc/cron.daily/` ইত্যাদি | দৈনিক/সাপ্তাহিক script-এর folder (Ubuntu-তে anacron/timer চালায়) |
| anacron | বন্ধ থাকা সময়ের দৈনিক/সাপ্তাহিক কাজ পরে চালানোর tool |
| `.timer` unit | systemd-এর scheduler unit |
| `OnCalendar=` | ক্যালেন্ডার-ভিত্তিক সময় (যেমন `Mon..Fri *-*-* 09:00:00`) |
| `OnBootSec=`, `OnUnitActiveSec=` | Boot-এর পরে / শেষ run-এর পরে নির্দিষ্ট সময় (monotonic timer) |
| `Persistent=true` | বন্ধ থাকা সময়ের বাদ পড়া run পরের চালুতে চালানো |
| `RandomizedDelaySec=` | এলোমেলো দেরি — একসাথে সব server না চালাতে |
| Overlap | আগের run শেষ না হতেই নতুন run |
| `flock` | File lock দিয়ে একসাথে একটিমাত্র instance নিশ্চিত করা |
| Thundering herd | একই মুহূর্তে অনেক client একসাথে একটি resource-এ ঝাঁপিয়ে পড়া |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Cron-এর পরিবেশ

Cron job interactive login-এর মতো environment পায় না:

- `SHELL=/bin/sh` (Ubuntu-তে dash — L01-06); `PATH` ছোট।
- `~/.bashrc` পড়া হয় না — সেখানে set করা alias/variable নেই।
- Current directory = user-এর home।
- Output (stdout/stderr) mail করা হয় (MAILTO); mail না থাকলে হারায়।
- `%` = newline — `\%` লিখুন।

তাই crontab-এ: absolute path, script-এর ভেতরে `set -euo pipefail` ও নিজস্ব logging, এবং output স্পষ্টভাবে redirect (`>> /var/log/job.log 2>&1` অথবা `| logger -t job` → journal)।

### 8.2 Day-of-month ও day-of-week — OR নিয়ম

`0 0 1 * 1` দেখে মনে হয় "মাসের ১ তারিখ **যদি** সোমবার হয়"। আসলে cron-এর নিয়ম: দুটোই `*` না হলে **যেকোনো একটি মিললেই** চলে — "মাসের ১ তারিখে **এবং** প্রতি সোমবারে"। এটি অনেক পুরোনো, বহু-আলোচিত আচরণ। এই lesson-এর `cron_explain.py` এটি সঠিকভাবে দেখায় এবং OnCalendar রূপান্তরে সতর্ক করে, কারণ systemd-এর `OnCalendar=`-এ weekday ও তারিখ **দুটোই** মিলতে হয় (AND)।

### 8.3 OnCalendar syntax

```text
DayOfWeek Year-Month-Day Hour:Minute:Second
Mon..Fri  *-*-*          09:00:00          ← সপ্তাহের দিনে ৯টায়
          *-*-*          *:0/5:00          ← প্রতি ৫ মিনিট (shorthand: *:0/5)
          *-*-01         03:00:00          ← প্রতি মাসের ১ তারিখ
daily = *-*-* 00:00:00   hourly, weekly, monthly — shorthand
```

`systemd-analyze calendar 'Mon..Fri 09:00'` দিয়ে যেকোনো expression যাচাই ও পরের সময় দেখা যায় — **সবসময় এটি দিয়ে নিশ্চিত হোন**।

### 8.4 Overlap প্রতিরোধ

- systemd: একটি `.service` ইতিমধ্যে active থাকলে timer তাকে আবার চালু করে না — স্বাভাবিকভাবেই overlap নেই।
- cron: নিজে নিশ্চিত করতে হয় — `flock`:

  ```text
  */5 * * * * /usr/bin/flock -n /run/lock/healthcheck.lock /usr/local/bin/healthcheck.sh
  ```

  `-n` = lock না পেলে অপেক্ষা না করে বেরিয়ে যাও।

### 8.5 Timezone ও daylight saving

Cron ও timer system timezone-এ চলে (`timedatectl`)। Daylight saving-যুক্ত অঞ্চলে ০২:৩০-এর job বছরে একদিন বাদ পড়তে বা দুবার চলতে পারে। Server-এ প্রায়ই UTC ব্যবহার করা হয়; `OnCalendar=`-এ timezone নির্দিষ্ট করা যায় (যেমন `... 09:00 Asia/Dhaka`)। বাংলাদেশে daylight saving নেই, কিন্তু আপনার server অন্য অঞ্চলে থাকতে পারে।

## 9. Practical demonstration (Ubuntu VM)

### 9.1 Cron expression বুঝুন — Python

File: [`code/L01-11/cron_explain.py`](code/L01-11/cron_explain.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-11
python3 cron_explain.py "*/15 9-17 * * 1-5" --count 4 --start 2026-10-26T08:50
python3 cron_explain.py "30 2 * * 0" --count 2 --start 2026-10-26T08:50
python3 cron_explain.py "0 0 1 * 1" --count 3 --start 2026-10-27T00:00
```

**আসল output (repository-তে চালানো):**

```text
cron      : */15 9-17 * * 1-5
OnCalendar: Mon..Fri *-*-* 9..17:00/15:00
next 4 run(s) after 2026-10-26 08:50:
  Mon 2026-10-26 09:00
  Mon 2026-10-26 09:15
  Mon 2026-10-26 09:30
  Mon 2026-10-26 09:45
cron      : 30 2 * * 0
OnCalendar: Sun *-*-* 02:30:00
next 2 run(s) after 2026-10-26 08:50:
  Sun 2026-11-01 02:30
  Sun 2026-11-08 02:30
cron      : 0 0 1 * 1
OnCalendar: (manual) dom ও dow দুটোই দেওয়া — cron OR করে, OnCalendar AND করে; দুটি আলাদা timer লিখুন
next 3 run(s) after 2026-10-27 00:00:
  Sun 2026-11-01 00:00
  Mon 2026-11-02 00:00
  Mon 2026-11-09 00:00
```

তৃতীয় উদাহরণে দেখুন: ১ নভেম্বর (রবিবার, ১ তারিখ বলে) **এবং** প্রতি সোমবার — OR নিয়মের প্রমাণ।

Native যাচাই (Ubuntu):

```bash
systemd-analyze calendar --iterations=3 'Mon..Fri *-*-* 9..17:00/15:00'
```

এর "Next elapse" Python-এর ফলের সাথে মেলান।

### 9.2 Crontab (⚠️ ছোট পরীক্ষা)

```bash
crontab -l                                   # বর্তমান (প্রথমবার "no crontab")
( crontab -l 2>/dev/null; echo '* * * * * /usr/bin/date >> /tmp/cron-test.log 2>&1' ) | crontab -
sleep 130; cat /tmp/cron-test.log            # দুই-তিনটি লাইন
crontab -l | grep -v cron-test | crontab -   # সরিয়ে ফেলা
rm /tmp/cron-test.log
grep CRON /var/log/syslog | tail -3          # Ubuntu-তে cron log (rsyslog থাকলে)
journalctl -u cron --since "5 min ago"       # অথবা journal
```

> **Fedora-তে:** `sudo dnf install -y cronie && sudo systemctl enable --now crond`; log: `journalctl -u crond`।

### 9.3 systemd timer — Project 1-এর memcheck

Files: [`ops-memcheck.service`](code/L01-11/ops-memcheck.service), [`ops-memcheck.timer`](code/L01-11/ops-memcheck.timer) — L01-09-এর `mem_report.py` প্রতি ৫ মিনিটে চালায়, `nobody` user হিসেবে, sandbox ও memory limit সহ।

```bash
sudo mkdir -p /opt/ops-toolkit
sudo install -m 0644 ../L01-09/mem_report.py /opt/ops-toolkit/
sudo install -m 0644 ops-memcheck.service ops-memcheck.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl start ops-memcheck.service          # একবার হাতে চালিয়ে পরীক্ষা
journalctl -u ops-memcheck -n 5 --no-pager
sudo systemctl enable --now ops-memcheck.timer
systemctl list-timers ops-memcheck.timer
```

উদাহরণ `list-timers` output:

```text
NEXT                        LEFT     LAST  PASSED  UNIT               ACTIVATES
Mon 2026-10-26 10:05:12 UTC 3min 4s  -     -       ops-memcheck.timer ops-memcheck.service
```

> **Fedora-তে:** `nogroup`-এর বদলে `nobody` group — service file-এ `Group=nobody` করুন (Fedora-তে `nogroup` নেই)। বাকি একই।

**ব্যর্থতা পরীক্ষা (Level C-ধরন):** service-এ ExecStart-এর path ইচ্ছাকৃত ভুল করুন (`mem_reportX.py`), `daemon-reload`, `start` — তারপর `systemctl --failed` ও `journalctl -u ops-memcheck`-এ কী দেখেন? ঠিক করে আবার `start`, তারপর `sudo systemctl reset-failed`।

**Cleanup (⚠️):**

```bash
sudo systemctl disable --now ops-memcheck.timer
sudo rm -f /etc/systemd/system/ops-memcheck.{service,timer}
sudo systemctl daemon-reload
sudo rm -r /opt/ops-toolkit
```

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_cron_explain.py`](code/L01-11/test_cron_explain.py)-এর ৮টি test: field parse (`*/15`, range, list, `5/20`), ভুল expression, ব্যবসায়িক সময়ে প্রতি ১৫ মিনিট, শুক্রবার সন্ধ্যার পরে সোমবারে লাফ, রবিবার = ৭, dom/dow OR নিয়ম, ৩০ ফেব্রুয়ারি কখনো না, ও OnCalendar রূপান্তর।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `parse_field()` | `*`, `a-b`, `*/n`, `a/n`, `x,y` → set | Cron-এর মূল syntax; সীমার বাইরে মান প্রত্যাখ্যান |
| `{d % 7 for d in dows}` | ৭ → ০ | রবিবারের দুই রূপ |
| `(t.weekday() + 1) % 7` | Python Mon=0 → cron Mon=1, Sun=0 | দুই convention মেলানো |
| `matches()`-এর dom/dow শাখা | OR নিয়ম | Section 8.2 |
| `next_runs()`: প্রতি মিনিট পরীক্ষা | সরল ও সঠিক | শেখার জন্য পরিষ্কার; production scheduler আরো দক্ষ অ্যালগরিদম ব্যবহার করে |
| `horizon_days` | অসম্ভব expression-এ অসীম loop নয় | `0 0 30 2 *` কখনো মেলে না |
| `to_oncalendar()` | সাধারণ ক্ষেত্রে রূপান্তর, OR-এ সতর্কতা | নীরবে ভুল রূপান্তরের চেয়ে স্পষ্ট "manual" ভালো |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `cron_explain.py "61 * * * *"` | `error: value out of range`, exit 2 |
| `systemd-analyze calendar` | Python-এর পরের সময়ের সাথে মেলে |
| `systemctl list-timers` | ops-memcheck-এর NEXT সময় |
| `journalctl -u ops-memcheck` | প্রতি ৫ মিনিটে memory/load সারাংশ |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Terminal-এ চলে, cron-এ চলে না | PATH, shell, env | Job-এর শুরুতে `env > /tmp/cron-env.txt` | Absolute path; script-এ env set |
| `date +%F` cron-এ ভাঙে | `%` = newline | — | `\%` বা script-এর ভেতরে |
| Cron output কোথাও নেই | Mail নেই | — | `>> log 2>&1` বা `\| logger -t job` |
| Timer চলে না | `enable` হয়নি বা timer নয়, service enable করেছেন | `systemctl list-timers --all` | `systemctl enable --now X.timer` |
| Timer চলে কিন্তু service ব্যর্থ | Script/permission | `systemctl status X.service`, journal | কারণ ঠিক; `reset-failed` |
| একই job দুবার একসাথে (cron) | ধীর run | `ps` | `flock -n` |
| বন্ধ থাকা সময়ের run হয়নি | cron/`Persistent=false` | `list-timers` LAST | `Persistent=true` |

## 13. Security, performance ও cost বিবেচনা

- **Security:** Root-এর crontab-এ চলা script যদি অন্য user লিখতে পারে → privilege escalation (L01-04: script-এর owner ও mode `root:root 0755`)। Job-এ secret command line-এ দেবেন না। systemd timer-এর service-এ non-root user ও sandbox।
- **Performance:** একই মুহূর্তে অনেক job (বা অনেক server) — `RandomizedDelaySec=`; ভারী job রাতে, `Nice=`/`IOSchedulingClass=idle` দিয়ে কম অগ্রাধিকার।
- **Cost:** Cloud-এ প্রতি মিনিটে চলা অপ্রয়োজনীয় job CPU ও API call খরচ বাড়ায়; সঠিক interval বেছে নিন।

## 14. Hands-on exercise

1. `cron_explain.py` দিয়ে নিচেরগুলোর পরের ৩টি সময় আগে অনুমান, তারপর যাচাই: `0 */6 * * *`, `15 3 1,15 * *`, `0 9 * * 6,0`, `*/10 * * * 1-5`।
2. প্রতিটির OnCalendar রূপ `systemd-analyze calendar` দিয়ে যাচাই করুন। কোথাও পার্থক্য পেলে কারণ লিখুন।
3. `ops-memcheck.timer`-কে `OnBootSec=2min` + `OnUnitActiveSec=5min` (monotonic) দিয়ে লিখুন। `OnCalendar` থেকে আচরণ কীভাবে আলাদা?
4. `cron_explain.py`-তে `@daily`, `@hourly`, `@reboot` shorthand সমর্থন যোগ করুন (`@reboot`-এর "next run" অর্থহীন — স্পষ্ট বার্তা)। Test লিখুন।
5. Section 5-এর backup crontab-কে systemd timer + script-এ নতুন করে লিখুন: আকার যাচাই, exit code, journal log।

## 15. Mini-project — job health monitor

একটি read-only script লিখুন যা `systemctl list-timers --all --output=json` (systemd-এর নতুন version-এ JSON সমর্থিত; না থাকলে text parse) ও `systemctl show -p Result,ExecMainExitTimestamp X.service` থেকে প্রতিটি timer-এর জন্য দেখায়: শেষ run কখন, ফল কী, এবং "শেষ সফল run প্রত্যাশিত interval-এর দ্বিগুণের বেশি পুরোনো" হলে WARN। এটি Section 5-এর "backup হচ্ছে কিনা কেউ জানে না" সমস্যার detect-ধরনের সমাধান (Module 17-এ alert-এ রূপান্তর হবে)।

## 16. Interview প্রশ্ন

1. Cron-এর পাঁচটি field কী? `*/15 9-17 * * 1-5` ব্যাখ্যা করুন।
2. Cron job terminal-এ চলে কিন্তু cron-এ চলে না — সাধারণ কারণ কী কী?
3. systemd timer cron-এর চেয়ে কোথায় ভালো?
4. `Persistent=true` কী করে?
5. Scheduled job-এর overlap কীভাবে আটকাবেন?
6. একশো server একই সময়ে job চালালে কী সমস্যা, সমাধান কী?
7. Backup job "সফল" হলেই কি backup ঠিক আছে?

## 17. Self-assessment প্রশ্ন

1. অ্যালার্ম ঘড়ি বনাম সহকারী analogy কোথায় মেলে না?
2. Section 5-এর পাঁচটি ভুল।
3. `0 0 1 * 1` cron-এ কখন চলে, এবং OnCalendar-এ কেন সরাসরি রূপান্তর করা যায় না?
4. Cron-এ `%` কেন বিপজ্জনক?
5. `ops-memcheck.service`-এ `Type=oneshot` কেন?
6. Fedora-তে service file-এ কোন লাইন বদলাতে হবে এবং কেন?

## 18. সংক্ষিপ্ত সারাংশ

- **cron**: সরল, সর্বত্র; কিন্তু ছোট environment, `%`, হারানো output, overlap, বাদ পড়া run।
- **systemd timer**: `.timer` + `.service`; journal log, status, `Persistent=`, `RandomizedDelaySec=`, sandbox — নতুন কাজে সুপারিশকৃত।
- Cron-এর dom/dow **OR** নিয়ম; OnCalendar AND। `systemd-analyze calendar` দিয়ে যাচাই।
- প্রতিটি scheduled job: চললো কিনা, ব্যর্থ হলে কে জানবে, ফল ঠিক কিনা।

## 19. Completion checklist

- [ ] `cron_explain.py` দিয়ে ৫টি expression ব্যাখ্যা ও `systemd-analyze calendar`-এর সাথে মিলিয়েছি
- [ ] Crontab-এ একটি job যোগ, ফল দেখা ও সরানো
- [ ] ops-memcheck timer install, `list-timers` ও journal-এ ফল দেখা
- [ ] ইচ্ছাকৃত ব্যর্থতা `--failed`-এ দেখে ঠিক করেছি
- [ ] Cleanup সম্পন্ন
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `crontab(5)` (Debian/Ubuntu cron): https://manpages.ubuntu.com/manpages/noble/man5/crontab.5.html
- `systemd.timer(5)`: https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html
- `systemd.time(7)` — OnCalendar syntax: https://www.freedesktop.org/software/systemd/man/latest/systemd.time.html
- `systemd-analyze(1)` — `calendar`: https://www.freedesktop.org/software/systemd/man/latest/systemd-analyze.html
- `flock(1)`: https://man7.org/linux/man-pages/man1/flock.1.html

---

**পরের lesson:** L01-12 — Storage: partition, filesystem, LVM, disk usage
