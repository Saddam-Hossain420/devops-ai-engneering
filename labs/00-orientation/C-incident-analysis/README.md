# Lab 00-C — Incident analysis: আসল কারণ বনাম decoy

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৯০ মিনিট |
| **Environment** | Ubuntu, Python 3.10+; temporary directory |
| **Label** | — (read-only analysis + temporary file) |

## Objective

একটি production incident-এর log থেকে প্রমাণভিত্তিক timeline তৈরি করা, **দুটি সন্দেহভাজন ঘটনার মধ্যে আসল কারণ আলাদা করা** (correlation বনাম causation), incident report ও postmortem লেখা, এবং একটি automated gate দিয়ে একই failure পুনরায় ঘটা আটকানো — সেই gate নিজে ভেঙে পরীক্ষা করা।

## Prerequisites

- Lesson: [L00-04](../../../00-orientation/L00-04-environments.md), [L00-06](../../../00-orientation/L00-06-learning-by-experiment.md)
- Template: [incident report](../../../templates/incident-report-template.md), [postmortem](../../../templates/postmortem-template.md)

## পরিস্থিতি

৩ নভেম্বর সকালে TaskFlow API-তে user-রা error পেয়েছেন। On-call engineer-এর হাতে আছে শুধু application log: [`incident.log`](incident.log) (২০৪ লাইন, ০৯:০০–০৯:১৫ UTC)। সকালে দুটি উল্লেখযোগ্য ঘটনা ঘটেছিল — marketing email-এর কারণে traffic spike, এবং একটি configuration পরিবর্তন। Team-এর অর্ধেক মনে করে traffic দায়ী, বাকি অর্ধেক config। আপনাকে **data দিয়ে** সিদ্ধান্ত দিতে হবে।

## Environment setup

```bash
cd ~/devops-ai-engineering/labs/00-orientation/C-incident-analysis
TOOL=../../../00-orientation/code/L00-06/incident_timeline.py
```

## Steps

### ১. Hypothesis ও prediction আগে লিখুন

Log দেখার আগে notebook-এ দুটি hypothesis লিখুন, প্রতিটির **prediction** সহ:

- H1: "Traffic spike error-এর কারণ।" → সত্য হলে error কখন শুরু হওয়া উচিত? Spike শেষ হলে কী হওয়া উচিত?
- H2: "Config পরিবর্তন error-এর কারণ।" → সত্য হলে কী দেখব?

### ২. Timeline

```bash
python3 "$TOOL" incident.log
grep -n "traffic spike\|config reloaded" incident.log
```

দুটিই শুধু পড়ে।

### ৩. Hypothesis পরীক্ষা

- Spike-এর মিনিটগুলোতে (request সংখ্যা দেখুন — INFO+WARN+ERROR) error rate কত ছিল?
- Config পরিবর্তনের পরে প্রথম ERROR কত সেকেন্ড পরে?
- Config ফেরত আনার পরে কী হলো?

কোন hypothesis-এর prediction মিলল? Notebook-এ সিদ্ধান্ত লিখুন — এবং **কী প্রমাণ নেই** তাও লিখুন (যেমন: কেন pool_size ২-এ নামানো হয়েছিল, log তা বলে না)।

### ৪. Threshold-এর ফাঁদ

```bash
python3 "$TOOL" incident.log --threshold 20
python3 "$TOOL" incident.log --threshold 5
```

Incident window কীভাবে বদলায়? `last ERROR` সময়ের সাথে window-এর শেষ মিনিট মেলান। আপনার incident report-এ **কোন** শেষ সময় লিখবেন এবং কেন?

### ৫. Incident report ও postmortem

Template অনুযায়ী `~/devops-notebook/incidents/2026-11-03-pool-exhaustion.md`-এ লিখুন:

- Timeline (UTC, প্রতিটি লাইনের সাথে log-এর লাইন নম্বর — প্রমাণ)
- Impact (কত মিনিট, আনুমানিক কত শতাংশ request ব্যর্থ)
- Root cause ও contributing factor
- Decoy কেন কারণ নয় — প্রমাণ সহ
- কমপক্ষে তিনটি action item (prevent / detect / mitigate)

