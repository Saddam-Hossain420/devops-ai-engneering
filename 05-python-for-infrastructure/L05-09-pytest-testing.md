# L05-09 — pytest দিয়ে unit ও integration testing

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-08 — argparse CLI](L05-08-argparse-cli.md), [L04-07 — ShellCheck ও bats](../04-bash-and-shell-automation/L04-07-shellcheck-bats-testing.md) |
| **Label** | — |
| **Tested** | `retention.py`: pytest-এ ২২টি test পাস (pytest 9.1.1, Python 3.14.5, Windows); `-m "not integration"`-এ ২০টি। unittest wrapper-এর ৩টি test পাস (একটি পুরো pytest suite চালায়)। প্রথম run-এ **২টি test ব্যর্থ হয়েছিল — ভুল ছিল test-এর প্রত্যাশায়, code-এ নয়** (Section 9.3)। নমুনা backup directory-তে CLI-এর dry-run চালানো হয়েছে। `pytest-cov` এই machine-এ নেই, তাই coverage **মাপা হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- pytest-এর মূল ধারণা: সাধারণ function + `assert`, assertion rewriting, test discovery।
- **Fixture:** `tmp_path`, `capsys`, `monkeypatch`, নিজের fixture, **factory fixture**, `conftest.py`।
- **`parametrize`** — একটি test, অনেক input (edge case-এর তালিকা)।
- **Marker:** `@pytest.mark.integration`, `-m "not integration"`, `--strict-markers`।
- Unit বনাম integration test: কোনটা কী যাচাই করে, কোনটা কতটা।
- সময়-নির্ভর code test করা (`now` inject করা)।
- **Safety property** test: "কখনো নতুনতম backup মুছবে না"।
- pytest ও unittest একসাথে; pytest না থাকা CI-তে কী করবেন।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Backup retention script-এর একটি ভুল হলে দুটির একটি ঘটে:

- **বেশি রাখা** — disk ভরে যায়, এবং backup job নিজেই ব্যর্থ হয়।
- **বেশি মোছা** — যেদিন restore দরকার, সেদিন দেখা যায় শেষ ৩০ দিনের backup নেই।

দ্বিতীয়টি সাধারণত **মাস পরে** ধরা পড়ে, যখন আর কিছু করার নেই।

এ ধরনের code-এ manual testing ("একবার চালিয়ে দেখলাম ঠিক আছে") যথেষ্ট নয়, কারণ ভুলগুলো থাকে কোণায়:

- বছরের শেষ সপ্তাহ।
- Leap day।
- একই দিনে চারটি backup।
- Server-এর ঘড়ি এগিয়ে থাকা।
- নামের সাথে না মেলা file।

Automated test এই কোণাগুলোকে স্থায়ী "পাহারাদার" বানায় — পরে কেউ code বদলালে CI সাথে সাথে বলে দেয় কী ভাঙল।

## 3. সহজ ভাষায় পরিচয়

```python
# tests/test_retention.py — pytest-style
import pytest, retention as r

def test_parse_name():
    assert r.parse_name("README.md") is None             # সাধারণ assert

@pytest.mark.parametrize("name", ["db-20261332T0300Z.sql.gz", "db-20250229T0300Z.sql.gz"])
def test_impossible_dates(name):
    assert r.parse_name(name) is None

def test_cli(tmp_path, capsys):                          # fixture: নাম দিয়ে চাওয়া
    (tmp_path / "x.txt").write_text("hi")
    r.main([str(tmp_path)])
    assert "ignored=1" in capsys.readouterr().out
```

```bash
python3 -m pytest -v                    # সব
python3 -m pytest -k iso_week           # নামে মিললে
python3 -m pytest -m "not integration"  # দ্রুত unit test
python3 -m pytest -x --lf               # প্রথম ব্যর্থতায় থামো; শুধু আগের ব্যর্থগুলো
```

| | unittest | pytest |
|---|---|---|
| Install | stdlib | `pip install pytest` |
| Test | `class X(TestCase)` + `self.assertEqual` | সাধারণ function + `assert` |
| Setup | `setUp`/`tearDown` | Fixture (পুনর্ব্যবহারযোগ্য, scope) |
| অনেক input | `subTest` | `parametrize` (প্রতিটি আলাদা test) |
| Failure বার্তা | `AssertionError: 7 != 9` | মধ্যবর্তী মানসহ বিস্তারিত (Section 9.2) |

