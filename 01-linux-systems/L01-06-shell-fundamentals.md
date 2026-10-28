# L01-06 — Shell fundamentals: quoting, expansion, environment variable, exit code

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-05 — ACL, sudo ও least privilege](L01-05-acl-sudo.md) |
| **Label** | — |
| **Tested** | ৮টি unit test পাস, যার ৩টি আসল Bash চালিয়ে (Python 3.14 + **Git Bash = GNU Bash** on Windows)। Section 9-এর `argv_show.py`, glob ও exit code output এই Bash-এ চালিয়ে পাওয়া আসল ফল; Ubuntu-র Bash-এ এই আচরণ একই হওয়ার কথা, তবে সেখানে চালানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Shell কী, এবং একটি command line ভেতরে কোন ধাপে প্রক্রিয়া হয়।
- **Quoting:** single quote, double quote, backslash — কোনটি কী আটকায়।
- **Expansion:** variable, command substitution, arithmetic, brace, tilde, **glob** — এবং **word splitting**।
- **Shell variable বনাম environment variable** (`export`), `PATH` কীভাবে কাজ করে।
- **Exit code:** 0, 1, 2, 126, 127, 128+N; `$?`, `&&`, `||`।
- Python দিয়ে দেখা: program আসলে কী argument পায়; exit code-এর অর্থ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

DevOps-এর অধিকাংশ কাজ শেষ পর্যন্ত কোনো না কোনো shell-এ চলে: terminal, CI pipeline-এর `run:` step, Dockerfile-এর `RUN`, systemd-এর `ExecStart`, cron। আর shell-এর সবচেয়ে বিপজ্জনক bug-গুলো আসে **quoting ও expansion** না বোঝা থেকে:

- File নামে space থাকলে script ভুল file মুছে ফেলে।
- Variable খালি থাকলে `rm -rf "$DIR/"*` হয়ে যায় `rm -rf /*`।
- CI-তে একটি command ব্যর্থ হলেও pipeline "সবুজ" দেখায়, কারণ exit code দেখা হয়নি।
- Container `137` দিয়ে বন্ধ হয়েছে — অর্থ না জানলে বোঝা যায় না যে memory limit ছাড়িয়েছে।

এই lesson Bash script লেখার (Module 04) আগে **ভিত্তি**।

## 3. সহজ ভাষায় পরিচয়

**Shell কী?** একটি program যা আপনার লেখা command line পড়ে, ব্যাখ্যা করে, এবং অন্য program চালায়। Ubuntu-তে default interactive shell **Bash**; script-এ `/bin/sh` আসলে **dash** (একটি ছোট, দ্রুত POSIX shell) — তাই Bash-এর বিশেষ feature `sh`-এ কাজ নাও করতে পারে।

> **Fedora-তে:** `/bin/sh` হলো Bash নিজেই (POSIX mode-এ)। তাই "Fedora-তে চলে, Ubuntu-তে `sh script.sh` দিয়ে ভাঙে" — একটি পরিচিত সমস্যা। Script-এ সবসময় `#!/usr/bin/env bash` লিখুন যদি Bash feature ব্যবহার করেন।

**মূল সত্য:** Program নিজে কখনো quote, `*`, বা `$HOME` দেখে না। **Shell আগে সব প্রক্রিয়া করে**, তারপর program-কে একটি **argument-এর তালিকা** দেয়। এই lesson-এর `argv_show.py` সেই তালিকা দেখায় — shell বোঝার সবচেয়ে কার্যকর পরীক্ষা।

**Exit code কী?** প্রতিটি program শেষে ০–২৫৫ একটি সংখ্যা ফেরত দেয়। **০ = সফল**, অন্য যেকোনো = কোনো ধরনের ব্যর্থতা। Shell, CI, systemd, Kubernetes — সবাই এই সংখ্যা দেখে সিদ্ধান্ত নেয়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের সহকারী ও নির্দেশপত্র

আপনি সহকারীকে (shell) একটি নির্দেশপত্র দিলেন: "ফাইল আলমারি থেকে *সব জানুয়ারির* ফাইল আনো এবং $বস-এর টেবিলে রাখো।"

