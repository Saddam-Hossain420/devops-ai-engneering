# L03-04 — Pull request, code review, protected branch, CODEOWNERS

| | |
|---|---|
| **Module** | 03 — Git and Collaboration |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩ ঘণ্টা |
| **পূর্বশর্ত** | [L03-02 — Branch, merge ও rebase](L03-02-branch-merge-rebase.md), [L03-03 — Remote, tag ও SemVer](L03-03-remotes-tags-semver.md) |
| **Label** | — (GitHub-এ practical-এর জন্য বিনামূল্যের account যথেষ্ট) |
| **Tested** | `codeowners.py` ও `protection_check.py`: ৯টি test পাস — **GitHub documentation-এর CODEOWNERS উদাহরণের প্রত্যাশিত ফল** (শেষ match জেতে, `apps/` যেকোনো গভীরতায়, owner-হীন লাইন, `docs/*` শুধু সরাসরি file), নমুনা file-এর lint, আসল git repository থেকে পরিবর্তিত file, branch protection নমুনা (Python 3.14, Git 2.54, Windows)। Output Section 9-এ। **কোনো আসল GitHub repository-তে** protection, CODEOWNERS বা `gh api` **চালানো হয়নি**; `sample-protection.json` API-র আকারে হাতে লেখা। |

---

## 1. এই lesson-এ যা শিখবেন

- **Pull request (PR)**-এর উদ্দেশ্য: review, আলোচনা, CI যাচাই ও audit trail।
- একটি ভালো PR কেমন: ছোট, একটি বিষয়, স্পষ্ট বর্ণনা, যাচাইয়ের প্রমাণ।
- **Code review**: reviewer কী দেখবেন, কীভাবে মন্তব্য করবেন, কী automation-এ ছেড়ে দেবেন।
- **Protected branch** / ruleset: PR বাধ্যতামূলক, approval, status check, force push নিষেধ।
- **CODEOWNERS**: কোন path-এর জন্য কার review বাধ্যতামূলক; "শেষ match জেতে" নিয়মের ফাঁদ।
- Fork ও PR-এর নিরাপত্তা (বাইরের contributor-এর code CI-তে)।
- Python দিয়ে CODEOWNERS বিশ্লেষণ ও branch protection policy যাচাই।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

`main`-এ সরাসরি push মানে: কেউ যাচাই করেনি, test চলেনি, এবং কেন পরিবর্তন হলো তার কোনো আলোচনা নেই। একটি typo production বন্ধ করতে পারে। আর একটি compromised account চুপচাপ ক্ষতিকর code ঢোকাতে পারে।

PR-ভিত্তিক workflow দেয়:

- **চার চোখের নীতি** (four-eyes): অন্তত একজন অন্য মানুষ দেখেছেন।
- **CI gate**: test, lint ও security scan সবুজ না হলে merge নয় (L03-06, Module 06)।
- **Audit trail**: কে, কবে, কেন, কে অনুমোদন দিল — compliance (SOC 2 ইত্যাদি) ও incident তদন্তে কাজে লাগে।
- **জ্ঞান ভাগাভাগি**: review-এর মাধ্যমে দল code চেনে, এবং একজনের উপর নির্ভরতা কমে।

CODEOWNERS নিশ্চিত করে যে payment, infrastructure বা CI workflow-এর মতো সংবেদনশীল অংশে সঠিক বিশেষজ্ঞের অনুমোদন ছাড়া পরিবর্তন যাবে না।

## 3. সহজ ভাষায় পরিচয়

**PR-এর জীবনচক্র:**

```text
branch তৈরি → commit → push → PR খোলা (বর্ণনা, template)
   → CI চলে (test, lint, scan)        → reviewer স্বয়ংক্রিয়ভাবে যুক্ত (CODEOWNERS)
   → review: comment / request changes / approve
   → পরিবর্তন → নতুন commit → (stale approval বাতিল) → আবার review
   → সব শর্ত পূরণ → merge (squash / merge commit / rebase) → branch মুছে ফেলা
   → deploy pipeline (Module 06)
```

**Protected branch-এর প্রধান নিয়ম:**

