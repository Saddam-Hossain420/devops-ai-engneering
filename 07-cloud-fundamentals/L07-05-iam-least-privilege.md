# L07-05 — IAM, identity ও least privilege

| | |
|---|---|
| **Module** | 07 — Cloud Fundamentals |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L07-02 — Shared responsibility](L07-02-service-models-shared-responsibility.md), [L01-04 — User ও permission](../01-linux-systems/L01-04-users-permissions.md), [L05-10 — Secret](../05-python-for-infrastructure/L05-10-secrets-and-config.md) |
| **Label** | — |
| **Tested** | `policy_eval.py` ও `policy_lint.py`: ৮টি test পাস (Python 3.14.5, Windows)। প্রত্যাশাগুলো AWS IAM documentation-এর policy evaluation logic অনুযায়ী লেখা। এটা **শেখার জন্য সরল একটি evaluator** — resource policy, permission boundary, SCP ও session policy বিবেচনা করে না। আসল AWS-এর IAM policy simulator-এর সাথে **মেলানো হয়নি**। লেখার সময় lint-এর একটি গুরুতর ফাঁক ধরা পড়েছে (Section 9.3)। কোনো cloud account বা API call ব্যবহার হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Identity বনাম access: authentication (তুমি কে) ও authorization (তুমি কী করতে পারো)।
- Cloud IAM-এর অংশ: user, group, **role**, policy, temporary credential।
- Policy-র ভাষা (AWS-এর রূপ — শিল্পে সবচেয়ে প্রচলিত): Effect, Action, Resource, Condition, NotAction।
- **Evaluation-এর নিয়ম:** default deny → কোনো Allow → কিন্তু explicit Deny সবসময় জেতে।
- **Least privilege** বাস্তবে: নির্দিষ্ট action, নির্দিষ্ট resource, শর্ত (MFA, source IP)।
- Privilege escalation-এর পথ: `iam:PassRole`, `NotAction`, policy-version বদল।
- Long-lived access key বনাম role ও short-lived credential।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

Cloud-এ network-এর চেয়েও বড় নিরাপত্তা-সীমানা হলো **identity**। একটি API call দিয়েই server বানানো, database মোছা, বা data বাইরে পাঠানো যায় — তাই কোন credential কী করতে পারে, সেটাই আসল প্রশ্ন।

সাধারণ ব্যর্থতা:

- "দ্রুত কাজ চালাতে" developer-কে `AdministratorAccess`। পরে তার laptop থেকে key চুরি হলো, এবং আক্রমণকারী পুরো account নিয়ন্ত্রণ পেল।
- Application-এর code-এ long-lived access key, যা Git-এ চলে গেছে (L05-10)।
- একটি policy যা "শুধু billing বাদে সব" দেয় — যার মধ্যে IAM-ও আছে। নিজেকে admin বানানো এক step।
- CI pipeline-এর key-এর এত অনুমতি যে compromised dependency production মুছে দিতে পারে।

## 3. সহজ ভাষায় পরিচয়

| ধারণা | কী | কখন |
|---|---|---|
| User | মানুষ (বা পুরোনো ধাঁচে app), long-lived credential | মানুষের জন্য — SSO ও MFA সহ |
| Group | User-দের দল, একসাথে policy | Role-ভিত্তিক বিভাজন |
| Role | Assume করা যায় এমন পরিচয়, temporary credential | **App, CI, service — সবসময়** |
| Policy | কে কোন resource-এ কী করতে পারবে, JSON | Least privilege-এর একক |

```json
{"Effect": "Allow",
 "Action": ["s3:GetObject", "s3:PutObject"],
 "Resource": "arn:aws:s3:::taskflow-uploads/u/*"}
```

**সিদ্ধান্তের ক্রম:**

```text
১. কোনো Deny মিলেছে?       → DENY (শেষ)
২. কোনো Allow মিলেছে?      → ALLOW
৩. কিছুই না               → DENY (implicit)
```

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হোটেলের key card

