# L08-11 — CloudWatch

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L08-09 — ALB](L08-09-elastic-load-balancing.md), [L08-06 — EC2](L08-06-ec2.md), [L05-07 — Logging](../05-python-for-infrastructure/L05-07-logging-structured.md) |
| **Label** | 💰 AWS service-এর মৌলিক metric সাধারণত বিনামূল্যে; **alarm, custom metric, log ingestion ও storage, Logs Insights query, detailed monitoring** চার্জযোগ্য — CloudWatch pricing page দেখুন। Log group-এর ডিফল্ট retention "never expire" — বদলান |
| **Tested** | `alarm_sim.py` ও `alarm_defs.py`: ৫টি test পাস (Python 3.14.5, Windows)। `alarm_sim.py` **একটি সরল মডেল** — M-of-N ও `breaching`/`notBreaching` documentation অনুযায়ী; `missing`/`ignore`-এ AWS আরও পেছনের datapoint দেখতে পারে, যা এখানে নেই। Metric-এর নাম ও dimension AWS ELB/EC2 documentation অনুযায়ী। **কোনো alarm তৈরি বা metric পড়া হয়নি।** |

---

## 1. এই lesson-এ যা শিখবেন

- Metric: namespace, নাম, dimension, period, statistic (Sum, Average, Maximum, p95)।
- কোন metric AWS নিজে দেয়, আর কোনটা দেয় না — EC2-এর memory ও disk দেয় না, তার জন্য CloudWatch agent।
- **Alarm:** threshold, "M out of N", `TreatMissingData` — একই data-য় চার mode-এর ভিন্ন ফল।
- কোন alarm রাখবেন: user-এর অভিজ্ঞতা (5xx, latency) ও প্রতিকারযোগ্য কারণ; শুধু CPU% নয়।
- CloudWatch Logs: log group, retention, Logs Insights দিয়ে TaskFlow-এর JSON log।
- SNS দিয়ে notification।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L08-09-এর ALB-এর পেছনে TaskFlow চলছে। রাত দুটোয় একটি instance-এর disk ভরে গেল, 5xx বাড়ল। জানা গেল সকালে, user-দের অভিযোগ থেকে।

পরিচিত ভুল:

- Alarm শুধু `CPUUtilization > 80%`-এ। Disk ভরা, memory leak বা 5xx-এ CPU চুপ।
- প্রতিটি spike-এ alarm — দলের সবাই notification mute করল (alert fatigue)।
- Traffic না থাকলে metric আসে না, alarm `INSUFFICIENT_DATA`-তে — কেউ জানে না এটা ভালো না খারাপ।
- Log group-এর retention নেই; বছরের পর বছর জমা হচ্ছে, বিলও বাড়ছে।

## 3. সহজ ভাষায় পরিচয়

| ধারণা | উদাহরণ |
|---|---|
| Namespace | `AWS/EC2`, `AWS/ApplicationELB`, `CWAgent` (agent-এর) |
| Metric | `HTTPCode_Target_5XX_Count`, `TargetResponseTime`, `CPUUtilization` |
| Dimension | `LoadBalancer=app/lab08-alb/…`, `InstanceId=i-…` |
| Period ও statistic | ৬০ s-এর Sum, Maximum, p95 |
| Alarm state | `OK`, `ALARM`, `INSUFFICIENT_DATA` |
| M out of N | শেষ N period-এর মধ্যে M-টি threshold পার করলে ALARM |
| TreatMissingData | Data না এলে: `missing`, `ignore`, `breaching`, `notBreaching` |

**AWS দেয় বনাম agent লাগে (EC2):**

| AWS/EC2 থেকে | CloudWatch agent লাগে |
|---|---|
| CPU, network, disk I/O (instance store), status check | Memory ব্যবহার, filesystem-এর ভরাট %, process, application log |

**Local-এর তুলনা (L01-15, L05-07):** `top`, `df`, `journalctl` = এক server-এর দৃশ্য। CloudWatch = সব server ও service-এর সময়-ধারা, এক জায়গায়, alarm-সহ।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের monitor

- **Metric** = হৃদস্পন্দনের রেখা।
- **Alarm threshold** = "১২০-এর ওপরে গেলে বাজবে"।
- **M out of N** = "শেষ ৩ মিনিটের মধ্যে ২ মিনিট ১২০-এর ওপরে থাকলে" — হাঁচিতে নয়।
- **Missing data** = sensor খুলে গেছে।

