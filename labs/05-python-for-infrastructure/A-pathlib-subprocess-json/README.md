# Lab 05-A — pathlib, json ও subprocess: আগে অনুমান, পরে যাচাই

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৪৫–৬০ মিনিট |
| **Environment** | Python ৩.১১+ — Ubuntu, Fedora বা Windows |
| **Label** | — (শুধু temp directory-তে; system বদলায় না) |
| **Tested** | `experiments.py` চালানো হয়েছে Python 3.14.5, Windows-এ (২০২৬-১০-২৭)। Answer key-তে সেই আসল output। Linux-এ যেগুলো ভিন্ন হওয়ার কথা, সেগুলো আলাদা করে চিহ্নিত — **Linux-এ চালানো হয়নি**। |

## Objective

Ops script-এর অনেক bug আসে "আমি ভেবেছিলাম এটা এভাবে কাজ করে" থেকে। এই lab-এ ১৫টি ছোট experiment-এর ফল **আগে লিখে অনুমান** করবেন, তারপর চালিয়ে মেলাবেন। ভুল অনুমানগুলোই এই lab-এর আসল শিক্ষা।

## Prerequisites

- [L05-02](../../../05-python-for-infrastructure/L05-02-python-fundamentals-type-hints.md), [L05-03](../../../05-python-for-infrastructure/L05-03-files-and-pathlib.md), [L05-04](../../../05-python-for-infrastructure/L05-04-subprocess-safely.md), [L05-05](../../../05-python-for-infrastructure/L05-05-json-yaml-config.md)

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/05-python-for-infrastructure/A-pathlib-subprocess-json
python3 --version
```

File: [`experiments.py`](experiments.py) — প্রতিটি experiment একটি ছোট function। **চালানোর আগে code পড়বেন না** (শুধু নিচের প্রশ্ন দেখুন)।

## Steps

1. Notebook-এ ১ থেকে ১৫ পর্যন্ত একটি তালিকা বানান। প্রতিটির পাশে আপনার অনুমান লিখুন — **চালানোর আগে**।

   | # | প্রশ্ন |
   |---|---|
   | 1 | `PurePosixPath("/srv/app") / "/etc/passwd"` কী হবে? |
   | 2 | `backup-2026.tar.gz`-এর `suffix`, `suffixes`, `stem`? |
   | 3 | একটি directory-তে `a.log`, `.hidden.log`, `b.txt` আছে। `Path.glob("*.log")` কোনগুলো দেবে? |
   | 4 | `PurePosixPath("logs/../etc/./x.conf").parts`? `..` কি resolve হয়? |
   | 5 | `json.loads('{"port": 8000, "port": 9000}')`? Error, নাকি কিছু একটা? |
   | 6 | `json.dumps({"ratio": float("nan")})`? এটা কি বৈধ JSON? |
   | 7 | `{1: "one"}` → `json.dumps` → `json.loads`: আগের মতো ফিরবে? |
   | 8 | `json.loads('{"replicas": 1e400}')`? |
   | 9 | `json.dumps({"name": "ঢাকা"})` — default ও `ensure_ascii=False`-এ পার্থক্য? |
   | 10 | `isinstance(True, int)`, `True + True`, `{1: "a", True: "b"}`? |
   | 11 | `subprocess.run([... "sys.exit(3)"])` — exception, নাকি কিছু ফেরত? |
   | 12 | `subprocess.run([python, "-c", "print(sys.argv[1:])", "my file.txt", "*.log", "$HOME"])` কী print করবে? |
   | 13 | `shlex.split('tar czf "my backup.tgz" --exclude=\'*.tmp\' /data')` ও `shlex.quote("it's")`? |
   | 14 | `capture_output=True` (`text` ছাড়া)-এ `print('ok')`-এর `stdout`; `== "ok\n"`? |
   | 15 | ৫ s ঘুমানো child-এ `timeout=0.5`? |

2. চালান:

   ```bash
   python3 experiments.py
   ```

3. প্রতিটি মিলিয়ে ✓ বা ✗ দিন। প্রতিটি ✗-এর জন্য এক লাইনে লিখুন: কেন ভুল ভেবেছিলেন, এবং কোন ops script-এ এই ভুল ক্ষতি করতে পারত।
4. দুটি experiment নিজে বদলে দেখুন (যেমন ৩-এ `rglob`; ১২-এ `shell=True` + string — **শুধু এই নিরীহ উদাহরণে**)।

## Expected behavior

- `experiments.py` exit ০ দেয়, ১৫টি লাইন print করে।
- কয়েকটির "উত্তর" অপ্রত্যাশিত — সেটাই উদ্দেশ্য।

## Verification

```bash
python3 experiments.py | wc -l        # 15
python3 experiments.py 5 7 14          # আলাদা করে আবার দেখা
```

Lab সম্পন্ন: notebook-এ ১৫টি অনুমান, ✓/✗, এবং প্রতিটি ✗-এর ব্যাখ্যা।

## Answer key — আসল output (Python 3.14.5, Windows) ও ব্যাখ্যা

<details><summary>নিজের তালিকা শেষ করার পরে খুলুন</summary>

```text
 1. PurePosixPath('/etc/passwd')
 2. ('.gz', ['.tar', '.gz'], 'backup-2026.tar')
 3. ['.hidden.log', 'a.log']
 4. ('logs', '..', 'etc', 'x.conf')
 5. {'port': 9000}
 6. '{"ratio": NaN}'
 7. ({'1': 'one'}, False)
 8. {'replicas': inf}
 9. ('{"name": "\\u09a2\\u09be\\u0995\\u09be"}', '{"name": "ঢাকা"}')
