# Lab 00-B — TaskFlow delivery design

| | |
|---|---|
| **Level** | B — Integrated |
| **সময়** | ৯০ মিনিট |
| **Environment** | Ubuntu, Python 3.10+; temporary directory |
| **Label** | — |

## Objective

TaskFlow API-র জন্য একটি ছোট কিন্তু সম্পূর্ণ "delivery design package" তৈরি করা: Container diagram, তিনটি ADR, তিন environment-এর configuration এবং একটি production gate — সব কিছু যন্ত্র দিয়ে যাচাইযোগ্য (docs-as-code)।

## Prerequisites

- Lesson: [L00-03](../../../00-orientation/L00-03-sdlc-agile-release.md), [L00-04](../../../00-orientation/L00-04-environments.md), [L00-05](../../../00-orientation/L00-05-diagrams-and-docs.md)
- Tool: `python3`, Markdown viewer বা https://mermaid.live

## Environment setup

```bash
cd ~/devops-ai-engineering
LAB=$(mktemp -d)                         # temporary কাজের directory
echo "$LAB"
cp -r 00-orientation/code/L00-04/config "$LAB/config"
cp 00-orientation/code/L00-04/envconfig.py "$LAB/"
mkdir -p "$LAB/docs/adr"
```

`cp -r` folder সহ ভেতরের সব কিছু copy করে। মূল lesson file অপরিবর্তিত থাকে।

## Steps

### ১. Container diagram

`$LAB/docs/architecture.md` লিখুন — একটি Mermaid Container diagram, যেখানে:

- Nginx, TaskFlow API, PostgreSQL, Redis, **background worker**, **queue**, email provider
- Trust boundary (internet / public edge / private)
- প্রতিটি arrow-এ protocol ও sync/async

### ২. তিনটি ADR

```bash
ADR=00-orientation/code/L00-05/adr.py
python3 $ADR --dir "$LAB/docs/adr" new "Send emails asynchronously through a queue"
python3 $ADR --dir "$LAB/docs/adr" new "Use three environments dev staging prod"
python3 $ADR --dir "$LAB/docs/adr" new "Release with semantic versioning and git tags"
```

প্রতিটির Context, অন্তত দুটি Option, Decision ও Consequences পূরণ করুন। প্রথম ADR-এর Status `Accepted` করুন।

### ৩. Environment configuration

`$LAB/config/base.json`-এ যোগ করুন:

```json
"queue": { "url_host": "localhost", "max_retries": 5 }
```

`staging.json` ও `prod.json`-এ `queue.url_host` আলাদা মান দিন।

### ৪. Production gate

`$LAB/envconfig.py`-এর `validate()`-এ দুটি নিয়ম যোগ করুন:

- prod-এ `database.pool_size >= 10`
- prod-এ `queue.url_host` localhost নয়

### ৫. সব যাচাই একসাথে

```bash
cd "$LAB"
read -rs -p "practice DB password: " APP_DATABASE__PASSWORD; echo; export APP_DATABASE__PASSWORD
python3 envconfig.py validate prod;    echo "validate=$?"
python3 envconfig.py diff staging prod
python3 ~/devops-ai-engineering/00-orientation/code/L00-05/adr.py --dir docs/adr lint; echo "lint=$?"
```

### ৬. Gate ভাঙে কিনা পরীক্ষা

```bash
APP_DATABASE__POOL_SIZE=2 python3 envconfig.py validate prod; echo "validate=$?"
```

## Expected behavior

- Step ৫: `prod: OK`, `validate=0`; diff-এ `queue.url_host` দেখা যায়; `lint=0`।
- Step ৬: আপনার নতুন pool_size নিয়মে FAIL, `validate=1`।
- Mermaid diagram mermaid.live-এ error ছাড়া render হয়।

## Verification

```bash
ls "$LAB/docs/adr"                                   # তিনটি NNNN-*.md
grep -c "Status:" "$LAB"/docs/adr/*.md               # প্রতিটিতে ১
python3 envconfig.py show prod | grep -A3 '"queue"'  # নতুন section, password masked
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `json.decoder.JSONDecodeError` / `error: Expecting ','` | JSON-এ কমা বাদ বা বাড়তি | `python3 -m json.tool config/base.json` |
| নতুন নিয়ম কাজ করে না | `validate()`-এ `env == "prod"` শর্তের বাইরে লিখেছেন | শর্তের ভেতরে রাখুন |
| `lint` FAIL: `missing section` | ADR-এর heading মুছে ফেলেছেন | `## Context`, `## Decision`, `## Consequences` রাখুন |
| Mermaid render হয় না | label-এ বিশেষ অক্ষর quote ছাড়া | label `"..."`-এর ভেতরে |

## Cleanup / reset

কাজ notebook-এ রাখতে চাইলে আগে copy করুন:

```bash
cp -r "$LAB/docs" ~/devops-notebook/labs/00-B-docs
echo "$LAB"                      # নিশ্চিত হোন path /tmp/...
rm -r "$LAB"
unset LAB ADR APP_DATABASE__PASSWORD
```

## Assessment

1. Email-কে async করার ADR-এ কোন নেতিবাচক ফলাফল লিখেছেন? (সংকেত: message হারানো, delay, duplicate)
2. `diff staging prod`-এর প্রতিটি পার্থক্য কি ইচ্ছাকৃত? কোনটি parity নষ্ট করছে কিনা যুক্তি দিন।
3. আপনার production gate কোন বাস্তব incident প্রতিরোধ করত? (L00-04 Section 5 ও Lab C দেখুন)
4. এই package-এর কোন অংশ এখনো হাতে যাচাই করতে হয়, যা CI-তে automate করা যেত?
