# L00-07 — Lab environment setup: Ubuntu (VM/native/WSL2), Python venv, notebook

| | |
|---|---|
| **Module** | 00 — Engineering Orientation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৪ ঘণ্টা (download ও install-এর সময় সহ) |
| **পূর্বশর্ত** | [L00-06 — Experiment, log, measurement](L00-06-learning-by-experiment.md) |
| **Label** | 🖥️ VM (সুপারিশকৃত) · ⚠️ System পরিবর্তন: package install, VM/partition তৈরি |
| **Tested** | `check_env.py`: ৯টি unit test পাস (Python 3.14); Windows 11-এ চালিয়ে দেখা গেছে এটি সঠিকভাবে "Linux নয়" FAIL দেয়। `init-notebook.sh`: `bash -n` syntax check, dry-run, প্রথম run ও idempotent rerun Git Bash-এ যাচাই; ShellCheck চালানো হয়নি (installed নেই)। **Ubuntu install-এর ধাপ ও `apt` command এই session-এ চালানো হয়নি** — Ubuntu 24.04 LTS লক্ষ্য করে লেখা। |

---

## 1. এই lesson-এ যা শিখবেন

- Ubuntu practice environment-এর তিনটি উপায় — native install, Virtual Machine, WSL2 — এবং কোনটি কখন।
- VM-এ **snapshot** দিয়ে নিরাপদে ভাঙা-জোড়া করা।
- প্রথম দিনের Ubuntu setup: update, দরকারি package, Git পরিচয়।
- Python **virtual environment (venv)** কী, কেন, এবং Ubuntu 24.04-এ কেন বাধ্যতামূলক।
- **Engineering notebook** তৈরি (idempotent Bash script দিয়ে)।
- Python দিয়ে **read-only environment checker** — machine lab-এর জন্য প্রস্তুত কিনা যাচাই।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

DevOps শেখার সময় আপনি ইচ্ছা করে system ভাঙবেন: service বন্ধ করবেন, firewall বদলাবেন, disk ভরবেন, permission নষ্ট করবেন। এটি যদি আপনার একমাত্র কাজের computer-এ করেন:

- ভুল command-এ ব্যক্তিগত file বা কাজ হারাতে পারেন।
- Network বা boot ভেঙে গেলে কাজ বন্ধ।
- কোন package কে install করেছে, কী বদলেছে — হিসাব থাকে না ("আমার machine-এ চলে" সমস্যা)।

আরেকটি সমস্যা: Python package system-wide install করলে বিভিন্ন project-এর version-এ সংঘাত হয়, এমনকি OS-এর নিজের tool ভাঙতে পারে।

সমাধান: **আলাদা, পুনরায় তৈরিযোগ্য, নিরাপদে ভাঙা যায় এমন lab environment** + প্রতিটি project-এর জন্য আলাদা Python environment + সব কিছুর লিখিত রেকর্ড (notebook)।

## 3. সহজ ভাষায় পরিচয়

### তিনটি উপায় — Ubuntu কোথায় চালাবেন

| উপায় | কী | সুবিধা | সীমাবদ্ধতা | কার জন্য |
|---|---|---|---|---|
| **Native install** | Ubuntu সরাসরি laptop-এ (একমাত্র OS বা dual boot) | সবচেয়ে বাস্তব; সব hardware ও kernel feature | ভাঙলে আপনার কাজের machine-ই ভাঙে; dual boot-এ partition ঝুঁকি | যাদের আলাদা machine আছে |
| **Virtual Machine (VM)** | আপনার OS-এর ভেতরে একটি সম্পূর্ণ আলাদা computer (software-এ) | **Snapshot**: ভাঙলে এক ক্লিকে আগের অবস্থায়; একাধিক VM দিয়ে multi-server lab | RAM ও CPU ভাগ হয়; সামান্য ধীর | **সবচেয়ে সুপারিশকৃত** — বিশেষ করে failure lab-এর জন্য |
| **WSL2** | Windows-এর ভেতরে Microsoft-এর হালকা VM-এ Linux kernel | দ্রুত শুরু, Windows file-এর সাথে কাজ | কিছু lab পুরোপুরি চলে না: boot process, disk partition, AppArmor, কিছু network lab | Windows ব্যবহারকারীর প্রথম কয়েকটি module |

**এই repository-র সুপারিশ:** দৈনন্দিন practice-এর জন্য একটি **Ubuntu VM** (snapshot সহ)। Windows-এ থাকলে প্রথম module-গুলো WSL2-তে শুরু করা যায়, তবে 🖥️ VM label-এর lesson-এ VM ব্যবহার করুন।

