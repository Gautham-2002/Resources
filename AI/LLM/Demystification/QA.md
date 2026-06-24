# Q&A — Demystifying LLMs
### Running log of questions and detailed answers

---

## Q1 — Does the vocabulary of 50,257 contain proper nouns like city names, famous persons, etc.?

**Short answer:** Yes, but not always as complete words — often as subword pieces.

The GPT-2 vocabulary of 50,257 entries was built by running **Byte Pair Encoding (BPE)** over a large corpus of internet text. The algorithm starts with individual bytes (256 entries) and repeatedly merges the most frequent adjacent pairs until it reaches the target vocabulary size. So the vocabulary contains:

- **Common whole words:** `"the"`, `"is"`, `"France"`, `"Paris"`, `"London"` — if they appeared frequently enough as a unit, they get their own entry.
- **Subword pieces of rare words:** A less common city like `"Naypyidaw"` (Myanmar's capital) might be split as `["Na", "yp", "yi", "daw"]` — four tokens. A famous person like `"Schwarzenegger"` might be `["Sch", "war", "zen", "eg", "ger"]`.
- **Common name fragments:** Prefixes and suffixes that appear in many names end up in the vocabulary — `" Mr"`, `" Mrs"`, `"son"`, `"berg"`, `"stein"`, etc.

**The key insight:** The vocabulary doesn't need one entry per name. It can represent *any* string of UTF-8 text (however rare) by falling back to smaller pieces, down to individual bytes if needed. No word is unrepresentable — it just costs more tokens to encode rare strings.

**A concrete example:**
```
"Paris"        →  1 token  (ID: 6342)
"Naypyidaw"    →  4 tokens (it's rare)
"Barack Obama" →  3 tokens ["Barack", " Obama"] → ["Bar", "ack", " Obama"]
" Schwarzeneg" →  multiple pieces
```

The model learns to reason about meaning by composing these subword pieces. After enough training, it understands that `"Sch" + "war" + "zen" + "eg" + "ger"` refers to the same entity as descriptions of the Austrian actor.

---

## Q2 — What does the positional encoding matrix mean? Why are you adding only `PE[0:5]`? What if my input is longer than 1024 tokens?

### Part A: What is the Positional Encoding matrix?

When you feed tokens into the model, the embedding lookup gives each token a 768-dimensional vector encoding *what* that token is. But there's a problem: attention is a **set operation** by nature — it has no built-in sense of order. The tokens `"dog bites man"` and `"man bites dog"` would produce identical attention scores if we didn't mark positions.

The fix: add a **position-specific signal** to each token's vector.

GPT-2 uses a **learned** positional encoding matrix `PE ∈ ℝ^(1024 × 768)`. Think of it as a second embedding table, but indexed by position rather than by token ID:

```
PE:
  Row 0   → 768-dim vector that says "I am at position 0"
  Row 1   → 768-dim vector that says "I am at position 1"
  Row 2   → 768-dim vector that says "I am at position 2"
  ...
  Row 1023 → 768-dim vector that says "I am at position 1023"
```

These 768-dimensional position vectors are **learned from training** — the model discovered, via gradient descent, which patterns in those 768 numbers were useful for encoding order. They are not hand-crafted sinusoids (that's what original "Attention is All You Need" used — GPT-2 learned its own).

### Part B: Why `PE[0:5]`?

Our input sentence `"The capital of France is"` has 5 tokens at positions 0, 1, 2, 3, 4.

```
Token         Position   PE Row Used
─────────────────────────────────────
"The"         0          PE[0]
" capital"    1          PE[1]
" of"         2          PE[2]
" France"     3          PE[3]
" is"         4          PE[4]
```

We take rows 0 through 4 from `PE` — that's `PE[0:5]` in Python slice notation — and **add** them element-wise to the token embeddings:

```
X₀ = X_embed + PE[0:5]    ∈ ℝ^(5 × 768)

X₀[0] = embedding("The")     + PE[0]   ← "The" at position 0
X₀[1] = embedding(" capital") + PE[1]   ← " capital" at position 1
X₀[2] = embedding(" of")     + PE[2]   ← " of" at position 2
X₀[3] = embedding(" France") + PE[3]   ← " France" at position 3
X₀[4] = embedding(" is")     + PE[4]   ← " is" at position 4
```

The shape stays `(5 × 768)`. The addition superimposes two signals in the same vector:
- Dimensions that encode **what** the token is (from `X_embed`)
- Dimensions that encode **where** the token sits (from `PE`)

The model doesn't analytically separate them — it learned during training to use the combined signal correctly.

### Part C: What happens if input > 1024 tokens?

GPT-2's `PE` matrix only has 1024 rows. If you try to input 1025 tokens, **there is no PE[1024]** — you've exceeded the model's **context window**.

What happens in practice:

| Scenario | Result |
|---|---|
| Input ≤ 1024 tokens | Works perfectly |
| Input > 1024 tokens (naively) | Index out of bounds error |
| Input > 1024 tokens (with truncation) | Model silently drops tokens beyond position 1023 |

Most serving frameworks truncate from the **left** — keeping the most recent 1024 tokens — because for generation, recency usually matters more.

**This is why newer models expanded their context:**
- GPT-2: 1,024 tokens
- GPT-3: 2,048 tokens
- GPT-4: up to 128,000 tokens (uses different techniques like RoPE to extend context without blowing up the PE matrix size)

The fundamental fix is to use positional encoding schemes that **generalize beyond their training length** (like Rotary Position Embeddings / RoPE), rather than a fixed learned table that caps out at a hard limit.

---

## Q3 — How is softmax calculated? How did the attention percentages come from the score matrix? What can I understand from it?

### Part A: How softmax works — the math

Softmax takes a row of raw scores and converts them to probabilities that sum to 1.

The formula for a row of scores `[s₁, s₂, ..., sₙ]`:

```
softmax(sᵢ) = exp(sᵢ) / Σ exp(sⱼ)  for all j
```

`exp(x)` means e^x (Euler's number ≈ 2.718 raised to the power x).

**Why exp?**
- It's always positive (can't have negative probabilities)
- It preserves ordering (higher score → higher probability)
- It **amplifies differences** — a score of 6 vs 5 leads to a much larger ratio than 2 vs 1

### Part B: Step-by-step for the `" is"` row

From the score matrix, the `" is"` row (after masking and scaling) is:

```
" is" row scores:  [1.8,  4.6,  0.3,  5.9,  4.1]
                    "The" "cap" "of"  "Fr"  "is"
```

**Step 1: Compute exp of each score**
```
exp(1.8) =  6.05
exp(4.6) = 99.48
exp(0.3) =  1.35
exp(5.9) = 365.04
exp(4.1) = 60.34
```

**Step 2: Sum all the exp values**
```
Total = 6.05 + 99.48 + 1.35 + 365.04 + 60.34 = 532.26
```

**Step 3: Divide each by the total**
```
"The"     → 6.05   / 532.26 = 0.0114  →  ~1%
" capital"→ 99.48  / 532.26 = 0.1869  → ~19%
" of"     → 1.35   / 532.26 = 0.0025  →  ~0%
" France" → 365.04 / 532.26 = 0.6859  → ~69%
" is"     → 60.34  / 532.26 = 0.1134  → ~11%
```

> **Note:** The document's example shows 4%, 48%, 2%, 42%, 4% — those come from a *different set of illustrative scores*, not exactly the matrix shown. Both are illustrative. The math process is identical.

**To get the document's output of 4%/48%/2%/42%/4%, the underlying scores would have been closer to:**
```
[1.8, 4.6, 0.3, 5.9, 4.1] → gives ~1%/19%/0%/69%/11%

For 4%/48%/2%/42%/4% you'd need scores like ≈ [1.5, 3.6, 0.5, 3.5, 1.5]
```
The exact numbers are illustrative in both cases — what matters is the pattern.

### Part C: What can you understand from the attention matrix?

```
         "The"  " cap"  " of"  " Fr"  " is"
"The" [   5.2   -∞      -∞     -∞     -∞   ]
" cap"[   1.3    4.8    -∞     -∞     -∞   ]
" of" [   0.9    3.2    5.1    -∞     -∞   ]
" Fr" [   2.1    1.5    0.7    6.3    -∞   ]
" is" [   1.8    4.6    0.3    5.9    4.1  ]
```

**Reading the matrix:**
- **Each row** = one token asking "who should I attend to?"
- **Each column** = one token being asked "are you relevant to me?"
- **`-∞`** = causal mask — token cannot look at future positions (becomes 0% after softmax)
- **The diagonal** (e.g., `5.2`, `4.8`, `5.1`, `6.3`, `4.1`) = how much a token attends to itself. High self-attention means the token's own representation is informative enough.

**What the high scores tell you (for this head):**
| Token | Attends strongly to | Interpretation |
|---|---|---|
| `"The"` | Only itself (only option) | Nothing to attend to yet |
| `" capital"` | Itself (4.8 >> 1.3) | Strong self-signal, doesn't need "The" much |
| `" of"` | Itself (5.1 >> others) | Preposition mostly attends to itself |
| `" France"` | Itself (6.3 >> others) | Proper noun is self-identifying |
| `" is"` | `" capital"` and `" France"` | **This is the interesting one** — the verb is looking for its subject context |

The `-∞` entries enforce **causal (left-to-right) generation**: when predicting token at position `i`, you can only condition on tokens at positions `0` to `i`. This prevents the model from "cheating" by looking at future tokens during both training and inference.

---

## Q4 — What is `W_O`? Does it get generated during training?

### What is `W_O`?

`W_O` is the **Output Projection Matrix** of the Multi-Head Attention layer. Its shape is `ℝ^(768 × 768)`.

Here's why it exists and what it does:

Recall that we split the 768 dimensions into 12 heads, each with 64 dimensions. Each head independently computes its own attention and produces its own 64-dimensional output. When all 12 heads are done, we concatenate their outputs:

```
head₁ output:  [64 numbers]
head₂ output:  [64 numbers]
head₃ output:  [64 numbers]
...
head₁₂ output: [64 numbers]
─────────────────────────────
Concatenated:  [768 numbers]  — just stacked, no mixing yet
```

The problem: these 768 numbers are **isolated outputs** from 12 separate computation streams. Head 3 might have tracked grammatical roles. Head 7 might have tracked coreference. They computed independently — they haven't been combined yet.

**`W_O` is the "mixer"** — a `768 × 768` learned matrix that takes this concatenated vector and combines information across all 12 heads into a unified 768-dimensional representation:

```
MHA_output = Concat(head₁, ..., head₁₂) · W_O    ∈ ℝ^(5 × 768)
```

Think of it as: each head votes separately, and `W_O` is the learned function that synthesizes all the votes into one decision.

### Does `W_O` get generated during training?

**Yes, absolutely.** `W_O` is one of the learned weight matrices — it's initialized randomly before training and updated via backpropagation throughout training.

In GPT-2 small (12 layers), the full parameter count from attention alone:
```
Per block:
  W_Q: 768 × 768 = 589,824 params
  W_K: 768 × 768 = 589,824 params
  W_V: 768 × 768 = 589,824 params
  W_O: 768 × 768 = 589,824 params
  ───────────────────────────────
  Per block: ~2.4M attention params

Across 12 blocks: ~28.3M attention params
```

During training:
1. A forward pass computes predictions
2. Cross-entropy loss measures surprise
3. Gradients flow backward through the entire computation graph
4. `W_O` receives its gradient and is updated by the optimizer (Adam)
5. Repeat for hundreds of billions of tokens

By the end of training, `W_O` has learned *exactly* which linear combinations of the 12 heads' outputs are useful for making good predictions.

---

## Q5 — Can you explain the embedding + positional encoding visually, like on a Cartesian plane? Show how adding shifts the point.

Think of each token's embedding as a **point in high-dimensional space**. We'll use 2D to visualize it (real embeddings are 768D — same logic, just more axes).

### Starting Point: Token Embeddings

Imagine these are the 2D coordinates (simplified from 768D) of our tokens:

```
2D Semantic Space (simplified):

    ^
  4 |         × " capital"
    |
  3 |                    × " France"
    |
  2 |   × "The"
    |
  1 |              × " of"
    |
  0 +────────────────────────────────>
    0    1    2    3    4    5    6
```

Two tokens can be "similar" in meaning if their points are close together.

### Positional Encoding as a Shift Vector

The positional encoding `PE[i]` for position `i` is a vector — a direction and magnitude of shift. When you **add** it to the embedding, you move the point:

```
New Position = Old Position + Shift Vector

X₀[i] = X_embed[i] + PE[i]
```

Visually (again, 2D simplification):

```
Before PE (embeddings only):        After adding PE (embeddings + position):

   ^                                    ^
 4 |    × " capital" (pos 1)          4 |         ×' " capital" (shifted right)
   |                                    |
 3 |             × " France" (pos 3)  3 |                  ×' " France" (shifted)
   |                                    |
 2 | × "The" (pos 0)                  2 |  ×' "The" (small shift, pos 0)
   |                                    |
 1 |         × " of" (pos 2)          1 |           ×' " of" (shifted)
   |                                    |
   +─────────────────>                  +─────────────────────────────>
```

### The Key Point: Same Word, Different Position = Different Point

If you repeated the word `"is"` twice in the sentence `"is it is"`:

```
"is" at position 0:   embedding("is") + PE[0]   → point A
"is" at position 2:   embedding("is") + PE[2]   → point B
```

Even though `embedding("is")` is **identical** for both (same token ID → same row in embedding matrix), `PE[0] ≠ PE[2]`, so the final points A and B are **different**. The transformer can now tell them apart and reason about their different roles.

### What the shift encodes

In 768D real space, the PE vectors encode subtle patterns across many dimensions. The model learned that:

- Small positions (early tokens) need certain shift patterns
- Large positions (late tokens) get different shifts
- The **difference** between `PE[3]` and `PE[2]` encodes "one step forward"

You don't need to interpret individual PE dimensions — the model learned what shifts make the downstream attention and FFN computations work correctly. The geometry is a learned artifact of training, not a human-designed coordinate system.

---

## Q6 — What is MLP, GELU, and the Feed-Forward Network? How do neurons fire and affect the next layer?

### 6a: What is an MLP?

**MLP = Multi-Layer Perceptron** — the classic neural network building block. It's just a sequence of:

```
Input → [Linear transformation] → [Non-linearity] → [Linear transformation] → Output
```

In the transformer's FFN (Feed-Forward Network), each token independently goes through this MLP. For a single token's 768-dimensional vector `x`:

```
Step 1:  hidden = GELU(x · W₁ + b₁)
           x:      768 dimensions
           W₁:     768 × 3072 matrix
           b₁:     3072-dimensional bias
           hidden: 3072 dimensions   ← EXPANSION

Step 2:  out = hidden · W₂ + b₂
           hidden: 3072 dimensions
           W₂:     3072 × 768 matrix
           b₂:     768-dimensional bias
           out:    768 dimensions    ← CONTRACTION
```

The network expands 768 → 3072 (4× wider), applies a non-linearity, then contracts back to 768.

### 6b: What is GELU?

**GELU = Gaussian Error Linear Unit** — a smooth activation function.

The purpose of any activation function (GELU, ReLU, tanh, etc.) is to introduce **non-linearity**. Without it, stacking linear layers accomplishes nothing — `Ax` followed by `Bx` is just `(BA)x`, which is still linear. You can collapse all linear layers into one. The network has no expressive power to learn curves or complex functions.

**ReLU** (simpler predecessor) works like: `max(0, x)` — it's zero for negative inputs, linear for positive.

**GELU** is smoother — it "softly" gates the input:

```
GELU(x) ≈ x · Φ(x)   where Φ is the cumulative standard normal distribution

Approximately:  GELU(x) ≈ 0.5 · x · (1 + tanh(√(2/π) · (x + 0.044715·x³)))
```

Visually:
```
        GELU curve:

   out ^
     2 |                      /
       |                    /
     1 |                  /
       |               /
     0 |──────────────────── (near-zero for very negative inputs)
       |          ↗ (smooth transition, not sharp like ReLU)
    -1 |
       +──────────────────────> x
       -3  -2  -1   0   1   2   3
```

GELU allows **small negative values to pass** (unlike ReLU which kills them entirely), and the transition is smooth (better gradients during training).

### 6c: Mental Model — Neurons Firing, Layer by Layer

Let's say we have a very simple FFN with `3 input neurons → 6 hidden neurons → 3 output neurons` (a tiny version of the real 768 → 3072 → 768):

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT LAYER         HIDDEN LAYER          OUTPUT LAYER     │
│  (3 neurons)         (6 neurons)           (3 neurons)      │
│                                                             │
│  x₁ = 0.8 ──┬────→  h₁ = GELU(w·x + b)  ┬──→  y₁         │
│              ├────→  h₂ = GELU(...)       ├──→  y₂         │
│  x₂ = 0.2 ──┤────→  h₃ = GELU(...)       ├──→  y₃         │
│              ├────→  h₄ = GELU(...)       │                 │
│  x₃ = 0.9 ──┴────→  h₅ = GELU(...)       │                 │
│                     h₆ = GELU(...)   ─────┘                 │
│                                                             │
│  Every input connects to EVERY hidden neuron.               │
│  Every hidden neuron connects to EVERY output neuron.       │
└─────────────────────────────────────────────────────────────┘
```

**How each neuron fires:**

1. **Each hidden neuron** `hᵢ` receives a **weighted sum** of all input values:
   ```
   raw_hᵢ = w_{i,1}·x₁ + w_{i,2}·x₂ + w_{i,3}·x₃ + bᵢ
   ```
   Where `w_{i,j}` is the learned weight for the connection from input `j` to hidden neuron `i`.

2. **The GELU activation** decides how much of that signal to pass forward:
   ```
   hᵢ = GELU(raw_hᵢ)
   ```
   - If `raw_hᵢ` is large and positive → `hᵢ ≈ raw_hᵢ` (neuron fires strongly)
   - If `raw_hᵢ` is near zero → `hᵢ ≈ 0` (neuron barely fires)
   - If `raw_hᵢ` is very negative → `hᵢ ≈ 0` (neuron is "off")

3. **Each output neuron** `yₖ` is then a weighted sum of all hidden neuron outputs:
   ```
   yₖ = w_{k,1}·h₁ + w_{k,2}·h₂ + ... + w_{k,6}·h₆ + bₖ
   ```

### 6d: In the Real GPT-2 FFN (768 → 3072 → 768)

```
Token " is" enters: 
  x ∈ ℝ^768  (768 input "neurons" / features)
         │
         │  W₁ (768 × 3072): each of the 3072 hidden neurons
         │  is connected to all 768 input features
         ▼
  raw_hidden = x · W₁ + b₁  ∈ ℝ^3072
         │
         │  GELU applied element-wise
         ▼
  hidden = GELU(raw_hidden)  ∈ ℝ^3072
  
  ← Now each of 3072 neurons is either firing (positive) or quiet (near 0)
  ← THESE are the "neurons" that encode factual knowledge
  ← When " France" + " capital" appear in the context, specific neurons
     here fire strongly — neurons that, during training, were activated
     by this exact pattern and pushed the output toward "Paris"
         │
         │  W₂ (3072 × 768): contract back
         ▼
  out = hidden · W₂ + b₂  ∈ ℝ^768
```

### 6e: The Factual Knowledge Claim — Visualized

The research claim in the document (`L247`) is this:

```
Before FFN (" is" vector after attention):
  " is" now "knows" about " capital" and " France" (from attention)
  But it hasn't yet resolved WHAT the answer is

Inside FFN hidden layer (3072 neurons):
  Neuron  #142:  fires at 0.91   ← activated by "capital of France" pattern
  Neuron  #567:  fires at 0.73   ← activated by "European capital" pattern
  Neuron  #2201: fires at 0.12   ← barely fires
  Neuron  #3001: fires at 0.88   ← activated by "is <city>" pattern
  ... (3072 neurons total)

These firing neurons, via W₂, push the output vector:
  out = (0.91 × W₂[142] + 0.73 × W₂[567] + 0.88 × W₂[3001] + ...)

After FFN + residual (" is" vector):
  The 768-dimensional vector has shifted in the direction of "Paris"
  When unembedded at the end, "Paris" now has the highest logit
```

Think of it like this: each neuron in the hidden layer is a **pattern detector**. During training, neuron #142 was repeatedly activated when the input contained a "capital of France" pattern. The weights `W₂[142]` (the 768 numbers in that neuron's output connections) were shaped during training to push the residual stream toward tokens that correctly follow that pattern — i.e., `"Paris"`.

This is why the FFN is called the **"key-value memory"** in some literature. The 3072 hidden neurons are like "keys" — patterns they recognize. The output weights `W₂` are the "values" — what they contribute to the stream when they fire.

### 6f: The Full Picture — 12 Layers of This

```
Layer 1 FFN:  Handles low-level patterns (word endings, punctuation, basic syntax)
Layer 2 FFN:  Builds on layer 1, starts recognizing simple phrases
Layer 3 FFN:  Recognizes grammatical constructs
...
Layer 8 FFN:  Recognizes entity types ("France" = country, "capital" = city)
Layer 9 FFN:  Starts activating knowledge neurons for country-capital pairs
Layer 10 FFN: Resolves the specific pairing (France → Paris)
Layer 11 FFN: Refines the prediction
Layer 12 FFN: Final refinement before unembedding
```

(The exact distribution varies — this is a conceptual model, not measured fact.)

The reason you need 12 layers rather than 1 huge FFN is that the **reasoning is compositional** — later layers can use the refined representations from earlier layers to make higher-level inferences. One layer can only compute one "step" of reasoning. Depth gives the network more "thinking steps."

---

*This file will be updated with new questions as they arise.*
*Cross-reference with the numbered documents (01–07) for deep mathematical detail.*
