# Lab 05-B — TaskFlow-এর জন্য health check ও log analysis CLI

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ২–৩ ঘণ্টা |
| **Environment** | Python ৩.১১+ (Ubuntu, Fedora বা Windows); Part 4 Ubuntu VM-এ (systemd) |
| **Label** | — (শুধু localhost ও নিজের directory) |
| **Tested** | `check_b.py` (grader) যাচাই করা হয়েছে দুভাবে: একটি ফাঁকা stub-এ ১৫টি FAIL, এবং একটি reference solution-এ (repo-তে রাখা হয়নি) `ALL CHECKS PASSED` — Python 3.14.5, Windows, ২০২৬-১০-২৭। Part 2–3 L05-13 ও L05-12-এর tool দিয়ে চালানো যায়; Part 4 (systemd timer) **চালানো হয়নি**। |

## Objective

L05-11-এর log analysis ও L05-12-এর health check ধারণা মিলিয়ে continuous project **TaskFlow**-এর জন্য একটি ছোট operations toolkit বানানো:

1. `taskflow_report.py` — TaskFlow-এর JSON access log থেকে route-ভিত্তিক report (আপনি লিখবেন, test-সহ)।
2. TaskFlow-এর জন্য `checks.json` — L05-12-এর `healthcheck.py` দিয়ে।
3. আসল TaskFlow চালিয়ে দুটো tool-ই আসল data-য় প্রয়োগ।

এটাই Module 05-এর completion criterion "Log analyzer ও health checker test সহ"।

## Prerequisites

- [L05-07](../../../05-python-for-infrastructure/L05-07-logging-structured.md), [L05-08](../../../05-python-for-infrastructure/L05-08-argparse-cli.md), [L05-09](../../../05-python-for-infrastructure/L05-09-pytest-testing.md), [L05-11](../../../05-python-for-infrastructure/L05-11-log-analysis-tool.md), [L05-12](../../../05-python-for-infrastructure/L05-12-healthcheck-backup-verify.md), [L05-13](../../../05-python-for-infrastructure/L05-13-taskflow-api-v01.md)

## Environment setup

```bash
mkdir -p ~/devops-ai-engineering-work/lab05b && cd ~/devops-ai-engineering-work/lab05b
LAB=~/devops-ai-engineering/labs/05-python-for-infrastructure/B-health-and-log-cli
python3 $LAB/gen_taskflow_log.py --lines 5000 > taskflow-access.jsonl
head -3 taskflow-access.jsonl
```

Files: [`gen_taskflow_log.py`](gen_taskflow_log.py) (কৃত্রিম log, seed স্থির), [`check_b.py`](check_b.py) (grader)।

> `check_b.py`-এর `truth()` function সঠিক উত্তর হিসাব করে। নিজের tool শেষ করার আগে সেটা পড়বেন না।

## Steps

### Part 1 — `taskflow_report.py` (৯০ মিনিট)

`~/devops-ai-engineering-work/lab05b/taskflow_report.py` লিখুন।

**Input ও output:**

- **Input:** এক বা একাধিক JSONL file, অথবা `-` (stdin)।
- **শুধু `"msg": "request"` লাইন গণনা হবে।** অন্য বৈধ JSON লাইন (`listening`, `stopped`) উপেক্ষা করুন। JSON হিসেবে parse না হওয়া লাইন `unparsed`-এ গুনুন।
- **Route:** `"{method} {path}"`, যেখানে `/tasks/<সংখ্যা>` → `/tasks/{id}` (cardinality — L05-11)।
- **`--json` output:**

  ```json
  {
    "requests": 5000,
    "unparsed": 2,
    "error_rate_5xx": 0.0146,
    "by_route": {"GET /tasks/{id}": {"count": 0, "p50_ms": 0.0, "p99_ms": 0.0, "errors_5xx": 0}, "...": {}},
    "slowest_request_ids": ["r000137", "...", "..."]
  }
  ```

  উপরের সংখ্যাগুলো আকৃতি বোঝানোর উদাহরণ মাত্র।

**নিয়ম:**

- `error_rate_5xx` চার দশমিক পর্যন্ত round; কোনো request না থাকলে `null`।
- Percentile **nearest-rank** (L05-11), `duration_ms`-এর ওপর।
- `slowest_request_ids`: `duration_ms` অনুযায়ী শীর্ষ ৩।
- `by_route`-এর key ক্রমানুসারে।
- **Exit code:** error rate `--max-error-rate`-এর (default ০.০১) বেশি হলে ১, নইলে ০। File না পেলে ২, traceback ছাড়া।

**Test:** কমপক্ষে ৬টি unit test লিখুন (unittest বা pytest — L05-09)। বিশেষত:

- Path normalization।
- ভাঙা লাইন।
- খালি input।
- এক উপাদানের percentile।
- Exit code।

