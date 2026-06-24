# 01 — Tokenization & Embeddings
### How Raw Text Becomes Mathematics

> **Prerequisite concepts:** Unicode, vocabulary, one-hot encoding, matrix multiplication.  
> **Key insight:** A model cannot operate on characters or words directly. It requires a fixed-size, differentiable, dense numerical representation. Tokenization and embeddings solve these two problems in sequence.

---

## The Core Problem

Neural networks are differentiable functions that operate on real-valued tensors. Raw text is a sequence of Unicode code points — a discrete, variable-length, unbounded set. To bridge this gap, we need two transformations:

1. **Tokenization** — Map the infinite string space to a finite vocabulary of integer IDs.
2. **Embedding** — Map discrete integer IDs to continuous high-dimensional vectors on which we can compute gradients.

---

## Part 1 — Tokenization

### Why Not Characters?

You could tokenize at the character level. Every English character maps to one of ~100 ASCII values. Simple, lossless.

**Problems:**
- Long sequences: "Transformer" → 11 tokens. At 4096 context length, you model far fewer words than at subword level.
- Attention cost scales as **O(T²)** in the basic formulation. Doubling sequence length quadruples compute.
- No morphological compression: "run", "running", "runner" have no shared structure.

### Why Not Full Words?

A word-level tokenizer has a fixed vocabulary of, say, 50,000 words.

**Problems:**
- Out-of-vocabulary (OOV) problem: "ChatGPT", "decolonisation", proper nouns → `[UNK]`. Information is destroyed.
- Inflected forms: every conjugation and declension bloats the vocabulary.
- Languages like Finnish, Turkish, German (agglutinative/compound-forming) are intractable.

### The Solution: Byte Pair Encoding (BPE)

BPE is a **data-compression algorithm** repurposed for vocabulary construction. It was introduced by Sennrich et al. (2016) and is used by GPT-2, GPT-3, GPT-4, LLaMA, and most modern LLMs.

#### Algorithm: BPE Vocabulary Construction

**Input:** A large training corpus (raw text), target vocabulary size `V`.

**Step 0 — Pre-tokenization**  
Split the corpus into "words" using a deterministic rule (e.g., whitespace + punctuation). GPT-2 uses a regex that also keeps leading spaces attached to words (so `" the"` and `"the"` are distinct).

Each word is represented as a sequence of its **bytes** (not characters). This is the "Byte-level" BPE variant, which handles all Unicode without an OOV problem — every possible byte sequence is expressible.

```
Initial vocabulary: {0x00, 0x01, ..., 0xFF}  →  256 base tokens
```

**Step 1 — Count bigram frequencies**  
Scan the entire corpus and count how often every adjacent token pair appears.

```
Corpus (simplified, after splitting):
  "low low low lower lowest"
  
Token sequences:
  [l, o, w] [l, o, w] [l, o, w] [l, o, w, e, r] [l, o, w, e, s, t]

Bigram counts:
  (l, o) → 5
  (o, w) → 5
  (w, e) → 2
  (e, r) → 1
  (e, s) → 1
  ...
```

**Step 2 — Merge the most frequent pair**  
Take the most frequent bigram `(l, o)` → create new token `lo`. Replace all occurrences.

```
After merge 1:
  [lo, w] [lo, w] [lo, w] [lo, w, e, r] [lo, w, e, s, t]

New bigram counts:
  (lo, w) → 5   ← now most frequent
  (w, e)  → 2
  ...
```

**Step 3 — Repeat**  
Continue merging. Each iteration creates one new vocabulary entry.

```
Merge 2: (lo, w) → low
Merge 3: (low, e) → lowe
Merge 4: (lowe, r) → lower
...
```

**Termination:** Stop when vocabulary size reaches the target `V` (e.g., 50,257 for GPT-2).

**Why this is elegant:**
- Frequent subwords (common morphemes, words) get merged early → become single tokens.
- Rare sequences remain as byte sequences → zero OOV.
- The merge order is deterministic and reproducible. The resulting tokenizer is a pure lookup table (no model weights).

#### BPE at Inference Time (Encoding)

Given a new string, we apply the learned merge rules **in the same order they were learned**, greedily from highest priority to lowest.

```python
# Pseudocode for BPE encoding
def bpe_encode(text: str, merges: List[Tuple[str, str]]) -> List[int]:
    tokens = list(text.encode("utf-8"))  # start as bytes
    for (left, right) in merges:        # apply merges in learned order
        tokens = apply_merge(tokens, left, right)
    return [vocab[t] for t in tokens]   # map to integer IDs
```

The result is a sequence of integers: `[15496, 11, 995, 0]` for `"Hello, world!"`.

---

### Special Tokens

Beyond the subword vocabulary, every model adds control tokens:

| Token | Purpose |
|-------|---------|
| `<|endoftext|>` | Document boundary / EOS |
| `<pad>` | Padding to uniform batch length |
| `<bos>` | Beginning of sequence |
| `<eos>` | End of sequence |
| `[MASK]` | BERT-style masked language modeling |

These are **appended** to the vocabulary and initialized with random embeddings like any other token.

---

## Part 2 — Embeddings

### From Integers to Vectors

After tokenization, a sequence of text becomes a sequence of integers:

```
"The cat sat" → [464, 3797, 3332]   (example GPT-2 token IDs)
```

A neural network needs floating-point tensors. The naive approach is **one-hot encoding**:

```
Token 464 → [0, 0, ..., 1, ..., 0]   ∈ {0,1}^V
```

**Problems with one-hot:**
- Dimensionality: `V = 50,257` → each token is a 50K-dimensional sparse vector.
- All tokens are equidistant (cosine similarity = 0 for all pairs). The representation encodes no semantic structure.
- Not differentiable in a useful way — gradients are zero almost everywhere.

