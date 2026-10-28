# L08-02 — AWS CLI, profile, temporary credential ও boto3

| | |
|---|---|
| **Module** | 08 — AWS Core Services |
| **Difficulty** | Intermediate |
| **আনুমানিক সময়** | ২.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L08-01 — Account safety](L08-01-account-safety-root-mfa-budget.md), [L05-01 — venv ও pip](../05-python-for-infrastructure/L05-01-python-environment.md), [L05-10 — Secret](../05-python-for-infrastructure/L05-10-secrets-and-config.md) |
| **Label** | 💰 আসল AWS account — এই lesson-এর command-গুলো শুধু পড়ে (Describe/List/GetCallerIdentity); সাধারণত চার্জ হয় না, কিন্তু account-এ চলমান resource-এর বিল চলতেই থাকে |
| **Tested** | `aws_config_audit.py` ও `inventory.py`: ৭টি test পাস (Python 3.14.5, Windows)। Config file **হাতে তৈরি** (নকল key, কাল্পনিক account)। `inventory.py` একটি **নকল boto3 session** দিয়ে পরীক্ষিত — boto3 এই machine-এ নেই, API-র রূপ boto3 documentation অনুযায়ী লেখা; **আসল AWS-এ চালানো হয়নি।** Credential precedence-এর মডেল AWS CLI user guide-এর সরল রূপ। |

---

## 1. এই lesson-এ যা শিখবেন

- AWS CLI v2: install, `--query`, `--output`, region।
- `~/.aws/config` ও `~/.aws/credentials`-এর গঠন: profile, `sso-session`, `role_arn`/`source_profile`।
- **দীর্ঘমেয়াদি key বনাম অস্থায়ী credential** — `AKIA…` বনাম `ASIA…` + session token।
- IAM Identity Center (SSO) দিয়ে CLI login: `aws configure sso`, `aws sso login`।
- Credential কোথা থেকে আসে (precedence) — এবং কেন env-এর একটি পুরোনো key অবাক করে।
- boto3: session, client, paginator; একটি read-only inventory script।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

L08-01-এর পরে console-এ নিরাপদে ঢোকা যায়। কিন্তু automation (script, CI, Terraform) চলে API দিয়ে, আর API-র জন্য credential লাগে। পরিচিত ভুল:

- Laptop-এর `~/.aws/credentials`-এ বছর-পুরোনো admin key; laptop চুরি বা backup ফাঁস হলেই account উন্মুক্ত।
- Terminal-এ আগের কাজের `AWS_ACCESS_KEY_ID` রয়ে গেছে; `--profile` না দিয়ে command চালানোয় **ভুল account-এ** resource মুছে গেল।
- Profile-এ region নেই; resource গেল `us-east-1`-এ, খোঁজার সময় পাওয়া গেল না — কিন্তু বিল চলছে।
- Script প্রথম page-এর ১০০০টি object দেখে "সব দেখেছি" ভাবল (pagination ভুলে যাওয়া)।

## 3. সহজ ভাষায় পরিচয়

| Credential | চেহারা | মেয়াদ | কোথায় |
|---|---|---|---|
| IAM user access key | `AKIA…` + secret | যতদিন না মোছেন | এড়িয়ে চলুন |
| অস্থায়ী (STS) credential | `ASIA…` + secret + **session token** | মিনিট থেকে ঘণ্টা | SSO, assume-role, instance profile |
| SSO (Identity Center) | browser-এ login → cache-এ token | session শেষে নতুন login | মানুষের CLI কাজ |

**Profile** = একটি নামযুক্ত setting-এর সমষ্টি (credential-এর উৎস, region, output)। `--profile NAME` বা `AWS_PROFILE=NAME`।

**Linux-এর তুলনা:** `sudo` একবার password নিয়ে কিছুক্ষণ (ডিফল্ট ১৫ মিনিট) মনে রাখে, তারপর আবার চায় — অস্থায়ী credential-ও তেমন। আর `root`-এর password একটি file-এ লিখে রাখা = `~/.aws/credentials`-এ admin key।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### অফিসের ভিজিটর কার্ড

- **Access key** = অফিসের স্থায়ী চাবির copy — যে পায় সে-ই ঢোকে, যতদিন না তালা বদলান।
- **অস্থায়ী credential** = reception থেকে নেওয়া দিনের ভিজিটর কার্ড — সন্ধ্যায় নিজে থেকেই অকেজো।
- **SSO login** = প্রতিদিন সকালে পরিচয়পত্র দেখিয়ে নতুন কার্ড নেওয়া।
- **Assume role** = নিজের কার্ড দেখিয়ে নির্দিষ্ট কাজের জন্য আলাদা কার্ড নেওয়া (যেমন server room)।

