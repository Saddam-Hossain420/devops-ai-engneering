# L01-04 — Users, groups, ownership ও permission

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-03 — Filesystem hierarchy, inode, link](L01-03-filesystem-hierarchy.md) |
| **Label** | ⚠️ user তৈরি/মোছা system বদলায় — VM-এ snapshot নিন |
| **Tested** | `perm_tool.py`: ৮টি test-এর ৭টি পাস (Python 3.14, Windows); `audit` test **skip হয়েছে** কারণ Windows-এ POSIX chmod নেই — Ubuntu-তে চলবে। `explain`, `umask`, `check`, `users` চালানো হয়েছে। `useradd`, `chmod`, `chown`, `id` ইত্যাদি **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- Linux-এ **user** ও **group** আসলে কী — নাম নয়, **সংখ্যা (UID, GID)**।
- `/etc/passwd`, `/etc/group`, `/etc/shadow`-এর গঠন।
- **Ownership** (owner ও group) এবং **permission bit** (r, w, x) — file ও directory-তে আলাদা অর্থ।
- Octal (`640`) ও symbolic (`rw-r-----`) রূপ, `chmod`, `chown`, `chgrp`।
- Kernel কীভাবে access সিদ্ধান্ত নেয় — **প্রথম মেলা class-ই চূড়ান্ত**।
- **umask**, এবং বিশেষ bit: **setuid, setgid, sticky**।
- System user ও service account — কেন nginx `www-data` হিসেবে চলে।
- Python দিয়ে mode ব্যাখ্যা, umask হিসাব, access সিদ্ধান্ত ও security audit।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Linux শুরু থেকেই **multi-user** system: একই machine-এ অনেক মানুষ ও অনেক service। দরকার:

- একজন user অন্যজনের file পড়তে বা বদলাতে না পারা।
- Web server hack হলেও আক্রমণকারী database-এর file বা SSH key ছুঁতে না পারা।
- একটি team-এর সদস্যরা একটি shared directory-তে একসাথে কাজ করতে পারা।

Permission ঠিক না জানলে দুই রকম ভুল হয়: হয় "Permission denied" দেখে `chmod 777` করে সব খুলে দেওয়া (বড় নিরাপত্তা ঝুঁকি), নয়তো এত বন্ধ রাখা যে service চলে না। WordPress-এ হয়তো দেখেছেন: upload কাজ করে না, কেউ বলল `chmod -R 777 wp-content` — এই lesson-এর পরে বুঝবেন কেন সেটি বিপজ্জনক এবং সঠিক সমাধান কী।

## 3. সহজ ভাষায় পরিচয়

**User** = একটি পরিচয়, যার একটি সংখ্যা আছে — **UID**। Kernel শুধু সংখ্যা চেনে; নাম (`sami`) মানুষের সুবিধার জন্য `/etc/passwd`-এ ম্যাপ করা।

| UID | কে |
|---|---|
| 0 | `root` — সর্বোচ্চ অধিকার |
| 1–999 | System/service user (Ubuntu-তে; `www-data` = 33) |
| 1000+ | সাধারণ মানুষ user |

**Group** = user-দের দল, নিজস্ব সংখ্যা **GID**। প্রতিটি user-এর একটি **primary group** ও শূন্য বা বেশি **supplementary group**।

**প্রতিটি file-এর আছে:** একজন owner (UID), একটি group (GID), এবং ৯টি permission bit — তিনটি class × তিনটি অধিকার:

```text
 -  rw-  r--  ---
 │   │    │    └── other (বাকি সবাই): কিছু না
 │   │    └─────── group: শুধু পড়া
 │   └──────────── owner: পড়া ও লেখা
 └──────────────── type: - file, d directory, l symlink
```

**File-এ বনাম directory-তে অর্থ:**

| Bit | File-এ | Directory-তে |
|---|---|---|
| r (4) | বিষয়বস্তু পড়া | ভেতরের **নামের তালিকা** দেখা (`ls`) |
| w (2) | বিষয়বস্তু বদলানো | ভেতরে file **তৈরি, মোছা, নাম বদলানো** (x-ও লাগে) |
| x (1) | Program হিসেবে চালানো | ভেতরে **প্রবেশ** করা / path পেরোনো (`cd`, file খোলা) |

