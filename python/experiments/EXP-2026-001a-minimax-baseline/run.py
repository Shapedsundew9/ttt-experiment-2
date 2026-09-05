"""Execution runner and CLI entry point for EXP-2026-001a."""

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
import time

from python.experiments.exp_2026_001a_minimax_baseline.config import ExperimentConfig
from python.experiments.exp_2026_001a_minimax_baseline.evaluator import evaluate_synthesis_comparison
from python.experiments.exp_2026_001a_minimax_baseline.minimax import (
    compute_oracle_decisions,
    verify_oracle_game_tree,
)
from python.experiments.exp_2026_001a_minimax_baseline.state_space import generate_state_records
from python.experiments.exp_2026_001a_minimax_baseline.synthesis import LogicSynthesizer
from python.experiments.exp_2026_001a_minimax_baseline.truth_table import export_truth_tables


def run_experiment(config: ExperimentConfig, stage: str = "all") -> None:
    """Executes the complete experimental pipeline for EXP-2026-001a."""
    t0 = time.time()
    output_dir = config.telemetry_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    print(f"=== Running EXP-2026-001a Pipeline (Stage: {stage}) ===")
    print(f"Output directory: {output_dir}")

    # Stage 1: State Space Enumeration
    print("\n--- [1/4] Enumerating Reachable State Space ---")
    records, ply_counts, uci_metrics = generate_state_records()
    total_states = len(records)
    print(f"Reachable non-terminal X-turn states: {total_states}")
    print(f"Ply distribution: {ply_counts}")
    print(f"UCI Endgame dataset count: {uci_metrics['total_uci_endgames']}")

    states_payload = {
        "total_reachable_x_states": total_states,
        "ply_distribution": ply_counts,
        "uci_endgame_benchmark": uci_metrics,
        "states": [
            {
                "state_id": r.state_id,
                "ply": r.ply,
                "x_bitboard": r.x_bitboard,
                "o_bitboard": r.o_bitboard,
                "board_string": r.board_string,
                "legal_moves_mask": r.legal_moves_mask,
                "dual_bitboard_int": r.dual_bitboard_int,
                "interleaved_int": r.interleaved_int,
            }
            for r in records
        ],
    }
    with open(output_dir / "states_958.json", "w") as f:
        json.dump(states_payload, f, indent=2)

    if stage == "enumerate":
        return

    # Stage 2: Canonical Minimax Oracle & Tree Verification
    print("\n--- [2/4] Minimax Value Iteration & Game Tree Verification ---")
    raw_board_pairs = [(r.x_bitboard, r.o_bitboard) for r in records]
    decisions = compute_oracle_decisions(raw_board_pairs, config.canonical_order)
    tree_stats = verify_oracle_game_tree(config.canonical_order)
    print(f"Exhaustive game tree paths traversed: {tree_stats['total_terminal_paths']}")
    print(f"Wins: {tree_stats['wins']} | Draws: {tree_stats['draws']} | Losses: {tree_stats['losses']}")
    print(f"Oracle zero-defect invariant: {tree_stats['oracle_zero_defect_invariant']}")

    with open(output_dir / "tree_validation.json", "w") as f:
        json.dump(tree_stats, f, indent=2)

    if stage == "oracle":
        return

    # Stage 3: Truth Table & Don't-Care Dataset Emission
    print("\n--- [3/4] Emitting Truth Tables (.pla & JSON) ---")
    exported_paths = export_truth_tables(
        records, decisions, output_dir, config.canonical_order
    )
    for k, p in exported_paths.items():
        print(f"Emitted {k}: {p}")

    if stage == "emit":
        return

    # Stage 4: Logic Synthesis & Complexity Evaluation
    print("\n--- [4/4] Synthesizing Boolean Logic DAGs ---")
    synthesizer = LogicSynthesizer(basis=config.basis)

    # Condition E: Decoder Benchmark
    res_decoder = synthesizer.synthesize_decoder_benchmark()
    print(f"Condition E (Decoder Benchmark): {res_decoder.gate_count} gates, depth {res_decoder.dag_depth}")

    # Condition B: Dual Bitboard
    dag_dual, res_dual = synthesizer.synthesize_dual_bitboard_dag(records, decisions)
    print(f"Condition B (Dual Bitboard): {res_dual.gate_count} gates, depth {res_dual.dag_depth}")

    # Condition A: Interleaved
    dag_inter, res_inter = synthesizer.synthesize_interleaved_dag(records, decisions)
    print(f"Condition A (Interleaved): {res_inter.gate_count} gates, depth {res_inter.dag_depth}")

    # Condition C: Ablation (Zero Don't-Cares)
    res_nodc = synthesizer.synthesize_ablation_nodc(records, decisions)
    print(f"Condition C (Ablation No-DC): {res_nodc.gate_count} gates, depth {res_nodc.dag_depth}")

    # Comparative evaluation
    comparison = evaluate_synthesis_comparison(
        res_inter=res_inter,
        res_dual=res_dual,
        res_nodc=res_nodc,
        res_decoder=res_decoder,
    )
    comp_metrics = comparison["comparison"]
    print(f"\nComparative Results:")
    print(f"Gate count: Interleaved = {comp_metrics['n_interleaved']} vs Dual = {comp_metrics['n_dual_bitboard']}")
    print(f"Decoder penalty: {comp_metrics['decoder_penalty_gates']} gates")
    print(f"Gate count reduction: {comp_metrics['gate_count_reduction_pct']}% (Target >= 20.0%) -> Passed: {comp_metrics['gate_reduction_passed']}")
    print(f"DAG depth reduction: {comp_metrics['dag_depth_reduction_pct']}% (Target >= 25.0%) -> Passed: {comp_metrics['depth_reduction_passed']}")

    with open(output_dir / "synthesis_results.json", "w") as f:
        json.dump(comparison, f, indent=2)

    # Raw telemetry execution log
    total_elapsed = time.time() - t0
    raw_telemetry = {
        "experiment_id": config.id,
        "status": "COMPLETED",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "duration_seconds": round(total_elapsed, 4),
        "total_reachable_x_states": total_states,
        "uci_endgames_verified": uci_metrics["total_uci_endgames"],
        "game_tree_paths": tree_stats["total_terminal_paths"],
        "oracle_losses": tree_stats["losses"],
        "comparison_metrics": comp_metrics,
    }
    with open(output_dir / "raw_telemetry.json", "w") as f:
        json.dump(raw_telemetry, f, indent=2)

    print(f"\n=== Experiment EXP-2026-001a Completed in {total_elapsed:.2f}s ===")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run EXP-2026-001a Experiment Pipeline")
    parser.add_argument("--config", type=str, default="python/experiments/EXP-2026-001a-minimax-baseline/config.toml")
    parser.add_argument("--output-dir", type=str, default="data/telemetry/EXP-2026-001a")
    parser.add_argument("--stage", type=str, default="all", choices=["all", "enumerate", "oracle", "emit", "synthesize"])
    args = parser.parse_args()

    cfg_path = Path(args.config)
    config = ExperimentConfig.load(cfg_path)
    if args.output_dir:
        config.telemetry_dir = Path(args.output_dir)

    run_experiment(config, stage=args.stage)


if __name__ == "__main__":
    main()
