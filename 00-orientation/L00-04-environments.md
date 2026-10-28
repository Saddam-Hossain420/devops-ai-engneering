# L00-04 — Environments: development, testing, staging, production

| | |
|---|---|
| **Module** | 00 — Engineering Orientation |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ২–৩ ঘণ্টা |
| **পূর্বশর্ত** | [L00-03 — SDLC, Agile, Scrum, Kanban ও release management](L00-03-sdlc-agile-release.md) |
| **Label** | — |
| **Tested** | Python code: Python 3.14-এ ১১টি test পাস; `show`, `diff`, `validate` command চালিয়ে output যাচাই (Git Bash)। Ubuntu-তে চালানো হয়নি (শুধু standard library)। |

---

## 1. এই lesson-এ যা শিখবেন

- **Environment** কী এবং কেন development, testing, staging, production আলাদা রাখা হয়।
- **Promotion:** একই artifact কীভাবে এক environment থেকে পরের environment-এ যায়।
- **Environment parity** — environment-গুলো কতটা একই রকম হওয়া উচিত, কোথায় পার্থক্য স্বাভাবিক।
- **Configuration ও code আলাদা রাখা** (Twelve-Factor App-এর নীতি)।
- Secret কেন file-এ নয়, environment variable বা secret store-এ।
- Python দিয়ে layered configuration loader তৈরি: base → environment file → environment variable, সাথে production safety rule ও environment-এর মধ্যে diff।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

ধরুন আপনি সরাসরি live WordPress site-এ plugin update বা code পরিবর্তন করলেন। কিছু ভাঙলে **আসল customer** সেটা দেখবেন, sale হারাবেন, data নষ্ট হতে পারে। আপনার WordPress অভিজ্ঞতায় সম্ভবত এমন হয়েছে — "live-এ ঠিক করতে গিয়ে site ভেঙে গেছে।"

Environment আলাদা রাখার মূল উদ্দেশ্য: **পরিবর্তন production-এ পৌঁছানোর আগে কম ঝুঁকির জায়গায় যাচাই করা।**

কিন্তু শুধু আলাদা environment থাকলেই হয় না। নতুন সমস্যাও আসে:

- "Staging-এ তো চলছিল!" — কারণ staging আর production-এর configuration বা version আলাদা ছিল।
- Production-এর database password ভুল করে staging-এর config file-এ commit হয়ে গেল।
- Production-এ `DEBUG=true` রয়ে গেল — error page-এ internal তথ্য প্রকাশ পেল।

এই lesson শেখায় কীভাবে environment আলাদা রাখবেন, অথচ **যা গুরুত্বপূর্ণ তা একই রাখবেন**।

## 3. সহজ ভাষায় পরিচয়

**Environment কী?** একটি application চালানোর জন্য সম্পূর্ণ পরিবেশ — server, configuration, database, network, external service — যেখানে নির্দিষ্ট উদ্দেশ্যে software চলে।

| Environment | উদ্দেশ্য | কে ব্যবহার করে | Data |
|---|---|---|---|
| **Development (dev)** | Code লেখা ও দ্রুত পরীক্ষা | Developer (প্রায়ই নিজের laptop) | নকল/ছোট sample data |
| **Testing / CI** | Automated test চালানো | CI pipeline | প্রতিবার নতুন তৈরি test data |
| **Staging** | Production-এর মতো পরিবেশে শেষ যাচাই | QA, product team, release verification | Production-এর মতো, কিন্তু আসল personal data নয় |
| **Production (prod)** | আসল user-এর জন্য service | Customer | আসল data |

কখনো আরো থাকে: **QA**, **UAT** (User Acceptance Testing — customer নিজে যাচাই করেন), **preview environment** (প্রতিটি pull request-এর জন্য আলাদা অস্থায়ী environment)।

**কেন তৈরি হয়েছিল?** Production-এ সরাসরি পরীক্ষা করা বিপজ্জনক। তাই ধাপে ধাপে ঝুঁকি বাড়ে এমন পথ: dev (সবচেয়ে কম ঝুঁকি) → test → staging → prod (সবচেয়ে বেশি ঝুঁকি)।

