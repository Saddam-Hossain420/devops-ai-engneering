# L01-02 — Package management: apt, dpkg, repository (Fedora-তে dnf, rpm)

| | |
|---|---|
| **Module** | 01 — Linux and Operating Systems |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L01-01 — Linux architecture](L01-01-linux-architecture.md) |
| **Label** | 🎩 Fedora অংশ আছে · ⚠️ install/remove system বদলায় — VM-এ snapshot নিন |
| **Tested** | `pkg_inventory.py`: ৫টি unit test পাস ও `top`/`diff` চালানো (Python 3.14, Windows)। Sample inventory file হাতে তৈরি, আসল dpkg/rpm-এর format-এ। `apt`, `dpkg`, `dnf`, `rpm` command **এই session-এ চালানো হয়নি** — output উদাহরণ হিসেবে চিহ্নিত; Ubuntu 24.04 ও Fedora 41 লক্ষ্য করে লেখা। |

---

## 1. এই lesson-এ যা শিখবেন

- Package কী, কেন package manager দরকার, এবং dependency কীভাবে সমাধান হয়।
- **Debian/Ubuntu stack:** `dpkg` (নিচের স্তর) ও `apt` (উপরের স্তর)।
- **Repository**, signature ও trust — package নিরাপদে আসে কীভাবে।
- Package version-এর গঠন (epoch, upstream, revision)।
- Update, upgrade, hold, autoremove, history ও log।
- **Fedora stack:** `rpm` ও `dnf` — পার্থক্য ও মিল।
- Python দিয়ে package inventory বিশ্লেষণ: সবচেয়ে বড় package ও **দুই server-এর drift**।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Package manager না থাকলে software install মানে: website থেকে source নামানো, compile, কোন library লাগবে খুঁজে বের করা, সেগুলোও compile, তারপর কোথায় কোন file গেল কেউ জানে না। Update-এর সময় সব আবার; uninstall প্রায় অসম্ভব। আর নিরাপত্তা? নামানো file আসলেই মূল লেখকের কিনা, কেউ জানে না।

Package manager সমাধান করে:

- **Dependency resolution:** `nginx` install করলে তার দরকারি library নিজেই আনে।
- **Tracking:** কোন package কোন file install করেছে, কোন version — সব database-এ।
- **Update:** একটি command-এ সব security fix।
- **Trust:** cryptographic signature দিয়ে যাচাই যে package বিশ্বস্ত repository থেকেই এসেছে এবং বদলানো হয়নি।
- **Reproducibility:** একই package list দিয়ে আরেকটি server একই রকম বানানো (Module 13-এ Ansible)।

DevOps-এ এর গুরুত্ব: অধিকাংশ security vulnerability fix আসে package update হিসেবে। Server-গুলোর package version আলাদা হলে (drift) একটিতে bug আছে, অন্যটিতে নেই — "কিছু server-এ সমস্যা" ধরনের রহস্যময় incident।

## 3. সহজ ভাষায় পরিচয়

**Package কী?** একটি archive file (`.deb` বা `.rpm`) যাতে আছে: program-এর file, metadata (নাম, version, dependency, বিবরণ), এবং install/remove-এর সময় চালানোর script।

**দুই স্তর:**

| স্তর | Ubuntu/Debian | Fedora/RHEL | কাজ |
|---|---|---|---|
| নিচের স্তর | `dpkg` | `rpm` | একটি local package file install/remove; database রাখা। Dependency নিজে আনে না |
| উপরের স্তর | `apt` (`apt-get`, `apt-cache`) | `dnf` | Repository থেকে খোঁজা, নামানো, dependency সমাধান, তারপর নিচের স্তরকে দিয়ে install |

**Repository কী?** একটি server (HTTP) যেখানে হাজার হাজার package ও তাদের index থাকে, signature সহ। Ubuntu-র official repository-গুলোর নাম: `main` (Canonical সমর্থিত), `universe` (community), `restricted`, `multiverse`।

**`apt` বনাম `apt-get`:** দুটোই একই engine। `apt` মানুষের জন্য সুন্দর output (progress bar); `apt-get`-এর output স্থির — **script-এ `apt-get` ব্যবহার করুন** (apt নিজেই এ বিষয়ে সতর্ক করে)।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### সুপারশপ ও বাড়ির ভাঁড়ার

