# L01-07 — Pipe, redirection, grep, sed, awk, find, xargs, jq

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা |
| **পূর্বশর্ত** | [L01-06 — Shell fundamentals](L01-06-shell-fundamentals.md) |
| **Label** | — |
| **Tested** | `access_report.py`: ৪টি test পাস, যার একটি **আসল shell pipeline চালিয়ে Python-এর ফলের সাথে মিলিয়েছে**। Section 9-এর `awk`/`sort`/`uniq`/`grep`/`sed`/`find`/`xargs` output GNU tool-এ (Git Bash, Windows) চালিয়ে পাওয়া আসল ফল। `jq` installed ছিল না — jq-এর প্রত্যাশিত ফল Python দিয়ে একই data-য় হিসাব করে দেখানো; jq নিজে চালানো হয়নি। `access.log` ও `events.json` script দিয়ে তৈরি নমুনা data। |

---

## 1. এই lesson-এ যা শিখবেন

- **stdin, stdout, stderr** ও **redirection** (`>`, `>>`, `2>`, `2>&1`, `<`)।
- **Pipe** (`|`) — Unix দর্শন: ছোট tool, একটি কাজ, একসাথে জোড়া।
- **grep** (খোঁজা), **sed** (stream সম্পাদনা), **awk** (column ও হিসাব), **sort/uniq/wc/cut/head/tail**।
- **find** ও **xargs** — নিরাপদভাবে (`-print0`, `-0`, `-exec +`)।
- **jq** — JSON-এর জন্য।
- একটি Nginx access log বিশ্লেষণ: shell one-liner বনাম Python — এবং দুটোর ফল মিলিয়ে দেখা।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

রাত ২টায় incident: "API ধীর, কিছু user 500 পাচ্ছে।" আপনার কাছে ২ GB-র access log। প্রশ্ন:

- কোন IP সবচেয়ে বেশি request করছে? (আক্রমণ?)
- কোন endpoint 500 দিচ্ছে?
- কোন request সবচেয়ে ধীর?

Program লিখতে বসার সময় নেই, আর server-এ হয়তো Python-ও নেই। Text tool দিয়ে কয়েক সেকেন্ডে উত্তর বের করা DevOps/SRE-র মৌলিক দক্ষতা। আবার যখন বিশ্লেষণ জটিল হয় বা বারবার করতে হয় — তখন Python-এ যাওয়া সঠিক। এই lesson দুটোই শেখায় এবং কখন কোনটি তা দেখায়।

## 3. সহজ ভাষায় পরিচয়

**তিনটি standard stream:** প্রতিটি process জন্ম থেকে তিনটি খোলা file descriptor পায় (L01-01):

| fd | নাম | default |
|---|---|---|
| 0 | stdin (input) | keyboard |
| 1 | stdout (স্বাভাবিক output) | screen |
| 2 | stderr (error ও diagnostic) | screen |

**Redirection** এই প্রবাহ file-এ পাঠায়; **pipe** একটি program-এর stdout সরাসরি পরেরটির stdin-এ জোড়ে।

**Unix দর্শন:** প্রতিটি tool একটি কাজ ভালোভাবে করে; text হলো সবার সাধারণ ভাষা; tool-গুলো জুড়ে বড় কাজ।

| Tool | এক কথায় |
|---|---|
| `grep` | যে লাইনে pattern আছে তা দেখাও |
| `sed` | প্রতিটি লাইনে খুঁজে-বদলাও (stream editor) |
| `awk` | লাইনকে column-এ ভাগ করে শর্ত ও হিসাব |
| `sort` / `uniq -c` | সাজাও / পরপর একই লাইন গোনো |
| `cut`, `head`, `tail`, `wc` | column কাটো, শুরু, শেষ, গোনো |
| `find` | শর্ত অনুযায়ী file খোঁজো |
| `xargs` | stdin-এর লাইনকে অন্য command-এর argument বানাও |
| `jq` | JSON থেকে field বের করো, filter ও রূপান্তর |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### কারখানার conveyor belt

প্রতিটি tool একজন কর্মী: প্রথমজন বাক্স থেকে শুধু লাল জিনিস বাছেন (`grep`), দ্বিতীয়জন প্রতিটির লেবেল বদলান (`sed`), তৃতীয়জন ওজন মাপেন (`awk`), চতুর্থজন সাজান (`sort`), শেষজন গোনেন (`uniq -c`)। Belt-টি **pipe**। প্রত্যেকে আগের জনের কাজ শেষ হওয়ার অপেক্ষা না করে **একসাথে** কাজ করেন।

