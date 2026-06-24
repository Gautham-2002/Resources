# 01 — Pre-Training: Learning from the World
### The Foundational Stage — How a Random Model Becomes Knowledgeable

> **Key insight:** Pre-training is the only stage where the model acquires knowledge. Every subsequent stage (SFT, RLHF) only reshapes *how* the model expresses that knowledge — not what it knows. A model cannot be taught facts it wasn't pre-trained on.

---

## Part 1 — The Self-Supervised Learning Objective

Pre-training requires no human labels. The supervision signal is the training data itself.

### Next-Token Prediction (Causal Language Modeling)

For a decoder-only model (GPT family), the training objective is:

```
Given tokens [t₁, t₂, ..., t_{T-1}], predict t_T
```

Applied at every position simultaneously (via the causal mask):

```
Input:   [t₁,  t₂,  t₃,  t₄,  t₅]
Targets: [t₂,  t₃,  t₄,  t₅,  t₆]

Each position predicts the next token.
One forward pass → T loss terms.
```

The loss is the **average cross-entropy** over all positions in the batch:

```
L = -(1 / (B × T)) × Σ_{b=1}^{B} Σ_{t=1}^{T} log P(t_{b,t+1} | t_{b,1}, ..., t_{b,t})
```

Where:
- `B` = batch size (number of sequences)
- `T` = sequence length (tokens per sequence)
- `P(t | ...)` = the model's probability for the correct next token

**This is the only thing pre-training optimizes.** Despite its simplicity, minimizing this loss over trillions of tokens forces the model to develop:
- Syntactic understanding (grammar, sentence structure)
- Semantic knowledge (meaning, relationships)
- Factual knowledge (who, what, when, where)
- Reasoning capabilities (if-then, cause-effect)
- Multiple languages simultaneously

### Masked Language Modeling (BERT-style, for Encoders)

For encoder-only models (BERT, RoBERTa), a different objective:

```
Input:  "The [MASK] of France is Paris"
Target: "capital" at the MASK position
```

Randomly mask 15% of tokens; predict them using full bidirectional context.  
This enables seeing both left and right context — but cannot be used for generation.

This document focuses on **causal LM pre-training** (decoder-only), which underlies GPT, LLaMA, Claude, and all major chat models.

---

## Part 2 — The Training Loop: What Actually Happens

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRE-TRAINING LOOP                           │
│                                                                 │
│  Initialize:  All weights θ ~ N(0, σ²)  (small random values)  │
│                                                                 │
│  For each step 1..N_steps:                                      │
│    1. SAMPLE: Draw a mini-batch B of token sequences from disk  │
│    2. FORWARD: Compute predictions for each position            │
│    3. LOSS: Compute cross-entropy loss L                        │
│    4. BACKWARD: Compute ∂L/∂θ via backpropagation              │
│    5. CLIP: Clip gradient norm to max_norm (e.g., 1.0)         │
│    6. UPDATE: Apply AdamW step                                  │
│    7. LOG: Record loss, learning rate, gradient norm            │
│    8. CHECKPOINT: Save weights every N steps                    │
│                                                                 │
│  N_steps for a frontier model: ~1,000,000 – 5,000,000 steps    │
└─────────────────────────────────────────────────────────────────┘
```

### What "Initialization" Means

All weights start as small random numbers, typically drawn from a normal distribution with a carefully chosen standard deviation:

```
For a weight matrix W ∈ ℝ^(d_in × d_out):

Standard initialization: W_ij ~ N(0, 1/d_in)    (Xavier)
                    or:  W_ij ~ N(0, 2/(d_in + d_out))   (Glorot)

GPT-2 residual layers: scaled by 1/√(2N) where N = number of layers
  (prevents residual stream from growing too large in deep models)