- **User** = নিয়মিত কর্মী — নিজের স্থায়ী card।
- **Role** = "রাতের নিরাপত্তারক্ষী"-র দায়িত্ব — শিফট শুরুতে card নেন, শেষে ফেরত দেন (temporary credential)।
- **Policy** = card কোন দরজা খোলে: "৩য় তলা, ৩০১–৩১০, রাত ১০টা–৬টা"।
- **Least privilege** = housekeeping-এর card শুধু নির্ধারিত ঘর খোলে, vault নয়।
- **Explicit deny** = vault-এর দরজায় লেখা "কোনো card খুলবে না, CEO-রটাও না"।

### Analogy কোথায় মেলে না

- **হোটেলে কেউ নিজের card-এ নতুন দরজা যোগ করতে পারে না।** IAM-এ পারে, যদি তার IAM-এর অনুমতি থাকে: `iam:AttachUserPolicy`, `iam:CreatePolicyVersion`, বা `iam:PassRole` দিয়ে বেশি-ক্ষমতার role একটি server-কে দিয়ে সেই server-এর মাধ্যমে কাজ করানো। এগুলোই **privilege escalation**-এর পথ — IAM-এর অনুমতি admin-এর সমান।
- **"সব দরজা, শুধু অফিস বাদে" card বিরল।** IAM-এ `NotAction` দিয়ে এটা সহজ, এবং বিপজ্জনক: provider নতুন service আনলে সেটাও স্বয়ংক্রিয়ভাবে অনুমোদিত। আর বাদের তালিকায় IAM না থাকলে কার্যত admin (Section 9.3)।
- **হারানো card বাতিল করলে শেষ।** Long-lived access key হাজার জায়গায় copy হয় — laptop, CI, log, Git history। বাতিল করার আগে জানতে হয় কোথায় কোথায় ব্যবহার হচ্ছে। Role-এর temporary credential নিজে থেকেই কয়েক ঘণ্টায় মেয়াদোত্তীর্ণ।

## 5. Real-world engineering scenario — "শুধু billing বাদে সব"

**পরিস্থিতি:** একজন developer অভিযোগ করলেন, প্রতিটি নতুন service-এ "AccessDenied"। Team lead "সমাধান" দিলেন `dev-admin.json`:

- `NotAction: ["aws-portal:*", "budgets:*"]` + `Resource: *` — "billing ছাড়া সব"।
- `iam:PassRole` on `*`।
- `s3:*` on `*`।
- একটি Deny: MFA না থাকলে IAM নয়।

ছয় মাস পরে developer-এর laptop-এ malware, এবং browser-এর session চুরি (MFA-সহ session)। আক্রমণকারী যা করতে পারল (`policy_eval.py`-এর আসল ফল):

```text
ALLOW iam:CreateUser           *   allowed by EverythingExceptBilling     (MFA-যুক্ত session-এ)
ALLOW ec2:TerminateInstances   *   allowed by EverythingExceptBilling
DENY  aws-portal:ViewBilling   *   implicit deny
```

অর্থাৎ নতুন admin user বানানো, সব server মোছা, সব bucket পড়া — শুধু billing দেখা যাবে না।

`policy_lint.py`-এর আসল ফল:

```text
CRIT  dev-admin.json EverythingExceptBilling Allow + NotAction on "*" — effectively administrator (iam, kms, organizations, sts still allowed)
CRIT  dev-admin.json PassAnyRole         iam:passrole on "*" — known privilege-escalation path; scope the resource
WARN  dev-admin.json S3All               s3:* — every action of s3, including delete; list the actions needed
```

**সঠিক পদ্ধতি:**

- Developer-এর জন্য নির্দিষ্ট service ও dev account-এ সীমিত অনুমতি।
- Production-এ শুধু read, অথবা break-glass role (সময়সীমিত, audited)।
- App-এর জন্য `taskflow-app.json`-এর মতো নির্দিষ্ট policy (lint পরিষ্কার)।
- "AccessDenied" এলে CloudTrail/access analyzer দেখে **ঠিক যে action লাগবে** সেটাই যোগ করা।

**শিক্ষা:** "Billing ছাড়া সব" মানে "admin"। IAM-এর অনুমতি থাকলে বাকি সব অনুমতি নিজেকে দেওয়া যায়।

## 6. Diagram — একটি request-এর সিদ্ধান্ত

