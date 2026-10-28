# Module 05 Quiz — Python for Infrastructure

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৭৫ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে Python না চালিয়ে উত্তর দিন, পরে চালিয়ে যাচাই করুন।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. venv-এ `sys.prefix` ও `sys.base_prefix`-এর সম্পর্ক কী?
2. PEP 668 কী, এবং Ubuntu-তে system Python-এ `pip install` করলে কী হয়?
3. Library ও application-এর dependency নির্দিষ্ট করার নিয়মের পার্থক্য কী?
4. Python-এর type hint runtime-এ কী যাচাই করে?
5. `@dataclass(frozen=True)`-এর দুটি সুবিধা।
6. `(str, Enum)` ও `StrEnum`-এর `str()`-এ পার্থক্য, এবং argparse-এ কোথায় চোখে পড়ে?
7. Atomic write-এর চারটি ধাপ।
8. Temp file কেন target-এর **একই directory**-তে বানাতে হয়?
9. Cleanup script-এ symlink অনুসরণ কেন বিপজ্জনক?
10. `shell=True`-এর বিপদ কী, এবং নিরাপদ বিকল্প কী?
11. Subprocess-এর timeout দিলেও script কীভাবে ঝুলে থাকতে পারে?
12. কোন HTTP status-এ retry করবেন, কোনগুলোয় কখনো নয়?
13. Exponential backoff-এ jitter কেন দরকার?
14. Idempotency key কী সমস্যার সমাধান করে?
15. Structured (JSON) log-এর দুটি সুবিধা।
16. নতুন thread-এ `contextvars`-এর request id কেন হারায়, এবং সমাধান কী?
17. Monitoring-plugin রীতিতে exit code ০/১/২/৩-এর অর্থ।
18. Secret-এর উৎস হিসেবে env var ও `NAME_FILE`-এর ঝুঁকির পার্থক্য।
19. Liveness ও readiness check-এর পার্থক্য।
20. Backup-এর checksum PASS মানে কী, এবং কী মানে নয়?

## Part B — Code reading / output prediction (প্রতিটি ২ নম্বর)

21. Output কী?

    ```python
    from pathlib import PurePosixPath
    print(PurePosixPath("/srv/app") / "/etc/passwd")
    ```

22. Output কী?

    ```python
    import json
    print(json.loads('{"port": 8000, "port": 9000}'))
    print(json.loads(json.dumps({1: "a"})))
    ```

23. এই config-এ `validate` কী বলা উচিত, এবং সাধারণ `isinstance(v, int)` কেন ব্যর্থ হয়?

    ```python
    cfg = {"server": {"port": True}}
    ```

24. এই code-এ দুটি সমস্যা চিহ্নিত করুন:

    ```python
    subprocess.run(f"tar czf /backup/{name}.tgz /data", shell=True)
    ```

25. `python3 tool.py --json disk /`-এ `args.json` কত, এবং কেন?

    ```python
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--json", action="store_true")
    ap = argparse.ArgumentParser(parents=[common])
    sub = ap.add_subparsers(dest="cmd")
    sub.add_parser("disk", parents=[common]).add_argument("path")
    ```

26. এই regex কেন `DB_PASSWORD = "<১২ অক্ষরের একটি আসল-দেখতে মান>"` ধরনের লাইন ধরে না?

    ```python
    re.compile(r'(?i)\b(?:password|token)\w*\s*=\s*"([^"]{8,})"')
    ```

27. নিচের retention নিয়মে ২০২৪-১২-৩০ ও ২০২৫-০১-০৫ কয়টি সপ্তাহ হিসেবে গোনা হবে, এবং কেন এটা bug?

    ```python
    key = (d.year, d.isocalendar()[1])
    ```

28. এই health checker deadline ৪ s-এ report দেয়, কিন্তু process ২০ s পরে বের হয়। কেন?

    ```python
    pool = ThreadPoolExecutor(8)
    futures = [pool.submit(check, c) for c in checks]
    done, pending = wait(futures, timeout=4)
    pool.shutdown(wait=False, cancel_futures=True)
    ```

