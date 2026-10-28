# L01-17 — Mandatory access control: AppArmor (Ubuntu) ও SELinux (Fedora)

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Advanced |
| **আনুমানিক সময়** | ৩–৪ ঘণ্টা (Fedora অংশ সহ আরো) |
| **পূর্বশর্ত** | [L01-16 — Namespace, cgroup, capability](L01-16-namespaces-cgroups-capabilities.md); [L01-04 — permission](L01-04-users-permissions.md) |
| **Label** | 🖥️ VM (WSL2-তে AppArmor/SELinux enforcement পাওয়া যায় না) · 🎩 Fedora অংশ — SELinux শিখতে একটি Fedora VM সুপারিশকৃত |
| **Tested** | `mac_denials.py`: ৫টি test পাস; নমুনা AppArmor ও SELinux log-এ চালানো (Python 3.14, Windows)। Test-এ একটি bug ধরা পড়ে ঠিক হয়েছে (bind-এর port `src=` field-এ)। নমুনা log হাতে তৈরি (আসল audit format অনুসরণে)। `aa-status`, profile load, `ls -Z`, `restorecon`, `semanage` **Ubuntu/Fedora-তে চালানো হয়নি** — output উদাহরণ। |

---

## 1. এই lesson-এ যা শিখবেন

- **DAC** (L01-04-এর owner/permission) বনাম **MAC** (Mandatory Access Control) — কেন দুটোই দরকার।
- **AppArmor** (Ubuntu default): path-ভিত্তিক profile, enforce/complain mode, local override।
- **SELinux** (Fedora/RHEL default): label/context-ভিত্তিক, type enforcement, boolean, port label।
- Denial log পড়া ও **সঠিক সমাধান** — "বন্ধ করে দাও" কখনো নয়।
- নিজের একটি ছোট AppArmor profile লেখা (Ubuntu) এবং SELinux label সমস্যা ঠিক করা (Fedora)।
- Python দিয়ে AppArmor ও SELinux denial বিশ্লেষণ ও পরবর্তী পদক্ষেপ সুপারিশ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L01-04-এর DAC-এ file-এর মালিক নিজেই ঠিক করেন কে access পাবে, এবং **root সব পারে**। ধরুন Nginx-এ একটি vulnerability দিয়ে আক্রমণকারী `www-data` হিসেবে code চালাতে পারল:

- DAC অনুযায়ী `www-data` যা পড়তে পারে সব পড়তে পারবে — `/tmp`, অন্য world-readable config, হয়তো ভুল permission-এর `.env`।
- কোনোভাবে root পেলে — সব শেষ।

**MAC** একটি অতিরিক্ত, **কেন্দ্রীয় নীতি** যোগ করে যা file-এর মালিক বা root-ও এড়াতে পারে না: "Nginx process শুধু `/var/www/**` পড়তে পারবে, port ৮০/৪৪৩ খুলতে পারবে — আর কিছু নয়।" Hack হলেও ক্ষতি সীমিত (blast radius, L01-05)।

কিন্তু MAC নতুনদের কাছে সবচেয়ে বিরক্তিকর: সব permission ঠিক, তবু "Permission denied"। ফলে অনেকে AppArmor/SELinux বন্ধ করে দেন — এবং সুরক্ষার একটি পুরো স্তর হারান। এই lesson শেখায় কীভাবে denial **পড়ে সঠিকভাবে ঠিক** করতে হয়।

## 3. সহজ ভাষায় পরিচয়

| | DAC (L01-04) | MAC |
|---|---|---|
| কে নীতি ঠিক করে | File-এর মালিক | Administrator/policy (কেন্দ্রীয়) |
| Root | সব পারে | Policy-র অধীন |
| ভিত্তি | UID/GID, mode bit | Profile (AppArmor) বা label (SELinux) |
| ক্রম | আগে DAC যাচাই, তারপর MAC — **দুটোতেই পাস করতে হবে** | |

**AppArmor (Ubuntu):** প্রতিটি program-এর জন্য একটি **profile** — সেই program কোন **path** পড়তে/লিখতে/চালাতে পারবে, কোন capability ও network পাবে। Profile নেই এমন program "unconfined"। দুই mode:

- **enforce** — নিয়ম ভাঙলে আটকায় ও log করে (`apparmor="DENIED"`)।
- **complain** — আটকায় না, শুধু log করে (`apparmor="ALLOWED"`) — profile তৈরির সময় শেখার জন্য।

**SELinux (Fedora/RHEL):** প্রতিটি process ও প্রতিটি file/port-এর একটি **label (context)** — যেমন process `httpd_t`, file `httpd_sys_content_t`। Policy বলে কোন type কোন type-এ কী করতে পারে ("`httpd_t` পড়তে পারে `httpd_sys_content_t`")। মোড: **enforcing**, **permissive** (শুধু log), disabled।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের নিরাপত্তা

- **DAC** = প্রতিটি ঘরের দরজার তালা, ঘরের মালিক চাবি দেন।
- **AppArmor** = প্রতিটি **কর্মীর জন্য** লিখিত তালিকা: "ক্যান্টিন কর্মী: শুধু রান্নাঘর ও স্টোররুম" — কর্মী কোন ঘরের চাবি পেলেন তাতে কিছু যায় আসে না, তালিকার বাইরে গেলেই নিরাপত্তারক্ষী থামান। তালিকা ঘরের **ঠিকানা (path)** দিয়ে লেখা।
- **SELinux** = প্রতিটি কর্মী ও প্রতিটি ঘরে **রঙের ব্যাজ**: "নীল ব্যাজধারী শুধু নীল ঘরে"। ঘরের ঠিকানা বদলালেও (file move) ঘরের রঙ যায় সাথে — যদি ভুল রঙের ঘরে জিনিস রাখা হয়, নীল কর্মী ঢুকতে পারেন না।

### Analogy কোথায় মেলে না

- হাসপাতালে রক্ষী বিবেচনা করে ব্যতিক্রম দেন। MAC **কোনো ব্যতিক্রম জানে না** — policy-তে না থাকলে root-ও আটকাবে। এটি শক্তি, আবার debugging-এ বিভ্রান্তির কারণ।
- রঙের ব্যাজ চোখে দেখা যায়। SELinux label লুকানো — `ls -Z`, `ps -Z` দিয়ে দেখতে হয়। আর `mv` করলে label **সাথে যায়** (পুরোনো জায়গার label), `cp` করলে নতুন জায়গার label পায় — Section 5-এর incident এই পার্থক্য থেকে।
- AppArmor-এর path-ভিত্তিক তালিকা: একই file hard link (L01-03) বা অন্য path দিয়ে পৌঁছালে নিয়ম আলাদা আচরণ করতে পারে — SELinux label inode-এ থাকে, তাই path যাই হোক একই।

## 5. Real-world engineering scenario

### Fedora: "Nginx 403, অথচ permission ঠিক"

**পরিস্থিতি:** একজন engineer website-এর file নিজের home-এ তৈরি করে `sudo mv ~/site/index.html /usr/share/nginx/html/` করলেন। Nginx 403 দিচ্ছে। `ls -l` — permission `644`, owner ঠিক। DAC সব ঠিক।

**Diagnosis:**

```bash
ls -Z /usr/share/nginx/html/index.html
```

উদাহরণ: `unconfined_u:object_r:user_home_t:s0 index.html` — **label `user_home_t`** (home-এর label)। `mv` label সাথে নিয়ে এসেছে। Nginx (`httpd_t`) `user_home_t` পড়তে পারে না।

এই lesson-এর নমুনা log-এ ঠিক এই denial:

```text
2× [selinux/enforced] nginx: httpd_t — read file → index.html (user_home_t)
    next: file-এর label 'user_home_t' — সম্ভবত ভুল জায়গা থেকে move/copy; restorecon -Rv PATH, স্থায়ী হলে semanage fcontext
```

**সমাধান:** `sudo restorecon -Rv /usr/share/nginx/html` — policy অনুযায়ী সেই জায়গার সঠিক label (`httpd_sys_content_t`) বসায়।