**এটি না থাকলে কী হতো?** প্রতিটি ভুল user-এর কাছে পৌঁছাত। অথবা উল্টোটা — ভয়ে কেউ পরিবর্তনই করত না।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### নাটকের মহড়া

- **Development:** অভিনেতা নিজের ঘরে একা সংলাপ মুখস্থ করছেন। ভুল হলে কেউ দেখে না।
- **Testing:** পরিচালক প্রতিটি দৃশ্য আলাদা করে পরীক্ষা করছেন — সংলাপ ঠিক আছে কিনা।
- **Staging — Dress rehearsal:** আসল মঞ্চে, আসল পোশাক, আলো, শব্দ সহ পূর্ণ মহড়া — শুধু দর্শক নেই।
- **Production:** দর্শকের সামনে আসল প্রদর্শনী।

Dress rehearsal-এ যদি অন্য মঞ্চ, অন্য আলো ব্যবহার হয়, তাহলে আসল দিনে নতুন সমস্যা দেখা দেবে — এটাই **environment parity**-র গুরুত্ব।

### Analogy কোথায় মেলে না

- নাটকে প্রতিটি প্রদর্শনী আলাদা। Software-এ production **একটানা চলছে** — নতুন version-কে চলমান অবস্থায় বদলাতে হয়, দর্শক বসে থাকা অবস্থায় মঞ্চ বদলানোর মতো। তাই rolling/blue-green deployment লাগে (Module 11)।
- মহড়ায় দর্শকের আচরণ পরীক্ষা করা যায় না। Software-এ staging-এ **আসল traffic-এর পরিমাণ ও ধরন** প্রায় কখনো পুরোপুরি থাকে না — তাই কিছু সমস্যা শুধু production-এ ধরা পড়ে। এজন্য canary deployment ও monitoring দরকার।
- নাটকের মঞ্চ একই থাকে। Cloud-এ environment code দিয়ে তৈরি হয় (Terraform, Module 12) — পুরো environment মুছে আবার একইভাবে তৈরি করা যায়।

## 5. Real-world engineering scenario — "Staging-এ তো চলছিল!"

**পরিস্থিতি:** একটি SaaS কোম্পানি নতুন report feature release করছে। Staging-এ সব test পাস। Production-এ deploy-এর ১০ মিনিট পরে API-র অর্ধেক request timeout।

**জড়িত component:** API server, PostgreSQL database, connection pool।

**ঘটনার ক্রম:**

1. নতুন feature প্রতিটি request-এ দুটি অতিরিক্ত database query করে।
2. Staging-এ: ১০ জন tester, database-এ ১,০০০ row, `pool_size = 5`। কোনো সমস্যা নেই।
3. Production-এ: ৫,০০০ concurrent user, ২ কোটি row, আর কেউ জানত না — production-এর `pool_size` ভুল করে hard-code করা ছিল ৫ (staging-এ ১০)।
4. Connection pool ভরে গেল → request অপেক্ষায় → timeout।

**Diagnose কীভাবে:**

- Metric: error শুরুর সময় = deploy-এর সময় (L00-01-এর deployment history)।
- Log: "timeout acquiring connection from pool"।
- **Config diff:** staging ও prod-এর configuration পাশাপাশি তুলনা — `pool_size` আলাদা, এবং production-এর মানটি code-এ hard-code করা, configuration-এ নয়।

**সমাধান:** তাৎক্ষণিক rollback; তারপর configuration code থেকে বের করে layered config-এ আনা, staging-এ production-এর মতো load test, এবং deploy-এর আগে স্বয়ংক্রিয় config validation।

**শিক্ষা:** দুটি মূল কারণ — (১) **parity-র অভাব:** data-র আকার ও load আলাদা; (২) **config code-এর ভেতরে:** তাই কেউ পার্থক্য দেখতে পায়নি। এই lesson-এর `envconfig.py` ঠিক এই দুটি সমস্যার একটি ছোট সমাধান দেখায়।

## 6. Diagram — promotion ও configuration layer