pytest unittest-এর test-ও চালাতে পারে, কিন্তু উল্টোটা নয়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### বিমানের pre-flight checklist

- **Unit test** = প্রতিটি যন্ত্রাংশ আলাদাভাবে পরীক্ষা (fuel gauge সঠিক দেখায় কিনা)।
- **Integration test** = পুরো ব্যবস্থা একসাথে — engine চালু করে gauge-এর কাঁটা নড়ে কিনা।
- **Parametrize** = একই পরীক্ষা বিভিন্ন অবস্থায় (খালি ট্যাংক, অর্ধেক, ভরা, উল্টে রাখা)।
- **Fixture** = পরীক্ষার আগে প্রস্তুত করা অবস্থা (hangar, নির্দিষ্ট তাপমাত্রা) — প্রতি পরীক্ষায় নতুন, পরে পরিষ্কার।
- **Safety property** = "দরজা খোলা থাকলে উড্ডয়ন অসম্ভব" — নির্দিষ্ট পরিস্থিতি নয়, **সব** পরিস্থিতিতে সত্য নিয়ম।

### Analogy কোথায় মেলে না

- Checklist-এর প্রতিটি লাইন বিমান-প্রস্তুতকারী লেখেন, যিনি নকশা জানেন। **Test লেখেন সেই মানুষ যিনি code লিখেছেন — তাঁর ভুল ধারণা test-এও যায়।** এই lesson-এ আসলে তাই ঘটেছে: দুটি test ব্যর্থ হয়েছিল কারণ আমার হিসাব ভুল ছিল, code নয় (Section 9.3)। Test spec-কে যাচাই করে না, শুধু code ও test-এর মিল যাচাই করে।
- Checklist পাস = উড্ডয়ন নিরাপদ (মোটামুটি)। **সব test পাস ≠ bug নেই।** যে পরিস্থিতির test নেই (যেমন DST, ভিন্ন time zone-এর নাম), সেখানে কিছুই জানা যায় না। Coverage বলে কোন লাইন চলেছে, কিন্তু কোন **পরিস্থিতি** পরীক্ষা হয়েছে তা বলে না।
- Hangar-এর তাপমাত্রা নিয়ন্ত্রণ করা যায়। **"এখন"-এর সময় test-এ নিয়ন্ত্রণ করতে হয় code-এর নকশা দিয়ে** (`now` parameter) — নইলে test আজ পাস করে, কাল ব্যর্থ হয়।

## 5. Real-world engineering scenario — "নতুন বছরের প্রথম সপ্তাহে weekly backup উধাও"

**পরিস্থিতি:** একটি retention script weekly backup রাখত `(date.year, date.isocalendar().week)` দিয়ে।

২০২৪-১২-৩০ (সোমবার) ও ২০২৫-০১-০৫ (রবিবার) একই ISO সপ্তাহে (2025-W01) পড়ে। কিন্তু `date.year` দিল ২০২৪ ও ২০২৫, ফলে script ভাবল দুটি আলাদা সপ্তাহ: (2024, 1) ও (2025, 1)।

ফলাফল:

- একটি "সপ্তাহ" দুবার গোনা হলো, আর `weekly=4` আসলে ৩টি ভিন্ন সপ্তাহ রাখল।
- তার চেয়েও খারাপ: (2024, 1) key-টি ২০২৪-এর জানুয়ারির প্রথম সপ্তাহের সাথে মিলে গেল — সেই বাকেট ভুলভাবে "আগেই দেখা" হিসেবে ধরা হলো।

এক বছর পরে audit-এ দেখা গেল, ডিসেম্বরের শেষ দুই সপ্তাহের weekly backup নেই।

**এই lesson-এর code** `d.isocalendar()[:2]` ব্যবহার করে — (ISO **বছর**, সপ্তাহ), যেখানে ISO বছর ক্যালেন্ডার বছর থেকে ভিন্ন হতে পারে। আর `test_iso_week_across_new_year` এই কোণাটা স্থায়ীভাবে পাহারা দেয়।

**শিক্ষা:** Bug-এর জন্য test আগে লিখুন (ব্যর্থ হবে), তারপর ঠিক করুন (পাস হবে)। তখন সেই bug আর কখনো নীরবে ফিরে আসবে না — একে বলে regression test।

## 6. Diagram — test-এর কাঠামো

