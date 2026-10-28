# L08-03 — IAM: policy, role, instance profile

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L07-05 — IAM ও least privilege](../07-cloud-fundamentals/L07-05-iam-least-privilege.md), [L08-02 — CLI ও credential](L08-02-aws-cli-profiles-temporary-credentials-boto3.md) |
| **Label** | 💰 আসল AWS account — IAM role ও policy নিজে চার্জমুক্ত; role ব্যবহারকারী resource (EC2) চার্জযোগ্য (L08-06) |
| **Tested** | `trust_policy_lint.py`: ৬টি test পাস (Python 3.14.5, Windows)। Role file **হাতে তৈরি** — `aws iam get-role`-এর রূপে, account কাল্পনিক। GitHub OIDC-এর condition key GitHub ও AWS documentation অনুযায়ী। **আসল AWS-এ role বানানো বা `get-role` চালানো হয়নি।** Permission-এর অংশ L07-05-এর সরল evaluator দিয়ে; IAM policy simulator-এ মেলানো হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- Policy-র ধরন: AWS managed, customer managed, inline; identity-based বনাম resource-based।
- **Role-এর দুই অংশ:** trust policy (কে role নিতে পারে) ও permission policy (role কী করতে পারে)।
- Instance profile: EC2-কে role দেওয়ার পাত্র; IMDS থেকে অস্থায়ী credential।
- `iam:PassRole` — কেন EC2 চালু করতে এটা লাগে, এবং কেন সীমিত রাখতে হয় (L07-05)।
- Cross-account trust ও ExternalId; GitHub Actions OIDC trust-এর `sub` condition।
- Access Analyzer-এর policy validation।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

TaskFlow EC2-এ চলবে এবং S3-এ upload রাখবে। পুরোনো উপায় ছিল একটি IAM user-এর access key `.env`-এ রাখা। ফল:

- Key server-এর disk-এ, AMI-তে, backup-এ, log-এ।
- Rotation করতে হয় হাতে, এবং করা হয় না।
- কোন server key ব্যবহার করছে, বোঝা যায় না।

**Role + instance profile:** server-এ কোনো key নেই। EC2 নিজে থেকে কয়েক ঘণ্টার মেয়াদের credential পায় এবং মেয়াদের আগে নবায়ন হয়। CI-এর জন্যও একই নীতি — GitHub Actions OIDC দিয়ে key ছাড়া role।

কিন্তু role-এর দরজা (trust policy) ভুল হলে key-এর চেয়েও বড় বিপদ। সবচেয়ে পরিচিত উদাহরণ: GitHub OIDC trust-এ `sub` condition নেই, ফলে **GitHub-এর যেকোনো repo** আপনার role নিতে পারে।

## 3. সহজ ভাষায় পরিচয়

| অংশ | প্রশ্ন | কোথায় লেখা |
|---|---|---|
| Trust policy | **কে** এই role হতে পারে? | Role-এর `AssumeRolePolicyDocument` |
| Permission policy | Role হয়ে **কী** করা যায়? | Role-এ attached managed বা inline policy |
| Permission boundary | সর্বোচ্চ কতটা পর্যন্ত (ঊর্ধ্বসীমা)? | Role/user-এ ঐচ্ছিক |
| Instance profile | কোন role EC2-কে দেওয়া হবে? | আলাদা IAM resource, ঠিক একটি role |

| Policy-র ধরন | বৈশিষ্ট্য |
|---|---|
| AWS managed (`ReadOnlyAccess`) | AWS রক্ষণাবেক্ষণ করে; প্রায়ই বেশি চওড়া |
| Customer managed | আপনার; version থাকে, একাধিক role-এ ব্যবহার |
| Inline | একটি role-এর সাথে বাঁধা; role মুছলে মোছে |
| Resource-based (S3 bucket policy, KMS key policy) | Resource-এর গায়ে; সেখানে `Principal` থাকে |

**Linux-এর তুলনা:**

- Role = একটি service account (L01-04)।
- Trust policy = `/etc/sudoers`-এর "কে এই user-এ `sudo -u` করতে পারবে"।
- Permission policy = সেই user-এর file permission।
- Instance profile = systemd unit-এর `User=` (L01-10) — process নিজে থেকে সেই পরিচয় পায়।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের ডিউটি-কার্ড