### ৬. প্রতিরোধ: gate তৈরি ও ভেঙে পরীক্ষা (failure injection)

একই ভুল configuration deploy-এর আগে আটকানোর জন্য:

```bash
LAB=$(mktemp -d)
cp -r ../../../00-orientation/code/L00-04/config ../../../00-orientation/code/L00-04/envconfig.py "$LAB/"
cd "$LAB"
read -rs -p "practice DB password: " APP_DATABASE__PASSWORD; echo; export APP_DATABASE__PASSWORD
```

**Failure inject করুন — gate ছাড়া:**

```bash
APP_DATABASE__POOL_SIZE=2 python3 envconfig.py validate prod; echo "exit=$?"
```

প্রত্যাশিত: `prod: OK`, `exit=0` — অর্থাৎ **বর্তমান gate এই ভুল ধরে না।** এটাই incident-এর একটি contributing factor।

এখন `envconfig.py`-এর `validate()`-এ prod-এর জন্য নিয়ম যোগ করুন: `database.pool_size` কমপক্ষে ১০। তারপর আবার:

```bash
APP_DATABASE__POOL_SIZE=2  python3 envconfig.py validate prod; echo "exit=$?"   # FAIL, exit=1
APP_DATABASE__POOL_SIZE=20 python3 envconfig.py validate prod; echo "exit=$?"   # OK,   exit=0
```

## Expected behavior

- Timeline-এ error শুরু ০৯:০৯ (config পরিবর্তন ০৯:০৯:০০-এর পরে), শেষ ০৯:১২-এ; config ফেরত ০৯:১৩:০০।
- Spike-এর মিনিটগুলো (০৯:০৫–০৯:০৭) বেশি request কিন্তু error rate ০%।
- Gate যোগ করার আগে ভুল config পাস করে, পরে FAIL করে।

## Verification

```bash
python3 "$TOOL" ~/devops-ai-engineering/labs/00-orientation/C-incident-analysis/incident.log | grep "incident window"
grep -c "level=ERROR" ~/devops-ai-engineering/labs/00-orientation/C-incident-analysis/incident.log
APP_DATABASE__POOL_SIZE=2 python3 "$LAB/envconfig.py" validate prod; echo "exit=$?"   # 1 হওয়া উচিত
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `error: file not found` | ভুল directory | `pwd`; lab folder থেকে চালান |
| Gate যোগের পরেও `exit=0` | নিয়ম `env == "prod"` শর্তের বাইরে, বা `<`/`<=` ভুল | `validate()` দেখুন; ২ ও ২০ দুটিই পরীক্ষা করুন |
| `database.password must be set` | password export হয়নি | `read -rs` ও `export` আবার করুন |

## Cleanup / reset

```bash
echo "$LAB"            # /tmp/... নিশ্চিত হোন
rm -r "$LAB"
unset LAB TOOL APP_DATABASE__PASSWORD
```

`incident.log` অপরিবর্তিত থাকে (শুধু পড়া হয়েছে)।

## Assessment

1. H1 (traffic) কোন প্রমাণে বাতিল হলো? H2-এর পক্ষে সবচেয়ে শক্তিশালী প্রমাণ কী?
2. Config ফেরত আনার সাথে error শেষ হওয়া কেন correlation-এর চেয়ে শক্তিশালী প্রমাণ?
3. `--threshold 20`-এ window ০৯:১১-এ শেষ, কিন্তু শেষ ERROR ০৯:১২:৩০। Incident-এর সময়কাল কীভাবে নির্ধারণ করবেন?
4. Log থেকে কোন গুরুত্বপূর্ণ প্রশ্নের উত্তর পাওয়া যায় না? আর কোন উৎস দেখবেন?
5. আপনার gate কোন ধরনের action item — prevent, detect নাকি mitigate? আর একটি detect-ধরনের action item প্রস্তাব করুন।