```text
 code/L05-09/
 ├── retention.py              ← যা test হচ্ছে (parse_name, plan, main)
 ├── pytest.ini                ← testpaths=tests, marker নিবন্ধন, --strict-markers
 ├── test_l05_09.py            ← unittest wrapper (CI-র `unittest discover` এটা পায়)
 │      ├─ CoreTest: ২টি মূল test (pytest ছাড়াও চলে)
 │      └─ PytestSuite: pytest থাকলে `python -m pytest` subprocess-এ, না থাকলে skip
 └── tests/                    ← __init__.py নেই → unittest discovery ঢোকে না
        ├── conftest.py        ← fixture: now, make_backups (factory) — সব test file পায়
        └── test_retention.py
               ├─ unit:        parametrize(parse_name ×7), counts ×5, newest-per-day, ISO week
               ├─ safety:      future কখনো মোছা নয়, অজানা file উপেক্ষা, newest কখনো মোছা নয় ×4
               └─ integration: CLI dry-run → --delete (tmp_path), ভুল argument   @pytest.mark.integration

 test pyramid:   অনেক দ্রুত unit  ▸  কিছু integration (filesystem, CLI)  ▸  অল্প end-to-end (Module 11)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Unit test | একটি function/অংশ আলাদাভাবে, বাইরের নির্ভরতা ছাড়া |
| Integration test | একাধিক অংশ বা আসল resource (filesystem, DB, network) একসাথে |
| Fixture | Test-এর জন্য প্রস্তুত করা অবস্থা বা object |
| Factory fixture | Fixture যা একটি function ফেরত দেয় — test নিজে parameter দেয় |
| `conftest.py` | Directory-র সব test-এর shared fixture |
| Parametrize | এক test-কে বহু input দিয়ে চালানো |
| Marker | Test-এর ট্যাগ (integration, slow) — বাছাই করে চালানো |
| Assertion rewriting | pytest `assert`-এর মধ্যবর্তী মান দেখায় |
| Regression test | একবার পাওয়া bug আবার না আসার পাহারাদার |
| Property / invariant | সব input-এ সত্য থাকা নিয়ম |
| Flaky test | একই code-এ কখনো পাস, কখনো ব্যর্থ |
| Coverage | কোন লাইন test-এ চলেছে তার মাপ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Discovery

pytest `testpaths`-এর ভেতরে `test_*.py` বা `*_test.py` file খোঁজে, সেখানে `test_` দিয়ে শুরু function এবং `Test` দিয়ে শুরু class।

`conftest.py` নিজে থেকে load হয়; এর fixture ওই directory ও subdirectory-র সব test পায়, কোনো import ছাড়াই।

### 8.2 Fixture-এর জীবনকাল

- Fixture-এর **scope:** default `function` — প্রতিটি test-এ নতুন। `module`/`session` scope-এ একবার তৈরি হয়ে ভাগ হয় (যেমন DB container — Module 20)।
- `yield`-এর পরের অংশ teardown।
- `tmp_path` প্রতিটি test-এ নতুন, খালি directory দেয়; pytest পুরোনোগুলো সময়মতো পরিষ্কার করে।

### 8.3 Assertion rewriting

pytest test file import করার সময় AST বদলে প্রতিটি `assert`-কে এমন code-এ রূপান্তর করে, যা ব্যর্থ হলে প্রতিটি অংশের মান দেখায়। তাই `self.assertEqual`-এর দরকার নেই।

এটা শুধু pytest-এর import করা test file-এ কাজ করে। `retention.py`-এর ভেতরের `assert` বদলায় না। Production code-এ `assert` দিয়ে validation করবেন না — `python -O` দিলে সব `assert` মুছে যায়।

### 8.4 সময়

`plan(paths, now, …)` "এখন" বাইরে থেকে নেয়। Test-এ `NOW = 2026-10-27 12:00 UTC` স্থির রাখা হয়, ফলে আজ, কাল বা এক বছর পরেও একই ফল।

বিকল্প হিসেবে `freezegun`/`time-machine` library আছে। তবে inject করাই সবচেয়ে সরল ও স্পষ্ট (L04-06-এর `--now`, L05-03-এর `now=`)।

### 8.5 এই repo-র CI ও pytest

এই repo-র CI (`validate.yml`) প্রতিটি lesson folder-এ `python3 -m unittest discover` চালায় এবং pytest install করে না।

- `tests/`-এ `__init__.py` নেই, তাই unittest সেগুলো import করে না। করলে `make_backups` fixture-এর মানে বুঝত না, এবং error দিত।
- `test_l05_09.py` wrapper pytest থাকলে পুরো suite চালায়, না থাকলে skip করে।

Module 11-এ CI-তে pytest install করে সরাসরি চালানো হবে।

> **Fedora-তে:** কোনো পার্থক্য নেই। pytest venv-এ install করুন (`python3 -m pip install pytest`), অথবা distribution package `python3-pytest` (Fedora ও Ubuntu দুটোতেই এই নাম)।

## 9. Practical demonstration

Files:

- [`code/L05-09/retention.py`](code/L05-09/retention.py), [`pytest.ini`](code/L05-09/pytest.ini)।
- [`tests/conftest.py`](code/L05-09/tests/conftest.py), [`tests/test_retention.py`](code/L05-09/tests/test_retention.py)।
- [`test_l05_09.py`](code/L05-09/test_l05_09.py) (unittest wrapper)।

### 9.1 চালানো

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-09
python3 -m pytest -q
python3 -m pytest -q -m "not integration"
python3 -m unittest -v                       # CI-এর মতো
```