### Virtual environment (venv) কী?

একটি আলাদা folder, যেখানে একটি project-এর নিজস্ব Python package থাকে। এক project-এ `requests 2.31`, অন্যটিতে `requests 2.32` — কোনো সংঘাত নেই, এবং OS-এর Python অক্ষত।

### Engineering notebook কী?

L00-06-এ শিখেছেন — প্রতিটি experiment, lab ও incident-এর লিখিত রেকর্ড। এই lesson-এ একটি script দিয়ে তার কাঠামো তৈরি করবেন।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### VM ও snapshot — রসায়ন ল্যাবের আলাদা টেবিল

বাড়ির রান্নাঘরে রাসায়নিক পরীক্ষা করলে খাবার ও বাসন নষ্ট হতে পারে। ল্যাবে আলাদা টেবিল, আলাদা সরঞ্জাম — ভুল হলে শুধু সেই টেবিল পরিষ্কার করতে হয়। **Snapshot** হলো এমন একটি জাদুকরী ছবি: পরীক্ষার আগে টেবিলের ছবি তুললেন; সব কিছু উল্টে গেলে ছবিতে ফিরে যান — টেবিল হুবহু আগের মতো।

### venv — প্রতিটি রান্নার আলাদা মশলার বাক্স

এক রেসিপিতে ঝাল মরিচ, অন্যটিতে মিষ্টি paprika — একই বয়ামে রাখলে মিশে যাবে। প্রতিটি রেসিপির আলাদা বাক্স (venv) রাখলে কোনো রান্না অন্যটিকে নষ্ট করে না।

### Analogy কোথায় মেলে না

- ল্যাবের টেবিল ও বাড়ির রান্নাঘর একই ঘরে নয়। VM কিন্তু **একই physical hardware** ব্যবহার করে: VM-এ ১০০% CPU ব্যবহার করলে host-ও ধীর হবে, VM-এর disk ভরলে host-এর disk-এর জায়গাও যায়। VM নিরাপদ, কিন্তু সম্পূর্ণ বিচ্ছিন্ন নয়।
- Snapshot **backup নয়।** Snapshot সাধারণত একই disk-এ থাকে; host-এর disk নষ্ট হলে VM ও snapshot দুটোই যায়। আর অনেক snapshot জমলে VM ধীর হয় ও জায়গা খায়।
- মশলার বাক্স সম্পূর্ণ আলাদা; কিন্তু venv **Python interpreter নিজে আলাদা করে না** — শুধু package আলাদা করে। ভিন্ন Python version লাগলে আলাদা tool লাগে (পরে Module 05-এ)।

## 5. Real-world engineering scenario — "OS-এর Python ভেঙে গেল"

**পরিস্থিতি:** একজন engineer একটি automation script-এর জন্য Ubuntu server-এ `sudo pip install` দিয়ে একটি library-র নতুন version install করলেন।

**ঘটনার ক্রম:**

1. Library-টি একটি dependency-কে নতুন version-এ upgrade করল, যা system-wide Python-এ install হলো।
2. Ubuntu-র নিজের একটি tool (যা Python-এ লেখা, OS-এর package হিসেবে install করা) সেই dependency-র পুরোনো version-এর উপর নির্ভর করত।
3. পরদিন package update চালাতে গিয়ে সেই tool crash করল। Server-এর update প্রক্রিয়া আটকে গেল।

**কেন এমন হলো:** OS-এর package manager (`apt`) ও `pip` একই জায়গার Python package নিয়ন্ত্রণ করতে চাইছিল — দুই রাঁধুনি একই হাঁড়িতে।

**আধুনিক সমাধান:** এই সংঘাত রোধে Python-এর একটি standard (**PEP 668**) অনুযায়ী Ubuntu 23.04 থেকে system Python-কে "externally managed" চিহ্নিত করা হয়েছে। এখন `pip install` system-wide চালালে pip নিজেই প্রত্যাখ্যান করে এবং `error: externally-managed-environment` দেখায়। সঠিক পথ:

- Project-এর জন্য **venv**।
- OS-এর জন্য দরকারি Python tool → `apt`-এর package (যেমন `python3-requests`)।
- Command-line Python tool → `pipx` (প্রতিটি tool-এর জন্য আলাদা venv স্বয়ংক্রিয়ভাবে)।

**Engineer কীভাবে diagnose করবেন:** Error-এর traceback-এ কোন file path (system site-packages নাকি venv), `pip list` বনাম `dpkg -l | grep python3-`, এবং সাম্প্রতিক পরিবর্তনের ইতিহাস।

