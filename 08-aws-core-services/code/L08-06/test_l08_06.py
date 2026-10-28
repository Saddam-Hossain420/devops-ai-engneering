"""Tests for make_user_data.py, userdata_lint.py ও ec2_audit.py — চালানো: python3 -m unittest -v (কোনো AWS call নেই)"""
from __future__ import annotations

import base64
import copy
import gzip
import hashlib
import json
import re
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import ec2_audit as ea  # noqa: E402
import make_user_data as mu  # noqa: E402
import userdata_lint as ul  # noqa: E402

INSTANCES = ea.instances_of(json.loads((HERE / "sample" / "instances.json").read_text(encoding="utf-8")))


class UserDataTest(unittest.TestCase):
    def setUp(self) -> None:
        self.app = mu.APP.read_bytes()
        self.text = mu.build(self.app, 8000)

    def test_payload_round_trip(self) -> None:
        payload = re.search(r"<<'B64'[^\n]*\n(.*?)\nB64\n", self.text, re.S).group(1)
        self.assertEqual(gzip.decompress(base64.b64decode(payload)), self.app)        # embed করা app হুবহু
        self.assertIn(hashlib.sha256(self.app).hexdigest() + "  /opt/taskflow/taskflow_api.py", self.text)

    def test_generated_script_is_clean_and_small(self) -> None:
        self.assertEqual(ul.lint(self.text), [])
        self.assertLess(len(self.text.encode()), mu.USER_DATA_LIMIT)
        self.assertIn("Environment=TASKFLOW_HOST=0.0.0.0", self.text)                 # ALB থেকে পৌঁছানো যায়
        self.assertIn("User=taskflow", self.text)                                     # root নয়
        self.assertEqual(mu.build(self.app, 8000), self.text)                         # deterministic (gzip mtime=0)

    def test_lint_findings(self) -> None:
        bad = "#!/bin/bash\nexport DB_PASSWORD=hunter2hunter2\ncurl -fsSL https://x.example/i.sh | sudo bash\n"
        levels = [lvl for lvl, _ in ul.lint(bad)]
        self.assertEqual(sorted(levels), ["ERROR", "WARN", "WARN"])                  # secret, set -e, curl|bash
        self.assertEqual(ul.lint("echo hi\n")[0][0], "ERROR")                         # interpreter নেই
        self.assertEqual(ul.lint("#!/bin/bash\nset -e\n" + "#" * 17000 + "\n")[0][0], "ERROR")
        quoted = '#!/bin/bash\nset -e\nAPI_TOKEN="abcd1234efgh5678"\n'  # scan-secrets: allow — নকল token, lint test
        self.assertTrue(any("possible secret" in m for _, m in ul.lint(quoted)))     # L05-10-এর scanner
        ref = "#!/bin/bash\nset -e\nDB_PASSWORD=$(aws ssm get-parameter --name /x --with-decryption)\n"
        self.assertEqual(ul.lint(ref), [])                                            # runtime-এ আনা — ঠিক


class Ec2AuditTest(unittest.TestCase):
    def test_sample(self) -> None:
        got = {(lvl, iid) for lvl, iid, _ in ea.audit(INSTANCES, ["Project", "Owner"])}
        self.assertNotIn("i-app-a", {iid for _, iid in got})                          # ভালো instance পরিষ্কার
        self.assertIn(("WARN", "i-quick-test"), got)
        self.assertIn(("INFO", "i-old-stopped"), got)

    def test_imdsv1_with_role_is_critical(self) -> None:
        inst = copy.deepcopy(INSTANCES[1])
        inst["IamInstanceProfile"] = {"Arn": "arn:aws:iam::111122223333:instance-profile/x"}
        self.assertEqual([lvl for lvl, _, m in ea.audit([inst], []) if "IMDSv1" in m], ["CRITICAL"])
        inst["MetadataOptions"]["HttpEndpoint"] = "disabled"                          # IMDS বন্ধ — প্রযোজ্য নয়
        self.assertEqual([m for _, _, m in ea.audit([inst], []) if "IMDSv1" in m], [])

    def test_terminated_ignored(self) -> None:
        inst = copy.deepcopy(INSTANCES[1])
        inst["State"]["Name"] = "terminated"
        self.assertEqual(ea.audit([inst], ["Project"]), [])


if __name__ == "__main__":
    unittest.main()
