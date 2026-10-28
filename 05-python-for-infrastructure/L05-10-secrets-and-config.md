# L05-10 — Secret ও configuration: env var, .env, secret manager

| | |
|---|---|
| **Module** | 05 — Python for Infrastructure |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L05-05 — Config](L05-05-json-yaml-config.md), [L05-07 — Logging](L05-07-logging-structured.md), [L01-04 — User ও permission](../01-linux-systems/L01-04-users-permissions.md) |
| **Label** | — |
| **Tested** | `secrets_loader.py` ও `scan_secrets.py`: ১৩টি test-এর ১২টি পাস, ১টি skip (POSIX file permission — Windows-এ skip)। Python 3.14.5, Windows। **Scanner এই পুরো repository-তে চালানো হয়েছে:** ৪৯৫টি file-এ প্রথমে ৮টি finding এসেছিল — সবই শেখানোর জন্য বানানো নকল বা placeholder, কোনো আসল secret নয়। তৈরির সময় scanner-এর **একটি false negative ও দুটি false positive bug** ধরা পড়েছে (Section 9.4)। কোনো secret manager (Vault, AWS) **চালানো হয়নি**। |

---

## 1. এই lesson-এ যা শিখবেন

- Secret কী, config থেকে কেন আলাদা, এবং কোথায় **কখনো** থাকবে না (code, Git, log, CLI argument, image)।
- তিনটি সাধারণ উৎস ও তাদের ঝুঁকি: **env var**, **`NAME_FILE`** (mounted file), **`.env`** (শুধু local)।
- Secret manager (Vault, AWS Secrets Manager, SOPS): কখন, কেন।
- **`SecretStr`** — মান ভুল করে print, log বা traceback-এ যাওয়া ঠেকানো।
- **Secret scanning:** কীভাবে কাজ করে, false positive/negative-এর টানাপোড়েন, allowlist-এর নিয়ম।
- Secret ফাঁস হলে কী করবেন: **rotate আগে**, history পরিষ্কার পরে।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

GitHub-এ public repository-তে push করা cloud credential কয়েক মিনিটের মধ্যেই স্বয়ংক্রিয় bot খুঁজে পায় এবং ব্যবহার শুরু করে — প্রায়ই crypto mining-এর জন্য বিপুল compute চালিয়ে। এটি বহুবার রিপোর্ট হওয়া একটি নিদর্শন।

Private repository-ও নিরাপদ নয়:

- Contractor-এর access থাকে।
- Laptop চুরি হয়।
- CI log-এ secret ছাপা হয়।
- Docker image layer-এ `.env` থেকে যায়।

মূল সমস্যা তিনটি:

1. Secret কোথায় রাখা হবে।
2. কীভাবে program-এ পৌঁছাবে, কোনো চিহ্ন না রেখে।
3. ভুল করে কোথাও চলে গেলে কীভাবে দ্রুত ধরা পড়বে।

## 3. সহজ ভাষায় পরিচয়

| উৎস | কোথায় দেখা যায় | ভালো | ঝুঁকি |
|---|---|---|---|
| Code-এ লেখা | Git history, সবাই | — | **কখনো নয়** |
| CLI argument | `ps`, shell history | — | **কখনো নয়** |
| Env var | `/proc/PID/environ` (একই user ও root), child process, crash dump | সহজ, ১২-factor | Child-এ চলে যায়; debug endpoint-এ dump হয় |
| `NAME_FILE` (mounted file) | File permission (`0400`) | Env-এ মান নেই; Docker/K8s secret | Permission ঠিক রাখা |
| `.env` file | Disk-এ plaintext | Local development | Git-এ চলে যাওয়া, image-এ copy |
| Secret manager | API + IAM, audit log | Rotation, access control, audit | জটিলতা, network নির্ভরতা |