> **Fedora-তে:** একই নীতি — system Python-এ `sudo pip install` করবেন না; venv ব্যবহার করুন। OS-এর Python package `dnf` দিয়ে (`python3-<name>`)।

## 6. Diagram — আপনার lab-এর গঠন

```text
 ┌───────────────────────── আপনার laptop (host OS: Windows/Ubuntu/macOS) ─────────────────────────┐
 │                                                                                                │
 │   ┌─────────────── Ubuntu VM ("devlab") ───────────────┐   ┌──── দ্বিতীয় VM (পরে) ────┐      │
 │   │  snapshots: [clean-install] → [base-setup] → ...    │   │  multi-server lab-এর জন্য │      │
 │   │                                                     │   └───────────────────────────┘      │
 │   │  ~/devops-ai-engineering/   (এই repository, git)   │                                       │
 │   │  ~/devops-notebook/          (আপনার নোট)            │                                       │
 │   │                                                     │                                       │
 │   │  project-A/.venv/  ← project-A-এর package           │                                       │
 │   │  project-B/.venv/  ← project-B-এর package           │                                       │
 │   │  /usr/lib/python3/ ← OS-এর Python (apt-এর এলাকা,   │                                       │
 │   │                       pip দিয়ে হাত দেবেন না)         │                                       │
 │   └─────────────────────────────────────────────────────┘                                       │
 └────────────────────────────────────────────────────────────────────────────────────────────────┘
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Host | যে physical machine ও OS-এ VM চলে |
| Guest | VM-এর ভেতরের OS (এখানে Ubuntu) |
| Hypervisor | VM চালানোর software (VirtualBox, VMware, Hyper-V, KVM) — Module 07-এ বিস্তারিত |
| Snapshot | VM-এর নির্দিষ্ট মুহূর্তের অবস্থা, যেখানে পরে ফিরে যাওয়া যায় |
| LTS (Long Term Support) | দীর্ঘ মেয়াদে (Ubuntu-তে standard ৫ বছর) security update পাওয়া release |
| WSL2 | Windows Subsystem for Linux 2 — Windows-এ হালকা VM-এ আসল Linux kernel |
| Package manager | Software install/update/remove-এর tool (`apt`, Fedora-তে `dnf`) |
| venv | Python-এর project-ভিত্তিক আলাদা package environment |
| PEP 668 | System Python-কে "externally managed" চিহ্নিত করার standard |
| pipx | Python command-line tool-গুলো প্রতিটি আলাদা venv-এ install করার tool |
| Idempotent | একাধিকবার চালালেও ফল একবারের মতোই |
| Dry-run | কী করবে শুধু দেখায়, আসলে করে না |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 venv ভেতরে কী

`python3 -m venv .venv` চালালে:

1. `.venv/` folder তৈরি হয়।
2. `.venv/bin/python` — system Python-এর দিকে symlink (Python নিজে copy হয় না)।
3. `.venv/pyvenv.cfg` — কোন base Python, কোন version তার রেকর্ড।
4. `.venv/lib/python3.X/site-packages/` — এই project-এর package এখানে যাবে।
5. `.venv/bin/activate` — একটি shell script।

`source .venv/bin/activate` চালালে আসলে শুধু `PATH` environment variable-এর শুরুতে `.venv/bin` যোগ হয় (L00-04-এ environment variable শিখেছেন)। ফলে `python` বা `pip` লিখলে shell প্রথমে `.venv/bin/`-এ খোঁজে। এটাই সব "জাদু"। `deactivate` আগের `PATH` ফিরিয়ে দেয়।

Python নিজে জানে সে venv-এ আছে কিনা: `sys.prefix` (বর্তমান environment) ≠ `sys.base_prefix` (মূল Python)। এই lesson-এর `check_env.py` ঠিক এভাবে যাচাই করে।

### 8.2 `apt` কী করে (সংক্ষেপে)

- `apt update` — repository থেকে **package-এর তালিকা** (index) নামায়; কোনো software বদলায় না।
- `apt install X` — X ও তার dependency নামিয়ে install করে; system বদলায়, তাই `sudo` লাগে।
- `apt upgrade` — installed package-গুলোর নতুন version install করে।

Module 01-এর L01-02-এ dpkg, repository, signing key সহ বিস্তারিত।

> **Fedora-তে:** `dnf` install-এর সময় নিজেই metadata refresh করে; আলাদা `update` ধাপ সাধারণত লাগে না। `sudo dnf upgrade` = সব আপডেট।

### 8.3 WSL2 ও systemd

অনেক lesson-এ `systemctl` লাগবে (Module 01 থেকে)। এর জন্য PID 1 (প্রথম process) হতে হবে systemd। সাম্প্রতিক WSL ও Ubuntu WSL image-এ systemd সাধারণত default চালু, কিন্তু নিশ্চিত হতে:

```bash
ps -p 1 -o comm=
```

Output `systemd` হলে ঠিক আছে। না হলে `/etc/wsl.conf`-এ:

```ini
[boot]
systemd=true
```

তারপর Windows PowerShell-এ `wsl --shutdown` চালিয়ে আবার Ubuntu খুলুন। (`check_env.py` এটিও যাচাই করে।)

## 9. Practical demonstration

> ⚠️ এই section-এর install ধাপগুলো system পরিবর্তন করে। প্রতিটি ধাপের আগে পড়ুন কী হবে।

### 9.1 Ubuntu পাওয়া — একটি উপায় বেছে নিন

**বিকল্প A — VM (সুপারিশকৃত):**

1. একটি hypervisor install করুন: VirtualBox (Windows/Linux/macOS, বিনামূল্যে), বা Windows Pro-তে Hyper-V, বা Linux host-এ virt-manager (KVM)।
2. Ubuntu-র official website থেকে **Ubuntu 24.04 LTS** (Desktop বা Server) ISO নামান। Checksum যাচাই করুন (download page-এ নির্দেশ আছে)।
3. VM তৈরি: **RAM ৪ GB (সম্ভব হলে ৬–৮), CPU ২ (সম্ভব হলে ৪), disk ৪০ GB (dynamically allocated)**।
4. Install শেষে, কিছু করার আগেই **snapshot নিন** — নাম `clean-install`।

**বিকল্প A2 — Multipass (Ubuntu Server VM, command line দিয়ে):** Canonical-এর Multipass দিয়ে এক command-এ Ubuntu VM তৈরি করা যায় (Windows, macOS, Linux-এ চলে)। Install পদ্ধতি official site-এ। উদাহরণ:

```bash
multipass launch 24.04 --name devlab --cpus 2 --memory 4G --disk 40G
multipass shell devlab
```

**বিকল্প B — WSL2 (Windows):** PowerShell (Administrator) থেকে:

```powershell
wsl --list --online          # কোন distribution নাম পাওয়া যায় দেখায় (শুধু পড়ে)
wsl --install -d Ubuntu-24.04
```

Distribution-এর হুবহু নাম সময়ের সাথে বদলাতে পারে — `--list --online`-এর output থেকে নাম নিন।

**বিকল্প C — Native:** ⚠️ Dual boot-এ partition পরিবর্তন হয় — ভুলে data হারাতে পারে। আগে সম্পূর্ণ backup নিন। শুরুতে VM সুপারিশকৃত।

> **Fedora-তে:** Fedora Workstation ISO দিয়ে একই VM পদ্ধতি; Linux host-এ GNOME Boxes সবচেয়ে সহজ। WSL-এ Fedora: `wsl --list --online`-এ Fedora আছে কিনা দেখুন।

### 9.2 প্রথম দিনের setup (Ubuntu VM-এর ভেতরে)

```bash
# ১. Package index refresh (software বদলায় না)
sudo apt update

