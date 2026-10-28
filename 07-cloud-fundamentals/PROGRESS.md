# Module 07 Progress — Cloud Fundamentals

Content status: `NOT_STARTED` · `IN_PROGRESS` · `COMPLETED` · `NEEDS_REVISION` (Claude update করবে)  
Learner status: Not started · In progress · Practiced · Assessment passed · Project completed · Needs revision (আপনি update করবেন)

| ID | Lesson | Content | Learner | Required files | Validation | Prerequisites | Next |
|---|---|---|---|---|---|---|---|
| L07-01 | [Virtualization ও hypervisor](L07-01-virtualization-hypervisor.md) | COMPLETED | Not started | `L07-01-virtualization-hypervisor.md`, `code/L07-01/virt_probe.py`, `test_l07_01.py` | 7 test pass (নমুনা DMI); এই laptop-এ আসলে চালানো (physical HP, HypervisorPresent=True — root partition); Linux steal/systemd-detect-virt চালানো হয়নি; কোনো VM/cloud resource তৈরি হয়নি | L06-09 | L07-02 |
| L07-02 | [IaaS, PaaS, SaaS ও shared responsibility model](L07-02-service-models-shared-responsibility.md) | COMPLETED | Not started | `L07-02-service-models-shared-responsibility.md`, `code/L07-02/responsibility.py`, `sample-incidents.json`, `test_l07_02.py` | 5 test pass (matrix invariant সহ); matrix প্রকাশিত model-এর সাধারণ রূপ; resilience layer যোগ; cloud resource তৈরি হয়নি | L07-01 | L07-03 |
| L07-03 | [Region, availability zone ও fault domain](L07-03-regions-zones-fault-domains.md) | COMPLETED | Not started | `L07-03-regions-zones-fault-domains.md`, `code/L07-03/availability.py`, `single-vm.json`, `same-az-pair.json`, `two-az.json`, `test_l07_03.py` | 6 test pass; analytic ও Monte Carlo মিলেছে; naive formula-র দিক নিয়ে নিজের ভুল ধারণা ধরা ও output ঠিক; সংখ্যা অনুমান, SLA নয় | L07-02 | L07-04 |
| L07-04 | [Public বনাম private networking](L07-04-public-private-networking.md) | COMPLETED | Not started | `L07-04-public-private-networking.md`, `code/L07-04/subnet_plan.py`, `taskflow-vpc.json`, `conflict-vpc.json`, `tiny-vpc.json`, `test_l07_04.py` | 4 test pass (overlap-হীনতা ও reserved হিসাব যাচাই); নতুন bug পাওয়া যায়নি; cloud resource বা API call নেই | L07-03 | L07-05 |
| L07-05 | [IAM, identity ও least privilege](L07-05-iam-least-privilege.md) | COMPLETED | Not started | `L07-05-iam-least-privilege.md`, `code/L07-05/policy_eval.py`, `policy_lint.py`, `taskflow-app.json`, `dev-admin.json`, `requests.json`, `test_l07_05.py` | 8 test pass (AWS doc-এর evaluation logic); সরল evaluator — SCP/boundary/resource policy নেই, AWS simulator-এ মেলানো হয়নি; NotAction-admin lint ফাঁক ধরা ও ঠিক | L07-04 | L07-06 |
| L07-06 | [Cloud cost model, budget, tagging ও cleanup](L07-06-cost-budget-tagging-cleanup.md) | COMPLETED | Not started | `L07-06-cost-budget-tagging-cleanup.md`, `code/L07-06/cost_estimate.py`, `example-prices.json`, `taskflow-arch.json`, `tag_audit.py`, `inventory.json`, `test_l07_06.py` | 6 test pass; সব দাম উদাহরণ (আসল নয়, output-এ সতর্কতা); নতুন bug পাওয়া যায়নি; cloud account/billing API ব্যবহার হয়নি | L07-05 | L08-01 |

## Module assessment

| Assessment | Score | তারিখ |
|---|---|---|
| [Module quiz](../assessments/07-cloud-fundamentals/quiz.md) | — | — |
| [Level A lab](../labs/07-cloud-fundamentals/A-local-vm-observe/README.md) | — | — |
| [Level B lab](../labs/07-cloud-fundamentals/B-onprem-vs-cloud/README.md) | — | — |
| [Level C lab](../labs/07-cloud-fundamentals/C-iam-policy-risk/README.md) | — | — |