```python
from secrets_loader import get_secret
found = get_secret("DB_PASSWORD", required=True)      # env → DB_PASSWORD_FILE → (.env)
print(found.source)                                   # "file:/run/secrets/db_password" — মান নয়
connect(password=found.value.reveal())                # শুধু ব্যবহারের মুহূর্তে
log.info("connecting with %s", found.value)           # → "connecting with ***"
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের চাবি

- **Code-এ secret** = চাবি দরজার ওপরে টেপ দিয়ে লাগানো — যে দরজা দেখে, সে-ই চাবি দেখে।
- **Env var** = চাবি পকেটে — আপনার কাছে আছে, কিন্তু আপনি যাকে কোট ধার দেন (child process), সে-ও পকেটে হাত দিতে পারে।
- **Mounted file (`0400`)** = তালাবদ্ধ ড্রয়ারে চাবি, ড্রয়ারের চাবি শুধু আপনার।
- **Secret manager** = নিরাপত্তারক্ষীর কাছে চাবির বাক্স — পরিচয়পত্র দেখিয়ে নিতে হয়, খাতায় লেখা হয় কে কখন নিল, এবং তালা বদলালে (rotation) নতুন চাবি।
- **Secret scanning** = দরজায় দরজায় ঘুরে দেখা কেউ চাবি ঝুলিয়ে রেখেছে কিনা।

### Analogy কোথায় মেলে না

- চাবি হারালে নতুন তালা লাগালেই হয়। **Git-এ push হওয়া secret commit মুছলেও যায় না** — history-তে, অন্যদের clone-এ, fork-এ, CI cache-এ থেকে যায়। তাই প্রথম কাজ **rotate** (পুরোনো secret অকেজো করা), history পরিষ্কার দ্বিতীয়।
- চাবি একটাই জিনিস। **Secret-এর copy বানানো খরচহীন ও অদৃশ্য** — log, core dump, swap, clipboard, terminal scrollback। কোনো copy-ই "ফেরত আনা" যায় না।
- দরজায় চাবি দেখলে চেনা সহজ। **Scanner-কে নিয়ম দিয়ে চিনতে হয়:** `DB_PASSWORD` ধরতে গিয়ে `NOPASSWD`-ও ধরে, আবার একটি ছোট ভুলে অক্ষর-সংখ্যার সব password ছেড়ে দেয় — Section 9.4-এ এই lesson-এর scanner-এ ঠিক তাই ঘটেছে।

## 5. Real-world engineering scenario — "Debug endpoint-এ পুরো environment"

**পরিস্থিতি:** একটি internal service-এ `/debug/env` endpoint ছিল, যা troubleshooting-এর জন্য `os.environ` JSON করে দেখাত। Service-এর সব secret ছিল env var-এ: DB password, payment API key, JWT signing key।

একটি load balancer rule-এর ভুলে endpoint-টি internet-এ খুলে গেল। Signing key দিয়ে আক্রমণকারী যেকোনো user-এর token বানাতে পারত।

**কী কী ঘটতে পারত এবং প্রতিরোধ:**

| স্তর | প্রতিরোধ |
|---|---|
| Debug endpoint | Production-এ বন্ধ; থাকলে auth ও allowlist করা key |
| Env var-এ secret | `NAME_FILE` (mounted file) — env dump-এ শুধু path দেখা যায় |
| Code-এ মান ছড়ানো | `SecretStr` — dump বা log-এ `***` |
| দীর্ঘজীবী key | Secret manager + নিয়মিত rotation; ছোট মেয়াদের credential (Module 19) |
| ফাঁসের পরে | Rotate → audit log দেখা → কোন token ইস্যু হয়েছিল তা বাতিল |

**শিক্ষা:** "Secret কোথায় রাখি" প্রশ্নের সাথে আরেকটি প্রশ্ন আছে: "ভুল করে কোথায় কোথায় copy হয়ে যেতে পারে?" Env var সবচেয়ে সহজ, কিন্তু সবচেয়ে বেশি জায়গায় copy হয়।

## 6. Diagram — secret-এর যাত্রা

```text
 Secret manager (Vault / AWS SM)        Git repo (শুধু code ও config, secret নয়)
        │ IAM / token                         │  pre-commit + CI: scan_secrets.py
        ▼                                     │  .gitignore: .env, *.key
 Deploy system (K8s / Docker / systemd)       ▼
        │ mount: /run/secrets/db_password (0400, tmpfs)
        │ env:   DB_PASSWORD_FILE=/run/secrets/db_password
        ▼
 Python: get_secret("DB_PASSWORD")
   ① env DB_PASSWORD?          ── আছে → SecretStr, source=env
   ② env DB_PASSWORD_FILE?     ── path → file পড়া, শেষের newline বাদ, permission যাচাই → SecretStr
   ③ .env (শুধু dev)           ── parse (expansion নেই)
   ④ required → SecretError (কোন উৎসগুলো দেখা হয়েছে, তা বলে; মান নয়)
        │
        ├─► connect(password=value.reveal())        ← একমাত্র জায়গা
        └─► log/print/repr  →  "***"
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Secret | যা ফাঁস হলে access দেয়: password, API key, private key, token |
| Config | গোপন নয় এমন setting: port, log level |
| `NAME_FILE` রীতি | Env var-এ মানের বদলে file-এর path |
| tmpfs | RAM-ভিত্তিক filesystem — disk-এ লেখা হয় না |
| Secret manager | Secret সংরক্ষণ, access control, audit ও rotation-এর service |
| Rotation | Secret নিয়মিত বা ফাঁসের পরে বদলানো |
| Short-lived credential | কয়েক মিনিট/ঘণ্টার মেয়াদ (IAM role, OIDC) |
| Secret scanning | Code/history-তে secret-এর নিদর্শন খোঁজা |
| False positive / negative | ভুল সতর্কতা / ছুটে যাওয়া আসল secret |
| Fingerprint allowlist | নির্দিষ্ট finding-এর hash দিয়ে ছাড় |
| SOPS | Git-এ encrypted secret file রাখার tool |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Env var কোথায় কোথায় যায়

