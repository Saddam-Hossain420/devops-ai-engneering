# Module 03 Progress — Git and Collaboration

Content status: `NOT_STARTED` · `IN_PROGRESS` · `COMPLETED` · `NEEDS_REVISION` (Claude update করবে)  
Learner status: Not started · In progress · Practiced · Assessment passed · Project completed · Needs revision (আপনি update করবেন)

| ID | Lesson | Content | Learner | Required files | Validation | Prerequisites | Next |
|---|---|---|---|---|---|---|---|
| L03-01 | [Git internals: object, commit, tree, ref](L03-01-git-internals.md) | COMPLETED | Not started | `L03-01-git-internals.md`, `code/L03-01/git_objects.py`, `make_demo_repo.sh`, `test_git_objects.py` | 8 unit test pass (আসল git 2.54-এর সাথে তুলনা); deterministic demo চালানো (একই hash দুবার); Ubuntu-তে চালানো হয়নি (OS-নির্ভর অংশ নেই) | L02-17 | L03-02 |
| L03-02 | [Branch, merge ও rebase](L03-02-branch-merge-rebase.md) | COMPLETED | Not started | `L03-02-branch-merge-rebase.md`, `code/L03-02/graph.py`, `conflict_markers.py`, `merge_vs_rebase.sh`, `test_l03_02.py` | 7 unit test pass (আসল git merge-base/rev-list-এর সাথে তুলনা, criss-cross সহ); deterministic demo চালানো; Ubuntu-তে চালানো হয়নি (OS-নির্ভর অংশ নেই) | L03-01 | L03-03 |
| L03-03 | [Remote, tag ও semantic versioning](L03-03-remotes-tags-semver.md) | COMPLETED | Not started | `L03-03-remotes-tags-semver.md`, `code/L03-03/semver.py`, `remote_demo.sh`, `test_semver.py` | 8 unit test pass (semver.org precedence উদাহরণ, আসল git tag); remote demo (local bare repo) চালানো; hosted remote/SSH push চালানো হয়নি | L03-02 | L03-04 |
| L03-04 | [Pull request, code review, protected branch, CODEOWNERS](L03-04-pull-requests-review.md) | COMPLETED | Not started | `L03-04-pull-requests-review.md`, `code/L03-04/codeowners.py`, `sample-CODEOWNERS`, `protection_check.py`, `sample-protection.json`, `pull_request_template.md`, `test_l03_04.py` | 9 unit test pass (GitHub doc-এর CODEOWNERS উদাহরণ, আসল git diff); owners/lint/protection চালানো; আসল GitHub repository/gh api চালানো হয়নি | L03-03 | L03-05 |
| L03-05 | [Git recovery: reflog, reset, revert, bisect](L03-05-git-recovery.md) | COMPLETED | Not started | `L03-05-git-recovery.md`, `code/L03-05/lost_commits.py`, `recovery_demo.sh`, `bisect_demo.sh`, `test_l03_05.py` | 7 unit test pass (আসল git: reset/branch/fsck, bisect→change 21); bisect-এর stale .pyc ফাঁদ ধরা ও ঠিক; Ubuntu-তে চালানো হয়নি | L03-04 | L03-06 |
| L03-06 | [GitHub Actions fundamentals](L03-06-github-actions-fundamentals.md) | COMPLETED | Not started | `L03-06-github-actions-fundamentals.md`, `code/L03-06/workflow_lint.py`, `sample-bad-workflow.yml`, `sample-good-workflow.yml`, `test_workflow_lint.py`; repo-র `validate.yml` ও CI template SHA-pinned; labs A/B/C (`labs/03-git-and-collaboration/`, Lab C-এর break-it/check/reset.sh); module quiz | 7 unit test pass; action SHA git ls-remote দিয়ে যাচাই; repo workflow-এর ত্রুটি ধরা ও ঠিক; Lab C break→সমাধান→check ALL PASSED (Windows); GitHub-এ workflow চালানো হয়নি | L03-05 | L04-01 |

## Module assessment

| Assessment | Score | তারিখ |
|---|---|---|
| [Module quiz](../assessments/03-git-and-collaboration/quiz.md) | — | — |
| [Level A lab](../labs/03-git-and-collaboration/A-inside-dot-git/README.md) | — | — |
| [Level B lab](../labs/03-git-and-collaboration/B-pr-to-release/README.md) | — | — |
| [Level C lab](../labs/03-git-and-collaboration/C-git-disaster-recovery/README.md) | — | — |