```text
 TaskFlow app (EC2/ECS/Lambda) ── role assume ──► temporary credential (ঘণ্টায় মেয়াদ শেষ)
        │
        ▼ API call: s3:PutObject  arn:aws:s3:::taskflow-uploads/u/42/a.png
 ┌──────────────────── policy evaluation ────────────────────┐
 │ সব policy-র সব statement:                                   │
 │   Action মেলে? (wildcard, case-insensitive)                 │
 │   Resource মেলে? (wildcard, case-sensitive)                 │
 │   Condition সত্য? (MFA, SourceIp, prefix …)                 │
 │ মিলে যাওয়াগুলোর মধ্যে:                                       │
 │   কোনো Deny?  ── হ্যাঁ ──► DENY (explicit)                   │
 │   কোনো Allow? ── হ্যাঁ ──► ALLOW                             │
 │   কিছু নয়     ─────────► DENY (implicit)                    │
 └────────────────────────────────────────────────────────────┘
 (বাস্তবে এর ওপরে: SCP, permission boundary, resource policy, session policy — সবগুলোর মিল)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Principal | যে request করছে (user, role, service) |
| Authentication / authorization | পরিচয় যাচাই / অনুমতি যাচাই |
| Role | Assume-যোগ্য পরিচয়, temporary credential |
| Trust policy | কে এই role assume করতে পারবে |
| Identity policy / resource policy | Principal-এ লাগানো / resource-এ লাগানো (bucket policy) |
| ARN | Resource-এর পূর্ণ নাম |
| Implicit / explicit deny | কোনো অনুমতি নেই / স্পষ্ট নিষেধ |
| Least privilege | কাজের জন্য ন্যূনতম অনুমতি |
| Privilege escalation | নিজের অনুমতি বাড়ানোর পথ |
| `iam:PassRole` | কোনো service-কে একটি role দেওয়ার অনুমতি |
| Permission boundary / SCP | অনুমতির সর্বোচ্চ সীমা (user / account স্তরে) |
| SSO / federation | বাইরের identity provider দিয়ে login |
| Break-glass | জরুরি, সময়সীমিত, audited উচ্চ অনুমতি |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Evaluation

AWS documentation-এর identity-policy অংশ:

- Default deny।
- কোনো statement-এর Effect `Deny` মিললে সিদ্ধান্ত deny, অন্য কোনো Allow যাই বলুক।
- নইলে কোনো Allow মিললে allow।

`policy_eval.py` এই অংশটুকু করে। Test-এ যাচাই করা হয়, policy-র ক্রম বদলালেও ফল একই।

### 8.2 Matching-এর সূক্ষ্মতা

- **Action** case-insensitive (`S3:GETOBJECT` = `s3:GetObject`); **resource ARN** case-sensitive।
- `*` যেকোনো অক্ষর, `?` একটি অক্ষর।
- `NotAction` + Allow = "তালিকার বাইরের সব" — Allow-এর সাথে প্রায় সবসময় ভুল। Deny-এর সাথে কাজের: "এগুলো ছাড়া সব নিষেধ"।

### 8.3 Condition-এর নিয়ম

- একটি statement-এর একাধিক key = AND; একটি key-এর একাধিক মান = OR।
- **Request-এ key না থাকলে** সাধারণ operator মিথ্যা দেয়। কিন্তু `…IfExists` সত্য দেয়।

তাই `"Deny if BoolIfExists aws:MultiFactorAuthPresent = false"` — MFA-এর তথ্যই না থাকলে (যেমন long-lived access key-এর call) **deny** করে। নিরাপদ default এটাই। Test-এ দুটোই যাচাই করা।

### 8.4 Role ও temporary credential

App বা CI-কে key দেওয়ার বদলে role দিন:

- **Compute service** (VM/container/function) metadata থেকে নিজে temporary credential পায়, এবং তা কয়েক ঘণ্টায় নবায়ন হয়।
- **CI:** OIDC দিয়ে GitHub Actions সরাসরি role assume করে, তাই repository-তে কোনো secret থাকে না (Module 11)।
- **মানুষ:** SSO, MFA বাধ্যতামূলক।

> **Fedora-তে:** কোনো পার্থক্য নেই — ধারণাগত। Linux-এর নিজস্ব সমতুল্য L01-04/05 (user, group, sudo)।

## 9. Practical demonstration

Files:

- [`code/L07-05/policy_eval.py`](code/L07-05/policy_eval.py), [`policy_lint.py`](code/L07-05/policy_lint.py)।
- [`taskflow-app.json`](code/L07-05/taskflow-app.json) (least privilege), [`dev-admin.json`](code/L07-05/dev-admin.json) (ঝুঁকিপূর্ণ) — দুটোই হাতে তৈরি; account id কাল্পনিক।
- [`requests.json`](code/L07-05/requests.json)।
- [`test_l07_05.py`](code/L07-05/test_l07_05.py)।

### 9.1 TaskFlow-এর least-privilege policy — আসল output

```bash
cd ~/devops-ai-engineering/07-cloud-fundamentals/code/L07-05
python3 policy_eval.py taskflow-app.json --requests requests.json; echo "exit=$?"
```

```text
ALLOW s3:GetObject             arn:aws:s3:::taskflow-uploads/u/42/avatar.png    allowed by UploadsReadWrite  ✓
DENY  s3:GetObject             arn:aws:s3:::taskflow-uploads/admin/report.csv   implicit deny (no statement allows it)  ✓
ALLOW S3:PutObject             arn:aws:s3:::taskflow-uploads/u/1.png            allowed by UploadsReadWrite  ✓
DENY  s3:DeleteObject          arn:aws:s3:::taskflow-uploads/u/1.png            implicit deny (no statement allows it)  ✓
ALLOW s3:ListBucket            arn:aws:s3:::taskflow-uploads                    allowed by ListOwnPrefix  ✓
DENY  s3:ListBucket            arn:aws:s3:::taskflow-uploads                    implicit deny (no statement allows it)  ✓
ALLOW secretsmanager:GetSecretValue …secret:taskflow/db-AbCdEf                  allowed by ReadDbSecret  ✓
DENY  secretsmanager:GetSecretValue …secret:billing/api-key-XyZ                 implicit deny (no statement allows it)  ✓
DENY  ec2:TerminateInstances   *                                                implicit deny (no statement allows it)  ✓
exit=0
```

- `ListBucket` একই resource-এ দুবার: `s3:prefix = u/42/` থাকলে allow, না থাকলে deny (Condition)।
- App অন্য prefix (`admin/`), অন্য secret, বা delete কোনোটাই পারে না — compromise হলেও ক্ষতির সীমা ছোট (blast radius)।

### 9.2 `dev-admin.json`

Section 5-এর আসল output দেখুন। MFA-এর তিন অবস্থায়:

```text
--context aws:MultiFactorAuthPresent=false   DENY  iam:CreateUser  explicit deny by IamWithMfaOnly
--context aws:MultiFactorAuthPresent=true    ALLOW iam:CreateUser  allowed by EverythingExceptBilling
(context নেই)                                 DENY  iam:CreateUser  explicit deny by IamWithMfaOnly     ← BoolIfExists
```

MFA-এর Deny ঠিকমতো কাজ করছে — কিন্তু MFA-যুক্ত চুরি-যাওয়া session-এর বিরুদ্ধে কিছু করে না।

### 9.3 লেখার সময় ধরা পড়া lint-এর ফাঁক

প্রথম সংস্করণে `NotAction`-এর জন্য lint শুধু **WARN** দিচ্ছিল:

```text
WARN  dev-admin.json EverythingExceptBilling Allow with NotAction grants everything except the list — …
```

অথচ evaluator একই policy-তে `iam:CreateUser` ও `ec2:TerminateInstances` ALLOW দেখাচ্ছিল। দুটো tool পাশাপাশি চালিয়ে অসঙ্গতি ধরা পড়ল। এখন নিয়ম: `NotAction` + `Resource: *`, যদি বাদের তালিকায় iam/sts/kms/organizations-এর সবগুলো না থাকে → **CRITICAL** ("effectively administrator")। একটি regression test আছে।

**শিক্ষা:** একটি security tool-এর সতর্কতার মাত্রাও test করুন। ভুল মাত্রার সতর্কতা ("শুধু warning") উপেক্ষিত হয়।

### 9.4 আসল cloud-এ (চালানো হয়নি; account ও খরচের প্রশ্ন — Module 08)

AWS-এর IAM policy simulator ও IAM Access Analyzer (policy validation, unused access) একই প্রশ্নের প্রামাণিক উত্তর দেয়। Module 08-এ account safety-র পরে ব্যবহার করা হবে।

### 9.5 Test

```bash
python3 -m unittest -v
```

৮টি test:

- Default deny ও explicit deny (policy-র ক্রম নির্বিশেষে)।
- Wildcard ও case।
- `NotAction` / `NotResource`।
- Condition: Bool, IP, key না থাকা, `IfExists`।
- নমুনা request-এর প্রত্যাশা।
- Lint-এর নমুনা।
- **NotAction-admin = critical** (regression)।
- অন্যান্য নিয়ম, যার মধ্যে `Principal: *`।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `wildcard(…, case_sensitive)` | `*`/`?` → regex | Action ও resource-এর ভিন্ন নিয়ম |
| Deny পেলেই return | Explicit deny জেতে | Documentation-এর নিয়ম |
| `allow_by` মনে রাখা, শেষে সিদ্ধান্ত | সব statement দেখা | পরে Deny থাকতে পারে |
| `condition_ok` — key নেই → মিথ্যা, `IfExists` → সত্য | AWS-এর আচরণ | MFA-এর deny নিরাপদ default |
| `reason` | কোন Sid সিদ্ধান্ত দিল | Debug ও audit |
| `ESCALATION` set | পরিচিত escalation action | `iam:PassRole` ইত্যাদি |
| NotAction-এর বাদের তালিকা দেখা | Admin কিনা নির্ণয় | Section 9.3 |
| Exit = worst (lint) | CI-তে policy review | Module 11/19 |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `policy_eval.py taskflow-app.json --requests requests.json` | ৯টি ✓, exit ০ |
| `policy_lint.py taskflow-app.json` | `ok` |
| `policy_lint.py dev-admin.json` | ২টি CRIT, ১টি WARN, exit ২ |
| `python3 -m unittest -v` | `Ran 8 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom / ভুল | কারণ | সমাধান |
|---|---|---|
| "AccessDenied", কিন্তু policy-তে action আছে | Resource ARN ভুল (bucket বনাম `bucket/*`) | `ListBucket` → bucket ARN; `GetObject` → object ARN |
| Allow আছে, তবুও deny | কোথাও explicit deny (SCP, boundary, অন্য policy) | সব স্তর দেখুন |
| MFA থাকা সত্ত্বেও deny | Long-lived key-এর call-এ MFA context নেই | Role + MFA-সহ session |
| "সব কাজ করাতে" `*` দেওয়া | দ্রুত সমাধান | Access log থেকে প্রয়োজনীয় action |
| App-এ access key | Key ফাঁস, rotation কঠিন | Role / instance profile |
| CI-তে admin key | Pipeline compromise = account compromise | OIDC + সীমিত role (Module 11) |
| প্রাক্তন কর্মীর access চালু | Offboarding নেই | SSO + নিয়মিত access review |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Least privilege; role, key নয়।
  - মানুষের জন্য SSO + MFA।
  - Root account শুধু জরুরি অবস্থায় (Module 08)।
  - IAM-এর অনুমতিকে admin-এর সমান ধরুন।
  - নিয়মিত access review; audit log (CloudTrail) চালু রাখুন।
  - Policy-কে code হিসেবে রাখুন, PR-এ lint (Module 12/19)।