**ভুল "সমাধান":** `setenforce 0` — সব নিরাপত্তা বন্ধ; সমস্যা আসলে একটি ভুল label ছিল।

### Fedora: reverse proxy upstream-এ যেতে পারে না

Nginx `proxy_pass http://127.0.0.1:8000` (Module 06) — 502। Log:

```text
1× [selinux/enforced] nginx: httpd_t — name_connect tcp_socket → port 8000 (soundd_port_t)
    next: boolean দেখুন: getsebool httpd_can_network_connect ...
```

Default policy-তে web server যেকোনো port-এ connect করতে পারে না; আর মজার ব্যাপার, Fedora-র policy-তে port ৮০০০-এর label `soundd_port_t`! সমাধান: `sudo setsebool -P httpd_can_network_connect on` (কারণ বুঝে), অথবা app-কে একটি `http_port_t` port-এ চালানো।

### Ubuntu: AppArmor profile-এর বাইরের path

একটি profile-যুক্ত service নতুন জায়গা (`/srv/taskflow/static/`) থেকে file পড়তে চায় — profile শুধু পুরোনো path অনুমোদন করে → `apparmor="DENIED" ... name="/srv/taskflow/static/app.js"`। সমাধান: profile-এর **local override**-এ (`/etc/apparmor.d/local/<profile>`) সেই path যোগ, তারপর profile reload।

## 6. Diagram — access সিদ্ধান্তের স্তর

```text
 nginx (www-data / httpd_t) চায়: open("/srv/www/index.html", O_RDONLY)
          │
          ▼
  ১. DAC (L01-04/05): owner/group/other, ACL ── ব্যর্থ? → EACCES (log: সাধারণত কিছু না)
          │ পাস
          ▼
  ২. Capability (L01-16) প্রযোজ্য হলে
          │
          ▼
  ৩. LSM / MAC:
       Ubuntu → AppArmor profile "/usr/sbin/nginx": "/srv/www/** r" আছে?
       Fedora → SELinux: httpd_t → httpd_sys_content_t : file { read } অনুমোদিত?
          │ না → EACCES + audit log (apparmor="DENIED" / avc: denied)
          ▼ হ্যাঁ
       অনুমোদিত
```

User-এর কাছে দুই ধরনের ব্যর্থতাই একই "Permission denied" — পার্থক্য শুধু **audit log**-এ। তাই "permission ঠিক, তবু denied" হলে প্রথমে audit log।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| DAC | Discretionary Access Control — মালিক-নির্ধারিত (UID/mode) |
| MAC | Mandatory Access Control — কেন্দ্রীয় policy, root-ও অধীন |
| LSM | Linux Security Module — kernel-এর hook যেখানে AppArmor/SELinux যুক্ত |
| AppArmor profile | একটি program-এর অনুমোদিত path, capability, network |
| Enforce / complain | আটকানো + log / শুধু log |
| Unconfined | কোনো profile নেই |
| SELinux context / label | `user:role:type:level` — যেমন `system_u:object_r:httpd_sys_content_t:s0` |
| Type enforcement | কোন process type কোন object type-এ কী করতে পারে |
| Enforcing / permissive | আটকানো / শুধু log |
| Boolean | Policy-র পূর্বনির্ধারিত on/off সুইচ (`httpd_can_network_connect`) |
| `restorecon` | Path-এর জন্য policy-র default label পুনঃস্থাপন |
| `semanage fcontext` / `port` | স্থায়ী label নিয়ম (path বা port) |
| AVC | Access Vector Cache — SELinux denial log-এর নাম |
| `audit2why` / `audit2allow` | Denial-এর কারণ ব্যাখ্যা / নিয়ম প্রস্তাব (শেষ উপায়) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 AppArmor profile-এর গঠন

```text
#include <tunables/global>

/usr/local/bin/labcat {
  #include <abstractions/base>          # libc ইত্যাদি সাধারণ অনুমতি

  /etc/hostname r,                       # শুধু পড়া
  /usr/local/bin/labcat mr,              # নিজের binary map + read

  include if exists <local/usr.local.bin.labcat>   # admin-এর local override
}
```

