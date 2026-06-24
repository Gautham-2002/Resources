# 06 — The Training Story: From Raw Text to ChatGPT
### A Narrative Account of Every Decision Made

> **The example:** We will follow the creation of a model like InstructGPT/ChatGPT — from the raw internet to a deployed assistant — and explain *why* each decision was made, not just *what* was done.

---

## Prologue: The Year Is 2021

OpenAI has GPT-3: a 175 billion parameter language model trained on 300 billion tokens of internet text. It is arguably the most capable language model ever built. It is also, from a product standpoint, nearly unusable.

It completes text. When you ask it a question, it continues the question with more questions. When you ask it to be helpful, it recites a Wikipedia article. When you give it a harmful prompt, it often complies without hesitation.

The architecture is correct. The training data is enormous. The compute invested is staggering. And yet the model is not doing what anyone actually wants.

The gap between "knows a lot" and "is useful" is vast. Closing it is the story of the next two years.

---

## Chapter 1 — Starting the Pre-Training Run

### The Hardware Setup

```
Training cluster: ~1,000 A100 GPUs
Interconnect: InfiniBand (high-bandwidth, low-latency GPU-to-GPU communication)
Storage: ~10PB NFS network filesystem holding tokenized training data

Parallelism strategy:
  Tensor parallel: 8 (within each node of 8 GPUs)
  Pipeline parallel: 4 (across 4 nodes)
  Data parallel: 32 (32 replica groups)
  Total GPUs: 8 × 4 × 32 = 1024 GPUs
```

### The First 1000 Steps

The model is initialized. Every weight is a small random number. The initial loss is:

```
L₀ = -log(1/50,257) ≈ 10.82 nats
```

The model doesn't know any language. It doesn't know any facts. It assigns nearly equal probability to all tokens.

After 1000 steps (~500M tokens processed), the loss has dropped to ~7. The model has learned that common English words are more likely than rare ones. "The" is more probable than "aardvark." Simple stuff.

The learning rate is still in its warmup phase, rising linearly toward `3×10⁻⁴`.

### Weeks 2-4: Structure Emerges

By step 50,000 (~25 billion tokens), loss is around 4. The model has now learned:
- Sentence structure: nouns follow determiners, verbs follow subjects
- Common phrases: "New York City," "United States," "according to"
- Basic factual associations: "Paris" appearing near "France" appearing near "capital"

It still can't reason. It still can't follow instructions. But it can produce grammatically correct English text that looks vaguely coherent.

### Month 3: The Long Slog

This is where pre-training spends most of its time. Loss is declining from ~4 to ~3 — a seemingly small change that encodes enormous amounts of knowledge.

At step 500,000 (~250B tokens), the model demonstrates an emergent capability that wasn't present earlier: **in-context learning**. Show it two examples of a translation task in the prompt, and it generalizes to translate new examples. This ability appeared without being trained on it explicitly — it emerged from sufficiently deep next-token prediction.

### The Pre-Training Checkpoint

After ~300 billion tokens, training ends. The loss has converged to approximately 3.2. The checkpoint is saved.

```
GPT-3 base model characteristics:
  Parameters: 175,000,000,000 (175B)
  Training tokens: 300B
  Training compute: ~3.14×10²³ FLOPs
  Training time: ~355 GPU-years (34 days on 1000 GPUs)
  Cost: ~$4.6M (estimated at 2020 A100 prices)

Capabilities:
  ✓ Coherent text completion in any style
  ✓ In-context learning from examples in the prompt
  ✓ Basic factual recall
  ✓ Code completion
  
  ✗ Following instructions
  ✗ Being helpful rather than just completing
  ✗ Refusing harmful requests
  ✗ Consistent persona
```

The base model is complete. Now the work of making it useful begins.

---

## Chapter 2 — Building the SFT Dataset

A team of 40 contractors — vetted for writing quality, common sense, and ethical judgment — is given detailed guidelines and begins annotating.

