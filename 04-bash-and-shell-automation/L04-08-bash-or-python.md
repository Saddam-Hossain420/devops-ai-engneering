# L04-08 — কখন Bash, কখন Python

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২ ঘণ্টা |
| **পূর্বশর্ত** | L04-01 থেকে L04-07 |
| **Label** | — |
| **Tested** | একই কাজ (access log-এর সবচেয়ে বেশি 5xx-যুক্ত path, JSON-এ) Bash/awk ও Python দুটোতে: ৪টি test পাস — স্বাভাবিক log-এ দুটোর ফল হুবহু এক, অদ্ভুত লাইনে Bash একটি error **নিঃশব্দে হারায়**, Python অসম্পূর্ণ লাইন গোনে ও escape ঠিক করে (GNU Bash 5.3.9, GNU awk, Python 3.14, Windows/Git Bash)। ২,০০,০০০ লাইনে সময় আসলে মাপা হয়েছে (তিনবার)। **আমার দুটি প্রত্যাশা ভুল প্রমাণিত হয়েছে, এবং Python-এর প্রথম regex-এ একটি bug ধরা পড়েছে** — Section 9। Ubuntu-তে চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Bash-এর শক্তি ও দুর্বলতা — module-এর আগের সাত lesson-এর অভিজ্ঞতা থেকে।
- একটি **সিদ্ধান্তের checklist**: কখন Bash যথেষ্ট, কখন Python-এ যাওয়া উচিত।
- একই কাজ দুই ভাষায় — সঠিকতা, edge case, গতি ও পাঠযোগ্যতা মেপে তুলনা।
- "Glue" pattern: Bash দিয়ে command জোড়া, Python দিয়ে logic।
- Bash script থেকে Python-এ migration-এর ধাপ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

প্রায় প্রতিটি team-এ ৫০০ লাইনের এমন Bash script আছে যেটা কেউ ছুঁতে চায় না। শুরুতে ১০ লাইন ছিল, তারপর একটা `if`, একটা associative array, JSON-এর জন্য `jq`, retry, তারপর আরো। এখন:

- Test নেই — Bash-এ test লেখা কঠিন মনে হয়।
- Error handling `set -e`-এর অনিশ্চিত আচরণের উপর নির্ভর করে (L04-01)।
- Data structure (nested JSON, list of objects) জোড়াতালি দিয়ে চলে।
- Edge case-এ নিঃশব্দে ভুল ফল দেয়।

উল্টো দিকে, ৩ লাইনের `rsync && systemctl restart` কাজের জন্য ৮০ লাইনের Python + `subprocess` + virtual environment — অপ্রয়োজনীয় জটিলতা।

সঠিক tool বাছাই মানে ভবিষ্যতের রক্ষণাবেক্ষণের খরচ কমানো।

## 3. সহজ ভাষায় পরিচয়

### Bash যেখানে স্বাভাবিক

- **অন্য program চালানো ও জোড়া দেওয়া:** `pg_dump | gzip > file`, `systemctl`, `rsync`, `tar`।
- ছোট, রৈখিক কাজ: ১০–১০০ লাইন, কয়েকটি `if`।
- যেখানে Python নেই বা নিশ্চিত নয় (minimal container, recovery shell, installer)।
- File, process ও signal-কেন্দ্রিক কাজ: lock, trap, `exec` (L04-04, L04-06)।

### Python যেখানে ভালো

- **Data structure:** list, dict, nested JSON/YAML (L05-05)।
- জটিল logic, অনেক শাখা, পুনর্ব্যবহারযোগ্য function।
- Text parsing, যেখানে field-এ space, quote বা unicode থাকতে পারে (এই lesson-এর পরীক্ষা)।
- HTTP API, retry, timeout (L05-06); concurrency।
- পরিষ্কার error handling (exception) ও unit test (L05-09)।
- Cross-platform (Windows-ও)।

### সিদ্ধান্তের checklist — যেকোনো একটি "হ্যাঁ" হলে Python বিবেচনা করুন

