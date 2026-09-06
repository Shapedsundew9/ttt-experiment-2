"""Main CLI orchestration entry point for EXP-2026-002a."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import time
import sys
from typing import Dict, List, Optional

root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from python.experiments.exp_2026_002a_ply_mealy.config import load_config
from python.experiments.exp_2026_002a_ply_mealy.evaluator import ExperimentEvaluator
from python.experiments.exp_2026_002a_ply_mealy.ply_partition import (
    export_partition_stats,
    generate_partitioned_states,
)
from python.experiments.exp_2026_002a_ply_mealy.synthesis_mealy import (
    MealySynthesizer,
    StageSynthesisResult,
)
from python.experiments.exp_2026_002a_ply_mealy.truth_table_mealy import (
    emit_complete_json,
    emit_multiplexer_pla,
    emit_ply_pla,
    generate_mealy_truth_tables,
)
from tools.tictactoe import MinimaxSolver


def serialize_synthesis_report(report) -> Dict:
    """Serializes MealySynthesisReport into a JSON-compatible dictionary."""
    def _stage_res_dict(res: StageSynthesisResult) -> Dict:
        return {
            "stage": res.stage,
            "ply": res.ply,
            "representation": res.representation,
            "gate_count": res.gate_count,
            "dag_depth": res.dag_depth,
            "operator_distribution": res.operator_distribution,
            "synthesis_time_seconds": res.synthesis_time_seconds,
            "accuracy_pct": res.accuracy_pct,
        }

    return {
        "experiment_id": "EXP-2026-002a",
        "conditions": {
            "condition_a_monolithic_dual": _stage_res_dict(report.condition_a_monolithic_dual),
            "condition_b_monolithic_interleaved": _stage_res_dict(report.condition_b_monolithic_interleaved),
            "condition_c_state_factored_dual": {
                f"stage_{stg}": _stage_res_dict(res)
                for stg, res in report.condition_c_state_factored_dual.items()
            },
            "condition_d_state_factored_interleaved": {
                f"stage_{stg}": _stage_res_dict(res)
                for stg, res in report.condition_d_state_factored_interleaved.items()
            },
            "condition_e_decoder_benchmark": _stage_res_dict(report.condition_e_decoder_benchmark),
            "condition_e_multiplexer_benchmark": _stage_res_dict(report.condition_e_multiplexer_benchmark),
        },
        "comparisons": {
            "combined_mealy_dual_gates": report.combined_mealy_dual_gates,
            "combined_mealy_dual_depth": report.combined_mealy_dual_depth,
            "combined_mealy_interleaved_gates": report.combined_mealy_interleaved_gates,
            "combined_mealy_interleaved_depth": report.combined_mealy_interleaved_depth,
            "delta_n_mealy": report.delta_n_mealy,
            "delta_d_mealy": report.delta_d_mealy,
            "operational_ply_delta_n": report.operational_ply_delta_n,
            "decoder_penalty_gates": report.condition_e_decoder_benchmark.gate_count,
            "multiplexer_recombination_gates": report.condition_e_multiplexer_benchmark.gate_count,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="EXP-2026-002a Orchestration Harness")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    parser.add_argument("--output-dir", type=Path, default=None, help="Telemetry output directory")
    parser.add_argument(
        "--stage",
        choices=["all", "partition", "emit", "synthesize", "evaluate"],
        default="all",
        help="Pipeline stage to execute",
    )
    args = parser.parse_args()

    cfg = load_config(args.config)
    out_dir = args.output_dir or cfg.output_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    print("=" * 70)
    print(f"Starting {cfg.experiment_id}: {cfg.title}")
    print(f"Output Directory: {out_dir}")
    print(f"Target Stage: {args.stage}")
    print("=" * 70)

    # 1. State Partitioning
    partition = generate_partitioned_states()
    export_partition_stats(partition, out_dir / "ply_partition_stats.json")
    print(f"[✓] State Space Partitioned: {partition.total_states} states across plies {dict(partition.ply_counts)}")

    if args.stage == "partition":
        return

    # 2. Truth Tables & PLA Emission
    solver = MinimaxSolver()
    entries_by_stage = generate_mealy_truth_tables(partition, solver)

    # Emit PLAs
    for stage, entries in entries_by_stage.items():
        ply = stage * 2
        emit_ply_pla(entries, stage, "dual", out_dir / f"truth_table_ply{ply}.pla")

    emit_multiplexer_pla(out_dir / "truth_table_multiplexer.pla")
    emit_complete_json(entries_by_stage, out_dir / "truth_table_complete_mealy.json")
    print(f"[✓] Emitted 5 Ply PLAs, Multiplexer PLA, and Complete JSON database.")

    if args.stage == "emit":
        return

    # 3. Logic Synthesis across Conditions A..E
    synth = MealySynthesizer(basis=cfg.basis_gates)
    dags, syn_report = synth.run_full_synthesis(entries_by_stage)

    syn_json_data = serialize_synthesis_report(syn_report)
    with open(out_dir / "synthesis_results_mealy.json", "w", encoding="utf-8") as f:
        json.dump(syn_json_data, f, indent=2)

    print(f"[✓] Logic Synthesis Complete:")
    print(f"    - State-Factored Dual Mealy Gates: {syn_report.combined_mealy_dual_gates} (Depth: {syn_report.combined_mealy_dual_depth})")
    print(f"    - State-Factored Interleaved Gates: {syn_report.combined_mealy_interleaved_gates} (Depth: {syn_report.combined_mealy_interleaved_depth})")
    print(f"    - Gate Count Reduction (Delta N): {syn_report.delta_n_mealy * 100:.2f}% (Target: >= 20.0%)")
    print(f"    - DAG Depth Reduction (Delta D): {syn_report.delta_d_mealy * 100:.2f}% (Target: >= 25.0%)")
    print(f"    - Operational Ply Reductions: {syn_report.operational_ply_delta_n}")
    print(f"    - Monolithic Dual 4-bit Gates: {syn_report.condition_a_monolithic_dual.gate_count} (Target: <= 45)")

    if args.stage == "synthesize":
        return

    # 4. Evaluation & Verification
    evaluator = ExperimentEvaluator()
    eval_report = evaluator.run_evaluation(
        entries_by_stage, syn_report, output_path=out_dir / "evaluator_validation.json"
    )

    t_total = time.time() - t_start

    # Raw telemetry
    raw_telem = {
        "experiment_id": cfg.experiment_id,
        "execution_wall_time_seconds": round(t_total, 4),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "eval_report": asdict(eval_report),
        "synthesis_summary": syn_json_data["comparisons"],
    }
    with open(out_dir / "raw_telemetry.json", "w", encoding="utf-8") as f:
        json.dump(raw_telem, f, indent=2)

    print("-" * 70)
    print(f"Evaluation Verdict: {eval_report.milestone_verdict}")
    print(f"Zero Defect Invariant: {'PASSED' if eval_report.zero_defect_invariant_passed else 'FAILED'}")
    print(f"Canonical Tree Paths: {eval_report.game_tree_paths} (Wins: {eval_report.oracle_wins}, Draws: {eval_report.oracle_draws}, Losses: {eval_report.oracle_losses})")
    print(f"Falsification Gates:")
    for gate_name, status in eval_report.falsification_gates.items():
        print(f"    - {gate_name}: {'PASSED' if status else 'FAILED'}")
    print(f"Total Execution Time: {t_total:.2f} seconds")
    print("=" * 70)


if __name__ == "__main__":
    main()
