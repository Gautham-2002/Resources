# 02 — The Attention Mechanism
### Scaled Dot-Product Attention: The Core of Everything

> **Key insight:** Attention is a differentiable, content-based memory lookup. Every token gathers information from any other token — weighted by *learned relevance*, not fixed position.

---

## Why Attention?

RNNs compress all history into a single fixed-size hidden state vector. Long-range dependencies degrade because gradients must flow through many recurrent steps (vanishing gradient problem).

Attention solves this: allow every token to **directly attend to any past token**, computing a weighted average of all their representations. No compression bottleneck, no sequential dependency.

---

## Part 1 — Q, K, and V: A Soft Dictionary Lookup

| Component | Role | Analogy |
|-----------|------|---------|
| **Query (Q)** | What am I looking for? | Search term |
| **Key (K)** | What do I advertise? | Index entry |
| **Value (V)** | What do I return when selected? | Stored content |

Every token produces all three. A token's **query** is compared against every token's **key**; the matched **values** are aggregated.

---

## Part 2 — Scaled Dot-Product Attention, Derived

Given sequence matrix `X ∈ ℝ^(T × d_model)`, project into Q/K/V spaces:

```
Q = X W_Q    W_Q ∈ ℝ^(d_model × d_k)
K = X W_K    W_K ∈ ℝ^(d_model × d_k)
V = X W_V    W_V ∈ ℝ^(d_model × d_v)
```

**Similarity scores** (all pairs simultaneously):

```
Scores = Q Kᵀ   ∈ ℝ^(T × T)
```

### Why Scale by `1/√d_k`?

For `q, k ∈ ℝ^d_k` with components drawn i.i.d. from `N(0, 1)`:

```
Var[q · k] = Σᵢ Var[qᵢ kᵢ] = d_k
→  Std[q · k] = √d_k
```

Dot-product magnitudes grow with `√d_k`. Large inputs to softmax push it into **near-zero gradient territory** — softmax saturates, becoming a one-hot distribution, killing gradient flow.

**The fix:** divide by `√d_k` to normalize variance back to ~1:

```
Scaled Scores = Q Kᵀ / √d_k
```

### Full Formula

```
Attention(Q, K, V) = softmax( Q Kᵀ / √d_k ) · V
```

- `A = softmax(...)    ∈ ℝ^(T × T)`  — row-normalized attention weights
- `A V                 ∈ ℝ^(T × d_v)` — weighted sum of value vectors

---

## Part 3 — Causal (Masked) Attention

Decoder-only models must predict token `t` using only tokens `< t`. We enforce this with a **causal mask** added before softmax:

```
Mask[i, j] = 0    if j ≤ i    (past/present — allowed)
Mask[i, j] = -∞   if j > i    (future — blocked)
```

After softmax: `exp(-∞) = 0`, so future attention weights are exactly zero.

```
Mask for T=4:
         k=0   k=1   k=2   k=3
q=0  [    0    -∞    -∞    -∞  ]
q=1  [    0     0    -∞    -∞  ]
q=2  [    0     0     0    -∞  ]
q=3  [    0     0     0     0  ]
```

**Efficiency benefit:** Training computes all `T` next-token predictions in one forward pass (teacher forcing) — no sequential loop needed.

---

## Part 4 — Multi-Head Attention

A single head computes one kind of similarity in one subspace. Language has many simultaneous relationship types (syntactic agreement, coreference, semantic proximity). Multi-Head Attention runs `H` independent attention heads in parallel:

```
head_h = Attention(X W_Q^h,  X W_K^h,  X W_V^h)    for h = 1 … H
```

Each head uses `d_k = d_v = d_model / H` — same total parameter count as one large head.

Outputs are concatenated and projected:

```
MultiHead(X) = Concat(head_1, …, head_H) · W_O

  Concat: ∈ ℝ^(T × d_model)
  W_O:    ∈ ℝ^(d_model × d_model)
```

**Total parameters per MHA layer:** `4 × d_model²` (W_Q, W_K, W_V combined across heads + W_O).

Empirically, heads specialize: some track local syntax, some track long-range coreference, some handle positional patterns.

---

## Part 5 — Complexity & Flash Attention

| Operation | Complexity |
|-----------|-----------|
| Q, K, V projections | O(T · d_model²) |
| Score matrix `Q Kᵀ` | **O(T² · d_k)** ← bottleneck |
| Softmax + weighted sum | O(T²) |

Doubling context length → 4× attention compute. This is why context length is precious.

**Flash Attention (Dao et al., 2022):** An IO-aware algorithm that tiles Q, K, V to stay in GPU SRAM (fast memory), avoiding materializing the full T×T matrix in HBM (slow memory). Same mathematical result, O(T) memory, significantly faster wall-clock. Enables 128K+ context windows.

---

## Data Flow Diagram

```
Input X:  ∈ ℝ^(B × T × d_model)
              │
    ┌─────────┼──────────┐
   W_Q       W_K        W_V
    │         │          │
    Q         K          V
    │         │          │
    └────┬────┘          │
      Q Kᵀ / √d_k        │
      + Mask              │
      softmax → A         │
         └──── A · V ─────┘
                  │
                 W_O
                  │
              Output: ∈ ℝ^(B × T × d_model)
```

---

## Design Decisions Summarized

| Decision | Reason |
|----------|--------|
| Dot-product similarity | Efficient (GEMM), differentiable |
| `1/√d_k` scaling | Prevents softmax saturation as d_k grows |
| Learned Q, K, V projections | Content-based routing, not static similarity |
| Causal mask | Full-sequence training in one parallel pass |
| Multi-head | Different relational subspaces simultaneously |
| Output projection W_O | Mixes and recombines information across heads |

---

*Previous: [01 — Tokenization & Embeddings](./01_Tokenization_and_Embeddings.md)*
*Next: [03 — The Transformer Block](./03_Transformer_Block.md)*
