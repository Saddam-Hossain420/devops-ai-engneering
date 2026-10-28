# L05-02 — Ops-এর জন্য Python fundamentals ও type hint

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-01 — Python environment](L05-01-python-environment.md) |
| **Label** | — |
| **Tested** | `inventory.py`: ৮টি unit test পাস (Python 3.14.5, Windows)। `ruff check` পরিষ্কার (default নিয়ম, এবং `F,W,ANN,UP,B,I`)। লেখার সময় **তিনটি আসল সমস্যা** ধরা পড়েছে — Section 9.3-এ বিস্তারিত। `mypy` এই machine-এ নেই, তাই type checker **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Ops script-এ সবচেয়ে বেশি লাগা Python অংশ: `str`, `list`, `dict`, `set`, comprehension, function, exception।
- **dataclass** দিয়ে "এক টুকরো তথ্য"-এর কাঠামো (host, check result) — `frozen`, `field`।
- **Enum / StrEnum** দিয়ে সীমিত মানের তালিকা (env, role)।
- **Type hint:** `list[str]`, `dict[str, int]`, `X | None`, `Iterable`। কেন লিখবেন, কী যাচাই করে আর কী করে না।
- ভুল input-কে "সব বাতিল" না করে **row-ভিত্তিক সমস্যার তালিকা** — ops-এ গুরুত্বপূর্ণ নকশা।
- `ruff` দিয়ে lint।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

ছোট ops script প্রায়ই এভাবে শুরু হয়: `row[3]`, `host["evn"]`, `if env == "prdo"`। ছয় মাস পরে কেউ জানে না `row[3]` কী, typo-র জন্য prod host বাদ পড়ে যায়, আর ভুল IP-ওয়ালা একটি লাইনের কারণে পুরো inventory script crash করে deploy থেমে যায়।

এই lesson-এর যন্ত্রগুলো এগুলো ঠেকায়:

- dataclass — নাম দেওয়া field।
- Enum — typo সাথে সাথে error দেয়।
- Type hint — editor ও checker আগেই ভুল দেখায়।
- Row-ভিত্তিক validation — একটি খারাপ লাইন বাকিগুলোকে আটকায় না।

## 3. সহজ ভাষায় পরিচয়

```python
from dataclasses import dataclass
from enum import StrEnum

class Env(StrEnum):
    DEV = "dev"
    PROD = "prod"

@dataclass(frozen=True)
class Host:
    name: str
    ip: str
    env: Env
    cpu: int

h = Host("web-01", "192.0.2.11", Env("prod"), 2)   # Env("prdo") → ValueError
prod = [x for x in hosts if x.env is Env.PROD]     # list comprehension
by_env: dict[str, list[Host]] = {}                 # type hint
```

| যন্ত্র | কাজ | Ops-এ উদাহরণ |
|---|---|---|
| `dict` | নাম → মান | config, JSON response |
| `set` | অনন্য মান, দ্রুত সদস্যতা | duplicate খোঁজা, allowlist |
| comprehension | filter + রূপান্তর এক লাইনে | prod host-এর নাম |
| `dataclass` | নাম দেওয়া field-এর record | host, check result |
| `Enum` | নির্দিষ্ট কিছু মান | env, severity, status |
| exception | ভুল জানানো ও ধরা | ভুল IP → `ValueError` |
| type hint | কোন ধরনের মান প্রত্যাশিত | `def load(text: str) -> list[Host]` |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### ফর্ম ও ড্রপডাউন

- `dict` = সাদা কাগজে হাতে লেখা তথ্য — যে কেউ যা খুশি লিখতে পারে ("ঠিকানা"-র জায়গায় "ঠিকানাা")।
- `dataclass` = ছাপানো ফর্ম — নির্দিষ্ট ঘর, নির্দিষ্ট নাম।
- `Enum` = ড্রপডাউন মেনু — "prod", "staging", "dev" ছাড়া কিছু বাছাই করা যায় না।
- Type hint = ঘরের পাশে লেখা নির্দেশ "শুধু সংখ্যা"।
- Row-ভিত্তিক validation = ভুল ভরা ফর্মটি ফেরত দেওয়া, কিন্তু বাকি ৯৯টি ফর্ম গ্রহণ করা।

