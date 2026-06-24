# 07 — The Story: One Sentence Through the Entire Machine
### A Narrative Data Flow Trace from Raw Text to Generated Output

> **The example:** We will feed the sentence `"The capital of France is"` to an LLM and watch it generate the token `" Paris"`. Every number and shape shown is representative of a real GPT-2 small model (d_model=768, 12 heads, 12 layers, vocab=50,257).
>
> **Format:** This is a story. Follow the token. Everything that happens to it, and why, is told in sequence.

---

## Prologue: The Stage

Somewhere on a cluster of GPUs, a transformer model sits loaded in memory. Its 117 million parameters — 117 million floating-point numbers — are distributed across weight matrices in 12 transformer blocks. The model has been trained on hundreds of gigabytes of internet text. It has seen this pattern — `"The capital of France is _"` — or something very close to it, countless times.

We send it five words. It will return one.

Here is what happens.

---

## Act 1 — At the Gates: Tokenization

**Input:** The string `"The capital of France is"`

The string arrives at the tokenizer — a lookup table encoding the rules of Byte Pair Encoding learned during training. The tokenizer has no model weights. It is pure deterministic logic.

It scans the string and applies its merge rules, splitting the text into subword units and assigning each an integer ID from its vocabulary of 50,257 entries.

**Output — token IDs:**
```
"The"      →  464
" capital" →  3139
" of"      →  286
" France"  →  4881
" is"      →  318

token_ids = [464, 3139, 286, 4881, 318]   shape: (5,)
```

Five integers. The entire semantic content of our sentence — the concepts of capitals, nations, identity — is now reduced to five numbers. All context from the original string has been stripped except what those IDs encode.

This is the only irreversible step in the pipeline. Everything from here is learned and differentiable. The tokenizer is fixed.

---

## Act 2 — Finding Coordinates: The Embedding Lookup

The five token IDs arrive at the **embedding matrix** `E ∈ ℝ^(50257 × 768)`. This matrix has been learned during training — 50,257 rows, one per vocabulary entry, each a 768-dimensional vector.

The model does a simple lookup: take rows 464, 3139, 286, 4881, 318 from this matrix.

What emerges is a 2D matrix:

```
X_embed ∈ ℝ^(5 × 768)
```

Five rows. Each row is a 768-dimensional vector — the model's learned "coordinates" for that token in semantic space. The row for `" France"` (ID 4881) sits near `" Germany"`, `" Italy"`, and `" Europe"` in this 768-dimensional space. The row for `" capital"` sits near `" city"`, `" center"`, `" seat"`.

These vectors didn't come from any dictionary. They emerged because, during training, tokens that appeared in similar contexts ended up with similar learned coordinates — the loss function punished surprise, and the embedding matrix adjusted to minimize it.

But these vectors don't yet know where in the sequence each token sits. The word `"France"` at position 4 doesn't know it comes after `"of"` at position 3.

---

## Act 3 — Marking Position: Positional Encoding

A second lookup. The model has a **positional encoding** matrix `PE ∈ ℝ^(1024 × 768)` — one vector per possible position, also learned during training.

The model reads off rows 0, 1, 2, 3, 4 from this matrix and **adds** them element-wise to the token embeddings:

```
X₀ = X_embed + PE[0:5]    ∈ ℝ^(5 × 768)
```

Each token's 768-dimensional vector now contains two superimposed signals:
- What the token *is* (its semantic identity)
- *Where* it is in the sequence (its positional identity)

The model cannot distinguish these signals analytically. It doesn't need to. During training it learned to use this combined representation correctly. `X₀` is the input to the transformer.

The shape has not changed: `(5 × 768)`. We have 5 token vectors, each with 768 features.

---

## Act 4 — The First Transformer Block: Attention

`X₀` enters **Transformer Block 1** of 12. There are 12 identical-in-structure (but different-in-weights) blocks. Each passes its output to the next.

### Step 4a — Layer Normalization

Before anything else, the block normalizes its input:

```
X₀_norm = LayerNorm(X₀)    ∈ ℝ^(5 × 768)
```

For each of the 5 token vectors independently, the 768 values are rescaled to have approximately zero mean and unit variance, then shifted and scaled by two small learned vectors `γ` and `β`.

This keeps the numbers well-behaved — neither exploding to thousands nor collapsing to millionths — before the expensive attention computation begins.

