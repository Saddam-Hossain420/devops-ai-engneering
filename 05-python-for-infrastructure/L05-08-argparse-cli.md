# L05-08 — argparse দিয়ে CLI tool

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L05-07 — Logging](L05-07-logging-structured.md), [L04-05 — Argument parsing (Bash)](../04-bash-and-shell-automation/L04-05-argument-parsing-logging.md) |
| **Label** | — |
| **Tested** | `opsctl.py`: ১০টি test পাস (Python 3.14.5, Windows, Git Bash)। Help, validation, disk, port, JSON ও closed pipe — সব আসলে চালানো হয়েছে। লেখার সময় **চারটি আসল সমস্যা** পাওয়া গেছে (Section 9.4): argparse-এর subparser default ফাঁদ, status-এর ভুল ক্রম, Windows-এ broken pipe-এর ভিন্ন error, এবং Git Bash-এর path রূপান্তর। Linux-এর `BrokenPipeError` path **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- `argparse`: positional, option, `nargs`, `choices`, `type`, default, `--version`।
- **Subcommand** (`git commit`-এর মতো) ও **সাধারণ option** (`parents=`), এবং তার একটি নীরব ফাঁদ।
- Custom type validator — ভুল input-এ সুন্দর error।
- **Exit code-এর রীতি:** monitoring-plugin (০/১/২/৩), usage error (৬৪), Ctrl-C (১৩০), SIGPIPE (১৪১)।
- Pipe-বান্ধব CLI: `| head`-এ traceback নয়; ফল stdout-এ, error stderr-এ; `--json`।
- Env var থেকে default; `pyproject.toml`-এর `[project.scripts]` দিয়ে install।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি script প্রথমে `sys.argv[1]` দিয়ে শুরু হয়। ছয় মাস পরে:

- কেউ জানে না কোন argument কোন ক্রমে।
- `--help` নেই।
- ভুল মান দিলে ৩০ লাইনের traceback।
- Monitoring system exit code দেখে "OK" ভাবে, কারণ script সব অবস্থায় ০ দেয়।
- `| head`-এ `BrokenPipeError`-এর traceback cron mail ভরিয়ে দেয়।

একটি ভালো CLI নিজেই নিজের documentation (help), ভুল input সাথে সাথে স্পষ্টভাবে প্রত্যাখ্যান করে, এবং অন্য tool-এর সাথে (shell, monitoring, CI) নির্ভরযোগ্যভাবে কথা বলে (exit code, JSON)।

## 3. সহজ ভাষায় পরিচয়

```python
import argparse
ap = argparse.ArgumentParser(prog="opsctl", description="...")
ap.add_argument("paths", nargs="+")                         # positional, এক বা একাধিক
ap.add_argument("--warn", type=float, default=80)           # option, type রূপান্তর
ap.add_argument("--json", action="store_true")              # flag
ap.add_argument("--level", choices=["info", "debug"])
args = ap.parse_args()                                      # ভুল হলে usage + exit 2
```

| CLI নিয়ম | কেন |
|---|---|
| `--help` সবসময় | নিজের documentation |
| ফল stdout-এ, বার্তা ও error stderr-এ | Pipe ও `jq` নিরাপদ (L04-01) |
| অর্থপূর্ণ exit code | Shell, cron, monitoring সিদ্ধান্ত নেয় |
| `--json` | অন্য tool পড়তে পারে |
| ভুল input-এ এক লাইনের error | Traceback নয় |
| Destructive কাজে `--dry-run` / নিশ্চিতকরণ | L04-06, L05-03 |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### সরকারি অফিসের ফর্ম জমা

