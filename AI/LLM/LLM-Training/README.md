# How LLMs Are Trained
### From Raw Internet Text to a Helpful Assistant — A Complete Technical Guide

> **Companion to:** [Demystifying LLMs](../Demystifying%20LLMs/README.md) — the architecture series.  
> **Philosophy:** Every training decision is a constraint on the loss surface. Every alignment technique is a form of distribution shift. We trace cause and effect rigorously.

---

## Why You Should Read This First

The *Demystifying LLMs* series explains how a trained model **works** — the forward pass, attention, embeddings, inference.  

This series explains how the model **gets trained** — how a randomly-initialized set of parameters is shaped, in stages, into a model that can reason, follow instructions, and decline harmful requests.

These are two different questions. The architecture is a vessel. The training is what fills it.

```
╔══════════════════════════════════════════════════════════════════════════════╗
║               COMPLETE LLM TRAINING PIPELINE                                ║
╠══════════════════════════════════════════════════════════════════════════════╣
║                                                                              ║
║  ┌─────────────────────────────────────────────────────────────────┐        ║
║  │  🌐  RAW INTERNET TEXT                                          │        ║
║  │  Billions of web pages • Books • Code • Wikipedia               │        ║
║  └──────────────────────────────┬──────────────────────────────────┘        ║
║                                 │                                            ║
║                    ┌────────────▼────────────┐                              ║
║                    │   DATA PIPELINE          │  ← 00_Data.md               ║
║                    │  Filter → Dedup → Score  │                              ║
║                    │  ~15 Trillion tokens     │                              ║
║                    └────────────┬────────────┘                              ║
║                                 │                                            ║
║  ╔══════════════════════════════▼══════════════════════════════════╗         ║
║  ║  STAGE 1: PRE-TRAINING                    ← 01_Pretraining.md  ║         ║
║  ║  ─────────────────────────────────────────────────────────────  ║         ║
║  ║  Objective: Predict next token (cross-entropy loss)            ║         ║
║  ║  Compute:   ~10²³ FLOPs  •  Weeks on 1000s of GPUs            ║         ║
║  ║  Output:    BASE MODEL                                          ║         ║
║  ║             ✓ Knows language and world facts                    ║         ║
║  ║             ✗ Cannot follow instructions                        ║         ║
║  ╚══════════════════════════════╦══════════════════════════════════╝         ║
║                                 ║                                            ║
║  ╔══════════════════════════════▼══════════════════════════════════╗         ║
║  ║  STAGE 2: SUPERVISED FINE-TUNING (SFT)  ← 02_SFT.md           ║         ║
║  ║  ─────────────────────────────────────────────────────────────  ║         ║
║  ║  Data:     10K–100K (instruction, response) pairs              ║         ║
║  ║  Method:   Standard cross-entropy, loss-masked to responses     ║         ║
║  ║  Compute:  ~0.01% of pre-training cost                         ║         ║
║  ║  Output:   INSTRUCTION-TUNED MODEL                             ║         ║
║  ║             ✓ Answers questions in assistant format             ║         ║
║  ║             ✗ No sense of values or safety                      ║         ║
║  ╚══════════════════════════════╦══════════════════════════════════╝         ║
║                                 ║                                            ║
║  ╔══════════════════════════════▼══════════════════════════════════╗         ║
║  ║  STAGE 3: REWARD MODEL TRAINING          ← 03_RLHF.md          ║         ║
║  ║  ─────────────────────────────────────────────────────────────  ║         ║
║  ║  Data:     33K–1.4M (prompt, y_win, y_lose) human comparisons  ║         ║
║  ║  Method:   Bradley-Terry preference model → binary cross-entropy ║        ║
║  ║  Output:   REWARD MODEL r(x, y) → scalar "goodness" score      ║         ║
║  ╚══════════════════════════════╦══════════════════════════════════╝         ║
║                                 ║                                            ║
║  ╔══════════════════════════════▼══════════════════════════════════╗         ║
║  ║  STAGE 4: ALIGNMENT (RLHF or DPO)   ← 03_RLHF + 04_DPO.md    ║         ║
║  ║  ─────────────────────────────────────────────────────────────  ║         ║
║  ║                                                                 ║         ║
║  ║  Option A — RLHF/PPO:                                          ║         ║
║  ║    max E[r(x,y)] - β·KL(π_θ || π_ref)                         ║         ║
║  ║    Requires: 4 models, online rollouts, complex orchestration   ║         ║
║  ║                                                                 ║         ║
║  ║  Option B — DPO:                                               ║         ║
║  ║    L = -E[log σ(β·log(π_θ(y_w)/π_ref(y_w)) - ...)]           ║         ║
║  ║    Requires: 2 models, offline data, simple as SFT             ║         ║
║  ║                                                                 ║         ║
║  ║  Output:   ALIGNED MODEL                                        ║         ║
║  ║             ✓ Helpful, honest, harmless                         ║         ║
║  ║             ✓ Admits uncertainty, refuses harm                  ║         ║
║  ╚══════════════════════════════╦══════════════════════════════════╝         ║
║                                 ║                                            ║
║  ╔══════════════════════════════▼══════════════════════════════════╗         ║
║  ║  STAGE 5 (Optional): PEFT / LoRA       ← 05_PEFT_and_LoRA.md  ║         ║
║  ║  ─────────────────────────────────────────────────────────────  ║         ║
║  ║  Purpose:  Domain specialization without full fine-tuning       ║         ║
║  ║  Method:   ΔW ≈ B·A  where rank(B·A) = r << d                 ║         ║
║  ║  Cost:     ~0.001% of pre-training  •  Fits on 1 consumer GPU  ║         ║
║  ║  Output:   SPECIALIZED MODEL (medical, legal, code, etc.)       ║         ║
║  ╚══════════════════════════════╦══════════════════════════════════╝         ║
║                                 ║                                            ║
║  ┌──────────────────────────────▼──────────────────────────────────┐        ║
║  │  🚀  DEPLOYED ASSISTANT                                         │        ║
║  │  ChatGPT • Claude • LLaMA-Chat • Gemini                         │        ║
║  └─────────────────────────────────────────────────────────────────┘        ║
╚══════════════════════════════════════════════════════════════════════════════╝

Relative Compute Budget (approximate):
  Pre-Training:       ████████████████████████████████████████  ~$10-50M
  Reward Model:       ██░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~$1-5M
  SFT:                █░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~$100K-1M
  RLHF/PPO:           ███░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~$1-5M
  LoRA Fine-Tuning:   ░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░░  ~$100-10K
```

