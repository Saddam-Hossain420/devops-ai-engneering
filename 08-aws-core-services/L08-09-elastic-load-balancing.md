# L08-09 — Elastic Load Balancing

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L08-06 — EC2](L08-06-ec2.md), [L08-05 — Security group](L08-05-security-groups-nacl.md), [L06-04 — Reverse proxy](../06-web-server-and-reverse-proxy/L06-04-reverse-proxy-upstream.md), [L02-12 — Load balancing](../02-computer-networking/L02-12-load-balancing.md) |
| **Label** | 💰 Application Load Balancer তৈরি থেকে মোছা পর্যন্ত ঘণ্টা অনুযায়ী চার্জযোগ্য, সাথে ব্যবহার-ভিত্তিক unit (LCU) ও তার public IPv4 — ELB pricing page দেখুন; lab শেষে মুছুন |
| **Tested** | `tg_health.py` ও `hc_sim.py`: ৪টি test পাস (Python 3.14.5, Windows)। `hc_sim.py` **আসল local HTTP server ও দুটি আসল TaskFlow process**-এর বিরুদ্ধে চালানো হয়েছে; detection/readmit সময় মাপা (Section 9.2)। `tg_health.py`-এর input হাতে তৈরি; reason code-এর অর্থ AWS ELB documentation অনুযায়ী। **আসল ALB বানানো বা চালানো হয়নি** — `hc_sim` ALB-এর নিয়মের অনুকরণ, ALB নয়। |

---

## 1. এই lesson-এ যা শিখবেন

- ELB-এর ধরন: Application (L7, HTTP), Network (L4, TCP/UDP, স্থির IP), Gateway।
- ALB-এর অংশ: load balancer (অন্তত দুটি AZ-এর subnet), listener, rule, target group, health check।
- **Health check-এর গণিত:** কত সেকেন্ডে মৃত target বাদ পড়ে, কত সেকেন্ডে ফেরে — নিজে মেপে দেখা।
- Deregistration delay ও app-এর graceful shutdown (L05-13) — zero-downtime deploy।
- Reason code (`Target.Timeout`, `Target.ResponseCodeMismatch` …) থেকে diagnosis।
- HTTPS: ACM certificate (domain লাগে — L08-10)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

একটি EC2-এ TaskFlow (L08-06) মানে একটি single point of failure (L07-03)। দুটি AZ-এ দুটি instance রাখলে সামনে কিছু একটা লাগে, যা:

- একটি স্থির ঠিকানা দেয় (DNS নাম);
- শুধু সুস্থ instance-এ traffic পাঠায়;
- deploy-এর সময় চলমান request শেষ হতে দেয়;
- TLS শেষ করে।

L06-এ nginx এই কাজ করেছিল, কিন্তু nginx নিজেও একটি server — তারও redundancy লাগে। ALB AWS-পরিচালিত ও বহু-AZ।

পরিচিত সমস্যা:

- Health check `/`-এ, যা login page-এ redirect করে (302); সব target unhealthy, site বন্ধ।
- Unhealthy threshold ও interval বড়, তাই মৃত instance দেড় মিনিট traffic পায়।
- Deregistration delay app-এর shutdown-এর চেয়ে কম; প্রতিটি deploy-এ কিছু request কেটে যায়।

## 3. সহজ ভাষায় পরিচয়

| অংশ | কাজ | nginx-এর তুলনা (L06) |
|---|---|---|
| Load balancer | DNS নাম, প্রতি AZ-এ node | `server { listen … }` |
| Listener | Port + protocol (HTTP:80, HTTPS:443) | `listen 443 ssl` |
| Rule | Path/host অনুযায়ী কোন target group | `location /api/` |
| Target group | Backend-এর তালিকা + health check | `upstream taskflow { … }` |
| Health check | নিয়মিত `GET /health`, threshold | (nginx OSS-এ passive `max_fails`) |
| Deregistration delay | সরানোর আগে চলমান request শেষ হতে দেওয়া | Graceful reload |

**ALB বনাম NLB:**