| প্রশ্ন | কেন |
|---|---|
| ১০০ লাইনের বেশি হবে? | Bash-এ বড় code দ্রুত অপাঠ্য হয় |
| Nested data (JSON/YAML) পড়তে বা লিখতে হবে? | Bash-এর array এক স্তরের |
| দশমিক গণিত, তারিখ বা সময়ের হিসাব? | Bash শুধু integer জানে (L04-03-এর `to_bytes`-এ `awk` লাগল) |
| HTTP API, retry, timeout? | `curl`-এর exit code ও output parsing ভঙ্গুর |
| Unit test দরকার? | Python-এ সহজ ও প্রচলিত |
| ভুল input-এ নিঃশব্দে ভুল ফল হলে বড় ক্ষতি? | Parsing-এর নিয়ন্ত্রণ |
| একাধিক মানুষ দীর্ঘদিন রক্ষণাবেক্ষণ করবে? | পাঠযোগ্যতা ও tooling |

এবং উল্টো প্রশ্ন: **কাজটা কি মূলত command চালানো?** তাহলে Bash-এ থাকুন, অথবা Python-এ `subprocess` দিয়ে (L05-04)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাতুড়ি ও ড্রিল মেশিন

- **Bash** = হাতুড়ি: সবসময় হাতের কাছে, একটা পেরেক ঠোকা দ্রুত, কোনো সেটআপ নেই।
- **Python** = ড্রিল মেশিন: সেটআপ লাগে (interpreter, dependency), কিন্তু অনেক জটিল কাজ নির্ভুলভাবে করে।
- শুধু হাতুড়ি দিয়ে আলমারি বানানো সম্ভব, কিন্তু ফলাফল নড়বড়ে। একটা পেরেকের জন্য ড্রিল সেট করা সময়ের অপচয়।

### Analogy কোথায় মেলে না

- হাতুড়ি ভুল জায়গায় পড়লে সাথে সাথে দেখা যায়। Bash script-এর ভুল প্রায়ই **নিঃশব্দ** — Section 9-এর পরীক্ষায় একটি 5xx error কোনো সতর্কতা ছাড়াই হারিয়ে গেছে, এবং JSON বৈধই ছিল, তাই কেউ টের পেত না।
- ড্রিল সবসময় হাতুড়ির চেয়ে "ভালো" মনে হয়। কিন্তু Python-ও নিজে থেকে সঠিক নয়: আমার Python সংস্করণের প্রথম regex-এ একটি bug ছিল, এবং সেটাও নিঃশব্দে ভুল path দিয়েছিল। ভাষা নয় — **parsing-এর নিয়ম ও test** সঠিকতা আনে। Python শুধু সেগুলো সহজ করে।
- হাতুড়ি ও ড্রিল আলাদা কাজের। বাস্তবে প্রায়ই **দুটো একসাথে**: Bash wrapper (lock, environment, `exec`) যা Python tool চালায়; অথবা Python যা `subprocess` দিয়ে `pg_dump` চালায়।

## 5. Real-world engineering scenario — "Deploy script ৬০০ লাইনে পৌঁছাল"

**পরিস্থিতি:** একটি deploy script শুরু হয়েছিল এভাবে:

```bash
git pull && pip install -r requirements.txt && systemctl restart app
```

দুই বছরে যোগ হলো: environment অনুযায়ী config (associative array), Slack-এ notification (`curl` + হাতে লেখা JSON), health check retry, canary শতাংশ, rollback, `jq` দিয়ে cloud API-র response parsing, এবং `if`-এর ভেতরে `if`।

একদিন একটি release note-এ `"` থাকায় Slack-এর JSON ভাঙল, `curl` ৪০০ দিল। `set -e` সেটা ধরেনি, কারণ `curl`-এ `--fail` ছিল না। Deploy "সফল" হলো, কিন্তু কেউ জানল না।

**Migration-এর পদ্ধতি (বড় বিস্ফোরণ নয়, ধাপে ধাপে):**

1. বর্তমান আচরণের **characterization test** লিখুন (L04-07-এর bats বা Python `subprocess` test) — আগে যা করে, পরেও তা-ই করবে।
2. সবচেয়ে ভঙ্গুর অংশ (JSON, API, retry) আলাদা Python tool-এ সরান: `notify.py`, `healthcheck.py` (L05-12)।
3. Bash হয়ে থাকুক পাতলা orchestrator: lock, environment, ধাপের ক্রম।
4. ধীরে ধীরে orchestrator-ও Python-এ, অথবা প্রকৃত deploy tool-এ (Ansible — Module 08; CI/CD — Module 06)।