- **Positional argument** = ফর্মের বাধ্যতামূলক ঘর (নাম, ঠিকানা) — ক্রম নির্দিষ্ট।
- **Option** = ঐচ্ছিক ঘর ("জরুরি হলে টিক দিন")।
- **Type validator** = কাউন্টারের কর্মী, যিনি জমা নেওয়ার আগেই বলেন "জন্মতারিখ ভুল format-এ" — ফর্ম ভেতরে গিয়ে এক সপ্তাহ পরে বাতিল হয় না।
- **Subcommand** = ভিন্ন কাউন্টার (পাসপোর্ট, লাইসেন্স), প্রত্যেকের নিজের ফর্ম, কিন্তু কিছু ঘর সাধারণ (নাম)।
- **Exit code** = রসিদের রং: সবুজ (গৃহীত), হলুদ (আংশিক), লাল (প্রত্যাখ্যাত)।

### Analogy কোথায় মেলে না

- অফিসে সাধারণ ঘর একবার লিখলেই সব কাউন্টারে যায়। **argparse-এ সাধারণ option main parser ও subparser দুটোতে রাখলে subparser-এর default চুপচাপ main-এর মান মুছে দেয়** (`opsctl --json disk` → `json=False`)। এর কোনো error নেই — Section 9.4।
- রসিদের রং যেকোনো ক্রমে সাজানো যায়। **Exit code-এর সংখ্যা গুরুত্বের ক্রম নয়:** UNKNOWN = ৩, CRITICAL = ২, কিন্তু একটি CRITICAL disk বেশি জরুরি। `max()` দিয়ে সামগ্রিক status বের করলে ভুল হয়।
- কর্মী ফর্ম ফেরত দিলে আপনি সাথে সাথে জানেন। **Program-এর output-এর পাঠক মাঝপথে চলে যেতে পারে** (`| head -1`), এবং লেখার চেষ্টায় error আসে — Linux-এ এক রকম, Windows-এ আরেক রকম।

## 5. Real-world engineering scenario — "Monitoring সব সবুজ দেখাচ্ছিল"

**পরিস্থিতি:** একটি disk-check script monitoring agent (Nagios/Icinga/Sensu-ধাঁচ) থেকে চলে। Agent exit code দেখে: ০ OK, ১ WARNING, ২ CRITICAL, ৩ UNKNOWN।

Script-টি এমন ছিল:

```python
used = check(sys.argv[1])
if used > 90:
    print("CRITICAL")
# … শেষে কিছুই return করে না → exit 0
```

ফলে "CRITICAL" print হলেও agent পেত exit ০, অর্থাৎ সবুজ। Disk ১০০% হয়ে database বন্ধ হলো। পরে দেখা গেল, ভুল path দিলেও script crash করে exit ১ দিত — যাকে agent পড়ত **WARNING**, যদিও আসলে check-টিই চলেনি।

**এই lesson-এর পদ্ধতি:**

- প্রতিটি check-এর status → **সবচেয়ে গুরুতর** status = exit code।
- পড়া যায়নি = UNKNOWN (৩)।
- ভুল ব্যবহার = ৬৪ — monitoring-এর ০–৩-এর সাথে মিশবে না।
- Text ও JSON দুটোই।

**শিক্ষা:** CLI-এর exit code তার API। Output মানুষ পড়ে; exit code পড়ে machine — এবং machine-ই রাত ৩টায় আপনাকে জাগায় (বা জাগায় না)।

## 6. Diagram — opsctl-এর কাঠামো

