"""Configuration dataclasses and loaders for EXP-2026-002a."""

from dataclasses import dataclass, field
from pathlib import Path
import tomllib
from typing import List, Optional


@dataclass(frozen=True)
class ExperimentConfig:
    experiment_id: str = "EXP-2026-002a"
    title: str = "State-Factored Ply Decomposition Mealy Machine"
    basis_gates: List[str] = field(default_factory=lambda: ["AND", "OR", "XOR", "ANDN"])
    tie_breaking_order: List[int] = field(default_factory=lambda: [4, 0, 2, 6, 8, 1, 3, 5, 7])
    expected_ply_distribution: List[int] = field(default_factory=lambda: [1, 72, 756, 1372, 222])
    total_states_expected: int = 2423
    dont_care_states_expected: int = 259721
    move_encoding: str = "dense_4bit_binary"
    output_bits: int = 4
    timeout_per_ply_seconds: float = 300.0
    timeout_total_seconds: float = 7200.0
    gate_reduction_threshold: float = 0.20
    depth_reduction_threshold: float = 0.25
    operational_ply_delta_n_threshold: float = 0.20
    subcone_gate_thresholds: List[int] = field(default_factory=lambda: [0, 12, 28, 32, 8])
    max_baseline_subcone: int = 45
    max_mux_gates: int = 20
    max_mux_depth: int = 3
    output_dir: Path = Path("data/telemetry/EXP-2026-002a")


def load_config(config_path: Optional[Path] = None) -> ExperimentConfig:
    """Loads configuration from config.toml if provided, or returns defaults."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.toml"

    if not config_path.exists():
        return ExperimentConfig()

    with open(config_path, "rb") as f:
        data = tomllib.load(f)

    exp = data.get("experiment", {})
    tb = data.get("tie_breaking", {})
    ss = data.get("state_space", {})
    enc = data.get("encoding", {})
    syn = data.get("synthesis", {})
    th = data.get("thresholds", {})
    out = data.get("output", {})

    return ExperimentConfig(
        experiment_id=exp.get("id", "EXP-2026-002a"),
        title=exp.get("title", "State-Factored Ply Decomposition Mealy Machine"),
        basis_gates=syn.get("basis", ["AND", "OR", "XOR", "ANDN"]),
        tie_breaking_order=tb.get("canonical_order", [4, 0, 2, 6, 8, 1, 3, 5, 7]),
        expected_ply_distribution=ss.get("expected_ply_counts", [1, 72, 756, 1372, 222]),
        total_states_expected=ss.get("expected_total_states", 2423),
        dont_care_states_expected=ss.get("expected_dont_cares", 259721),
        move_encoding=enc.get("move_encoding", "dense_4bit_binary"),
        output_bits=enc.get("output_bits", 4),
        timeout_per_ply_seconds=float(syn.get("timeout_per_ply_seconds", 300.0)),
        timeout_total_seconds=float(syn.get("timeout_total_seconds", 7200.0)),
        gate_reduction_threshold=float(th.get("gate_reduction_delta_n", 0.20)),
        depth_reduction_threshold=float(th.get("depth_reduction_delta_d", 0.25)),
        operational_ply_delta_n_threshold=float(th.get("operational_ply_delta_n", 0.20)),
        subcone_gate_thresholds=syn.get("subcone_gate_bounds", [0, 12, 28, 32, 8]),
        max_baseline_subcone=syn.get("max_baseline_subcone", 45),
        max_mux_gates=syn.get("max_mux_gates", 20),
        max_mux_depth=syn.get("max_mux_depth", 3),
        output_dir=Path(out.get("telemetry_dir", "data/telemetry/EXP-2026-002a")),
    )