29. এই function `python -O`-এ কী আচরণ করবে?

    ```python
    def create(title):
        task_id = insert(title)
        assert task_id is not None
        return get(task_id)
    ```

30. এই sync code-এ ফাঁদ কী, যখন API ঝুলে থাকে বা ভাঙা JSON দেয়?

    ```python
    with open(out, "w") as f:
        try:
            data = json.loads(urllib.request.urlopen(url).read())
            json.dump(summarise(data), f)
        except Exception as exc:
            print("sync failed:", exc)
    sys.exit(0)
    ```

## Part C — Scenario (প্রতিটি ৪ নম্বর)

31. Ubuntu ২৪.০৪-এ upgrade-এর পরে একটি monitoring script `ModuleNotFoundError: requests` দিচ্ছে, আর `sudo pip install requests` দিচ্ছে `externally-managed-environment`। কী ঘটেছে, এবং দীর্ঘমেয়াদি সমাধান কী (systemd-এর `ExecStart` সহ)?

32. Deploy script প্রতিটি নতুন instance-এর `/health` দেখে। এক রাতে script ৬ ঘণ্টা ঝুলে রইল। পরের সপ্তাহে "সমাধান" হিসেবে প্রতি সেকেন্ডে অসীম retry যোগ করা হলো, এবং পরের বিভ্রাটে service আবার পড়ে গেল। সঠিক নকশা কী? সংখ্যাসহ বলুন।

33. Centralized logging-এ audit-এ একটি database password পাওয়া গেছে। দুটি সম্ভাব্য পথ কী? আপনার প্রথম তিনটি কাজ কী? কোন স্তরের প্রতিরোধ ভবিষ্যতে এটা ঠেকাবে?

34. ১ ঘণ্টার nginx log-এ 5xx rate ১.৯%, p50 ৫০ ms, কিন্তু customer-রা "অর্ডার দিতে পারছি না" বলছেন। কীভাবে তদন্ত করবেন, এবং কোন সংখ্যা সমস্যাটা প্রকাশ করবে?

35. "Backup job প্রতিদিন সফল", কিন্তু restore-এর দিন file ৩০ byte। কী ঘটেছিল হতে পারে (bash pipeline)? এবং `verify_backup.py`-এর কোন ধাপ প্রথম রাতেই ধরত? একটি backup-এর checksum PASS, archive PASS, কিন্তু তবুও restore অকেজো — কীভাবে সম্ভব?

---

## Answer key

<details><summary>Part A</summary>