- **Repository** = বিশ্বস্ত সুপারশপ, যার প্রতিটি পণ্যে সিল (signature) আছে।
- **apt** = দোকানের কর্মচারী, যিনি জানেন "বিরিয়ানির জন্য চাল, মাংস, মশলা সব লাগবে" — তালিকা দিলেই সব নিয়ে আসেন (dependency)।
- **dpkg** = বাড়ির ভাঁড়ারের রক্ষক, যিনি যা এলো তা তাকে সাজিয়ে রাখেন এবং খাতায় লেখেন কোন জিনিস কোথায়। কিন্তু নিজে বাজারে যান না।
- **`apt update`** = দোকানের নতুন মূল্যতালিকা আনা (পণ্য কেনা নয়)।
- **`apt upgrade`** = তালিকা দেখে পুরোনো জিনিস নতুন দিয়ে বদলানো।

### Analogy কোথায় মেলে না

- দোকানের সিল নকল করা সহজ হতে পারে; package signature **cryptographic** — private key ছাড়া নকল করা কার্যত অসম্ভব। কিন্তু আপনি যদি একটি অবিশ্বস্ত repository-কে (যেমন অজানা PPA) নিজে "বিশ্বস্ত" ঘোষণা করেন, সিল আর রক্ষা করে না।
- বাজারের জিনিস একে অপরকে বদলায় না। Package upgrade একটি shared library বদলালে **একসাথে বহু program-এর আচরণ বদলাতে পারে** — তাই production-এ upgrade পরীক্ষা করে নিতে হয়।
- ভাঁড়ারের খাতা ভুল হলে আপনি নিজে দেখে ঠিক করেন। dpkg-র database (`/var/lib/dpkg/`) হাতে বদলালে system অসঙ্গত হয়ে যায় — কখনো করবেন না।

## 5. Real-world engineering scenario — "কিছু server-এ TLS error"

**পরিস্থিতি:** একটি load balancer-এর পেছনে দুটি Ubuntu server (server-a, server-b)। User-দের প্রায় অর্ধেক request-এ TLS-সংক্রান্ত error। এক মাস আগে একটি OpenSSL security update বেরিয়েছিল।

**Diagnosis:**

1. Error অর্ধেক request-এ → সন্দেহ: দুটি server আলাদা আচরণ করছে।
2. দুটি server-এর package inventory তুলনা করা হলো (এই lesson-এর tool):

   ```text
   version differs: 2
     ~ curl: 8.5.0-2ubuntu10.4 -> 8.5.0-2ubuntu10.1
     ~ openssl: 3.0.13-0ubuntu3.4 -> 3.0.13-0ubuntu3.1
   ```

3. server-b-তে openssl পুরোনো — automatic update বন্ধ ছিল, কেউ হাতে update করেননি।
4. সাথে আরেকটি অপ্রত্যাশিত জিনিস: `+ telnetd` — server-b-তে কেউ debug করতে গিয়ে telnet server install করে রেখে গেছেন। Telnet unencrypted — **নিরাপত্তা ঝুঁকি**।
5. আর server-a-তে `nginx` আছে, server-b-তে নেই — হয়তো server-b আসলে অন্য কাজের জন্য, ভুল করে load balancer-এ যোগ হয়েছে।

**সমাধান:** server-b-তে update, `telnetd` remove, এবং দীর্ঘমেয়াদে: package list code-এ (Ansible, Module 13) ও immutable image (Module 09, 12), যাতে হাতে পরিবর্তন সম্ভব না হয়।

**শিক্ষা:** **Configuration drift** — সময়ের সাথে হাতে করা পরিবর্তনে "একই রকম" server আলাদা হয়ে যায়। Inventory diff একটি সহজ কিন্তু শক্তিশালী detect উপায়।

## 6. Diagram — `sudo apt install nginx`-এর পেছনে

```text
  apt install nginx
     │
     ├─1─► local index পড়ে (/var/lib/apt/lists/*)  ← `apt update` আগে নামিয়েছিল
     │       nginx-এর dependency: nginx-common, libssl3t64, ...
     │
     ├─2─► dependency resolver: কোনগুলো আগে থেকে আছে? কী install/upgrade লাগবে?
     │
     ├─3─► .deb file নামায় → /var/cache/apt/archives/
     │       প্রতিটির hash index-এর সাথে মেলায়
     │       (index নিজে repository-র signed InRelease file দিয়ে যাচাইকৃত)
     │
     └─4─► dpkg-কে দেয়:
             unpack → file /usr/sbin/nginx, /etc/nginx/... তে
             maintainer script চালায় (user তৈরি, service enable)
             database আপডেট: /var/lib/dpkg/status
             log: /var/log/dpkg.log, /var/log/apt/history.log
```

