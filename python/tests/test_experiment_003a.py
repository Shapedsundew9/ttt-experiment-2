"""Comprehensive unit test suite for EXP-2026-003a SWAR Bitboard & 64-Bit ALU Arithmetic Synthesis."""

import json
from pathlib import Path
import unittest

from python.experiments.exp_2026_002a_ply_mealy.ply_partition import (
    generate_partitioned_states,
)
from python.experiments.exp_2026_002a_ply_mealy.truth_table_mealy import (
    generate_mealy_truth_tables,
)
from python.experiments.exp_2026_003a_swar_alu.evaluator import ALUEvaluator
from python.experiments.exp_2026_003a_swar_alu.synthesis_alu import ALUSynthesizer
from python.experiments.exp_2026_003a_swar_alu.swar_engine import (
    WIN_LINES,
    compute_stage_index,
    evaluate_swar_threat,
    evaluate_swar_win,
    extract_open_cell_coordinate,
    project_swar,
    run_swar_microbenchmarks,
)
from python.scripts.reduce_telemetry import reduce_telemetry_003a
from tools.tictactoe import MinimaxSolver


class TestExperiment003a(unittest.TestCase):
    """Unit test suite for EXP-2026-003a."""

    @classmethod
    def setUpClass(cls):
        cls.partition = generate_partitioned_states()
        cls.solver = MinimaxSolver()
        cls.entries_by_stage = generate_mealy_truth_tables(cls.partition, cls.solver)
        cls.synthesizer = ALUSynthesizer()
        cls.syn_report = cls.synthesizer.run_full_alu_synthesis(cls.entries_by_stage)
        cls.evaluator = ALUEvaluator()

    def test_swar_bitboard_projection(self):
        """SWAR engine projects 9-bit bitboards into 8 byte lanes correctly."""
        # Empty bitboard
        self.assertEqual(project_swar(0), 0)

        # Full bitboard (0x1FF)
        swar_full = project_swar(0x1FF)
        for lane in range(8):
            lane_byte = (swar_full >> (lane * 8)) & 0xFF
            self.assertEqual(lane_byte, 0x07)

        # Single winning line (e.g. line 0: cells 0, 1, 2 -> bits 0, 1, 2)
        bb_line0 = (1 << 0) | (1 << 1) | (1 << 2)
        swar_line0 = project_swar(bb_line0)
        # Lane 0 should have 0x07
        self.assertEqual(swar_line0 & 0xFF, 0x07)

    def test_swar_win_kernel_accuracy_and_instruction_bound(self):
        """SWAR win kernel runs in <= 4 instructions and correctly detects wins."""
        from tools.tictactoe import check_win

        # Exhaustive verification across all 512 bitboards
        for bb in range(512):
            swar_val = project_swar(bb)
            k_win, ops = evaluate_swar_win(swar_val)
            self.assertEqual(ops, 4)
            expected_win = check_win(bb)
            actual_win = k_win > 0
            self.assertEqual(
                actual_win,
                expected_win,
                f"Mismatch for bitboard 0x{bb:03x}: expected {expected_win}, got {actual_win}",
            )

    def test_swar_threat_kernel_accuracy(self):
        """SWAR threat kernel identifies threats where 2 of 3 cells are occupied and 1 empty."""
        # X has cells 0, 1; cell 2 is empty -> threat in line 0
        bb_x = (1 << 0) | (1 << 1)
        bb_e = 1 << 2
        swar_x = project_swar(bb_x)
        swar_e = project_swar(bb_e)
        threat, ops = evaluate_swar_threat(swar_x, swar_e)
        self.assertLessEqual(ops, 5)
        self.assertGreater(threat, 0)

        # Blocked: X has 0, 1; empty mask does not have 2 -> no threat
        threat_blocked, _ = evaluate_swar_threat(swar_x, 0)
        self.assertEqual(threat_blocked, 0)

    def test_stage_index_computation(self):
        """t = popcount(X | O) >> 1 computes correct stage index in 2 ALU instructions."""
        t, ops = compute_stage_index(0, 0)
        self.assertEqual(t, 0)
        self.assertEqual(ops, 2)

        # Ply 4: 2 X marks, 2 O marks -> popcount 4 -> stage 2
        t, ops = compute_stage_index(0b101, 0b01010)
        self.assertEqual(t, 2)
        self.assertEqual(ops, 2)

    def test_open_cell_extraction(self):
        """extract_open_cell_coordinate converts 1-hot open cell into 4-bit coordinate."""
        for cell in range(9):
            coord, ops = extract_open_cell_coordinate(1 << cell)
            self.assertEqual(coord, cell)
            self.assertLessEqual(ops, 4)

    def test_alu_instruction_counts_and_gate_ceilings(self):
        """Unified ALU policy satisfies <= 25 instructions and each stage <= 8."""
        total_instructions = self.syn_report.total_static_instructions
        self.assertLessEqual(total_instructions, 25)

        # Stage ceilings: f0 = 0, f1 <= 6, f2 <= 8, f3 <= 8, f4 <= 6
        ceilings = {"f0": 0, "f1": 6, "f2": 8, "f3": 8, "f4": 6}
        for stage_name, count in self.syn_report.stage_instruction_counts.items():
            self.assertLessEqual(
                count,
                ceilings[stage_name],
                f"Stage {stage_name} exceeded ceiling {ceilings[stage_name]}: got {count}",
            )

        # Sequential dispatch overhead is 0 (N_mux = 0)
        self.assertEqual(self.syn_report.mux_overhead_instructions, 0)

    def test_oracle_zero_losses_and_move_legality(self):
        """64-bit ALU SWAR policy achieves 0 losses and 100% legal moves."""
        paths, wins, draws, losses = self.evaluator.evaluate_game_tree()
        self.assertEqual(paths, 152)
        self.assertEqual(wins, 142)
        self.assertEqual(draws, 10)
        self.assertEqual(losses, 0)

        report = self.evaluator.run_evaluation(self.entries_by_stage, self.syn_report)
        self.assertEqual(report.move_legality_rate, 1.0)
        self.assertEqual(report.milestone_verdict, "PASS")
        self.assertTrue(all(report.falsification_gates.values()))

    def test_telemetry_reduction_003a(self):
        """Validates that reduce_telemetry_003a produces a valid summary_reduced.json."""
        test_out = Path("data/telemetry/EXP-2026-003a/test_summary_reduced.json")
        reduce_telemetry_003a(Path("data/telemetry/EXP-2026-003a"), test_out)
        self.assertTrue(test_out.exists())

        with open(test_out, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertEqual(data["experiment_id"], "EXP-2026-003a")
        self.assertEqual(data["status"], "PASS")
        self.assertEqual(data["metrics"]["total_reachable_x_states"], 2423)
        self.assertLessEqual(data["metrics"]["total_static_alu_instructions"], 25)
        self.assertEqual(data["metrics"]["stage_dispatch_mux_instructions"], 0)
        self.assertEqual(data["metrics"]["oracle_losses"], 0)
        test_out.unlink()


if __name__ == "__main__":
    unittest.main()
