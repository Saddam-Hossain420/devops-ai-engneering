# L04-02 — Variable, array ও parameter expansion

| | |
|---|---|
| **Module** | 04 — Bash and Shell Automation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L04-01 — Script-এর গঠন ও strict mode](L04-01-script-structure-strict-mode.md) |
| **Label** | — |
| **Tested** | `expansion_lab.sh` ও `rename_ext.sh`: ৭টি test পাস — string কাটা-ছাঁটা, unset বনাম খালি, quote করা বনাম না-করা array, sparse ও associative array, নিরাপদ splitting; rename-এ space, শুরুতে `-`, **নামের ভেতরে newline**, আগে থেকে থাকা target (GNU Bash 5.3.9, Windows/Git Bash)। Demo লেখার সময় নিজের একটি ভুল ধরা পড়েছে (`[@]` বনাম `[*]`) — Section 9.1। Ubuntu-তে চালানো হয়নি — আচরণ একই হওয়ার কথা (Bash 5.2)। |

---

## 1. এই lesson-এ যা শিখবেন

- Variable: assignment-এর নিয়ম, scope, `readonly`, `local`, `export`।
- **Parameter expansion** দিয়ে external command ছাড়া string কাটা-ছাঁটা: basename, dirname, extension, replace, case, substring।
- Default মান: `:-`, `:=`, `:?`, `:+` — এবং **unset বনাম খালি** পার্থক্য।
- **Indexed ও associative array**; `"${arr[@]}"` কেন সবসময় quote করবেন; sparse array।
- নিরাপদ splitting: `read -r -a`, `mapfile -t`, `find -print0` + `read -d ''`।
- `printf %q` দিয়ে নিরাপদে দেখানো।
- একটি বাস্তব script: কঠিন নামের file-ও নিরাপদে rename।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Bash-এর প্রায় সব বড় bug-এর মূলে আছে দুটি জিনিস: **variable-এর মান কীভাবে বিস্তৃত (expand) হয়**, এবং **কোথায় ভেঙে যায় (word splitting)**।

- `for f in $(ls *.log)` — space-যুক্ত file name দুই ভাগ হয়, এবং ভুল file মুছে যায়।
- `rm -rf $DIR/*` — DIR খালি থাকলে `/`।
- `basename`, `dirname`, `sed` loop-এর ভেতরে হাজার বার চালানো — প্রতিবার নতুন process, তাই ধীর script।
- Config-এর ঐচ্ছিক মান হাতে `if [ -z ... ]` দিয়ে পরীক্ষা — দীর্ঘ, ভুলপ্রবণ।

Parameter expansion এগুলোর বেশিরভাগ সমাধান করে, একটি process ছাড়াই।

## 3. সহজ ভাষায় পরিচয়

**Variable:**

```bash
name=value          # = এর দুই পাশে space নয়
name="two words"    # space থাকলে quote
readonly MAX=5      # আর বদলানো যাবে না
local tmp           # শুধু function-এর ভেতরে (L04-03)
export PATH         # child process-কে দেখায়
```

**String expansion** (`path=/var/log/nginx/access.log.2.gz`):

| Expansion | ফল | মনে রাখার উপায় |
|---|---|---|
| `${path##*/}` | `access.log.2.gz` | `#` = বাম থেকে কাটো, `##` = সবচেয়ে বেশি |
| `${path%/*}` | `/var/log/nginx` | `%` = ডান থেকে কাটো |
| `${path%.*}` | `…/access.log.2` | শেষ extension বাদ |
| `${path%%.*}` | `…/access` | সব extension বাদ |
| `${path##*.}` | `gz` | শেষ extension |
| `${path//log/LOG}` | সব `log` বদল | `/` = প্রথমটি, `//` = সব |
| `${#path}` | `30` | দৈর্ঘ্য |
| `${path:0:4}` / `${path: -5}` | `/var` / `.2.gz` | substring; ঋণাত্মকের আগে **space** |
| `${name^^}` / `${name,,}` | বড় / ছোট হাতের | Bash ৪+ |

(`#` বাম দিকে কারণ keyboard-এ `$`-এর বামে; `%` ডানে।)

**Default মান:**

| Expansion | VAR unset | VAR খালি (`""`) | VAR="x" |
|---|---|---|---|
| `${VAR:-d}` | d | d | x |
| `${VAR-d}` | d | **""** | x |
| `${VAR:=d}` | d (এবং VAR=d) | d (এবং VAR=d) | x |
| `${VAR:?msg}` | error, exit | error, exit | x |
| `${VAR:+alt}` | "" | "" | alt |