**Trust chain:**

```text
Ubuntu archive signing key (আপনার system-এ /usr/share/keyrings/...)
   └─ যাচাই করে ─► InRelease (repository-র signed index-এর তালিকা)
                     └─ hash দিয়ে যাচাই ─► Packages index
                                              └─ hash দিয়ে যাচাই ─► nginx_*.deb
```

একটি স্তরও না মিললে apt থামে এবং error দেখায়।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Package | Program-এর file + metadata + install script-এর archive (`.deb`, `.rpm`) |
| Dependency | একটি package চলার জন্য যে অন্য package লাগে |
| Repository | Package ও signed index রাখা server |
| Index / metadata | Repository-তে কী আছে তার তালিকা (`apt update` নামায়) |
| Signing key / GPG | Repository-র পরিচয় যাচাইয়ের cryptographic key |
| Epoch | Version-এর শুরুর `1:` অংশ — version গণনা পদ্ধতি বদলালে ক্রম ঠিক রাখতে |
| Upstream version | মূল software-এর version (যেমন `2.43.0`) |
| Debian revision | Distribution-এর নিজস্ব build নম্বর (যেমন `1ubuntu7.1`) |
| Hold | নির্দিষ্ট package upgrade হওয়া আটকে রাখা |
| Autoremove | আর কোনো package-এর দরকার নেই এমন dependency মুছে ফেলা |
| PPA | Personal Package Archive — Launchpad-এ ব্যক্তি/team-এর third-party repository |
| Unattended upgrades | স্বয়ংক্রিয় security update |
| Configuration drift | একই রকম হওয়ার কথা এমন system-এর মধ্যে সময়ের সাথে পার্থক্য |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Repository configuration (Ubuntu 24.04)

Ubuntu 24.04 থেকে repository-র তালিকা নতুন **deb822** format-এ থাকে:

```bash
cat /etc/apt/sources.list.d/ubuntu.sources
```

উদাহরণ গঠন:

```text
Types: deb
URIs: http://archive.ubuntu.com/ubuntu/
Suites: noble noble-updates noble-backports
Components: main restricted universe multiverse
Signed-By: /usr/share/keyrings/ubuntu-archive-keyring.gpg
```

| Field | অর্থ |
|---|---|
| `Suites` | `noble` = 24.04-এর codename; `-updates` = bug fix; `-security` আলাদা entry-তে |
| `Components` | repository-র অংশ |
| `Signed-By` | **শুধু** এই key দিয়ে sign করা index গ্রহণ করা হবে |

পুরোনো Ubuntu-তে `/etc/apt/sources.list` (এক-লাইন format) ছিল। পুরোনো tutorial-এ দেখা `apt-key add` **deprecated** — এটি key-কে সব repository-র জন্য বিশ্বস্ত করত। আধুনিক পদ্ধতি: key `/etc/apt/keyrings/`-এ রেখে নির্দিষ্ট repository-তে `Signed-By` দিয়ে সীমিত করা। Third-party repository যোগ করার সময় ঠিক এভাবে করুন (Module 09-এ Docker repository যোগে দেখবেন)।

### 8.2 Version-এর গঠন ও তুলনা

`1:2.43.0-1ubuntu7.1` = epoch `1` : upstream `2.43.0` - revision `1ubuntu7.1`।

Version তুলনা সাধারণ string তুলনা নয়। যেমন `1.10` নতুন `1.9`-এর চেয়ে, যদিও অক্ষর ধরে তুলনায় উল্টো আসে। dpkg-র নিজস্ব নিয়ম আছে:

```bash
dpkg --compare-versions 3.0.13-0ubuntu3.4 gt 3.0.13-0ubuntu3.1 && echo newer
```

(`gt` = greater than; exit code 0 মানে সত্য।) এই lesson-এর Python tool শুধু "আলাদা কিনা" দেখে, কোনটি নতুন বলে না — ইচ্ছা করে, কারণ সঠিক তুলনা জটিল (Exercise ৩)।