### Step 4b — Computing Q, K, V

The normalized `X₀_norm` is multiplied by three learned weight matrices:

```
W_Q, W_K, W_V  each ∈ ℝ^(768 × 768)
```

```
Q = X₀_norm · W_Q    ∈ ℝ^(5 × 768)
K = X₀_norm · W_K    ∈ ℝ^(5 × 768)
V = X₀_norm · W_V    ∈ ℝ^(5 × 768)
```

Three separate matrices, each `(5 × 768)`. These are the Queries, Keys, and Values.

Think of it this way: each token now has three different "faces":
- Its **query face** — the question it's asking of the rest of the sequence
- Its **key face** — the advertisement it broadcasts to other tokens' queries
- Its **value face** — the actual information it contributes if selected

The token `" is"` (position 4) is asking its query: *"What am I looking for to understand what comes before me?"* Its key is saying: *"Here's what I am, in case others need me."* Its value is ready to contribute if called upon.

### Step 4c — Multi-Head Split

The 768 dimensions are split into **12 heads**, each with `768/12 = 64` dimensions. We now have 12 separate Q, K, V triplets, each `(5 × 64)`.

Each head will independently compute its own attention pattern. Some heads will learn to track grammatical roles. Some will track semantic relationships. Some will simply attend to nearby tokens. None of this is hand-programmed — the specialization emerged from training.

### Step 4d — The Attention Score Matrix

**Focus on one head.** Within this head:

```
Q_h ∈ ℝ^(5 × 64)
K_h ∈ ℝ^(5 × 64)
```

We compute **all pairwise similarity scores** simultaneously:

```
Scores = Q_h · K_hᵀ    ∈ ℝ^(5 × 5)
```

A `5×5` matrix where entry `[i, j]` is the dot product of token `i`'s query with token `j`'s key — a number representing how much token `i` wants to "attend to" token `j`.

Before softmax, we **scale** all scores by `1/√64 = 1/8`. This prevents large values from causing softmax to produce near-zero gradients.

Then we apply the **causal mask**: for a decoder-only model generating left-to-right, token `i` is forbidden from attending to any token `j > i` — it cannot look into the future. Future positions are set to `-∞`.

The masked, scaled score matrix for our 5-token sequence looks structurally like:

```
         "The"  " cap"  " of"  " Fr"  " is"
"The" [   5.2   -∞      -∞     -∞     -∞   ]
" cap"[   1.3    4.8    -∞     -∞     -∞   ]
" of" [   0.9    3.2    5.1    -∞     -∞   ]
" Fr" [   2.1    1.5    0.7    6.3    -∞   ]
" is" [   1.8    4.6    0.3    5.9    4.1  ]
```

*(These numbers are illustrative, not exact.)*

### Step 4e — Softmax: Turning Scores into Weights

Softmax is applied **row by row** — each token's row of scores becomes a probability distribution over the tokens it can see:

```
A_h = softmax(Scores)    ∈ ℝ^(5 × 5)
```

Row `" is"` might look like:

```
" is" attends to:
  "The"    →  4%
  " capital" → 48%
  " of"    →  2%
  " France" → 42%
  " is"    →  4%
```

The token `" is"` is strongly attending to both `" capital"` and `" France"`. This makes sense — to complete `"The capital of France is ___"`, the most informative context is what capital and what country we're talking about. The attention mechanism has learned this from training.

### Step 4f — Weighted Sum of Values

```
head_output = A_h · V_h    ∈ ℝ^(5 × 64)
```

The output for the `" is"` position is a weighted blend of the value vectors of all 5 tokens, weighted by the attention distribution computed above. The result is a new `64`-dimensional vector for `" is"` that now "contains" information about `" capital"` and `" France"` — gathered from across the sequence.

### Step 4g — Recombine Heads

All 12 heads run in parallel and produce their outputs independently. Their `64`-dimensional outputs are concatenated:

```
Concat(head₁, ..., head₁₂)    ∈ ℝ^(5 × 768)
```

This is then multiplied by the output projection matrix `W_O ∈ ℝ^(768 × 768)`, mixing information across heads:

```
MHA_output = Concat(...) · W_O    ∈ ℝ^(5 × 768)
```

### Step 4h — Residual Connection

We add the Multi-Head Attention output back to the **original input** (before the layer norm):