`:` থাকলে "খালি"-কেও অনুপস্থিত ধরা হয়; না থাকলে শুধু unset।

**Array:**

```bash
files=("my report.txt" "a b c.log" plain)   # indexed
"${files[@]}"     # প্রতিটি element আলাদা word — প্রায় সবসময় এটাই চাই
"${files[*]}"     # সব একটি string (IFS-এর প্রথম অক্ষর দিয়ে জোড়া)
${#files[@]}      # সংখ্যা
${!files[@]}      # index-গুলো
declare -A port=([ssh]=22 [https]=443)      # associative (Bash ৪+)
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### খাম ও চিঠি

- **Variable** = একটি খাম, যার গায়ে নাম লেখা, ভেতরে চিঠি (মান)।
- **Quote ছাড়া `$var`** = খাম খুলে চিঠির **প্রতিটি শব্দ আলাদা কাগজে** ছড়িয়ে দেওয়া, এবং `*` লেখা থাকলে ঘরের সব file-এর নাম তুলে দেওয়া।
- **`"$var"`** = খাম অক্ষত রেখে পাঠানো।
- **Array** = খামের একটি বাক্স — `"${arr[@]}"` প্রতিটি খাম আলাদা রেখে পাঠায়।
- **Parameter expansion** = কাঁচি দিয়ে চিঠির শুরু বা শেষ কেটে ফেলা — অন্য কাউকে ডাকা ছাড়াই (`basename`, `sed`-এর মতো বাইরের process নয়)।

### Analogy কোথায় মেলে না

- খাম খালি থাকলে চোখে পড়ে। Bash-এ unset ও খালি variable **একই রকম দেখায়** (`echo` দুটোতেই কিছু ছাপে না), কিন্তু `${VAR-d}` ও `${VAR:-d}`-এর কাছে ভিন্ন (Section 9.1)। `set -u` শুধু unset ধরে, খালি নয়।
- বাক্সে খামগুলো ক্রমানুসারে থাকে, ফাঁক থাকে না। Bash array **sparse** হতে পারে: `unset 'arr[1]'`-এর পরে index ০, ২, ৩ — `${#arr[@]}` = ৩, কিন্তু শেষ index ৩। `for ((i=0; i<${#arr[@]}; i++))` তখন ভুল element নেয়।
- চিঠি ছড়ানোর নিয়ম সবসময় একই। Word splitting নির্ভর করে **IFS**-এর উপর (L04-01-এর template-এ IFS বদলানো হয়েছে), এবং glob নির্ভর করে বর্তমান directory-তে কোন file আছে তার উপর — একই code ভিন্ন জায়গায় ভিন্ন ফল দেয়।

## 5. Real-world engineering scenario — "Log cleanup script অন্য file মুছে দিল"

**পরিস্থিতি:** একটি cron job পুরোনো log মুছত:

```bash
for f in $(ls /var/log/app/*.log | grep -v current); do
  rm $f
done
```

একদিন একটি application `debug output.log` নামে file তৈরি করল। Script চালাল `rm debug` ও `rm output.log`। `output.log` নামে আরেকটি গুরুত্বপূর্ণ file মুছে গেল, আর `debug` না থাকায় error হলো (কেউ দেখেনি)।

**তিনটি ভুল:**

1. `$(ls ...)` — output word splitting-এ ভাঙে।
2. `$f` quote ছাড়া।
3. `rm`-এ `--` নেই — `-rf.log` নামের file option হয়ে যেত।

**সঠিক রূপ:**

```bash
shopt -s nullglob                         # match না হলে literal "*.log" নয়, খালি
for f in /var/log/app/*.log; do           # glob সরাসরি — ls নয়
  [[ ${f##*/} == current* ]] && continue  # parameter expansion — grep নয়
  rm -- "$f"
done
# বা: find /var/log/app -maxdepth 1 -name '*.log' ! -name 'current*' -mtime +7 -delete
```

**শিক্ষা:** File name-কে "শব্দ" নয়, যেকোনো byte-এর ক্রম ধরুন (শুধু `/` ও NUL বাদে)। Glob বা `find -print0`, সবসময় quote, এবং `--`।

## 6. Diagram — expansion-এর ক্রম

```text
 command line:   rm -- $dir/*.log
        │
 ১. brace expansion          {a,b}
 ২. tilde expansion          ~ → /home/user
 ৩. parameter/variable       $dir → "/var/log/my app"    ┐ quote না থাকলে
    command substitution     $(...)                       │ এই ফলগুলো
    arithmetic               $((...))                     ┘ পরের ধাপে যায়
 ৪. word splitting (IFS)     "/var/log/my" "app/*.log"    ← quote থাকলে এই ধাপ নেই
 ৫. pathname (glob)          app/*.log → files            ← quote থাকলে এই ধাপও নেই
 ৬. quote removal
        ▼
 rm -- /var/log/my app/*.log   (দুটি ভুল argument)    বনাম    rm -- "$dir"/*.log  (সঠিক)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Parameter expansion | `${...}` দিয়ে variable-এর মান রূপান্তর |
| Word splitting | Unquoted ফল IFS অনুযায়ী ভাগ |
| Globbing / pathname expansion | `*`, `?`, `[...]` থেকে file name |
| `nullglob` | Match না হলে খালি (literal pattern নয়) |
| Indexed / associative array | সংখ্যা / string key-যুক্ত array |
| Sparse array | মাঝে মাঝে index অনুপস্থিত |
| Indirect expansion | `${!ref}` — যে variable-এর নাম ref-এ |
| `mapfile` / `readarray` | লাইন-প্রতি array element |
| Process substitution | `<(cmd)` — command-এর output file হিসেবে |
| `printf %q` | Shell-এ পুনরায় ব্যবহারযোগ্য quote-সহ রূপ |
| `--` | "এরপর আর কোনো option নয়" |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 কেন parameter expansion দ্রুত

`basename "$f"` প্রতিবার একটি নতুন process (fork + exec)। `${f##*/}` Bash-এর ভেতরেই হয়। ১০,০০০ file-এর loop-এ পার্থক্য সেকেন্ড বনাম মিলিসেকেন্ড (Exercise ৪-এ মেপে দেখুন)। একই কারণে `$(echo "$x" | tr a-z A-Z)`-এর বদলে `${x^^}` ব্যবহার করুন।

### 8.2 Array-ই আসল নিরাপদ list

Command-এর argument জমাতে string নয়, array ব্যবহার করুন:

```bash
args=(--archive --verbose)
[[ -n $EXCLUDE ]] && args+=(--exclude "$EXCLUDE")    # space-যুক্ত pattern অক্ষত
rsync "${args[@]}" "$src" "$dst"
```

String-এ জমালে (`args="--exclude $EXCLUDE"`) quote হারিয়ে যায়। `eval` দিয়ে "সমাধান" করলে injection-এর ঝুঁকি তৈরি হয়।

### 8.3 Line পড়ার সঠিক উপায়

```bash
while IFS= read -r line; do ...; done < file        # IFS= : শুরু/শেষের space রাখে; -r : backslash অক্ষত
mapfile -t lines < file                             # পুরো file array-তে
while IFS= read -r -d '' f; do ...; done < <(find . -type f -print0)   # নামে newline থাকলেও
```

`cat file | while read ...` লিখলে loop একটি subshell-এ চলে, তাই loop-এর ভেতরে বদলানো variable বাইরে হারিয়ে যায়। `done < <(...)` (process substitution) এই সমস্যা এড়ায়।

### 8.4 Associative array-এর ক্রম

Key-এর ক্রম নিশ্চিত নয়। স্থির output চাইলে sort করুন (Section 9.1-এ `keys, sorted`)।

## 9. Practical demonstration

### 9.1 Expansion lab

File: [`code/L04-02/expansion_lab.sh`](code/L04-02/expansion_lab.sh)

```bash
cd ~/devops-ai-engineering/04-bash-and-shell-automation/code/L04-02
bash expansion_lab.sh
```

**আসল output (GNU Bash 5.3.9):**

```text
== string: path=/var/log/nginx/access.log.2.gz
${#path}                           → [30]
${path##*/}   (basename)           → [access.log.2.gz]
${path%/*}    (dirname)            → [/var/log/nginx]
${path#*.}    (shortest)           → [log.2.gz]
${path##*.}   (last ext)           → [gz]
${path%.*}    (drop ext)           → [/var/log/nginx/access.log.2]
${path%%.*}   (drop all)           → [/var/log/nginx/access]
${path/log/LOG}  (first)           → [/var/LOG/nginx/access.log.2.gz]
${path//log/LOG} (all)             → [/var/LOG/nginx/access.LOG.2.gz]
${path:0:4}                        → [/var]
${path: -5}  (space!)              → [.2.gz]
== case: name=ubuntu-Server
${name^^}                          → [UBUNTU-SERVER]
${name,,}                          → [ubuntu-server]
${name^}                           → [Ubuntu-Server]
== unset vs empty: unset UNSET; EMPTY=''
${UNSET:-default}                  → [default]
${EMPTY:-default}                  → [default]
${EMPTY-default}  (no :)           → []
${EMPTY:+alt}                      → []
${SET:+alt}                        → [alt]
${ASSIGNED:=...} then $ASSIGNED    → [from-default]
${UNSET:?is required}              → [error, exit 1]
${!ref}  (indirect)                → [ubuntu-Server]
== arrays
${#files[@]}                       → [3]
for f in "${files[@]}" (count)     → [3]
for f in ${files[@]}  (count)      → [6]
"${files[*]}"                      → [my report.txt a b c.log plain]
${files[@]:1:1}                    → [a b c.log]
after += and unset [1]: ${!files[*]} → [0 2 3]
${#files[@]}                       → [3]
${port[https]}                     → [443]
keys, sorted                       → [https postgres ssh ]
${port[missing]:-none}             → [none]
== splitting safely
IFS=, read -r -a fields            → [10.0.1.5]
mapfile -t lines ; ${lines[1]}     → [two words]
printf %q "it's a $test"           → [it\'s\ a\ \$test]
```

**লক্ষ্য করুন:**

- তিনটি নামের array quote ছাড়া loop-এ **৬**টি "file" হয়ে গেছে।
- `${EMPTY-default}` খালি থেকে গেছে (`:` নেই, আর EMPTY set আছে)।
- `unset`-এর পরে index `0 2 3` — sparse।

**Demo লেখার সময় নিজের ভুল:** প্রথম সংস্করণে index দেখাতে `"${!files[@]}"` দিয়েছিলাম। এটা তিনটি আলাদা argument হিসেবে `show()`-এ যায়, এবং function শুধু দ্বিতীয় argument ছাপে — ফলে output-এ এসেছিল শুধু `[0]`। ঠিক করা হয়েছে `"${!files[*]}"` দিয়ে। এই lesson-এর মূল বিষয়টিই (`[@]` = আলাদা word, `[*]` = এক string) লেখকের নিজের code-এ ধরা পড়ল।

### 9.2 নিরাপদ rename

File: [`code/L04-02/rename_ext.sh`](code/L04-02/rename_ext.sh)

```bash
T=$(mktemp -d)
touch "$T/my photo.jpeg" "$T/-dash.jpeg" "$T/plain.jpeg" "$T/keep.png" "$T/clash.jpeg" "$T/clash.jpg"
touch "$T/$(printf 'new\nline.jpeg')"
bash rename_ext.sh -n "$T" jpeg jpg; echo "exit=$?"
bash rename_ext.sh "$T" .jpeg .jpg; echo "exit=$?"
ls -1 "$T" | cat -A
```

**আসল output:**

```text
would rename: -dash.jpeg -> -dash.jpg
skip (target exists): clash.jpeg
would rename: my\ photo.jpeg -> my\ photo.jpg
would rename: $'new\nline.jpeg' -> $'new\nline.jpg'
would rename: plain.jpeg -> plain.jpg
4 would be renamed, 1 skipped
exit=1
renamed: -dash.jpeg -> -dash.jpg
skip (target exists): clash.jpeg
renamed: my\ photo.jpeg -> my\ photo.jpg
renamed: $'new\nline.jpeg' -> $'new\nline.jpg'
renamed: plain.jpeg -> plain.jpg
4 renamed, 1 skipped
exit=1
-dash.jpg$
clash.jpeg$
clash.jpg$
keep.png$
my photo.jpg$
new$
line.jpg$
plain.jpg$
```

- নামের ভেতরে newline থাকা file-ও সঠিকভাবে rename হয়েছে (`ls`-এর output-এ দুই লাইনে দেখায়, কিন্তু একটিই file)। `printf %q` সেটা দ্ব্যর্থহীনভাবে `$'new\nline.jpeg'` হিসেবে দেখায়।
- `-dash.jpeg` option হিসেবে ভুল পড়া হয়নি (`mv --`)।
- `clash.jpg` আগে থেকে থাকায় skip করা হয়েছে, এবং exit ১ — calling script জানতে পারে যে কাজ পুরো হয়নি।

### 9.3 Test

```bash
python3 -m unittest -v
```

[`test_l04_02.py`](code/L04-02/test_l04_02.py)-এর ৭টি test:

- **Expansion:** string কাটা, unset বনাম খালি, `:?`, quote-সহ ও quote-ছাড়া array, sparse array, associative array ও splitting।
- **Rename:** dry-run-এ কিছু বদলায় না; আসল rename-এ কঠিন নাম সামলানো ও overwrite না করা; usage error।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `from=${2#.}` | শুরুর `.` বাদ | `jpeg` ও `.jpeg` দুটোই গ্রহণ |
| Extension whitelist regex | শুধু অক্ষর ও সংখ্যা | `*` বা `/`-যুক্ত input-এ glob বা path traversal নয় |
| `find -maxdepth 1 -print0 \| sort -z` | NUL-বিভক্ত, ক্রমানুসারে | যেকোনো নাম নিরাপদ; output স্থির |
| `while IFS= read -r -d ''` | NUL পর্যন্ত পড়া | `-print0`-এর জোড়া |
| `done < <(...)` | Process substitution | Loop main shell-এ — counter হারায় না |
| `${src%.*}.$to` | Extension বদল | Process ছাড়া |
| `[[ -e $dst ]]` + `mv -n` | আগে পরীক্ষা, তারপর no-clobber | দুই স্তরের সুরক্ষা (পরীক্ষা ও mv-এর মাঝে race) |
| শেষ লাইন `(( skipped == 0 ))` | Exit code-ই ফল | Caller বুঝবে সব হয়েছে কিনা |

**Bash কেন এখানে, কোথায় নয়:** file-এর উপর কাজ ও command জোড়া দেওয়ায় Bash স্বাভাবিক। Nested data (JSON/YAML) বা জটিল নিয়ম লাগলে Python (`pathlib`) পরিষ্কার এবং test করা সহজ (L04-08)।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `bash expansion_lab.sh` | Section 9.1-এর table |
| `rename_ext.sh -n` | কিছু বদলায় না, exit ১ (conflict থাকলে) |
| Rename-এর পরে `clash.jpg`-এর content | আগের মতোই (overwrite হয়নি) |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom / ভুল | কারণ | সঠিক পদ্ধতি |
|---|---|---|
| `for f in $(ls)` space-যুক্ত নামে ভাঙে | Word splitting | Glob বা `find -print0` |
| Glob কিছু না মিললে `*.log` নামে literal | Default আচরণ | `shopt -s nullglob` বা `[[ -e $f ]] \|\| continue` |
| `${var: -3}` কাজ করে না | Space ছাড়া `:-` (default) হয়ে যায় | `${var: -3}` বা `${var:(-3)}` |
| Loop-এর ভেতরের variable বাইরে হারায় | `cmd \| while` subshell | `done < <(cmd)` |
| Array থেকে command-এ quote হারায় | String-এ জমানো | Array + `"${arr[@]}"` |
| `declare -A` error | Bash ৩ (macOS-এর পুরোনো default) | Bash ৪+; Ubuntu ও Fedora-তে সমস্যা নেই |
| `set -u`-এ খালি array error | Bash ৪.৪-এর আগে | Bash ৪.৪+; বা `${arr[@]+"${arr[@]}"}` |
| `read` backslash হারায় | `-r` নেই | সবসময় `read -r` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Unquoted variable = glob ও splitting injection।
  - `--` না দিলে `-`-যুক্ত নাম option হয়ে যায় (`rm -rf` বসানো যায়)।
  - `eval`-এ user input কখনো নয় — array ব্যবহার করুন।
  - Log বা message-এ user-নিয়ন্ত্রিত নাম দেখাতে `printf %q` ব্যবহার করুন (terminal escape sequence ও newline লুকায় না)।
- **Performance:**
  - Parameter expansion বনাম external command: process তৈরির খরচ এড়ায়।
  - বড় file-এ Bash loop-এর বদলে একবার `awk` বা Python।
- **Cost:**
  - ভুল file মুছে যাওয়ার খরচ (Section 5) অনেক বড়।
  - Dry-run ও "no overwrite" default সস্তা বীমা।

## 14. Hands-on exercise

1. `path=/srv/app/releases/2026-10-27_1530/app.tar.gz` থেকে শুধু parameter expansion দিয়ে বের করুন: release-এর তারিখ (`2026-10-27`), সময় (`1530`), এবং `.tar.gz` ছাড়া file-এর নাম।
2. একটি function লিখুন, যা associative array থেকে `KEY=VALUE` আকারের `.env`-ধাঁচের file লেখে — key ক্রমানুসারে, এবং value `printf %q` দিয়ে।
3. `rename_ext.sh`-এ `-r` (recursive) option যোগ করুন এবং Python test লিখুন। Symlink-এর ক্ষেত্রে কী করবেন, সিদ্ধান্ত নিন।
4. ১০,০০০টি path-এ `basename` বনাম `${f##*/}`-এর সময় `time` দিয়ে মাপুন (L00-06-এর পদ্ধতিতে ৩ বার)।
5. Section 5-এর ভুল script একটি temporary directory-তে (কাল্পনিক file দিয়ে) চালিয়ে ক্ষতি দেখুন, তারপর সঠিক রূপ চালান।

## 15. Mini-project — Log archiver (প্রথম অংশ)

একটি `archive_logs.sh DIR DAYS` লিখুন:

- `find -print0` দিয়ে DAYS-এর পুরোনো `*.log` খুঁজবে।
- নাম থেকে তারিখ বের করে (parameter expansion) `archive/YYYY-MM/`-এ সরাবে।
- Array-তে জমিয়ে শেষে একবারে `tar` করবে।
- Dry-run default থাকবে।

L04-05 ও L04-06-এ এতে option parsing, locking ও atomic লেখা যোগ হবে।

## 16. Interview প্রশ্ন

1. `"$@"`, `"$*"`, `$@` ও `$*`-এর পার্থক্য।
2. `${var:-x}` ও `${var-x}`-এর পার্থক্য কী?
3. External command ছাড়া একটি path থেকে basename ও extension কীভাবে বের করবেন?
4. `for f in $(ls)` কেন ভুল? সঠিক বিকল্প কী?
5. Command-এর argument dynamic-ভাবে কীভাবে তৈরি করবেন?
6. `cmd | while read` loop-এর ভেতরে বদলানো variable বাইরে কেন পাওয়া যায় না?

## 17. Self-assessment প্রশ্ন

1. খাম analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর তিনটি ভুল কী কী?
3. Section 9.1-এর demo-তে লেখকের ভুল কী ছিল?
4. `rename_ext.sh` কোন দুই স্তরে overwrite আটকায়?
5. Sparse array-তে `for ((i=0; i<${#arr[@]}; i++))` কেন ভুল?

## 18. সংক্ষিপ্ত সারাংশ

- Quote করুন: `"$var"`, `"${arr[@]}"` — splitting ও glob বন্ধ।
- `#`/`##` বাম থেকে, `%`/`%%` ডান থেকে কাটে; `/`/`//` replace; `^^`/`,,` case — process ছাড়া।
- `:-` খালি ও unset দুটোই ধরে, `-` শুধু unset; `:?` প্রয়োজনীয় মান নিশ্চিত করে।
- Argument জমাতে array; file-এর তালিকায় glob বা `find -print0` + `read -d ''`।
- `--` ও `printf %q` — অদ্ভুত নামের বিরুদ্ধে সুরক্ষা।

## 19. Completion checklist

- [ ] Expansion lab-এর প্রতিটি সারি ব্যাখ্যা করতে পারি
- [ ] কঠিন নামের file দিয়ে `rename_ext.sh` চালিয়েছি
- [ ] Exercise ৪-এ process-এর খরচ মেপেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash Reference Manual — Shell Parameter Expansion: https://www.gnu.org/software/bash/manual/html_node/Shell-Parameter-Expansion.html
- GNU Bash Reference Manual — Arrays: https://www.gnu.org/software/bash/manual/html_node/Arrays.html
- GNU Bash Reference Manual — Shell Expansions: https://www.gnu.org/software/bash/manual/html_node/Shell-Expansions.html
- BashFAQ/001 — How can I read a file line-by-line?: https://mywiki.wooledge.org/BashFAQ/001
- BashPitfalls: https://mywiki.wooledge.org/BashPitfalls

---

**পরের lesson:** L04-03 — Function ও reusable script