- Process-এর environment `/proc/PID/environ`-এ থাকে। একই user ও root পড়তে পারে।
- প্রতিটি child process (`subprocess.run`) default-এ পুরো environment পায়।
- Crash reporter, APM agent, error tracker প্রায়ই environment সংগ্রহ করে।
- `docker inspect` container-এর env দেখায়।

তাই env var "যথেষ্ট ভালো", কিন্তু mounted file আরো সংকীর্ণ।

### 8.2 `NAME_FILE`

Docker secrets (`/run/secrets/<name>`) ও Kubernetes secret volume file হিসেবে mount হয়, প্রায়ই tmpfs-এ। Official database image-গুলো `POSTGRES_PASSWORD_FILE`-এর মতো রীতি সমর্থন করে।

`get_secret` file-এর **শুধু শেষের** newline বাদ দেয় (`echo "x" > file`-এর `\n`), মাঝেরটা নয় — কারণ PEM key-এর ভেতরে newline থাকে। POSIX-এ group/other-এর access থাকলে সতর্কতা দেয়।

### 8.3 `SecretStr`

`__repr__`, `__str__`, `__format__` সবই `***` ফেরত দেয়। ফলে f-string, `%s`, `print(dict)`, traceback-এর locals, এমনকি `logging`-এর extra field — কোথাও আসল মান যায় না। Pickle নিষেধ, যাতে ভুল করে cache বা queue-তে না যায়।

এটা একটি **সতর্কতা-ব্যবস্থা**, নিরাপত্তার সীমানা নয়: `.reveal()` বা `_value` দিয়ে মান পাওয়া যায়, এবং memory dump-এ মান থাকে।

### 8.4 Scanner কীভাবে কাজ করে

তিন ধরনের নিয়ম:

1. **নির্দিষ্ট format:** AWS access key id-এর `AKIA` + ১৬ অক্ষর, GitHub token-এর `ghp_` prefix, PEM header। নির্ভুল, false positive কম।
2. **প্রসঙ্গ-ভিত্তিক:** `password = "…"`, `scheme://user:…@`। বেশি ধরে, কিন্তু false positive-ও বেশি — তাই placeholder তালিকা (`changeme`, `${VAR}`, `TOKEN`) ও constant নাম বাদ দেওয়া হয়।
3. **Entropy-ভিত্তিক** (এখানে নেই): এলোমেলো-দেখতে দীর্ঘ string। শক্তিশালী, কিন্তু hash ও UUID-ও ধরে।

Allowlist-এ **fingerprint** (path + rule + মানের hash) ব্যবহার করুন। `path:rule` পুরো file-কে ছাড় দেয়, ফলে পরে ওই file-এ আসল secret এলেও চাপা পড়বে।