| নিয়ম | কী আটকায় |
|---|---|
| PR বাধ্যতামূলক | সরাসরি push |
| ন্যূনতম approval (১–২) | একা merge |
| Stale approval বাতিল | Approval-এর পরে চুপচাপ নতুন code ঢোকানো |
| Code owner review | ভুল ব্যক্তির অনুমোদন |
| Required status checks | ভাঙা test নিয়ে merge |
| Branch up to date | Main-এর নতুন পরিবর্তনের সাথে না মিলিয়ে merge (semantic conflict, L03-02) |
| Force push / deletion নিষেধ | History পুনর্লিখন, branch মুছে ফেলা |
| Admin-দের জন্যও প্রযোজ্য | "জরুরি" bypass |
| Conversation resolution | উত্তর না দেওয়া মন্তব্য রেখে merge |
| Signed commits (ঐচ্ছিক) | নকল author |

**CODEOWNERS** (`.github/CODEOWNERS`, root বা `docs/`-এ রাখা যায়):

```text
*                    @acme/platform          ← সাধারণ নিয়ম আগে
/app/payments/       @acme/payments @acme/security
/.github/workflows/  @acme/platform @acme/security
```

নিয়মগুলো gitignore-এর মতো pattern। **শেষ যে লাইন মেলে সেটিই জেতে।** একাধিক owner থাকলে তাদের **যেকোনো একজনের** approval যথেষ্ট।

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### হাসপাতালের ওষুধের প্রেসক্রিপশন

- **PR** = ডাক্তারের লেখা প্রেসক্রিপশন। ফার্মেসি তা দেখে ওষুধ দেয়; ডাক্তার নিজে তাক থেকে ওষুধ নিতে পারেন না।
- **Review** = ফার্মাসিস্ট পরীক্ষা করেন — মাত্রা ঠিক? অন্য ওষুধের সাথে বিক্রিয়া?
- **CODEOWNERS** = নিয়ন্ত্রিত ওষুধ (narcotics) শুধু বিশেষ অনুমোদনপ্রাপ্ত ফার্মাসিস্ট দিতে পারেন।
- **Protected branch** = তাকে তালা — প্রেসক্রিপশন ছাড়া কেউ, এমনকি হাসপাতালের পরিচালকও, ওষুধ নিতে পারেন না।
- **CI** = স্বয়ংক্রিয় allergy-check system।

### Analogy কোথায় মেলে না

- ফার্মাসিস্ট প্রতিটি প্রেসক্রিপশন খুঁটিয়ে দেখেন। বাস্তবে reviewer-রা বড় PR **কম মনোযোগে** দেখেন — ১০ লাইনের PR-এ দশটি মন্তব্য পড়ে, ১০০০ লাইনের PR-এ পড়ে "LGTM"। তাই PR ছোট রাখাই নিরাপত্তা।
- প্রেসক্রিপশনের মান মোটামুটি নিশ্চিত। Code review **নিরাপত্তার নিশ্চয়তা দেয় না** — subtle bug বা ইচ্ছাকৃত backdoor চোখ এড়াতে পারে। Review একটি স্তর মাত্র; test, static analysis ও least privilege লাগবেই।
- ওষুধ দেওয়ার নিয়ম একবারই লেখা হয়। CODEOWNERS file নিজেও code — কেউ নিজেকে owner বানাতে পারেন। তাই **CODEOWNERS file-এর নিজেরও owner থাকা দরকার**।

## 5. Real-world engineering scenario — "Review হয়েছিল, তবু ক্ষতিকর code main-এ"

**পরিস্থিতি:** একজন contributor-এর PR approve হলো। তারপর তিনি আরো একটি commit push করলেন — CI workflow-এ একটি step, যা secret বাইরে পাঠায়। Repository-তে "dismiss stale approvals" বন্ধ ছিল, তাই পুরোনো approval বহাল থাকল এবং তিনি নিজেই merge করলেন। এছাড়া `.github/workflows/`-এর জন্য কোনো code owner ছিল না, তাই security team-কে কখনো review-তে ডাকা হয়নি।

**কী ভুল ছিল (এই lesson-এর `protection_check.py` যা ধরে):**

1. `dismiss_stale_reviews: false`।
2. `require_last_push_approval: false`। এটা চালু থাকলে শেষ push যিনি করেছেন তিনি ছাড়া অন্য কারো approval লাগত।
3. CODEOWNERS-এ workflow path-এর জন্য security owner নেই।
4. `enforce_admins: false`। "জরুরি" bypass খোলা।

**সমাধান:**

