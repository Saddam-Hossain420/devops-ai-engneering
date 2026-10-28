# L04-07 — ShellCheck ও bats দিয়ে testing

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | L04-01 থেকে L04-06 |
| **Label** | — |
| **Tested** | **ShellCheck ও bats এই machine-এ নেই, এবং install করার অনুমতি পাওয়া যায়নি — দুটোর কোনোটিই এই repository-তে চালানো হয়নি।** এখানে যা আসলে চলেছে: `shlint_mini.py` (ShellCheck-এর ছয়টি নিয়মের শেখার-সংস্করণ) ও `run_checks.sh`। Python test: ১০টি চলেছে, ৭টি পাস, ৩টি skip (bats ও ShellCheck — opt-in)। `shlint_mini` **এই module-এর নিজের script-এ একটি আসল bug ধরেছে** (L04-01-এর template-এ SC2155) এবং তার নিজের তিনটি false positive ঠিক করা হয়েছে — Section 9.2। Bats test file (`tests/*.bats`) লেখা হয়েছে কিন্তু **একবারও চালানো হয়নি**; Ubuntu-তে চালানোর ধাপ Section 9.4-এ। |

---

## 1. এই lesson-এ যা শিখবেন

- **Static analysis** কেন shell script-এ বিশেষভাবে জরুরি।
- **ShellCheck:** কী ধরে, code-এর (SCxxxx) অর্থ, `# shellcheck disable=` (কারণসহ), `source` অনুসরণ, `.shellcheckrc`।
- **bats-core:** `@test`, `run`, `$status`, `$output`, `setup`/`teardown`, `BATS_TEST_TMPDIR`।
- কী test করবেন: exit code, stdout বনাম stderr, file system-এর পরিবর্তন, dry-run, কঠিন input।
- Python unittest দিয়েও shell script test (এই module যা এতদিন করেছে) — কখন কোনটি।
- CI-তে check, এবং "SKIP" যেন কখনো "PASS" না দেখায়।
- একটি ছোট regex-ভিত্তিক linter লিখে দেখা কেন আসল parser দরকার।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Bash-এর ভুলগুলো সাধারণত **syntax error নয়** — script চলে, এবং কোনো বিশেষ input-এ ক্ষতি করে:

- Unquoted variable — space-যুক্ত নামে ভুল file মোছা (L04-02)।
- `local x=$(cmd)` — ব্যর্থতা লুকানো (L04-01)।
- `rm -rf "$DIR/"*` — DIR খালি হলে `/`-এর সব কিছু।
- `read` without `-r`, `for f in $(ls)`, `cd` ব্যর্থ হলে ভুল directory-তে কাজ।

এই module-এর প্রতিটি lesson-এ এমন একটি না একটি ভুল **লেখকের নিজের code-এ** ধরা পড়েছে — কোনোটি test-এ, কোনোটি আসল output-এ। Static analysis এগুলো চালানোর **আগেই** ধরে। আর automated test নিশ্চিত করে, পরের পরিবর্তনে পুরোনো ভুল ফিরে আসেনি (regression)।

## 3. সহজ ভাষায় পরিচয়

### ShellCheck

Shell script পড়ে (চালায় না), পূর্ণ parse করে, এবং পরিচিত ভুলের সতর্কতা দেয়:

```text
In backup.sh line 12:
rm -rf $TMPDIR/build
       ^-----^ SC2086 (info): Double quote to prevent globbing and word splitting.
       ^-----------^ SC2115 (warning): Use "${var:?}" to ensure this never expands to /build .
```

(উপরেরটি ShellCheck-এর output-এর **আকারের উদাহরণ** — এই repository-তে আসলে চালানো নয়।)

| ব্যবহার | Command |
|---|---|
| একটি file | `shellcheck script.sh` |
| `source` করা file-ও | `shellcheck -x script.sh` |
| CI-যোগ্য format | `shellcheck -f gcc script.sh` |
| শুধু warning ও তার উপরে | `shellcheck -S warning script.sh` |
| একটি লাইনে বন্ধ | পূর্বের লাইনে `# shellcheck disable=SC2086  # কারণ` |

