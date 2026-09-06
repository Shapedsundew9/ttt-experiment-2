"""Experiment configuration loader and dataclasses."""

from dataclasses import dataclass, field
import os
from pathlib import Path
import tomllib
from typing import List


@dataclass
class ExperimentConfig:
    id: str = "EXP-2026-001a"
    name: str = "minimax-baseline"
    seed: int = 42
    canonical_order: List[int] = field(
        default_factory=lambda: [4, 0, 2, 6, 8, 1, 3, 5, 7]
    )
    ablation_lex_order: List[int] = field(
        default_factory=lambda: [0, 1, 2, 3, 4, 5, 6, 7, 8]
    )
    eval_interleaved: bool = True
    eval_dual_bitboard: bool = True
    basis: List[str] = field(default_factory=lambda: ["AND", "OR", "XOR", "ANDN"])
    timeout_per_cone_seconds: int = 300
    max_total_synthesis_seconds: int = 1200
    exact_dag_upper_bound: int = 60
    eval_dont_care_ablation: bool = True
    eval_decoder_benchmark: bool = True
    telemetry_dir: Path = field(default_factory=lambda: Path("data/telemetry/EXP-2026-001a"))

    @classmethod
    def load(cls, config_path: Path) -> "ExperimentConfig":
        if not config_path.exists():
            return cls()

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        exp = data.get("experiment", {})
        tb = data.get("tie_breaking", {})
        rep = data.get("representations", {})
        syn = data.get("synthesis", {})
        out = data.get("output", {})

        return cls(
            id=exp.get("id", "EXP-2026-001a"),
            name=exp.get("name", "minimax-baseline"),
            seed=exp.get("seed", 42),
            canonical_order=tb.get("canonical_order", [4, 0, 2, 6, 8, 1, 3, 5, 7]),
            ablation_lex_order=tb.get("ablation_lex_order", [0, 1, 2, 3, 4, 5, 6, 7, 8]),
            eval_interleaved=rep.get("eval_interleaved", True),
            eval_dual_bitboard=rep.get("eval_dual_bitboard", True),
            basis=syn.get("basis", ["AND", "OR", "XOR", "ANDN"]),
            timeout_per_cone_seconds=syn.get("timeout_per_cone_seconds", 300),
            max_total_synthesis_seconds=syn.get("max_total_synthesis_seconds", 1200),
            exact_dag_upper_bound=syn.get("exact_dag_upper_bound", 60),
            eval_dont_care_ablation=syn.get("eval_dont_care_ablation", True),
            eval_decoder_benchmark=syn.get("eval_decoder_benchmark", True),
            telemetry_dir=Path(out.get("telemetry_dir", "data/telemetry/EXP-2026-001a")),
        )