### Analogy কোথায় মেলে না

- ফর্মের "শুধু সংখ্যা" নির্দেশ মানুষ পড়ে মানে। **Python-এর type hint runtime-এ কিছুই আটকায় না:** `Host("a", "b", "prod", "two")` চলে যাবে — `cpu`-তে string থাকবে। Hint যাচাই করে `mypy`/`pyright`-এর মতো আলাদা tool, অথবা আপনার নিজের validation code (`parse_row`)। এই lesson-এ দুটোই কেন লাগে, সেটাই মূল বিষয়।
- ড্রপডাউন UI-তে থাকে। Enum-এ ভুল মান দিলে **exception** হয় — সেটা ধরে অর্থপূর্ণ বার্তা দেওয়া আপনার দায়িত্ব।
- ছাপানো ফর্ম বদলানো যায় না। `frozen=True` dataclass সাধারণ assignment আটকায়, কিন্তু ভেতরের `list` বদলানো যায় — তাই `tags` এখানে `tuple`।

## 5. Real-world engineering scenario — "prdo"

**পরিস্থিতি:** Patch script inventory থেকে prod host বাছাই করে maintenance window-এ restart করে। Inventory spreadsheet থেকে export করা হয়। এক নতুন সদস্য একটি host-এর env লিখলেন `prdo`।

- **পুরোনো script** (`if row["env"] == "prod"`): host টি চুপচাপ বাদ গেল। Patch হলো না, এবং কেউ জানল না। তিন সপ্তাহ পরে vulnerability scan-এ ধরা পড়ল।
- **আরেকটি পুরোনো script** (strict, প্রথম ভুলেই `raise`): পুরো patch run বাতিল হলো, ২০০টি host-এর কোনোটিই patch হলো না।
- **এই lesson-এর পদ্ধতি:** `Env("prdo")` → `ValueError` → `PROBLEM line 57: unknown env/role 'prdo'/'web'`। বাকি host-এ কাজ চলল, exit ১ হলো, আর CI/alert-এ সমস্যাটি সবার চোখে পড়ল।

**শিক্ষা:** অজানা মান চুপচাপ উপেক্ষা করা যাবে না, আবার সব কিছু থামিয়ে দেওয়াও নয়। সমস্যাটা স্পষ্টভাবে জানিয়ে বাকি কাজ চালান, এবং exit code-এ সেটা প্রকাশ করুন। কোনটা উপযুক্ত তা পরিস্থিতির ওপর নির্ভর করে — destructive কাজে "কোনো সমস্যা থাকলে কিছুই নয়" (L04-06-এর নীতি) নিরাপদ হতে পারে।

## 6. Diagram — inventory.py-এর data flow