```

At step 0, the model has no knowledge. Its predictions are essentially random — it assigns roughly equal probability to all 50,257+ tokens. The initial loss is therefore approximately:

```
L₀ ≈ -log(1/V) = log(V) = log(50257) ≈ 10.82 nats
```

Over training, this drops dramatically — to ~2.5-3.5 for a well-trained frontier model.

---

## Part 3 — The Learning Rate Schedule

Learning rate is the most critical hyperparameter. The standard schedule for modern LLMs:

```
Learning Rate

  η_max ┤          ╭─────────────────────────────╮
        │         ╱                               ╲
        │        ╱    Cosine Decay                  ╲
        │       ╱                                    ╲
  η_min ┤╌╌╌╌╌╌╱                                    ╰──── (η_min = 0.1×η_max typically)
        │      ╱
   0    ┤─────╱
        └────────────────────────────────────────────────►
        0   warmup_steps                        max_steps
            (e.g., 2000)                        (e.g., 1M)

Warmup phase: LR increases linearly from 0 to η_max
Cosine phase: LR follows cosine curve from η_max to η_min
```

**The warmup phase:** At step 0, the model's gradients are large and noisy — the loss landscape is poorly understood by the optimizer. Starting with a small LR prevents catastrophic early updates. After warmup, the model has settled into a reasonable region of the loss landscape.

**The cosine decay:** As training proceeds, we want smaller and smaller updates — the model is converging toward a minimum. Cosine decay is smooth and empirically outperforms linear decay.

**Typical hyperparameters for a 7B-70B model:**
```
η_max = 3×10⁻⁴ to 1×10⁻³  (depends on batch size via linear scaling rule)
warmup_steps = 2000
β₁ = 0.9, β₂ = 0.95
ε = 1×10⁻⁸ (Adam epsilon)
weight_decay = 0.1
gradient_clip_norm = 1.0
```

---

## Part 4 — Scaling Laws: How Much Compute Is Needed?

### The Kaplan et al. (OpenAI, 2020) Scaling Laws

The first major empirical paper showing that LLM performance is **predictable** from compute:

```
Loss L depends on three quantities:
  N = number of parameters
  D = number of training tokens
  C = compute budget (FLOPs)

Key findings:
  L(N) ∝ N^{-0.076}   (more params → lower loss)
  L(D) ∝ D^{-0.095}   (more data → lower loss)
  L(C) ∝ C^{-0.050}   (more compute → lower loss)
```

These are **power laws** — log-linear relationships between scale and performance.

**The original prescription (Kaplan):** For a fixed compute budget `C`, maximize `N` (model size). Data `D` can be smaller because data is "cheap."

This led to GPT-3: 175B parameters, trained on "only" 300B tokens.

### The Chinchilla Scaling Laws (Hoffmann et al., DeepMind, 2022)

Chinchilla challenged Kaplan's prescription. By training many models of different sizes on different amounts of data:

```
Optimal allocation of compute C:
  N* = optimal parameter count
  D* = optimal token count

Finding: N* ∝ C^0.5   and   D* ∝ C^0.5

Simplified rule: Train on ~20 tokens per parameter
  → For a 7B model: train on ~140B tokens
  → For a 70B model: train on ~1.4T tokens
```

**The key result:** GPT-3 (175B params, 300B tokens = ~1.7 tokens/param) was **severely undertrained**. A 70B model trained on 1.4T tokens achieves *better* performance at *lower* inference cost.

```
Model Comparison (Chinchilla paper):
  Gopher (280B params, 300B tokens):  loss = X
  Chinchilla (70B params, 1.4T tokens): loss < X

Same compute budget. 4× smaller model. Better performance.
```

**Why this matters:** Inference cost scales with model size, not training FLOPs. A smaller, compute-optimally trained model is both cheaper to train AND cheaper to run.

### The Post-Chinchilla Paradigm: Intentional Over-Training

LLaMA 1 (2023) made a different choice: train a 7B model on 1 **Trillion** tokens (~143 tokens/param — 7× the Chinchilla optimum).

**Reasoning:** Chinchilla optimizes for a single training run. But if you want the best model at inference time, you should train a smaller model for much longer. LLaMA 7B at 1T tokens outperforms larger models at inference — and is cheaper to serve.

```
Strategy comparison:

                  Training Cost    Inference Cost   Final Quality