```text
 opsctl [--json] [-q] [--version] COMMAND …
   │
   ├─ disk PATH... [--warn %] [--crit %] [--json] [-q]
   │     type=percent → 0..100 যাচাই; warn < crit যাচাই (UsageError → 64)
   │     shutil.disk_usage → Check(OK/WARNING/CRITICAL/UNKNOWN)
   │
   └─ port HOST:PORT... [--timeout s ← env OPSCTL_TIMEOUT] [--json] [-q]
         type=host_port → ("::1", 22); socket.create_connection(timeout)

 checks ──► worst()  (severity: OK < WARNING < UNKNOWN < CRITICAL)  ──► exit 0/1/3/2
        └─► render(): text বা JSON (stdout);  -q → শুধু non-OK

 বিশেষ exit: argparse ভুল → 64 · --help/--version → 0 · Ctrl-C → 130 · বন্ধ pipe → 141
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Positional argument | নাম ছাড়া, অবস্থান দিয়ে চেনা |
| Option / flag | `--name value` / `--flag` |
| `nargs` | কয়টি মান (`?`, `*`, `+`, সংখ্যা) |
| Subcommand / subparser | `tool verb ...` কাঠামো |
| Parent parser | একাধিক parser-এ ভাগ করা option |
| `argparse.SUPPRESS` | Default না বসানো — attribute-ই থাকবে না |
| `ArgumentTypeError` | Custom type-এর ভুলে argparse-এর সুন্দর error |
| EX_USAGE (৬৪) | `sysexits.h`-এর "ভুল ব্যবহার" |
| SIGPIPE / EPIPE | পাঠক চলে যাওয়ার পরে লেখা |
| Entry point | Install করলে `opsctl` নামে command |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Subparser-এর default ফাঁদ

argparse প্রথমে main parser-এর option পড়ে `--json=True` বসায়। তারপর subcommand-এর অংশ subparser-কে দেয়। Subparser **নিজের সব default আবার বসায়**, ফলে `json=False` দিয়ে আগের `True` মুছে যায়।

`default=argparse.SUPPRESS` দিলে subparser কিছুই বসায় না, তাই আগের মান থাকে। তখন option না দিলে attribute-ই থাকে না — `getattr(args, "json", False)` দিয়ে পড়তে হয়।

### 8.2 Type validator

`type=` যেকোনো callable — string নিয়ে মান ফেরত দেয়, অথবা `ArgumentTypeError` তোলে। argparse তখন বলে `argument --warn: must be between 0 and 100, got 150` ও exit ২ দেয়।

যে যাচাই একাধিক argument-এর ওপর নির্ভর করে (warn < crit), সেটা parse-এর পরে করতে হয়।

### 8.3 Exit code ও argparse-এর ২

ভুল ব্যবহারে argparse `sys.exit(2)` করে। কিন্তু monitoring-এর রীতিতে ২ = CRITICAL! ভুল flag দিলে monitoring দেখাত "CRITICAL", যেন disk ভরা।

`opsctl` তাই `SystemExit`-এর ২-কে ৬৪ (EX_USAGE)-এ বদলায়। আপনার tool কোন জগতে কথা বলে (shell, monitoring, CI), সেই রীতি মেনে exit code বাছুন।

### 8.4 Broken pipe

`opsctl … | head -1`: head প্রথম লাইন পড়ে বেরিয়ে যায়, pipe-এর read end বন্ধ হয়।

- **Linux:** পরের `write` পায় SIGPIPE। Python এটা উপেক্ষা করে, তাই `BrokenPipeError` (EPIPE) আসে।
- **Windows:** এই machine-এ আসলে চালিয়ে দেখা গেছে, একই ঘটনায় এসেছে **`OSError: [Errno 22] Invalid argument`**।

সমাধান Python documentation-এর পরামর্শ অনুযায়ী: stdout-কে `/dev/null`-এ `dup2`, যাতে interpreter বন্ধের সময় flush আবার error না দেয়। Exit ১৪১ (১২৮ + SIGPIPE ১৩) — shell-এ signal-এ মারা যাওয়া process-এর রীতি।

**Timing-নির্ভরতা:** Output pipe buffer-এর (Linux-এ সাধারণত ৬৪ KiB) চেয়ে ছোট হলে head বন্ধ হওয়ার আগেই সব লেখা হয়ে যায়, ফলে কোনো error নেই (Section 9.3)।

> **Fedora-তে:** কোনো পার্থক্য নেই। `pipx install .` দিয়ে `opsctl` command install করা দুই distro-তে একই (L05-01)।

## 9. Practical demonstration

Files: [`code/L05-08/opsctl.py`](code/L05-08/opsctl.py), [`test_l05_08.py`](code/L05-08/test_l05_08.py)।

### 9.1 Help ও সফল/ব্যর্থ চালানো

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-08
python3 opsctl.py --help
python3 opsctl.py --json -q disk / /nonexistent --warn 10 --crit 50; echo "exit=$?"
python3 opsctl.py port 127.0.0.1:1 --timeout 0.5; echo "exit=$?"
```

