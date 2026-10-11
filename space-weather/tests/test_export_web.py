"""The web exporter: banned-key guard, honest nulls, and the real September 2017 payload."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

from weather import export_web as E
from weather.assemble import assemble
from weather.parse import Alert, Point
from weather.storm import RAW, ROOT, build_report

HAVE_RAW = (RAW / "g13_epead_cpflux_5m_20170901_20170930.csv").exists()


def _utc(*a):
    return datetime(*a, tzinfo=timezone.utc)


class BannedKeyTests(unittest.TestCase):
    def test_refuses_each_banned_key_at_any_depth(self):
        for key in ("score", "safe", "rank", "forecast", "Score", "FORECAST", "risk_score", "is-safe", "forecastNote", "rankOrder"):
            with self.assertRaises(E.BannedKeyError, msg=key):
                E.check_keys({"a": {"b": [{key: 1}]}})

    def test_allows_ordinary_keys(self):
        E.check_keys({"samples": [{"peak": 1}], "source_file": "x", "hours_at_or_above": 2, "scoreboard_free": 0})

    def test_write_refuses_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(E.BannedKeyError):
                E.write({"audiences": {"crew": {"score": 3}}}, tmp)
            self.assertEqual(list(Path(tmp).iterdir()), [])


class SyntheticTests(unittest.TestCase):
    def setUp(self):
        start = _utc(2020, 1, 1, 0)
        end = start + timedelta(minutes=30)

        def at(m, v, prod, unit="p/(cm^2 s sr)"):
            return Point(start + timedelta(minutes=m), v, unit, prod, "goes.csv")

        # the 10-minute slot is absent (flagged or missing upstream): it must come out as None, not 0
        g10 = [at(0, 50.0, "GOES-13 EPEAD ZPGT10E"), at(5, 150.0, "GOES-13 EPEAD ZPGT10E"), at(15, 200.0, "GOES-13 EPEAD ZPGT10E"), at(20, 90.0, "GOES-13 EPEAD ZPGT10E"), at(25, 120.0, "GOES-13 EPEAD ZPGT10E")]
        g100 = [at(0, 0.5, "GOES-13 EPEAD ZPGT100E"), at(5, 2.0, "GOES-13 EPEAD ZPGT100E")]
        dose = [Point(start + timedelta(minutes=1), 11.5, "uGy/hour", "CRaTER-D1D2", "dose.csv")]
        alerts = [
            Alert("proton", start + timedelta(minutes=2), None, 10.0, ">=", "10MeV", "pfu", "SWPC PRF 1", "a.pdf", "alert"),
            Alert("geomagnetic", start + timedelta(minutes=3), None, 7.0, "=", "K", "K", "SWPC PRF 1", "a.pdf", "alert"),
            Alert("geomagnetic", start, start + timedelta(minutes=20), 7.0, ">=", "K", "K", "SWPC PRF 1", "a.pdf", "extended warning"),
        ]
        self.report = assemble(alerts=alerts, proton_gt10=g10, proton_gt100=g100, dose=dose, window_start=start, window_end=end, storm="synthetic")
        self.alerts = alerts
        self.payload = E.build_payload(self.report, alerts, quality=None, manifest=[])

    def test_missing_slots_are_null_never_zero(self):
        values = self.payload["series"]["gt10"]["values"]
        self.assertEqual(len(values), 6)
        self.assertIsNone(values[2])
        self.assertNotIn(0, [v for v in values if v is not None])
        self.assertEqual(self.payload["series"]["gt100"]["values"][2:], [None] * 4)
        self.assertEqual(self.payload["audiences"]["polar"]["stats"]["samples_without_value"], 1)

    def test_counts_come_from_the_series_and_agree_with_the_sentence(self):
        st = self.payload["audiences"]["polar"]["stats"]
        self.assertEqual((st["samples_at_or_above"], st["minutes_at_or_above"]), (3, 15))
        self.assertEqual((st["peak"], st["peak_time"]), (200.0, "2020-01-01T00:15:00Z"))
        self.assertEqual(st["separate_stretches"], 3)
        self.assertIn("has 3 samples", self.payload["sentences"][1])

    def test_alerts_and_warning_are_typed_separately(self):
        a = self.payload["alerts"]
        self.assertEqual([x["type"] for x in a["proton"]], ["proton_alert"])
        self.assertEqual([x["type"] for x in a["grid_issued"]], ["grid_issued_alert"])
        self.assertEqual([x["type"] for x in a["grid_warnings"]], ["grid_warning"])
        self.assertFalse(a["grid_warnings"][0]["observed_k"])
        self.assertFalse(self.payload["audiences"]["grid"]["stats"]["warning_is_observed_k"])

    def test_dose_is_a_separate_copied_series(self):
        d = self.payload["series"]["dose"]
        self.assertFalse(d["derived_from_flux"])
        self.assertEqual((d["t_seconds"], d["values"]), ([60], [11.5]))
        self.assertIn("lunar orbit", d["where"])

    def test_payload_has_no_banned_keys_and_is_strict_json(self):
        E.check_keys(self.payload)
        json.dumps(self.payload, allow_nan=False)


@unittest.skipUnless(HAVE_RAW, "data/raw is not populated (fetch the files in data/MANIFEST.tsv)")
class RealStormTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = build_report()
        cls.payload = E.build_payload(cls.report)

    def test_numbers_match_the_project_sentences(self):
        a = self.payload["audiences"]
        crew, polar = a["crew"]["stats"], a["polar"]["stats"]
        self.assertEqual((polar["samples_at_or_above"], polar["minutes_at_or_above"], polar["first_at_or_above"], polar["last_at_or_above"]), (997, 4985, "2017-09-05T07:15:00Z", "2017-09-12T21:30:00Z"))
        self.assertEqual((polar["peak"], polar["peak_time"]), (1493.5, "2017-09-11T11:45:00Z"))
        self.assertEqual((crew["samples_at_or_above"], crew["minutes_at_or_above"], crew["first_at_or_above"], crew["last_at_or_above"]), (661, 3305, "2017-09-10T16:25:00Z", "2017-09-13T03:30:00Z"))
        self.assertEqual(crew["peak_time"], "2017-09-10T22:15:00Z")
        self.assertAlmostEqual(crew["peak"], 68.1, places=1)
        self.assertEqual(a["crew"]["dose"]["max"], 22968.75)
        self.assertEqual(a["crew"]["dose"]["min_time"], "2017-09-04T14:00:00Z")
        self.assertEqual(self.payload["sentences"], list(self.report.sentences))

    def test_alert_counts_and_warning(self):
        al = self.payload["alerts"]
        self.assertEqual(len(al["proton"]), 29)
        self.assertEqual([x["start"] for x in al["grid_issued"]][0], "2017-09-07T23:25:00Z")
        self.assertEqual((len(al["grid_issued"]), al["grid_issued"][-1]["start"]), (7, "2017-09-08T16:04:00Z"))
        chosen = [w for w in al["grid_warnings"] if w["longest_in_sentence"]]
        self.assertEqual(len(chosen), 1)
        self.assertEqual((chosen[0]["start"], chosen[0]["end"], chosen[0]["hours_valid"]), ("2017-09-07T23:00:00Z", "2017-09-08T21:00:00Z", 22.0))
        for x in al["proton"] + al["grid_issued"] + al["grid_warnings"]:
            self.assertTrue(x["source_file"].endswith(".pdf") and x["product_id"].startswith("SWPC PRF"))

    def test_quality_flags_are_respected_and_reported(self):
        q = self.payload["series"]["quality"]
        self.assertEqual(q["slots_without_value"], {"gt10": 2, "gt100": 2})
        self.assertEqual(q["csv_rows"]["ZPGT10E"]["flagged_nonzero"], 2)
        for key in ("gt10", "gt100"):
            vals = self.payload["series"][key]["values"]
            self.assertEqual(len(vals), 3168)
            self.assertEqual(sum(v is None for v in vals), 2)
        self.assertFalse(self.payload["series"]["downsampling"]["applied"])

    def test_manifest_entries_carry_sha256_and_url(self):
        m = {x["filename"]: x for x in self.payload["manifest"]}
        self.assertEqual(len(m), 5)
        for x in m.values():
            self.assertEqual(len(x["sha256"]), 64)
            self.assertTrue(x["url"].startswith("https://"))

    def test_committed_files_are_small_twins_without_banned_keys(self):
        data = ROOT / "web" / "data"
        js, js_json = (data / "storm.js").read_text(encoding="utf-8"), (data / "storm.json").read_text(encoding="utf-8")
        self.assertTrue(js.startswith("window.STORM=") and js.rstrip().endswith(";"))
        self.assertEqual(js[len("window.STORM="):].rstrip().rstrip(";"), js_json.strip())
        E.check_keys(json.loads(js_json))
        self.assertLess(sum(p.stat().st_size for p in data.iterdir() if p.is_file()), 2_000_000)
        self.assertEqual(json.loads(js_json), json.loads(json.dumps(self.payload)))


if __name__ == "__main__":
    unittest.main()