---

## Table of Contents

| # | Document | Core Topics |
|---|----------|-------------|
| 0 | [Data: What Gets Fed In](./00_Data_and_Pretraining_Corpus.md) | Data collection, quality filters, deduplication, tokenization at scale, data mixtures |
| 1 | [Pre-Training: Learning from the World](./01_Pretraining.md) | Language modeling objective, scaling laws, compute budgets, Chinchilla, loss curves |
| 2 | [Supervised Fine-Tuning (SFT)](./02_Supervised_Finetuning.md) | Instruction datasets, format, loss masking, catastrophic forgetting |
| 3 | [RLHF: Learning from Human Preferences](./03_RLHF.md) | Reward models, PPO, KL penalty, the alignment tax |
| 4 | [Beyond RLHF: DPO and Modern Alignment](./04_DPO_and_Modern_Alignment.md) | Direct Preference Optimization, ORPO, Constitutional AI, RLAIF |
| 5 | [Efficient Adaptation: PEFT & LoRA](./05_PEFT_and_LoRA.md) | Parameter-efficient tuning, LoRA math, QLoRA, prompt tuning, adapters |
| 6 | [The Training Story: Raw Text → ChatGPT](./06_The_Training_Story.md) | End-to-end narrative: GPT-3 → InstructGPT → ChatGPT, decision-by-decision |

---

## Reading Order

**If you want the narrative first:** Start with `06_The_Training_Story.md`, then backfill each stage.  
**If you want the math first:** Start at `00` and read in order.  
**If you want one concept:** Each document is self-contained.

---

## Notation Conventions

Inherited from the *Demystifying LLMs* series, plus:

| Symbol | Meaning |
|--------|---------|
| `θ` | All model parameters (weights) |
| `π_θ` | Policy — the language model as a probability distribution |
| `π_ref` | Reference policy — the frozen SFT model used in RLHF |
| `r(x, y)` | Reward model score for prompt `x`, completion `y` |
| `β` | KL penalty coefficient in RLHF |
| `D_KL` | KL divergence — measures how far one distribution is from another |
| `y_w` | Preferred (winning) response in a preference pair |
| `y_l` | Dispreferred (losing) response in a preference pair |
| `r` | Rank of LoRA decomposition |
| `α` | LoRA scaling factor |

---

## Key Insight Per Stage

```
Pre-Training:     "Predict the next token" shapes knowledge of the world.
SFT:              "Imitate good examples" shapes the format and tone.
RLHF:             "Maximize human approval" shapes values and safety.
DPO:              "Directly prefer good over bad" — same goal, less complexity.
LoRA:             "Update a small subspace" — same capability, 1000× less memory.
```

---

*Series: How LLMs Are Trained | April 2026*  
*Companion series: [Demystifying LLMs](../Demystifying%20LLMs/README.md)*
