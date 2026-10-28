# P05 — Configuration Management

**Status:** NOT_STARTED · **Milestone:** 5 · **Track:** A, B · **পূর্বশর্ত:** Module 06, Module 13

## লক্ষ্য

Ansible দিয়ে একটি clean Ubuntu server প্রস্তুত করা: package, user, firewall, Nginx, application deploy ও health verify।

## Architecture

```text
control node ──SSH──► target(s)
   roles/common   : update, user, SSH hardening, ufw
   roles/nginx    : install, template, handler
   roles/app      : venv, systemd unit, config
   roles/verify   : uri module দিয়ে /health
```

## Features (scope)

- Inventory: local container/VM target
- Vault দিয়ে secret
- Handler দিয়ে শুধু দরকার হলে reload
- Check mode ও diff
- Fedora target-এর জন্য `ansible_os_family` অনুযায়ী আলাদা task

## Acceptance criteria

Project সম্পন্ন ধরা হবে যখন নিচের সবগুলো **বাস্তবে চালিয়ে** যাচাই হবে:

- [ ] প্রথম run সফল, দ্বিতীয় run `changed=0`
- [ ] `--check --diff` কোনো অপ্রত্যাশিত পরিবর্তন দেখায় না
- [ ] Molecule test পাস
- [ ] Health check সফল

## Resource requirements

Control node: Ubuntu। Target: ১–২টি VM বা systemd-সক্ষম container।

## Cleanup

VM snapshot-এ ফিরে যাওয়া বা VM মুছে ফেলা।

## Implementation plan

Code এই folder-এ তৈরি হবে যখন সংশ্লিষ্ট module-এর lesson-গুলো সম্পন্ন হবে। ধাপ:

1. Design: architecture ও ADR (`docs/`)
2. Minimal working version + test
3. Security ও reliability যোগ
4. Failure scenario ও runbook
5. Portfolio README: সমস্যা, architecture, decision, কী শিখলাম, demo
