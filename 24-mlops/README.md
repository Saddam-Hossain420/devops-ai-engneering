# Module 24 — MLOps

**Stage:** 14 · **Lesson:** 15 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Reproducible experiment, data/model versioning, MLflow, registry, pipeline, evaluation gate, FastAPI serving, batch/online inference, drift monitoring, retraining ও rollback, CI/CD for ML, orchestration, governance ও GPU scheduling।

## পূর্বশর্ত (Prerequisites)

[09-docker-and-containers](../09-docker-and-containers/README.md), [11-ci-cd-and-release-engineering](../11-ci-cd-and-release-engineering/README.md), [23-machine-learning-fundamentals](../23-machine-learning-fundamentals/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- MLflow দিয়ে experiment track ও register
- Versioned inference API deploy
- Drift monitor ও rollback

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L24-01 | MLOps lifecycle | Beginner |  | NOT_STARTED |
| L24-02 | Reproducible ML experiment | Intermediate |  | NOT_STARTED |
| L24-03 | Dataset ও model versioning (DVC) | Intermediate |  | NOT_STARTED |
| L24-04 | MLflow experiment tracking | Intermediate |  | NOT_STARTED |
| L24-05 | Model registry ও artifact storage | Intermediate |  | NOT_STARTED |
| L24-06 | Training pipeline orchestration | Advanced |  | NOT_STARTED |
| L24-07 | Automated evaluation ও quality gate | Advanced |  | NOT_STARTED |
| L24-08 | FastAPI দিয়ে model serving | Intermediate |  | NOT_STARTED |
| L24-09 | Batch inference বনাম online inference | Intermediate |  | NOT_STARTED |
| L24-10 | Model monitoring ও data drift | Advanced |  | NOT_STARTED |
| L24-11 | Retraining trigger, rollback ও version promotion | Advanced |  | NOT_STARTED |
| L24-12 | ML-এর জন্য CI/CD ও continuous training | Advanced |  | NOT_STARTED |
| L24-13 | Kubeflow ও হালকা বিকল্প | Advanced | 🧠 | NOT_STARTED |
| L24-14 | Model lineage, governance ও reproducibility | Advanced |  | NOT_STARTED |
| L24-15 | GPU scheduling ও distributed training concept | Advanced | 🎮 | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `24-mlops/LNN-MM-slug.md`

## Labs

Lab folder: `labs/24-mlops/`

- Level A — MLflow tracking
- Level B — train → register → serve
- Level C — drift ও bad model rollback

## সংশ্লিষ্ট project

[P10-end-to-end-mlops](../projects/P10-end-to-end-mlops/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 10 end-to-end, GPU ছাড়াই

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