### একই artifact, বিভিন্ন configuration

```text
                    ┌─────────────────────────┐
  git commit ──────►│ CI: build + test        │
                    │ artifact: app:1.4.0     │  ◄── একবারই build (immutable)
                    └───────────┬─────────────┘
                                │ একই artifact promote হয়
          ┌─────────────────────┼──────────────────────┐
          ▼                     ▼                      ▼
   ┌─────────────┐      ┌──────────────┐       ┌──────────────┐
   │     dev     │ ───► │   staging    │ ────► │     prod     │
   │ app:1.4.0   │      │  app:1.4.0   │ gate  │  app:1.4.0   │
   │ + dev cfg   │      │ + staging cfg│(test, │ + prod cfg   │
   └─────────────┘      └──────────────┘approval)└────────────┘
```

**মূল নীতি: "Build once, deploy many."** প্রতিটি environment-এর জন্য আলাদা করে build করলে staging-এ যা পরীক্ষা করলেন আর production-এ যা গেল তা আলাদা হতে পারে। একই artifact, শুধু configuration আলাদা।

### Configuration layer (এই lesson-এর script)

```text
  ┌──────────────────────────────────────────────┐
  │ 3. Environment variable  APP_DATABASE__...    │  ← সর্বোচ্চ অগ্রাধিকার; secret সবসময় এখানে
  ├──────────────────────────────────────────────┤
  │ 2. config/prod.json   (শুধু যা আলাদা)         │
  ├──────────────────────────────────────────────┤
  │ 1. config/base.json   (সবার common default)   │  ← সর্বনিম্ন অগ্রাধিকার
  └──────────────────────────────────────────────┘
          উপরের layer নিচের layer-এর একই key-কে override করে
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Environment | Application চালানোর সম্পূর্ণ পরিবেশ: server, config, data, network |
| Promotion | একই artifact-কে এক environment থেকে পরের environment-এ নেওয়া |
| Artifact | Build-এর ফলাফল (container image, package) যা deploy হয় |
| Immutable artifact | একবার তৈরি হলে বদলায় না; নতুন পরিবর্তন মানে নতুন version |
| Environment parity | Environment-গুলোর মধ্যে মিল (OS, version, architecture, config-এর গঠন) |
| Configuration drift | সময়ের সাথে environment-গুলো হাতে-করা পরিবর্তনে আলাদা হয়ে যাওয়া |
| Environment variable | Process চালু হওয়ার সময় OS থেকে পাওয়া key=value সেটিং |
| Secret | Password, API key, token — যা প্রকাশ পেলে ক্ষতি |
| Secret store | Secret নিরাপদে রাখার বিশেষ system (যেমন Vault, AWS Secrets Manager) |
| Feature flag | Code deploy থাকলেও feature চালু/বন্ধ configuration দিয়ে |
| Preview / ephemeral environment | প্রতিটি pull request-এর জন্য অস্থায়ী environment, merge-এর পরে মুছে যায় |
| Twelve-Factor App | Cloud-এ চালানোর উপযোগী application-এর ১২টি নীতি |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Twelve-Factor App: "Config in the environment"

Twelve-Factor App (Heroku-র engineer-দের লেখা প্রভাবশালী নীতিমালা)-এর তৃতীয় নীতি বলে: **যা environment ভেদে বদলায় তা code থেকে আলাদা রাখুন, environment-এ রাখুন।**

Environment ভেদে যা বদলায়:

- Database ও cache-এর address
- External service-এর credential
- প্রতিটি deploy-এর নির্দিষ্ট মান (যেমন hostname)

যা বদলায় না (code-এর অংশ): business logic, route, dependency-র তালিকা।

**সহজ পরীক্ষা:** আপনার codebase কি এই মুহূর্তে public করা যায়, কোনো credential প্রকাশ না করে? না হলে config ও code মিশে আছে।

### 8.2 Environment variable কীভাবে কাজ করে (Linux)

প্রতিটি Linux process-এর সাথে key=value জোড়ার একটি তালিকা থাকে — **environment**। Process নতুন process (child) তৈরি করলে child এর একটি copy পায়। Shell-এ:

```bash
export APP_APP__LOG_LEVEL=warning   # এই shell ও তার child process-এর environment-এ যোগ
python3 envconfig.py show prod      # child process (python) মানটি দেখতে পায়
unset APP_APP__LOG_LEVEL            # সরিয়ে ফেলা
```

Linux-এ একটি চলমান process-এর environment দেখা যায় `/proc/<PID>/environ` থেকে (শুধু সেই process-এর মালিক বা root)। এজন্য environment variable-এ রাখা secret-ও পুরোপুরি গোপন নয় — একই user-এর অন্য process পড়তে পারে। Production-এ secret store ও file-ভিত্তিক secret (সীমিত permission সহ) আরো নিরাপদ বিকল্প (Module 19)। Module 01-এ `/proc` বিস্তারিত দেখবেন।

### 8.3 Parity — কোথায় একই, কোথায় আলাদা

| বিষয় | একই রাখা উচিত | আলাদা হওয়া স্বাভাবিক |
|---|---|---|
| Artifact (code + dependency) | ✔ হুবহু একই | |
| OS, runtime version (Python, PostgreSQL) | ✔ | |
| Architecture (proxy → app → DB) | ✔ গঠনে একই | Replica সংখ্যা |
| Configuration-এর **গঠন** (কোন key আছে) | ✔ | |
| Configuration-এর **মান** | | ✔ host, pool size, log level |
| Secret | | ✔ প্রতিটি environment-এর আলাদা secret |
| Data | | ✔ production-এর আসল personal data কখনো dev/staging-এ নয় |
| আকার ও খরচ | | ✔ staging ছোট হতে পারে |

**গুরুত্বপূর্ণ:** Production-এর আসল user data staging-এ copy করা privacy ও আইনগত ঝুঁকি। Anonymized বা synthetic data ব্যবহার করুন।

### 8.4 Promotion gate

এক environment থেকে পরের environment-এ যাওয়ার আগে শর্ত:

- dev → staging: সব automated test পাস, code review।
- staging → prod: smoke test, integration test, প্রয়োজনে manual approval, change window।

এগুলো CI/CD-তে "environment protection rule" দিয়ে বাস্তবায়ন হয় (Module 11)। এই lesson-এর `validate` command হলো এমন একটি gate-এর ছোট উদাহরণ।

## 9. Practical demonstration — layered configuration

### ধাপ ১ — Configuration file দেখুন

Folder: [`code/L00-04/config/`](code/L00-04/config/base.json)

```bash
cd 00-orientation/code/L00-04
cat config/base.json
cat config/prod.json
```

লক্ষ্য করুন:

- `base.json`-এ সব common default।
- `prod.json`-এ **শুধু** যা production-এ আলাদা (database host ও pool size)। পুরো config আবার লেখা হয়নি — এতে environment-গুলোর পার্থক্য এক নজরে দেখা যায়।
- কোনো file-এ **password নেই**। এটি ইচ্ছাকৃত।

### ধাপ ২ — Final configuration দেখুন

```bash
python3 envconfig.py show dev
```

এটি তিনটি layer merge করে final configuration দেখায়। শুধু file পড়ে, কিছু লেখে না।

**এই repository-তে চালিয়ে পাওয়া আসল output:**

```text
{
  "app": {
    "name": "taskflow-api",
    "port": 8000,
    "debug": true,
    "log_level": "debug"
  },
  "database": {
    "host": "localhost",
    "port": 5432,
    "name": "taskflow",
    "user": "taskflow",
    "pool_size": 5
  },
  "features": {
    "new_dashboard": true
  },
  "environment": "dev"
}
```

`debug: true` এসেছে `dev.json` থেকে, বাকিগুলো `base.json` থেকে।

### ধাপ ৩ — Production validate করুন (secret ছাড়া)

```bash
python3 envconfig.py validate prod
echo "exit code: $?"
```

**আসল output:**

```text
FAIL  database.password must be set via APP_DATABASE__PASSWORD
prod: 1 problem(s)
exit code: 1
```

Exit code ১ মানে ব্যর্থ — CI pipeline এখানে deployment থামিয়ে দেবে।

### ধাপ ৪ — Secret নিরাপদে দিন

**ভুল উপায়** (password shell history-তে থেকে যায়):

```bash
# এভাবে করবেন না:
APP_DATABASE__PASSWORD=MyRealPassword python3 envconfig.py validate prod
```

`~/.bash_history` file-এ পুরো command লেখা থাকবে, password সহ।

**ভালো উপায়** — `read -s` দিয়ে টাইপ করা (screen-এ দেখা যায় না, history-তে যায় না):

```bash
read -rs -p "DB password: " APP_DATABASE__PASSWORD; echo
export APP_DATABASE__PASSWORD
python3 envconfig.py validate prod
echo "exit code: $?"
unset APP_DATABASE__PASSWORD   # কাজ শেষে সরিয়ে ফেলুন
```

| Option | অর্থ |
|---|---|
| `read` | keyboard থেকে একটি লাইন পড়ে variable-এ রাখে |
| `-r` | backslash-কে বিশেষ অর্থে না নেওয়া |
| `-s` | silent — টাইপ করা অক্ষর দেখায় না |
| `-p "..."` | prompt বার্তা |
| `export` | variable-কে child process (python)-এর environment-এ পাঠায় |
| `unset` | variable মুছে ফেলে |

যেকোনো practice মান দিন (আসল password নয়)। প্রত্যাশিত output:

```text
prod: OK
exit code: 0
```

### ধাপ ৫ — Production safety rule পরীক্ষা

Production-এ debug চালু করার চেষ্টা (environment variable layer সব file-কে override করে):

```bash
export APP_DATABASE__PASSWORD=practice-only
APP_APP__DEBUG=true python3 envconfig.py validate prod
echo "exit code: $?"
```

**আসল output:**

```text
FAIL  app.debug must be false in prod
prod: 1 problem(s)
exit code: 1
```

`APP_APP__DEBUG` নামের গঠন: `APP_` prefix + `APP` (section) + `__` (দুটি underscore = nesting) + `DEBUG` (key) → `config["app"]["debug"]`। মান `"true"` JSON হিসেবে parse হয়ে boolean `True` হয়।

### ধাপ ৬ — Staging ও production-এর পার্থক্য দেখুন

```bash
python3 envconfig.py diff staging prod
```

**আসল output** (`APP_DATABASE__PASSWORD` set থাকা অবস্থায়):

```text
key                          staging                prod
database.host                "db.staging.internal"  "db.prod.internal"
database.pool_size           10                     20
environment                  "staging"              "prod"
features.new_dashboard       true                   false
```

এই ছোট তালিকাই staging ও prod-এর **সব** পার্থক্য। Section 5-এর incident-এ এমন একটি diff থাকলে `pool_size`-এর পার্থক্য deploy-এর আগেই চোখে পড়ত। লক্ষ্য করুন password diff-এ দেখা যায় না — output-এ secret সবসময় `***` (masked)।

শেষে পরিষ্কার করুন:

```bash
unset APP_DATABASE__PASSWORD
```

### ধাপ ৭ — Test

```bash
python3 -m unittest -v
```

[`test_envconfig.py`](code/L00-04/test_envconfig.py)-এর ১১টি test: merge মূল data বদলায় না, env var-এর type (সংখ্যা, boolean) ঠিক থাকে, layer-এর অগ্রাধিকার, অজানা environment প্রত্যাখ্যান, **config file-এ secret থাকলে প্রত্যাখ্যান**, production rule, dev-এ debug অনুমোদিত, secret masking, ও staging/prod diff।

## 10. Code-এর ব্যাখ্যা

File: [`code/L00-04/envconfig.py`](code/L00-04/envconfig.py) · Python 3.10+ · Dependency: নেই

| অংশ | কী করে | কেন এভাবে |
|---|---|---|
| `deep_merge()` | Nested dictionary merge, override জেতে | সাধারণ `dict.update()` পুরো `database` section প্রতিস্থাপন করত — `port`, `name` হারিয়ে যেত |
| `copy.deepcopy()` | মূল data-র আলাদা copy | Merge-এর সময় `base` বদলে গেলে পরের environment load-এ ভুল মান আসত (test আছে) |
| `env_overrides()` | `APP_A__B=x` → `{"a": {"b": x}}` | Environment variable flat; `__` দিয়ে nesting প্রকাশ — অনেক framework-এ প্রচলিত convention |
| `parse_env_value()` | `json.loads` চেষ্টা, না হলে string | Env var সবসময় string; `"20"`-কে সংখ্যা ও `"true"`-কে boolean করা দরকার |
| `find_secrets_in_files()` | Config file-এ `password`/`secret`/`token`/`api_key` key খোঁজে | **Fail closed:** কেউ ভুল করে file-এ secret লিখলে load-ই ব্যর্থ — Git-এ যাওয়ার আগেই ধরা |
| `validate()` | Environment-ভিত্তিক নিয়ম | Production-এর নিয়ম কঠোর, dev-এ শিথিল — একই code, ভিন্ন নীতি |
| `masked()` | Secret-এর মান `***` | Log, terminal বা CI output-এ secret কখনো ছাপা হবে না |
| `diff()` | দুই environment flatten করে তুলনা | Parity যাচাই: পার্থক্য স্পষ্টভাবে দেখা |
| Exit code `0` / `1` / `2` | ঠিক / নিয়ম ভঙ্গ / input error | CI-তে সরাসরি gate হিসেবে ব্যবহারযোগ্য |

### Python কেন এখানে, আর কোথায় Python যথেষ্ট নয়

এই lesson-এ Python দিয়ে configuration-এর **ধারণা** (layer, precedence, validation) শেখানো হলো। বাস্তবে:

- Application নিজে প্রায়ই একটি library দিয়ে config পড়ে (যেমন Python-এ `pydantic-settings`, Module 05)।
- Kubernetes-এ configuration আসে **ConfigMap** ও **Secret** (YAML) থেকে (Module 14) — Python তা প্রতিস্থাপন করে না।
- Infrastructure-স্তরের environment পার্থক্য Terraform-এর variable ও workspace (HCL) দিয়ে (Module 12)।

তবে এই lesson-এর `validate` ধারণা — deploy-এর আগে config যাচাই — সব জায়গায় প্রযোজ্য।

## 11. প্রত্যাশিত ফল ও যাচাই

| Command | প্রত্যাশিত |
|---|---|
| `python3 envconfig.py show dev` | `"debug": true`, `"environment": "dev"` |
| `python3 envconfig.py validate dev` | `dev: OK`, exit 0 (dev-এ password বাধ্যতামূলক নয়) |
| `python3 envconfig.py validate prod` (password ছাড়া) | password FAIL, exit 1 |
| `python3 envconfig.py show qa` | `error: unknown environment 'qa'...`, exit 2 |
| `python3 -m unittest -v` | `Ran 11 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | সম্ভাব্য কারণ | কীভাবে নিশ্চিত হবেন | সমাধান |
|---|---|---|---|
| Env var দিলেও মান বদলায় না | `export` করেননি, বা নাম ভুল (একটি `_` বনাম দুটি `__`) | `env \| grep APP_` | `export` করুন; nesting-এ দুটি underscore |
| `"20"` string হিসেবে আসছে | অন্য tool-এ JSON parse নেই | Type দেখুন | এই script `json.loads` করে; নিজের code-এ type রূপান্তর করুন |
| `secret-like keys in base.json` | File-এ password লিখেছেন | Error-এ key-এর path | File থেকে মুছে env var ব্যবহার করুন; আগে commit হয়ে থাকলে secret **বদলে** ফেলুন (rotate) |
| Password history-তে চলে গেছে | Inline `VAR=... command` ব্যবহার | `history \| grep PASSWORD` | Password বদলান; `history -d <number>` দিয়ে সেই লাইন মুছুন; ভবিষ্যতে `read -s` |
| Staging-এ চলে, prod-এ না | Config, version, data বা load-এর পার্থক্য | `diff staging prod`, version তুলনা | Parity বাড়ান, staging-এ load test |