| Permission | অর্থ |
|---|---|
| `r` / `w` / `a` | read / write / append |
| `m` | memory map executable |
| `ix` / `px` / `ux` | চালানো: একই profile-এ / নিজের profile-এ / unconfined (⚠️) |
| `**` | যেকোনো গভীরতার path |

Profile file `/etc/apparmor.d/`-এ, নাম path-এর `/` → `.` (যেমন `usr.local.bin.labcat`)। Load: `apparmor_parser -r`।

### 8.2 SELinux label কোথা থেকে আসে

- নতুন file সাধারণত parent directory-র label পায়।
- `cp` → নতুন জায়গার (parent-এর) label; `mv` → **পুরোনো label রাখে** (Section 5)।
- `restorecon` → policy-র file-context নিয়ম (`semanage fcontext -l`) অনুযায়ী label।
- Custom path-এ স্থায়ী নিয়ম: `semanage fcontext -a -t httpd_sys_content_t "/srv/www(/.*)?"` তারপর `restorecon -Rv /srv/www`।

### 8.3 সঠিক সমাধানের অগ্রাধিকার

1. **Label/path ঠিক?** (`restorecon`, ভুল জায়গা থেকে file সরানো) — বেশিরভাগ সমস্যা।
2. **Boolean আছে কি?** (`getsebool -a | grep httpd`) — policy লেখকরা সাধারণ চাহিদার সুইচ রেখেছেন।
3. **Port label?** (`semanage port -l | grep http_port_t`) — অস্বাভাবিক port।
4. **AppArmor local override** — profile-এর নির্দিষ্ট নিয়ম যোগ।
5. **শেষ উপায়:** `audit2allow`/নতুন policy module বা `aa-logprof` — প্রতিটি নিয়ম পড়ে বুঝে।

**কখনো:** `setenforce 0`, `SELINUX=disabled`, `systemctl disable apparmor`। Debugging-এ সাময়িক প্রয়োজন হলে শুধু একটি domain permissive (`semanage permissive -a httpd_t`) বা একটি AppArmor profile complain mode — তারপর ফিরিয়ে আনা।

## 9. Practical demonstration

### 9.1 Ubuntu — AppArmor অবস্থা

```bash
sudo aa-status                          # কতগুলো profile, কোনগুলো enforce/complain, কোন process confined
ls /etc/apparmor.d/ | head
ps -eZ | grep -v unconfined | head      # confined process ও তাদের profile
sudo journalctl -k --since today | grep -i apparmor | tail
```

### 9.2 Ubuntu — নিজের profile (⚠️ VM-এ)

```bash
sudo apt install -y apparmor-utils
sudo cp /usr/bin/cat /usr/local/bin/labcat                  # আলাদা binary, যাতে আসল cat প্রভাবিত না হয়
sudo tee /etc/apparmor.d/usr.local.bin.labcat > /dev/null <<'EOF'
#include <tunables/global>

/usr/local/bin/labcat {
  #include <abstractions/base>
  /usr/local/bin/labcat mr,
  /etc/hostname r,
}
EOF
sudo apparmor_parser -r /etc/apparmor.d/usr.local.bin.labcat   # load/replace
labcat /etc/hostname              # অনুমোদিত — hostname দেখাবে
labcat /etc/os-release            # Permission denied — profile-এ নেই (DAC অনুযায়ী সবাই পড়তে পারে!)
sudo journalctl -k -n 3 | grep labcat
```

`/etc/os-release` সবার জন্য readable (DAC পাস) — তবু denied, কারণ MAC। এটাই MAC-এর মূল ধারণা নিজের চোখে।

**Complain mode-এ দেখুন:**

```bash
sudo aa-complain /usr/local/bin/labcat
labcat /etc/os-release            # এখন কাজ করে, কিন্তু log-এ apparmor="ALLOWED"
sudo aa-enforce /usr/local/bin/labcat
```