```
X₁ = X₀ + MHA_output    ∈ ℝ^(5 × 768)
```

The residual connection is a gradient highway. During training, gradients can flow directly through this `+ X₀` path without passing through any weights, allowing early layers to receive useful gradient signal even in a 12-layer network.

At this point, `" is"` carries richer information — it now "knows" about `" capital"` and `" France"` in its 768-dimensional vector.

---

## Act 5 — The FFN: Per-Token Processing

Still inside Block 1.

### Step 5a — Layer Normalization (Again)

```
X₁_norm = LayerNorm(X₁)    ∈ ℝ^(5 × 768)
```

### Step 5b — The Feed-Forward Network

Unlike attention, the FFN operates on **each token independently** — no information crosses between positions here.

For each token's 768-dimensional vector, a 2-layer MLP is applied:

```
hidden = GELU(X₁_norm · W₁ + b₁)    W₁ ∈ ℝ^(768 × 3072)
                                      hidden: ∈ ℝ^(5 × 3072)

FFN_out = hidden · W₂ + b₂           W₂ ∈ ℝ^(3072 × 768)
                                      FFN_out: ∈ ℝ^(5 × 768)
```

The vector expands from 768 → 3072 dimensions, passes through a non-linearity (GELU), then contracts back to 768. This expansion allows the model to compute complex, non-linear functions of each token's representation.

Research suggests that this FFN layer is where *factual knowledge* lives. The pattern `" France" + " capital"` activating certain neurons, which in turn push the representation of `" is"` toward `"Paris"`, is a plausible mechanistic account of how stored knowledge gets retrieved.

### Step 5c — Residual Connection

```
X₂ = X₁ + FFN_out    ∈ ℝ^(5 × 768)
```

**Block 1 is complete.** `X₂ ∈ ℝ^(5 × 768)` — 5 enriched token vectors, each having "read" context from the rest of the sequence and had its representations refined by the FFN.

---

## Act 6 — Through the Depths: Blocks 2 through 12

`X₂` flows into Block 2, which performs the identical sequence of operations — Layer Norm, Multi-Head Attention, Residual, Layer Norm, FFN, Residual — but with its own completely independent set of learned weights.

Then Block 3. Then Block 4. Through all 12 blocks.

Each block:
- Refines its understanding of the relationships between tokens
- Accumulates more context into each token's representation
- Adds its contribution to the residual stream

Earlier blocks tend to capture local, syntactic patterns — word order, punctuation, morphology. Later blocks build more abstract, semantic representations — the meaning of phrases, long-range coreference, logical relationships.

By the time we exit Block 12, the token `" is"` at position 4 has been processed by 12 rounds of contextual attention and FFN refinement. Its 768-dimensional vector is no longer just "the word is" — it is a rich, context-dependent representation that encodes the entire semantic context: *"this is a completion of a statement about what France's capital is."*

The output of Block 12:

```
X_final ∈ ℝ^(5 × 768)
```

---

## Act 7 — The Final Judgment: Predicting the Next Token

We only care about the **last token's** representation — `" is"` at position 4 — because the model predicts what comes *after* the last token.

```
h = X_final[4]    ∈ ℝ^(768,)
```

This single 768-dimensional vector is the model's entire compressed understanding of `"The capital of France is"`.

### Step 7a — Final Layer Normalization

```
h_norm = LayerNorm(h)    ∈ ℝ^(768,)
```

### Step 7b — Unembedding: Back to Vocabulary Space

The model multiplies by the **unembedding matrix** — which in GPT-2 is the *transposed embedding matrix* (tied weights):

```
logits = h_norm · Eᵀ    ∈ ℝ^(50257,)
```

We arrive at a vector of 50,257 raw scores — one per vocabulary token. Each number represents how strongly the model, given this entire context, believes that token should come next.

The logit for `" Paris"` is very high. The logit for `" Berlin"` is lower but notable. `" London"` appears. `" Rome"`. `" pizza"` has a very low logit. `" elephant"` is near the bottom of the distribution.

The model has not been explicitly told that `" Paris"` is the capital of France. It has *learned*, from training on millions of documents, that this exact context pattern strongly predicts `" Paris"` next. The logit distribution is the encoded result of all that learning.

### Step 7c — Softmax: Converting to Probabilities

```
P = softmax(logits / τ)    ∈ ℝ^(50257,)    where τ is temperature (e.g., 0.8)
```

