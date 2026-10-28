# Module 06 — Web Server and Reverse Proxy

**Stage:** 4 · **Lesson:** 9 · **Progress:** [PROGRESS.md](PROGRESS.md)

## Scope

DNS record, Nginx architecture, server block, reverse proxy, application process ও socket, caching, TLS, server hardening এবং PHP-FPM/WordPress — continuous project-কে Nginx-এর পেছনে systemd service হিসেবে চালানো।

## পূর্বশর্ত (Prerequisites)

[02-computer-networking](../02-computer-networking/README.md), [05-python-for-infrastructure](../05-python-for-infrastructure/README.md)

## Learning outcomes

এই module শেষে আপনি পারবেন:

- Nginx-এর master/worker ও request processing ব্যাখ্যা
- Reverse proxy ও upstream configure
- TLS certificate configure ও যাচাই
- 502/504/413 error diagnose
- Linux server harden করা

## Lessons

| ID | Lesson | Level | Label / Needs | Status |
|---|---|---|---|---|
| L06-01 | [DNS record ও domain configuration](L06-01-dns-records-domains.md) | Beginner |  | COMPLETED |
| L06-02 | [Nginx architecture: master, worker, event loop](L06-02-nginx-architecture.md) | Intermediate |  | COMPLETED |
| L06-03 | [Nginx server block (virtual host)](L06-03-nginx-server-blocks.md) | Beginner |  | COMPLETED |
| L06-04 | [Reverse proxy ও upstream](L06-04-reverse-proxy-upstream.md) | Intermediate | Needs L05-13 | COMPLETED |
| L06-05 | [Application process, port, unix socket ও systemd service](L06-05-app-process-socket-systemd.md) | Intermediate |  | COMPLETED |
| L06-06 | [Nginx caching ও compression](L06-06-caching-compression.md) | Intermediate |  | COMPLETED |
| L06-07 | [Nginx-এ TLS ও certificate](L06-07-nginx-tls-certificates.md) | Intermediate |  | COMPLETED |
| L06-08 | [Linux server hardening](L06-08-linux-server-hardening.md) | Intermediate | 🖥️ | COMPLETED |
| L06-09 | [PHP-FPM ও WordPress deployment](L06-09-php-fpm-wordpress.md) | Intermediate |  | COMPLETED |

Lesson file তৈরি হলে এখানে link যোগ হবে। File pattern: `06-web-server-and-reverse-proxy/LNN-MM-slug.md`

## Labs

Lab folder: [labs/06-web-server-and-reverse-proxy/](../labs/06-web-server-and-reverse-proxy/README.md) · Module quiz: [assessments/06-web-server-and-reverse-proxy/quiz.md](../assessments/06-web-server-and-reverse-proxy/quiz.md)

- Level A — দুটি static site + catch-all server block; আগে অনুমান, পরে আসল nginx
- Level B — TaskFlow: nginx → unix socket (systemd socket activation) → HTTPS (lab PKI)
- Level C — মেয়াদোত্তীর্ণ certificate, ভুল socket নাম, socket permission — একটির পর একটি

## সংশ্লিষ্ট project

[P02-production-web-app](../projects/P02-production-web-app/README.md)

## Completion criteria

Module সম্পন্ন ধরা হবে যখন:

- [ ] সব lesson-এর practical demonstration নিজে চালিয়ে যাচাই করা
- [ ] সব lesson-এর hands-on exercise শেষ
- [ ] Level A, B, C lab সম্পন্ন ও verification command পাস
- [ ] Module quiz-এ ≥ 70% ([assessments/](../assessments/README.md))
- [ ] Continuous project Nginx + TLS-এর পেছনে চলা
- [ ] ভুল proxy config থেকে আসা error diagnose

> শুধু পড়া শেষ করলে module সম্পন্ন নয়। Practical verification ও assessment বাধ্যতামূলক।
