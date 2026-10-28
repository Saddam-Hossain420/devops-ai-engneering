# Module 07 Quiz — Cloud Fundamentals

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৭৫ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে tool না চালিয়ে উত্তর দিন, পরে module-এর tool দিয়ে যাচাই করুন।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

Part B-এর দাম `example-prices.json`-এর উদাহরণ-দাম — আসল নয়।

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. Type 1 ও type 2 hypervisor-এর পার্থক্য কী? KVM কোনটি, এবং কেন বিতর্ক আছে?
2. CPU steal time কী? কোথায় দেখবেন?
3. CPU overcommit ও memory overcommit-এর মধ্যে কোনটি বেশি বিপজ্জনক, কেন?
4. Windows-এ `HypervisorPresent=True` হলে কি machine-টি VM? ব্যাখ্যা করুন।
5. IaaS, PaaS, FaaS ও SaaS — প্রতিটিতে OS patch কার দায়িত্ব?
6. কোন তিনটি দায়িত্ব কোনো service model-এই provider-এর কাছে যায় না?
7. Provider-এর একটি AZ বন্ধ হলে আপনার service down হলো। দায়িত্ব কার, কেন?
8. Region, availability zone ও data center-এর সম্পর্ক কী?
9. Correlated failure কী? একটি উদাহরণ দিন।
10. দুটি instance একই AZ-এ রাখলে "স্বাধীন" ধরে availability হিসাব করা ভুল কেন?
11. Public subnet ও private subnet-কে কী আলাদা করে?
12. NAT gateway কী কাজ করে? Inbound connection কি এর মধ্য দিয়ে আসতে পারে?
13. Private endpoint (VPC endpoint) কেন ব্যবহার করবেন — দুটি কারণ বলুন।
14. VPC CIDR বাছাইয়ের সময় overlap কেন ভবিষ্যতের সমস্যা?
15. IAM-এ explicit deny, explicit allow ও implicit deny-এর ক্রম কী?
16. User-এর long-lived access key-এর বদলে role কেন?
17. `iam:PassRole` কেন privilege escalation-এর পথ?
18. Instance "stop" করলে কোন কোন খরচ চলতে থাকে?
19. On-demand, reserved/savings ও spot — কোনটি কোন workload-এর জন্য?
20. Budget alert কেন "জাল, প্রতিরোধ নয়"?

## Part B — Output prediction (প্রতিটি ২ নম্বর)

21. `policy_eval.py`-এর ফল কী — allow না deny, এবং কোন statement-এর কারণে?

    ```json
    {"Statement": [
      {"Effect": "Allow", "Action": "s3:GetObject", "Resource": "arn:aws:s3:::tf-uploads/u/*"},
      {"Sid": "NoAdmin", "Effect": "Deny", "Action": "s3:*", "Resource": "arn:aws:s3:::tf-uploads/u/admin/*"}
    ]}
    ```

    Request: `s3:GetObject` on `arn:aws:s3:::tf-uploads/u/admin/report.csv`।

22. একই policy-তে request `s3:PutObject` on `arn:aws:s3:::tf-uploads/u/42/a.png`। ফল কী?

23. Policy: `{"Effect": "Allow", "NotAction": ["iam:*"], "Resource": "*"}`। `sts:AssumeRole` allowed? `policy_lint.py` কী মাত্রা দেবে?

24. একটি Deny statement-এর condition `{"Bool": {"aws:MultiFactorAuthPresent": "false"}}`। একটি CI role (MFA-র কোনো key নেই) সেই action চাইলে Deny খাটবে? `BoolIfExists` হলে?

25. `availability.py`-তে spec: lb ১টি (AZ a), app ২টি (দুটিই AZ a), db ১টি (AZ a)। `SPOF` লাইন কয়টি আসবে, কোন কোন tier-এর?

26. `subnet_plan.py`-এর `prefix_for`: provider প্রতি subnet-এ ৫টি address রাখে। ১০০ host-এর জন্য কোন prefix? ২৫২ host-এর জন্য?

27. `virt_probe.py overcommit --host-cores 8 --vcpus 12 --host-ram-gb 16 --vm-ram-gb 18` — দুটি অনুপাত কত, এবং কোনটি নিয়ে সতর্কবার্তা আসবে?

28. `cost_estimate.py`-এ resource: `{"name": "d", "env": "dev", "type": "small-vm", "count": 2, "storage_gb": 50}`; উদাহরণ-দাম small-vm ০.০২/ঘণ্টা, storage ০.১০/GB-মাস। মাসিক খরচ কত? `--schedule-dev 12x22` দিলে কত?

