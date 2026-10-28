# L01-05 — ACL, sudo ও least privilege

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner–Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-04 — Users, groups, ownership ও permission](L01-04-users-permissions.md) |
| **Label** | ⚠️ sudoers ভুল হলে admin অধিকার হারাতে পারেন — VM-এ snapshot নিন, সবসময় `visudo` |
| **Tested** | `acl_check.py` ও `sudoers_audit.py`: ১১টি unit test পাস; `--effective`, `--user ... --op`, sudoers audit চালানো (Python 3.14, Windows)। Sample `getfacl` ও sudoers file হাতে তৈরি। `setfacl`, `getfacl`, `sudo -l`, `visudo` **Ubuntu-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- **Least privilege** নীতি — কেন "কাজের জন্য যতটুকু দরকার, ততটুকুই"।
- সাধারণ owner/group/other permission-এর সীমা, এবং **POSIX ACL** দিয়ে নির্দিষ্ট user/group-কে আলাদা অধিকার।
- ACL-এর **mask** — কেন "দিলাম তবু কাজ করে না"।
- **Default ACL** — নতুন file-এ স্বয়ংক্রিয় অধিকার।
- **sudo** কী করে, `/etc/sudoers` ও `/etc/sudoers.d/`-এর নিয়ম, `visudo`।
- ঝুঁকিপূর্ণ sudo নিয়ম: `NOPASSWD: ALL`, shell escape (less, vim, find, systemctl-এর pager), wildcard।
- Python দিয়ে ACL সিদ্ধান্ত ও sudoers policy audit।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L01-04-এর মডেলে একটি file-এর একটিমাত্র owner ও একটিমাত্র group। বাস্তবে প্রয়োজন আরো সূক্ষ্ম:

- "`report.txt` developers group পড়বে, কিন্তু alice-কে লিখতেও দিতে হবে, আর auditors group-ও পড়বে।" — একটি group-এ সবাইকে ঢোকালে অন্যরাও অতিরিক্ত অধিকার পায়।
- Deploy pipeline-কে শুধু `systemctl restart taskflow` চালাতে দিতে হবে — পূর্ণ root নয়।
- একজন contractor-কে সাময়িক admin অধিকার — কিন্তু কী করলেন তার রেকর্ড চাই।

**ACL** প্রথম সমস্যা, **sudo** দ্বিতীয় ও তৃতীয় সমস্যার সমাধান। দুটোরই লক্ষ্য **least privilege**: প্রতিটি মানুষ ও service শুধু তার কাজের জন্য প্রয়োজনীয় অধিকার পাবে। এতে ভুল (accidental `rm -rf`) ও আক্রমণ (hack হওয়া account) — দুটোর ক্ষতির পরিধি ছোট থাকে। এটিকে বলে **blast radius** কমানো।

## 3. সহজ ভাষায় পরিচয়

### ACL (Access Control List)

সাধারণ permission-এর সাথে অতিরিক্ত entry যোগ করার ব্যবস্থা:

```text
user::rw-          ← owner (সাধারণ permission-এর অংশ)
user:alice:rw-     ← named user: শুধু alice-এর জন্য
group::r--         ← owning group
group:auditors:r-- ← named group
mask::r--          ← named user + সব group entry-র সর্বোচ্চ সীমা
other::---         ← বাকি সবাই
```

ACL থাকলে `ls -l`-এ permission-এর শেষে **`+`** চিহ্ন দেখায় (`-rw-r-----+`)।

### sudo ("superuser do")

একজন অনুমোদিত user-কে **নির্দিষ্ট command** অন্য user (সাধারণত root) হিসেবে চালাতে দেয়, **নিজের password** দিয়ে (root-এর password নয়), এবং **প্রতিটি ব্যবহার log করে**। কে কোন command চালাতে পারবে তা ঠিক হয় `/etc/sudoers` ও `/etc/sudoers.d/*` file-এ।

**root login বনাম sudo:** সরাসরি root হিসেবে কাজ করলে কে কী করল জানা যায় না (সবাই "root"), ভুলের সম্ভাবনা বেশি (সারাক্ষণ সর্বোচ্চ অধিকার)। sudo-তে প্রতিটি privileged command আলাদা, ইচ্ছাকৃত, এবং নামসহ log হয়। Ubuntu-তে default-ভাবে root-এর password lock করা থাকে; প্রথম user `sudo` group-এ থাকেন।

