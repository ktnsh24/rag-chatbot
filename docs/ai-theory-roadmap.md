# AI Engineering — Complete Theory & Learning Roadmap

> **Purpose:** A structured, in-depth learning plan to become an AI Engineer.
> This is not a surface-level overview — it's the actual theory you need to
> understand, with the math intuition, the "why" behind every concept, and
> concrete steps to build real understanding.
>
> **Prerequisites:** You already know Python, FastAPI, AWS, Azure, Terraform,
> Git, and data engineering concepts (ETL, SQL, data quality).

---

## Table of Contents

### Part 1: Foundations
1. [What is AI Engineering?](#1-what-is-ai-engineering)
2. [Neural Networks — The Absolute Basics](#2-neural-networks--the-absolute-basics)
3. [The Transformer — The Architecture Behind Everything](#3-the-transformer--the-architecture-behind-everything)

### Part 2: Large Language Models (LLMs)
4. [How LLMs Work — From Training to Inference](#4-how-llms-work--from-training-to-inference)
5. [Tokenisation — How LLMs Read Text](#5-tokenisation--how-llms-read-text)
6. [The Attention Mechanism — How LLMs "Think"](#6-the-attention-mechanism--how-llms-think)
7. [Inference — How LLMs Generate Text](#7-inference--how-llms-generate-text)
8. [Temperature, Top-P, and Sampling — Controlling Output](#8-temperature-top-p-and-sampling--controlling-output)

### Part 3: Embeddings & Vector Search
9. [Embeddings — The Mathematical Foundation](#9-embeddings--the-mathematical-foundation)
10. [Vector Similarity — Cosine, Dot Product, Euclidean](#10-vector-similarity--cosine-dot-product-euclidean)
11. [Vector Databases — How They Work](#11-vector-databases--how-they-work)

### Part 4: RAG (Retrieval-Augmented Generation)
12. [RAG — The Complete Theory](#12-rag--the-complete-theory)
13. [Chunking Strategies — Deep Dive](#13-chunking-strategies--deep-dive)
14. [Retrieval Strategies — Beyond Basic Search](#14-retrieval-strategies--beyond-basic-search)
15. [RAG Evaluation — Measuring Quality](#15-rag-evaluation--measuring-quality)

### Part 5: Prompt Engineering
16. [Prompt Engineering — The Science](#16-prompt-engineering--the-science)
17. [Advanced Prompting Techniques](#17-advanced-prompting-techniques)

### Part 6: AI Agents
18. [What Are AI Agents — Theory & Architecture](#18-what-are-ai-agents--theory-and-architecture)
19. [Tool Use — How Agents Interact With the World](#19-tool-use--how-agents-interact-with-the-world)
20. [Agent Patterns — ReAct, Plan-and-Execute, Reflection](#20-agent-patterns--react-plan-and-execute-reflection)
21. [Agent Memory — Short-Term and Long-Term](#21-agent-memory--short-term-and-long-term)

### Part 7: MCP (Model Context Protocol)
22. [MCP — Theory & Architecture](#22-mcp--theory-and-architecture)
23. [Building MCP Servers & Clients](#23-building-mcp-servers-and-clients)

### Part 8: The Learning Plan
24. [Week-by-Week Study Plan](#24-week-by-week-study-plan)
25. [Hands-On Exercises](#25-hands-on-exercises)
26. [Recommended Resources](#26-recommended-resources)

---

# Part 1: Foundations

## 1. What is AI Engineering?

AI Engineering is a **new discipline** that sits between Software Engineering
and Machine Learning:

```
Machine Learning Engineer          AI Engineer              Software Engineer
─────────────────────────          ────────────             ─────────────────
Trains models from scratch         Uses pre-trained models  Builds applications
Needs PhD-level math               Needs practical math     Needs no ML math
Works with datasets & GPUs         Works with APIs & prompts Works with APIs & DBs
Months to build a model            Days to build an AI app  Days to build an app
Focus: model accuracy              Focus: system quality    Focus: functionality
```

### What an AI Engineer actually does

1. **Selects** the right model for the task (Claude vs GPT-4 vs Llama)
2. **Designs** the pipeline (RAG, agents, fine-tuning)
3. **Engineers prompts** to get the best output quality
4. **Builds infrastructure** to serve AI at scale
5. **Evaluates** AI output quality systematically
6. **Monitors** AI behaviour in production
7. **Optimises** cost, latency, and quality trade-offs

### You do NOT need to

- Train models from scratch
- Understand backpropagation math in detail
- Write CUDA kernels
- Have a PhD

### You DO need to understand

- How LLMs work (at a conceptual level)
- Embeddings and vector search
- Prompt engineering
- RAG and agent patterns
- Evaluation and monitoring
- Cost and latency trade-offs

---

## 2. Neural Networks — The Absolute Basics

### What is a neural network?

A neural network is a **function that learns patterns from data**. At its core,
it's just matrix multiplication + a simple non-linear function, repeated many times.

### The simplest neural network (one neuron)

```
Inputs           Weights          Output
──────           ───────          ──────
x₁ = 0.5  ──→  w₁ = 0.3  ──┐
                              ├──→  sum = (0.5×0.3) + (0.8×0.7) = 0.71
x₂ = 0.8  ──→  w₂ = 0.7  ──┘                │
                                              ▼
                                    activation(0.71) = 0.67
                                    (e.g., sigmoid squashes to 0-1)
```

A neuron: **multiply inputs by weights, add them up, apply activation function**.

### A layer = many neurons

```
Input Layer      Hidden Layer       Output Layer
(your data)      (learned features) (prediction)

[x₁] ──────┐
            ├──→ [h₁] ──────┐
[x₂] ──────┤               ├──→ [output]
            ├──→ [h₂] ──────┘
[x₃] ──────┘

Each arrow has a "weight" (a number the network learns).
Learning = adjusting these weights to make better predictions.
```

### Why this matters for AI Engineering

You don't need to train networks, but you need to know:

- **More parameters = smarter model** (GPT-4 has ~1.8 trillion parameters/weights)
- **Training = adjusting weights** based on examples (done by OpenAI/Anthropic)
- **Inference = running the learned function** on new input (what you pay for)
- **The model IS the weights** — when you call Bedrock, you're using Anthropic's weights

---

## 3. The Transformer — The Architecture Behind Everything

### Why this matters

Every LLM you'll work with (GPT-4, Claude, Llama, Mistral) is a **Transformer**.
Understanding the Transformer means understanding the foundation of modern AI.

### The key innovation: Attention

Before Transformers (2017), AI processed text word by word, left to right.
The Transformer processes **all words simultaneously** and learns which words
should "pay attention to" which other words.

```
Input: "The cat sat on the mat because it was tired"

Question the model answers: What does "it" refer to?

Attention mechanism:
  "it" pays high attention to "cat"    (0.7)  ← "it" means "the cat"
  "it" pays low attention to "mat"     (0.1)
  "it" pays low attention to "sat"     (0.05)
  "it" pays medium attention to "tired" (0.15) ← related context
```

This ability to connect distant words is what makes Transformers powerful.

### Transformer architecture (simplified)

```
Input text → Tokenise → Embed → [Transformer Block × N] → Output

Each Transformer Block:
┌─────────────────────────────────────┐
│  1. Self-Attention                  │  "Which other tokens matter for
│     (which words relate to which?)  │   understanding this token?"
│                                     │
│  2. Feed-Forward Network            │  "Given these relationships,
│     (process the information)       │   what features to extract?"
│                                     │
│  3. Layer Normalisation             │  "Keep the numbers stable"
│     + Residual Connection           │   (technical necessity)
└─────────────────────────────────────┘

GPT-4:  ~120 Transformer blocks
Claude: ~80+ Transformer blocks (estimated)
```

### The key numbers

| Model | Parameters | Transformer Blocks | Context Window |
| --- | --- | --- | --- |
| GPT-4o | ~200B (estimated) | ~120 | 128K tokens |
| Claude 3.5 Sonnet | ~70B (estimated) | ~80 | 200K tokens |
| Llama 3.1 70B | 70B | 80 | 128K tokens |
| Llama 3.1 8B | 8B | 32 | 128K tokens |

**More parameters = more knowledge captured, but slower and more expensive.**

---

# Part 2: Large Language Models (LLMs)

## 4. How LLMs Work — From Training to Inference

### The three phases of an LLM's life

```
Phase 1: PRE-TRAINING (done by OpenAI/Anthropic — NOT your job)
────────────────────
- Train on internet-scale text (trillions of tokens)
- The model learns: grammar, facts, reasoning, coding, etc.
- Cost: $10M - $100M+ in GPU compute
- Time: months
- Result: a "base model" that can predict the next word

Phase 2: FINE-TUNING / ALIGNMENT (done by OpenAI/Anthropic — NOT your job)
──────────────────────────────
- RLHF (Reinforcement Learning from Human Feedback)
- Humans rate model outputs → model learns to give helpful, harmless answers
- Instruction following: model learns to follow system prompts
- Result: a "chat model" (what you use via API)

Phase 3: INFERENCE (YOUR job as an AI Engineer)
────────────────
- You send a prompt → model generates a response
- You pay per token (input + output)
- You control: temperature, max_tokens, system prompt
- You evaluate: quality, latency, cost
```

### What the model actually learned

```
Pre-training objective: "Given the previous tokens, predict the next token"

Training example:
  Input:  "The capital of France is"
  Target: "Paris"

After billions of such examples, the model implicitly learns:
  - Language structure (grammar, syntax)
  - World knowledge (facts, relationships)
  - Reasoning patterns (logic, math)
  - Code patterns (syntax, algorithms)
  - Writing styles (formal, casual, technical)
```

### Why this matters for you

When you send a prompt to Claude/GPT-4:
- The model is NOT "searching the internet"
- The model is NOT "looking things up"
- The model is **generating the most likely next tokens** based on patterns
  it learned during training
- That's why it can hallucinate — it generates plausible-sounding text
  even when it doesn't "know" the answer
- That's why RAG works — you provide the facts in the context, so the model
  doesn't need to rely on its training knowledge

---

## 5. Tokenisation — How LLMs Read Text

### Why tokenisation matters

LLMs don't read characters or words. They read **tokens** — subword units
that balance vocabulary size with coverage.

### How it works

```
Text:    "Unbelievable! The refund process takes 14 business days."
Tokens:  ["Un", "believ", "able", "!", " The", " refund", " process",
          " takes", " 14", " business", " days", "."]
Count:   12 tokens

Each token maps to a number (token ID):
  "Un"       → 1844
  "believ"   → 39377
  " refund"  → 24339
  " 14"      → 220
  ...
```

### Why subwords, not words?

| Approach | Vocabulary size | Problem |
| --- | --- | --- |
| Characters (a, b, c...) | 256 | Too fine — "refund" = 6 tokens, very slow |
| Words (refund, policy...) | 500,000+ | Too many — rare words not covered |
| **Subwords (BPE)** | 50,000-100,000 | Just right — common words = 1 token, rare words = 2-3 |

### The BPE algorithm (Byte Pair Encoding)

This is how the tokeniser vocabulary is built:

```
Step 1: Start with all individual characters
  Vocabulary: [a, b, c, d, e, ..., z, space, ...]

Step 2: Count the most frequent pair of adjacent tokens
  "th" appears 1,000,000 times → merge into one token "th"
  Vocabulary: [a, b, c, ..., z, space, ..., "th"]

Step 3: Repeat
  "the" appears 800,000 times → merge "th" + "e" → "the"
  "in" appears 700,000 times → merge "i" + "n" → "in"
  ...

After 50,000 merges: you have a vocabulary of 50,000 tokens
  Common words = 1 token: "the", "and", "refund"
  Rare words = 2-3 tokens: "un" + "believ" + "able"
```

### Practical implications for your project

1. **Cost** — you pay per token, so fewer tokens = cheaper
2. **Context window** — 200K tokens ≈ 150K words ≈ a 500-page book
3. **Chunk size** — your 1000-character chunks ≈ 250 tokens each
4. **A full RAG query** — ~1500 input tokens + ~200 output tokens ≈ $0.004

### Try it yourself

```python
# pip install tiktoken
import tiktoken

enc = tiktoken.encoding_for_model("gpt-4o")
text = "What is the refund policy?"
tokens = enc.encode(text)
print(f"Text: '{text}'")
print(f"Tokens: {tokens}")
print(f"Count: {len(tokens)}")
print(f"Decoded: {[enc.decode([t]) for t in tokens]}")
```

---

## 6. The Attention Mechanism — How LLMs "Think"

### The intuition

Attention answers the question: **"When processing this token, how much
should I look at every other token?"**

### The math (simplified)

For each token, the model computes three vectors:
- **Query (Q)**: "What am I looking for?"
- **Key (K)**: "What do I contain?"
- **Value (V)**: "What information do I carry?"

```
Token: "it" (in "The cat sat on the mat because it was tired")

Q ("it" asks): "I'm a pronoun — what noun do I refer to?"
K ("cat" offers): "I'm a noun — I could be what you refer to"
K ("mat" offers): "I'm a noun — I could be what you refer to"

Attention score = how well Q matches each K:
  Q("it") · K("cat") = 0.9  ← high match!
  Q("it") · K("mat") = 0.3  ← low match
  Q("it") · K("sat") = 0.1  ← very low

Softmax normalises to probabilities:
  Attention to "cat" = 0.7
  Attention to "mat" = 0.2
  Attention to "sat" = 0.1

Final output = weighted sum of Values:
  output = 0.7 × V("cat") + 0.2 × V("mat") + 0.1 × V("sat")
  → The representation of "it" now carries mostly "cat" information
```

### Multi-head attention

The model doesn't compute attention once — it computes it **many times in parallel**
(called "heads"), each focusing on different relationships:

```
Head 1: "What does this pronoun refer to?" (coreference)
Head 2: "What's the verb for this subject?" (syntax)
Head 3: "What's the sentiment?" (emotion)
Head 4: "What's the topic?" (semantics)
...
Head 64: (some abstract learned relationship)
```

### Why this matters for prompts

Understanding attention explains why prompt engineering works:

```
Bad prompt:   "Tell me about refunds"
  → "refunds" has attention connections, but they're spread thin

Good prompt:  "Based on the context documents below, what is the refund
               policy? Only use facts from the context."
  → "context documents" creates strong attention to the context
  → "only use facts" creates attention to the constraint
  → "refund policy" creates focused attention to relevant chunks
```

---

## 7. Inference — How LLMs Generate Text

### Autoregressive generation

LLMs generate text **one token at a time**, always looking at everything
generated so far:

```
Input: "The refund policy states that"

Step 1: Model sees "The refund policy states that"
        → Predicts next token: "refunds" (probability: 0.45)
        
Step 2: Model sees "The refund policy states that refunds"
        → Predicts next token: "are" (probability: 0.72)
        
Step 3: Model sees "The refund policy states that refunds are"
        → Predicts next token: "processed" (probability: 0.38)
        
Step 4: Model sees "The refund policy states that refunds are processed"
        → Predicts next token: "within" (probability: 0.61)

... continues until max_tokens or a stop token
```

### Why this is slow

Each step requires running the **entire model** (all 80+ transformer blocks).
For Claude 3.5 Sonnet generating 200 tokens:
- 200 × full model forward pass
- Each pass: billions of matrix multiplications
- That's why it takes 2-3 seconds even on enterprise GPUs

### KV Cache — Why input tokens are cheaper

```
First token:  Process ALL input tokens (expensive, but done once)
              → Cache the Key and Value matrices (KV cache)
              
Second token: Only process the new token + look up cached KV
              → Much faster!

That's why:
  - Input tokens: $0.003/1K (processed once, in parallel)
  - Output tokens: $0.015/1K (processed one at a time, sequential)
  - Output is 5× more expensive because each token needs a full pass
```

---

## 8. Temperature, Top-P, and Sampling — Controlling Output

### What temperature does

At each step, the model produces probabilities for EVERY token in its vocabulary:

```
Next token probabilities (temperature=0):
  "processed"  → 0.38
  "handled"    → 0.25
  "completed"  → 0.15
  "refunded"   → 0.10
  "done"       → 0.05
  ...          → (50,000 other tokens with tiny probabilities)

Temperature = 0: ALWAYS pick "processed" (highest probability)
                 → Deterministic, factual, repetitive

Temperature = 0.5: Usually pick "processed", sometimes "handled"
                    → Mostly consistent, slight variety

Temperature = 1.0: Pick proportional to probability
                    → Creative, varied, sometimes surprising

Temperature = 1.5+: Even rare tokens get picked
                     → Wild, unpredictable, often nonsensical
```

### The formula

```
adjusted_probability = softmax(logits / temperature)

temperature < 1: Sharpens distribution (high-probability tokens dominate)
temperature = 1: Original distribution
temperature > 1: Flattens distribution (low-probability tokens get a chance)
```

### Top-P (nucleus sampling)

Instead of considering all 50,000 tokens, only consider the smallest set
whose cumulative probability exceeds P:

```
Top-P = 0.9:
  "processed"  → 0.38  (cumulative: 0.38)
  "handled"    → 0.25  (cumulative: 0.63)
  "completed"  → 0.15  (cumulative: 0.78)
  "refunded"   → 0.10  (cumulative: 0.88)
  "done"       → 0.05  (cumulative: 0.93) ← stop here (>0.9)
  
  Only these 5 tokens are candidates. All others are excluded.
```

### What we use in this project and why

```python
# src/llm/aws_bedrock.py
inferenceConfig={
    "temperature": 0.1,   # Almost deterministic — we want factual answers
    "topP": 0.9,          # Cut off very unlikely tokens
    "maxTokens": 2048,    # Stop after 2048 tokens (~1500 words)
}
```

For RAG: **low temperature (0.1)** because we want the model to faithfully
reproduce information from the context, not be creative.

---

# Part 3: Embeddings & Vector Search

## 9. Embeddings — The Mathematical Foundation

### What embeddings really are

An embedding is a **learned mapping from discrete objects (words, sentences)
to points in a continuous vector space**, where distance corresponds to
semantic similarity.

### The intuition: a meaning map

Imagine a 2D map where every sentence has coordinates:

```
                    ↑ about "money"
                    │
  "refund policy"   │  "return the item"
         ×          │        ×
                    │
  "get money back"  │  "cash refund"
         ×          │      ×
                    │
 ───────────────────┼──────────────────→ about "products"
                    │
  "delivery time"   │  "shipping speed"
         ×          │        ×
                    │
  "when arrives"    │  "tracking number"
         ×          │        ×
                    │
```

Sentences about refunds cluster together. Sentences about delivery cluster
together. The **distance** between points reflects **semantic distance**.

Real embeddings have 1024-1536 dimensions (not 2), capturing much more
nuance than we can visualise.

### How embeddings are trained

The embedding model learns from massive text data:

```
Training signal: "Words that appear in similar contexts have similar meanings"

Example contexts:
  "The customer requested a [refund] for the broken item"
  "The customer requested a [return] for the broken item"
  → "refund" and "return" appear in identical contexts
  → Their embeddings should be close together

  "The customer requested a [pizza] for the broken item"
  → Doesn't make sense → "pizza" should be far from "refund"
```

### Why dimensions matter

Each dimension captures some aspect of meaning:

```
1024 dimensions = 1024 independent semantic features

Hypothetical features (we don't know the exact ones):
  Dim 0:   formality       (formal ←→ casual)
  Dim 1:   topic           (finance ←→ cooking)
  Dim 2:   sentiment       (positive ←→ negative)
  Dim 3:   specificity     (general ←→ specific)
  ...
  Dim 1023: (some abstract learned feature)

More dimensions = more nuance captured
But also: more storage, more compute for comparison
```

---

## 10. Vector Similarity — Cosine, Dot Product, Euclidean

### Three ways to measure similarity

```
Given two vectors A and B:

1. COSINE SIMILARITY (what we use):
   cos(A, B) = (A · B) / (|A| × |B|)
   Range: -1 to 1 (usually 0 to 1 for normalised embeddings)
   Measures: angle between vectors (direction)
   Ignores: magnitude (length)
   
2. DOT PRODUCT:
   dot(A, B) = A · B = Σ(aᵢ × bᵢ)
   Range: -∞ to +∞
   Measures: both direction and magnitude
   Faster than cosine (no division)
   
3. EUCLIDEAN DISTANCE:
   dist(A, B) = √(Σ(aᵢ - bᵢ)²)
   Range: 0 to ∞
   Measures: straight-line distance
   Lower = more similar (opposite of cosine!)
```

### Why cosine is the default for text

```
Document A: mentions "refund" 5 times  → long vector (high magnitude)
Document B: mentions "refund" 1 time   → short vector (low magnitude)

Euclidean: B is far from A (different magnitudes) → BAD
Dot product: B scores lower than A (shorter vector) → MISLEADING
Cosine: B ≈ A (same direction, magnitude ignored) → CORRECT

Both documents are about refunds — cosine captures this.
```

### Practical example

```python
import numpy as np

def cosine_similarity(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# Embeddings (simplified to 4 dimensions)
refund_query    = [0.8, 0.1, -0.3, 0.5]
refund_chunk    = [0.7, 0.2, -0.2, 0.6]   # Similar topic
delivery_chunk  = [0.1, 0.8, 0.5, -0.1]   # Different topic

print(cosine_similarity(refund_query, refund_chunk))    # → 0.97 (very similar)
print(cosine_similarity(refund_query, delivery_chunk))   # → 0.15 (very different)
```

---

## 11. Vector Databases — How They Work

### The problem

You have 10,000 document chunks, each with a 1024-dimensional embedding.
A user asks a question. You need to find the 5 most similar chunks.

**Brute force:** Compare the query to all 10,000 vectors = 10,000 cosine calculations.
At 1 million chunks: 1,000,000 comparisons per query. Too slow.

### The solution: Approximate Nearest Neighbour (ANN)

Instead of checking every vector, build an index that lets you check ~50
vectors and get 95%+ accuracy.

### HNSW — The algorithm we use

HNSW (Hierarchical Navigable Small World) builds a multi-layer graph:

```
Building the index (when you store vectors):

1. Assign each vector a random layer (higher = rarer)
   Layer 3: 1% of vectors     (very sparse — long jumps)
   Layer 2: 5% of vectors     (sparse — medium jumps)
   Layer 1: 20% of vectors    (moderate — short jumps)
   Layer 0: 100% of vectors   (dense — fine-grained)

2. At each layer, connect each vector to its nearest neighbours
   → Creates a navigable graph at each layer

Searching:
1. Start at the top layer (Layer 3)
   → Few nodes, big jumps, quickly get to the right region
2. Drop to Layer 2
   → More nodes, medium jumps, narrow down
3. Drop to Layer 1
   → More nodes, shorter jumps, get closer
4. Search Layer 0
   → All nodes, find the exact nearest neighbours

Result: ~log(N) comparisons instead of N
  10,000 vectors → ~14 comparisons (instead of 10,000)
  1,000,000 vectors → ~20 comparisons (instead of 1,000,000)
```

### Trade-offs in ANN algorithms

| Algorithm | Speed | Accuracy | Memory | Used by |
| --- | --- | --- | --- | --- |
| **HNSW** | Fast | 95-99% | High (graph in memory) | OpenSearch, pgvector |
| IVF | Medium | 90-95% | Medium (cluster centres) | FAISS |
| Product Quantisation | Very fast | 85-90% | Low (compressed vectors) | FAISS |
| Flat (brute force) | Slow | 100% | Low | Small datasets only |

---

# Part 4: RAG (Retrieval-Augmented Generation)

## 12. RAG — The Complete Theory

### The problem RAG solves

LLMs have three fundamental limitations:

```
1. KNOWLEDGE CUTOFF: Training data has a date limit
   → GPT-4o doesn't know about events after its training date
   → Your company's internal documents are NOT in its training data

2. HALLUCINATION: LLMs generate plausible text, not necessarily true text
   → "Paris is the capital of France" (true — in training data)
   → "Your refund takes 14 days" (might be wrong — guessing)

3. NO PRIVATE DATA: LLMs don't know your internal documents
   → Can't answer "What is OUR refund policy?"
```

### How RAG solves it

```
INSTEAD OF:
  User → LLM → Answer (from training memory — might be wrong)

RAG DOES:
  User → Search your docs → Found relevant text → LLM reads it → Answer
         (always current)   (grounded in facts)   (faithful)    (accurate)
```

### The original RAG paper (Lewis et al., 2020)

The paper "Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks"
proposed combining a retriever (DPR — Dense Passage Retrieval) with a
generator (BART). The key insight:

> "By providing retrieved passages as additional context, the generator
> can produce responses that are more factual and specific than a
> generator alone."

### RAG vs alternatives

| Approach | Cost | Update speed | Accuracy | When to use |
| --- | --- | --- | --- | --- |
| **RAG** | Low ($0.004/query) | Instant (upload new doc) | High | Most use cases — start here |
| Fine-tuning | Medium ($100-1000) | Hours to days | Higher for specific tasks | Domain-specific language/style |
| Pre-training | Very high ($10M+) | Months | Highest for general knowledge | Only for model providers |
| Prompt stuffing | Very low | Instant | Medium | Very small knowledge bases |

### When RAG fails and what to do

| Failure mode | Symptom | Root cause | Fix |
| --- | --- | --- | --- |
| Wrong chunks retrieved | Answer is about wrong topic | Bad embeddings or chunk boundaries | Better chunking, re-embed |
| Relevant chunks not found | "I don't have information" | Chunk doesn't match query semantically | Hybrid search (keyword + vector) |
| Hallucination despite context | Answer has made-up facts | Weak prompt constraints | Strengthen prompt, lower temperature |
| Answer too vague | "The policy mentions refunds" | Chunks too large, diluted context | Smaller chunk size |
| Answer misses details | Missing important points | Not enough chunks retrieved | Increase top_k |

---

## 13. Chunking Strategies — Deep Dive

### Why chunking is critical

Chunking is the **most impactful parameter** in a RAG system. Bad chunking
makes everything else fail — even with the best LLM and vector database.

### Strategy 1: Fixed-size (what we use)

```python
RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
```

```
Pros: Simple, predictable, works well for most documents
Cons: Can split sentences mid-thought, ignores document structure

Best for: General-purpose documents, quick implementation
```

### Strategy 2: Sentence-based

```
Split on sentence boundaries. Each chunk = N sentences.

Pros: Never splits mid-sentence
Cons: Sentences vary wildly in length (10 to 200+ characters)
      Some chunks too small, some too large
```

### Strategy 3: Semantic chunking

```
Use an embedding model to detect topic boundaries.
When similarity between consecutive sentences drops below threshold,
start a new chunk.

Sentence 1: "Our refund policy is generous."         → embed
Sentence 2: "Returns are accepted within 30 days."   → embed
Sentence 3: "We ship to 45 countries worldwide."     → embed

Similarity(S1, S2) = 0.85  → same topic, keep in same chunk
Similarity(S2, S3) = 0.23  → topic change! Start new chunk

Pros: Chunks align with natural topic boundaries
Cons: Slow (need to embed every sentence), non-deterministic
```

### Strategy 4: Document-structure-aware

```
Use the document's own structure (headings, paragraphs, sections).

H1: Refund Policy
  H2: Eligibility
    Paragraph 1 → Chunk 1
    Paragraph 2 → Chunk 2
  H2: Process
    Paragraph 3 → Chunk 3
    Paragraph 4 → Chunk 4

Pros: Respects the author's organisation
Cons: Not all documents have good structure
      PDFs often lose heading information
```

### How to choose

| Document type | Recommended strategy | chunk_size | overlap |
| --- | --- | --- | --- |
| General PDFs | Fixed-size (recursive) | 1000 | 200 |
| Legal contracts | Semantic or structure-aware | 1500 | 300 |
| FAQ pages | Sentence-based (Q&A pairs) | 500 | 50 |
| Technical docs | Structure-aware (by section) | 1000 | 200 |
| Short emails | No chunking (whole document) | — | — |

---

## 14. Retrieval Strategies — Beyond Basic Search

### Strategy 1: Vector search only (what we do now)

```
Question → Embed → Find nearest vectors → Return chunks
Simple, fast, works well for most cases.
```

### Strategy 2: Hybrid search (vector + keyword)

```
Question → Embed → Vector search → Top 10 by similarity
        → Keywords → BM25 search → Top 10 by keyword match
        → Merge and re-rank → Return top 5

Why: Vector search misses exact matches ("error code E-4021")
     Keyword search misses semantic matches ("get money back" → "refund")
     Hybrid combines both strengths.
```

### Strategy 3: Re-ranking

```
Question → Vector search → Top 20 candidates
        → Re-ranker model → Re-score based on question-chunk relevance
        → Return top 5

Why: The embedding model scores chunks independently.
     A re-ranker sees the question AND the chunk together,
     making a more informed relevance judgement.

Models: Cohere Rerank, BGE Reranker, cross-encoder models
```

### Strategy 4: Multi-query retrieval

```
Question: "What are the return policies and shipping costs?"

Generated sub-queries:
  1. "What is the return policy?"
  2. "What are the shipping costs?"
  3. "How do returns affect shipping charges?"

Search each sub-query → Merge results → Deduplicate → Return

Why: One question can need information from multiple topics.
     Splitting into sub-queries finds all relevant chunks.
```

---

## 15. RAG Evaluation — Measuring Quality

### The RAGAS framework (industry standard)

RAGAS (Retrieval-Augmented Generation Assessment) defines four metrics:

```
1. CONTEXT RELEVANCY: Are the retrieved chunks relevant to the question?
   Score = (relevant chunks) / (total chunks retrieved)
   
   High: All 5 chunks are about refunds (for a refund question)
   Low:  3 of 5 chunks are about shipping (irrelevant noise)

2. FAITHFULNESS: Does the answer only use facts from the context?
   Score = (claims supported by context) / (total claims in answer)
   
   High: Every sentence in the answer traces back to a chunk
   Low:  The answer includes facts not in any chunk (hallucination)

3. ANSWER RELEVANCY: Does the answer address the question?
   Score = semantic similarity between question and answer
   
   High: Question about refunds → answer about refund policy
   Low:  Question about refunds → answer about company history

4. ANSWER CORRECTNESS: Is the answer factually correct?
   Score = (correct facts) / (total facts in answer)
   Requires ground truth (known correct answer)
```

### Where this is implemented in your project

```
src/evaluation/evaluator.py  → Implements dimensions 1, 2, 3
src/evaluation/golden_dataset.py → Test cases for dimension 4
tests/test_evaluation.py → Automated regression tests
```

---

# Part 5: Prompt Engineering

## 16. Prompt Engineering — The Science

### Why prompts matter so much

The prompt is the **only way you communicate with the model**. The same model
can give brilliant or terrible answers depending on the prompt.

```
Bad prompt:
  "Summarise this"
  → Vague, no constraints, no format, no context about what "this" is

Good prompt:
  "You are an expert summariser. Summarise the following customer complaint
   in exactly 3 bullet points. Focus on: the issue, the impact, and the
   desired resolution. Only use information from the text below.
   
   TEXT: {customer_complaint}"
  → Clear role, specific format, constraints, explicit input
```

### The anatomy of a prompt

```
┌─────────────────────────────────────────────────────┐
│ 1. SYSTEM PROMPT (who the model is)                 │
│    "You are a helpful assistant that answers         │
│     questions based on provided documents."          │
├─────────────────────────────────────────────────────┤
│ 2. CONSTRAINTS (rules to follow)                    │
│    "ONLY use information from the context."          │
│    "If unsure, say you don't know."                  │
│    "Never make up information."                      │
├─────────────────────────────────────────────────────┤
│ 3. FORMAT INSTRUCTIONS (how to structure output)    │
│    "Use bullet points for lists."                    │
│    "Cite sources as [Document N]."                   │
│    "Keep the answer under 200 words."                │
├─────────────────────────────────────────────────────┤
│ 4. CONTEXT (the data to work with)                  │
│    "CONTEXT DOCUMENTS: {chunks}"                     │
├─────────────────────────────────────────────────────┤
│ 5. INPUT (the actual question)                      │
│    "QUESTION: {user_question}"                       │
└─────────────────────────────────────────────────────┘
```

---

## 17. Advanced Prompting Techniques

### Chain of Thought (CoT)

```
Without CoT:
  Q: "If a customer bought 3 items at €15 each and returned 1, what's the refund?"
  A: "€45" ← WRONG

With CoT:
  Q: "Think step by step: If a customer bought 3 items at €15 each
      and returned 1, what's the refund?"
  A: "Step 1: 3 items × €15 = €45 total purchase
      Step 2: Returned 1 item → refund for 1 × €15
      Step 3: Refund = €15" ← CORRECT

Why it works: Forces the model to show intermediate reasoning,
which activates more careful computation.
```

### Few-Shot Prompting

```
"Here are examples of how to answer:

Q: What is the return window?
A: According to [Document 1], the return window is 30 days from purchase.

Q: Do I need the receipt?
A: Based on [Document 3], a receipt or order confirmation email is required.

Now answer this question in the same format:
Q: {user_question}"

Why it works: Shows the model exactly what format you expect.
The model mimics the pattern.
```

### Self-Consistency

```
Generate 3 answers with temperature=0.7
Pick the answer that appears most frequently (majority vote)

Why it works: If 3 independent attempts agree, the answer is
likely correct. Disagreement signals uncertainty.

Cost: 3× more expensive (3 LLM calls per question)
```

---

# Part 6: AI Agents

## 18. What Are AI Agents — Theory & Architecture

### Definition

An AI Agent is a system where an LLM **decides which actions to take**
to accomplish a goal. The LLM acts as the "brain" that plans and reasons,
while tools provide the "hands" to interact with the world.

### Key properties that distinguish agents from chatbots

```
CHATBOT (what you have in V1):
  - Single turn: question → answer
  - Fixed pipeline: always embed → search → generate
  - No decision-making: always runs the same steps
  - Reactive: only responds to user input

AGENT (what you'd build in V2):
  - Multi-turn: goal → [think → act → observe]* → result
  - Dynamic pipeline: chooses which tools to use
  - Decision-making: decides what to do next based on observations
  - Proactive: can plan and execute multi-step strategies
```

### The cognitive architecture of an agent

```
┌──────────────────────────────────────────────────┐
│                    THE AGENT                      │
│                                                   │
│  ┌───────────────────────────────┐               │
│  │         LLM (Brain)           │               │
│  │                               │               │
│  │  • Understands the goal       │               │
│  │  • Plans next action          │               │
│  │  • Interprets tool results    │               │
│  │  • Decides when done          │               │
│  └───────────┬───────────────────┘               │
│              │                                    │
│  ┌───────────▼───────────────────┐               │
│  │        Tool Router            │               │
│  │                               │               │
│  │  "Which tool should I use?"   │               │
│  │                               │               │
│  └──┬────┬────┬────┬────┬───────┘               │
│     │    │    │    │    │                         │
│  ┌──▼─┐┌─▼──┐┌▼──┐┌▼──┐┌▼────┐                 │
│  │RAG ││Web ││SQL││File││Email│  ← Tools        │
│  │Tool││Tool││Tool││Tool││Tool│                  │
│  └────┘└────┘└────┘└────┘└────┘                  │
│                                                   │
│  ┌───────────────────────────────┐               │
│  │          Memory               │               │
│  │  • Conversation history       │               │
│  │  • Previous tool results      │               │
│  │  • Learned preferences        │               │
│  └───────────────────────────────┘               │
└──────────────────────────────────────────────────┘
```

---

## 19. Tool Use — How Agents Interact With the World

### The tool use protocol

LLMs are trained to output **structured tool calls** when they need
to interact with external systems:

```
User: "Find the refund policy and email it to john@example.com"

LLM response (not text — a structured tool call):
{
  "tool_name": "search_documents",
  "arguments": {"query": "refund policy"}
}

System executes the tool → returns result to LLM

LLM sees: "The refund policy states... 14 days..."

LLM response (another tool call):
{
  "tool_name": "send_email",
  "arguments": {
    "to": "john@example.com",
    "subject": "Refund Policy",
    "body": "The refund policy states..."
  }
}

System executes the tool → returns "Email sent"

LLM response (text — done):
"I found the refund policy and emailed it to john@example.com."
```

### How tools are defined

You describe tools to the LLM using a schema:

```python
tools = [
    {
        "name": "search_documents",
        "description": "Search uploaded documents for information about a topic",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "The search query"
                }
            },
            "required": ["query"]
        }
    },
    {
        "name": "send_email",
        "description": "Send an email to a recipient",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Recipient email"},
                "subject": {"type": "string"},
                "body": {"type": "string"}
            },
            "required": ["to", "subject", "body"]
        }
    }
]
```

The LLM reads these descriptions and decides when to use each tool.

---

## 20. Agent Patterns — ReAct, Plan-and-Execute, Reflection

### Pattern 1: ReAct (Reasoning + Acting)

The most common agent pattern. The LLM alternates between thinking and acting:

```
User: "Compare our refund policy with Amazon's"

Thought 1: I need to find our refund policy first.
Action 1:  search_documents("refund policy")
Observation 1: "Refunds processed within 14 days..."

Thought 2: Now I need Amazon's refund policy.
Action 2:  web_search("Amazon refund policy")
Observation 2: "Amazon offers refunds within 30 days..."

Thought 3: I have both policies. I can now compare them.
Action 3:  (no tool needed — just generate the comparison)
Final Answer: "Your policy offers 14-day refunds while Amazon offers 30-day..."
```

### Pattern 2: Plan-and-Execute

First plan ALL steps, then execute them:

```
User: "Create a monthly report of customer queries"

PLAN:
  1. Search documents for all query categories
  2. Count queries per category
  3. Calculate trends vs last month
  4. Generate a summary report
  5. Save as PDF

EXECUTE:
  Step 1: search_documents("query categories") → ...
  Step 2: calculator("count by category") → ...
  Step 3: calculator("compare with last month") → ...
  Step 4: generate_text("monthly report") → ...
  Step 5: save_file("report.pdf") → done
```

### Pattern 3: Reflection

The agent evaluates its own output and improves:

```
User: "Explain the refund policy"

Attempt 1: "Refunds are available."
Self-evaluation: "Too vague. Missing: timeframe, conditions, process."

Attempt 2: "Refunds are processed within 14 days. Products must be
            in original packaging. Contact support@example.com."
Self-evaluation: "Better. Covers timeframe and conditions. Good enough."

Final Answer: Attempt 2
```

---

## 21. Agent Memory — Short-Term and Long-Term

### Short-term memory (conversation context)

```
What the agent remembers within a single session:
  - The user's goal
  - What tools it has called
  - What results it got
  - What it has already told the user

Implementation: simply the message history (context window)
Limitation: lost when the session ends or context is full
```

### Long-term memory (persistent storage)

```
What the agent remembers across sessions:
  - User preferences ("always summarise in bullet points")
  - Previous interactions ("last time you asked about refunds")
  - Learned facts ("this user is in the B2C segment")

Implementation: stored in a database (DynamoDB / Cosmos DB)
Your project already has this: src/history/ module
```

---

# Part 7: MCP (Model Context Protocol)

## 22. MCP — Theory & Architecture

### The problem MCP solves

Every AI application integrates tools differently:

```
Before MCP:
  ChatGPT plugins → OpenAI's proprietary format
  Claude tools   → Anthropic's tool_use format
  Copilot tools  → VS Code extension API
  LangChain      → LangChain's tool class
  
  If you build a tool, you need DIFFERENT integrations for each platform.
```

MCP creates ONE standard:

```
After MCP:
  Your MCP Server ←→ MCP Protocol ←→ Any MCP Client
                                      (Claude, Copilot, custom apps)
  
  Build your tool ONCE, use it EVERYWHERE.
```

### MCP architecture

```
┌──────────────┐                    ┌──────────────┐
│  MCP HOST     │                    │  MCP SERVER   │
│  (AI app)     │                    │  (your tool)  │
│               │    MCP Protocol    │               │
│  Claude       │◄──────────────────►│  RAG Chatbot  │
│  Copilot      │   JSON-RPC over    │  Database     │
│  Custom app   │   stdio or HTTP    │  File system  │
│               │                    │  API          │
└──────────────┘                    └──────────────┘

The protocol defines:
  1. TOOLS:      Functions the server exposes (search_documents, etc.)
  2. RESOURCES:  Data the server provides (document list, etc.)
  3. PROMPTS:    Pre-built prompt templates
```

### MCP vs REST API

| Aspect | REST API | MCP |
| --- | --- | --- |
| Purpose | Any application | AI assistants specifically |
| Discovery | Read docs, write code | AI reads schema, calls automatically |
| Schema | OpenAPI / Swagger | MCP tool definitions |
| Auth | API keys, OAuth | Built-in transport security |
| Streaming | Requires SSE/WebSocket | Built-in |
| AI-optimised | No | Yes — descriptions help AI choose tools |

---

## 23. Building MCP Servers & Clients

### An MCP server for your RAG chatbot

```python
# Conceptual example of what you'd build:

from mcp.server import Server

server = Server("rag-chatbot")

@server.tool()
async def search_documents(query: str) -> str:
    """Search uploaded documents for information.
    
    Use this tool when the user asks about company policies,
    product information, or any topic covered in uploaded documents.
    """
    result = await rag_chain.query(question=query, session_id="mcp")
    return result["answer"]

@server.tool()
async def upload_document(filename: str, content: str) -> str:
    """Upload a new document to the knowledge base."""
    doc_id = await rag_chain.ingest_document(...)
    return f"Document '{filename}' uploaded successfully ({doc_id})"

@server.tool()
async def list_documents() -> str:
    """List all documents in the knowledge base."""
    docs = await storage.list_documents()
    return "\n".join(f"- {d.filename}" for d in docs)
```

Once built, ANY MCP-compatible AI can use your RAG chatbot as a tool:
- Claude Desktop could search your documents
- VS Code Copilot could answer questions from your docs
- Your own agent could use it as one of many tools

---

# Part 8: The Learning Plan

## 24. Week-by-Week Study Plan

### Phase 1: Foundations (Week 1-2)

**Week 1: LLMs & Embeddings**

| Day | Topic | Study | Practice |
| --- | --- | --- | --- |
| Mon | Neural network basics | This doc: Section 2 | Watch 3Blue1Brown neural network video |
| Tue | Transformers & attention | This doc: Sections 3, 6 | Watch "Attention is All You Need" explained |
| Wed | Tokenisation | This doc: Section 5 | Run tiktoken example, count tokens |
| Thu | Embeddings | This doc: Section 9 | Run sentence-transformers example |
| Fri | Vector similarity | This doc: Section 10 | Implement cosine similarity from scratch |

**Week 2: RAG & Prompt Engineering**

| Day | Topic | Study | Practice |
| --- | --- | --- | --- |
| Mon | RAG theory | This doc: Section 12 | Read the original RAG paper abstract |
| Tue | Chunking strategies | This doc: Section 13 | Chunk a real PDF, compare strategies |
| Wed | Prompt engineering | This doc: Sections 16-17 | Write 10 prompts, compare outputs in ChatGPT |
| Thu | RAG evaluation | This doc: Section 15 | Read the RAGAS framework docs |
| Fri | Review & consolidate | Re-read all sections | Explain RAG to someone (or write it down) |

### Phase 2: Hands-On (Week 3-4)

**Week 3: Build & Understand the RAG Chatbot**

| Day | Topic | Activity |
| --- | --- | --- |
| Mon | Setup | `poetry install`, configure `.env`, start the server |
| Tue | Ingestion | Upload a PDF, read the logs, trace through ingestion.py |
| Wed | Query | Ask questions, check sources, set breakpoints in chain.py |
| Thu | Evaluation | Run `pytest tests/test_evaluation.py`, understand scores |
| Fri | Experiment | Change chunk_size, compare evaluation scores |

**Week 4: Cloud Integration**

| Day | Topic | Activity |
| --- | --- | --- |
| Mon | AWS Bedrock | Enable Bedrock, try playground, call from Python |
| Tue | Azure OpenAI | Deploy model, try Studio, call from Python |
| Wed | Vector store | Try ChromaDB locally, understand indexing |
| Thu | Compare | Same question through AWS vs Azure, compare quality |
| Fri | Cost analysis | Calculate token costs for 1000 queries |

### Phase 3: Advanced (Week 5-6)

**Week 5: Agents**

| Day | Topic | Study | Practice |
| --- | --- | --- | --- |
| Mon | Agent theory | This doc: Sections 18-19 | Read LangChain agents docs |
| Tue | ReAct pattern | This doc: Section 20 | Implement a simple ReAct loop |
| Wed | Tool use | This doc: Section 19 | Define 3 tools, test with Claude |
| Thu | Agent memory | This doc: Section 21 | Add conversation memory to agent |
| Fri | Build agent v2 | — | Add agent layer to RAG chatbot |

**Week 6: MCP & Polish**

| Day | Topic | Study | Practice |
| --- | --- | --- | --- |
| Mon | MCP theory | This doc: Sections 22-23 | Read MCP specification |
| Tue | MCP server | — | Build an MCP server for your RAG chatbot |
| Wed | MCP testing | — | Connect Claude Desktop to your MCP server |
| Thu | Portfolio polish | — | Clean up code, update README, record demo |
| Fri | Interview prep | docs/ai-engineer-guide.md | Practice explaining the project |

---

## 25. Hands-On Exercises

### Exercise 1: Embedding Explorer (Week 1)

```python
"""
Compare embeddings of similar and different sentences.
Prove to yourself that embeddings capture meaning.
"""
# pip install sentence-transformers numpy
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

sentences = [
    "How do I get a refund?",
    "I want my money back",
    "What is the return policy?",
    "The weather is sunny today",
    "My order hasn't arrived yet",
]

embeddings = model.encode(sentences)

# Compare every pair
for i in range(len(sentences)):
    for j in range(i+1, len(sentences)):
        sim = np.dot(embeddings[i], embeddings[j]) / (
            np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[j])
        )
        print(f"{sim:.3f}  '{sentences[i]}' ↔ '{sentences[j]}'")
```

### Exercise 2: Build RAG from Scratch (Week 2)

```python
"""
Build the simplest possible RAG system. No frameworks, no cloud.
Just Python + a free embedding model + a list of chunks.
"""
from sentence_transformers import SentenceTransformer
import numpy as np

model = SentenceTransformer("all-MiniLM-L6-v2")

# Your "knowledge base" (normally from uploaded documents)
documents = [
    "Refunds are processed within 14 business days.",
    "Products must be returned in original packaging.",
    "Digital products are non-refundable.",
    "Free shipping on orders over 50 euros.",
    "Contact support@example.com for help.",
]

# Embed all documents (normally done during ingestion)
doc_embeddings = model.encode(documents)

# The RAG function
def ask(question: str, top_k: int = 2) -> str:
    # Step 1: Embed the question
    q_embedding = model.encode(question)
    
    # Step 2: Find most similar documents
    similarities = [
        np.dot(q_embedding, doc_emb) / (np.linalg.norm(q_embedding) * np.linalg.norm(doc_emb))
        for doc_emb in doc_embeddings
    ]
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    # Step 3: Build context
    context = "\n".join(f"- {documents[i]} (score: {similarities[i]:.2f})" for i in top_indices)
    
    # Step 4: (In real RAG, send to LLM. Here we just show the context.)
    return f"Question: {question}\n\nRelevant documents:\n{context}"

print(ask("How do I get my money back?"))
print()
print(ask("How much for shipping?"))
```

### Exercise 3: Prompt Engineering Lab (Week 2)

```
Open ChatGPT or Claude and try these experiments:

EXPERIMENT 1: Role matters
  Bad:  "Summarise this text"
  Good: "You are an expert legal analyst. Summarise this contract clause,
         highlighting any risks for the buyer."

EXPERIMENT 2: Constraints matter
  Bad:  "Answer this question about the document"
  Good: "Answer ONLY using the document below. If the answer isn't in the
         document, say 'Not found in document.' Never guess."

EXPERIMENT 3: Format matters
  Bad:  "List the key points"
  Good: "List exactly 5 key points as bullet points. Each bullet must be
         one sentence. Start each bullet with an action verb."

EXPERIMENT 4: Chain of thought
  Bad:  "What's 17% of the €234.50 order minus the €15 coupon?"
  Good: "Calculate step by step: What's 17% of the €234.50 order minus
         the €15 coupon? Show each calculation."
```

### Exercise 4: Evaluation Practice (Week 3)

```python
"""
Run the evaluation framework on different scenarios.
See how scores change with good vs bad retrieval.
"""
from src.evaluation.evaluator import RAGEvaluator

evaluator = RAGEvaluator()

# Scenario 1: Good retrieval, faithful answer
result1 = evaluator.evaluate(
    question="What is the refund policy?",
    answer="Refunds are processed within 14 business days. Products must be returned in original packaging.",
    retrieved_chunks=[
        ("Refunds are processed within 14 business days.", 0.95),
        ("Products must be returned in original packaging.", 0.88),
    ],
)
print(f"Scenario 1 (good): {result1.overall_score}")

# Scenario 2: Good retrieval, hallucinated answer
result2 = evaluator.evaluate(
    question="What is the refund policy?",
    answer="Refunds are instant and come with a free gift basket and helicopter ride.",
    retrieved_chunks=[
        ("Refunds are processed within 14 business days.", 0.95),
        ("Products must be returned in original packaging.", 0.88),
    ],
)
print(f"Scenario 2 (hallucination): {result2.overall_score}")
print(f"Flagged: {result2.faithfulness.flagged_sentences}")
```

---

## 26. Recommended Resources

### Must-Read (Free)

| Resource | What you learn | Time |
| --- | --- | --- |
| [Attention Is All You Need](https://arxiv.org/abs/1706.03762) | The Transformer paper — read the abstract + Section 3 | 30 min |
| [RAG paper](https://arxiv.org/abs/2005.11401) | The original RAG paper — read abstract + intro | 20 min |
| [Prompt Engineering Guide](https://www.promptingguide.ai/) | Every prompting technique, with examples | 2 hours |
| [RAGAS docs](https://docs.ragas.io/) | RAG evaluation framework | 1 hour |
| [MCP Specification](https://modelcontextprotocol.io/) | The MCP standard | 1 hour |

### Must-Watch (Free)

| Video | What you learn | Time |
| --- | --- | --- |
| [3Blue1Brown: Neural Networks](https://www.youtube.com/watch?v=aircAruvnKk) | Visual intuition for neural networks | 20 min |
| [3Blue1Brown: Transformers](https://www.youtube.com/watch?v=wjZofJX0v4M) | Visual intuition for attention | 25 min |
| [Andrej Karpathy: Intro to LLMs](https://www.youtube.com/watch?v=zjkBMFhNj_g) | Best LLM overview for engineers | 60 min |
| [DeepLearning.AI: LangChain for LLM Apps](https://www.deeplearning.ai/short-courses/langchain-for-llm-application-development/) | Practical LangChain | 1 hour |
| [DeepLearning.AI: Chat with Your Data](https://www.deeplearning.ai/short-courses/langchain-chat-with-your-data/) | RAG specifically | 1 hour |
| [DeepLearning.AI: Building Agentic RAG](https://www.deeplearning.ai/short-courses/building-agentic-rag-with-llamaindex/) | Agents + RAG | 1 hour |
| [DeepLearning.AI: AI Agents in LangGraph](https://www.deeplearning.ai/short-courses/ai-agents-in-langgraph/) | Agent patterns | 1 hour |

### Books (Optional, for deeper understanding)

| Book | Level | Focus |
| --- | --- | --- |
| *AI Engineering* — Chip Huyen (2025) | Intermediate | **Best book for AI Engineers** — covers exactly your path |
| *Build a Large Language Model (From Scratch)* — Sebastian Raschka | Advanced | Deep understanding of LLM internals |
| *Designing Machine Learning Systems* — Chip Huyen | Intermediate | Production ML systems |
| *Natural Language Processing with Transformers* — Tunstall et al. | Intermediate | Transformers with HuggingFace |

### The one resource to start with

If you only have time for ONE thing, watch **Andrej Karpathy's "Intro to Large Language Models"** (60 min on YouTube). It's the best single resource for understanding LLMs as an engineer.
