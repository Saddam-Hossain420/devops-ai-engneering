"""Tests for availability.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import availability as av  # noqa: E402


def one_tier(azs: list[str], a: float = 0.995, az: float = 0.999, min_healthy: int = 1) -> av.Spec:
    return av.Spec("t", az, [av.Tier("app", a, azs, min_healthy)])


class AnalyticTest(unittest.TestCase):
    def test_single_instance_is_product(self) -> None:
        self.assertAlmostEqual(av.analytic(one_tier(["a"])), 0.995 * 0.999, places=12)

    def test_same_az_pair_is_limited_by_the_az(self) -> None:
        same, spread = av.analytic(one_tier(["a", "a"])), av.analytic(one_tier(["a", "b"]))
        self.assertLess(same, 0.999)                                   # AZ-এর চেয়ে ভালো হতে পারে না
        self.assertGreater(spread, 0.9999)
        self.assertAlmostEqual(av.naive(one_tier(["a", "a"])), av.naive(one_tier(["a", "b"])), places=12)

    def test_min_healthy(self) -> None:
        # দুটির দুটিই লাগলে redundancy নেই — একটির চেয়েও খারাপ
        self.assertLess(av.analytic(one_tier(["a", "b"], min_healthy=2)), av.analytic(one_tier(["a"])))

    def test_monte_carlo_agrees(self) -> None:
        spec = av.load(HERE / "same-az-pair.json")
        self.assertAlmostEqual(av.simulate(spec, 200_000, seed=3), av.analytic(spec), delta=0.0008)


class SpecTest(unittest.TestCase):
    def test_single_points_of_failure(self) -> None:
        spofs = av.single_points(av.load(HERE / "same-az-pair.json"))
        self.assertEqual(len(spofs), 3)
        self.assertEqual(av.single_points(av.load(HERE / "two-az.json")), [])
        uneven = one_tier(["a", "a", "a", "b"], min_healthy=2)
        self.assertIn("losing the biggest AZ", av.single_points(uneven)[0])

    def test_validation_and_downtime_format(self) -> None:
        import json
        import tempfile
        with tempfile.TemporaryDirectory() as d:
            p = Path(d, "bad.json")
            p.write_text(json.dumps({"name": "x", "az_availability": 0.999,
                                     "tiers": [{"name": "a", "availability": 0.99, "azs": ["a"], "min_healthy": 2}]}))
            with self.assertRaises(ValueError):
                av.load(p)
        self.assertEqual(av.fmt_downtime(0.999), "8.8 h/year")
        self.assertEqual(av.fmt_downtime(0.99999), "5 min/year")


if __name__ == "__main__":
    unittest.main()
