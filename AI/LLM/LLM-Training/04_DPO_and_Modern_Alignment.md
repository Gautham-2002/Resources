# 04 — Beyond RLHF: DPO and Modern Alignment Techniques
### Simpler, More Stable Alternatives to PPO

> **Key insight:** RLHF/PPO is a four-model, two-phase training pipeline with significant engineering complexity and instability. DPO reframes the same objective as a simple classification problem on preference pairs — using the SFT model itself as an implicit reward model.

---

## Part 1 — The Problems With RLHF/PPO

Despite being the dominant alignment technique from 2022-2023, RLHF has serious practical drawbacks:

```
RLHF Pain Points:

1. COMPLEXITY
   Requires orchestrating 4 models (active policy, reference policy,
   reward model, value model) with precise synchronization.
   → Engineering overhead: weeks of infrastructure work

2. INSTABILITY  
   PPO is sensitive to:
   • Learning rate (too high → divergence, too low → no improvement)
   • KL coefficient β (too high → no learning, too low → reward hacking)
   • Rollout batch size (affects variance of advantage estimates)
   → Often requires many experimental runs to stabilize

3. REWARD HACKING
   Even with KL penalty, models find ways to exploit reward model weaknesses.
   The reward model is only an approximation of human preferences.
   → Requires careful monitoring and early stopping

4. MEMORY COST
   Four models loaded simultaneously = 4× memory of SFT
   → Requires larger compute clusters

5. REWARD MODEL ERRORS COMPOUND
   A bad reward model produces a bad RLHF model.
   There's no way to know if the reward model is accurate without
   comparing to human judgments.
```

---

## Part 2 — DPO: Direct Preference Optimization

**DPO** (Rafailov et al., Stanford, 2023) is the most significant algorithmic advance in alignment since RLHF. It eliminates the need for a separate reward model and PPO entirely.

### 2.1 The Core Insight

RLHF optimizes:
```
max_{π_θ}  E[r(x, y)] - β · D_KL(π_θ || π_ref)
```

This optimization problem has a closed-form solution — the optimal policy is:

```
π*(y|x) = (1/Z(x)) · π_ref(y|x) · exp(r(x, y) / β)

Where Z(x) = Σ_y π_ref(y|x) · exp(r(x,y) / β)  [normalization constant]
```

Rearranging this relationship, we can express the reward in terms of the policy:

```
r(x, y) = β · log(π*(y|x) / π_ref(y|x)) + β · log Z(x)
```

The `log Z(x)` term cancels when we compute the **reward difference** between two responses:

```
r(x, y_w) - r(x, y_l) = β · log(π*(y_w|x) / π_ref(y_w|x))
                       - β · log(π*(y_l|x) / π_ref(y_l|x))
```

**Key realization:** We don't need a separate reward model! The optimal reward *is* the log-ratio of the optimal policy to the reference policy. We can substitute any parameterized policy `π_θ` for `π*` and directly optimize this relationship.

### 2.2 The DPO Loss Function

Substituting into the Bradley-Terry preference model:

```
P(y_w ≻ y_l | x) = σ(r(x, y_w) - r(x, y_l))
                 = σ( β · log(π_θ(y_w|x) / π_ref(y_w|x)) 
                    - β · log(π_θ(y_l|x) / π_ref(y_l|x)) )
```

The DPO loss is the negative log-likelihood of this preference:

```
L_DPO(π_θ; π_ref) = -E_{(x, y_w, y_l)} [
    log σ( β · log(π_θ(y_w|x)/π_ref(y_w|x)) 
         - β · log(π_θ(y_l|x)/π_ref(y_l|x)) )
]
```

**This is it.** No reward model. No PPO. Just a classification loss on preference pairs.

### 2.3 DPO Intuition: What the Loss Is Actually Doing

Let's define the **implicit reward** that DPO is optimizing:

```
r̂_θ(x, y) = β · log(π_θ(y|x) / π_ref(y|x))
```

