# ROADMAP — পুরো যাত্রার মানচিত্র

এই roadmap সময়ের প্রতিশ্রুতি দেয় না ("৩ মাসে DevOps engineer" জাতীয়)। অগ্রগতি মাপা হয় **প্রমাণিত সক্ষমতা (demonstrated capability)** দিয়ে: আপনি কী বানাতে, ভাঙতে, খুঁজে বের করতে এবং ব্যাখ্যা করতে পারেন।

---

## Stage overview

```text
Stage 0  Orientation ──► Stage 1  Linux ──► Stage 2  Networking
                                  │
                                  ▼
             Stage 3  Git · Bash · Python · Automation
                                  │
                                  ▼
             Stage 4  Web server · Cloud fundamentals · AWS
                                  │
                                  ▼
             Stage 5  Docker · Container networking & storage
                                  │
                                  ▼
             Stage 6  CI/CD & Release engineering
                                  │
                                  ▼
             Stage 7  Terraform (IaC) · Ansible (Config mgmt)
                                  │
                                  ▼
             Stage 8  Kubernetes · Helm ──► Stage 9  GitOps · Platform
                                  │
                ┌─────────────────┼──────────────────┐
                ▼                 ▼                  ▼
     Stage 10 Observability  Stage 11 DevSecOps  Stage 12 Databases ·
              · SRE                               Messaging · Data eng
                │                                    │
                │                                    ▼
                │                    Stage 13 ML fundamentals ──► Stage 14 MLOps
                │                                                    │
                │                                                    ▼
                │                              Stage 15 LLMOps · GPU · Model serving
                │                                                    │
                └──────────────────────┬─────────────────────────────┘
                                       ▼
                         Stage 16 AI agents · Intelligent ops
                                       │
                                       ▼
             Stage 17 Advanced cloud · Networking · Service mesh
                                       │
                                       ▼
             Stage 18 FinOps · DR · Production operations
                                       │
                                       ▼
             System design · Capstone · Interview preparation
```

| Stage | বিষয় | Module |
|---|---|---|
| 0 | Engineering Orientation | `00-orientation` |
| 1 | Linux and Operating Systems | `01-linux-systems` |
| 2 | Computer Networking | `02-computer-networking` |
| 3 | Git, Bash, Python, Automation | `03`, `04`, `05` |
| 4 | Web Infrastructure and Cloud Fundamentals | `06`, `07`, `08` |
| 5 | Docker and Containers | `09`, `10` |
| 6 | CI/CD and Release Engineering | `11` |
| 7 | Infrastructure as Code and Configuration Management | `12`, `13` |
| 8 | Kubernetes | `14`, `15` |
| 9 | GitOps and Platform Engineering | `16` |
| 10 | Observability and SRE | `17`, `18` |
| 11 | DevSecOps and Security Engineering | `19` |
| 12 | Databases, Distributed Systems, Data Engineering | `20`, `21`, `22` |
| 13 | ML Fundamentals for Infrastructure Engineers | `23` |
| 14 | MLOps | `24` |
| 15 | LLMOps and AI Infrastructure | `25`, `26` |
| 16 | AI Agents and Intelligent Operations | `27` |
| 17 | Advanced Cloud, Networking, Platform | `28` |
| 18 | FinOps and Production Operations | `29`, `30` |
| — | System Design, Capstone, Interview | `31`, `32` |

---

## Continuous project — একটি application যা ধাপে ধাপে বড় হয়

পুরো curriculum জুড়ে একটি ছোট **Python web API** ব্যবহার হবে, যাতে প্রতিটি নতুন ধারণা আগের কাজের সাথে যুক্ত থাকে:

```text
Python script ─► Web API ─► logging/tests ─► systemd service ─► Nginx reverse proxy
   ─► Docker image ─► Docker Compose (DB, cache) ─► GitHub Actions CI
   ─► image publishing ─► deployment automation ─► Terraform infra ─► Ansible config
   ─► Kubernetes ─► GitOps ─► monitoring/alerting ─► security scanning
   ─► (optional) ML inference ─► (optional) LLM endpoint ─► AI ops assistant
```

প্রতিটি ধাপে ব্যাখ্যা থাকবে: আগের architecture-এ কোন সমস্যা ছিল এবং নতুন ধাপ কেন দরকার।

---

## Milestones ও readiness criteria