- ALB HTTP বোঝে — path, header, redirect, WAF।
- NLB শুধু TCP/UDP দেখে — খুব কম latency, প্রতি AZ-এ স্থির IP, client-এর IP যেমন আছে তেমন থাকে।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের reception ও ডাক্তারদের ডিউটি

- **ALB** = reception — রোগী (request) এসে কোন ডাক্তারের কাছে যাবে, ঠিক করে।
- **Health check** = প্রতি আধঘণ্টায় nurse গিয়ে দেখে ডাক্তার চেম্বারে আছেন কিনা।
- **Unhealthy threshold** = পরপর দুবার না পেলে নতুন রোগী পাঠানো বন্ধ।
- **Deregistration delay** = ডাক্তার ছুটিতে যাওয়ার আগে চলমান রোগী দেখে শেষ করার সময়।

### Analogy কোথায় মেলে না

- **Nurse দেখে বোঝেন ডাক্তার অসুস্থ কিনা।** ALB শুধু দেখে health URL নির্দিষ্ট code দিচ্ছে কিনা। `/health` 200 দিল, কিন্তু database-এ পৌঁছাতে পারছে না — ALB সুস্থ ভাববে। কী পরীক্ষা করবেন, সেটা নকশার সিদ্ধান্ত (L05-13-এর `/health` বনাম `/ready`)।
- **একজন অনুপস্থিত হলে reception সাথে সাথে জানে।** Health check একটি নির্দিষ্ট ছন্দে চলে। Interval ৩০ s × threshold ৩ = প্রায় ৯০ s মৃত instance-এ traffic যায় (Section 9.1-এর হিসাব), আর ফেরার সময় healthy threshold × interval অপেক্ষা।
- **সব ডাক্তার অনুপস্থিত হলে reception বন্ধ।** সব target unhealthy হলে ALB "fail open" করে — সবগুলোতেই traffic পাঠায়, কারণ শুধু health check ভুল হতে পারে। তাই সব-unhealthy অবস্থায় 502/503-এর ধরন আলাদা।

## 5. Real-world engineering scenario — "Deploy-এ সবসময় কয়েকটি 502"

TaskFlow-এর প্রতিটি deploy-এ কয়েক সেকেন্ড 502। Target group-এর setting `tg_health.py`-তে (হাতে তৈরি নমুনা, আসল output):

```text
lab08-app (HTTP:8000, check HTTP / expect 200)
  INFO   detect a dead target in ≈90s, readmit a recovered one in ≈150s
  WARN   90s to detect a dead target — users get errors that long; lower interval or threshold
  WARN   health check on '/' — use a cheap dedicated endpoint (/health) that does not need a login
  WARN   deregistration delay 5s < app shutdown 10.0s — requests are cut off during deploys
  OK     i-app-a:8000 healthy
  ERROR  i-app-b:8000 unhealthy — Target.Timeout: no answer within HealthCheckTimeout — packets dropped by a security group/NACL (sg_reach.py), or the app is too slow
  ERROR  i-app-c:8000 unhealthy — Target.ResponseCodeMismatch: app answered, but not with the matcher code — wrong path, redirect (301/302), or auth; curl the health path from inside the VPC
```

**তিনটি সমস্যা, তিনটি সমাধান:**

1. Deregistration delay ৫ s, অথচ app-এর চলমান request শেষ করতে ১০ s লাগে → delay বাড়ান (বা app-এর shutdown ছোট করুন)।
2. Health check `/`-এ → `/health`।
3. Detection ৯০ s → interval ১০ s × threshold ২।

`i-app-b`-এর Timeout-এর জন্য L08-05-এর `sg_reach.py`, আর `i-app-c`-এর 404-এর জন্য path।

## 6. Diagram

