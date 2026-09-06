"""Forward reachability state space generation and discrete ply partitioning for EXP-2026-002a."""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Dict, List, Set, Tuple

from tools.tictactoe import (
    check_win,
    get_legal_mask,
    to_dual_bitboard,
    to_interleaved,
)


@dataclass(frozen=True)
class PlyStateRecord:
    state_id: int
    x_bitboard: int
    o_bitboard: int
    ply: int                  # Physical ply: 0, 2, 4, 6, 8
    stage: int                # Discrete stage: 0, 1, 2, 3, 4
    dual_bitboard: int        # (O << 9) | X
    interleaved: int          # sum(x_i 2^{2i} + o_i 2^{2i+1})
    legal_mask: int           # ~(X | O) & 0x1FF


@dataclass
class PlyPartitionResult:
    total_states: int
    stage_partitions: Dict[int, List[PlyStateRecord]]  # stage -> list of records
    ply_counts: Dict[int, int]                         # ply -> count


def generate_partitioned_states() -> PlyPartitionResult:
    """Performs forward BFS reachability from root state (0, 0) and partitions non-terminal X-decision states."""
    visited: Set[Tuple[int, int]] = set()
    queue: List[Tuple[int, int, int]] = [(0, 0, 0)]
    visited.add((0, 0))

    raw_x_states: List[Tuple[int, int, int]] = []

    while queue:
        x_bb, o_bb, ply = queue.pop(0)

        # Invariant 1: Mutual Spatial Exclusivity
        assert (x_bb & o_bb) == 0, f"Invariant 1 violated: cell overlap in state X={bin(x_bb)}, O={bin(o_bb)}"

        # Invariant 3: Non-Terminal Precondition
        if check_win(x_bb) or check_win(o_bb):
            continue
        if (x_bb | o_bb) == 0x1FF:
            continue

        if ply % 2 == 0:
            stage = ply // 2
            # Invariant 2: Turn Parity & Popcount Conservation
            x_pop = bin(x_bb).count("1")
            o_pop = bin(o_bb).count("1")
            assert x_pop == o_pop == stage, (
                f"Invariant 2 violated: popcounts (X={x_pop}, O={o_pop}) do not match stage {stage}"
            )
            raw_x_states.append((x_bb, o_bb, ply))

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

    # Invariant 4: Forward Reachability Closure
    assert len(raw_x_states) == 2423, f"Invariant 4 violated: expected 2,423 states, got {len(raw_x_states)}"

    # Sort deterministically: by ply, then x_bb, then o_bb
    raw_x_states.sort(key=lambda s: (s[2], s[0], s[1]))

    stage_partitions: Dict[int, List[PlyStateRecord]] = {0: [], 1: [], 2: [], 3: [], 4: []}
    ply_counts: Dict[int, int] = {0: 0, 2: 0, 4: 0, 6: 0, 8: 0}

    for state_id, (x_bb, o_bb, ply) in enumerate(raw_x_states):
        stage = ply // 2
        record = PlyStateRecord(
            state_id=state_id,
            x_bitboard=x_bb,
            o_bitboard=o_bb,
            ply=ply,
            stage=stage,
            dual_bitboard=to_dual_bitboard(x_bb, o_bb),
            interleaved=to_interleaved(x_bb, o_bb),
            legal_mask=get_legal_mask(x_bb, o_bb),
        )
        stage_partitions[stage].append(record)
        ply_counts[ply] += 1

    expected_counts = {0: 1, 2: 72, 4: 756, 6: 1372, 8: 222}
    assert ply_counts == expected_counts, (
        f"Ply count mismatch: expected {expected_counts}, got {ply_counts}"
    )

    return PlyPartitionResult(
        total_states=len(raw_x_states),
        stage_partitions=stage_partitions,
        ply_counts=ply_counts,
    )


def export_partition_stats(result: PlyPartitionResult, output_path: Path) -> None:
    """Serializes ply partition statistics to ply_partition_stats.json."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    stats = {
        "total_reachable_non_terminal_x_states": result.total_states,
        "dont_care_states_count": 262144 - result.total_states,
        "dont_care_percentage": round((262144 - result.total_states) / 262144 * 100, 5),
        "ply_distribution": {
            f"ply_{ply}_stage_{ply // 2}": count
            for ply, count in sorted(result.ply_counts.items())
        },
        "invariants_verified": {
            "mutual_spatial_exclusivity": True,
            "turn_parity_popcount": True,
            "non_terminal_precondition": True,
            "forward_reachability_closure": True,
        },
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
