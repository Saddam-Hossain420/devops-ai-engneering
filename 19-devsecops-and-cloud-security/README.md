# Module 19 — DevSecOps and Cloud Security

**Stage:** 11 · **Lesson:** 16 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Threat modeling, identity, hardening, certificate, secret, vulnerability scanning, SAST/DAST, container scanning, SBOM ও signing, IaC policy, Kubernetes admission ও runtime security, audit, zero trust, ransomware resilience এবং AI endpoint সুরক্ষা। প্রতিটি tool কী ধরতে পারে আর কী পারে না — স্পষ্টভাবে।

## পূর্বশর্ত (Prerequisites)

[11-ci-cd-and-release-engineering](../11-ci-cd-and-release-engineering/README.md), [12-terraform-and-iac](../12-terraform-and-iac/README.md), [14-kubernetes](../14-kubernetes/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- STRIDE দিয়ে threat model
- Pipeline-এ scan, SBOM, signing যুক্ত করা
- Admission policy দিয়ে unsafe workload আটকানো
- Scan পাস আর আসল security assurance-এর পার্থক্য ব্যাখ্যা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L19-01 | Threat modeling ও attack surface | Intermediate |  | NOT_STARTED |
| L19-02 | IAM, RBAC, least privilege ও workload identity | Intermediate |  | NOT_STARTED |
| L19-03 | Linux, SSH, network ও cloud hardening | Intermediate |  | NOT_STARTED |
| L19-04 | TLS ও certificate lifecycle management | Intermediate |  | NOT_STARTED |
| L19-05 | Secret management ও rotation | Intermediate |  | NOT_STARTED |
| L19-06 | Dependency ও vulnerability scanning | Intermediate |  | NOT_STARTED |
| L19-07 | SAST ও DAST | Intermediate |  | NOT_STARTED |
| L19-08 | Container scanning (Trivy ও বিকল্প) | Intermediate |  | NOT_STARTED |
| L19-09 | SBOM, image signing ও artifact verification | Advanced |  | NOT_STARTED |
| L19-10 | Terraform security check ও policy enforcement | Advanced |  | NOT_STARTED |
| L19-11 | Kubernetes admission policy ও runtime security | Advanced |  | NOT_STARTED |
| L19-12 | Audit log ও security monitoring | Advanced |  | NOT_STARTED |
| L19-13 | Cloud security posture ও incident response | Advanced | 💰 | NOT_STARTED |
| L19-14 | Zero-trust architecture | Advanced |  | NOT_STARTED |
| L19-15 | Backup security ও ransomware resilience | Advanced |  | NOT_STARTED |
| L19-16 | AI infrastructure ও model-serving endpoint সুরক্ষা | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `19-devsecops-and-cloud-security/LNN-MM-slug.md`

## Labs

Lab folder: `labs/19-devsecops-and-cloud-security/`

- Level A — Trivy দিয়ে image scan ও ফল ব্যাখ্যা
- Level B — secure pipeline
- Level C — leaked secret detect ও rotate

## সংশ্লিষ্ট project

[P09-secure-software-delivery](../projects/P09-secure-software-delivery/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 9: unsigned/critical-vuln image deploy আটকায়

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