**Denial বিশ্লেষণ — Python** (File: [`code/L01-17/mac_denials.py`](code/L01-17/mac_denials.py)):

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-17
sudo journalctl -k --since today | grep -i apparmor > /tmp/mac.log
python3 mac_denials.py /tmp/mac.log
python3 mac_denials.py sample-apparmor.log; echo "exit=$?"
```

**নমুনা দিয়ে আসল output:**

```text
  2× [apparmor/enforced] nginx: /usr/sbin/nginx — open file → /srv/taskflow/static/app.js
      next: profile '/usr/sbin/nginx' open নিষেধ করছে '/srv/taskflow/static/app.js' — path কি প্রত্যাশিত? হলে profile/local override-এ নিয়ম যোগ (aa-logprof বা /etc/apparmor.d/local/)
  1× [apparmor/complain] sh: taskflow-demo — exec file → /usr/bin/curl
      next: ...

3 denial(s), 2 unique, 2 enforced (actually blocked)
exit=1
```

(নমুনায় nginx-এর একটি profile আছে ধরা হয়েছে; Ubuntu-র nginx package নিজে profile দেয় কিনা আপনার version-এ `aa-status` দিয়ে যাচাই করুন।) "complain" লাইনটি আটকায়নি — শুধু সতর্কতা; tool তাই enforced আলাদা গোনে।

**Cleanup:**

```bash
sudo apparmor_parser -R /etc/apparmor.d/usr.local.bin.labcat    # unload
sudo rm /etc/apparmor.d/usr.local.bin.labcat /usr/local/bin/labcat
```

### 9.3 Fedora — SELinux (🎩 Fedora VM)

```bash
getenforce                                  # Enforcing
sestatus
ls -Z /usr/share/nginx/html/                # file label
ps -eZ | grep nginx                         # process label (httpd_t)

# Section 5 পুনরুৎপাদন (nginx installed ও চালু থাকলে)
echo "hello" > ~/index.html
sudo mv ~/index.html /usr/share/nginx/html/index.html
ls -Z /usr/share/nginx/html/index.html      # user_home_t!
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1/   # 403
sudo ausearch -m avc -ts recent | tail -3
sudo ausearch -m avc -ts recent | audit2why  # কারণ ব্যাখ্যা
sudo restorecon -Rv /usr/share/nginx/html
curl -s http://127.0.0.1/                    # hello

getsebool httpd_can_network_connect
sudo semanage port -l | grep -E '^http_port_t|soundd_port_t'
```

**Python বিশ্লেষণ:**

```bash
sudo ausearch -m avc -ts today > /tmp/mac.log
python3 mac_denials.py /tmp/mac.log
python3 mac_denials.py sample-selinux.log
```

**নমুনা দিয়ে আসল output:**

```text
  2× [selinux/enforced] nginx: httpd_t — read file → index.html (user_home_t)
      next: file-এর label 'user_home_t' — সম্ভবত ভুল জায়গা থেকে move/copy; restorecon -Rv PATH, স্থায়ী হলে semanage fcontext
  1× [selinux/enforced] nginx: httpd_t — name_connect tcp_socket → port 8000 (soundd_port_t)
      next: boolean দেখুন: getsebool httpd_can_network_connect — চালু করতে setsebool -P (কারণ বুঝে)
  1× [selinux/permissive] sshd: sshd_t — name_bind tcp_socket → port 2222 (unreserved_port_t)
      next: অস্বাভাবিক port — semanage port -a -t <type>_port_t -p tcp PORT