- **Performance:** IAM evaluation-এর খরচ নগণ্য। কিন্তু temporary credential-এর নবায়ন ব্যর্থ হলে app থেমে যায় — SDK-এর credential chain বুঝুন।
- **Cost:** অতিরিক্ত অনুমতির সবচেয়ে বড় খরচ incident-এ: চুরি-যাওয়া credential দিয়ে বড় instance চালানো (crypto mining)। Budget alert (L07-06) ও অপ্রয়োজনীয় region বন্ধ রাখা (SCP) এর বিরুদ্ধে সুরক্ষা।

## 14. Hands-on exercise

1. `taskflow-app.json`-এ একটি নতুন প্রয়োজন যোগ করুন: app নিজের log একটি নির্দিষ্ট log group-এ লিখবে। ন্যূনতম action ও resource কী? `requests.json`-এ allow ও deny দুই ধরনের request যোগ করে যাচাই করুন।
2. `dev-admin.json`-কে নিরাপদ developer policy-তে বদলান — dev account-এ EC2, S3 (নির্দিষ্ট bucket-prefix), log পড়া; IAM নয়। Lint পরিষ্কার হলো কি?
3. `policy_eval.py`-তে resource policy সমর্থন যোগ করুন (bucket policy-র Principal): একই account-এ identity বা resource policy-র যেকোনো একটি allow করলেই allow, কিন্তু যেকোনো deny জেতে।
4. Escalation-এর পথ নিয়ে পড়ুন: `iam:PassRole` + `ec2:RunInstances` দিয়ে কীভাবে admin হওয়া যায়? `policy_lint.py`-এ এই জোড়া শনাক্ত করার নিয়ম যোগ করুন।
5. একটি GitHub Actions workflow-এর জন্য OIDC trust policy-র রূপ documentation থেকে লিখুন — শুধু একটি repository ও `main` branch assume করতে পারবে।