Chinchilla-opt    Moderate         High (big model)  Good
Over-trained      High             Low (small model) Good

For APIs serving millions of users: inference cost >> training cost.
→ Over-training smaller models is often the right business decision.
```

LLaMA 3 (2024) took this to the extreme: 8B model trained on 15.6T tokens — ~1,950 tokens/param.

---

## Part 5 — Distributed Training: Fitting the Problem on Hardware

A 70B parameter model in BFloat16 requires:
```
70B params × 2 bytes/param = 140GB just for weights

AdamW optimizer states (2 copies per param): 70B × 2 × 4 bytes = 560GB
Gradients: 70B × 2 bytes = 140GB

Total: ~840GB minimum for training
```

A single A100 GPU has 80GB of VRAM. A frontier model requires **10+ GPUs minimum** just to hold the model. In practice, training uses thousands of GPUs simultaneously.

### Three Parallelism Strategies

```
┌─────────────────────────────────────────────────────────────────┐
│              PARALLELISM IN LLM TRAINING                        │
│                                                                 │
│  1. DATA PARALLELISM                                            │
│     ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐               │
│     │GPU 0   │ │GPU 1   │ │GPU 2   │ │GPU 3   │               │
│     │Full    │ │Full    │ │Full    │ │Full    │               │
│     │Model   │ │Model   │ │Model   │ │Model   │               │
│     │Batch A │ │Batch B │ │Batch C │ │Batch D │               │
│     └────────┘ └────────┘ └────────┘ └────────┘               │
│     Gradients averaged via AllReduce after each step           │
│     → 4× throughput; model must fit in 1 GPU                  │
│                                                                 │
│  2. TENSOR PARALLELISM (Megatron-LM)                           │
│     Weight matrix split across GPUs column-wise:               │
│     ┌──────────────────────────────────────┐                  │
│     │ W = [W₁ | W₂ | W₃ | W₄]            │                  │
│     │      GPU0  GPU1  GPU2  GPU3          │                  │
│     └──────────────────────────────────────┘                  │
│     Each GPU computes its slice of every matmul               │
│     → Requires fast NVLink within a node                      │
│                                                                 │
│  3. PIPELINE PARALLELISM                                        │
│     GPU 0: Layers 1-10 → GPU 1: Layers 11-20 → ...           │
│     Micro-batches overlap forward/backward passes              │
│     → Hides pipeline bubble; requires careful scheduling       │
└─────────────────────────────────────────────────────────────────┘
```

In practice, all three are combined: **3D parallelism** (Data × Tensor × Pipeline). Meta used 2,000+ A100 GPUs for LLaMA 2 training; Google used thousands of TPUs for PaLM.

### ZeRO Optimization (DeepSpeed)

ZeRO (Zero Redundancy Optimizer) eliminates redundant copies of data in data-parallel training:

```
ZeRO Stages:
  Stage 1: Shard optimizer states across GPUs      (4× memory reduction)
  Stage 2: + Shard gradients                       (8× memory reduction)
  Stage 3: + Shard model parameters                (N_gpus× reduction)

ZeRO-3 with 64 GPUs: 64× less memory per GPU
→ Effectively allows training of models that don't fit on any single GPU
  using only standard data parallelism infrastructure.
```

---

## Part 6 — The Loss Curve: What Training Looks Like

```
Cross-Entropy Loss During Pre-Training

 11 ┤█
    │
 10 ┤  █
    │   █
  9 ┤    ██
    │      ███
  8 ┤         ████
    │             ████
  7 ┤                 █████
    │                      ██████
  6 ┤                            ████████
    │                                    █████████
  5 ┤                                            █████████
    │                                                     ██████████
  4 ┤                                                               ████████████
    │                                                                            ████████
  3 ┤                                                                                    ████────
    │
  2 ┤
    └────────────────────────────────────────────────────────────────────────────────────────────►
    0                    Training Steps (billions)

