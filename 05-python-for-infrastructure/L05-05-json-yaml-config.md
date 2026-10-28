# L05-05 — JSON, YAML ও configuration processing

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-02 — Python fundamentals](L05-02-python-fundamentals-type-hints.md) |
| **Label** | — |
| **Tested** | `config_loader.py`: ১২টি test-এর ১১টি পাস, ১টি skip (Python 3.14.5, Windows)। আসলে চালানো হয়েছে: TOML, JSON, duplicate-key JSON, env var ও `--set` সহ সব demo। **PyYAML এই machine-এ নেই** (install করা হয়নি), তাই YAML-এর "Norway problem" test **skip হয়েছে**। Section 8.3-এর YAML আচরণ YAML 1.1 spec ও PyYAML-এর documented আচরণ থেকে লেখা, এখানে চালানো নয়। |

---

## 1. এই lesson-এ যা শিখবেন

- JSON, TOML, YAML: কোনটা কখন, কার কী দুর্বলতা।
- `json.loads`-এর লুকানো আচরণ: **duplicate key নীরবে মুছে যায়**।
- YAML 1.1-এর ফাঁদ: `NO` → `false`, `010` → ৮, `1:30` → ৯০; এবং `yaml.load` বনাম `yaml.safe_load`।
- **স্তরভিত্তিক config:** default < file < env var < CLI, এবং **কোন মান কোথা থেকে এল** তা দেখানো।
- Schema validation: type, সীমা, বাধ্যতামূলক key, অজানা key (typo)।
- Secret-এর মান output-এ mask করা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Production incident-এর একটি বড় অংশ code নয়, **config পরিবর্তন** থেকে আসে। সাধারণ রূপগুলো:

- Typo-ওয়ালা key (`featurs`) — tool চুপচাপ উপেক্ষা করে, default চলতে থাকে, আর কেউ বোঝে না যে নতুন setting কাজ করছে না।
- `"timeout": "5"` (string) — code-এ `timeout * 2` = `"55"`।
- একই key দুবার — শেষেরটা জেতে, review-এ চোখে পড়ে না।
- "Port ৯০০০ কোথা থেকে এল? File-এ তো ৮০০০!" — একটি পুরোনো env var।

এই lesson-এর loader এগুলোকে **load-এর সময়ই** ধরে, যাতে service শুরু না হয়ে স্পষ্ট error দেয় (fail fast)।

## 3. সহজ ভাষায় পরিচয়

| Format | ভালো | দুর্বলতা | ব্যবহার |
|---|---|---|---|
| JSON | সর্বত্র, কঠোর, stdlib | Comment নেই, trailing comma নিষেধ | API, machine-generated config |
| TOML | Comment, স্পষ্ট type, stdlib (`tomllib`, শুধু পড়া) | গভীর nesting অসুবিধাজনক | Python project, app config |
| YAML | পড়তে সহজ, comment, anchor | Implicit type-এর ফাঁদ, indentation, stdlib-এ নেই | Kubernetes, Ansible, CI |

