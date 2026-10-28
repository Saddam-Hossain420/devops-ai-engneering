# Module 03 Quiz — Git and Collaboration

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৬০ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে module-এর tool ছাড়া উত্তর দিন, পরে tool দিয়ে মিলিয়ে নিন। Part C যেকোনো machine-এ (Git + Bash) — Part C-এর ৩৪ নম্বরে GitHub account লাগবে।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. Git-এর চার ধরনের object কী কী?
2. Branch আসলে কী, এবং branch তৈরি কেন তাৎক্ষণিক?
3. `git add`-এর সময় object database-এ কী লেখা হয়?
4. একটি পুরোনো file-এর একটি byte বদলালে পরের commit-গুলোর hash-এর কী হয়, এবং কেন?
5. Lightweight ও annotated tag-এর পার্থক্য; release-এ কোনটি?
6. Fast-forward merge কখন সম্ভব?
7. Merge base কী, এবং three-way merge-এ কেন লাগে?
8. Rebase কেন commit-এর hash বদলায়?
9. Rebase চলাকালীন conflict-এ "ours" কোন পক্ষ?
10. `--force-with-lease` `--force` থেকে কীভাবে নিরাপদ?
11. `git fetch` ও `git pull`-এর পার্থক্য।
12. `origin/main` কখন update হয়?
13. SemVer-এ MINOR কখন বাড়ে?
14. CODEOWNERS-এ একাধিক লাইন মিললে কোনটি কার্যকর?
15. "Dismiss stale approvals" কোন আক্রমণ বা ভুল আটকায়?
16. Reset ও revert-এর পার্থক্য; push হয়ে যাওয়া shared branch-এ কোনটি?
17. Commit না করা পরিবর্তন `reset --hard`-এর পরে উদ্ধারযোগ্য কি? Commit করা পরিবর্তন?
18. Reflog-এর দুটি সীমাবদ্ধতা।
19. GitHub Actions-এ script injection কী, এবং কীভাবে প্রতিরোধ করবেন?
20. Action-কে tag-এর বদলে commit SHA দিয়ে কেন pin করবেন?

## Part B — Calculation ও analysis (প্রতিটি ২ নম্বর)

21. `hello world\n` (১২ byte) file-এর blob ID হিসাব করতে SHA-1-এর input হুবহু কী হবে? (Hash নিজে হিসাব করার দরকার নেই।)
22. Three-way merge: base-এ একটি লাইন `timeout=30`, ours-এ `timeout=30`, theirs-এ `timeout=60`। ফল কী? যদি ours-এ `timeout=45` হতো?
23. এই version-গুলো SemVer precedence অনুযায়ী ছোট থেকে বড় সাজান: `2.0.0-rc.2`, `1.10.0`, `2.0.0`, `1.9.3`, `2.0.0-rc.10`, `2.0.0-beta`। `1.10.0` ও `1.10.0+build.7`-এর মধ্যে কোনটি বড়?
24. বর্তমান version `2.3.1`। পরের release-এর commit: (ক) `fix: a`, `docs: b`, `perf: c`; (খ) `fix: a`, এবং `refactor: config loader` যার footer-এ `BREAKING CHANGE: YAML replaces INI`; (গ) বর্তমান `0.9.0`, commit `feat!: new API` (০.x-এ breaking change-এ minor বাড়ানোর রীতি ধরে)। প্রতিটির পরের version?
25. ১০০০টি commit-এর পরিসরে `git bisect` দিয়ে দায়ী commit খুঁজতে আনুমানিক কতবার test চালাতে হবে? কেন?
26. CODEOWNERS:

    ```text
    *              @acme/platform
    /infra/        @acme/sre
    *.md           @acme/docs
    /infra/README.md
    ```

    `infra/README.md`, `infra/main.tf`, `docs/x.md`, `infra/notes.md` — প্রতিটির owner কে? কোনটি সম্ভবত অনিচ্ছাকৃত?