### bats-core

Bash-এ লেখা test framework:

```bash
@test "missing source is a usage error" {
  run bash backup_safe.sh -s /does/not/exist -d "$BATS_TEST_TMPDIR/bk"
  [ "$status" -eq 2 ]
  [[ "$output" == *"not a directory"* ]]
}
```

- `run` command চালায় এবং `$status` (exit code) ও `$output`-এ ফল রাখে। Default-এ stderr-ও `$output`-এ মেশানো থাকে; আলাদা করতে `run --separate-stderr` (নতুন version)।
- প্রতিটি `@test` আলাদা process-এ চলে, এবং প্রতিটির নিজের `BATS_TEST_TMPDIR`।

### কোনটি কখন

| প্রশ্ন | Tool |
|---|---|
| Code-এ পরিচিত ভুলের pattern আছে কি? | ShellCheck |
| Script ঠিক আচরণ করে কি (exit code, file, output)? | bats বা Python unittest |
| Script-টি একটি বড় Python project-এর অংশ? | Python unittest + `subprocess` (এই repository-র CI loop) |
| শুধু shell team, কোনো Python নেই? | bats |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### গাড়ির inspection

- **ShellCheck** = যান্ত্রিক inspection: ব্রেক প্যাড, টায়ার, লাইট — গাড়ি না চালিয়েই পরিচিত ত্রুটির তালিকা ধরে পরীক্ষা।
- **bats test** = test drive: নির্দিষ্ট পরিস্থিতিতে (ভেজা রাস্তা, হঠাৎ ব্রেক) গাড়ি সত্যিই ঠিক আচরণ করে কি।
- **CI** = প্রতিবার মেরামতের পরে বাধ্যতামূলক inspection — "এবার তো ছোট কাজ" বলে বাদ নয়।

### Analogy কোথায় মেলে না

- Inspection-এর তালিকা সম্পূর্ণ মনে হয়। ShellCheck **শুধু পরিচিত pattern** ধরে — logic-এর ভুল (ভুল directory-র backup, ভুল threshold) ধরে না। পরিষ্কার ShellCheck মানে "সঠিক program" নয়।
- Inspector সবসময় সঠিক। Static analysis-এর **false positive** থাকে (Section 9.2-এ নিজের linter-এর তিনটি), এবং তখন `disable` করতে হয় — কারণ লিখে, যাতে পরের পাঠক বোঝেন এটা অবহেলা নয়।
- Inspection না হলে লোকে জানে। Tool **না থাকলে** অনেক CI script চুপচাপ এগিয়ে যায়, ফলে "সবুজ" দেখায় অথচ কিছুই পরীক্ষা হয়নি। এই lesson-এর `run_checks.sh` তাই প্রতিটি অনুপস্থিত tool-কে স্পষ্টভাবে **SKIP** বলে, এবং `--strict`-এ ব্যর্থ হয়।

## 5. Real-world engineering scenario — "Code review পাস, production-এ `/` মুছল"

**পরিস্থিতি (পরিচিত ঘটনা-ধরনের সংক্ষিপ্ত রূপ):** একটি installer-এর uninstall script-এ ছিল:

```bash
rm -rf "$INSTALL_ROOT/"*
```

একটি নতুন ধাপে `INSTALL_ROOT` সেট হওয়ার আগে কিছু অবস্থায় এই লাইন চলে গেল, ফলে command হয়ে গেল `rm -rf /*`। Review-তে কেউ ধরেননি — লাইনটি "স্বাভাবিক" দেখায়। এমন bug সত্যিকারের software-এ ঘটেছে এবং user-দের data মুছেছে।

**কী ধরত:**