### Analogy কোথায় মেলে না

- Belt-এ একজন কর্মী থেমে গেলে সবাই দেখে। Pipe-এ মাঝের একটি command ব্যর্থ হলে shell **নীরবে** এগিয়ে যায় — exit code শুধু শেষেরটির (L01-06, `pipefail`)।
- Belt-এর জিনিস বস্তু। Pipe-এ **byte-এর প্রবাহ** — "লাইন" বা "column"-এর ধারণা প্রতিটি tool নিজে তৈরি করে। তাই একটি log-এর field-এ অপ্রত্যাশিত space থাকলে `awk`-এর column গুনতি সরে যায় (Section 8.3)।
- `sort`-এর মতো কর্মী সব জিনিস না পাওয়া পর্যন্ত কিছু পাঠাতে পারেন না — তাই বিশাল input-এ memory ও disk (temporary file) লাগে।

## 5. Real-world engineering scenario — "কিছু user 500 পাচ্ছে"

**পরিস্থিতি:** TaskFlow API-র সামনে Nginx। Alert: 5xx error বেড়েছে। Log: `/var/log/nginx/access.log`।

**Diagnosis পথ (এই lesson-এর নমুনা log-এ আসলে চালানো):**

1. Status code বণ্টন: `200=265  404=27  500=8` → ৫০০ আছে, তবে কম (2.7%)।
2. কোন path 500 দেয়?
   ```bash
   awk '$9 >= 500 {print $7}' access.log | sort | uniq -c | sort -rn
   ```
   → সব `/api/export`।
3. ধীর request কোনগুলো? → `/api/export` ৮টি, সবই ≥ ১ সেকেন্ড।
4. **Hypothesis (L00-06):** export endpoint-এ ধীর query, timeout হয়ে 500।
5. বাড়তি পর্যবেক্ষণ: top 404 path `/wp-login.php` (২২টি) — এটি TaskFlow-এ নেই; একটি IP (`192.0.2.99`) WordPress login খুঁজছে → **bot/scanner**, incident-এর কারণ নয়, তবে security note (rate limit, Module 06)।

**শিক্ষা:** তিন-চারটি one-liner দিয়ে symptom থেকে নির্দিষ্ট endpoint পর্যন্ত পৌঁছানো গেল — এবং noise (bot) আলাদা করা গেল।

## 6. Diagram

### Pipe ও stream

```text
  awk '{print $1}' access.log  │  sort  │  uniq -c  │  sort -rn  │  head -3
        fd1 ──────────────────►│ fd0 fd1 ►│ fd0 fd1 ──►│ fd0 fd1 ───►│ fd0 fd1 ──► screen
        fd2 ─────────────────────────────────────────────────────────────────────► screen (error)

  প্রতিটি "│" = kernel-এর pipe buffer; সব process একসাথে চলে।
  head -3 তিন লাইন পেয়ে বন্ধ হলে আগেরটি SIGPIPE পায় (L01-06: exit 141 = 128+13)।
```

### Redirection

```text
 cmd  > out.txt        stdout → file (আগের বিষয়বস্তু মুছে)
 cmd >> out.txt        stdout → file-এর শেষে যোগ
 cmd 2> err.txt        stderr → file
 cmd  > all.txt 2>&1   stdout file-এ, তারপর stderr-কে stdout যেখানে সেখানে  (ক্রম গুরুত্বপূর্ণ!)
 cmd 2>&1 > out.txt    ⚠️ stderr এখনো screen-এ — কারণ 2>&1 হয়েছে stdout বদলানোর আগে
 cmd  < in.txt         file → stdin
 cmd 2>/dev/null       error ফেলে দাও (সাবধানে — সমস্যা লুকাতে পারে)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| stdin/stdout/stderr | Process-এর তিনটি default stream (fd 0/1/2) |
| Redirection | Stream-কে file বা অন্য fd-তে পাঠানো |
| Pipe | একটি process-এর stdout থেকে পরেরটির stdin-এ সংযোগ |
| Filter | stdin পড়ে রূপান্তর করে stdout-এ লেখা program |
| Regular expression (regex) | Text-এর pattern বর্ণনার ভাষা |
| BRE / ERE | Basic / Extended regex (`grep` / `grep -E`, `sed` / `sed -E`) |
| Field | awk-এ লাইনের একটি column (`$1`, `$2`, `$NF` = শেষ) |
| NUL-delimited | নাম আলাদা করতে `\0` byte ব্যবহার — file নামে এটি থাকতে পারে না, তাই নিরাপদ |
| `/dev/null` | যা লেখা হয় তা হারিয়ে যায় — "black hole" |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Pipe কী

Shell `pipe()` system call দিয়ে kernel-এ একটি buffer তৈরি করে (Linux-এ সাধারণত ৬৪ KiB), তারপর দুটি process-এর stdout ও stdin সেখানে জোড়ে। Buffer ভরে গেলে লেখক অপেক্ষা করে; খালি হলে পাঠক অপেক্ষা করে — স্বয়ংক্রিয় flow control। কোনো temporary file লাগে না।

### 8.2 grep, sed, awk-এর মূল ব্যবহার

```bash
grep -n "ERROR" app.log          # -n লাইন নম্বর
grep -i "timeout" app.log        # case-insensitive
grep -v "health" access.log      # মেলে না এমন লাইন
grep -c " 500 " access.log       # গণনা
grep -rE "password|secret" ./    # recursive, ERE (| = অথবা)
grep -o '"GET [^ ]*' access.log  # শুধু মেলা অংশ