### 8.3 `upgrade` বনাম `full-upgrade`

- `apt upgrade` — নতুন version install করে, কিন্তু **কোনো installed package remove করে না**; ফলে কিছু package "held back" থাকতে পারে।
- `apt full-upgrade` — দরকার হলে package remove করেও upgrade সম্পূর্ণ করে। শক্তিশালী, কিন্তু কী remove হবে আগে পড়ুন।

### 8.4 Snap — একটি পার্থক্য

Ubuntu কিছু software (যেমন Firefox) **snap** package হিসেবে দেয় — নিজস্ব dependency সহ বন্ধ বাক্স, `snapd` চালায়, আলাদা update ব্যবস্থা। `apt` ও `snap` আলাদা জগৎ: `snap list` দিয়ে দেখুন। Server-এ DevOps কাজে মূলত `apt`; snap-এর উপস্থিতি জানা থাকা দরকার (inventory-তে `snapd` বড় package হিসেবে দেখবেন)।

### 8.5 Fedora: rpm ও dnf

> **Fedora-তে:**
> - Repository: `/etc/yum.repos.d/*.repo` (INI format), `gpgcheck=1` signature যাচাই চালু রাখে।
> - Fedora 41 থেকে `dnf` আসলে নতুন **dnf5** (দ্রুত, C++-এ লেখা); command মোটামুটি একই, কিছু output ও option আলাদা।
> - `dnf history` ও `dnf history undo <id>` — একটি install/upgrade পুরো ফিরিয়ে নেওয়া যায় (apt-এ এমন সরাসরি সুবিধা নেই)।
> - Version: `NAME-VERSION-RELEASE.ARCH`, যেমন `nginx-1.26.2-1.fc41.x86_64`; `fc41` = Fedora 41।

## 9. Practical demonstration (Ubuntu VM — আগে snapshot নিন)

### 9.1 Read-only অনুসন্ধান

```bash
apt list --installed | wc -l          # কতগুলো package install আছে
apt show nginx                        # package-এর বিবরণ, dependency (install না করেও)
apt-cache policy nginx                # কোন version installed, কোন repository থেকে কোন version পাওয়া যায়
dpkg -l | head                        # dpkg-র তালিকা (ii = installed)
dpkg -S /usr/bin/curl                 # এই file কোন package-এর
dpkg -L curl | head                   # curl package কোন file install করেছে
```

`apt-cache policy` উদাহরণ output:

```text
nginx:
  Installed: (none)
  Candidate: 1.24.0-2ubuntu7.1
  Version table:
     1.24.0-2ubuntu7.1 500
        500 http://archive.ubuntu.com/ubuntu noble-updates/main amd64 Packages
```

`Candidate` = install করলে কোন version আসবে; `500` = priority।

> **Fedora-তে:** `dnf list --installed | wc -l`, `dnf info nginx`, `rpm -qa | head`, `rpm -qf /usr/bin/curl`, `rpm -ql curl | head`।

### 9.2 Install, পর্যবেক্ষণ, remove (⚠️ system বদলায়)

```bash
sudo apt update                       # index refresh
sudo apt install -y tree              # ছোট package
dpkg -L tree                          # কী file এলো
grep -A3 "install tree" /var/log/apt/history.log | tail -5   # ইতিহাস
sudo apt remove -y tree               # program মুছে, config রাখে
sudo apt purge -y tree                # config সহ সব মুছে (⚠️)
sudo apt autoremove                   # অপ্রয়োজনীয় dependency মোছার প্রস্তাব — তালিকা পড়ুন, তারপর y
```

`remove` বনাম `purge`: `remove` `/etc/`-এর configuration রেখে দেয় (আবার install করলে আগের config থাকে); `purge` সেগুলোও মোছে।

> **Fedora-তে:** `sudo dnf install -y tree`; `sudo dnf remove -y tree` (rpm-এ remove ও purge-এর পার্থক্য এভাবে নেই; পরিবর্তিত config `.rpmsave` হিসেবে থেকে যেতে পারে); `dnf history`।

### 9.3 Hold — একটি package আটকে রাখা

```bash
sudo apt-mark hold nginx              # (installed থাকলে) upgrade আটকায়
apt-mark showhold
sudo apt-mark unhold nginx
```