- **ShellCheck SC2115:** `Use "${var:?}" to ensure this never expands to /*` — এই lesson-এর `shlint_mini`-এর M005 একই নিয়মের সরল রূপ।
- `set -u` (L04-01) — যদি variable কখনো সংজ্ঞায়িত না হতো।
- একটি test: "INSTALL_ROOT খালি হলে script ব্যর্থ হয় এবং কিছু মোছে না।"

**সঠিক রূপ:**

```bash
rm -rf -- "${INSTALL_ROOT:?INSTALL_ROOT is empty}/"*
```

**শিক্ষা:** মানুষের review বিপজ্জনক pattern নিয়মিতভাবে মিস করে। Static analysis একটি সস্তা, ক্লান্তিহীন reviewer — সবসময়, প্রতিটি commit-এ চালান।

## 6. Diagram — check-এর স্তর

```text
 লেখা ──► bash -n (syntax) ──► ShellCheck (pattern, parser-ভিত্তিক) ──► test (আচরণ) ──► review ──► merge
            সেকেন্ড-এর ভগ্নাংশ       সেকেন্ড                          সেকেন্ড–মিনিট       মানুষ
            শুধু parse error         SC2086, SC2155, SC2115…         exit code, file,      design,
                                                                     dry-run, কঠিন input   logic

 এই repository-তে আজ:
   bash -n            ✔ চালানো (run_checks.sh)
   ShellCheck         ✗ এই machine-এ নেই — Ubuntu-তে: sudo apt install shellcheck
   shlint_mini        ✔ চালানো (ShellCheck-এর ৬টি নিয়মের সরল রূপ — বিকল্প নয়)
   Python unittest    ✔ চালানো (প্রতিটি lesson-এর test_*.py, CI loop)
   bats               ✗ এই machine-এ নেই — tests/*.bats লেখা কিন্তু চালানো হয়নি
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Static analysis | Code না চালিয়ে বিশ্লেষণ |
| Linter | Static analysis tool (ShellCheck) |
| SCxxxx | ShellCheck-এর সতর্কতার code — wiki-তে ব্যাখ্যা |
| Directive | `# shellcheck disable=…` / `source=…` |
| False positive / negative | ভুলভাবে ধরা / ধরতে না পারা |
| bats `run` | Command চালিয়ে `$status`/`$output` ধরা |
| `setup` / `teardown` | প্রতিটি test-এর আগে / পরে |
| Fixture | Test-এর প্রস্তুত data বা file |
| Regression test | পুরোনো bug ফিরে না আসার পরীক্ষা |
| Opt-in check | পরিবেশ-চলক দিয়ে ইচ্ছামতো চালু |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 কেন regex যথেষ্ট নয় — নিজের linter-এর শিক্ষা

`shlint_mini.py` লাইন-ভিত্তিক regex দিয়ে quote সরিয়ে pattern খোঁজে। প্রথম সংস্করণ এই module-এর নিজের script-এ তিনটি **false positive** দিয়েছিল:

1. `tar … -C "$(dirname -- "$SOURCE")"` — double quote-এর ভেতরে `$(...)`, এবং তার ভেতরে আবার double quote। সরল quote-scanner দ্বিতীয় `"`-কে বাইরের quote-এর শেষ ধরে, তাই `$SOURCE`-কে "unquoted" দেখেছিল।
2. `readonly SCRIPT_DIR=$(cd -- "$(dirname -- …)" …)` — একই nested quote।
3. `local extra=$(( … ))` — arithmetic `$((`-কে command substitution `$(` ভেবেছিল।

এখন nested `$(...)` ও `$((` আলাদা করে মানে, কিন্তু তবু নিখুঁত নয় — heredoc-এর ভেতরে `$(`, escaped quote, `case`-এর pattern, line continuation ইত্যাদি। Shell-এর grammar context-নির্ভর। ShellCheck তাই একটি **পূর্ণ parser** (Haskell-এ লেখা) ব্যবহার করে। শিক্ষা: নিজের linter শেখার জন্য ভালো, production-এ প্রতিষ্ঠিত tool।