- **Role** = "রাতের নার্স"-এর ডিউটি-কার্ড; কার্ডে লেখা কোন ঘরে ঢোকা যায় (permission)।
- **Trust policy** = কার্ড কে নিতে পারবে — শুধু এই হাসপাতালের নিবন্ধিত নার্স।
- **Instance profile** = ওয়ার্ডের দেয়ালে লাগানো কার্ড-হোল্ডার — ওয়ার্ডে যে যন্ত্র বসানো হবে, সে কার্ড পায়।
- **ExternalId** = বাইরের ঠিকাদারের জন্য গোপন চুক্তি-নম্বর।

### Analogy কোথায় মেলে না

- **ভুল লোক কার্ড নিলে গার্ড দেখে।** AWS-এ trust policy-তে `"Principal": "*"` বা condition-হীন OIDC থাকলে কোনো মানুষ পাহারা দেয় না — শর্ত মিললেই credential।
- **কার্ড এক জায়গায় থাকে।** Instance profile-এর credential IMDS থেকে যেকোনো process পড়তে পারে, যে server-এ চলে। SSRF bug থাকলে বাইরের আক্রমণকারীও পড়তে পারে। তাই IMDSv2 বাধ্যতামূলক (L08-06)।
- **কার্ডের ক্ষমতা কার্ডেই লেখা।** AWS-এ ফল আসে কয়েকটি policy মিলিয়ে: identity policy, resource policy, boundary, SCP, session policy। একটির Deny সব Allow-কে হারায় (L07-05)।

## 5. Real-world engineering scenario — "আমাদের role, অন্যের repo"

TaskFlow team GitHub Actions থেকে deploy করতে OIDC role `github-deploy` বানাল। একটি blog-এর trust policy copy করল, কিন্তু `sub` লাইনটি বাদ পড়েছিল ("কাজ তো করছে")। Review-তে `trust_policy_lint.py`-এর আসল output (হাতে তৈরি নমুনায়):

```text
CRITICAL  github-deploy              GitHub OIDC trust without a 'sub' condition — any repository on GitHub can assume this role
WARN      partner-audit              MaxSessionDuration 12 h — stolen session lasts that long
WARN      partner-audit              cross-account trust to 444455556666 without sts:ExternalId or aws:PrincipalOrgID (confused-deputy risk for third parties)
no findings: taskflow-app
3 role(s): 1 critical, 2 warning(s)
```

**কেন critical:** GitHub-এর OIDC token-এর `aud` প্রায় সবার জন্য একই (`sts.amazonaws.com`)। শুধু `aud` যাচাই করলে যেকোনো GitHub user নিজের repo-র workflow থেকে আপনার account id ও role-এর নাম দিয়ে assume করতে পারে। নিজের repo চিহ্নিত করে শুধু `sub`।

**সমাধান:** [`trust-github-pinned.json`](code/L08-03/sample/trust-github-pinned.json) — `sub = repo:YOUR-ORG/taskflow:environment:production`। এতে নির্দিষ্ট repo-র production environment ছাড়া কেউ পারে না।

## 6. Diagram — EC2 কীভাবে credential পায়