**আসল output:**

```text
......................                                                   [100%]
22 passed in 0.39s

....................                                                     [100%]
20 passed, 2 deselected in 0.36s

test_newest_always_kept (test_l05_09.CoreTest.test_newest_always_kept) ... ok
test_parse_name (test_l05_09.CoreTest.test_parse_name) ... ok
test_pytest_suite_passes (test_l05_09.PytestSuite.test_pytest_suite_passes) ... ok
Ran 3 tests in 0.986s
OK
```

### 9.2 pytest-এর failure বার্তা — আসল নমুনা

একটি ইচ্ছাকৃত ব্যর্থ test (`assert sum(kept.values()) == 9`):

```text
>       assert sum(kept.values()) == 9
E       AssertionError: assert 7 == 9
E        +  where 7 = sum(dict_values([7, 0, 0]))
E        +    where dict_values([7, 0, 0]) = <built-in method values of dict object at 0x…>()
E        +      where <built-in method values of dict object at 0x…> = {'daily': 7, 'weekly': 0, 'monthly': 0}.values
```

কোন মান থেকে ৭ এল, তা debugger ছাড়াই দেখা যাচ্ছে।

### 9.3 প্রথম run-এ দুটি ব্যর্থতা — দোষ ছিল test-এর

```text
FAILED tests/test_retention.py::test_counts[7-4-3-10] - AssertionError: asser...
FAILED tests/test_retention.py::test_cli_dry_run_then_delete - AssertionError...
======================== 2 failed, 20 passed in 0.43s =========================
```

`capsys`-এ ধরা output দেখাল: ৩০ দিনে `--daily 7 --weekly 2 --monthly 1`-এ রাখা হয়েছে মাত্র ৭টি — আমার প্রত্যাশা ছিল ৯। কারণ:

- এই সপ্তাহ ও আগের সপ্তাহের সবচেয়ে নতুন backup (২৭ ও ২৫ অক্টোবর) **আগে থেকেই daily-তে** আছে।
- এই মাসের সবচেয়ে নতুনটাও (২৭ অক্টোবর)।

বাকেটগুলো overlap করে, এবং একই file একাধিক কারণে রাখা হয়। restic-এর `--keep-weekly`-ও এভাবেই গোনে।

সমাধান code বদলানো নয়, **spec থেকে সাবধানে হিসাব করা** এবং test-এ সেই হিসাব comment হিসেবে লেখা:

```python
# daily ২১–২৭ অক্টো; weekly: ২৭, ২৫ (দুটোই daily-তে আছে), ১৮, ১১ → +২; monthly: ২৭, ৩০ সেপ্টে, ৩১ আগস্ট → +২
(7, 4, 3, 11),
```

**শিক্ষা:** Test ব্যর্থ হলে প্রথম প্রশ্ন "code ভুল না প্রত্যাশা ভুল?" Test-কে code-এর মতো পাস করানোর জন্য বদলানো বিপজ্জনক। তাই কেন বদলানো হলো, তার যুক্তি test-এর পাশেই লিখে রাখুন।

### 9.4 CLI dry-run — আসল output

৬০ দিনের নমুনা backup ও একটি `db-latest.sql.gz` (scratchpad-এ বানানো), `--daily 3 --weekly 3 --monthly 3`:

