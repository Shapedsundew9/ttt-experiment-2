"""Comprehensive unit test suite for EXP-2026-002a State-Factored Ply Decomposition Mealy Machine."""

import json
from pathlib import Path
import unittest

from python.experiments.exp_2026_002a_ply_mealy.evaluator import ExperimentEvaluator
from python.experiments.exp_2026_002a_ply_mealy.ply_partition import (
    generate_partitioned_states,
)
from python.experiments.exp_2026_002a_ply_mealy.synthesis_mealy import MealySynthesizer
from python.experiments.exp_2026_002a_ply_mealy.truth_table_mealy import (
    generate_mealy_truth_tables,
    to_4bit_binary,
)
from python.scripts.reduce_telemetry import reduce_telemetry_002a
from tools.tictactoe import MinimaxSolver


class TestExperiment002a(unittest.TestCase):
    """Unit test suite for EXP-2026-002a."""

    @classmethod
    def setUpClass(cls):
        cls.partition = generate_partitioned_states()
        cls.solver = MinimaxSolver()
        cls.tt_by_stage = generate_mealy_truth_tables(cls.partition, cls.solver)
        cls.synthesizer = MealySynthesizer()
        cls.dags, cls.syn_report = cls.synthesizer.run_full_synthesis(cls.tt_by_stage)
        cls.evaluator = ExperimentEvaluator()

    def test_ply_partition_cardinalities(self):
        """Invariant 4: Total non-terminal reachable states = 2,423 with exact ply partition."""
        self.assertEqual(self.partition.total_states, 2423)
        expected = {0: 1, 2: 72, 4: 756, 6: 1372, 8: 222}
        self.assertEqual(self.partition.ply_counts, expected)

    def test_dense_4bit_encoding(self):
        """Validates that cell coordinates 0..8 map invertibly to 4-bit binary strings."""
        for cell in range(9):
            b_str = to_4bit_binary(cell)
            self.assertEqual(len(b_str), 4)
            self.assertEqual(int(b_str, 2), cell)
        with self.assertRaises(ValueError):
            to_4bit_binary(9)

    def test_constant_f0_stage(self):
        """Stage 0 sub-function f0 requires 0 gates and depth 0."""
        _, f0_res = self.synthesizer.synthesize_stage_f0(self.tt_by_stage[0], "dual")
        self.assertEqual(f0_res.gate_count, 0)
        self.assertEqual(f0_res.dag_depth, 0)

    def test_forced_f4_open_cell(self):
        """Stage 4 priority encoder extracts unique open cell with <= 8 gates."""
        _, f4_res = self.synthesizer.synthesize_stage_f4(self.tt_by_stage[4], "dual")
        self.assertLessEqual(f4_res.gate_count, 8)
        self.assertLessEqual(f4_res.dag_depth, 3)

    def test_branchless_multiplexer_complexity(self):
        """Stage decoder + 4-bit multiplexer tree satisfies <= 20 gates and <= 3 depth."""
        _, mux_res = self.synthesizer.synthesize_branchless_multiplexer()
        self.assertLessEqual(mux_res.gate_count, 20)
        self.assertLessEqual(mux_res.dag_depth, 3)

    def test_oracle_zero_losses_and_move_legality(self):
        """Canonical Minimax Oracle achieves 0 losses and 100% legal moves."""
        paths, wins, draws, losses = self.evaluator.evaluate_game_tree()
        self.assertEqual(paths, 152)
        self.assertEqual(wins, 142)
        self.assertEqual(draws, 10)
        self.assertEqual(losses, 0)

        eval_report = self.evaluator.run_evaluation(self.tt_by_stage, self.syn_report)
        self.assertEqual(eval_report.move_legality_rate, 1.0)
        self.assertEqual(eval_report.milestone_verdict, "PASS")
        self.assertTrue(all(eval_report.falsification_gates.values()))

    def test_telemetry_reduction_002a(self):
        """Validates that reduce_telemetry_002a produces a valid summary_reduced.json."""
        test_out = Path("data/telemetry/EXP-2026-002a/test_summary_reduced.json")
        reduce_telemetry_002a(Path("data/telemetry/EXP-2026-002a"), test_out)
        self.assertTrue(test_out.exists())

        with open(test_out, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["experiment_id"], "EXP-2026-002a")
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["metrics"]["total_reachable_x_states"], 2423)
        self.assertGreaterEqual(data["metrics"]["gate_reduction_delta_n_mealy"], 0.20)
        self.assertGreaterEqual(data["metrics"]["dag_depth_reduction_delta_d_mealy"], 0.25)
        test_out.unlink()


if __name__ == "__main__":
    unittest.main()
