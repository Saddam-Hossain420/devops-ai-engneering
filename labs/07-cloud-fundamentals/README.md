# Module 07 Labs — Cloud Fundamentals

| Lab | Level | বিষয় | সময় | ব্যবহৃত lesson |
|---|---|---|---|---|
| [A — Local VM তৈরি ও পর্যবেক্ষণ](A-local-vm-observe/README.md) | A — Fundamentals | নিজের machine-এ Ubuntu VM; host ও guest-এর `virt_probe.py`, overcommit, idle বনাম load-এ steal, snapshot ও revert | ৯০ মিনিট | L07-01 |
| [B — On-prem বনাম cloud](B-onprem-vs-cloud/README.md) | B — Integrated | একই পদ্ধতিতে দুটি নকশা: availability (`availability.py`), খরচ (`cost_estimate.py` + on-prem TCO অনুমান), লিখিত সিদ্ধান্ত | ২–২.৫ ঘণ্টা | L07-02, L07-03, L07-04, L07-06 |
| [C — ভুল IAM policy-র ঝুঁকি](C-iam-policy-risk/README.md) | C — Failure and Recovery | CI deploy role-এর ঝুঁকিপূর্ণ policy বিশ্লেষণ (একটি Deny যা কখনো খাটে না সহ) → least-privilege fix → ১৯টি request ও lint দিয়ে প্রমাণ | ৬০–৯০ মিনিট | L07-05 |

**Environment:**

- Lab B ও C সম্পূর্ণ offline — যেকোনো OS-এ Python 3। Checker দুটি Windows-এ reference solution দিয়ে যাচাই করা (solution repo-তে নেই)।
- Lab A-তে নিজের machine-এ একটি VM লাগে। Checker-এর guest দিক simulate করা input দিয়ে যাচাই; **আসল VM-এ চালানো হয়নি**।
- **কোনো lab-এ cloud account, credential বা খরচ নেই।** আসল cloud শুরু Module 08-এ — তার আগে L07-06-এর budget ও cleanup অভ্যাস।
- Lab B-এর খরচ উদাহরণ-দামে (`example-prices.json`) — আসল দাম নয়।

**Module 07-এর completion criteria:**

- "VM ও cloud instance-এর সম্পর্ক" → Lab A।
- "নকশার availability ও খরচ যুক্তি দিয়ে তুলনা" → Lab B।
- "Least-privilege policy লেখা ও বিপজ্জনক policy চেনা" → Lab C।

ফল `~/devops-notebook/labs/`-এ রাখুন এবং [07-cloud-fundamentals/PROGRESS.md](../../07-cloud-fundamentals/PROGRESS.md)-এর Module assessment table আপডেট করুন।