> **Fedora-তে:** admin group হলো `wheel`; installer-এ root password সেট করার বিকল্প থাকতে পারে, তবে নীতি একই — দৈনন্দিন কাজে sudo।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের ওষুধের আলমারি

- সাধারণ permission = আলমারির তিনটি তালা: মালিক নার্স, ward-এর নার্সরা, বাকিরা।
- **ACL** = আলমারির গায়ে একটি তালিকা: "ডা. করিম: খুলতে ও রাখতে পারবেন; pharmacy team: শুধু দেখতে পারবে।"
- **mask** = নিরাপত্তা বিভাগের নিয়ম: "তালিকায় যা-ই লেখা থাকুক, মালিক ছাড়া কেউ ওষুধ সরাতে পারবে না।" তালিকায় ডা. করিমের "সরানো" অধিকার থাকলেও mask সেটি আটকে দেয়।
- **sudo** = নিয়ন্ত্রিত ওষুধ (morphine) বের করার register: নার্স নিজের card দেখিয়ে, register-এ নাম ও সময় লিখে, শুধু নির্দিষ্ট ওষুধ নিতে পারেন — পুরো pharmacy-র চাবি পান না।

### Analogy কোথায় মেলে না

- Register-এ লেখা থাকলেও কেউ ওষুধ নিয়ে অন্য কাজে লাগাতে পারেন — সেটি আলাদা বিষয়। sudo-তে ব্যাপারটি আরো সূক্ষ্ম: অনুমোদিত **একটি** command নিজেই যদি shell খুলতে দেয় (যেমন `less`-এ `!sh`), তাহলে "শুধু এই ওষুধ" আসলে "পুরো pharmacy" হয়ে যায়। এটি software-এর বিশেষ ঝুঁকি, Section 8.4।
- আলমারির তালিকা মানুষ পড়ে বিবেচনা করেন। Kernel ACL-এর **নির্দিষ্ট ক্রমের algorithm** অন্ধভাবে অনুসরণ করে (Section 8.1) — "বিবেচনা" নেই।

## 5. Real-world engineering scenario — "সাময়িক" root যা কখনো সরানো হয়নি

**পরিস্থিতি:** এক বছর আগে একটি incident-এর সময় একজন বাইরের contractor-কে দ্রুত সাহায্যের জন্য একটি server-এ sudo দেওয়া হয়েছিল:

```text
contractor  ALL=(ALL) NOPASSWD: ALL
```

Incident শেষ, contractor-এর চুক্তি শেষ — কিন্তু নিয়ম ও account রয়ে গেল।

**ঘটনার ক্রম:**

1. Contractor-এর ব্যক্তিগত laptop থেকে তাঁর SSH private key চুরি হলো (অন্য একটি ঘটনায়)।
2. আক্রমণকারী সেই key দিয়ে server-এ login করল।
3. `sudo -l` চালিয়ে দেখল: password ছাড়া সব কিছু root হিসেবে।
4. পুরো server আক্রমণকারীর নিয়ন্ত্রণে।

**কী ভুল ছিল (একাধিক স্তরে):**

- **NOPASSWD: ALL** — একটি key চুরি = পূর্ণ root।
- **কোনো মেয়াদ ছিল না** — "সাময়িক" অধিকার স্থায়ী হয়ে গেছে।
- **Audit হয়নি** — কেউ নিয়মিত sudoers পর্যালোচনা করেনি।
- Account offboarding প্রক্রিয়া ছিল না।

**কীভাবে ধরা যেত:** sudoers নিয়মিত audit (এই lesson-এর `sudoers_audit.py` প্রথম লাইনেই `CRITICAL` দেখায়), sudo log পর্যালোচনা (`journalctl _COMM=sudo`), এবং "temporary" অধিকারের সাথে ticket ও মেয়াদ।

## 6. Diagram

### POSIX ACL access algorithm