### The Prompt Distribution

The team needs prompts that represent what users actually want to do:

```
OpenAI's prompt mix for InstructGPT SFT data:
  • Brainstorming:         ~25% ("Give me 10 ideas for...")
  • Open QA:               ~20% ("What is the difference between X and Y?")
  • Summarization:         ~15% ("Summarize this article:")
  • Rewriting/editing:     ~15% ("Improve this email:")
  • Classification:        ~10% ("Categorize the sentiment:")
  • Code generation:        ~5% ("Write a Python function that...")
  • Closed QA:              ~5% ("Based on the following, answer:")
  • Other:                  ~5%
```

Some prompts come from actual GPT-3 API users (anonymized and reviewed). This is crucial — it captures what people *actually* ask, not what researchers think they'll ask.

### What Makes a Good Response

Annotators are given explicit guidelines. A high-quality response should be:

```
HELPFUL:
  ✓ Fully addresses the prompt
  ✓ Provides relevant, accurate information
  ✓ Has appropriate length (not too short, not padded)

HONEST:
  ✓ Acknowledges uncertainty ("I'm not certain, but...")
  ✓ Doesn't fabricate facts
  ✓ Corrects factually wrong premises in the question

HARMLESS:
  ✓ Doesn't produce content that could enable serious harm
  ✓ Doesn't demean groups of people
  ✓ Declines harmful requests with a brief explanation
```

### The Cost Calculation

```
13,000 prompt-response pairs
Each response: ~15-30 minutes of annotator time (including review)
Average: ~20 minutes × 13,000 = 260,000 minutes = ~4,300 hours
Contractor rate: ~$20-30/hour
Estimated SFT data cost: ~$85,000 – $130,000

Plus review time, quality assurance, annotator management: ~$200,000 total

Compare to pre-training cost: $4.6M
SFT data: a tiny fraction.
```

### Running the SFT Fine-Tuning

With 13,000 examples, a fine-tuning run is computationally trivial:

```
SFT training:
  Base: GPT-3 175B (or a smaller variant for testing)
  Learning rate: 9.65×10⁻⁶ (much lower than pre-training)
  Batch size: 32
  Epochs: 1 (for 175B; the model is powerful enough to learn from one pass)
  Training time: ~hours on the same cluster (vs. weeks for pre-training)

Loss masking:
  Only compute loss on the assistant response tokens.
  Instruction tokens have loss weight = 0.

Result: SFT model
  → Responds to questions instead of continuing them
  → Has an assistant persona
  → Covers common tasks reasonably well
  → Still not aligned on values
```

---

## Chapter 3 — The Reward Model

The SFT model is good at format but not at quality. To teach quality, we need human preferences — not just demonstrations.

### Collecting Comparisons

For the same prompt, generate multiple responses from the SFT model (with different temperatures), then ask a human to rank them:

```
Prompt: "Explain the trolley problem."

Response A (temp=1.0):
"The trolley problem is a famous ethical dilemma. Imagine a runaway
trolley heading toward five people. You can pull a lever to divert it
to another track, where only one person stands. Do you pull the lever?"

Response B (temp=0.7):
"The trolley problem is a thought experiment in ethics, created by
philosopher Philippa Foot in 1967. It involves a trolley hurtling toward
five people tied to the tracks. You, standing at a lever, can divert the
trolley to a side track where one person is tied. Pulling the lever saves
five lives but directly causes the death of one. The dilemma explores
whether it is morally permissible to cause harm to save a greater number."

Annotator rates: B ≻ A  (B is more informative and historically accurate)
```

After collecting ~33,000 such comparisons across all prompt categories:

### Training the Reward Model

