<!-- নমুনা PR template — নিজের repository-তে `.github/pull_request_template.md` হিসেবে রাখুন -->

## কী ও কেন

<!-- এক-দুই বাক্যে: কোন সমস্যা, কোন সমাধান। Issue/ticket link। -->

## পরিবর্তনের ধরন

- [ ] `fix` — bug fix (PATCH)
- [ ] `feat` — নতুন feature, backward-compatible (MINOR)
- [ ] **Breaking change** (MAJOR) — commit-এ `!` বা `BREAKING CHANGE:` footer দেওয়া হয়েছে
- [ ] `docs` / `chore` / `refactor` / `test` — release নয়

## কীভাবে যাচাই করা হয়েছে

<!-- কোন test, কোন command, আসল output। "Works on my machine" নয়। -->

## Reviewer-এর জন্য ঝুঁকি ও মনোযোগের জায়গা

- [ ] Database migration / data পরিবর্তন
- [ ] Configuration, secret বা permission পরিবর্তন
- [ ] Infrastructure / network / firewall পরিবর্তন
- [ ] Rollback পরিকল্পনা: <!-- কীভাবে ফেরানো যাবে -->

## Checklist

- [ ] PR ছোট ও একটি বিষয়ে (≈ ৪০০ লাইনের কম পরিবর্তন)
- [ ] Test যোগ/আপডেট করা হয়েছে, CI সবুজ
- [ ] কোনো secret, token, `.env` বা private key নেই
- [ ] Documentation/CHANGELOG আপডেট (দরকার হলে)