```text
 process (user, groups) চায় op (r/w/x)
          │
          ▼
  user == file owner? ──yes──► user:: entry   (mask প্রযোজ্য নয়) ──► সিদ্ধান্ত
          │ no
          ▼
  named user:NAME: entry আছে? ──yes──► entry AND mask ──► সিদ্ধান্ত
          │ no
          ▼
  user-এর কোনো group মেলে (group:: বা group:NAME:)? ──yes──►
          │                    মেলা entry-গুলোর যেকোনোটিতে (AND mask) op আছে? → allowed
          │                    কোনোটিতে নেই → DENIED (other আর দেখা হয় না)
          │ no
          ▼
  other:: entry ──► সিদ্ধান্ত
```

### sudo flow

```text
 user$ sudo systemctl restart taskflow
          │
          ▼
  sudo (setuid-root program)
    ├─ /etc/sudoers + sudoers.d পড়ে: এই user, এই host, এই command অনুমোদিত?
    ├─ প্রয়োজনে user-এর নিজের password (PAM দিয়ে) — কিছুক্ষণ cache হয়
    ├─ environment পরিষ্কার করে (env_reset), PATH = secure_path
    ├─ log: journald / /var/log/auth.log  ("sami : TTY=pts/0 ; PWD=... ; USER=root ; COMMAND=...")
    └─ command root হিসেবে চালায়
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Least privilege | কাজের জন্য ন্যূনতম প্রয়োজনীয় অধিকার |
| Blast radius | একটি ভুল বা আক্রমণে কতটা ক্ষতি ছড়াতে পারে |
| ACL | File-এ অতিরিক্ত user/group-ভিত্তিক permission entry |
| Named user / group entry | নির্দিষ্ট নামের user/group-এর জন্য ACL entry |
| mask | Named user ও সব group entry-র সর্বোচ্চ সীমা |
| Effective permission | Entry AND mask — আসলে যা কার্যকর |
| Default ACL | Directory-তে রাখা ACL, যা ভেতরে নতুন তৈরি file/directory উত্তরাধিকারসূত্রে পায় |
| sudoers | কে কী sudo দিয়ে চালাতে পারবে তার নিয়ম |
| visudo | sudoers নিরাপদে সম্পাদনা: lock + syntax যাচাই |
| NOPASSWD | sudo-তে password না চাওয়া |
| Shell escape | কোনো program-এর ভেতর থেকে shell খোলার উপায় (যেমন `less`-এ `!sh`) |
| secure_path | sudo command-এর জন্য নির্দিষ্ট নিরাপদ PATH |
| env_reset | sudo-তে caller-এর environment variable বাদ দেওয়া |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 ACL ও mask-এর সম্পর্ক

- ACL-এ named entry থাকলে `ls -l`-এর **group column আসলে mask দেখায়**, owning group-এর permission নয় — এটি একটি সাধারণ বিভ্রান্তি।
- `chmod g-w file` করলে আসলে **mask** বদলায় — ফলে সব named user/group-এর লেখার অধিকার চলে যায়।
- `setfacl -m u:alice:rw file` চালালে setfacl সাধারণত mask-কে প্রয়োজন অনুযায়ী পুনর্গণনা করে বাড়ায়; কিন্তু পরে কেউ `chmod` চালালে mask কমে যেতে পারে।

### 8.2 Default ACL

Directory-তে default ACL থাকলে ভেতরে নতুন তৈরি file সেই ACL উত্তরাধিকার পায় — umask-এর পরিবর্তে (default ACL থাকলে umask প্রযোজ্য হয় না)। Shared project directory-তে এটি setgid-এর (L01-04) চেয়ে শক্তিশালী সমাধান: একাধিক group-কে আলাদা অধিকার।

### 8.3 sudoers syntax

```text
WHO    WHERE = (AS_WHOM)  [TAGS:] COMMANDS
deploy ALL   = (root)     NOPASSWD: /usr/bin/systemctl restart taskflow
%sudo  ALL   = (ALL:ALL)  ALL
```

| অংশ | অর্থ |
|---|---|
| `deploy` / `%sudo` | user / `%` দিয়ে group |
| `ALL` (WHERE) | যেকোনো host (একই sudoers অনেক server-এ ব্যবহার হলে অর্থবহ) |
| `(root)` / `(ALL:ALL)` | কোন user (ও group) হিসেবে চালানো যাবে |
| `NOPASSWD:` | password চাইবে না |
| Command | **absolute path**, প্রয়োজনে নির্দিষ্ট argument সহ; argument না দিলে যেকোনো argument অনুমোদিত |

নিয়ম:

- সম্পাদনা সবসময় `sudo visudo` (মূল file) বা `sudo visudo -f /etc/sudoers.d/deploy` দিয়ে। Syntax ভুল হলে visudo save করতে দেয় না — নাহলে ভুল sudoers-এ **কেউই sudo করতে পারবে না**।
- নিজের নিয়ম `/etc/sudoers.d/`-এ আলাদা file-এ (মূল file package update-এ বদলাতে পারে)। File নামে `.` বা `~` থাকলে উপেক্ষিত হয়; permission `0440`।
- পরে আসা নিয়ম আগেরটিকে override করতে পারে (শেষ মিল জেতে) — ক্রম গুরুত্বপূর্ণ।

### 8.4 "নির্দিষ্ট command" কেন যথেষ্ট নয়

একটি নিরীহ মনে হওয়া command নিজেই root shell দিতে পারে:

| অনুমোদিত command | কীভাবে root shell |
|---|---|
| `less /var/log/x` | `less`-এর ভেতরে `!sh` |
| `vim file` | `:!sh` বা `:shell` |
| `find ... ` | `-exec /bin/sh \;` |
| `tar ...` | `--checkpoint-action=exec=sh` |
| `systemctl status x` | output pager (`less`) খোলে → `!sh` |
| `python3 script.py` | script-এর জায়গায় নিজের code; বা `python3 -c` |
| `cp`, `tee` | `/etc/sudoers` বা `/etc/shadow` overwrite |
| wildcard `/var/log/*` | `/var/log/../../etc/shadow` জাতীয় argument |

এমন program-এর পূর্ণ তালিকা ও কৌশল GTFOBins প্রকল্পে সংকলিত (security community-র পরিচিত reference)।

**নিরাপদ বিকল্প:**

- Log দেখার জন্য sudo-র বদলে user-কে `adm` বা `systemd-journal` group-এ (শুধু পড়ার অধিকার)।
- নির্দিষ্ট কাজের জন্য root-owned, অন্যদের লেখা-অযোগ্য **wrapper script** (absolute path, argument যাচাই করে) এবং sudo-তে শুধু সেই script।
- `systemctl`-এর ক্ষেত্রে নির্দিষ্ট argument সহ: `/usr/bin/systemctl restart taskflow` (status বাদ, বা `--no-pager` সহ)।
- File সম্পাদনার অনুমতি দিতে `sudoedit` (editor user হিসেবে চলে, শুধু file লেখা root হিসেবে)।
- Systemd service-এর বিশেষ অধিকার দরকার হলে sudo নয়, unit file-এ capability (L01-16)।

## 9. Practical demonstration (Ubuntu VM — snapshot নিন)

### 9.1 ACL

```bash
sudo apt install -y acl                     # getfacl/setfacl (Ubuntu-তে সাধারণত আগেই থাকে)
cd "$(mktemp -d)"
echo "q3 numbers" > report.txt
chmod 640 report.txt
sudo setfacl -m u:alice:rw report.txt       # named user entry
sudo setfacl -m g:auditors:r report.txt     # named group (group আগে তৈরি করুন: sudo groupadd auditors)
getfacl report.txt
ls -l report.txt                            # শেষে + চিহ্ন
```

উদাহরণ `getfacl` output:

```text
# file: report.txt
# owner: sami
# group: sami
user::rw-
user:alice:rw-
group::r--
group:auditors:r--
mask::rw-
other::---
```

**mask-এর প্রভাব দেখুন:**

```bash
chmod g-w report.txt                        # আসলে mask থেকে w বাদ
getfacl report.txt                          # user:alice:rw-   #effective:r--
sudo -u alice sh -c 'echo x >> report.txt'  # Permission denied — mask আটকাচ্ছে
```

ACL সরানো: `setfacl -x u:alice report.txt` (একটি entry), `setfacl -b report.txt` (সব)।

**Default ACL (shared directory):**

```bash
mkdir shared
sudo setfacl -d -m g:auditors:rx shared     # -d = default
touch shared/new.txt
getfacl shared/new.txt                      # auditors entry উত্তরাধিকার পেয়েছে
```

> **Fedora-তে:** একই command (`acl` package সাধারণত installed); btrfs ও ext4 দুটোতেই ACL সমর্থিত।

### 9.2 ACL সিদ্ধান্ত — Python

File: [`code/L01-05/acl_check.py`](code/L01-05/acl_check.py) · Sample: [`sample-getfacl.txt`](code/L01-05/sample-getfacl.txt) (mask `r--`)

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-05
python3 acl_check.py sample-getfacl.txt --effective
python3 acl_check.py sample-getfacl.txt --user alice --groups alice,developers --op w; echo "exit=$?"
```

**আসল output (repository-তে চালানো):**

```text
user::rw-   (owner sami)
user:alice:rw-   effective r--
user:bob:r--   effective r--
group::r--   effective r--  (group developers)
group:auditors:r--   effective r--
mask::r--
other::---
DENIED  named user entry user:alice:rw- (effective r--)
exit=1
```

alice-এর entry `rw-`, কিন্তু mask `r--` → effective `r--` → লেখা DENIED। নিজের আসল file দিয়ে:

```bash
getfacl -p /path/to/file > /tmp/acl.txt
python3 acl_check.py /tmp/acl.txt --user alice --groups "$(id -Gn alice | tr ' ' ',')" --op w
```

`id -Gn alice` = alice-এর সব group-এর নাম (space দিয়ে); `tr ' ' ','` space-কে কমা করে।

### 9.3 sudo পর্যবেক্ষণ

```bash
sudo -l                                     # আমি কী কী sudo করতে পারি
sudo -l -U alice                            # alice কী পারে (root লাগে)
sudo journalctl _COMM=sudo --since today    # আজকের sudo ব্যবহার
sudo grep sudo /var/log/auth.log | tail     # Ubuntu-তে auth log
```

> **Fedora-তে:** `/var/log/auth.log` নেই — `journalctl _COMM=sudo` বা `/var/log/secure` (rsyslog থাকলে)।

### 9.4 Least-privilege sudo নিয়ম যোগ (⚠️)

```bash
sudo useradd --system --shell /usr/sbin/nologin deploybot 2>/dev/null || true
sudo visudo -f /etc/sudoers.d/deploybot
```

Editor-এ লিখুন:

```text
# Ticket OPS-123: CI restarts taskflow after deploy. Owner: platform team. Review: 2027-01-31
deploybot ALL=(root) NOPASSWD: /usr/bin/systemctl restart taskflow
```

Save করলে visudo syntax যাচাই করে। তারপর:

```bash
sudo visudo -c                              # সব sudoers file-এর syntax যাচাই
sudo -l -U deploybot
ls -l /etc/sudoers.d/deploybot              # -r--r----- root root হওয়া উচিত
```

Comment-এ ticket, owner ও review তারিখ — Section 5-এর "ভুলে যাওয়া অধিকার" সমস্যার সহজ প্রতিকার।

> **Fedora-তে:** একই (`visudo` ও `/etc/sudoers.d/`); `%wheel` লাইন মূল file-এ থাকে।

### 9.5 sudoers policy audit — Python

File: [`code/L01-05/sudoers_audit.py`](code/L01-05/sudoers_audit.py) · Sample: [`sample-sudoers.txt`](code/L01-05/sample-sudoers.txt) (ইচ্ছাকৃত ভুল সহ)

```bash
python3 sudoers_audit.py sample-sudoers.txt; echo "exit=$?"
```

**আসল output:**

```text
CRITICAL line 15  contractor: full root via ALL without password
HIGH     line 8   root: full root via ALL
HIGH     line 9   %sudo: full root via ALL
HIGH     line 12  deploy: systemctl can spawn a shell or write files as root
HIGH     line 18  support: less can spawn a shell or write files as root
HIGH     line 18  support: wildcard in '/usr/bin/less /var/log/*' can be abused with extra arguments
HIGH     line 21  backup: tar can spawn a shell or write files as root
HIGH     line 21  backup: find can spawn a shell or write files as root
HIGH     line 21  backup: wildcard in '/usr/bin/find /var/www -name *.php' can be abused with extra arguments
HIGH     line 24  env_keep includes a library/loader variable
MEDIUM   line 12  deploy: NOPASSWD for '/usr/bin/systemctl restart taskflow' — document why
MEDIUM   line 12  deploy: NOPASSWD for '/usr/bin/systemctl status taskflow' — document why
MEDIUM   line 21  backup: command without absolute path: tar
MEDIUM   line 21  backup: NOPASSWD for 'tar -czf /backup/etc.tgz /etc' — document why
MEDIUM   line 21  backup: NOPASSWD for '/usr/bin/find /var/www -name *.php' — document why
summary: CRITICAL=1  HIGH=9  MEDIUM=5
exit=1
```

**Finding ব্যাখ্যা করুন, অন্ধভাবে নয়:**

- `root` ও `%sudo`-র ALL — **প্রত্যাশিত** (Ubuntu default)। Tool ঝুঁকি দেখাচ্ছে, কিন্তু সিদ্ধান্ত আপনার: admin group-এ কে আছে নিয়মিত পর্যালোচনা করুন।
- `contractor` — **সরানো উচিত** (Section 5)।
- `deploy` systemctl — `restart` নির্দিষ্ট argument সহ থাকায় তুলনামূলক নিরাপদ, কিন্তু **`status` pager খোলে** → `--no-pager` যোগ করুন বা status-এর জন্য sudo-ই লাগে না (`systemctl status` সাধারণ user-ও দেখতে পারে)।
- `support` less + wildcard — `adm` group-এ যোগ করে sudo ছাড়াই log পড়তে দিন।
- `backup` — wrapper script দিয়ে প্রতিস্থাপন।

আসল system-এ (root দিয়ে পড়ে, Python script নিজে root হিসেবে চালাবেন না):

```bash
sudo cat /etc/sudoers /etc/sudoers.d/* > /tmp/sudoers-all.txt
python3 sudoers_audit.py /tmp/sudoers-all.txt
rm /tmp/sudoers-all.txt
```

⚠️ `/tmp/sudoers-all.txt`-এ আপনার system-এর নিরাপত্তা নীতি আছে — কাজ শেষে মুছুন।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_l01_05.py`](code/L01-05/test_l01_05.py)-এর ১১টি test: getfacl parse, mask দিয়ে named user সীমিত, owner-এ mask প্রযোজ্য নয়, group ও other, named user group-এর আগে, ভুল input; sudoers-এ CRITICAL প্রথমে, প্রত্যাশিত সব finding, continuation লাইনের সঠিক লাইন নম্বর, একই লাইনে একবার report, ও পরিষ্কার নিয়মে কোনো finding নেই।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `Acl.masked()` | `bits & mask` | Effective permission-এর সংজ্ঞা |
| `decide()`-এ owner-এ mask নেই | `user::` entry সরাসরি | acl(5)-এর নিয়ম |
| Group অংশে `any(...)` | মেলা যেকোনো group entry-তে অধিকার থাকলেই allowed | POSIX ACL-এ group entry-গুলোর মধ্যে "যেকোনো একটি যথেষ্ট"; কিন্তু group মিললে other আর দেখা হয় না |
| `default:` লাইন বাদ | এই file-এর access নয় | Default ACL শুধু directory-তে নতুন file-এর জন্য |
| `join_continuations()` | `\` দিয়ে ভাঙা লাইন জোড়া | sudoers syntax-এ সমর্থিত; লাইন নম্বর শুরুরটা রাখা হয় (bug খুঁজে ঠিক করা হয়েছে) |
| `split_commands()` | `NOPASSWD:` জাতীয় tag আলাদা | একাধিক tag থাকতে পারে (`NOPASSWD: NOEXEC:`) |
| `re.sub(r"\d+...$", "", base)` | `python3.12` → `python` | Version-যুক্ত নাম চেনা |
| `escape_reported` set | এক লাইনে একবার | এই repository লেখার সময় duplicate finding ধরা পড়েছিল |
| Exit 1 on CRITICAL/HIGH | CI-তে policy gate | L00-04-এর gate ধারণা |

**সীমাবদ্ধতা (সৎভাবে):** এটি একটি শিক্ষামূলক static audit। `User_Alias`/`Cmnd_Alias` expand করে না, `!` (negation) নিয়ম বোঝে না, এবং syntax যাচাই করে না — সেজন্য `visudo -c`। Production-এ ব্যবহারের আগে এই সীমা মনে রাখুন।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| ACL যোগের পরে `ls -l` | permission-এর শেষে `+` |
| `chmod g-w`-এর পরে `getfacl` | named entry-তে `#effective:r--` |
| `sudo visudo -c` | `parsed OK` |
| `sudo -l -U deploybot` | শুধু `systemctl restart taskflow` |
| `python3 -m unittest -v` | `Ran 11 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| ACL দিলাম তবু লিখতে পারে না | mask | `getfacl` — `#effective` | `setfacl -m m::rw file` (বুঝে) |
| `ls -l`-এর group column ভুল দেখায় | ACL থাকলে সেটি mask | `getfacl` | — |
| `setfacl: Operation not supported` | Filesystem ACL সমর্থন করে না (কিছু পুরোনো mount, vfat) | `findmnt -no FSTYPE,OPTIONS --target .` | ext4/xfs/btrfs ব্যবহার করুন |
| `user is not in the sudoers file. This incident will be reported.` | User sudo group-এ নেই | `id` | `sudo usermod -aG sudo user` (অন্য admin দিয়ে); তারপর login আবার |
| sudoers ভেঙে গেছে, কেউ sudo পারছে না | visudo ছাড়া সম্পাদনা | `pkexec visudo` বা recovery mode | ⚠️ এজন্যই snapshot ও `visudo` |
| sudo-তে command "not found" | sudo-র `secure_path`-এ নেই | `sudo env \| grep PATH` | Absolute path ব্যবহার করুন |
| `/etc/sudoers.d/` file উপেক্ষিত | নামে `.` আছে (যেমন `deploy.conf`) | — | নাম বদলান (`deploy`) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `NOPASSWD: ALL` কখনো মানুষের account-এ নয়; automation-এ শুধু নির্দিষ্ট command।
  - Shell-escape-সক্ষম program sudo-তে দেবেন না; wrapper script বা group অধিকার।
  - প্রতিটি sudo নিয়মে owner, কারণ, মেয়াদ (comment)।
  - Sudo log কেন্দ্রীয়ভাবে সংগ্রহ (Module 17) — আক্রমণকারী স্থানীয় log মুছে ফেলতে পারে।
  - ACL ভুলে যাওয়া সহজ (`ls -l`-এ শুধু `+`) — backup/restore-এ ACL রক্ষিত হয় কিনা যাচাই করুন (`tar --acls`, `rsync -A`)।
- **Performance:** নগণ্য।
- **Cost:** অতিরিক্ত অধিকারের breach-এর খরচ; নিয়মিত access review একটি সস্তা নিয়ন্ত্রণ।

## 14. Hands-on exercise

1. `/srv/reports` directory বানান: owner `sami`, `developers` group পড়া-লেখা, `auditors` group শুধু পড়া, অন্যরা কিছু না — **default ACL সহ**, যাতে নতুন file-ও একই নিয়ম পায়। `sudo -u alice` ও একজন auditor দিয়ে যাচাই করুন।
2. `acl_check.py`-তে `--path` দিয়ে সরাসরি file দিলে `getfacl` subprocess (list argument) দিয়ে চালিয়ে ACL পড়ার option যোগ করুন। Linux না হলে স্পষ্ট error।
3. `sample-sudoers.txt` copy করে সব CRITICAL ও HIGH ঠিক করুন (`root`/`%sudo` ছাড়া), যাতে audit-এ শুধু সেগুলো থাকে। প্রতিটি পরিবর্তনের কারণ comment-এ লিখুন।
4. `sudoers_audit.py`-তে নতুন নিয়ম: rule-এর লাইনের ঠিক আগের comment-এ "Review:" তারিখ না থাকলে MEDIUM। Test লিখুন।
5. VM-এ `sudo less /etc/hostname` চালিয়ে less-এর ভেতরে `!id` লিখুন (⚠️ শুধু নিজের lab-এ)। কী user দেখাচ্ছে? এই অভিজ্ঞতা notebook-এ লিখুন।

## 15. Mini-project — access review report

একটি read-only script `access_review.py` লিখুন যা (sudo দিয়ে প্রস্তুত করা input file থেকে):

1. `/etc/passwd` থেকে login-সক্ষম user তালিকা (L01-04-এর `perm_tool.py users`)।
2. `/etc/group` থেকে `sudo`/`adm` (Fedora-তে `wheel`) group-এর সদস্য।
3. sudoers audit-এর finding।
4. প্রতিটি user-এর জন্য একটি সারিতে: login shell, admin group, sudo নিয়ম, ঝুঁকি।

Output Markdown table, যা একজন manager পড়ে "এই অধিকার এখনো দরকার কি?" সিদ্ধান্ত নিতে পারেন। এটি Project 1 ও Module 19-এর (access review) ভিত্তি।

## 16. Interview প্রশ্ন

1. Least privilege কী? Linux server-এ তিনটি উদাহরণ দিন।
2. ACL কখন দরকার, সাধারণ permission কখন যথেষ্ট?
3. ACL mask কী? "ACL দিলাম তবু কাজ করে না" — প্রথমে কী দেখবেন?
4. Root login-এর চেয়ে sudo কেন ভালো?
5. `NOPASSWD: ALL` কেন বিপজ্জনক? Automation-এ কীভাবে নিরাপদে sudo দেবেন?
6. `sudo less` বা `sudo vim` দেওয়া কেন পূর্ণ root দেওয়ার সমান?
7. sudoers কেন `visudo` দিয়ে সম্পাদনা করবেন?

## 17. Self-assessment প্রশ্ন

1. হাসপাতাল analogy দিয়ে ACL, mask ও sudo ব্যাখ্যা করুন; কোথায় মেলে না?
2. Sample-এ alice-এর `rw-` entry থাকা সত্ত্বেও লেখা DENIED কেন? হাতে AND হিসাব দেখান।
3. bob `developers` group-এ থাকলেও কেন named user entry আগে মেলে?
4. Section 5-এর incident-এ চারটি ভুল কী ছিল?
5. `systemctl status` কীভাবে shell escape দেয়, এবং নিরাপদ বিকল্প কী?
6. `sudoers_audit.py`-এর তিনটি সীমাবদ্ধতা কী?

## 18. সংক্ষিপ্ত সারাংশ

- **Least privilege** = ন্যূনতম অধিকার → ছোট blast radius।
- **ACL** নির্দিষ্ট user/group-কে অধিকার দেয়; **mask** named ও group entry-র সর্বোচ্চ সীমা; **effective = entry AND mask**; owner-এ mask প্রযোজ্য নয়। **Default ACL** নতুন file-এ উত্তরাধিকার।
- **sudo** = নিজের password, নির্দিষ্ট command, log। সম্পাদনা শুধু `visudo`; নিজের নিয়ম `/etc/sudoers.d/`-এ।
- **নির্দিষ্ট command-ও বিপজ্জনক** হতে পারে (shell escape, wildcard, pager) — wrapper script, group অধিকার বা `sudoedit`।
- নিয়মিত access review ও "সাময়িক" অধিকারের মেয়াদ।

## 19. Completion checklist

- [ ] `setfacl`/`getfacl` দিয়ে named user, named group ও default ACL প্রয়োগ করেছি
- [ ] mask-এর প্রভাব নিজে দেখেছি (`#effective`)
- [ ] `visudo -f /etc/sudoers.d/...` দিয়ে একটি নির্দিষ্ট-command নিয়ম যোগ ও `sudo -l -U` দিয়ে যাচাই
- [ ] `sudo journalctl _COMM=sudo`-এ নিজের sudo ব্যবহার দেখেছি
- [ ] দুটি Python tool চালিয়েছি এবং sample sudoers-এর finding ব্যাখ্যা করেছি
- [ ] `python3 -m unittest -v`-এ ১১টি test পাস
- [ ] Exercise ১ ও ৩ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- `acl(5)` — POSIX ACL ও access check algorithm: https://man7.org/linux/man-pages/man5/acl.5.html
- `setfacl(1)`: https://man7.org/linux/man-pages/man1/setfacl.1.html
- `getfacl(1)`: https://man7.org/linux/man-pages/man1/getfacl.1.html
- sudo project documentation (sudoers manual): https://www.sudo.ws/docs/
- Ubuntu Server — Security / users: https://documentation.ubuntu.com/server/
- GTFOBins (shell escape-সক্ষম Unix binary-র তালিকা): https://gtfobins.github.io/

---

**পরের lesson:** L01-06 — Shell fundamentals: quoting, expansion, environment variable, exit code