### Analogy কোথায় মেলে না

- **Sensor খুললে monitor চেঁচায়।** CloudWatch-এ data না এলে কী হবে, তা **আপনি** ঠিক করেন। 5xx-এর metric শুধু error হলে আসে — data না আসা মানে "error নেই", তাই `notBreaching`। কিন্তু instance-এর status check-এর data না আসা মানে instance-ই নেই, তাই `breaching`। ভুল বাছলে নিঃশব্দ ব্যর্থতা।
- **Monitor সব রোগীর জন্য একই।** প্রতিটি alarm-এর নিজের মানে, runbook ও মালিক থাকা উচিত। নইলে কেউ জানে না বাজলে কী করতে হবে।
- **Monitor real-time।** CloudWatch-এ metric period শেষে আসে, তারপর N period মূল্যায়ন — alarm কয়েক মিনিট পরে বাজে। Section 9.1-এ first ALARM ২৪০ s-এ।

## 5. Real-world engineering scenario — "রাতে কিছু বাজেনি"

TaskFlow-এর একমাত্র alarm ছিল `CPUUtilization > 80%`। রাতে database lock-এর কারণে 5xx বাড়ল; CPU ২০%-এ রইল; কেউ জানল না।

**নতুন alarm-এর নকশা** (`alarm_defs.py`-এর আসল output):

```text
lab08-target-5xx.json        HTTPCode_Target_5XX_Count  Sum     3/5 × 60s  GreaterThanOrEqualToThreshold 5  missing=notBreaching
lab08-unhealthy-hosts.json   UnHealthyHostCount         Maximum 2/3 × 60s  GreaterThanOrEqualToThreshold 1  missing=breaching
lab08-status-check.json      StatusCheckFailed          Maximum 2/2 × 60s  GreaterThanOrEqualToThreshold 1  missing=breaching
lab08-p95-latency.json       TargetResponseTime         p95     3/5 × 60s  GreaterThanThreshold 0.5  missing=notBreaching
```

**প্রতিটির যুক্তি:**

- **5xx ও latency:** user যা অনুভব করে। ৫ মিনিটে ৩ বার — হাঁচিতে নয়, স্থায়ী সমস্যায়।
- **Unhealthy host:** ALB এখনো সামলাচ্ছে, কিন্তু capacity কম — কাজের সময়ে দেখার মতো।
- **Status check:** hardware বা OS — instance বদলাতে হবে।
- `TargetResponseTime` সেকেন্ডে, তাই ৫০০ ms = `0.5` (test-এ যাচাই)।

## 6. Diagram