> **Fedora-তে:** সব command একই (Bash, Python, `read`, `export`)।

### ধারণাগত সাধারণ ভুল

- **প্রতিটি environment-এর জন্য আলাদা build** — "build once, deploy many" ভাঙে।
- **Production data staging-এ copy** — privacy ও আইনি ঝুঁকি।
- **Code-এ `if env == "prod":` ছড়িয়ে রাখা** — আচরণ configuration দিয়ে নিয়ন্ত্রণ করুন (feature flag), environment নামের উপর শাখা দিয়ে নয়।
- **Staging-কে অবহেলা** — পুরোনো version, ভাঙা data; তখন staging-এ পাস করা অর্থহীন।
- **`.env` file Git-এ commit** — এই repository-র [.gitignore](../.gitignore)-এ `.env` বাদ দেওয়া আছে, `.env.example` রাখা যায়।

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - প্রতিটি environment-এর **আলাদা secret** — staging-এর password ফাঁস হলে production নিরাপদ থাকে।
  - Production-এ access সবচেয়ে সীমিত; dev-এ developer-এর পূর্ণ access থাকতে পারে।
  - Debug mode production-এ stack trace, configuration ও internal path প্রকাশ করতে পারে — তাই `validate`-এ নিয়ম।
  - Environment variable-ও সম্পূর্ণ গোপন নয় (`/proc/<PID>/environ`, crash dump, debug output) — sensitive production secret-এর জন্য secret store (Module 19)।
