# L05-01 — Python environment: version, venv, pip, pyproject

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L00-07 — Lab environment](../00-orientation/L00-07-lab-environment-setup.md), [L04-08 — Bash বনাম Python](../04-bash-and-shell-automation/L04-08-bash-or-python.md) |
| **Label** | — |
| **Tested** | `envcheck.py` ও `pin_check.py`: ৭টি test পাস, যার একটি test **একটি আসল venv তৈরি করে** তার ভেতর থেকে চালায় (Python 3.14.5, Windows)। আসলে চালানো হয়েছে: system Python ও নতুন venv-এ `envcheck`, `python -m venv`-এর সময়, venv-এর `pip list`, দুটি নমুনায় `pin_check`। `pin_check`-এর একটি bug ধরা পড়েছে (Section 9.3)। **কোনো package internet থেকে install করা হয়নি।** Ubuntu-র PEP 668 আচরণ ও `python3-venv` package **Ubuntu-তে চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- একটি machine-এ একাধিক Python: system Python, distribution package, নিজের install করা।
- **Virtual environment (venv):** কেন, কীভাবে কাজ করে (`sys.prefix` বনাম `sys.base_prefix`)।
- **PEP 668** ("externally managed"): Ubuntu-তে `pip install` কেন error দেয়, সঠিক বিকল্প কী।
- `pip`, `requirements.txt`, **pinning ও hash**; application বনাম library-র নিয়ম।
- `pyproject.toml`: আধুনিক project-এর কাঠামো।
- পুনরুৎপাদনযোগ্য environment: lock file, `pip-compile`/`uv`।
- নিজের environment পরীক্ষা ও dependency যাচাইয়ের tool।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

"আমার machine-এ চলে" — Python-এ এর প্রধান কারণ environment:

- Server-এ Python ৩.৮, আপনার laptop-এ ৩.১২ — `match` statement বা নতুন type hint syntax-এ error।
- `sudo pip install` system Python-এর package বদলে দিয়েছে — OS-এর নিজের tool (Ubuntu-র `apt`-এর অংশ, cloud-init) ভেঙে গেছে।
- `requirements.txt`-এ শুধু `requests` লেখা। গত মাসের deploy-এ ২.৩১ এসেছিল, আজ এসেছে নতুন major version, এবং আচরণ বদলেছে।
- CI-তে সবুজ, production-এ crash — কারণ ভিন্ন dependency version।

এই lesson-এর পরে প্রতিটি Python tool (এই module, পরে Docker image — Module 09, CI — Module 11) একটি নির্দিষ্ট, পুনরুৎপাদনযোগ্য environment-এ চলবে।

## 3. সহজ ভাষায় পরিচয়

| স্তর | কী | কার |
|---|---|---|
| System Python (`/usr/bin/python3`) | OS-এর অংশ, OS-এর tool ব্যবহার করে | Distribution — **ছোঁবেন না** |
| venv | একটি directory-তে নিজস্ব `site-packages` | প্রতিটি project-এর |
| pipx | CLI tool-এর জন্য আলাদা venv স্বয়ংক্রিয়ভাবে | User-এর tool (`ruff`, `ansible`) |
| Container | পুরো OS-স্তরের আলাদাকরণ | Production (Module 09) |

**venv-এর মূল command:**

```bash
python3 -m venv .venv               # তৈরি
. .venv/bin/activate                # চালু (PATH-এর শুরুতে .venv/bin)
python -m pip install -r requirements.txt
deactivate
.venv/bin/python script.py          # activate না করেও — script ও systemd-এ এটাই নিরাপদ
```

**Dependency লেখার রূপ:**

| রূপ | উদাহরণ | কোথায় |
|---|---|---|
| Unpinned | `requests` | কোথাও নয় (production-এ বিপজ্জনক) |
| Range | `requests>=2.31,<3` | **Library**-র `pyproject.toml` (অন্যের সাথে মানিয়ে নিতে) |
| Pinned | `requests==2.32.3` | **Application**-এর lock file |
| Pinned + hash | `… --hash=sha256:…` | Supply-chain-সচেতন deploy (`pip install --require-hashes`) |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রান্নাঘর ও রেসিপি

