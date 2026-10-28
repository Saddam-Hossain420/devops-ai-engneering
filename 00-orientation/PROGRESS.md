# Module 00 Progress — Engineering Orientation

Content status: `NOT_STARTED` · `IN_PROGRESS` · `COMPLETED` · `NEEDS_REVISION` (Claude update করবে)  
Learner status: Not started · In progress · Practiced · Assessment passed · Project completed · Needs revision (আপনি update করবেন)

| ID | Lesson | Content | Learner | Required files | Validation | Prerequisites | Next |
|---|---|---|---|---|---|---|---|
| L00-01 | [DevOps আসলে কী: culture, feedback loop ও DORA metrics](L00-01-what-is-devops.md) | COMPLETED | Not started | `L00-01-what-is-devops.md`, `code/L00-01/dora_metrics.py`, `deployments.csv`, `test_dora_metrics.py` | 7 unit test pass (Python 3.14); script output যাচাই; link check pass; Ubuntu-তে চালানো হয়নি | — | L00-02 |
| L00-02 | [Engineering roles: DevOps, SRE, Platform, Cloud, Security, MLOps, AI Infra](L00-02-engineering-roles.md) | COMPLETED | Not started | `L00-02-engineering-roles.md`, `code/L00-02/role_fit.py`, `roles.json`, `sample-skills.json`, `test_role_fit.py` | 9 unit test pass (Python 3.14); sample output ও হাতে হিসাব মিলেছে; link check pass; Ubuntu-তে চালানো হয়নি | L00-01 | L00-03 |
| L00-03 | [SDLC, Agile, Scrum, Kanban ও release management](L00-03-sdlc-agile-release.md) | COMPLETED | Not started | `L00-03-sdlc-agile-release.md`, `code/L00-03/flow_metrics.py`, `work_items.csv`, `test_flow_metrics.py` | 7 unit test pass (Python 3.14); sample output ও হাতে হিসাব মিলেছে; link check pass; Ubuntu-তে চালানো হয়নি | L00-02 | L00-04 |
| L00-04 | [Environments: development, testing, staging, production](L00-04-environments.md) | COMPLETED | Not started | `L00-04-environments.md`, `code/L00-04/envconfig.py`, `config/*.json`, `test_envconfig.py` | 11 unit test pass (Python 3.14); show/diff/validate output যাচাই (Git Bash); link check pass; Ubuntu-তে চালানো হয়নি | L00-03 | L00-05 |
| L00-05 | [Architecture diagram ও technical documentation (C4, ADR, docs-as-code)](L00-05-diagrams-and-docs.md) | COMPLETED | Not started | `L00-05-diagrams-and-docs.md`, `code/L00-05/adr.py`, `example-adr/*.md`, `test_adr.py` | 9 unit test pass (Python 3.14); new/list/supersede/lint চালিয়ে যাচাই; repo-র architecture/adr lint pass; Mermaid render যাচাই হয়নি; Ubuntu-তে চালানো হয়নি | L00-04 | L00-06 |
| L00-06 | [Experiment, log, measurement ও incident analysis দিয়ে শেখা](L00-06-learning-by-experiment.md) | COMPLETED | Not started | `L00-06-learning-by-experiment.md`, `code/L00-06/latency_experiment.py`, `incident_timeline.py`, `sample-app.log`, `test_l00_06.py` | 7 unit test pass (local HTTP server integration সহ, ResourceWarning-মুক্ত); দুটি tool চালানো Windows 11-এ, latency সংখ্যা সেখানকার; Ubuntu-তে চালানো হয়নি | L00-05 | L00-07 |
| L00-07 | [Lab environment setup: Ubuntu (VM/native/WSL2), Python venv, notebook](L00-07-lab-environment-setup.md) | COMPLETED | Not started | `L00-07-lab-environment-setup.md`, `code/L00-07/check_env.py`, `init-notebook.sh`, `test_check_env.py`; labs A/B/C; module quiz | 9 unit test pass; check_env Windows-এ সঠিক FAIL দেয়; init-notebook.sh bash -n, dry-run, idempotent rerun যাচাই; Lab C-এর timeline ও gate injection চালিয়ে যাচাই; ShellCheck ও Ubuntu install ধাপ চালানো হয়নি | L00-06 | L01-01 |

## Module assessment

| Assessment | Score | তারিখ |
|---|---|---|
| [Module quiz](../assessments/00-orientation/quiz.md) | — | — |
| [Level A lab](../labs/00-orientation/A-delivery-metrics/README.md) | — | — |
| [Level B lab](../labs/00-orientation/B-delivery-design/README.md) | — | — |
| [Level C lab](../labs/00-orientation/C-incident-analysis/README.md) | — | — |