- **Performance:** Staging-এ production-এর মতো data-র আকার ও load না থাকলে performance সমস্যা ধরা পড়ে না (Section 5)। Load testing: Module 18।
- **Cost:** Staging সবসময় production-এর পূর্ণ আকারে চালানো ব্যয়বহুল। সাধারণ কৌশল: একই গঠন, কম replica; কাজের সময়ের বাইরে বন্ধ রাখা; preview environment merge-এর পরে স্বয়ংক্রিয়ভাবে মুছে ফেলা।

## 14. Hands-on exercise

1. **নতুন setting:** `base.json`-এ `"app": {"request_timeout_seconds": 30}` যোগ করুন, `prod.json`-এ ১০ করুন। `diff dev prod` চালিয়ে দেখুন।
2. **নতুন validation rule:** `validate()`-এ নিয়ম যোগ করুন: production-এ `database.pool_size` কমপক্ষে ১০ হতে হবে। একটি pass ও একটি fail test লিখুন।
3. **Secret সুরক্ষা পরীক্ষা:** `staging.json`-এ ভুল করে `"database": {"password": "test"}` লিখুন। `show staging` চালিয়ে কী হয় দেখুন। তারপর মুছে ফেলুন।
4. **QA environment যোগ:** `ENVIRONMENTS`-এ `"qa"` যোগ করুন, `config/qa.json` বানান। QA-র জন্য কোন নিয়ম staging-এর মতো হওয়া উচিত? `validate`-এ যুক্তি দিয়ে যোগ করুন।
5. **History পরীক্ষা (নিজের Ubuntu-তে):** একটি নকল মান দিয়ে inline `APP_DATABASE__PASSWORD=fake123 python3 envconfig.py validate prod` চালান, তারপর `history | tail -3` দেখুন। এরপর `read -s` পদ্ধতিতে একই কাজ করে history তুলনা করুন।