- **System Python** = হোটেলের কেন্দ্রীয় রান্নাঘর — সবার খাবার এখান থেকে; এখানে নিজের মশলা মিশিয়ে দিলে অন্য সবার খাবার বদলে যায়।
- **venv** = নিজের ছোট রান্নাঘর — নিজের মশলা, নিজের পাত্র; ভুল হলে পুরো ঘর মুছে নতুন বানানো যায় (`rm -rf .venv`)।
- **Pinned requirements** = নির্দিষ্ট ব্র্যান্ড ও ওজনসহ রেসিপি ("লবণ: X ব্র্যান্ড, ৫ গ্রাম") — সব জায়গায় একই স্বাদ।
- **Unpinned** = "লবণ, পরিমাণমতো" — প্রতিবার ভিন্ন।

### Analogy কোথায় মেলে না

- নিজের রান্নাঘর পুরোপুরি আলাদা। **venv পুরোপুরি আলাদা নয়:** একই Python interpreter (`sys.base_prefix`) ব্যবহার করে। System Python আপগ্রেড হলে (যেমন Ubuntu release upgrade-এ ৩.১০ থেকে ৩.১২) পুরোনো venv ভেঙে যায় — তখন venv আবার তৈরি করতে হয়। C library (`libssl`, `libpq`)-ও system থেকে আসে।
- রেসিপিতে ব্র্যান্ড লিখলে ঠিক সেটাই পাওয়া যায়। `requests==2.32.3` লিখলেও **requests-এর নিজের dependency** (urllib3, idna…) আলাদাভাবে বদলাতে পারে, যদি না সেগুলোও pin করা থাকে। পূর্ণ lock file (transitive সহ) লাগে।
- একই নামের ব্র্যান্ড একই জিনিস। Package index-এ একই version নম্বরের file **বদলে দেওয়া** যায় না, কিন্তু typo-squatting (`reqeusts`) বা compromised account থেকে ক্ষতিকর নতুন version আসতে পারে। Hash যাচাই ও বিশ্বস্ত mirror প্রতিরোধ দেয় (Module 19)।

## 5. Real-world engineering scenario — "Ubuntu upgrade-এর পরে monitoring script বন্ধ"

**পরিস্থিতি:** একটি server-এ monitoring script বছরের পর বছর চলছিল। কেউ একবার `sudo pip install requests psutil` করেছিলেন। Ubuntu ২২.০৪ থেকে ২৪.০৪-এ upgrade-এর পরে তিনটি ঘটনা ঘটল:

1. Python ৩.১০ থেকে ৩.১২ হলো — আগের `pip`-এ install করা package নতুন Python-এর `site-packages`-এ নেই।
2. `sudo pip install` আবার চালাতে গেলে এল `error: externally-managed-environment` (PEP 668)।
3. কেউ `--break-system-packages` দিয়ে জোর করলেন — এবং একটি system package-এর version বদলে `apt`-এর একটি helper ভেঙে গেল।

**সঠিক পদ্ধতি:**

```bash
sudo apt install python3-venv                         # Ubuntu-তে venv module আলাদা package
sudo python3 -m venv /opt/monitoring/.venv
sudo /opt/monitoring/.venv/bin/pip install -r /opt/monitoring/requirements.lock
# systemd unit-এ: ExecStart=/opt/monitoring/.venv/bin/python /opt/monitoring/check.py
```

Upgrade-এর পরে শুধু venv আবার তৈরি করুন (`rm -rf .venv` → একই lock থেকে install), system-এ কোনো প্রভাব পড়ে না।

**শিক্ষা:** System Python OS-এর জন্য, আপনার tool-এর জন্য নয়। প্রতিটি tool-এর নিজের venv ও lock file থাকবে, এবং পুনর্নির্মাণ হবে এক command-এ।

## 6. Diagram — venv-এর ভেতরে কী