**আসল output** (Windows; `C:/` ও `Z:/` ব্যবহার করা হয়েছে):

```text
usage: opsctl [-h] [--json] [-q] [--version] COMMAND ...
Small operations checks with monitoring-style exit codes.
  …
exit codes: 0 OK, 1 WARNING, 2 CRITICAL, 3 UNKNOWN, 64 usage error
examples:
  opsctl disk / --warn 80 --crit 90
  opsctl --json port 127.0.0.1:22

{
  "status": "critical",
  "checks": [
    { "name": "disk:C:/", "status": "critical", "detail": "82.4% used, 54 GiB free", "value": 82.4 },
    { "name": "disk:Z:/", "status": "unknown", "detail": "The system cannot find the path specified", "value": null }
  ]
}
exit=2

CRITICAL  port:127.0.0.1:1             timeout after 0.5s
exit=2
```

### 9.2 ভুল ব্যবহার — সব exit ৬৪

```text
$ opsctl disk / --warn 95 --crit 90
usage: opsctl [-h] [--json] [-q] [--version] COMMAND ...
opsctl: error: --warn (95) must be lower than --crit (90)
exit=64

$ opsctl disk / --warn 150
opsctl disk: error: argument --warn: must be between 0 and 100, got 150
exit=64

$ opsctl port localhost:99999
opsctl port: error: argument HOST:PORT: expected HOST:PORT, got 'localhost:99999'
exit=64

$ opsctl
opsctl: error: the following arguments are required: COMMAND
exit=64
```

### 9.3 Pipe

```bash
python3 opsctl.py disk / | head -0;  echo "exit=${PIPESTATUS[0]}"     # → 141, traceback নেই
python3 opsctl.py --json disk / / / …(৪০০ বার) | head -2; echo "exit=${PIPESTATUS[0]}"   # → 1
```

দ্বিতীয়টিতে ১৪১ নয়, ১ (WARNING) এসেছে। ~৪৮ KB output head বন্ধ হওয়ার আগেই pipe buffer-এ ঢুকে গিয়েছিল, তাই লেখায় কোনো error হয়নি। Broken pipe **timing-নির্ভর**। তাই test-এ read end লেখার **আগেই** বন্ধ করা হয়, যাতে ফল নির্দিষ্ট হয়।

### 9.4 লেখার সময় ধরা পড়া চারটি সমস্যা

1. **Subparser default ফাঁদ** — আলাদা script-এ আসলে চালিয়ে দেখা হয়েছে:

   ```text
   suppress=False: --json disk -> False | disk --json -> True
   suppress=True:  --json disk -> True  | disk --json -> True
   ```

2. **Status-এর ক্রম:** প্রথম সংস্করণে `max(status)`, ফলে CRITICAL + UNKNOWN মিলে "unknown", exit ৩ হচ্ছিল। এখন `SEVERITY` ক্রম; একই input-এ "critical", exit ২।
3. **Windows-এ broken pipe:** handler শুধু `BrokenPipeError` ধরছিল। এল `OSError: [Errno 22] Invalid argument` ও `Exception ignored while flushing sys.stdout`, exit ১২০। এখন EINVAL-ও ধরা হয়, exit ১৪১।
4. **Git Bash-এর path রূপান্তর:** `opsctl.py disk /` চালালে নাম এল `disk:C:/Program Files/Git/`। Git Bash (MSYS) `/`-দিয়ে শুরু argument-কে Windows path-এ বদলে দেয়। `MSYS_NO_PATHCONV=1` দিলে `/` অপরিবর্তিত যায়। এটা program-এর bug নয়, কিন্তু Windows-এ শেখার সময় বিভ্রান্তিকর — Ubuntu-তে ঘটে না।

### 9.5 Install করা command হিসেবে

`pyproject.toml`-এ (L05-01-এর নমুনার মতো):

```toml
[project.scripts]
opsctl = "opsctl:entrypoint"
```

