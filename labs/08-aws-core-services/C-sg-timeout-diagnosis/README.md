# Lab 08-C — Security group ভুলের কারণে timeout diagnose

| | |
|---|---|
| **Level** | C — Failure and Recovery |
| **সময়** | ৬০–৯০ মিনিট |
| **Environment** | যেকোনো OS-এ Python 3 — সম্পূর্ণ offline |
| **Label** | — (কোনো AWS account বা খরচ নেই; incident-এর data হাতে তৈরি) |
| **Tested** | `check_c.py` Windows-এ যাচাই করা: `broken`-এ ৬টি FAIL; শুধু একটি কারণ ঠিক করলে ৫টি FAIL (দ্বিতীয় কারণ সামনে আসে); "সব খুলে দেওয়া" অলস fix-এ ৩টি FAIL; একটি reference fix-এ (repo-তে নেই) ALL PASS। মূল্যায়ন L08-05-এর `sg_reach.py`-এর সরল মডেলে — route table ও VPC Reachability Analyzer-এর সাথে মেলানো হয়নি। |

## Objective

**Incident:** গতকাল (২০২৬-১০-২৭) TaskFlow-এর ALB নতুন করে বানানো হয়েছে, আর একজন সহকর্মী "নিরাপত্তা বাড়াতে" app subnet-এ একটি কাস্টম network ACL দিয়েছেন। আজ সকাল থেকে:

- `curl http://<ALB>/health` কয়েক সেকেন্ড অপেক্ষা করে `504 Gateway Time-out` দেয়;
- `describe-target-health`: দুটি target-ই `unhealthy` — `Target.Timeout`;
- Instance-এর console output-এ app সুস্থ: `taskflow healthy`।

আপনার কাজ:

1. কারণ খুঁজে বের করা — **একাধিক হতে পারে**।
2. **ন্যূনতম** fix।
3. Tool দিয়ে প্রমাণ।
4. লিখিত diagnosis।

## Prerequisites

- [L08-05 — Security group ও NACL](../../../08-aws-core-services/L08-05-security-groups-nacl.md)
- [L08-09 — ALB health check](../../../08-aws-core-services/L08-09-elastic-load-balancing.md)
- [L02-16 — Troubleshooting](../../../02-computer-networking/L02-16-troubleshooting-toolkit.md) (timeout বনাম refused)

## Environment setup

```bash
mkdir -p ~/lab08c
cd ~/devops-ai-engineering/labs/08-aws-core-services/C-sg-timeout-diagnosis
T=../../../08-aws-core-services/code
```

[`broken/`](broken/)-এ incident-এর সময়ের describe output (হাতে তৈরি):

- `security-groups.json`, `network-acls.json`
- `subnets.json`, `route-tables.json`, `instances.json`, `load-balancers.json`
- `tg.json`, `health.json`
- `console-output-i-a.txt`

File: [`check_c.py`](check_c.py)। **আগে tool ছাড়া** file-গুলো পড়ে অনুমান লিখুন — তারপর tool।

## Steps

1. **Symptom থেকে শুরু:**

   ```bash
   python3 $T/L08-09/tg_health.py broken/tg.json --attributes broken/tg-attrs.json --health broken/health.json
   cat broken/console-output-i-a.txt
   ```

   `Target.Timeout` কী বোঝায়, আর app সুস্থ হলে কোথায় খুঁজবেন? `~/lab08c/diagnosis.md`-এ লিখুন।

2. **Routing বাদ দিন:** `python3 $T/L08-04/vpc_audit.py broken/subnets.json broken/route-tables.json broken/nat-gateways.json broken/internet-gateways.json` — ALB ও app একই VPC-তে, `local` route। Route সমস্যা কি?

3. **Flow পরীক্ষা:** ALB-এর একটি subnet থেকে একটি instance-এ:

   ```bash
   python3 $T/L08-05/sg_reach.py check broken/security-groups.json broken/network-acls.json \
     --src-ip 10.20.2.10 --src-sg sg-alb --src-subnet subnet-pub-a \
     --dst-ip 10.20.0.20 --dst-sg sg-app --dst-subnet subnet-app-a --port 8000
   python3 $T/L08-05/sg_reach.py audit broken/security-groups.json
   ```

   কোন ধাপে `XX`? কেন? (`sg-alb`-এর description পড়ুন।)

