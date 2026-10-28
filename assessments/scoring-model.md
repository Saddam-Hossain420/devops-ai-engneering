# Scoring model

সব module quiz, stage exam, lab ও project একই মাপকাঠিতে মূল্যায়ন হয়।

| ক্ষেত্র | ওজন | কী দেখা হয় |
|---|---|---|
| Conceptual understanding | 20% | নিজের ভাষায় কেন ও কীভাবে ব্যাখ্যা করতে পারা; analogy-র সীমা জানা |
| Hands-on implementation | 30% | কাজ করা code/config; নিজে চালানো ও যাচাই |
| Troubleshooting and debugging | 20% | symptom থেকে প্রমাণভিত্তিক কারণ খোঁজা; সঠিক tool |
| Security and reliability | 15% | least privilege, secret handling, failure handling, rollback |
| Documentation and engineering judgment | 15% | পরিষ্কার README/runbook; trade-off ব্যাখ্যা; অপ্রয়োজনীয় জটিলতা এড়ানো |

## প্রতিটি ক্ষেত্রের score (0–4)

| Score | অর্থ |
|---|---|
| 4 | স্বাধীনভাবে, সঠিকভাবে, ব্যাখ্যা সহ; edge case জানে |
| 3 | সঠিক, সামান্য সাহায্যে |
| 2 | আংশিক; গুরুত্বপূর্ণ ফাঁক আছে |
| 1 | মূলত ভুল বা অন্যের থেকে copy, ব্যাখ্যা করতে পারে না |
| 0 | চেষ্টা নেই |

**হিসাব:** মোট % = Σ (score ÷ 4 × ওজন)।

উদাহরণ: concept 3, hands-on 4, troubleshooting 2, security 3, docs 3 →
(3/4×20) + (4/4×30) + (2/4×20) + (3/4×15) + (3/4×15) = 15 + 30 + 10 + 11.25 + 11.25 = **77.5%**

## Pass mark

| Assessment | Pass |
|---|---|
| Lesson self-assessment | সব প্রশ্নের নিজের উত্তর লেখা |
| Module quiz | ≥ 70% |
| Stage exam | ≥ 70%, এবং কোনো ক্ষেত্রে score 1 বা 0 নয় |
| Capstone | ≥ 75% |

## সততার নিয়ম

- কোনো lab বা assessment "pass" লেখা হবে না যদি তার check আসলে চালানো না হয়।
- Fail হলে status `Needs revision`, এবং কোন ক্ষেত্রে দুর্বল তা PROGRESS-এ লিখুন।
