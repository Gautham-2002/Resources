# 05 — Architectural Patterns
### Decoder-Only vs. Encoder-Decoder: When to Use Each

> **Key insight:** The architecture is a statement about the task's information flow. Decoder-only models treat all text as a completion problem. Encoder-Decoder models explicitly separate understanding (encoding) from generation (decoding). The choice is a fundamental systems design decision.

---

## Overview of Transformer Architectures

The original Transformer (Vaswani et al., 2017) had both an encoder and a decoder. Since then, three major architectural families have emerged:

| Family | Examples | Core Mechanism |
|--------|----------|----------------|
| **Encoder-Only** | BERT, RoBERTa, DeBERTa | Bidirectional attention, no generation |
| **Decoder-Only** | GPT-2/3/4, LLaMA, Mistral, Claude | Causal (unidirectional) attention, autoregressive |
| **Encoder-Decoder** | T5, BART, mT5 | Encoder: bidirectional; Decoder: causal + cross-attention |

We focus on the two generative families: **Decoder-Only** and **Encoder-Decoder**.

---

## Part 1 — Decoder-Only Architecture (GPT Family)

### Structure

```
Input Tokens
     │
     ▼
[Token Embedding + Positional Encoding]
     │
     ▼
┌─────────────────────────┐
│  Transformer Block 1    │  ← Causal Self-Attention
│  Transformer Block 2    │  ← Causal Self-Attention
│      ...                │
│  Transformer Block N    │  ← Causal Self-Attention
└─────────────────────────┘
     │
     ▼
[Linear Unembedding + Softmax]
     │
     ▼
P(next token | all previous tokens)
```

**Key property:** Every layer uses **causal (masked) self-attention**. Token `t` can only attend to tokens `1, ..., t`. Information flows in one direction: left to right.

### The Unified Sequence Approach

Decoder-only models handle all tasks by formatting them as **text completion**:

```
Prompt:    "Translate to French: The cat sat on the mat. →"
Completion: "Le chat était assis sur le tapis."
```

```
Prompt:    "Q: What is the capital of France? A:"
Completion: "Paris"
```

This is the key insight behind GPT-3's in-context learning and instruction-tuned models: the model has one universal interface (text completion), and task formatting is just prompt engineering.

### Attention Pattern

```
Attention matrix for T=5 (■ = allowed, □ = masked):

Token:    t1   t2   t3   t4   t5
t1   [    ■    □    □    □    □  ]
t2   [    ■    ■    □    □    □  ]
t3   [    ■    ■    ■    □    □  ]
t4   [    ■    ■    ■    ■    □  ]
t5   [    ■    ■    ■    ■    ■  ]
```

Each token has full access to all preceding context. The context window (e.g., 128K tokens for LLaMA 3) defines the maximum lookback.

### Parameter Efficiency

For a given compute budget, decoder-only models use all parameters for generation. There's no "split" between encoder and decoder — the same weights process both the prompt and the generated continuation.

This is particularly efficient for **long-context generation** where the prompt is short and the output is long.

---

## Part 2 — Encoder-Decoder Architecture (T5 Family)

### Structure

```
Source Tokens                 Target Tokens (shifted right)
     │                               │
     ▼                               ▼
[Embedding + PE]            [Embedding + PE]
     │                               │
     ▼                               ▼
┌──────────────┐             ┌────────────────────┐
│  Encoder 1   │             │  Decoder Block 1   │
│  Encoder 2   │──────────►  │  Decoder Block 2   │
│    ...       │  Cross-Attn │       ...          │
│  Encoder N   │             │  Decoder Block N   │
└──────────────┘             └────────────────────┘
                                      │
                                      ▼
                             P(target token_t | source, target_{<t})
```

### The Three Attention Mechanisms

An encoder-decoder model uses three distinct attention patterns:

**1. Encoder Self-Attention (Bidirectional)**

```
Attention matrix (T=4, no mask):

Token:    s1   s2   s3   s4
s1   [    ■    ■    ■    ■  ]
s2   [    ■    ■    ■    ■  ]
s3   [    ■    ■    ■    ■  ]
s4   [    ■    ■    ■    ■  ]
```

Every source token can attend to every other source token. This is **bidirectional context** — token `s1` can "see" what comes after it. This produces the richest possible representation of the source sequence.

**2. Decoder Causal Self-Attention**

```
Target tokens: t1, t2, t3
                        (same lower-triangular causal mask as decoder-only)
```

Each generated token can only attend to previously generated tokens.

**3. Cross-Attention**

The decoder attends to the **encoder's output**. In each decoder block:

```
Q = decoder_state × W_Q         (from the decoder's current state)
K = encoder_output × W_K        (from the encoder's final representations)
V = encoder_output × W_V        (from the encoder's final representations)

cross_attn = softmax(Q Kᵀ / √d_k) · V
```

This is the information bridge: the decoder can attend to any encoder position at every decoder step. The encoder's bidirectional representation of the full source is available to every decoder token, at every decoding step.

### T5's Text-to-Text Framework

T5 (Raffel et al., 2019) rephrases all NLP tasks as text-to-text:

```
Task:         Sentiment classification
Input:        "sentiment: This movie was great!"
Output:       "positive"

Task:         Translation
Input:        "translate English to German: The house is wonderful."
Output:       "Das Haus ist wunderschön."

Task:         Summarization
Input:        "summarize: [long article text]"
Output:       "Brief summary of the article."
```

