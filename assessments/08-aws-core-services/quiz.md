# Module 08 Quiz — AWS Core Services

- **Pass mark:** ≥ 70% ([scoring model](../scoring-model.md))
- **সময়:** ৭৫ মিনিট
- **নিয়ম:** আগে নিজে উত্তর লিখুন, তারপর answer key। Part B-তে tool না চালিয়ে উত্তর দিন, পরে module-এর tool দিয়ে যাচাই করুন।

মোট নম্বর: ৬০ (Part A ২০ + Part B ২০ + Part C ২০)

---

## Part A — Concept (প্রতিটি ১ নম্বর)

1. Root user দিয়ে দৈনন্দিন কাজ কেন নয়? Root-কে IAM policy দিয়ে সীমিত করা যায় না কেন?
2. Budget-এর ACTUAL ও FORECASTED alert-এর পার্থক্য কী? Budget কি খরচ থামায়?
3. `AKIA…` ও `ASIA…` access key-এর পার্থক্য কী? দ্বিতীয়টির সাথে আর কী লাগে?
4. AWS CLI-তে named profile কি `[default]`-এর region পায়?
5. boto3-এ paginator কেন দরকার?
6. IAM role-এর trust policy ও permission policy-র পার্থক্য কী?
7. Instance profile কী? এতে কয়টি role থাকে?
8. `iam:PassRole` কেন EC2 চালু করতে লাগে, আর কেন ঝুঁকিপূর্ণ?
9. একটি subnet public না private, AWS-এ কী দিয়ে ঠিক হয়?
10. NAT gateway কোন subnet-এ বসে, কেন?
11. Main route table-এর ঝুঁকি কী?
12. Security group ও network ACL-এর তিনটি পার্থক্য বলুন।
13. Firewall-এ আটকানো traffic-এ client timeout পায়, "connection refused" নয় — কেন?
14. EC2 user data কখন, কোন user হিসেবে চলে? সীমা কত? Secret কেন নয়?
15. IMDSv2 কোন আক্রমণ কঠিন করে, কীভাবে?
16. Instance stop করলে কোন খরচ চলে? Terminate করলে কখন volume থেকে যায়?
17. EBS volume কেন অন্য AZ-এর instance-এ attach করা যায় না? কীভাবে সরাবেন?
18. Versioned S3 bucket সম্পূর্ণ মুছতে `aws s3 rm --recursive` কেন যথেষ্ট নয়?
19. Route 53 alias record ও CNAME-এর দুটি পার্থক্য বলুন।
20. EC2-এর কোন metric AWS নিজে দেয় না? কীভাবে পাবেন?

## Part B — Output prediction (প্রতিটি ২ নম্বর)

21. `trust_policy_lint.py` এই trust policy-তে কী বলবে, কেন?

    ```json
    {"Effect": "Allow",
     "Principal": {"Federated": "arn:aws:iam::111122223333:oidc-provider/token.actions.githubusercontent.com"},
     "Action": "sts:AssumeRoleWithWebIdentity",
     "Condition": {"StringEquals": {"token.actions.githubusercontent.com:aud": "sts.amazonaws.com"}}}
    ```

22. Terminal-এ `AWS_PROFILE=learn-admin` (SSO profile) আর `AWS_ACCESS_KEY_ID=ASIA…` দুটোই set। `aws s3 ls` (কোনো `--profile` নয়) কোন credential ব্যবহার করবে? `aws_config_audit.py --which`-এর উত্তর কী?

23. একটি subnet-এর নিজের route table association নেই। VPC-র main route table-এ আছে `10.0.0.0/16 → local` ও `0.0.0.0/0 → igw-1`। `vpc_audit.py` subnet-টিকে কী শ্রেণি দেবে, এবং কোন দুটি finding দেবে?

24. ALB (public subnet, NACL সব allow) → app (8000)। App-এর SG ALB-এর SG থেকে 8000 allow করে। App subnet-এর NACL: inbound সব allow, outbound **শুধু TCP 443 to 0.0.0.0/0**। `sg_reach.py check` কোন ধাপে `XX` দেখাবে?

25. একটি instance-এ `HttpTokens=optional` এবং একটি instance profile আছে। `ec2_audit.py` IMDS-এর জন্য কোন মাত্রা দেবে? Instance profile না থাকলে?

26. `/etc/fstab`-এর এই লাইনে `fstab_lint.py` কয়টি ERROR দেবে, কী কী?

    ```text
    /dev/xvdf  /data  ext4  defaults  0 2
    ```