```python
import json, tomllib
cfg = json.loads(text)                        # str → dict
text = json.dumps(cfg, indent=2)              # dict → str
with open("app.toml", "rb") as f:             # tomllib-এ binary mode
    cfg = tomllib.load(f)
import yaml                                   # PyYAML (pip, venv-এ)
cfg = yaml.safe_load(text)                    # কখনো yaml.load(text) নয়
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রেস্তোরাঁর অর্ডার

- **Default** = মেনুর সাধারণ রেসিপি।
- **Config file** = এই শাখার নিয়ম ("এখানে ঝাল কম")।
- **Env var** = আজকের দিনের নির্দেশ ("আজ লবণ কম, সরবরাহে সমস্যা")।
- **CLI `--set`** = এই একটি অর্ডারে খদ্দেরের অনুরোধ।

পরের স্তর আগেরটাকে ছাপিয়ে যায়। `--explain` হলো প্লেটের পাশে কাগজ: "ঝাল কম — শাখার নিয়ম থেকে; লবণ কম — আজকের নির্দেশ থেকে"।

### Analogy কোথায় মেলে না

- রাঁধুনি অদ্ভুত অনুরোধে প্রশ্ন করেন ("ঝাল -৫?")। **Parser প্রশ্ন করে না** — JSON-এ duplicate key বা YAML-এ `NO` দিলে সে নিজে একটা সিদ্ধান্ত নিয়ে চুপচাপ এগিয়ে যায়। প্রশ্ন করা (validation) আপনার code-এর কাজ।
- অর্ডার কাগজে থাকে, সবাই দেখে। **Env var অদৃশ্য** — `ps`, systemd unit, container spec, CI secret, `.bashrc` যেকোনো জায়গা থেকে আসতে পারে। তাই provenance (উৎস) দেখানো জরুরি।
- রেসিপি একবার পড়লেই হয়। Config অনেক সময় **runtime-এ বদলায়** (reload, SIGHUP)। নতুন config-ও একই validation-এর মধ্য দিয়ে যাওয়া উচিত, এবং ভুল হলে পুরোনোটা রাখা উচিত (nginx `-t`-এর মতো — Module 06)।

## 5. Real-world engineering scenario — "Norway-তে কোনো user নেই"

**পরিস্থিতি:** একটি service-এর YAML config-এ সমর্থিত দেশের তালিকা:

```yaml
countries: [GB, IE, NO, SE]
```

Deploy-এর পরে নরওয়ের user-রা "country not supported" দেখলেন। কারণ: YAML 1.1-এ উদ্ধৃতিহীন `NO` হলো boolean `false`। তালিকা হয়ে গেল `["GB", "IE", False, "SE"]`, আর `"NO" in countries` হলো মিথ্যা।

একই পরিবারের অন্য ঘটনা:

- `umask: 010` → অষ্টাল সংখ্যা **৮** (দশমিক ১০ নয়)।
- `window: 1:30` → **৯০** (base-60 সংখ্যা)।
- `version: 1.10` → float **১.১** — "১.১০" আর "১.১" একই হয়ে গেল।

**সমাধানের স্তর:**

1. String-এ সবসময় quote: `"NO"`, `"1.10"`।
2. Schema validation — `countries`-এর প্রতিটি উপাদান `str` হতে হবে।
3. যেখানে সম্ভব কঠোর format (TOML/JSON), অথবা YAML 1.2-ভিত্তিক parser।
4. CI-তে config lint (`yamllint` — Module 11)।

**শিক্ষা:** Parser "সফল" হওয়া মানে config সঠিক নয়। Type ও মানের validation আলাদা ধাপ।

## 6. Diagram — স্তর ও যাচাই

```text
  DEFAULTS (code-এ)          server.port=8080  host=127.0.0.1  workers=2
        │  ছাপিয়ে যায়
  app.toml / app.json        server.port=8000  host=0.0.0.0                 ← parse: duplicate key? syntax line:col?
        │
  env: APP_SERVER__PORT      server.port=9000                               ← coerce: "9000" → int (ভুল হলে exit 2)
        │
  CLI: --set server.port=…   server.port=9100
        ▼
  effective config  +  source map {server.port: "cli", host: "app.toml", workers: "default"}
        │
  validate(SCHEMA): unknown key? type? range? choices? required?   ── ভুল → exit 1 (service শুরু হয় না)
        │
  masked() → output / log   (password → "***")
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Serialization | Object → text (dump); উল্টোটা deserialization (load) |
| Schema | Config-এর কাঠামো ও নিয়মের ঘোষণা |
| Layered / hierarchical config | একাধিক উৎস, নির্দিষ্ট অগ্রাধিকারে |
| Provenance | মানটি কোন উৎস থেকে এসেছে |
| Coercion | String থেকে প্রত্যাশিত type-এ রূপান্তর |
| Fail fast | ভুল config-এ শুরুতেই থামা |
| `object_pairs_hook` | JSON object তৈরির আগে key-value জোড়া দেখার hook |
| Implicit typing (YAML) | Quote ছাড়া মানের type parser অনুমান করে |
| `safe_load` | শুধু সাধারণ type বানায়, কোনো Python object নয় |
| 12-factor config | Config environment-এ, code-এ নয় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 JSON-এর duplicate key