### 8.2 ShellCheck-এর কয়েকটি গুরুত্বপূর্ণ code

| Code | অর্থ | এই module-এ |
|---|---|---|
| SC2086 | Unquoted variable | L04-02 |
| SC2155 | `local x=$(...)` exit status লুকায় | L04-01 case ৭; template-এর আসল bug |
| SC2115 | `rm -rf "$x/"*` খালি হলে বিপদ | Section 5 |
| SC2164 | `cd` ব্যর্থ হলে? | L04-01 |
| SC2045 / SC2044 | `for f in $(ls/find)` | L04-02 |
| SC2162 | `read` without `-r` | L04-02 |
| SC2068 | Unquoted `$@` বা array | L04-02 |
| SC2016 | Single quote-এ `$` expand হয় না (হয়তো ইচ্ছাকৃত) | `expansion_lab.sh`-এর label — disable, কারণসহ |
| SC1091 | `source` করা file পাওয়া যায়নি | `-x`, `source=` directive |

### 8.3 Disable করার নিয়ম

```bash
# shellcheck disable=SC2016  # '${...}' লেখাগুলো ইচ্ছাকৃতভাবে literal label — expand হওয়ার কথা নয়
```

- শুধু নির্দিষ্ট code, নির্দিষ্ট লাইন বা file-এ।
- **সবসময় কারণ লিখুন।**
- পুরো repository-তে বন্ধ (`.shellcheckrc`-এ `disable=`) শুধু সত্যিকারের নীতিগত সিদ্ধান্তে।

### 8.4 অনুপস্থিত tool ও CI

একটি CI step "shellcheck না থাকলে skip"-এর মতো নিঃশব্দ হলে মাসের পর মাস কিছুই পরীক্ষা হয় না, অথচ সবুজ দেখায়। নীতি:

- Local-এ `SKIP` স্পষ্টভাবে ছাপুন।
- CI-তে tool install বাধ্যতামূলক করুন এবং `--strict` দিন।

এই repository-তে একটি বিশেষ সতর্কতা: GitHub-এর Ubuntu runner-এ ShellCheck সাধারণত আগে থেকেই থাকে, অথচ এখানে কখনো ShellCheck চালানো হয়নি। যাচাই-না-করা প্রত্যাশায় CI ভাঙা এড়াতে ShellCheck ও bats test **opt-in** রাখা হয়েছে (`RUN_SHELLCHECK=1`, `RUN_BATS=1`)। Ubuntu-তে একবার চালিয়ে finding ঠিক করার পরে CI-তে চালু করুন (Exercise ১, ২)।

## 9. Practical demonstration

### 9.1 শেখার linter — নমুনা

Files: [`code/L04-07/shlint_mini.py`](code/L04-07/shlint_mini.py), [`sample-bad.sh`](code/L04-07/sample-bad.sh) (হাতে তৈরি, ইচ্ছাকৃত ভুলে ভরা — চালাবেন না)।

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-07
python3 shlint_mini.py --list
python3 shlint_mini.py sample-bad.sh; echo "exit=$?"
```

**আসল output:**

```text
M001  (SC2086       ) unquoted variable in a file/dir command (word splitting + glob)
M002  (SC2155       ) `local/export/declare/readonly x=$(...)` hides the command's exit status
M003  (SC2164       ) `cd` without a failure check in a script that lacks `set -e`
M004  (SC2045/SC2044) looping over `$(ls ...)`/`$(find ...)` output breaks on spaces
M005  (SC2115       ) `rm -rf "$VAR/..."` — if VAR is empty this becomes `/...`; use ${VAR:?}
M006  (SC2162       ) `read` without -r mangles backslashes

sample-bad.sh:7: M002 `local/export/declare/readonly x=$(...)` hides the command's exit status [SC2155]
    local count=$(ls "$BACKUP_DIR" | wc -l)