27. Bucket policy-তে `Allow`, `Principal "*"`, `s3:GetObject`, কিন্তু condition `StringEquals aws:SourceVpce = vpce-1`। `s3_audit.py` কি একে "everyone"-এর জন্য খোলা বলবে? কেন?

28. Target group: interval ৩০ s, UnhealthyThresholdCount ৩, HealthyThresholdCount ৫। মৃত target কত সেকেন্ডে বাদ পড়ে, সুস্থ হলে কত সেকেন্ডে ফেরে (আনুমানিক)?

29. `r53_plan.py`-এর desired-এ দুটি record: `@ CNAME 300 → x.elb.amazonaws.com` এবং `api A` alias সহ `"ttl": 60`। কী ফল?

30. `alarm_sim.py --series 1,9,1,9,1 --threshold 5 --n 3 --m 2 --missing missing` — পাঁচটি period-এর state কী?

## Part C — Scenario (প্রতিটি ৪ নম্বর)

31. নতুন AWS account খোলার পরের প্রথম এক ঘণ্টার checklist লিখুন, এবং প্রতিটি ধাপ কীভাবে যাচাই করবেন।

32. ALB-এর সব target `Target.Timeout`, অথচ instance-এর console output-এ `taskflow healthy`। গতকাল ALB নতুন করে বানানো হয়েছে, আর app subnet-এ একটি কাস্টম NACL যোগ হয়েছে। কোন ক্রমে খুঁজবেন, কোন tool দিয়ে, এবং কী কী কারণ সম্ভব? (Lab 08-C)

33. Lab শেষে instance ও ALB মোছা হয়েছে, তবু পরের মাসে "EC2 - Other" ও "Amazon Virtual Private Cloud"-এর খরচ বেড়েছে। কী রয়ে গেছে, কীভাবে খুঁজবেন, কীভাবে নিরাপদে মুছবেন?

34. TaskFlow-এর deploy-এ প্রতিবার কয়েক সেকেন্ড 502। সম্ভাব্য কারণ ও তিনটি পরিবর্তন প্রস্তাব করুন।

35. CI (GitHub Actions) থেকে TaskFlow deploy করতে AWS access দরকার। একজন বলছেন, "একটি IAM user বানিয়ে key GitHub secret-এ রাখি।" বিকল্প নকশা দিন — trust policy-র মূল অংশ ও permission-এর সীমা সহ।

---

## Answer key

<details><summary>Part A</summary>

1. Root-এর ক্ষমতা সীমাহীন; ফাঁস হলে account হারানোর ঝুঁকি। IAM policy root-এর ওপর প্রযোজ্য নয় — একক account-এ কোনো policy তাকে সীমিত করে না (Organizations-এর SCP member account-এর root-কে পারে)।
2. ACTUAL: খরচ হয়ে যাওয়ার পরে। FORECASTED: মাস শেষে সীমা ছাড়াবে বলে অনুমান হলে আগেই। Budget শুধু সতর্ক করে, খরচ থামায় না।
3. `AKIA` = দীর্ঘমেয়াদি IAM user key। `ASIA` = STS-এর অস্থায়ী credential; সাথে session token লাগে, নইলে প্রতিটি call ব্যর্থ।
4. না — named profile `[default]` থেকে setting পায় না। প্রতিটি profile-এ `region` লিখুন, নইলে env (`AWS_REGION`) বা ব্যর্থতা।
5. বহু-page API-র ফল এক call-এ আসে না। Paginator ছাড়া শুধু প্রথম page দেখে "সব দেখেছি" ভুল হয়।
6. Trust: **কে** role assume করতে পারে (role-এর resource policy)। Permission: role হয়ে **কী** করা যায়।
7. EC2-কে role দেওয়ার পাত্র; ঠিক একটি role। Instance IMDS থেকে সেই role-এর অস্থায়ী credential পায়।
8. Instance-এ role "দেওয়া" PassRole-এর কাজ। `Resource: "*"` হলে admin role বসিয়ে instance-এর মাধ্যমে তার ক্ষমতা নেওয়া যায় — privilege escalation। তাই নির্দিষ্ট role ও `iam:PassedToService`।
9. Route table: `0.0.0.0/0 → igw-` = public; `→ nat-` (বা firewall/TGW) = private; default route নেই = isolated। নাম নয়।
10. Public subnet-এ, কারণ NAT নিজেও IGW দিয়ে বাইরে যায়। Private subnet-এ বসালে কিছুই বাইরে যায় না।
11. Association-হীন সব subnet main table পায়। কেউ সেখানে IGW route যোগ করলে সবগুলো হঠাৎ public — তাই main শুধু local, প্রতিটি subnet explicit।
12. যেকোনো তিনটি:
    - SG ENI-স্তরে, NACL subnet-স্তরে।
    - SG stateful, NACL stateless।
    - SG শুধু allow, NACL allow ও deny।
    - SG-এর সব rule একসাথে, NACL-এ সংখ্যার ক্রমে প্রথম মিল।
    - SG অন্য SG reference করতে পারে।
