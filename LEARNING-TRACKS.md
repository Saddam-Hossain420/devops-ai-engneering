# LEARNING TRACKS — Specialization path

সব track একটি **shared foundation** এর উপর দাঁড়িয়ে। Foundation ছাড়া specialization শুরু করলে পরে troubleshooting-এ আটকে যাবেন।

## Shared foundation (সব track-এর জন্য বাধ্যতামূলক)

| Module | কেন সবার দরকার |
|---|---|
| 00 Orientation | Role, culture, SDLC, environment-এর ধারণা |
| 01 Linux systems | প্রায় সব server, container ও cluster Linux-এ চলে |
| 02 Computer networking | প্রতিটি production সমস্যার বড় অংশ network-এ |
| 03 Git and collaboration | সব configuration ও code-এর source of truth |
| 04 Bash automation | Server-এ দ্রুত automation |
| 05 Python for infrastructure | বড় automation, API, testing, ML, AI tool |
| 09 Docker and containers | আধুনিক deployment-এর মৌলিক unit |

```text
                 ┌──────────── Shared foundation (00–05, 09) ────────────┐
                 │                                                       │
   ┌─────────┬───┴──────┬──────────┬────────────┬───────────┬───────────┐
   ▼         ▼          ▼          ▼            ▼           ▼           ▼
Track A   Track B    Track C    Track D      Track E     Track F     Track G
DevOps    Cloud/     SRE        DevSecOps    MLOps       AI Infra/   AI-Powered
          Platform                                       LLMOps      Ops
```

---

## Track A — DevOps Engineer

- **লক্ষ্য:** Code থেকে production পর্যন্ত নির্ভরযোগ্য, automated delivery।
- **Module:** 06, 07, 08, 10, 11, 12, 13, 14, 17
- **Project যা দক্ষতা প্রমাণ করে:** Project 1, 2, 3, 4, 5, 6
- **Milestone:** 1–6

## Track B — Cloud and Platform Engineer

- **লক্ষ্য:** Developer-দের জন্য self-service, নিরাপদ, multi-environment platform।
- **পূর্বশর্ত:** Track A-এর 07, 08, 12, 14
- **Module:** 15, 16, 19 (policy অংশ), 28, 29
- **Project:** Project 4, 6, 7, 13
- **Milestone:** 5, 6, 12

## Track C — SRE and Production Reliability

- **লক্ষ্য:** Reliability-কে measurable ও engineering problem হিসেবে পরিচালনা।
- **পূর্বশর্ত:** 06, 11, 14
- **Module:** 17, 18, 20, 21, 30, 31
- **Project:** Project 8, 13
- **Milestone:** 7, 12

## Track D — DevSecOps Engineer

- **লক্ষ্য:** Identity, supply chain ও workload security।
- **পূর্বশর্ত:** 08, 11, 12, 14
- **Module:** 19, 16 (policy as code), 28 (identity federation), 30 (ransomware resilience)
- **Project:** Project 3, 9, 13
- **Milestone:** 4, 8

## Track E — MLOps Engineer

- **লক্ষ্য:** Reproducible training, automated deployment, model monitoring ও rollback।
- **পূর্বশর্ত:** 11, 14 (basic), 20
- **Module:** 22, 23, 24
- **Project:** Project 10
- **Milestone:** 9

## Track F — AI Infrastructure and LLMOps Engineer

- **লক্ষ্য:** Model serving, GPU infrastructure, inference optimization, cost control।
- **পূর্বশর্ত:** Track E, 14, 17
- **Module:** 25, 26, 29 (GPU cost)
- **Project:** Project 11
- **Milestone:** 10

## Track G — AI-Powered Operations Engineer

- **লক্ষ্য:** MCP, constrained agent, runbook retrieval, safe incident triage।
- **পূর্বশর্ত:** 17, 18, 25 (RAG অংশ)
- **Module:** 27
- **Project:** Project 12
- **Milestone:** 11

---

## Track বাছাইয়ের পরামর্শ

1. প্রথমে **Track A** শেষ করুন। এটি বাকি সব track-এর বাস্তব ভিত্তি।
2. এরপর **Track C (SRE)** অথবা **Track B (Platform)**। দুটোই senior role-এ সরাসরি কাজে লাগে।
3. AI দিকে যেতে চাইলে **E → F → G** ক্রমে যান।
4. **Track D (DevSecOps)** প্রতিটি track-এর সাথে সমান্তরালে চলতে পারে।

আপনার WordPress/PHP অভিজ্ঞতা কাজে লাগবে Module 06 (PHP-FPM, Nginx), 09 (WordPress container) এবং 11 (application deployment)-এ।
