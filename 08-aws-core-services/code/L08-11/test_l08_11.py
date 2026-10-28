"""Tests for alarm_sim.py ও alarm_defs.py — চালানো: python3 -m unittest -v (কোনো AWS call নেই)"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import alarm_defs as ad  # noqa: E402
import alarm_sim as sim  # noqa: E402

SERIES = sim.parse_series("1,2,9,9,2,9,9,9,-,-,-")
LB = "arn:aws:elasticloadbalancing:ap-south-1:111122223333:loadbalancer/app/lab08-alb/50dc6c495c0c9188"
TG = "arn:aws:elasticloadbalancing:ap-south-1:111122223333:targetgroup/lab08-app/943f017f100becff"


class AlarmSimTest(unittest.TestCase):
    def test_m_of_n(self) -> None:
        s = sim.evaluate(SERIES, 5, 3, 2, "missing")
        self.assertEqual(s[:4], ["INSUFFICIENT_DATA", "OK", "OK", "ALARM"])       # একটি spike-এ নয়, দুটিতে
        self.assertEqual(s[4], "ALARM")                                             # 9,9,2 — এখনো ২টি
        spike = sim.evaluate([1, 9, 1, 1, 9, 1], 5, 3, 2, "missing")
        self.assertNotIn("ALARM", spike)                                            # বিচ্ছিন্ন spike — কোনো alarm নয়
        self.assertEqual(sim.evaluate([1, 9, 1, 1, 9, 1], 5, 1, 1, "missing").count("ALARM"), 2)

    def test_missing_data_modes(self) -> None:
        end = {mode: sim.evaluate(SERIES, 5, 3, 2, mode)[-1] for mode in sim.MISSING}
        self.assertEqual(end, {"missing": "INSUFFICIENT_DATA", "ignore": "ALARM",
                               "breaching": "ALARM", "notBreaching": "OK"})
        # একটি breaching datapoint + দুটি missing: প্রমাণ যথেষ্ট নয় → আগের state থাকে
        self.assertEqual(sim.evaluate(SERIES, 5, 3, 2, "missing")[9], "ALARM")

    def test_operators_and_validation(self) -> None:
        low = sim.evaluate([50, 10, 10], 20, 2, 2, "missing", op="LessThanThreshold")
        self.assertEqual(low[-1], "ALARM")
        with self.assertRaises(ValueError):
            sim.evaluate(SERIES, 5, 2, 3, "missing")                                # M > N
        with self.assertRaises(ValueError):
            sim.evaluate(SERIES, 5, 3, 2, "zero")


class AlarmDefsTest(unittest.TestCase):
    def test_dimensions_from_arns(self) -> None:
        self.assertEqual(ad.lb_dimension(LB), "app/lab08-alb/50dc6c495c0c9188")
        self.assertEqual(ad.tg_dimension(TG), "targetgroup/lab08-app/943f017f100becff")
        with self.assertRaises(ValueError):
            ad.lb_dimension(TG)

    def test_build(self) -> None:
        alarms = {a["AlarmName"]: a for a in ad.build(LB, TG, "i-0abc", "arn:aws:sns:ap-south-1:1:t", "lab08", 500)}
        self.assertEqual(len(alarms), 4)
        p95 = alarms["lab08-p95-latency"]
        self.assertEqual((p95["ExtendedStatistic"], p95["Threshold"]), ("p95", 0.5))   # metric সেকেন্ডে
        self.assertNotIn("Statistic", p95)                                            # দুটো একসাথে নয়
        self.assertEqual(alarms["lab08-target-5xx"]["TreatMissingData"], "notBreaching")
        for a in alarms.values():
            self.assertLessEqual(a["DatapointsToAlarm"], a["EvaluationPeriods"])
            self.assertEqual(a["AlarmActions"], a["OKActions"])
            self.assertIn({"Key": "Project", "Value": "lab08"}, a["Tags"])


if __name__ == "__main__":
    unittest.main()
