# Scientific Research Campaign State Tracker Template

This template defines the persistent state tracker for ongoing scientific campaigns. It maintains campaign continuity across session boundaries, tracks active hypotheses, records complexity ladder progression, and logs all iteration decisions.

Save active campaign state to `docs/research/CAMPAIGN.md`.

---

```markdown
# Scientific Research Campaign: [Campaign Title]

- **Campaign Identifier**: CAMPAIGN-[YEAR]-[SLUG]
- **Current Status**: ACTIVE | STALLED | COMPLETED | PIVOTED
- **Target Paradigm**: [e.g., Non-gradient sequence learning via flux-conserving dynamical attractors]
- **Last Updated**: YYYY-MM-DD HH:MM:SS UTC

---

## 1. Active Campaign State Machine

| Stage | Active Agent | Active Artifact Reference | Status |
|---|---|---|---|
| Strategic Direction | Sci: Research Strategist | `docs/research/STRAT-[ID].md` | COMPLETED |
| Hypothesis Formulation | Sci: Hypothesis Formulator | `docs/research/hypotheses/HYP-[ID].md` | COMPLETED |
| Protocol Design | Sci: Experiment Protocol Designer | `docs/research/protocols/EXP-[ID].md` | COMPLETED |
| Protocol & Budget Sign-Off | Operator / User | **Gate H/P**: Sign-off on budget & metrics | APPROVED |
| Execution & Telemetry | Code Track / Operator | `docs/research/runs/RUN-EXP-[ID].md` | COMPLETED |
| Diagnostic Analysis | Sci: Empirical Diagnostician | `docs/research/diagnostics/DIAG-[ID].md` | IN PROGRESS |
| Curriculum Iteration | Sci: Curriculum Director | `docs/research/ITER-[ID].md` | PENDING |
| Iteration Approval | Operator / User | **Gate I**: Sign-off on next action | PENDING |

---

## 2. Complexity Ladder Progression

Track the structural capability rungs established by the campaign:

| Rung | Theoretical Capability | Key Invariant / Metric Threshold | Status | Evidence Document |
|---|---|---|---|---|
| 1 | Basic Attractor Stability | Spectral radius $\rho(W) \le 1.0$, limit cycle period $T > 10$ | VERIFIED | `DIAG-2025-001` |
| 2 | Single-Task Memory Retention | Bit accuracy $> 0.95$ over 500 delay steps | VERIFIED | `DIAG-2025-003` |
| 3 | Multi-Task Backward Transfer | Backward Transfer $\text{BWT} > -0.05$ across 10 switches | ACTIVE | `EXP-2025-014a` |
| 4 | Compositional Generalization | Assembly Index $A_x > 5.0$ on unseen combinations | LOCKED | Requires Rung 3 |
| 5 | Lifelong Adaptation | Bounded assembly space under continuous shift | LOCKED | Requires Rung 4 |

---

## 3. Iteration & Decision History

Audit log of every discovery cycle executed within this campaign:

| Cycle | Hypothesis | Protocol | Package Path | Run ID | Git Tag | Diagnostic Verdict | Action Selected | User Gate Approval |
|---|---|---|---|---|---|---|---|---|
| 1 | `HYP-014` | `EXP-014a` | `python/experiments/exp_014a_flux/` | `RUN-EXP-014a-01` | `exp/EXP-014a-01` | Inconclusive (collapse at $\lambda=1.0$) | MUTATE (soft penalty) | Approved (Gate I on YYYY-MM-DD) |
| 2 | `HYP-014-v2` | `EXP-014b` | `python/experiments/exp_014b_penalty/` | `RUN-EXP-014b-01` | `exp/EXP-014b-01` | Supported ($\text{BWT} = -0.03 \pm 0.02$) | ADVANCE (Rung 4 evaluation) | Approved (Gate I on YYYY-MM-DD) |

---

## 4. Resource & Compute Accounting

- **Total Allocated Campaign Budget**: [e.g., 500 Compute-Hours]
- **Compute Consumed to Date**: [e.g., 142 Compute-Hours]
- **Remaining Budget**: [e.g., 358 Compute-Hours]
- **Max Iteration Limit per Milestone**: 5 iterations (Current: Cycle 2 of 5)
```
