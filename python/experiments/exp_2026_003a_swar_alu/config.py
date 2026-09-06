"""Configuration dataclasses and loaders for EXP-2026-003a."""

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import List, Optional


@dataclass(frozen=True)
class Experiment003aConfig:
    experiment_id: str = "EXP-2026-003a"
    title: str = "SWAR Bitboard and 64-Bit ALU Arithmetic Synthesis"
    alu_basis: List[str] = field(default_factory=lambda: [
        "AND", "OR", "XOR", "ANDN", "SHL", "SHR", "NOT"
    ])
    tie_breaking_order: List[int] = field(default_factory=lambda: [4, 0, 2, 6, 8, 1, 3, 5, 7])
    expected_ply_distribution: List[int] = field(default_factory=lambda: [1, 72, 756, 1372, 222])
    total_states_expected: int = 2423
    dont_care_states_expected: int = 259721
    max_total_instructions: int = 25
    max_stage_instructions: List[int] = field(default_factory=lambda: [0, 6, 8, 8, 6])
    max_single_stage_ceiling: int = 8
    max_win_kernel_instructions: int = 4
    max_threat_kernel_instructions: int = 6
    expected_mux_overhead: int = 0
    max_dynamic_step_instructions: int = 10
    timeout_per_stage_seconds: float = 300.0
    timeout_total_seconds: float = 7200.0
    output_dir: Path = Path("data/telemetry/EXP-2026-003a")


def load_config(config_path: Optional[Path] = None) -> Experiment003aConfig:
    """Loads configuration from config.toml if provided, or returns defaults."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.toml"

    if not config_path.exists():
        return Experiment003aConfig()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    exp = data.get("experiment", {})
    tb = data.get("tie_breaking", {})
    ss = data.get("state_space", {})
    sub = data.get("substrate", {})
    bud = data.get("complexity_budgets", {})
    to = data.get("timeouts", {})
    out = data.get("output", {})

    return Experiment003aConfig(
        experiment_id=exp.get("id", "EXP-2026-003a"),
        title=exp.get("title", "SWAR Bitboard and 64-Bit ALU Arithmetic Synthesis"),
        alu_basis=sub.get("isa_basis", ["AND", "OR", "XOR", "ANDN", "SHL", "SHR", "NOT"]),
        tie_breaking_order=tb.get("canonical_order", [4, 0, 2, 6, 8, 1, 3, 5, 7]),
        expected_ply_distribution=ss.get("expected_ply_counts", [1, 72, 756, 1372, 222]),
        total_states_expected=ss.get("expected_total_states", 2423),
        dont_care_states_expected=ss.get("expected_dont_cares", 259721),
        max_total_instructions=bud.get("max_total_instructions", 25),
        max_stage_instructions=bud.get("max_stage_instructions", [0, 6, 8, 8, 6]),
        max_single_stage_ceiling=bud.get("max_single_stage_ceiling", 8),
        max_win_kernel_instructions=bud.get("max_win_kernel_instructions", 4),
        max_threat_kernel_instructions=bud.get("max_threat_kernel_instructions", 6),
        expected_mux_overhead=bud.get("expected_mux_overhead", 0),
        max_dynamic_step_instructions=bud.get("max_dynamic_step_instructions", 10),
        timeout_per_stage_seconds=float(to.get("timeout_per_stage_seconds", 300.0)),
        timeout_total_seconds=float(to.get("timeout_total_seconds", 7200.0)),
        output_dir=Path(out.get("telemetry_dir", "data/telemetry/EXP-2026-003a")),
    )
