# Agent Activity & Token Profile

- **Generated UTC**: 2026-09-06 17:38:48 UTC
- **Sessions Profiled**: 2

---

## 1. Executive Summary & Overhead Ratios

| Session / File | Steps | Total Tools | Discovery Calls | Write Calls | Discovery Ratio (DOR) | Est. Tokens |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `ed194e84.../transcript.jsonl` | 70 | 34 | 6 | 28 | 17.6% | 17,383 |
| `dc06fc96.../transcript.jsonl` | 95 | 44 | 22 | 22 | 50.0% | 35,436 |

- **Combined Steps**: 165
- **Combined Tool Calls**: 78
- **Global Discovery Overhead Ratio (DOR)**: `35.9%` (Percentage of productive actions spent re-reading / discovering files)
- **Total Estimated LLM Tokens**: `52,819`

---

## 2. Tool Category Distribution

| Tool Name | Category | Invocations | Percentage |
| :--- | :--- | :--- | :--- |
| `run_command` | Execution / Write | 48 | 61.5% |
| `view_file` | Discovery / Read | 18 | 23.1% |
| `find_by_name` | Discovery / Read | 6 | 7.7% |
| `search_web` | Discovery / Read | 2 | 2.6% |
| `grep_search` | Discovery / Read | 1 | 1.3% |
| `replace_file_content` | Execution / Write | 1 | 1.3% |
| `list_dir` | Discovery / Read | 1 | 1.3% |
| `write_to_file` | Execution / Write | 1 | 1.3% |

---

## 3. Subagent Dispatch Accounting

| Session | Step | Role | Type | Est. Prompt Tokens |
| :--- | :--- | :--- | :--- | :--- |
| *None recorded in checked sessions* | - | - | - | - |

---

## 4. Cold Start & In-Context Efficiency Insights

1. **Discovery Cold Start**: Discovery/read operations comprise **35.9%** of all tool calls, showing the heavy cost of agents needing to orient themselves.
2. **Subagent Overhead**: Dispatched subagents inherit no conversational working memory, forcing duplicate discovery sweeps.
3. **Optimization Potential**: Consolidating formulation and evaluation into **in-context skills** eliminates repeated system prompt injections and discovery passes.