---

## Part 3 — Architectural Comparison

### Attention Flow

| Aspect | Decoder-Only | Encoder-Decoder |
|--------|-------------|-----------------|
| Prompt representation | Causal (token t sees t_{<t}) | Bidirectional (full mutual attention) |
| Generation | Causal autoregressive | Causal autoregressive with cross-attention |
| Source-target interaction | Unified sequence; implicit | Explicit cross-attention mechanism |
| KV cache during inference | Entire context | Encoder: computed once; Decoder: incremental |

### Compute Profile

For source length `S` and target length `T`:

**Decoder-Only (prompt + generation as one sequence of length S+T):**
```
Attention compute: O((S + T)² × d_k)
```

**Encoder-Decoder:**
```
Encoder attention:   O(S² × d_k)
Decoder self-attn:   O(T² × d_k)
Cross-attention:     O(S × T × d_k)    ← per decoding step
Total:               O((S² + T² + ST) × d_k)
```

For `S = T`: Encoder-Decoder has 3 terms vs. `(S+T)² = 4S²` for decoder-only — roughly similar, but the cross-attention adds a constant multiplicative overhead per decoder block.

### The Parameter Split Problem

An Encoder-Decoder model with `N` total parameters splits them between encoder and decoder. Each half has `N/2` parameters to process its task. A decoder-only model of the same total `N` parameters devotes all of them to the generation task.

Empirically this is why **decoder-only models tend to be stronger at generation** per parameter — there's no "tax" paid to the encoder half.

---

## Part 4 — When to Use Each

### Use Decoder-Only When:

**1. Generation is the primary output**
- Chat, code generation, creative writing, document drafting
- GPT-4, Claude, LLaMA: all decoder-only

**2. Long-context generation where prompt << output**
- Writing a 10,000-word essay from a 50-word prompt
- The encoder's advantage (bidirectionality over source) is negligible for short prompts

**3. In-context learning and few-shot prompting**
- The unified sequence format handles arbitrary task formats
- No need to re-architect for new tasks

**4. Serving efficiency**
- One KV cache; simpler serving infrastructure
- Streaming generation is straightforward

**5. Scaling beyond ~10B parameters**
- The research community has converged on decoder-only for frontier models
- Better scaling laws empirically

### Use Encoder-Decoder When:

**1. Source sequence is long and output is conditioned heavily on it**
- Summarization: 10,000-word source → 200-word summary
- Translation: sentence-level, where source structure matters throughout
- Document QA: answer extracted from a long document

**Reason:** Bidirectional encoder produces richer source representations. Every decoder step cross-attends to all source positions simultaneously — much better than the decoder-only approach of just including the source in the causal context.

**2. The source and target are structurally different**
- Code-to-text (explain this function)
- SQL generation from natural language
- Structured data (tables/JSON) → natural language

The hard separation between "understanding source" (encoder) and "generating target" (decoder) is an inductive bias that helps when these are genuinely different tasks.

**3. Tasks requiring strong bidirectional understanding + generation**
- Question generation from a passage
- Paraphrasing
- Data augmentation

**4. Smaller models / constrained inference budgets**
- T5-Small (60M params) is competitive with much larger decoder-only models on specific tasks
- Encoder-decoder is more parameter-efficient for seq2seq at smaller scales

### When Encoder-Only (BERT)?

If **no generation is needed** — classification, named entity recognition, semantic similarity, retrieval — use encoder-only. Bidirectional attention produces the best token representations for discriminative tasks. No causal restriction needed.

---

## Part 5 — Architectural Innovations Blurring the Line

### Prefix-LM

A hybrid: bidirectional attention over a "prefix" (input), causal attention over the "generation" portion. Used in UL2, GLM.

```
[prefix tokens: bidirectional] | [generation tokens: causal]
```

Theoretically captures the best of both, but hasn't displaced either architecture in practice.

### Mixture of Experts (MoE)

Not strictly an architectural family split, but applies to both: replace the dense FFN with `E` expert FFNs, routing each token to the top-`K` experts:

```
FFN_MoE(x) = Σ_{k ∈ TopK(router(x))} gate_k(x) · Expert_k(x)
```

- **Mistral's Mixtral:** 8 experts, top-2 routing (56B total params, 14B active)
- **GPT-4:** rumored to be a large MoE

MoE scales parameter count without proportionally scaling compute — a form of **conditional computation**.

---

## Summary Table

| Criterion | Decoder-Only | Encoder-Decoder |
|-----------|-------------|-----------------|
| Best for | Open-ended generation, chat, code | Seq2seq, summarization, translation |
| Source representation | Causal (limited) | Bidirectional (full) |
| Parameter efficiency at scale | High | Moderate (split between enc/dec) |
| Inference complexity | Simpler (one KV cache) | More complex (encoder + decoder KV) |
| Frontier models | GPT-4, Claude, LLaMA, Gemini | T5, BART, mT5 |
| Dominant use case today | General-purpose LLMs | Specialized seq2seq tasks |

---

*Previous: [04 — Training & Backpropagation](./04_Training_and_Backpropagation.md)*
*Next: [06 — Inference & Sampling](./06_Inference_and_Sampling.md)*
