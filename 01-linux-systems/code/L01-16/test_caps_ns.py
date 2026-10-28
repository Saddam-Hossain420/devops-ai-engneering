"""Tests for caps_ns.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import caps_ns as cn  # noqa: E402

# Docker-এর documented default capability set
DOCKER_DEFAULT = {"CAP_CHOWN", "CAP_DAC_OVERRIDE", "CAP_FSETID", "CAP_FOWNER", "CAP_MKNOD", "CAP_NET_RAW",
                  "CAP_SETGID", "CAP_SETUID", "CAP_SETFCAP", "CAP_SETPCAP", "CAP_NET_BIND_SERVICE",
                  "CAP_SYS_CHROOT", "CAP_KILL", "CAP_AUDIT_WRITE"}


class DecodeTest(unittest.TestCase):
    def test_docker_default_mask(self) -> None:
        self.assertEqual(set(cn.decode("00000000a80425fb")), DOCKER_DEFAULT)

    def test_single_bits(self) -> None:
        self.assertEqual(cn.decode("0000000000000400"), ["CAP_NET_BIND_SERVICE"])   # bit 10
        self.assertEqual(cn.decode("0000000000200000"), ["CAP_SYS_ADMIN"])          # bit 21
        self.assertEqual(cn.decode("0"), [])

    def test_full_and_unknown(self) -> None:
        self.assertEqual(len(cn.decode("000001ffffffffff")), 41)
        self.assertIn("unknown bits", cn.decode("000003ffffffffff")[-1])


class StatusTest(unittest.TestCase):
    def test_container_vs_privileged(self) -> None:
        self.assertEqual(cn.main(["status", str(HERE / "sample-status-container.txt")]), 0)
        self.assertEqual(cn.main(["status", str(HERE / "sample-status-privileged.txt")]), 1)
        st = cn.parse_status((HERE / "sample-status-container.txt").read_text(encoding="utf-8"))
        self.assertEqual(st["Seccomp"], "2")


class NsCgroupTest(unittest.TestCase):
    def test_compare(self) -> None:
        a = cn.parse_ns((HERE / "sample-ns-host.txt").read_text(encoding="utf-8"))
        b = cn.parse_ns((HERE / "sample-ns-container.txt").read_text(encoding="utf-8"))
        self.assertEqual(a["net"], 4026531840)
        shared = [ns for ns, same in cn.compare_ns(a, b) if same]
        self.assertEqual(shared, ["time", "user"])   # user namespace ব্যবহার না করা container

    def test_cgroup(self) -> None:
        self.assertEqual(cn.parse_cgroup("0::/user.slice/user-1000.slice/session-3.scope\n"),
                         "/user.slice/user-1000.slice/session-3.scope")
        with self.assertRaises(ValueError):
            cn.parse_cgroup("12:memory:/docker/abc\n")


if __name__ == "__main__":
    unittest.main()
