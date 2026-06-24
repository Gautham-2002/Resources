# 05 — Efficient Adaptation: PEFT & LoRA
### Fine-Tuning Without Full-Model Updates

> **Key insight:** A 70B model has 70 billion parameters. Full fine-tuning requires updating all of them — which demands the same compute and memory as pre-training. LoRA makes fine-tuning tractable by observing that the *changes* to a model's weights during fine-tuning live in a very low-dimensional subspace, not the full parameter space.

---

## Part 1 — The Full Fine-Tuning Problem

Recall from pre-training: a 70B model in BFloat16 requires:

```
Model weights:        70B × 2 bytes = 140GB
Optimizer states:     70B × 8 bytes = 560GB (AdamW: 2 states × float32)
Gradients:            70B × 2 bytes = 140GB
Activations:          ~10-50GB (depends on sequence length, batch size)

Total:                ~850GB – 1TB

Number of A100 GPUs (80GB each) needed:
  Minimum: ceil(850 / 80) ≈ 11 GPUs
  In practice with overhead: 16-32 GPUs
```

For most companies and researchers, this is inaccessible. A single A100 GPU costs ~$10K. A 32-GPU cluster costs ~$320K just in hardware.

**Parameter-Efficient Fine-Tuning (PEFT)** methods solve this by updating only a small subset of parameters while keeping most of the model frozen.

---

## Part 2 — LoRA: Low-Rank Adaptation

**LoRA** (Hu et al., Microsoft, 2021) is the most widely adopted PEFT method. It has become the standard for fine-tuning models across the industry.

### 2.1 The Core Hypothesis

During fine-tuning, the update to any weight matrix `W` can be well-approximated by a **low-rank matrix**:

```
W_pretrained ∈ ℝ^(d × k)   (original, frozen)

During fine-tuning, the model learns an update ΔW:
  W_finetuned = W_pretrained + ΔW

ΔW ∈ ℝ^(d × k)   — same shape as W

LoRA hypothesis: rank(ΔW) << min(d, k)
  The useful fine-tuning signal lives in a low-dimensional subspace.
```

**Evidence for this hypothesis:**
- Aghajanyan et al. (2020) showed that the loss landscape of fine-tuning is effectively low-dimensional — you can find good solutions by varying a small number of parameters.
- In practice, LoRA with rank 4-16 matches or exceeds full fine-tuning on most tasks.

### 2.2 The LoRA Parameterization

Instead of directly learning `ΔW ∈ ℝ^(d×k)`, LoRA decomposes it:

```
ΔW = B · A

Where:
  A ∈ ℝ^(r × k)   (down-projection, small)
  B ∈ ℝ^(d × r)   (up-projection, small)
  r << min(d, k)   (rank, e.g., r = 4, 8, or 16)

Number of parameters in ΔW:     d × k
Number of parameters in B + A:  r × k + d × r = r(d + k)

For d = k = 4096, r = 8:
  Full ΔW: 4096 × 4096 = 16,777,216 parameters
  LoRA A + B: 8 × (4096 + 4096) = 65,536 parameters
  Reduction: 256× fewer parameters to learn
```

### 2.3 LoRA Forward Pass

During training with LoRA:

```
Normal linear layer forward pass:
  h = x · W_pretrained^T

LoRA forward pass:
  h = x · W_pretrained^T + x · A^T · B^T · (α / r)

Where:
  α = scaling factor (hyperparameter, often set equal to r)
  α/r = the LoRA scaling — controls how much the LoRA update matters
```

The full weight `W_pretrained + B·A·(α/r)` is never explicitly computed during training — the two parts are kept separate and applied as two sequential matrix multiplications.

**Initialization:**
```
A initialized: N(0, σ²)  (random)
B initialized: 0         (all zeros)

At initialization: B·A = 0·A = 0, so ΔW = 0.
The model starts at its pre-trained state. This is critical for stability.
```

### 2.4 LoRA Architecture: Where to Apply It

LoRA is applied to specific weight matrices in the transformer. Typical choices:

```
Transformer Block:
  ├── Attention
  │     ├── W_Q  ←── LoRA applied here
  │     ├── W_K  ←── LoRA applied here  
  │     ├── W_V  ←── LoRA applied here
  │     └── W_O  ←── LoRA applied here (optional)
  └── FFN
        ├── W_up   ←── sometimes
        └── W_down ←── sometimes

Original LoRA paper: applied to W_Q and W_V only.
Modern practice: apply to all 4 attention matrices (or all 6 including FFN).
```

The embedding and unembedding matrices are usually kept frozen (they are already token-aligned from pre-training).

### 2.5 Memory Impact of LoRA

```
Full fine-tuning of LLaMA-2-7B:
  Trainable parameters: 7B
  Optimizer states (AdamW): 7B × 8 bytes = 56GB
  Total additional memory: ~60GB

LoRA fine-tuning of LLaMA-2-7B (rank=16, W_Q/W_K/W_V/W_O):
  LoRA matrices per layer: 4 matrices × 2 (A and B) × 16 rank
  4 × (4096 × 16 + 16 × 4096) = 4 × 131,072 = 524,288 params per layer
  32 layers × 524,288 = 16.8M trainable parameters

  Optimizer states: 16.8M × 8 bytes = 134MB (vs 56GB for full fine-tuning)

  The 7B frozen model weights: 7B × 2 bytes = 14GB (BF16)
  Total GPU memory for LoRA training: ~18-24GB (fits on a single A100!)

Memory reduction: optimizer states drop from 56GB → 134MB (~420× reduction)
```