```text
ignore  db-latest.sql.gz  (name does not match)
keep    db-20260831T0300Z.sql.gz  (monthly)
keep    db-20260930T0300Z.sql.gz  (monthly)
keep    db-20261018T0300Z.sql.gz  (weekly)
keep    db-20261025T0300Z.sql.gz  (daily, weekly)
keep    db-20261026T0300Z.sql.gz  (daily)
keep    db-20261027T0300Z.sql.gz  (newest, daily, weekly, monthly)
delete  db-20260829T0300Z.sql.gz  (dry-run)
…  (আরও ৫৩টি delete লাইন)
summary: keep=6 delete=54 ignored=1
```

প্রতিটি "keep"-এর পাশে **কারণ** — review-এ "এটা কেন রাখা হলো?" প্রশ্নের উত্তর সাথেই থাকে।

### 9.5 Ubuntu-তে (চালানো হয়নি)

```bash
python3 -m venv .venv && . .venv/bin/activate && pip install pytest pytest-cov
python3 -m pytest --cov=retention --cov-report=term-missing
```

কোন লাইন test-এ চলেনি তা দেখাবে। Coverage ১০০% হলেও Section 4-এর সতর্কতা মনে রাখুন।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `NAME` regex + `strptime` | নাম থেকে সময় | mtime copy/restore-এ বদলায়; নাম বদলায় না |
| `strptime`-এর `ValueError` → None | `20261332` | Regex মেলে, তারিখ অসম্ভব |
| `Z` বাধ্যতামূলক | UTC নিশ্চিত | Time zone-হীন সময় অস্পষ্ট |
| `isocalendar()[:2]` | (ISO বছর, সপ্তাহ) | Section 5-এর bug |
| `_bucket_keepers` | প্রতিটি বাকেটের নতুনতম | GFS নিয়ম |
| `future` | Clock skew-এর backup রাখা | ভুল ঘড়ির জন্য data হারানো নয় |
| `newest` সবসময় | Count ০ হলেও | শেষ backup কখনো নয় |
| `keep: dict[Path, list[str]]` | রাখার কারণ | Review ও debugging |
| `main(..., now=None)` | Test-এ সময় inject | নির্ভরযোগ্য test |
| `--strict-markers` | অজানা marker = error | `@pytest.mark.integation` typo ধরা |
| Factory fixture `make_backups` | Test নিজে দিন/সংখ্যা দেয় | এক fixture, অনেক পরিস্থিতি |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `python3 -m pytest -q` | `22 passed` |
| `-m "not integration"` | `20 passed, 2 deselected` |
| `python3 -m unittest -v` | ৩টি OK (pytest না থাকলে ১টি skip) |
| CLI dry-run | কিছু মোছে না; প্রতিটি keep-এর কারণ |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `ModuleNotFoundError: retention` | Test-এর path-এ module নেই | `conftest.py`-তে `sys.path`, বা package + `pip install -e .` |
| `fixture 'make_backups' not found` | `conftest.py` ভুল directory-তে | Test-এর সাথে বা উপরের directory-তে |
| unittest pytest-এর file চালিয়ে error দেয় | `tests/`-এ `__init__.py` | সরান, বা শুধু pytest দিয়ে চালান |
| Test আজ পাস, কাল ব্যর্থ | `datetime.now()` সরাসরি | `now` inject |
| CI-তে কখনো পাস, কখনো ব্যর্থ | Flaky: সময়, ক্রম, network, shared state | Fixture isolation; বাইরের নির্ভরতা বাদ |
| `PytestUnknownMarkWarning` | Marker নিবন্ধিত নয় | `pytest.ini`-এর `markers` |
| ব্যর্থ test পাস করাতে expected বদলানো | Spec বোঝা হয়নি | প্রথমে কারণ নির্ণয়; যুক্তি comment-এ |
| `assert` production-এ কাজ করে না | `python -O` | সাধারণ `if … raise` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Test-এ আসল credential বা production resource নয়।
  - `tmp_path` ব্যবহার করুন — `/var/backups`-এ test চালানো দুর্ঘটনার রেসিপি।
  - Destructive code-এর (মোছা) test অবশ্যই isolated directory-তে।
  - CI-তে test-এর output-এ secret যেন না আসে (L05-07)।
- **Performance:**
  - Unit test মিলিসেকেন্ডে চলা উচিত (এখানে ২২টি ০.৩৯ s-এ)। ধীর test মানে মানুষ চালানো বন্ধ করে দেয়।
  - Integration/slow test marker দিয়ে আলাদা রাখুন।
  - `pytest -x --lf` দিয়ে দ্রুত চক্র।
  - বড় suite-এ `pytest-xdist`-এ সমান্তরাল।
