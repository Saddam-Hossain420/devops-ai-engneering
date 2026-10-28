# Capstone evaluation rubric (Project 13)

Pass: **≥ 75%**, এবং কোনো ক্ষেত্রে score 1 বা 0 নয়। Score পদ্ধতি: [scoring-model.md](scoring-model.md)।

| ক্ষেত্র | ওজন | 4 (চমৎকার) | 2 (আংশিক) | প্রমাণ |
|---|---|---|---|---|
| Conceptual understanding | 20% | প্রতিটি component কেন আছে, কী ব্যর্থ হলে কী হবে — মৌখিকভাবে ব্যাখ্যা | কিছু decision-এর কারণ বলতে পারে না | architecture walkthrough |
| Hands-on implementation | 30% | এক command-এ চালু; IaC দিয়ে পুনরায় তৈরি যায়; CI/CD সবুজ | হাতে ধাপ লাগে; কিছু অংশ কাজ করে না | demo, repository |
| Troubleshooting | 20% | তিনটি injected failure নিজে diagnose ও recover, runbook অনুযায়ী | সাহায্য লাগে বা অনুমানভিত্তিক | live failure drill |
| Security and reliability | 15% | threat model, least privilege, signed image, backup restore drill, SLO | কিছু নিয়ন্ত্রণ নেই | threat model, drill report |
| Documentation and judgment | 15% | ADR, DR plan, cost estimate, cleanup, portfolio README; অপ্রয়োজনীয় জটিলতা নেই | document অসম্পূর্ণ; justification নেই | docs/ |

## বাধ্যতামূলক artifact

- [ ] Architecture diagram (context + container level)
- [ ] ADR (কমপক্ষে ৫টি গুরুত্বপূর্ণ সিদ্ধান্ত, Kubernetes ব্যবহার বা না-ব্যবহারের যুক্তি সহ)
- [ ] Threat model
- [ ] Deployment ও rollback procedure
- [ ] DR plan ও restore drill-এর মাপা RTO/RPO
- [ ] Cost estimate ও cleanup checklist
- [ ] Runbook (কমপক্ষে ৩টি)
- [ ] Postmortem (কমপক্ষে ১টি simulated incident)
- [ ] Portfolio README
