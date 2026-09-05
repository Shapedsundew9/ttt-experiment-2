# Creating a Tic-Tac-Toe Digital Mealy Machine

## Problem Formulation & Invariants

Let the input be an 18-bit vector $I \in \{0,1\}^{18}$ (9 positions $\times$ 2 bits: `00`=empty, `01`=X, `10`=O, `11`=invalid). The Mealy machine computes the next move $M \in \{0,1\}^9$ (one-hot) or $M \in \{0,1\}^4$ (index $0\text{--}8$), along with the next state $S' \in \{0,1\}^k$ ($k \le 46$).

* **The Don't-Care Leverage:** Out of $2^{18} = 262,144$ possible inputs, only **958 board states** represent reachable, legal positions where it is X's turn to move (assuming X plays first). Over **99.6%** of the input space constitutes "Don't-Care" (DC) conditions.
* **Role of the Internal State $S$:** Tic-tac-toe is a game of perfect information; the current board $I$ fully specifies optimal play without history. However, using $S$ to track the **ply count** ($t \in \{0, 1, 2, 3, 4\}$) decomposes a monolithic 18-input Boolean function into 5 disjoint, low-complexity sub-functions.

---

### 1. Exact Logic Synthesis via SAT/QBF (Provably Minimal Gate DAG)

Because every 2-input Boolean gate directly maps to a single 64-bit CPU bitwise instruction (`AND`, `OR`, `XOR`, `ANDN`), synthesizing a minimal circuit directly yields the minimal instruction sequence.

**Method:**

1. Extract the on-set ($F$) and off-set ($R$) for each output bit across the 958 reachable board states. All remaining $261,186$ patterns belong to the don't-care set ($D$).
2. Formulate the circuit synthesis problem as a **Boolean Satisfiability (SAT)** or **Quantified Boolean Formula (QBF)** instance parameterized by DAG size $N$ (number of 2-input gates).
3. Use incremental SAT solving (e.g., using **Berkeley ABC** or the EPFL **Mockturtle / CirKit** exact synthesis framework) to find the smallest $N$ such that a DAG of 2-input gates satisfies all $F$ and $R$ constraints.

**CPU Mapping:**

$$\text{Gate } i = g_i(\text{wire}_a, \text{wire}_b) \implies r_i = \text{op}_i(r_a, r_b)$$

With $k$ output bits computed as terminal nodes in the synthesized DAG.

---

### 2. State-Factored Ply Decomposition (Mealy Partitioning)

Instead of evaluating a global policy function, use the Mealy state $S$ as a stage-select register ($S \in \{0, 1, 2, 3, 4\}$) or to latch previous moves.

```text
Ply 0 (Turn 1): Output = Center (Cell 4)                [0 ops: Constant]
Ply 1 (Turn 2): If O played Corner -> Play Opposite Corner
                Else -> Play adjacent Corner            [Minimal LUT / Mask]
Ply 2 (Turn 3): Check immediate Win -> Block O Win      [3-in-a-row masks]
Ply 3 (Turn 4): Win / Block / Force Fork
Ply 4 (Turn 5): Play only remaining empty square        [Bitwise NOT/AND]
```

* **Bit-Parallel Multiplexing:** Condition execution paths on state bits using branchless masking:

$$\text{Move} = \bigoplus_{t=0}^4 (\text{Mask}_t \ \& \ f_t(I))$$

Because $f_0(I)$ through $f_2(I)$ only inspect a subset of input bits, their individual gate counts collapse to single-digit operations.

---

### 3. Cartesian & Linear Genetic Programming (CGP / LGP)

Exact SAT synthesis scales exponentially with gate count and struggles if native 64-bit operations beyond 2-input logic (e.g., shifts, additions, bit-reversals, or carry chains) are permitted. Genetic Programming searches this broader instruction space directly.

* **Representation:** A linear genome of $N$ instructions operating on a bank of 64-bit registers:

$$r_d \leftarrow \text{OP}(r_s, r_t), \quad \text{OP} \in \{\text{AND}, \text{OR}, \text{XOR}, \text{ANDN}, \text{SHL}, \text{SHR}, \text{ADD}, \text{SUB}\}$$

* **Fitness Function:**

$$\text{Fitness} = \text{Score}_{\text{Minimax}}(G) - \lambda \cdot (\text{Instruction Count})$$

