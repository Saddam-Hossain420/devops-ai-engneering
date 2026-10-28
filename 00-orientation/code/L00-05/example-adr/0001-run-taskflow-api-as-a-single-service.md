# ADR-0001: Run TaskFlow API as a single service

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

Continuous project (TaskFlow API) এখন একজন developer তৈরি করছেন, user সংখ্যা কম, feature কম। Microservice architecture-এ প্রতিটি service-এর আলাদা deploy, network call, monitoring ও failure mode সামলাতে হয়।

## Options considered

1. **একটি service (modular monolith)** — সহজ deploy ও debug; একটি process, একটি log। অসুবিধা: পরে আলাদা অংশ আলাদাভাবে scale করা কঠিন।
2. **Microservices (task, user, notification আলাদা)** — স্বাধীন scale ও deploy। অসুবিধা: network latency, distributed tracing দরকার, একজনের জন্য অনেক operational কাজ।

## Decision

একটি service হিসেবে চালানো হবে, তবে code-এর ভেতরে module (task, user, notification) স্পষ্টভাবে আলাদা রাখা হবে, যাতে প্রয়োজনে পরে আলাদা করা যায়।

## Consequences

- ইতিবাচক: একটি artifact, একটি deployment, সহজ local development।
- নেতিবাচক: একটি অংশের memory leak পুরো service-কে প্রভাবিত করবে।
- পুনর্বিবেচনা: যদি কোনো একটি অংশের load অন্যগুলোর চেয়ে ১০ গুণ হয়, বা team ৩টির বেশি হয়।