### Analogy কোথায় মেলে না

- **ভিজিটর কার্ড হারালে কেউ জানবে।** অস্থায়ী credential copy হলেও মেয়াদ পর্যন্ত পুরোপুরি বৈধ — log-এ বা env-এ ফাঁস হলে সেই সময়টুকু ঝুঁকি থাকে। মেয়াদ ছোট রাখাই সুরক্ষা।
- **কার্ড একটাই, পকেটে।** একই terminal-এ env variable, profile file, SSO cache — তিনটি জায়গায় একসাথে credential থাকতে পারে। CLI একটি নির্দিষ্ট ক্রমে বেছে নেয় (Section 8.2); সেটা না জানলে ভুল account-এ কাজ হয়।
- **দরজা একটাই।** AWS-এ প্রতিটি region আলাদা; ভুল region-এ চালানো command ভুল দরজায় যায়, এবং "কিছু নেই" দেখায়।

## 5. Real-world engineering scenario — "কোন account-এ চালালাম?"

একজন engineer sandbox-এ cleanup script চালাতে চাইলেন। আগের দিন production debug করতে terminal-এ `export AWS_ACCESS_KEY_ID=…` দিয়েছিলেন; সেই shell তখনো খোলা। Script-এ `--profile` ছিল না।

**কী হলো:** CLI ও boto3 env-এর key আগে নেয়, তাই production-এর resource তালিকা এল এবং মোছার প্রস্তাব হলো। ভাগ্যক্রমে script-এ dry-run ছিল।

**প্রতিরোধ:**

1. প্রতিটি automation শুরুতে `aws sts get-caller-identity` চালিয়ে account id মেলাবে, না মিললে থামবে (L08-12-এর cleanup script তাই করে)।
2. দীর্ঘমেয়াদি key নয় — SSO profile; env-এ key রাখা নয়।
3. `aws_config_audit.py` env-এ key থাকলে সতর্ক করে:

   ```text
   WARN   (env)                AWS_ACCESS_KEY_ID ASIA…WXYZ is set — it overrides AWS_PROFILE and the files unless --profile is given
   ```

   (এই লাইনটি code-এর বার্তার উদাহরণ; নমুনা run-এ env-এ key ছিল না।)

## 6. Diagram — CLI/boto3 credential কোথা থেকে নেয় (সরল)

```text
 aws s3 ls  /  boto3.client("s3")
   │
   ├─ 1. command line: --profile X          ── থাকলে সেই profile
   ├─ 2. env: AWS_ACCESS_KEY_ID (+SECRET, +SESSION_TOKEN)
   ├─ 3. profile (AWS_PROFILE বা default) ─┬─ role_arn → STS AssumeRole (source_profile থেকে) → ASIA…
   │                                       ├─ sso_session → ~/.aws/sso/cache-এর token → ASIA…
   │                                       └─ credentials file-এর key (AKIA… বা ASIA…+token)
   └─ 4. container credential / EC2 instance profile (IMDS) → ASIA…   (L08-03, L08-06)
```

পূর্ণ তালিকা AWS CLI user guide-এ (Section 20); এটা শেখার জন্য সরল রূপ।

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Profile | নামযুক্ত setting-এর সমষ্টি (`[profile X]` config-এ, `[X]` credentials-এ) |
| STS | Security Token Service — অস্থায়ী credential দেয় |
| Session token | অস্থায়ী credential-এর তৃতীয় অংশ; ছাড়া call ব্যর্থ |
| AssumeRole | একটি role-এর অস্থায়ী credential নেওয়া |
| `source_profile` | Role assume করতে কোন profile-এর credential ব্যবহার হবে |
| `sso-session` | Identity Center-এর login setting, একাধিক profile ভাগ করে |
| JMESPath / `--query` | CLI output থেকে অংশ বেছে নেওয়ার ভাষা |
| Paginator | বহু page-এর API ফল এক এক করে আনার boto3 সুবিধা |
| ARN | Amazon Resource Name — `arn:aws:service:region:account:resource` |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 দুটি file

- `~/.aws/config`: `[default]`, `[profile NAME]`, `[sso-session NAME]` — region, output, role, SSO।
- `~/.aws/credentials`: `[NAME]` — শুধু key (এখানে `profile ` prefix নেই)।

