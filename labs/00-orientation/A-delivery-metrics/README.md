# Lab 00-A — Delivery metrics

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৪৫ মিনিট |
| **Environment** | Ubuntu (বা যেকোনো OS-এ Python 3.10+) |
| **Label** | — (read-only; শুধু নিজের তৈরি CSV লেখে) |

## Objective

নিজের তৈরি data দিয়ে DORA metric ও Kanban flow metric হিসাব করা, হাতে যাচাই করা এবং ফল থেকে একটি উন্নতির সিদ্ধান্ত নেওয়া।

## Prerequisites

- Lesson: [L00-01](../../../00-orientation/L00-01-what-is-devops.md), [L00-03](../../../00-orientation/L00-03-sdlc-agile-release.md)
- Tool: `python3 --version` → 3.10+

## Environment setup

```bash
cd ~/devops-ai-engineering
mkdir -p ~/devops-notebook/labs/00-A
```

## Steps

1. **Deployment data তৈরি:** আপনার কোনো আসল বা কল্পিত project-এর শেষ ৮–১২টি deploy নিয়ে `~/devops-notebook/labs/00-A/deployments.csv` বানান। Format: [`deployments.csv`](../../../00-orientation/code/L00-01/deployments.csv)-এর মতো (`deploy_id,commit_time,deploy_time,failed,restored_time`)। অন্তত দুটি failed deploy রাখুন।
2. **Prediction লিখুন (চালানোর আগে):** notebook-এ আপনার অনুমান — deployment frequency, median lead time, change failure rate কত হবে।
3. **DORA metric চালান:**

   ```bash
   python3 00-orientation/code/L00-01/dora_metrics.py ~/devops-notebook/labs/00-A/deployments.csv
   ```

4. **হাতে যাচাই:** lead time-এর median ও change failure rate হাতে হিসাব করে মেলান।
5. **Work item data:** একই সময়ের ১০–১৫টি কাজ নিয়ে `work_items.csv` বানান ([format](../../../00-orientation/code/L00-03/work_items.csv))। অন্তত একটি কাজ খোলা রাখুন (`done` খালি)।
6. **Flow metric চালান:**

   ```bash
   python3 00-orientation/code/L00-03/flow_metrics.py ~/devops-notebook/labs/00-A/work_items.csv
   ```

7. **সিদ্ধান্ত:** কোন একটি metric উন্নত করবেন? Little's Law ব্যবহার করে হিসাব করুন — WIP অর্ধেক করলে (throughput একই ধরে) গড় cycle time কত হবে।

## Expected behavior

- দুটি script exit code 0 দিয়ে শেষ হয় এবং metric দেখায়।
- আপনার হাতে করা হিসাব script-এর সাথে মেলে।

## Verification

```bash
python3 00-orientation/code/L00-01/dora_metrics.py ~/devops-notebook/labs/00-A/deployments.csv --json; echo "exit=$?"
python3 00-orientation/code/L00-03/flow_metrics.py ~/devops-notebook/labs/00-A/work_items.csv; echo "exit=$?"
```

`exit=0` দুটিতেই।

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| `invalid data: failed must be yes/no` | `Yes`/`true` লেখা | `yes`/`no` লিখুন |
| `failed deployment needs restored_time` | failed=yes কিন্তু restore সময় নেই | সময় যোগ করুন |
| `no items finished in the period` | সব কাজ খোলা, বা `--start/--end` ভুল | অন্তত একটি `done` তারিখ দিন |
| `Invalid isoformat string` | তারিখের format ভুল | `YYYY-MM-DD` বা `YYYY-MM-DDTHH:MM:SS` |

## Cleanup / reset

কিছু মুছতে হবে না — CSV ও notebook আপনার রেকর্ড। নতুন করে শুরু করতে `~/devops-notebook/labs/00-A/` folder-এর file বদলান।

## Assessment

1. আপনার prediction ও আসল ফলের মধ্যে সবচেয়ে বড় পার্থক্য কোথায়, এবং কেন?
2. আপনার data-য় গড় ও median lead time কতটা আলাদা? কোন deploy পার্থক্যের জন্য দায়ী?
3. Little's Law দিয়ে WIP অর্ধেক করার প্রভাব হিসাব দেখান।
4. চারটি DORA metric-এর মধ্যে কোনটি আপনার ক্ষেত্রে সবচেয়ে দুর্বল, এবং এই repository-র কোন module তা উন্নত করতে সাহায্য করবে?