কখন: একটি নতুন version-এ জানা bug আছে এবং test শেষ না হওয়া পর্যন্ত আটকে রাখতে হবে। **ঝুঁকি:** hold ভুলে গেলে security fix-ও আটকে থাকে — hold করলে ticket বা notebook-এ কারণ ও মেয়াদ লিখুন।

> **Fedora-তে:** `sudo dnf versionlock add nginx` (versionlock plugin লাগতে পারে)।

### 9.4 Security update কী অপেক্ষা করছে

```bash
apt list --upgradable
systemctl status unattended-upgrades --no-pager
ls /var/run/reboot-required 2>/dev/null && echo "reboot needed"
```

Kernel বা core library update-এর পরে reboot লাগে — `/var/run/reboot-required` file থাকলে Ubuntu তা জানায়।

### 9.5 Package inventory ও drift — Python tool

File: [`code/L01-02/pkg_inventory.py`](code/L01-02/pkg_inventory.py)

**নিজের server-এর inventory তৈরি** (read-only):

```bash
cd ~/devops-ai-engineering/01-linux-systems/code/L01-02
dpkg-query -W -f='${Package}\t${Version}\t${Installed-Size}\n' > /tmp/my-server.tsv
python3 pkg_inventory.py top /tmp/my-server.tsv --n 10
```

`-W` = installed package দেখাও; `-f` = নিজের format (tab দিয়ে আলাদা); `${Installed-Size}` = KiB।

**Sample data দিয়ে চালিয়ে পাওয়া আসল output:**

```bash
python3 pkg_inventory.py top server-a.tsv --n 5
```

```text
14 packages, total 287.1 MiB
   114.8 MiB  snapd  2.63+24.04
    99.2 MiB  linux-modules-6.8.0-45-generic  6.8.0-45.45
    25.6 MiB  git  1:2.43.0-1ubuntu7.1
    15.1 MiB  linux-image-6.8.0-45-generic  6.8.0-45.45
    13.1 MiB  libc6:amd64  2.39-0ubuntu8.3
```

**Drift (Section 5-এর scenario):**

```bash
python3 pkg_inventory.py diff server-a.tsv server-b.tsv; echo "exit=$?"
```

```text
only in server-a.tsv: 1
  - nginx 1.24.0-2ubuntu7.1
only in server-b.tsv: 1
  + telnetd 0.17+2.5-3ubuntu4
version differs: 2
  ~ curl: 8.5.0-2ubuntu10.4 -> 8.5.0-2ubuntu10.1
  ~ openssl: 3.0.13-0ubuntu3.4 -> 3.0.13-0ubuntu3.1
exit=1
```

Drift থাকলে exit code ১ — CI বা cron job এটি দিয়ে alert দিতে পারে।