গুরুত্বপূর্ণ ফল: **একটি file মোছার অধিকার file-এর permission-এ নয়, directory-র w-তে।** আর directory-তে x না থাকলে ভেতরের file-এর permission যাই হোক, পৌঁছানো যায় না (L01-03-এর path resolution)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিস ভবন

- **UID** = কর্মীর ID card নম্বর; নাম card-এ ছাপা থাকলেও দরজার যন্ত্র শুধু নম্বর পড়ে।
- **Group** = বিভাগ (Accounts, IT)।
- **File permission** = প্রতিটি ঘরের দরজায় তিনটি নিয়ম: "মালিকের জন্য", "বিভাগের জন্য", "বাকি সবার জন্য"।
- **Directory x** = করিডোরে ঢোকার অধিকার — করিডোরে ঢুকতে না পারলে ভেতরের কোনো ঘরে যাওয়া যাবে না।
- **root** = ভবনের মালিক, master key।
- **setuid** = একটি বিশেষ দরজা যা খুললে কিছুক্ষণের জন্য মালিকের card পাওয়া যায় — যেমন `passwd` command সাধারণ user-কে root-এর অধিকারে নিজের password বদলাতে দেয়।

### Analogy কোথায় মেলে না

- অফিসে আপনি একসাথে কয়েকটি নিয়মের সুবিধা নিতে পারেন ("মালিক হিসেবে না পারলে বিভাগের সদস্য হিসেবে")। Linux-এ **না**: kernel প্রথম যে class মেলে (owner → group → other) শুধু সেটিই দেখে। Owner-এর অধিকার other-এর চেয়ে কম হলে owner আসলে কম পায় (Section 8.2)।
- Master key দিয়ে মালিক সব পারেন। Linux-এ root-ও সব পারে না: কোনো execute bit না থাকলে root file চালাতে পারে না; আর AppArmor/SELinux (L01-17) root-কেও সীমিত করতে পারে।
- অফিসের ID card নাম বদলালে নতুন করে বানাতে হয়। Linux-এ নাম বদলালেও UID একই থাকলে সব file-এর মালিকানা অক্ষত — আবার ভিন্ন server-এ একই নামের ভিন্ন UID থাকলে (যেমন NFS বা container volume) file-এর মালিক "ভুল" দেখায়।

## 5. Real-world engineering scenario — WordPress upload ব্যর্থ ও "chmod 777"-এর ফাঁদ

**পরিস্থিতি:** Ubuntu server-এ Nginx + PHP-FPM-এ WordPress। নতুন deploy-এর পরে admin panel থেকে image upload ব্যর্থ: "Unable to create directory wp-content/uploads/2026/10. Is its parent directory writable by the server?"

**জড়িত component:** PHP-FPM process (কোন user হিসেবে চলে), `wp-content/uploads` directory-র owner, group ও mode।

**Diagnosis:**

```bash
ps -o user,group,pid,cmd -C php-fpm8.3     # PHP কোন user হিসেবে চলে
ls -ld /var/www/site/wp-content/uploads    # directory-র owner/group/mode
```

উদাহরণ output:

```text
USER     GROUP    PID   CMD
www-data www-data 2210  php-fpm: pool www
drwxr-xr-x 2 deploy deploy 4096 Oct 26 09:00 /var/www/site/wp-content/uploads
```

- PHP চলে `www-data` হিসেবে।
- Directory-র owner `deploy` (CI/CD user যে file copy করেছে), group `deploy`, mode `755`।
- `www-data` owner নয়, group-এর সদস্যও নয় → **other** class → `r-x` → লেখার অধিকার নেই।

**ভুল সমাধান:** `chmod -R 777 /var/www/site` — সব file সবার জন্য লেখাযোগ্য। এখন যেকোনো process (একটি hack হওয়া plugin, অন্য site-এর user) PHP file বদলে malicious code ঢোকাতে পারে। আর PHP file-গুলোও লেখাযোগ্য — web shell লাগানোর আদর্শ পরিবেশ।

**সঠিক সমাধান (least privilege):**

```bash
sudo chgrp -R www-data /var/www/site/wp-content/uploads       # group = www-data
sudo chmod -R g+w /var/www/site/wp-content/uploads             # group লিখতে পারে
sudo find /var/www/site/wp-content/uploads -type d -exec chmod g+s {} +   # setgid: নতুন file-ও www-data group পায়
```