sample-bad.sh:9: M005 `rm -rf "$VAR/..."` — if VAR is empty this becomes `/...`; use ${VAR:?} [SC2115]
    rm -rf "$BACKUP_DIR/"*
sample-bad.sh:12: M003 `cd` without a failure check in a script that lacks `set -e` [SC2164]
    cd /var/app
sample-bad.sh:13: M004 looping over `$(ls ...)`/`$(find ...)` output breaks on spaces [SC2045/SC2044]
    for f in $(ls *.log); do
sample-bad.sh:14: M001 unquoted variable in a file/dir command (word splitting + glob) [SC2086]
    cp $f /tmp/
sample-bad.sh:17: M006 `read` without -r mangles backslashes [SC2162]
    while read line; do
sample-bad.sh:21: M001 unquoted variable in a file/dir command (word splitting + glob) [SC2086]
    rm -rf $TMPDIR/build    # TMPDIR খালি হলে?
sample-bad.sh:21: M005 `rm -rf "$VAR/..."` — if VAR is empty this becomes `/...`; use ${VAR:?} [SC2115]
    rm -rf $TMPDIR/build    # TMPDIR খালি হলে?
1 file(s), 8 finding(s)
exit=1
```

### 9.2 Module-এর নিজের script-এ — একটি আসল bug

```bash
cd ..   # code/
python3 L04-07/shlint_mini.py L04-0[1-6]/*.sh L04-03/lib/*.sh
```

**প্রথম চালানোর আসল output (linter-এর false positive ঠিক করার আগে):**

```text
code\L04-01\script_template.sh:16: M001 unquoted variable … [SC2086]          ← false positive (nested quote)
code\L04-01\script_template.sh:16: M002 `…readonly x=$(...)` hides the command's exit status [SC2155]   ← আসল bug
    readonly SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
code\L04-01\strict_mode_demo.sh:27: M002 … [SC2155]                            ← ইচ্ছাকৃত (string-এর ভেতরে demo)
code\L04-06\backup_safe.sh:99: M002 … [SC2155]                                 ← false positive ($(( )))
code\L04-06\backup_safe.sh:129: M001 … [SC2086]                                ← false positive (nested quote)
11 file(s), 5 finding(s)
```

**আসল bug:** L04-01-এর template, যা নিজেই L04-01-এ শেখায় যে `local x=$(...)` ব্যর্থতা লুকায়, সেটাই এক লাইনে লিখেছিল `readonly SCRIPT_DIR=$(cd … && pwd)`। `cd` ব্যর্থ হলেও `readonly`-র সফলতা দেখা যেত, এবং script ভুল (খালি) `SCRIPT_DIR` নিয়ে চলত। এখন দুই লাইনে ভাগ করা: `SCRIPT_DIR=$(…)`, তারপর `readonly SCRIPT_DIR`। L04-01 lesson-এও আপডেট করা হয়েছে।

**তিনটি false positive** Section 8.1-এ ব্যাখ্যা করা হয়েছে, এবং linter ঠিক করা হয়েছে। ইচ্ছাকৃত demo-টি single quote-এর ভেতরে, তাই এখন ধরা পড়ে না। পরে:

```text
11 file(s), 0 finding(s)
```

এবং `test_module_scripts_are_clean` এখন প্রতিটি script-কে পাহারা দেয়।

### 9.3 `run_checks.sh` — স্পষ্ট SKIP

File: [`code/L04-07/run_checks.sh`](code/L04-07/run_checks.sh)

```bash
bash run_checks.sh; echo "exit=$?"
bash run_checks.sh --strict >/dev/null; echo "strict exit=$?"
```

**আসল output (এই machine — ShellCheck ও bats নেই):**

```text
checking 12 script(s) under /…/04-bash-and-shell-automation/code

== ShellCheck
SKIP shellcheck: not installed (Ubuntu: sudo apt install shellcheck; Fedora: sudo dnf install ShellCheck)

== bats
SKIP bats: not installed (Ubuntu: sudo apt install bats; Fedora: sudo dnf install bats)

== shlint_mini (learning linter — not a ShellCheck replacement)
12 file(s), 0 finding(s)
PASS shlint_mini

== bash -n (syntax)
PASS bash -n
exit=0
strict exit=1
```

প্রথম সংস্করণে `sample-bad.sh` (ইচ্ছাকৃত ভুলের fixture) scan-এ ঢুকে পুরো check ব্যর্থ করছিল — এখন `sample-*` বাদ।

### 9.4 Ubuntu-তে ShellCheck ও bats (এই repository-তে চালানো হয়নি)

```bash
sudo apt install shellcheck bats          # Fedora: sudo dnf install ShellCheck bats
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-07
shellcheck --version
shellcheck -x --rcfile shellcheckrc ../L04-0*/*.sh ../L04-03/lib/*.sh
shellcheck sample-bad.sh                  # SC2155, SC2045, SC2086, SC2162, SC2115, SC2164 প্রত্যাশিত
bats tests/                               # backup_safe.bats (৫টি), rename_ext.bats (৪টি)
bash run_checks.sh --strict
RUN_SHELLCHECK=1 RUN_BATS=1 python3 -m unittest -v
```

**প্রত্যাশা (যাচাই হয়নি):** `sample-bad.sh`-এ ShellCheck `shlint_mini`-এর চেয়ে **বেশি** সতর্কতা দেবে (যেমন `$1` unquoted assignment-এর পরে ব্যবহার, `wc -l`-এর বদলে glob-এর পরামর্শ)। Module-এর script-গুলোতে কিছু finding আসতে পারে, যা এখানে ধরা পড়েনি — সেগুলো ঠিক করা বা কারণসহ disable করা Exercise ১।

### 9.5 Bats test file

Files: [`tests/backup_safe.bats`](code/L04-07/tests/backup_safe.bats) (৫টি test), [`tests/rename_ext.bats`](code/L04-07/tests/rename_ext.bats) (৪টি test)। এগুলো L04-06 ও L04-02-এর Python test-এর একই আচরণ bats-এ যাচাই করে — দুটি ভাষায় একই specification। `@test`-এর syntax সাধারণ Bash নয়, তাই এখানে `bash -n` দিয়েও যাচাই করা যায়নি।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_l04_07.py`](code/L04-07/test_l04_07.py)-এর ১০টি test:

- **`shlint_mini` (৫টি):**
  - নমুনায় ৮টি finding হুবহু (লাইন ও নিয়ম)।
  - Quote ও guard করা রূপ পরিষ্কার।
  - Nested quote ও arithmetic-এর false positive-এর regression।
  - Heredoc ও disable comment।
  - Module-এর সব script পরিষ্কার।
- **`run_checks.sh` (২টি):** SKIP স্পষ্ট; `--strict` ও usage।
- **Opt-in, এখানে skip (৩টি):** bats suite; ShellCheck-এ module পরিষ্কার; নমুনায় ShellCheck-এর চারটি code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `strip_quotes` + `depth` | Quote সরানো, `$(...)`-এর ভেতরের nested quote আলাদা | Section 8.1-এর false positive |
| Heredoc skip | `<<EOF … EOF`-এর ভেতর বাদ | Heredoc-এর text code নয় |
| `shlint-disable=` | লাইন-ভিত্তিক বন্ধ | ShellCheck-এর directive-এর মতো |
| `run_checks.sh`-এ SKIP ও `--strict` | অনুপস্থিত tool স্পষ্ট | Section 8.4 |
| `-not -name 'sample-*'` | Fixture বাদ | ইচ্ছাকৃত ভুল scan-এ নয় |
| `--skip-external` ও opt-in env | যাচাই-না-করা tool CI-তে না চালানো | এখানে কখনো চালানো হয়নি এমন প্রত্যাশা নয় |
| `shellcheckrc` optional check comment | প্রথমে default, তারপর ধাপে ধাপে | অজানা সংখ্যক নতুন finding |

**Bash কেন এখানে, কোথায় নয়:** `run_checks.sh` tool জোড়া দেওয়ার কাজ (Bash-এর শক্তি)। Linter Python-এ, কারণ text বিশ্লেষণ ও test সহজ। আসল কাজে ShellCheck (Haskell) — ভাষা নয়, parser-ই মূল কথা।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `shlint_mini.py sample-bad.sh` | ৮টি finding, exit ১ |
| `shlint_mini.py` module-এর script-এ | ০টি finding |
| `run_checks.sh` (tool ছাড়া) | দুটি SKIP, দুটি PASS, exit ০; `--strict`-এ exit ১ |
| (Ubuntu) `bats tests/` | ৯টি test — **যাচাই হয়নি** |
| `python3 -m unittest -v` | `Ran 10 tests`, `OK (skipped=3)` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `SC1091: Not following: lib/common.sh` | `-x` নেই বা path অজানা | `shellcheck -x`; `# shellcheck source=lib/common.sh` |
| সব জায়গায় `disable` | Tool-কে চুপ করানো | প্রতিটি disable-এ কারণ; review-এ প্রশ্ন |
| CI সবুজ কিন্তু ShellCheck কখনো চলেনি | Tool অনুপস্থিত, নিঃশব্দ skip | স্পষ্ট SKIP ও `--strict` |
| bats-এ `$output`-এ stderr মিশে গেছে | `run`-এর default | `run --separate-stderr` (bats ১.৫+) বা assertion-এ সতর্কতা |
| bats test একে অপরকে প্রভাবিত করে | Shared temp | `BATS_TEST_TMPDIR` |
| নিজের linter-এ false positive | Regex-এর সীমা | ShellCheck; বা disable comment |
| Windows-এ `CRLF`-এর কারণে bats/ShellCheck অদ্ভুত error | Line ending | `.gitattributes`-এ `*.sh text eol=lf`, `*.bats text eol=lf` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - ShellCheck-এর অনেক নিয়ম সরাসরি নিরাপত্তার (SC2086 — injection ও glob; SC2115 — `/` মোছা)।
  - Script-এর test-এ শুধু `BATS_TEST_TMPDIR` বা `mktemp` — কখনো আসল path নয়।
  - Test-এ ইচ্ছাকৃত ভুলের fixture যেন কখনো চালানো না হয় (`sample-bad.sh`-এর শুরুতে সতর্কতা আছে)।
- **Performance:**
  - ShellCheck দ্রুত, তাই প্রতিটি commit-এ চালান। pre-commit hook-এ শুধু পরিবর্তিত file।
  - Bats test-এ `sleep`-নির্ভর test (concurrency) ধীর — সংখ্যা সীমিত রাখুন।
- **Cost:**
  - CI-এর কয়েক সেকেন্ড বনাম production-এ ভুল মোছা (Section 5)।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.4: ShellCheck চালিয়ে module-এর প্রতিটি finding লিখুন। প্রতিটিকে ঠিক করুন, বা কারণসহ disable করুন। কোনগুলো `shlint_mini` ধরতে পারেনি?
2. `bats tests/` চালান। কোনো test ব্যর্থ হলে, সেটা script-এর bug নাকি test-এর ভুল — নির্ণয় করে ঠিক করুন। তারপর `.github/workflows/validate.yml`-এ ShellCheck ও bats install এবং `RUN_SHELLCHECK=1 RUN_BATS=1` যোগ করুন।
3. `shlint_mini.py`-তে একটি নতুন নিয়ম M007 লিখুন: `[ $var = x ]`-এ unquoted variable (SC2086-এর একটি রূপ), test সহ। কোন ক্ষেত্রে false positive হয়?
4. L04-04-এর `safe_job.sh`-এর জন্য bats test লিখুন — সফল, ব্যর্থ ও SIGTERM (bats-এর ভেতরে background process)।
5. একটি pre-commit hook লিখুন (`.git/hooks/pre-commit`), যা staged `.sh` file-এ ShellCheck ও `shlint_mini` চালায় এবং finding থাকলে commit আটকায়।

## 15. Mini-project — Module 04-এর quality gate

`run_checks.sh`-কে repository-ব্যাপী quality gate বানান:

- সব module-এর `*.sh` file।
- ShellCheck (`-S warning` থেকে শুরু করে ধীরে ধীরে কঠোর)।
- bats suite, `shlint_mini`, `bash -n`, এবং `.sh` file-এ CRLF পরীক্ষা।
- JSON সারাংশ (কোন check, কত finding, SKIP কিনা)।
- CI-তে `--strict`।

Module 06-এর CI/CD pipeline-এ এটি একটি job হবে।

## 16. Interview প্রশ্ন

1. ShellCheck কী ধরে, কী ধরে না?
2. SC2086 ও SC2155 কী? উদাহরণ দিন।
3. একটি ShellCheck সতর্কতা কখন disable করা গ্রহণযোগ্য? কীভাবে?
4. Bash script কীভাবে test করবেন? bats-এর `run` কী করে?
5. Script-এর কোন আচরণ test করবেন (তালিকা)?
6. CI-তে tool অনুপস্থিত থাকলে কী হওয়া উচিত?

## 17. Self-assessment প্রশ্ন

1. গাড়ির inspection analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর bug কোন নিয়ম ধরত, এবং সঠিক রূপ কী?
3. Section 9.2-এ কোনটি আসল bug, কোনগুলো false positive — কেন?
4. ShellCheck ও bats test কেন opt-in রাখা হয়েছে?
5. এই lesson-এ কী আসলে চালানো হয়েছে, কী হয়নি?

## 18. সংক্ষিপ্ত সারাংশ

- Shell-এর বিপজ্জনক ভুল syntax error নয় — static analysis (ShellCheck) ও আচরণের test (bats বা unittest) দুটোই লাগে।
- ShellCheck: পূর্ণ parser; `-x`; directive কারণসহ; `.shellcheckrc`।
- bats: `run`, `$status`, `$output`, `BATS_TEST_TMPDIR`।
- Regex linter দ্রুত শেখায়, কিন্তু false positive দেয় — production-এ parser-ভিত্তিক tool।
- অনুপস্থিত tool-কে স্পষ্টভাবে SKIP বলুন; CI-তে `--strict`।
- এই repository-তে ShellCheck ও bats এখনো চালানো হয়নি — প্রথম কাজ Ubuntu-তে সেটা করা।

## 19. Completion checklist

- [ ] `shlint_mini.py`-এর আটটি finding ও তিনটি false positive ব্যাখ্যা করতে পারি
- [ ] Ubuntu-তে ShellCheck চালিয়ে module-এর finding ঠিক করেছি (Exercise ১)
- [ ] `bats tests/` চালিয়েছি এবং CI-তে যোগ করেছি (Exercise ২)
- [ ] `python3 -m unittest -v`-এ ১০টি test (৩টি opt-in skip, অথবা Ubuntu-তে সবগুলো পাস)
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- ShellCheck: https://www.shellcheck.net/
- ShellCheck wiki (প্রতিটি SC code): https://www.shellcheck.net/wiki/
- ShellCheck — source code ও `.shellcheckrc`: https://github.com/koalaman/shellcheck
- bats-core documentation: https://bats-core.readthedocs.io/
- bats-core — Writing tests: https://bats-core.readthedocs.io/en/stable/writing-tests.html
- Google Shell Style Guide: https://google.github.io/styleguide/shellguide.html

---

**পরের lesson:** L04-08 — কখন Bash, কখন Python