- **Cost:**
  - CI-এর মিনিটে বিল হয়।
  - Integration test-এ cloud resource বানালে তা মুছতে ভুলবেন না — "orphaned test resource" একটি পরিচিত cost leak (Module 29)।
  - Test pyramid: বেশিরভাগ সস্তা unit test রাখুন।

## 14. Hands-on exercise

1. `retention.py`-তে `isocalendar()[:2]`-কে `(d.year, d.isocalendar()[1])`-এ বদলান। কোন test ব্যর্থ হয়? Failure বার্তা পড়ুন, তারপর ফেরত দিন।
2. `--yearly N` যোগ করুন — আগে test লিখুন (ব্যর্থ হবে), তারপর code।
3. `hypothesis` (venv-এ) দিয়ে property test লিখুন: যেকোনো backup তালিকা ও যেকোনো count-এ `keep ∪ delete` = সব মেলা file, `keep ∩ delete` = ∅, newest ∉ delete।
4. Ubuntu-তে `pytest-cov` দিয়ে coverage মাপুন। কোন লাইন test হয়নি? সেগুলোর জন্য test দরকার কি?
5. `--delete`-এ একটি file-এর permission সরিয়ে মোছা ব্যর্থ করান (Linux, non-root) এবং exit ১ হচ্ছে কিনা test করুন (`monkeypatch` দিয়ে `Path.unlink`-কে ব্যর্থ করানোও একটি উপায়)।

## 15. Mini-project — Module 05-এর সব tool-এর জন্য pytest suite

- `~/devops-ai-engineering-work/`-এ একটি project বানান: `pyproject.toml` (dev extra-তে pytest), `src/opstools/`-এ এই module-এর tool, `tests/`-এ pytest।
- Marker: `unit`, `integration`, `network` (local server)।
- `pytest -m unit` এক সেকেন্ডের নিচে।
- `Makefile`/script: `make test`, `make test-all`।

Module 11-এ এটাই CI pipeline-এর ভিত্তি।

## 16. Interview প্রশ্ন

1. Unit ও integration test-এর পার্থক্য কী? Test pyramid কী?
2. pytest fixture কী? Scope কীভাবে কাজ করে?
3. সময়-নির্ভর code কীভাবে test করবেন?
4. Flaky test-এর সাধারণ কারণ ও সমাধান কী?
5. Coverage ১০০% মানে কি bug নেই?
6. Test ব্যর্থ হলে কীভাবে সিদ্ধান্ত নেবেন code ভুল নাকি test?

## 17. Self-assessment প্রশ্ন

1. Checklist analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর ISO week bug-টি কী ছিল?
3. প্রথম run-এর দুটি ব্যর্থতার কারণ কী ছিল?
4. `tests/`-এ `__init__.py` কেন রাখা হয়নি?
5. Production code-এ `assert` কেন ব্যবহার করবেন না?

## 18. সংক্ষিপ্ত সারাংশ

- pytest: সাধারণ `assert`, fixture (`tmp_path`, `capsys`, factory), `parametrize`, marker।
- Edge case-গুলো parametrize-এ তালিকা করুন; safety property আলাদা test-এ।
- সময় inject করুন; destructive code শুধু `tmp_path`-এ।
- Bug-এর জন্য আগে ব্যর্থ test, তারপর fix (regression test)।
- Test ব্যর্থ হলে আগে নির্ণয় করুন — দোষ test-এরও হতে পারে; যুক্তি লিখে রাখুন।

## 19. Completion checklist

- [ ] pytest ও unittest দুভাবে suite চালিয়েছি
- [ ] Exercise ১-এ ISO week bug ফিরিয়ে test ব্যর্থ হতে দেখেছি
- [ ] একটি নতুন feature test-first লিখেছি
- [ ] (Ubuntu) coverage মেপেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- pytest documentation: https://docs.pytest.org/en/stable/
- pytest — How to use fixtures: https://docs.pytest.org/en/stable/how-to/fixtures.html
- pytest — How to parametrize: https://docs.pytest.org/en/stable/how-to/parametrize.html
- pytest — Working with custom markers: https://docs.pytest.org/en/stable/example/markers.html
- Python — `unittest`: https://docs.python.org/3/library/unittest.html
- Python — `datetime.date.isocalendar`: https://docs.python.org/3/library/datetime.html#datetime.date.isocalendar
- restic — Removing snapshots according to a policy: https://restic.readthedocs.io/en/stable/060_forget.html

---

**পরের lesson:** L05-10 — Secret ও configuration: env var, .env, secret manager
