# Runbook: <Alert / কাজের নাম>

| | |
|---|---|
| **Service** | |
| **Owner** | |
| **Alert** | `<AlertName>` |
| **Severity** | SEV1 / SEV2 / SEV3 |
| **শেষ যাচাই** | YYYY-MM-DD (কেউ আসলে চালিয়ে দেখেছেন) |

## এই alert-এর অর্থ

<user-এর উপর প্রভাব কী।>

## দ্রুত যাচাই (প্রথম ৫ মিনিট)

```bash
# read-only command — কিছু পরিবর্তন করে না
```

## Diagnosis

| যা দেখবেন | কোথায় | স্বাভাবিক মান | অস্বাভাবিক হলে |
|---|---|---|---|
| | dashboard / command | | ধাপ X-এ যান |

## Mitigation

1. **নিরাপদ (reversible):** ...
2. **⚠️ ঝুঁকিপূর্ণ (approval দরকার):** ...

## Rollback

## Escalation

| কখন | কাকে | কীভাবে |
|---|---|---|

## Communication template

> [SEVx] <service> — <প্রভাব>। তদন্ত চলছে। পরবর্তী আপডেট HH:MM-এ।

## Incident-এর পরে

- [ ] Incident report
- [ ] Postmortem দরকার কিনা সিদ্ধান্ত
- [ ] এই runbook আপডেট
