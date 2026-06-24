# 00 — Math & Conceptual Foundations
### Everything You Need Before Reading the Rest of This Series

> **Who this is for:** Software engineers comfortable with programming but who haven't used linear algebra or calculus since university (or ever). This document builds the mathematical vocabulary used throughout the series — without code, without hand-waving.

---

## Why Math, Not Intuition?

Most LLM explainers use metaphors: "attention is like a spotlight," "the model learns patterns." These are useful starting points but break down quickly. When you need to debug a training run, understand why a model hallucinates, or design a new architecture, you need the underlying mathematics.

The good news: the math required is surprisingly small. You need six concepts well.

---

## Concept 1 — Scalars, Vectors, Matrices, and Tensors

These are the data types of machine learning. Think of them as a hierarchy of dimensionality.

### Scalar

A single real number. No structure, no dimensions.

```
x = 3.14
```

A loss value, a learning rate, a temperature parameter — all scalars.

### Vector

An ordered list of scalars. A vector `v` with `n` elements lives in **n-dimensional space**, written `ℝⁿ`.

```
v = [1.2, -0.5, 0.8, 3.1]   ∈ ℝ⁴
```

A vector can represent:
- A point in n-dimensional space
- A direction and magnitude (arrow in space)
- A token's embedding (its "meaning coordinates")

The **dimension** of a vector is just how many numbers are in it. An embedding vector in GPT-2 has 768 dimensions — it's a list of 768 floats.

### Matrix

A 2D grid of scalars, organized into rows and columns. A matrix `M` with `m` rows and `n` columns lives in `ℝ^(m × n)`.

```
M = [ 1.0   0.5   -1.2 ]    ∈ ℝ^(2 × 3)
    [ 0.3   2.1    0.7 ]
```

Matrices represent:
- **Linear transformations** (rotating, scaling, projecting vectors)
- **Collections of vectors** (each row or column is a vector)
- **Lookup tables** (the embedding matrix: row `i` is the embedding for token `i`)

The notation `M ∈ ℝ^(m × n)` is read "M is a real-valued matrix with m rows and n columns."

### Tensor

A generalization: a tensor is an n-dimensional array of numbers. A scalar is a 0-tensor, a vector is a 1-tensor, a matrix is a 2-tensor.

In deep learning, a **3-tensor** commonly represents a batch of sequences:

```
Shape: (B, T, D)
  B = batch size (number of sequences processed together)
  T = sequence length (number of tokens)
  D = dimension (features per token)
```

For a batch of 8 sentences, each 512 tokens long, with 768 features per token:

```
X ∈ ℝ^(8 × 512 × 768)
```

This is just a 3D array — 8 × 512 × 768 = ~3.1 million floats. Nothing magical. The "tensor" terminology is borrowed from physics but in ML simply means "multi-dimensional array."

**Shape** is the most important property of a tensor. Almost every bug in deep learning is a shape mismatch.

---

## Concept 2 — Matrix Multiplication

This is the single most important operation in all of deep learning. Every layer of a neural network is, at its core, a matrix multiplication.

### Rules

To multiply matrix `A ∈ ℝ^(m × k)` by matrix `B ∈ ℝ^(k × n)`, the **inner dimensions must match** (`k`). The result is `C ∈ ℝ^(m × n)`.

```
A (m × k) × B (k × n) = C (m × n)
```

Each element of the result:

```
C[i, j] = Σ_{l=1}^{k}  A[i, l] · B[l, j]
```

Row `i` of `A` dotted with column `j` of `B`.

### What It Geometrically Means

Multiplying a vector `x ∈ ℝ^n` by a matrix `W ∈ ℝ^(m × n)`:

```
y = W x   ∈ ℝ^m
```

This **transforms** `x` from n-dimensional space into m-dimensional space. It's a linear map — lines stay lines, the origin stays fixed, parallel lines stay parallel.

