# L04-01 — Bash script-এর গঠন ও strict mode (এবং এর সীমাবদ্ধতা)

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L01-06 — Shell fundamentals](../01-linux-systems/L01-06-shell-fundamentals.md), [L01-07 — Pipe, grep, sed, awk](../01-linux-systems/L01-07-pipes-text-tools.md) |
| **Label** | — |
| **Tested** | `strict_mode_demo.sh` ও `script_template.sh`: ৮টি test পাস — ১৮টি strict-mode case-এর আসল ফল (GNU Bash 5.3.9, Windows/Git Bash), template-এর help, usage error, dry-run, input validation। Template লেখার সময় **নিজের একটি bug ধরা পড়েছে** (IFS ও `"$*"`) — Section 9.3। Ubuntu-র Bash 5.2-এ চালানো হয়নি — আচরণ একই হওয়ার কথা; case 13-এর exit code version-ভেদে ভিন্ন হতে পারে। |

---

## 1. এই lesson-এ যা শিখবেন

- একটি production-যোগ্য Bash script-এর গঠন: shebang, header, strict mode, constant, function, `main "$@"`।
- `set -e`, `set -u`, `set -o pipefail`, `set -E`, `inherit_errexit` — প্রতিটি কী করে।
- **Strict mode কোথায় চুপচাপ কাজ করে না** — ১৮টি আসল case।
- `((i++))`, `local x=$(...)`, `grep -c` ও SIGPIPE-এর মতো ফাঁদ।
- stdout বনাম stderr; exit code-এর চুক্তি; `IFS`-এর সুবিধা ও পার্শ্বপ্রতিক্রিয়া।
- একটি template যা পরের সব lesson-এ ব্যবহার হবে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Bash-এর default আচরণ হলো **ব্যর্থতা উপেক্ষা করে চালিয়ে যাওয়া**:

```bash
cd /var/app/releases/new     # directory নেই — ব্যর্থ, কিন্তু script চলতেই থাকে
rm -rf ./*                   # এখন বর্তমান directory-তে (হয়তো /)!
```

এই ধরনের script ইতিহাসে বহু data মুছেছে। একটি বিখ্যাত ধরনের উদাহরণ: `rm -rf "$STEAMROOT/"*`, যেখানে variable খালি থাকলে command হয়ে যায় `rm -rf /*`।

Strict mode (`set -euo pipefail`) এর বিরুদ্ধে প্রথম প্রতিরক্ষা। কিন্তু অনেকে ভাবেন এটা "সব ব্যর্থতা ধরে" — **ধরে না**। এই lesson-এর মূল শিক্ষা: strict mode কোথায় সাহায্য করে, কোথায় নীরব থাকে, এবং কোথায় অপ্রত্যাশিতভাবে ভালো code-ও থামিয়ে দেয়।

## 3. সহজ ভাষায় পরিচয়

**গঠন:**

```bash
#!/usr/bin/env bash                      # ১. shebang: কোন interpreter
# name.sh — কী করে, usage, exit code     # ২. header: পরের মানুষের জন্য
set -Eeuo pipefail                       # ৩. strict mode
readonly SCRIPT_DIR=...                  # ৪. constant
usage() { ...; }                         # ৫. function
main() { parse_args "$@"; ...; }
main "$@"                                # ৬. শেষ লাইনে চালানো — পুরো file পড়ার পরে
```

**Strict mode-এর অংশ:**

| Option | কী করে | কেন |
|---|---|---|
| `set -e` (errexit) | কোনো command ব্যর্থ (exit ≠ ০) হলে script থামে | ব্যর্থতার পরে চালিয়ে যাওয়া বন্ধ |
| `set -u` (nounset) | অজানা variable ব্যবহারে error | `$TYPO` খালি string হয়ে `rm -rf "$TYPO/"` না হয় |
| `set -o pipefail` | Pipeline-এর যেকোনো অংশ ব্যর্থ হলে pipeline ব্যর্থ | `curl ... \| tar x` — curl ব্যর্থ হলেও tar সফল দেখাত |
| `set -E` (errtrace) | ERR trap function-এর ভেতরেও | L04-04 |
| `shopt -s inherit_errexit` | `$(...)`-এর ভেতরেও `-e` | Bash 4.4+; default-এ subshell `-e` উত্তরাধিকার পায় না |