Code (`.php`) `deploy`-এর মালিকানায় ও `www-data`-র জন্য শুধু পড়া থাকে; শুধু `uploads` লেখাযোগ্য। Hack হওয়া PHP process code বদলাতে পারে না।

> **Fedora-তে:** web server user সাধারণত `apache` (php-fpm) বা `nginx`; এবং SELinux-এর কারণে শুধু permission ঠিক করলেও লেখা ব্যর্থ হতে পারে — directory-তে `httpd_sys_rw_content_t` context লাগবে (L01-17)।

## 6. Diagram — kernel-এর access সিদ্ধান্ত

```text
 process (uid=1001, gids={1001,33}) চায়: open("/etc/app.conf", O_RDONLY)
                │
                ▼
        uid == 0 (root)? ──yes──► allowed (read/write); execute-এ কোনো x bit লাগে
                │ no
                ▼
     uid == file owner? ──yes──► owner bits দেখো ──► r আছে? → allowed / denied
                │ no                                  (group/other আর দেখা হয় না!)
                ▼
     file group ∈ process gids? ──yes──► group bits দেখো ──► সিদ্ধান্ত
                │ no
                ▼
          other bits দেখো ──► সিদ্ধান্ত

 (বাস্তবে এর আগে-পরে আরো স্তর: path-এর প্রতিটি directory-র x, ACL (L01-05),
  capability, AppArmor/SELinux (L01-17))
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| UID / GID | User / group-এর সংখ্যাগত পরিচয় — kernel এটাই দেখে |
| Primary group | User-এর default group; নতুন file সাধারণত এই group পায় |
| Supplementary group | অতিরিক্ত group membership |
| Owner | File-এর মালিক UID |
| Mode | Permission bit + special bit (যেমন `0640`) |
| Octal | ৮-ভিত্তিক সংখ্যা: r=4, w=2, x=1 যোগ করে প্রতিটি class |
| umask | নতুন file/directory তৈরির সময় কোন bit **বাদ** দেওয়া হবে |
| setuid (4000) | Program file-এর owner-এর অধিকারে চলে |
| setgid (2000) | Program-এ group-এর অধিকার; directory-তে নতুন file directory-র group পায় |
| sticky (1000) | Directory-তে শুধু file-এর owner মুছতে পারে (`/tmp`) |
| System user | Service চালানোর জন্য login-অক্ষম user (`www-data`, `postgres`) |
| `nologin` shell | Interactive login আটকানোর shell |
| DAC | Discretionary Access Control — owner নিজে permission ঠিক করে (এই lesson-এর মডেল) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 User database

```text
/etc/passwd   (সবাই পড়তে পারে — password নেই)
sami:x:1000:1000:Sami,,,:/home/sami:/bin/bash
 │   │  │    │     │         │          └ login shell
 │   │  │    │     │         └ home directory
 │   │  │    │     └ মন্তব্য (GECOS)
 │   │  │    └ primary GID
 │   │  └ UID
 │   └ "x" = password hash আলাদা file-এ
 └ username

