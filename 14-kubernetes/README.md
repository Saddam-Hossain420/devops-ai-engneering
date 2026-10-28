# Module 14 — Kubernetes

**Stage:** 8 · **Lesson:** 24 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

YAML মুখস্থ নয় — architecture ও internals থেকে Kubernetes: control plane, node, workload, Service, Ingress/Gateway, config, storage, probe, resource, RBAC, security, scheduling, autoscaling, NetworkPolicy, CRD/operator, troubleshooting, upgrade, EKS ও multi-tenancy।

## পূর্বশর্ত (Prerequisites)

[10-container-networking-and-storage](../10-container-networking-and-storage/README.md), [11-ci-cd-and-release-engineering](../11-ci-cd-and-release-engineering/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Control loop ও scheduler ব্যাখ্যা
- Probe, resource, secret সহ production-style deployment
- Pending/CrashLoopBackOff/ImagePullBackOff/DNS failure diagnose
- RBAC ও NetworkPolicy দিয়ে workload সুরক্ষা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L14-01 | Kubernetes কেন: orchestration-এর সমস্যা | Beginner |  | NOT_STARTED |
| L14-02 | Control plane: API server, etcd, scheduler, controller manager | Intermediate |  | NOT_STARTED |
| L14-03 | Worker node: kubelet, kube-proxy, container runtime | Intermediate |  | NOT_STARTED |
| L14-04 | Local cluster: kind বনাম minikube বনাম k3d | Beginner |  | NOT_STARTED |
| L14-05 | Pod | Beginner |  | NOT_STARTED |
| L14-06 | ReplicaSet ও Deployment | Beginner |  | NOT_STARTED |
| L14-07 | StatefulSet, DaemonSet, Job ও CronJob | Intermediate |  | NOT_STARTED |
| L14-08 | Service ও cluster DNS | Intermediate |  | NOT_STARTED |
| L14-09 | Ingress ও Gateway API | Intermediate |  | NOT_STARTED |
| L14-10 | ConfigMap ও Secret | Intermediate |  | NOT_STARTED |
| L14-11 | Volume, PV, PVC, StorageClass ও CSI | Intermediate |  | NOT_STARTED |
| L14-12 | Liveness, readiness ও startup probe | Intermediate |  | NOT_STARTED |
| L14-13 | Resource request, limit, QoS ও eviction | Intermediate |  | NOT_STARTED |
| L14-14 | Namespace, RBAC ও ServiceAccount | Intermediate |  | NOT_STARTED |
| L14-15 | Security context ও Pod Security Standards | Advanced |  | NOT_STARTED |
| L14-16 | Scheduling: affinity, taint, toleration, topology spread | Advanced |  | NOT_STARTED |
| L14-17 | Horizontal Pod Autoscaler ও cluster autoscaling | Advanced |  | NOT_STARTED |
| L14-18 | NetworkPolicy ও CNI plugin | Advanced |  | NOT_STARTED |
| L14-19 | Custom Resource Definition ও operator | Advanced |  | NOT_STARTED |
| L14-20 | Rolling update, rollback ও failure recovery | Intermediate |  | NOT_STARTED |
| L14-21 | Troubleshooting: Pending, CrashLoopBackOff, ImagePullBackOff, DNS, probe, PV | Advanced |  | NOT_STARTED |
| L14-22 | Cluster lifecycle ও upgrade | Advanced | 🔗 | NOT_STARTED |
| L14-23 | Amazon EKS | Advanced | 💰 | NOT_STARTED |
| L14-24 | Multi-tenancy ও policy enforcement | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `14-kubernetes/LNN-MM-slug.md`

## Labs

Lab folder: `labs/14-kubernetes/`

- Level A — Pod, Deployment, Service পর্যবেক্ষণ
- Level B — continuous project probes, limits, ingress সহ
- Level C — scheduling ও probe failure diagnose

## সংশ্লিষ্ট project

[P06-kubernetes-platform](../projects/P06-kubernetes-platform/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 6 local cluster-এ চলা
- [ ] Troubleshooting challenge-এ ৫টির মধ্যে ৪টি সমাধান

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
