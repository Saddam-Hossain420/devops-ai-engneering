# Hardware ও cost guide

## Local hardware — module অনুযায়ী

| Module | CPU | RAM | Disk | বিশেষ |
|---|---|---|---|---|
| 00–05 | 2 core | 4 GB | 20 GB | যেকোনো Ubuntu VM |
| 06–08 | 2 core | 4 GB | 20 GB | 08: AWS account (💰) |
| 09–11 | 4 core | 8 GB | 40 GB | Docker image-এ disk দ্রুত ভরে — `docker system df` |
| 12–13 | 2–4 core | 8 GB | 30 GB | Ansible-এর জন্য ১–২টি অতিরিক্ত ছোট VM |
| 14–16 | 4 core | 8 GB (🧠 16 GB আরামদায়ক) | 40 GB | kind cluster + Argo CD |
| 17–18 | 4 core | 8–16 GB | 40 GB | Prometheus + Grafana + Loki + tracing একসাথে ভারী |
| 19–22 | 4 core | 8 GB | 40 GB | Kafka/Airflow lab-এ 🧠 16 GB |
| 23–24 | 4 core | 8 GB | 30 GB | GPU দরকার নেই |
| 25–26 | 4–8 core | 16 GB | 50 GB+ | ছোট quantized model CPU-তে; 🎮 GPU ঐচ্ছিক |
| 27 | 4 core | 8–16 GB | 30 GB | local LLM হলে বেশি RAM |

## LLM memory — মোটামুটি হিসাব (শুধু weight)

`memory ≈ parameter সংখ্যা × প্রতি parameter byte`

| Model size | 16-bit (2 byte) | 8-bit (1 byte) | 4-bit (0.5 byte) |
|---|---|---|---|
| 1B | ~2 GB | ~1 GB | ~0.5 GB |
| 3B | ~6 GB | ~3 GB | ~1.5 GB |
| 7–8B | ~14–16 GB | ~7–8 GB | ~3.5–4 GB |

এর উপর runtime overhead ও KV cache (context দৈর্ঘ্য ও concurrency অনুযায়ী বাড়ে) যোগ হয়। কোনো model "fit করবে" দাবি করার আগে L25-03-এর পদ্ধতিতে হিসাব ও তারপর বাস্তবে মাপুন।

## Cloud cost নিয়ন্ত্রণ

**যেকোনো AWS lab-এর আগে বাধ্যতামূলক:**

1. Root user-এ MFA; দৈনন্দিন কাজে root নয়।
2. **Budget alert** (যেমন মাসিক $5–10 সীমা, 50%/80%/100%-এ email)।
3. সব resource-এ tag: `Project`, `Environment`, `Owner`, `TTL`।
4. Lab শেষে cleanup checklist এবং inventory যাচাই।

**সাধারণ "লুকানো" খরচ (lab-এ সতর্ক থাকুন):**

| Resource | কেন বিপজ্জনক |
|---|---|
| NAT Gateway | ঘণ্টাভিত্তিক বিল + data processing; ব্যবহার না হলেও চলতে থাকে |
| Load balancer | ঘণ্টাভিত্তিক বিল |
| Public IPv4 address | ব্যবহারে থাকা public IPv4-এর জন্যও এখন ঘণ্টাভিত্তিক চার্জ হয় |
| EBS volume ও snapshot | instance মুছলেও volume/snapshot থেকে যেতে পারে |
| EKS control plane | cluster চালু থাকলেই ঘণ্টাভিত্তিক বিল |
| GPU instance | প্রতি ঘণ্টায় উচ্চ খরচ; ভুলে চালু রাখা সবচেয়ে বড় ঝুঁকি |
| Data transfer out | internet-এ data পাঠানো |
| CloudWatch Logs | বেশি log ingest ও দীর্ঘ retention |

সঠিক মূল্য region ও সময় অনুযায়ী বদলায় — সবসময় [AWS Pricing Calculator](https://calculator.aws/) দিয়ে নিজে হিসাব করুন। এই repository-তে নির্দিষ্ট ডলার মূল্য লেখা হলে তারিখ সহ "আনুমানিক" চিহ্নিত থাকবে।

## খরচ ছাড়া বিকল্প

| Cloud জিনিস | Local বিকল্প |
|---|---|
| EC2 | Multipass / VirtualBox VM |
| S3 | MinIO (container) |
| EKS | kind / k3d |
| Terraform AWS lab | Terraform `docker`/`local` provider |
| Managed DB | PostgreSQL container |
| Cloud GPU | ছোট quantized model CPU-তে, বা mock inference service |