একটি named profile `[default]`-এর setting **উত্তরাধিকারসূত্রে পায় না**। তাই প্রতিটি profile-এ `region` লিখুন। `aws_config_audit.py` region-হীন profile-এ WARN দেয়।

### 8.2 Precedence-এর ফাঁদ

`--profile` দিলে সেই profile-ই ব্যবহার হয়। না দিলে env-এর `AWS_ACCESS_KEY_ID` জেতে — `AWS_PROFILE` set থাকলেও। `aws_config_audit.py --which` এই সরল মডেল দেখায়, এবং test-এ তিনটি ক্ষেত্র যাচাই করা আছে।

### 8.3 অস্থায়ী credential-এর জীবন

- AssumeRole-এর ডিফল্ট মেয়াদ এক ঘণ্টা; role-এর maximum session duration পর্যন্ত বাড়ানো যায়।
- CLI ও boto3 role profile-এর credential cache করে এবং মেয়াদ শেষে আবার নেয়।
- SSO-র login session শেষ হলে `aws sso login` আবার লাগে।
- `ASIA…` key-এর সাথে session token না থাকলে প্রতিটি call ব্যর্থ — audit এটাকে ERROR দেয়।

### 8.4 boto3

- `boto3.Session(profile_name=…)` একই credential chain ব্যবহার করে।
- `session.client("ec2", region_name=…)` region-নির্দিষ্ট; S3-এর `list_buckets` account-ব্যাপী।
- বহু-page API-তে **paginator** ব্যবহার করুন — নইলে শুধু প্রথম page আসে। Test-এ দুই page-এর instance যাচাই করা আছে।
- `describe_regions` ডিফল্টে শুধু চালু (enabled) region দেয়।

> **Fedora-তে:** AWS-এর official installer দুই distro-তেই একই। Fedora repo-তে `awscli2` package-ও আছে — version পুরোনো হতে পারে, `aws --version` দেখুন।

## 9. Practical demonstration

Files:

- [`code/L08-02/aws_config_audit.py`](code/L08-02/aws_config_audit.py)
- [`inventory.py`](code/L08-02/inventory.py)
- [`sample/config`](code/L08-02/sample/config), [`sample/credentials`](code/L08-02/sample/credentials) — হাতে তৈরি, নকল মান
- [`test_l08_02.py`](code/L08-02/test_l08_02.py)

### 9.1 AWS CLI ও SSO (আপনার machine-এ — চালানো হয়নি)

AWS CLI v2 install করুন official guide অনুযায়ী (Section 20), তারপর:

```bash
aws --version
aws configure sso                    # sso-session নাম, start URL, region; browser-এ login; account ও role বাছাই
aws sso login --profile learn-admin
aws sts get-caller-identity --profile learn-admin
```

শেষ command-এর উত্তরে `Account` ও `Arn` থাকে। Identity Center-এর role হলে Arn-এ `assumed-role/AWSReservedSSO_…` দেখা যায়। `inventory.py`-র `arn_kind()` এটাই চেনে (test-এ যাচাই)।

Identity Center না থাকলে L08-01-এর IAM admin user দিয়ে `aws configure` — এটা দীর্ঘমেয়াদি key বানায়। শুধু শেখার account-এ, MFA-সহ, এবং পরে মুছে ফেলার পরিকল্পনা নিয়ে ব্যবহার করুন।

### 9.2 `--query` ও `--output`

```bash
aws ec2 describe-regions --query 'Regions[].RegionName' --output text --profile learn-admin
aws ec2 describe-instances --query 'Reservations[].Instances[].[InstanceId,State.Name]' --output table --profile learn-admin
```

### 9.3 Config audit — আসল output (হাতে তৈরি নমুনায়)

```bash
cd ~/devops-ai-engineering/08-aws-core-services/code/L08-02
python3 aws_config_audit.py --config sample/config --credentials sample/credentials; echo "exit=$?"
```

```text
ERROR  broken-chain         source_profile 'does-not-exist' does not exist
ERROR  half-sso             SSO profile missing sso_account_id
ERROR  temp-without-token   temporary key ASIA…0002 without aws_session_token — every call will fail
WARN   broken-chain         no region — not inherited from [default]; uses AWS_REGION/AWS_DEFAULT_REGION or fails
WARN   deployer             no region — not inherited from [default]; uses AWS_REGION/AWS_DEFAULT_REGION or fails
WARN   half-sso             no region — not inherited from [default]; uses AWS_REGION/AWS_DEFAULT_REGION or fails
WARN   old-keys             long-lived access key AKIA…0001 — prefer SSO or an assumed role
INFO   deployer             role requires MFA (mfa_serial) — good for powerful roles
5 profile(s), 2 credential section(s): 3 error(s), 4 warning(s)
exit=1
```