1. venv-এ `sys.prefix` = venv directory, `sys.base_prefix` = মূল interpreter। দুটো ভিন্ন হলে venv-এর ভেতরে (L05-01)।
2. Distribution-এর Python-এ `EXTERNALLY-MANAGED` marker থাকে, তাই pip system-এ install প্রত্যাখ্যান করে (`externally-managed-environment`)। সমাধান venv/pipx, `--break-system-packages` নয়।
3. Library: `pyproject.toml`-এ range (অন্যের সাথে মানিয়ে নেওয়ার জন্য)। Application: lock file-এ সব (transitive সহ) নির্দিষ্ট version, hash-সহ।
4. কিছুই না — শুধু annotation জমা রাখে। যাচাই static checker (mypy) বা নিজের validation code-এর কাজ।
5. দুর্ঘটনাজনিত পরিবর্তন আটকায়; hashable, তাই `set`/`dict` key হিসেবে ব্যবহার করা যায়।
6. `(str, Enum)` → `'Env.PROD'`; `StrEnum` → `'prod'`। argparse-এর `choices` help-এ `{Env.DEV,…}` দেখায়।
7. Temp file লেখা → flush + `fsync` → (mode কপি) → `os.replace`।
8. `os.replace` atomic শুধু একই filesystem-এ; ভিন্ন mount-এ `EXDEV`।
9. Symlink বাইরের directory বা loop-এ নিয়ে যেতে পারে; আক্রমণকারী symlink রেখে root-এর cleanup দিয়ে গুরুত্বপূর্ণ file মুছিয়ে নিতে পারে।
10. বাইরের মান shell-এ command হিসেবে ব্যাখ্যা হয় (injection)। বিকল্প: list argument, shell ছাড়া; দরকারে `shlex.quote` বা env দিয়ে মান পাঠানো।
11. Grandchild process pipe খোলা রাখে, তাই `communicate()` EOF-এর অপেক্ষায় থাকে। সমাধান: `start_new_session` + `killpg` (মাপা হয়েছে: ১ s timeout = ৬.০৬ s, L05-04)।
12. Retry: connection error/timeout, 429 (Retry-After), 502/503/504 — idempotent request-এ। কখনো নয়: 400/401/403/404/422; key ছাড়া POST।
13. সব client একসাথে retry করলে সবে সেরে ওঠা server আবার পড়ে যায় (thundering herd)।
14. POST retry-তে duplicate কাজ (দুটি order/charge) — server একই key চিনে আগের ফল ফেরত দেয়।
15. Machine-এ খোঁজা/filter করা যায়; field-ভিত্তিক context (request_id, db), এবং traceback এক field-এ।
16. নতুন thread খালি context দিয়ে শুরু হয় (সাধারণ CPython build)। সমাধান: `contextvars.copy_context().run(fn)`।
17. ০ OK, ১ WARNING, ২ CRITICAL, ৩ UNKNOWN।
18. Env var child process, `/proc/PID/environ`, crash/debug dump, `docker inspect`-এ ছড়ায়। `NAME_FILE`-এ env-এ শুধু path থাকে, এবং file-এর permission দিয়ে নিয়ন্ত্রণ করা যায়।
19. Liveness: process জীবিত (ব্যর্থ হলে restart)। Readiness: traffic নিতে প্রস্তুত (ব্যর্থ হলে traffic সরানো, restart নয়)।
20. File backup-এর পরে বদলায়নি — এটুকুই। Backup নেওয়ার সময়ের ভুল, অনিরাপদ বিষয়বস্তু বা নষ্ট database-এর বিষয়ে কিছু বলে না।

</details>

<details><summary>Part B</summary>

21. `/etc/passwd` — absolute অংশ আগেরটা মুছে দেয় (path traversal-এর ঝুঁকি)।
22. `{'port': 9000}` (duplicate-এ শেষেরটা নীরবে); `{'1': 'a'}` — JSON key সবসময় string।
23. `server.port: expected int, got bool True`। `bool` হলো `int`-এর subclass, তাই `isinstance(True, int)` সত্য — আলাদাভাবে `bool` বাদ দিতে হয় (L05-05)।
24. (১) `name` shell-এ ব্যাখ্যা হয় — injection। (২) Timeout নেই, return code দেখা হয় না (`check`)। সাথে glob/space-ও সমস্যা।
25. `False` — subparser-এর default মূল parser-এর মান মুছে দেয়। সমাধান: `default=argparse.SUPPRESS` (L05-08)।
26. `DB_PASSWORD`-এ `_` ও `P` দুটোই word character — মাঝে `\b` নেই। সমাধান: `\b\w*(?:password|…)`। (তাছাড়া `(?i)`-এর পরিধি নিয়ে সতর্ক থাকুন — L05-10।)
27. দুটি — (2024, 1) ও (2025, 1); অথচ ISO-তে দুটোই 2025-W01। `isocalendar()[:2]` (ISO বছর, সপ্তাহ) ব্যবহার করুন (L05-09)।
28. `ThreadPoolExecutor`-এর worker non-daemon। Interpreter বন্ধের সময় `atexit` চলমান worker-এর শেষের অপেক্ষা করে; `cancel_futures` শুধু শুরু না হওয়া কাজ বাতিল করে। সমাধান: daemon thread + `join(বাকি সময়)` (L05-12)।
29. `-O` দিলে `assert` মুছে যায় — `None` id দিয়েই `get` চলে, এবং অদ্ভুত ফল আসে। স্পষ্ট `if … raise` ব্যবহার করুন (L05-09, L05-13)।
30. `open(out, "w")` data আসার আগেই পুরোনো file শূন্য করে; `urlopen`-এ timeout নেই; `except Exception` সব কিছু গিলে stdout-এ লেখে; শেষে exit ০ (নীরব ব্যর্থতা)। এটাই Lab 05-C।

