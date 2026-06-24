# Demystifying Large Language Models
### A Principal Engineer's Field Guide

> **Audience:** Software Engineers transitioning into AI Systems.  
> **Philosophy:** No hand-wavy analogies. Every design decision traced back to linear algebra, calculus, or systems engineering.

---

## Table of Contents

| # | Document | Core Topics |
|---|----------|-------------|
| 0 | [Math & Conceptual Foundations](./00_Math_Foundations.md) | Tensors, matrix multiplication, dot product, gradients, probability, normalization |
| 1 | [Tokenization & Embeddings](./01_Tokenization_and_Embeddings.md) | BPE, vocabulary construction, embedding matrices, positional encoding |
| 2 | [The Attention Mechanism](./02_Attention_Mechanism.md) | Q/K/V projections, scaled dot-product attention, causal masking |
| 3 | [The Transformer Block](./03_Transformer_Block.md) | Multi-Head Attention, Layer Norm, FFN, residual connections |
| 4 | [Training & Backpropagation](./04_Training_and_Backpropagation.md) | Cross-entropy loss, next-token prediction, gradient flow, optimizers |
| 5 | [Architectural Patterns](./05_Architectural_Patterns.md) | Decoder-only (GPT), Encoder-Decoder (T5), when to use each |
| 6 | [Inference & Sampling](./06_Inference_and_Sampling.md) | Softmax, temperature, Top-K, Top-P (nucleus), KV cache |
| 7 | [The Story: End-to-End](./07_The_Story_End_to_End.md) | Narrative trace of `"The capital of France is"` → `" Paris"` through every layer |

---

## How to Read This Series

These documents are **ordered by data flow** — the same order in which a token travels through the system at training and inference time:

```
Raw Text
   │
   ▼
[01] Tokenizer → integer token IDs
   │
   ▼
[01] Embedding Layer → continuous vectors ∈ ℝ^d_model
   │
   ▼
[02–03] N × Transformer Blocks (Attention + FFN)
   │
   ▼
[06] Linear Projection + Softmax → probability distribution over vocabulary
   │
   ├─── [04] Training: compute loss, backpropagate, update weights
   └─── [06] Inference: sample next token, autoregress
```

Each document is self-contained but references others where relevant.

---

## Notation Conventions Used Throughout

| Symbol | Meaning |
|--------|---------|
| `B` | Batch size |
| `T` | Sequence length (number of tokens) |
| `d_model` | Model hidden dimension (e.g., 768 for GPT-2 base) |
| `d_k`, `d_v` | Per-head key/value dimension |
| `H` | Number of attention heads |
| `V` | Vocabulary size |
| `N` | Number of transformer layers (depth) |
| `W_*` | Learned weight matrix |
| `⊕` | Element-wise addition (residual) |
| `‖·‖` | L2 norm |

---

## Quick Reference: Key Equations

```
Attention(Q, K, V) = softmax( QKᵀ / √d_k ) · V

LayerNorm(x) = γ · (x - μ) / √(σ² + ε) + β

FFN(x) = max(0, xW₁ + b₁)W₂ + b₂     [or GELU variant]

Loss = -∑ log P(token_t | token_{<t})   [Cross-Entropy, teacher-forced]

P(x) = softmax(z / τ)                   [Temperature-scaled logits]
```

---

*Generated: April 2026 | Series: Demystifying LLMs*