**যাচাই:**

```bash
python3 $LAB/check_b.py taskflow_report.py
```

সব PASS না হওয়া পর্যন্ত ঠিক করুন। প্রতিটি FAIL-এ expected/got দেখানো হয়।

### Part 2 — আসল TaskFlow, আসল log (৩০ মিনিট)

```bash
TF=~/devops-ai-engineering/05-python-for-infrastructure/code/L05-13
TASKFLOW_DB=$PWD/tf.db python3 $TF/taskflow_api.py 2> tf-access.jsonl &
for i in $(seq 1 50); do curl -s -X POST 127.0.0.1:8000/tasks -H 'Content-Type: application/json' -d "{\"title\": \"t$i\"}" >/dev/null; done
for i in $(seq 1 200); do curl -s 127.0.0.1:8000/tasks/$((RANDOM % 60)) >/dev/null; done   # কিছু 404 হবে
curl -s -X POST 127.0.0.1:8000/tasks -d 'x' >/dev/null                                      # 415
python3 taskflow_report.py --json tf-access.jsonl
```

Report-এ কী দেখলেন? 4xx কোথায়? কোন route সবচেয়ে ধীর? এখানে 5xx না থাকার কারণ কী?

### Part 3 — Health check (২০ মিনিট)

L05-12-এর `healthcheck.py`-এর জন্য `checks.json` লিখুন:

- TaskFlow `/health` (body-তে `"ok"`, `warn_ms` ২০০)।
- `/ready`।
- Port ৮০০০।
- `tf.db`-এর জন্য `file_age` (অনুশীলনের জন্য `warn_h` ১)।
- Disk।

```bash
python3 ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-12/healthcheck.py checks.json; echo "exit=$?"
kill %1                                                       # TaskFlow বন্ধ
python3 ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-12/healthcheck.py checks.json; echo "exit=$?"
```

দ্বিতীয়বার কোন check কী status দিল, এবং কেন?

### Part 4 — (Ubuntu) প্রতি ৫ মিনিটে (ঐচ্ছিক, ৩০ মিনিট)

L01-11-এর মতো একটি systemd `--user` timer:

- `healthcheck.py --json`-এর ফল ও `taskflow_report.py`-এর সারাংশ `~/lab05b/reports/`-এ timestamp-সহ (atomic write — L05-03)।
- কোনোটি non-zero দিলে `logger`/journald-এ সতর্কতা।

## Expected behavior

- `check_b.py`: `ALL CHECKS PASSED`, exit ০।
- Part 1-এর আপনার নিজের test সব পাস।
- Part 2: route-ভিত্তিক report, `GET /tasks/{id}`-এ 404 গোনা।
- Part 3: চলমান অবস্থায় OK (বা `file_age` WARNING), বন্ধ অবস্থায় CRITICAL, exit ২।

## Verification

```bash
python3 $LAB/check_b.py taskflow_report.py; echo "exit=$?"     # ALL CHECKS PASSED, 0
python3 -m unittest -v        # বা: python3 -m pytest -q   — আপনার test
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| `requests` বেশি | `listening`/`stopped` লাইনও গুনছেন |
| `unparsed` ভুল | ফাঁকা লাইনকে unparsed গুনছেন, বা ভাঙা লাইনে crash |
| `by_route keys` FAIL | `/tasks/123` normalize হয়নি; বা method বাদ |
| p99 এক ধাপ সরে আছে | Interpolation বা `int(p/100*n)` (ceil নয়) |
| `reads stdin` FAIL | `-` বিশেষভাবে ধরা হয়নি |
| Windows-এ `UnicodeEncodeError` | stdout-এর encoding — `reconfigure(encoding="utf-8")` |
| Part 2-এ log ফাঁকা | TaskFlow-এর stderr redirect হয়নি (`2>`) |

## Cleanup / reset

```bash
kill %1 2>/dev/null; rm -rf ~/devops-ai-engineering-work/lab05b        # শুধু lab-এর নিজের directory
```

## Assessment

1. `check_b.py`-এর প্রথম run-এ কোন check-গুলো FAIL করেছিল, এবং কেন?
2. Part 2-এ আপনার report ও L05-11-এর `logscan.py`-এর পার্থক্য কী (format, normalization, কী মাপে)?
3. `GET /tasks/{id}`-এর p50 ও p99-এর পার্থক্য কী বলে (নমুনা log-এ)? কোন request id দিয়ে তদন্ত শুরু করবেন?
4. Part 3-এ TaskFlow বন্ধ থাকলে `/health` ও `/ready` দুটোই CRITICAL — কোন পরিস্থিতিতে শুধু `/ready` CRITICAL হতো?
5. এই দুই tool একটি systemd timer-এ চালালে কোন exit code-এ alert হওয়া উচিত, কোনটায় নয়?
