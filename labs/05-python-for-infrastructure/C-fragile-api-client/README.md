# Lab 05-C — ভঙ্গুর API client: timeout, ভাঙা JSON ও অপ্রাপ্য API

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট |
| **Environment** | Python ৩.১১+ — Ubuntu, Fedora বা Windows |
| **Label** | — (শুধু নিজের তৈরি directory ও 127.0.0.1-এর chaos server) |
| **Tested** | `break_it.py` → `check_c.py`: ভাঙা অবস্থায় **১৭টি FAIL** → একটি learner-ধাঁচের সংশোধিত `sync.py` (repo-তে রাখা হয়নি) → `ALL CHECKS PASSED`, মোট ~২৭ s। `reset.py` marker ছাড়া directory মুছতে অস্বীকার করে — যাচাই করা হয়েছে। Python 3.14.5, Windows, ২০২৬-১০-২৭। |

## Objective

একটি ছোট sync tool TaskFlow API থেকে task-এর সারাংশ এনে `summary.json`-এ লেখে, যা একটি dashboard পড়ে। স্বাভাবিক দিনে এটা ঠিকঠাক চলে। কিন্তু **চারটি ফাঁদ** আছে, যা শুধু খারাপ দিনে প্রকাশ পায় — API ঝুলে থাকলে, ভাঙা উত্তর দিলে, বা পাওয়াই না গেলে।

ছয়টি পরিস্থিতিতে tool-টিকে spec অনুযায়ী আচরণ করানো এই lab-এর লক্ষ্য।

**Spec** (`sync.py`-এর docstring-এ লেখা):

- সফল হলে exit ০, এবং `summary.json` = `{"total", "done", "fetched_at"}`।
- ব্যর্থ হলে exit ২, stderr-এ এক লাইনের কারণ, এবং **আগের `summary.json` অক্ষত**।
- ১০ সেকেন্ডের বেশি কখনো নয়; সাময়িক 503/502-এ কয়েকবার চেষ্টা।

## Prerequisites