13. SG বা NACL packet নীরবে ফেলে দেয় — কোনো উত্তর নেই, তাই client অপেক্ষা করে timeout পায়। "Refused" মানে packet host-এ পৌঁছেছে, কিন্তু সেই port-এ কেউ শুনছে না (RST)।
14. প্রথম boot-এ একবার, root হিসেবে (cloud-init)। সর্বোচ্চ ১৬ KB (base64-এর আগে)। Instance-এর যেকোনো process IMDS থেকে, আর `ec2:DescribeInstanceAttribute`-অনুমতিধারী API দিয়ে পড়তে পারে — encrypted নয়।
15. SSRF দিয়ে role-এর credential চুরি। IMDSv2-এ আগে `PUT` দিয়ে session token নিতে হয়, যা সাধারণ GET-ভিত্তিক SSRF পারে না। Hop limit ১ container থেকে পৌঁছানোও আটকায়।
16. Stop: compute থামে; EBS, Elastic IP চলে। Terminate: `DeleteOnTermination=false` থাকা volume থেকে যায় ও বিল চলে।
17. EBS একটি AZ-এর resource। Snapshot নিয়ে লক্ষ্য AZ-এ সেই snapshot থেকে নতুন volume বানান।
18. সেটা শুধু delete marker যোগ করে; পুরোনো version থাকে এবং bucket "খালি নয়"। Version ও delete marker `delete-objects` দিয়ে মুছতে হয় (L08-08/L08-12)।
19. যেকোনো দুটি:
    - Alias apex-এ চলে, CNAME চলে না।
    - Alias-এ TTL নেই (target-এর TTL)।
    - Alias resolver-কে সরাসরি IP দেয়, CNAME আরেকটি নাম দেয়।
    - Alias target শুধু AWS resource।
20. Memory ব্যবহার ও filesystem-এর ভরাট %। CloudWatch agent (`CWAgent` namespace, custom metric — চার্জযোগ্য)।

</details>

<details><summary>Part B</summary>

21. **CRITICAL** — "GitHub OIDC trust without a 'sub' condition — any repository on GitHub can assume this role"। `aud` প্রায় সবার জন্য একই; repo/branch চিহ্নিত করে শুধু `sub`।
22. **Environment-এর key** জেতে — `AWS_PROFILE` set থাকলেও, যদি `--profile` না দেওয়া হয়। `--which`: "environment variables: temporary-keys (these win over AWS_PROFILE and the files)"।
23. **public**। Finding: CRITICAL "MAIN route table has an internet route (igw-1) …" এবং WARN "uses the main route table implicitly …"।
24. ফেরত পথে: "return: destination NACL outbound to port 50000 …" — app-এর NACL ALB-এর ephemeral port-এ উত্তর যেতে দেয় না (stateless)। SG-এর ধাপগুলো `ok`।
25. Profile-সহ: **CRITICAL** (role-এর credential চুরির ঝুঁকি)। Profile ছাড়া: **WARN** (এখন চুরির কিছু নেই, কিন্তু role দেওয়ার আগে IMDSv2 required করুন)।
26. **দুটি ERROR:**
    - `/dev/xvdf` device name (Nitro-তে নাম বা ক্রম বদলাতে পারে → `UUID=`);
    - `nofail` নেই (volume না পেলে emergency mode)।
27. **না।** `aws:SourceVpce` condition statement-টিকে একটি VPC endpoint-এর traffic-এ সীমিত করে, তাই audit একে public বলে না। (`RestrictPublicBuckets` চালু থাকলে সত্যিকারের public policy-ও WARN-এ নামে।)
28. মৃত target ≈ **৯০ s** (৩০ × ৩); ফেরত ≈ **১৫০ s** (৩০ × ৫)।
29. দুটি ERROR, exit ১:
    - "example.com. CNAME: not allowed at the zone apex (RFC 1034) — use an alias A/AAAA record";
    - "api.example.com. A: alias records have no TTL …"।
