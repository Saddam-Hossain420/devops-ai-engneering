# L08-01 — AWS account safety: root user, MFA, budget alert

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২ ঘণ্টা (account খোলা সহ) |
| **পূর্বশর্ত** | [L07-05 — IAM ও least privilege](../07-cloud-fundamentals/L07-05-iam-least-privilege.md), [L07-06 — Cost, budget, cleanup](../07-cloud-fundamentals/L07-06-cost-budget-tagging-cleanup.md), [L01-05 — sudo](../01-linux-systems/L01-05-acl-sudo.md) |
| **Label** | 💰 আসল AWS account — এই lesson-এর ধাপগুলো (MFA, budget, IAM user) সাধারণত চার্জমুক্ত, কিন্তু account-এ যেকোনো resource চালু করলে বিল হয় |
| **Tested** | `account_baseline.py` ও `make_budget.py`: ৬টি test পাস (Python 3.14.5, Windows)। Input **হাতে তৈরি** — AWS CLI-র documented output-এর রূপে (`get-account-summary`, credential report CSV, `describe-budgets`)। **কোনো AWS account-এ চালানো হয়নি; AWS CLI এই machine-এ নেই।** Lesson-এর `aws` command-গুলো আপনার account-এ চালানোর জন্য — output আমার দেখানো নয়। |

---

## 1. এই lesson-এ যা শিখবেন

- Root user কী, কেন এটা দিয়ে দৈনন্দিন কাজ নয়, কোন কাজে root লাগে।
- Root ও প্রতিটি মানুষের login-এ MFA।
- Root-এর access key কেন কখনো নয়।
- দৈনন্দিন কাজের জন্য আলাদা identity: IAM Identity Center (পছন্দনীয়) বা MFA-সহ IAM admin user।
- **Budget ও alert — কোনো resource চালুর আগেই।**
- Credential report দিয়ে account-এর অবস্থা যাচাই (`account_baseline.py`)।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

নতুন AWS account মানে একটি email + password, যার হাতে **সীমাহীন ক্ষমতা** ও আপনার card। পরিচিত ঘটনা:

- Root-এর access key দিয়ে tutorial অনুসরণ করা হলো; key GitHub-এ গেল; কয়েক ঘণ্টায় অন্য region-এ বড় instance চালু হলো। কেউ জানল বিল আসার পরে।
- Root password-এ MFA নেই; একই password অন্য site-এ ফাঁস হলো।
- Lab শেষে NAT gateway মোছা হয়নি; budget না থাকায় এক মাস পরে জানা গেল।

L07-05-এর IAM ও L07-06-এর budget-এর ধারণা এখানে আসল account-এ প্রয়োগ হয় — **কোনো resource বানানোর আগে।**

## 3. সহজ ভাষায় পরিচয়

| Identity | কী | কখন ব্যবহার |
|---|---|---|
| **Root user** | Account খোলার email; সব ক্ষমতা; IAM policy দিয়ে সীমিত করা যায় না | শুধু root-only কাজ — যেমন account বন্ধ, কিছু billing ও support setting। তারপর তালাবন্ধ |
| **IAM Identity Center user** | একটি কেন্দ্রীয় login; প্রতিবার অস্থায়ী credential | মানুষের দৈনন্দিন কাজ — AWS-এর সুপারিশ |
| **IAM user** | Account-এর ভেতরের স্থায়ী user; password ও/বা access key | ছোট lab-এ admin user (MFA-সহ); দীর্ঘমেয়াদি key এড়িয়ে চলুন |
| **IAM role** | অস্থায়ী credential দেওয়া identity | Service, CI, cross-account (L08-03) |

**Linux-এর তুলনা (L01-05):** root user = Linux-এর `root`; admin user + MFA = `sudo`-ক্ষমতাসম্পন্ন নিজের user। Linux-এ যেমন root-এ SSH login বন্ধ রেখে `sudo` ব্যবহার করেন, AWS-এও তেমন।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### বাড়ির মূল দলিল ও চাবি