```text
 client ──HTTP:80──► ALB lab08-alb (sg-alb; public-a, public-b)
                      listener :80 → default action: forward → target group lab08-app (HTTP:8000)
                         │ health: GET /health every 10s, timeout 5s, healthy 2, unhealthy 2, matcher 200
             ┌───────────┴───────────┐
       i-app-a (AZ a, app-a)    i-app-b (AZ b, app-b)       sg-app: 8000 ← sg-alb
       TaskFlow 0.0.0.0:8000    TaskFlow 0.0.0.0:8000
 deploy: deregister i-app-a → draining (≤ delay) → terminate → নতুন instance register → initial → healthy
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Listener | যে port/protocol-এ ALB শোনে |
| Target group | Backend-এর দল ও তাদের health check |
| Health check matcher | সুস্থ ধরার HTTP code (যেমন `200` বা `200-299`) |
| Healthy/Unhealthy threshold | পরপর কতবার সফল/ব্যর্থ হলে state বদলায় |
| Deregistration delay (draining) | সরানোর আগে চলমান connection-এর সময় |
| Cross-zone load balancing | সব AZ-এর target-এ সমানভাবে ভাগ (ALB-এ ডিফল্টে চালু) |
| Fail open | সব target unhealthy হলে সবগুলোতেই পাঠানো |
| `X-Forwarded-For` / `-Proto` | আসল client IP ও protocol (L06-04) |
| ACM | AWS Certificate Manager — ELB-এর জন্য public certificate |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Health check-এর ছন্দ

প্রতিটি ALB node আলাদাভাবে প্রতিটি target-কে check করে। তাই app-এর log-এ health check-এর হার interval-এর চেয়ে বেশি দেখায় — এটা স্বাভাবিক।

| ঘটনা | আনুমানিক সময় |
|---|---|
| মৃত target বাদ | interval × UnhealthyThresholdCount |
| সুস্থ target ফেরত | interval × HealthyThresholdCount |
| নতুন target প্রথম traffic | HealthyThresholdCount সফল check-এর পরে |

`hc_sim.py` এই নিয়মটি local-এ চালায়, আর Section 9.2-এ আসল process দিয়ে মাপা হয়েছে।

### 8.2 Zero-downtime deploy

1. পুরোনো target-কে deregister করুন → state `draining`; নতুন request আর আসে না।
2. চলমান request শেষ হতে দিন — deregistration delay পর্যন্ত।
3. তারপর instance বন্ধ।

App-কে SIGTERM পেলে নতুন connection নেওয়া বন্ধ করে চলমানগুলো শেষ করতে হয় (L05-13-এর graceful shutdown)। Delay ≥ app-এর shutdown-এর সময়।

### 8.3 Security group

- ALB-এর SG: internet থেকে 80/443।
- App-এর SG: শুধু ALB-এর SG থেকে 8000 (L08-05)।

ALB health check-ও ALB node-এর private IP থেকে আসে, তাই SG reference দিয়ে health check-ও চলে।

### 8.4 HTTPS

ACM থেকে public certificate পেতে domain-এর মালিকানা প্রমাণ লাগে (DNS validation — L08-10)। Lab-এ domain না থাকলে HTTP:80-এ সীমিত থাকুন, এবং কোনো সত্যিকারের data পাঠাবেন না।

> **Fedora-তে:** কোনো পার্থক্য নেই — `hc_sim.py` ও TaskFlow দুই distro-তেই চলে।

## 9. Practical demonstration

Files:

- [`code/L08-09/tg_health.py`](code/L08-09/tg_health.py), [`hc_sim.py`](code/L08-09/hc_sim.py)
- [`sample/`](code/L08-09/sample/) — target group, attributes, health (হাতে তৈরি)
- [`test_l08_09.py`](code/L08-09/test_l08_09.py)

### 9.1 Setting-এর হিসাব — আসল output

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-09
python3 tg_health.py sample/tg.json --attributes sample/tg-attrs.json --health sample/health.json --app-shutdown 10
```

Output Section 5-এ।

### 9.2 Health check নিজে মাপা — আসল output (এই laptop, দুটি আসল TaskFlow process)

Interval ১ s, timeout ০.৫ s, healthy after ৩, unhealthy after ২। ৬.৫ s-এ `:18102` বন্ধ, ১২.৫ s-এ আবার চালু:

```text
interval 1s, timeout 0.5s, healthy after 3, unhealthy after 2
    2.0s  http://127.0.0.1:18102/health      → healthy   (HTTP 200)
    3.0s  http://127.0.0.1:18101/health      → healthy   (HTTP 200)
    6.5s  [killed :18102]
    8.0s  http://127.0.0.1:18102/health      → unhealthy (timeout)
   12.5s  [restarted :18102]
   15.0s  http://127.0.0.1:18102/health      → healthy   (HTTP 200)
```

**পর্যবেক্ষণ:**

- বন্ধের ১.৫ s পরে unhealthy — interval × ২-এর মধ্যে।
- আবার চালুর ২.৫ s পরে healthy — প্রায় interval × ৩।
- `:18101` এক সেকেন্ড পরে healthy হয়েছে। প্রথম check-এর সময় process তখনো চালু হচ্ছিল, ফলে streak নতুন করে শুরু হয়।
- মৃত process-এ ফল `timeout`, "refused" নয়। এটা Windows-এর আচরণ: বন্ধ localhost port-এ RST পাওয়ার পরেও Windows কিছুক্ষণ আবার চেষ্টা করে, তাই ০.৫ s timeout আগে ফুরায়। Linux-এ একই ঘটনায় সাধারণত সঙ্গে সঙ্গে `ConnectionRefusedError` আসত। ALB-এর reason code-এর পার্থক্যও (Timeout বনাম FailedHealthChecks) এই কারণেই অর্থবহ।

নিজে চালাতে:

```bash
TASKFLOW_PORT=8001 TASKFLOW_DB=/tmp/a.db python3 ../../../05-python-for-infrastructure/code/L05-13/taskflow_api.py &
TASKFLOW_PORT=8002 TASKFLOW_DB=/tmp/b.db python3 ../../../05-python-for-infrastructure/code/L05-13/taskflow_api.py &
python3 hc_sim.py http://127.0.0.1:8001/health http://127.0.0.1:8002/health --interval 2 --timeout 1 --healthy 3 --unhealthy 2
# অন্য terminal-এ: kill %2 … তারপর আবার চালু
```

### 9.3 আসল ALB (আপনার account-এ — চালানো হয়নি)

```bash
TG=$(aws elbv2 create-target-group --name lab08-app --protocol HTTP --port 8000 --vpc-id "$V" --target-type instance \
  --health-check-path /health --health-check-interval-seconds 10 --healthy-threshold-count 2 \
  --unhealthy-threshold-count 2 --tags Key=Project,Value=lab08 --query 'TargetGroups[0].TargetGroupArn' --output text)
aws elbv2 modify-target-group-attributes --target-group-arn "$TG" --attributes Key=deregistration_delay.timeout_seconds,Value=30
aws elbv2 register-targets --target-group-arn "$TG" --targets Id="$IID"
read LB DNS < <(aws elbv2 create-load-balancer --name lab08-alb --type application --scheme internet-facing \
  --subnets "$PUBLIC_A" "$PUBLIC_B" --security-groups "$ALB_SG" --tags Key=Project,Value=lab08 \
  --query 'LoadBalancers[0].[LoadBalancerArn,DNSName]' --output text)            # 💰 এখান থেকে ঘণ্টার চার্জ
aws elbv2 create-listener --load-balancer-arn "$LB" --protocol HTTP --port 80 \
  --default-actions Type=forward,TargetGroupArn="$TG"
aws elbv2 wait load-balancer-available --load-balancer-arns "$LB"
aws elbv2 wait target-in-service --target-group-arn "$TG" --targets Id="$IID"
curl -s "http://$DNS/health"
```

যাচাই:

```bash
aws elbv2 describe-target-groups --target-group-arns "$TG" > tg.json
aws elbv2 describe-target-group-attributes --target-group-arn "$TG" > tg-attrs.json
aws elbv2 describe-target-health --target-group-arn "$TG" > health.json
python3 tg_health.py tg.json --attributes tg-attrs.json --health health.json --app-shutdown 10
```