- [L05-03](../../../05-python-for-infrastructure/L05-03-files-and-pathlib.md) (atomic write)
- [L05-06](../../../05-python-for-infrastructure/L05-06-http-client-retry.md) (timeout, retry)
- [L05-07](../../../05-python-for-infrastructure/L05-07-logging-structured.md) (stderr, বার্তা)
- [L05-08](../../../05-python-for-infrastructure/L05-08-argparse-cli.md) (exit code)
- [L05-05](../../../05-python-for-infrastructure/L05-05-json-yaml-config.md) (input যাচাই)

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/05-python-for-infrastructure/C-fragile-api-client
python3 break_it.py ~/lab05c
cat ~/lab05c/sync.py                      # এটা debugging-এর lab — code পড়ুন
python3 chaos_server.py --port 8098 &     # অন্য terminal-এ রাখলেও চলে
```

Files: [`break_it.py`](break_it.py), [`chaos_server.py`](chaos_server.py), [`check_c.py`](check_c.py), [`reset.py`](reset.py)।

## Steps

1. Timer চালু করুন।
2. **লক্ষণ দেখুন** — প্রতিটির আগে একটি "ভালো" summary রাখুন:

   ```bash
   cd ~/lab05c
   for mode in ok flaky hang broken html502; do
     echo '{"total": 99, "done": 42}' > summary.json
     echo "== $mode"; timeout 20 python3 sync.py http://127.0.0.1:8098/$mode summary.json; echo "exit=$?"
     cat summary.json; echo
   done
   python3 sync.py http://127.0.0.1:1 summary.json; echo "exit=$?"    # অপ্রাপ্য
   ```

   প্রতিটি পরিস্থিতিতে লিখুন: exit code কী, `summary.json`-এর কী হলো, এবং dashboard কী দেখাবে।

   (`timeout` command Windows-এর Git Bash-এ না থাকলে বাদ দিন; hang-এ Ctrl-C।)

3. **Checker চালান:**

   ```bash
   python3 ~/devops-ai-engineering/labs/05-python-for-infrastructure/C-fragile-api-client/check_c.py ~/lab05c
   ```

4. **একটি একটি করে ঠিক করুন** এবং প্রতিবার checker চালান।
5. শেষে `ALL CHECKS PASSED`।
6. Notebook-এ প্রতিটি ফাঁদের জন্য লিখুন: লক্ষণ, কোন পরিস্থিতিতে প্রকাশ পেল, কোন lesson, এবং fix।

## Expected behavior

| পরিস্থিতি | Exit | `summary.json` | সময় |
|---|---|---|---|
| ok | ০ | total=৩, done=১ | দ্রুত |
| flaky (503, 503, তারপর ok) | ০ | total=৩, done=১ | ~১ s (retry) |
| hang | ২ | আগেরটা অক্ষত | ≤ ১০ s |
| broken JSON | ২ | আগেরটা অক্ষত | দ্রুত |
| HTML 502 | ২ | আগেরটা অক্ষত | retry-র পরে |
| অপ্রাপ্য | ২ | আগেরটা অক্ষত | ≤ ১০ s |

সব ব্যর্থতায় stderr-এ এক লাইন, কোনো traceback নয়। stdout-এ ভুল ধারণা দেওয়ার মতো কিছু নেই। Directory-তে কোনো temp file থাকবে না।

## Verification

```bash
python3 check_c.py ~/lab05c; echo "exit=$?"      # ALL CHECKS PASSED, 0
```

## Troubleshooting (সূত্র — একটি একটি করে খুলুন)

<details><summary>সূত্র ১ — "ok" ছাড়া প্রায় সব ক্ষেত্রে summary.json উধাও বা ফাঁকা</summary>

File কখন খোলা হচ্ছে, data আসার আগে নাকি পরে? `open(out, "w")` সাথে সাথে file-কে শূন্য করে দেয়। L05-03-এর atomic write: একই directory-তে temp → `fsync` → `os.replace`।
</details>

<details><summary>সূত্র ২ — ব্যর্থ হলেও exit 0</summary>

`except Exception` সব কিছু ধরে শুধু print করছে, এবং `return 0`। এটা "নীরব ব্যর্থতা" — cron বা monitoring কখনো জানবে না (L05-08)। নির্দিষ্ট exception ধরুন, stderr-এ লিখুন, exit ২।
</details>

<details><summary>সূত্র ৩ — hang-এ tool কখনো শেষ হয় না</summary>

`urlopen`-এ `timeout` নেই — default অসীম (L05-06)। কিন্তু শুধু per-attempt timeout যথেষ্ট নয়: retry-সহ **মোট** সময় ১০ s-এর মধ্যে রাখতে deadline হিসাব করুন।
</details>

<details><summary>সূত্র ৪ — flaky-তে exit 0, কিন্তু summary নেই</summary>

এটাই সবচেয়ে বিপজ্জনক লক্ষণ: "সফল" বলে, কিন্তু কিছুই লেখেনি। 503 সাময়িক — retry-যোগ্য (L05-06)। কিন্তু 404/400 নয়।
</details>

<details><summary>সূত্র ৫ — broken JSON বা HTML-এ অদ্ভুত বার্তা</summary>

HTTP 200 মানেই body বৈধ নয়। Parse করুন, প্রত্যাশিত কাঠামো (`items` list, `done` bool) যাচাই করুন, এবং ব্যর্থ হলে স্পষ্ট বার্তা দিন (L05-05)। Proxy-র HTML error page JSON নয় — status code আগে দেখুন।
</details>

## Cleanup / reset

```bash
kill %1 2>/dev/null                 # chaos server (background-এ চালালে)
python3 reset.py ~/lab05c           # শুধু .lab05c চিহ্নযুক্ত directory
```

## Assessment

1. চারটি ফাঁদের প্রতিটির লক্ষণ, প্রকাশের পরিস্থিতি ও fix।
2. Flaky পরিস্থিতিতে মূল tool exit ০ দিয়ে কিছুই লেখেনি। Dashboard ব্যবহারকারী কী দেখতেন? এটা কেন "ব্যর্থতার" চেয়েও খারাপ?
3. আপনার fix-এ hang পরিস্থিতিতে মোট সময় কত? কোন সংখ্যাগুলো (per-attempt timeout, retry, backoff) এটা ঠিক করে? Deadline না রাখলে সবচেয়ে খারাপ ক্ষেত্রে কত হতো?
4. `summary.json` stale (পুরোনো) থাকলে dashboard কীভাবে বুঝবে? (`fetched_at`, L05-12-এর `file_age`)
5. এই tool-এ POST থাকলে retry-র নীতি কীভাবে বদলাত? (L05-06, idempotency)