Initial loss ≈ log(vocab_size) ≈ 10.8  (random model)
Good frontier model: ~2.5 – 3.0 nats at convergence
```

### What the Model Is Learning at Each Phase

```
Steps 0 – 10K:       Big drop
  • Common tokens, basic statistics (token frequency)
  • "The" is more likely than "aardvark" after most contexts

Steps 10K – 100K:    Steady decline
  • Grammar and syntax learned
  • Word co-occurrence patterns
  • Named entity patterns

Steps 100K – 1M:     Slow, consistent improvement
  • Factual associations (Paris → capital, Einstein → physics)
  • Semantic reasoning patterns
  • Long-range dependencies

Steps 1M+:           Diminishing returns
  • Rare knowledge, edge cases
  • Fine-grained stylistic distinctions
  • Complex reasoning on harder examples
```

### Loss Spikes

During training, the loss occasionally spikes upward before recovering:

```
Normal curve:   ─────────────────────────────────────
Spike:          ─────────────────────╮╰───────────────
```

Causes:
- An exceptionally hard batch (dense math, unusual code pattern)
- Numerical instability in attention (large activation values)
- Data pipeline serving a corrupted or unusual shard

Mitigation: Gradient clipping (limits the maximum update magnitude). At very large scales, major spikes can cause labs to roll back to a checkpoint and resume from there.

---

## Part 7 — What the Model Learns to Represent

After pre-training, several remarkable properties emerge — none of which were explicitly programmed:

### Emergent Capabilities

```
< 1B params:    Basic language understanding, simple completion
1B – 10B:       Grammar, basic facts, simple reasoning
10B – 100B:     Complex reasoning, multi-step logic, code
100B+:          In-context learning, chain-of-thought reasoning,
                few-shot task adaptation
```

**Emergent capabilities** are abilities that appear suddenly at scale — not gradually. A model at 9B params can't do chain-of-thought. At 12B params, it can. This step-change behavior is not fully understood.

### Representation Geometry

After pre-training, the embedding space has meaningful structure:

```
Linear algebraic structure in embeddings:
  vec("king") - vec("man") + vec("woman") ≈ vec("queen")
  vec("Paris") - vec("France") + vec("Germany") ≈ vec("Berlin")
```

These relationships weren't encoded — they *emerged* from predicting next tokens, because these relationships are implicit in the statistical structure of language.

### Mechanistic Interpretability Hints

Research has found that individual attention heads in pre-trained models specialize:
- Some heads reliably track subject-verb agreement
- Some heads track coreference (which pronoun refers to which noun)
- Some FFN neurons appear to store factual associations

This specialization wasn't designed — it emerged as the optimal way to minimize cross-entropy loss on natural language.

---

## Pre-Training Summary

```
INPUT:  Random weights θ₀ + Trillions of tokens of cleaned text

PROCESS:
  For each training step:
    1. Sample a batch of token sequences
    2. Forward pass → predict next token at each position
    3. Compute cross-entropy loss (how surprised was the model?)
    4. Backward pass → compute gradients (which direction reduces surprise?)
    5. AdamW optimizer step (move weights slightly in that direction)
    6. Repeat 1M+ times

OUTPUT: Weights θ_pretrained
  • Knows language syntax and grammar
  • Has factual knowledge compressed from training data
  • Can complete text coherently
  • Cannot follow instructions (will complete "What is 2+2?" with "What is 3+3?")
  • Will not refuse harmful requests
  • Has no concept of "being helpful"
```

A pre-trained base model is a **text completion engine**, not an assistant. The next stages transform it into something useful.

---

*Previous: [00 — Data: The Pre-Training Corpus](./00_Data_and_Pretraining_Corpus.md)*  
*Next: [02 — Supervised Fine-Tuning (SFT)](./02_Supervised_Finetuning.md)*