29. `tag_audit.py --today 2026-10-28`-এ একটি instance-এর `expires` tag `2026-10-28`। Finding আসবে? `--today 2026-10-29` হলে?

30. Inventory-তে একটি volume `attached_to: i-x`, এবং `i-x`-এর `state: stopped`। আরেকটি volume-এ `attached_to` নেই। `tag_audit.py` দুটির জন্য কী বলবে?

## Part C — Scenario (প্রতিটি ৪ নম্বর)

31. Team বলছে, "আমরা দুটি app server রেখেছি, তাই highly available।" দুটিই একই AZ-এ, database একটি। কী ভুল, কীভাবে সংখ্যা দিয়ে দেখাবেন, এবং কী বদলাবেন?

32. Private subnet-এর app server-গুলো প্রতি মাসে কয়েক TB data object storage-এ পাঠায়। বিলে NAT-এর খরচ সবচেয়ে বড় লাইনগুলোর একটি। কারণ কী, এবং কী করবেন?

33. একটি developer-এর access key GitHub-এ ফাঁস হয়েছে; key-তে `AdministratorAccess`। প্রথম এক ঘণ্টায় কী করবেন, এবং ভবিষ্যতে কী বদলাবেন?

34. মাসের বিল আগের মাসের দ্বিগুণ। কোনো tag নেই। কীভাবে কারণ খুঁজবেন, এবং কী নিয়ম চালু করবেন?

35. CTO জানতে চান, "সব কিছু cloud-এ নিলে কি সস্তা ও নিরাপদ হবে?" একটি সৎ, কাঠামোবদ্ধ উত্তর দিন।

---

## Answer key

<details><summary>Part A</summary>

1. Type 1 সরাসরি hardware-এ চলে (ESXi, Xen, Hyper-V)। Type 2 একটি সাধারণ OS-এর ওপর application হিসেবে চলে (VirtualBox)। KVM Linux kernel-এর module — kernel নিজেই hypervisor হয়ে যায়, তাই সাধারণত type 1 ধরা হয়, যদিও host-এ পূর্ণ OS চলে।
2. Guest-এর vCPU চলতে প্রস্তুত ছিল, কিন্তু hypervisor তখন অন্য guest-কে physical CPU দিয়েছে — সেই অপেক্ষার সময়। Guest-এ `top`-এর `%st`, `/proc/stat`-এর ৮ম কলাম, বা `virt_probe.py steal`।
3. Memory। CPU overcommit-এ শুধু সময় ভাগ হয় (ধীর হয়)। Memory overcommit-এ host ballooning বা swap করে — সব guest ধীর হয়, OOM-এর ঝুঁকিও।
4. না, নিশ্চিত নয়। Hyper-V/VBS/WSL2 চালু থাকলে Windows নিজেই root partition-এ চলে — physical machine, কিন্তু hypervisor উপস্থিত। Guest কিনা জানতে manufacturer/model দেখুন (L07-01)।
5. IaaS: customer; PaaS: provider; FaaS: provider; SaaS: provider। (On-prem: সবই customer।)
6. Identity (কে access পায়, MFA, key), data (শ্রেণিবিভাগ, backup নীতি, encryption-এর সিদ্ধান্ত), configuration/endpoint — যেকোনো তিনটি। SaaS-এও এগুলো আপনার।
7. AZ-এর hardware provider-এর দায়িত্ব। কিন্তু একটি AZ গেলেও service চালু রাখা (resilience, architecture) IaaS-এ customer-এর দায়িত্ব — L07-02-এর `resilience` layer।
8. Region = একটি ভৌগোলিক এলাকা। তার ভেতরে কয়েকটি AZ — প্রতিটি AZ এক বা একাধিক data center, আলাদা বিদ্যুৎ, cooling ও network, কিন্তু কম-latency link দিয়ে যুক্ত।
9. একটি কারণে একাধিক component একসাথে ব্যর্থ হওয়া — একই AZ-এর বিদ্যুৎ বিভ্রাট, একই rack, একই ভুল config push, একই software bug, একই certificate-এর মেয়াদ।
10. AZ গেলে দুটি instance একসাথে যায়। Instance-গুলোকে স্বাধীন ধরলে AZ-এর ব্যর্থতা প্রতিটিতে আলাদাভাবে গোনা হয়, অথচ আসলে একবারই ঘটে এবং দুটিকেই নামায়। L07-03-এ same-AZ জোড়ার সঠিক downtime বছরে ৯.০ ঘণ্টা, naive হিসাবে মাত্র ১৯ মিনিট।
11. Route table: public subnet-এর default route internet gateway-তে যায়; private subnet-এর যায় NAT-এ বা কোথাও না। শুধু public IP থাকা যথেষ্ট নয়।
12. Private subnet-এর instance-কে outbound internet দেয় (update, API call), source address বদলে। নতুন inbound connection এর মধ্য দিয়ে আসতে পারে না।
13. Traffic provider-এর network-এই থাকে (internet বা NAT হয়ে যায় না), এবং NAT-এর data processing খরচ কমে। বাড়তি সুবিধা: endpoint policy দিয়ে শুধু নিজের bucket-এ সীমিত রাখা।
14. পরে VPC peering, VPN বা অফিস network-এর সাথে যুক্ত করতে হলে overlapping range route করা যায় না। আবার address দিতে হয়, যা migration।
15. প্রথমে explicit deny (যেকোনো একটি থাকলেই deny); তারপর কোনো allow থাকলে allow; কিছুই না মিললে implicit deny।
16. Role-এর credential অস্থায়ী (মেয়াদ শেষে বাতিল) ও স্বয়ংক্রিয়ভাবে rotate হয়; code বা disk-এ রাখতে হয় না, তাই ফাঁস হলে ক্ষতি সময়ে সীমিত। Long-lived key বছরের পর বছর বৈধ থাকে।
17. যে নিজে admin নয়, সে admin role-কে একটি নতুন instance বা function-এ "pass" করে সেই compute-এর মাধ্যমে admin ক্ষমতা পেতে পারে। তাই resource নির্দিষ্ট role-এ ও `iam:PassedToService` দিয়ে সীমিত রাখুন।
18. Attached disk (volume), snapshot, public IP (প্রায়ই), এবং load balancer বা NAT-এর মতো আলাদা resource। শুধু compute-এর ঘণ্টা থামে।
19. On-demand — অনিশ্চিত বা নতুন workload। Reserved/savings — মেপে দেখা স্থির baseline। Spot — stateless, পুনরায় চালানো যায় এমন batch/CI কাজ; database নয়।
20. Billing data কয়েক ঘণ্টা দেরিতে আসে, এবং alert শুধু জানায়, কিছু থামায় না। প্রতিরোধ হলো IAM least privilege, অব্যবহৃত region বন্ধ (SCP) ও quota।

