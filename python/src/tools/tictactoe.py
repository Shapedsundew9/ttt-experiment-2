"""Tic-Tac-Toe Bitboard and Game-Theoretic Foundations.

Provides bitboard definitions, win condition checks, forward reachability
enumeration, minimax solver, and canonical policy generation.
"""

from typing import Dict, List, Set, Tuple

WIN_MASKS: List[int] = [
    0x007, 0x038, 0x1C0,  # Rows
    0x049, 0x092, 0x124,  # Columns
    0x111, 0x054,         # Diagonals
]

CANONICAL_TIE_BREAKER: List[int] = [4, 0, 2, 6, 8, 1, 3, 5, 7]
LEXICOGRAPHICAL_TIE_BREAKER: List[int] = [0, 1, 2, 3, 4, 5, 6, 7, 8]


def check_win(bitboard: int) -> bool:
    """Returns True if the bitboard contains any winning 3-in-a-row line."""
    return any((bitboard & mask) == mask for mask in WIN_MASKS)


def get_legal_mask(x_bb: int, o_bb: int) -> int:
    """Returns a 9-bit bitmask of unoccupied cells."""
    return (~(x_bb | o_bb)) & 0x1FF


def to_dual_bitboard(x_bb: int, o_bb: int) -> int:
    """Encodes (X, O) into an 18-bit dual bitboard: [O_8..0 | X_8..0]."""
    return ((o_bb & 0x1FF) << 9) | (x_bb & 0x1FF)


def from_dual_bitboard(w: int) -> Tuple[int, int]:
    """Decodes an 18-bit dual bitboard into (x_bb, o_bb)."""
    return w & 0x1FF, (w >> 9) & 0x1FF


def to_interleaved(x_bb: int, o_bb: int) -> int:
    """Encodes (X, O) into an 18-bit interleaved vector: b_{2i} = X_i, b_{2i+1} = O_i."""
    inter = 0
    for i in range(9):
        x_bit = (x_bb >> i) & 1
        o_bit = (o_bb >> i) & 1
        inter |= (x_bit << (2 * i)) | (o_bit << (2 * i + 1))
    return inter


def from_interleaved(val: int) -> Tuple[int, int]:
    """Decodes an 18-bit interleaved vector into (x_bb, o_bb)."""
    x_bb = 0
    o_bb = 0
    for i in range(9):
        x_bit = (val >> (2 * i)) & 1
        o_bit = (val >> (2 * i + 1)) & 1
        x_bb |= x_bit << i
        o_bb |= o_bit << i
    return x_bb, o_bb


def enumerate_all_reachable_x_states() -> List[Tuple[int, int, int]]:
    """Exhaustive forward reachability enumeration from empty board.
    
    Returns a list of tuples (x_bb, o_bb, ply) for all non-terminal reachable
    board configurations where it is X's turn to move (ply % 2 == 0).
    """
    visited: Set[Tuple[int, int]] = set()
    queue: List[Tuple[int, int, int]] = [(0, 0, 0)]
    visited.add((0, 0))

    reachable_x_states: List[Tuple[int, int, int]] = []

    while queue:
        x_bb, o_bb, ply = queue.pop(0)

        # Non-terminal check: neither player has won, and board is not completely full
        if check_win(x_bb) or check_win(o_bb):
            continue
        if (x_bb | o_bb) == 0x1FF:
            continue

        if ply % 2 == 0:
            reachable_x_states.append((x_bb, o_bb, ply))
            legal = get_legal_mask(x_bb, o_bb)
            for i in range(9):
                if (legal >> i) & 1:
                    nx = x_bb | (1 << i)
                    if (nx, o_bb) not in visited:
                        visited.add((nx, o_bb))
                        queue.append((nx, o_bb, ply + 1))
        else:
            legal = get_legal_mask(x_bb, o_bb)
            for i in range(9):
                if (legal >> i) & 1:
                    no = o_bb | (1 << i)
                    if (x_bb, no) not in visited:
                        visited.add((x_bb, no))
                        queue.append((x_bb, no, ply + 1))

    return reachable_x_states


