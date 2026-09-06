"""Evaluation and verification engine for EXP-2026-003a SWAR 64-Bit ALU Policy."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from python.experiments.exp_2026_002a_ply_mealy.truth_table_mealy import MealyTruthTableEntry
from python.experiments.exp_2026_003a_swar_alu.synthesis_alu import ALUSynthesisReport
from tools.tictactoe import (
    CANONICAL_TIE_BREAKER,
    MinimaxSolver,
    check_win,
    get_legal_mask,
)


@dataclass
class ALUEvaluationReport:
    total_states_evaluated: int
    move_legality_rate: float
    canonical_game_tree_paths: int
    oracle_wins: int
    oracle_draws: int
    oracle_losses: int
    zero_defect_passed: bool
    total_static_instructions: int
    stage_instruction_counts: Dict[str, int]
    max_single_stage_instructions: int
    win_kernel_instructions: int
    threat_kernel_instructions: int
    mux_overhead_instructions: int
    max_dynamic_step_instructions: int
    falsification_gates: Dict[str, bool]
    milestone_verdict: str


class ALUEvaluator:
    """Validates game tree soundness, move legality, and ALU complexity budgets."""

    def __init__(self) -> None:
        self.solver = MinimaxSolver()

    def evaluate_game_tree(self) -> Tuple[int, int, int, int]:
        """Traverses all deterministic play-out paths under canonical policy tau_canon.
        
        Returns (total_paths, wins, draws, losses).
        """
        wins = 0
        draws = 0
        losses = 0

        stack: List[Tuple[int, int, int]] = [(0, 0, 0)]
        paths = 0

        while stack:
            x_bb, o_bb, turn = stack.pop()

            if check_win(x_bb):
                wins += 1
                paths += 1
                continue
            if check_win(o_bb):
                losses += 1
                paths += 1
                continue
            if (x_bb | o_bb) == 0x1FF:
                draws += 1
                paths += 1
                continue

            legal = get_legal_mask(x_bb, o_bb)
            if legal == 0:
                draws += 1
                paths += 1
                continue

            if turn == 0:
                best_move, _ = self.solver.get_best_move(x_bb, o_bb, CANONICAL_TIE_BREAKER)
                stack.append((x_bb | (1 << best_move), o_bb, 1))
            else:
                for cell in range(9):
                    if (legal >> cell) & 1:
                        stack.append((x_bb, o_bb | (1 << cell), 0))

        return paths, wins, draws, losses

    def run_evaluation(
        self,
        entries_by_stage: Dict[int, List[MealyTruthTableEntry]],
        synthesis_report: ALUSynthesisReport,
        output_path: Optional[Path] = None,
    ) -> ALUEvaluationReport:
        """Audits all falsification criteria for Milestone 3 / Rung 4."""
        all_entries = [e for stage_list in entries_by_stage.values() for e in stage_list]
        total_states = len(all_entries)

        # 1. Move legality check
        legal_count = 0
        for e in all_entries:
            x_bb = e.dual_bitboard & 0x1FF
            o_bb = (e.dual_bitboard >> 9) & 0x1FF
            if ((1 << e.canonical_move) & (x_bb | o_bb)) == 0:
                legal_count += 1

        move_legality_rate = round(legal_count / total_states, 6) if total_states > 0 else 0.0

        # 2. Game tree traversal check
        paths, wins, draws, losses = self.evaluate_game_tree()
        zero_defect = (losses == 0) and (move_legality_rate == 1.0) and (paths == 152)

        # 3. Falsification Gates
        # Gate H0-1: Program minimality (<= 25 instructions)
        gate_h0_1 = synthesis_report.total_static_instructions <= 25

        # Gate H0-2: Stage complexity ceilings
        counts = synthesis_report.stage_instruction_counts
        gate_h0_2 = (
            counts.get("f0", 0) == 0
            and counts.get("f1", 0) <= 6
            and counts.get("f2", 0) <= 8
            and counts.get("f3", 0) <= 8
            and counts.get("f4", 0) <= 6
            and synthesis_report.max_single_stage_instructions <= 8
        )

        # Gate H0-3: Win kernel efficiency (<= 4 instructions)
        gate_h0_3 = synthesis_report.win_kernel_instruction_count <= 4

        # Gate H0-4: Zero multiplexer overhead (N_mux == 0)
        gate_h0_4 = synthesis_report.mux_overhead_instructions == 0

        # Invariant 5: Oracle soundness
        gate_inv5 = zero_defect and (total_states == 2423)

        falsification_gates = {
            "gate_h0_1_program_minimality": gate_h0_1,
            "gate_h0_2_stage_ceilings": gate_h0_2,
            "gate_h0_3_win_kernel_efficiency": gate_h0_3,
            "gate_h0_4_zero_mux_overhead": gate_h0_4,
            "gate_invariant_5_oracle_soundness": gate_inv5,
        }

        all_passed = all(falsification_gates.values())
        verdict = "PASS" if all_passed else "FAIL"

        report = ALUEvaluationReport(
            total_states_evaluated=total_states,
            move_legality_rate=move_legality_rate,
            canonical_game_tree_paths=paths,
            oracle_wins=wins,
            oracle_draws=draws,
            oracle_losses=losses,
            zero_defect_passed=zero_defect,
            total_static_instructions=synthesis_report.total_static_instructions,
            stage_instruction_counts=synthesis_report.stage_instruction_counts,
            max_single_stage_instructions=synthesis_report.max_single_stage_instructions,
            win_kernel_instructions=synthesis_report.win_kernel_instruction_count,
            threat_kernel_instructions=synthesis_report.threat_kernel_instruction_count,
            mux_overhead_instructions=synthesis_report.mux_overhead_instructions,
            max_dynamic_step_instructions=synthesis_report.max_dynamic_step_instructions,
            falsification_gates=falsification_gates,
            milestone_verdict=verdict,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2)

        return report