</details>

<details><summary>Part B</summary>

21. **Deny** — `explicit deny by NoAdmin`। Resource Allow-এর `u/*`-এও মেলে, কিন্তু explicit deny সবসময় জেতে।
22. **Deny** — implicit deny। Allow শুধু `s3:GetObject`-এর জন্য।
23. **Allowed** — `NotAction ["iam:*"]` মানে iam ছাড়া সব, তাই sts-ও অন্তর্ভুক্ত। `policy_lint.py`: **CRITICAL** — "Allow + NotAction on "*" — effectively administrator (kms, organizations, sts still allowed)"।
24. **`Bool`:** key নেই, তাই condition মিথ্যা — Deny **খাটবে না** (Lab 07-C-এর ফাঁদ)। **`BoolIfExists`:** key না থাকলে শর্তটি বাদ পড়ে — Deny **খাটবে**।
25. **তিনটি:**
    - lb: ১টি instance, সবটাই দরকার;
    - app: দুটিই AZ a-তে;
    - db: ১টি instance।
26. ১০০ + ৫ = ১০৫ → ১২৮ → **/25**। ২৫২ + ৫ = ২৫৭ > ২৫৬ → **/23**। ২৫১ পর্যন্ত /24-এ ধরে।
27. vCPU:pCPU = ১২/৮ = **১.৫**; memory = ১৮/১৬ ≈ **১.১২**। সতর্কবার্তা আসবে **memory**-র জন্য (১-এর বেশি)। CPU-র সতর্কতা আসে ৪:১-এর বেশি হলে।
28. Compute: ২ × ৭৩০ × ০.০২ = ২৯.২০। Storage: ২ × ৫০ × ০.১০ = ১০.০০। মোট **৩৯.২০** (উদাহরণ)।
    `12x22`-এ compute ২ × ২৬৪ × ০.০২ = ১০.৫৬; storage বদলায় না (১০.০০); মোট **২০.৫৬**।