```text
 /usr/bin/python3.12  (base interpreter, OS-এর)          sys.base_prefix = /usr
        ▲ symlink / copy
 project/.venv/
 ├── pyvenv.cfg          home = /usr/bin ; version = 3.12.3      ← base কোথায়
 ├── bin/python ─────────┘                                         sys.prefix = project/.venv
 ├── bin/pip, bin/activate
 └── lib/python3.12/site-packages/   ← শুধু এই project-এর package
          requests/, urllib3/, ...

 python -m pip install X   → .venv-এর site-packages-এ (system-এ নয়)
 /usr/lib/python3/dist-packages   ← apt-এর package (OS-এর) — venv default-এ দেখে না
 /usr/lib/python3.12/EXTERNALLY-MANAGED  ← PEP 668 marker (Ubuntu ২৩.০৪+)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Interpreter | Python program যা code চালায় |
| venv | Project-এর আলাদা package environment |
| `sys.prefix` / `sys.base_prefix` | বর্তমান environment / মূল interpreter-এর অবস্থান |
| site-packages | Install করা package-এর directory |
| pip | Package installer |
| PEP 668 | "Externally managed" — distribution-এর Python-এ pip দিয়ে system-এ install নিষেধ |
| pipx | CLI tool-গুলো আলাদা venv-এ install |
| `requirements.txt` | Dependency-র তালিকা |
| Lock file | সব (transitive সহ) dependency-র নির্দিষ্ট version, প্রায়ই hash সহ |
| Transitive dependency | Dependency-র dependency |
| `pyproject.toml` | Project-এর metadata, dependency ও tool-এর configuration (PEP 517/518/621) |
| Wheel / sdist | Built package / source distribution |
| `requires-python` | Project কোন Python version সমর্থন করে |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 venv কীভাবে কাজ করে

`python -m venv .venv` একটি directory বানায়, যেখানে `pyvenv.cfg` থাকে আর base interpreter-এর একটি link বা copy। এই interpreter চালু হলে `pyvenv.cfg` দেখে বোঝে যে সে venv-এর ভেতরে আছে: `sys.prefix` = `.venv`, এবং `site-packages` শুধু venv-এর।

`activate` শুধু `PATH`-এর শুরুতে `.venv/bin` যোগ করে ও prompt বদলায় — এর বেশি কিছু নয়। তাই script বা systemd-এ সরাসরি `.venv/bin/python` ব্যবহার করুন; `activate`-এর দরকার নেই।

### 8.2 PEP 668

Ubuntu (২৩.০৪ থেকে) ও Debian system Python-এর stdlib directory-তে `EXTERNALLY-MANAGED` file রাখে। pip সেই file দেখে system-এ install প্রত্যাখ্যান করে, এবং venv বা pipx ব্যবহারের পরামর্শ দেয়। `--break-system-packages` flag-টির নামই ঝুঁকিটা বলে দেয় (Section 5)। venv-এর ভেতরে এই নিয়ম প্রযোজ্য নয়, কারণ venv-এর stdlib path-এ marker নেই।

> **Fedora-তে:** `python3`-এর সাথে `venv` module থাকে (আলাদা package লাগে না)। PEP 668 marker নিয়ে Fedora-র নীতি Ubuntu থেকে ভিন্ন হতে পারে — নিজের system-এ `python3 envcheck.py`-এর `externally_managed` লাইন দেখে নিশ্চিত হন। যেভাবেই হোক, system-এ `pip install` এড়িয়ে চলুন।

### 8.3 Application বনাম library

- **Library** (অন্যরা import করবে): `pyproject.toml`-এ **range** (`requests>=2.31,<3`)। খুব কঠোর pin অন্যের project-এ version conflict তৈরি করে।
- **Application/tool** (deploy হবে): range রাখুন `pyproject.toml`-এ, আর আলাদা **lock file**-এ সব কিছুর নির্দিষ্ট version, hash সহ:
  - `pip-compile --generate-hashes`, বা `uv pip compile --generate-hashes`;
  - deploy-এ `pip install --require-hashes -r requirements.lock`।

`pip freeze > requirements.txt` একটি দ্রুত বিকল্প, কিন্তু তাতে hash থাকে না, এবং ভুল করে install হওয়া package-ও ঢুকে যায়।

### 8.4 Python version নির্বাচন

- Production-এ distribution-এর দেওয়া, নিরাপত্তা-আপডেট পাওয়া version, অথবা নির্দিষ্ট version-এর official container image (Module 09)।
- `requires-python` ঘোষণা করুন। CI-তে matrix দিয়ে নিম্নসীমা ও সর্বোচ্চ দুটোই পরীক্ষা করুন (L03-06)।
- একাধিক version লাগলে `uv python install` বা `pyenv`; Ubuntu-তে deadsnakes PPA (তৃতীয় পক্ষ — বিশ্বাসের সিদ্ধান্ত আপনার)।

## 9. Practical demonstration

Files: [`code/L05-01/envcheck.py`](code/L05-01/envcheck.py), [`pin_check.py`](code/L05-01/pin_check.py), [`sample-requirements.txt`](code/L05-01/sample-requirements.txt), [`sample-pyproject.toml`](code/L05-01/sample-pyproject.toml) (দুটোই হাতে তৈরি নমুনা)।

### 9.1 System Python বনাম venv

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-01
python3 envcheck.py --requires ">=3.10"
python3 -m venv /tmp/demo-venv
/tmp/demo-venv/bin/python envcheck.py --require-venv --pyproject sample-pyproject.toml
/tmp/demo-venv/bin/python -m pip list
```

