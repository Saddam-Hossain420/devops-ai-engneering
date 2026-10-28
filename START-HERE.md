# START HERE — কোথা থেকে শুরু করবেন

এই file পড়ে আপনি জানবেন:

1. এই repository কীভাবে ব্যবহার করবেন,
2. কোন environment-এ practice করবেন,
3. প্রতিটি lesson কীভাবে পড়বেন ও practice করবেন,
4. কখন একটি lesson "সম্পন্ন" ধরা হবে।

---

## 1. আপনার learning environment

### Primary: Ubuntu Linux

সব lesson, command এবং lab **Ubuntu LTS (24.04 লক্ষ্য করে লেখা)**-এর জন্য তৈরি। যেখানে Fedora-তে আলাদা কিছু করতে হয়, সেখানে এভাবে note থাকবে:

> **Fedora-তে:** `apt install nginx` এর বদলে `sudo dnf install nginx`।

Ubuntu চালানোর তিনটি উপায় (যেকোনো একটি বেছে নিন):

| উপায় | সুবিধা | সীমাবদ্ধতা |
|---|---|---|
| Ubuntu সরাসরি install (dual boot বা আলাদা laptop) | সবচেয়ে বাস্তব, সব lab চলবে | আলাদা partition/machine দরকার |
| Virtual Machine (VirtualBox, VMware, Hyper-V, KVM) | Snapshot নিয়ে ভাঙা-জোড়া করা সহজ, নিরাপদ | RAM ভাগ হয়ে যায় |
| WSL2 (Windows-এর ভেতরে Ubuntu) | দ্রুত শুরু করা যায় | কিছু kernel-level lab (AppArmor, boot, disk partition) পুরোপুরি চলে না |

যে lesson-এ পূর্ণ Linux VM বা real machine দরকার, সেখানে **🖥️ VM** label থাকবে।

### Minimum hardware (সাধারণ developer laptop)

| Resource | Minimum | সুবিধাজনক |
|---|---|---|
| CPU | 4 core | 8+ core |
| RAM | 8 GB | 16 GB |
| Disk | 40 GB free | 80 GB+ free |
| GPU | দরকার নেই | ঐচ্ছিক (GPU lesson-এ CPU বিকল্প থাকবে) |

Label-এর অর্থ:

| Label | অর্থ |
|---|---|
| 🖥️ VM | Full Linux VM বা real machine দরকার |
| 💰 COST | Paid cloud resource তৈরি হতে পারে — আগে cost estimate ও cleanup plan |
| 🎮 GPU | Dedicated GPU দরকার (CPU বিকল্প দেওয়া থাকবে) |
| 🧠 16GB | ১৬ GB+ RAM সুপারিশকৃত |
| 🔗 MULTI | একাধিক machine/VM দরকার |
| ⚠️ DESTRUCTIVE | Data মুছে যেতে পারে বা system পরিবর্তন হয় — শুধু disposable environment-এ |

### প্রথম দিনের setup (Ubuntu)

নিচের command-গুলো system-এ package install করে। প্রতিটি কী করে তা পাশে লেখা আছে।

```bash
# Package list update করে (কোনো software পরিবর্তন করে না, শুধু index refresh)
sudo apt update

# প্রথম কয়েকটি module-এর জন্য দরকারি tool install করে
sudo apt install -y git curl wget vim tree jq python3 python3-venv python3-pip \
    build-essential net-tools dnsutils iproute2 traceroute mtr-tiny tcpdump htop

# যাচাই: version দেখায়
git --version
python3 --version
jq --version
```

> **Fedora-তে:**
> ```bash
> sudo dnf install -y git curl wget vim tree jq python3 python3-pip \
>     gcc make net-tools bind-utils iproute traceroute mtr tcpdump htop
> ```
> Fedora-তে `python3 -m venv` আলাদা package ছাড়াই কাজ করে। `dnsutils`-এর বদলে `bind-utils`।

Docker, Kubernetes, Terraform, Ansible ইত্যাদি **নিজ নিজ module-এ** install করা শেখানো হবে। সেগুলো এখনই install করার দরকার নেই।

---

## 2. প্রতিটি lesson কীভাবে পড়বেন