## 15. Mini-project — নিজের WordPress site-এর environment পরিকল্পনা

আপনার একটি WordPress/PHP project ধরে `~/devops-notebook/L00-04-environments.md` লিখুন:

1. বর্তমানে কয়টি environment আছে? কোথায় পরিবর্তন পরীক্ষা হয়?
2. `wp-config.php`-এ কোন মানগুলো environment ভেদে বদলায় (DB host, salt, `WP_DEBUG`)? কোনগুলো secret?
3. Section 6-এর মতো একটি promotion diagram আঁকুন: local → staging → production।
4. Production database staging-এ নেওয়ার সময় কোন personal data (user email, order) anonymize করতে হবে?
5. `envconfig.py`-এর ধারণা কাজে লাগিয়ে WordPress-এর জন্য তিনটি validation rule লিখুন (যেমন production-এ `WP_DEBUG` false)।

## 16. Interview প্রশ্ন

1. Dev, staging ও production environment কেন আলাদা রাখা হয়? Staging-এর মূল উদ্দেশ্য কী?
2. "Build once, deploy many" বলতে কী বোঝায়? প্রতিটি environment-এর জন্য আলাদা build করলে কী ঝুঁকি?
3. Environment parity কী? কোন বিষয়গুলো একই আর কোনগুলো আলাদা হতে পারে?
4. Twelve-Factor App-এর "config" নীতি ব্যাখ্যা করুন।
5. Secret কোথায় রাখবেন এবং কোথায় কখনো নয়?
6. "Staging-এ চলে, production-এ চলে না" — কীভাবে তদন্ত শুরু করবেন?
7. Production data কি staging-এ ব্যবহার করা উচিত? কেন বা কেন নয়?

