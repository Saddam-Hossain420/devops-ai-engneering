# P12 — AI Operations Assistant

**Status:** NOT_STARTED · **Milestone:** 11 · **Track:** G · **পূর্বশর্ত:** Module 27

## লক্ষ্য

Constrained Python application যা runbook retrieve করে, অনুমোদিত log পরীক্ষা করে, metric correlate করে এবং evidence-সহ incident summary দেয়। Remediation-এ human approval বাধ্যতামূলক।

## Architecture

```text
operator ──► assistant ──► MCP tools (read-only): read_log(allowlist), query_metrics, search_runbooks
                    │
                    └──► proposed action ──► human approval ──► (ঐচ্ছিক) executor with scoped credential
   সব call ──► audit log (JSONL)
```

## Features (scope)

- Allowlist-ভিত্তিক log access
- প্রতিটি দাবির সাথে evidence reference
- Untrusted log content-কে data হিসেবে আলাদা রাখা
- LLM ব্যর্থ হলে deterministic fallback
- Prompt-এ বা code-এ কোনো credential নয়

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] Prompt-injection log দিলে কোনো tool action নয়
- [ ] Approval ছাড়া write হয় না (test দিয়ে প্রমাণ)
- [ ] Evaluation set-এ triage accuracy মাপা

## Resource requirements

Local LLM (CPU) বা API key (খরচ হিসাব সহ)।

## Cleanup

Audit log সংরক্ষণ নীতি; test credential revoke।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