```
Architecture: GPT-3 175B with the final token's representation
              projected to a scalar via a linear layer.

Training:
  L_RM = -E[(x,y_w,y_l)] [ log σ(r_φ(x,y_w) - r_φ(x,y_l)) ]

  Each mini-batch contains multiple completions per prompt.
  For K completions ranked, we get C(K,2) = K(K-1)/2 preference pairs per prompt.

Training time: Several hours (33K examples, reasonable to iterate on)
```

The reward model is then evaluated: does it agree with held-out human preferences? The validation accuracy is ~69-73% for pairwise comparisons — human raters themselves only agree ~77% of the time, so this is approaching human-level consistency.

---

## Chapter 4 — The RLHF/PPO Run

Now the most complex stage: using the reward model to fine-tune the SFT model with PPO.

### Setting Up the Infrastructure

```
Active models in GPU memory simultaneously:
  1. SFT model (being trained):   175B params × 2 bytes = 350GB
  2. Reference model (frozen):    175B params × 2 bytes = 350GB
  3. Reward model (frozen):       175B params × 2 bytes = 350GB
     (in practice, may use a smaller reward model)
  4. Value model (being trained): 175B params × 2 bytes = 350GB

If all models are 175B and stored in BF16:
  Total weights: ~1.4TB

This requires distributing across hundreds of GPUs.
In practice, OpenAI used smaller SFT variants (6B, 1.3B) for faster iteration,
and only trained the 175B InstructGPT version for final deployment.
```

### The PPO Training Loop

```
Iteration 1:
  • Sample 64 prompts from the prompt dataset
  • Generate full responses with current π_θ (SFT model, initially)
  • Score each response: reward = r_φ(x, y) - 0.02 × KL(π_θ || π_ref)
    (β = 0.02 means we're applying a moderate KL penalty)
  • Compute advantage estimates with GAE (γ=1, λ=0.95)
  • PPO clip parameter: ε = 0.2
  • Gradient step on PPO objective + value function loss
  • Clip gradient norm to 1.0

After 1000 iterations:
  • KL divergence from reference: ~2.0 nats (model has moved modestly)
  • Mean reward: significantly increased
  • Qualitative: model is noticeably more helpful, more calibrated

After 10,000 iterations:
  • KL divergence: ~5-8 nats (model has moved substantially)
  • Reward plateauing
  • Signs of mild reward hacking starting to appear (verbosity increase)
  • Training is stopped here (early stopping based on KL + human evals)
```

### The Critical Human Evaluation

Benchmarks can't fully capture alignment quality. The team runs human evaluations:

```
Protocol:
  Show 1000 prompts to human raters (different raters from training annotators)
  Show two responses: one from GPT-3 base, one from InstructGPT
  Ask: "Which response would you prefer from a responsible AI?"

Results (from the InstructGPT paper):
  InstructGPT 1.3B preferred over GPT-3 175B: 71% of the time
  InstructGPT 175B preferred over GPT-3 175B: 85% of the time

  InstructGPT 1.3B (1.3B parameters, RLHF-trained)
  outperforms GPT-3 175B (175B parameters, base model)
  on human preference — 100× fewer parameters, better perceived quality.
```

This result is remarkable: **alignment has a larger impact on perceived quality than 100× more parameters.** The base model knows more, but the aligned model *uses* what it knows better.

---

## Chapter 5 — From InstructGPT to ChatGPT

InstructGPT (March 2022) is the research result. ChatGPT (November 2022) is the product.

### What Changed

**1. Multi-turn conversation format:**

InstructGPT was primarily trained for single-turn interactions. ChatGPT uses a proper multi-turn chat template:

```
InstructGPT format:
  [Instruction]
  ---
  [Completion]

ChatGPT format:
  [System]: You are a helpful assistant.
  [Human]: Tell me about black holes.
  [Assistant]: Black holes are regions of spacetime where...
  [Human]: How do they form?
  [Assistant]: Black holes form when...
```

The SFT training data included full multi-turn conversations, teaching the model to track context across turns.

**2. Safety training was significantly expanded:**