### 2.6 Inference: Merging LoRA Weights

After LoRA training, the adapter weights can be **merged** back into the base model:

```
At inference time:
  W_final = W_pretrained + B·A·(α/r)

This is a one-time operation. The merged model has IDENTICAL inference speed
to the original — no overhead from the two separate multiplications.

For serving, always merge LoRA back into base weights before deployment.
```

---

## Part 3 — QLoRA: Quantized LoRA

**QLoRA** (Dettmers et al., University of Washington, 2023) extends LoRA with 4-bit quantization of the frozen base model, enabling training of very large models on consumer hardware.

### 3.1 The Quantization Idea

Instead of storing `W_pretrained` in BFloat16 (2 bytes per parameter), quantize it to 4-bit integers (0.5 bytes):

```
BFloat16 storage for 70B model: 70B × 2 bytes = 140GB
4-bit storage for 70B model:    70B × 0.5 bytes = 35GB

A 70B model now fits on a single A100 (80GB) — with room for LoRA adapters!
```

### 3.2 NF4: NormalFloat4

QLoRA introduces a new 4-bit data type specifically designed for neural network weights:

```
Standard 4-bit integers: 0, 1, 2, ..., 15  (linear spacing)
NF4 (NormalFloat4): non-linear quantization levels optimized for the
                    Normal distribution of pre-trained weights.

Pre-trained weights are approximately normally distributed N(0, σ²).
NF4 places more quantization levels near 0 (where most weights are)
and fewer levels in the tails.

Result: NF4 quantization loses less information than standard int4 for
        normally-distributed weights.
```

### 3.3 Double Quantization

QLoRA quantizes even the quantization constants:

```
Standard quantization:
  Weights → stored in 4-bit
  Quantization scales → stored in float32 (adds 32 bits per block)

Double quantization:
  Weights → stored in 4-bit (NF4)
  Quantization scales → quantized to 8-bit (FP8)
  Quantization constants for the scales → stored in float32

Net effect: reduces average storage to ~4.5 bits per parameter
(vs. 4 bits without double quantization, but higher accuracy)
```

### 3.4 Paged Optimizers

Another QLoRA innovation: optimizer state paging. When GPU memory is insufficient:

```
Normal situation: optimizer states live in GPU VRAM entirely.
If insufficient VRAM → OOM (out of memory) error, training crashes.

QLoRA paged optimizers:
  Optimizer states live in GPU VRAM when possible.
  When a memory spike occurs (e.g., long sequences), optimizer states
  are "paged out" to CPU RAM automatically.
  Paged back in for the optimizer step.

This prevents OOM crashes at the cost of some CPU-GPU transfer overhead.
```

### 3.5 QLoRA's Impact

```
Hardware requirements for fine-tuning (LoRA, rank=64):

Model     | Full FT   | LoRA (BF16) | QLoRA (NF4)
──────────────────────────────────────────────────
7B        | 8× A100   | 1× A100     | 1× RTX 3090 (24GB)
13B       | 16× A100  | 2× A100     | 1× A100 (80GB)
33B       | 32× A100  | 4× A100     | 2× A100
70B       | 64× A100  | 8× A100     | 4× A100

QLoRA made fine-tuning a 7B model accessible on a ~$300 consumer GPU.
This democratized LLM fine-tuning beyond big labs.
```

---

## Part 4 — Other PEFT Methods

### 4.1 Adapter Layers (Houlsby et al., 2019)

Insert small "adapter" modules inside each transformer block:

```
Normal transformer block:
  x → Attention → x + Attention(x) → FFN → x + FFN(x) → output

Adapter transformer block:
  x → Attention → Adapter₁(x + Attention(x)) → FFN → Adapter₂(x + FFN(x)) → output

Each adapter:
  [Down-project: d → r] → [Nonlinearity] → [Up-project: r → d]
  (same low-rank structure as LoRA, but applied in series not in parallel)
```

Adapters were the original PEFT method. LoRA largely replaced them because:
- LoRA has no inference overhead (can be merged into W)
- Adapters add sequential depth (slightly slower inference)

### 4.2 Prefix Tuning (Li & Liang, 2021)

Instead of modifying weights, prepend a set of learned virtual tokens to each attention layer's key and value matrices:

```
Normal attention:
  K = x · W_K    ∈ ℝ^(T × d)
  V = x · W_V    ∈ ℝ^(T × d)

Prefix tuning:
  K = concat([P_K; x · W_K])   P_K ∈ ℝ^(L × d)  (learned prefix)
  V = concat([P_V; x · W_V])   P_V ∈ ℝ^(L × d)

Where L = prefix length (e.g., 10-100 tokens).
Every attention query now attends to these L prefix positions.
```

