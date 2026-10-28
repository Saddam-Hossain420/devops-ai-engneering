"""Tests for fw_sim.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import fw_sim as fw  # noqa: E402

SAMPLE = HERE / "sample-rules.txt"


class ParseTest(unittest.TestCase):
    def test_parse_sample(self) -> None:
        policy, rules = fw.parse_rules(SAMPLE.read_text(encoding="utf-8"))
        self.assertEqual(policy, "drop")
        self.assertEqual(len(rules), 8)
        self.assertEqual(rules[3].dports, [(80, 80), (443, 443)])

    def test_parse_errors(self) -> None:
        for bad in ("allow proto tcp", "accept dport 70000", "accept proto", "accept color red", "policy maybe"):
            with self.assertRaises(ValueError, msg=bad):
                fw.parse_rules(bad)


class HostFirewallTest(unittest.TestCase):
    def setUp(self) -> None:
        self.fw = fw.HostFirewall(*fw.parse_rules(SAMPLE.read_text(encoding="utf-8")))

    def test_first_match_wins(self) -> None:
        # 10.20.1.5 ∈ 10.0.0.0/8 → line 6 আগে accept করে, line 8-এর drop কখনো পৌঁছায় না
        action, why = self.fw.inbound(fw.Packet("tcp", "10.20.1.5", 22))
        self.assertEqual(action, "accept")
        self.assertIn("line 6", why)
        self.assertEqual(self.fw.inbound(fw.Packet("tcp", "198.51.100.7", 22))[0], "drop")   # policy

    def test_stateful_return_traffic(self) -> None:
        f = fw.HostFirewall(*fw.parse_rules("policy drop\naccept state established"))
        out = fw.Packet("tcp", "192.0.2.10", dport=443, sport=40000, dst="93.184.215.14")
        back = fw.Packet("tcp", "93.184.215.14", dport=40000, sport=443, dst="192.0.2.10")
        self.assertEqual(f.inbound(back)[0], "drop")
        f.outbound(out)
        self.assertEqual(f.inbound(back)[0], "accept")


class CloudTest(unittest.TestCase):
    def test_nacl_ephemeral_trap(self) -> None:
        https = fw.parse_rules("accept proto tcp dport 443")[1][0]
        eph = fw.parse_rules("accept proto tcp dport 1024-65535")[1][0]
        reply = fw.Packet("tcp", "10.0.1.20", dport=51514, sport=443)
        self.assertEqual(fw.Nacl(outbound=[(100, https)]).check("out", reply)[0], "drop")
        self.assertEqual(fw.Nacl(outbound=[(100, eph)]).check("out", reply)[0], "accept")

    def test_nacl_number_order(self) -> None:
        deny = fw.parse_rules("drop src 203.0.113.0/24")[1][0]
        allow = fw.parse_rules("accept proto tcp dport 443")[1][0]
        p = fw.Packet("tcp", "203.0.113.9", 443)
        # list-এর ক্রম নয়, নম্বর: 90 (deny) আগে
        self.assertEqual(fw.Nacl(inbound=[(100, allow), (90, deny)]).check("in", p), ("drop", "rule 90"))

    def test_security_group_allow_only(self) -> None:
        sg = fw.SecurityGroup(fw.parse_rules("accept proto tcp dport 443 src 0.0.0.0/0")[1])
        self.assertTrue(sg.allows(fw.Packet("tcp", "198.51.100.1", 443)))
        self.assertFalse(sg.allows(fw.Packet("tcp", "198.51.100.1", 22)))


class AuditTest(unittest.TestCase):
    def test_sample_findings(self) -> None:
        findings = fw.audit(*fw.parse_rules(SAMPLE.read_text(encoding="utf-8")))
        text = "\n".join(findings)
        self.assertIn("line 8 CONFLICT (never reached): shadowed by line 6", text)
        self.assertIn("line 9 redundant: shadowed by line 7", text)
        self.assertIn("line 10: Ollama LLM API (11434) open to the whole internet", text)
        self.assertNotIn("9100", text)          # monitoring subnet-এ সীমিত — ঠিক আছে
        self.assertNotIn("SSH (22) open", text)  # 10.0.0.0/8-এ সীমিত
        self.assertEqual(len(findings), 3)

    def test_policy_accept_and_cli(self) -> None:
        self.assertTrue(any("policy accept" in f for f in fw.audit(*fw.parse_rules("accept proto tcp dport 80"))))
        self.assertEqual(fw.main(["audit", str(SAMPLE)]), 1)
        self.assertEqual(fw.main(["eval", str(SAMPLE), "--src", "198.51.100.7", "--dport", "443"]), 0)
        self.assertEqual(fw.main(["eval", str(SAMPLE), "--src", "198.51.100.7", "--dport", "3306"]), 1)
        self.assertEqual(fw.main(["audit", str(HERE / "missing.txt")]), 2)


if __name__ == "__main__":
    unittest.main()
