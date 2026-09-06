"""Truth table generator and PLA file emitter with 4-bit binary move encoding for EXP-2026-002a."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Dict, List, Tuple

from python.experiments.exp_2026_002a_ply_mealy.ply_partition import (
    PlyPartitionResult,
    PlyStateRecord,
)
from tools.tictactoe import CANONICAL_TIE_BREAKER, MinimaxSolver


@dataclass(frozen=True)
class MealyTruthTableEntry:
    state_id: int
    stage: int
    ply: int
    dual_bitboard: int
    interleaved: int
    canonical_move: int        # Cell index 0..8
    move_4bit_binary: str      # E.g. "0100" for cell 4
    move_4bit_int: int         # E.g. 4 for cell 4
    minimax_value: int         # +1 (Win), 0 (Draw), -1 (Loss)


def to_4bit_binary(cell: int) -> str:
    """Formats cell index 0..8 as 4-bit zero-padded binary string (m3 m2 m1 m0)."""
    if not (0 <= cell <= 8):
        raise ValueError(f"Cell index {cell} out of valid range 0..8")
    return f"{cell:04b}"


def generate_mealy_truth_tables(
    partition: PlyPartitionResult, solver: MinimaxSolver
) -> Dict[int, List[MealyTruthTableEntry]]:
    """Computes canonical minimax moves and 4-bit binary encoding across all partitioned states."""
    results_by_stage: Dict[int, List[MealyTruthTableEntry]] = {0: [], 1: [], 2: [], 3: [], 4: []}

    for stage, records in partition.stage_partitions.items():
        for rec in records:
            best_move, val = solver.get_best_move(
                rec.x_bitboard, rec.o_bitboard, tie_breaker=CANONICAL_TIE_BREAKER
            )

            # Invariant 5: Move legality assertion
            assert ((1 << best_move) & (rec.x_bitboard | rec.o_bitboard)) == 0, (
                f"Invariant 5 violation: chosen move {best_move} occupied in state X={bin(rec.x_bitboard)}, O={bin(rec.o_bitboard)}"
            )

            entry = MealyTruthTableEntry(
                state_id=rec.state_id,
                stage=rec.stage,
                ply=rec.ply,
                dual_bitboard=rec.dual_bitboard,
                interleaved=rec.interleaved,
                canonical_move=best_move,
                move_4bit_binary=to_4bit_binary(best_move),
                move_4bit_int=best_move,
                minimax_value=val,
            )
            results_by_stage[stage].append(entry)

    return results_by_stage


def emit_ply_pla(
    entries: List[MealyTruthTableEntry],
    stage: int,
    representation: str,
    output_path: Path,
) -> None:
    """Emits Berkeley ABC standard .pla format for a single ply sub-circuit with 4-bit output."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Berkeley PLA Truth Table for EXP-2026-002a Stage {stage} ({representation})",
        f"# On-set patterns: {len(entries)}, Dont-cares: {262144 - len(entries)}",
        ".i 18",
        ".o 4",
        ".type fd",  # First listed are care, unlisted default to DC
    ]

    if representation == "dual":
        input_names = [f"x{i}" for i in range(9)] + [f"o{i}" for i in range(9)]
    else:
        input_names = [f"b{i}" for i in range(18)]

    output_names = ["m3", "m2", "m1", "m0"]
    lines.append(".ilb " + " ".join(input_names))
    lines.append(".ob " + " ".join(output_names))
    lines.append(f".p {len(entries)}")

    for entry in entries:
        raw_val = entry.dual_bitboard if representation == "dual" else entry.interleaved
        in_bits = "".join("1" if (raw_val & (1 << i)) else "0" for i in range(18))
        out_bits = entry.move_4bit_binary
        lines.append(f"{in_bits} {out_bits}")

    lines.append(".e")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def emit_multiplexer_pla(output_path: Path) -> None:
    """Emits Berkeley ABC standard .pla format for 3-to-5 stage decoder + 4-bit multiplexer."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Berkeley PLA Truth Table for EXP-2026-002a Stage Multiplexer",
        "# Inputs: s2 s1 s0 d3 d2 d1 d0 (7 inputs), Outputs: m3 m2 m1 m0 (4 outputs)",
        ".i 7",
        ".o 4",
        ".type fd",
        ".ilb s2 s1 s0 d3 d2 d1 d0",
        ".ob m3 m2 m1 m0",
    ]

    entries = []
    for s in range(5):
        s_bits = f"{s:03b}"
        for d in range(16):
            d_bits = f"{d:04b}"
            entries.append(f"{s_bits}{d_bits} {d_bits}")

    lines.append(f".p {len(entries)}")
    lines.extend(entries)
    lines.append(".e")
    lines.append("")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def emit_complete_json(
    entries_by_stage: Dict[int, List[MealyTruthTableEntry]], output_path: Path
) -> None:
    """Serializes unified truth table database to truth_table_complete_mealy.json."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    total_states = sum(len(el) for el in entries_by_stage.values())

    data = {
        "schema": "EXP-2026-002a-truth-table-v1",
        "experiment_id": "EXP-2026-002a",
        "total_states": total_states,
        "dont_care_states": 262144 - total_states,
        "encoding": "dense_4bit_binary",
        "output_terminals": 4,
        "stages": {
            f"stage_{stage}": [asdict(entry) for entry in entries]
            for stage, entries in sorted(entries_by_stage.items())
        },
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
