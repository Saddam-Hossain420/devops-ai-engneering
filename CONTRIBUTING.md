# CONTRIBUTING — লেখার নিয়ম ও repository convention

এই নিয়মগুলো মানুষ ও Claude — দুজনের জন্যই প্রযোজ্য।

## 1. ভাষা

- ব্যাখ্যা সহজ, স্বাভাবিক বাংলায়। ছোট বাক্য, ছোট section, numbered step।
- Technical term English-এ রাখুন, প্রথমবার এলে বাংলা ব্যাখ্যা দিন: `Process (চলমান প্রোগ্রাম)`।
- Code, command, configuration কখনো অনুবাদ করবেন না। Code comment বাংলা বা English — যেটা পরিষ্কার।
- English documentation উদ্ধৃত করলে তার অর্থ বাংলায় সারাংশ করুন।

## 2. Operating system

- **Primary: Ubuntu LTS।** সব command প্রথমে Ubuntu-তে কাজ করার মতো লিখুন।
- Fedora-তে আলাদা হলে ঠিক সেই জায়গায় blockquote দিন:

  ```markdown
  > **Fedora-তে:** `sudo dnf install nginx` — Fedora-তে firewall হলো `firewalld`, `ufw` নয়।
  ```

- সাধারণ পার্থক্য (মনে রাখার জন্য):

  | বিষয় | Ubuntu | Fedora |
  |---|---|---|
  | Package manager | `apt`, `dpkg` | `dnf`, `rpm` |
  | Firewall frontend | `ufw` | `firewalld` (`firewall-cmd`) |
  | Mandatory access control | AppArmor | SELinux |
  | DNS tool package | `dnsutils` | `bind-utils` |
  | Nginx config layout | `sites-available/` + `sites-enabled/` | `/etc/nginx/conf.d/` |
  | Web server user | `www-data` | `nginx` / `apache` |
  | Admin group | `sudo` | `wheel` |
  | Python venv | `python3-venv` package দরকার | built-in |

## 3. Naming ও file layout

| জিনিস | নিয়ম | উদাহরণ |
|---|---|---|
| Module folder | `NN-kebab-case/` | `01-linux-systems/` |
| Module index | `NN-module/README.md` | |
| Module progress | `NN-module/PROGRESS.md` | |
| Lesson | `NN-module/LNN-MM-slug.md` | `01-linux-systems/L01-03-filesystem-hierarchy.md` |
| Lesson code | `NN-module/code/LNN-MM/` | `01-linux-systems/code/L01-03/inode_demo.py` |
| Lab | `labs/NN-module/{A,B,C}-slug/README.md` | `labs/01-linux-systems/C-broken-service/README.md` |
| Project | `projects/PNN-slug/` | `projects/P01-linux-ops-toolkit/` |
| Reusable code | `scripts/` বা project-এর ভেতরে — lesson-এ কপি নয়, link | |

## 4. Lesson format

প্রতিটি lesson [templates/lesson-template.md](templates/lesson-template.md) অনুসরণ করবে। মূল ক্রম:

1. সহজ ভাষায় পরিচয় → 2. বাস্তব জীবনের উদাহরণ (ও analogy-র সীমা) → 3. Real-world engineering scenario → 4. Technical internals → 5. Practical demonstration → 6. Troubleshooting ও assessment।

Lesson কখনো শুধু command বা শুধু definition হবে না।

## 5. Code quality

- **Python:** 3.11+, type hint, standard library প্রথমে, `logging` module, error handling, test (`unittest` বা `pytest`)।
- **Bash:** `#!/usr/bin/env bash`, `set -euo pipefail` (সীমাবদ্ধতা lesson L04-01-এ ব্যাখ্যা), `shellcheck` পরিষ্কার।
- কোনো hard-coded password, key, token নয়। `.env.example` দিন, `.env` নয়।
- Script যতটা সম্ভব আবার চালানো নিরাপদ (idempotent) রাখুন।
- Pseudocode, mock বা অসম্পূর্ণ implementation স্পষ্টভাবে চিহ্নিত করুন।

## 6. Output-এর সততা

- Terminal output বানিয়ে লিখবেন না। উদাহরণ output হলে লিখুন: **"উদাহরণ output (আপনার মান ভিন্ন হবে)"**।
- যা চালিয়ে যাচাই করা হয়েছে এবং যা হয়নি তা আলাদা করে লিখুন।
- Version-sensitive command-এ tested/targeted version লিখুন।
- Documentation link বানাবেন না। নিশ্চিত না হলে link দেবেন না।

## 7. Safety label

| Label | কখন |
|---|---|
| `⚠️ DESTRUCTIVE` | data মুছতে পারে, disk/firewall/system পরিবর্তন করে |
| `💰 COST` | paid cloud resource তৈরি করে |
| `🖥️ VM` | full VM বা real machine দরকার |
| `🎮 GPU` | GPU দরকার |

Destructive ও costly কাজের আগে সবসময় cleanup নির্দেশ দিন।

## 8. Lesson সম্পন্ন করার checklist (`next` command)

- [ ] Lesson Markdown সব section সহ
- [ ] দরকারি Python code / configuration আসল file হিসেবে, lesson থেকে relative link
- [ ] Code চালিয়ে বা syntax check করে যাচাই (যা সম্ভব)
- [ ] Exercise ও assessment প্রশ্ন
- [ ] সব internal link কাজ করে
- [ ] Module `README.md` ও `PROGRESS.md` আপডেট
- [ ] Root `PROGRESS.md` ও `CHANGELOG.md` আপডেট

## 9. Git commit message

```text
<type>(<scope>): <সংক্ষিপ্ত বিবরণ>

type: lesson | lab | project | fix | docs | chore
উদাহরণ: lesson(L01-03): filesystem hierarchy ও inode lesson যোগ
```