### The Embedding Matrix

Instead, we define a learned **embedding matrix**:

```
E ∈ ℝ^(V × d_model)
```

Each row `E[i]` is the learned dense vector for token `i`. Conceptually:

```
embed(token_id) = E[token_id]   ∈ ℝ^d_model
```

This is equivalent to `one_hot(token_id) @ E` — but implemented as a fast array lookup (O(1) per token, no actual multiplication).

For a sequence of `T` tokens, the output is:

```
X = E[token_ids]   ∈ ℝ^(T × d_model)
```

**Typical dimensions:**

| Model | V | d_model |
|-------|---|---------|
| GPT-2 Small | 50,257 | 768 |
| GPT-2 XL | 50,257 | 1,600 |
| GPT-3 175B | 50,257 | 12,288 |
| LLaMA 3 70B | 128,256 | 8,192 |

The embedding matrix `E` is **trained via backpropagation**. Its gradients are computed like any other weight matrix — during each forward pass, only the rows corresponding to tokens in the current batch receive gradient updates (sparse gradient).

### Why High-Dimensional Space?

High dimensionality allows the model to encode:

- **Semantic similarity**: words with similar meanings → nearby vectors.
- **Compositional relationships**: the famous `king - man + woman ≈ queen` (Word2Vec observation, amplified in modern embeddings).
- **Syntactic roles**: nouns, verbs, adjectives cluster in learnable subspaces.
- **Polysemy**: unlike Word2Vec's static embeddings, the transformer's contextual embeddings allow the same token to have different representations in different contexts (because the embedding is just the *input*; the transformer layers compute the context-sensitive representation).

The geometry of embedding space is **not hand-crafted** — it emerges entirely from the training objective (next-token prediction). The model discovers that encoding semantic relationships reduces its loss.

---

## Part 3 — Positional Encoding

The embedding lookup `E[token_ids]` is **permutation-invariant**. The sentences "dog bites man" and "man bites dog" would produce the same set of embedding vectors (in a different order), but the transformer's attention mechanism is itself set-based. It needs to know **position**.

### Sinusoidal Positional Encoding (Original Transformer)

Vaswani et al. (2017) proposed adding a **fixed, non-learned** positional signal:

```
PE(pos, 2i)   = sin(pos / 10000^(2i / d_model))
PE(pos, 2i+1) = cos(pos / 10000^(2i / d_model))
```

Where `pos` is the position index (0, 1, 2, ...) and `i` ranges over half the embedding dimensions.

**Why sinusoids?**
- **Uniqueness:** Every position gets a unique encoding vector.
- **Relative position expressibility:** `PE(pos + k)` can be expressed as a linear function of `PE(pos)` — this means the model can learn to attend based on *relative* distance.
- **Extrapolation:** The function is defined for any `pos`, including lengths longer than those seen during training.

The input to the first transformer layer is:

```
X₀ = E[token_ids] + PE   ∈ ℝ^(T × d_model)
```

### Learned Positional Embeddings (GPT-2, BERT)

A simpler alternative: define a second matrix:

```
P ∈ ℝ^(T_max × d_model)
```

Each row is the learned embedding for that position. Add to token embeddings:

```
X₀ = E[token_ids] + P[0:T]
```

**Trade-off:** Simpler to implement, but cannot generalize to sequences longer than `T_max` seen during training.

### Rotary Positional Embedding — RoPE (LLaMA, Mistral, GPT-NeoX)

RoPE is the current state-of-the-art approach. Instead of *adding* a positional signal to the embedding, it *rotates* the Query and Key vectors in the attention mechanism by position-dependent rotation matrices.

The key insight: dot products `qᵢ · kⱼ` become functions of the *relative position* `i - j`, not absolute positions `i` and `j` separately. This dramatically improves length generalization.

```
q̃ᵢ = R(i) · qᵢ    where R(i) is a block-diagonal rotation matrix parameterized by position i
k̃ⱼ = R(j) · kⱼ

q̃ᵢ · k̃ⱼ = qᵢᵀ R(i)ᵀ R(j) kⱼ = qᵢᵀ R(j - i) kⱼ   ← depends only on relative offset
```

RoPE requires no extra parameters and integrates naturally into the attention computation. We'll revisit this in [02 — The Attention Mechanism](./02_Attention_Mechanism.md).

---

## Data Flow Summary

```
Input:  "The transformer is powerful"
           │
           ▼
[Tokenizer / BPE]
           │
           ▼
token_ids: [464, 47741, 318, 3665]    shape: (T,) = (4,)
           │
           ▼
[Embedding Lookup: E ∈ ℝ^(V × d_model)]
           │
           ▼
X_embed:  ∈ ℝ^(4 × 768)              each row is d_model-dimensional
           │
           ▼
[+ Positional Encoding]
           │
           ▼
X₀:       ∈ ℝ^(4 × 768)              ← input to Transformer Block 1
```

---

## Key Design Decisions Summarized

| Decision | Engineering Reason |
|----------|--------------------|
| BPE over characters | Shorter sequences → O(T²) attention is cheaper |
| BPE over full words | Zero OOV, handles morphology and new words |
| Byte-level BPE | Handles all Unicode without special cases |
| Dense embeddings over one-hot | Semantic geometry, differentiable, compact |
| High d_model | More capacity to encode relationships; empirically better |
| Positional encoding added separately | Modularity; token identity and position are factored |
| RoPE over absolute PE | Better length generalization, relative position awareness |

---

*Next: [02 — The Attention Mechanism](./02_Attention_Mechanism.md)*
