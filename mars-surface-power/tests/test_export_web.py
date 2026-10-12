"""The web exporter: the banned-key guard, the 108 deficits, and a cross-check against build_report on the frozen slice."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from power.export_web import LS, WEB_DATA, banned_key, build, guard, write
from power.slice import build_report


class GuardTests(unittest.TestCase):
    def test_banned_words_are_refused_as_keys_and_as_words_in_keys(self):
        for key in ("score", "safe", "rank", "forecast", "risk_score", "is-safe", "site_rank", "forecasts", "ranking", "safeSite", "Score"):
            with self.assertRaises(ValueError, msg=key):
                guard({"ok": {"nested": [{key: 1}]}})

    def test_ordinary_keys_pass(self):
        for key in ("flux", "dod", "deficits", "source_file", "sha256", "ls", "lat", "lon", "note", "sites"):
            guard({key: 1})
        self.assertFalse(banned_key("interface_label"))

    def test_values_are_not_inspected_only_keys(self):
        guard({"no_power": "No power system was sized. Nothing here is safe or unsafe."})


class ExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.data = build()
        cls.report = build_report()

    def test_108_deficits_match_the_project_report_exactly(self):
        d = self.data["deficits"]
        self.assertEqual(len(d), 108)
        self.assertEqual(len(self.report.deficits), 108)
        self.assertEqual(sum(1 for x in d if x["scenario"] == "warm"), 72)
        self.assertEqual(sum(1 for x in d if x["scenario"] == "storm"), 36)
        ids = {s["id"]: s["name"] for s in self.data["sites"]}
        for mine, theirs in zip(d, self.report.deficits):
            self.assertEqual(ids[mine["site"]], theirs.site)
            self.assertEqual(mine["scenario"], theirs.scenario_key)
            self.assertEqual(mine["ls"], int(theirs.ls))
            self.assertEqual(mine["value"], theirs.value)
            self.assertEqual(mine["dusty_file"], theirs.dusty_file)
            self.assertEqual(mine["baseline_file"], theirs.baseline_file)

    def test_known_values(self):
        d = {(x["site"], x["scenario"], x["ls"]): x["value"] for x in self.data["deficits"]}
        self.assertAlmostEqual(d[("curiosity", "warm", 240)], -163.0, delta=0.5)
        self.assertAlmostEqual(d[("mesopotamia", "storm", 270)], -538.0, delta=0.5)
        s = self.data["series"]
        self.assertEqual([round(r["flux"]) for r in s["curiosity"]["cold"]], [548, 488, 437, 423, 464, 544, 621, 660, 655, 637, 624, 597])
        self.assertAlmostEqual(s["opportunity"]["storm"][6]["flux"], 174.2, delta=0.05)
        self.assertAlmostEqual(s["opportunity"]["storm"][6]["flux"] - s["opportunity"]["cold"][6]["flux"], -451.4248, delta=1e-3)

    def test_storm_exists_only_from_ls_180_and_absent_is_null_not_zero(self):
        for sid, per in self.data["series"].items():
            storm = per["storm"]
            self.assertEqual([r["ls"] for r in storm], list(LS))
            for r in storm:
                if r["ls"] < 180:
                    self.assertIsNone(r["flux"]); self.assertIsNone(r["dod"]); self.assertIsNone(r["file"])
                else:
                    self.assertGreater(r["flux"], 0); self.assertTrue(r["file"]); self.assertEqual(len(r["sha256"]), 64)
            self.assertEqual(sum(r["flux"] is not None for r in storm), 6)
            for k in ("cold", "climatology", "warm"):
                self.assertTrue(all(r["flux"] is not None for r in per[k]))

    def test_storm_optical_depth_matches_the_report_and_range(self):
        names = {s["name"]: s["id"] for s in self.data["sites"]}
        for o in self.report.storm_opacity:
            row = self.data["series"][names[o.site]]["storm"][LS.index(int(o.ls))]
            self.assertEqual(row["dod"], o.value); self.assertEqual(row["file"], o.source_file)
        vals = [o.value for o in self.report.storm_opacity]
        self.assertEqual(len(vals), 36)
        self.assertAlmostEqual(min(vals), 4.74, places=2); self.assertAlmostEqual(max(vals), 6.75, places=2)

    def test_opportunity_points_are_the_61_measured_values_in_their_own_unit(self):
        o = self.data["opportunity"]
        self.assertEqual(len(o["points"]), 61)
        self.assertEqual([(p["sol"], p["ls"], p["value"]) for p in o["points"]], [(p.sol, p.ls, p.value) for p in self.report.opportunity])
        v = [p["value"] for p in o["points"]]
        self.assertEqual((min(v), max(v)), (0.626, 2.259))
        self.assertEqual((o["points"][0]["sol"], o["points"][-1]["sol"]), (5066.542, 5105.61))
        self.assertNotEqual(o["unit"], o["storm_model_unit"])
        self.assertEqual(o["note"], "No conversion factor was applied.")

    def test_sites_scenarios_and_text_carry_the_project_statements(self):
        self.assertEqual([s["id"] for s in self.data["sites"]], ["deuteronilus", "protonilus", "mesopotamia", "curiosity", "perseverance", "opportunity"])
        self.assertEqual([(s["key"], s["dust"]) for s in self.data["scenarios"]], [("cold", 8), ("climatology", 1), ("warm", 7), ("storm", 5)])
        self.assertEqual([s["interface_label"] for s in self.data["scenarios"]], ["cold scenario (low dust, minimum solar)", "climatology average solar scenario", "warm scenario (dusty, maximum solar)", "dust storm average solar scenario"])
        coords = {s["id"]: (s["lat"], s["lon"]) for s in self.data["sites"]}
        self.assertEqual(coords["deuteronilus"], (39.11, 23.199)); self.assertEqual(coords["mesopotamia"], (-35.352, 94.02)); self.assertEqual(coords["opportunity"], (-1.95, 354.47))
        self.assertEqual(self.data["sentences"], list(self.report.sentences)); self.assertEqual(self.data["method"], self.report.method)
        self.assertEqual(self.data["sentences"][-1], "No power system was sized.")
        self.assertEqual(len(self.data["manifest"]), 261)
        self.assertTrue(all(len(m["sha256"]) == 64 for m in self.data["manifest"]))

    def test_no_banned_key_anywhere_and_small(self):
        guard(self.data)
        with tempfile.TemporaryDirectory() as tmp:
            j, s = write(self.data, Path(tmp))
            self.assertLess(j.stat().st_size, 1_000_000); self.assertLess(s.stat().st_size, 1_000_000)
            self.assertEqual(json.loads(j.read_text()), self.data)
            body = s.read_text()
            self.assertIn("window.MARS=", body)
            self.assertEqual(json.loads(body.split("window.MARS=", 1)[1].rstrip().rstrip(";")), self.data)

    def test_committed_export_is_current(self):
        committed = json.loads((WEB_DATA / "mars.json").read_text())
        self.assertEqual(committed, self.data, "run python3 -m power.export_web")
        js = (WEB_DATA / "mars.js").read_text()
        self.assertEqual(json.loads(js.split("window.MARS=", 1)[1].rstrip().rstrip(";")), self.data)


if __name__ == "__main__":
    unittest.main()