> **Fedora-তে:** কোনো পার্থক্য নেই। systemd-এর `LoadCredential=` (systemd ২৪৭+) দুই distro-তেই আছে — secret file `$CREDENTIALS_DIRECTORY`-এ পৌঁছায়, এবং `NAME_FILE` রীতির সাথে সহজে মেলে।

## 9. Practical demonstration

Files:

- [`code/L05-10/secrets_loader.py`](code/L05-10/secrets_loader.py), [`scan_secrets.py`](code/L05-10/scan_secrets.py)।
- [`repo-allowlist.txt`](code/L05-10/repo-allowlist.txt) — এই repo-র allowlist, প্রতিটি entry-র কারণসহ।
- [`test_l05_10.py`](code/L05-10/test_l05_10.py)।

### 9.1 Loader — উৎস দেখা, মান নয়

```bash
cd ~/devops-ai-engineering/05-python-for-infrastructure/code/L05-10
umask 077; printf '%s\n' '<আপনার-dev-password>' > /tmp/db_password
DB_PASSWORD_FILE=/tmp/db_password python3 secrets_loader.py DB_PASSWORD API_TOKEN; echo "exit=$?"
```

প্রত্যাশিত রূপ (test-এ যাচাই করা; এখানে দেখানো লাইনগুলো উদাহরণ):

```text
OK      DB_PASSWORD    from file:/tmp/db_password       length=…
MISSING API_TOKEN
exit=1
```

শুধু উৎস ও দৈর্ঘ্য — দৈর্ঘ্য দেখে বোঝা যায় file-এ ভুলে অতিরিক্ত space বা newline ঢুকেছে কিনা।

### 9.2 এই repository-তে scanner — আসল output

```bash
cd ~/devops-ai-engineering
python3 05-python-for-infrastructure/code/L05-10/scan_secrets.py .
```

প্রথম run (placeholder ও constant-এর নিয়ম যোগ করার আগে):

```text
scanned 493 files: 8 finding(s), 0 allowlisted
02-computer-networking/code/L02-11/sample-wg0.conf:8: wireguard-private-key: EBES…(44 chars)  [fp 4145f888e49b324b]
03-git-and-collaboration/L03-03-remotes-tags-semver.md:176: url-password: ***  [fp ffbd7c58653c9e66]
05-python-for-infrastructure/code/L05-07/demo_job.py:24: url-password: s3cr…(11 chars)  [fp f1dca4258056c55e]
05-python-for-infrastructure/code/L05-07/logsetup.py:34: url-password: ***  [fp 6df1fbb0727a11ab]
05-python-for-infrastructure/code/L05-07/test_l05_07.py:75: url-password: ***  [fp 41926e413df153b2]
05-python-for-infrastructure/code/L05-07/test_l05_07.py:87: url-password: tops…(9 chars)  [fp 8ec0b50808639c6a]
05-python-for-infrastructure/L05-07-logging-structured.md:86: url-password: Prod…(9 chars)  [fp 02476cb242349320]
05-python-for-infrastructure/L05-07-logging-structured.md:168: url-password: ***  [fp c24dc3c2da3b8d27]
```

প্রতিটি হাতে যাচাই করা হয়েছে:

| Finding | কী | সিদ্ধান্ত |
|---|---|---|
| `sample-wg0.conf` | L02-11-এর synthetic key — file-এর শুরুতেই "SYNTHETIC EXAMPLE" লেখা | Fingerprint allowlist |
| L03-03:176, `logsetup.py`:34, L05-07:168 | Documentation-এ `user:TOKEN@`, `user:PASSWORD@`, `user:pass@` — placeholder | **Scanner ঠিক করা** (placeholder তালিকা) |
| L05-07-এর demo, test, lesson | Redaction শেখানোর জন্য ইচ্ছাকৃত নকল password | Fingerprint allowlist, কারণসহ |

পরের run:

```text
$ scan_secrets.py . --allowlist 05-python-for-infrastructure/code/L05-10/repo-allowlist.txt
scanned 495 files: 0 finding(s), 5 allowlisted
exit=0
```