```text
 TaskFlow (EC2) ── JSON log (stderr→journald) ── CloudWatch agent ──► Logs: /lab08/taskflow (retention 14d)
        │                                              └──────────────► CWAgent: mem_used_percent, disk_used_percent
 ALB ───┴─► AWS/ApplicationELB: HTTPCode_Target_5XX_Count, TargetResponseTime, UnHealthyHostCount
 EC2 ─────► AWS/EC2: CPUUtilization, StatusCheckFailed
                 │
            Alarm (M of N, TreatMissingData) ──► SNS topic lab08-alerts ──► email (subscription confirm)
                 └── runbook link in AlarmDescription
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Basic / detailed monitoring | EC2 metric ৫ মিনিট (বিনামূল্যে) / ১ মিনিট (চার্জযোগ্য) |
| Custom metric | নিজের পাঠানো metric — চার্জযোগ্য |
| Percentile (p95) | ৯৫% request এর চেয়ে দ্রুত — গড়ের চেয়ে সৎ |
| `DatapointsToAlarm` | M — N-এর মধ্যে কয়টি breaching হলে ALARM |
| Composite alarm | একাধিক alarm-এর AND/OR |
| Log group / stream | Log-এর পাত্র / একটি উৎসের ধারা |
| Retention | কতদিন log থাকবে |
| Logs Insights | Log-এর ওপর query ভাষা (স্ক্যান করা GB অনুযায়ী চার্জ) |
| SNS | Notification-এর pub/sub service |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Alarm মূল্যায়ন

প্রতিটি period শেষে CloudWatch শেষ N period-এর datapoint দেখে। M-টি threshold পার করলে ALARM। ছোট period ও ছোট N মানে দ্রুত সাড়া, কিন্তু বেশি মিথ্যা alarm — trade-off।

### 8.2 Missing data — একই data-য় চার রকম শেষ

Series `1,2,9,9,2,9,9,9,-,-,-`, threshold ৫, 2 of 3 — `alarm_sim.py`-এর আসল শেষ state:

| `TreatMissingData` | শেষ state | কখন উপযুক্ত |
|---|---|---|
| `missing` | `INSUFFICIENT_DATA` | ডিফল্ট; "জানি না" |
| `ignore` | `ALARM` (আগের state থাকে) | বিরল data-র metric |
| `breaching` | `ALARM` | Data না আসাই সমস্যা (heartbeat, status check) |
| `notBreaching` | `OK` | Data শুধু খারাপ ঘটনায় আসে (5xx count) |

### 8.3 Logs

- TaskFlow প্রতিটি request-এর জন্য JSON log লেখে — `method`, `path`, `status`, `duration_ms` (L05-13)।
- Agent সেগুলো log group-এ পাঠায়। Logs Insights JSON field সরাসরি চেনে:

```text
fields @timestamp, path, status, duration_ms
| filter status >= 500
| stats count() as errors, pct(duration_ms, 95) as p95 by path
| sort errors desc
```

- **Retention:** ডিফল্টে কখনো মোছে না। `aws logs put-retention-policy --log-group-name /lab08/taskflow --retention-in-days 14`।

### 8.4 Notification

- SNS topic-এ email subscription করলে নিশ্চিতকরণের একটি email আসে। Confirm না করলে alarm বাজলেও কিছু আসে না।
- Alarm বানানোর পরে `set-alarm-state` দিয়ে পরীক্ষা করুন — এতে আসল সমস্যা ছাড়াই notification যাচাই হয়।

> **Fedora-তে:** CloudWatch agent-এর package ও install-পদ্ধতি distro-ভেদে আলাদা — AWS-এর agent documentation-এ Fedora/RHEL-এর অংশ দেখুন। Alarm ও Logs Insights একই।

## 9. Practical demonstration

Files:

- [`code/L08-11/alarm_sim.py`](code/L08-11/alarm_sim.py), [`alarm_defs.py`](code/L08-11/alarm_defs.py)
- [`test_l08_11.py`](code/L08-11/test_l08_11.py)

### 9.1 Alarm simulation — আসল output

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-11
python3 alarm_sim.py --series 1,2,9,9,2,9,9,9,-,-,- --threshold 5 --n 3 --m 2 --missing missing
```

```text
2 of 3 periods GreaterThanOrEqualToThreshold 5, TreatMissingData=missing, period 60s
  t=   60s  value=     1  INSUFFICIENT_DATA
  t=  120s  value=     2  OK  ← changed
  t=  180s  value=     9  OK
  t=  240s  value=     9  ALARM  ← changed
  t=  300s  value=     2  ALARM
  t=  360s  value=     9  ALARM
  t=  420s  value=     9  ALARM
  t=  480s  value=     9  ALARM
  t=  540s  value=     -  ALARM
  t=  600s  value=     -  ALARM
  t=  660s  value=     -  INSUFFICIENT_DATA  ← changed
first ALARM after 240s
```

**পর্যবেক্ষণ:**

- প্রথম ৯-এ (১৮০ s) alarm নয় — দ্বিতীয়টিতে (২৪০ s)।
- ৩০০ s-এর `2` alarm থামায় না, কারণ শেষ তিনটির দুটি এখনো breaching।
- প্রথম period-এ একটি মাত্র datapoint সিদ্ধান্তের জন্য যথেষ্ট নয়, তাই `INSUFFICIENT_DATA`।

`--missing` বদলে চারটি mode চালিয়ে Section 8.2-এর table মিলিয়ে নিন।

### 9.2 Alarm তৈরি (আপনার account-এ — চালানো হয়নি)

```bash
TOPIC=$(aws sns create-topic --name lab08-alerts --tags Key=Project,Value=lab08 --query TopicArn --output text)
aws sns subscribe --topic-arn "$TOPIC" --protocol email --notification-endpoint you@example.com   # email-এ confirm
python3 alarm_defs.py --lb-arn "$LB" --tg-arn "$TG" --instance "$IID" --topic-arn "$TOPIC" --out alarms/
for f in alarms/*.json; do aws cloudwatch put-metric-alarm --cli-input-json "file://$f"; done
aws cloudwatch set-alarm-state --alarm-name lab08-target-5xx --state-value ALARM --state-reason "notification test"
aws cloudwatch describe-alarms --alarm-name-prefix lab08- \
  --query 'MetricAlarms[].[AlarmName,StateValue]' --output table
```