**শিক্ষা:** Bash script-এর আকার ও জটিলতা নিয়মিত মাপুন। প্রথম nested data structure বা প্রথম API call-ই সাধারণত Python-এ যাওয়ার সংকেত।

## 6. Diagram — সিদ্ধান্তের প্রবাহ

```text
                নতুন automation কাজ
                        │
        মূলত অন্য command চালানো ও জোড়া দেওয়া?
              │ হ্যাঁ                         │ না
              ▼                               ▼
    ১০০ লাইনের কম, data সরল?            Python (data, logic, API, test)
         │ হ্যাঁ          │ না                    │
         ▼                ▼                       ▼
       Bash          Bash orchestrator      subprocess দিয়ে command
   (strict mode,     + Python tool          (list args, timeout — L05-04)
    trap, ShellCheck)  (ভঙ্গুর অংশ)
         │
   বাড়তে থাকলে → characterization test → ধাপে ধাপে Python-এ
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Glue code | Program-গুলো জোড়া দেওয়ার code |
| Orchestrator | ধাপের ক্রম ও শর্ত নিয়ন্ত্রণকারী |
| Characterization test | বর্তমান আচরণ ধরে রাখার test (refactor-এর আগে) |
| Silent failure | ভুল ফল, কোনো error নেই |
| Field-based parsing | Space দিয়ে column ধরে নেওয়া (`awk $9`) |
| Anchored regex | পরিচিত অংশে বাঁধা pattern (শেষে `HTTP/x`) |
| Process spawn cost | প্রতিটি external command-এ নতুন process-এর খরচ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Bash-এর গঠনগত সীমা

- **একটিই data type:** string (আর integer-গণিত)। Array এক স্তরের, associative array-এ nested নেই।
- **Quoting ও splitting** প্রতিটি লাইনে ভুলের সুযোগ (L04-02)।
- **Error model দুর্বল:** exit code + `set -e`-এর ব্যতিক্রম (L04-01); exception বা stack trace নেই (L04-04-এর ERR trap কাছাকাছি)।
- **Parsing field-ভিত্তিক:** `awk`, `cut`, `read` space ধরে column ভাগ করে — field-এর ভেতরে space থাকলে ভেঙে যায় (L04-03-এর `df`, এই lesson-এর log)।

### 8.2 Python-এর খরচ

- Interpreter শুরু হতে কয়েক দশ মিলিসেকেন্ড লাগে।
- Dependency থাকলে virtual environment ও version ব্যবস্থাপনা লাগে (L05-01)।
- Minimal image-এ Python নাও থাকতে পারে।
- `subprocess` দিয়ে command চালানো Bash-এর চেয়ে বেশি লেখা।

### 8.3 গতি সাধারণত সিদ্ধান্তের কারণ নয়

এই lesson-এর মাপ (Section 9.3): ২,০০,০০০ লাইনে দুটোই এক সেকেন্ডের এক-তৃতীয়াংশের কম, এবং পার্থক্য কয়েক দশ মিলিসেকেন্ড। Bash loop-এ লাইন-প্রতি external command চালালে অবশ্য Bash অনেক গুণ ধীর হয় (L04-02), কিন্তু `awk` ব্যবহার করলে দ্রুত। সাধারণ ops কাজে **সঠিকতা ও রক্ষণাবেক্ষণযোগ্যতাই** নির্ধারক।

## 9. Practical demonstration

Files: [`code/L04-08/gen_log.py`](code/L04-08/gen_log.py) (synthetic log — কোনো আসল traffic নয়), [`top_errors.sh`](code/L04-08/top_errors.sh) (Bash + awk), [`top_errors.py`](code/L04-08/top_errors.py)।

### 9.1 স্বাভাবিক log — একই উত্তর

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-08
T=$(mktemp -d)
python3 gen_log.py 200000 > "$T/access.log"
bash top_errors.sh "$T/access.log" 3
python3 top_errors.py "$T/access.log" 3
```

**আসল output:**

```text
{"top": [{"path": "/static/app.js", "count": 1730}, {"path": "/api/report", "count": 1723}, {"path": "/", "count": 1709}], "total_5xx": 11902}
{"top": [{"path": "/static/app.js", "count": 1730}, {"path": "/api/report", "count": 1723}, {"path": "/", "count": 1709}], "total_5xx": 11902, "unparsed_lines": 0}
```