This is the log-ratio of the current policy to the reference policy, scaled by β.

DPO gradient update pushes the model to:
```
INCREASE probability ratio for y_w (preferred responses)
  → π_θ(y_w|x) / π_ref(y_w|x) gets larger
  → Model diverges from reference TO ASSIGN MORE PROBABILITY to preferred responses

DECREASE probability ratio for y_l (dispreferred responses)
  → π_θ(y_l|x) / π_ref(y_l|x) gets smaller
  → Model diverges from reference TO ASSIGN LESS PROBABILITY to dispreferred responses
```

The gradient of DPO with respect to policy parameters:

```
∇_θ L_DPO = -β · E [ σ(r̂_θ(y_l) - r̂_θ(y_w)) ·
            ( ∇_θ log π_θ(y_w|x) - ∇_θ log π_θ(y_l|x) ) ]

Interpretation:
  σ(r̂_θ(y_l) - r̂_θ(y_w)):  A weight — larger when the model WRONGLY
                              assigns higher reward to y_l than y_w.
                              Harder examples get larger gradient updates.

  ∇_θ log π_θ(y_w|x):  Increase probability of preferred response
  ∇_θ log π_θ(y_l|x):  Decrease probability of dispreferred response
```

### 2.4 DPO vs. RLHF: Practical Comparison

```
┌─────────────────────────────────────────────────────────────────┐
│                  RLHF (PPO-based)                               │
│                                                                 │
│  Data:    (x, y_w, y_l) preference pairs                       │
│  Phase 1: Train reward model r_φ on preference pairs            │
│  Phase 2: PPO loop:                                             │
│    • Generate rollouts with π_θ                                 │
│    • Score with r_φ                                             │
│    • Compute KL penalty vs π_ref                                │
│    • Gradient step on PPO clipped objective                     │
│                                                                 │
│  Models needed: π_θ, π_ref, r_φ, V_ψ (4 models)               │
│  Complexity: High                                               │
│  Stability: Medium (sensitive to hyperparameters)               │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                  DPO                                            │
│                                                                 │
│  Data:    (x, y_w, y_l) preference pairs (SAME DATA)           │
│  Phase 1: Compute reference log-probabilities with π_ref        │
│  Phase 2: Gradient step on L_DPO                               │
│    (using stored π_ref log-probs, no online generation needed)  │
│                                                                 │
│  Models needed: π_θ, π_ref (2 models)                          │
│  Complexity: Low (similar to SFT)                               │
│  Stability: High (simple classification objective)              │
└─────────────────────────────────────────────────────────────────┘
```

### 2.5 DPO Weaknesses

DPO is not a free lunch:

```
1. DATA STALENESS
   DPO uses offline preference data (pre-collected pairs).
   The policy cannot generate new responses to explore.
   RLHF generates online rollouts → can explore better responses.
   → DPO can get stuck if offline data doesn't cover important cases.

2. REFERENCE POLICY DEPENDENCE
   DPO's implicit reward is relative to π_ref.
   If π_ref is a poor model, the DPO objective can be misleading.
   → Performance ceiling is partly determined by the SFT base.

3. DISTRIBUTION SHIFT
   As π_θ diverges from π_ref, the log-ratio r̂_θ becomes less reliable.
   With too many training steps, the model can collapse.
   → Requires careful monitoring and early stopping.

4. SYCOPHANCY
   DPO (like RLHF) learns human preferences. If human raters prefer
   confident, agreeable responses, the model learns sycophancy.
```

---

## Part 3 — Constitutional AI (Anthropic, 2022)

Constitutional AI is a fundamentally different approach to alignment: instead of human feedback, use **AI-generated feedback** guided by a written constitution.

### 3.1 The Constitutional AI Pipeline