5xx নিজে ঘটাতে TaskFlow-এর database file-এর permission কেড়ে নিন (শুধু lab instance-এ) — `/ready` ও লেখা ব্যর্থ হবে। তারপর alarm-এর state বদল দেখুন।

**Cleanup:**

1. `aws cloudwatch delete-alarms --alarm-names $(aws cloudwatch describe-alarms --alarm-name-prefix lab08- --query 'MetricAlarms[].AlarmName' --output text)`।
2. `aws sns delete-topic`।
3. `aws logs delete-log-group --log-group-name /lab08/taskflow`।

### 9.3 লেখার সময়

- **প্রথম সংস্করণের `missing` mode বিভ্রান্তিকর ছিল।** Window `[9, -, -]`-এ একটি মাত্র (breaching) datapoint, তবু state ALARM থেকে OK হয়ে যেত — শুধু data থেমে যাওয়ায়। এখন প্রমাণ যথেষ্ট না হলে আগের state থাকে; নিশ্চিতভাবে ALARM বা OK হলে তবেই বদলায়। Test-এ চার mode-এর শেষ state ও এই ক্ষেত্রটি যাচাই হয়।
- `breaching` শাখার প্রথম রূপ ছিল তিন লাইনের অপ্রয়োজনীয় জটিল কোড — এক লাইনে সরল করা হয়েছে, ফল একই।

### 9.4 Test

```bash
python3 -m unittest -v
```

৫টি test:

- M-of-N; বিচ্ছিন্ন spike-এ alarm নয়।
- চার missing mode।
- Operator ও validation।
- ARN থেকে dimension।
- চারটি alarm-এর গঠন (p95 = ExtendedStatistic, সেকেন্ড, tag, OK action)।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| শেষ N period-এর window | Alarm-এর মূল্যায়ন | CloudWatch-এর নিয়ম |
| `fine > n - m` → OK | নিশ্চিত OK | প্রমাণ ছাড়া state বদল নয় |
| `breaching`/`notBreaching` | Missing → খারাপ/ভালো | Metric-এর অর্থ অনুযায়ী |
| `lb_dimension()` | ARN → `app/NAME/ID` | ভুল dimension = metric পাওয়া যায় না, alarm চিরকাল `INSUFFICIENT_DATA` |
| `ExtendedStatistic` p95 | Percentile | `Statistic` ও `ExtendedStatistic` একসাথে নয় |
| `OKActions` | সমাধানেও notification | "এখন ঠিক আছে" জানা দরকার |
| Description-এ runbook | কী করতে হবে | Alert fatigue কমায় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `alarm_sim.py` (missing) | first ALARM ২৪০ s, শেষে `INSUFFICIENT_DATA` |
| `alarm_defs.py` | ৪টি JSON, p95 threshold `0.5` |
| `set-alarm-state` | Email-এ notification |
| `python3 -m unittest -v` | `Ran 5 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Alarm চিরকাল `INSUFFICIENT_DATA` | Dimension ভুল (যেমন LB-এর পুরো ARN), বা metric নেই | `list-metrics --namespace AWS/ApplicationELB` দিয়ে আসল dimension |
| Alarm বাজে, email আসে না | SNS subscription confirm হয়নি | `list-subscriptions-by-topic` — `PendingConfirmation` |
| প্রতি spike-এ alarm | M=N=1 | 3 of 5 |
| Traffic নেই, 5xx alarm `INSUFFICIENT_DATA` | `missing` | `notBreaching` |
| EC2 memory metric নেই | AWS দেয় না | CloudWatch agent |
| Log বিল বাড়ছে | Retention নেই, debug log | Retention; log level |
| Logs Insights ধীর বা দামি | বড় সময়-পরিসর | সময় সীমিত, field filter আগে |

**`lab08-target-5xx`-এর runbook (উদাহরণ):**

1. ALB-এর target health (`tg_health.py`)।
2. Logs Insights-এ ৫xx-এর path।
3. সাম্প্রতিক deploy?
4. `/ready` — database?
5. প্রয়োজনে আগের version-এ ফেরা।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Log-এ secret বা PII নয় (L05-07-এর redaction)।
  - Log group KMS-এ encrypt করা যায়।
  - Alarm ও SNS-এর permission সীমিত রাখুন।
  - Security event-এর (CloudTrail) alarm — Module 19।
- **Performance:**
  - p95/p99 দেখুন, গড় নয়।
  - Alarm-এর delay = period × N — দ্রুত সাড়া বনাম শান্তি।
  - Agent-এর CPU/memory খরচ সামান্য, কিন্তু শূন্য নয়।
- **Cost:**
  - Alarm-প্রতি চার্জ।
  - Custom metric-এর সংখ্যা (dimension-এর প্রতিটি মিশ্রণ আলাদা metric)।
  - Log ingestion ও storage — retention ও log level।
  - Logs Insights-এ স্ক্যান করা GB।

## 14. Hands-on exercise

1. `alarm_sim.py` দিয়ে চার mode চালিয়ে Section 8.2-এর table নিজে বানান।
2. নিজের ALB-এ চারটি alarm বানিয়ে `set-alarm-state` দিয়ে notification পরীক্ষা করুন; তারপর cleanup।
3. `alarm_defs.py`-তে পঞ্চম alarm যোগ করুন: `CWAgent` namespace-এর `disk_used_percent > 85` (agent-এর config-এর dimension মিলিয়ে)।
4. Section 8.3-এর Logs Insights query নিজের TaskFlow log-এ চালান; ৫xx-এর path খুঁজুন।
5. Composite alarm: `5xx AND unhealthy-hosts` — কখন page করবেন, কখন শুধু ticket?

## 15. Mini-project — SLO-ভিত্তিক alert

TaskFlow-এর SLO লিখুন — যেমন ৩০ দিনে ৯৯.৫% request সফল।

- Error budget হিসাব করুন (L07-03-এর downtime-এর গণিত)।
- Metric math দিয়ে success rate: `1 - 5xx/RequestCount`।
- Burn-rate alarm দুটি: দ্রুত (১ ঘণ্টা) ও ধীর (৬ ঘণ্টা)।

Module 17-18-এর SRE অংশের ভিত্তি।

## 16. Interview প্রশ্ন

1. CloudWatch-এ metric, dimension ও statistic কী?
2. EC2-এর কোন metric AWS দেয় না? কীভাবে পাবেন?
3. "M out of N" alarm কেন? `TreatMissingData`-এর চার রূপ কখন কোনটা?
4. শুধু CPU alarm-এর সমস্যা কী? কোন alarm রাখবেন?
5. Log-এর খরচ কীভাবে নিয়ন্ত্রণ করবেন?
6. Alarm বাজলেও কেউ জানল না — সম্ভাব্য কারণ কী?

## 17. Self-assessment প্রশ্ন

1. হাসপাতাল-monitor analogy কোথায় মেলে না?
2. 5xx alarm-এ `notBreaching`, status check-এ `breaching` কেন?
3. Section 9.1-এ ৩০০ s-এর `2` কেন alarm থামায় না?
4. `TargetResponseTime`-এর threshold ৫০০ ms হলে মান কী?
5. Log group-এর ডিফল্ট retention কী, এবং কেন সমস্যা?

## 18. সংক্ষিপ্ত সারাংশ

- Metric = namespace + নাম + dimension; EC2-এর memory/disk-এর জন্য agent।
- Alarm: M of N, metric-এর অর্থ অনুযায়ী `TreatMissingData`, runbook, OK action।
- User-এর অভিজ্ঞতা (5xx, p95) ও কারণ (unhealthy, status check) — CPU একা নয়।
- Log: JSON + Logs Insights + retention; SNS subscription confirm।

## 19. Completion checklist

- [ ] `alarm_sim.py`-এর চার mode-এর পার্থক্য ব্যাখ্যা করতে পারি
- [ ] নিজের account-এ alarm + SNS, notification পরীক্ষা, তারপর cleanup
- [ ] Log group-এ retention দেওয়া
- [ ] `python3 -m unittest -v`-এ ৫টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- Amazon CloudWatch — What is CloudWatch: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/WhatIsCloudWatch.html
- CloudWatch — Using alarms (missing data সহ): https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/AlarmThatSendsEmail.html
- ALB — CloudWatch metrics: https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-cloudwatch-metrics.html
- CloudWatch Logs: https://docs.aws.amazon.com/AmazonCloudWatch/latest/logs/WhatIsCloudWatchLogs.html
- CloudWatch agent: https://docs.aws.amazon.com/AmazonCloudWatch/latest/monitoring/Install-CloudWatch-Agent.html
- Amazon CloudWatch pricing: https://aws.amazon.com/cloudwatch/pricing/

---

**পরের lesson:** L08-12 — Tagging, Cost Explorer ও resource cleanup automation