**Exit code-এর চুক্তি** (L01-06): ০ = সফল, ১ = runtime error, ২ = usage error (প্রচলিত রীতি)। **stdout = ফল** (অন্য program পড়বে), **stderr = log/diagnostic**।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### কারখানার জরুরি থামার বোতাম

- **No strict mode** = যন্ত্রে কিছু ভাঙলেও লাইন চলতে থাকে, ভাঙা অংশ নিয়েই।
- **`set -e`** = কোনো station লাল আলো দিলে পুরো লাইন থামে।
- **`set -u`** = লেবেলবিহীন বাক্স এলে থামে।
- **`pipefail`** = conveyor-এর মাঝের যেকোনো যন্ত্রের সমস্যাও গণ্য, শুধু শেষেরটা নয়।

### Analogy কোথায় মেলে না

- জরুরি বোতাম সব জায়গায় কাজ করে। `set -e` **অনেক জায়গায় ইচ্ছাকৃতভাবে বন্ধ থাকে**: `if`-এর শর্তে, `&&`/`||`-এর বাম দিকে, `if`-এর শর্তে ডাকা function-এর **পুরো ভেতরে**, `local x=$(...)`-এ। বোতামটা কোথায় কাজ করে না, সেটা মুখস্থ না থাকলে মিথ্যা নিরাপত্তাবোধ তৈরি হয়।
- লাল আলো মানে সমস্যা। Bash-এ **অ-শূন্য exit সবসময় সমস্যা নয়**: `grep` match না পেলে ১, `((0))` ১, `yes | head` SIGPIPE-এ ১৪১। Strict mode এগুলোতেও থামায়, তাই code-কে সচেতনভাবে লিখতে হয়।
- কারখানা থামলে কারণ দেখা যায়। `set -e` **নিঃশব্দে** থামে — কোন লাইনে, কেন, তা বলে না। ERR trap (L04-04) ছাড়া debug কঠিন।

## 5. Real-world engineering scenario — "Backup সফল বলছে, file খালি"

**পরিস্থিতি:** প্রতি রাতে একটি backup script চলে:

```bash
#!/bin/bash
pg_dump -h db.internal app | gzip > /backup/app-$(date +%F).sql.gz
echo "backup OK" | mail -s "backup" ops@example.com
```

তিন মাস ধরে প্রতিদিন "backup OK" email এসেছে। Restore-এর দিন দেখা গেল: সব file ২০ byte — খালি gzip।

**কারণ:** দুই মাস আগে database-এর password বদলেছিল। `pg_dump` ব্যর্থ হয়েছে, কিন্তু pipeline-এর exit code হয় **শেষ command (`gzip`)-এর**, এবং gzip খালি input পেয়েও সফল। `set -e` থাকলেও লাভ হতো না; **`pipefail`** লাগত।

**সঠিক রূপ:**

```bash
set -Eeuo pipefail
pg_dump -h db.internal app | gzip > "$tmp"
[[ $(stat -c %s "$tmp") -gt 1024 ]] || die "backup suspiciously small"
gzip -t "$tmp"                                  # archive অখণ্ড কিনা
mv -- "$tmp" "/backup/app-$(date +%F).sql.gz"   # atomic (L04-06)
```

এবং সবচেয়ে গুরুত্বপূর্ণ: **নিয়মিত restore পরীক্ষা** (Module 18)।