The 50,257 raw scores are transformed into a valid probability distribution. Dividing by temperature `τ = 0.8` sharpens the distribution slightly — making the model more confident in its top choices.

Perhaps the distribution looks like:

```
" Paris"      →  78.3%
" Lyon"       →   4.1%
" Marseille"  →   3.2%
" Bordeaux"   →   1.8%
" the"        →   1.2%
" its"        →   0.9%
...all others →  10.5% (spread across 50,251 tokens)
```

### Step 7d — Nucleus Sampling

With `top_p = 0.92`, we find the smallest set of tokens whose cumulative probability exceeds 92%:

```
" Paris"     → cumulative: 78.3%
" Lyon"      → cumulative: 82.4%
" Marseille" → cumulative: 85.6%
" Bordeaux"  → cumulative: 87.4%
" the"       → cumulative: 88.6%
" its"       → cumulative: 89.5%
...          → ...until cumulative ≥ 92%
```

The nucleus — say, the top 12 tokens covering 92% probability — has their probabilities re-normalized. Everything outside the nucleus is discarded.

We sample from this nucleus. A random draw from the resulting distribution.

**The drawn token: `" Paris"`**

---

## Act 8 — The Loop: Autoregression

The sampled token `" Paris"` (ID: 6342) is appended to the input:

```
New input: [464, 3139, 286, 4881, 318, 6342]
           "The  capital  of   France  is   Paris"
```

The entire forward pass runs again, now over 6 tokens. The KV cache from the previous step is reused — we don't recompute Keys and Values for positions 0-4, only for the new token at position 5.

The model predicts what comes after `"Paris"`. Perhaps `"."` with high probability. That gets sampled, appended, and the cycle repeats — until the model samples the End-of-Sequence token or a maximum length is reached.

**Final generated text:** `" Paris."`

---

## Epilogue: What Just Happened

Let's compress the entire journey:

```
"The capital of France is"
         │
         ▼ [Tokenizer]
[464, 3139, 286, 4881, 318]
         │
         ▼ [Embedding Lookup → E ∈ ℝ^(50257×768)]
X₀ ∈ ℝ^(5 × 768)    +   Positional Encoding
         │
         ▼ [Block 1: LN → MHA → Residual → LN → FFN → Residual]
X₂ ∈ ℝ^(5 × 768)
         │
         ▼ [Block 2 → Block 3 → ... → Block 12]
X_final ∈ ℝ^(5 × 768)
         │
         ▼ [Take last position's vector]
h ∈ ℝ^(768,)
         │
         ▼ [LN → Unembed: h · Eᵀ]
logits ∈ ℝ^(50257,)
         │
         ▼ [Softmax(logits / τ) + Nucleus Sampling]
next_token = " Paris"
         │
         ▼ [Append and repeat]
"The capital of France is Paris."
```

The model produced `" Paris"` not because it "knows" geography in any human sense. It produced it because, over the course of training, the pattern `"The capital of ___ is ___"` appeared in its training data many times, and the weight matrices in its 12 transformer blocks adjusted to make this pattern's continuation highly probable.

The "intelligence" is in the 117 million numbers — shaped by gradient descent over hundreds of gigabytes of human text, optimized to minimize surprise, one token at a time.

That is the ghost in the machine. Not a ghost at all. Just very well-organized arithmetic.

---

*This document traces the data flow described mechanically in the rest of the series.*
*For the detailed math at each step, see the corresponding numbered document.*

| Step in this story | Deep-dive document |
|-------------------|--------------------|
| Tokenization | [01 — Tokenization & Embeddings](./01_Tokenization_and_Embeddings.md) |
| Embeddings & Positional Encoding | [01 — Tokenization & Embeddings](./01_Tokenization_and_Embeddings.md) |
| Q, K, V and Attention | [02 — The Attention Mechanism](./02_Attention_Mechanism.md) |
| LayerNorm, FFN, Residuals | [03 — The Transformer Block](./03_Transformer_Block.md) |
| Loss & Training | [04 — Training & Backpropagation](./04_Training_and_Backpropagation.md) |
| Architecture Choices | [05 — Architectural Patterns](./05_Architectural_Patterns.md) |
| Softmax, Temperature, Nucleus | [06 — Inference & Sampling](./06_Inference_and_Sampling.md) |