In a neural network, `W` is a **learned linear transformation**. The weight matrix `W` defines how to project the input representation into the output space. The network learns what transformation is useful by adjusting `W` during training.

### Why Batch Dimensions Work

When your input is a batch `X ∈ ℝ^(B × T × D)` and your weight is `W ∈ ℝ^(D × D')`, the multiplication is applied independently to each of the `B × T` vectors:

```
Y = X W    ∈ ℝ^(B × T × D')
```

The batch and sequence dimensions are just "carried along." The weight `W` is the same for every position and every sequence — this is called **parameter sharing**.

---

## Concept 3 — The Dot Product

The dot product (also called inner product) of two vectors of the same dimension:

```
a = [a₁, a₂, ..., aₙ]
b = [b₁, b₂, ..., bₙ]

a · b = Σᵢ aᵢ bᵢ = a₁b₁ + a₂b₂ + ... + aₙbₙ   ∈ ℝ
```

The result is a single scalar.

### Geometric Interpretation

```
a · b = ‖a‖ · ‖b‖ · cos(θ)
```

Where `θ` is the angle between vectors `a` and `b`, and `‖v‖` is the length (L2 norm) of a vector.

This means:

| Angle between a and b | cos(θ) | Dot product |
|----------------------|--------|-------------|
| 0° (same direction) | 1.0 | Maximum positive |
| 90° (perpendicular) | 0.0 | Zero |
| 180° (opposite) | -1.0 | Maximum negative |

**The dot product measures similarity in direction.** Large positive → vectors point the same way → similar. Near zero → unrelated. Large negative → opposite.

This is why the attention mechanism uses dot products: `Q · K` measures how "relevant" a key is to a query. High dot product = high alignment = high attention weight.

### Relation to Matrix Multiplication

Matrix multiplication is just many dot products organized into a grid. `C = AB` computes the dot product of every row of `A` with every column of `B`.

---

## Concept 4 — The L2 Norm (Vector Length)

The **norm** of a vector is its length in n-dimensional space. The L2 norm:

```
‖v‖ = √(v₁² + v₂² + ... + vₙ²) = √(v · v)
```

This is Pythagoras' theorem generalized to n dimensions.

### Why It Matters in LLMs

**Scaling factor in attention:** The dot product `Q · K` grows with the length (norm) of the vectors. If Q and K have large norms, the dot products are large and destabilize training. Dividing by `√d_k` counteracts this growth.

**Weight decay:** A regularization term that penalizes large weight norms, preventing any single weight from dominating the model.

**RMSNorm:** Normalizes a vector by dividing by its RMS (root mean square), which is closely related to its L2 norm. Forces activations to have a consistent scale as they flow through layers.

### Unit Vectors

A **unit vector** has norm exactly 1. Any vector can be converted to a unit vector by dividing by its norm:

```
v̂ = v / ‖v‖
```

When both `a` and `b` are unit vectors, `a · b = cos(θ)` — the dot product is purely the cosine similarity, independent of vector magnitude. This is used in cosine similarity metrics for embeddings.

---

## Concept 5 — Functions, Derivatives, and Gradients

This is the calculus part. We need it to understand how a model *learns*.

### What Is a Derivative?

For a function `f(x)` that maps a scalar to a scalar, the derivative `f'(x)` or `df/dx` tells you:

> "If I increase `x` by a tiny amount `ε`, how much does `f(x)` change?"

More precisely:

```
f'(x) = lim_{ε→0}  [f(x + ε) - f(x)] / ε
```

The derivative is the **instantaneous rate of change** — the slope of `f` at point `x`.

**Examples:**
```
f(x) = x²      →   f'(x) = 2x
f(x) = exp(x)  →   f'(x) = exp(x)    (its own derivative!)
f(x) = log(x)  →   f'(x) = 1/x
f(x) = c       →   f'(x) = 0         (constant has zero slope)
```

### The Chain Rule

When functions are composed, their derivatives multiply:

```
If y = f(g(x)), then:   dy/dx = (df/dg) · (dg/dx)
```