sed 's/old/new/'      file       # প্রতিটি লাইনে প্রথম মিল বদলাও (output-এ; file অপরিবর্তিত)
sed 's/old/new/g'     file       # সব মিল
sed -n '10,20p'       file       # শুধু ১০–২০ লাইন
sed -i.bak 's/a/b/'   file       # ⚠️ file-এর ভেতরেই বদলাও, আগে file.bak backup

awk '{print $1, $9}'         access.log   # column ১ ও ৯
awk '$9 >= 500'              access.log   # শর্ত: status ≥ 500
awk '{s += $10} END {print s}' access.log # যোগফল
awk -F: '{print $1}' /etc/passwd          # -F = field separator
```

### 8.3 Combined log format-এ awk-এর column

```text
203.0.113.10 - - [26/Oct/2026:09:00:00 +0000] "GET /tasks/42 HTTP/1.1" 200 8585 "-" "Mozilla/5.0 (X11; Linux x86_64)" 0.052
$1           $2 $3 $4                    $5    $6   $7        $8        $9  $10  $11 $12 ...                            $NF
```

awk space দিয়ে ভাগ করে — তাই `[26/Oct/2026:09:00:00` ও `+0000]` আলাদা, `"GET` (quote সহ) `$6`। User-agent-এ space আছে বলে তার পরের column-এর নম্বর অনির্দিষ্ট — তাই request time-এর জন্য `$NF` (শেষ field)। **এই ভঙ্গুরতাই** কারণ যে জটিল log-এ Python + regex (বা Nginx-এ JSON log, Module 17) বেশি নির্ভরযোগ্য।

### 8.4 find ও xargs — নিরাপদভাবে

```bash
find /var/log -name '*.gz' -mtime +30 -size +1M      # ৩০ দিনের পুরোনো, ১ MB-এর বড়
find . -type f -perm -o+w                              # world-writable (L01-04)
find . -name '*.log' -print0 | xargs -0 gzip           # NUL-delimited: space/newline নিরাপদ
find . -name '*.log' -exec gzip {} +                   # xargs ছাড়াই, সমান নিরাপদ
```

`find ... | xargs cmd` (NUL ছাড়া) space-যুক্ত নামে ভাঙে — Section 9.4-এ আসল প্রমাণ।

⚠️ `find ... -delete` বা `xargs rm` চালানোর আগে সবসময় একই command `-print` দিয়ে চালিয়ে তালিকা দেখুন।

### 8.5 jq

```bash
jq '.[] | select(.level == "error") | .id' events.json
jq '[.[] | select(.level == "error")] | length' events.json
jq 'group_by(.service) | map({service: .[0].service, avg: (map(.latency_ms) | add / length)})' events.json
curl -s https://api.example.com/items | jq -r '.items[].name'   # -r = quote ছাড়া raw string
```

`jq` Kubernetes (`kubectl ... -o json | jq`), cloud CLI (`aws ... | jq`) ও API-র সাথে দৈনন্দিন tool।

## 9. Practical demonstration

### 9.1 Redirection ও stderr

```bash
ls /etc /nonexistent > out.txt 2> err.txt
cat out.txt | head -3
cat err.txt                      # ls: cannot access '/nonexistent': ...
ls /etc /nonexistent > all.txt 2>&1
wc -l all.txt
rm out.txt err.txt all.txt
```

### 9.2 Log বিশ্লেষণ — shell one-liner