```bash
python3 aws_config_audit.py --config sample/config --credentials sample/credentials --which deployer
# --profile deployer: assume-role
```

Secret কখনো ছাপা হয় না; key id-ও masked (test-এ যাচাই)। নিজের machine-এ শুধু `python3 aws_config_audit.py`।

### 9.4 Inventory (আপনার account-এ — চালানো হয়নি)

```bash
python3 -m venv ~/venvs/aws && . ~/venvs/aws/bin/activate && python3 -m pip install boto3
python3 inventory.py --profile learn-admin --all-regions --summary
python3 inventory.py --profile learn-admin --regions ap-south-1 > ~/aws-setup/inventory.json
```

শুধু Describe/List call হয় — test নিশ্চিত করে যে নকল session-এ কোনো লেখার call যায়নি। নতুন account-এ প্রত্যাশা: শুধু `account … as …`, resource নেই। কিছু থাকলে সেটাই আপনার বিলের উৎস।

এই machine-এ boto3 নেই, তাই আসল আচরণ:

```text
error: boto3 is not installed — python3 -m pip install boto3 (inside a venv)
exit=2
```

### 9.5 লেখার সময়

- প্রথম সংস্করণ ধরে নিয়েছিল, profile-এ region না থাকলে `[default]`-এর region ব্যবহার হয়। AWS CLI-র নিয়মে named profile default থেকে setting পায় না, তাই এখন সব region-হীন profile-এ WARN।
- Secret scanner L08-01-এর test-এর একটি তারিখ (`password_last_used=`)-কে password ভেবেছিল। লাইনে কারণসহ `scan-secrets: allow` যোগ করা হয়েছে।

### 9.6 Test

```bash
python3 -m unittest -v
```

৭টি test:

- নমুনার ERROR ও WARN; সম্পূর্ণ SSO profile পরিষ্কার।
- Secret বা পূর্ণ key id ছাপা হয় না।
- Role chain-এর চক্র।
- Precedence-এর তিনটি ক্ষেত্র।
- Inventory-তে pagination, terminated/deleted বাদ, tag।
- শুধু read call।
- ARN-এর ধরন।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `configparser(interpolation=None)` | INI পড়ে | Secret-এ `%` থাকলে ভাঙে না |
| `mask()` | `AKIA…0001` | Log-এ পূর্ণ key id-ও নয় |
| `kind_of()` | role/sso/key ধরন | কোন পথে credential আসবে |
| Chain loop detection | `seen` set | Role-এর পর role-এর চক্র |
| `which()` | Precedence-এর সরল মডেল | ভুল account-এর দুর্ঘটনা বোঝা |
| `pages()` | Paginator | প্রথম page-এ থেমে না যাওয়া |
| `import boto3` main-এর ভেতরে | Test-এ boto3 লাগে না | নকল session inject |
| `caller_kind == "root"` হলে warning | Root-এ script নয় | L08-01 |

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| নমুনায় `aws_config_audit.py` | ৩ error, ৪ warning, exit ১ |
| নিজের `~/.aws` | ০ error; দীর্ঘমেয়াদি key থাকলে WARN |
| `aws sts get-caller-identity --profile learn-admin` | নিজের account id, root নয় |
| `inventory.py --summary` | Account ও caller kind; প্রত্যাশিত resource ছাড়া কিছু নয় |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| `Unable to locate credentials` | কোনো উৎসে credential নেই | `--profile`, `aws sso login` |
| `The SSO session associated with this profile has expired` | SSO token-এর মেয়াদ শেষ | `aws sso login --profile …` |
| `ExpiredToken` | অস্থায়ী credential পুরোনো | Env থেকে পুরোনো key সরান; নতুন login |
| `InvalidClientTokenId` | Key মুছে ফেলা হয়েছে, বা `ASIA…` key token ছাড়া | Audit চালান |
| `You must specify a region` | Profile-এ region নেই | `region = …` |
| Resource "নেই", অথচ বিল আসছে | অন্য region | `inventory.py --all-regions` |
| `AccessDenied` on `sts:AssumeRole` | Trust policy বা MFA | L08-03; `mfa_serial` থাকলে MFA code |
| Script-এ ১০০০-এর বেশি পায় না | Pagination নেই | Paginator |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - মানুষের জন্য SSO, যন্ত্রের জন্য role (L08-03)।
  - `~/.aws/credentials`-এ কিছু না রাখাই লক্ষ্য; রাখলে `chmod 600`।
  - Env-এ key রাখা shell history ও child process-এ ছড়ায়।
  - Script-এর শুরুতে `get-caller-identity` দিয়ে account মেলান।
