# 03 — The Transformer Block
### Multi-Head Attention + Layer Norm + FFN + Residual Connections

> **Key insight:** A transformer block is a carefully engineered composition of four components. Each solves a specific failure mode of deep networks. The ordering and residual connections are not arbitrary — they are the reason training at depth is numerically stable.

---

## Overview: What a Block Does

One transformer block takes a sequence of token representations `X ∈ ℝ^(T × d_model)` and outputs a refined sequence of the same shape. It does this in two sub-layers:

```
1. Self-Attention Sub-Layer    (reads across the sequence)
2. Feed-Forward Sub-Layer      (processes each token independently)
```

With residual connections and layer normalization around each.

---

## Part 1 — Residual Connections

### The Vanishing Gradient Problem at Depth

Consider a deep network `f = fₙ ∘ ... ∘ f₂ ∘ f₁`. During backpropagation, the gradient of the loss with respect to early layer parameters requires multiplying Jacobians across every subsequent layer:

```
∂L/∂θ₁ = (∂L/∂fₙ) · (∂fₙ/∂fₙ₋₁) · ... · (∂f₂/∂f₁) · (∂f₁/∂θ₁)
```

If each Jacobian has spectral norm < 1 (common during early training), this product exponentially vanishes. Layers near the input receive near-zero gradient — they don't learn. This limits practical depth to ~10-20 layers without tricks.

### The He et al. (2016) Solution: Residual Connections

```
x_{out} = F(x) + x
```

The `+ x` term creates a **gradient highway**. The gradient now has two paths:

```
∂L/∂x = ∂L/∂x_{out} · (∂F/∂x + I)
```

The identity term `I` means the gradient is *at least* `∂L/∂x_{out}`, regardless of how small `∂F/∂x` becomes. The gradient cannot vanish as long as the skip connection exists.

**Practical effect:** GPT-3 has 96 transformer layers. Without residuals, training 96-layer networks is near-impossible. Residuals make depth effectively free.

### Geometric Interpretation

Each sub-layer learns a **residual** (correction) to apply to the current representation, not a full transformation from scratch. This is a gentler optimization landscape — the function `F(x) = 0` (identity) is an easy initial state (just zero out weights), and the network builds up corrections incrementally.

---

## Part 2 — Layer Normalization

### Why Normalization?

During training, activations shift in distribution as weights update (Internal Covariate Shift). Layers deeper in the network see constantly changing input distributions, making learning unstable.

**Batch Normalization** (standard in CNNs): normalize over the *batch* dimension. Problem: depends on batch size; doesn't work with small batches or autoregressive inference where batch size = 1.

**Layer Normalization (Ba et al., 2016):** normalize over the *feature* dimension (d_model) for each token independently.

### Formula

For a vector `x ∈ ℝ^d`:

```
μ = (1/d) Σᵢ xᵢ                    (mean over features)
σ² = (1/d) Σᵢ (xᵢ - μ)²           (variance over features)

LayerNorm(x) = γ ⊙ (x - μ) / √(σ² + ε)  +  β
```

Where:
- `γ ∈ ℝ^d` — learned scale parameter (initialized to 1)
- `β ∈ ℝ^d` — learned shift parameter (initialized to 0)
- `ε ≈ 1e-5` — small constant for numerical stability

**Parameters:** `2d` per layer norm instance (γ and β).

**Computational properties:**
- Independent of batch size — works at inference with batch=1
- Operates per-token — no cross-token information
- `O(d)` — negligible cost

### Pre-LN vs. Post-LN

**Original Transformer (Post-LN):**
```
x = LayerNorm(x + Attention(x))
x = LayerNorm(x + FFN(x))
```

**Modern models (Pre-LN, GPT-2 onward):**
```
x = x + Attention(LayerNorm(x))
x = x + FFN(LayerNorm(x))
```

**Why Pre-LN is better:**
- The residual stream `x` flows through the entire network without normalization, preserving gradient magnitude.
- At initialization, `LayerNorm(x) ≈ x/‖x‖`, so each sub-layer starts near identity.
- Training is more stable at depth — no need for learning rate warmup tricks.

LLaMA, Mistral, and most modern LLMs use Pre-LN.

**RMSNorm (LLaMA variant):** Drops the mean-centering step (just divides by RMS), which is slightly faster and empirically equivalent:

```
RMSNorm(x) = γ ⊙ x / √(mean(x²) + ε)
```

---

## Part 3 — The Feed-Forward Network (FFN)

### Structure

Applied **independently to each token position**. The FFN is a 2-layer MLP with an expansion factor (typically 4×):

```
FFN(x) = f_act(x W₁ + b₁) W₂ + b₂

  W₁ ∈ ℝ^(d_model × d_ff)     d_ff = 4 · d_model
  W₂ ∈ ℝ^(d_ff × d_model)
```

For GPT-3 with `d_model = 12288` and `d_ff = 49152` (4×):

```
Parameters per FFN: 2 × 12288 × 49152 ≈ 1.2B parameters
```