A deep neural network is a composition of many functions: `L = loss(softmax(linear(relu(linear(...(x))))))`. The chain rule, applied recursively, gives us the derivative of the loss with respect to every parameter. This recursive application is **backpropagation**.

### Gradient: Derivative of a Scalar w.r.t. a Vector

When a scalar function `L` takes a vector `x ∈ ℝⁿ` as input, the **gradient** is:

```
∇ₓL = [∂L/∂x₁,  ∂L/∂x₂,  ...,  ∂L/∂xₙ]   ∈ ℝⁿ
```

It's a vector with the same shape as `x`, where each component is the partial derivative of `L` with respect to that component of `x`.

**The gradient points in the direction of steepest ascent** of `L`. To minimize `L`, move in the *opposite* direction — **gradient descent**:

```
x ← x - η · ∇ₓL
```

Where `η` (eta) is the **learning rate** — a small scalar controlling step size.

### Why This Matters

Every parameter in an LLM — every number in every weight matrix — is one component of a massive combined vector `θ ∈ ℝ^N` where `N` is the number of parameters (e.g., 70 billion for LLaMA 3 70B).

Training computes:

```
∇_θ L = gradient of loss w.r.t. all 70 billion parameters
```

Then updates:

```
θ ← θ - η · ∇_θ L
```

Repeat billions of times, and the model becomes very good at predicting the next token.

### Jacobian: Derivative of a Vector w.r.t. a Vector

When both input and output are vectors (`f: ℝⁿ → ℝᵐ`), the derivative is a **Jacobian matrix** `J ∈ ℝ^(m × n)`:

```
J[i, j] = ∂fᵢ/∂xⱼ
```

The Jacobian describes how each output dimension changes with respect to each input dimension. Backpropagation chains Jacobians together to propagate gradients through every layer.

---

## Concept 6 — Probability and Softmax

### Probability Distribution

A probability distribution over a set of `n` outcomes is a vector `p ∈ ℝⁿ` such that:

```
pᵢ ≥ 0   for all i
Σᵢ pᵢ = 1
```

Each `pᵢ` is the probability of outcome `i`. An LLM's output is a probability distribution over a vocabulary of ~50,000 tokens.

### Softmax

Given any vector of real numbers (logits) `z ∈ ℝⁿ`, softmax converts them into a valid probability distribution:

```
softmax(z)ᵢ = exp(zᵢ) / Σⱼ exp(zⱼ)
```

Properties:
- Output is always in `(0, 1)` — never exactly 0 or 1
- Outputs sum to exactly 1
- Monotone: larger input → larger output (ordering preserved)
- Exponential: a difference of 1 in logits ≈ a factor of `e ≈ 2.7` in probability ratio

### Log and Entropy

The natural logarithm `log(x)` is the inverse of `exp(x)`:

```
log(exp(x)) = x
exp(log(x)) = x
```

Properties:
- `log(1) = 0` — probability of 1 → 0 surprise
- `log(x) → -∞` as `x → 0⁺` — probability near 0 → infinite surprise
- `log(a · b) = log(a) + log(b)` — converts products to sums

**Why log probabilities?** Multiplying many small probabilities underflows to zero numerically. Adding log probabilities is numerically stable:

```
log P(t₁, t₂, ..., tₙ) = log P(t₁) + log P(t₂|t₁) + ... + log P(tₙ|t₁...tₙ₋₁)
```

The **cross-entropy loss** is just negative log probability — how "surprised" the model is:

```
L = -log P(correct token)
```

---

## Concept 7 — Linearity vs. Non-Linearity

### Why Linear Alone Is Not Enough

A composition of linear transformations is still linear. If every layer is `y = Wx`, then a 96-layer network is just one big matrix multiplication — no more expressive than a single layer.

```
Layer 1: y₁ = W₁ x
Layer 2: y₂ = W₂ y₁ = W₂ W₁ x = (W₂W₁) x
Layer 3: y₃ = W₃ y₂ = (W₃W₂W₁) x
```