প্রতিটি milestone-এ: **পূর্বশর্ত**, **যা তৈরি করতে হবে (artifacts)**, **acceptance test**, **সাধারণ ব্যর্থতা**, এবং **যা নিজে ব্যাখ্যা করতে পারতে হবে**।

### Milestone 1 — Linux server আত্মবিশ্বাসের সাথে চালানো ও troubleshoot করা

- **পূর্বশর্ত:** Module 00, 01
- **Artifacts:** systemd service হিসেবে চলা একটি script; disk/memory/process inspection notes; Project 1-এর প্রথম version
- **Acceptance test:** একটি ভাঙা service (ভুল permission, ভুল port, পূর্ণ disk) ১৫ মিনিটের মধ্যে `journalctl`, `systemctl`, `ss`, `df` দিয়ে কারণ খুঁজে ঠিক করা
- **সাধারণ ব্যর্থতা:** `chmod 777` দিয়ে সমস্যা "সমাধান"; log না পড়ে restart করা
- **ব্যাখ্যা করতে পারতে হবে:** process vs thread, signal, permission bit, systemd unit lifecycle, OOM killer

### Milestone 2 — End-to-end network ও HTTP request flow ব্যাখ্যা ও debug করা

- **পূর্বশর্ত:** Module 02, 06
- **Artifacts:** browser → DNS → TCP/TLS → Nginx → app → DB request flow-এর নিজের আঁকা diagram; Nginx reverse proxy config
- **Acceptance test:** DNS ভুল, firewall block, TLS certificate মেয়াদোত্তীর্ণ, upstream down — চারটি পরিস্থিতিতে সঠিক layer চিহ্নিত করা
- **সাধারণ ব্যর্থতা:** 502 vs 504 এর পার্থক্য না বোঝা; DNS cache ভুলে যাওয়া
- **ব্যাখ্যা করতে পারতে হবে:** TCP handshake, CIDR, NAT, DNS resolution chain, TLS handshake, L4 vs L7 load balancing

### Milestone 3 — Containerized application build, test ও automate করা

- **পূর্বশর্ত:** Module 03, 04, 05, 09, 10
- **Artifacts:** multi-stage Dockerfile; Compose stack (proxy, API, DB, cache); unit test; Project 2
- **Acceptance test:** `docker compose up` এ পুরো stack healthy; non-root container; DB data restart-এর পরেও থাকে
- **সাধারণ ব্যর্থতা:** `latest` tag-এ নির্ভরতা; image-এ secret রেখে দেওয়া
- **ব্যাখ্যা করতে পারতে হবে:** image layer, namespace ও cgroup, container DNS, volume vs bind mount

### Milestone 4 — নিরাপদ CI/CD pipeline তৈরি

- **পূর্বশর্ত:** Module 11
- **Artifacts:** GitHub Actions pipeline: test → build → scan → publish → deploy → verify; Project 3
- **Acceptance test:** ইচ্ছাকৃত ভাঙা test pipeline আটকে দেয়; rollback কাজ করে
- **সাধারণ ব্যর্থতা:** long-lived cloud key secret-এ রাখা; mutable tag deploy করা
- **ব্যাখ্যা করতে পারতে হবে:** CI vs CD vs continuous deployment, OIDC, blue-green vs canary, artifact immutability

### Milestone 5 — Terraform দিয়ে infrastructure ও Ansible দিয়ে configuration

- **পূর্বশর্ত:** Module 07, 08, 12, 13
- **Artifacts:** Terraform module; remote state with locking; Ansible role; Project 4, Project 5
- **Acceptance test:** `terraform plan` এ drift ধরা পড়ে; Ansible playbook দ্বিতীয়বার চালালে `changed=0`
- **সাধারণ ব্যর্থতা:** state file Git-এ commit; non-idempotent shell task
- **ব্যাখ্যা করতে পারতে হবে:** state-এর ভূমিকা, plan/apply, Terraform বনাম Ansible-এর দায়িত্বের সীমা

### Milestone 6 — Kubernetes-এ deploy ও troubleshoot