29. ২৮ তারিখে **না** — মেয়াদের দিনেই resource বৈধ। ২৯ তারিখে **হ্যাঁ** — `expired 1 day(s) ago`।
30. প্রথমটি: `stopped-instance-volume` — "… GB still billed while i-x is stopped"। দ্বিতীয়টি: `unattached-volume` — "… GB billed, attached to nothing"। Required tag না থাকলে `missing-tags`-ও আসবে।

</details>

<details><summary>Part C — মূল্যায়নের মূল বিষয়</summary>

31. **Correlated failure ও SPOF।**
    - দুটি app-ই এক AZ-এ — AZ গেলে দুটিই যায়। Database একটি — নিজেই SPOF।
    - সংখ্যা দিয়ে দেখানো: L07-03-এর `availability.py`-তে spec লিখুন, `--compare-naive` দিয়ে দেখান naive হিসাব কতটা আশাবাদী; `SPOF` লাইনগুলো দেখান।
    - বদল: app ও load balancer দুটি AZ-এ, database multi-AZ (standby)।
    - খরচের সাথে তুলনা (L07-06): downtime-এর দাম বনাম অতিরিক্ত খরচ।
32. **NAT-এর data processing চার্জ ও private endpoint।**
    - প্রতিটি GB NAT দিয়ে যায় এবং processing চার্জ লাগে।
    - Object storage-এর জন্য VPC endpoint (gateway/interface) — traffic NAT-এ যায় না। Endpoint policy দিয়ে শুধু নিজের bucket।
    - পরিবর্তনের পরে বিলে বা flow log-এ যাচাই করুন।
33. **Incident response — আগে ধারণ, পরে তদন্ত।**
    - **ধারণ:** key সাথে সাথে deactivate বা মুছুন; repo থেকে সরানোই যথেষ্ট নয় — history ও fork-এ থাকে।
    - **তদন্ত:** CloudTrail-এ সেই key-এর সব কাজ দেখুন — নতুন user/key/role, অন্য region-এ instance, data access। তৈরি হওয়া resource বন্ধ করুন। বিল ও budget দেখুন।
    - **ভবিষ্যৎ:**
      - human-এর long-lived key নয় — SSO বা অস্থায়ী credential;
      - least privilege;
      - MFA;
      - repo-তে secret scan (L05-10) ও push protection;
      - budget alert;
      - অব্যবহৃত region বন্ধ।
34. **Cost explorer ও tagging।**
    - সাময়িক উপায়: service, region ও resource-ভিত্তিক breakdown দিয়ে দেখুন কোন service ও region বেড়েছে; audit log দিয়ে কে বানিয়েছে।
    - Inventory-তে `tag_audit.py`-এর মতো audit: stopped instance-এর disk, অনাথ resource, পুরোনো snapshot।
    - নিয়ম:
      - বাধ্যতামূলক tag (owner, env, cost-center, expires — YYYY-MM-DD) IaC বা policy দিয়ে;
      - forecast-ভিত্তিক budget alert;
      - সাপ্তাহিক cleanup review;
      - non-prod schedule।
35. **"নির্ভর করে" — কিন্তু কাঠামো দিয়ে।**
    - **খরচ:** TCO তুলনা করুন — hardware, বিদ্যুৎ, মানুষের সময় বনাম cloud বিল (data transfer ও managed service সহ)। স্থির, বড় workload-এ on-prem সস্তা হতে পারে; পরিবর্তনশীল load-এ cloud।
    - **নিরাপত্তা:** shared responsibility — physical ও hypervisor provider নেয়, কিন্তু identity, data ও configuration আপনার। বেশিরভাগ cloud incident ভুল configuration ও credential থেকে।
    - **ঝুঁকি:** vendor lock-in, দক্ষতা, data residency।
    - **প্রস্তাব:** একটি workload দিয়ে pilot, মাপা সংখ্যা দিয়ে সিদ্ধান্ত (Lab 07-B)।

</details>

## Scoring

| অংশ | নম্বর |
|---|---|
| Part A | ২০ × ১ = ২০ |
| Part B | ১০ × ২ = ২০ |
| Part C | ৫ × ৪ = ২০ |
| **মোট** | **৬০** — pass ≥ ৪২ |

ফল [07-cloud-fundamentals/PROGRESS.md](../../07-cloud-fundamentals/PROGRESS.md)-এর Module assessment table-এ লিখুন।