- **Root** = বাড়ির দলিল। আলমারিতে তালাবন্ধ থাকে; প্রতিদিন পকেটে নিয়ে ঘোরেন না।
- **MFA** = দলিলের আলমারির দ্বিতীয় তালা।
- **Admin user / Identity Center** = প্রতিদিনের চাবি; হারালে বদলানো যায়।
- **Budget alert** = বিদ্যুৎ-বিলের মাঝ-মাসের SMS।

### Analogy কোথায় মেলে না

- **দলিল চুরি হলেও বাড়ি সরানো যায় না।** Root credential চুরি হলে আক্রমণকারী মিনিটের মধ্যে account থেকে আপনাকে বের করে দিতে পারে (email ও password বদলে)। Recovery-তে দিন লাগতে পারে।
- **চাবি একটাই।** Access key একটি text — copy হয়, log-এ যায়, repo-তে commit হয়, এবং আপনি জানতেও পারেন না কতগুলো copy আছে।
- **বিদ্যুৎ-বিলের SMS সময়মতো আসে।** AWS-এর billing data দিনে কয়েকবার আপডেট হয় — real-time নয়। Budget alert দেরিতে জানায়; প্রতিরোধ নয় (L07-06)।

## 5. Real-world engineering scenario — "প্রথম দিনের checklist"

একটি ছোট team AWS-এ যাচ্ছে। একজন account খুলে root দিয়েই console-এ EC2 চালু করেছেন। দুই মাস পরে নিরাপত্তা review-তে তাঁরা credential report download করে `account_baseline.py` চালালেন। নমুনা report-এর আসল output:

```text
CRITICAL  root                       root user has no MFA — enable it before anything else
CRITICAL  root                       root user has access keys — delete them (root keys cannot be limited by IAM)
WARN      ana                        console password without MFA
WARN      ana                        access key 1 is 269 days old (> 90) — rotate, or better: replace with a role/SSO
WARN      budget monthly-learning    no FORECASTED notification (warns early, while the month is still young)
WARN      ci-bot                     access key 1 is 227 days old (> 90) — rotate, or better: replace with a role/SSO
WARN      ci-bot                     access key 1 never used in 227 days — deactivate it
WARN      root                       root signed in 3 day(s) ago — use an admin user/role for daily work
8 finding(s), 2 critical
```

**ক্রম:**

1. Root-এ MFA।
2. Root key মোছা।
3. Admin identity বানিয়ে root-এ logout।
4. Budget-এ FORECASTED alert।
5. মানুষের MFA।
6. অব্যবহৃত key বন্ধ।
7. CI-এর key-এর বদলে role (L08-03, Module 11-এর OIDC)।

**শিক্ষা:** প্রথম দিনেই এই ক্রম মানলে দুই মাসের ঝুঁকি তৈরিই হতো না।

## 6. Diagram — নিরাপদ account-এর রূপ