`W₃W₂W₁` is just another single matrix. All depth would be wasted.

### Activation Functions: The Non-Linear Gate

By applying a **non-linear activation function** between layers, we break linearity and allow the network to learn arbitrary complex functions (universal approximation theorem).

**ReLU (Rectified Linear Unit):**
```
ReLU(x) = max(0, x)
```
- Positive values pass through unchanged
- Negative values are zeroed out
- Simple, efficient, but zero gradient for negative inputs ("dying ReLU")

**GELU (Gaussian Error Linear Unit):**
```
GELU(x) ≈ x · σ(1.702x)    where σ is the sigmoid function
```
- Smooth approximation of ReLU
- Negative values are not hard-zeroed, but heavily suppressed
- Better empirical performance in transformers

**Sigmoid:**
```
σ(x) = 1 / (1 + exp(-x))    ∈ (0, 1)
```
Squashes any input to `(0, 1)`. Used in gating mechanisms (SwiGLU), not in the main computation path of modern LLMs.

---

## Concept 8 — Normalization

**The problem:** During training, as weights change, the distributions of activations (outputs of each layer) shift unpredictably. Deeper layers see chaotic input distributions, making learning slow and unstable.

**The solution:** Normalize activations to have zero mean and unit variance at strategic points.

### Mean and Variance

For a set of values `{x₁, x₂, ..., xₙ}`:

```
Mean:     μ = (1/n) Σᵢ xᵢ

Variance: σ² = (1/n) Σᵢ (xᵢ - μ)²

Std Dev:  σ = √σ²
```

### Normalizing a Vector

To give a vector zero mean and unit variance:

```
x_norm = (x - μ) / σ
```

Then apply learned scale `γ` and shift `β` to let the network control the final distribution:

```
LayerNorm(x) = γ · (x - μ) / σ + β
```

This is **Layer Normalization** — normalizing over the feature dimension (across the `d_model` values for each token position), applied at key points in every transformer block.

---

## Concept 9 — What "Learning" Means, Precisely

A neural network `f(x; θ)` is a function parameterized by a set of weight matrices `θ` (all the `W_Q`, `W_K`, `W_V`, `W₁`, `W₂`, etc.). At initialization, `θ` is random. The model outputs near-uniform probability distributions — it knows nothing.

Training is the process of finding `θ*` that minimizes the average loss over the training dataset:

```
θ* = argmin_θ  E[L(f(x; θ), y)]
```

This is done by gradient descent: repeatedly computing the gradient of the loss and nudging `θ` in the direction that reduces the loss. Over millions of steps and billions of examples, the model learns to assign high probability to likely next tokens — which requires it to implicitly model grammar, facts, reasoning, and style.

The learned `θ` is the model. It is just a large collection of floating-point numbers — about 140GB for a 70B parameter model in BFloat16. Those numbers, combined with the fixed architecture, constitute everything the model "knows."

---

## Putting It Together: The Data Type of Everything

| Concept | Math Object | Example in LLMs |
|---------|------------|-----------------|
| A single number | Scalar ∈ ℝ | Loss value, temperature, learning rate |
| Token embedding | Vector ∈ ℝ^d | 768-dim float array per token |
| A sequence of embeddings | Matrix ∈ ℝ^(T × d) | One sentence |
| A batch of sequences | 3-tensor ∈ ℝ^(B × T × d) | Training batch |
| A weight matrix | Matrix ∈ ℝ^(d × d') | W_Q, W_K, W_V, W₁, W₂ |
| Output probabilities | Vector ∈ ℝ^V | Distribution over 50K-token vocab |
| Gradient of loss | Tensor (same shape as θ) | Direction to update each weight |

---

*This document is the mathematical foundation for the rest of the series.*
*Next: [01 — Tokenization & Embeddings](./01_Tokenization_and_Embeddings.md)*