- **পূর্বশর্ত:** Module 14, 15, 16
- **Artifacts:** probes, resource limits, secrets, ingress সহ deployment; Helm chart; GitOps setup; Project 6, 7
- **Acceptance test:** Pending, CrashLoopBackOff, ImagePullBackOff, DNS failure — প্রতিটির কারণ খুঁজে ঠিক করা
- **সাধারণ ব্যর্থতা:** resource request না দেওয়া; readiness ও liveness probe গুলিয়ে ফেলা
- **ব্যাখ্যা করতে পারতে হবে:** control loop, scheduler, Service → Endpoint, QoS class, reconciliation

### Milestone 7 — Monitoring, SLO, alert ও incident runbook

- **পূর্বশর্ত:** Module 17, 18, 20
- **Artifacts:** Prometheus + Grafana stack; SLO document; alert rule; runbook; postmortem; Project 8
- **Acceptance test:** simulated failure-এ alert fire হয় এবং runbook অনুসরণ করে recover করা যায়
- **সাধারণ ব্যর্থতা:** cause-ভিত্তিক noisy alert; SLO ছাড়া alerting
- **ব্যাখ্যা করতে পারতে হবে:** SLI/SLO/SLA, error budget, RED vs USE, trace context propagation

### Milestone 8 — Delivery pipeline ও production workload সুরক্ষিত করা

- **পূর্বশর্ত:** Module 19
- **Artifacts:** threat model; SBOM; image signing; IaC policy check; least-privilege pipeline; Project 9
- **Acceptance test:** unsigned বা critical vulnerability থাকা image deploy হতে বাধা পায়
- **সাধারণ ব্যর্থতা:** "scan পাস = নিরাপদ" ধরে নেওয়া
- **ব্যাখ্যা করতে পারতে হবে:** প্রতিটি scanner কী ধরতে পারে এবং কী পারে না; supply-chain attack

### Milestone 9 — Reproducible MLOps pipeline চালানো

- **পূর্বশর্ত:** Module 23, 24
- **Artifacts:** MLflow tracking; model registry; versioned inference API; drift monitoring; Project 10
- **Acceptance test:** একই data ও code থেকে একই metric; আগের model version-এ rollback
- **সাধারণ ব্যর্থতা:** data leakage; dependency pin না করা
- **ব্যাখ্যা করতে পারতে হবে:** training vs inference, data drift, evaluation gate

### Milestone 10 — AI inference service deploy ও measure করা

- **পূর্বশর্ত:** Module 25, 26
- **Artifacts:** ছোট LLM বা mock inference service; latency/throughput/memory benchmark; Project 11
- **Acceptance test:** TTFT, tokens/sec, p95 latency এবং memory মাপা ও report করা
- **সাধারণ ব্যর্থতা:** memory হিসাব না করে model চালানো; average latency দেখে সন্তুষ্ট হওয়া
- **ব্যাখ্যা করতে পারতে হবে:** VRAM estimation, quantization trade-off, batching, KV cache

### Milestone 11 — নিরাপদ AI-assisted operations workflow

- **পূর্বশর্ত:** Module 27
- **Artifacts:** read-only MCP server; runbook retrieval; incident summary with evidence; Project 12
- **Acceptance test:** prompt-injection যুক্ত log দিলে assistant কোনো action নেয় না; সব write কাজে human approval লাগে
- **সাধারণ ব্যর্থতা:** agent-কে privileged credential দেওয়া
- **ব্যাখ্যা করতে পারতে হবে:** tool permission boundary, audit trail, deterministic fallback

### Milestone 12 — Final production architecture তৈরি ও defend করা

- **পূর্বশর্ত:** Module 28–32
- **Artifacts:** Project 13 (capstone): architecture diagram, threat model, DR plan, cost estimate, runbook, portfolio README
- **Acceptance test:** capstone rubric-এ ≥ 75%; architecture decision-গুলো trade-off সহ মৌখিকভাবে ব্যাখ্যা
- **সাধারণ ব্যর্থতা:** দরকার ছাড়া Kubernetes/Kafka/service mesh যোগ করা
- **ব্যাখ্যা করতে পারতে হবে:** প্রতিটি component কেন আছে, কী ব্যর্থ হলে কী হবে, খরচ কত

---

## Scoring model (সব assessment-এ একই)

| ক্ষেত্র | ওজন |
|---|---|
| Conceptual understanding | 20% |
| Hands-on implementation | 30% |
| Troubleshooting and debugging | 20% |
| Security and reliability | 15% |
| Documentation and engineering judgment | 15% |

Module pass: ≥ 70%। Capstone pass: ≥ 75%।
