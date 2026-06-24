# 04 — Training & Backpropagation
### Loss Functions, Gradient Flow, and Updating Billions of Parameters

> **Key insight:** Training an LLM is the repeated application of one principle — *minimize surprise*. Every weight update makes the model slightly less surprised by the next token in the training data, measured by cross-entropy loss.

---

## Part 1 — The Training Objective: Next-Token Prediction

An LLM is trained as a **language model** — it learns the probability distribution:

```
P(token_t | token_1, token_2, ..., token_{t-1})
```

The training data is raw text. Given the sequence `[t_1, t_2, ..., t_T]`, we feed `[t_1, ..., t_{T-1}]` as input and ask the model to predict `[t_2, ..., t_T]` — each token predicts the next.

This is **self-supervised** — no human labeling required. The label for each position is simply the next token in the raw corpus.

---

## Part 2 — Cross-Entropy Loss

### Probability of the Correct Token

At each position `t`, the model outputs a probability distribution over the vocabulary `V`:

```
P(· | context) = softmax(Xₜ W_E^T)   ∈ ℝ^V
```

Where `W_E^T` is the transposed embedding matrix (used for unembedding in weight-tied models).

The **cross-entropy loss** at position `t`:

```
L_t = -log P(token_t | token_{<t})
```

This is the **negative log-likelihood** of the correct token. It equals:

```
L_t = -log( exp(logit_{token_t}) / Σⱼ exp(logit_j) )
   = log(Σⱼ exp(logit_j)) - logit_{token_t}
   = LogSumExp(logits) - logit_{correct token}
```

**Why negative log?**
- `P ∈ (0, 1)` → `log(P) ∈ (-∞, 0)` → `-log(P) ∈ (0, ∞)`
- When `P → 1` (certain of correct token): `L → 0` (no loss, no surprise)
- When `P → 0` (very wrong): `L → ∞` (maximum surprise)

### Sequence Loss

The total loss for one training sequence is the average over all positions:

```
L = -(1/T) Σ_{t=1}^{T} log P(token_t | token_{<t})
```

This is equivalent to the **negative log-likelihood of the sequence** under the model:

```
L = -log P(t_1, t_2, ..., t_T) / T
```

Dividing by `T` makes loss comparable across sequences of different length.

### Perplexity

A more intuitive metric derived from cross-entropy:

```
Perplexity = exp(L) = exp( -(1/T) Σ log P(tₜ | t_{<t}) )
```

Interpretation: the model is "as confused as if choosing uniformly among `PPL` options at each step."
- GPT-2 on WebText: PPL ≈ 18
- GPT-3 on Penn Treebank: PPL ≈ 20
- Random model with V=50K vocab: PPL = 50,000

---

## Part 3 — Teacher Forcing and Efficiency

During training, we use **teacher forcing**: always feed the *ground truth* token at each position, never the model's own predictions.

**Why:** Without teacher forcing, errors accumulate — a wrong prediction at step 3 corrupts steps 4, 5, 6... making the loss signal noisy and training slow.

**Combined with the causal mask**, this allows computing all `T` next-token predictions in a single forward pass:

```
Input:   [t_1, t_2, t_3, t_4]    (shifted right)
Targets: [t_2, t_3, t_4, t_5]    (shifted left / original)

One forward pass → T predictions → T cross-entropy losses → averaged
```

Training efficiency: for a batch of `B` sequences of length `T`, each forward pass produces `B × T` loss terms.

---

## Part 4 — Backpropagation Through the Transformer

### The Chain Rule at Scale

Backpropagation applies the chain rule of calculus to compute `∂L/∂θ` for every parameter `θ` in the model.

For a composition `L = l(fₙ(fₙ₋₁(...f₁(x))))`:

```
∂L/∂x = (∂L/∂fₙ) · Jₙ · Jₙ₋₁ · ... · J₁

where Jᵢ = ∂fᵢ/∂fᵢ₋₁  (Jacobian of layer i)
```

**Key gradient flows through the transformer:**

### Gradient Through Softmax + Cross-Entropy

The gradient of cross-entropy + softmax w.r.t. the logits has a beautifully clean form:

```
∂L/∂logit_j = P(j) - 1{j = correct token}
             = P(j) - y_j
```

Where `y` is the one-hot target. This is `(predicted - true)` — the residual. No special cases, no numerical instability.

### Gradient Through Attention

The attention mechanism gradient is more involved. The key term:

```
∂L/∂Q = (∂L/∂Output) · Vᵀ · ∂Softmax/∂(QKᵀ/√d_k) · (K/√d_k)
```

The Jacobian of softmax for a vector `s = softmax(z)`:

```
∂s/∂z = diag(s) - ssᵀ   ∈ ℝ^(T × T)
```

This is a rank-`(T-1)` matrix, enforcing that changes to logits don't alter the sum of attention weights (always 1).

### Gradient Through Residual Connections

For `x_out = F(x) + x`:

```
∂L/∂x = ∂L/∂x_out · (∂F/∂x + I)
```

The identity `I` guarantees the gradient has a direct path. Even if `∂F/∂x ≈ 0` (early training), `∂L/∂x ≈ ∂L/∂x_out` — gradient flows unchanged.

---

## Part 5 — Optimizers: Moving Through Billions of Dimensions

### Basic Gradient Descent

```
θ ← θ - η · ∂L/∂θ
```

Naive gradient descent doesn't work well at scale because:
- Learning rate `η` needs to be different per parameter
- Gradients are noisy (mini-batch estimates)
- Loss landscape has flat plateaus and sharp cliffs