def enumerate_uci_endgames() -> List[Tuple[int, int]]:
    """Enumerates all 958 terminal endgame states (UCI Tic-Tac-Toe dataset).
    
    A state is an endgame state if either X won, O won, or board is full (draw),
    and no moves were played after the terminal condition.
    """
    visited: Set[Tuple[int, int, int]] = set()
    endgames: Set[Tuple[int, int]] = set()
    queue: List[Tuple[int, int, int]] = [(0, 0, 0)]
    visited.add((0, 0, 0))

    while queue:
        x_bb, o_bb, turn = queue.pop(0)
        if check_win(x_bb) or check_win(o_bb) or (x_bb | o_bb) == 0x1FF:
            endgames.add((x_bb, o_bb))
            continue

        legal = get_legal_mask(x_bb, o_bb)
        for i in range(9):
            if (legal >> i) & 1:
                if turn == 0:
                    nxt = (x_bb | (1 << i), o_bb, 1)
                else:
                    nxt = (x_bb, o_bb | (1 << i), 0)
                if nxt not in visited:
                    visited.add(nxt)
                    queue.append(nxt)

    return sorted(list(endgames))


class MinimaxSolver:
    """Memoized Minimax value iteration and canonical policy provider."""

    def __init__(self) -> None:
        self._memo: Dict[Tuple[int, int, int], int] = {}

    def minimax(self, x_bb: int, o_bb: int, turn: int) -> int:
        """Returns game-theoretic value from X perspective: +1 (Win), 0 (Draw), -1 (Loss)."""
        key = (x_bb, o_bb, turn)
        if key in self._memo:
            return self._memo[key]

        if check_win(x_bb):
            return 1
        if check_win(o_bb):
            return -1
        legal = get_legal_mask(x_bb, o_bb)
        if legal == 0:
            return 0

        if turn == 0:  # X plays to maximize
            val = -2
            for i in range(9):
                if (legal >> i) & 1:
                    v = self.minimax(x_bb | (1 << i), o_bb, 1)
                    if v > val:
                        val = v
                        if val == 1:
                            break
            self._memo[key] = val
            return val
        else:  # O plays to minimize
            val = 2
            for i in range(9):
                if (legal >> i) & 1:
                    v = self.minimax(x_bb, o_bb | (1 << i), 0)
                    if v < val:
                        val = v
                        if val == -1:
                            break
            self._memo[key] = val
            return val

    def get_best_move(
        self, x_bb: int, o_bb: int, tie_breaker: List[int] = CANONICAL_TIE_BREAKER
    ) -> Tuple[int, int]:
        """Returns (best_move_cell_index, minimax_value) under the specified tie-breaker."""
        legal = get_legal_mask(x_bb, o_bb)
        best_val = -2
        best_moves: List[int] = []

        for i in range(9):
            if (legal >> i) & 1:
                v = self.minimax(x_bb | (1 << i), o_bb, 1)
                if v > best_val:
                    best_val = v
                    best_moves = [i]
                elif v == best_val:
                    best_moves.append(i)

        for cell in tie_breaker:
            if cell in best_moves:
                return cell, best_val

        return best_moves[0], best_val

    def verify_game_tree(
        self, tie_breaker: List[int] = CANONICAL_TIE_BREAKER
    ) -> Dict[str, int]:
        """Traverses the full game tree where X follows the canonical policy and O plays all legal moves."""
        stats = {"paths": 0, "wins": 0, "draws": 0, "losses": 0}

        def dfs(x_bb: int, o_bb: int, turn: int) -> None:
            if check_win(x_bb):
                stats["wins"] += 1
                stats["paths"] += 1
                return
            if check_win(o_bb):
                stats["losses"] += 1
                stats["paths"] += 1
                return
            legal = get_legal_mask(x_bb, o_bb)
            if legal == 0:
                stats["draws"] += 1
                stats["paths"] += 1
                return

            if turn == 0:
                best_cell, _ = self.get_best_move(x_bb, o_bb, tie_breaker)
                dfs(x_bb | (1 << best_cell), o_bb, 1)
            else:
                for i in range(9):
                    if (legal >> i) & 1:
                        dfs(x_bb, o_bb | (1 << i), 0)

        dfs(0, 0, 0)
        return stats