</details>

<details><summary>Part C — মূল্যায়নের মূল বিষয়</summary>

31.
- **কী ঘটেছে:** আগে `sudo pip` দিয়ে system Python-এ install করা হয়েছিল। Upgrade-এ Python-এর version বদলেছে (৩.১০ → ৩.১২), এবং নতুন version-এ PEP 668 আছে।
- **সমাধান:**
  - `apt install python3-venv`।
  - `/opt/monitoring/.venv` বানিয়ে lock file থেকে install।
  - `ExecStart=/opt/monitoring/.venv/bin/python /opt/monitoring/check.py`।
  - পরের upgrade-এ শুধু venv আবার তৈরি; `--break-system-packages` কখনো নয়।
- **(৪ নম্বর:** কারণ ১, venv ১, ExecStart ১, পুনর্নির্মাণ/lock ১।)

32.
- প্রতিটি call-এ timeout (যেমন connect ও read ৫ s)।
- সীমিত retry (৩–৫), শুধু অস্থায়ী ব্যর্থতায়।
- Exponential backoff + full jitter (base ০.৫ s, cap ১০ s)।
- `Retry-After` মানা।
- মোট deadline (যেমন ২ মিনিট)।
- শেষে স্পষ্ট ব্যর্থতা (exit ≠ ০), যাতে pipeline rollback করতে পারে।
- Retry একটিই স্তরে।

33.
- **দুটি পথ:**
  - f-string-এ DSN সরাসরি log।
  - Driver-এর exception message-এ DSN, যা `log.exception`-এর traceback-এ যায়।
- **প্রথম তিন কাজ:**
  - Password rotate।
  - Access/audit দেখা (কে পড়েছে, কোথায় copy আছে)।
  - Log-এ ছড়ানো copy নির্ণয় ও retention অনুযায়ী মোছা।
- **প্রতিরোধ:**
  - DSN-এ password না রাখা (`*_FILE`)।
  - `SecretStr`।
  - Handler-এ redaction filter (message, extra, traceback)।
  - Test-এ `assertNotIn`।
  - Pipeline-এ redaction।

34.
- প্রতি মিনিটের 5xx ও p99-এর সময়রেখা।
- Endpoint অনুযায়ী ভাগ।
- Incident window আলাদা করে দেখা।
- উদাহরণে `/api/orders`-এ ০৯:২০–০৯:২৪-এ 5xx ৭.৭% ও p99 ৪.৬৮ s, যা পুরো ঘণ্টার গড়ে "পাতলা" হয়ে গিয়েছিল।
- গড় নয় — percentile, সময়রেখা ও ভাগ।

35.
- **কী ঘটেছিল:** `pg_dump | gzip`, `pipefail` ছাড়া — dump ব্যর্থ, কিন্তু gzip খালি stream compress করে ০ দিয়েছে।
- **কোন ধাপ ধরত:** `size` (`--min-bytes`) প্রথম রাতেই; test restore/application check-ও।
- **Checksum + archive PASS, তবুও অকেজো:**
  - Database file নিজেই নষ্ট — শুধু `PRAGMA integrity_check`-এর মতো application check ধরে।
  - অথবা ভুল database-এর backup।
  - অথবা অনিরাপদ বিষয়বস্তু (traversal)।

</details>

## Scoring

| অংশ | নম্বর |
|---|---|
| Part A | ২০ × ১ = ২০ |
| Part B | ১০ × ২ = ২০ |
| Part C | ৫ × ৪ = ২০ |
| **মোট** | **৬০** — pass ≥ ৪২ |

ফল [05-python-for-infrastructure/PROGRESS.md](../../05-python-for-infrastructure/PROGRESS.md)-এর Module assessment table-এ লিখুন।