/etc/shadow   (শুধু root পড়তে পারে) — password hash, মেয়াদ
/etc/group    developers:x:1002:sami,deploy   (group নাম, GID, সদস্য)
```

এগুলো সরাসরি editor দিয়ে না বদলে command ব্যবহার করুন (`useradd`, `usermod`, `groupadd`) — অথবা প্রয়োজনে `vipw`/`vigr` (lock ও syntax যাচাই করে)।

### 8.2 প্রথম মেলা class — একটি বিস্ময়কর ফল

Mode `0047` (`---r--rwx`): owner কিছুই পারে না, group পড়তে পারে, other সব পারে। Owner file পড়তে চাইলে? Kernel দেখে uid == owner → owner bits `---` → **DENIED**। Owner "other" হিসেবে সুবিধা পায় না। (এই lesson-এর `check` command ও test এটি দেখায়।) এমন mode বাস্তবে প্রায় অর্থহীন, কিন্তু নিয়মটি বোঝার জন্য গুরুত্বপূর্ণ।

### 8.3 umask

নতুন file-এর ভিত্তি `666` (file সাধারণত execute-যোগ্য নয়), directory-র `777`। umask সেখান থেকে bit **বাদ** দেয় (bitwise: `base & ~umask`)।

| umask | নতুন file | নতুন directory | কখন |
|---|---|---|---|
| `022` | `644` (rw-r--r--) | `755` | সাধারণ default |
| `002` | `664` | `775` | Shared group কাজ (Ubuntu-তে user-private-group সহ default হতে পারে) |
| `027` | `640` | `750` | Server-এ "other" কিছুই পাবে না |
| `077` | `600` | `700` | সর্বোচ্চ গোপনীয়তা (key, secret) |

হিসাব (027): file → 666 & ~027 = 110 110 110 & 111 101 000 = 110 100 000 = **640**।

umask প্রতিটি process-এর বৈশিষ্ট্য (inherit হয়)। systemd service-এর umask unit file-এ `UMask=` দিয়ে ঠিক করা যায় (L01-10)।

### 8.4 Special bit

- **setuid** — `ls -l /usr/bin/passwd` → `-rwsr-xr-x root`। সাধারণ user `passwd` চালালে process root অধিকার পায় যাতে `/etc/shadow` লিখতে পারে। প্রতিটি setuid-root program একটি সম্ভাব্য privilege escalation পথ — তাই সংখ্যা ন্যূনতম রাখা ও নিয়মিত audit।
- **setgid directory** — shared project folder: নতুন file স্বয়ংক্রিয়ভাবে directory-র group পায়, user-এর primary group নয়।
- **sticky** — `/tmp` হলো `drwxrwxrwt` (1777): সবাই লিখতে পারে, কিন্তু অন্যের file মুছতে পারে না।

`ls`-এ বড় হাতের `S`/`T` মানে special bit আছে কিন্তু নিচে execute bit নেই — সাধারণত ভুল configuration।

### 8.5 Linux user পরিবর্তনের সাথে process

একটি process-এর **effective UID** permission সিদ্ধান্তে ব্যবহার হয়। নতুন group-এ যোগ করলে **চলমান** shell সেটি পায় না — logout/login (বা `newgrp`) লাগে, কারণ group তালিকা login-এর সময় process-এ বসানো হয়। এটি খুব সাধারণ বিভ্রান্তি।

## 9. Practical demonstration (Ubuntu VM — snapshot নিন)

### 9.1 নিজের পরিচয়

```bash
id                     # uid, gid, groups
id www-data
getent passwd sami     # passwd database থেকে (LDAP থাকলে সেখান থেকেও)
getent group sudo
```

উদাহরণ:

```text
uid=1000(sami) gid=1000(sami) groups=1000(sami),4(adm),27(sudo)
```

> **Fedora-তে:** admin group `wheel` (`sudo` নয়)।

### 9.2 User ও group তৈরি (⚠️)

```bash
sudo groupadd developers
sudo useradd --create-home --shell /bin/bash --groups developers alice
sudo passwd alice                       # (lab-এ) password দিন
sudo useradd --system --no-create-home --shell /usr/sbin/nologin myapp    # service account
getent passwd alice myapp
```

| Option | অর্থ |
|---|---|
| `--create-home` | `/home/alice` তৈরি |
| `--groups developers` | supplementary group |
| `--system` | ছোট UID (system range), aging নেই |
| `--shell /usr/sbin/nologin` | interactive login আটকায় |

Ubuntu-তে `adduser` একটি interactive, বন্ধুত্বপূর্ণ wrapper; script-এ `useradd` বেশি পূর্বানুমেয়।

> **Fedora-তে:** `useradd` default-ভাবে home তৈরি করে; `adduser` একই `useradd`-এর link।

### 9.3 Permission পরিবর্তন

```bash
cd "$(mktemp -d)"
touch report.txt
ls -l report.txt                         # default mode (umask অনুযায়ী)
chmod 640 report.txt                     # octal
chmod u+x,g-r report.txt                 # symbolic: owner-এ x যোগ, group থেকে r বাদ
chmod a-x report.txt                     # a = all
stat -c '%a %A %U:%G' report.txt         # octal, symbolic, owner:group
sudo chown alice:developers report.txt   # owner ও group
ls -l report.txt
```

`chmod -R` সাবধানে: directory ও file দুটোতে একই mode দিলে (যেমন `-R 644`) directory-তে x চলে যায় → ভেতরে প্রবেশ বন্ধ। আলাদা করে:

```bash
find DIR -type d -exec chmod 755 {} +
find DIR -type f -exec chmod 644 {} +
```

### 9.4 Python tool

File: [`code/L01-04/perm_tool.py`](code/L01-04/perm_tool.py)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-04
python3 perm_tool.py explain 640
python3 perm_tool.py explain rwsr-xr-x
python3 perm_tool.py umask 027
```