ChatGPT's safety training was much more extensive than InstructGPT's. Additional effort went into:
- Refusing requests for harmful content (malware, weapons, etc.)
- Reducing false factual claims ("hallucinations")
- Handling sensitive topics (medical, legal, political) more carefully

**3. More RLHF iterations:**

ChatGPT went through more rounds of RLHF with a larger annotator team.

**4. Constitutional principles were incorporated:**

Following Anthropic's Constitutional AI approach, explicit principles were incorporated into the feedback guidelines — ensuring annotators evaluated responses against specific criteria rather than vague "quality" judgments.

### The Launch

ChatGPT launched November 30, 2022. It reached 1 million users in 5 days — faster than any product in history at the time.

What users experienced:
```
• Conversations that actually go somewhere (multi-turn coherence)
• A model that says "I don't know" when it doesn't know
• A model that can write code, debug, explain, summarize
• A model that refuses clear harm but isn't overly restrictive
• A model that feels, for the first time, genuinely useful
```

---

## Chapter 6 — The LLaMA 2 Story: Open Source Alignment

Meta took a different path: fully open-source, transparent training procedure, and a novel rejection sampling step.

### The LLaMA 2 Training Pipeline

```
Stage 1: Pre-Training
  • 2 trillion tokens (vs. 1T for LLaMA 1)
  • 7B, 13B, 34B, 70B parameter variants
  • 40% more code data than LLaMA 1
  • Extended context window from 2K → 4K tokens

Stage 2: SFT
  • ~27,000 high-quality instruction-response pairs
  • Quality >> quantity: "fewer but better" philosophy
  • Every example reviewed by Meta annotators

Stage 3: Rejection Sampling Fine-Tuning (RSTF) — NEW
  • For each prompt, sample K=10-20 responses from the SFT model
  • Score each response with the reward model
  • Keep only the highest-scoring response
  • Fine-tune on these "cherry-picked" response pairs (standard SFT)
  
  This is a simplified RL approach: no PPO, no value model.
  Just "generate many and keep the best."

Stage 4: PPO
  • Standard RLHF/PPO using the reward model
  • Iterative: reward model retrained multiple times with new data

Stage 5: Iterative Refinement
  • Meta ran 5 sequential RLHF iterations
  • Each iteration: new SFT data + RSTF + PPO
  • Each subsequent reward model trained on data from the previous policy
```

### LLaMA 2's Dual Reward Models

A novel contribution: two separate reward models, one for helpfulness and one for safety:

```
Reward Model 1: Helpfulness RM
  Trained on: comparisons focused on task quality
  Captures: accuracy, depth, usefulness

Reward Model 2: Safety RM
  Trained on: comparisons focused on harm avoidance
  Captures: harmlessness, appropriateness

Combined reward:
  r_final = r_helpfulness + r_safety × (safety_weight)
  safety_weight is higher for categories with safety concerns
```

This allows independent control of the helpfulness/safety trade-off — a key engineering insight.

---

## Chapter 7 — What We've Learned

### The Training Stack, Summarized

```
Raw Internet Text
         │
         ▼ [Quality pipeline: filter, dedup, score, tokenize]
Cleaned Pre-Training Corpus (~1-15T tokens)
         │
         ▼ [Pre-training: next-token prediction, AdamW, ~1M steps]
Base Model (knows the world, no behavior)
         │
         ▼ [SFT: few thousand to few hundred thousand instruction pairs]
Instruction-Tuned Model (has format, no values)
         │
         ▼ [RLHF or DPO: ~10K-1M preference pairs]
Aligned Model (helpful, harmless, honest)
         │
         ▼ [Optional: LoRA adapters for domain specialization]
Deployed Product (ChatGPT, Claude, LLaMA-Chat, etc.)
```

### The Surprising Lessons

**Lesson 1: Data quality beats data quantity (at the SFT stage)**

