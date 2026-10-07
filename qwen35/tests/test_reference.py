"""CPU-only controls for the independent recurrence and verification gate."""

from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from reference import OriginalWeights, recurrent
from verify import compare


class ReferenceControls(unittest.TestCase):
    def test_delta_rule_with_decay_and_unequal_key_value_widths(self):
        q = np.array([[[1., 0.]], [[1., 1.]]])
        k = np.array([[[1., 0.]], [[0., 1.]]])
        v = np.array([[[2., 4., 6.]], [[5., 7., 9.]]])
        decay, beta = np.array([[1.], [.25]]), np.array([[.5], [1.]])
        initial = np.zeros((1, 2, 3))
        output, state = recurrent(q, k, v, decay, beta, initial)
        np.testing.assert_array_equal(output, [[[1., 2., 3.]], [[5.25, 7.5, 9.75]]])
        np.testing.assert_array_equal(state, [[[.25, .5, .75], [5., 7., 9.]]])
        first, saved = recurrent(q[:1], k[:1], v[:1], decay[:1], beta[:1], initial)
        second, final = recurrent(q[1:], k[1:], v[1:], decay[1:], beta[1:], saved)
        np.testing.assert_array_equal(np.concatenate((first, second)), output)
        np.testing.assert_array_equal(final, state)
        np.testing.assert_array_equal(initial, 0)

    def test_original_bfloat_values_are_preserved_without_transport_rounding(self):
        reader = object.__new__(OriginalWeights)
        reader.entries = {"weight": {"dtype": "BF16"}}
        raw = np.array([0x3f80, 0xbf00, 1], dtype=np.uint16)
        expected = np.array([1., -.5, 2. ** -133], dtype=np.float64)
        np.testing.assert_array_equal(reader.decode("weight", raw), expected)

    def test_numeric_bound_and_selected_token_are_both_required(self):
        reference = np.zeros(248320)
        reference[41] = 1
        actual = reference.copy()
        actual[3] = .04999
        self.assertTrue(compare(actual, reference, 41)["passed"])
        self.assertFalse(compare(actual, reference, 42)["passed"])
        actual[3] = .05001
        row = compare(actual, reference, 41)
        self.assertFalse(row["passed"])
        self.assertEqual(row["values_outside_bound"], 1)

    def test_nonfinite_and_partial_vectors_cannot_pass(self):
        reference = np.zeros(248320)
        for value in (np.nan, np.inf, -np.inf):
            actual = reference.copy()
            actual[0] = value
            with self.assertRaises(ValueError):
                compare(actual, reference, 0)
            with self.assertRaises(ValueError):
                compare(reference, actual, 0)
        with self.assertRaises(ValueError):
            compare(reference[:-1], reference, 0)


if __name__ == "__main__":
    unittest.main()
