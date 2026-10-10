import unittest

from atlas.export_web import _check


class ExportGuardTest(unittest.TestCase):
    def test_rejects_combined_score_keys(self):
        with self.assertRaises(RuntimeError):
            _check({"a": {"score": 1}})

    def test_accepts_plain_values(self):
        _check({"query": {"slope_deg": 2.9}, "series": ["0101"]})


if __name__ == "__main__":
    unittest.main()
