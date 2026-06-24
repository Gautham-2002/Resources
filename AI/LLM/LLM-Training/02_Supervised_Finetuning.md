# 02 — Supervised Fine-Tuning (SFT)
### Teaching the Model to Be an Assistant

> **Key insight:** Pre-training gives the model knowledge but no behavior. SFT gives it behavior — a format, a tone, and the basic ability to follow instructions. But it doesn't give it *values*. That requires the alignment stage.

---

## Part 1 — Why Does a Pre-Trained Model Need Fine-Tuning?

A freshly pre-trained base model has a fundamental problem: it was trained to **complete text**, not to **answer questions**.

```
Prompt to GPT-3 base model:
  "What is the capital of Australia?"

Base model completion (representative):
  "What is the capital of Australia?
   What is the capital of Canada?
   What is the capital of New Zealand?
   ..."

It completes the pattern (a list of geography questions) instead of answering.
```

The model knows the answer — "Canberra" — because it has processed this fact in training data. But it doesn't know to express that knowledge in response to a user's question. The format is wrong.

**Another failure mode — harmful completion:**

```
Prompt:  "Write a step-by-step guide for picking a lock."
Base model: [proceeds to write the guide]
```

The model has no concept of "I shouldn't answer this." It just completes whatever pattern looks most likely given the training data.

SFT fixes the format. RLHF fixes the values. They are separate problems requiring separate solutions.

---

## Part 2 — What Supervised Fine-Tuning Is

SFT is **standard supervised learning** applied to (instruction, response) pairs:

```
Dataset format:
  Each example = (instruction, response)

Examples:

  {"instruction": "Translate 'hello' to Spanish.",
   "response": "Hola"}

  {"instruction": "Write a Python function to reverse a string.",
   "response": "def reverse_string(s):\n    return s[::-1]"}

  {"instruction": "Explain Newton's second law in simple terms.",
   "response": "Newton's second law says that the force acting on an
               object equals its mass times its acceleration (F = ma).
               A heavier object needs more force to accelerate at the
               same rate as a lighter one."}
```

The model is trained to predict the response given the instruction, using the same next-token prediction loss as pre-training.

---

## Part 3 — SFT Data: The Instruction Dataset

### 3.1 The Format: System + User + Assistant

Modern instruction fine-tuned models use a **chat template** — a standardized format for multi-turn conversations:

```
[System Message]
You are a helpful, harmless, and honest AI assistant.

[User Message]
What are the three primary colors?

[Assistant Message]
The three primary colors are red, blue, and yellow (in the traditional
RYB color model used in art), or red, green, and blue (in the RGB
additive color model used in digital displays).

[User Message]
Which model is used in TV screens?

[Assistant Message]
TV screens use the RGB (Red, Green, Blue) additive color model.
Pixels in the display emit light in these three colors, combined at
various intensities to produce all visible colors.
```

This exact format — with special separator tokens marking turns — is tokenized and fed to the model. The model learns that after `<|assistant|>`, it should produce helpful responses.

### 3.2 Loss Masking: Only Train on Responses

During SFT, we compute the cross-entropy loss **only on the assistant's response tokens**, not on the instruction or system message:

```
Token sequence:
[System] You are helpful. [User] What is 2+2? [Assistant] The answer is 4.

Loss mask:
      0          0           0       0     0    1      1      1  1  1  1

Loss is computed only on the highlighted (1) tokens.
```

**Why?** We don't want to penalize the model for the phrasing of the system/user turns — those are given. We only want to optimize the quality of the assistant's output.

If we trained on all tokens equally, the model would also optimize the probability of system messages and user prompts, which is meaningless.

### 3.3 How Instruction Datasets Are Created

**Method 1: Human Expert Annotation**

Pay domain experts (or specialized crowd workers) to write instruction-response pairs.

```
OpenAI's InstructGPT approach (described in the paper, 2022):
  - 40 contractor annotators
  - Guidelines covering: quality, truthfulness, safety, helpfulness
  - ~13,000 prompt-response pairs for initial SFT
  - Expensive: ~$0.50 – $2.00 per example from skilled annotators
```