# ২. Installed package আপডেট (system বদলায়; কয়েক মিনিট লাগতে পারে)
sudo apt upgrade -y

# ৩. প্রথম module-গুলোর tool (system বদলায়)
sudo apt install -y git curl wget vim tree jq python3 python3-venv python3-pip \
    build-essential dnsutils iproute2 traceroute mtr-tiny tcpdump htop shellcheck
```

| Option | অর্থ |
|---|---|
| `sudo` | এই একটি command root অধিকারে চালানো (Module 01-এ বিস্তারিত) |
| `-y` | "Continue? [Y/n]" প্রশ্নে স্বয়ংক্রিয় হ্যাঁ — শুধু তখনই ব্যবহার করুন যখন জানেন কী install হচ্ছে |
| `\` (লাইনের শেষে) | Command পরের লাইনে চলতে থাকে |

> **Fedora-তে:**
> ```bash
> sudo dnf upgrade -y
> sudo dnf install -y git curl wget vim tree jq python3 python3-pip gcc make \
>     bind-utils iproute traceroute mtr tcpdump htop ShellCheck
> ```
> Package নামের পার্থক্য: [reference/ubuntu-vs-fedora.md](../reference/ubuntu-vs-fedora.md)।

**Git পরিচয় (একবার):**

```bash
git config --global user.name "আপনার নাম"
git config --global user.email "you@example.com"
git config --global init.defaultBranch main
git config --global --list        # যাচাই — শুধু পড়ে
```

এগুলো `~/.gitconfig` file-এ লেখা হয়। Email public commit-এ দেখা যাবে — চাইলে GitHub-এর "noreply" email ব্যবহার করুন।

**Repository আনুন:** এই repository আপনার VM-এ `~/devops-ai-engineering/`-এ রাখুন (Git clone বা copy)। WSL-এ থাকলে Windows-এর drive (`/mnt/c/...`) নয়, Linux-এর home-এ রাখুন — Linux filesystem-এ file permission ও গতি সঠিক থাকে।

**Snapshot:** এখন দ্বিতীয় snapshot নিন — `base-setup`।

### 9.3 Python venv — প্রথম অনুশীলন

```bash
mkdir -p ~/venv-practice && cd ~/venv-practice
python3 -m venv .venv               # .venv folder তৈরি
source .venv/bin/activate           # PATH পরিবর্তন — prompt-এ (.venv) দেখাবে
which python                        # .venv/bin/python দেখানো উচিত
python -c "import sys; print(sys.prefix != sys.base_prefix)"   # True = venv-এর ভেতরে
pip install requests                # শুধু এই venv-এ install
pip list
deactivate                          # PATH আগের মতো
which python3                       # আবার /usr/bin/python3
```

**PEP 668 নিজে দেখুন** (venv-এর বাইরে, কোনো ক্ষতি নেই — pip প্রত্যাখ্যান করবে):

```bash
pip install requests
```

Ubuntu 24.04-এ প্রত্যাশিত: `error: externally-managed-environment` এবং venv বা `apt`/`pipx` ব্যবহারের পরামর্শ। এই error-কে `--break-system-packages` দিয়ে এড়াবেন না — নাম থেকেই বোঝা যায় কেন।

পরিষ্কার: `rm -r ~/venv-practice` (শুধু practice folder)।

### 9.4 Engineering notebook তৈরি

File: [`code/L00-07/init-notebook.sh`](code/L00-07/init-notebook.sh)

প্রথমে **dry-run** — কী করবে শুধু দেখায়:

```bash
cd ~/devops-ai-engineering/00-orientation/code/L00-07
bash init-notebook.sh --dry-run
```

তারপর আসলে চালান:

```bash
bash init-notebook.sh
```

**এই repository-তে (temporary directory-তে) চালিয়ে পাওয়া আসল output-এর গঠন:**

```text
create /…/devops-notebook/README.md
create /…/devops-notebook/experiments/TEMPLATE.md
notebook ready: /…/devops-notebook
```

আবার চালান — **idempotency** দেখুন:

```text
skip   /…/devops-notebook/README.md (already exists)
skip   /…/devops-notebook/experiments/TEMPLATE.md (already exists)
notebook ready: /…/devops-notebook
```

আপনার লেখা নোট কখনো overwrite হবে না।

**Script-এর ব্যাখ্যা:**

| Line / অংশ | কী করে | কেন |
|---|---|---|
| `#!/usr/bin/env bash` | কোন interpreter চালাবে | `env` PATH থেকে bash খোঁজে — বিভিন্ন system-এ bash-এর path আলাদা হতে পারে |
| `set -euo pipefail` | `-e`: command ব্যর্থ হলে থামো; `-u`: অসংজ্ঞায়িত variable-এ থামো; `pipefail`: pipe-এর মাঝের ব্যর্থতাও ধরো | ভুল নীরবে এগিয়ে যাওয়া আটকায়। সীমাবদ্ধতা আছে — L04-01-এ বিস্তারিত |
| `case "$arg" in ... esac` | Argument বিশ্লেষণ | অজানা option-এ exit 2 — ভুল টাইপ নীরবে উপেক্ষিত হয় না |
| `run()` | Dry-run-এ শুধু ছাপায়, নাহলে চালায় | পরিবর্তনের আগে দেখার সুযোগ |
| `mkdir -p` | Directory তৈরি; থাকলে কিছু করে না, error-ও নয় | Idempotent |
| `write_if_missing()` | File না থাকলে তবেই লেখে | ব্যবহারকারীর data রক্ষা |
| `"$TARGET"` (quote সহ) | Path-এ space থাকলেও সঠিক | Quote ছাড়া space-যুক্ত path দুই টুকরো হয়ে যায় (L01-06) |