- সহকারী আগে নির্দেশ বুঝে নেন: "সব জানুয়ারির" → আসল ফাইলের তালিকা (**glob expansion**), "$বস" → আজকের বস কে (**variable expansion**)।
- তারপর কর্মীকে (program) **নির্দিষ্ট তালিকা** দেন — কর্মী কখনো "সব জানুয়ারির" কথাটি দেখেন না।
- আপনি যদি উদ্ধৃতিচিহ্নে লেখেন 'সব জানুয়ারির' — সহকারী অক্ষরে অক্ষরে পাঠান, ব্যাখ্যা করেন না (**single quote**)।
- কর্মী কাজ শেষে একটি টিক বা ক্রস দেন (**exit code**)।

### Analogy কোথায় মেলে না

- মানুষ সহকারী ভুল বুঝলে প্রশ্ন করেন। Shell **কখনো প্রশ্ন করে না**: খালি variable থাকলে নীরবে খালি string বসিয়ে দেয়, এবং command চলে যায় — `rm -rf "$DIR"/` যেখানে `DIR` খালি, ঝুঁকিপূর্ণ।
- মানুষ বুঝবেন "my file.txt" একটি নাম। Shell quote ছাড়া space দেখলেই **দুটি আলাদা word** বানায় — word splitting যান্ত্রিক।
- কর্মীর টিক/ক্রস শুধু দুই রকম। Exit code-এর অনেক মান, এবং ১২৮-এর বেশি সংখ্যার নির্দিষ্ট অর্থ আছে (signal)।

## 5. Real-world engineering scenario — space-যুক্ত file নাম ও ভুল delete

**পরিস্থিতি:** একটি cleanup script পুরোনো backup মুছে:

```bash
for f in $(ls /backup/*.tar.gz); do
  rm $f
done
```

একদিন কেউ backup রাখলেন `/backup/db 2026-10.tar.gz` (নামে space)।

**ঘটনার ক্রম:**

1. `$(ls ...)`-এর output unquoted → word splitting → `/backup/db` এবং `2026-10.tar.gz` দুটি আলাদা word।
2. `rm /backup/db` — যদি `/backup/db` নামে অন্য কিছু থাকত (যেমন একটি directory-র file নয় কিন্তু অন্য দরকারি file), সেটি মুছে যেত; না থাকলে error।
3. `rm 2026-10.tar.gz` — **current directory**-তে একই নামের file থাকলে সেটি মুছে যায়!
4. আসল backup অক্ষত থাকে, অথচ script "সফল" মনে হতে পারে।

**সঠিক রূপ:**

```bash
for f in /backup/*.tar.gz; do      # glob সরাসরি — প্রতিটি নাম একটি word
  rm -- "$f"                       # quote: space নিরাপদ; -- : '-' দিয়ে শুরু নাম option নয়
done
```

**শিক্ষা:** `$(ls)` parse করবেন না; variable সবসময় `"$var"`। ShellCheck (Module 04) এই ভুলগুলো স্বয়ংক্রিয়ভাবে ধরে।

## 6. Diagram — Bash কীভাবে একটি command line প্রক্রিয়া করে

```text
 ইনপুট:   cp ~/"my file.txt" "$DEST"/backup-$(date +%F).txt *.log
     │
     ▼ 1. Tokenize — quote মেনে word ও operator-এ ভাগ
     ▼ 2. Brace expansion      {a,b} → a b
     ▼ 3. Tilde expansion      ~ → /home/sami
     ▼ 4. Parameter/variable   $DEST → /srv/backups
     ▼ 5. Command substitution $(date +%F) → 2026-10-26
     ▼ 6. Arithmetic           $((1+2)) → 3
     ▼ 7. Word splitting       (শুধু UNQUOTED expansion-এর ফলাফলে, IFS দিয়ে)
     ▼ 8. Pathname (glob)      *.log → app.log error.log   (unquoted হলে)
     ▼ 9. Quote removal        quote চিহ্নগুলো মুছে যায়
     ▼
 program পায় argv:
   ["cp", "/home/sami/my file.txt", "/srv/backups/backup-2026-10-26.txt", "app.log", "error.log"]
```

**Quote-এর প্রভাব:**