**আসল output (Windows; Ubuntu-তে path ও version ভিন্ন হবে):**

```text
python               3.14.5
implementation       CPython
executable           C:\Python314\python.exe
in_venv              False
prefix               C:\Python314
base_prefix          C:\Python314
externally_managed   None
pip                  26.2.1
installed_count      80

(venv তৈরি: 3.330 s)
python               3.14.5
executable           …\scratchpad\demo-venv\Scripts\python.exe
in_venv              True
prefix               …\scratchpad\demo-venv
base_prefix          C:\Python314
externally_managed   None
pip                  26.1.1
installed_count      1

Package Version
------- -------
pip     26.1.1
```

**পর্যবেক্ষণ:**

- venv-এ `prefix` ≠ `base_prefix` — এটাই venv-এর সংজ্ঞা।
- System-এ ৮০টি package, venv-এ শুধু pip — পরিষ্কার শুরু।
- **venv-এর pip (২৬.১.১) system-এর pip (২৬.২.১)-এর চেয়ে পুরোনো:** venv internet থেকে নয়, Python-এর সাথে bundled (`ensurepip`) pip নেয়। নতুন venv-এর পরে `python -m pip install --upgrade pip` সাধারণ প্রথম ধাপ (internet লাগে; এখানে চালানো হয়নি)।
- এই Windows Python-এ PEP 668 marker নেই। Ubuntu ২৪.০৪-এর system Python-এ `externally_managed` লাইনে marker-এর path দেখা যাওয়ার কথা (যাচাই হয়নি)।

`--requires ">=3.15"` দিলে `PROBLEM: python 3.14.5 does not satisfy >=3.15` ও exit ১ — CI-তে "ভুল Python" দ্রুত ধরে।

### 9.2 Dependency কতটা নির্দিষ্ট

```bash
python3 pin_check.py sample-requirements.txt; echo "exit=$?"
python3 pin_check.py sample-pyproject.toml --mode library; echo "exit=$?"
```

**আসল output:**

```text
ok   line 3   pinned    requests
ok   line 4   hashed    urllib3
WARN line 6   range     pyyaml
WARN line 7   range     rich
WARN line 8   unpinned  click
ok   line 9   pinned    psycopg
WARN line 10  url       git+https://github.com/example/internal-tool.git@main
WARN line 11  editable  ./libs/shared
ok   line 12  include   dev-requirements.txt
summary: hashed=1, pinned=2, range=2, unpinned=1, url=1, editable=1, include=1
exit=1

ok   line 1   range     requests
ok   line 2   range     pyyaml
WARN line 3   unpinned  click
summary: range=2, unpinned=1
exit=1
```

- Application mode-এ range ও unpinned দুটোই সতর্কতা। Library mode-এ শুধু সীমাহীন `click`।
- `git+…@main` — একটি **branch**, প্রতিদিন বদলাতে পারে। Commit SHA দিয়ে pin করা উচিত (L03-06-এর action pinning-এর একই নীতি)।

### 9.3 লেখার সময় ধরা পড়া bug