### 9.5 Environment যাচাই

File: [`code/L00-07/check_env.py`](code/L00-07/check_env.py)

```bash
python3 check_env.py
echo "exit code: $?"
```

Script **সম্পূর্ণ read-only**: `/etc/os-release`, `/proc/meminfo`, `/proc/version`, `/proc/1/comm` পড়ে, tool খোঁজে (`which`-এর মত), `git --version` চালায়। কিছু install বা পরিবর্তন করে না।

**Ubuntu-তে প্রত্যাশিত output-এর গঠন (উদাহরণ — আপনার মান ভিন্ন হবে; এটি এই session-এ Ubuntu-তে চালানো হয়নি):**

```text
[PASS] os               Ubuntu 24.04.1 LTS
[INFO] wsl              WSL নয় (native বা VM)
[PASS] systemd          PID 1 = systemd
[PASS] python           3.12.3 (minimum 3.10)
[INFO] venv             venv সক্রিয় নয় — ...
[PASS] tool:git         /usr/bin/git
...
[PASS] ram              5.8 GB (minimum 4, Kubernetes/observability-তে 8–16 GB)
[PASS] notebook         /home/you/devops-notebook

PASS=..  WARN=..  FAIL=0  INFO=..
```

**আসল পর্যবেক্ষণ (এই repository লেখার Windows machine-এ):** script সঠিকভাবে `[FAIL] os  Windows — lab-গুলো Linux-এর জন্য` দেখিয়েছে, এবং `jq`, `dig`, `ip`, `ss` FAIL — exit code 1। অর্থাৎ checker ঠিকই ধরেছে যে Windows lab environment নয়।

