# Module 26 — GPU Computing and Model Serving

**Stage:** 15 · **Lesson:** 9 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

GPU architecture, driver/CUDA/container, Kubernetes-এ GPU, VRAM ও OOM, inference optimization, multi-GPU, autoscaling, cloud GPU cost এবং training/fine-tuning/inference পার্থক্য। 🎮 GPU lab-এ CPU বিকল্প ও সৎ hardware ব্যাখ্যা।

## পূর্বশর্ত (Prerequisites)

[14-kubernetes](../14-kubernetes/README.md), [25-llmops-and-ai-infrastructure](../25-llmops-and-ai-infrastructure/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- VRAM utilization ও OOM কারণ ব্যাখ্যা
- Workload metric দিয়ে autoscaling
- GPU cost per token হিসাব

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L26-01 | GPU architecture: infrastructure engineer-এর দৃষ্টিতে | Intermediate |  | NOT_STARTED |
| L26-02 | GPU driver, CUDA ও container | Advanced | 🎮 | NOT_STARTED |
| L26-03 | Kubernetes-এ GPU | Advanced | 🎮 | NOT_STARTED |
| L26-04 | VRAM utilization ও OOM troubleshooting | Advanced | 🎮 | NOT_STARTED |
| L26-05 | Inference optimization | Advanced |  | NOT_STARTED |
| L26-06 | Multi-GPU ও distributed inference concept | Advanced | 🎮 | NOT_STARTED |
| L26-07 | AI workload autoscaling | Advanced |  | NOT_STARTED |
| L26-08 | Cloud GPU option ও cost | Advanced | 💰 | NOT_STARTED |
| L26-09 | Training বনাম fine-tuning বনাম inference | Intermediate |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `26-gpu-computing-and-model-serving/LNN-MM-slug.md`

## Labs

Lab folder: `labs/26-gpu-computing-and-model-serving/`

- Level A — GPU/CPU benchmark তুলনা
- Level B — GPU-সক্ষম serving (ঐচ্ছিক, 🎮)
- Level C — OOM simulation (ছোট workload)

## সংশ্লিষ্ট project

[P11-llm-serving-performance](../projects/P11-llm-serving-performance/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] GPU capacity plan ও cost estimate

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