## 17. Self-assessment প্রশ্ন

1. চারটি মূল environment-এর উদ্দেশ্য, user ও data এক লাইনে লিখুন।
2. নাটকের analogy কোন দুই জায়গায় software environment-এর সাথে মেলে না?
3. `APP_DATABASE__POOL_SIZE=50` দিলে final config-এ কী বদলায় এবং কেন এটি `prod.json`-কে override করে?
4. `deep_merge` না করে সাধারণ `dict.update` ব্যবহার করলে `show prod`-এ কোন key হারিয়ে যেত?
5. `VAR=value command` আকারে password দেওয়া কেন ঝুঁকিপূর্ণ? নিরাপদ বিকল্প কী?
6. Section 5-এর incident-এর দুটি মূল কারণ কী, এবং `diff` ও `validate` command কীভাবে সাহায্য করত?

## 18. সংক্ষিপ্ত সারাংশ

- **Environment** = application চালানোর সম্পূর্ণ পরিবেশ। Dev → test → staging → prod পথে ঝুঁকি ধাপে ধাপে বাড়ে।
- **Build once, deploy many:** একই immutable artifact promote হয়, শুধু configuration আলাদা।
- **Parity:** artifact, runtime version ও architecture একই; মান, secret, আকার আলাদা হতে পারে। Production-এর আসল personal data dev/staging-এ নয়।
- **Config code-এর বাইরে** (Twelve-Factor): layer — base → environment file → environment variable।
- **Secret** কখনো file বা Git-এ নয়; shell history-তেও নয় (`read -s`); output-এ সবসময় masked।
- Deploy-এর আগে **config validation** একটি সহজ কিন্তু শক্তিশালী gate।