10. (True, 2, {1: 'b'})
11. 3
12. "['my file.txt', '*.log', '$HOME']"
13. (['tar', 'czf', 'my backup.tgz', '--exclude=*.tmp', '/data'], '\'it\'"\'"\'s\'')
14. (b'ok\r\n', False)
15. 'TimeoutExpired after 0.5s'
```

| # | কেন | Ops-এ ঝুঁকি |
|---|---|---|
| 1 | Absolute অংশ আগের সব মুছে দেয় | User-এর দেওয়া নাম `/etc/passwd` হলে "base directory-র ভেতরে" লেখা আসলে বাইরে যায় — path traversal। `resolve()` + `is_relative_to(base)` যাচাই করুন |
| 2 | `suffix` শুধু শেষেরটা | `.tar.gz` চিনতে `suffixes` বা `name.endswith` |
| 3 | **pathlib-এর `*` hidden file-ও ধরে**, shell-এর `*` ধরে না | Shell-এর অভ্যাসে লেখা cleanup `.hidden` file মুছে দিতে পারে |
| 4 | `..` আক্ষরিক থাকে; `resolve()` না করলে বোঝা যায় না কোথায় যাচ্ছে | ১-এর মতো traversal |
| 5 | Duplicate key-তে শেষেরটা নীরবে জেতে | L05-05: `object_pairs_hook` |
| 6 | `NaN` **বৈধ JSON নয়**; Python default-এ লেখে | অন্য ভাষার parser (`jq`, JavaScript-এর `JSON.parse`) ব্যর্থ হবে; `allow_nan=False` |
| 7 | JSON-এর key সবসময় string | Round-trip-এর পরে `d[1]` → `KeyError` |
| 8 | Overflow নীরবে `inf` | `replicas: inf` — validation-এ সীমা দরকার |
| 9 | Default-এ non-ASCII escape হয় | Log পড়তে অসুবিধা; `ensure_ascii=False` + UTF-8 |
| 10 | `bool` হলো `int`; `True == 1`, একই hash | Config-এ `port: true` সাধারণ `isinstance` যাচাই পেরিয়ে যায় (L05-05) |
| 11 | `check=True` ছাড়া exception নেই | ব্যর্থ command "সফল" ধরে নেওয়া (L05-04) |
| 12 | List argument-এ কোনো shell নেই — space, `*`, `$HOME` আক্ষরিক | এটাই নিরাপদ আচরণ; glob চাইলে `Path.glob` |
| 13 | `shlex` POSIX shell-এর নিয়মে ভাঙে ও quote করে | Log-এ command দেখাতে `shlex.join` |
| 14 | `text=True` ছাড়া `bytes`; **Windows-এ `\r\n`** | `b"ok\r\n" != "ok\n"` — `text=True` ও `.strip()`; Linux-এ `b'ok\n'` হওয়ার কথা (চালানো হয়নি) |
| 15 | Timeout-এ child বন্ধ করে exception | Grandchild থাকলে এতটা সরল নয় (L05-04) |

</details>

## Cleanup / reset

কিছু লাগে না — সব experiment নিজের temp directory মুছে ফেলে।

## Assessment

1. কোন তিনটি experiment-এ আপনার অনুমান ভুল ছিল? প্রতিটির জন্য একটি বাস্তব ops ঝুঁকি লিখুন।
2. Experiment ১ ও ৪ মিলিয়ে একটি `safe_join(base, user_path)` function লিখুন, যা base-এর বাইরে গেলে `ValueError` দেয়। ৫টি test লিখুন।
3. Experiment ৬ ও ৮: একটি JSON config validator-এ কোন দুটি যাচাই যোগ করবেন?
4. Experiment ১৪-এর পার্থক্য CI-তে (Linux) ও আপনার laptop-এ (Windows) কোন ধরনের "আমার machine-এ চলে" সমস্যা তৈরি করতে পারে?
