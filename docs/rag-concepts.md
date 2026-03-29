# RAG Concepts — What is RAG, Explained Simply

## Table of Contents

- [What is RAG?](#what-is-rag)
- [The problem RAG solves](#the-problem-rag-solves)
- [How RAG works step by step](#how-rag-works-step-by-step)
- [What are embeddings?](#what-are-embeddings)
- [What is a vector store?](#what-is-a-vector-store)
- [What is chunking?](#what-is-chunking)
- [What is cosine similarity?](#what-is-cosine-similarity)
- [What is a prompt?](#what-is-a-prompt)
- [What is a token?](#what-is-a-token)
- [RAG vs Fine-tuning](#rag-vs-fine-tuning)
- [Common RAG problems and solutions](#common-rag-problems-and-solutions)

---

## What is RAG?

**RAG** stands for **Retrieval-Augmented Generation**.

It's a technique where an LLM generates answers using **your own documents** as context, instead of relying only on its training data.

Simple analogy:

- **Without RAG**: You ask someone a question and they answer from memory (might be wrong or outdated)
- **With RAG**: You ask someone a question, they first look up relevant pages in a book, then answer based on what they found (grounded in facts)

---

## The problem RAG solves

LLMs like GPT-4o and Claude are trained on public internet data up to a cutoff date. They:

- Don't know your company's internal documents
- Don't know data created after their training date
- Can "hallucinate" — confidently make up facts
- Can't cite sources

RAG fixes all of these by:

1. Storing your documents in a searchable database
2. Finding relevant documents for each question
3. Giving those documents to the LLM as context
4. The LLM answers based on your actual data

---

## How RAG works step by step

### Phase 1: Ingestion (one-time per document)

```
Document → Read → Chunk → Embed → Store in Vector DB

"refund-policy.pdf"
    │
    ▼
Read: "Our refund policy allows returns within 14 days..."
    │
    ▼
Chunk: ["Our refund policy allows...", "To request a refund...", ...]
    │
    ▼
Embed: [[0.12, -0.45, 0.78, ...], [0.33, 0.67, -0.12, ...], ...]
    │
    ▼
Store: Each chunk + its vector saved in the vector database
```

### Phase 2: Query (every time a user asks)

```
Question → Embed → Search → Retrieve → Generate → Answer

"What is the refund policy?"
    │
    ▼
Embed: [0.11, -0.44, 0.79, ...]  (similar to refund-related chunks)
    │
    ▼
Search: Find top 5 most similar vectors in the database
    │
    ▼
Retrieve: Get the actual text of those 5 chunks
    │
    ▼
Generate: Send to LLM:
    "Context: [chunk 1] [chunk 2] [chunk 3] ...
     Question: What is the refund policy?"
    │
    ▼
Answer: "Based on the documents, refunds are processed within 14 days..."
```

---

## What are embeddings?

An **embedding** is a list of numbers (a vector) that represents the "meaning" of a text.

```
"What is the refund policy?"  →  [0.12, -0.45, 0.78, 0.33, -0.91, ...]
"How do I get my money back?" →  [0.11, -0.44, 0.79, 0.34, -0.90, ...]
"What's the weather today?"   →  [0.88, 0.23, -0.56, 0.12, 0.45, ...]
```

Notice:
- The first two sentences are about the same topic → their vectors are very similar
- The third sentence is about a different topic → its vector is very different

This is how the system knows which document chunks are relevant to your question.

**Technical details:**
- Amazon Titan Embeddings v2: produces 1024-dimensional vectors
- Azure text-embedding-3-small: produces 1536-dimensional vectors
- Each number in the vector captures a different aspect of meaning

---

## What is a vector store?

A **vector store** is a database optimized for storing and searching vectors.

Regular databases search by exact match:
```sql
SELECT * FROM documents WHERE topic = 'refund'
```

Vector databases search by **similarity**:
```
"Find the 5 vectors most similar to [0.12, -0.45, 0.78, ...]"
```

This is called **approximate nearest neighbor (ANN)** search.

### How it works internally

Most vector stores use **HNSW** (Hierarchical Navigable Small World) — a graph-based algorithm:

1. Vectors are organized in layers (like a highway system)
2. Top layer: few nodes, big jumps (highways)
3. Bottom layer: many nodes, small jumps (local roads)
4. To find nearest neighbors: start at top, narrow down layer by layer
5. Result: O(log N) search time instead of O(N) brute force

---

## What is chunking?

**Chunking** is splitting a large document into smaller pieces.

Why?
- LLMs have a maximum context size (200K tokens for Claude)
- But sending the entire document wastes tokens (and money)
- Smaller chunks are more precise — the LLM gets exactly the relevant part
- Embedding models work best on paragraph-sized text

### Chunking strategies

**Fixed-size chunks (what we use):**
- Split every 1000 characters with 200 character overlap
- Simple and effective
- Overlap prevents sentences from being cut in half

```
Document: "AAAA BBBB CCCC DDDD EEEE FFFF GGGG HHHH"

Chunk 1: "AAAA BBBB CCCC DDDD"
Chunk 2: "CCCC DDDD EEEE FFFF"  ← overlap with chunk 1
Chunk 3: "EEEE FFFF GGGG HHHH"  ← overlap with chunk 2
```

**Other strategies (not used here, documented for reference):**
- Sentence-based: split on sentence boundaries
- Paragraph-based: split on double newlines
- Semantic: use an LLM to identify topic boundaries
- Sliding window: fixed size with variable overlap

---

## What is cosine similarity?

**Cosine similarity** measures how similar two vectors are. Range: -1.0 to 1.0 (we normalize to 0.0 to 1.0).

- **1.0** = identical meaning
- **0.8+** = very similar
- **0.5** = somewhat related
- **0.0** = unrelated

```
cos_similarity("What is the refund policy?", "How to get a refund") = 0.92
cos_similarity("What is the refund policy?", "Company mission statement") = 0.23
cos_similarity("What is the refund policy?", "Pizza recipe") = 0.05
```

In this project, when you ask a question, the vector store returns chunks sorted by cosine similarity. The top-k chunks (highest scores) become the context for the LLM.

---

## What is a prompt?

A **prompt** is the text you send to the LLM. In RAG, the prompt has three parts:

```
[System instructions]
You are a helpful assistant. Only use the context below to answer.

[Context — the retrieved chunks]
Document chunk 1: "Refunds are processed within 14 days..."
Document chunk 2: "To request a refund, email support@..."

[User question]
What is the refund policy?
```

The quality of the prompt directly affects the quality of the answer. This is called **prompt engineering**.

---

## What is a token?

A **token** is the unit LLMs use to process text. Roughly:
- 1 token ≈ 4 characters in English
- 1 token ≈ 0.75 words
- "Hello, world!" = 3 tokens
- A typical RAG query with context = 1500–3000 tokens

Tokens matter because:
- LLMs have a maximum context window (tokens they can process at once)
- You pay per token (input and output)
- More context chunks = more input tokens = higher cost

---

## RAG vs Fine-tuning

| | RAG (what we build) | Fine-tuning |
| --- | --- | --- |
| **How** | Add documents at runtime | Retrain the model on your data |
| **Data updates** | Upload new documents instantly | Retrain the model (hours/days) |
| **Cost** | Per-query (token costs) | Upfront training cost ($100–$10K+) |
| **Accuracy** | Good with good retrieval | Better for specialized domains |
| **Sources** | Can cite exact documents | No source attribution |
| **Best for** | Knowledge bases, Q&A | Tone/style changes, specialized tasks |

**For this project:** RAG is the right choice. Your documents change over time, you need source citations, and you don't want to pay for model training.

---

## Common RAG problems and solutions

| Problem | Cause | Solution |
| --- | --- | --- |
| Wrong answer | Irrelevant chunks retrieved | Increase `top_k`, improve chunking |
| "I don't know" when answer exists | Chunk too small, question too vague | Increase chunk size, rephrase question |
| Hallucination | LLM ignores context | Stronger system prompt ("ONLY use context") |
| Slow responses | Too many chunks sent to LLM | Reduce `top_k`, use faster model |
| High cost | Too many tokens per query | Reduce chunk size, reduce `top_k` |
| Duplicate information | Overlapping chunks | Reduce `chunk_overlap` |