```text
 hosts.csv ──read_text──► splitlines(keepends) ──► comment/খালি বাদ (line নম্বর রাখা)
                                                        │
                                                 csv.DictReader
                                                        │ প্রতিটি row
                                        ┌───── parse_row(row) ─────┐
                                        │ ip: ipaddress             │
                                        │ env/role: Enum            │
                                        │ cpu/mem: int, > 0         │
                                        └────┬──────────────┬───────┘
                                         ঠিক │              │ ValueError
                                     duplicate? ──হ্যাঁ──► Problem(line, message)
                                             │ না
                                         Host (frozen dataclass)
                                             │
                          select(env, role) ─► group_by(env|role) ─► text / --json
                                                                       exit 0 / 1 / 2
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Comprehension | `[x for x in items if cond]` — filter ও রূপান্তর |
| dataclass | Field ঘোষণা থেকে `__init__`, `__repr__`, `__eq__` স্বয়ংক্রিয় |
| `frozen=True` | Instance বদলানো যায় না; hash করা যায় |
| Enum / StrEnum | নির্দিষ্ট নামের মানের সেট; StrEnum-এর সদস্য নিজেই `str` |
| Type hint / annotation | Parameter ও return-এর প্রত্যাশিত type-এর ঘোষণা |
| Static type checker | Code না চালিয়ে hint যাচাই করে (mypy, pyright) |
| `X \| None` | X অথবা None (Python 3.10+) |
| Duck typing | "Method আছে কিনা" দেখে আচরণ, type-এর নাম দেখে নয় |
| Exception chaining | `raise ... from exc` / `from None` |
| Linter | Style ও সম্ভাব্য bug খোঁজার tool (ruff) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Type hint runtime-এ কী করে

Annotation function-এর `__annotations__`-এ জমা থাকে, কিন্তু Python সেগুলো **যাচাই করে না**। `from __future__ import annotations` দিলে annotation string হিসেবে রাখা হয় — তাই runtime-এ কোনো খরচ নেই, এবং পরে ঘোষিত class-এর নামও ব্যবহার করা যায়।

যাচাই হয় দুই স্তরে:

1. **Static:** mypy/pyright code পড়ে বলে "`cpu`-তে `str` দেওয়া হচ্ছে"। CI-তে চালানো উচিত (Module 11)।
2. **Runtime:** বাইরের data (CSV, JSON, env) কখনো hint মানে না — `parse_row`-এর মতো code দিয়ে **নিজে** যাচাই করতে হয়। বড় project-এ pydantic-এর মতো library এই কাজ করে।

### 8.2 dataclass কী তৈরি করে

`@dataclass` class-এর annotation পড়ে `__init__`, `__repr__`, `__eq__` লেখে। `frozen=True` দিলে `__setattr__` exception দেয় এবং `__hash__` তৈরি হয় — ফলে `set`-এ বা `dict`-এর key হিসেবে রাখা যায়।

Default মান mutable হলে (`list`) অবশ্যই `field(default_factory=list)` দিতে হয়, নইলে সব instance একই list ভাগ করবে — এটি Python-এর বিখ্যাত ফাঁদ, dataclass এখানে error দিয়ে আপনাকে রক্ষা করে।

### 8.3 Enum: `(str, Enum)` বনাম `StrEnum`

দুটোই `== "prod"` সত্য দেয়। কিন্তু `str()` করলে পার্থক্য দেখা যায় — এখানে আসলে চালানো:

```text
(str, Enum):  str(A.X) → 'A.X'    f'{A.X}' → 'A.X'
StrEnum:      str(B.X) → 'x'
```

argparse `choices` দেখাতে `str()` ব্যবহার করে, তাই প্রথম সংস্করণের help-এ এসেছিল `{Env.DEV,Env.STAGING,Env.PROD}` (Section 9.3)। `StrEnum` (Python 3.11+) সমাধান। পুরোনো Python-এ `choices=[e.value for e in Env]` ব্যবহার করুন।

### 8.4 Exception — ধরা ও নতুন বার্তা

`parse_row` নিচু স্তরের `ValueError`/`KeyError` ধরে **অর্থপূর্ণ** বার্তাসহ নতুন `ValueError` তোলে, `from None` দিয়ে। এতে ব্যবহারকারী দেখেন "invalid ip '192.0.2.300'", ভেতরের traceback নয়।

Debug-এর জন্য মূল কারণ রাখতে চাইলে `from exc` দিন। কখনো খালি `except:` বা `except Exception: pass` নয় — তাতে typo-ও (`NameError`) চাপা পড়ে।

## 9. Practical demonstration

Files: [`code/L05-02/inventory.py`](code/L05-02/inventory.py), [`hosts.csv`](code/L05-02/hosts.csv) (হাতে তৈরি নমুনা; IP-গুলো documentation range — RFC 5737), [`test_l05_02.py`](code/L05-02/test_l05_02.py)।

### 9.1 চালানো

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-02
python3 inventory.py hosts.csv; echo "exit=$?"
python3 inventory.py hosts.csv --env prod --group-by role
python3 inventory.py hosts.csv --env nope; echo "exit=$?"
```

**আসল output:**