FFN layers hold the majority of parameters in large models.

### Activation Functions

**ReLU (original Transformer):**
```
f_act(x) = max(0, x)
```
Simple but has the "dying ReLU" problem: neurons stuck at zero gradient.

**GELU (GPT-2/3, BERT):**
```
GELU(x) = x · Φ(x)    where Φ is the Gaussian CDF
        ≈ 0.5x(1 + tanh(√(2/π)(x + 0.044715x³)))
```
Smoother transition than ReLU, empirically better for LLMs.

**SwiGLU (LLaMA, PaLM):** A gated variant that uses two parallel projections:
```
SwiGLU(x) = (x W₁ ⊙ SiLU(x W_gate)) W₂

  SiLU(x) = x · σ(x)    (sigmoid linear unit)
```
SwiGLU uses ~1.5x the parameters of a standard FFN but achieves better performance. LLaMA sets `d_ff = (8/3) · d_model` to match the standard parameter budget.

### What Does the FFN Learn?

Mechanistic interpretability research suggests FFN layers act as **key-value memories** (Geva et al., 2021):
- `W₁` rows are "keys" — patterns that activate on specific token contexts.
- `W₂` rows are "values" — information retrieved when that pattern fires.
- The FFN looks up and injects factual knowledge into the residual stream.

This is why FFN layers (not attention) appear to store most world knowledge — ablating FFN layers selectively degrades factual recall.

---

## Part 4 — Full Transformer Block

### Pre-LN Formulation (Modern Standard)

```python
def transformer_block(x, mask):
    # Sub-layer 1: Self-Attention
    residual = x
    x = layer_norm_1(x)           # normalize
    x = multi_head_attention(x, mask)  # attend
    x = residual + x              # residual add

    # Sub-layer 2: Feed-Forward
    residual = x
    x = layer_norm_2(x)           # normalize
    x = ffn(x)                    # transform
    x = residual + x              # residual add

    return x
```

**Shape through the block:**
```
Input:    (B, T, d_model)
→ LN1:    (B, T, d_model)   [no shape change]
→ MHA:    (B, T, d_model)   [no shape change]
→ +res:   (B, T, d_model)
→ LN2:    (B, T, d_model)
→ FFN:    (B, T, d_ff) → (B, T, d_model)
→ +res:   (B, T, d_model)
Output:   (B, T, d_model)   [same as input]
```

The block is an **identity-shaped transformation** — input and output dimensions match, enabling stacking `N` blocks without adapters.

---

## Part 5 — Stacking N Blocks: The Residual Stream View

With N blocks, the overall computation is:

```
X₀ = Embedding(tokens) + PositionalEncoding
X₁ = Block₁(X₀)
X₂ = Block₂(X₁)
...
Xₙ = Blockₙ(Xₙ₋₁)
Logits = Xₙ @ E.T    (unembed)
```

A cleaner view of the **residual stream** — since every block adds to the input rather than replacing it:

```
Xₙ = X₀ + Σₖ₌₁ⁿ  (MHA_k contribution + FFN_k contribution)
```

The residual stream is a **shared workspace** where all layers read from and write to. Each layer adds its specialized correction. This view explains:
- Why the residual stream tends to have consistent magnitude throughout depth.
- Why different layers compose: late layers can easily "read" what early layers wrote.
- Why it's possible to do model surgery (e.g., removing layers, merging models) with predictable effects.

---

## Parameter Count Per Block

For a model with `d_model = D`, `H` heads, `d_ff = 4D`:

| Component | Parameters |
|-----------|-----------|
| W_Q, W_K, W_V (MHA) | 3 × D² |
| W_O (MHA output) | D² |
| LayerNorm 1 | 2D |
| W₁, b₁ (FFN) | D × 4D + 4D |
| W₂, b₂ (FFN) | 4D × D + D |
| LayerNorm 2 | 2D |
| **Total per block** | **~8D² + 8D** ≈ **8D²** for large D |

For `N` blocks, total transformer body parameters ≈ `8ND²`.

GPT-3: `N=96`, `D=12288` → `8 × 96 × 12288² ≈ 116B` parameters (plus embeddings ≈ 175B total).

---

## Design Decisions Summarized

| Decision | Reason |
|----------|--------|
| Residual connections | Enable gradient flow through 96+ layers |
| Layer Normalization | Stable activation distributions; works at inference batch=1 |
| Pre-LN over Post-LN | More stable training at extreme depth |
| RMSNorm | Cheaper, empirically equivalent to LayerNorm |
| 4× FFN expansion | More expressive per layer; most parameters stored here |
| GELU/SwiGLU over ReLU | Smoother gradients, better empirical performance |
| Fixed block shape (d_model in/out) | Enables depth stacking without adapters |

---

*Previous: [02 — The Attention Mechanism](./02_Attention_Mechanism.md)*
*Next: [04 — Training & Backpropagation](./04_Training_and_Backpropagation.md)*
