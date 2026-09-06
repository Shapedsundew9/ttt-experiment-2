"""Evaluation and comparative metric computation for EXP-2026-001a."""

from dataclasses import asdict
from typing import Any, Dict

from python.experiments.exp_2026_001a_minimax_baseline.synthesis import SynthesisResult


def evaluate_synthesis_comparison(
    res_inter: SynthesisResult,
    res_dual: SynthesisResult,
    res_nodc: SynthesisResult,
    res_decoder: SynthesisResult,
) -> Dict[str, Any]:
    """Computes gate count reduction, DAG depth reduction, and asserts pass/fail gates."""
    n_inter = res_inter.gate_count
    n_dual = res_dual.gate_count
    d_inter = res_inter.dag_depth
    d_dual = res_dual.dag_depth

    delta_n = (n_inter - n_dual) / n_inter if n_inter > 0 else 0.0
    delta_d = (d_inter - d_dual) / d_inter if d_inter > 0 else 0.0

    threshold_gate_reduction = 0.20
    threshold_depth_reduction = 0.25

    gate_passed = delta_n >= threshold_gate_reduction
    depth_passed = delta_d >= threshold_depth_reduction

    return {
        "condition_a_interleaved": asdict(res_inter),
        "condition_b_dual_bitboard": asdict(res_dual),
        "condition_c_ablation_nodc": asdict(res_nodc),
        "condition_e_decoder_benchmark": asdict(res_decoder),
        "comparison": {
            "n_interleaved": n_inter,
            "n_dual_bitboard": n_dual,
            "decoder_penalty_gates": n_inter - n_dual,
            "gate_count_reduction_delta_n": round(delta_n, 4),
            "gate_count_reduction_pct": round(delta_n * 100, 2),
            "d_interleaved": d_inter,
            "d_dual_bitboard": d_dual,
            "dag_depth_reduction_delta_d": round(delta_d, 4),
            "dag_depth_reduction_pct": round(delta_d * 100, 2),
            "threshold_gate_reduction": threshold_gate_reduction,
            "threshold_depth_reduction": threshold_depth_reduction,
            "gate_reduction_passed": gate_passed,
            "depth_reduction_passed": depth_passed,
            "overall_synthesis_passed": gate_passed and depth_passed,
        },
    }