Data: [`code/L01-07/access.log`](code/L01-07/access.log) (৩০০ লাইনের নমুনা, Nginx combined format + request time)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-07

awk '{print $1}' access.log | sort | uniq -c | sort -rn | head -3     # top IP
awk '{print $9}' access.log | sort | uniq -c                          # status বণ্টন
awk '$9 == 404 {print $7}' access.log | sort | uniq -c | sort -rn | head -3
awk '$NF >= 1.0 {print $7}' access.log | sort | uniq -c | sort -rn   # ধীর path
grep -c '" 5[0-9][0-9] ' access.log                                   # 5xx সংখ্যা
awk '{s += $10} END {print s}' access.log                              # মোট byte
```

**আসল output (GNU awk/sort/uniq/grep-এ চালানো):**

```text
     93 203.0.113.10
     67 203.0.113.25
     60 192.0.2.150

    265 200
     27 404
      8 500

     22 /wp-login.php
      5 /tasks/999

      8 /api/export

8

1194496
```

`sort | uniq -c`-এ `sort` আগে কেন? `uniq` শুধু **পরপর** একই লাইন গোনে — না সাজালে ভুল গণনা।

**sed দিয়ে IP-র শেষ অংশ লুকানো** (log শেয়ারের আগে privacy):

```bash
sed -E 's/^([0-9]+\.[0-9]+\.[0-9]+)\.[0-9]+/\1.xxx/' access.log | head -2
```

```text
203.0.113.xxx - - [26/Oct/2026:09:00:00 +0000] "GET /tasks/42 HTTP/1.1" 200 8585 "-" "Mozilla/5.0 (X11; Linux x86_64)" 0.052
192.0.2.xxx - - [26/Oct/2026:09:00:12 +0000] "GET /static/app.js HTTP/1.1" 200 7091 "-" "python-requests/2.32" 0.063
```

`-E` = extended regex; `( )` = group; `\1` = প্রথম group-এর মিল।

### 9.3 একই কাজ Python-এ

File: [`code/L01-07/access_report.py`](code/L01-07/access_report.py)

```bash
python3 access_report.py access.log --top 3
```

**আসল output:**

```text
requests: 300  (unparsable: 0)  bytes sent: 1194496
status codes: 200=265  404=27  500=8
5xx error rate: 2.7%
top client IPs:
     93  203.0.113.10
     67  203.0.113.25
     60  192.0.2.150
top 404 paths:
     22  /wp-login.php
      5  /tasks/999
slow paths (>= 1s):
      8  /api/export
```

**ছয়টি প্রশ্নের প্রতিটিতে shell ও Python-এর উত্তর হুবহু মিলেছে।** দুই পদ্ধতিতে একই ফল = উত্তরে আস্থা (L00-06-এর measurement নীতি)। Test-এর একটি অংশ ঠিক এই তুলনা স্বয়ংক্রিয়ভাবে করে।

**কখন কোনটি:**

| পরিস্থিতি | ভালো পছন্দ |
|---|---|
| Incident-এ এককালীন প্রশ্ন, server-এ | Shell one-liner |
| Log format জটিল (quote, space-যুক্ত field) | Python + regex / JSON log |
| একাধিক metric একসাথে, বারবার চালানো, test দরকার | Python |
| খুব বড় file, সাধারণ field | awk (দ্রুত, কম memory) |
| পরে অন্য কেউ রক্ষণাবেক্ষণ করবে | Python (পাঠযোগ্য, testable) |

### 9.4 find + xargs — ভাঙা ও নিরাপদ (temporary directory-তে)

```bash
cd "$(mktemp -d)"
touch "a.log" "b c.log" "keep.txt"
find . -name '*.log' | xargs ls           # ⚠️ ভাঙে
find . -name '*.log' -print0 | xargs -0 ls
find . -name '*.log' -exec ls {} +
```

**আসল output:**

```text
ls: cannot access './b': No such file or directory
ls: cannot access 'c.log': No such file or directory
./a.log

./a.log
./b c.log

