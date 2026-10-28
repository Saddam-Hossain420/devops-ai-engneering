# Lab 03-A — Inside `.git`: object database অনুসন্ধান

| | |
|---|---|
| **Level** | A — Fundamentals |
| **সময়** | ৪৫–৬০ মিনিট |
| **Environment** | Git ২.৩০+, Bash, Python ৩.১০+ (Ubuntu, Fedora বা Git Bash) |
| **Label** | — (শুধু demo repository; system পরিবর্তন নেই) |

## Objective

একটি নির্দিষ্ট (deterministic) demo repository-তে `git` command ও `git_objects.py` দুটো দিয়ে একই প্রশ্নের উত্তর মেলানো:

- `git add` ও `git commit`-এ `.git`-এ কী কী নতুন জিনিস তৈরি হয়?
- অপরিবর্তিত file-এর blob কীভাবে ভাগ হয়?
- `amend` কেন নতুন commit তৈরি করে?

## Prerequisites

- Lesson: [L03-01](../../../03-git-and-collaboration/L03-01-git-internals.md)
- File: [`make_demo_repo.sh`](../../../03-git-and-collaboration/code/L03-01/make_demo_repo.sh), [`git_objects.py`](../../../03-git-and-collaboration/code/L03-01/git_objects.py)

## Environment setup

```bash
C=~/devops-ai-engineering/03-git-and-collaboration/code/L03-01
bash $C/make_demo_repo.sh ~/lab03a
export GIT_CONFIG_GLOBAL=~/lab03a/.empty-gitconfig GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME="Lab User" GIT_AUTHOR_EMAIL=lab@example.com GIT_COMMITTER_NAME="Lab User" GIT_COMMITTER_EMAIL=lab@example.com
cd ~/lab03a/demo
mkdir -p ~/devops-notebook/labs/03-A
```

## Steps

1. **গণনা:** `find .git/objects -type f | wc -l` — কতটি object? প্রতিটির ধরন বের করুন:

   ```bash
   for f in $(find .git/objects -type f); do s=$(echo "$f" | sed 's|.git/objects/||; s|/||'); echo "$s $(git cat-file -t $s)"; done
   ```

   Blob, tree, commit ও tag মিলিয়ে কতটি?
2. **`git add`-এর প্রভাব:** `echo "notes" > notes.txt`, তারপর `git add notes.txt` — `git hash-object notes.txt` ও `python3 $C/git_objects.py hash notes.txt` মেলান। কোন file নতুন হলো?
3. **Commit-এর প্রভাব:** `git commit -m "docs: notes"` — এবার কয়টি নতুন object (blob, tree, commit)? কেন `src/` tree নতুন হয়নি?
4. **গাছ দেখা:** `python3 $C/git_objects.py walk HEAD` ও `python3 $C/git_objects.py walk HEAD~1` — কোন blob ও tree দুই commit-এ ভাগ হয়েছে?
5. **Amend:** `git commit --amend -m "docs: add notes"` — `git rev-parse HEAD` বদলাল কেন? পুরোনো commit কোথায় দেখা যায় (`git reflog -3`)?
6. **Tag:** `python3 $C/git_objects.py refs` — `v1.0.0` কোন ধরনের object-কে নির্দেশ করে? `git cat-file -p v1.0.0`।
7. **Pack:** `git gc -q`, তারপর `git count-objects -v`। `git_objects.py cat HEAD` কী বলে, এবং `git cat-file -p HEAD` কেন এখনো কাজ করে?

## Expected behavior

- শুরুতে ১০টি object: ৩ blob, ৪ tree, ২ commit, ১ tag (L03-01 Section 9.4)।
- Step 2-এর পরে ১১টি object — `git add`-ই notes-এর blob লিখেছে। Step 3-এর পরে ১৩টি — commit-এ মাত্র ২টি নতুন (root tree ও commit); `src/` tree ও পুরোনো blob অপরিবর্তিত, ভাগ করা। (এই সংখ্যাগুলো Windows/Git Bash-এ আসলে মেলানো হয়েছে।)
- Amend-এর পরে HEAD-এর hash বদলায়; পুরোনো commit reflog-এ থাকে।

## Verification

```bash
git hash-object hello.txt                                          # ce013625030ba8dba906f756967f9e9ca394464a
git log --oneline v1.0.0 -1                                        # bea3fb5 change app
python3 $C/git_objects.py walk HEAD | grep -c "hello.txt"          # 1
test -s ~/devops-notebook/labs/03-A/answers.md && echo "notes written"
```

## Troubleshooting

| সমস্যা | কারণ | সমাধান |
|---|---|---|
| Hash L03-01-এর থেকে ভিন্ন | `make_demo_repo.sh` ছাড়া নিজে তৈরি, বা line ending রূপান্তর | Script ব্যবহার করুন; Windows-এ `core.autocrlf` বন্ধ রাখুন (script নিজেই global config বাদ দেয়) |
| `git_objects.py cat` → "not a loose object" | `git gc`-এর পরে packed | প্রত্যাশিত (Step 7); `git cat-file` ব্যবহার করুন |
| `Author identity unknown` | Lab-এর আলাদা config-এ নাম নেই | Environment setup-এর `GIT_AUTHOR_*` export করুন |

## Cleanup / reset

```bash
rm -rf ~/lab03a
```

## Assessment

1. `git add` ও `git commit` প্রত্যেকে কোন object তৈরি করে? আপনার গণনা দিয়ে দেখান।
2. Amend কেন "পুরোনো commit বদলানো" নয়, বরং নতুন commit? (Hash শৃঙ্খল)
3. একটি ১ GB-র binary file তিনবার সামান্য বদলে commit করলে repository-তে কী হয় (`gc`-এর আগে ও পরে)?
