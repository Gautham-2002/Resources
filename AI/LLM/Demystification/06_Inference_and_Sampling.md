# 06 — Inference & Sampling
### From Logits to Generated Text: Softmax, Temperature, and Sampling Strategies

> **Key insight:** The model outputs a probability distribution over the vocabulary at each step. How you *sample* from that distribution is a critical engineering decision that controls the creativity-coherence tradeoff. The math is simple; the implications are profound.

---

## Part 1 — The Inference Forward Pass

At inference time, the model generates text **autoregressively** — one token at a time, feeding each generated token back as input for the next step.

### Single Step

Given a prompt of `T` tokens, the forward pass produces:

```
X_N ∈ ℝ^(T × d_model)    (final transformer layer output)
```

We only care about the **last position**:

```
h_T = X_N[T-1]   ∈ ℝ^d_model
```

This is projected to vocabulary logits via the **unembedding matrix** (often weight-tied to the input embedding `E`):

```
logits = h_T · Eᵀ   ∈ ℝ^V
```

The logit `logits[v]` is the unnormalized score for token `v` being the next token.

---

## Part 2 — Softmax: Converting Logits to Probabilities

```
P(v) = softmax(logits)[v] = exp(logits[v]) / Σⱼ exp(logits[j])
```

Properties:
- `P(v) ∈ (0, 1)` for all `v` (never exactly 0 or 1)
- `Σᵥ P(v) = 1` (valid probability distribution)
- **Monotone:** higher logit → higher probability
- **Exponential amplification:** a logit difference of `Δ` → probability ratio of `exp(Δ)`

For example, if logit["Paris"] = 5.0 and logit["Berlin"] = 3.0:

```
P("Paris") / P("Berlin") = exp(5.0) / exp(3.0) = exp(2) ≈ 7.4
```

"Paris" is 7.4× more likely than "Berlin" given this logit gap.

### Numerical Stability

Naive softmax overflows for large logits. In practice:

```
softmax(z)ᵢ = exp(zᵢ - max(z)) / Σⱼ exp(zⱼ - max(z))
```

Subtracting `max(z)` doesn't change the output (the max cancels in numerator and denominator) but prevents `exp` overflow.

---

## Part 3 — Temperature Scaling

**Temperature `τ`** is a scalar applied to the logits before softmax:

```
P(v; τ) = softmax(logits / τ)[v] = exp(logits[v] / τ) / Σⱼ exp(logits[j] / τ)
```

Temperature controls the **sharpness** of the probability distribution:

### τ → 0 (Greedy)

```
logits / τ → ±∞
```

The distribution becomes a delta function — all probability mass on the highest-logit token:

```
P(argmax token) → 1.0
```

**Effect:** Deterministic, repetitive output. Always picks the statistically most likely next token. Good for factual extraction, bad for creativity.

### τ = 1.0 (Default)

The raw model distribution. This is what the model actually learned during training.

### τ > 1.0 (High Temperature)

Logits are compressed: `logits / τ` → smaller values → softer distribution.

```
τ = 2.0: logits compressed by 2×. Gap between tokens halved. Less contrast → more uniform.
τ → ∞: P(v) → 1/V for all v. Uniform random sampling.
```

**Effect:** More random, diverse, creative. Can produce incoherent text when too high.

### Visualization

```
Logits: ["cat"=3.0, "dog"=2.0, "table"=0.5, "the"=-1.0]

τ=0.5:  P ≈ [0.88,  0.12,  0.00, 0.00]   (very peaked — "cat" dominates)
τ=1.0:  P ≈ [0.62,  0.23,  0.10, 0.05]   (model's natural distribution)
τ=1.5:  P ≈ [0.47,  0.25,  0.19, 0.09]   (flatter — more diversity)
τ=3.0:  P ≈ [0.34,  0.28,  0.24, 0.14]   (nearly uniform — random)
```

**Typical values:** `τ = 0.7–0.9` for coherent, slightly creative text. `τ = 1.0` as baseline. `τ = 1.2–1.5` for creative writing.

---

## Part 4 — Top-K Sampling

Before sampling, restrict the distribution to the `K` highest-probability tokens:

```
Algorithm:
1. Sort tokens by logit (descending)
2. Keep top-K tokens; set logits of all others to -∞
3. Re-normalize (re-apply softmax)
4. Sample from the resulting K-way distribution
```