Where $\text{Score}_{\text{Minimax}}$ validates that the machine achieves a draw or win against all reachable opponent responses (exact minimax verification over the full game tree).

* **Evaluation Speed:** The 958 reachable test boards can be packed into 15 64-bit words, enabling candidate programs to evaluate the entire game tree via bit-parallel SIMD/GPU in microseconds.

---

### 4. Bitboard Arithmetic & Win-Line Parallel Convolution

Deconstruct the 18-bit input into two 9-bit bitboards:

* $X = I \ \& \ \text{0x15555}$ (Mask odd bits)
* $O = (I \gg 1) \ \& \ \text{0x15555}$ (Mask even bits)
* $E = \sim(X \mid O) \ \& \ \text{0x1FF}$ (Empty positions)

```text
        Win Lines (8 total):
        Rows:    0x007, 0x038, 0x1C0
        Cols:    0x049, 0x092, 0x124
        Diags:   0x111, 0x054
```

* **Win / Block Detection via Bit Multiplication or Shift-Accumulate:**
For each winning line $L_k$, a winning threat for player $P$ exists where:

$$\text{popcount}(P \ \& \ L_k) = 2 \quad \text{and} \quad (E \ \& \ L_k) \neq 0$$

* **64-bit Parallelism:** Pack the 8 win lines across 8 bytes of a single 64-bit register. Compute the convolution of $X$ and $O$ against all 8 win lines simultaneously in 3–4 SIMD-within-a-register (SWAR) instructions.

---

### Comparison of Methodologies

| Approach | Optimality | Instruction Set Expressiveness | Scalability / Synthesis Time |
| --- | --- | --- | --- |
| **SAT-Based Exact Synthesis** | **Provably Minimal** (for 2-input boolean gates) | Boolean only (`AND`, `OR`, `XOR`, `ANDN`) | Minutes to hours via Z3/ABC |
| **State-Factored (Mealy)** | Near-Minimal (structured) | Any CPU instructions | Fast manual/heuristic design |
| **CGP / LGP** | Heuristically Minimal | Full 64-bit ISA (`SHL`, `ADD`, `BMI2`, etc.) | Hours of evolutionary search |
| **SWAR Bitboard Arithmetic** | Deterministic / Compact | SWAR / Byte-parallel ops | Immediate analytical derivation |

---

### Recommended Pipeline

1. **Step 1:** Generate the canonical minimax lookup table for all 958 reachable boards with the 18-bit input and desired 9-bit one-hot output. Fill all other $261,186$ entries with "Don't-Care" (`X`).
2. **Step 2:** Run **Berkeley ABC** with `resyn2`, `fraig`, and exact SAT-synthesis (`exact` command) targeting 2-input LUTs/gates to establish the global minimum baseline for pure Boolean operations.
3. **Step 3:** Use **Cartesian Genetic Programming** seeded with the decomposed ply-based logic to search for non-linear arithmetic reductions (e.g., using shifts, masks, and `SUB` carries) to beat the pure Boolean lower bound.

## Splitting the States

Splitting the board representation into separate 9-bit bitplanes—either **(Occupied $V$, Piece $P$)** or **Dual Bitboards ($X, O$)**—is substantially more efficient than the 18-bit interleaved format.

In logic synthesis and bitwise computation, interleaved 2-bit cell encoding forces the machine to spend gates simply demultiplexing coordinates. Planar representations eliminate this decoding penalty and expose geometric symmetry directly to bitwise operations.

---

### Key Structural Advantages

#### 1. Instant Legal Move Masking (1 Operation vs ~6)

* **Interleaved:** Finding empty squares requires evaluating $\sim(b_{2i+1} \mid b_{2i})$ for all 9 pairs, requiring shift-mask-unpack sequences.
* **Separated ($V, P$):** The set of legal moves is strictly the complement of the occupied mask:

$$\text{LegalMoves} = (\sim V) \ \& \ \text{0x1FF}$$

#### 2. Parallel Win-Line Convolutions via 1D Bit Shifts

When all squares reside in a single 9-bit plane, spatial lines (rows, columns, diagonals) can be evaluated simultaneously using parallel shift-and operations across the entire board:

```text
Board Index Mapping:
0 | 1 | 2
3 | 4 | 5
6 | 7 | 8

```

* **All 3 Columns in 2 Shifts:**

