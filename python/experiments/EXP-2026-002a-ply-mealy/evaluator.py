"""Independent evaluation and verification engine for EXP-2026-002a."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from python.experiments.exp_2026_002a_ply_mealy.synthesis_mealy import MealySynthesisReport
from python.experiments.exp_2026_002a_ply_mealy.truth_table_mealy import MealyTruthTableEntry
from tools.tictactoe import (
    CANONICAL_TIE_BREAKER,
    MinimaxSolver,
    check_win,
    get_legal_mask,
)


@dataclass
class EvaluationReport:
    total_states_evaluated: int
    move_legality_rate: float
    game_tree_paths: int
    oracle_wins: int
    oracle_draws: int
    oracle_losses: int
    zero_defect_invariant_passed: bool
    condition_metrics: Dict[str, Any]
    falsification_gates: Dict[str, bool]
    milestone_verdict: str


class ExperimentEvaluator:
    """Validates game tree correctness, move legality, and pre-registered falsification gates."""

    def __init__(self) -> None:
        self.solver = MinimaxSolver()

    def evaluate_game_tree(self) -> Tuple[int, int, int, int]:
        """Traverses all deterministic play-out paths under canonical policy tau_canon against all legal opponent moves.
        
        Returns (total_paths, wins, draws, losses).
        """
        wins = 0
        draws = 0
        losses = 0

        # Stack contains (x_bb, o_bb, turn)
        # turn: 0 for X, 1 for O
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
                # X moves according to canonical minimax policy
                best_move, _ = self.solver.get_best_move(x_bb, o_bb, CANONICAL_TIE_BREAKER)
                stack.append((x_bb | (1 << best_move), o_bb, 1))
            else:
                # O branches across all legal countermoves
                for cell in range(9):
                    if (legal >> cell) & 1:
                        stack.append((x_bb, o_bb | (1 << cell), 0))

        return paths, wins, draws, losses

    def run_evaluation(
        self,
        entries_by_stage: Dict[int, List[MealyTruthTableEntry]],
        synthesis_report: MealySynthesisReport,
        output_path: Optional[Path] = None,
    ) -> EvaluationReport:
        """Executes full evaluation and audits all falsification criteria."""
        all_entries = [e for stage_list in entries_by_stage.values() for e in stage_list]
        total_states = len(all_entries)

        # 1. Move legality audit
        legal_count = 0
        for e in all_entries:
            # Decode dual bitboard to x and o
            x_bb = e.dual_bitboard & 0x1FF
            o_bb = (e.dual_bitboard >> 9) & 0x1FF
            if ((1 << e.canonical_move) & (x_bb | o_bb)) == 0:
                legal_count += 1

        move_legality_rate = round(legal_count / total_states, 6) if total_states > 0 else 0.0

        # 2. Game tree traversal audit
        paths, wins, draws, losses = self.evaluate_game_tree()
        zero_defect = (losses == 0) and (move_legality_rate == 1.0) and (paths == 152)

        # 3. Pre-registered Gate Audits
        # Gate H0-1: Subcone bounds
        subcone_bounds = [0, 12, 28, 32, 8]
        gate_h0_1 = True
        for stg, max_b in enumerate(subcone_bounds):
            gc = synthesis_report.condition_c_state_factored_dual[stg].gate_count
            if gc > max_b or gc >= 45:
                gate_h0_1 = False

        # Gate H0-2: Encoding collapse (<= 45 gates)
        gate_h0_2 = synthesis_report.condition_a_monolithic_dual.gate_count <= 45

        # Gate H0-3: Representation advantage
        gate_h0_3 = (
            synthesis_report.delta_n_mealy >= 0.20
            and synthesis_report.delta_d_mealy >= 0.25
            and all(v >= 0.20 for v in synthesis_report.operational_ply_delta_n.values())
        )

        # Gate H0-4: Multiplexer overhead (<= 20 gates, depth <= 3)
        mux_gates = synthesis_report.condition_e_multiplexer_benchmark.gate_count
        mux_depth = synthesis_report.condition_e_multiplexer_benchmark.dag_depth
        gate_h0_4 = (mux_gates <= 20) and (mux_depth <= 3)

        # Invariant 5: Zero defect soundness
        gate_inv5 = zero_defect and (total_states == 2423)

        falsification_gates = {
            "gate_h0_1_subcone_bounds": gate_h0_1,
            "gate_h0_2_encoding_collapse": gate_h0_2,
            "gate_h0_3_representation_advantage": gate_h0_3,
            "gate_h0_4_mux_overhead": gate_h0_4,
            "gate_invariant_5_oracle_soundness": gate_inv5,
        }

        all_passed = all(falsification_gates.values())
        milestone_verdict = "PASS" if all_passed else "FAIL"

        condition_metrics = {
            "monolithic_dual_4bit_gates": synthesis_report.condition_a_monolithic_dual.gate_count,
            "monolithic_interleaved_4bit_gates": synthesis_report.condition_b_monolithic_interleaved.gate_count,
            "combined_mealy_dual_gates": synthesis_report.combined_mealy_dual_gates,
            "combined_mealy_interleaved_gates": synthesis_report.combined_mealy_interleaved_gates,
            "combined_mealy_dual_depth": synthesis_report.combined_mealy_dual_depth,
            "combined_mealy_interleaved_depth": synthesis_report.combined_mealy_interleaved_depth,
            "delta_n_mealy": synthesis_report.delta_n_mealy,
            "delta_d_mealy": synthesis_report.delta_d_mealy,
            "operational_ply_delta_n": synthesis_report.operational_ply_delta_n,
            "multiplexer_gates": mux_gates,
            "multiplexer_depth": mux_depth,
            "decoder_penalty_gates": synthesis_report.condition_e_decoder_benchmark.gate_count,
        }

        report = EvaluationReport(
            total_states_evaluated=total_states,
            move_legality_rate=move_legality_rate,
            game_tree_paths=paths,
            oracle_wins=wins,
            oracle_draws=draws,
            oracle_losses=losses,
            zero_defect_invariant_passed=zero_defect,
            condition_metrics=condition_metrics,
            falsification_gates=falsification_gates,
            milestone_verdict=milestone_verdict,
        )

        if output_path:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(asdict(report), f, indent=2)

        return report