JSON spec (RFC 8259) বলে, object-এর key "SHOULD be unique" — অর্থাৎ বাধ্যতামূলক নয়। Python-এর `json.loads` শেষ মানটি রাখে, কোনো সতর্কতা ছাড়াই। `object_pairs_hook` সব জোড়া list হিসেবে দেয়, তাই duplicate ধরা যায় (Section 9.3)।

### 8.2 TOML

- Type স্পষ্ট: string সবসময় quote-এ, তারিখ নিজস্ব type, integer ও float আলাদা।
- Python ৩.১১+-এ `tomllib` stdlib-এ আছে, শুধু **পড়ার** জন্য। লিখতে third-party (`tomli-w`) লাগে।
- `tomllib.load` binary file নেয় (`"rb"`), কারণ TOML সবসময় UTF-8।

### 8.3 YAML-এর দুটি বিপদ

1. **Implicit typing (YAML 1.1):** উদ্ধৃতিহীন `yes/no/on/off/y/n` হয় bool, `0`-দিয়ে শুরু সংখ্যা হয় অষ্টাল, `:`-ওয়ালা সংখ্যা হয় base-60। PyYAML YAML 1.1 অনুসরণ করে। YAML 1.2 (২০০৯) এগুলোর বেশিরভাগ বাদ দিয়েছে, কিন্তু অনেক tool এখনো 1.1।
2. **Code execution:** পুরোনো `yaml.load(text)` (Loader ছাড়া) `!!python/object/apply:os.system` জাতীয় tag থেকে Python object বানাতে পারত — অর্থাৎ config file দিয়ে code চালানো। সবসময় `yaml.safe_load`।

> এই অংশ PyYAML-এর documented আচরণ থেকে লেখা; এই machine-এ PyYAML নেই বলে চালানো হয়নি। নিজের venv-এ `pip install pyyaml` করে `python3 -m unittest -v` চালালে Norway test চলবে।

### 8.4 Env var-এর নামকরণ

`APP_SERVER__PORT` → `server.port`। Prefix (`APP_`) অন্য program-এর env থেকে আলাদা রাখে। Double underscore section বোঝায়, কারণ single underscore key-র নামেই থাকতে পারে (`timeout_s`)।

Env var সবসময় string, তাই schema দেখে coerce করতে হয়। Bool-এর জন্য শুধু স্পষ্ট শব্দ গ্রহণ করা হয়: `"maybe"` হলে error, নীরবে `False` নয়।

### 8.5 `bool` হলো `int`

Python-এ `isinstance(True, int)` সত্য। তাই `port: true` সাধারণ `isinstance` যাচাই পার হয়ে যায়। `validate` আলাদাভাবে এটা ধরে। উল্টো দিকে, `timeout_s: 3` (int) float-এর জায়গায় গ্রহণযোগ্য।

> **Fedora-তে:** কোনো পার্থক্য নেই। PyYAML distribution package হিসেবে `python3-pyyaml` (Fedora) / `python3-yaml` (Ubuntu) নামে আছে, তবে project-এর জন্য venv-এ install করুন (L05-01)।

## 9. Practical demonstration

Files:

- [`code/L05-05/config_loader.py`](code/L05-05/config_loader.py), [`test_l05_05.py`](code/L05-05/test_l05_05.py)।
- নমুনা (হাতে তৈরি): [`app.toml`](code/L05-05/app.toml), [`app.json`](code/L05-05/app.json) (ইচ্ছাকৃত ভুলসহ), [`dup.json`](code/L05-05/dup.json), [`norway.yaml`](code/L05-05/norway.yaml)।

