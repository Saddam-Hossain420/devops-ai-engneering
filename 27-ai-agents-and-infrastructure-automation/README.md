# Module 27 — AI Agents and Infrastructure Automation

**Stage:** 16 · **Lesson:** 13 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

Tool calling, permission boundary, MCP, Python MCP server, read-only inspection tool, log triage, runbook retrieval, human approval, prompt injection, sandbox, evaluation, AI-assisted IaC/K8s এবং cost/latency monitoring। প্রথম implementation সম্পূর্ণ read-only।

## পূর্বশর্ত (Prerequisites)

[18-sre-and-reliability-engineering](../18-sre-and-reliability-engineering/README.md), [25-llmops-and-ai-infrastructure](../25-llmops-and-ai-infrastructure/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Read-only MCP server তৈরি
- Untrusted log-এর prompt injection প্রতিরোধ
- Human approval ও audit trail

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L27-01 | LLM-based agent ও tool calling | Intermediate |  | NOT_STARTED |
| L27-02 | Agent permission ও execution boundary | Intermediate |  | NOT_STARTED |
| L27-03 | Model Context Protocol (MCP) | Intermediate |  | NOT_STARTED |
| L27-04 | ছোট Python MCP server তৈরি | Advanced |  | NOT_STARTED |
| L27-05 | Read-only infrastructure inspection tool | Advanced |  | NOT_STARTED |
| L27-06 | Log summarization ও incident triage | Advanced |  | NOT_STARTED |
| L27-07 | Internal runbook ও documentation-এর উপর retrieval | Advanced |  | NOT_STARTED |
| L27-08 | Human approval ও audit trail | Advanced |  | NOT_STARTED |
| L27-09 | Prompt injection ও untrusted log/data handling | Advanced |  | NOT_STARTED |
| L27-10 | Sandboxed execution ও credential isolation | Advanced |  | NOT_STARTED |
| L27-11 | Agent evaluation, failure recovery ও deterministic fallback | Advanced |  | NOT_STARTED |
| L27-12 | AI-assisted Terraform ও Kubernetes workflow | Advanced |  | NOT_STARTED |
| L27-13 | Agent system-এর cost ও latency monitoring | Advanced |  | NOT_STARTED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `27-ai-agents-and-infrastructure-automation/LNN-MM-slug.md`

## Labs

Lab folder: `labs/27-ai-agents-and-infrastructure-automation/`

- Level A — MCP server-এ একটি read-only tool
- Level B — log + runbook triage assistant
- Level C — prompt-injection log দিয়ে assistant পরীক্ষা

## সংশ্লিষ্ট project

[P12-ai-operations-assistant](../projects/P12-ai-operations-assistant/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Project 12: injection test-এ কোনো action নয়, সব write-এ approval

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