**শিক্ষা:** "Exit 0" মানে script যা পরীক্ষা করেছে তা ঠিক — script কী পরীক্ষা করেছে, সেটাই প্রশ্ন। Strict mode ভিত্তি; আসল ফলের যাচাই (আকার, checksum, restore) আলাদাভাবে লাগে।

## 6. Diagram — `set -e` কখন কাজ করে

```text
command ব্যর্থ (exit ≠ 0)
        │
        ├─ if / while / until-এর শর্তে?                    → উপেক্ষিত (case 3)
        ├─ && বা ||-এর (শেষ নয় এমন) অংশে?                   → উপেক্ষিত (case 4, 5)
        ├─ `!` দিয়ে উল্টানো?                                → উপেক্ষিত
        ├─ এমন function-এর ভেতরে যা if/&&/||-এ ডাকা হয়েছে?  → পুরো function-এ -e বন্ধ (case 6)
        ├─ pipeline-এর শেষ নয় এমন অংশে, pipefail ছাড়া?      → উপেক্ষিত (case 9)
        ├─ `local`/`export`/`declare` x=$(...)?              → builtin-এর সফলতা দেখা হয় (case 7)
        ├─ $(...)-এর ভেতরে, inherit_errexit ছাড়া?           → subshell চালিয়ে যায় (case 15)
        └─ অন্য সব ক্ষেত্রে                                   → script থামে
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Shebang | প্রথম লাইন `#!` — interpreter নির্ধারণ |
| `#!/usr/bin/env bash` | PATH থেকে bash খোঁজে (portable) |
| errexit / nounset / pipefail | `-e` / `-u` / pipeline-এর ব্যর্থতা |
| errtrace (`-E`) | ERR trap-এর উত্তরাধিকার |
| `inherit_errexit` | Command substitution-এ `-e` |
| Exit status | ০–২৫৫; ১২৮+N = signal N-এ মৃত্যু |
| SIGPIPE (১৪১) | পড়ার পক্ষ বন্ধ হলে লেখার পক্ষের সংকেত |
| IFS | Word splitting-এর বিভাজক অক্ষর |
| `"$@"` বনাম `"$*"` | আলাদা argument বনাম IFS-এর প্রথম অক্ষর দিয়ে জোড়া এক string |
| stdout / stderr | ফল / diagnostic |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 কেন এত ব্যতিক্রম?

`set -e` POSIX-এর একটি পুরোনো সংজ্ঞা অনুসরণ করে: একটি command-এর ব্যর্থতা যদি **ইতিমধ্যে পরীক্ষা করা হচ্ছে** (`if`, `&&`, `||`, `!`), তাহলে তা "অপ্রত্যাশিত" নয়। Function-এর ক্ষেত্রে নিয়মটি পুরো function-এর উপর ছড়িয়ে পড়ে — সবচেয়ে বিপজ্জনক অংশ, কারণ function-এর লেখক জানেন না কে কীভাবে ডাকবে (case 6: `false`-এর পরেও function চলেছে)।

### 8.2 সাধারণ ফাঁদ ও নিরাপদ রূপ

| ফাঁদ | কেন | নিরাপদ রূপ |
|---|---|---|
| `((count++))` যখন count=০ | Post-increment পুরোনো মান (০) ফেরত দেয়; `((0))` = exit ১ | `count=$((count + 1))` বা `((++count))` (ফল ≥১ হলে) |
| `local x=$(cmd)` | `local`-এর নিজের exit (০) দেখা হয় | `local x; x=$(cmd)` |
| `n=$(grep -c pat file)` | ০ match = exit ১ | `n=$(grep -c pat file || true)` |
| `yes \| head -1`, `cmd \| head` | head আগে বন্ধ → SIGPIPE ১৪১ | `head`-এর আগে সীমিত output, বা `\|\| true` সতর্কভাবে |
| `cd dir; rm -rf *` | cd ব্যর্থ হলে ভুল জায়গায় | `cd -- "$dir" \|\| exit 1` (strict mode থাকলেও স্পষ্ট) |
| `rm -rf "$DIR/"*` | DIR খালি হলে `/` | `set -u` + `: "${DIR:?}"` + path যাচাই |

