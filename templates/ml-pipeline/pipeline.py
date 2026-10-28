"""Template: ML pipeline-এর কাঠামো (load → split → train → evaluate → gate → save).

এটি standard library দিয়ে লেখা একটি *কাঠামো* — আসল model-এর জায়গায় একটি
সরল baseline (majority class) আছে, যাতে dependency ছাড়াই চালানো যায়।
Module 23/24-এ scikit-learn ও MLflow দিয়ে প্রতিটি ধাপ প্রতিস্থাপন হবে।
"""
from __future__ import annotations

import argparse
import json
import logging
import random
from collections import Counter
from pathlib import Path

log = logging.getLogger("pipeline")


def load_rows(path: Path) -> list[tuple[list[float], str]]:
    """CSV: শেষ column label, বাকিগুলো সংখ্যা।"""
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines()[1:]:
        *features, label = line.split(",")
        rows.append(([float(x) for x in features], label))
    return rows


def split(rows, test_ratio: float, seed: int):
    rng = random.Random(seed)  # seed = reproducibility
    shuffled = rows[:]
    rng.shuffle(shuffled)
    cut = int(len(shuffled) * (1 - test_ratio))
    return shuffled[:cut], shuffled[cut:]


def train(train_rows) -> dict:
    majority = Counter(label for _, label in train_rows).most_common(1)[0][0]
    return {"type": "majority-baseline", "predict": majority}


def evaluate(model: dict, test_rows) -> dict:
    correct = sum(1 for _, label in test_rows if label == model["predict"])
    return {"accuracy": correct / len(test_rows) if test_rows else 0.0}


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("data", type=Path)
    p.add_argument("--out", type=Path, default=Path("model.json"))
    p.add_argument("--min-accuracy", type=float, default=0.5, help="quality gate")
    p.add_argument("--seed", type=int, default=42)
    a = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    train_rows, test_rows = split(load_rows(a.data), 0.2, a.seed)
    model = train(train_rows)
    metrics = evaluate(model, test_rows)
    log.info("metrics=%s", metrics)

    if metrics["accuracy"] < a.min_accuracy:
        log.error("quality gate failed: %.3f < %.3f", metrics["accuracy"], a.min_accuracy)
        return 1
    a.out.write_text(json.dumps({"model": model, "metrics": metrics, "seed": a.seed}, indent=2))
    log.info("saved %s", a.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
