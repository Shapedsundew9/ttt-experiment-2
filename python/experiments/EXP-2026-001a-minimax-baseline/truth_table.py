"""Truth table emission and PLA formatting for logic synthesis."""

import json
from pathlib import Path
from typing import Dict, List, Tuple

from python.experiments.exp_2026_001a_minimax_baseline.minimax import OracleDecision
from python.experiments.exp_2026_001a_minimax_baseline.state_space import BoardStateRecord
from tools.tictactoe import CANONICAL_TIE_BREAKER


def to_binary_string(val: int, width: int) -> str:
    """Formats an integer into a binary string with MSB at index 0."""
    return "".join("1" if (val >> (width - 1 - i)) & 1 else "0" for i in range(width))


def generate_pla_content(
    records: List[BoardStateRecord],
    decisions: List[OracleDecision],
    use_dual_bitboard: bool = True,
) -> str:
    """Generates standard Berkeley PLA format content.
    
    Inputs: 18 bits (either Dual Bitboard [O | X] or Interleaved [b_17..b_0])
    Outputs: 9 bits (one-hot move M_0..M_8)
    Don't-cares: Specified by .type fd where unspecified inputs default to don't-care.
    """
    lines = []
    lines.append(".i 18")
    lines.append(".o 9")

    if use_dual_bitboard:
        in_labels = [f"x_{i}" for i in range(9)] + [f"o_{i}" for i in range(9)]
    else:
        in_labels = [f"b_{i}" for i in range(18)]
    out_labels = [f"m_{i}" for i in range(9)]

    lines.append(f".ilb {' '.join(in_labels)}")
    lines.append(f".ob {' '.join(out_labels)}")
    lines.append(f".p {len(records)}")
    lines.append(".type fd")

    for rec, dec in zip(records, decisions):
        if use_dual_bitboard:
            # Inputs: x_0..x_8, o_0..o_8
            in_val = rec.dual_bitboard_int
        else:
            in_val = rec.interleaved_int

        in_str = to_binary_string(in_val, 18)
        # Outputs: m_0..m_8
        out_str = "".join("1" if (dec.best_move_cell == i) else "0" for i in range(9))
        lines.append(f"{in_str} {out_str}")

    lines.append(".e")
    return "\n".join(lines) + "\n"


def export_truth_tables(
    records: List[BoardStateRecord],
    decisions: List[OracleDecision],
    output_dir: Path,
    tie_breaking_order: List[int] = CANONICAL_TIE_BREAKER,
) -> Dict[str, Path]:
    """Exports PLA and JSON truth table artifacts to the designated directory."""
    output_dir.mkdir(parents=True, exist_ok=True)
    paths: Dict[str, Path] = {}

    # 1. Dual Bitboard PLA
    dual_pla_path = output_dir / "truth_table_dual.pla"
    dual_pla_content = generate_pla_content(records, decisions, use_dual_bitboard=True)
    with open(dual_pla_path, "w") as f:
        f.write(dual_pla_content)
    paths["dual_pla"] = dual_pla_path

    # 2. Interleaved PLA
    inter_pla_path = output_dir / "truth_table_interleaved.pla"
    inter_pla_content = generate_pla_content(records, decisions, use_dual_bitboard=False)
    with open(inter_pla_path, "w") as f:
        f.write(inter_pla_content)
    paths["interleaved_pla"] = inter_pla_path

    # 3. Complete JSON truth table
    complete_json_path = output_dir / "truth_table_complete.json"
    json_records = []
    for rec, dec in zip(records, decisions):
        json_records.append(
            {
                "state_id": rec.state_id,
                "ply": rec.ply,
                "interleaved_int": rec.interleaved_int,
                "interleaved_bin": to_binary_string(rec.interleaved_int, 18),
                "dual_int": rec.dual_bitboard_int,
                "dual_bin": to_binary_string(rec.dual_bitboard_int, 18),
                "best_move_cell": dec.best_move_cell,
                "best_move_onehot": dec.best_move_onehot,
                "minimax_value": dec.minimax_value,
            }
        )

    json_payload = {
        "metadata": {
            "total_reachable_states": len(records),
            "total_dont_care_states": (1 << 18) - len(records),
            "input_bits": 18,
            "output_bits": 9,
            "tie_breaking_order": tie_breaking_order,
        },
        "records": json_records,
    }
    with open(complete_json_path, "w") as f:
        json.dump(json_payload, f, indent=2)
    paths["complete_json"] = complete_json_path

    return paths
