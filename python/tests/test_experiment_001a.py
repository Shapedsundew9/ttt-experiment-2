"""Unit tests for EXP-2026-001a tools and experiment modules."""

import unittest

from python.experiments.exp_2026_001a_minimax_baseline.config import ExperimentConfig
from python.experiments.exp_2026_001a_minimax_baseline.evaluator import evaluate_synthesis_comparison
from python.experiments.exp_2026_001a_minimax_baseline.synthesis import LogicSynthesizer
from tools.boolean_dag import BooleanDAG, GateOp, build_interleaved_decoder_dag
from tools.tictactoe import (
    CANONICAL_TIE_BREAKER,
    MinimaxSolver,
    check_win,
    enumerate_uci_endgames,
    from_dual_bitboard,
    from_interleaved,
    get_legal_mask,
    to_dual_bitboard,
    to_interleaved,
)


class TicTacToeDomainTests(unittest.TestCase):
    def test_win_check(self) -> None:
        # Row 0 win
        self.assertTrue(check_win(0x007))
        # Col 0 win
        self.assertTrue(check_win(0x049))
        # Diag 0 win
        self.assertTrue(check_win(0x111))
        # Incomplete
        self.assertFalse(check_win(0x003))

    def test_representation_roundtrip(self) -> None:
        x_bb = 0x055
        o_bb = 0x0AA
        # Dual bitboard
        dual = to_dual_bitboard(x_bb, o_bb)
        dec_x, dec_o = from_dual_bitboard(dual)
        self.assertEqual((dec_x, dec_o), (x_bb, o_bb))

        # Interleaved
        inter = to_interleaved(x_bb, o_bb)
        dec_x_i, dec_o_i = from_interleaved(inter)
        self.assertEqual((dec_x_i, dec_o_i), (x_bb, o_bb))

    def test_minimax_root_draw(self) -> None:
        solver = MinimaxSolver()
        val = solver.minimax(0, 0, 0)
        self.assertEqual(val, 0)  # Game-theoretic draw from root

    def test_uci_endgames_count(self) -> None:
        endgames = enumerate_uci_endgames()
        self.assertEqual(len(endgames), 958)

    def test_decoder_dag(self) -> None:
        dag = build_interleaved_decoder_dag()
        self.assertEqual(dag.gate_count, 18)
        self.assertEqual(dag.compute_depth(), 1)
        # Test evaluation on cell 0 having X: b_0 = 1, b_1 = 0 -> X_0 = 1, O_0 = 0
        res = dag.evaluate(0x01)
        # Bit 0 is X_0, bit 9 is O_0
        self.assertEqual(res & 1, 1)
        self.assertEqual((res >> 9) & 1, 0)


class SynthesisEvaluationTests(unittest.TestCase):
    def test_decoder_penalty_reduction(self) -> None:
        synthesizer = LogicSynthesizer()
        res_decoder = synthesizer.synthesize_decoder_benchmark()
        self.assertEqual(res_decoder.gate_count, 18)


if __name__ == "__main__":
    unittest.main()