প্রথম সংস্করণ শুধু ঠিক `pyproject.toml` নামের file-কে TOML ভাবত। তাই `sample-pyproject.toml`-কে requirements file হিসেবে পড়ে `error: line 2: cannot parse '[build-system]'` দিল। এখন file-এর suffix (`.toml`) দেখে চেনে।

### 9.4 Ubuntu-তে (চালানো হয়নি)

```bash
python3 --version
python3 -m venv /tmp/x            # "ensurepip is not available" → sudo apt install python3-venv
pip install requests              # system-এ: error: externally-managed-environment (PEP 668)
python3 envcheck.py               # externally_managed: /usr/lib/python3.12/EXTERNALLY-MANAGED
sudo apt install pipx && pipx install ruff     # CLI tool-এর জন্য
```

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_l05_01.py`](code/L05-01/test_l05_01.py)-এর ৭টি test:

- Version parsing।
- `requires` ও pyproject থেকে পড়া; exit ০/১/২।
- venv-এর যুক্তি (mock)।
- **আসল venv** তৈরি করে ভেতর থেকে `--require-venv` (pip ছাড়া venv)।
- Requirements-এর শ্রেণিবিভাগ (continuation-এর hash, extra ও marker সহ)।
- Mode ও exit।
- `==2.*` pin নয়।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `sys.prefix != sys.base_prefix` | venv চেনা | Python-এর documented পদ্ধতি |
| `sysconfig.get_path("stdlib")/EXTERNALLY-MANAGED` | PEP 668 marker | Ubuntu/Debian-এর রীতি |
| `importlib.metadata` | Installed package ও pip version | `pip` চালানো ছাড়া, দ্রুত |
| `tomllib` | pyproject পড়া | Standard library (৩.১১+) |
| `classify`-এ marker (`;`) বাদ | `psycopg==3.2.3 ; python_version…` | Marker version-এর অংশ নয় |
| Continuation (`\`) জোড়া | Hash পরের লাইনে | `pip-compile`-এর output এভাবেই |
| `==2.*` = range | Wildcard pin নয় | ভিন্ন patch আসতে পারে |
| Test-এ `venv.EnvBuilder(with_pip=False)` | Network ছাড়া আসল venv | দ্রুত, সব machine-এ চলে |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| venv-এ `envcheck.py --require-venv` | `in_venv True`, exit ০ |
| System-এ `--require-venv` | `PROBLEM: not inside…`, exit ১ |
| `pin_check.py sample-requirements.txt` | ৫টি WARN, exit ১ |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `error: externally-managed-environment` | PEP 668 | venv বা pipx; `--break-system-packages` নয় |
| `ensurepip is not available` | Ubuntu-তে `python3-venv` নেই | `sudo apt install python3-venv` (বা `python3.12-venv`) |
| `ModuleNotFoundError` অথচ install করেছি | ভিন্ন interpreter-এ install | `python -m pip`, এবং `which python` |
| Upgrade-এর পরে venv ভাঙা | Base interpreter বদলেছে | venv মুছে lock থেকে আবার তৈরি |
| systemd service package পায় না | System python দিয়ে চালানো | `ExecStart=/path/.venv/bin/python` |
| CI ও production-এ ভিন্ন আচরণ | Unpinned/transitive | Lock file + `--require-hashes` |
| `pip install` খুব ধীর বা ব্যর্থ (proxy) | Network | Internal mirror/proxy; `--index-url` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `sudo pip` কখনো নয় — install script root হিসেবে চলে (setup.py-এর code চলতে পারে)।
  - Lock + hash + `--require-hashes` ব্যবহার করুন; typo-squatting থেকে সতর্ক থাকুন।
  - `git+…@branch` নয়, commit SHA দিন।
  - Dependency-র vulnerability scan (`pip-audit`, Module 19) চালান।
  - venv directory Git-এ নয় (`.gitignore`-এ `.venv/` আছে)।
- **Performance:**
  - venv তৈরি কয়েক সেকেন্ড (এখানে ৩.৩ s)।
  - Wheel থাকলে install দ্রুত, sdist build ধীর।
  - CI-তে pip cache (L03-06); `uv` অনেক দ্রুত resolver।
- **Cost:**
  - Docker image-এ শুধু runtime dependency রাখুন (dev আলাদা) — ছোট image, কম storage ও transfer (Module 09)।

## 14. Hands-on exercise

1. Ubuntu VM-এ Section 9.4 চালান: PEP 668 error নিজের চোখে দেখুন, তারপর venv-এ একই install সফল করুন।
2. একটি venv-এ `requests` install করে `pip freeze` ও `pip-compile`-এর (বা `uv pip compile`) output তুলনা করুন। Transitive dependency কয়টি?
3. `pin_check.py`-তে `--strict-hashes` mode যোগ করুন: application-এ hash ছাড়া pinned dependency-ও WARN। Test লিখুন।
4. `envcheck.py`-তে "venv-এর base interpreter আর আছে কিনা" পরীক্ষা যোগ করুন (`pyvenv.cfg`-এর `home` পড়ে) — Section 5-এর upgrade পরিস্থিতি ধরার জন্য।
5. এই module-এর জন্য নিজের project `~/devops-ai-engineering-work/`-এ একটি `pyproject.toml` (requires-python, dev extra-তে pytest ও ruff) ও venv তৈরি করুন।

## 15. Mini-project — Environment bootstrap script

`bootstrap.sh` (Bash — L04-08-এর নিয়মে command জোড়া):

- `requires-python` যাচাই (`envcheck.py`)।
- `.venv` না থাকলে বা base interpreter বদলে থাকলে আবার তৈরি।
- Lock file-এর hash দিয়ে install।
- `pin_check.py` চালানো।
- শেষে `envcheck.py --require-venv --json`।
- Idempotent হতে হবে (L04-06)।

Module 11-এর CI ও Module 09-এর Dockerfile এই ধাপগুলো অনুসরণ করবে।

## 16. Interview প্রশ্ন

1. Virtual environment কী এবং কেন ব্যবহার করবেন?
2. `sudo pip install` কেন খারাপ ধারণা? PEP 668 কী?
3. Library ও application-এর dependency নির্দিষ্ট করার পার্থক্য কী?
4. Lock file ও `requirements.txt`-এর পার্থক্য। Hash কেন?
5. OS upgrade-এর পরে Python tool ভেঙে গেলে কী করবেন?
6. systemd service-এ venv-এর Python কীভাবে ব্যবহার করবেন?

## 17. Self-assessment প্রশ্ন

1. রান্নাঘর analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি ঘটনা ও সঠিক পদ্ধতি কী?
3. venv-এর pip system-এর চেয়ে পুরোনো কেন?
4. `git+…@main` কেন সতর্কতা পেল?
5. `activate` আসলে কী করে?

## 18. সংক্ষিপ্ত সারাংশ

- System Python OS-এর; প্রতিটি tool-এর নিজের venv (`.venv/bin/python`)।
- venv: `sys.prefix` ≠ `sys.base_prefix`; base interpreter বদলালে আবার তৈরি করতে হয়।
- PEP 668: system-এ pip নিষেধ — venv বা pipx; `--break-system-packages` নয়।
- Library-তে range, application-এ lock (transitive ও hash সহ)।
- `pyproject.toml` + `requires-python`; CI-তে version matrix।

## 19. Completion checklist

- [ ] System ও venv-এ `envcheck.py` চালিয়ে পার্থক্য ব্যাখ্যা করতে পারি
- [ ] Ubuntu-তে PEP 668 error ও তার সঠিক সমাধান দেখেছি
- [ ] একটি lock file (hash সহ) তৈরি করেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `venv`: https://docs.python.org/3/library/venv.html
- Python Packaging User Guide — Installing packages using pip and virtual environments: https://packaging.python.org/en/latest/guides/installing-using-pip-and-virtual-environments/
- PEP 668 — Marking Python base environments as "externally managed": https://peps.python.org/pep-0668/
- Python Packaging User Guide — Writing your `pyproject.toml`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/
- pip — Secure installs (`--require-hashes`): https://pip.pypa.io/en/stable/topics/secure-installs/
- pip-tools: https://pip-tools.readthedocs.io/
- uv documentation: https://docs.astral.sh/uv/
- pipx: https://pipx.pypa.io/

---

**পরের lesson:** L05-02 — Ops-এর জন্য Python fundamentals ও type hint