প্রতিটি FAIL ঠিক করুন (সাধারণত 9.2-এর install command), তারপর আবার চালান যতক্ষণ না `FAIL=0`। Machine-readable output:

```bash
python3 check_env.py --json > ~/devops-notebook/labs/env-check-$(date +%F).json
```

`$(date +%F)` আজকের তারিখ (`2026-10-26` format) বসায়; `>` output file-এ লেখে।

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_check_env.py`](code/L00-07/test_check_env.py)-এর ৯টি test আসল machine-এর উপর নির্ভর না করে **নমুনা text** দিয়ে চলে: os-release ও meminfo parse, WSL চেনা, Ubuntu/Fedora/অন্য Linux/Windows-এর ফল, Python version সীমা, নকল `which` দিয়ে tool check, ও resource সীমা। এভাবে test যেকোনো machine-এ একই ফল দেয় — এটি **testability**-র জন্য ভালো design: system-এর উপর নির্ভরশীল অংশ (file পড়া) থেকে যুক্তি (parse ও সিদ্ধান্ত) আলাদা রাখা।

## 10. Code-এর ব্যাখ্যা — check_env.py

Python 3.10+ · Dependency: নেই

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `parse_os_release(text)` | Text নেয়, file নয় | Test-এ নমুনা text দেওয়া যায়; file পড়া আলাদা (`read_text`) |
| `read_text()` → `""` on `OSError` | File না থাকলে খালি | Windows বা container-এ `/proc` না থাকলে crash নয় |
| `check_tools(which=shutil.which)` | `which` function parameter হিসেবে | Test-এ নকল function দেওয়া যায় (dependency injection) |
| `subprocess.run([...], timeout=5, check=False)` | List argument, timeout | `shell=True` নয় (injection ঝুঁকি নেই); কোনো tool আটকে গেলে script আটকায় না (Module 05) |
| `sys.prefix != sys.base_prefix` | venv-এ আছে কিনা | Python-এর official পদ্ধতি |
| Status: PASS/WARN/FAIL/INFO | চার স্তর | Required জিনিস না থাকলে FAIL, সুপারিশ না মানলে WARN, তথ্য INFO — সব কিছু "error" নয় |
| Exit `1` যদি কোনো FAIL | | CI বা অন্য script এটি gate হিসেবে ব্যবহার করতে পারে |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `lsb_release -a` বা `cat /etc/os-release` | Ubuntu 24.04 (বা আপনার LTS) |
| `ps -p 1 -o comm=` | `systemd` |
| `python3 -m venv /tmp/t && /tmp/t/bin/python -c "import sys;print(sys.prefix)"` | `/tmp/t` |
| `bash init-notebook.sh` দুবার | দ্বিতীয়বার সব `skip` |
| `python3 check_env.py` | `FAIL=0`, exit 0 |
| VM-এ snapshot তালিকা | `clean-install`, `base-setup` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| `The virtual environment was not created successfully because ensurepip is not available` | `python3-venv` package নেই | Error message | `sudo apt install python3-venv` |
| `error: externally-managed-environment` | venv-এর বাইরে `pip install` | Prompt-এ `(.venv)` নেই | venv activate করুন; বা `apt`/`pipx` |
| `E: Could not get lock /var/lib/dpkg/lock-frontend` | অন্য apt/unattended-upgrade চলছে | `ps aux \| grep -i apt` | কয়েক মিনিট অপেক্ষা; lock file **মুছবেন না** |
| `systemctl: System has not been booted with systemd` | WSL-এ systemd বন্ধ | `ps -p 1 -o comm=` | Section 8.3 |
| VM খুব ধীর | কম RAM/CPU বা hardware virtualization BIOS-এ বন্ধ | Host-এর task manager; VM setting | RAM/CPU বাড়ান; BIOS/UEFI-তে VT-x/AMD-V চালু করুন |
| `Permission denied` script চালাতে | Execute permission নেই | `ls -l init-notebook.sh` | `bash init-notebook.sh` দিয়ে চালান, বা `chmod +x` (L01-04) |
| WSL-এ file খুব ধীর বা permission অদ্ভুত | Repository `/mnt/c/`-এ | `pwd` | Linux home-এ (`~`) রাখুন |

> **Fedora-তে:** venv-এর জন্য আলাদা package লাগে না; lock সমস্যায় `dnf`-এর আলাদা process চলছে কিনা দেখুন।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - VM-এ শক্ত password; SSH চালু করলে key-ভিত্তিক login (L01-13)।
  - Lab VM-এ আসল কাজের credential (company cloud key, ব্যক্তিগত email password) রাখবেন না।
  - ISO শুধু official source থেকে, checksum যাচাই সহ।
  - `curl ... | sudo bash` জাতীয় "এক লাইনে install" command চালানোর আগে script পড়ুন — আপনি অচেনা code root অধিকারে চালাচ্ছেন।
  - `--break-system-packages` বা `sudo pip` এড়িয়ে চলুন।
- **Performance:** Host-এর অর্ধেকের বেশি RAM VM-কে দেবেন না — host-ও ধীর হবে। Snapshot জমিয়ে রাখবেন না; পুরোনোগুলো মুছুন।
- **Cost:** সব কিছু বিনামূল্যে (VirtualBox, Ubuntu, WSL)। Disk-এর জায়গাই মূল "খরচ" — Docker image ও VM disk দ্রুত বাড়ে; [docs/hardware-and-cost-guide.md](../docs/hardware-and-cost-guide.md) দেখুন।

## 14. Hands-on exercise

1. **Snapshot অনুশীলন:** VM-এ snapshot নিন, তারপর ইচ্ছা করে `sudo apt remove -y tree` চালান। `tree` কাজ করে না দেখুন। Snapshot-এ ফিরে যান এবং `tree` আবার কাজ করছে নিশ্চিত করুন। Notebook-এ লিখুন।
2. **venv-এর ভেতর:** একটি venv তৈরি করে `cat .venv/pyvenv.cfg` ও `ls -l .venv/bin/python*` দেখুন। Activate করার আগে ও পরে `echo $PATH` তুলনা করুন — ঠিক কী বদলালো?
3. **check_env সম্প্রসারণ:** `check_env.py`-তে একটি check যোগ করুন: `~/.gitconfig`-এ `user.email` set আছে কিনা (`git config --global user.email` চালিয়ে)। না থাকলে WARN। একটি unit test লিখুন (subprocess-নির্ভর অংশ আলাদা function-এ রেখে)।
4. **ShellCheck:** `shellcheck init-notebook.sh` চালান। কোনো warning এলে notebook-এ লিখুন কেন এবং ঠিক করুন।
5. **Fedora তুলনা (ঐচ্ছিক, 🎩):** একটি Fedora VM-এ একই `check_env.py` চালিয়ে কোন tool-এর নাম/package আলাদা লাগলো তালিকা করুন।

## 15. Mini-project — পুনরায় তৈরিযোগ্য lab

একটি `~/devops-notebook/labs/lab-setup.md` লিখুন যাতে অন্য কেউ (বা ভবিষ্যতের আপনি) শূন্য থেকে হুবহু আপনার lab তৈরি করতে পারেন:

1. Host OS, hypervisor ও version।
2. VM-এর RAM/CPU/disk ও Ubuntu version।
3. প্রতিটি install command, ক্রম অনুযায়ী।
4. Git config, repository-র অবস্থান, notebook-এর অবস্থান।
5. `check_env.py --json`-এর ফল (আসল output)।
6. Snapshot-এর নাম ও কোনটি কখন নেওয়া।

তারপর চ্যালেঞ্জ: একটি **নতুন VM** তৈরি করে শুধু এই document অনুসরণ করে lab তৈরি করুন এবং `FAIL=0` পান। কোথাও আটকে গেলে document ঠিক করুন। (এটি Module 12-13-এর Infrastructure as Code ও configuration management-এর মূল ধারণার হাতে-কলমে ভূমিকা: হাতে করা setup document-ও "code"-এর মত পরীক্ষাযোগ্য হওয়া উচিত।)

## 16. Interview প্রশ্ন

1. Lab-এর জন্য VM, container ও WSL-এর মধ্যে কীভাবে বেছে নেবেন?
2. VM snapshot কি backup? কেন বা কেন নয়?
3. Python virtual environment কী এবং activate করলে ভেতরে কী বদলায়?
4. `error: externally-managed-environment` কেন আসে? সঠিক সমাধান কী, এবং কোনটি এড়ানো উচিত?
5. Idempotent script বলতে কী বোঝায়? একটি উদাহরণ দিন।
6. `curl https://... | sudo bash` চালানোর ঝুঁকি কী?

