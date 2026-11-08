import unittest
from analyze import bpb, bootstrap_ci, paired_diff_ci, FILTERS

def r(i, bits, nbytes, cat="code"): return {"id": str(i), "bits": bits, "bytes": nbytes, "category": cat}

class T(unittest.TestCase):
    def test_bpb_is_byte_weighted(self):
        self.assertAlmostEqual(bpb([r(1, 100, 100), r(2, 300, 100)]), 2.0)
        self.assertAlmostEqual(bpb([r(1, 10, 10), r(2, 900, 90)]), 9.1)
    def test_bootstrap_ci_contains_point_and_is_deterministic(self):
        rows = [r(i, i * 3 + 7, 10 + i) for i in range(30)]
        a, b = bootstrap_ci(rows, seed=1), bootstrap_ci(rows, seed=1)
        self.assertEqual(a, b); self.assertLessEqual(a[0], bpb(rows)); self.assertGreaterEqual(a[1], bpb(rows))
    def test_paired_diff_zero_for_identical(self):
        rows = [r(i, i + 5, 10) for i in range(20)]
        pt, (lo, hi) = paired_diff_ci(rows, rows)
        self.assertEqual((pt, lo, hi), (0.0, 0.0, 0.0))
    def test_paired_diff_constant_shift(self):
        a = [r(i, 20, 10) for i in range(20)]; b = [r(i, 10, 10) for i in range(20)]
        pt, (lo, hi) = paired_diff_ci(a, b); self.assertAlmostEqual(pt, 1.0); self.assertAlmostEqual(lo, 1.0); self.assertAlmostEqual(hi, 1.0)
    def test_filters(self):
        rows = [r(1, 1, 1, "code"), r(2, 1, 1, "generated"), r(3, 1, 1, "docs")]
        self.assertEqual(sum(FILTERS["code-only"](x) for x in rows), 1)
        self.assertEqual(sum(FILTERS["no-generated"](x) for x in rows), 2)
        self.assertEqual(sum(FILTERS["code+docs"](x) for x in rows), 2)
if __name__ == "__main__": unittest.main()