তারপর `pipx install .` বা venv-এ `pip install -e .` → `opsctl disk /`। `entrypoint()` Ctrl-C (১৩০) ও broken pipe সামলায়। (এই repo-তে package বানানো হয়নি — উদাহরণ।)

### 9.6 Test

```bash
python3 -m unittest -v
```

১০টি test:

- Global option subcommand-এর আগে ও পরে।
- Validator (IPv6 `[::1]:22` সহ)।
- Usage error → ৬৪; help/version → ০।
- Env default।
- Disk threshold (mock); severity ক্রম।
- আসল socket-এ খোলা/বন্ধ port।
- JSON + `-q`।
- **বন্ধ pipe → ১৪১, traceback নয়।**

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `common` parent + `SUPPRESS` | `--json` যেকোনো অবস্থানে | Subparser default ফাঁদ এড়ানো |
| `getattr(args, "json", False)` | SUPPRESS-এর পরে পড়া | Attribute না-ও থাকতে পারে |
| `percent`, `host_port`, `positive_float` | Type + সীমা যাচাই | Parse-এর সময়ই এক লাইনের error |
| `rpartition(":")` + `strip("[]")` | `[::1]:22` | IPv6-এ একাধিক `:` |
| `required=True` subparsers | Command ছাড়া চালালে error | নইলে `args.command` None |
| `RawDescriptionHelpFormatter` + epilog | Help-এ উদাহরণ ও exit code | নিজের documentation |
| `%%` help-এ | `%` print | argparse help-এ `%` format-এর অক্ষর |
| `SEVERITY` + `worst()` | গুরুত্ব অনুযায়ী সামগ্রিক status | Section 9.4-এর bug |
| `SystemExit` 2 → 64 | Usage error আলাদা | Monitoring-এর ২-এর সাথে সংঘাত নয় |
| `entrypoint()` | ১৩০ / ১৪১ | Pipe ও Ctrl-C-তে traceback নয় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `opsctl --json disk /` | JSON (json হারায় না) |
| একটি CRITICAL + একটি UNKNOWN | `"status": "critical"`, exit ২ |
| `--warn 150` | exit ৬৪ |
| `… \| head -0` | exit ১৪১, traceback নেই |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `--json` দিলেও text | Subparser default মুছে দিয়েছে | `default=argparse.SUPPRESS` |
| `AttributeError: 'Namespace' has no attribute 'command'` | Subcommand ঐচ্ছিক | `required=True` |
| Help-এ `ValueError: unsupported format character` | Help text-এ `%` | `%%` |
| Monitoring ভুল flag-এ CRITICAL দেখায় | argparse-এর exit ২ | ৬৪-তে বদলান |
| `\| head`-এ traceback | Broken pipe সামলানো নেই | `entrypoint()`-এর মতো handler |
| Windows-এ `Errno 22` | Broken pipe-এর Windows রূপ | EINVAL-ও ধরুন |
| Git Bash-এ `/` ভিন্ন path | MSYS path conversion | `MSYS_NO_PATHCONV=1` |
| `-1` value option ভাবছে | `-`-দিয়ে শুরু মান | `--warn=-1` বা `--` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - CLI argument অন্য user `ps`-এ দেখতে পারে — password argument-এ নয় (`--password-file`, env; L05-10)।
  - `type=` দিয়ে input-এর সীমা যাচাই করুন — যেমন path-কে একটি নির্দিষ্ট directory-র ভেতরে রাখা।
  - Destructive subcommand-এ `--yes` বা interactive নিশ্চিতকরণ।
- **Performance:**
  - CLI-এর শুরুর সময় গুরুত্বপূর্ণ (প্রতি মিনিটে monitoring)। ভারী module (pandas, boto3) শুধু প্রয়োজনীয় subcommand-এর ভেতরে import করুন।
  - `python3 -X importtime opsctl.py --help` দিয়ে মাপুন।
- **Cost:** প্রতি মিনিটে ১০০০টি host-এ চললে শুরুর ২০০ ms = দিনে ~৮০ CPU-ঘণ্টা। ছোট মনে হয়, কিন্তু fleet-এ যোগ হয়।