- উপরের চারটি setting চালু করা।
- `.github/workflows/` ও `CODEOWNERS`-এর owner হিসেবে security team-কে রাখা।
- Workflow-এর permission ন্যূনতম করা এবং action SHA দিয়ে pin করা (L03-06)।
- Secret শুধু protected environment-এ রাখা (Module 06)।

**শিক্ষা:** Protection setting-এর ছোট একটি ফাঁকও পুরো review প্রক্রিয়া অর্থহীন করে দিতে পারে। Setting-গুলো হাতে click করে বসানোর বদলে code (Terraform-এর GitHub provider, ruleset) ও policy check দিয়ে রাখুন, এবং নিয়মিত audit করুন।

## 6. Diagram — PR-এর পথে gate

```text
 developer ── push feature/x ──► PR #42 ───────────────────────────────────────► merge to main
                                   │                                              ▲
                                   ├─ CI: test ✓ lint ✓ conflict-markers ✓ ───────┤ required checks
                                   ├─ CODEOWNERS: app/payments/ → @acme/payments ─┤ code owner approval
                                   │              .github/workflows/ → @acme/security
                                   ├─ review: 1 approval (not the last pusher) ───┤
                                   ├─ new commit? → old approvals dismissed ──────┤
                                   ├─ branch up to date with main ────────────────┤
                                   └─ conversations resolved ─────────────────────┘
 protected main: no direct push · no force push · no deletion · admins included
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| Pull request / merge request | একটি branch-এর পরিবর্তন অন্যটিতে আনার অনুরোধ (GitHub / GitLab) |
| Reviewer / approver | যিনি দেখেন / যাঁর অনুমোদন গণ্য |
| Code owner | একটি path-এর বাধ্যতামূলক reviewer |
| Protected branch / ruleset | Branch-এর পরিবর্তনের নিয়ম |
| Required status check | Merge-এর আগে সফল হতে হবে এমন CI job |
| Stale review | Approval-এর পরে নতুন commit এলে পুরোনো approval |
| Draft PR | এখনো review-এর জন্য প্রস্তুত নয় |
| Merge queue | একের পর এক PR main-এর সর্বশেষ অবস্থায় test করে merge |
| Fork | অন্যের repository-র নিজের copy |
| LGTM | "Looks good to me" — সতর্কতার সাথে ব্যবহার করুন |
| Nit | ছোট, অবাধ্যতামূলক মন্তব্য |
| Four-eyes principle | কমপক্ষে দুইজনের দেখা |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 ভালো PR

- **ছোট:** গবেষণা ও শিল্প-অভিজ্ঞতা দুটোই বলে, বড় PR-এ review-এর মান দ্রুত কমে যায়। প্রায় ২০০–৪০০ লাইন একটি যুক্তিসঙ্গত সীমা।
- **একটি বিষয়:** refactor ও feature আলাদা PR-এ।
- **বর্ণনা:** কী ও কেন, কীভাবে যাচাই করা হয়েছে, ঝুঁকি কী, rollback কীভাবে ([`pull_request_template.md`](code/L03-04/pull_request_template.md))।
- **নিজে আগে review:** PR খোলার আগে নিজের diff পড়ুন।
- **Commit message:** Conventional Commits (L03-03)।

### 8.2 Reviewer কী দেখবেন (ক্রম অনুযায়ী)

1. **উদ্দেশ্য:** পরিবর্তন কি সঠিক সমস্যা সমাধান করে? Design ঠিক আছে?
2. **সঠিকতা:** edge case, error handling, concurrency।
3. **নিরাপত্তা:** input validation, secret, permission, dependency।
4. **Operability:** log, metric, timeout, migration, rollback (Module 17)।
5. **Test:** পরিবর্তনের সাথে test আছে কি? কোন test এই পরিবর্তন ছাড়া fail করত?
6. **পাঠযোগ্যতা:** নামকরণ, জটিলতা।

Formatting, import ক্রম বা style-এর মতো বিষয় **মানুষ দেখবেন না** — সেগুলো automation-এর কাজ (formatter, linter)।

**মন্তব্যের ধরন:**

- নির্দিষ্ট হোন: "এখানে timeout নেই, upstream ঝুলে গেলে worker আটকে যাবে"।
- প্রস্তাব দিন: "`timeout=5` বিবেচনা করবেন?"।
- কোনটি বাধ্যতামূলক আর কোনটি `nit:` তা স্পষ্ট করুন।
- মন্তব্য code নিয়ে, মানুষ নিয়ে নয়।

### 8.3 CODEOWNERS-এর নিয়ম

- Pattern gitignore-ধাঁচের। শুরুতে `/` থাকলে বা মাঝে `/` থাকলে pattern root-এর সাপেক্ষে; নইলে যেকোনো গভীরতায় মেলে (`apps/`, `*.js`)।
- `**` যেকোনো সংখ্যক directory।
- **শেষ মিলটি জেতে।** তাই সাধারণ নিয়ম উপরে, নির্দিষ্ট নিয়ম নিচে। পরে লেখা একটি সাধারণ নিয়ম (যেমন `*.md`) আগের নির্দিষ্ট নিয়ম (যেমন `/docs/*`)-কেও ঢেকে দেয় (Section 9.1)।
- Owner ছাড়া একটি লাইন = ঐ path-এর কোনো owner নেই (ইচ্ছাকৃত ব্যতিক্রম, বা ভুল)।
- GitHub-এ `!` negation ও `[ ]` range সমর্থিত নয়। ভুল syntax-এর লাইন উপেক্ষিত হয়।
- `docs/*` শুধু docs-এর সরাসরি file-এ মেলে (gitignore থেকে ভিন্ন — GitHub documentation-এ উল্লেখিত)।
- Owner-এর repository-তে write access থাকতে হবে, নইলে তিনি গণ্য হন না।

### 8.4 Fork থেকে আসা PR ও CI-এর নিরাপত্তা

বাইরের contributor-এর PR-এ CI চালালে তাঁর code আপনার runner-এ চলে। GitHub default-এ fork PR-এর workflow-কে secret দেয় না এবং read-only token দেয়। `pull_request_target` trigger base repository-র context-এ (secret সহ) চলে — এর ভেতরে PR-এর code checkout করে চালানো একটি পরিচিত বিপজ্জনক pattern (L03-06-এর linter এটা ধরে)।

## 9. Practical demonstration

Files: [`code/L03-04/codeowners.py`](code/L03-04/codeowners.py), [`sample-CODEOWNERS`](code/L03-04/sample-CODEOWNERS) (হাতে তৈরি, কাল্পনিক org, ইচ্ছাকৃত ভুল সহ), [`protection_check.py`](code/L03-04/protection_check.py), [`sample-protection.json`](code/L03-04/sample-protection.json)।

### 9.1 কোন file-এর owner কে

```bash
cd ~/devops-ai-engineering/03-git-and-collaboration/code/L03-04
python3 codeowners.py owners sample-CODEOWNERS README.md app/api/routes.py app/payments/charge.py \
  app/payments/migrations/0001.sql infra/terraform/main.tf infra/k8s/deploy.yaml \
  .github/workflows/ci.yml docs/guide.md docs/api/ref.md
```

**আসল output:**

```text
README.md                                @acme/tech-writers  (line 14: *.md)
app/api/routes.py                        @acme/backend  (line 6: /app/)
app/payments/charge.py                   @acme/payments @acme/security  (line 7: /app/payments/)
app/payments/migrations/0001.sql         @acme/dba  (line 10: **/migrations/)
infra/terraform/main.tf                  — no owner  (line 17: /infra/terraform/)
infra/k8s/deploy.yaml                    @acme/platform @acme/sre  (line 8: /infra/)
.github/workflows/ci.yml                 @acme/platform @acme/security  (line 9: /.github/workflows/)
docs/guide.md                            @acme/tech-writers  (line 14: *.md)
docs/api/ref.md                          @acme/tech-writers  (line 14: *.md)
```

**তিনটি শিক্ষা:**

1. `docs/guide.md`-এর জন্য `/docs/*` (line 12, @acme/docs) লেখা ছিল, কিন্তু পরে লেখা `*.md` (line 14) জিতেছে। **শেষ match জেতে** — পরে যোগ করা একটি সাধারণ নিয়ম চুপচাপ আগের নির্দিষ্ট নিয়ম ঢেকে দেয়।
2. Payment-এর migration-এ `@acme/payments` বা security নেই, শুধু `@acme/dba` আছে। `**/migrations/` পরে লেখা বলে payment team-এর নিয়ম বাতিল হয়েছে। এটা ইচ্ছাকৃত কিনা team-কে ঠিক করতে হবে।
3. Terraform-এর কোনো owner নেই — line 17-এর owner-হীন pattern।

### 9.2 Lint

```bash
python3 codeowners.py lint sample-CODEOWNERS --require .github/workflows/ --require infra/terraform/ --require app/payments/
```

**আসল output:**

```text
- line 20: invalid owner 'platform-team' (use @user, @org/team or an email)
- line 23: '!' negation is not supported in CODEOWNERS — pattern ignored
- line 14: pattern '*.md' repeats line 5 — the earlier one never applies
- required path infra/terraform/ has no owner (line 17 '/infra/terraform/' removes owners)
11 rule(s), 4 finding(s)
exit=1
```

GitHub নিজেও repository-র CODEOWNERS file-এর syntax error দেখায়। তবে "কোন গুরুত্বপূর্ণ path-এর owner নেই" — এই policy check আপনার নিজের লিখতে হয়, যেমন CI-তে `lint --require ...`।

### 9.3 PR-এর জন্য কার review লাগবে

```bash
# যেকোনো repository-তে, feature branch-এ দাঁড়িয়ে:
python3 codeowners.py review .github/CODEOWNERS --repo . --base origin/main
```

`git diff --name-only origin/main...HEAD` (তিন বিন্দু = merge base থেকে) দিয়ে পরিবর্তিত file বের করে প্রতিটির owner দেখায়। Test-এ একটি temporary repository-তে যাচাই করা হয়েছে।

### 9.4 Branch protection policy

```bash
python3 protection_check.py sample-protection.json --require-check validate; echo "exit=$?"
```

**আসল output:**

```text
PASS  pull request required before merging
PASS  at least 1 approving review(s) (has 1)
FAIL  new commits dismiss stale approvals
PASS  code owner review required (CODEOWNERS enforced)
PASS  status checks required
FAIL  branch must be up to date with base before merging
FAIL  rules apply to administrators too
PASS  force push disabled
PASS  branch deletion disabled
PASS  review conversations must be resolved
PASS  required check 'validate' configured
8/11 policy items met
exit=1
```

তিনটি FAIL-এর প্রথম ও শেষটি Section 5-এর ঘটনার দুটি কারণ। নিজের repository-তে (admin অধিকার থাকলে) আসল JSON নিন:

```bash
gh auth login                                   # GitHub CLI (একবার)
gh api repos/OWNER/REPO/branches/main/protection > protection.json
python3 protection_check.py protection.json --require-check validate
```

⚠️ `sample-protection.json` হাতে লেখা, GitHub API-র আকারে। আসল response-এ আরো field থাকে, এবং GitHub-এর নতুন **ruleset** ব্যবস্থার response-এর আকার ভিন্ন।

### 9.5 GitHub-এ setup (নিজের practice repository-তে)

1. Settings → Branches (বা Rules → Rulesets) → `main`: PR বাধ্যতামূলক, ১টি approval, dismiss stale, require code owner review, required status check `validate`, force push নিষেধ, admin-দের জন্যও প্রযোজ্য।
2. `.github/CODEOWNERS` ও `.github/pull_request_template.md` যোগ করুন।
3. একটি feature branch → PR → নিজের PR নিজে approve করতে পারবেন না (GitHub-এর নিয়ম)। দ্বিতীয় account বা সহকর্মী লাগবে; একা থাকলে approval সংখ্যা ০ রেখে বাকি নিয়মগুলো অনুশীলন করুন।

Terminal থেকে (`gh` CLI):

```bash
git switch -c feat/health-endpoint && git commit -am "feat: add /health" && git push -u origin HEAD
gh pr create --fill --draft
gh pr ready
gh pr checks --watch
gh pr merge --squash --delete-branch
```

### 9.6 Test

```bash
python3 -m unittest -v
```

[`test_l03_04.py`](code/L03-04/test_l03_04.py)-এর ৯টি test: GitHub documentation-এর উদাহরণ — শেষ match, inline comment, `apps/` গভীরতায়, `**/logs`, owner-হীন `/apps/github`, `docs/*`-এর সরাসরি-file নিয়ম; sample-এর চারটি lint finding; payment-এর owner; আসল git repository-তে পরিবর্তিত file; protection-এর তিনটি FAIL এবং খালি config।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| `to_regex` anchored নিয়ম | শুরুতে বা মাঝে `/` থাকলে root-এর সাপেক্ষে | gitignore-এর নিয়ম |
| `(?:/.*)?` suffix | Directory-তে মিললে ভেতরের সব কিছু | `/build/logs` তার নিচের সব file ঢাকে |
| `docs/*`-এর ব্যতিক্রম | Suffix নেই | GitHub-এর documented আচরণ |
| `owners_for` loop-এ শেষটি রাখা | — | "Last match wins" |
| Owner-হীন rule-এ খালি list | — | ইচ্ছাকৃত ব্যতিক্রম চেনা |
| `lint --require` | গুরুত্বপূর্ণ path-এর owner যাচাই | GitHub নিজে এটা বাধ্য করে না |
| `protection_check.enabled` | `{"enabled": bool}` বা অনুপস্থিত | API-র আকার; অনুপস্থিত = বন্ধ |

**সীমাবদ্ধতা:** escaped `\#`, CODEOWNERS-এর সর্বোচ্চ আকার (GitHub-এ 3 MB), team-এর write access যাচাই করা নেই। এটি শেখার tool; GitHub UI-ই আসল সত্য।

**Python কেন এখানে, কোথায় নয়:** policy-as-code check ও audit script-এ ভালো। Setting প্রয়োগে GitHub ruleset বা Terraform-এর GitHub provider (Module 07) ব্যবহার করুন — হাতে click করলে drift হয়।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `owners sample-CODEOWNERS docs/guide.md` | `@acme/tech-writers` (line 14) |
| `lint sample-CODEOWNERS --require infra/terraform/` | ৪টি finding, exit ১ |
| `protection_check.py sample-protection.json` | ৩টি FAIL |
| `python3 -m unittest -v` | `Ran 9 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Code owner review request আসে না | File ভুল জায়গায়, pattern ভুল, owner-এর write access নেই | `.github/CODEOWNERS`; GitHub-এর error দেখুন; `codeowners.py owners` |
| ভুল team-কে review request | পরে লেখা সাধারণ নিয়ম | নির্দিষ্ট নিয়ম নিচে রাখুন |
| "Merge blocked: required check expected" | Check-এর নাম বদলেছে বা workflow চলেনি | Workflow job-এর নাম ও protection-এর নাম মেলান |
| Approval-এর পরে নতুন commit, তবু merge হলো | Dismiss stale বন্ধ | চালু করুন (Section 5) |
| Admin নিজে bypass করছেন | `enforce_admins` বন্ধ | চালু করুন; জরুরি পরিস্থিতির জন্য নথিভুক্ত break-glass প্রক্রিয়া |
| PR বিশাল, review ঝুলে আছে | Scope বড় | ভাগ করুন; feature flag (L03-02) |
| Fork PR-এর CI-তে secret নেই | নিরাপত্তার জন্য ইচ্ছাকৃত | `pull_request_target` দিয়ে "ঠিক" করবেন না (L03-06) |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - `CODEOWNERS` ও `.github/workflows/`-এর নিজস্ব owner রাখুন (security team)।
  - Stale approval বাতিল ও last-push approval চালু রাখুন।
  - Admin-রাও নিয়মের অধীন থাকবেন।
  - Signed commit বিবেচনা করুন।
  - Secret scanning ও push protection (Module 19) চালু রাখুন।
  - Review সব ধরা পড়ার নিশ্চয়তা দেয় না — automation ও least privilege-এর সাথে মিলিয়ে ব্যবহার করুন।
- **Performance:**
  - ছোট PR → দ্রুত review → কম lead time (DORA, L00-01)।
  - Review-এর SLA (যেমন এক কর্মদিবস) রাখুন।
  - Merge queue দিয়ে একসাথে অনেক PR নিরাপদে merge করুন।
- **Cost:**
  - প্রতিটি PR-এ CI-এর মিনিট খরচ হয় — path filter ও cache ব্যবহার করুন (L03-06)।
  - Private repository-তে কিছু protection feature GitHub-এর নির্দিষ্ট plan-এ সীমিত হতে পারে — নিজের plan-এর documentation দেখুন।

## 14. Hands-on exercise

1. `sample-CODEOWNERS` ঠিক করুন: চারটি lint finding শূন্য, এবং `docs/guide.md` → `@acme/docs`, payment migration → `@acme/payments @acme/dba`। `owners` দিয়ে যাচাই করুন।
2. `codeowners.py`-তে একটি `coverage` command যোগ করুন: `git ls-files`-এর কত শতাংশ file-এর owner আছে, এবং owner-হীন directory-গুলোর তালিকা। Test লিখুন।
3. নিজের GitHub practice repository-তে Section 9.5-এর protection চালু করুন, তারপর `gh api` দিয়ে JSON নিয়ে `protection_check.py` চালান।
4. Branch protection চালু থাকা অবস্থায় `git push origin main` চেষ্টা করুন — কী error আসে, লিখে রাখুন।
5. একটি সহপাঠীর (বা নিজের পুরোনো) PR Section 8.2-এর ক্রম অনুযায়ী review করুন। প্রতিটি মন্তব্যকে "বাধ্যতামূলক" বা "nit" হিসেবে চিহ্নিত করুন।

## 15. Mini-project — Repository governance pack

এই repository (বা practice repo)-র জন্য একটি `.github/` pack তৈরি করুন:

- `CODEOWNERS` (lint পরিষ্কার, critical path-এর owner সহ)।
- `pull_request_template.md`।
- `CONTRIBUTING.md`-এর review অংশ (Section 8.2)।
- একটি CI step যা `codeowners.py lint --require ...` চালায়।
- `protection_check.py`-এর policy একটি config file-এ।

L03-06-এ এটি GitHub Actions workflow-এ যুক্ত হবে, এবং Module 06-এ পূর্ণ CI/CD pipeline-এর অংশ হবে।

## 16. Interview প্রশ্ন

1. Pull request workflow-এর উপকারিতা কী? সরাসরি main-এ push-এর ঝুঁকি কী?
2. Protected branch-এর কোন কোন setting আপনি সবসময় চালু রাখবেন এবং কেন?
3. CODEOWNERS কীভাবে কাজ করে? একাধিক pattern মিললে কোনটি জেতে?
4. "Dismiss stale approvals" কেন গুরুত্বপূর্ণ?
5. একটি ভালো code review-এ আপনি কী দেখেন?
6. Fork থেকে আসা PR-এর CI-তে secret কেন দেওয়া হয় না?
7. বড় PR কীভাবে ছোট করবেন?

## 17. Self-assessment প্রশ্ন

1. প্রেসক্রিপশন analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 9.1-এ `docs/guide.md`-এর owner কেন `@acme/docs` নয়?
3. Section 5-এর চারটি ফাঁক কী কী?
4. Owner-হীন CODEOWNERS লাইনের প্রভাব কী?
5. Reviewer কোন বিষয়গুলো automation-এর উপর ছেড়ে দেবেন?

## 18. সংক্ষিপ্ত সারাংশ

- PR = review + CI gate + আলোচনা + audit trail।
- ভালো PR ছোট, একটি বিষয়ে, স্পষ্ট বর্ণনা ও যাচাইয়ের প্রমাণ সহ।
- Protected branch-এ PR বাধ্যতামূলক; approval, stale approval বাতিল, code owner, status check, force push নিষেধ, এবং admin-রাও অন্তর্ভুক্ত।
- CODEOWNERS: gitignore-ধাঁচের pattern, শেষ match জেতে; CODEOWNERS ও workflow-এর নিজস্ব owner রাখুন।
- Review নিশ্চয়তা দেয় না — automation ও least privilege-এর সাথে একটি স্তর।
- Setting code ও policy check দিয়ে রাখুন, নিয়মিত audit করুন।

## 19. Completion checklist

- [ ] `codeowners.py owners`-এর output ব্যাখ্যা করতে পারি, বিশেষত "last match wins"
- [ ] Sample CODEOWNERS ঠিক করে lint পরিষ্কার করেছি (Exercise ১)
- [ ] GitHub practice repository-তে protection ও CODEOWNERS চালু করেছি
- [ ] একটি PR খুলে review ও merge প্রক্রিয়া সম্পূর্ণ করেছি
- [ ] `python3 -m unittest -v`-এ ৯টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GitHub — About pull requests: https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/proposing-changes-to-your-work-with-pull-requests/about-pull-requests
- GitHub — About code owners: https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-code-owners
- GitHub — About protected branches: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches/about-protected-branches
- GitHub — About rulesets: https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/about-rulesets
- GitHub REST API — Branch protection: https://docs.github.com/en/rest/branches/branch-protection
- GitHub CLI manual: https://cli.github.com/manual/
- Google Engineering Practices — Code review: https://google.github.io/eng-practices/review/

---

**পরের lesson:** L03-05 — Git recovery: reflog, reset, revert, bisect
