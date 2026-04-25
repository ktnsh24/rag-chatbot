# Deep Dive: The LLM Interface — `src/llm/base.py`

> **Study order:** #7 · **Difficulty:** ★☆☆☆☆ (the code is simple — the concepts are what you're learning)
> **File:** [`src/llm/base.py`](../../src/llm/base.py)
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — What You Already Know](#de-parallel--what-you-already-know)
3. [Concept 1: Tokens — The Unit of AI Cost](#concept-1-tokens--the-unit-of-ai-cost-llmresponse)
4. [Concept 2: Generation — Sending a Prompt, Getting an Answer](#concept-2-generation--sending-a-prompt-and-getting-an-answer-generate)
5. [Concept 3: Temperature — Controlling Randomness](#concept-3-temperature--controlling-randomness)
6. [Concept 4: Embeddings — Turning Meaning into Math](#concept-4-embeddings--turning-meaning-into-math-get_embedding)
7. [Concept 5: Batch Embeddings — Performance Optimisation](#concept-5-batch-embeddings--the-performance-optimisation-get_embeddings_batch)
8. [Where `base.py` Sits in the RAG Pipeline](#where-basepy-sits-in-the-rag-pipeline)
9. [Self-Test Questions](#questions-to-ask-yourself-after-reading-this-file)
10. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

This is the **first AI file** you encounter after Phase 1. It defines the contract that every LLM provider (Bedrock, Azure OpenAI, Ollama) must follow. The code pattern is something you already know — `ABC` with `@abstractmethod`. What's new are the **five AI concepts** embedded in the interface:

| # | Concept | Method / class | DE parallel | What's new | 🫏 Donkey |
|---|---|---|---|---| --- |
| 1 | **Tokens** | `LLMResponse` | RCU/WCU (DynamoDB capacity units) | The unit of cost — output tokens cost 5× more than input | The donkey 🐴 |
| 2 | **Generation** | `generate()` | `db.query(sql)` → rows | Send prompt + context → get text + token counts back | Cargo unit ⚖️ |
| 3 | **Temperature** | `temperature` param | ❌ No parallel — pure AI | Controls randomness: 0.0 = deterministic, 1.0 = creative | 🫏 On the route |
| 4 | **Embeddings** | `get_embedding()` | ❌ No parallel — brand new | Converts text → fixed-size vector that captures meaning | GPS warehouse 🗺️ |
| 5 | **Batch embeddings** | `get_embeddings_batch()` | Batch INSERT | One API call instead of N — same performance pattern | Stable door 🚪 |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — What You Already Know

```
┌─────────────────────────────────────┐    ┌─────────────────────────────────────┐
│  DATA ENGINEERING (what you know)   │    │  AI ENGINEERING (what this file is) │
│                                     │    │                                     │
│  class BaseStorage(ABC):            │    │  class BaseLLM(ABC):                │
│      def query(sql) → rows          │    │      def generate(prompt) → text    │
│      def insert(rows)               │    │      def get_embedding(text) → vec  │
│                                     │    │                                     │
│  DynamoDB / PostgreSQL / S3         │    │  Bedrock / Azure OpenAI / Ollama    │
│  (different backends, same API)     │    │  (different providers, same API)    │
│                                     │    │                                     │
│  "Strategy Pattern"                 │    │  "Strategy Pattern" — exact same    │
└─────────────────────────────────────┘    └─────────────────────────────────────┘
```

You've used this pattern in DE work — abstract class with multiple concrete implementations. You swap DynamoDB ↔ PostgreSQL. Here you swap Bedrock ↔ Azure OpenAI ↔ Ollama (local). **The pattern is identical. Only the domain is different.**

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## Concept 1: Tokens — The Unit of AI Cost (`LLMResponse`)

**The code (lines 19–35):**
```python
@dataclass
class LLMResponse:
    text: str            # The generated answer
    input_tokens: int    # How many tokens YOU sent
    output_tokens: int   # How many tokens the LLM generated
    model_id: str        # Which model (for logging)
```

### What is a token?

Not a word, not a character — a **subword piece** produced by a tokenizer. Roughly 1 token ≈ 4 characters ≈ 0.75 words.

```
"How do refunds work?" → ["How", " do", " ref", "unds", " work", "?"] = 6 tokens
"authentication"       → ["auth", "ent", "ication"]                    = 3 tokens
"Hi"                   → ["Hi"]                                        = 1 token
```

### Why track input AND output separately?

Because they have different prices:

| Token type | Who produces it | Claude 3.5 Sonnet price | DE parallel | 🫏 Donkey |
|---|---|---|---| --- |
| **Input tokens** | You send them (prompt + context) | $0.003 / 1K tokens | Like DynamoDB Read Capacity Units | AWS depot 🏭 |
| **Output tokens** | LLM generates them (the answer) | $0.015 / 1K tokens (**5× more**) | Like DynamoDB Write Capacity Units | The donkey 🐴 |

Output tokens cost **5× more** than input tokens — same pattern as DynamoDB where writes cost more than reads. Tracking them separately lets you optimise: a verbose LLM answer costs more than a concise one.

### Context window limit

Every model has a maximum total tokens (input + output). Claude 3.5 Sonnet: 200K tokens. Exceed it → the API returns an error — like a `VARCHAR(255)` limit but for the entire conversation.

📖 **More on tokens:** [RAG Concepts → What is a Token?](rag-concepts.md#what-is-a-token) · [Cost Analysis](cost-analysis.md)

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Concept 2: Generation — Sending a Prompt and Getting an Answer (`generate()`)

**The code (lines 38–65):**
```python
@abstractmethod
async def generate(
    self,
    prompt: str,
    context: list[str],
    temperature: float = 0.1
) -> LLMResponse:
```

### Three parameters, three concepts

| Parameter | What it is | What goes in | DE parallel | 🫏 Donkey |
|---|---|---|---| --- |
| `prompt` | The user's question + system instructions | `"What is the refund policy?"` | The SQL query | Delivery note 📋 |
| `context` | Document chunks retrieved by vector search | `["Our refund policy allows...", "Returns must be..."]` | The tables the query runs against | backpack piece 📦 |
| `temperature` | Randomness control (0.0 = deterministic, 1.0 = creative) | `0.1` | ❌ No DE parallel — pure AI concept | 🫏 On the route |

### How generation works end-to-end

```
YOU build the input:                         LLM produces the output:
┌────────────────────────────────┐           ┌──────────────────────────────┐
│ System prompt    (~150 tokens) │           │                              │
│ + context chunks (~1250 tokens)│  ──LLM──▶ │ "The refund policy states    │
│ + user question  (~30 tokens)  │           │  that returns are accepted   │
│                                │           │  within 14 business days..." │
│ Total INPUT: ~1430 tokens      │           │ Total OUTPUT: ~70 tokens     │
└────────────────────────────────┘           └──────────────────────────────┘

Cost: (1430/1000 × $0.003) + (70/1000 × $0.015) = $0.00429 + $0.00105 = ~$0.005 per query
```

### Key insight

The LLM does **NOT** search for documents. It only **reads what you give it** (the context) and **writes an answer**. The searching happened earlier — `generate()` is step 3 of the RAG pipeline, not step 1.

- 🫏 **Donkey:** The delivery note: standing orders (system prompt) + cargo manifest (retrieved chunks) + the customer's specific request.

---

## Concept 3: Temperature — Controlling Randomness

**The parameter (line 50):** `temperature: float = 0.1`

Temperature controls how the LLM picks the next word. At each step, the model calculates a probability distribution over all possible next words:

```
Next word probabilities for "The refund policy ___":

  temperature=0.0     temperature=0.1      temperature=0.7      temperature=1.0
  (deterministic)     (this chatbot)       (creative)           (maximum random)

  "states"   → 95%    "states"   → 90%     "states"   → 45%     "states"   → 30%
  "allows"   → 3%     "allows"   → 6%      "allows"   → 25%     "allows"   → 22%
  "requires" → 1%     "requires" → 2%      "requires" → 15%     "requires" → 18%
  "is"       → 0.5%   "is"       → 1%      "is"       → 10%     "is"       → 15%
  "sucks"    → 0.001% "sucks"    → 0.01%   "sucks"    → 3%      "sucks"    → 10%
                                                                  ^^^^^^^^^^^^^  ← dangerous
```

### Temperature cheat sheet

| Temperature | Behaviour | Use case | 🫏 Donkey |
|---|---|---| --- |
| 0.0 | Always picks the highest-probability word | Math, code generation | 🫏 On the route |
| **0.1** | **Almost always the highest, tiny variation** | **RAG chatbots (this repo) — accuracy matters** | backpack check 🫏 |
| 0.7 | Distributes across likely words | Creative writing, brainstorming | Stable address 🏷️ |
| 1.0 | Nearly uniform distribution — anything goes | Experimental, often unusable | 🫏 On the route |

### Why 0.1 for this chatbot?

It answers questions about documents. You want **accurate, consistent** answers — not creative writing. The same question should give essentially the same answer every time. Like using `SELECT ... ORDER BY` instead of random sampling.

📖 **More on temperature:** [How Services Work → Converse API parameters](../architecture-and-design/how-services-work.md#the-converse-api--what-each-parameter-does)

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Concept 4: Embeddings — Turning Meaning into Math (`get_embedding()`)

**The code (lines 67–83):**
```python
@abstractmethod
async def get_embedding(self, text: str) -> list[float]:
```

**This is the most important new concept in this file.** It has NO data engineering equivalent.

```
INPUT:   "What is the refund policy?"        (a string — any length)
OUTPUT:  [0.12, -0.45, 0.78, ..., 0.33]     (always exactly 1024 floats for Titan)
```

### What happened?

The embedding model converted **meaning** into **math**. That list of 1024 numbers is a coordinate in 1024-dimensional space. Texts with similar meanings land near each other:

```
"What is the refund policy?"   → [0.12, -0.45, 0.78, ...]  ─┐ cosine similarity = 0.98
"How do I get my money back?"  → [0.11, -0.44, 0.79, ...]  ─┘ (very similar = same topic)

"What's the weather today?"    → [0.88, 0.23, -0.56, ...]  ─── cosine similarity = 0.15
                                                                 (very different topic)
```

### The closest DE analogy (imperfect)

Think of a hash function — it takes any input and produces a fixed-size output. But unlike a hash:
- **Similar inputs → similar outputs** (a hash would give totally different outputs)
- The output **preserves meaning relationships** (a hash deliberately destroys them)

### Critical facts about embeddings

| Property | Value | Why it matters | 🫏 Donkey |
|---|---|---| --- |
| Output size | Always 1024 floats (Titan) or 1536 (Azure) | Vector store must match this dimension | GPS warehouse 🗺️ |
| Input can be any length | `"Hi"` or a 2000-char paragraph → same 1024 floats | The model compresses meaning into fixed-size | backpack check 🫏 |
| Runs at two different times | Ingestion (embed every chunk) AND query (embed the question) | Both must use the **same** model — mixing models = garbage results | backpack piece 📦 |
| Not reversible | Cannot convert [0.12, -0.45, ...] back to text | Like a hash — one-way function | 🫏 On the route |

### When `get_embedding()` runs in the RAG pipeline

```
                    INGESTION (once per document)           QUERY (every user question)
                    ─────────────────────────────           ──────────────────────────
                    Doc → chunks → get_embedding()          Question → get_embedding()
                    each chunk → [1024 floats]              question  → [1024 floats]
                    stored in vector database               compared against stored vectors
                                                            → top-k most similar chunks returned
```

📖 **More on embeddings:** [RAG Concepts → What are Embeddings?](rag-concepts.md#what-are-embeddings) · [RAG Concepts → 42 Chunks Example](rag-concepts.md#concrete-example-42-chunks--42-vectors) · [RAG Concepts → Dimensions Must Match](rag-concepts.md#dimensions-must-match-between-model-and-store)

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Concept 5: Batch Embeddings — The Performance Optimisation (`get_embeddings_batch()`)

**The code (lines 85–97):**
```python
@abstractmethod
async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
```

### DE parallel

This is `INSERT INTO ... VALUES (), (), ()` (batch) vs individual `INSERT` statements. One network round-trip instead of N:

```python
# Slow: N network calls (one per chunk)
for chunk in 42_chunks:
    vector = await llm.get_embedding(chunk)     # 42 API calls = 42 round trips

# Fast: 1 network call (batch)
vectors = await llm.get_embeddings_batch(42_chunks)  # 1 API call = 1 round trip
```

Used during **ingestion** when embedding all chunks of a document at once. At query time you only embed one question, so `get_embedding()` is sufficient.

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Where `base.py` Sits in the RAG Pipeline

```
USER: "What is the refund policy?"
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        RAG Pipeline                                 │
│                                                                     │
│  Step 1: EMBED the question              ← base.py: get_embedding()│
│     llm.get_embedding("What is the refund policy?")                │
│     → [0.12, -0.45, 0.78, ...]                                    │
│                                                                     │
│  Step 2: SEARCH the vector store         ← vectorstore/base.py     │
│     vectorstore.search([0.12, -0.45, ...], k=5)                    │
│     → ["Chunk about refunds...", "Chunk about returns..."]         │
│                                                                     │
│  Step 3: GENERATE the answer             ← base.py: generate()     │
│     llm.generate(                                                   │
│         prompt="What is the refund policy?",                        │
│         context=["Chunk about refunds...", ...],                    │
│         temperature=0.1                                             │
│     )                                                               │
│     → LLMResponse(text="The refund policy states...",              │
│                    input_tokens=860, output_tokens=70)              │
│                                                                     │
└──────────────────────────────────────────────────────────────────────┘
```

**Notice:** `base.py` is used in steps 1 AND 3. The same `BaseLLM` interface handles both embedding and generation — but they use **different underlying models** (Titan for embeddings, Claude for generation). You'll see this in `aws_bedrock.py` (file #8).

- 🫏 **Donkey:** The donkey checks its backpack full of retrieved document chunks before answering — no guessing from memory.

---

## Questions to Ask Yourself After Reading This File

| Question | Answer | Concept it tests | 🫏 Donkey |
|---|---|---| --- |
| "What does `get_embedding()` return for a 2-word input vs a 2000-word input?" | The same: a list of exactly 1024 floats (Titan). Input length doesn't affect output size. | Embeddings | GPS warehouse 🗺️ |
| "Why does `LLMResponse` track `input_tokens` and `output_tokens` separately?" | Because output tokens cost 5× more. Tracking separately enables cost optimisation. | Tokens & cost | The donkey 🐴 |
| "What happens if you use temperature=0.8 instead of 0.1 for this chatbot?" | Answers become inconsistent and creative. The same question might get different answers. Hallucination risk increases. | Temperature | Memory drift ⚠️ |
| "Why is `get_embedding()` on the same `BaseLLM` class as `generate()`?" | Because the LLM *provider* (Bedrock/Azure) handles both, even though they use different models internally. It's an interface grouping by provider, not by model. | Strategy pattern | The donkey 🐴 |
| "What happens if you embed documents with Titan (1024-dim) but embed the question with Azure (1536-dim)?" | Vector search fails — you can't compare vectors of different dimensions. Both must use the same model. | Dimension matching | GPS warehouse 🗺️ |
| "How much does one `get_embedding()` call cost vs one `generate()` call?" | Embedding: ~$0.00002 (30 tokens × $0.0001/1K). Generation: ~$0.005 (1430 input + 70 output). Generation is ~250× more expensive. | Cost awareness | Cargo unit ⚖️ |

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.

---

## What to Study Next

Now that you understand the **interface**, study the **implementations**:
- **File #8:** [`src/llm/aws_bedrock.py`](../../src/llm/aws_bedrock.py) + [`src/llm/azure_openai.py`](../../src/llm/azure_openai.py) — the cloud provider implementations that call Bedrock (boto3) and Azure OpenAI (AsyncAzureOpenAI). Same SDK patterns you use for other cloud services, but calling a language model.
- **File #12:** [`src/llm/local_ollama.py`](../../src/llm/local_ollama.py) — the local Ollama implementation using plain HTTP (`httpx`). Runs entirely on your machine with no cloud credentials or costs.

📖 **Related docs:**
- [Deep Dive: LLM Providers (AWS Bedrock + Azure OpenAI + Local Ollama)](llm-providers-deep-dive.md)
- [RAG Concepts → Three Components](rag-concepts.md#the-three-components-you-must-understand)
- [Cost Analysis](cost-analysis.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