**Why Top-K?**
- Eliminates "tail" tokens (incoherent words, garbage) with probability too low to ever be good choices
- Keeps diversity within the coherent high-probability region

**The problem with fixed K:**
- When the model is very confident (sharp distribution), `K=50` might include tokens with probability ~1e-10 — effectively noise.
- When the model is genuinely uncertain (flat distribution), `K=50` might miss good alternatives.

---

## Part 5 — Top-P Sampling (Nucleus Sampling)

Holtzman et al. (2020) introduced **nucleus sampling** as a principled fix for Top-K's fixed-K problem.

Instead of fixing the number of tokens, fix the **cumulative probability mass**:

```
Algorithm:
1. Sort tokens by probability (descending): p(v₁) ≥ p(v₂) ≥ ... ≥ p(v_V)
2. Find the smallest set S such that: Σ_{v ∈ S} p(v) ≥ p_threshold
   (S is the "nucleus" — smallest set covering p_threshold probability)
3. Sample uniformly within S (re-normalized)
```

### Example

```
Sorted probabilities:
  "the":    0.40
  "a":      0.20
  "this":   0.15
  "any":    0.10
  "some":   0.08
  "an":     0.05
  ...rest:  0.02

With p=0.90:
  Cumulative: 0.40 → 0.60 → 0.75 → 0.85 → 0.93  ← crosses 0.90
  Nucleus = {"the", "a", "this", "any", "some"}   (5 tokens)

With p=0.90 but different distribution (uncertain model):
  "run":    0.05
  "go":     0.05
  "move":   0.04
  ...       all roughly equal
  Nucleus grows to 20+ tokens automatically
```

Top-P **adapts the vocabulary size** to the model's uncertainty. Confident predictions → small nucleus. Uncertain predictions → large nucleus. This is more principled than a fixed K.

**Typical values:** `p = 0.9–0.95`.

---

## Part 6 — Combining Temperature + Top-P

In practice, temperature and Top-P are applied together:

```
1. logits_scaled = logits / τ          (temperature scaling)
2. probs = softmax(logits_scaled)      (convert to probabilities)
3. Sort probs descending
4. Find nucleus (cumulative ≥ p)       (Top-P filter)
5. Re-normalize within nucleus
6. Sample                              (categorical distribution)
```

The combined effect:
- Temperature controls the *shape* of the distribution (how uniform)
- Top-P controls the *cutoff* (how many tokens are in play)

**Greedy decoding** (τ→0, or argmax) is equivalent to `Top-K=1` or `Top-P→0`.

---

## Part 7 — The KV Cache: Making Autoregression Efficient

### The Problem

At each generation step, we recompute the full forward pass over the entire sequence (prompt + all previously generated tokens). The attention computation for the `t`-th step processes a sequence of length `t`:

```
Step 1: forward pass over [t_1]           → O(1²) attention
Step 2: forward pass over [t_1, t_2]      → O(2²) attention
...
Step t: forward pass over [t_1, ..., t_t] → O(t²) attention

Total attention compute: O(T³) for T generation steps!
```

### The KV Cache Solution

Notice that in causal attention, when generating token `t+1`, the K and V vectors for all previous tokens `1 ... t` are **unchanged**. We only need to compute K and V for the new token `t+1`.

The **KV Cache** stores the K and V tensors from all previous steps:

```
KV_cache[layer][step] = {K: ..., V: ...}
```

At each new step, we:
1. Compute Q, K, V only for the **new token** (one row, not the full sequence)
2. Append new K and V to the cache
3. Compute attention: Q (1×d_k) against cached K (T×d_k) → O(T × d_k) not O(T² × d_k)

**Complexity with KV cache:**
```
Per step:    O(T × d_k × H × N)    (attention over all cache)
Total:       O(T² × d_k × H × N)   (sum over T steps)
```

Still O(T²) total, but now *sequential* — each step is O(T) rather than O(T²). Critical for low-latency streaming.

**Memory cost of KV cache:**