./a.log
./b c.log
```

প্রথমটিতে `b c.log` দুই টুকরো হয়ে গেছে — এখানে `ls` বলে ক্ষতি নেই, কিন্তু `rm` হলে ভুল file মুছতে পারত।

### 9.5 jq (Ubuntu-তে install করে)

```bash
sudo apt install -y jq          # Fedora-তে: sudo dnf install -y jq
jq '[.[] | select(.level == "error")] | length' events.json
jq '[.[] | select(.level == "error") | .id]' events.json
```

Data: [`events.json`](code/L01-07/events.json)। এই repository লেখার machine-এ jq ছিল না; একই data-য় **Python দিয়ে হিসাব করা প্রত্যাশিত ফল:** error event ২টি, ID `[2, 9]`; service-ভিত্তিক গড় latency: api 448.6, db 535.1, worker 398.0 ms। আপনার jq output এর সাথে মেলান — না মিললে query বা data আবার দেখুন।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_access_report.py`](code/L01-07/test_access_report.py)-এর ৪টি test: একটি লাইন parse, `-` size ও request time ছাড়া লাইন, নমুনা log-এর সব metric, এবং **আসল `awk | sort | uniq -c` pipeline চালিয়ে Python-এর top IP-র সাথে তুলনা** (bash/awk না থাকলে skip)।