```text
           ┌──────────────── AWS account 111122223333 ────────────────┐
 email +   │  ROOT  ── MFA ✔ ── access key ✘ ── শুধু root-only কাজে    │
 password ─┤                                                           │
           │  Identity Center / IAM admin (MFA ✔) ──► দৈনন্দিন console/CLI │
           │       └─ অস্থায়ী credential (L08-02)                       │
           │  IAM role ◄── EC2 / CI (L08-03)                            │
           │                                                           │
           │  Budget: ACTUAL 50·80·100% + FORECASTED 100% ──► email     │
           │  CloudTrail event history (management event, ৯০ দিন)       │
           └───────────────────────────────────────────────────────────┘
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Root user | Account-এর মালিক identity; সীমাহীন ক্ষমতা |
| MFA | দ্বিতীয় প্রমাণ — passkey/security key বা authenticator app |
| IAM Identity Center | AWS-এর কেন্দ্রীয় login (SSO); অস্থায়ী credential |
| Access key | `AKIA…` id + secret — দীর্ঘমেয়াদি programmatic credential |
| Credential report | Account-এর সব user-এর password, MFA ও key-এর অবস্থার CSV |
| AWS Budgets | খরচের সীমা ও alert (ACTUAL / FORECASTED) |
| CloudTrail | API call-এর audit log; event history ডিফল্টে চালু |
| Alternate contact | Billing, operations ও security-র জন্য আলাদা যোগাযোগ |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Root কেন সীমিত করা যায় না

IAM policy root-এর ওপর প্রযোজ্য নয়। AWS Organizations-এর SCP member account-এর root-কে সীমিত করতে পারে, কিন্তু একক account-এ নয়। তাই root-এর একমাত্র সুরক্ষা হলো শক্তিশালী password, MFA, key না থাকা ও ব্যবহার না করা।

### 8.2 Credential report

`aws iam generate-credential-report` একটি CSV তৈরি করে; `get-credential-report` base64-এ ফেরত দেয়। Root-এর সারির নাম `<root_account>`। কিছু ঘরে তারিখের বদলে বিশেষ মান থাকে — `N/A`, `no_information`, `not_supported`। `account_baseline.py` সেগুলোকে তারিখ ধরে না (test-এ যাচাই)।

### 8.3 Budget-এর alert

- **ACTUAL** — খরচ হয়ে যাওয়ার পরে।
- **FORECASTED** — AWS-এর অনুমান মাস শেষে সীমা ছাড়াবে বলে।

নতুন account-এ forecast-এর জন্য যথেষ্ট ইতিহাস না থাকতে পারে, তাই দুটোই রাখুন। Amount আপনার নিজের সীমা — শেখার জন্য ছোট একটি সংখ্যা।

### 8.4 Free tier সম্পর্কে সতর্কতা

AWS ২০২৫-এ নতুন account-এর free tier-এর নিয়ম বদলেছে। Signup-এর সময় [AWS Free Tier page](https://aws.amazon.com/free/)-এ **বর্তমান** নিয়ম পড়ুন। এই course কোনো নির্দিষ্ট "বিনামূল্যে" পরিমাণ দাবি করে না।

ধরে নিন যা চালু করবেন তার বিল হতে পারে। তাই প্রতিটি lab-এ cleanup আছে।

> **Fedora-তে:** কোনো পার্থক্য নেই — browser ও AWS CLI-র কাজ।

## 9. Practical demonstration

Files:

- [`code/L08-01/account_baseline.py`](code/L08-01/account_baseline.py)
- [`make_budget.py`](code/L08-01/make_budget.py)
- [`sample/`](code/L08-01/sample/) — হাতে তৈরি
- [`test_l08_01.py`](code/L08-01/test_l08_01.py)

### 9.1 Account খোলা ও root সুরক্ষা (console — আপনি করবেন)

1. Account খুলুন এমন email দিয়ে, যা একটি team/নিজের নিয়ন্ত্রিত inbox (ব্যক্তিগত job email নয়)। Password manager-এ দীর্ঘ random password।
2. Root হিসেবে sign in → **Security credentials** → MFA যোগ (passkey/security key বা authenticator app)। দ্বিতীয় একটি MFA device-ও যোগ করে রাখুন — একটি হারালে lockout এড়াতে।
3. Root-এর **Access keys** অংশে কোনো key থাকলে মুছুন।
4. **Account → Alternate contacts** — billing ও security contact।
5. **Account → IAM user and role access to Billing information** চালু করুন, যাতে admin user budget দেখতে পারে।
6. Admin identity বানান — Identity Center (সুপারিশ), বা MFA-সহ একটি IAM user (`AdministratorAccess`, শুধু console)।
7. Root থেকে sign out। এরপর root শুধু root-only কাজে।

### 9.2 Budget বানানো — আসল output (local)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-01
python3 make_budget.py --name monthly-learning --amount 10 --email you@example.com --out ~/aws-setup
```

