"""Tools package for experimental Tic-Tac-Toe Mealy Machine research."""

from tools.boolean_dag import BooleanDAG, GateNode, GateOp, build_interleaved_decoder_dag
from tools.tictactoe import (
    CANONICAL_TIE_BREAKER,
    LEXICOGRAPHICAL_TIE_BREAKER,
    WIN_MASKS,
    MinimaxSolver,
    check_win,
    enumerate_all_reachable_x_states,
    enumerate_uci_endgames,
    from_dual_bitboard,
    from_interleaved,
    get_legal_mask,
    to_dual_bitboard,
    to_interleaved,
)

__all__ = [
    "BooleanDAG",
    "GateNode",
    "GateOp",
    "build_interleaved_decoder_dag",
    "CANONICAL_TIE_BREAKER",
    "LEXICOGRAPHICAL_TIE_BREAKER",
    "WIN_MASKS",
    "MinimaxSolver",
    "check_win",
    "enumerate_all_reachable_x_states",
    "enumerate_uci_endgames",
    "from_dual_bitboard",
    "from_interleaved",
    "get_legal_mask",
    "to_dual_bitboard",
    "to_interleaved",
]
