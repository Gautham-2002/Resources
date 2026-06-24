# 03 — RLHF: Reinforcement Learning from Human Feedback
### Teaching the Model to Be Good, Not Just Competent

> **Key insight:** RLHF is not primarily about making the model safer. It's about making it *better* — more helpful, more honest, more calibrated — according to a definition of "better" provided by human raters. Safety is a byproduct of getting the values right.

---

## Part 1 — The Alignment Problem

After SFT, the model follows instructions. But it doesn't have *good judgment*.

```
Human annotation reveals a consistent pattern:

Given two responses to the same prompt, human raters systematically prefer:
  ✓ More detailed and accurate explanations
  ✓ Responses that admit uncertainty ("I'm not sure, but...")
  ✓ Responses that stay on topic
  ✓ Appropriate length (not too verbose, not too terse)
  ✓ Better organized, more readable answers

...but SFT cannot capture this. SFT learns FORMAT. Human preference is about QUALITY.
```

**The core challenge:** Quality is hard to define as a loss function. You can't write a mathematical equation that says "this response is better than that response." But humans can compare two responses and say which one they prefer.

RLHF turns this human comparison signal into a training objective.

---

## Part 2 — RLHF Overview: The Three Stages

```
RLHF consists of three stages run sequentially:

Stage 1: Supervised Fine-Tuning (SFT)
  └── Already done! (See previous document)

Stage 2: Reward Model Training
  ├── Collect human preference data: (prompt, response_A, response_B, human_choice)
  └── Train a reward model to predict human preferences

Stage 3: RL Fine-Tuning with PPO
  ├── Use the reward model as a scalar signal
  ├── Use PPO to maximize expected reward
  └── Apply KL penalty to prevent the model from drifting too far from SFT behavior
```

---

## Part 3 — Stage 2: Training the Reward Model

### 3.1 Collecting Preference Data

For each prompt, generate **two** different responses (from the SFT model, or different sampling temperatures):

```
Prompt:  "Explain quantum entanglement simply."

Response A:  "Quantum entanglement is when two particles become linked
             in such a way that the state of one instantly determines
             the state of the other, regardless of distance."

Response B:  "Quantum entanglement is a quantum mechanical phenomenon
             where two particles interact and become correlated. The
             quantum state of each cannot be described independently
             of the others, even when separated by large distances.
             Einstein called this 'spooky action at a distance.'"

Human rater chooses: B preferred over A
```

A human rater evaluates this and marks which response they prefer (or "tie"). They don't give scores — just a preference.

