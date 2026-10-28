# Module 08 Progress — AWS Core Services

Content status: `NOT_STARTED` · `IN_PROGRESS` · `COMPLETED` · `NEEDS_REVISION` (Claude update করবে)  
Learner status: Not started · In progress · Practiced · Assessment passed · Project completed · Needs revision (আপনি update করবেন)

| ID | Lesson | Content | Learner | Required files | Validation | Prerequisites | Next |
|---|---|---|---|---|---|---|---|
| L08-01 | [AWS account safety: root user, MFA, budget alert](L08-01-account-safety-root-mfa-budget.md) | COMPLETED | Not started | `L08-01-account-safety-root-mfa-budget.md`, `code/L08-01/account_baseline.py`, `make_budget.py`, `sample/`, `test_l08_01.py` | 6 test pass; হাতে তৈরি CLI-output নমুনা; duplicate finding ধরা ও ঠিক; AWS account-এ চালানো হয়নি (AWS CLI নেই) | L07-06 | L08-02 |
| L08-02 | [AWS CLI, profile, temporary credential ও boto3](L08-02-aws-cli-profiles-temporary-credentials-boto3.md) | COMPLETED | Not started | `L08-02-aws-cli-profiles-temporary-credentials-boto3.md`, `code/L08-02/aws_config_audit.py`, `inventory.py`, `sample/config`, `sample/credentials`, `test_l08_02.py` | 7 test pass; inventory নকল boto3 session-এ (boto3 নেই); region-inheritance ভুল ধারণা ধরা ও ঠিক; আসল AWS-এ চালানো হয়নি | L08-01 | L08-03 |
| L08-03 | [IAM: policy, role, instance profile](L08-03-iam-policy-role-instance-profile.md) | COMPLETED | Not started | `L08-03-iam-policy-role-instance-profile.md`, `code/L08-03/trust_policy_lint.py`, `sample/`, `test_l08_03.py` | 6 test pass; হাতে তৈরি get-role নমুনা (URL-encoded সহ); sub-wildcard নিয়মের ফাঁক ধরা ও ঠিক; আসল AWS-এ চালানো হয়নি | L08-02 | L08-04 |
| L08-04 | [VPC design: subnet, route table, gateway](L08-04-vpc-subnet-route-gateway.md) | COMPLETED | Not started | `L08-04-vpc-subnet-route-gateway.md`, `code/L08-04/vpc_audit.py`, `vpc_commands.py`, `sample-plan.json`, `sample/`, `test_l08_04.py` | 8 test pass; হাতে তৈরি describe-* নমুনা; তৈরি script bash -n-এ যাচাই; py3.11 f-string সমস্যা ধরা ও ঠিক; AWS-এ চালানো হয়নি | L08-03 | L08-05 |
| L08-05 | [Security group ও network ACL](L08-05-security-groups-nacl.md) | COMPLETED | Not started | `L08-05-security-groups-nacl.md`, `code/L08-05/sg_reach.py`, `sample/`, `test_l08_05.py` | 6 test pass (stateless return path সহ); সরল মডেল, Reachability Analyzer-এ মেলানো হয়নি; py3.13-only copy.replace ধরা ও ঠিক; AWS-এ চালানো হয়নি | L08-04 | L08-06 |
| L08-06 | [EC2](L08-06-ec2.md) | COMPLETED | Not started | `L08-06-ec2.md`, `code/L08-06/make_user_data.py`, `userdata_lint.py`, `ec2_audit.py`, `sample/instances.json`, `test_l08_06.py` | 6 test pass; user-data payload Git Bash-এ decode+sha256 OK, TaskFlow-এর env local-এ /health 200; IMDS severity ও heredoc-escape ভুল ধরা ও ঠিক; systemd/cloud-init আসল EC2-এ চালানো হয়নি | L08-05 | L08-07 |
| L08-07 | [EBS ও EFS](L08-07-ebs-efs.md) | COMPLETED | Not started | `L08-07-ebs-efs.md`, `code/L08-07/ebs_audit.py`, `fstab_lint.py`, `sample/`, `test_l08_07.py` | 6 test pass; হাতে তৈরি নমুনা; nfs4-এ _netdev নিয়ে অতিরঞ্জিত দাবি ধরা ও ঠিক; attach/mount/reboot আসল EC2-এ পরীক্ষা হয়নি | L08-06 | L08-08 |
| L08-08 | [S3](L08-08-s3.md) | COMPLETED | Not started | `L08-08-s3.md`, `code/L08-08/presign.py`, `s3_audit.py`, `sample/`, `test_l08_08.py` | 6 test pass; presign AWS documentation-এর SigV4 উদাহরণের signature হুবহু মেলায়; s3_audit হাতে তৈরি নমুনায়; আসল bucket-এ চালানো হয়নি | L08-07 | L08-09 |
| L08-09 | [Elastic Load Balancing](L08-09-elastic-load-balancing.md) | COMPLETED | Not started | `L08-09-elastic-load-balancing.md`, `code/L08-09/tg_health.py`, `hc_sim.py`, `sample/`, `test_l08_09.py` | 4 test pass; hc_sim আসল local server ও দুটি TaskFlow process-এ চালিয়ে detection/readmit মাপা; Timeout-এর ভুল ব্যাখ্যা ধরা ও ঠিক; আসল ALB চালানো হয়নি | L08-08 | L08-10 |
| L08-10 | [Route 53](L08-10-route53.md) | COMPLETED | Not started | `L08-10-route53.md`, `code/L08-10/r53_plan.py`, `sample/`, `test_l08_10.py` | 5 test pass (idempotency সহ); হাতে তৈরি নমুনা; একমুখী CNAME-conflict check ও DELETE-ক্রমের ভুল ধরা ও ঠিক; কোনো zone-এ change পাঠানো হয়নি | L08-09 | L08-11 |
| L08-11 | [CloudWatch](L08-11-cloudwatch.md) | COMPLETED | Not started | `L08-11-cloudwatch.md`, `code/L08-11/alarm_sim.py`, `alarm_defs.py`, `test_l08_11.py` | 5 test pass; alarm_sim সরল মডেল (missing/ignore-এর পূর্ণ AWS table নয়); বিভ্রান্তিকর missing-mode আচরণ ধরা ও ঠিক; কোনো alarm তৈরি হয়নি | L08-10 | L08-12 |
| L08-12 | [Tagging, Cost Explorer ও resource cleanup automation](L08-12-tagging-cost-explorer-cleanup.md) | COMPLETED | Not started | `L08-12-tagging-cost-explorer-cleanup.md`, `code/L08-12/cleanup_plan.py`, `ce_report.py`, `sample/`, `test_l08_12.py` | 7 test pass; তৈরি cleanup script নকল aws দিয়ে Git Bash-এ আসলে চালানো (dry-run, account guard, ক্রম, মুছে-যাওয়া volume); SG-ক্রম ও volume-abort bug ধরা ও ঠিক; cost সংখ্যা বানানো; আসল AWS-এ চালানো হয়নি | L08-11 | L09-01 |

## Module assessment

| Assessment | Score | তারিখ |
|---|---|---|
| [Module quiz](../assessments/08-aws-core-services/quiz.md) | — | — |
| [Level A lab](../labs/08-aws-core-services/A-s3-bucket-iam-policy/README.md) | — | — |
| [Level B lab](../labs/08-aws-core-services/B-taskflow-vpc-ec2-alb/README.md) | — | — |
| [Level C lab](../labs/08-aws-core-services/C-sg-timeout-diagnosis/README.md) | — | — |