```text
wrote …/aws-setup/budget.json and …/aws-setup/notifications.json
review both files, then run (account id: aws sts get-caller-identity --query Account --output text):
  aws budgets create-budget --account-id <ACCOUNT_ID> --budget file://…/budget.json --notifications-with-subscribers file://…/notifications.json
verify: aws budgets describe-notifications-for-budget --account-id <ACCOUNT_ID> --budget-name monthly-learning
```

`10` আমার উদাহরণ — নিজের সীমা দিন। আসল email দিন। AWS CLI ও credential L08-02-এ; তার আগে console-এর **Billing and Cost Management → Budgets** থেকেও একই budget বানাতে পারেন।

### 9.3 Baseline যাচাই — আসল output (হাতে তৈরি নমুনায়)

```bash
python3 account_baseline.py --summary sample/account-summary.json --report sample/credential-report.csv \
  --budgets sample/budgets.json --notifications sample/notifications-monthly-learning.json --today 2026-10-28
echo "exit=$?"
```

Output Section 5-এ, `exit=1`। নিজের account-এ (L08-02-এর পরে):

```bash
aws iam get-account-summary > account-summary.json
aws iam generate-credential-report
aws iam get-credential-report --query Content --output text | base64 -d > credential-report.csv
aws budgets describe-budgets --account-id "$(aws sts get-caller-identity --query Account --output text)" > budgets.json
```

লক্ষ্য: `baseline OK`, exit ০।

### 9.4 লেখার সময়

প্রথম সংস্করণে root-এর MFA না থাকা দুবার দেখাত — একবার summary থেকে, একবার credential report থেকে। এখন একই সমস্যা একবার দেখায় (test: `count("root user has no MFA") == 1`)।

### 9.5 Test

```bash
python3 -m unittest -v
```

৬টি test:

- নমুনার ৮টি finding।
- নিরাপদ account-এ শূন্য finding।
- বিশেষ মান তারিখ নয়।
- Budget-এর check।
- `make_budget`-এর output baseline পাস করে।
- ভুল input প্রত্যাখ্যান।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| Saved CLI output পড়ে | Offline | API credential ছাড়াই review; CI-তে চালানো যায় |
| `parse_day` | `N/A` ইত্যাদি → None | Credential report-এর বিশেষ মান |
| CRITICAL বনাম WARN | Root-এর MFA/key critical | আগে কোনটা ঠিক করবেন |
| `notifications-<name>.json` | Budget-এর নাম file-নামে | API output-এ নাম থাকে না |
| `make_budget.py` command ছাপে, চালায় না | মানুষ দেখে চালায় | Account-এ পরিবর্তন সচেতনভাবে |
| Amount বাধ্যতামূলক, default নেই | নিজের সীমা | কোনো "দাম" বানানো নয় |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় `account_baseline.py` | ৮ finding, ২ critical, exit ১ |
| নিজের account (সব ধাপের পরে) | `baseline OK`, exit ০ |
| Console → Budgets | `monthly-learning`, চারটি alert |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| ভুল | ফল | সমাধান |
|---|---|---|
| Root দিয়ে দৈনন্দিন কাজ | সব ঝুঁকি এক জায়গায় | Admin identity, root logout |
| একটিমাত্র MFA device | Phone হারালে lockout | দুটি device; recovery পথ জানুন |
| Root access key | সীমাহীন key ফাঁসের ঝুঁকি | মুছুন; কখনো বানাবেন না |
| Admin user budget দেখতে পায় না | "Access denied" Billing-এ | Root থেকে IAM access to Billing চালু |
| শুধু ACTUAL alert | দেরিতে জানা | FORECASTED যোগ |
| Budget email অন্যের inbox-এ | কেউ দেখে না | নিজের ও team-এর address |
| `base64 -d` Windows-এ নেই | CSV হয় না | Git Bash-এ চলে, বা PowerShell-এ `[Convert]::FromBase64String` |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Root email-এর নিজের নিরাপত্তাও গুরুত্বপূর্ণ (password reset এখানেই যায়) — সেখানেও MFA।
  - CloudTrail event history ডিফল্টে ৯০ দিনের management event রাখে। দীর্ঘ সংরক্ষণের জন্য trail (L08-11/Module 19)।