This comparative format is deliberate:
- Absolute rating (1-5 stars) has high inter-rater variance (what's a "4" to me is a "3" to you)
- **Relative comparison** is much more consistent between raters

### 3.2 The Bradley-Terry Preference Model

Human preferences are modeled probabilistically using the **Bradley-Terry model**:

```
Given two responses y_w (preferred/"winner") and y_l (not preferred/"loser"):

P(y_w ≻ y_l | x) = σ(r(x, y_w) - r(x, y_l))

Where:
  r(x, y) = reward model score for prompt x, response y
  σ       = sigmoid function σ(z) = 1/(1 + e^{-z})
```

**Intuition:** If the reward model assigns a much higher score to y_w than y_l, the probability of preferring y_w approaches 1. If scores are equal, probability is 0.5 (coin flip). The model is trained to separate winner from loser scores.

### 3.3 The Reward Model Architecture

The reward model is:
1. **Initialized** from the SFT model weights (same transformer architecture)
2. **Modified**: the final "next-token prediction" head is replaced by a single scalar output head

```
Architecture change:
  SFT model:    [Transformer] → [Linear: d_model → V] → logits (vocab-sized)
  Reward model: [Transformer] → [Linear: d_model → 1] → scalar reward

The reward model takes a complete (prompt, response) and outputs one number.
That number represents "how good is this response?"
```

### 3.4 Reward Model Loss Function

```
L_RM = -E_{(x, y_w, y_l)} [ log σ(r_θ(x, y_w) - r_θ(x, y_l)) ]
```

This is the **binary cross-entropy** over pairwise preferences. We're training the model to assign higher scores to preferred responses than dispreferred ones.

Expanding:
```
When r(x, y_w) >> r(x, y_l):   σ(large positive) → 1   → log(1) → 0 (no loss)
When r(x, y_w) << r(x, y_l):   σ(large negative) → 0   → log(0) → ∞ (high loss)
When r(x, y_w) ≈ r(x, y_l):    σ(0) = 0.5          → log(0.5) → moderate loss
```

### 3.5 How Much Preference Data Is Needed?

```
InstructGPT (OpenAI, 2022):
  ~33,000 pairwise comparisons for the reward model
  Cost: hundreds of hours of annotator time

Anthropic's Constitutional AI (2022):
  Tens of thousands of comparisons
  Used both humans and AI feedback

Llama 2 (Meta, 2023):
  ~1.4M pairwise comparisons (much larger)
  Collected over ~27,000 human-annotated prompts
```

The reward model quality directly determines the ceiling of the final model's alignment quality. Bad reward model → misaligned model.

---

## Part 4 — Stage 3: PPO — Reinforcement Learning Fine-Tuning

### 4.1 The RL Setup

With a trained reward model, we now formulate LLM training as a **reinforcement learning** problem:

```
RL Framework for LLMs:
  Environment:  The prompt space (distribution of user queries)
  Agent:        The language model π_θ
  State:        Current token sequence (prompt + generated tokens so far)
  Action:       Sample the next token from π_θ's distribution
  Episode:      Complete a full response (until EOS token)
  Reward:       r(x, y) from the reward model, given at episode end
```

This is a **sparse reward** problem — the reward is only given at the end of the episode, not after each token.

### 4.2 The PPO Objective

PPO (Proximal Policy Optimization, Schulman et al., 2017) is the RL algorithm used in RLHF. The key idea: update the policy in the direction that increases expected reward, but don't update it *too much* in a single step (keep it "proximal" to the current policy).

The full RLHF objective:

```
max_{π_θ}  E_{x~D, y~π_θ(·|x)} [ r(x, y) - β · D_KL(π_θ(·|x) || π_ref(·|x)) ]

Where:
  r(x, y)        = reward model score (what we're maximizing)
  π_ref          = frozen SFT model (the reference policy)
  D_KL(π_θ||π_ref) = KL divergence between current policy and reference
  β              = penalty strength (typically 0.01 – 0.1)
```

### 4.3 Understanding the KL Penalty

**Why do we need the KL penalty?**

Without it, the RL model will engage in **reward hacking** — finding outputs that score high on the reward model without actually being good:

```
Example of reward hacking without KL penalty:

Prompt: "What is 2+2?"

Reward model was trained on human preferences. Humans tend to prefer:
  - Longer responses
  - More confident responses
  - Responses that include context

Model discovers: "The answer is 4. Mathematics tells us that when we
combine two and two, through the principles of arithmetic established
by centuries of mathematical thought, we arrive at the integer four.
Four is also the square of two, a perfect square, and an even number.
..."

This scores high on the reward model but is obviously not better.
The model has hacked the reward signal.
```

The KL penalty prevents this. It penalizes the model proportionally to how far it has moved from the SFT model's behavior. The sycophantic response above would be penalized because it diverges heavily from what the SFT model would produce.

```
D_KL(π_θ(·|x) || π_ref(·|x)) = Σ_t π_θ(t|x) · log(π_θ(t|x) / π_ref(t|x))

High KL = model is producing text very different from SFT baseline
Low KL  = model stays close to SFT baseline

The β term controls the trade-off:
  High β: Very conservative; model barely moves from SFT
  Low β:  Aggressive RL optimization; risk of reward hacking
```

### 4.4 The PPO Algorithm in Detail

PPO alternates between collecting rollouts and updating the policy:

```
For each PPO iteration:

  [Rollout Phase]
  1. Sample prompts x from the prompt dataset
  2. Generate full responses y using current policy π_θ
  3. Score each response: reward = r(x, y) - β · D_KL(π_θ || π_ref)
  4. Compute advantage estimates using Generalized Advantage Estimation (GAE)

  [Update Phase]
  5. Compute the PPO clipped objective:
     L_PPO = E_t [ min( ρ_t · A_t, clip(ρ_t, 1-ε, 1+ε) · A_t ) ]

     Where:
       ρ_t = π_θ(a_t|s_t) / π_old(a_t|s_t)  (probability ratio)
       A_t = advantage at step t
       ε   = clip parameter (typically 0.2)

  6. Add value function loss (trains the value head, which estimates future reward)
  7. Gradient step on L_PPO
  8. Repeat
```

The **clip** operation is PPO's key innovation: if the policy ratio `ρ_t` strays outside `[1-ε, 1+ε]`, the gradient is zeroed out. This prevents large, destabilizing updates.

### 4.5 Training Infrastructure for PPO

PPO is significantly more complex than SFT to implement:

```
PPO requires running FOUR models simultaneously:
  1. Active policy π_θ     (the model being trained — updated every step)
  2. Reference policy π_ref (frozen SFT model — for KL computation)
  3. Reward model r_φ       (frozen — scores completed responses)
  4. Value model V_ψ        (estimates expected future reward — updated every step)

Memory footprint for a 7B PPO training run:
  4 × 7B params × 2 bytes (BF16) = 56GB just for model weights
  + optimizer states, activations, gradients
  → Requires ~8-16 A100 GPUs (80GB each)

This is 4-8× more complex to orchestrate than SFT.
```

Frameworks like `trl` (HuggingFace), `OpenRLHF`, and Anthropic's internal systems handle this orchestration.

---

## Part 5 — The Alignment Tax

One well-documented side effect of RLHF: **the alignment tax** — a small degradation in raw capability.

```
GPT-3 175B (base):        High capability, willing to answer anything
InstructGPT 1.3B (RLHF):  Lower parameter count, but human raters prefer it

The RLHF model is:
  ✓ More helpful on actual user tasks
  ✓ More honest (admits uncertainty)
  ✗ Slightly worse on some academic benchmarks (TruthfulQA, coding)

Why the tax?
  RLHF shifts the distribution. The model produces "safer" text, which
  is sometimes less informative. It becomes more hedged, adds more
  caveats, and occasionally refuses legitimate questions.
```

**Minimizing the tax:**
- Careful prompt distribution design (diverse prompts → less overfitting)
- Conservative KL coefficient (don't move too far from SFT)
- High-quality reward model training data (human raters who value capability, not just safety)

---

## Part 6 — Visualizing the Training Dynamics

### How the Loss Landscape Changes

```
Pre-training loss landscape (schematic):

         ↑ Loss
         │      *
         │    *   *
         │  *       *
         │*           *──────── θ_pretrained (broad minimum)
         └─────────────────────► Parameter Space

After RLHF:

         ↑ Loss
         │
         │    *                 *
         │  *   *             *   *
         │*       ***───***         *
         └─────────────────────────► Parameter Space
                  θ_RLHF
                  (moved from pre-training minimum, constrained by KL)
```

The KL penalty prevents the RLHF model from moving too far. The reward signal pulls it toward higher-reward regions. The result is a model that balances capability retention and alignment.

### Reward During PPO Training

```
Mean Reward During PPO Training:

  ↑
  │                          ╭─────────────────────────────── (plateau)
  │                      ╭───╯
  │                  ╭───╯
  │              ╭───╯
  │          ╭───╯
  │      ╭───╯
  │  ╭───╯
  │──╯
  └──────────────────────────────────────────────► PPO steps

KL divergence from SFT reference:

  ↑
  │                                           ╭───────────────
  │                                      ╭───╯
  │                                 ╭────╯
  │                           ╭─────╯
  │                    ╭──────╯
  │           ╭────────╯
  │───────────╯
  └──────────────────────────────────────────────► PPO steps
```

The reward increases rapidly at first (easy improvements), then plateaus. KL divergence grows throughout — the model is constantly moving away from the SFT baseline, but the penalty term prevents it from going too far.

---

## Part 7 — What RLHF Produces

```
SFT Model:
  • Follows instructions: ✓
  • Helpful and calibrated: ~
  • Refuses harmful requests: ✗
  • Acknowledges uncertainty: ~
        │
        │  [RLHF: PPO with reward model]
        ▼
RLHF Model (e.g., InstructGPT, LLaMA-2-Chat):
  • Follows instructions: ✓
  • Helpful and calibrated: ✓ (strongly improved)
  • Refuses harmful requests: ✓ (with good training data)
  • Acknowledges uncertainty: ✓
  • Honest about limitations: ✓
  • Risk: sycophancy (tells users what they want to hear)
  • Risk: over-refusal (refuses legitimate requests)
```

RLHF is powerful but expensive and unstable. This drove research into simpler alternatives — most notably DPO.

---

## Summary: RLHF Mechanics

```
1. Collect preference data:
   (prompt, response_A, response_B) → human labels: A ≻ B or B ≻ A

2. Train reward model r_φ:
   Objective: r(x, y_w) > r(x, y_l) for all preference pairs
   Architecture: SFT model + scalar head

3. Fine-tune with PPO:
   Objective: max E[r(x,y)] - β·KL(π_θ || π_ref)
   KL penalty prevents reward hacking / keeps model near SFT baseline

4. Monitor:
   • Reward: should increase
   • KL divergence: should stay bounded
   • Capability benchmarks: should not degrade significantly
```

---

*Previous: [02 — Supervised Fine-Tuning (SFT)](./02_Supervised_Finetuning.md)*  
*Next: [04 — Beyond RLHF: DPO and Modern Alignment](./04_DPO_and_Modern_Alignment.md)*