```text
PROBLEM line 9: duplicate name 'web-01' (first on line 3)
PROBLEM line 10: invalid ip '192.0.2.300'
[all] 6 hosts, 13 cpu, 38 GB
  web-01       192.0.2.11      prod     web     nginx,public
  web-02       192.0.2.12      prod     web     nginx,public
  db-01        192.0.2.21      prod     db      postgres
  web-stg-01   198.51.100.11   staging  web     nginx
  db-stg-01    198.51.100.21   staging  db      postgres
  dev-box      203.0.113.5     dev      worker
exit=1

[db] 1 hosts, 4 cpu, 16 GB
  db-01        192.0.2.21      prod     db      postgres
[web] 2 hosts, 4 cpu, 8 GB
  web-01       192.0.2.11      prod     web     nginx,public
  web-02       192.0.2.12      prod     web     nginx,public

usage: inventory.py [-h] [--env {dev,staging,prod}] ...
inventory.py: error: argument --env: invalid Env value: 'nope'
exit=2
```

- Line নম্বর file-এর আসল লাইন (comment লাইনসহ গোনা) — editor-এ সরাসরি যাওয়া যায়।
- `192.0.2.300` IP-এর মতো দেখায়, কিন্তু octet ২৫৫-এর বেশি। `ipaddress` সেটা ধরে, সাধারণ regex হয়তো ধরত না।
- Duplicate-এর ক্ষেত্রে প্রথমটি রাখা হয়েছে এবং দ্বিতীয়টি সমস্যা হিসেবে জানানো হয়েছে, কোনো চুপচাপ overwrite নেই।
- PROBLEM লাইনগুলো stderr-এ যায় (L04-01-এর নিয়ম), তাই `--json | jq` নিরাপদ।

### 9.2 JSON

```bash
python3 inventory.py hosts.csv --role cache --json
```

```text
{
  "hosts": [],
  "problems": [
    { "line": 9,  "message": "duplicate name 'web-01' (first on line 3)" },
    { "line": 10, "message": "invalid ip '192.0.2.300'" }
  ]
}
```

(আসল output-এ `indent=2`-এর কারণে প্রতিটি field আলাদা লাইনে আছে; এখানে জায়গা বাঁচাতে সংক্ষেপ করা হয়েছে।) একমাত্র cache host-এর IP ভুল, তাই `hosts` খালি। JSON-এ সমস্যাগুলোও থাকে, যাতে পরের tool সিদ্ধান্ত নিতে পারে।

### 9.3 লেখার সময় ধরা পড়া তিনটি সমস্যা

1. **argparse help-এ `{Env.DEV,Env.STAGING,Env.PROD}`** — `(str, Enum)`-এর `str()` আচরণ (Section 8.3)। `StrEnum`-এ বদলে ঠিক হলো।
2. **ruff B905** — `zip(numbered[1:], reader)` strict নয়। কেবল warning মনে হলেও আসল ঝুঁকি ছিল: quoted field একাধিক লাইনে গেলে CSV row ও file-এর লাইন আর মেলে না, ফলে **ভুল line নম্বর** দেখাত। সমাধান: `reader.line_num` (reader কতগুলো লাইন পড়েছে) থেকে আসল লাইন বের করা।
3. **Test-এ ধরা পড়া data corruption:** multi-line field-এর test-এ এল `('xy',) != ('x\ny',)`। `text.splitlines()` লাইনের শেষের newline মুছে দেয়, তাই csv reader field-এর ভেতরের newline পায়নি — data **চুপচাপ বদলে যাচ্ছিল**, কোনো error ছাড়াই। সমাধান: `splitlines(keepends=True)`।

তৃতীয়টি এই lesson-এর সবচেয়ে বড় শিক্ষা: type hint এটা ধরত না (type ঠিক ছিল, মান ভুল) — **edge case-এর test** ধরেছে।

### 9.4 Lint

```bash
ruff check .                                  # default নিয়ম → All checks passed!
ruff check --select F,W,ANN,UP,B,I .          # annotation, pyupgrade, bugbear, import order
```

দুটোই পরিষ্কার। `--select E` দিলে E501 (৮৮ অক্ষরের বেশি লাইন) আসে, কারণ এই repo-তে লাইন ১০০–১১০ অক্ষর পর্যন্ত রাখা হয়েছে। Project-এ `pyproject.toml`-এ `[tool.ruff] line-length = 110` ঠিক করে দেওয়াই নিয়ম (L05-01-এর exercise ৫)।