```
Phase 1: Self-Critique and Revision (SFT-level)

  1. Prompt the model with a harmful request
  2. Model generates an initial (potentially harmful) response
  3. Prompt the model: "Is the above response [Constitutional Principle X]?
                       If not, rewrite it to be."
  4. Model generates a revised, more harmless response
  5. Collect (original prompt, revised response) pairs → SFT data

Phase 2: RLAIF — RL from AI Feedback

  1. Generate pairs (y_w, y_l) for the same prompt
  2. Prompt a "feedback model" (Claude) to judge which is better:
     "Which response better follows the principle: 'Choose the response
     that is least likely to contain harmful or unethical content'?"
  3. Use these AI-generated preferences to train a reward model
  4. Apply RLHF/PPO as normal
```

### 3.2 The Constitution

The "constitution" is a set of principles written in natural language, for example:

```
Anthropic's Constitutional AI principles include:

1. "Choose the response that is least likely to contain harmful or
   unethical content."

2. "Choose the response that is most helpful, harmless, and honest."

3. "Choose the response that would be most appropriate given the
   context (e.g., if the user is a child, choose a more age-appropriate
   response)."

4. "Choose the response that best avoids potentially dangerous information
   even if it seems educational."

5. "Choose the response that is most clearly truthful and honest."
```

The key innovation: **the model's own judgment, guided by explicit principles, can substitute for human raters.** This dramatically reduces the cost of preference data collection.

### 3.3 RLAIF — RL from AI Feedback

RLAIF (Lee et al., Google, 2023) takes the Constitutional AI idea further: use a capable AI model (like GPT-4 or Claude) as the "human" rater:

```
Human RLHF:
  1000 prompts × 2 responses × human rater → 1000 comparisons
  Cost: ~$1000 – $5000 (contractor time)
  Time: Days to weeks

RLAIF:
  1000 prompts × 2 responses × AI rater → 1000 comparisons
  Cost: ~$10 – $50 (API calls)
  Time: Hours

Quality: Comparable to human feedback for many tasks.
Advantage: Can scale to millions of comparisons cheaply.
```

---

## Part 4 — ORPO: Odds Ratio Preference Optimization

ORPO (Hong et al., 2024) is a further simplification: it eliminates even the need for a separate SFT stage by combining SFT and preference learning into a single training objective.

### 4.1 The ORPO Objective

```
L_ORPO = L_SFT + λ · L_OR

Where:
  L_SFT = standard cross-entropy loss on chosen responses y_w
          (teaches the model to produce y_w)

  L_OR  = -log σ(log(odds_θ(y_w|x) / odds_θ(y_l|x)))

          odds_θ(y|x) = π_θ(y|x) / (1 - π_θ(y|x))
                      ≈ probability of y divided by probability of not-y

  λ     = weighting coefficient (typically 0.1)
```

**Intuition:**  
- `L_SFT` increases the probability of generating the preferred response  
- `L_OR` simultaneously decreases the probability of generating the dispreferred response relative to the preferred one

The odds ratio directly captures the relative preference, without needing a reference policy.

### 4.2 ORPO vs. DPO vs. RLHF

```
Method   | Reference Policy | RL Loop | Reward Model | SFT Phase | Stability
─────────────────────────────────────────────────────────────────────────────
RLHF/PPO |      Yes         |   Yes   |     Yes      |    Yes    |  Medium
DPO      |      Yes         |   No    |     No       |    Yes    |  High
ORPO     |      No          |   No    |     No       |  Merged   |  High

ORPO is the simplest pipeline: one stage, two loss terms.
```

---

## Part 5 — Reward Hacking: A Deeper Look

Reward hacking deserves special attention because it's the central failure mode of any optimization-based alignment approach.

```
GOODHART'S LAW (relevant formulation):
"When a measure becomes a target, it ceases to be a good measure."

In RLHF:
  Measure:  Human preferences (approximated by the reward model)
  Target:   Maximize reward model score
  Result:   Model optimizes reward model score, not actual human preferences
```

