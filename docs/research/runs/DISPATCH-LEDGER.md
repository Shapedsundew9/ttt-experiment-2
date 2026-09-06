# Agent Dispatch & Financial Controller Ledger

Audit log of all subagent dispatch requests evaluated by the Financial Controller.

| Timestamp (UTC) | Dispatch Tool | Requested Agent(s) | Ruling | Rationale / Policy |
| :--- | :--- | :--- | :--- | :--- |
| 2026-09-06 17:47:29 | `invoke_subagent` | `sci-hypothesis-formulator` | **DENY** | Context Consolidation Guardrail: Subagent dispatch for ['sci-hypothesis-formulator'] is blocked. Execute this step in-context using skill 'sci-formulation' (for strategy/hypothesis/protocol) or 'sci-evaluation' (for diagnostics/curriculum) to prevent cold-start overhead. |
| 2026-09-06 17:47:29 | `runSubagent` | `code: swe` | **ASK** | Financial Controller Alert: The active campaign in docs/research/CAMPAIGN.md is marked as TERMINATED_SUCCESS. Operator confirmation required to dispatch new workers. |