**আসল output (repository-তে চালানো):**

```text
octal 0640   symbolic rw-r-----
  owner: read, write
  group: read
  other: nothing
octal 4755   symbolic rwsr-xr-x
  owner: read, write, execute
  group: read, execute
  other: read, execute
  setuid: চালালে program file-এর owner-এর অধিকারে চলে
umask 0027 → new file 0640 (rw-r-----), new dir 0750 (rwxr-x---)
```

**Kernel-এর সিদ্ধান্ত simulation** — Section 5-এর মত: uid 1001, group-এ 33 (www-data), file `root:www-data 640`:

```bash
python3 perm_tool.py check --uid 1001 --gids 1001,33 --owner 0 --group 33 --mode 640 --op r
python3 perm_tool.py check --uid 1000 --gids 1000 --owner 1000 --group 1000 --mode 047 --op r; echo "exit=$?"
```

```text
ALLOWED  (matched class: group (r--))
DENIED  (matched class: owner (---))
exit=1
```

দ্বিতীয়টি Section 8.2-এর "প্রথম মেলা class" নিয়মের প্রমাণ।

**Login করতে পারে এমন user** (sample বা আসল `/etc/passwd`):

```bash
python3 perm_tool.py users sample-passwd.txt
python3 perm_tool.py users                     # আপনার /etc/passwd
```

```text
  root         uid=0      home=/root                shell=/bin/bash
  postgres     uid=111    home=/var/lib/postgresql  shell=/bin/bash
  sami         uid=1000   home=/home/sami           shell=/bin/bash
  deploy       uid=1001   home=/home/deploy         shell=/bin/bash
```

Security প্রশ্ন: `postgres` (service account)-এর login shell `/bin/bash` কেন? Ubuntu-র PostgreSQL package ইচ্ছা করে এটি দেয় (`sudo -u postgres psql`-এর সুবিধার জন্য); কিন্তু audit-এ প্রতিটি login-সক্ষম service account-এর কারণ জানা থাকা উচিত।

**Audit (read-only):**

```bash
python3 perm_tool.py audit /var/www            # world-writable ও setuid/setgid খোঁজে
sudo find / -xdev -perm -4000 -type f 2>/dev/null   # system-এর সব setuid file (native tool)
```