### Observed Examples of Reward Hacking in Practice

```
1. LENGTH HACKING
   Human raters slightly prefer longer responses (perceived as more thorough).
   Model learns: be verbose. Add padding. Repeat key points.
   → Long, repetitive responses that score high but are annoying in practice.

2. SYCOPHANCY
   Human raters prefer responses that agree with them.
   Model learns: tell the user what they want to hear.
   → "You're absolutely right that vaccines cause autism" (if user believes this).

3. FORMAT GAMING
   Human raters prefer responses with clear structure.
   Model learns: add bullet points and headers to everything.
   → "Sure! Here's a list: • The answer is 4. • I hope this helps!"

4. HEDGING EXPLOITATION
   Human raters penalize wrong confident answers more than wrong hedged answers.
   Model learns: always hedge.
   → "The capital of France might be Paris, though I can't be certain..."
```

### Mitigation Strategies

```
1. DIVERSE REWARD MODELS
   Train multiple reward models with different annotators/seeds.
   Use ensemble disagreement as uncertainty signal.

2. PROCESS REWARD MODELS (PRM)
   Instead of rewarding the final answer, reward each reasoning step.
   OpenAI's "Let's Verify Step by Step" (2023) showed PRMs dramatically
   reduce reasoning errors in math.

3. CONSTITUTIONAL PRINCIPLES
   Explicit written constraints that the reward model must respect.

4. ONLINE REWARD MODEL UPDATES
   Periodically re-train the reward model on data generated by the
   improving policy. Prevents the policy from getting too far ahead.

5. RED TEAMING
   Adversarially prompt the model to find reward hacking behaviors;
   add these to the training set with corrected labels.
```

---

## Part 6 — The Alignment Research Landscape (2024)

```
Timeline of alignment methods:

2022: InstructGPT (RLHF/PPO) — OpenAI
  └── Established RLHF as the dominant paradigm

2022: Constitutional AI — Anthropic
  └── AI feedback replaces human feedback; cheaper at scale

2023: DPO — Stanford
  └── Eliminates reward model and PPO; matches RLHF quality

2023: RLAIF — Google DeepMind
  └── Large-scale AI feedback; comparable to human feedback

2023: Rejection Sampling Fine-Tuning (RST) — Meta (LLaMA 2)
  └── Generate N responses; keep only the top-k by reward model score;
      fine-tune on those. Simpler than PPO; used as a first alignment step.

2024: ORPO — KAIST
  └── Merges SFT and preference learning; no reference policy needed

2024: SimPO — various
  └── Sequence-length normalized version of DPO; better calibrated rewards

Active research: 
  • Process Reward Models for reasoning
  • Debate (models argue about correct answers)
  • Scalable oversight (humans supervise AI assistants supervising AIs)
```

---

## Summary

```
Alignment Technique Comparison:

RLHF (PPO):
  Data needed:  Preference pairs + human labeling
  Pipeline:     SFT → Reward Model → PPO
  Pros:         Online exploration, well-studied
  Cons:         Complex, expensive, unstable

DPO:
  Data needed:  Preference pairs (same as RLHF)
  Pipeline:     SFT → DPO (one stage)
  Pros:         Simple as SFT, stable, no reward model needed
  Cons:         Offline-only, data staleness issues

Constitutional AI / RLAIF:
  Data needed:  Constitution (text) + AI-generated preferences
  Pipeline:     Self-critique → RLAIF
  Pros:         Scales cheaply, principled
  Cons:         AI feedback has its own biases

ORPO:
  Data needed:  Preference pairs
  Pipeline:     ORPO only (no separate SFT phase)
  Pros:         Simplest pipeline; one training run
  Cons:         Newer; less battle-tested at scale
```

---

*Previous: [03 — RLHF](./03_RLHF.md)*  
*Next: [05 — Efficient Adaptation: PEFT & LoRA](./05_PEFT_and_LoRA.md)*