```text
 IAM role "taskflow-app"
   ├─ trust:      Principal.Service = ec2.amazonaws.com   ◄── কে নিতে পারে
   └─ permission: s3:GetObject/PutObject on taskflow-uploads/u/*   ◄── কী করতে পারে (L07-05)
        │
 instance profile "taskflow-app"  (ঠিক ১টি role)
        │   aws ec2 run-instances --iam-instance-profile Name=taskflow-app
        │   └─ এই call-এর caller-এর লাগে iam:PassRole on role/taskflow-app
        ▼
 EC2 instance ──► IMDSv2  http://169.254.169.254/latest/meta-data/iam/security-credentials/taskflow-app
                    └─ ASIA… + secret + token, মেয়াদের আগে নবায়ন  ──► boto3/CLI নিজে থেকে নেয় (L08-02 chain-এর শেষ ধাপ)
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Trust policy | Role-এর resource policy — কোন principal `sts:AssumeRole*` করতে পারবে |
| Principal | AWS account/user/role, service (`ec2.amazonaws.com`), বা federated (OIDC/SAML) |
| Instance profile | EC2-কে role দেওয়ার পাত্র |
| `iam:PassRole` | একটি role কোনো service-কে "দেওয়ার" অনুমতি |
| ExternalId | তৃতীয় পক্ষের cross-account role-এ confused deputy প্রতিরোধ |
| `aws:PrincipalOrgID` | শুধু নিজের Organization-এর principal |
| OIDC federation | বাইরের identity (GitHub) token দিয়ে key ছাড়া role |
| Permission boundary | Identity-র সর্বোচ্চ সম্ভাব্য permission |
| Access Analyzer | Policy যাচাই ও বাইরের access খোঁজার AWS সেবা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Assume করতে দুই দিকের অনুমতি

একই account-এ একটি user role নিতে চাইলে:

1. **Trust policy** সেই user-কে, বা পুরো account-কে (`arn:aws:iam::ACCOUNT:root`), allow করে।
2. Trust-এ পুরো account থাকলে, user-এর নিজের policy-তেও `sts:AssumeRole` লাগে।

তাই `…:root` trust মানে "এই account-এর যাকে নিজের policy অনুমতি দেয়" — সবাই নয়। Linter এটাকে INFO দেয়, ঝুঁকি নয়। অন্য account-এর ক্ষেত্রে দুই account-ই অনুমতি দিতে হয়।

### 8.2 Confused deputy ও ExternalId

একটি SaaS vendor অনেক গ্রাহকের role assume করে। আক্রমণকারী vendor-কে আপনার role ARN দিলে vendor ভুল করে আপনার account-এ ঢুকতে পারে। প্রতিটি গ্রাহকের আলাদা ExternalId এটা থামায়। নিজের Organization-এর ভেতরে `aws:PrincipalOrgID` বিকল্প।

### 8.3 Instance profile ও IMDS

- Console-এ EC2-এর role বানালে একই নামের instance profile নিজে তৈরি হয়। CLI-তে আলাদা ধাপ লাগে।
- Instance-এর ভেতরে SDK নিজে IMDS থেকে credential নেয়।
- IMDSv2-এ আগে `PUT` দিয়ে session token নিতে হয়। এতে সাধারণ SSRF (শুধু GET) আটকায় — L08-06।

### 8.4 PassRole

`run-instances --iam-instance-profile` চালাতে caller-এর লাগে `iam:PassRole` on সেই role। `Resource: "*"` হলে যেকোনো role — admin role-ও — নতুন instance-এ বসিয়ে তার ক্ষমতা নেওয়া যায় (L07-05, Lab 07-C)।

> **Fedora-তে:** কোনো পার্থক্য নেই — AWS CLI ও JSON।

## 9. Practical demonstration

Files:

- [`code/L08-03/trust_policy_lint.py`](code/L08-03/trust_policy_lint.py)
- [`sample/`](code/L08-03/sample/) — তিনটি role, একটি instance profile (হাতে তৈরি); ব্যবহারযোগ্য [`trust-ec2.json`](code/L08-03/sample/trust-ec2.json) ও [`trust-github-pinned.json`](code/L08-03/sample/trust-github-pinned.json)
- [`test_l08_03.py`](code/L08-03/test_l08_03.py)
- Permission policy: L07-05-এর [`taskflow-app.json`](../07-cloud-fundamentals/code/L07-05/taskflow-app.json)

### 9.1 Trust lint — আসল output (হাতে তৈরি নমুনায়)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-03
python3 trust_policy_lint.py sample/role-*.json --account 111122223333 \
  --instance-profile sample/instance-profile-taskflow.json; echo "exit=$?"
```

Output Section 5-এ, `exit=1`। `partner-audit`-এর trust policy file-এ URL-encoded string — API যেভাবে দেয়। Tool দুই রূপই পড়ে (test-এ যাচাই)।

### 9.2 Role ও instance profile বানানো (আপনার account-এ — চালানো হয়নি)

```bash
P=--profile learn-admin
L705=../../../07-cloud-fundamentals/code/L07-05
python3 trust_policy_lint.py <(echo '{"Role":{"RoleName":"taskflow-app","AssumeRolePolicyDocument":'"$(cat sample/trust-ec2.json)"'}}')
aws accessanalyzer validate-policy --policy-type IDENTITY_POLICY --policy-document file://$L705/taskflow-app.json $P

aws iam create-role --role-name taskflow-app --assume-role-policy-document file://sample/trust-ec2.json \
  --tags Key=Project,Value=lab08 $P
aws iam put-role-policy --role-name taskflow-app --policy-name taskflow-app \
  --policy-document file://$L705/taskflow-app.json $P
aws iam create-instance-profile --instance-profile-name taskflow-app $P
aws iam add-role-to-instance-profile --instance-profile-name taskflow-app --role-name taskflow-app $P

aws iam get-role --role-name taskflow-app $P > role-taskflow-app.json
aws iam get-instance-profile --instance-profile-name taskflow-app $P > ip.json
python3 trust_policy_lint.py role-taskflow-app.json --instance-profile ip.json --account <ACCOUNT_ID>
```