**Cleanup ক্রম:**

1. `delete-load-balancer`।
2. `wait load-balancers-deleted`।
3. `delete-target-group`।

### 9.4 লেখার সময়

- `Target.Timeout`-এর ব্যাখ্যায় প্রথমে "app `0.0.0.0`-এ শুনছে না" লিখেছিলাম। কিন্তু শুধু `127.0.0.1`-এ শোনা app-এ connection **refused** হয় — সেটা `FailedHealthChecks`। ব্যাখ্যা সরানো হয়েছে।
- Experiment script প্রথমবার Windows-এর cp1252 stdout-এ `→` ছাপতে ব্যর্থ হয়েছিল। Tool-এর `main()` UTF-8 করে, কিন্তু সরাসরি `run()` ডাকায় হয়নি।
- Test-এর timing প্রথমে ৫০ ms ছিল; পুরো suite-এর load-এ flaky হওয়ার ঝুঁকিতে ৩০০ ms করা হয়েছে (L05-13-এর অভিজ্ঞতা)।

### 9.5 Test

```bash
python3 -m unittest -v
```

৪টি test:

- State machine।
- আসল local server-এর বিরুদ্ধে healthy → 503 → unhealthy; matcher বদলালে healthy।
- Setting-এর হিসাব ও সতর্কতা।
- Reason code-এর ব্যাখ্যা; অজানা code-এ AWS-এর description।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `step()` streak | পরপর সফল/ব্যর্থ গোনে | ALB-এর threshold-এর নিয়ম |
| একটি ব্যর্থতায় state বদলায় না | Flapping কম | Threshold-এর উদ্দেশ্য |
| `probe()` matcher | Status code সেটে আছে কিনা | 503 = "চলছে কিন্তু অসুস্থ" |
| `timeout < interval` বাধ্য | ALB-এর নিয়ম | Check-এর overlap নয় |
| `REASONS` dict | Reason → পরের পদক্ষেপ | Diagnosis দ্রুত |
| `deregistration_delay` বনাম `--app-shutdown` | Deploy-এ কাটা request | Zero-downtime |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় `tg_health.py` | ৩ WARN, ২ ERROR, exit ১ |
| `hc_sim.py` + দুটি TaskFlow | বন্ধের ≤ interval × unhealthy পরে unhealthy |
| আসল ALB | `curl http://DNS/health` → 200; `tg_health.py`-এ কোনো WARN নয় |
| `python3 -m unittest -v` | `Ran 4 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| সব target `Target.Timeout` | App SG-তে ALB SG নেই | `sg_reach.py` |
| `Target.FailedHealthChecks` | App চলছে না বা `127.0.0.1`-এ | `TASKFLOW_HOST=0.0.0.0`; console output |
| `Target.ResponseCodeMismatch` (302/404) | Health path ভুল বা redirect | `/health`, matcher |
| `Target.NotInUse` | Target-এর AZ load balancer-এ চালু নেই | ALB-এর subnet-এ সেই AZ |
| Client-এ 502 | Target connection কেটেছে (app crash, keep-alive timeout ALB-এর চেয়ে ছোট) | App-এর keep-alive > ALB idle timeout |
| Client-এ 503 | Target group-এ কোনো target নেই | Register |
| Client-এ 504 | Target উত্তর দিতে দেরি | App latency; idle timeout |
| `create-load-balancer`: subnet error | এক AZ-এর subnet | দুটি AZ-এর public subnet |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Target-এর SG শুধু ALB SG থেকে।
  - HTTPS (ACM) ও HTTP → HTTPS redirect (domain-সহ)।
  - WAF সংযুক্ত করা যায় (চার্জযোগ্য)।
  - App-এ `X-Forwarded-For` বিশ্বাস শুধু ALB থেকে আসা traffic-এ (L06-04)।
- **Performance:**
  - Detection-এর সময় বনাম মিথ্যা alarm-এর trade-off।
  - Health check হালকা রাখুন — প্রতিটি ALB node আলাদা check করে।
  - Slow start mode নতুন target-এ ধীরে traffic বাড়ায়।
- **Cost:**
  - ALB তৈরি থেকেই ঘণ্টার চার্জ — lab শেষে মুছুন।
  - একাধিক app একটি ALB-এ host/path rule দিয়ে রাখলে সংখ্যা কমে।

## 14. Hands-on exercise

1. Section 9.2-এর experiment নিজের Ubuntu-তে চালান। মৃত process-এ `timeout` না `ConnectionRefusedError` আসে? কেন?
2. `hc_sim.py`-তে "fail open" যোগ করুন: সব target unhealthy হলে একটি সতর্কবার্তা ছাপুন ও লিখুন ALB কী করত।
3. TaskFlow-এর `/ready` (database-সহ) ও `/health` (process-মাত্র) — ALB-এর health check কোনটায় হওয়া উচিত? Database বন্ধ হলে প্রতিটির ফল কী?
4. আসল ALB-এ একটি deploy অনুশীলন করুন: দ্বিতীয় instance register → healthy → প্রথমটি deregister → draining দেখুন (`describe-target-health`)।
5. `tg_health.py`-তে `--json` output যোগ করুন, যাতে CI-তে ব্যবহার করা যায়।

## 15. Mini-project — Rolling deploy script

`rolling_deploy.sh`:

1. নতুন user data দিয়ে নতুন instance (L08-06)।
2. Register → `wait target-in-service`।
3. পুরোনো deregister → delay অপেক্ষা → terminate।
4. প্রতিটি ধাপে `curl` loop চালিয়ে কোনো non-200 এল কিনা গুনুন।

লক্ষ্য: ০টি ব্যর্থ request। Module 11-এর CD-তে ব্যবহার হবে।

## 16. Interview প্রশ্ন

1. ALB ও NLB-এর পার্থক্য কী? কখন কোনটা?
2. Health check-এর setting থেকে মৃত target বাদ পড়ার সময় কীভাবে হিসাব করবেন?
3. Deregistration delay কী, এবং app-এর graceful shutdown-এর সাথে সম্পর্ক কী?
4. 502, 503 ও 504 ALB-এর প্রেক্ষাপটে কী বোঝায়?
5. সব target unhealthy হলে ALB কী করে?
6. Health check `/`-এ রাখার সমস্যা কী?

## 17. Self-assessment প্রশ্ন

1. হাসপাতাল-analogy কোথায় মেলে না?
2. Section 9.2-এ `:18101` কেন এক সেকেন্ড পরে healthy হলো?
3. `Target.Timeout` ও `Target.FailedHealthChecks`-এর পার্থক্য কী বলে?
4. ALB-এর জন্য কয়টি AZ-এর subnet লাগে?
5. App-এর SG-তে ALB-এর SG reference কেন health check-এর জন্যও যথেষ্ট?

## 18. সংক্ষিপ্ত সারাংশ

- ALB = listener → rule → target group (+ health check); অন্তত দুটি AZ।
- Detect ≈ interval × unhealthy threshold; readmit ≈ interval × healthy threshold — নিজে মাপা।
- Deregistration delay ≥ app-এর shutdown; health check হালকা ও নির্দিষ্ট endpoint-এ।
- Reason code থেকে diagnosis: Timeout → SG/NACL; FailedHealthChecks → app/port; ResponseCodeMismatch → path/matcher।

## 19. Completion checklist

- [ ] `hc_sim.py` experiment নিজে চালিয়ে detection সময় মাপা
- [ ] আসল ALB-এ `curl /health` → 200, তারপর মোছা
- [ ] `tg_health.py`-এ নিজের target group-এ কোনো WARN নেই
- [ ] `python3 -m unittest -v`-এ ৪টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Application Load Balancer — What is it: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/introduction.html
- ALB — Target groups: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-target-groups.html
- ALB — Health checks for target groups: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/target-group-health-checks.html
- Elastic Load Balancing pricing: https://aws.amazon.com/elasticloadbalancing/pricing/

---

**পরের lesson:** L08-10 — Route 53