### 9.3 Output-এ মানও mask করা

Finding-এ শুধু প্রথম ৪ অক্ষর ও দৈর্ঘ্য দেখায় (`s3cr…(11 chars)`), ৮ অক্ষরের কম হলে `***`। Scanner-এর output নিজেই CI log-এ যায় — সেখানে পুরো secret ছাপা মানে নতুন করে ফাঁস।

### 9.4 Scanner-এর তিনটি আসল bug — তৈরির সময় ধরা পড়েছে

1. **False negative — `\b`-এর ফাঁদ:** test-এ `db_password = "…"` ধরা পড়ল না।
   - Regex ছিল `\b(?:password|…)`।
   - `db_password`-এ `_` ও `p` দুটোই word character, তাই মাঝে কোনো word boundary নেই।
   - ফল: **সবচেয়ে সাধারণ নাম `DB_PASSWORD`-ই বাদ পড়ছিল।**
   - সমাধান: `\b\w*(?:password|…)`।
2. **False positive — constant:** নতুন regex `01-linux-systems/code/L01-05/sudoers_audit.py`-এর `nopasswd = "NOPASSWD"` ধরল — এটা sudoers-এর tag-এর নাম, secret নয়। তাই সব-বড়-হাতের identifier বাদ দেওয়া হলো।
3. **গুরুতর false negative — `(?i)`-এর পরিধি:** constant-এর নিয়মটি (`^[A-Z][A-Z0-9_]*$`) প্রথমে case-insensitive placeholder regex-এর **ভেতরে** যোগ করা হয়েছিল। `(?i)` পুরো pattern-এ প্রযোজ্য, তাই এটা মিলছিল **যেকোনো অক্ষর-সংখ্যার মানের** সাথে।
   - সরাসরি যাচাইয়ে দেখা গেল `correcthorsebattery` ও `Corr3ct` দুটোকেই "placeholder" ধরা হচ্ছে — অর্থাৎ বেশিরভাগ আসল password scanner উপেক্ষা করত।
   - **সব test তখনও পাস করছিল,** কারণ test-এর নকল password-এ `-` ছিল।
   - ধরা পড়ল দুটি লক্ষণে: repo scan-এ allowlisted সংখ্যা ৫ থেকে ৩-এ নেমে যাওয়া, এবং হাতে কয়েকটি মান দিয়ে পরীক্ষা।
   - সমাধান: আলাদা case-sensitive `CONSTANT_NAME`, এবং অক্ষর-মাত্র password-এর জন্য regression test।

**শিক্ষা:** Security tool-এর test-এ "ধরা উচিত" ও "ধরা উচিত নয়" দুই তালিকাই লাগে, এবং বৈচিত্র্যপূর্ণ input। একটি false negative bug চুপচাপ থাকে — কেউ জানতেও পারে না যে scanner অন্ধ।

### 9.5 Ubuntu-তে (চালানো হয়নি)

```bash
chmod 644 /tmp/db_password
DB_PASSWORD_FILE=/tmp/db_password python3 secrets_loader.py DB_PASSWORD
# WARN    DB_PASSWORD: /tmp/db_password is accessible by group/others (mode 644); use chmod 600
cat /proc/$$/environ | tr '\0' '\n' | grep -c .     # নিজের shell-এর env — অন্য process-ও এভাবে দেখতে পারে
```

### 9.6 Test

```bash
python3 -m unittest -v
```

১৩টি test:

- `SecretStr` সাত রকম ভাবে print করলেও মান নয়; pickle নিষেধ।
- উৎসের অগ্রাধিকার; missing/required/empty/অপঠনযোগ্য file।
- World-readable সতর্কতা *(POSIX — Windows-এ skip)*।
- `.env` parsing (`export`, quote, inline comment, `${A}` আক্ষরিক)।
- CLI কখনো মান print করে না।
- ৬টি নিয়মের detection।
- Placeholder ও inline allow।
- **অক্ষর-মাত্র password এখনও ধরা পড়ে** (regression)।
- Masking।
- Directory scan (`.git` ও binary বাদ) + fingerprint allowlist।
- **এই repository পরিষ্কার।**

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `SecretStr.__format__` | f-string-এও `***` | `__str__` একা f-string-এর format spec ধরে না |
| `__reduce__` → `TypeError` | Pickle নিষেধ | Cache/queue-তে ফাঁস নয় |
| `rstrip("\r\n")` | শুধু শেষের newline | PEM-এর ভেতরের newline রাখা |
| Empty file → error | ফাঁকা secret | নীরবে ফাঁকা password দিয়ে চেষ্টা নয় |
| `.env`-এ expansion নেই | `${A}` আক্ষরিক | অপ্রত্যাশিত মান বা injection নয় |
| Error-এ উৎসের তালিকা, মান নয় | "tried env X, env X_FILE" | Debug করা যায়, ফাঁস হয় না |
| `mask()` | ৪ অক্ষর + দৈর্ঘ্য | CI log-এ পুরো secret নয় |
| `fingerprint` | path+rule+মানের hash | মান বা path বদলালে ছাড় বাতিল |
| `SKIP_DIRS`, `MAX_BYTES`, UTF-8 ব্যর্থ = binary | Noise ও গতি | `.git`, venv, বড় file বাদ |
| `CONSTANT_NAME` আলাদা regex | Case-sensitive | `(?i)`-এর bug (Section 9.4) |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `secrets_loader.py` | শুধু উৎস ও দৈর্ঘ্য; missing হলে exit ১ |
| `scan_secrets.py .` (allowlist সহ) | `0 finding(s), 5 allowlisted`, exit ০ |
| Allowlist ছাড়া | ৫টি finding, exit ১ |
| `python3 -m unittest -v` | `Ran 13 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Secret Git-এ push হয়ে গেছে | `.env` commit | **আগে rotate**, তারপর history পরিষ্কার (`git filter-repo`) ও সবাইকে re-clone |
| Password-এ শেষে অদৃশ্য অক্ষর | File-এর newline বা Windows-এর `\r\n` | `rstrip("\r\n")`; `length=` দেখুন |
| Container-এ secret পাওয়া যায় না | `_FILE` path ভুল বা mount নেই | `ls -l /run/secrets`; source error-এর তালিকা দেখুন |
| Docker image-এ secret | `COPY . .` + `.env` | `.dockerignore`; BuildKit secret mount (Module 09) |
| CI log-এ secret | `set -x` বা debug print | CI-এর masking + `SecretStr`; `set -x` বন্ধ |
| Scanner অনেক false positive দেয় | প্রসঙ্গ-ভিত্তিক নিয়ম | Placeholder তালিকা; fingerprint allowlist |
| Allowlist পুরো file ছাড় দেয় | `path:rule` | Fingerprint ব্যবহার করুন |
| `ps`-এ password দেখা যায় | CLI argument | File বা env দিয়ে দিন |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Least privilege: প্রতিটি service-এর নিজের credential, শুধু প্রয়োজনীয় অনুমতি।
  - ছোট মেয়াদের credential (IAM role, OIDC — Module 08/11) দীর্ঘজীবী key-র চেয়ে ভালো।
  - Rotation-এর পরিকল্পনা আগে থেকেই করুন। "এই key বদলালে কী কী ভাঙবে?" প্রশ্নের উত্তর জানা থাকা উচিত।
  - Pre-commit hook ও CI দুই জায়গাতেই scan (Module 19-এ gitleaks/trufflehog)।
  - GitHub-এর push protection চালু রাখুন।
- **Performance:**
  - Secret manager-এ প্রতিটি request-এ API call নয় — শুরুতে পড়ে memory-তে রাখুন, মেয়াদ অনুযায়ী refresh।
  - Scanner ৪৯৫টি file দ্রুত পড়ে; বড় repo-তে শুধু পরিবর্তিত file scan করুন (pre-commit)।
- **Cost:**
  - Secret manager-এ প্রতি secret ও প্রতি API call-এ খরচ হতে পারে (AWS Secrets Manager)। Parameter Store-এর মতো সস্তা বিকল্প আছে (Module 08)।
  - ফাঁস হওয়া cloud key-র খরচ (অন্যের mining) এর তুলনায় বহু গুণ বেশি — billing alert রাখুন (Module 29)।

## 14. Hands-on exercise

1. Ubuntu-তে Section 9.5 চালান — permission সতর্কতা ও `/proc/PID/environ` নিজে দেখুন।
2. `scan_secrets.py`-এ entropy-ভিত্তিক নিয়ম যোগ করুন (Shannon entropy > ৪.৫, দৈর্ঘ্য ≥ ২০)। এই repo-তে কতগুলো false positive আসে? কোনগুলো hash বা UUID?
3. `scan_secrets.py`-কে একটি Git pre-commit hook হিসেবে বসান — শুধু staged file (`git diff --cached --name-only`)।
4. Docker-এ একটি container চালান যেখানে `--secret`/`-v` দিয়ে `/run/secrets/db_password` mount ও `DB_PASSWORD_FILE` set করা (Module 09-এর আগে প্রস্তুতি)। `docker inspect`-এ কী দেখা যায়, কী যায় না?
5. "Secret ফাঁস হয়েছে" runbook লিখুন: প্রথম ১৫ মিনিটে কী কী (rotate, audit log, scope নির্ণয়, যোগাযোগ)।

## 15. Mini-project — Secret rotation helper

`rotate.py DB_PASSWORD --target file:/run/secrets/db_password`:

- নতুন শক্তিশালী মান (`secrets.token_urlsafe`)।
- Atomic write (L05-03), mode `0600`।
- পুরোনো মানের fingerprint log-এ (মান নয়)।
- `--verify-cmd` দিয়ে নতুন মান কাজ করছে কিনা যাচাই, ব্যর্থ হলে পুরোনোটা ফেরত।
- **কোনো আসল database-এ নয় — local test service-এ।**

## 16. Interview প্রশ্ন

1. Application-এ secret কীভাবে দেবেন? Env var-এর ঝুঁকি কী?
2. Git-এ secret push হয়ে গেলে প্রথম তিনটি কাজ কী?
3. Secret manager কী সুবিধা দেয়?
4. Secret scanning-এ false positive ও false negative-এর মধ্যে কীভাবে ভারসাম্য রাখবেন?
5. Kubernetes secret কি "secret"? (base64 ≠ encryption — Module 14)
6. Short-lived credential কেন ভালো?

## 17. Self-assessment প্রশ্ন

1. চাবি analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এ কোন স্তরগুলো ঘটনা ঠেকাতে পারত?
3. `\b(?:password)` কেন `DB_PASSWORD` ধরে না?
4. `(?i)`-এর bug-এ test কেন পাস করছিল?
5. Fingerprint allowlist কেন `path:rule`-এর চেয়ে ভালো?

## 18. সংক্ষিপ্ত সারাংশ

- Secret কখনো code, Git, CLI argument, log বা image-এ নয়।
- উৎস: secret manager > mounted file (`NAME_FILE`) > env var; `.env` শুধু local।
- `SecretStr` — মান শুধু `.reveal()`-এ; সব print/log-এ `***`।
- Scanner pre-commit ও CI-তে; allowlist fingerprint দিয়ে, কারণসহ।
- ফাঁস হলে আগে rotate, পরে পরিষ্কার।

## 19. Completion checklist

- [ ] `NAME_FILE` দিয়ে secret পড়েছি, permission সতর্কতা দেখেছি
- [ ] নিজের project-এ scanner চালিয়ে প্রতিটি finding-এর সিদ্ধান্ত নিয়েছি
- [ ] Scanner-এর তিনটি bug ব্যাখ্যা করতে পারি
- [ ] `python3 -m unittest -v`-এ সব test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- The Twelve-Factor App — Config: https://12factor.net/config
- OWASP — Secrets Management Cheat Sheet: https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html
- Docker — Manage sensitive data with Docker secrets: https://docs.docker.com/engine/swarm/secrets/
- Kubernetes — Secrets: https://kubernetes.io/docs/concepts/configuration/secret/
- systemd — Credentials: https://systemd.io/CREDENTIALS/
- GitHub — About secret scanning: https://docs.github.com/en/code-security/secret-scanning/introduction/about-secret-scanning
- Gitleaks: https://github.com/gitleaks/gitleaks

---

**পরের lesson:** L05-11 — Log analysis tool তৈরি