- `validate-policy` Access Analyzer-এর syntax ও best-practice পরামর্শ দেয়।
- `taskflow-app.json`-এর bucket ও secret নাম আপনার নিজের নাম দিয়ে বদলান।
- Instance-এ এই profile লাগানো L08-06-এ।

### 9.3 নিজের account-এর সব role যাচাই

```bash
for r in $(aws iam list-roles --query 'Roles[?!starts_with(Path, `/aws-service-role/`)].RoleName' --output text $P); do
  aws iam get-role --role-name "$r" $P > "role-$r.json"
done
python3 trust_policy_lint.py role-*.json --account <ACCOUNT_ID>
```

Service-linked role (`/aws-service-role/`) AWS নিজে পরিচালনা করে, তাই বাদ দেওয়া হয়েছে।

### 9.4 লেখার সময়

- প্রথম সংস্করণে `Principal` পরীক্ষা ছিল এক লাইনের জটিল expression — `"Principal": "*"` (string) ও `{"AWS": "*"}` দুই রূপ সামলাতে গিয়ে ভঙ্গুর। এখন `principals()` helper; test-এ তিন রূপই যাচাই।
- `sub` wildcard-এর প্রথম নিয়ম `:` গুনে সিদ্ধান্ত নিত, তাই `repo:acme/taskflow:*` (যেকোনো branch/PR) ছাড় পেত। এখন যেকোনো wildcard-এ WARN; `repo:*`-এ CRITICAL।

### 9.5 Test

```bash
python3 -m unittest -v
```

৬টি test:

- নমুনার ফল।
- GitHub `sub`-এর চার রূপ (pinned → ০, branch wildcard → WARN, `repo:*` → CRITICAL, নেই → CRITICAL)।
- `Principal "*"`-এর তিন রূপ।
- নিজের বনাম অন্য account (ExternalId থাকলে ঠিক)।
- URL-encoded document।
- Instance profile-এর role-এ EC2 trust।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `trust_doc()` | String হলে `unquote` + JSON | API URL-encoded দেয়, CLI decode করে |
| `principals()` | `"*"` string → `{"AWS": "*"}` | Policy grammar-এর দুই রূপ |
| `cond_values()` | Condition key case-insensitive | AWS condition key case-insensitive |
| Own-account `:root` → INFO | ঝুঁকি নয়, তথ্য | User-এর নিজের policy-ও লাগে |
| OIDC `sub` নেই → CRITICAL | যেকোনো repo | সবচেয়ে বিপজ্জনক ভুল |
| `MaxSessionDuration > 4h` → WARN | চুরি-যাওয়া session-এর আয়ু | ছোট মেয়াদ |
| `check_instance_profile` | ঠিক ১টি role, EC2 trust | না হলে instance credential পায় না |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় lint | ১ critical, ২ warning, exit ১ |
| `trust-ec2.json`, `trust-github-pinned.json` | কোনো finding নেই |
| নিজের account-এর role-গুলো | কোনো CRITICAL নয় |
| `python3 -m unittest -v` | `Ran 6 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `MalformedPolicyDocument` on create-role | Trust-এ `Resource` লেখা, বা JSON ভুল | Trust policy-তে `Resource` থাকে না |
| `not authorized to perform: iam:PassRole` | Caller-এর PassRole নেই | নির্দিষ্ট role ARN-এ PassRole |
| Instance-এ `Unable to locate credentials` | Profile লাগানো নেই, role-এ EC2 trust নেই, বা IMDS hop limit (container) | `--instance-profile` lint; L08-06 |
| `AccessDenied` on AssumeRole (cross-account) | একদিকের অনুমতি নেই | Trust ও caller-এর policy দুটোই |
| GitHub Actions: `Not authorized to perform sts:AssumeRoleWithWebIdentity` | `sub` মেলে না (branch, environment) | Workflow-এর আসল `sub` দেখে trust ঠিক করুন — wildcard নয় |
| Role মুছতে `DeleteConflict` | Instance profile বা policy এখনো যুক্ত | আগে remove-role-from-instance-profile, delete-role-policy |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - প্রতিটি workload-এর আলাদা role; শেয়ার করা "app-role" নয়।
  - Permission policy L07-05-এর lint ও Access Analyzer দিয়ে যাচাই।
  - Trust policy এই lesson-এর lint দিয়ে।
  - অব্যবহৃত role ও permission খুঁজতে Access Analyzer বা IAM-এর "last accessed" তথ্য।
- **Performance:** SDK credential cache করে — প্রতিটি call-এ IMDS নয়। Container-এ IMDSv2-এর hop limit (L08-06)।
- **Cost:** IAM নিজে চার্জমুক্ত। Access Analyzer-এর কিছু analyzer (যেমন unused access) চার্জযোগ্য — চালুর আগে pricing দেখুন।

## 14. Hands-on exercise

1. Section 9.2 অনুযায়ী `taskflow-app` role ও instance profile বানিয়ে lint চালান।
2. নিজের GitHub repo-র জন্য `trust-github-pinned.json` লিখুন (`YOUR-ORG` বদলে)। `sub`-এর তিনটি রূপ — branch, environment, pull_request — কোনটা কখন?
3. `trust_policy_lint.py`-তে নতুন নিয়ম: `Principal.Service` থাকলে এবং সেটা `ec2.amazonaws.com` না হলে `aws:SourceAccount` condition-এর পরামর্শ (INFO)।
4. একটি role-এ permission boundary দিন যা শুধু S3 ও CloudWatch Logs অনুমতি দেয়। তারপর role-এ `AdministratorAccess` attach করে দেখান যে boundary-র বাইরের কাজ deny হয় (IAM policy simulator)।
5. Cleanup: Section 12-এর `DeleteConflict` ক্রম মেনে role ও instance profile মুছুন।

## 15. Mini-project — IAM review in CI

একটি Makefile target বা script:

1. `iam/` folder-এর সব permission policy-তে L07-05-এর `policy_lint.py`।
2. সব trust policy-তে `trust_policy_lint.py`।
3. CRITICAL থাকলে CI fail।

Module 11-এর CI pipeline ও Module 12-এর Terraform-এ যুক্ত হবে।

## 16. Interview প্রশ্ন

1. Trust policy ও permission policy-র পার্থক্য কী?
2. Instance profile কী? EC2 কীভাবে credential পায়?
3. `iam:PassRole` কেন লাগে, এবং কেন ঝুঁকিপূর্ণ?
4. GitHub Actions OIDC role-এ কোন condition বাধ্যতামূলক, এবং কেন?
5. Confused deputy সমস্যা কী? ExternalId কীভাবে সমাধান করে?
6. Inline, customer managed ও AWS managed policy — কখন কোনটা?

## 17. Self-assessment প্রশ্ন

1. ডিউটি-কার্ড analogy কোথায় মেলে না?
2. `arn:aws:iam::ACCOUNT:root` trust মানে কি account-এর সবাই role নিতে পারে?
3. Instance profile-এ কয়টি role থাকতে পারে?
4. `sub = repo:acme/taskflow:*` কেন সতর্কতা পায়?
5. Role মোছার সঠিক ক্রম কী?

## 18. সংক্ষিপ্ত সারাংশ

- Role = trust (কে) + permission (কী); দুটোই review করুন।
- EC2: instance profile → IMDSv2 → অস্থায়ী credential; server-এ কোনো key নয়।
- PassRole নির্দিষ্ট role-এ; OIDC trust-এ `aud` ও নির্দিষ্ট `sub`; তৃতীয় পক্ষের জন্য ExternalId।
- `trust_policy_lint.py` + L07-05-এর lint + Access Analyzer।

## 19. Completion checklist

- [ ] `taskflow-app` role ও instance profile তৈরি, lint-এ কোনো finding নেই
- [ ] নিজের account-এর সব role-এ কোনো CRITICAL নেই
- [ ] GitHub OIDC trust-এর `sub` নিজের repo-তে pinned
- [ ] `python3 -m unittest -v`-এ ৬টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS IAM — Roles: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles.html
- AWS IAM — Instance profiles: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_use_switch-role-ec2_instance-profiles.html
- AWS IAM — The confused deputy problem: https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html
- AWS IAM — Policy evaluation logic: https://docs.aws.amazon.com/IAM/latest/UserGuide/reference_policies_evaluation-logic.html
- GitHub Docs — Configuring OpenID Connect in Amazon Web Services: https://docs.github.com/en/actions/deployment/security-hardening-your-deployments/configuring-openid-connect-in-amazon-web-services
- IAM Access Analyzer — Policy validation: https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-policy-validation.html

---

**পরের lesson:** L08-04 — VPC design: subnet, route table, gateway