InstructGPT's 13,000 high-quality examples produced a model preferred over GPT-3's raw 300B token training. At the SFT stage, a small amount of high-quality targeted data dominates.

**Lesson 2: Alignment beats scale (for perceived quality)**

A 1.3B aligned model beats a 175B base model on human preference. The gap in "apparent helpfulness" is mostly a training objective problem, not a capacity problem.

**Lesson 3: Reward models are the bottleneck**

The ceiling of an RLHF model is determined by the quality of the reward model. A perfect reward model would produce a perfect aligned model. Reward models are far from perfect — which is why alignment remains an active research area.

**Lesson 4: The base model is the foundation**

All the alignment techniques in the world can't overcome fundamental gaps in the base model. A base model that has never seen medical literature cannot be made into a reliable medical advisor through SFT or RLHF. Pre-training determines the knowledge ceiling.

**Lesson 5: Iteration beats single-shot perfection**

The most capable models (GPT-4, Claude 3, LLaMA 3) are products of multiple training iterations, extensive red-teaming, and continuous evaluation. There is no single training run that produces a perfect model. Deployment followed by data collection from real user interactions, followed by retraining — this cycle is how models improve.

---

## Epilogue: The Numbers Behind ChatGPT

A back-of-envelope estimate of what it took to create a ChatGPT-class model:

```
Pre-training:
  Compute: ~10²³ – 10²⁴ FLOPs  (larger than GPT-3)
  Cost:    ~$10M – $50M in compute

SFT data collection:
  Annotators: 40-100 people
  Pairs: ~10,000 – 100,000
  Cost: ~$500K – $2M

Reward model data:
  Comparisons: ~33,000 – 1.4M  
  Cost: ~$1M – $5M (scales with volume)

PPO training:
  Compute: ~10× SFT compute
  Cost: ~$1M – $5M

Infrastructure (storage, networking, monitoring):
  Cost: ~$5M – $20M

Total: ~$20M – $80M to build a frontier aligned LLM from scratch

Annual operational cost to serve at ChatGPT's scale:
  ~$100M+ in compute costs alone

This is why frontier AI remains concentrated in a handful of well-funded organizations.
The open-source community closes this gap not by matching compute,
but by leveraging open base models (LLaMA) and PEFT techniques (LoRA).
```

---

## The End of the Training Story

The model that answers your questions is not "intelligent" in any human sense. It is a weight matrix — a large array of floating-point numbers — that has been iteratively shaped by:

1. **Gradient descent on next-token prediction** — to learn language and knowledge
2. **Gradient descent on human demonstrations** — to learn format and behavior
3. **Reinforcement learning from human preferences** — to learn values

Each stage is a form of optimization. Each optimization moves a distribution. The final distribution — the probability distribution over tokens given a prompt — is one that produces outputs that humans find helpful, honest, and harmless.

Not because the model understands helpfulness. Not because it has values. But because its 70 billion numbers were nudged, over millions of gradient steps, into a configuration that maps your prompts to outputs that humans rate highly.

That is all it is. And it is, by some measures, enough.

---

*Previous: [05 — Efficient Adaptation: PEFT & LoRA](./05_PEFT_and_LoRA.md)*  
*Back to: [README](./README.md)*

---

| Stage | Key Document |
|-------|-------------|
| Data Pipeline | [00 — Data: Pre-Training Corpus](./00_Data_and_Pretraining_Corpus.md) |
| Pre-Training | [01 — Pre-Training](./01_Pretraining.md) |
| SFT | [02 — Supervised Fine-Tuning](./02_Supervised_Finetuning.md) |
| RLHF | [03 — RLHF](./03_RLHF.md) |
| DPO & Modern Alignment | [04 — DPO and Modern Alignment](./04_DPO_and_Modern_Alignment.md) |
| PEFT & LoRA | [05 — PEFT & LoRA](./05_PEFT_and_LoRA.md) |
