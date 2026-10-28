# Continuous project — architecture-এর বিবর্তন

একটি ছোট Python web API ধাপে ধাপে production platform-এ পরিণত হয়। প্রতিটি ধাপে প্রশ্ন: **আগের architecture-এ কোন সমস্যা ছিল, নতুন ধাপ কোনটি সমাধান করে?**

| ধাপ | Module | Architecture | যে সমস্যা সমাধান হয় |
|---|---|---|---|
| v0.1 | 05 | `python app.py` — একটি process, localhost | কিছুই নেই — শুরু |
| v0.2 | 05 | + structured logging, test | কী ঘটছে বোঝা যায় না; পরিবর্তনে ভাঙে কিনা জানা যায় না |
| v0.3 | 01, 06 | systemd service | terminal বন্ধ করলে app বন্ধ; crash-এ নিজে চালু হয় না |
| v0.4 | 06 | Nginx reverse proxy + TLS | সরাসরি app port খোলা; TLS, static file, buffering নেই |
| v0.5 | 09 | Docker image | "আমার machine-এ চলে" সমস্যা; dependency গোলমাল |
| v0.6 | 09, 10, 20 | Compose: proxy + api + postgres + redis | data persistence, cache, multi-service |
| v0.7 | 11 | GitHub Actions CI | হাতে test/build — ভুলে যাওয়া, অসঙ্গতি |
| v0.8 | 11 | Image publish + automated deploy + verify | হাতে deploy, rollback কঠিন |
| v0.9 | 12, 13 | Terraform (infra) + Ansible (server config) | হাতে তৈরি server — পুনরায় তৈরি অসম্ভব, drift |
| v1.0 | 14, 15 | Kubernetes + Helm | একাধিক replica, self-healing, rolling update |
| v1.1 | 16 | GitOps (Argo CD) | cluster-এ হাতে `kubectl apply` — audit নেই, drift |
| v1.2 | 17, 18 | Metrics, logs, traces, SLO alert | সমস্যা user-এর আগে জানা যায় না |
| v1.3 | 19 | Scan, SBOM, signing, policy | supply-chain ও misconfiguration ঝুঁকি |
| v1.4 | 24 | (ঐচ্ছিক) ML inference service | — |
| v1.5 | 25 | (ঐচ্ছিক) LLM endpoint via gateway | — |
| v1.6 | 27 | Read-only AI ops assistant | incident triage-এ সময় |

## নিয়ম

- প্রতিটি ধাপ যতটা সম্ভব নিজে নিজে চালানো যায় (আগের সব ধাপ ছাড়াই)।
- আগের ধাপে যা দরকার নেই, তা জোর করে আনা হবে না (যেমন v0.3-এ Docker নয়)।
- Kubernetes বা Kafka-র মতো জটিলতা শুধু তখনই, যখন তার মূল্য খরচের চেয়ে বেশি — ADR-এ ব্যাখ্যা থাকবে।