27. `main`: A–B–C। `feature`: B থেকে শাখা, D–E। `feature`, `main`-এর তুলনায় কত ahead ও behind? Merge base কোনটি? `main`-এ `git merge --ff-only feature` সফল হবে কি?
28. Reflog:

    ```text
    a1b2c3d HEAD@{0}: checkout: moving from fix/x to main
    9f8e7d6 HEAD@{1}: commit: fix: x
    a1b2c3d HEAD@{2}: checkout: moving from main to fix/x
    a1b2c3d HEAD@{3}: reset: moving to HEAD~1
    5e6f7a8 HEAD@{4}: commit: feat: y
    ```

    `fix/x` branch মুছে ফেলা হয়েছে, আর `feat: y` reset-এ হারিয়েছে। দুটি উদ্ধারের command লিখুন। `HEAD@{n}` ব্যবহার করা কেন ঝুঁকিপূর্ণ?
29. `git reset --soft HEAD~1`-এর পরে শেষ commit-এর পরিবর্তনগুলো কোথায় থাকে? `--mixed` হলে? `--hard` হলে?
30. Workflow-এর এই step-এর সমস্যা কী? ঠিক করে লিখুন।

    ```yaml
    - run: echo "Branch: ${{ github.head_ref }}"
    ```

## Part C — Practical

31. (৫ নম্বর) [Lab 03-C](../../labs/03-git-and-collaboration/C-git-disaster-recovery/README.md) সম্পূর্ণ করুন। `check.sh`-এর output, মোট সময়, এবং সহকর্মীর commit কোথা থেকে উদ্ধার করলেন তা লিখুন।
32. (৫ নম্বর) [`make_demo_repo.sh`](../../03-git-and-collaboration/code/L03-01/make_demo_repo.sh) দিয়ে demo বানান, তারপর `git_objects.py walk HEAD` এবং নিজের হাতে (`git cat-file`) একই গাছ বের করে মেলান। `src/app.py` বদলে commit করলে কোন কোন object নতুন হলো?
33. (৫ নম্বর) একটি regression-এর জন্য `git bisect run`। নিজের বা [`bisect_demo.sh`](../../03-git-and-collaboration/code/L03-05/bisect_demo.sh)-এর repository-তে চালান। Test-এ কোন জিনিস ফল ভুল করতে পারত, এবং কীভাবে তা এড়ালেন?
34. (৫ নম্বর) GitHub practice repository-তে protected `main` (PR, CI check, force push নিষেধ), CODEOWNERS ও lint-পরিষ্কার CI workflow। একটি PR merge করুন। `protection_check.py`-এর output ও PR link দিন।

---

<details>
<summary><strong>Answer key</strong></summary>

**Part A**

1. blob (file content), tree (directory), commit (snapshot + parent + author + message), tag (annotated)।
2. একটি commit-এর নাম, অর্থাৎ ৪১ byte-এর একটি file। কোনো file copy হয় না।
3. File content-এর blob object (zlib-compressed); index update হয়।
4. সব বদলায়: blob → তার tree → root tree → commit; এবং প্রতিটি পরের commit-এ parent-এর hash থাকে।
5. Lightweight = শুধু ref; annotated = নিজস্ব object (tagger, তারিখ, message, signature)। Release-এ annotated।
6. যখন target branch source-এর পূর্বপুরুষ, অর্থাৎ target সরেনি।
7. দুই branch-এর সর্বশেষ সাধারণ পূর্বপুরুষ। এটা ছাড়া জানা যায় না কোন দিক কী বদলেছে।
8. প্রতিটি commit-এর hash-এ parent-এর hash থাকে; নতুন base মানে নতুন parent, তাই নতুন hash।
9. যে base-এর উপর বসানো হচ্ছে (যেমন main) — merge-এর উল্টো।
10. Remote branch আপনার শেষ দেখা অবস্থা থেকে বদলে থাকলে push প্রত্যাখ্যান করে।
11. Fetch শুধু আনে (`origin/*` update করে); pull = fetch + merge/rebase।
12. Fetch, pull বা push-এর সময় — নিজে থেকে কখনো না।
13. নতুন backward-compatible feature যোগ হলে।
14. শেষ যে লাইন মেলে।
15. Approval-এর পরে চুপচাপ নতুন (সম্ভবত ক্ষতিকর বা ভুল) code ঢুকিয়ে merge করা।
16. Reset branch সরায় (history পুনর্লিখন); revert নতুন উল্টো commit যোগ করে। Shared branch-এ revert।
17. Commit না করা: না (শুধু `add` করা থাকলে blob থাকে, নাম ছাড়া)। Commit করা: হ্যাঁ, reflog থেকে।
18. শুধু local (অন্যের clone-এ নেই); মেয়াদ আছে (default ৯০/৩০ দিন); এছাড়া branch মুছলে তার নিজের reflog মুছে যায়।
19. Untrusted context (PR title, `head_ref`) `${{ }}` দিয়ে সরাসরি `run:`-এ বসে shell code হয়ে যায়। প্রতিরোধ: `env:` দিয়ে দিন, তারপর `"$VAR"`।
20. Tag সরানো যায় (এবং সত্যিই সরে — `v4` বনাম `v4.2.2`); SHA অপরিবর্তনীয়, তাই supply-chain সুরক্ষা।