এই test লিখতে গিয়ে একটি platform সমস্যা ধরা পড়েছিল: Windows-এ `subprocess.run(["bash", ...])` System32-এর WSL `bash.exe` চালায়, Git Bash নয়। সমাধান: `shutil.which("bash")`-এর পূর্ণ path। Linux-এ এই সমস্যা নেই, তবে পূর্ণ path ব্যবহার সবসময় বেশি পূর্বানুমেয়।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `LINE_RE` named group | ip, time, method, path, status, size, agent, rt | Quote-এর ভেতরের space সঠিকভাবে সামলায় — awk-এর column সমস্যা নেই |
| `(?: (?P<rt>[\d.]+))?` | Request time ঐচ্ছিক | Default combined format-এ এটি নেই |
| `size == "-"` → 0 | Nginx body না থাকলে `-` লেখে | int রূপান্তরে crash এড়ায় |
| `Counter.most_common(n)` | `sort \| uniq -c \| sort -rn \| head` | এক লাইনে একই কাজ |
| `skipped` গণনা | Parse-অযোগ্য লাইন report | নীরবে data বাদ দেওয়া গোপন হয় না |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| top IP one-liner | `93 203.0.113.10` প্রথমে |
| `grep -c '" 5[0-9][0-9] '` | 8 |
| `find ... \| xargs ls` space-যুক্ত নামে | error |
| `-print0 \| xargs -0` | সঠিক |
| `python3 -m unittest -v` | `Ran 4 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `uniq -c` ভুল গণনা | আগে `sort` নেই | — | `sort \| uniq -c` |
| `> file` দিয়ে file খালি হয়ে গেল | একই file পড়া ও লেখা: `sort f > f` | — | অন্য file-এ লিখে `mv`; বা `sort -o f f` |
| Error message file-এ যায়নি | `2>&1`-এর ক্রম ভুল | — | `> file 2>&1` |
| awk-এর column সরে গেছে | Field-এ space | কয়েকটি লাইনে `awk '{print NF}'` | `$NF` বা Python/regex বা JSON log |
| `sed -i` Fedora/Ubuntu-তে চলে, macOS-এ না | GNU বনাম BSD sed | — | এই repository Linux-কেন্দ্রিক; portable script-এ সাবধান |
| Regex মেলে না | BRE-তে `+`, `\|` বিশেষ নয় | `grep -E` দিয়ে চেষ্টা | `-E` ব্যবহার করুন |
| `grep` বিশাল log-এ ধীর | — | — | `LC_ALL=C grep` (byte-ভিত্তিক তুলনা দ্রুত), বা নির্দিষ্ট সময়ের অংশে সীমিত করুন |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Log-এ personal data (IP, email, token in URL) থাকে — শেয়ারের আগে `sed` দিয়ে mask।
  - `grep -r password` দিয়ে নিজের repository-তে ভুলে রাখা secret খোঁজা ভালো অভ্যাস (Module 19-এ secret scanner)।
  - `xargs rm`/`find -delete` আগে `-print` দিয়ে যাচাই।
- **Performance:** Pipe-এর সব stage parallel চলে; `sort` বড় input-এ temporary file ব্যবহার করে (`-S` দিয়ে memory, `-T` দিয়ে directory)। `zcat`/`zgrep` দিয়ে compressed log না খুলেই খোঁজা।
- **Cost:** Cloud log service-এ query প্রতি খরচ হতে পারে; local filtering আগে করলে কম data পাঠাতে হয়।

## 14. Hands-on exercise

1. `access.log` থেকে: প্রতি মিনিটে কতগুলো request (`awk '{print substr($4, 14, 5)}' | sort | uniq -c`)। কোন মিনিটে সর্বোচ্চ?
2. `/wp-login.php` চাওয়া IP-গুলো এবং প্রত্যেকের কতবার — একটি one-liner লিখুন।
3. `access_report.py`-তে `--per-minute` option যোগ করে (১)-এর ফলের সাথে মেলান। Test লিখুন।
4. নিজের VM-এ: `journalctl -o json --since today | jq -r '.SYSLOG_IDENTIFIER' | sort | uniq -c | sort -rn | head` — আজ কোন service সবচেয়ে বেশি log লিখেছে?
5. `find /etc -type f -newer /etc/hostname 2>/dev/null | head` — কী জানায়? `-newer`-এর অর্থ `man find`-এ খুঁজুন।

## 15. Mini-project — incident one-liner cheat sheet

`~/devops-notebook/cheatsheet-logs.md`-এ নিজের ১০টি পরীক্ষিত one-liner লিখুন (প্রতিটির সাথে: প্রশ্ন, command, নমুনা data-য় আসল output, সীমাবদ্ধতা)। অন্তত: top IP, status বণ্টন, top error path, ধীর request, প্রতি মিনিটের হার, নির্দিষ্ট সময়সীমার লাইন (`awk '$4 >= "[26/Oct/2026:09:30"'`), compressed log (`zgrep`), JSON log (`jq`)। এটি Project 1-এর `logs` subcommand-এর পরিকল্পনা।

## 16. Interview প্রশ্ন

1. stdout ও stderr আলাদা কেন? `> file 2>&1` ও `2>&1 > file`-এর পার্থক্য কী?
2. একটি access log থেকে top 10 IP বের করার one-liner লিখুন। `sort` কেন `uniq`-এর আগে?
3. `find | xargs rm` কেন বিপজ্জনক হতে পারে? নিরাপদ বিকল্প কী?
4. grep, sed, awk — প্রতিটি কখন?
5. কখন shell one-liner ছেড়ে Python script লিখবেন?
6. `head` pipe-এর শেষে থাকলে আগের command কোন signal পায়?

## 17. Self-assessment প্রশ্ন

1. Conveyor belt analogy কোথায় মেলে না?
2. Combined log-এ status কোন column এবং request time-এর জন্য কেন `$NF`?
3. Section 5-এ bot traffic কীভাবে আলাদা করলেন?
4. Shell ও Python-এর ফল মিলিয়ে দেখা কেন মূল্যবান?
5. `-print0`/`xargs -0` কেন নিরাপদ?
6. Test-এ `"bash"`-এর বদলে পূর্ণ path কেন দরকার হলো?

## 18. সংক্ষিপ্ত সারাংশ

- প্রতিটি process-এর stdin/stdout/stderr; redirection file-এ পাঠায়, pipe process জোড়ে — সব stage একসাথে চলে।
- `grep` খোঁজে, `sed` বদলায়, `awk` column ও হিসাব করে, `sort | uniq -c` গোনে, `find` খোঁজে, `xargs` argument বানায়, `jq` JSON সামলায়।
- `sort` আগে `uniq`; `> f 2>&1` ক্রম; `-print0 | xargs -0`; বিপজ্জনক কাজের আগে `-print`।
- awk-এর column ভঙ্গুর — জটিল format-এ Python বা JSON log।
- দুই পদ্ধতিতে একই উত্তর = আস্থা।

## 19. Completion checklist

- [ ] Redirection ও `2>&1`-এর ক্রম পরীক্ষা করেছি
- [ ] নমুনা log-এ ছয়টি one-liner চালিয়ে Python-এর সাথে মিলিয়েছি
- [ ] find/xargs-এর ভাঙা ও নিরাপদ রূপ নিজে দেখেছি
- [ ] jq install করে প্রত্যাশিত ফল মিলিয়েছি
- [ ] `python3 -m unittest -v`-এ ৪টি test পাস
- [ ] Exercise ১, ২ ও ৪ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GNU Bash manual — Redirections, Pipelines: https://www.gnu.org/software/bash/manual/bash.html
- GNU grep: https://www.gnu.org/software/grep/manual/
- GNU sed: https://www.gnu.org/software/sed/manual/
- GNU awk (gawk): https://www.gnu.org/software/gawk/manual/
- GNU findutils (find, xargs): https://www.gnu.org/software/findutils/manual/
- jq manual: https://jqlang.org/manual/
- Nginx log format: https://nginx.org/en/docs/http/ngx_http_log_module.html

---

**পরের lesson:** L01-08 — Process, thread, process state ও signal