### 8.3 `IFS=$'\n\t'` — সুবিধা ও খরচ

Unquoted variable-এ space-এ ভাঙা বন্ধ হয়, অর্থাৎ space-যুক্ত file name-এ কম দুর্ঘটনা ঘটে। কিন্তু:

- **Quote করা এখনো বাধ্যতামূলক।**
- `"$*"` এখন **newline** দিয়ে জোড়ে (Section 9.3-এ আসল bug)।
- `read -r a b <<< "x y"` আর space-এ ভাগ করে না।

অনেক অভিজ্ঞ লেখক তাই IFS default রেখে সবসময় quote করার নীতি পছন্দ করেন। এই repository-র template IFS বদলায়, তবে `log()`-এ স্থানীয়ভাবে ফিরিয়ে দেয়।

### 8.4 কখন strict mode যথেষ্ট নয়

Strict mode ব্যর্থতা ধরে, **ভুল ফল** ধরে না (Section 5)। জটিল logic, data structure বা error handling লাগলে Python বিবেচনা করুন (L04-08)।

## 9. Practical demonstration

### 9.1 ১৮টি case — strict mode কোথায় থামে

File: [`code/L04-01/strict_mode_demo.sh`](code/L04-01/strict_mode_demo.sh) — প্রতিটি case আলাদা child bash-এ চলে।

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-01
bash strict_mode_demo.sh
```

**আসল output (GNU Bash 5.3.9):**

```text
case title                                                       result
1   no strict mode: failing command                            continued (exit 0)
2   set -e: failing command                                    STOPPED   (exit 1)
3   set -e: failure inside if-condition                        continued (exit 0)
4   set -e: failure on left of && (not last)                   continued (exit 0)
5   set -e: failure on left of ||                              continued (exit 0)
6   set -e: function called as if-condition                    continued (exit 0)
7   set -e: local x=$(false) - local masks status              continued (exit 0)
8   set -e: x=$(false) - plain assignment                      STOPPED   (exit 1)
9   set -e: false | true (no pipefail)                         continued (exit 0)
10  set -eo pipefail: false | true                             STOPPED   (exit 1)
11  set -e: ((count++)) when count=0                           STOPPED   (exit 1)
12  set -e: count=$((count + 1)) when count=0                  continued (exit 0)
13  set -u: unset variable                                     STOPPED   (exit 127)
14  set -u: ${VAR:-default}                                    continued (exit 0)
15  set -e: $(false; echo x) - subshell, no inherit            continued (exit 0)
16  set -e + inherit_errexit: same                             STOPPED   (exit 1)
17  set -eo pipefail: grep -c with zero matches                STOPPED   (exit 1)
18  set -eo pipefail: yes | head -1 (SIGPIPE)                  STOPPED   (exit 141)
```

**সবচেয়ে গুরুত্বপূর্ণ সারি:**

- **৬:** `if f`-এর ভেতরে `f`-এর `false`-এর পরেও কাজ চলেছে। Function-এর লেখক `set -e`-এর উপর ভরসা করলে বিপদ।
- **৭ বনাম ৮:** একই `$(false)` — `local`-এ থামেনি, সাধারণ assignment-এ থেমেছে।
- **১১ বনাম ১২:** একই কাজ (count বাড়ানো), একটি script মেরে ফেলে। Loop counter-এ এই bug খুব প্রচলিত।
- **১৭, ১৮:** সম্পূর্ণ স্বাভাবিক কাজও strict mode-এ থামে — "০টি match" ব্যর্থতা নয়, এবং `head` আগে থামা স্বাভাবিক।
- **১৩:** exit code ১২৭ — Bash version-ভেদে ভিন্ন হতে পারে; আসল কথা, script থেমেছে।

### 9.2 Template

File: [`code/L04-01/script_template.sh`](code/L04-01/script_template.sh)

```bash
bash script_template.sh -h; echo "exit=$?"
bash script_template.sh -n world; echo "exit=$?"
bash script_template.sh 'bad name; rm -rf /'; echo "exit=$?"
bash script_template.sh; echo "exit=$?"
```

**আসল output (সংক্ষেপিত; সময় ও path ভিন্ন হবে):**

```text
script_template.sh — নতুন Bash script-এর শুরুর কাঠামো। Copy করে নাম ও কাজ বদলান।