4. **প্রথম কারণ ঠিক করুন:** `broken/security-groups.json` `~/lab08c/`-এ copy করে শুধু প্রয়োজনীয় পরিবর্তন করুন। আবার ধাপ ৩ চালান (`~/lab08c/security-groups.json` দিয়ে)। এখনো `XX`? এবার কোথায়?

5. **দ্বিতীয় কারণ:** `network-acls.json` `~/lab08c/`-এ copy করে ঠিক করুন। নিয়ম:
   - SSH-এর deny থাকবে;
   - app subnet থেকে উত্তর যাবে শুধু VPC-র ভেতরে, ALB-এর ephemeral port-এ;
   - internet-এর সব port নয়।

6. **Diagnosis** (`~/lab08c/diagnosis.md`):
   - দুটি কারণ — নির্দিষ্ট id ও rule নম্বর সহ;
   - কেন symptom timeout, "connection refused" নয়;
   - কেন একটি ঠিক করার পরেও timeout থাকল;
   - ভবিষ্যতে কীভাবে ঠেকাবেন (L08-05-এর expected-flow test, ALB rebuild-এর runbook)।

7. **যাচাই** (নিচে)।

## Expected behavior

| অবস্থা | `check_c.py` |
|---|---|
| `broken` | ৬টি FAIL — সব ALB → app flow SG-তে আটকায় |
| শুধু SG ঠিক | ৫টি FAIL — এবার আটকায় NACL-এর ফেরত পথে |
| দুটোই ঠিক, diagnosis-সহ | ALL CHECKS PASSED |
| "সব খুলে দেওয়া" (0.0.0.0/0, allow-all outbound) | Traffic চলে, কিন্তু ৩টি FAIL — fix কারণ লুকায় |

## Verification

```bash
python3 check_c.py broken                                              # কী ভাঙা, দেখুন
python3 check_c.py ~/lab08c --diagnosis ~/lab08c/diagnosis.md; echo "exit=$?"   # ALL CHECKS PASSED, 0
```

## Troubleshooting

| Symptom | সম্ভাব্য কারণ |
|---|---|
| `no reference to a security group that does not exist` FAIL | পুরোনো reference মুছে নতুনটি দিন — দুটো পাশাপাশি রাখা নয় |
| `replies limited to the VPC` FAIL | Outbound-এ `0.0.0.0/0` 1024–65535 — VPC CIDR দিন |
| `SSH from internet still denied` FAIL | Rule 90 মুছে ফেলেছেন, বা subnet default NACL-এ সরিয়েছেন |
| `ALB (subnet-pub-b) → …` FAIL, কিন্তু `pub-a` PASS | Fix শুধু একটি ALB subnet-এর CIDR দিয়ে করা |
| `error: … JSONDecodeError` | Copy করা JSON-এ comma — `python3 -m json.tool file` |

## Cleanup / reset

কোনো cloud resource নেই। `~/lab08c/` notebook-এ রাখুন; আবার শুরু করতে মুছে ফেলুন।

## Assessment

1. Load balancer আবার বানানো কেন এই incident ঘটাল? কোন ধরনের reference এড়ালে ঘটত না, আর কোনটা তবুও ভালো?
2. প্রথম কারণ দ্বিতীয়টিকে লুকিয়ে রেখেছিল কেন? বাস্তবে এমন "স্তরে স্তরে" bug কীভাবে খুঁজবেন?
3. ALB সব target unhealthy হলে 504 দেয় কেন (fail open, L08-09)?
4. "Hardened" NACL-এর লেখক কী ভুল ধারণা করেছিলেন? Stateless firewall-এর নিয়ম লেখার checklist দিন।
5. এই incident-এর postmortem-এর জন্য একটি সময়রেখা ও তিনটি action item লিখুন (Module 18-এর blameless ধাঁচে)।