4 denial(s), 3 unique, 3 enforced (actually blocked)
```

তৃতীয়টি L01-13-এর Fedora note: SSH port ২২২২-তে সরাতে `semanage port -a -t ssh_port_t -p tcp 2222` লাগে। প্রথম version-এ এই লাইনে port "?" দেখাচ্ছিল — bind-এর port `src=` field-এ, connect-এর `dest=`-এ; test এই bug ধরেছে।

### 9.4 Test

```bash
python3 -m unittest -v
```

[`test_mac_denials.py`](code/L01-17/test_mac_denials.py)-এর ৫টি test: AppArmor parse, গ্রুপিং ও complain mode; SELinux parse (SYSCALL লাইন বাদ, permissive চেনা, connect ও bind-এর port); তিন ধরনের সুপারিশ (restorecon, boolean, semanage port); context থেকে type বের করা (MLS range সহ); ও CLI exit code।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `KV_RE` | `key=value` ও `key="quoted value"` | Audit log-এর format |
| `apparmor="DENIED"` বনাম `"ALLOWED"` | enforce বনাম complain | Complain আসলে আটকায় না — আলাদা গণনা |
| `AVC_RE` + `permissive=1` | SELinux permissive চেনা | একই কারণে |
| `selinux_type()` | context-এর তৃতীয় অংশ | Type enforcement-এ type-ই মূল |
| `dest` বা `src` | connect বনাম bind | Test-এ ধরা পড়া bug-এর সমাধান |
| `Counter(denials)` | একই denial গ্রুপ | হাজার লাইনের log-এ কয়েকটি অনন্য সমস্যা |
| `suggest()` | label → boolean → port → audit2why | Section 8.3-এর অগ্রাধিকার |
| কখনো "disable" সুপারিশ নয় | | নিরাপত্তা নীতি |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `labcat /etc/hostname` | hostname |
| `labcat /etc/os-release` | Permission denied + kernel log-এ DENIED |
| Fedora `mv` করা file | `user_home_t`, nginx 403; `restorecon`-এর পরে 200 |
| `python3 -m unittest -v` | `Ran 5 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Permission ঠিক, তবু denied | MAC | Ubuntu: `journalctl -k \| grep apparmor`; Fedora: `ausearch -m avc` | Section 8.3 |
| Fedora-তে web server 403 | ভুল label | `ls -Z` | `restorecon`, `semanage fcontext` |
| Fedora-তে proxy 502 | `httpd_can_network_connect` বন্ধ বা port label | AVC `name_connect` | Boolean বা port |
| Port বদলালে service চালু হয় না (Fedora) | Port label নেই | AVC `name_bind` | `semanage port -a` |
| Profile বদলালাম, প্রভাব নেই | Reload হয়নি | `aa-status` | `apparmor_parser -r` |
| WSL2-তে AppArmor কাজ করে না | WSL kernel-এ enforcement নেই | `aa-status` error | VM ব্যবহার করুন |
| `audit2allow` দিয়ে সব allow করে দিলাম | ⚠️ সুরক্ষা দুর্বল | — | নিয়মগুলো পড়ুন; সাধারণত label/boolean-ই সঠিক |

## 13. Security, performance ও cost বিবেচনা

- **Security:** MAC হলো defense in depth-এর একটি স্তর — application hack হলেও ক্ষতি সীমিত। **কখনো বন্ধ নয়**; debugging-এ সাময়িক complain/permissive শুধু একটি profile/domain-এ। Container-এ AppArmor `docker-default` ও SELinux `container_t` container escape কঠিন করে (L01-16)।
- **Performance:** AVC cache-এর কারণে overhead সাধারণত সামান্য।
- **Cost:** ভুল সমাধান (disable) একটি breach-এর খরচ বাড়ায়; সঠিক সমাধান শিখতে সময় লাগে কিন্তু একবারের বিনিয়োগ।

## 14. Hands-on exercise

1. `labcat` profile-এ `/etc/os-release r,` যোগ করে reload করুন — এখন কাজ করে? তারপর local override file দিয়ে একই কাজ করুন (মূল profile না বদলে)।
2. `aa-genprof` বা complain mode + `aa-logprof` দিয়ে একটি ছোট script-এর profile স্বয়ংক্রিয়ভাবে তৈরি করুন; প্রস্তাবিত প্রতিটি নিয়ম পড়ে সিদ্ধান্ত নিন।
3. 🎩 Fedora-তে `/srv/www` নামে নতুন web root বানিয়ে `semanage fcontext` + `restorecon` দিয়ে সঠিক label দিন এবং nginx দিয়ে serve করুন।
4. `mac_denials.py`-তে `--json` output যোগ করুন। Test লিখুন।
5. `BOOLEAN_HINTS`-এ আরেকটি পরিচিত boolean যোগ করুন (যেমন `httpd_t` + home directory-র file পড়া → `httpd_enable_homedirs`) এবং সংশ্লিষ্ট নমুনা লাইন দিয়ে test লিখুন।