$$\text{ColWin}(X) = X \ \& \ (X \gg 3) \ \& \ (X \gg 6)$$

* **Both Diagonals:**

$$\text{Diag1}(X) = (X \ \& \ 0\text{x}100) \ \& \ (X \gg 4) \ \& \ (X \gg 8)$$

$$\text{Diag2}(X) = (X \ \& \ 0\text{x}040) \ \& \ (X \gg 2) \ \& \ (X \gg 4)$$

* **Threat Detection (2-in-a-row with open 3rd):**
Finding unblocked lines only requires masking these shifts against $\sim V$.

#### 3. Decoupling Turn Phase from Strategic State

* The game turn (ply count) is strictly a function of $V$:

$$\text{Ply} = \text{popcount}(V)$$

* The Mealy state transitions become independent of player identity, reducing the state machine transition logic to monotonic updates on $V$.

---

### Comparison: $(V, P)$ vs. $(X, O)$ Dual Bitboards

| Metric | Interleaved (18-bit) | Occupied + Piece ($V, P$) | Dual Bitboard ($X, O$) |
| --- | --- | --- | --- |
| **Bit Definition** | `[b1 b0] * 9` | $V = \text{occupied},\ P = \text{is\_X}$ | $X = \text{X-cells},\ O = \text{O-cells}$ |
| **Compute Empty** | 6–9 ops (mask/shift/OR) | **1 op** (`~V & 0x1FF`) | 2 ops (`~(X \| O) & 0x1FF`) |
| **Compute X / O** | N/A (coupled) | $X = V \ \& \ P$, $O = V \ \& \ \sim P$ | **0 ops** (native) |
| **Win Line Check** | Multi-LUT matching | 3–4 ops (after $X$ extraction) | **2 ops per axis** (`X & (X>>k)...`) |
| **SAT DAG Synthesis** | High gate depth (decoder penalty) | **Low gate depth** | **Lowest gate depth** |

---

### Impact on Automated Logic Synthesis (ABC / SAT)

When synthesizing the circuit with SAT/QBF exact synthesizers:

1. **Gate Count Reduction:** In an interleaved model, roughly **15 to 25% of the total 2-input gate budget** is wasted synthesizing equivalence extractors (e.g., $b_{2i} \land \overline{b_{2i+1}}$). Planar encoding gives the solver direct access to single-variable predicates.
2. **Shorter Critical Path:** Because $X$ and $O$ signals are independent inputs, the SAT solver can build parallel evaluation trees for offensive threats ($X$) and defensive threats ($O$) simultaneously, flattening the DAG depth.
3. **Don't-Care Optimization:** In the $(V, P)$ representation, whenever $V_i = 0$, $P_i$ is an unconditional Don't-Care ($DC$). The logic synthesizer can set $P_i$ to whatever constant minimizes the gate count for that specific sub-tree.

```text
       18-bit Input Register:
[ 17 . . . . . . . . 9 | 8 . . . . . . . . 0 ]
[      O Bitboard      |      X Bitboard      ]

```

### Bit Assignment

Each 9-bit segment maps directly to the $3 \times 3$ grid in row-major order (bits $0 \dots 8$ for positions $0 \dots 8$):

```text
Grid Indices:
 0 | 1 | 2
---+---+---
 3 | 4 | 5
---+---+---
 6 | 7 | 8

```

* **X Bitboard ($X$):** Bit $i = 1$ if cell $i$ contains an **X**, otherwise $0$.
* **O Bitboard ($O$):** Bit $i = 1$ if cell $i$ contains an **O**, otherwise $0$.

---

### Why Dual Bitboards Streamline Logic

* **Empty / Legal Moves (1 Bitwise Op):**

$$\text{Empty} = \sim(X \mid O) \ \& \ \text{0x1FF}$$

* **Mutual Exclusivity Invariant:**

$$(X \ \& \ O) = 0 \quad \text{(a cell cannot hold both)}$$

* **Symmetric Threat Detection:**
The sub-circuits for checking offensive opportunities ($X$) and defensive blocks ($O$) become identical logic functions operating on different halves of the 18-bit word:

$$\text{WinThreat}(P) = f(P, \text{Empty}) \quad \text{where } P \in \{X, O\}$$

* **Zero Decoding Overhead:**
Evaluating whether player $P$ controls the center square (index 4) requires no conditional decoding—only a direct bit-test: `(P >> 4) & 1`.
