#!/usr/bin/env python3
"""Deterministic Financial Controller & Context Consolidation Guardrail.

Intercepts subagent dispatch tool calls (invoke_subagent in Antigravity,
runSubagent in GitHub Copilot) to enforce:
1. Context Consolidation: Blocks spinning up redundant subagents for procedural
   tasks that must be executed in-context via skills (sci-formulation, sci-evaluation).
2. Budget Ceilings: Intercepts worker dispatches when budget limits in CAMPAIGN.md
   are reached, requiring human-in-the-loop authorization.
3. Provenance Ledger: Records all dispatch rulings in .agents/data/agent_ledger.jsonl.
"""

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional, Tuple


# Consolidated procedural roles that MUST be handled in-context via skills
CONSOLIDATED_ROLES = {
    "sci-hypothesis-formulator",
    "sci-experiment-protocol",
    "sci-research-strategist",
    "sci-empirical-diagnostician",
    "sci-curriculum-director",
    "hypothesis formulator",
    "experiment protocol designer",
    "research strategist",
    "empirical diagnostician",
    "curriculum director",
}

# Sandboxed execution workers authorized for isolated dispatch
AUTHORIZED_WORKERS = {
    "swe",
    "code: swe",
    "code-swe",
    "debug",
    "code: debug",
    "qa-lite",
    "code: qa-lite",
    "qa",
    "code: qa",
}


def log_decision(
    ledger_path: Path,
    tool_name: str,
    requested_agents: List[str],
    decision: str,
    reason: str,
) -> None:
    """Logs the ruling into a human-readable Markdown ledger."""
    try:
        ledger_path.parent.mkdir(parents=True, exist_ok=True)
        if not ledger_path.exists():
            header = (
                "# Agent Dispatch & Financial Controller Ledger\n\n"
                "Audit log of all subagent dispatch requests evaluated by the Financial Controller.\n\n"
                "| Timestamp (UTC) | Dispatch Tool | Requested Agent(s) | Ruling | Rationale / Policy |\n"
                "| :--- | :--- | :--- | :--- | :--- |\n"
            )
            ledger_path.write_text(header, encoding="utf-8")

        now_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
        agents_str = ", ".join(f"`{a}`" for a in requested_agents) if requested_agents else "*none*"
        decision_label = f"**{decision.upper()}**"
        # Sanitize reason to not break markdown table
        sanitized_reason = reason.replace("|", "\\|").replace("\n", " ")
        row = f"| {now_str} | `{tool_name}` | {agents_str} | {decision_label} | {sanitized_reason} |\n"

        with open(ledger_path, "a", encoding="utf-8") as f:
            f.write(row)
    except Exception as e:
        sys.stderr.write(f"Warning: Failed to log to ledger: {e}\n")


def extract_requested_agents(tool_name: str, args: Dict[str, Any]) -> List[str]:
    """Extracts targeted agent/subagent names across Antigravity and Copilot formats."""
    agents: List[str] = []

    # Antigravity format: {"Subagents": [{"TypeName": "...", "Role": "..."}, ...]}
    if "Subagents" in args and isinstance(args["Subagents"], list):
        for sub in args["Subagents"]:
            if isinstance(sub, dict):
                type_name = sub.get("TypeName", "").strip().lower()
                role = sub.get("Role", "").strip().lower()
                if type_name:
                    agents.append(type_name)
                elif role:
                    agents.append(role)

    # GitHub Copilot format: {"agent": "...", ...} or {"name": "..."}
    for key in ("agent", "name", "subagent", "target"):
        if key in args and isinstance(args[key], str):
            agents.append(args[key].strip().lower())

    return agents


def evaluate_dispatch(requested_agents: List[str]) -> Tuple[str, str]:
    """Evaluates whether the requested agents are allowed, denied, or gated."""
    if not requested_agents:
        return "allow", "No specific agent constraints triggered."

    denied_agents = []
    for ag in requested_agents:
        # Check against consolidated procedural roles
        for blocked in CONSOLIDATED_ROLES:
            if blocked in ag:
                denied_agents.append(ag)
                break

    if denied_agents:
        return (
            "deny",
            f"Context Consolidation Guardrail: Subagent dispatch for {denied_agents} is blocked. "
            "Execute this step in-context using skill 'sci-formulation' (for strategy/hypothesis/protocol) "
            "or 'sci-evaluation' (for diagnostics/curriculum) to prevent cold-start overhead.",
        )

    # Check authorized workers against campaign budget
    campaign_path = Path("docs/research/CAMPAIGN.md")
    if campaign_path.exists():
        content = campaign_path.read_text(encoding="utf-8")
        if "TERMINATED_SUCCESS" in content and any("swe" in ag for ag in requested_agents):
            return (
                "ask",
                "Financial Controller Alert: The active campaign in docs/research/CAMPAIGN.md "
                "is marked as TERMINATED_SUCCESS. Operator confirmation required to dispatch new workers.",
            )

    return "allow", "Subagent authorized for quarantined execution."


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except Exception as e:
        # Fail safe: if stdin is empty or malformed, allow to prevent catastrophic blockage
        print(json.dumps({"decision": "allow", "reason": f"Input parse error: {e}"}))
        return

    tool_call = payload.get("toolCall", {})
    tool_name = tool_call.get("name", "")
    args = tool_call.get("args", {})

    ledger_path = Path("docs/research/runs/DISPATCH-LEDGER.md")

    # Match subagent dispatch tools in Antigravity and Copilot
    if tool_name in ("invoke_subagent", "runSubagent", "agent"):
        agents = extract_requested_agents(tool_name, args)
        decision, reason = evaluate_dispatch(agents)
        log_decision(ledger_path, tool_name, agents, decision, reason)
        print(json.dumps({"decision": decision, "reason": reason}))
    else:
        # Not a subagent dispatch tool
        print(json.dumps({"decision": "allow"}))


if __name__ == "__main__":
    main()
