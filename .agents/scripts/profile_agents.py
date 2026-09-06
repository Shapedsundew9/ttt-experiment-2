#!/usr/bin/env python3
"""Agent Activity & Token Profiler for Antigravity & Copilot Workflows.

Parses conversation transcripts and logs to measure:
- Tool call distribution (Discovery/Read vs Execution/Write vs Orchestration)
- Cold-start Discovery Overhead Ratio (DOR)
- Estimated token volumes (Prompt, Output, Tool payloads)
- Subagent dispatch count and payload sizes
- Emits structured Markdown profiling reports
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Optional


DISCOVERY_TOOLS = {
    "view_file",
    "grep_search",
    "find_by_name",
    "list_dir",
    "read_url_content",
    "search_web",
    "read",
    "search",
}

EXECUTION_TOOLS = {
    "write_to_file",
    "replace_file_content",
    "run_command",
    "edit",
    "execute",
}

ORCHESTRATION_TOOLS = {
    "invoke_subagent",
    "manage_subagents",
    "send_message",
    "manage_task",
    "schedule",
    "ask_question",
    "runSubagent",
    "agent",
}


def estimate_tokens(text: str) -> int:
    """Rough estimation of token count from text (~4 chars per token)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def analyze_transcript(transcript_path: Path) -> Dict[str, Any]:
    """Analyzes a single transcript.jsonl file."""
    steps: List[Dict[str, Any]] = []
    tool_counter: Counter = Counter()
    category_counter: Counter = Counter()
    subagent_dispatches: List[Dict[str, Any]] = []

    total_chars_in = 0
    total_chars_out = 0
    discovery_tool_count = 0
    execution_tool_count = 0
    orchestration_tool_count = 0
    other_tool_count = 0

    first_write_step: Optional[int] = None
    first_write_tool: Optional[str] = None
    discovery_calls_before_write = 0

    if not transcript_path.exists():
        return {"error": f"Path does not exist: {transcript_path}"}

    with open(transcript_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                step = json.loads(line)
                steps.append(step)
            except json.JSONDecodeError:
                continue

    for step in steps:
        step_idx = step.get("step_index", 0)
        source = step.get("source", "")
        content = step.get("content", "") or ""
        tool_calls = step.get("tool_calls", []) or []

        if source == "USER_EXPLICIT":
            total_chars_in += len(content)
        elif source == "MODEL":
            total_chars_out += len(content)
            thinking = step.get("thinking", "") or ""
            total_chars_out += len(thinking)

        for tc in tool_calls:
            if not isinstance(tc, dict):
                continue
            fn = tc.get("function", {}) if "function" in tc else tc
            name = fn.get("name") or tc.get("name", "unknown")
            args = fn.get("arguments") or tc.get("args", {})
            args_str = json.dumps(args) if isinstance(args, (dict, list)) else str(args)
            total_chars_out += len(args_str)

            tool_counter[name] += 1

            if name in DISCOVERY_TOOLS:
                category_counter["Discovery / Read"] += 1
                discovery_tool_count += 1
                if first_write_step is None:
                    discovery_calls_before_write += 1
            elif name in EXECUTION_TOOLS:
                category_counter["Execution / Write"] += 1
                execution_tool_count += 1
                if first_write_step is None:
                    first_write_step = step_idx
                    first_write_tool = name
            elif name in ORCHESTRATION_TOOLS:
                category_counter["Orchestration"] += 1
                orchestration_tool_count += 1
                if name in ("invoke_subagent", "runSubagent"):
                    sub_list = args.get("Subagents", []) if isinstance(args, dict) else []
                    for sub in sub_list:
                        subagent_dispatches.append({
                            "step_index": step_idx,
                            "role": sub.get("Role", "unknown"),
                            "type": sub.get("TypeName", "unknown"),
                            "prompt_tokens": estimate_tokens(sub.get("Prompt", "")),
                        })
            else:
                category_counter["Other"] += 1
                other_tool_count += 1

    total_tool_calls = sum(tool_counter.values())
    productive_sum = discovery_tool_count + execution_tool_count
    dor = (discovery_tool_count / productive_sum) if productive_sum > 0 else 0.0

    est_input_tokens = estimate_tokens(" " * total_chars_in)
    est_output_tokens = estimate_tokens(" " * total_chars_out)

    return {
        "file_path": str(transcript_path),
        "total_steps": len(steps),
        "total_tool_calls": total_tool_calls,
        "tool_counter": dict(tool_counter.most_common()),
        "category_counter": dict(category_counter),
        "discovery_tool_count": discovery_tool_count,
        "execution_tool_count": execution_tool_count,
        "orchestration_tool_count": orchestration_tool_count,
        "other_tool_count": other_tool_count,
        "discovery_overhead_ratio": dor,
        "discovery_calls_before_first_write": discovery_calls_before_write,
        "first_write_step": first_write_step,
        "first_write_tool": first_write_tool,
        "subagent_dispatches": subagent_dispatches,
        "estimated_input_tokens": est_input_tokens,
        "estimated_output_tokens": est_output_tokens,
        "estimated_total_tokens": est_input_tokens + est_output_tokens,
    }


def format_markdown_report(analyses: List[Dict[str, Any]], title: str = "Agent Activity & Token Profile") -> str:
    """Formats one or more analyses into a structured Markdown document."""
    lines: List[str] = [
        f"# {title}",
        "",
        f"- **Generated UTC**: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')}",
        f"- **Sessions Profiled**: {len(analyses)}",
        "",
        "---",
        "",
        "## 1. Executive Summary & Overhead Ratios",
        "",
        "| Session / File | Steps | Total Tools | Discovery Calls | Write Calls | Discovery Ratio (DOR) | Est. Tokens |",
        "| :--- | :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    total_steps = 0
    total_tools = 0
    total_disc = 0
    total_exec = 0
    total_tokens = 0

    for a in analyses:
        if "error" in a:
            continue
        fname = Path(a["file_path"]).name
        parent_dir = Path(a["file_path"]).parents[2].name if len(Path(a["file_path"]).parents) >= 3 else fname
        label = f"{parent_dir[:8]}.../{fname}"
        steps = a["total_steps"]
        tools = a["total_tool_calls"]
        disc = a["discovery_tool_count"]
        exec_calls = a["execution_tool_count"]
        dor = a["discovery_overhead_ratio"]
        tokens = a["estimated_total_tokens"]

        total_steps += steps
        total_tools += tools
        total_disc += disc
        total_exec += exec_calls
        total_tokens += tokens

        lines.append(f"| `{label}` | {steps} | {tools} | {disc} | {exec_calls} | {dor * 100:.1f}% | {tokens:,} |")

    tot_prod = total_disc + total_exec
    global_dor = (total_disc / tot_prod) if tot_prod > 0 else 0.0
    lines.extend([
        "",
        f"- **Combined Steps**: {total_steps}",
        f"- **Combined Tool Calls**: {total_tools}",
        f"- **Global Discovery Overhead Ratio (DOR)**: `{global_dor * 100:.1f}%` (Percentage of productive actions spent re-reading / discovering files)",
        f"- **Total Estimated LLM Tokens**: `{total_tokens:,}`",
        "",
        "---",
        "",
        "## 2. Tool Category Distribution",
        "",
        "| Tool Name | Category | Invocations | Percentage |",
        "| :--- | :--- | :--- | :--- |",
    ])

    agg_tools: Counter = Counter()
    for a in analyses:
        for t, cnt in a.get("tool_counter", {}).items():
            agg_tools[t] += cnt

    for t, cnt in agg_tools.most_common():
        cat = "Discovery / Read" if t in DISCOVERY_TOOLS else ("Execution / Write" if t in EXECUTION_TOOLS else ("Orchestration" if t in ORCHESTRATION_TOOLS else "Other"))
        pct = (cnt / total_tools * 100) if total_tools > 0 else 0.0
        lines.append(f"| `{t}` | {cat} | {cnt} | {pct:.1f}% |")

    lines.extend([
        "",
        "---",
        "",
        "## 3. Subagent Dispatch Accounting",
        "",
        "| Session | Step | Role | Type | Est. Prompt Tokens |",
        "| :--- | :--- | :--- | :--- | :--- |",
    ])

    subagent_count = 0
    for a in analyses:
        parent_dir = Path(a["file_path"]).parents[2].name if len(Path(a["file_path"]).parents) >= 3 else "unknown"
        for sub in a.get("subagent_dispatches", []):
            subagent_count += 1
            lines.append(f"| `{parent_dir[:8]}` | {sub['step_index']} | {sub['role']} | `{sub['type']}` | {sub['prompt_tokens']:,} |")

    if subagent_count == 0:
        lines.append("| *None recorded in checked sessions* | - | - | - | - |")

    lines.extend([
        "",
        "---",
        "",
        "## 4. Cold Start & In-Context Efficiency Insights",
        "",
        f"1. **Discovery Cold Start**: Discovery/read operations comprise **{global_dor * 100:.1f}%** of all tool calls, showing the heavy cost of agents needing to orient themselves.",
        "2. **Subagent Overhead**: Dispatched subagents inherit no conversational working memory, forcing duplicate discovery sweeps.",
        "3. **Optimization Potential**: Consolidating formulation and evaluation into **in-context skills** eliminates repeated system prompt injections and discovery passes.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile Agent Token & Activity Overhead")
    parser.add_argument("--transcript", type=str, default=None, help="Path to transcript.jsonl")
    parser.add_argument("--brain-dir", type=str, default="/home/vscode/.gemini/antigravity-cli/brain", help="Brain directory")
    parser.add_argument("--output-md", type=str, default=None, help="Path to write output markdown report")
    parser.add_argument("--all", action="store_true", help="Scan all conversations in brain directory")
    args = parser.parse_args()

    target_files: List[Path] = []

    if args.transcript:
        p = Path(args.transcript)
        if p.exists():
            target_files.append(p)
    else:
        brain_path = Path(args.brain_dir)
        if brain_path.exists():
            for t_path in brain_path.glob("*/.system_generated/logs/transcript.jsonl"):
                target_files.append(t_path)

    if not target_files:
        print("No transcripts found.")
        sys.exit(1)

    analyses = [analyze_transcript(tf) for tf in target_files]
    report = format_markdown_report(analyses)

    if args.output_md:
        out_p = Path(args.output_md)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(report, encoding="utf-8")
        print(f"Report written to {out_p}")
    else:
        print(report)


if __name__ == "__main__":
    main()