প্রতিটি lesson একই ক্রমে সাজানো:

1. **সহজ ভাষায় পরিচয়** — এটা কী, কেন এসেছে, কোন সমস্যা সমাধান করে
2. **বাস্তব জীবনের উদাহরণ** — analogy, এবং analogy কোথায় মেলে না
3. **Real-world engineering scenario** — বাস্তব production পরিস্থিতি
4. **Technical internals** — ভেতরে আসলে কী ঘটে
5. **Practical demonstration** — command, Python code, configuration
6. **Troubleshooting ও assessment** — সাধারণ ভুল, exercise, প্রশ্ন

পড়ার নিয়ম:

- শুধু পড়বেন না — প্রতিটি command নিজে চালান এবং output নিজের চোখে দেখুন।
- Lesson-এ "উদাহরণ output" লেখা থাকলে আপনার output হুবহু মিলবে না। গঠন মেলাবেন, সংখ্যা নয়।
- নিজের একটি **engineering notebook** রাখুন (যেমন `~/devops-notebook/`), যেখানে লিখবেন: কী চালালেন, কী দেখলেন, কী বুঝলেন, কী ভাঙল।

---

## 3. কখন একটি lesson "সম্পন্ন"?

শুধু পড়া শেষ করলে lesson সম্পন্ন হয় না। এগুলো লাগবে:

- [ ] Practical demonstration নিজে চালিয়েছেন এবং ফলাফল যাচাই করেছেন
- [ ] Hands-on exercise শেষ করেছেন
- [ ] Self-assessment প্রশ্নের উত্তর নিজের ভাষায় লিখতে পেরেছেন
- [ ] Completion checklist-এর সব item টিক দিয়েছেন

আপনার নিজের অগ্রগতির status ([PROGRESS.md](PROGRESS.md)-এ):

| Status | অর্থ |
|---|---|
| Not started | শুরু হয়নি |
| In progress | পড়ছেন / practice করছেন |
| Practiced | Practical ও exercise শেষ |
| Assessment passed | Quiz/assessment-এ পাস (≥ 70%) |
| Project completed | সংশ্লিষ্ট project শেষ |
| Needs revision | আবার দেখা দরকার |

---

## 4. Claude-এর সাথে কাজের command

| Command | কাজ |
|---|---|
| `next` | পরের একটি lesson তৈরি ও সম্পন্ন করা |
| `next 2`, `next 3`, `next N` | ঠিক N টি lesson |
| `status` | অগ্রগতি দেখানো |
| `explain <topic>` | বাংলায় ব্যাখ্যা, lesson counter বাড়বে না |
| `review <path>` | কোনো file review |
| `practice` | সম্পন্ন lesson থেকে practical exercise |
| `quiz` | বোঝাপড়া যাচাই |
| `repeat` | সর্বশেষ lesson আরো ব্যাখ্যা ও exercise সহ |
| `fix` | নির্দিষ্ট সমস্যা সমাধান |

---

## 5. Safety নিয়ম (বাধ্যতামূলক)

1. সব lab আগে local, disposable environment-এ (VM, container, isolated network)।
2. `sudo` শুধু তখনই, যখন lesson স্পষ্টভাবে বলে এবং কেন লাগে তা বুঝেছেন।
3. `⚠️ DESTRUCTIVE` চিহ্নিত কাজ কখনো আপনার main system বা কোনো production system-এ নয়।
4. Cloud resource তৈরির আগে **budget alert** সেট করুন এবং cleanup checklist পড়ুন।
5. কোনো password, access key, token Git-এ, shell history-তে বা screenshot-এ রাখবেন না।
6. শুধু নিজের বা অনুমতিপ্রাপ্ত system-এ security scan চালাবেন।

---

## 6. এখন কী করবেন

1. [ROADMAP.md](ROADMAP.md) পড়ে পুরো যাত্রার ধারণা নিন।
2. [assessments/](assessments/) folder-এর diagnostic assessment দিয়ে নিজের বর্তমান level যাচাই করুন।
3. [CURRICULUM-MAP.md](CURRICULUM-MAP.md) থেকে প্রথম lesson শুরু করুন: **Module 00 — Engineering Orientation**।