**Method 2: Self-Instruct (Wang et al., 2022)**

Bootstrap instruction data using the model itself:

```
Algorithm:
  1. Start with 175 hand-written seed tasks
  2. Use the model to generate new instructions: "Generate a new task."
  3. Use the model to generate responses to its own instructions
  4. Filter: remove too-similar instructions (ROUGE similarity > 0.7)
  5. Human verify a sample; add accepted ones back to the pool
  6. Repeat

Result: 52K instruction-response pairs generated from 175 seeds.
  Used to fine-tune LLaMA → Alpaca (Stanford, 2023)
  Cost: ~$500 in API calls (vs. $10M+ for human annotation at scale)
```

**Method 3: FLAN — Finetuned Language Net (Wei et al., 2021)**

Convert existing NLP benchmarks into instruction format:

```
Original NLP dataset (e.g., Stanford NLI):
  Premise: "A man is walking his dog."
  Hypothesis: "A person is outside."
  Label: ENTAILMENT

FLAN instruction format:
  Instruction: "Does the hypothesis follow from the premise?
                Premise: A man is walking his dog.
                Hypothesis: A person is outside."
  Response: "Yes, the hypothesis follows. Walking outside with a dog
             implies the person is outside."
```

FLAN collected 62 NLP datasets, reformatted them with 10+ instruction templates each → 1,800+ task variants.

**Key FLAN finding:** Models fine-tuned on a diverse set of NLP tasks generalize to *unseen* tasks at test time. The instruction format isn't just memorization — it teaches the model the *concept* of instruction following.

**Method 4: Distillation from Stronger Models (Alpaca → Vicuna → ...)**

Fine-tune a smaller open model on outputs from a larger commercial model:

```
Process:
  1. Collect user prompts (ShareGPT conversations)
  2. Generate responses using GPT-4 or Claude
  3. Use these (prompt, GPT-4-response) pairs to fine-tune LLaMA
  4. Result: a smaller open model that partially mimics GPT-4's style

Examples:
  Alpaca:  LLaMA fine-tuned on 52K GPT-3.5 outputs    (Stanford)
  Vicuna:  LLaMA fine-tuned on 70K ShareGPT conversations
  WizardLM: LLaMA fine-tuned on "evolved" GPT-4 outputs
```

⚠️ **Legal/ethical concern:** Most commercial model ToS prohibit using their outputs to train competing models. This method is widely used in the open-source community but is legally ambiguous.

---

## Part 4 — The SFT Training Process

### 4.1 Why It's Cheaper Than Pre-Training

| Dimension | Pre-Training | SFT |
|-----------|-------------|-----|
| Training tokens | 1T – 15T | 100K – 10M |
| Training steps | 1M – 5M | 1K – 50K |
| GPU-hours | 10K – 100K+ | 10 – 500 |
| Data cost | Terabytes | Gigabytes |

SFT uses a tiny fraction of pre-training compute. The model already has the knowledge — SFT just adjusts the output format.

### 4.2 Learning Rate for SFT

A much lower learning rate than pre-training:

```
Pre-training LR:  η ~ 3×10⁻⁴
SFT LR:           η ~ 1×10⁻⁵ to 2×10⁻⁵

Why lower? Catastrophic forgetting (see Part 5).
```

### 4.3 SFT Epochs

