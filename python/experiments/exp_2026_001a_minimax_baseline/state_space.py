"""State space enumeration and reachability analysis for EXP-2026-001a."""

from dataclasses import asdict, dataclass
from typing import Dict, List, Tuple

from tools.tictactoe import (
    check_win,
    enumerate_all_reachable_x_states,
    enumerate_uci_endgames,
    from_dual_bitboard,
    from_interleaved,
    get_legal_mask,
    to_dual_bitboard,
    to_interleaved,
)


@dataclass
class BoardStateRecord:
    state_id: int
    ply: int
    x_bitboard: int
    o_bitboard: int
    board_string: str
    legal_moves_mask: int
    dual_bitboard_int: int
    interleaved_int: int


def format_board_string(x_bb: int, o_bb: int) -> str:
    """Returns a 9-character string representing row-major grid."""
    chars = []
    for i in range(9):
        if (x_bb >> i) & 1:
            chars.append("X")
        elif (o_bb >> i) & 1:
            chars.append("O")
        else:
            chars.append(".")
    return "".join(chars)


def generate_state_records() -> Tuple[List[BoardStateRecord], Dict[str, int], Dict[str, int]]:
    """Generates exhaustive state records for all reachable non-terminal X-turn states,
    along with ply distribution metrics and UCI endgame comparison metrics.
    """
    raw_states = enumerate_all_reachable_x_states()
    records: List[BoardStateRecord] = []
    ply_counts: Dict[str, int] = {}

    for idx, (x_bb, o_bb, ply) in enumerate(raw_states):
        key = f"ply_{ply}"
        ply_counts[key] = ply_counts.get(key, 0) + 1
        rec = BoardStateRecord(
            state_id=idx,
            ply=ply,
            x_bitboard=x_bb,
            o_bitboard=o_bb,
            board_string=format_board_string(x_bb, o_bb),
            legal_moves_mask=get_legal_mask(x_bb, o_bb),
            dual_bitboard_int=to_dual_bitboard(x_bb, o_bb),
            interleaved_int=to_interleaved(x_bb, o_bb),
        )
        records.append(rec)

    # Also compute UCI endgame distribution
    uci_endgames = enumerate_uci_endgames()
    uci_ply_counts: Dict[str, int] = {}
    for x_bb, o_bb in uci_endgames:
        moves = bin(x_bb | o_bb).count("1")
        k = f"ply_{moves}"
        uci_ply_counts[k] = uci_ply_counts.get(k, 0) + 1

    uci_metrics = {
        "total_uci_endgames": len(uci_endgames),
        **uci_ply_counts,
    }

    return records, ply_counts, uci_metrics
