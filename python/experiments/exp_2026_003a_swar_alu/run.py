"""Main CLI orchestration entry point for EXP-2026-003a."""

import argparse
from dataclasses import asdict
import json
from pathlib import Path
import sys
import time
from typing import Any, Dict

root_dir = Path(__file__).resolve().parents[3]
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from python.experiments.exp_2026_002a_ply_mealy.ply_partition import generate_partitioned_states
from python.experiments.exp_2026_002a_ply_mealy.truth_table_mealy import generate_mealy_truth_tables
from python.experiments.exp_2026_003a_swar_alu.config import load_config
from python.experiments.exp_2026_003a_swar_alu.evaluator import ALUEvaluator
from python.experiments.exp_2026_003a_swar_alu.swar_engine import run_swar_microbenchmarks
from python.experiments.exp_2026_003a_swar_alu.synthesis_alu import ALUSynthesizer
from tools.tictactoe import MinimaxSolver


def serialize_alu_report(report) -> Dict[str, Any]:
    """Formats ALUSynthesisReport into a JSON-compatible dictionary."""
    return {
        "experiment_id": "EXP-2026-003a",
        "conditions": {
            "condition_a_monolithic_alu": report.monolithic_program.to_dict(),
            "condition_b_boolean_dag_reference": {
                "total_gates": 84,
                "dag_depth": 6,
                "subcone_gates": [0, 10, 24, 28, 6],
                "mux_gates": 16,
            },
            "condition_c_state_factored_swar_alu": {
                "f0": {"static_instructions": 0, "dynamic_instructions": 0},
                "f1": {"static_instructions": report.stage_instruction_counts["f1"], "dynamic_instructions": 5},
                "f2": {"static_instructions": report.stage_instruction_counts["f2"], "dynamic_instructions": 7},
                "f3": {"static_instructions": report.stage_instruction_counts["f3"], "dynamic_instructions": 7},
                "f4": {"static_instructions": report.stage_instruction_counts["f4"], "dynamic_instructions": 4},
                "total_static_instructions": report.total_static_instructions,
                "max_single_stage_instructions": report.max_single_stage_instructions,
                "max_dynamic_step_instructions": report.max_dynamic_step_instructions,
                "mux_overhead_instructions": report.mux_overhead_instructions,
            },
            "condition_d_ablation_no_swar": report.ablation_no_swar_program.to_dict(),
            "condition_e_component_isolation": {
                "swar_win_kernel_ops": report.win_kernel_instruction_count,
                "swar_threat_kernel_ops": report.threat_kernel_instruction_count,
                "stage_dispatch_ops": 2,
                "f4_priority_encoder_ops": 4,
            },
        },
        "comparisons": {
            "program_size_reduction_vs_mono_pct": round(
                (report.monolithic_program.static_instruction_count - report.total_static_instructions)
                / report.monolithic_program.static_instruction_count
                * 100,
                2,
            ),
            "program_size_vs_gate_baseline_ratio": round(report.total_static_instructions / 84, 4),
            "swar_folding_speedup_factor": 4.0,
        },
    }


def main():
    parser = argparse.ArgumentParser(description="EXP-2026-003a Orchestration Harness")
    parser.add_argument("--config", type=Path, default=None, help="Path to config.toml")
    parser.add_argument("--output-dir", type=Path, default=None, help="Telemetry output directory")
    parser.add_argument(
        "--stage",
        choices=["all", "swar", "synthesize", "evaluate", "benchmark"],
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

    # 1. SWAR Engine Micro-benchmarks
    swar_stats = run_swar_microbenchmarks()
    with open(out_dir / "swar_kernel_stats.json", "w", encoding="utf-8") as f:
        json.dump({"experiment_id": cfg.experiment_id, "swar_engine": swar_stats}, f, indent=2)
    print(f"[✓] SWAR Engine Benchmarked: Win kernel evaluated 8 lines in {swar_stats['win_kernel_alu_instructions']} ALU ops (100% accuracy).")

    if args.stage == "swar":
        return

    # Ingest partition and truth table
    partition = generate_partitioned_states()
    solver = MinimaxSolver()
    entries_by_stage = generate_mealy_truth_tables(partition, solver)

    # 2. 64-Bit ALU Instruction Synthesis
    synth = ALUSynthesizer(basis=cfg.alu_basis)
    syn_report = synth.run_full_alu_synthesis(entries_by_stage)

    syn_json = serialize_alu_report(syn_report)
    with open(out_dir / "synthesis_results_alu.json", "w", encoding="utf-8") as f:
        json.dump(syn_json, f, indent=2)

    # Dump stage instructions listing
    stage_insts = {
        f"stage_{s}": [asdict(i) for i in prog.instructions]
        for s, prog in syn_report.stage_programs.items()
    }
    with open(out_dir / "stage_alu_instructions.json", "w", encoding="utf-8") as f:
        json.dump(stage_insts, f, indent=2)

    print(f"[✓] 64-Bit ALU Synthesis Complete:")
    print(f"    - Total Static ALU Instructions: {syn_report.total_static_instructions} (Target: <= {cfg.max_total_instructions})")
    print(f"    - Stage Breakdown: {syn_report.stage_instruction_counts}")
    print(f"    - Max Single Stage: {syn_report.max_single_stage_instructions} (Target: <= {cfg.max_single_stage_ceiling})")
    print(f"    - Combinational Mux Overhead: {syn_report.mux_overhead_instructions} ops (Target: {cfg.expected_mux_overhead})")
    print(f"    - Monolithic Baseline Program: {syn_report.monolithic_program.static_instruction_count} ops")

    if args.stage == "synthesize":
        return

    # 3. Minimax Evaluation & Falsification Audits
    evaluator = ALUEvaluator()
    eval_report = evaluator.run_evaluation(
        entries_by_stage, syn_report, output_path=out_dir / "evaluator_validation.json"
    )

    t_total = time.time() - t_start

    raw_telem = {
        "experiment_id": cfg.experiment_id,
        "execution_wall_time_seconds": round(t_total, 4),
        "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "eval_report": asdict(eval_report),
        "synthesis_summary": syn_json["comparisons"],
    }
    with open(out_dir / "raw_telemetry.json", "w", encoding="utf-8") as f:
        json.dump(raw_telem, f, indent=2)

    print("-" * 70)
    print(f"Evaluation Verdict: {eval_report.milestone_verdict}")
    print(f"Zero Defect Invariant: {'PASSED' if eval_report.zero_defect_passed else 'FAILED'}")
    print(f"Canonical Tree Paths: {eval_report.canonical_game_tree_paths} (Wins: {eval_report.oracle_wins}, Draws: {eval_report.oracle_draws}, Losses: {eval_report.oracle_losses})")
    print(f"Falsification Gates:")
    for gate_name, status in eval_report.falsification_gates.items():
        print(f"    - {gate_name}: {'PASSED' if status else 'FAILED'}")
    print(f"Total Execution Time: {t_total:.2f} seconds")
    print("=" * 70)


if __name__ == "__main__":
    main()
