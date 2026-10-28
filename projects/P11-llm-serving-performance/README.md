# P11 — LLM Serving and Performance

**Status:** NOT_STARTED · **Milestone:** 10 · **Track:** F · **পূর্বশর্ত:** Module 25, Module 26

## লক্ষ্য

ছোট language model (বা OpenAI-compatible mock) deploy করে memory, latency, throughput ও resource consumption মাপা। ঐচ্ছিক GPU version।

## Architecture

```text
load generator ──► gateway (rate limit, routing, metrics) ──► serving engine
                                                              (CPU: llama.cpp/Ollama · GPU: vLLM)
   Prometheus ◄── TTFT, tokens/sec, p95, queue depth, memory
```

## Features (scope)

- Memory estimate প্রথমে হিসাব, তারপর মাপা
- Concurrency অনুযায়ী benchmark
- Quantization তুলনা
- সৎ hardware requirement ব্যাখ্যা

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] Benchmark report-এ সব সংখ্যা প্রকৃত মাপা (machine spec সহ)
- [ ] Timeout ও overload-এ graceful 429/503

## Resource requirements

CPU baseline: ৮–১৬ GB RAM ছোট quantized model-এর জন্য। 🎮 GPU ঐচ্ছিক।

## Cleanup

Model file ও container মুছে ফেলা; disk space যাচাই।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
