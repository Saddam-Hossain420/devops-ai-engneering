# Security review checklist

## Secret

- [ ] Code, Git history, log, image layer, CI output-এ কোনো secret নেই
- [ ] `.env` gitignored, `.env.example`-এ শুধু placeholder
- [ ] Secret rotation সম্ভব এবং প্রক্রিয়া লেখা

## Identity ও access

- [ ] Least privilege: IAM policy, Kubernetes RBAC, CI `permissions:`
- [ ] Long-lived key নয় — role, OIDC, temporary credential
- [ ] Service account token দরকার না হলে mount নয়

## Network

- [ ] শুধু প্রয়োজনীয় port খোলা (ufw / security group / NetworkPolicy)
- [ ] Admin interface public internet-এ নয়
- [ ] TLS সব জায়গায় যেখানে untrusted network

> **Fedora-তে:** firewall rule `firewall-cmd` দিয়ে; SELinux enforcing রাখুন, disable করে সমস্যা "সমাধান" নয়।

## Workload

- [ ] Container non-root, `cap_drop: ALL`, read-only filesystem যেখানে সম্ভব
- [ ] Base image pinned ও scan করা; critical vulnerability-র সিদ্ধান্ত নথিভুক্ত
- [ ] Resource limit (DoS প্রতিরোধ)

## Supply chain

- [ ] Dependency pin ও scan
- [ ] SBOM তৈরি
- [ ] Image signed ও deploy-এর সময় verify
- [ ] Third-party GitHub Action version/SHA pin

## Data

- [ ] Backup encrypted ও restore পরীক্ষিত
- [ ] Log-এ personal data বা token নেই

## AI-specific

- [ ] Untrusted input (log, document, user prompt) নির্দেশ হিসেবে ব্যবহার হয় না
- [ ] Agent tool read-only বা human approval সহ
- [ ] Prompt-এ credential নেই
- [ ] Rate limit ও cost limit

## মনে রাখুন

Scanner পাস = শুধু জানা pattern পাওয়া যায়নি। এটি logic bug, ভুল authorization, business-logic দুর্বলতা বা অজানা vulnerability ধরে না।
