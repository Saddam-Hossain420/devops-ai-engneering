# Module 05 Labs — Python for Infrastructure

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — pathlib, json ও subprocess](A-pathlib-subprocess-json/README.md) | A — Fundamentals | আগে অনুমান, পরে যাচাই: ১৫টি experiment (absolute path join, hidden file glob, duplicate key, `NaN`, `bool`/`int`, list argument, `\r\n`) | ৪৫–৬০ মিনিট | L05-02 – L05-05 |
| [B — Health check ও log analysis CLI](B-health-and-log-cli/README.md) | B — Integrated | TaskFlow-এর JSON access log-এর route-ভিত্তিক report (test-সহ, grader দিয়ে যাচাই) + TaskFlow-এর health check + (Ubuntu) systemd timer | ২–৩ ঘণ্টা | L05-07 – L05-13 |
| [C — ভঙ্গুর API client](C-fragile-api-client/README.md) | C — Failure and Recovery | চারটি ফাঁদযুক্ত sync tool: hang, ভাঙা JSON, HTML 502, 503, অপ্রাপ্য API — ছয়টি পরিস্থিতির check | ৬০–৯০ মিনিট | L05-03, L05-05 – L05-08 |

**Environment:**

- তিনটি lab-ই pure Python ও শুধু localhost — Ubuntu, Fedora বা Windows-এ চলে।
- Lab B-এর Part 4 (systemd timer) Ubuntu VM-এ।
- Lab B-এর grader ও Lab C-এর break → fix → check Windows-এ আসলে চালিয়ে যাচাই করা হয়েছে। Reference/সংশোধিত solution repo-তে রাখা হয়নি।

**Module 05-এর completion criteria:**

- "Log analyzer ও health checker test সহ" → Lab B।
- "Continuous project v0.1 চালু ও test পাস" → [L05-13](../../05-python-for-infrastructure/L05-13-taskflow-api-v01.md) ও Lab B-এর Part 2।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [05-python-for-infrastructure/PROGRESS.md](../../05-python-for-infrastructure/PROGRESS.md)-এর Module assessment table আপডেট করুন।
