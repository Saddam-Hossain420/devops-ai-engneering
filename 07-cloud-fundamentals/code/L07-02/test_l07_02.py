"""Tests for responsibility.py — চালানো: python3 -m unittest -v"""
from __future__ import annotations

import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import responsibility as r  # noqa: E402

RANK = {r.C: 2, r.S: 1, r.P: 0}


class MatrixInvariantsTest(unittest.TestCase):
    def test_always_customer(self) -> None:
        for layer in ("identity", "data", "configuration", "endpoint"):
            for model in r.MODELS:
                with self.subTest(layer=layer, model=model):
                    self.assertEqual(r.who(layer, model), r.C)

    def test_on_prem_is_all_customer(self) -> None:
        self.assertEqual(r.customer_layers("on-prem"), list(r.MATRIX))

    def test_responsibility_never_grows_up_the_stack(self) -> None:
        for layer, row in r.MATRIX.items():
            ranks = [RANK[x] for x in row]
            with self.subTest(layer=layer):
                self.assertEqual(ranks, sorted(ranks, reverse=True))      # on-prem → SaaS: কখনো বাড়ে না

    def test_specific_cells(self) -> None:
        self.assertEqual(r.who("os", "iaas"), r.C)
        self.assertEqual(r.who("os", "paas"), r.P)
        self.assertEqual(r.who("resilience", "iaas"), r.C)              # provider-এর outage, কিন্তু design আপনার
        with self.assertRaises(KeyError):
            r.who("kernel", "iaas")

    def test_sample_incidents_cover_every_layer(self) -> None:
        incidents = json.loads((HERE / "sample-incidents.json").read_text(encoding="utf-8"))
        self.assertEqual({i["layer"] for i in incidents} - set(r.MATRIX), set())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(r.main(["incidents", str(HERE / "sample-incidents.json"), "--model", "paas"]), 0)
        self.assertEqual(len(out.getvalue().splitlines()), len(incidents))


if __name__ == "__main__":
    unittest.main()