## 17. Self-assessment প্রশ্ন

1. তিনটি উপায়ের (native, VM, WSL2) একটি করে সুবিধা ও সীমাবদ্ধতা লিখুন। আপনি কোনটি বেছে নিলেন এবং কেন?
2. VM-এর analogy (ল্যাবের টেবিল) কোথায় মেলে না?
3. `source .venv/bin/activate` আসলে কোন environment variable বদলায়? এটি জানলে "ভুল python চলছে" সমস্যা কীভাবে diagnose করবেন?
4. `check_env.py`-তে file পড়া ও parse করা আলাদা function কেন?
5. `init-notebook.sh` দ্বিতীয়বার চালালে কী হয় এবং কোন দুটি কৌশল এটি নিশ্চিত করে?
6. Section 5-এর scenario-তে মূল কারণ কী ছিল, এবং PEP 668 কীভাবে এটি প্রতিরোধ করে?

## 18. সংক্ষিপ্ত সারাংশ

- Lab environment হতে হবে **আলাদা, পুনরায় তৈরিযোগ্য, নিরাপদে ভাঙা যায়**। সুপারিশ: Ubuntu 24.04 LTS VM + snapshot। WSL2 শুরু করার জন্য ভালো, তবে কিছু lab-এ VM লাগবে।
- Snapshot নিরাপদে experiment করতে দেয়, কিন্তু **backup নয়**।
- **venv** = project-ভিত্তিক Python package; activate মানে শুধু `PATH` পরিবর্তন। System Python-এ `sudo pip` নয় — PEP 668 এটি আটকায়।
- Script লিখুন **idempotent ও dry-run সমর্থিত**; check script লিখুন **read-only**।
- নিজের lab-এর setup লিখে রাখুন — শূন্য থেকে পুনরায় তৈরি করতে পারাই আসল পরীক্ষা।

