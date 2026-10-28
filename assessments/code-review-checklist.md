# Code review checklist

## Correctness

- [ ] Code যা দাবি করে তা-ই করে? Test দিয়ে প্রমাণিত?
- [ ] Edge case: খালি input, বড় input, network failure, timeout
- [ ] Error হলে চুপচাপ ব্যর্থ হয় না — log করে ও সঠিক exit code দেয়

## Readability

- [ ] নাম অর্থবহ; function ছোট ও একটি কাজ করে
- [ ] Comment "কেন" ব্যাখ্যা করে, "কী" নয়
- [ ] আশেপাশের code-এর style মেনে চলে

## Operations

- [ ] আবার চালানো নিরাপদ (idempotent) বা কেন নয় তা লেখা
- [ ] Timeout ও retry যুক্তিসঙ্গত (অসীম retry নয়)
- [ ] Log-এ যথেষ্ট context আছে, কিন্তু secret নেই
- [ ] Configuration hard-code নয় (env var / config file)

## Bash-specific

- [ ] `shellcheck` পরিষ্কার
- [ ] Variable quote করা (`"$var"`)
- [ ] Strict mode ও তার সীমাবদ্ধতা বিবেচিত
- [ ] Temp file `mktemp` দিয়ে, `trap` দিয়ে cleanup

## Python-specific

- [ ] Type hint
- [ ] `subprocess` list argument দিয়ে, `shell=True` নয় (কারণ ছাড়া)
- [ ] HTTP call-এ timeout
- [ ] Dependency pin করা

## Infrastructure code

- [ ] `terraform fmt`/`validate`, `ansible-lint`, `helm lint`, `kubectl --dry-run=server` যা প্রযোজ্য
- [ ] Image tag `latest` নয়
- [ ] Resource-এ tag/label আছে