- **Cost:**
  - Budget একটি সতর্কতা, সীমা নয় — AWS খরচ থামায় না।
  - Lab-এর জন্য ছোট সীমা ও ঘন alert রাখুন।
  - Cost Anomaly Detection আরেকটি স্তর (L08-12)।
- **Performance:** প্রযোজ্য নয়।

## 14. Hands-on exercise

1. Section 9.1-এর সাতটি ধাপ আপনার account-এ শেষ করুন; প্রতিটির screenshot বা নোট notebook-এ।
2. `make_budget.py` দিয়ে budget বানিয়ে `describe-notifications-for-budget` দিয়ে যাচাই করুন।
3. নিজের account-এর credential report-এ `account_baseline.py` চালিয়ে `baseline OK` পর্যন্ত পৌঁছান।
4. `account_baseline.py`-তে নতুন check যোগ করুন: password ৯০ দিনের বেশি পুরোনো (`password_last_changed`) — WARN।
5. লিখুন: root credential হারালে বা চুরি হলে আপনার recovery পরিকল্পনা কী?

## 15. Mini-project — Account bootstrap runbook

একটি Markdown runbook (`aws-account-bootstrap.md`):

- প্রতিটি ধাপ, কে করবে ও কীভাবে যাচাই;
- `account_baseline.py`-এর output-এর লক্ষ্য;
- জরুরি অবস্থায় (key ফাঁস) প্রথম ৩০ মিনিটের কাজ।

Module 19-এ multi-account ও Module 29-এ FinOps-এ এটি বাড়বে।

## 16. Interview প্রশ্ন

1. Root user কেন দৈনন্দিন কাজে ব্যবহার করা উচিত নয়? কোন কাজে root লাগে?
2. নতুন AWS account-এ প্রথম ৩০ মিনিটে কী করবেন?
3. IAM user ও Identity Center-এর পার্থক্য কী?
4. Budget ACTUAL ও FORECASTED alert-এর পার্থক্য কী? Budget কি খরচ থামায়?
5. Credential report-এ কী দেখেন?

## 17. Self-assessment প্রশ্ন

1. দলিল-analogy কোথায় মেলে না?
2. Root-কে IAM policy দিয়ে সীমিত করা যায় না কেন? কী দিয়ে যায়?
3. Credential report-এ `not_supported` কোথায় আসে?
4. দুটি MFA device কেন?
5. Admin user কেন budget দেখতে পায় না, এবং সমাধান কী?

## 18. সংক্ষিপ্ত সারাংশ

- Root: MFA, key নেই, তালাবন্ধ।
- দৈনন্দিন কাজে Identity Center বা MFA-সহ admin; programmatic কাজে অস্থায়ী credential (L08-02) ও role (L08-03)।
- কোনো resource চালুর আগে budget — ACTUAL ও FORECASTED।
- `account_baseline.py` দিয়ে নিয়মিত যাচাই; budget সতর্ক করে, থামায় না।

## 19. Completion checklist

- [ ] Root-এ MFA (দুটি device), root key নেই, alternate contact
- [ ] Admin identity তৈরি, root-এ logout
- [ ] Budget ও চারটি alert চালু (module completion criteria)
- [ ] নিজের account-এ `account_baseline.py` → `baseline OK`
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS IAM — Root user: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_root-user.html
- AWS IAM — MFA: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_mfa.html
- AWS IAM — Credential reports: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_getting-report.html
- AWS IAM — Security best practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- AWS Budgets: https://docs.aws.amazon.com/cost-management/latest/userguide/budgets-managing-costs.html
- AWS Free Tier: https://aws.amazon.com/free/

---

**পরের lesson:** L08-02 — AWS CLI, profile, temporary credential ও boto3