২১ লাইনের Bash ও ৫৩ লাইনের Python — স্বাভাবিক data-য় হুবহু একই ফল।

### 9.2 অদ্ভুত কিন্তু বাস্তব লাইন — এবং দুটি ভুল প্রত্যাশা

```bash
python3 gen_log.py 0 --tricky > "$T/tricky.log"       # ৬টি লাইন: quote, unicode, কাটা লাইন, space, backslash
bash top_errors.sh "$T/tricky.log" 10
python3 top_errors.py "$T/tricky.log" 10
```

**আসল output:**

```text
{"top": [{"path": "/a\\b", "count": 1}, {"path": "/api/tasks", "count": 1}, {"path": "/search?q=\"rm\"", "count": 1}, {"path": "/খোঁজ", "count": 1}], "total_5xx": 4}
{"top": [{"path": "/a\\b", "count": 1}, {"path": "/api/tasks", "count": 1}, {"path": "/my file.txt", "count": 1}, {"path": "/search?q=\"rm\"", "count": 1}, {"path": "/খোঁজ", "count": 1}], "total_5xx": 5, "unparsed_lines": 1}
```

**ভুল প্রত্যাশা ১:** আমি ভেবেছিলাম Bash-এর হাতে লেখা JSON quote-যুক্ত path-এ ভাঙবে। ভাঙেনি — nginx নিজেই log-এ quote ও backslash escape করে লেখে (`\"`, `\\`), এবং সেটা কাকতালীয়ভাবে JSON-এর escape-এর সাথে মিলে যায়। JSON বৈধ ছিল। (অন্য উৎসের data-য় এই "সৌভাগ্য" থাকবে না।)

**আসল পার্থক্য — নিঃশব্দ ক্ষতি:** একটি লাইনে path-এ encode না করা space ছিল (`"GET /my file.txt HTTP/1.1" 502`) — ভুলভাবে তৈরি client বা আক্রমণে এমন লাইন আসে। awk-এর `$9` তখন status নয়, `HTTP/1.1"` পায়। ফলে **502-টি কোনো সতর্কতা ছাড়াই গণনা থেকে বাদ** পড়েছে (৪ বনাম ৫)। Output বৈধ JSON, দেখতে স্বাভাবিক — কেউ টের পেত না। কাটা লাইনটিও Bash নিঃশব্দে বাদ দিয়েছে; Python সেটা `unparsed_lines`-এ জানায়।

**ভুল প্রত্যাশা ২ — Python-এর নিজের bug:** Python-এর প্রথম regex (lazy match) একই লাইনে error গুনেছিল, কিন্তু path দিয়েছিল `"/my"` — এটাও নিঃশব্দ ভুল। Regex-কে শেষের `HTTP/x`-এ নোঙর করে ঠিক করা হয়েছে। ভাষা বদলালে সঠিকতা আসে না। আসে **test ও স্পষ্ট parsing-নিয়মে**, যা Python-এ লেখা সহজ।

### 9.3 গতি — আসল মাপ

```bash
TIMEFORMAT='%R'
for i in 1 2 3; do
  time bash top_errors.sh "$T/access.log" 3 >/dev/null
  time python3 top_errors.py "$T/access.log" 3 >/dev/null
done
```

**আসল ফল (সেকেন্ড, ২,০০,০০০ লাইন, Windows/Git Bash):**

| Run | Bash + awk | Python (প্রথম regex) | Python (সঠিক regex) |
|---|---|---|---|
| ১ | ০.২৪৪ / ০.২৬৬ | ০.২২৫ | ০.৩০৯ |
| ২ | ০.২৪৬ / ০.২৬৪ | ০.২২৩ | ০.৩৩৫ |
| ৩ | ০.২৭৩ / ০.২৫৫ | ০.২৩০ | ০.৩১৬ |