| | `$var` expand | `$(cmd)` | `*` glob | word splitting |
|---|---|---|---|---|
| quote নেই | হ্যাঁ | হ্যাঁ | হ্যাঁ | **হ্যাঁ** |
| `"double"` | হ্যাঁ | হ্যাঁ | না | **না** |
| `'single'` | না | না | না | না |

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Shell | Command line পড়ে, ব্যাখ্যা করে program চালানো program (Bash, dash, zsh) |
| argv | Program যে argument-এর তালিকা পায় |
| Quoting | Shell-কে নির্দিষ্ট অক্ষরের বিশেষ অর্থ ব্যবহার করতে না দেওয়া |
| Expansion | `$var`, `$(cmd)`, `~`, `*` ইত্যাদি আসল মানে রূপান্তর |
| Word splitting | Unquoted expansion-এর ফলকে space/tab/newline (IFS) দিয়ে ভাগ |
| Glob | `*`, `?`, `[...]` দিয়ে file নাম মেলানো |
| Shell variable | শুধু এই shell-এ; child process পায় না |
| Environment variable | `export` করা; child process copy পায় (L00-04) |
| `PATH` | Command খোঁজার directory-র তালিকা, `:` দিয়ে আলাদা |
| Exit status / code | Program শেষে ফেরত দেওয়া ০–২৫৫ সংখ্যা; `$?` |
| Builtin | Shell-এর নিজের command (`cd`, `export`, `echo`) — আলাদা program নয় |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Command খোঁজা

`python3` লিখলে Bash ক্রমে দেখে: alias → function → **builtin** → `PATH`-এর directory-গুলো বাম থেকে ডানে (প্রথম মিল)। পাওয়ার পরে L01-01-এর `fork`/`clone` + `execve` system call দিয়ে চালায়।

```bash
type cd python3 ls          # প্রতিটি কী: builtin, file, alias
echo "$PATH" | tr ':' '\n'  # PATH-এর প্রতিটি directory আলাদা লাইনে
command -v python3          # কোন path চালানো হবে
```

`cd` কেন builtin? কারণ child process-এর directory বদলালে parent shell-এর directory বদলায় না — তাই shell নিজেকেই বদলাতে হয়। একই কারণে `export` ও builtin।

### 8.2 Shell variable বনাম environment

```bash
GREETING=hello          # shell variable
python3 -c 'import os; print(os.environ.get("GREETING"))'   # None — child দেখে না
export GREETING         # environment-এ
python3 -c 'import os; print(os.environ.get("GREETING"))'   # hello
GREETING=hi python3 -c 'import os; print(os.environ["GREETING"])'   # শুধু এই একটি command-এর জন্য
```

`=`-এর দুই পাশে space নিষেধ: `GREETING = hello` মানে "`GREETING` নামের command চালাও, argument `=` ও `hello`"।

### 8.3 Exit code-এর নিয়ম

| Code | সাধারণ অর্থ |
|---|---|
| 0 | সফল |
| 1 | সাধারণ ব্যর্থতা |
| 2 | ভুল ব্যবহার (ভুল option) — অনেক tool-এর convention |
| 126 | Command পাওয়া গেছে কিন্তু চালানো যায় না (execute permission, noexec) |
| 127 | Command পাওয়া যায়নি |
| 128 + N | Signal N-এ মারা গেছে: 130 = Ctrl+C (2), **137 = SIGKILL (9)**, **143 = SIGTERM (15)** |

**137 দেখলেই সন্দেহ করুন OOM** — Linux OOM killer বা container-এর memory limit SIGKILL পাঠায় (L01-09, Module 09)। Exit status ৮ bit — `exit 256` আসলে 0।

**Pipe-এর exit code:** default-ভাবে pipeline-এর exit code = **শেষ** command-এর। `false | true` → 0! মাঝের ব্যর্থতা লুকিয়ে যায়। Bash-এ `set -o pipefail` (L04-01) বা `${PIPESTATUS[@]}`।

### 8.4 গুরুত্বপূর্ণ parameter expansion

```bash
echo "${NAME:-guest}"         # NAME খালি/unset হলে "guest" (NAME বদলায় না)
echo "${DIR:?DIR is not set}" # খালি হলে error দিয়ে থামো — বিপজ্জনক command-এ সুরক্ষা
file=report.tar.gz
echo "${file%.gz}"            # শেষ থেকে সবচেয়ে ছোট মিল বাদ → report.tar
echo "${file%%.*}"            # শেষ থেকে সবচেয়ে বড় মিল বাদ → report
echo "${#file}"               # দৈর্ঘ্য → 13
```

`rm -rf "${BUILD_DIR:?}/"*` — `BUILD_DIR` খালি হলে command চলবেই না। Section 5-এর মতো দুর্ঘটনার বিরুদ্ধে সস্তা বীমা।

