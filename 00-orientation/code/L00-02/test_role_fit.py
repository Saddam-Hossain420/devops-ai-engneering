"""Tests for role_fit.py — চালানো: python3 -m unittest -v (এই folder থেকে)।"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import role_fit as rf  # noqa: E402


class FitScoreTest(unittest.TestCase):
    def test_perfect_and_zero(self) -> None:
        weights = {"linux": 3, "cicd": 1}
        self.assertEqual(rf.fit_score(weights, {"linux": 4, "cicd": 4}), 100.0)
        self.assertEqual(rf.fit_score(weights, {}), 0.0)

    def test_weighted(self) -> None:
        # (3×2 + 1×4) / (3×4 + 1×4) = 10/16 = 62.5%
        self.assertEqual(rf.fit_score({"linux": 3, "cicd": 1}, {"linux": 2, "cicd": 4}), 62.5)


class GapTest(unittest.TestCase):
    def test_order_and_limit(self) -> None:
        weights = {"a": 3, "b": 1, "c": 2}
        ratings = {"a": 3, "b": 0, "c": 0}  # gaps: a=3, b=4, c=8
        self.assertEqual(rf.skill_gaps(weights, ratings, 2), [("c", 8), ("b", 4)])

    def test_no_gap_when_mastered(self) -> None:
        self.assertEqual(rf.skill_gaps({"a": 2}, {"a": 4}, 3), [])


class ValidationTest(unittest.TestCase):
    def test_rejects_unknown_skill(self) -> None:
        with self.assertRaises(ValueError):
            rf.validate_ratings({"cooking": 2}, {"linux"})

    def test_rejects_out_of_range(self) -> None:
        for bad in (5, -1, 2.5, "3"):
            with self.assertRaises(ValueError):
                rf.validate_ratings({"linux": bad}, {"linux"})


class ModelTest(unittest.TestCase):
    def test_model_is_consistent(self) -> None:
        model = rf.load_json(HERE / "roles.json")
        skills = set(model["skills"])
        self.assertEqual(set(model["modules"]), skills)
        for name, role in model["roles"].items():
            self.assertTrue(set(role["weights"]) <= skills, name)
            self.assertTrue(all(w in (1, 2, 3) for w in role["weights"].values()), name)

    def test_sample_ranking(self) -> None:
        model = rf.load_json(HERE / "roles.json")
        ratings = rf.load_json(HERE / "sample-skills.json")
        rf.validate_ratings(ratings, set(model["skills"]))
        ranking = rf.rank_roles(model, ratings)
        self.assertEqual(len(ranking), 7)
        self.assertEqual(ranking, sorted(ranking, key=lambda s: (-s[1], s[0])))

    def test_cli_exit_codes(self) -> None:
        self.assertEqual(rf.main([str(HERE / "sample-skills.json")]), 0)
        self.assertEqual(rf.main([str(HERE / "missing.json")]), 2)
        self.assertEqual(rf.main([str(HERE / "sample-skills.json"), "--role", "Astronaut"]), 2)


if __name__ == "__main__":
    unittest.main()