## 19. Completion checklist

- [ ] Ubuntu VM (বা WSL2/native) প্রস্তুত, `clean-install` ও `base-setup` snapshot নেওয়া
- [ ] Section 9.2-এর package install ও Git config সম্পন্ন
- [ ] venv তৈরি, activate/deactivate করে `which python` পার্থক্য দেখেছি; PEP 668 error নিজে দেখেছি
- [ ] `init-notebook.sh` চালিয়ে notebook তৈরি, দ্বিতীয়বার চালিয়ে idempotency দেখেছি
- [ ] `check_env.py`-তে `FAIL=0`; JSON ফল notebook-এ সংরক্ষিত
- [ ] `python3 -m unittest -v` চালিয়ে ৯টি test পাস দেখেছি
- [ ] Exercise ১ (snapshot ফিরে যাওয়া) শেষ করেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট করেছি

## 20. Official documentation ও further reading

- Ubuntu Server documentation: https://documentation.ubuntu.com/server/
- Ubuntu download (ISO ও checksum): https://ubuntu.com/download
- Multipass: https://canonical.com/multipass
- Microsoft WSL documentation: https://learn.microsoft.com/windows/wsl/
- VirtualBox: https://www.virtualbox.org/
- Python `venv`: https://docs.python.org/3/library/venv.html
- PEP 668 — Marking Python base environments as "externally managed": https://peps.python.org/pep-0668/
- pipx: https://pipx.pypa.io/
- Fedora documentation: https://docs.fedoraproject.org/

---

**Module 00 সম্পন্ন!** এখন: [Module 00-এর lab](../labs/00-orientation/README.md) ও [module quiz](../assessments/00-orientation/quiz.md)।

**পরের lesson:** L01-01 — Linux architecture: kernel space, user space ও system call