30. `INSUFFICIENT_DATA, INSUFFICIENT_DATA, OK, ALARM, OK`।
    - প্রথম দুটি period-এ সিদ্ধান্তের মতো প্রমাণ নেই।
    - তৃতীয়তে দুটি non-breaching, তাই আর ALARM সম্ভব নয় → OK।
    - চতুর্থে `9,1,9` → ২টি breaching → ALARM।
    - পঞ্চমে `1,9,1` → OK।

</details>

<details><summary>Part C — মূল্যায়নের মূল বিষয়</summary>

31. **L08-01:**
    - root-এ MFA (দুটি device);
    - root key নেই;
    - alternate contact;
    - IAM access to Billing;
    - admin identity (Identity Center বা MFA-সহ admin), তারপর root logout;
    - budget (ACTUAL 50/80/100 + FORECASTED 100);
    - region বাছাই।

    যাচাই: `account_baseline.py` → `baseline OK`; `describe-notifications-for-budget`; `get-caller-identity`-এ root নয়।
32. **Symptom → layer।**
    1. `tg_health.py`: Timeout = network drop, app নয় (console output সুস্থ)।
    2. `vpc_audit.py`: route ঠিক (একই VPC, local)।
    3. `sg_reach.py check`, ALB-এর **প্রতিটি** subnet থেকে।

    সম্ভাব্য কারণ:
    - app SG পুরোনো (মুছে-ফেলা) ALB SG-কে reference করছে (`audit`: "references … not in this input");
    - NACL-এর outbound ALB-এর ephemeral port-এ উত্তর আটকায়।

    একটি ঠিক করলে অন্যটি সামনে আসে। ন্যূনতম fix — 0.0.0.0/0 নয়, NACL-এর ফেরত পথ VPC CIDR-এ। প্রতিরোধ: expected-flow test (L08-05) ও ALB rebuild-এর runbook।
33. **"EC2 - Other"** = EBS volume/snapshot, NAT gateway, data transfer। **VPC** = public IPv4 (Elastic IP সহ)।

    খোঁজা:
    - `inventory.py --all-regions` (tag-নিরপেক্ষ);
    - `ebs_audit.py` (unattached, পুরোনো snapshot);
    - `resourcegroupstaggingapi get-resources`।

    মোছা: `cleanup_plan.py`-এর পদ্ধতি — dry-run, account guard, নির্ভরতার ক্রম (NAT → EIP → …), তারপর inventory-তে শূন্য। কারণ দূর করা: প্রতিটি resource-এ tag, cost allocation tag চালু, budget।
34. **কারণ:** পুরোনো target বন্ধ হওয়ার সময়ও request পাচ্ছে, বা চলমান request কেটে যাচ্ছে।

    পরিবর্তন (তিনটি):
    1. Deregistration delay ≥ app-এর graceful shutdown (L05-13-এর SIGTERM handling)।
    2. নতুন target `healthy` হওয়ার পরেই পুরোনোটি deregister (rolling)।
    3. App-এর keep-alive timeout > ALB-এর idle timeout।

    অতিরিক্ত: health check `/health`-এ, interval ও threshold কম; `tg_health.py`-এ WARN নেই।
35. **GitHub OIDC + IAM role:** কোনো দীর্ঘমেয়াদি key নয়।
    - **Trust:** `Principal.Federated = …:oidc-provider/token.actions.githubusercontent.com`, `Action = sts:AssumeRoleWithWebIdentity`, condition `aud = sts.amazonaws.com` এবং `sub = repo:ORG/taskflow:environment:production` (wildcard নয়)।
    - **Permission:** শুধু deploy-এর কাজ:
      - artifact bucket-এর নির্দিষ্ট prefix;
      - নির্দিষ্ট role-এ PassRole (`iam:PassedToService ec2`);
      - describe।
    - যাচাই: `trust_policy_lint.py` ও L07-05-এর `policy_lint.py`/`policy_eval.py` (Lab 07-C-এর মতো)।
    - সেশনের মেয়াদ ছোট; CloudTrail-এ নজর।

</details>

## Scoring

| অংশ | নম্বর |
|---|---|
| Part A | ২০ × ১ = ২০ |
| Part B | ১০ × ২ = ২০ |
| Part C | ৫ × ৪ = ২০ |
| **মোট** | **৬০** — pass ≥ ৪২ |

ফল [08-aws-core-services/PROGRESS.md](../../08-aws-core-services/PROGRESS.md)-এর Module assessment table-এ লিখুন।
