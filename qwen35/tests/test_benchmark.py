"""Controls for benchmark timing boundaries, shared history and summaries."""

from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
from benchmark import execute, summarize


class FakeBackend:
    def __init__(self, events, outputs):
        self.events, self.outputs = events, outputs
        self.index = self.kernels = 0
        self.inputs = []

    def reset(self):
        self.events.append("reset")
        self.index = 0
        self.kernels += 10

    def counters(self):
        return {"kernels": self.kernels}

    def predict(self, tokens):
        self.events.append("predict")
        self.inputs.append(tokens)
        result = self.outputs[self.index]
        self.index += 1
        self.kernels += 1
        return result

    def logits(self):
        self.events.append("logits")
        result = np.zeros(248320)
        result[self.outputs[self.index - 1]] = 1
        return result


class BenchmarkControls(unittest.TestCase):
    def test_reset_and_logit_reads_are_outside_timing_windows(self):
        events = []
        backend = FakeBackend(events, [3, 4, 5])
        expected = np.eye(1, 248320, 3)[0], np.eye(1, 248320, 4)[0], np.eye(1, 248320, 5)[0]
        count = 0
        def timer():
            nonlocal count
            events.append("timer")
            count += 1
            return count * 1_000_000
        with patch("benchmark.time.perf_counter_ns", side_effect=timer):
            result = execute(backend, [1, 2], [3, 4, 5], lambda: events.append("synchronize"), expected)
        self.assertEqual(events, ["reset", "synchronize"] + ["timer", "predict", "timer", "logits"] * 3)
        self.assertEqual(result["decode"]["raw_ms"], [1, 1])
        self.assertEqual(result["kernel_dispatches"], 3)
        self.assertTrue(all(row["passed"] for row in result["diagnostics"]))

    def test_decode_uses_the_cpu_history_when_gpu_predictions_disagree(self):
        backend = FakeBackend([], [9, 9, 9])
        result = execute(backend, [1, 2], [3, 4, 5], lambda: None)
        self.assertEqual(backend.inputs, [[1, 2], [3], [4]])
        self.assertNotEqual(result["predicted_token_ids"], [3, 4, 5])
        self.assertEqual(result["diagnostics"], [])

    def test_summary_uses_trial_throughput_medians(self):
        rows = [dict(timed=dict(prefill_ms=ms, prefill_tokens_per_second=2000/ms,
                                decode=dict(steps_per_second=speed), kernel_dispatches=30))
                for ms, speed in [(10, 100), (20, 50), (100, 10)]]
        result = summarize(rows)
        self.assertEqual(result["median_prefill_ms"], 20)
        self.assertEqual(result["median_decode_tokens_per_second"], 50)
        self.assertEqual(result["trial_prefill_ms"], [10, 20, 100])


if __name__ == "__main__":
    unittest.main()