Pre-training runs through the data ~1× (with enough data, you don't need to repeat). SFT data is smaller and higher quality — the model trains on it for multiple epochs:

```
Typical SFT: 1 – 3 epochs
  1 epoch = one pass through all instruction-response pairs
  2-3 epochs: small improvement, marginal overfitting risk

More than 3 epochs: high risk of overfitting to the SFT format
  → Model produces the expected format even when wrong
```

---

## Part 5 — Catastrophic Forgetting

**The fundamental risk of fine-tuning:** When you update model weights to optimize SFT loss, you risk damaging the pre-trained capabilities.

```
Before SFT:
  Model can: translate, code, reason, answer factual questions

After bad SFT:
  Model can: follow chat format correctly
  Model cannot: translate (capability degraded)

This is catastrophic forgetting — the model "overwrites" pre-trained
knowledge to minimize the SFT loss.
```

### Why It Happens

SFT data is a narrow distribution. If we update weights aggressively to minimize SFT loss, we shift the weight distribution toward what's optimal for SFT data — potentially moving away from what's optimal for the broader pre-training distribution.

### Mitigations

**1. Low Learning Rate**

Smaller updates → less weight movement → less forgetting.

```
η_SFT = η_pretrain / 10 to / 30
```

**2. Short Training Duration**

Stop before the model has fully "converged" on SFT data:

```
Early stopping: Monitor validation loss on a held-out SFT set.
                Stop when validation loss stops improving.
```

**3. Replay / Mixed Data**

Mix SFT instruction data with a sample of pre-training data:

```
Mixed batch = 80% instruction data + 20% pre-training data

The pre-training data "reminds" the model what it learned,
preventing extreme distribution shift.
```

**4. Parameter-Efficient Fine-Tuning (LoRA)**

Don't update all parameters — only update a small subset. Covered in depth in [05 — PEFT & LoRA](./05_PEFT_and_LoRA.md).

---

## Part 6 — What SFT Produces and What It Doesn't

### What SFT Gives the Model

```
✓ Correct output format (question → answer, not question → more questions)
✓ Instruction-following behavior
✓ Consistent assistant persona
✓ Basic task coverage (summarize, translate, explain, write code, etc.)
✓ Appropriate response length calibration
```

### What SFT Cannot Give the Model

```
✗ Values — knowing what it SHOULDN'T say
✗ Preference calibration — knowing which of two responses is better
✗ Safety — won't refuse harmful requests unless explicitly trained to do so
✗ Knowledge beyond pre-training — can only use what was pre-trained
✗ Robustness — easily manipulated by adversarial prompts
```

### The "Imitation" Problem

SFT teaches the model to **imitate** the format of good responses. But imitation doesn't generalize well:

```
SFT-only model failure:
  The model can imitate a doctor's bedside manner (friendly, reassuring tone)
  But it doesn't know WHEN a doctor would say "I don't know" or
  "you should see a specialist." It hasn't learned epistemic humility.

  It produces authoritative-sounding medical advice with confident wrong answers.
```

This is the motivation for RLHF: teach the model not just to sound helpful, but to actually be helpful and honest.

---

## Part 7 — Instruction Tuning vs. Chat Fine-Tuning

These terms are often used interchangeably but are slightly different:

| Term | Meaning |
|------|---------|
| **Instruction tuning** | Fine-tuning on diverse task-instruction pairs (FLAN-style) |
| **Chat fine-tuning** | Fine-tuning on multi-turn conversational data |
| **SFT** | Umbrella term for any supervised fine-tuning step |

Modern models use both: instruction tuning for task diversity, chat fine-tuning for conversation quality.

---

## Summary Diagram

```
PRE-TRAINED BASE MODEL
  • Knows the world
  • Completes text
  • Has no behavior constraints
        │
        │  [SFT: Fine-tune on ~10K-100K instruction-response pairs]
        │  Loss = cross-entropy on response tokens only
        │  LR = 10-30× smaller than pre-training
        │  Duration = 1-3 epochs
        ▼
SFT MODEL (e.g., LLaMA-2-Chat-7B before RLHF)
  • Follows instructions
  • Responds in assistant format
  • Covers common tasks
  • Still not well-aligned on values
  • Will produce harmful content if asked cleverly
        │
        │  [Next: RLHF]
        ▼
```

The SFT model is dramatically more useful than the base model for everyday tasks. But it is not safe, not consistently honest, and not robust to adversarial prompting. Those properties require the alignment stage.

---

*Previous: [01 — Pre-Training](./01_Pretraining.md)*  
*Next: [03 — RLHF: Learning from Human Preferences](./03_RLHF.md)*
