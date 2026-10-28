# Module 10 — Container Networking and Storage

**Stage:** 5 · **Lesson:** 7 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Bridge/host/none network, container DNS, port publishing-এর পেছনে iptables/nftables, overlay network, volume/bind mount/tmpfs, data persistence ও backup এবং rootless Podman।

## পূর্বশর্ত (Prerequisites)

[09-docker-and-containers](../09-docker-and-containers/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Container network traffic-এর পথ ব্যাখ্যা
- Container DNS সমস্যা diagnose
- Data persistence ও backup design
- Rootless container চালানো

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L10-01 | Bridge, host ও none network | Intermediate |  | NOT_STARTED |
| L10-02 | Container DNS ও service discovery | Intermediate |  | NOT_STARTED |
| L10-03 | Port publishing এবং iptables/nftables-এর ভূমিকা | Advanced |  | NOT_STARTED |
| L10-04 | Overlay network-এর পরিচিতি | Advanced | 🔗 | NOT_STARTED |
| L10-05 | Volume, bind mount ও tmpfs | Intermediate |  | NOT_STARTED |
| L10-06 | Container data persistence ও backup | Intermediate |  | NOT_STARTED |
| L10-07 | Rootless container ও Podman | Intermediate | 🎩 | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `10-container-networking-and-storage/LNN-MM-slug.md`

## Labs

Lab folder: `labs/10-container-networking-and-storage/`

- Level A — network mode তুলনা
- Level B — persistent DB + backup container
- Level C — container DNS ও port conflict সমস্যা

## সংশ্লিষ্ট project

[P02-production-web-app](../projects/P02-production-web-app/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Volume backup ও restore যাচাই

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