### 9.1 Provenance

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-05
python3 config_loader.py --config app.toml --explain; echo "exit=$?"
```

**আসল output:**

```text
server.host        = "0.0.0.0"                  <- app.toml
server.port        = 8000                       <- app.toml
server.workers     = 2                          <- default
log.level          = "info"                     <- app.toml
log.json           = true                       <- app.toml
db.url             = "sqlite:///var/lib/taskflow/taskflow.db" <- app.toml
db.password        = null                       <- default
db.timeout_s       = 2.5                        <- app.toml
features.signup    = true                       <- default
exit=0
```

### 9.2 স্তর, ভুল ও mask

```bash
APP_SERVER__PORT=9000 APP_DB__PASSWORD=hunter2 \
  python3 config_loader.py --config app.json --set log.level=debug; echo "exit=$?"
```

**আসল output (সংক্ষেপিত):**

```text
INVALID featurs.signup: unknown key (typo?)
INVALID db.timeout_s: expected float, got str '5'
{
  "server": { "host": "127.0.0.1", "port": 9000, "workers": 4 },
  "log": { "level": "debug", "json": false },
  "db": { "url": "sqlite:///taskflow.db", "password": "***", "timeout_s": "5" },
  ...
}
exit=1
```

- Port: file-এ ৮০০০, env-এ ৯০০০ → **৯০০০**।
- `app.json`-এর `"level": "warn"` (ভুল মান) CLI-এর `debug` দিয়ে ঢাকা পড়েছে, তাই এই run-এ সেই error নেই। CLI ছাড়া চালালে আসে `log.level: 'warn' not in [...]` (test-এ যাচাই করা)।
- `"5"` (quote-এ) — JSON-এ এটা string। Loader নীরবে রূপান্তর না করে error দিয়েছে।
- Password-এর জায়গায় `***`, অথচ আসল মান code-এর কাছে আছে।

### 9.3 Duplicate key, YAML, ভুল env

```bash
python3 config_loader.py --config dup.json; echo "exit=$?"
python3 -c "import json; print(json.loads(open('dup.json').read()))"
python3 config_loader.py --config norway.yaml; echo "exit=$?"
APP_SERVER__PORT=abc python3 config_loader.py; echo "exit=$?"
python3 config_loader.py --set log.json=maybe; echo "exit=$?"
python3 config_loader.py --set server.port=70000 --set log.level=WARN >/dev/null; echo "exit=$?"
```

**আসল output:**

```text
error: dup.json: duplicate key 'server'
exit=2
{'server': {'port': 9000}, 'log': {'level': 'info'}}          ← সাধারণ json.loads: প্রথম server নীরবে হারাল
error: norway.yaml: YAML needs PyYAML (pip install pyyaml in a venv); or use JSON/TOML
exit=2
error: env APP_SERVER__PORT: expected int, got 'abc'
exit=2
error: --set log.json: expected bool, got 'maybe'
exit=2
INVALID server.port: 70000 > max 65535
INVALID log.level: 'WARN' not in ['debug', 'info', 'warning', 'error']
exit=1
```

**লেখার সময় উন্নতি:** প্রথম সংস্করণের বার্তা ছিল `error: not a int: 'abc'` — কোন env var, বোঝা যেত না। এখন উৎসের নাম থাকে। রাত ৩টার debugging-এ এই পার্থক্য অনেক বড়।

### 9.4 Python version-ভেদে ভিন্ন error

Trailing comma-ওয়ালা JSON (`{"a": 1,}`)-এর জন্য Python ৩.১৪ বলেছে `bad.json:2:9: Illegal trailing comma before end of object` — comma-র সঠিক অবস্থানে। পুরোনো Python পরের লাইনে "Expecting property name…" বলে। Test তাই দুটোই মেনে নেয় (`:[23]:`)।

**শিক্ষা:** Error বার্তার হুবহু লেখা নিয়ে test লিখবেন না — version বদলালে test ভাঙবে।

### 9.5 Lint-এর একটি ফাঁদ

`ruff check --select I` প্রথমে `import tomllib`-কে third-party ভেবে import ক্রম ভুল বলল — ruff-এর default target Python version পুরোনো, যেখানে `tomllib` ছিল না। `--target-version py311` দিলে পরিষ্কার। Project-এ `pyproject.toml`-এর `requires-python` থেকে ruff এটা নিজেই বোঝে (L05-01)।

### 9.6 Test

```bash
python3 -m unittest -v
```

১২টি test:

- অগ্রাধিকার ও provenance; default-এর dict বদলায় না (deep copy)।
- Coercion।
- Duplicate key।
- Syntax error-এর অবস্থান (JSON line:col, TOML line), top-level list, অজানা extension।
- PyYAML না থাকলে স্পষ্ট error।
- **Norway** *(PyYAML লাগে — এখানে skip)*।
- নমুনা JSON-এর ভুল।
- bool ≠ int।
- Required ও range।
- Mask; CLI-এর exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `copy.deepcopy(DEFAULTS)` | Default-এর copy | Nested dict বদলালে module-এর DEFAULTS নষ্ট হতো |
| `object_pairs_hook=_no_duplicates` | Duplicate key → error | `json.loads` নীরবে মুছে দেয় |
| `exc.lineno`, `exc.colno` | Error-এর অবস্থান | Editor-এ সরাসরি যাওয়া |
| `yaml.safe_load` | নিরাপদ YAML | Code execution নয় |
| `flatten` / `set_path` | Nested ↔ `a.b.c` | Env/CLI-এর key ও provenance |
| `source` dict | কোন মান কোথা থেকে | `--explain` |
| `coerce(..., where)` | String → type, উৎসের নামসহ error | কোন env var ভুল, স্পষ্ট |
| Unknown key = error | Typo ধরা | `featurs` চুপচাপ উপেক্ষিত হয় না |
| `masked()` | Secret → `***` | Log-এ secret ফাঁস হয় না |
| Exit ২ বনাম ১ | Parse error বনাম validation | Automation আলাদাভাবে প্রতিক্রিয়া দেয় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `--config app.toml` | exit ০ |
| `--config app.json` | `featurs`, `timeout_s`, `log.level` — INVALID, exit ১ |
| `--config dup.json` | `duplicate key 'server'`, exit ২ |
| `APP_SERVER__PORT=abc` | `env APP_SERVER__PORT: expected int`, exit ২ |
| `python3 -m unittest -v` | `Ran 12 tests`, `OK` (PyYAML না থাকলে skip ১) |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Setting কাজ করছে না, কোনো error নেই | Key-তে typo | Unknown key = error |
| `"5" * 2 == "55"` | Quote-এ সংখ্যা | Schema type check |
| দেশ/মান `False` হয়ে গেছে | YAML `NO`/`off` | Quote দিন; validation |
| `0755` → ৪৯৩ | YAML/Python-এ অষ্টাল | String হিসেবে রেখে `int(x, 8)` |
| Port কোথা থেকে এল জানি না | পুরোনো env var | `--explain`; `env \| grep APP_` |
| `TypeError: File must be opened in binary mode` | `tomllib.load` | `open(..., "rb")` |
| Log-এ password | Config dump | `masked()`; secret আলাদা (L05-10) |
| `ModuleNotFoundError: yaml` | PyYAML নেই | venv-এ install, বা TOML/JSON |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `yaml.load` কখনো নয় — শুধু `safe_load`।
  - Config file-এ secret নয়: env, `*_FILE` বা secret manager (L05-10)।
  - Effective config log করলে mask করুন।
  - Untrusted config-এ সীমা দিন: file-এর আকার; YAML-এর "billion laughs" (anchor বিস্ফোরণ)।
- **Performance:** Config সাধারণত শুরুতে একবার পড়া হয় — খরচ নগণ্য। বড় JSON (শত MB) হলে streaming parser (`ijson`) বা JSON Lines।
- **Cost:** ভুল config-এর খরচ বাস্তব — `replicas: 100` টাইপো, `instance_type` ভুল। Range validation (যেমন `workers` ≤ ৬৪) একটি সস্তা guardrail (Module 29)।

## 14. Hands-on exercise

1. নিজের venv-এ `pip install pyyaml` করে test চালান। Norway test পাস করল? `norway.yaml`-এর `umask` ও `window`-এর মান কী এল?
2. `SCHEMA`-তে `features.countries: list[str]` সমর্থন যোগ করুন, যাতে Section 5-এর `False` ধরা পড়ে।
3. `--explain`-এ যে মান default-এর সমান কিন্তু file-এও লেখা আছে, তা "redundant" হিসেবে চিহ্নিত করুন।
4. `APP_CONFIG` env var দিয়ে config file-এর path দেওয়ার সমর্থন যোগ করুন (`--config`-এর চেয়ে কম অগ্রাধিকার)।
5. Config reload: SIGHUP পেলে নতুন config পড়ে validate করুন; ভুল হলে পুরোনোটা রাখুন ও log করুন।

## 15. Mini-project — Config diff ও policy check

`config_policy.py base.toml prod.toml`:

- দুটি effective config-এর পার্থক্য।
- Policy নিয়ম: prod-এ `log.level` ≠ `debug`, `server.host` ≠ `127.0.0.1`, `db.password` অবশ্যই env থেকে (file-এ নয় — provenance দেখে)।
- লঙ্ঘন হলে exit ১।

Module 11-এর CI pipeline-এ PR-এর config পরিবর্তন যাচাই করবে।

## 16. Interview প্রশ্ন

1. JSON, YAML ও TOML-এর পার্থক্য কী? কোনটা কখন?
2. YAML-এর "Norway problem" কী? কীভাবে এড়াবেন?
3. `yaml.load` কেন বিপজ্জনক?
4. Configuration-এর অগ্রাধিকার কেমন হওয়া উচিত, এবং কেন env var CLI-এর নিচে?
5. Config-এ একটি typo-ওয়ালা key থাকলে কী হওয়া উচিত?
6. Container-এ config ও secret কীভাবে দেবেন?

## 17. Self-assessment প্রশ্ন

1. রেস্তোরাঁ analogy কোথায় মেলে না (তিনটি বিষয়)?
2. `json.loads` duplicate key-তে কী করে, এবং কীভাবে ধরবেন?
3. Section 9.2-এ port ৯০০০ কেন হলো?
4. Error বার্তার হুবহু লেখা নিয়ে test লেখা কেন খারাপ?
5. `isinstance(True, int)` কেন সমস্যা?

## 18. সংক্ষিপ্ত সারাংশ

- Default < file < env < CLI; প্রতিটি মানের উৎস দেখাতে পারা উচিত।
- Parse সফল মানে config সঠিক নয় — schema দিয়ে type, সীমা, অজানা key যাচাই।
- JSON-এ duplicate key ধরুন; YAML-এ `safe_load` ও quote।
- ভুল config-এ service শুরু হবে না (fail fast), এবং বার্তায় উৎসের নাম থাকবে।
- Secret mask করুন; config file-এ রাখবেন না।

## 19. Completion checklist

- [ ] `--explain` দিয়ে প্রতিটি মানের উৎস দেখেছি
- [ ] Duplicate key ও typo key ধরা পড়তে দেখেছি
- [ ] (PyYAML-সহ venv-এ) Norway problem নিজে দেখেছি
- [ ] `python3 -m unittest -v`-এ সব test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `json`: https://docs.python.org/3/library/json.html
- Python — `tomllib`: https://docs.python.org/3/library/tomllib.html
- RFC 8259 — The JSON Data Interchange Format: https://www.rfc-editor.org/rfc/rfc8259
- TOML specification: https://toml.io/en/v1.0.0
- YAML 1.2.2 specification: https://yaml.org/spec/1.2.2/
- PyYAML documentation: https://pyyaml.org/wiki/PyYAMLDocumentation
- The Twelve-Factor App — Config: https://12factor.net/config

---

**পরের lesson:** L05-06 — HTTP client ও API: timeout, retry, error handling