- **Performance:**
  - Region loop ধীর — দরকারি region-এ সীমিত রাখুন, বা thread দিয়ে সমান্তরাল চালান।
  - API throttling হলে boto3 নিজে retry করে। Retry-এর ধরন config দিয়ে বদলানো যায় (`retries` setting)।
- **Cost:** Describe/List সাধারণত বিনামূল্যে। কিছু API-তে request-প্রতি চার্জ আছে (যেমন Cost Explorer — L08-12); নিয়মিত চালানোর আগে pricing দেখুন।

## 14. Hands-on exercise

1. `aws configure sso` দিয়ে দুটি profile বানান — `learn-admin` (AdministratorAccess) ও `learn-read` (ReadOnlyAccess)। দৈনন্দিন কাজে `learn-read`।
2. নিজের `~/.aws`-এ `aws_config_audit.py` চালিয়ে ০ error করুন।
3. `export AWS_ACCESS_KEY_ID=ASIAFAKE` দিয়ে `--which` চালান, তারপর `unset` করুন। ফল ব্যাখ্যা করুন।
4. `inventory.py`-তে একটি নতুন resource যোগ করুন: `describe_snapshots(OwnerIds=["self"])` — paginator সহ। Test-এর নকল session-এ data যোগ করে test লিখুন।
5. `inventory.py`-তে `--expect-account ID` যোগ করুন: caller-এর account না মিললে exit ২।

## 15. Mini-project — `aws-whoami` prompt

Shell prompt-এ বর্তমান AWS profile, account-এর শেষ চার অঙ্ক ও region দেখানোর একটি ছোট script। Env-এ key থাকলে লাল রঙে সতর্কতা। Production account হলে বিশেষ চিহ্ন। (Bash — L04; account id-গুলো একটি local file-এ।)

## 16. Interview প্রশ্ন

1. দীর্ঘমেয়াদি access key ও অস্থায়ী credential-এর পার্থক্য কী? কোনটা কখন?
2. AWS CLI কোন ক্রমে credential খোঁজে? একটি ফাঁদের উদাহরণ দিন।
3. `source_profile` ও `role_arn` দিয়ে role assume কীভাবে কাজ করে?
4. boto3-এ paginator কেন দরকার?
5. Script কীভাবে নিশ্চিত হবে যে সঠিক account-এ চলছে?

## 17. Self-assessment প্রশ্ন

1. ভিজিটর-কার্ড analogy কোথায় মেলে না?
2. `ASIA…` key-এর সাথে আর কী লাগে?
3. Named profile-এ region না থাকলে কী হয়?
4. `--profile` ও `AWS_ACCESS_KEY_ID` একসাথে থাকলে কোনটা জেতে?
5. `inventory.py` কোন কোন API call করে, এবং কেন ReadOnlyAccess যথেষ্ট?

## 18. সংক্ষিপ্ত সারাংশ

- মানুষ: SSO profile; যন্ত্র: role। দীর্ঘমেয়াদি key এড়িয়ে চলুন।
- প্রতিটি profile-এ region; env-এর key profile-কে চাপা দেয়।
- Script শুরুতে `get-caller-identity`; boto3-এ paginator।
- `aws_config_audit.py` দিয়ে local file-এর অবস্থা যাচাই, `inventory.py` দিয়ে account-এর।

## 19. Completion checklist

- [ ] AWS CLI v2 install, SSO profile দিয়ে `get-caller-identity`
- [ ] নিজের `~/.aws`-এ audit-এ ০ error
- [ ] `inventory.py --all-regions --summary` চালিয়ে কোনো অপ্রত্যাশিত resource নেই
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- AWS CLI — Install: https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html
- AWS CLI — Configuration and credential files: https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html
- AWS CLI — IAM Identity Center (SSO): https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-sso.html
- AWS CLI — Authentication and credential precedence: https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-authentication.html
- AWS IAM — Temporary security credentials: https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_temp.html
- boto3 — Credentials: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html
- boto3 — Paginators: https://boto3.amazonaws.com/v1/documentation/api/latest/guide/paginators.html

---

**পরের lesson:** L08-03 — IAM: policy, role, instance profile
