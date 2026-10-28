# Templates

নতুন lesson, lab, project বা configuration শুরু করার সময় এখান থেকে copy করুন। প্রতিটি code template সর্বনিম্ন কিন্তু নিরাপদ default সহ লেখা।

## Documentation template

| Template | কখন ব্যবহার |
|---|---|
| [lesson-template.md](lesson-template.md) | প্রতিটি নতুন lesson |
| [lab-template.md](lab-template.md) | Level A/B/C lab |
| [project-readme-template.md](project-readme-template.md) | Portfolio project README |
| [adr-template.md](adr-template.md) | Architecture Decision Record |
| [runbook-template.md](runbook-template.md) | Alert বা operational কাজের runbook |
| [incident-report-template.md](incident-report-template.md) | Incident চলাকালীন/পরে তথ্য সংরক্ষণ |
| [postmortem-template.md](postmortem-template.md) | Blameless postmortem |

## Code ও configuration template

| Template | বিষয় | Module |
|---|---|---|
| [github-actions-ci.yml](github-actions-ci.yml) | CI workflow (test → build) | 11 |
| [Dockerfile.python](Dockerfile.python) | Multi-stage, non-root Python image | 09 |
| [compose.yaml](compose.yaml) | proxy + api + postgres + redis | 09, 10 |
| [terraform-module/](terraform-module/main.tf) | Module structure, variable validation, tagging | 12 |
| [ansible-role/](ansible-role/tasks/main.yml) | Role: tasks, handlers, defaults, templates, meta | 13 |
| [k8s/deployment.yaml](k8s/deployment.yaml) | Deployment + Service + ConfigMap, probe ও security context সহ | 14 |
| [helm-chart/](helm-chart/Chart.yaml) | Minimal Helm chart | 15 |
| [prometheus-alerts.yaml](prometheus-alerts.yaml) | SLO burn-rate ও latency alert | 17, 18 |
| [ml-pipeline/pipeline.py](ml-pipeline/pipeline.py) | ML pipeline কাঠামো ও quality gate | 23, 24 |
| [model-serving-api.py](model-serving-api.py) | FastAPI model-serving API | 24 |
| [agent-tool.py](agent-tool.py) | Read-only, allowlist, audit-যুক্ত agent tool | 27 |

## নিয়ম

- Template-এ কোনো আসল secret নেই; সব জায়গায় `.env` বা secret store।
- Image tag ও version production-এ pin করুন।
- Fedora-তে আলাদা হলে template-এর comment-এ লেখা আছে (যেমন Ansible role-এ Nginx config path)।