> **Fedora-তে:**
> ```bash
> rpm -qa --queryformat '%{NAME}\t%{VERSION}-%{RELEASE}\t%{SIZE}\n' > /tmp/my-fedora.tsv
> python3 pkg_inventory.py --format rpm top /tmp/my-fedora.tsv --n 10
> ```
> rpm-এর `SIZE` byte-এ, script KiB-এ রূপান্তর করে। Sample: [`server-f.tsv`](code/L01-02/server-f.tsv)।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_pkg_inventory.py`](code/L01-02/test_pkg_inventory.py)-এর ৫টি test: dpkg ও rpm-এর একক, খালি size ও ভাঙা লাইন, top ক্রম, drift-এর তিন ধরন, ও CLI exit code (drift = 1, একই = 0, missing = 2)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `split("\t")` + তিনটি field যাচাই | Tab-separated parse | Version-এ space থাকে না, কিন্তু নিশ্চিত হতে field সংখ্যা যাচাই; ভুল format-এ লাইন নম্বর সহ error |
| `size_kib = size if dpkg else round(size/1024)` | একক মেলানো | দুই tool দুই এককে দেয় — না মেলালে তুলনা ভুল হতো |
| `libc6:amd64` নাম অক্ষত | Multi-arch package আলাদা থাকে | একই নামের i386 ও amd64 package গুলিয়ে না যায় |
| `diff_inventories()` | set operation: শুধু A, শুধু B, উভয়ে কিন্তু version আলাদা | Drift-এর তিন ধরন আলাদা করে দেখায় |
| Exit `1` on drift | Monitoring-এ ব্যবহারযোগ্য | L00-04-এর gate ধারণা |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `dpkg -S /usr/bin/curl` | `curl: /usr/bin/curl` |
| `apt-cache policy openssl` | Installed ও Candidate version |
| install-এর পরে `/var/log/apt/history.log` | `Install: tree:amd64 (...)` |
| `pkg_inventory.py diff a a` | drift নেই, exit 0 |
| `python3 -m unittest -v` | `Ran 5 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `E: Unable to locate package X` | `apt update` হয়নি, বা package `universe`-এ এবং সেটি বন্ধ, বা নাম ভুল | `apt-cache policy X`; sources file | `sudo apt update`; নাম `apt search` দিয়ে খুঁজুন |
| `Could not get lock /var/lib/dpkg/lock-frontend` | অন্য apt/unattended-upgrades চলছে | `ps aux \| grep -E 'apt\|dpkg'` | অপেক্ষা করুন; lock file **মুছবেন না** |
| `NO_PUBKEY ...` / `The following signatures couldn't be verified` | Repository-র key নেই বা মেয়াদোত্তীর্ণ | `apt update` output | Vendor-এর official নির্দেশে key `/etc/apt/keyrings/`-এ ও `Signed-By`; অজানা repository হলে মুছে ফেলুন |
| `dpkg was interrupted, you must manually run 'sudo dpkg --configure -a'` | Install মাঝপথে বন্ধ (power, Ctrl+C) | Error message | ঠিক সেই command চালান |
| `The following packages have been kept back` | `upgrade` remove করবে না এমন পরিবর্তন লাগবে, বা phased update | `apt list --upgradable` | কারণ পড়ুন; দরকার হলে `sudo apt install <pkg>` বা `full-upgrade` (তালিকা পড়ে) |
| Disk পূর্ণ `/var/cache/apt` | পুরোনো .deb জমেছে | `du -sh /var/cache/apt` | `sudo apt clean` |

> **Fedora-তে:** lock সমস্যায় অন্য `dnf`/PackageKit process দেখুন; signature error-এ `gpgcheck` বন্ধ করবেন না — key ঠিক করুন; cache: `sudo dnf clean all`।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - শুধু বিশ্বস্ত repository; প্রতিটি third-party repository = সেই vendor-কে root অধিকার দেওয়া (install script root হিসেবে চলে)।
  - `Signed-By` দিয়ে key-এর এখতিয়ার সীমিত রাখুন; `apt-key` (deprecated) নয়।
  - `--allow-unauthenticated` বা `gpgcheck=0` কখনো নয়।
  - Security update নিয়মিত (unattended-upgrades বা automation) এবং drift detect।
  - অপ্রয়োজনীয় package (যেমন telnetd) attack surface বাড়ায় — minimal install।
- **Performance:** Production-এ বড় upgrade চলাকালীন service restart হতে পারে — maintenance window বা rolling (Module 11)।
- **Cost:** Package cache ও পুরোনো kernel disk খায় — `apt autoremove` (পড়ে নিয়ে) ও `apt clean`। Cloud-এ বড় image মানে বেশি storage ও ধীর deploy।

## 14. Hands-on exercise

1. নিজের VM-এর inventory নিয়ে `top --n 10` চালান। সবচেয়ে বড় তিনটি package কী, এবং server-এ সেগুলো কি দরকার?
2. দুটি VM (বা একই VM-এ একটি package install-এর আগে ও পরে) inventory নিয়ে `diff` চালান। `apt install nginx`-এর সাথে কয়টি package যোগ হলো?
3. `pkg_inventory.py`-র `diff`-এ "কোনটি নতুন" দেখান: Ubuntu-তে `subprocess` দিয়ে `dpkg --compare-versions` ডেকে (`list` argument, `shell=True` নয়)। এর test কীভাবে লিখবেন যাতে Windows/Fedora-তেও চলে?
4. `apt-cache rdepends --installed libssl3t64 | head` চালিয়ে দেখুন কতগুলো installed package OpenSSL-এর উপর নির্ভরশীল। OpenSSL update কেন এত গুরুত্বপূর্ণ বুঝিয়ে লিখুন। (Package নাম Ubuntu version অনুযায়ী আলাদা হতে পারে — `dpkg -S libssl.so` দিয়ে খুঁজুন।)
5. 🎩 Fedora VM থাকলে `dnf history` ও `dnf history undo` দিয়ে একটি install ফিরিয়ে নিন।