(Bash দুবার মাপা হয়েছে, দুই সেশনে।) সঠিক regex-এর খরচ প্রায় ০.১ সেকেন্ড বেশি। দুটো সংস্করণই যথেষ্ট দ্রুত — সিদ্ধান্তের মাপকাঠি গতি নয়।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_l04_08.py`](code/L04-08/test_l04_08.py)-এর ৪টি test:

- স্বাভাবিক log-এ দুটোর একই উত্তর।
- Tricky log-এ Bash ৪টি, Python ৫টি (encode-না-করা space)।
- Python কাটা লাইন গোনে ও escape সঠিকভাবে ফেরায়।
- Usage।

দ্বিতীয় test **Bash-এর সীমাবদ্ধতাকে স্পষ্টভাবে নথিভুক্ত করে** — Bash সংস্করণ বদলালে test-টিও সচেতনভাবে বদলাতে হবে।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `awk '$9 ~ /^5../'` | Field ৯ = status ধরে নেওয়া | সরল, দ্রুত — space-যুক্ত field-এ ভুল |
| Bash-এ হাতে `printf` JSON | String জোড়া | Escape-এর দায় data-র উপর ছেড়ে দেওয়া |
| Python `LINE` regex, `HTTP/x`-এ নোঙর | পুরো লাইনের গঠন যাচাই | Path-এ space থাকলেও সঠিক; না মিললে গণনা |
| `unparsed_lines` | যা বোঝা যায়নি তা জানানো | নিঃশব্দ ক্ষতির বিপরীত |
| `json.dumps(ensure_ascii=False)` | নিরাপদ JSON, unicode অক্ষত | Escape-এর দায় library-র |
| `gen_log.py` নির্দিষ্ট seed | একই file প্রতিবার | Test ও তুলনা পুনরুৎপাদনযোগ্য |
| `hasattr(sys.stdout, "reconfigure")` | Test-এ StringIO | Library-র মতো code environment ধরে নেয় না |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| স্বাভাবিক log | দুটোই `total_5xx: 11902` |
| Tricky log | Bash ৪, Python ৫ ও `unparsed_lines: 1` |
| Bash-এর output | বৈধ JSON (তবু অসম্পূর্ণ) |
| `python3 -m unittest -v` | `Ran 4 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | পরিণতি | সঠিক পদ্ধতি |
|---|---|---|
| "Bash-এ শুরু করেছি, তাই Bash-এই চালাই" | ৬০০ লাইনের অরক্ষণীয় script | Checklist অনুযায়ী নিয়মিত পুনর্বিবেচনা |
| Python-এ সব কিছু, এমনকি `rsync && restart` | অপ্রয়োজনীয় জটিলতা | ছোট glue Bash-এই |
| Bash-এ হাতে JSON লেখা | Escape-এর ভুল, invalid JSON | `jq -n --arg` বা Python |
| Field-ভিত্তিক parsing অজানা data-য় | নিঃশব্দে ভুল ফল | Regex নোঙর, machine-readable format, অচেনা লাইন গোনা |
| "Python, তাই সঠিক" | ভাষা নয়, নিয়ম সঠিকতা আনে | Test (কঠিন input সহ) |
| Python-এ `subprocess.run(cmd, shell=True)` | Injection — Bash-এর সব সমস্যা ফিরে আসে | List argument (L05-04) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Bash-এর unquoted variable ও `eval` injection-এর বড় উৎস (L04-02)।
  - Python-এ `shell=True` একই ঝুঁকি ফিরিয়ে আনে।
  - যেকোনো ভাষায় untrusted input-এর parsing কঠোর রাখুন, এবং অচেনা input গুনে জানান।
- **Performance:**
  - সাধারণ ops কাজে পার্থক্য নগণ্য (Section 9.3)।
  - Bash loop-এ লাইন-প্রতি process তৈরি করলে বিশাল পার্থক্য হয় — awk বা Python ব্যবহার করুন।
- **Cost:**
  - নিঃশব্দ ভুল (হারানো error, ভুল alert) এবং অরক্ষণীয় script-এর engineer-সময় — এগুলোই আসল খরচ।

## 14. Hands-on exercise

