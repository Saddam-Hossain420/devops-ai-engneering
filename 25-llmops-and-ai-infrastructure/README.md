# Module 25 — LLMOps and AI Infrastructure

**Stage:** 15 · **Lesson:** 17 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Operational দৃষ্টিতে LLM: weight, tokenizer, context, memory estimation, quantization, serving engine, gateway, embedding, RAG ও evaluation, versioning, latency metric, batching, rate limit, observability, guardrail ও routing। CPU-বান্ধব বিকল্প সব জায়গায়।

## পূর্বশর্ত (Prerequisites)

[24-mlops](../24-mlops/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Model-এর memory প্রয়োজন হিসাব করা
- TTFT, tokens/sec, p95 মাপা
- RAG pipeline ও evaluation
- Prompt injection ঝুঁকি কমানো

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L25-01 | Operational দৃষ্টিতে LLM architecture | Intermediate |  | NOT_STARTED |
| L25-02 | Model weight, tokenizer, inference ও context window | Intermediate |  | NOT_STARTED |
| L25-03 | Model memory estimation ও VRAM হিসাব | Intermediate |  | NOT_STARTED |
| L25-04 | Quantization ও এর trade-off | Advanced |  | NOT_STARTED |
| L25-05 | Serving engine: Ollama, llama.cpp, vLLM, TGI | Advanced | 🎮 | NOT_STARTED |
| L25-06 | OpenAI-compatible API ও gateway pattern | Intermediate |  | NOT_STARTED |
| L25-07 | Embedding model ও vector database | Intermediate |  | NOT_STARTED |
| L25-08 | RAG pipeline: indexing, retrieval, document update | Advanced |  | NOT_STARTED |
| L25-09 | RAG evaluation | Advanced |  | NOT_STARTED |
| L25-10 | Prompt ও model versioning | Intermediate |  | NOT_STARTED |
| L25-11 | LLM evaluation, regression test ও quality gate | Advanced |  | NOT_STARTED |
| L25-12 | Latency, throughput, tokens/sec, time to first token | Advanced |  | NOT_STARTED |
| L25-13 | Batching, caching, concurrency ও request queue | Advanced |  | NOT_STARTED |
| L25-14 | Rate limiting, quota ও cost per request | Intermediate |  | NOT_STARTED |
| L25-15 | LLM observability ও token usage | Advanced |  | NOT_STARTED |
| L25-16 | Guardrail, input validation, privacy ও prompt injection | Advanced |  | NOT_STARTED |
| L25-17 | Multi-model routing ও fallback | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `25-llmops-and-ai-infrastructure/LNN-MM-slug.md`

## Labs

Lab folder: `labs/25-llmops-and-ai-infrastructure/`

- Level A — memory estimator (Python)
- Level B — local LLM/mock + gateway + metrics
- Level C — timeout ও memory exhaustion diagnose

## সংশ্লিষ্ট project

[P11-llm-serving-performance](../projects/P11-llm-serving-performance/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 11 benchmark report, প্রকৃত মাপা সংখ্যা সহ

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