Usage: script_template.sh [-h] [-n] NAME
  -h   help
  -n   dry-run: কী করত দেখায়, কিছু বদলায় না

Exit codes: 0 OK, 1 runtime error, 2 usage error
exit=0
01:45:26 script_template.sh: starting in /.../code/L04-01 (dry-run=1)
01:45:26 script_template.sh: dry-run: mkdir -p -- /tmp/world-demo
hello, world
exit=0
01:45:27 script_template.sh: ERROR: NAME must be letters, digits, _ or - (got: bad name; rm -rf /)
exit=1
(usage) exit=2
```

- Help header থেকেই তৈরি হয় (`sed`), তাই documentation ও code একসাথে থাকে।
- Log stderr-এ, ফল (`hello, world`) stdout-এ — `script_template.sh x | other_tool` পরিষ্কার থাকে।
- Input whitelist (`^[A-Za-z0-9_-]+$`) দিয়ে যাচাই — ক্ষতিকর নাম প্রত্যাখ্যাত।

### 9.3 Template-এ ধরা পড়া আসল bug

প্রথম সংস্করণে dry-run-এর output ছিল:

```text
01:44:59 script_template.sh: dry-run: mkdir
-p
--
/tmp/world-demo
```

কারণ: template `IFS=$'\n\t'` সেট করে, আর `log "dry-run: $*"`-এ `"$*"` argument-গুলো **IFS-এর প্রথম অক্ষর — newline — দিয়ে জোড়ে**।

সমাধান:

- `log()`-এ `local IFS=' '`।
- Dry-run-এ `printf '%q '` — যাতে দেখানো command হুবহু copy করে চালানো যায়, space-যুক্ত argument সহ।

একটি test (`test_dry_run_single_line_and_stdout_clean`) এখন এর regression ধরে।

**শিক্ষা:** "নিরাপদ" কৌশলেরও পার্শ্বপ্রতিক্রিয়া আছে। Script-এর output-ও test করুন।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_l04_01.py`](code/L04-01/test_l04_01.py)-এর ৮টি test:

- **Demo:** ১৮টি case চলেছে; কোন case-এ থামে আর কোনটায় চলে — দুটোই যাচাই; arithmetic ফাঁদ।
- **Template:** syntax ও help; usage error-এ exit ২; dry-run এক লাইনে ও stdout পরিষ্কার; ক্ষতিকর input প্রত্যাখ্যান।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| Demo-তে `"$BASH_BIN" -c "$code"` | প্রতিটি case আলাদা process | একটির থামা অন্যটিকে প্রভাবিত করে না |
| `REACHED` marker | শেষ পর্যন্ত পৌঁছালো কিনা | Exit code একা যথেষ্ট নয় (case 6: exit ০, কিন্তু ভুল জায়গায়) |
| `SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)`, তারপর `readonly SCRIPT_DIR` | Script-এর নিজের directory | `cd`-এর পরেও পাশের file খুঁজে পাওয়া। দুই লাইনে, কারণ `readonly x=$(...)` এক লাইনে লিখলে ব্যর্থতা লুকায় (case ৭-এর মতো) — প্রথম সংস্করণে এক লাইনে ছিল; L04-07-এর linter এটা ধরেছে |
| `getopts ':hn'` | Option parsing; শুরুর `:` = নিজে error সামলানো | L04-05-এ বিস্তারিত |
| `run()` wrapper | Dry-run-এ শুধু দেখায় | L04-06 |
| `main "$@"` শেষে | পুরো file parse হওয়ার পরে চলে | চালু থাকা অবস্থায় file বদলালে অদ্ভুত আচরণ এড়ায় |