## 9. Practical demonstration

### 9.1 Argument আসলে কী যায়

File: [`code/L01-06/argv_show.py`](code/L01-06/argv_show.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-06
name="my file.txt"
python3 argv_show.py $name "$name"
python3 argv_show.py *.py '*.py'
```

**আসল output (GNU Bash-এ চালানো):**

```text
received 3 argument(s)
  [1] 'my'
  [2] 'file.txt'
  [3] 'my file.txt'
received 4 argument(s)
  [1] 'argv_show.py'
  [2] 'exit_code.py'
  [3] 'test_l01_06.py'
  [4] '*.py'
```

- Unquoted `$name` → **দুটি** argument (word splitting)। Quoted `"$name"` → একটি।
- Unquoted `*.py` → shell file নাম বসিয়েছে; `'*.py'` → program আক্ষরিক `*.py` পেয়েছে।

নিজে চেষ্টা করুন:

```bash
python3 argv_show.py ~ "~" '$HOME' "$HOME"
python3 argv_show.py {a,b,c}.txt
python3 argv_show.py "$(date +%F)" $((6*7))
python3 argv_show.py ""                       # খালি string-ও একটি argument
```

**মিল খুঁজে না পাওয়া glob:** `python3 argv_show.py *.xyz` — কোনো `.xyz` file না থাকলে Bash default-ভাবে আক্ষরিক `*.xyz` পাঠায় (অপ্রত্যাশিত!)। `shopt -s nullglob` দিলে কিছুই পাঠায় না।

### 9.2 Exit code

File: [`code/L01-06/exit_code.py`](code/L01-06/exit_code.py)

```bash
ls /nonexistent; echo "exit: $?"
nosuchcmd; echo "exit: $?"
python3 exit_code.py 0 1 2 126 127 130 137 143
```

**আসল output (exit_code.py অংশ):**

```text
0: success
1: general error (program-নির্দিষ্ট)
2: misuse / invalid arguments (অনেক tool-এর convention; Bash builtin-এর ভুল ব্যবহার)
126: command found but not executable (permission বা noexec)
127: command not found (PATH বা বানান)
130: killed by SIGINT (128+2) — Ctrl+C
137: killed by SIGKILL (128+9) — জোর করে মারা — প্রায়ই OOM killer বা kill -9 / container memory limit
143: killed by SIGTERM (128+15) — ভদ্রভাবে বন্ধের অনুরোধ (systemctl stop, docker stop, kill)
```

Git Bash-এ `nosuchcmd` চালিয়ে আসল ফল ছিল `127`। `ls /nonexistent`-এর code Linux-এ GNU ls অনুযায়ী `2` (উদাহরণ — ls-এর documentation দেখুন)।

**Signal থেকে exit code নিজে তৈরি করুন (Ubuntu):**

```bash
sleep 100 &                 # background
kill -TERM $!               # $! = শেষ background process-এর PID
wait $!; echo "exit: $?"    # 143
sleep 100 &
kill -KILL $!
wait $!; echo "exit: $?"    # 137
```

### 9.3 `&&`, `||` ও pipe

```bash
mkdir -p /tmp/demo && echo "created"           # প্রথমটি সফল হলে দ্বিতীয়টি
false || echo "fallback ran"                    # প্রথমটি ব্যর্থ হলে দ্বিতীয়টি
false | true; echo "pipe exit: $?"              # 0 — ব্যর্থতা লুকানো!
false | true; echo "statuses: ${PIPESTATUS[*]}" # 1 0
set -o pipefail; false | true; echo "with pipefail: $?"; set +o pipefail
```

⚠️ `cmd1 && cmd2 || cmd3` if/else নয় — `cmd2` ব্যর্থ হলেও `cmd3` চলে। আসল শাখার জন্য `if`।

### 9.4 Python-এর shlex — shell-এর নিয়ম code-এ

Python-এ shell command তৈরি করতে হলে `shlex.quote` ব্যবহার করুন — বা আরো ভালো, list argument দিয়ে `subprocess.run([...])`, যাতে shell আদৌ জড়িত না থাকে (L05-04)। Test [`test_l01_06.py`](code/L01-06/test_l01_06.py) দেখায় `shlex.split` কীভাবে shell-এর quoting নিয়ম অনুসরণ করে এবং `shlex.quote` কীভাবে `x; rm -rf ...`-এর মতো ক্ষতিকর input-কে নিরীহ একটি argument বানায়।

```bash
python3 -m unittest -v
```

৮টি test: exit code ব্যাখ্যা ও CLI, shlex quoting নিয়ম, নিরাপদ quote, argv বিবরণ, এবং **আসল Bash চালিয়ে** word splitting, `&&`/`||`, ও `${X:-default}` (Bash না থাকলে এই ৩টি skip)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `sys.argv[1:]` | Program যা পেয়েছে | `argv[0]` program-এর নাম |
| `{a!r}` (repr) | `'my file.txt'`, `''` | Space ও খালি string চোখে পড়ে — `print(a)` দিলে লুকিয়ে যেত |
| `explain()`: `code > 128` → `code - 128` | Signal নম্বর বের করা | Shell-এর convention |
| `subprocess.run([BASH, "-c", script])` | Test-এ আসল Bash | শুধু Python-এ simulate না করে আসল আচরণ যাচাই |
| `@skipUnless(BASH)` | Bash না থাকলে skip | Platform-নির্ভরতা স্পষ্ট |
| `shlex.quote()` | নিরাপদ single-quoted রূপ | Command injection ঠেকায় |

### Python কেন এখানে, আর কোথায় নয়

Shell-এর আচরণ শিখতে আসল shell-ই দরকার — Python তা প্রতিস্থাপন করে না। Python এখানে **পর্যবেক্ষণের যন্ত্র** (argv দেখা) ও **নিয়ম যাচাইয়ের** (test) কাজ করে।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `argv_show.py $name` (name="a b") | ২টি argument |
| `argv_show.py "$name"` | ১টি argument |
| `nosuchcmd; echo $?` | 127 |
| `sleep 100 & kill -9 $!; wait $!; echo $?` | 137 |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `x: command not found` যেখানে `x=5` লিখেছেন | `=`-এর পাশে space | `x = 5` দেখুন | `x=5` |
| Space-যুক্ত নামে file "পাওয়া যায় না" | Unquoted variable | `argv_show.py $var` | `"$var"` |
| Script `sh script.sh` দিয়ে ভাঙে, `bash` দিয়ে চলে | Ubuntu-তে `sh` = dash | `ls -l /bin/sh` | `#!/usr/bin/env bash` ও `bash script.sh` বা `./script.sh` |
| Export করা variable নতুন terminal-এ নেই | Environment শুধু process ও তার child-এ | — | `~/.bashrc`-এ যোগ (interactive) বা systemd `Environment=` (service) |
| `Permission denied` (exit 126) | Execute bit নেই / noexec mount | `ls -l`, `findmnt` | `chmod +x` বা `bash script` |
| CI সবুজ, অথচ ধাপ ব্যর্থ | Pipe-এর মাঝে ব্যর্থতা | `${PIPESTATUS[@]}` | `set -o pipefail` |
| `$(ls)` loop-এ ভুল | Word splitting | — | Glob সরাসরি loop-এ |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - **Command injection:** user input unquoted বা `eval` দিয়ে shell-এ গেলে আক্রমণকারী নিজের command চালাতে পারে (`; rm -rf ~`)। কখনো `eval` untrusted input-এ নয়; Python-এ list argument।
  - Secret command line argument-এ দিলে `ps` দিয়ে অন্য user দেখতে পারে এবং history-তে যায় — environment বা file দিয়ে দিন (L00-04)।
  - `PATH`-এ `.` (current directory) কখনো রাখবেন না — অন্য কারো রাখা `ls` নামের program চলে যেতে পারে।
- **Performance:** Loop-এর ভেতরে বারবার external command (`$(date)`) ধীর; বড় কাজ Python-এ (L04-08)।
- **Cost:** একটি unquoted `rm`-এর খরচ = হারানো data।

## 14. Hands-on exercise

1. `argv_show.py` দিয়ে প্রতিটির argument সংখ্যা আগে অনুমান করুন, তারপর যাচাই: `"$@"`, `$*`, `"a"'b'c`, `a\ b c`, `"$(echo a b)"`, `$(echo a b)`।
2. একটি file তৈরি করুন যার নামে space ও newline আছে (`touch $'bad\nname'`)। `for f in $(ls)` ও `for f in *` তুলনা করুন।
3. `exit_code.py`-তে `--from-signal NAME` option যোগ করুন (যেমন `SIGTERM` → 143)। Test লিখুন।
4. `PATH`-এর শুরুতে `~/bin` যোগ করুন এবং সেখানে `python3` নামে একটি ছোট script রাখুন যা "fake!" ছাপে। `command -v python3` ও `python3` চালান। তারপর সরিয়ে ফেলুন — এই experiment কেন নিরাপত্তার দিক থেকে গুরুত্বপূর্ণ, লিখুন।
5. `set -o pipefail` ছাড়া ও সহ `grep nomatch /etc/hostname | wc -l; echo $?` তুলনা করুন।

## 15. Mini-project — safe cleanup

Section 5-এর cleanup script নিরাপদভাবে নতুন করে লিখুন (`cleanup-backups.sh`):

1. `BACKUP_DIR` environment variable থেকে, `${BACKUP_DIR:?}` দিয়ে সুরক্ষিত।
2. `--days N` (default 7) — `find "$BACKUP_DIR" -name '*.tar.gz' -mtime +N`।
3. Default **dry-run**; `--delete` দিলে তবেই মোছে (`-print0` ও `xargs -0`, L01-07)।
4. Space ও newline-যুক্ত নামে পরীক্ষা করুন (temporary directory-তে)।
5. Exit code: 0 = সফল, 2 = ভুল argument।

## 16. Interview প্রশ্ন

1. `"$var"` ও `$var`-এর পার্থক্য কী? কখন quote ছাড়া রাখবেন?
2. Single quote ও double quote-এর পার্থক্য কী?
3. Shell variable ও environment variable-এর পার্থক্য কী? `export` কী করে?
4. Exit code 127, 126, 137, 143-এর অর্থ কী?
5. `false | true`-এর exit code কত এবং কেন? কীভাবে ঠিক করবেন?
6. `cd` কেন একটি builtin?
7. Ubuntu-তে `/bin/sh` কী এবং এটি script-কে কীভাবে প্রভাবিত করে?

## 17. Self-assessment প্রশ্ন

1. Bash-এর expansion-এর ক্রম লিখুন। Word splitting কোন expansion-এর ফলে হয় না?
2. সহকারী analogy কোথায় মেলে না?
3. Section 5-এর script-এ ঠিক কোন দুটি ভুল ছিল?
4. `${DIR:?}` কীভাবে `rm -rf` দুর্ঘটনা ঠেকায়?
5. `argv_show.py *.xyz` (কোনো মিল নেই) কী পাঠায় এবং কেন?
6. Container 137 দিয়ে বন্ধ হলে প্রথম কোন সন্দেহ করবেন?

## 18. সংক্ষিপ্ত সারাংশ

- Shell command line প্রক্রিয়া করে (expansion, word splitting, glob, quote removal), তারপর program-কে **argv তালিকা** দেয়।
- **Double quote** expansion রাখে কিন্তু splitting ও glob বন্ধ করে; **single quote** সব বন্ধ করে। Variable সবসময় `"$var"`।
- **Environment variable** = `export` করা; child process পায়। `PATH` বাম থেকে ডানে।
- **Exit code:** 0 সফল; 126/127; 128+N = signal (137 SIGKILL, 143 SIGTERM)। Pipe শুধু শেষেরটি দেখায় — `pipefail`।
- `${VAR:?}`, `--`, glob loop — সস্তা কিন্তু শক্তিশালী সুরক্ষা।

## 19. Completion checklist

- [ ] `argv_show.py` দিয়ে quoting, glob, brace, tilde পরীক্ষা করেছি
- [ ] Exit code 127, 137, 143 নিজে তৈরি করে দেখেছি
- [ ] `PIPESTATUS` ও `pipefail` পরীক্ষা করেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] Exercise ১, ২ ও ৫ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash manual — Shell Expansions, Quoting, Exit Status: https://www.gnu.org/software/bash/manual/bash.html
- POSIX Shell Command Language: https://pubs.opengroup.org/onlinepubs/9799919799/utilities/V3_chap02.html
- `signal(7)`: https://man7.org/linux/man-pages/man7/signal.7.html
- Ubuntu wiki — DashAsBinSh: https://wiki.ubuntu.com/DashAsBinSh
- ShellCheck: https://www.shellcheck.net/
- Python `shlex`: https://docs.python.org/3/library/shlex.html

---

**পরের lesson:** L01-07 — Pipe, redirection, grep, sed, awk, find, xargs, jq