## 19. Completion checklist

- [ ] `show`, `diff`, `validate` তিনটি command চালিয়েছি
- [ ] `read -s` দিয়ে নিরাপদে secret দিয়ে `validate prod` পাস করিয়েছি এবং পরে `unset` করেছি
- [ ] Production-এ debug চালুর চেষ্টা validation আটকেছে দেখেছি
- [ ] `python3 -m unittest -v` চালিয়ে ১১টি test পাস দেখেছি
- [ ] Exercise ১, ২ ও ৩ শেষ করেছি
- [ ] Mini-project: নিজের WordPress project-এর environment পরিকল্পনা লিখেছি
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট করেছি

## 20. Official documentation ও further reading

- The Twelve-Factor App — Config: https://12factor.net/config
- Python `os.environ`: https://docs.python.org/3/library/os.html#os.environ
- Python `json` module: https://docs.python.org/3/library/json.html
- GNU Bash manual — `read` ও `export` builtin: https://www.gnu.org/software/bash/manual/
- পরবর্তী গভীরতা: Module 05 (secret ও config, L05-10), Module 11 (environment protection, L11-07), Module 12 (Terraform environment, L12-08), Module 19 (secret management, L19-05)

---

**পরের lesson:** L00-05 — Architecture diagram ও technical documentation (C4, ADR, docs-as-code)