The prefix vectors are task-specific and learned during fine-tuning. The model weights are frozen.

**Pros:** Extremely parameter-efficient (L × d × 2 × N_layers parameters).  
**Cons:** Less expressive than LoRA; harder to train (optimization is less stable).

### 4.3 Prompt Tuning (Lester et al., 2021)

Simpler than prefix tuning: add learned vectors only to the **input embedding** layer, not every attention layer.

```
Normal input:
  embeddings = lookup(token_ids)    ∈ ℝ^(T × d)

Prompt tuning:
  soft_prompt ∈ ℝ^(L × d)          (learned vectors, same dimension as embeddings)
  embeddings = concat([soft_prompt; lookup(token_ids)])

The model processes L + T tokens, where L is the soft prompt.
```

Even more parameter-efficient than prefix tuning (only L × d parameters). Works well for large models but is significantly worse than LoRA for smaller models (<11B parameters).

### 4.4 (IA)³: Infused Adapter by Inhibiting and Amplifying Inner Activations

A minimalist approach: scale key, value, and FFN activations with learned vectors:

```
Normal attention:
  K = x · W_K

(IA)³ attention:
  K = l_k ⊙ (x · W_K)   where l_k ∈ ℝ^d is a learned scaling vector

Same for V and the FFN intermediate activations.
```

Parameters per layer: 3 × d (three learned vectors, one per scaled activation). For a 7B model, this is ~1M total parameters — tiny.

Used in few-shot adaptation without catastrophic forgetting.

---

## Part 5 — Choosing the Right PEFT Method

```
Decision Framework:

Task has VERY FEW samples (< 1000)?
  → Prompt Tuning or (IA)³  (minimal overfitting)

Task needs MAXIMUM QUALITY?
  → Full fine-tuning (if compute allows) or LoRA with high rank (r=64+)

Hardware constrained to consumer GPU (< 24GB VRAM)?
  → QLoRA (4-bit quantized base + LoRA adapters)

Need to serve MULTIPLE TASKS from one base model?
  → LoRA (store separate adapter weights per task, swap at runtime)
  → Product: "base model" + multiple lightweight LoRA adapters

Need ZERO INFERENCE OVERHEAD after deployment?
  → LoRA (merge adapters into base weights before deployment)

Comparing PEFT methods:

Method         | Params     | Quality  | Inference overhead | Stability
───────────────────────────────────────────────────────────────────────────
Full FT        | 100%       | Best     | None               | High
LoRA (r=16)    | ~0.1%      | ~Full FT | None (after merge) | High
QLoRA (r=64)   | ~0.1%      | ~Full FT | None (after merge) | High
Adapters       | ~0.5-2%    | Good     | Small              | High
Prefix Tuning  | ~0.01-0.1% | Moderate | None               | Medium
Prompt Tuning  | ~0.001%    | Moderate | None               | Medium
(IA)³          | ~0.01%     | Moderate | None               | High
```

---

## Part 6 — Multi-Task LoRA: The Adapter Hub Pattern

A powerful operational pattern: maintain a single base model and multiple LoRA adapters for different tasks:

```
                    ┌─────────────────┐
                    │  Base Model     │
                    │  (7B, frozen)   │
                    └────────┬────────┘
                             │
              ┌──────────────┼──────────────┐
              ▼              ▼              ▼
     ┌────────────┐ ┌────────────┐ ┌────────────┐
     │ LoRA       │ │ LoRA       │ │ LoRA       │
     │ Medical QA │ │ Code Gen   │ │ Legal Text │
     │ (20MB)     │ │ (20MB)     │ │ (20MB)     │
     └────────────┘ └────────────┘ └────────────┘

Total storage: 14GB (base) + N × 20MB (adapters)
vs.
N separate fine-tuned 7B models: N × 14GB

For N=10 tasks: 14GB + 200MB  vs.  140GB
```

At inference time, load the base model once and swap adapters based on the task. This is the architecture behind products like Predibase, Together AI's fine-tuning platform, and others.

---

## Summary

```
PEFT Landscape:

The key insight: weight updates during fine-tuning are intrinsically low-rank.
We don't need to update all parameters — just the subspace that matters.

LoRA:     Learn B·A ≈ ΔW, where rank(B·A) = r << min(d,k)
          → 100-1000× fewer trainable parameters
          → Same quality as full fine-tuning
          → No inference overhead after merging

QLoRA:    Quantize frozen base to 4-bit + LoRA adapters in BF16
          → 4-8× more memory efficient than LoRA alone
          → Enables 70B model fine-tuning on a few A100s

Adapters: Small bottleneck layers inserted in series
          → Higher quality than prefix/prompt tuning
          → Small inference overhead (not zero)

For most practical fine-tuning: LoRA is the default choice.
For consumer hardware / very large models: QLoRA.
```

---

*Previous: [04 — Beyond RLHF: DPO and Modern Alignment](./04_DPO_and_Modern_Alignment.md)*  
*Next: [06 — The Training Story: Raw Text → ChatGPT](./06_The_Training_Story.md)*