```
Per token, per layer: 2 × d_model × 2 bytes (BF16)
Total for T tokens, N layers: T × N × 4 × d_model bytes

LLaMA 3 70B (d_model=8192, N=80):
  Per 1K tokens: 1024 × 80 × 4 × 8192 ≈ 2.6 GB
  Per 128K context: 128 × 2.6 GB ≈ 333 GB  ← why long context is memory-intensive
```

Techniques like **GQA (Grouped Query Attention)** and **MQA (Multi-Query Attention)** reduce KV cache memory by sharing K and V across multiple heads.

---

## Part 8 — Beam Search vs. Sampling

### Greedy Decoding

```
token_t = argmax P(· | context)
```
Always picks the most probable token. Fast but myopic — locally optimal choices may lead to globally suboptimal sequences.

### Beam Search

Maintain `B` candidate sequences ("beams") at each step. At each step, expand all beams by all possible tokens, keep the top `B` by cumulative log-probability:

```
score(t_1, ..., t_k) = Σ log P(tᵢ | t_{<i})
```

**Example with B=2:**
```
Step 0: [""]
Step 1: ["the" (score=-0.5), "a" (score=-0.8)]
Step 2: ["the cat" (score=-1.2), "the dog" (score=-1.4)]
Step 3: ["the cat sat" (score=-1.9), "the cat ran" (score=-2.1)]
...
```

**Beam search issues for LLMs:**
- High-beam outputs tend to be generic, repetitive, and low-entropy
- The "text degeneration" problem: beam search finds "the the the the..." type optima
- Empirically, **sampling with nucleus sampling outperforms beam search** for open-ended generation (Holtzman et al., 2020)

**Beam search is still preferred for:** machine translation, structured output (JSON, code with rigid syntax), where correctness > diversity.

---

## Part 9 — Repetition Penalty

A practical fix for repetition in generation:

```
logits[v] = logits[v] / penalty    if v was already generated
           (penalty > 1.0, e.g., 1.1–1.3)
```

This down-weights tokens that have already appeared, discouraging exact repetition. A softer variant weights by *how recently* a token appeared.

---

## Part 10 — Full Inference Loop (Pseudocode)

```python
def generate(prompt_tokens, model, max_new_tokens=200,
             temperature=0.8, top_p=0.95):
    tokens = list(prompt_tokens)
    kv_cache = init_kv_cache(model.num_layers)

    for _ in range(max_new_tokens):
        # Forward pass (only last token if using KV cache)
        logits, kv_cache = model.forward(tokens[-1:], kv_cache)
        # logits: ∈ ℝ^V

        # Temperature scaling
        logits = logits / temperature

        # Convert to probabilities
        probs = softmax(logits)

        # Top-P filtering (nucleus sampling)
        sorted_probs, sorted_indices = sort(probs, descending=True)
        cumulative_probs = cumsum(sorted_probs)
        # Find cutoff where cumulative exceeds top_p
        cutoff_idx = first_index_where(cumulative_probs >= top_p)
        # Zero out everything after cutoff
        sorted_probs[cutoff_idx + 1:] = 0.0
        # Re-normalize
        sorted_probs /= sum(sorted_probs)

        # Sample
        next_token_idx = categorical_sample(sorted_probs)
        next_token = sorted_indices[next_token_idx]

        tokens.append(next_token)

        # Stop conditions
        if next_token == EOS_TOKEN:
            break

    return tokens[len(prompt_tokens):]  # return only generated tokens
```

---

## Design Decisions Summarized

| Decision | Reason |
|----------|--------|
| Softmax over logits | Differentiable probability normalization; exponential amplification of logit gaps |
| Temperature τ < 1 | More deterministic; good for factual tasks |
| Temperature τ > 1 | More diverse; good for creative tasks |
| Greedy (τ→0) | Deterministic, fast; suboptimal for open-ended generation |
| Top-K | Simple truncation; fixed nucleus size (brittle) |
| Top-P (nucleus) | Adaptive nucleus based on uncertainty; better than Top-K |
| Beam search | Better for constrained/structured generation; poor for open-ended |
| KV cache | O(T) per step instead of O(T²); essential for low-latency streaming |
| GQA/MQA | Reduce KV cache memory by sharing K,V across heads |
| Repetition penalty | Practical fix for degeneration; not principled but effective |

---

*Previous: [05 — Architectural Patterns](./05_Architectural_Patterns.md)*
*Back to: [README — Series Index](./README.md)*