## 15. Mini-project — drift monitor

একটি Bash wrapper (`drift-check.sh`) লিখুন যা:

1. বর্তমান inventory `dpkg-query` দিয়ে নেয়।
2. একটি "baseline" file-এর সাথে `pkg_inventory.py diff` চালায়।
3. Drift থাকলে ফল `~/devops-notebook/labs/drift-$(date +%F).txt`-এ লেখে এবং exit 1।
4. `--update-baseline` option দিলে বর্তমান inventory-কে নতুন baseline করে।

Module 01-এর L01-11-এ এটিকে systemd timer দিয়ে প্রতিদিন চালানো শিখবেন।

## 16. Interview প্রশ্ন

1. `dpkg` ও `apt`-এর পার্থক্য কী? Fedora-তে এদের সমতুল্য কী?
2. `apt update` ও `apt upgrade`-এর পার্থক্য কী?
3. apt কীভাবে নিশ্চিত হয় একটি package বদলানো হয়নি?
4. `apt-key` কেন deprecated? এখন third-party repository কীভাবে যোগ করবেন?
5. Configuration drift কী এবং কীভাবে detect ও প্রতিরোধ করবেন?
6. Production-এ package upgrade কীভাবে নিরাপদে করবেন?
7. `remove` ও `purge`-এর পার্থক্য কী?

## 17. Self-assessment প্রশ্ন

1. সুপারশপ analogy দিয়ে apt, dpkg, repository ও `apt update` ব্যাখ্যা করুন; analogy কোথায় মেলে না?
2. `1:2.43.0-1ubuntu7.1`-এর তিনটি অংশ কী?
3. Section 5-এর drift report থেকে তিনটি আলাদা সমস্যা চিহ্নিত করুন এবং প্রতিটির ঝুঁকি বলুন।
4. Trust chain-এর স্তরগুলো লিখুন (key → InRelease → Packages → .deb)।
5. `apt-mark hold`-এর ঝুঁকি কী এবং কীভাবে সামলাবেন?
6. rpm inventory-তে size-কে কেন ১০২৪ দিয়ে ভাগ করা হয়েছে?

## 18. সংক্ষিপ্ত সারাংশ

- Package manager dependency, tracking, update ও trust সামলায়।
- Ubuntu: **dpkg** (local, নিচের স্তর) + **apt** (repository, dependency, উপরের স্তর)। Fedora: **rpm** + **dnf**।
- Repository index **cryptographically signed**; `Signed-By` দিয়ে key সীমিত রাখুন; `apt-key` deprecated।
- `update` = তালিকা; `upgrade` = install; `full-upgrade` remove-ও করতে পারে; `hold` সাবধানে।
- **Drift** — inventory diff দিয়ে detect; code ও immutable image দিয়ে প্রতিরোধ।

## 19. Completion checklist

- [ ] `apt show`, `apt-cache policy`, `dpkg -S`, `dpkg -L` চালিয়েছি
- [ ] একটি package install, log-এ দেখা, remove ও purge করেছি (snapshot সহ)
- [ ] নিজের VM-এর inventory নিয়ে `top` চালিয়েছি
- [ ] `diff` দিয়ে install-এর আগে-পরে পার্থক্য দেখেছি
- [ ] `python3 -m unittest -v`-এ ৫টি test পাস
- [ ] Exercise ১, ২ ও ৪ শেষ
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Ubuntu Server — Package management: https://documentation.ubuntu.com/server/
- `apt(8)`: https://manpages.ubuntu.com/manpages/noble/man8/apt.8.html
- `dpkg(1)`: https://manpages.ubuntu.com/manpages/noble/man1/dpkg.1.html
- `sources.list(5)` (deb822 format সহ): https://manpages.ubuntu.com/manpages/noble/man5/sources.list.5.html
- Debian Policy — version format: https://www.debian.org/doc/debian-policy/ch-controlfields.html#version
- Fedora — DNF: https://docs.fedoraproject.org/en-US/quick-docs/dnf/
- এই repository: [reference/ubuntu-vs-fedora.md](../reference/ubuntu-vs-fedora.md)

---

**পরের lesson:** L01-03 — Filesystem hierarchy, mount point, inode ও link