## 14. Hands-on exercise

1. Ubuntu-তে `python3 opsctl.py disk / | head -0` চালান। Exit ১৪১ ও কোনো traceback নেই — নিশ্চিত হন (Linux-এর `BrokenPipeError` path)।
2. `opsctl`-এ `--log-level` যোগ করুন, L05-07-এর `setup_logging` দিয়ে। Log stderr-এ যাবে; `--json`-এর output-এ কোনো প্রভাব থাকবে না।
3. `inode` subcommand যোগ করুন (`os.statvfs` — শুধু POSIX)। Windows-এ UNKNOWN দেবে, কোনো crash নয়।
4. `--warn`/`--crit`-এর জন্য config file (L05-05) সমর্থন যোগ করুন। অগ্রাধিকার: CLI > env > file > default।
5. `python3 -X importtime opsctl.py --help 2>&1 | sort -t'|' -k2 -n | tail` দিয়ে সবচেয়ে ধীর import বের করুন।

## 15. Mini-project — `opsctl` package

- `opsctl/` package: `cli.py` (parser), `checks/disk.py`, `checks/port.py`, `checks/http.py` (L05-06-এর client দিয়ে)।
- `pyproject.toml`-এ entry point।
- `pipx install .` দিয়ে install করে `opsctl --json disk / port db:5432 http https://…/health`-এর মতো mixed check।
- Shell completion (`argcomplete` — ঐচ্ছিক)।

L05-12-এর health check tool এর ওপর তৈরি হবে।

## 16. Interview প্রশ্ন

1. একটি ভালো CLI tool-এর বৈশিষ্ট্য কী?
2. Exit code কেন গুরুত্বপূর্ণ? Monitoring plugin-এর রীতি কী?
3. stdout ও stderr কখন কোনটা?
4. `BrokenPipeError` কখন হয় এবং কীভাবে সামলাবেন?
5. argparse-এ subcommand ও shared option কীভাবে বানাবেন?
6. CLI-তে secret কীভাবে নেবেন?

## 17. Self-assessment প্রশ্ন

1. ফর্ম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ monitoring কেন সবুজ দেখাচ্ছিল (দুটি কারণ)?
3. `SUPPRESS` ছাড়া `--json disk`-এ কী হয়, এবং কেন?
4. argparse-এর exit ২-কে কেন ৬৪ করা হলো?
5. বড় output-এ broken pipe কেন হলো না?

## 18. সংক্ষিপ্ত সারাংশ

- argparse: type validator, subcommand, parent parser (`SUPPRESS` সহ), help-এ উদাহরণ ও exit code।
- Exit code = API; গুরুত্বের ক্রম সংখ্যার ক্রম নয়।
- ফল stdout-এ, বাকি stderr-এ; `--json`।
- Pipe ও Ctrl-C-তে traceback নয় (১৪১, ১৩০); Windows-এ broken pipe = EINVAL।
- `[project.scripts]` দিয়ে install করা command।

## 19. Completion checklist

- [ ] Subparser default ফাঁদ নিজে পুনরুৎপাদন করেছি
- [ ] Exit code ০/১/২/৩/৬৪/১৪১ প্রতিটি দেখেছি
- [ ] Ubuntu-তে broken pipe পরীক্ষা করেছি
- [ ] `python3 -m unittest -v`-এ ১০টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `argparse`: https://docs.python.org/3/library/argparse.html
- Python — argparse tutorial: https://docs.python.org/3/howto/argparse.html
- Python — Note on SIGPIPE (`signal` module): https://docs.python.org/3/library/signal.html#note-on-sigpipe
- Monitoring Plugins Development Guidelines (exit codes): https://www.monitoring-plugins.org/doc/guidelines.html
- Command Line Interface Guidelines: https://clig.dev/
- Python Packaging User Guide — Entry points / `[project.scripts]`: https://packaging.python.org/en/latest/guides/writing-pyproject-toml/#creating-executable-scripts

---

**পরের lesson:** L05-09 — pytest দিয়ে unit ও integration testing
