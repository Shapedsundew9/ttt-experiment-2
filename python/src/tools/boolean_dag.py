"""Boolean Directed Acyclic Graph (DAG) for 2-Input Logic Synthesis.

Supports standard gates in Omega_DAG = {AND, OR, XOR, ANDN},
topological depth evaluation, node sharing, simulation, and complexity metrics.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Tuple


class GateOp(str, Enum):
    AND = "AND"
    OR = "OR"
    XOR = "XOR"
    ANDN = "ANDN"  # a AND (NOT b)


@dataclass(frozen=True)
class GateNode:
    op: GateOp
    left: int   # Index of left node (0..num_inputs-1 are primary inputs, >= num_inputs are gates)
    right: int  # Index of right node


@dataclass
class BooleanDAG:
    num_inputs: int
    outputs: List[int] = field(default_factory=list)  # Node indices driving each output
    gates: List[GateNode] = field(default_factory=list)

    def add_gate(self, op: GateOp, left: int, right: int) -> int:
        """Adds a 2-input gate and returns its global node index."""
        # Canonicalize commutative operators
        if op in (GateOp.AND, GateOp.OR, GateOp.XOR):
            if left > right:
                left, right = right, left

        node = GateNode(op=op, left=left, right=right)
        self.gates.append(node)
        return self.num_inputs + len(self.gates) - 1

    @property
    def gate_count(self) -> int:
        """Total number of 2-input logic gates in the DAG."""
        return len(self.gates)

    def compute_depth(self) -> int:
        """Computes the maximum topological depth (longest path from primary input to any output)."""
        depths: Dict[int, int] = {i: 0 for i in range(self.num_inputs)}
        for idx, gate in enumerate(self.gates):
            node_idx = self.num_inputs + idx
            d = 1 + max(depths[gate.left], depths[gate.right])
            depths[node_idx] = d

        if not self.outputs:
            return 0
        return max(depths[out] for out in self.outputs)

    def evaluate(self, input_bits: int) -> int:
        """Evaluates the DAG on an integer where bit i represents primary input i.
        
        Returns an integer where bit k represents output k.
        """
        values: Dict[int, int] = {}
        for i in range(self.num_inputs):
            values[i] = (input_bits >> i) & 1

        for idx, gate in enumerate(self.gates):
            node_idx = self.num_inputs + idx
            a = values[gate.left]
            b = values[gate.right]
            if gate.op == GateOp.AND:
                r = a & b
            elif gate.op == GateOp.OR:
                r = a | b
            elif gate.op == GateOp.XOR:
                r = a ^ b
            elif gate.op == GateOp.ANDN:
                r = a & (1 ^ b)
            else:
                raise ValueError(f"Unknown gate operator: {gate.op}")
            values[node_idx] = r

        output_val = 0
        for k, out_idx in enumerate(self.outputs):
            bit = values[out_idx]
            output_val |= (bit << k)
        return output_val

    def operator_distribution(self) -> Dict[str, int]:
        """Counts occurrences of each operator in the DAG."""
        dist = {op.value: 0 for op in GateOp}
        for g in self.gates:
            dist[g.op.value] += 1
        return dist


def build_interleaved_decoder_dag() -> BooleanDAG:
    """Constructs the canonical 18-gate cell decoder from Interleaved representation.
    
    Given 18 inputs: [b_0, b_1, b_2, ..., b_17]
    Outputs: [X_0..X_8, O_0..O_8] (18 outputs)
    Where X_i = b_{2i} AND NOT b_{2i+1}, O_i = b_{2i+1} AND NOT b_{2i}.
    Total gates: 18, depth: 1.
    """
    dag = BooleanDAG(num_inputs=18)
    outputs = []

    # X signals
    for i in range(9):
        b_low = 2 * i
        b_high = 2 * i + 1
        node = dag.add_gate(GateOp.ANDN, b_low, b_high)
        outputs.append(node)

    # O signals
    for i in range(9):
        b_low = 2 * i
        b_high = 2 * i + 1
        node = dag.add_gate(GateOp.ANDN, b_high, b_low)
        outputs.append(node)

    dag.outputs = outputs
    return dag