> **Fedora-তে:** কোনো পার্থক্য নেই — pure Python, শুধু stdlib। `ruff` না থাকলে `pipx install ruff`।

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- Valid row; ৫ ধরনের invalid row (`subTest`)।
- `frozen` dataclass।
- StrEnum-এর `str()`।
- নমুনা file-এর line নম্বর।
- Multi-line quoted field (Section 9.3-এর bug)।
- `select`/`group_by`।
- CLI-এর exit code ও JSON।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `class Env(StrEnum)` | Env-এর সীমিত মান | Typo → সাথে সাথে error; help-এ সুন্দর নাম |
| `@dataclass(frozen=True)` | অপরিবর্তনীয় Host | পরের কোডে ভুলক্রমে বদলানো আটকায় |
| `tags: tuple[str, ...]` | List নয়, tuple | Frozen-এর সাথে মিল রেখে সত্যিকারের অপরিবর্তনীয় |
| `@property is_prod` | Derived মান | Logic এক জায়গায় |
| `ipaddress.ip_address` | IPv4/IPv6 যাচাই | Regex-এর চেয়ে নির্ভুল |
| `raise ValueError(...) from None` | পরিষ্কার বার্তা | ব্যবহারকারী traceback নয়, কারণ দেখেন |
| `_data_lines` generator | Comment বাদ, line নম্বর রাখা | বার্তায় আসল লাইন |
| `reader.line_num` | Multi-line row-এর লাইন | `zip`-এর চেয়ে নির্ভুল |
| `seen: dict[str, int]` | Duplicate খোঁজা | প্রথমটি কোথায় ছিল তাও জানানো |
| `group_by(..., key)` + `defaultdict(list)` | Group | `sorted` — স্থির ক্রম, diff-বান্ধব |
| `type=Env, choices=list(Env)` | argparse-এ Enum | ভুল মানে exit ২ |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `inventory.py hosts.csv` | ৬টি host, line ৯ ও ১০-এ PROBLEM, exit ১ |
| `--env nope` | usage error, exit ২ |
| `--env staging --json` | ২টি host |
| `ruff check --select F,W,ANN,UP,B,I .` | `All checks passed!` |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `TypeError: unhashable type` | Non-frozen dataclass বা list-কে set/dict key | `frozen=True`, tuple |
| `ValueError: mutable default` | dataclass-এ `tags: list = []` | `field(default_factory=list)` |
| সব instance একই list ভাগ করে | সাধারণ function-এ `def f(x=[])` | `None` default, ভেতরে নতুন list |
| Help-এ `Env.PROD` | `(str, Enum)` | `StrEnum` বা `choices=[e.value ...]` |
| Hint থাকলেও ভুল type চলে গেল | Runtime-এ hint যাচাই হয় না | Input validation + mypy |
| `KeyError: 'env'` crash | CSV header-এ নাম ভিন্ন | `row.get`, header যাচাই |
| Typo চাপা পড়েছে | `except Exception: pass` | নির্দিষ্ট exception ধরুন |
| Multi-line CSV field নষ্ট | `splitlines()` / `newline` | `keepends=True`; file খুলতে `newline=""` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - বাইরের input (CSV, JSON, API) সবসময় যাচাই করুন — type hint নিরাপত্তা নয়।
  - `eval()`/`exec()` দিয়ে কখনো data parse করবেন না।
  - Error বার্তায় পুরো row print করার আগে ভাবুন — তাতে secret থাকতে পারে (L05-10)।
- **Performance:**
  - Membership check-এ `set`/`dict` (O(1)), list নয় (O(n)) — ১ লাখ host-এর inventory-তে পার্থক্য সেকেন্ড বনাম মিলিসেকেন্ড।
  - বড় file-এ `read_text` না করে line-by-line পড়ুন (L05-11)।
  - `frozen` dataclass-এর খরচ সামান্য; `slots=True` memory কমায়।
- **Cost:** Inventory-র সঠিকতা সরাসরি cost-এ প্রভাব ফেলে — ভুল env-এর কারণে "dev" হিসেবে চিহ্নিত বড় instance রাতে বন্ধ হয় না (Module 29-এর cost tagging)।

