#!/usr/bin/env python3
"""Role fit ও skill gap analyzer.

নিজের skill-কে 0-4 scale-এ rate করুন। Script প্রতিটি engineering role-এর জন্য
weighted fit score হিসাব করে, এবং বেছে নেওয়া role-এর সবচেয়ে বড় skill gap
ও কোন module সেগুলো শেখাবে তা দেখায়।

Rating scale:
  0 = জানি না, 1 = নাম জানি, 2 = গাইড দেখে করতে পারি,
  3 = স্বাধীনভাবে করতে পারি, 4 = অন্যকে শেখাতে ও troubleshoot করতে পারি

Usage:
  python3 role_fit.py my-skills.json
  python3 role_fit.py my-skills.json --role "Site Reliability Engineer" --top 5
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX_RATING = 4


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def validate_ratings(ratings: dict[str, int], known_skills: set[str]) -> None:
    """অজানা skill বা 0-4-এর বাইরে মান থাকলে ValueError।"""
    unknown = set(ratings) - known_skills
    if unknown:
        raise ValueError(f"unknown skills: {', '.join(sorted(unknown))}")
    for skill, value in ratings.items():
        if not isinstance(value, int) or not 0 <= value <= MAX_RATING:
            raise ValueError(f"{skill}: rating must be an integer 0-{MAX_RATING}, got {value!r}")


def fit_score(weights: dict[str, int], ratings: dict[str, int]) -> float:
    """Weighted fit (0-100%).

    fit = Σ(weight × rating) / Σ(weight × MAX_RATING) × 100
    Rating না দেওয়া skill = 0 ধরা হয়।
    """
    achieved = sum(w * ratings.get(skill, 0) for skill, w in weights.items())
    possible = sum(w * MAX_RATING for w in weights.values())
    return round(100 * achieved / possible, 1)


def skill_gaps(weights: dict[str, int], ratings: dict[str, int], top: int) -> list[tuple[str, int]]:
    """(skill, gap) — gap = weight × (MAX_RATING - rating); বড় gap আগে।"""
    gaps = [(skill, w * (MAX_RATING - ratings.get(skill, 0))) for skill, w in weights.items()]
    gaps = [g for g in gaps if g[1] > 0]
    # সমান gap হলে নাম অনুযায়ী সাজানো — output deterministic থাকে
    gaps.sort(key=lambda g: (-g[1], g[0]))
    return gaps[:top]


def rank_roles(model: dict, ratings: dict[str, int]) -> list[tuple[str, float]]:
    scores = [(name, fit_score(r["weights"], ratings)) for name, r in model["roles"].items()]
    scores.sort(key=lambda s: (-s[1], s[0]))
    return scores


def main(argv: list[str] | None = None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Engineering role fit and skill gap analysis.")
    parser.add_argument("ratings_file", type=Path, help="JSON: {skill: rating 0-4}")
    parser.add_argument("--model", type=Path, default=HERE / "roles.json")
    parser.add_argument("--role", help="gap analysis-এর role (default: সর্বোচ্চ fit)")
    parser.add_argument("--top", type=int, default=3, help="কয়টি gap দেখাবে")
    args = parser.parse_args(argv)

    try:
        model = load_json(args.model)
        ratings = load_json(args.ratings_file)
        validate_ratings(ratings, set(model["skills"]))
    except FileNotFoundError as exc:
        print(f"error: file not found: {exc.filename}", file=sys.stderr)
        return 2
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: invalid input: {exc}", file=sys.stderr)
        return 2

    ranking = rank_roles(model, ratings)
    print("Role fit (weighted, 0-100%):")
    for name, score in ranking:
        bar = "#" * int(score // 5)
        print(f"  {name:38} {score:5.1f}%  {bar}")

    role = args.role or ranking[0][0]
    if role not in model["roles"]:
        print(f"error: unknown role {role!r}", file=sys.stderr)
        return 2

    print(f"\nTop skill gaps for: {role} (track {model['roles'][role]['track']})")
    for skill, gap in skill_gaps(model["roles"][role]["weights"], ratings, args.top):
        modules = ", ".join(model["modules"].get(skill, []))
        print(f"  - {model['skills'][skill]:40} gap {gap:2}  → module {modules}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
