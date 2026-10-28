# Diagnostic assessment — শুরু করার আগে

উদ্দেশ্য: আপনার বর্তমান level জানা, যাতে কোথায় বেশি সময় দিতে হবে বোঝা যায়। এটি pass/fail পরীক্ষা নয়। সৎভাবে উত্তর দিন; "জানি না" একটি মূল্যবান উত্তর।

প্রতিটি প্রশ্নে নিজেকে 0–2 দিন: **0** = জানি না, **1** = আংশিক, **2** = আত্মবিশ্বাসের সাথে ব্যাখ্যা/করতে পারি।

## Part 1 — Linux (Module 01)

1. Process ও thread-এর পার্থক্য কী?
2. `chmod 640 file` এর পরে কে কী করতে পারবে?
3. `kill -15` ও `kill -9`-এর পার্থক্য কী? কোনটি আগে ব্যবহার করা উচিত, কেন?
4. একটি systemd service চালু হচ্ছে না — প্রথম দুটি command কী চালাবেন?
5. `df -h` বলছে disk-এ জায়গা আছে, কিন্তু নতুন file তৈরি করা যাচ্ছে না। সম্ভাব্য কারণ?
6. Hard link ও symbolic link-এর পার্থক্য কী?

## Part 2 — Networking (Module 02)

7. `192.168.1.0/26`-এ কয়টি usable host address?
8. Browser-এ URL লেখা থেকে page দেখা পর্যন্ত মূল ধাপগুলো কী?
9. "Connection refused" ও "connection timed out"-এর পার্থক্য কী বোঝায়?
10. DNS-এ A, CNAME ও MX record কী?
11. TCP three-way handshake কী?
12. HTTP 502 ও 504 error-এর পার্থক্য কী?

## Part 3 — Git, Bash, Python (Module 03–05)

13. `git merge` ও `git rebase`-এর পার্থক্য কী?
14. ভুল করে commit করা password কীভাবে সামলাবেন (শুধু `git rm` কেন যথেষ্ট নয়)?
15. Bash-এ `"$var"` বনাম `$var` — quote কেন গুরুত্বপূর্ণ?
16. `set -e` কী করে এবং কোথায় এটি কাজ করে না?
17. Python virtual environment কেন দরকার?
18. Python-এ `subprocess.run(cmd, shell=True)` কেন ঝুঁকিপূর্ণ হতে পারে?

## Part 4 — Web, container, cloud (Module 06–10)

19. Reverse proxy কী এবং কেন app-এর সামনে রাখা হয়?
20. Container ও virtual machine-এর মূল পার্থক্য কী?
21. Docker image layer কী? Dockerfile-এ instruction-এর ক্রম কেন গুরুত্বপূর্ণ?
22. Container মুছে ফেললে data কোথায় যায়? কীভাবে রক্ষা করবেন?
23. Cloud-এ "region" ও "availability zone"-এর পার্থক্য কী?
24. IAM-এ least privilege বলতে কী বোঝায়?

## Part 5 — Delivery ও operations (Module 11–18)

25. Continuous delivery ও continuous deployment-এর পার্থক্য কী?
26. Terraform state file কেন গুরুত্বপূর্ণ এবং কেন Git-এ রাখা উচিত নয়?
27. Kubernetes-এ Pod ও Deployment-এর পার্থক্য কী?
28. Readiness ও liveness probe-এর পার্থক্য কী?
29. SLO কী? 99.9% SLO-তে মাসে কত downtime গ্রহণযোগ্য?
30. Metric, log ও trace — প্রতিটি কোন প্রশ্নের উত্তর দেয়?

## Part 6 — Security, data, AI (Module 19–27)

31. Vulnerability scan পাস করা মানেই কি application নিরাপদ? কেন?
32. Database transaction-এ "isolation" কী?
33. Queue-তে একই message দুবার এলে কীভাবে নিরাপদ রাখবেন?
34. ML-এ training ও inference-এর পার্থক্য কী?
35. 7B parameter model 16-bit-এ চালাতে মোটামুটি কত memory লাগবে (শুধু weight)?
36. Prompt injection কী এবং AI agent-এর জন্য কেন বিপজ্জনক?

---

## Score ব্যাখ্যা

| Part | সর্বোচ্চ | আপনার score |
|---|---|---|
| 1 Linux | 12 | |
| 2 Networking | 12 | |
| 3 Git/Bash/Python | 12 | |
| 4 Web/container/cloud | 12 | |
| 5 Delivery/ops | 12 | |
| 6 Security/data/AI | 12 | |

| Part-এ score | সুপারিশ |
|---|---|
| 0–5 | সংশ্লিষ্ট module সম্পূর্ণ ধীরে পড়ুন, সব exercise করুন |
| 6–9 | পড়ুন, তবে practical ও Level C lab-এ বেশি জোর দিন |
| 10–12 | Lesson দ্রুত দেখুন; assessment ও lab দিয়ে যাচাই করুন — skip নয় |

> প্রশ্ন ৩৫-এর হিসাব পদ্ধতি L25-03-এ শেখানো হবে: parameter সংখ্যা × প্রতি parameter-এর byte (16-bit = 2 byte) → 7 × 10⁹ × 2 ≈ 14 GB, এর উপর runtime ও KV cache-এর জন্য অতিরিক্ত।

ফলাফল [PROGRESS.md](../PROGRESS.md)-এর session log-এ তারিখ সহ লিখে রাখুন। Module 18 শেষে আবার দিন এবং তুলনা করুন।