## 14. Hands-on exercise

1. `hosts.csv`-এ `prdo` env-এর একটি লাইন যোগ করে Section 5-এর আচরণ দেখুন।
2. `Host`-এ `slots=True` যোগ করুন; `sys.getsizeof` ও `tracemalloc` দিয়ে ১ লাখ instance-এর memory তুলনা করুন।
3. `--strict` flag যোগ করুন: কোনো PROBLEM থাকলে কোনো host-ই output-এ নয় (destructive কাজের জন্য)। Test লিখুন।
4. CSV header-এ প্রয়োজনীয় column না থাকলে (`ip` নেই) প্রতিটি row-এ আলাদা error না দিয়ে একবার স্পষ্ট error ও exit ২ দিন।
5. Ubuntu-তে একটি venv-এ `mypy` install করে `mypy --strict inventory.py` চালান। কী পেলেন? কোনো warning-এর সমাধান কি code-কে ভালো করে, নাকি শুধু checker-কে খুশি করে?

## 15. Mini-project — Inventory diff

`inventory_diff.py old.csv new.csv`:

- যোগ হওয়া, বাদ যাওয়া ও বদলানো host (কোন field বদলেছে)।
- `Host` frozen হওয়ায় `set` operation দিয়ে সহজে হিসাব করা যায়।
- Prod host বাদ গেলে বিশেষ সতর্কতা ও exit ১।
- `--json` output।

পরে PR review-এ (Module 11) inventory পরিবর্তনের সারাংশ হিসেবে কাজে লাগবে।

## 16. Interview প্রশ্ন

1. Python-এ type hint runtime-এ কী করে? তাহলে কেন লিখবেন?
2. `dataclass` কী সুবিধা দেয়? `frozen=True` কখন?
3. Mutable default argument সমস্যাটি ব্যাখ্যা করুন।
4. একটি config file-এ ভুল মান থাকলে আপনার tool-এর কী করা উচিত — থামা না চালিয়ে যাওয়া?
5. `list` বনাম `set`-এ membership check-এর জটিলতা কী?
6. `except Exception: pass` কেন বিপজ্জনক?

## 17. Self-assessment প্রশ্ন

1. ফর্ম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ তিনটি script-এর আচরণ কী ছিল, এবং কোনটি কখন উপযুক্ত?
3. `splitlines()` bug-টি কী ছিল, এবং type hint কেন সেটা ধরত না?
4. `reader.line_num` কেন `zip`-এর চেয়ে ভালো?
5. `tags` কেন `tuple`?

## 18. সংক্ষিপ্ত সারাংশ

- Record-এর জন্য dataclass (`frozen`), সীমিত মানের জন্য StrEnum।
- Type hint দলিল ও static check — runtime-এ বাইরের input নিজে যাচাই করুন।
- ভুল row: স্পষ্ট বার্তা (line নম্বরসহ), বাকি কাজ চালু, exit code-এ প্রকাশ।
- Edge-case test এমন bug ধরে যা type বা lint ধরে না।
- `ruff` সস্তা ও দ্রুত — প্রতিটি tool-এ চালান।

## 19. Completion checklist

- [ ] `inventory.py` চালিয়ে PROBLEM ও exit code ব্যাখ্যা করতে পারি
- [ ] Type hint ও runtime validation-এর পার্থক্য বলতে পারি
- [ ] `(str, Enum)` বনাম `StrEnum` পার্থক্য দেখেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `dataclasses`: https://docs.python.org/3/library/dataclasses.html
- Python — `enum` (StrEnum): https://docs.python.org/3/library/enum.html
- Python — `typing`: https://docs.python.org/3/library/typing.html
- Python — `csv`: https://docs.python.org/3/library/csv.html
- Python — `ipaddress`: https://docs.python.org/3/library/ipaddress.html
- mypy documentation: https://mypy.readthedocs.io/
- Ruff — rules: https://docs.astral.sh/ruff/rules/

---

**পরের lesson:** L05-03 — File, directory ও pathlib
