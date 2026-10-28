# P06 — Kubernetes Application Platform

**Status:** NOT_STARTED · **Milestone:** 6 · **Track:** A, B · **পূর্বশর্ত:** Module 14, Module 15

## লক্ষ্য

Continuous project local Kubernetes cluster-এ: probe, resource limit, secret, ingress/gateway routing ও monitoring সহ।

## Architecture

```text
kind cluster
   ingress/gateway ──► Service ──► Deployment (api, HPA)
                                   ├──► StatefulSet postgres (PVC)
                                   └──► redis
   namespace + RBAC + NetworkPolicy + PodSecurity
```

## Features (scope)

- Helm chart ও Kustomize overlay
- Liveness/readiness/startup probe
- Request/limit ও HPA
- NetworkPolicy: শুধু api → db
- Troubleshooting runbook

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] `kubectl get pods` সব Ready
- [ ] Rolling update-এ downtime নেই (load test চলাকালীন)
- [ ] ভুল image tag-এ ImagePullBackOff এবং rollback
- [ ] Pod মুছলে PVC-তে data থাকে

## Resource requirements

kind + Docker, ৮ GB RAM (🧠 ১৬ GB আরামদায়ক)।

## Cleanup

`kind delete cluster --name <name>`।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