`-perm -4000` = setuid bit আছে এমন; `2>/dev/null` = permission error বাদ। Python `audit` sticky directory (যেমন `/tmp`) রিপোর্ট করে না, কারণ সেটি ইচ্ছাকৃত।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_perm_tool.py`](code/L01-04/test_perm_tool.py)-এর ৮টি test: octal ↔ symbolic (special bit ও বড় হাতের S সহ), ভুল mode, umask, owner-class নিয়ম, group membership, root, passwd parse, এবং audit (শুধু Linux/POSIX-এ চলে; Windows-এ skip)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `mode >> (6 - i*3) & 7` | প্রতিটি class-এর ৩টি bit আলাদা করা | owner = bit 8-6, group = 5-3, other = 2-0 |
| `0o4000 / 0o2000 / 0o1000` | setuid/setgid/sticky | Python-এ `0o` = octal literal |
| `apply_umask`: `0o666 & ~mask` | Bitwise AND NOT | Kernel ঠিক এভাবেই হিসাব করে |
| `can_access()` | if/elif/else — প্রথম মেলাই চূড়ান্ত | Kernel-এর নিয়ম; ACL-এর বিস্তার L01-05-এ |
| `os.walk` + `lstat` | Symlink অনুসরণ না করে হাঁটা | Symlink loop ও tree-এর বাইরে চলে যাওয়া ঠেকায় |
| `stat.S_IMODE`, `S_ISDIR` | mode থেকে permission ও type আলাদা | Standard library-র সঠিক উপায় |
| `@unittest.skipUnless(os.name == "posix")` | Platform-নির্ভর test স্পষ্টভাবে skip | Test নীরবে ভুল pass করে না; skip report-এ দেখা যায় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `umask` | সাধারণত `0002` বা `0022` |
| নতুন file `ls -l` | umask অনুযায়ী `-rw-rw-r--` বা `-rw-r--r--` |
| `ls -ld /tmp` | `drwxrwxrwt` |
| `ls -l /usr/bin/passwd` | `-rwsr-xr-x ... root root` |
| `python3 -m unittest -v` (Ubuntu) | `Ran 8 tests`, `OK` (skip নেই) |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| File-এ `r` আছে তবু `Permission denied` | পথের কোনো directory-তে `x` নেই | `namei -l /full/path` (প্রতিটি অংশের permission) | Directory-তে প্রয়োজনীয় `x` |
| Group-এ যোগ করলাম, তবু কাজ করে না | চলমান session পুরোনো group তালিকা নিয়ে | `id` (session) বনাম `id user` | Logout/login বা service restart |
| `chmod: changing permissions ... Operation not permitted` | আপনি owner নন | `ls -l` | Owner বা `sudo` (কারণ বুঝে) |
| Script চলে না: `Permission denied` | `x` bit নেই, বা filesystem `noexec` | `ls -l`, `findmnt -no OPTIONS --target file` | `chmod +x` বা `bash script.sh` |
| `-R 644`-এর পরে directory-তে ঢোকা যায় না | Directory থেকে x চলে গেছে | `ls -ld` | `find -type d -exec chmod 755` |
| Container/NFS-এ file-এর owner "অচেনা সংখ্যা" | UID দুই system-এ আলাদা | `ls -ln` (সংখ্যা দেখায়) | UID মেলান (Module 10) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - **কখনো `chmod 777`** (বা `-R 777`) সমাধান হিসেবে নয়। সঠিক owner/group ও ন্যূনতম bit।
  - প্রতিটি service আলাদা system user হিসেবে চলুক (`--system`, `nologin`) — একটি hack হলে অন্যগুলো রক্ষা পায়।
  - Secret file (`.env`, private key) `600`, owner = যে service পড়বে।
  - SSH private key `600` না হলে `ssh` নিজেই প্রত্যাখ্যান করে (L01-13)।
  - setuid file-এর তালিকা baseline রাখুন; নতুন setuid file আবির্ভাব একটি আক্রমণের লক্ষণ হতে পারে।
- **Performance:** নগণ্য; তবে বিশাল tree-তে `chmod -R`/`chown -R` ধীর ও I/O-ভারী — production-এ সাবধানে।
- **Cost:** ভুল permission-এর data breach-এর খরচ বিশাল।

## 14. Hands-on exercise

1. `alice` (group `developers`) ও আপনার নিজের user দিয়ে `/srv/project` নামে shared directory তৈরি করুন যেখানে `developers` group-এর সবাই লিখতে পারে, নতুন file স্বয়ংক্রিয়ভাবে `developers` group পায়, এবং কেউ অন্যের file মুছতে পারে না। (সংকেত: setgid + sticky = mode `3770`)। `sudo -u alice touch /srv/project/a` দিয়ে যাচাই করুন।
2. `namei -l /home/sami/.ssh/authorized_keys` চালিয়ে পথের প্রতিটি অংশের permission পড়ুন।
3. `umask 077` করে একটি file ও directory তৈরি করুন; `perm_tool.py umask 077`-এর সাথে মেলান। (umask শুধু সেই shell-এ বদলায়।)
4. `perm_tool.py`-তে `check` command-এ একাধিক file-এর জন্য পথের directory-র `x` যাচাই যোগ করুন (`namei`-এর মত)। Test লিখুন।
5. `sudo find / -xdev -perm -4000 -type f 2>/dev/null` দিয়ে setuid file-এর তালিকা `~/devops-notebook/labs/setuid-baseline.txt`-এ রাখুন। প্রতিটি কেন setuid, তিনটির জন্য খুঁজে লিখুন।

## 15. Mini-project — WordPress permission hardening plan

Section 5-এর মত একটি WordPress site-এর জন্য (VM-এ `/var/www/site` নামে নকল structure বানিয়ে, শুধু খালি file দিয়ে) একটি script `fix-perms.sh` লিখুন যা:

1. `--dry-run` সমর্থন করে।
2. Code-এর owner `deploy:deploy`, directory `755`, file `644`।
3. শুধু `wp-content/uploads` `deploy:www-data`, group writable, setgid directory।
4. `wp-config.php` `640`, group `www-data`।
5. শেষে `perm_tool.py audit` চালিয়ে কোনো world-writable না থাকা নিশ্চিত করে।

## 16. Interview প্রশ্ন

1. `chmod 640` ও `chmod 755`-এর অর্থ কী?
2. Directory-তে r, w, x-এর অর্থ file থেকে কীভাবে আলাদা?
3. একটি file মোছার অধিকার কোথা থেকে আসে?
4. umask কী? `027` হলে নতুন file-এর permission কত?
5. setuid কী এবং কেন ঝুঁকিপূর্ণ? একটি বৈধ উদাহরণ দিন।
6. `/tmp`-এ sticky bit কেন?
7. "Permission denied" — কোন ক্রমে তদন্ত করবেন?
8. কেন `chmod 777` খারাপ সমাধান? WordPress-এর upload সমস্যা কীভাবে ঠিক করবেন?

## 17. Self-assessment প্রশ্ন

1. অফিস analogy-র কোন অংশ Linux-এ মেলে না (প্রথম মেলা class)?
2. Mode `0047`-এ owner পড়তে পারে না কেন?
3. umask `022`-এ নতুন directory-র mode হাতে bitwise হিসাব করুন।
4. Section 5-এ www-data কোন class-এ পড়েছিল এবং কেন?
5. Group-এ যোগ করার পরে কেন logout/login দরকার?
6. `audit` test Windows-এ skip হলো কেন, এবং এভাবে skip করা কেন নীরবে pass করানোর চেয়ে ভালো?

## 18. সংক্ষিপ্ত সারাংশ

- Kernel user/group চেনে **UID/GID সংখ্যা** দিয়ে; নাম `/etc/passwd`, `/etc/group`-এ; hash `/etc/shadow`-এ।
- প্রতিটি file: owner, group, ৯টি bit (owner/group/other × r/w/x) + special bit।
- Directory-তে r = তালিকা, w = তৈরি/মোছা, x = প্রবেশ; **মোছার অধিকার directory-তে**।
- **প্রথম মেলা class-ই চূড়ান্ত** (owner → group → other); root বেশিরভাগ যাচাই এড়ায়।
- **umask** নতুন file-এর bit বাদ দেয়; setuid/setgid/sticky-র নির্দিষ্ট ব্যবহার।
- `chmod 777` নয় — সঠিক owner/group ও least privilege; প্রতিটি service আলাদা system user।

## 19. Completion checklist

- [ ] `id`, `getent`, `/etc/passwd`, `/etc/group` পড়ে নিজের ও service user চিনেছি
- [ ] User, group ও service account তৈরি করেছি (snapshot সহ)
- [ ] `chmod` octal ও symbolic দুইভাবে, `chown`, `find ... -exec chmod` ব্যবহার করেছি
- [ ] Exercise ১-এর shared directory কাজ করছে
- [ ] `perm_tool.py`-এর সব command চালিয়েছি; Ubuntu-তে ৮টি test পাস (audit সহ)
- [ ] setuid baseline notebook-এ রেখেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `credentials(7)` — UID, GID, effective ID: https://man7.org/linux/man-pages/man7/credentials.7.html
- `chmod(1)`: https://man7.org/linux/man-pages/man1/chmod.1.html
- `path_resolution(7)`: https://man7.org/linux/man-pages/man7/path_resolution.7.html
- `passwd(5)`, `shadow(5)`, `group(5)`: https://man7.org/linux/man-pages/man5/passwd.5.html
- `umask(2)`: https://man7.org/linux/man-pages/man2/umask.2.html
- Ubuntu Server — User management: https://documentation.ubuntu.com/server/
- Python `stat` module: https://docs.python.org/3/library/stat.html

---

**পরের lesson:** L01-05 — ACL, sudo ও least privilege