## 15. Mini-project — Policy review bot

`policy_review.py policies/`:

- একটি directory-র সব policy lint।
- প্রতিটি policy-র জন্য "প্রয়োজনীয় request" তালিকা (`requests.json`) থাকলে `policy_eval` দিয়ে যাচাই — প্রয়োজনীয় সব allow, নিষিদ্ধ সব deny।
- Markdown report, PR comment-এর উপযোগী।

Module 12-এর Terraform PR ও Lab 07-C-এ ব্যবহার হবে।

## 16. Interview প্রশ্ন

1. Least privilege কী? বাস্তবে কীভাবে প্রয়োগ করবেন?
2. IAM policy evaluation-এর ক্রম ব্যাখ্যা করুন।
3. User ও role-এর পার্থক্য কী? App কেন role ব্যবহার করবে?
4. `iam:PassRole` কেন বিপজ্জনক?
5. `NotAction`-এর ঝুঁকি কী?
6. একটি access key ফাঁস হলে প্রথম তিনটি কাজ কী?

## 17. Self-assessment প্রশ্ন

1. Key card analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর policy কেন কার্যত admin?
3. `BoolIfExists` ও `Bool`-এর পার্থক্য MFA-এর ক্ষেত্রে কী?
4. `ListBucket` ও `GetObject`-এর resource ARN কেন আলাদা?
5. Lint-এর ফাঁক কীভাবে ধরা পড়ল?