1. `top_errors.sh`-কে ঠিক করুন যাতে encode-না-করা space-এ ভুল না করে (ইঙ্গিত: awk-এ `match()` দিয়ে quote-এর ভেতরের অংশ নিন, বা `"HTTP/` খুঁজুন)। কত লাইন বাড়ল, এবং পাঠযোগ্যতা কেমন হলো?
2. `top_errors.sh`-এ `jq -n --arg` দিয়ে JSON তৈরি করুন (Ubuntu: `sudo apt install jq`)। একটি কৃত্রিম path-এ নিয়ন্ত্রণ-অক্ষর (tab) দিয়ে পুরোনো ও নতুন সংস্করণ তুলনা করুন।
3. নিজের লেখা (বা কোনো পুরোনো) একটি Bash script নিয়ে Section 3-এর checklist প্রয়োগ করুন: Bash-এ থাকবে নাকি Python-এ যাবে, লিখিত যুক্তিসহ।
4. L04-06-এর `backup_safe.sh`-এর fingerprint ও rotation অংশ Python-এ লিখে Bash থেকে ডাকুন (hybrid)। Test-ও লিখুন।
5. `gen_log.py`-তে আরো একটি কঠিন লাইন যোগ করুন (যেমন IPv6 address বা খুব লম্বা path), এবং দুই সংস্করণ তুলনা করুন।

## 15. Mini-project — Module 04-এর tool-গুলোর পুনর্মূল্যায়ন

এই module-এ লেখা প্রতিটি script-এর জন্য:

- লাইন সংখ্যা ও কোন lesson-এর কোন bug।
- Checklist-এর ফল।
- সিদ্ধান্ত: Bash থাকবে / hybrid / Python।

ফলাফল একটি ADR হিসেবে লিখুন (L00-05)। Module 05-এর lesson-গুলো (log analysis, health check, backup verification) এই সিদ্ধান্তের উপর গড়ে উঠবে।

## 16. Interview প্রশ্ন

1. কোন পরিস্থিতিতে Bash script লিখবেন, কোনটিতে Python?
2. একটি বড় Bash script কীভাবে নিরাপদে Python-এ migrate করবেন?
3. Bash-এ JSON নিয়ে কাজ করার ঝুঁকি কী?
4. Field-ভিত্তিক text parsing-এর দুর্বলতা কী? উদাহরণ দিন।
5. Python script থেকে shell command চালানোর নিরাপদ উপায় কী?

## 17. Self-assessment প্রশ্ন

1. হাতুড়ি-ড্রিল analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 9.2-এ কোন দুটি প্রত্যাশা ভুল ছিল?
3. Bash সংস্করণ কোন লাইনে, কেন error হারাল?
4. গতির মাপ সিদ্ধান্তে কতটা গুরুত্বপূর্ণ ছিল, এবং কেন?
5. Section 5-এর migration-এর চারটি ধাপ কী?

## 18. সংক্ষিপ্ত সারাংশ

- Bash: command জোড়া, ছোট ও রৈখিক কাজ, process ও signal।
- Python: data structure, জটিল logic, API, test, কঠোর parsing।
- Checklist: ১০০+ লাইন, nested data, দশমিক বা তারিখ, API, test-এর প্রয়োজন, বা নিঃশব্দ ভুলের উচ্চ ঝুঁকি — Python।
- গতি সাধারণত নির্ধারক নয়; সঠিকতা ও রক্ষণাবেক্ষণযোগ্যতা নির্ধারক।
- ভাষা নয় — স্পষ্ট parsing-নিয়ম ও কঠিন input-সহ test সঠিকতা আনে।
- Migration ধাপে ধাপে: characterization test → ভঙ্গুর অংশ Python-এ → পাতলা orchestrator।

## 19. Completion checklist

- [ ] দুই সংস্করণ চালিয়ে Section 9-এর পার্থক্য নিজে দেখেছি
- [ ] Bash সংস্করণ ঠিক করার চেষ্টা করে খরচ বুঝেছি (Exercise ১)
- [ ] নিজের একটি script-এ checklist প্রয়োগ করেছি
- [ ] `python3 -m unittest -v`-এ ৪টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Google Shell Style Guide — "When to use Shell": https://google.github.io/styleguide/shellguide.html#when-to-use-shell
- GNU Awk User's Guide: https://www.gnu.org/software/gawk/manual/gawk.html
- Python `re` — Regular expression operations: https://docs.python.org/3/library/re.html
- Python `json`: https://docs.python.org/3/library/json.html
- Nginx `log_format` (escape রীতি): https://nginx.org/en/docs/http/ngx_http_log_module.html#log_format
- `jq` manual: https://jqlang.org/manual/

---

**পরের lesson:** L05-01 — Python environment: version, venv, pip, pyproject (Module 04 সম্পূর্ণ — তার আগে [Module 04 labs](../labs/04-bash-and-shell-automation/README.md) ও [quiz](../assessments/04-bash-and-shell-automation/quiz.md))
