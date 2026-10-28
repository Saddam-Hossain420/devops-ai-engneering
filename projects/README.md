# Projects — Portfolio-quality project

প্রতিটি project আগের module-এর দক্ষতা ব্যবহার করে এবং একটি milestone প্রমাণ করে। Project-এ এমন কিছু জোর করে ঢোকানো হয় না (Kubernetes, Kafka, service mesh, GPU) যার operational খরচ মূল্যের চেয়ে বেশি — প্রতিটি সিদ্ধান্তের ব্যাখ্যা ADR-এ থাকবে।

| Project | বিষয় | Module | Milestone | Track | Status |
|---|---|---|---|---|---|
| [P01](P01-linux-ops-toolkit/README.md) | Linux Server Operations Toolkit | 01, 04, 05 | 1 | A, C | NOT_STARTED |
| [P02](P02-production-web-app/README.md) | Production-Style Web Application | 05, 06, 09, 10, 20 | 3 | A | NOT_STARTED |
| [P03](P03-cicd-deployment/README.md) | Automated CI/CD Deployment | 03, 11 | 4 | A, D | NOT_STARTED |
| [P04](P04-aws-terraform-infrastructure/README.md) | Infrastructure as Code on AWS | 07, 08, 12 | 5 | A, B | NOT_STARTED |
| [P05](P05-ansible-configuration/README.md) | Configuration Management | 06, 13 | 5 | A, B | NOT_STARTED |
| [P06](P06-kubernetes-platform/README.md) | Kubernetes Application Platform | 14, 15 | 6 | A, B | NOT_STARTED |
| [P07](P07-gitops-platform/README.md) | GitOps Platform | 16 | 6 | B | NOT_STARTED |
| [P08](P08-observability-incident-response/README.md) | Observability and Incident Response | 17, 18 | 7 | C | NOT_STARTED |
| [P09](P09-secure-software-delivery/README.md) | Secure Software Delivery | 11, 19 | 8 | D | NOT_STARTED |
| [P10](P10-end-to-end-mlops/README.md) | End-to-End MLOps | 23, 24 | 9 | E | NOT_STARTED |
| [P11](P11-llm-serving-performance/README.md) | LLM Serving and Performance | 25, 26 | 10 | F | NOT_STARTED |
| [P12](P12-ai-operations-assistant/README.md) | AI Operations Assistant | 27 | 11 | G | NOT_STARTED |
| [P13](P13-capstone-production-platform/README.md) | Capstone Production Platform | 28, 29, 30, 31 | 12 | সব | NOT_STARTED |

## Continuous project

একটি ছোট Python web API (Module 05-এ শুরু) ধাপে ধাপে বড় হবে: systemd → Nginx → Docker → Compose → CI → Terraform/Ansible → Kubernetes → GitOps → monitoring → security → ML/LLM → AI ops assistant। Project 2, 3, 5, 6, 7, 8, 9 এই একই application ব্যবহার করে।

## প্রতিটি project-এর নিয়ম

- `README.md` — portfolio README (template: [templates/project-readme-template.md](../templates/project-readme-template.md))
- `docs/` — architecture, ADR, threat model, runbook
- এক command-এ local startup এবং আলাদা cleanup
- `.env.example`, কোনো আসল secret নয়
- Test ও acceptance check
- Cloud project হলে cost estimate ও cleanup checklist বাধ্যতামূলক
