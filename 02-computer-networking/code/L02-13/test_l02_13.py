"""Tests for netns_inspect.py and netns_lab.sh — চালানো: python3 -m unittest -v

netns_lab.sh-এর আসল network পরিবর্তন test-এ চালানো হয় না; শুধু syntax ও safety guard।
"""
from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import netns_inspect as ni  # noqa: E402

SAMPLE = HERE / "sample-links.json"
BASH = shutil.which("bash")


class InspectTest(unittest.TestCase):
    def setUp(self) -> None:
        self.links = json.loads(SAMPLE.read_text(encoding="utf-8"))

    def test_topology(self) -> None:
        bridges, loose, findings = ni.topology(self.links)
        self.assertEqual(sorted(bridges), ["br-lab", "docker0"])
        self.assertEqual([m["ifname"] for m in bridges["docker0"]], ["veth3f2a9c1", "veth81bd0e4"])
        self.assertEqual({l["ifname"] for l in loose}, {"veth-orphan", "veth-orphan-p"})
        self.assertTrue(any("veth-blue on br-lab is DOWN" in f for f in findings))
        self.assertEqual(len(findings), 3)

    def test_peer_description(self) -> None:
        red = next(l for l in self.links if l["ifname"] == "veth-red")
        self.assertEqual(ni.describe_peer(red), "peer ifindex 2 in netns id 2")
        orphan = next(l for l in self.links if l["ifname"] == "veth-orphan")
        self.assertEqual(ni.describe_peer(orphan), "peer veth-orphan-p in this namespace")

    def test_cli(self) -> None:
        self.assertEqual(ni.main([str(SAMPLE)]), 1)
        bad = HERE / "_bad_links.json"
        bad.write_text('{"not": "a list"}', encoding="utf-8")
        try:
            self.assertEqual(ni.main([str(bad)]), 2)
        finally:
            bad.unlink()


@unittest.skipUnless(BASH, "bash not installed")
class LabScriptTest(unittest.TestCase):
    script = str(HERE / "netns_lab.sh")

    def run_script(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run([BASH, self.script, *args], capture_output=True, text=True, timeout=30)

    def test_syntax(self) -> None:
        self.assertEqual(subprocess.run([BASH, "-n", self.script]).returncode, 0)

    def test_refuses_without_confirmation(self) -> None:
        r = self.run_script("up")
        self.assertEqual(r.returncode, 2)
        self.assertIn("refusing", r.stderr)

    def test_rejects_unknown_action(self) -> None:
        self.assertEqual(self.run_script("destroy-everything", "--yes-i-am-in-a-vm").returncode, 2)

    def test_every_create_has_a_delete(self) -> None:
        text = Path(self.script).read_text(encoding="utf-8")
        for created, deleted in (("ip netns add", "ip netns del"), ("type bridge", 'ip link del "$BR"'),
                                 ("nft add table ip netns_lab", "nft delete table ip netns_lab"),
                                 ('> "$STATE"', 'rm -f "$STATE"')):
            self.assertIn(created, text)
            self.assertIn(deleted, text)


if __name__ == "__main__":
    unittest.main()