**Bash কেন এখানে, কোথায় নয়:** command চালানো ও জোড়া লাগানোর জন্য Bash স্বাভাবিক। Test-এ Python, কারণ output parse করে যাচাই করা সহজ এবং এই repository-র CI loop Python unittest চালায়। Bash-এর নিজস্ব test framework (bats) L04-07-এ।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `bash strict_mode_demo.sh` | Section 9.1-এর table (case 13-এর exit code ভিন্ন হতে পারে) |
| `script_template.sh -n world` | এক লাইনের dry-run, stdout-এ শুধু `hello, world` |
| `script_template.sh` (argument ছাড়া) | exit ২ |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Script হঠাৎ নিঃশব্দে থেমে যায় | `set -e` + অপ্রত্যাশিত non-zero (`grep`, `((i++))`) | `bash -x script.sh`; ERR trap (L04-04) |
| `unbound variable` | `set -u` + ঐচ্ছিক variable | `${VAR:-}` বা `${VAR:-default}` |
| `$1: unbound variable` | Argument ছাড়া চালানো | `(( $# >= 1 )) \|\| usage` |
| Pipeline-এর ব্যর্থতা ধরা পড়ে না | `pipefail` নেই | `set -o pipefail`; `PIPESTATUS` দেখুন |
| `/bin/bash^M: bad interpreter` | Windows line ending (CRLF) | `dos2unix`; `.gitattributes`-এ `*.sh text eol=lf` |
| `#!/bin/sh`-এ `[[` কাজ করে না | Ubuntu-তে `sh` = dash (POSIX) | Bash feature লাগলে `#!/usr/bin/env bash` |
| Function-এর ভেতরে ব্যর্থতা ধরা পড়ে না | Function `if`/`&&`-এ ডাকা | স্পষ্ট `\|\| return 1`, বা return code পরীক্ষা |

> **Fedora-তে:** `/bin/sh` হলো bash (POSIX mode), Ubuntu-তে dash — তাই `#!/bin/sh` script Fedora-তে চলে কিন্তু Ubuntu-তে ভেঙে যেতে পারে। সবসময় সঠিক shebang দিন।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Input whitelist করে যাচাই করুন।
  - সব variable quote করুন (L01-06)।
  - `rm -rf "$VAR"`-এর আগে `${VAR:?}` ও path যাচাই করুন।
  - Secret argument-এ দেবেন না (`ps`-এ দেখা যায়) — environment বা file থেকে নিন (L00-04)।
  - `eval` এড়িয়ে চলুন।
  - Script-এর permission ৭৫৫ রাখুন; শুধু দরকারি অংশে sudo।
- **Performance:**
  - Bash-এ loop-এর ভেতরে external command (`sed`, `awk`) প্রতিবার নতুন process তৈরি করে — বড় data-য় ধীর। Parameter expansion (L04-02) বা একবারে `awk` ব্যবহার করুন।
- **Cost:**
  - নিঃশব্দে ব্যর্থ backup বা cleanup-এর মূল্য অনেক বেশি (Section 5)।
  - Strict mode ও ফলাফল-যাচাই সস্তা বীমা।

## 14. Hands-on exercise

