# devops-ai-engineering

> DevOps, SRE, Cloud, Platform Engineering, DevSecOps, MLOps, LLMOps এবং AI Infrastructure শেখার জন্য বাংলায় লেখা, practical-first learning repository।
>
> **Primary practice OS: Ubuntu Linux (LTS)।** Fedora-তে কোনো কিছু আলাদাভাবে করতে হলে সেখানে **"Fedora-তে:"** note দেওয়া থাকবে।

## এই repository-র উদ্দেশ্য

Tool মুখস্থ করা নয়। উদ্দেশ্য হলো:

- system ভেতরে কীভাবে কাজ করে তা বোঝা,
- নিজের হাতে implement করা,
- safe environment-এ ইচ্ছাকৃতভাবে ভেঙে troubleshoot করা,
- কাজ automate করা,
- reliable production infrastructure design করতে শেখা।

এই repository শেষ করলেই কেউ স্বয়ংক্রিয়ভাবে "top 1% engineer" হয়ে যায় না। এটি ধাপে ধাপে senior ও specialized role-এর জন্য দরকারি জ্ঞান, judgment এবং practical অভিজ্ঞতা তৈরি করতে সাহায্য করে।

## Folder and file structure

```text
devops-ai-engineering/
│
├── README.md
├── START-HERE.md
├── ROADMAP.md
├── LEARNING-TRACKS.md
├── CURRICULUM-MAP.md
├── GLOSSARY.md
├── PROGRESS.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── LICENSE
├── .gitignore
├── .editorconfig
│
├── 00-orientation/
├── 01-linux-systems/
├── 02-computer-networking/
├── 03-git-and-collaboration/
├── 04-bash-and-shell-automation/
├── 05-python-for-infrastructure/
├── 06-web-server-and-reverse-proxy/
├── 07-cloud-fundamentals/
├── 08-aws-core-services/
├── 09-docker-and-containers/
├── 10-container-networking-and-storage/
├── 11-ci-cd-and-release-engineering/
├── 12-terraform-and-iac/
├── 13-ansible-and-configuration-management/
├── 14-kubernetes/
├── 15-helm-and-kubernetes-packaging/
├── 16-gitops-and-platform-engineering/
├── 17-monitoring-logging-and-tracing/
├── 18-sre-and-reliability-engineering/
├── 19-devsecops-and-cloud-security/
├── 20-databases-and-distributed-systems/
├── 21-message-queues-and-event-driven-systems/
├── 22-data-engineering/
├── 23-machine-learning-fundamentals/
├── 24-mlops/
├── 25-llmops-and-ai-infrastructure/
├── 26-gpu-computing-and-model-serving/
├── 27-ai-agents-and-infrastructure-automation/
├── 28-advanced-networking-and-service-mesh/
├── 29-cost-optimization-and-finops/
├── 30-disaster-recovery-and-business-continuity/
├── 31-system-design-and-production-architecture/
├── 32-interview-preparation/
│
├── labs/
├── projects/
├── architecture/
├── scripts/
├── templates/
├── assessments/
├── troubleshooting/
├── runbooks/
├── reference/
├── docs/
└── .github/
```

## কোন file-এ কী আছে

| File / Folder | কী আছে |
|---|---|
| [START-HERE.md](START-HERE.md) | কোথা থেকে শুরু করবেন, Ubuntu lab setup, কাজের নিয়ম |
| [ROADMAP.md](ROADMAP.md) | Stage 0–18, milestone এবং readiness criteria |
| [LEARNING-TRACKS.md](LEARNING-TRACKS.md) | Track A–G (DevOps, Platform, SRE, DevSecOps, MLOps, LLMOps, AI Ops) |
| [CURRICULUM-MAP.md](CURRICULUM-MAP.md) | সব module ও lesson-এর ক্রম এবং dependency |
| [GLOSSARY.md](GLOSSARY.md) | গুরুত্বপূর্ণ technical term-এর বাংলা ব্যাখ্যা |
| [PROGRESS.md](PROGRESS.md) | অগ্রগতি, পরের lesson, status |
| [CHANGELOG.md](CHANGELOG.md) | Repository-র গুরুত্বপূর্ণ পরিবর্তন |
| [CONTRIBUTING.md](CONTRIBUTING.md) | লেখার নিয়ম, naming, lesson format |
| `00-orientation/` … `32-interview-preparation/` | প্রতিটি module-এ `README.md` index এবং numbered lesson |
| `labs/` | Level A (fundamentals), Level B (integrated), Level C (failure and recovery) lab |
| `projects/` | 13টি portfolio-quality project |
| `architecture/` | Architecture diagram ও ADR |
| `scripts/` | Repository-র helper script |
| `templates/` | Lesson, lab, project, ADR, runbook, postmortem ইত্যাদির template |
| `assessments/` | Diagnostic test, quiz, exam, rubric |
| `troubleshooting/` | Symptom → cause → fix guide |
| `runbooks/` | Operational runbook |
| `reference/` | Official documentation index, cheat sheet |
| `docs/` | Implementation plan, conventions, hardware ও cost guide |
| `.github/` | GitHub Actions workflow, issue/PR template |

## শুরু করুন

1. [START-HERE.md](START-HERE.md)
2. [ROADMAP.md](ROADMAP.md)
3. [CURRICULUM-MAP.md](CURRICULUM-MAP.md)
4. [PROGRESS.md](PROGRESS.md)

## Lesson-by-lesson command

| Command | কাজ |
|---|---|
| `next` | পরের একটি incomplete lesson সম্পূর্ণ করা |
| `next N` | ঠিক N টি lesson সম্পূর্ণ করা |
| `status` | অগ্রগতি ও পরের lesson দেখানো |
| `explain <topic>` | বাংলায় ব্যাখ্যা (lesson counter বাড়বে না) |
| `review <path>` | file বা lesson review |
| `practice` / `quiz` | সম্পন্ন lesson থেকে exercise বা quiz |
| `repeat` | সর্বশেষ lesson আরো ব্যাখ্যা সহ |
| `fix` | নির্দিষ্ট সমস্যা সমাধান |

## Safety

- সব lab আগে local ও disposable environment-এ করা হবে।
- Destructive বা খরচসাপেক্ষ operation স্পষ্টভাবে চিহ্নিত থাকবে: `⚠️ DESTRUCTIVE`, `💰 COST`।
- কোনো secret Git-এ রাখা হবে না। `.env.example` থাকবে, `.env` নয়।

License: [LICENSE](LICENSE)