## 15. Mini-project — MAC triage runbook

[Runbook template](../templates/runbook-template.md) অনুসরণে "Permission denied কিন্তু permission ঠিক" runbook-এর খসড়া লিখুন — Ubuntu ও Fedora দুটি শাখায়: log কোথায়, `mac_denials.py` দিয়ে সারাংশ, Section 8.3-এর অগ্রাধিকার অনুযায়ী সমাধান, এবং "কখনো disable নয়" নীতি। Module 01-এর Level C lab-এ এটি ব্যবহার হবে।

## 16. Interview প্রশ্ন

1. DAC ও MAC-এর পার্থক্য কী? দুটোই কেন দরকার?
2. AppArmor ও SELinux-এর মূল পার্থক্য কী (path বনাম label)?
3. "Permission ঠিক কিন্তু denied" — কোথায় দেখবেন?
4. Fedora-তে website 403 দিচ্ছে, permission ঠিক — সম্ভাব্য কারণ ও সমাধান?
5. `mv` ও `cp`-এ SELinux label-এর আচরণ কীভাবে আলাদা?
6. SELinux boolean কী? উদাহরণ দিন।
7. কেন `setenforce 0` সমাধান নয়?

## 17. Self-assessment প্রশ্ন

1. হাসপাতাল analogy কোথায় মেলে না?
2. `labcat /etc/os-release` DAC পাস করেও কেন denied?
3. Section 5-এর তিনটি scenario-র সঠিক সমাধান।
4. Complain/permissive denial-কে tool কেন আলাদা গোনে?
5. bind ও connect-এর denial-এ port কোন field-এ থাকে?
6. সমাধানের অগ্রাধিকার-ক্রম কী এবং `audit2allow` কেন শেষে?

## 18. সংক্ষিপ্ত সারাংশ

- **DAC** মালিক-নির্ধারিত, root সব পারে; **MAC** কেন্দ্রীয় policy, root-ও অধীন — দুটোতেই পাস করতে হয়।
- **AppArmor** (Ubuntu): path-ভিত্তিক profile, enforce/complain, local override, `aa-status`, `apparmor_parser`।
- **SELinux** (Fedora): label-ভিত্তিক type enforcement; `ls -Z`, `restorecon`, `semanage`, boolean; `mv` label রাখে।
- "Permission denied" কিন্তু permission ঠিক → audit log; সমাধান: label → boolean → port → নির্দিষ্ট নিয়ম। **কখনো disable নয়।**

## 19. Completion checklist

- [ ] `aa-status` পড়ে confined process চিনেছি
- [ ] `labcat` profile লিখে MAC-এর deny নিজে দেখেছি; complain mode পরীক্ষা
- [ ] (🎩) Fedora-তে label সমস্যা পুনরুৎপাদন ও `restorecon` দিয়ে সমাধান
- [ ] `mac_denials.py` দিয়ে আসল ও নমুনা log বিশ্লেষণ
- [ ] `python3 -m unittest -v`-এ ৫টি test পাস
- [ ] Cleanup সম্পন্ন
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Ubuntu Server — AppArmor: https://documentation.ubuntu.com/server/
- AppArmor project documentation: https://apparmor.net/
- `apparmor.d(5)` (profile syntax): https://manpages.ubuntu.com/manpages/noble/man5/apparmor.d.5.html
- Fedora quick docs (SELinux অংশ খুঁজুন): https://docs.fedoraproject.org/en-US/quick-docs/
- Red Hat — Using SELinux (বিস্তারিত গাইড): https://docs.redhat.com/
- Kernel docs — LSM: https://docs.kernel.org/admin-guide/LSM/index.html

---

**পরের lesson:** L01-18 — Software update, boot process ও system recovery (Module 01-এর শেষ lesson — সাথে Module 01-এর lab ও quiz)