1. `strict_mode_demo.sh`-এ তিনটি নতুন case যোগ করুন: `! false` (set -e), `false; true` বনাম `false && true`-এর পার্থক্য, এবং `set -u` সহ খালি array `"${arr[@]}"`। ফল ব্যাখ্যা করুন।
2. `script_template.sh` copy করে `disk_report.sh` বানান: `df -P`-এর output থেকে সবচেয়ে ভরা filesystem stdout-এ দেখাবে, আর log যাবে stderr-এ। `| tail -1` দিয়ে pipe করে দেখুন stdout পরিষ্কার কিনা।
3. Section 5-এর backup script `pipefail` ছাড়া ও সহ চালিয়ে দেখুন (database-এর বদলে `false | gzip > /tmp/x.gz`)। `PIPESTATUS[@]`-ও ছাপুন।
4. একটি file-এ CRLF line ending দিয়ে script বানিয়ে চালান — error message কী? `file script.sh` ও `cat -A` দিয়ে কারণ দেখান।
5. Case ৬-এর ফাঁদ এড়িয়ে একটি `check_service()` function লিখুন, যা `if`-এ ডাকা হলেও প্রতিটি ধাপের ব্যর্থতা ধরে।

## 15. Mini-project — Script skeleton generator

`new-script.sh NAME` লিখুন, যা `script_template.sh` থেকে নতুন script তৈরি করবে:

- নাম, তারিখ ও লেখক বসাবে, executable bit দেবে।
- আগে থেকে থাকলে overwrite করবে না।
- পাশে একটি Python test skeleton রাখবে।

পরের lesson-গুলোর প্রতিটি script এটি দিয়ে শুরু করুন।

## 16. Interview প্রশ্ন

1. `set -euo pipefail`-এর প্রতিটি অংশ কী করে?
2. `set -e` কোন কোন ক্ষেত্রে কাজ করে না?
3. `local x=$(cmd)` কেন ব্যর্থতা লুকায়?
4. `((i++))` কীভাবে strict mode-এ script মেরে ফেলতে পারে?
5. `"$@"` ও `"$*"`-এর পার্থক্য কী?
6. Script-এর log কেন stderr-এ লেখা উচিত?
7. `#!/bin/sh` ও `#!/usr/bin/env bash`-এর পার্থক্য।

## 17. Self-assessment প্রশ্ন

1. জরুরি বোতাম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর backup কেন "সফল" দেখাল?
3. Case ১৭ ও ১৮-এ কেন থামা অপ্রত্যাশিত?
4. Section 9.3-এর bug কী ছিল এবং কীভাবে ঠিক হলো?
5. Template-এর exit code চুক্তি কী?

## 18. সংক্ষিপ্ত সারাংশ

- গঠন: shebang, header, `set -Eeuo pipefail`, constant, function, শেষে `main "$@"`।
- Strict mode অনেক জায়গায় নীরব: `if`/`&&`/`||`, ঐ অবস্থায় ডাকা function, `local x=$(...)`, `$(...)` (inherit_errexit ছাড়া)।
- আবার স্বাভাবিক কাজেও থামায়: `((i++))`, `grep -c` = ০, SIGPIPE।
- stdout = ফল, stderr = log; exit ০/১/২।
- IFS বদলালে `"$*"`-এর আচরণও বদলায়।
- Strict mode ব্যর্থতা ধরে, ভুল ফল নয় — ফল আলাদাভাবে যাচাই করুন।

## 19. Completion checklist

- [ ] `strict_mode_demo.sh`-এর প্রতিটি case ব্যাখ্যা করতে পারি
- [ ] Template থেকে একটি নিজের script লিখেছি (Exercise ২)
- [ ] `pipefail`-এর প্রভাব নিজে দেখেছি (Exercise ৩)
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash Reference Manual — The Set Builtin: https://www.gnu.org/software/bash/manual/html_node/The-Set-Builtin.html
- GNU Bash Reference Manual — The Shopt Builtin: https://www.gnu.org/software/bash/manual/html_node/The-Shopt-Builtin.html
- POSIX — Shell Command Language: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html
- BashFAQ/105 — Why doesn't set -e do what I expected?: https://mywiki.wooledge.org/BashFAQ/105
- Google Shell Style Guide: https://google.github.io/styleguide/shellguide.html

---

**পরের lesson:** L04-02 — Variable, array ও parameter expansion