## 18. সংক্ষিপ্ত সারাংশ

- Default deny; Allow দরকার; explicit Deny সব কিছুর ওপরে।
- নির্দিষ্ট action, নির্দিষ্ট resource, শর্ত — least privilege।
- IAM-এর অনুমতি = admin; `iam:PassRole` ও `NotAction` ঝুঁকিপূর্ণ।
- App ও CI-তে role ও temporary credential; মানুষের জন্য SSO + MFA।
- Policy-কে code হিসেবে review, lint ও test করুন।

## 19. Completion checklist

- [ ] `policy_eval.py`-এ ১০টি request-এর সিদ্ধান্ত আগে অনুমান করে মিলিয়েছি
- [ ] `dev-admin.json`-কে নিরাপদ policy-তে বদলেছি
- [ ] Privilege escalation-এর তিনটি পথ বলতে পারি
- [ ] `python3 -m unittest -v`-এ ৮টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS IAM — Policy evaluation logic: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- AWS IAM — IAM JSON policy elements reference: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements.html
- AWS IAM — Condition operators (`…IfExists`): https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_elements_condition_operators.html
- AWS IAM — Security best practices: https://docs.aws.amazon.com/IAM/latest/UserGuide/best-practices.html
- AWS IAM Access Analyzer: https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html
- Google Cloud — IAM overview: https://cloud.google.com/iam/docs/overview
- Microsoft Learn — Azure RBAC: https://learn.microsoft.com/en-us/azure/role-based-access-control/overview

---

**পরের lesson:** L07-06 — Cloud cost model, budget, tagging ও cleanup