### Adam Optimizer (Kingma & Ba, 2015)

Adam maintains two running statistics per parameter:

```
m_t = β₁ m_{t-1} + (1 - β₁) g_t        (1st moment: gradient mean)
v_t = β₂ v_{t-1} + (1 - β₂) g_t²       (2nd moment: gradient variance)
```

Bias-corrected estimates:

```
m̂_t = m_t / (1 - β₁ᵗ)
v̂_t = v_t / (1 - β₂ᵗ)
```

Parameter update:

```
θ_t = θ_{t-1} - η · m̂_t / (√v̂_t + ε)
```

**Interpretation:**
- `m̂_t` is the momentum term — smoothed gradient direction
- `1/√v̂_t` is the adaptive learning rate — divides by the RMS of recent gradients, so parameters with high gradient variance get a smaller effective step

**Typical hyperparameters:** `β₁=0.9, β₂=0.999, ε=1e-8, η=3e-4` (base), with warmup and cosine decay.

### AdamW: Adam + Weight Decay

Standard L2 regularization adds `λθ` to the gradient. In Adam, this interacts poorly with the adaptive denominator (weight decay gets rescaled per-parameter).

AdamW decouples weight decay from the gradient:

```
θ_t = θ_{t-1} · (1 - η λ) - η · m̂_t / (√v̂_t + ε)
```

The weight decay term `(1 - ηλ)` is applied directly, not through the adaptive scaling. This is the standard optimizer for modern LLMs.

**Memory cost:** Adam stores 2 extra tensors per parameter (m and v), tripling the memory of the parameters themselves. For a 70B model: 70B params × 2 bytes (bf16) × 3 = **420GB** just for optimizer states. This drives the need for distributed training.

---

## Part 6 — Training at Scale: The Engineering

### Mixed Precision Training

Forward pass and gradient computation in **BFloat16** (2 bytes) for speed.  
Optimizer states and master weights in **Float32** (4 bytes) for numerical stability.

Why BFloat16 over Float16? BFloat16 has the same exponent range as Float32 (wider range), just less mantissa precision. It handles the large activation variance in deep transformers without overflow.

### Gradient Accumulation

If global batch size = 4M tokens but GPU can only fit 512 tokens at once:

```
accumulation_steps = 4M / 512 = 8192
```

Accumulate gradients over 8192 micro-batches, then do one optimizer step. Effective batch size decoupled from hardware capacity.

### Gradient Clipping

To prevent instability from occasional large gradients ("loss spikes"):

```
if ‖∂L/∂θ‖₂ > clip_threshold:
    ∂L/∂θ ← ∂L/∂θ · (clip_threshold / ‖∂L/∂θ‖₂)
```

Typical threshold: 1.0. Clips the global gradient norm, not per-parameter.

### Learning Rate Schedule

**Warmup + Cosine Decay** (Chinchilla and beyond):

```
                     ┌── Warmup (linear) ──┬────── Cosine decay ──────────┐
Learning Rate:       0 ─────────► η_max    η_max ──────────────────► η_min
                     0  warmup_steps              max_steps
```

**Why warmup:** At initialization, gradients are noisy. A small LR at start prevents large destructive updates before the model finds a reasonable region of the loss landscape.

**Why cosine decay:** Empirically better than linear decay; smooth slowdown allows fine-grained fitting near convergence.

### The Chinchilla Scaling Law

Hoffman et al. (2022) showed that for a given compute budget `C` (in FLOPs):

```
Optimal model size:  N* ≈ C^0.5 / 20
Optimal token count: D* ≈ 20 × N

i.e., train on ~20 tokens per parameter
```

GPT-3 (175B params) was trained on 300B tokens (~1.7 tokens/param) — under-trained by Chinchilla standards.

LLaMA 1 (7B params) was trained on 1T tokens (~143 tokens/param) — intentionally over-trained for inference efficiency.

---

## Loss Curve Interpretation

```
Training loss curve (typical):

  ↑
L │ ██
  │   ████
  │       ██████
  │             ████████
  │                     ████████████████████ ← converging
  └──────────────────────────────────────────► steps
```

- **Initial steep drop:** Easy patterns learned first (common tokens, basic syntax)
- **Long gradual decline:** World knowledge, reasoning patterns — slower to generalize
- **Loss spikes:** Gradient instability; often correlates with "hard" batches (code, math)
- **Validation loss diverging from train loss:** Overfitting (rare at scale; usually limited by data)

---

## Design Decisions Summarized

| Decision | Reason |
|----------|--------|
| Cross-entropy loss | Directly optimizes log-probability; gradient = (predicted - true) |
| Teacher forcing | Avoids error accumulation; enables parallel training over full sequence |
| Adam optimizer | Adaptive per-parameter learning rates; handles noisy mini-batch gradients |
| AdamW (decoupled weight decay) | Correct L2 regularization with Adam's adaptive scaling |
| BFloat16 mixed precision | 2× speed, same exponent range as FP32 (no overflow) |
| Gradient clipping (norm 1.0) | Prevents catastrophic updates from gradient spikes |
| Warmup + cosine decay | Stable early training; smooth convergence |
| Chinchilla scaling | Optimal compute allocation between model size and data |

---

*Previous: [03 — The Transformer Block](./03_Transformer_Block.md)*
*Next: [05 — Architectural Patterns](./05_Architectural_Patterns.md)*
