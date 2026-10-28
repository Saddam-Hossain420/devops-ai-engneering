# Tool বদলালেও শিখতে থাকা

DevOps ও AI infrastructure-এ tool দ্রুত বদলায়। Kubernetes-এর minor version প্রায় প্রতি চার মাসে আসে, AI serving tool আরো দ্রুত বদলায়। তাই এই repository-র নীতি: **stable concept আগে, version-specific detail পরে।**

## কী বদলায় না (দীর্ঘস্থায়ী জ্ঞান)

- Linux process, memory, filesystem, networking-এর মূল নীতি
- TCP/IP, DNS, HTTP, TLS
- Control loop / reconciliation, desired vs actual state
- Idempotency, immutability, least privilege
- Observability-র প্রশ্ন: কী ঘটছে, কেন, কোথায়
- Trade-off চিন্তা: খরচ বনাম reliability বনাম জটিলতা

এগুলো ভালোভাবে বুঝলে নতুন tool মানে শুধু নতুন interface।

## নতুন tool শেখার পদ্ধতি

1. **কোন সমস্যা সমাধান করে?** আগের tool-এর কোন সীমাবদ্ধতা থেকে এসেছে?
2. **Architecture কী?** কোন component, কোথায় state থাকে, কী ব্যর্থ হতে পারে?
3. **Official quick start** — শুধু official documentation থেকে।
4. **ভেঙে দেখুন** — ইচ্ছাকৃত ভুল configuration দিয়ে error message চিনুন।
5. **আগের tool-এর সাথে তুলনা** — একটি ছোট ADR লিখুন।

## তথ্য যাচাইয়ের নিয়ম

- Official documentation ও release notes আগে; blog/video পরে।
- প্রতিটি command-এর জন্য দেখুন: কোন version-এ পরীক্ষিত?
- "Deprecated" লেখা দেখলে replacement খুঁজুন এবং lesson-এ উল্লেখ করুন।
- AI assistant-এর উত্তর official documentation দিয়ে যাচাই করুন — এটি এই repository-র ক্ষেত্রেও প্রযোজ্য।

## নিয়মিত অভ্যাস

| কত দিন পরপর | কী |
|---|---|
| সাপ্তাহিক | ব্যবহৃত tool-এর release notes দেখা |
| মাসিক | একটি postmortem পড়া (অনেক কোম্পানি public postmortem প্রকাশ করে) |
| ত্রৈমাসিক | Repository-র lesson-এ "Tested on" version যাচাই, পুরোনো হলে `NEEDS_REVISION` |
| বার্ষিক | Diagnostic assessment আবার দেওয়া |

## Repository আপডেট

পুরোনো তথ্য পেলে: lesson-এ সংশোধন → `CHANGELOG.md`-এ `Changed`/`Fixed` → module PROGRESS-এ প্রয়োজনে `NEEDS_REVISION`।