**Part B**

21. `"blob 12\0hello world\n"`। (ফলাফল: `3b18e512dba79e4c8300dd08aeb37f8e728b8dad` — `git hash-object`-এ যাচাই করা।)
22. শুধু theirs বদলেছে → `timeout=60`। ours `45` হলে দুই দিকেই ভিন্ন পরিবর্তন → **conflict**।
23. `1.9.3` < `1.10.0` < `2.0.0-beta` < `2.0.0-rc.2` < `2.0.0-rc.10` < `2.0.0`। `1.10.0` ও `1.10.0+build.7` **সমান precedence** (build metadata উপেক্ষিত)।
24. (ক) `2.3.2` — fix ও perf দুটোই patch, docs কিছু না। (খ) `3.0.0` — footer-এর BREAKING CHANGE। (গ) `0.10.0`।
25. প্রায় **১০** বার — log₂(১০০০) ≈ ৯.৯৭; প্রতিবার পরিসর অর্ধেক হয়।
26. `infra/README.md` → **কোনো owner নেই** (শেষ লাইন, owner-হীন)। `infra/main.tf` → `@acme/sre`। `docs/x.md` → `@acme/docs`। `infra/notes.md` → `@acme/docs` (`*.md`, `/infra/`-এর পরে লেখা)। সম্ভবত অনিচ্ছাকৃত: infra-র markdown file SRE-র review এড়ায়, আর README-র কোনো owner নেই। (module-এর `codeowners.py` দিয়ে যাচাই করা।)
27. ২ ahead (D, E), ১ behind (C)। Merge base B। `--ff-only` **ব্যর্থ** হবে, কারণ branch diverged।
28. `git branch fix/x 9f8e7d6` এবং `git branch rescue/y 5e6f7a8` (বা `git reset --hard 5e6f7a8`, যদি working tree পরিষ্কার থাকে)। `HEAD@{n}` প্রতিটি নতুন checkout/commit-এ সরে যায় — SHA স্থির।
29. Soft: staged (index)-এ। Mixed: working tree-তে, unstaged। Hard: কোথাও না — তবে commit-টি reflog-এ থাকে।
30. `head_ref` attacker-নিয়ন্ত্রিত (branch-এর নাম), তাই script injection। ঠিক রূপ:

    ```yaml
    - env:
        BRANCH: ${{ github.head_ref }}
      run: echo "Branch: $BRANCH"
    ```

**Part C — গ্রহণযোগ্য উত্তরের বৈশিষ্ট্য:**

- আসল command ও output থাকতে হবে।
- Lab C: force push বা history পুনর্লিখন ছাড়া; reflog-এর সংখ্যা নয়, SHA দিয়ে উদ্ধার। সহকর্মীর commit তাঁর clone বা origin-এর dangling object থেকে, এবং `pull --rebase`-এর fork-point ফাঁদের উল্লেখ।
- Demo: নতুন blob, `src/` tree, root tree ও commit চিহ্নিত।
- Bisect: deterministic test, `python -B`/cache পরিষ্কার, শেষে `bisect reset`।
- GitHub: protection JSON-এ অন্তত PR, check ও force push নিষেধ PASS।

</details>
