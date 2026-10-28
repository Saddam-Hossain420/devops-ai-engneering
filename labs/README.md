# Labs — হাতে-কলমে practice

প্রতিটি major module-এর তিন স্তরের lab থাকবে:

| Level | নাম | উদ্দেশ্য |
|---|---|---|
| **A** | Fundamentals | একটি ধারণা শেখানোর ছোট experiment |
| **B** | Integrated | একাধিক ধারণা মিলিয়ে একটি কার্যকর system |
| **C** | Failure and Recovery | নিরাপদভাবে ইচ্ছাকৃত failure তৈরি করে diagnose ও recover |

## Folder layout

```text
labs/
└── <module-folder>/
    ├── A-<slug>/README.md
    ├── B-<slug>/README.md
    └── C-<slug>/README.md
```

প্রতিটি module-এর `README.md`-এ তার তিনটি lab-এর নাম আগে থেকে লেখা আছে। Lab file তৈরি হয় যখন সেই module-এর সংশ্লিষ্ট lesson সম্পন্ন হয়, যাতে lab সবসময় আগের শেখা জিনিসের উপর দাঁড়ায়।

## প্রতিটি lab-এ যা থাকবে

[templates/lab-template.md](../templates/lab-template.md) অনুযায়ী:

- Objective · Prerequisites · Environment setup
- Exact steps · Expected behavior · Verification command
- Troubleshooting · Cleanup/reset · ছোট assessment

## Level C failure lab-এর উদাহরণ

- Local service ভেঙে recover করা
- Isolated environment-এ DNS resolution সমস্যা
- Container-এর health check ব্যর্থ করানো
- Reverse proxy ভুল configure করে HTTP error পর্যবেক্ষণ
- CI pipeline ভেঙে failing stage খুঁজে বের করা
- Application memory limit simulate করা
- Kubernetes scheduling failure তদন্ত
- Infrastructure configuration drift detect করা
- Controlled environment-এ expired certificate
- হালকা workload দিয়ে model-serving timeout বা memory exhaustion

## Safety নিয়ম

1. ⚠️ Destructive lab শুধু disposable VM, container বা isolated network-এ।
2. Host OS, আসল production system বা cloud resource-এ কখনো স্পষ্ট নিশ্চিতকরণ ছাড়া নয়।
3. VM-এ lab শুরুর আগে **snapshot** নিন। ভুল হলে snapshot-এ ফিরে যান।
4. প্রতিটি lab-এর শেষে cleanup ধাপ চালান এবং যাচাই করুন যে কিছু রয়ে যায়নি।

## Lab environment সুপারিশ (Ubuntu)

| প্রয়োজন | সুপারিশ |
|---|---|
| সাধারণ Linux lab | Ubuntu VM (snapshot সহ) বা Multipass (`multipass launch 24.04`) |
| Container lab | Docker Engine |
| Kubernetes lab | kind (Docker-এর ভেতরে cluster) |
| Multi-machine lab | ২–৩টি ছোট VM বা Multipass instance |

> **Fedora-তে:** Multipass-এর বদলে `virt-manager`/libvirt বা GNOME Boxes সহজ; Docker-এর বদলে Podman preinstalled থাকে — Docker lab-এর জন্য Docker Engine install করুন অথবা Podman-এর পার্থক্য lesson L10-07 দেখুন।
