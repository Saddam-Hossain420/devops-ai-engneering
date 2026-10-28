# Runbooks

Runbook = নির্দিষ্ট alert বা operational কাজ সামলানোর ধাপে ধাপে নির্দেশিকা, যা রাত ৩টায় ঘুম-চোখেও অনুসরণ করা যায়।

Template: [templates/runbook-template.md](../templates/runbook-template.md)

## ভালো runbook-এর বৈশিষ্ট্য

- প্রথম ৫ মিনিটের **read-only** যাচাই ধাপ আগে।
- প্রতিটি command copy-paste যোগ্য এবং কী করে তা লেখা।
- ঝুঁকিপূর্ণ ধাপ `⚠️` চিহ্নিত, approval লাগলে স্পষ্ট বলা।
- Rollback ও escalation পথ।
- "শেষ যাচাই" তারিখ — কেউ আসলে চালিয়ে দেখেছেন।

## পরিকল্পিত runbook (সংশ্লিষ্ট lesson-এর সাথে তৈরি হবে)

| Runbook | Module |
|---|---|
| `disk-almost-full.md` | 01 |
| `service-crashloop-systemd.md` | 01 |
| `nginx-upstream-errors.md` | 06 |
| `certificate-expiring.md` | 06, 19 |
| `container-unhealthy.md` | 09 |
| `deployment-rollback.md` | 11 |
| `kubernetes-pod-not-ready.md` | 14 |
| `high-error-rate-slo-burn.md` | 18 |
| `database-restore.md` | 20, 30 |
| `leaked-secret-rotation.md` | 19 |
| `model-serving-latency.md` | 25 |
