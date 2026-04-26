# Deep Dive: Prompt Engineering — `src/rag/prompts.py`

> **Study order:** #12 · **Difficulty:** ★★★☆☆ (no new code patterns — the challenge is understanding *why* each word matters)  
>
> **File:** [`src/rag/prompts.py`](../../src/rag/prompts.py)  
>
> **Prerequisite:** [#7 — LLM Interface](llm-interface-deep-dive.md) · [#11 — Ingestion Pipeline](ingestion-pipeline-deep-dive.md)  
>
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — Prompts Are Query Templates](#de-parallel--prompts-are-query-templates)
3. [The Three Prompts](#the-three-prompts)
4. [Prompt 1: `RAG_SYSTEM_PROMPT` — The Core Instructions](#prompt-1-rag_system_prompt--the-core-instructions)
5. [Concept 1: Role Definition — Telling the LLM What It Is](#concept-1-role-definition--telling-the-llm-what-it-is)
6. [Concept 2: Constraints — The Rules That Prevent Hallucination](#concept-2-constraints--the-rules-that-prevent-hallucination)
7. [Concept 3: Template Variables — `{context}` and `{question}`](#concept-3-template-variables--context-and-question)
8. [Prompt 2: `RAG_CONVERSATIONAL_PROMPT` — Multi-Turn Chat](#prompt-2-rag_conversational_prompt--multi-turn-chat)
9. [Prompt 3: `SUMMARIZE_PROMPT` — Document Summarisation](#prompt-3-summarize_prompt--document-summarisation)
10. [How Prompts Are Used in the Pipeline (All Providers)](#how-prompts-are-used-in-the-pipeline)
11. [What Makes a Good Prompt — The Engineering Rules](#what-makes-a-good-prompt--the-engineering-rules)
12. [What Goes Wrong — Common Prompt Failures](#what-goes-wrong--common-prompt-failures)
13. [Cloud vs Local — How Prompts Behave Differently](#cloud-vs-local--how-prompts-behave-differently)
14. [Self-Test Questions](#self-test-questions)
15. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

This 65-line file controls **100% of the LLM's behaviour**. Change one word in the prompt and every answer the chatbot gives could change. In traditional engineering you write logic; in AI engineering you write *instructions* that a probabilistic model interprets.

| What you'll learn | DE parallel | 🚚 Courier |
|---|---| --- |
| System prompts that set LLM behaviour | SQL query templates with bind variables | The shipping manifest pinned to the dispatch board that every courier reads before any trip |
| Constraints that prevent hallucination | CHECK constraints that prevent bad data | Guardrails that stop the courier from inventing facts not found in its loaded parcel chunks |
| Template variables (`{context}`, `{question}`) | Parameterised queries (`?`, `$1`) | Blank slots on the shipping manifest where the shipping manifest and question get pasted in |
| Multi-turn conversation context | Session state management | Trip log entry — Multi-turn conversation context: Session state management |
| The cost impact of prompt length | The cost of scanning too many rows | Instructions tucked in the pannier — The cost impact of prompt length: The cost of scanning too many rows |

- 🚚 **Courier:** Think of this as the orientation briefing given to a new courier before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — Prompts Are Query Templates

```
DATA ENGINEER                              AI ENGINEER
────────────────                           ──────────────
SQL template:                              Prompt template:
  SELECT * FROM orders                       "You are a helpful assistant.
   WHERE customer = {customer_id}             Answer based on: {context}
   AND date > {start_date}                    Question: {question}"
   ORDER BY date DESC
   LIMIT 10

The template is fixed.                     The template is fixed.
The variables change per request.          The variables change per request.
Bad query = wrong rows.                    Bad prompt = hallucinated answers.
```

**The key difference:** A SQL template always returns the same result for the same input. A prompt template returns *slightly different* text each time (because LLMs are probabilistic). That's why `temperature=0.1` — to minimise the randomness.

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## The Three Prompts

```
src/rag/prompts.py
│
├── RAG_SYSTEM_PROMPT              ← The main one. Used for every chat query.
├── RAG_CONVERSATIONAL_PROMPT      ← For follow-up questions (includes history).
└── SUMMARIZE_PROMPT               ← For document summarisation (future feature).
```

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## Prompt 1: `RAG_SYSTEM_PROMPT` — The Core Instructions

This is the prompt sent to the LLM on **every chat query**:

```python
RAG_SYSTEM_PROMPT = """You are a helpful AI assistant that answers questions based on provided documents.

RULES:
1. ONLY use information from the context documents below to answer the question.
2. If the context does not contain enough information to answer, say:
   "I don't have enough information in the uploaded documents to answer that question."
3. Always cite which document(s) you used by referencing [Document chunk N].
4. Be concise but thorough — don't leave out important details.
5. Use bullet points for lists and structured information.
6. If the question is ambiguous, state your interpretation before answering.
7. Never make up information that isn't in the context.

CONTEXT DOCUMENTS:
{context}

---

USER QUESTION: {question}"""
```

**Every single line serves a purpose.** Let's break it down.

- 🚚 **Courier:** The courier checks its parcel full of retrieved document chunks before answering — no guessing from memory.

---

## Concept 1: Role Definition — Telling the LLM What It Is

```python
"You are a helpful AI assistant that answers questions based on provided documents."
```

**Why this line exists:** Without it, the LLM defaults to its general training — it will try to answer from its training data (Wikipedia, web pages, books). With it, the LLM understands its role is to be a *document-grounded* assistant.

**DE parallel:** This is like a SQL comment at the top of a stored procedure:
```sql
-- This procedure only returns data from the customer_orders table.
-- Do NOT join to external tables.
```

The role definition doesn't enforce anything technically — but it shifts the model's behaviour significantly.

**What happens without it:**

| With role definition | Without role definition | 🚚 Courier |
|---|---| --- |
| "Based on the documents, refunds take 14 days." | "Generally, refunds take 5-30 business days depending on the company." | Courier-side view of "Based on the documents, refunds take 14 days." — affects how the courier loads, reads, or delivers the parcels |
| Grounded in YOUR documents | Grounded in internet training data | Courier-side view of Grounded in YOUR documents — affects how the courier loads, reads, or delivers the parcels |
| Trustworthy for business use | Dangerous for business use | Courier-side view of Trustworthy for business use — affects how the courier loads, reads, or delivers the parcels |

- 🚚 **Courier:** The courier itself — it carries the question in, consults the parcel, and writes the answer on the way back.

---

## Concept 2: Constraints — The Rules That Prevent Hallucination

Each rule targets a specific failure mode:

| Rule | What it prevents | DE parallel | 🚚 Courier |
|---|---|---| --- |
| **Rule 1:** ONLY use context | Hallucination — making up facts | Referential integrity — no orphaned foreign keys | Forces courier to cite only parcel parcels — no guessing when it can't find the answer |
| **Rule 2:** Say "I don't know" | Confident wrong answers | `COALESCE(result, 'No data available')` | The courier honestly admitting it has no matching parcel rather than guessing |
| **Rule 3:** Cite sources | Untraceable claims | Audit trail — every row has a source system ID | Label on the original mail item the parcel was sliced from |
| **Rule 4:** Be thorough | Incomplete answers | `SELECT *` vs `SELECT id` — return all relevant columns | How confidently the warehouse says 'this parcel matches' — higher = closer GPS hit |
| **Rule 5:** Bullet points | Wall-of-text answers | Output formatting — structured JSON vs raw strings | Depot inspector — checks the code is tidy before letting the courier out |
| **Rule 6:** Handle ambiguity | Wrong interpretation | Input validation — clarify before processing | Courier-side view of Rule 6:** Handle ambiguity — affects how the courier loads, reads, or delivers the parcels |
| **Rule 7:** Never make up info | Reinforces Rule 1 | Defence in depth — multiple checks for the same risk | Courier-side view of Rule 7:** Never make up info — affects how the courier loads, reads, or delivers the parcels |

**Why Rule 7 repeats Rule 1:** LLMs respond to emphasis. Saying "only use context" (Rule 1) and "never make up information" (Rule 7) at the top AND bottom of the rules creates a "sandwich" effect — the model is less likely to hallucinate.

- 🚚 **Courier:** When the courier ignores the parcel and invents an answer from memory — RAG is the cure.

---

## Concept 3: Template Variables — `{context}` and `{question}`

```python
CONTEXT DOCUMENTS:
{context}

---

USER QUESTION: {question}
```

At runtime, `chain.py` replaces these:

```
{context}  →  "Chunk 1: Refunds are processed within 14 days...\n---\nChunk 2: To request a refund..."
{question} →  "What is the refund policy?"
```

**This is the RAG pattern in action:** the context comes from the vector store search (Step 2 in the pipeline), and the question comes from the user. The LLM sees both and generates an answer grounded in the context.

**Token cost impact:**

```
System prompt (rules):    ~80 tokens    (fixed — same every request)
Context (5 chunks):       ~750 tokens   (variable — depends on chunk_size × top_k)
Question:                 ~15 tokens    (variable — depends on user)
────────────────────────────────
Total input:             ~845 tokens

At $0.003/1K tokens (AWS) = $0.0025 per query
At $0.0025/1K tokens (Azure) = $0.0021 per query
At $0 (Local) = free
```

**The cost engineering insight:** The 80-token system prompt is cheap. The 750-token context is where cost grows. Reducing `top_k` from 5 to 3 saves ~300 tokens per query — that's ~$0.001 per query, or $30/month at 1000 queries/day.

- 🚚 **Courier:** Like a well-trained courier that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Prompt 2: `RAG_CONVERSATIONAL_PROMPT` — Multi-Turn Chat

```python
RAG_CONVERSATIONAL_PROMPT = """You are a helpful AI assistant...

CONVERSATION HISTORY:
{history}

CONTEXT DOCUMENTS:
{context}

---

USER QUESTION: {question}"""
```

**What's different:** The `{history}` variable injects previous messages:

```
CONVERSATION HISTORY:
User: "What is the refund policy?"
Assistant: "Refunds are processed within 14 days..."

CONTEXT DOCUMENTS:
[Chunk 1]: Digital products are non-refundable...

USER QUESTION: "What about digital products?"
```

Without history, the LLM would say *"I don't know what you're referring to"* — because "what about" has no referent. With history, the LLM understands "what about" refers to the refund policy from the previous turn.

**Token cost impact:** History adds ~100-200 tokens per previous turn. 10 turns of history = ~1500 extra tokens = ~$0.005 extra per query. This is why `get_history(limit=10)` caps the history.

📖 **Related:** [Conversation History Deep Dive](../architecture-and-design/history-explained.md)

- 🚚 **Courier:** The courier checks its parcel full of retrieved document chunks before answering — no guessing from memory.

---

## Prompt 3: `SUMMARIZE_PROMPT` — Document Summarisation

```python
SUMMARIZE_PROMPT = """Summarize the following document in a clear, structured way.
Use bullet points for key topics.
Keep the summary under 500 words.

DOCUMENT:
{document}"""
```

This is a simpler prompt — no context retrieval needed, just summarise a full document. It's used for the future document summary feature.

**Key constraints:** "under 500 words" limits output tokens (~670 tokens). Without this limit, the LLM might generate a 2000-word summary that costs 4x more.

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## How Prompts Are Used in the Pipeline

All three providers (AWS, Azure, Local) use the same prompt templates, but they format them slightly differently when sending to their respective APIs:

```
prompts.py                          chain.py                             LLM Provider
─────────                           ────────                             ────────────
RAG_SYSTEM_PROMPT                   query():
  template with                       1. Vector search → context
  {context} and                       2. Format prompt with context
  {question}                          3. llm.generate(question, context)
                                            │
                        ┌───────────────────┼───────────────────┐
                        ▼                   ▼                   ▼
                   BedrockLLM         AzureOpenAILLM       OllamaLLM
                   (Claude)           (GPT-4o)             (llama3.2)
                   ─────────          ──────────           ─────────
                   system=[{text:     messages=[           messages=[
                     system_prompt}]    {role:"system",      {role:"system",
                   messages=[{          content:prompt},     content:prompt},
                     role:"user",       {role:"user",        {role:"user",
                     content:msg}]      content:msg}]        content:msg}]
```

| Aspect | AWS (Bedrock/Claude) | Azure (OpenAI/GPT-4o) | Local (Ollama/llama3.2) | 🚚 Courier |
|---|---|---|---| --- |
| **System prompt placement** | Separate `system` field | `role: "system"` message | `role: "system"` message | Shipping manifest pinned to the saddle — System prompt placement: Separate system field · role: "system" message · role: "system" message |
| **User message** | `content: [{text: ...}]` (nested) | `content: "..."` (flat string) | `content: "..."` (flat string) | The customer's question — written on the shipping manifest for the courier to read |
| **Prompt format** | Identical template text | Identical template text | Identical template text | Note the courier carries — Prompt format: Identical template text · Identical template text · Identical template text |
| **Behaviour difference** | Best instruction following | More creative/verbose | Good but less nuanced | How precisely the courier obeys the shipping manifest on the shipping manifest |
| **Cost per prompt** | ~$0.0025 | ~$0.0021 | **$0** | Customer's written brief — Cost per prompt: ~$0.0025 · ~$0.0021 · $0 |

**Key insight:** The prompt text is the same across all providers. Only the API format differs. This is handled by each provider's `generate()` method, not by the prompt itself.

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## What Makes a Good Prompt — The Engineering Rules

| Rule | This prompt's example | Anti-pattern | 🚚 Courier |
|---|---|---| --- |
| **Be specific** | "ONLY use information from the context" | "Try to use the context" | Depot inspector — checks the code is tidy before letting the courier out |
| **Define fallback** | "If context doesn't have the answer, say so" | (no fallback → LLM guesses) | Tell the courier what to say when the parcel is empty, or it will invent parcels to deliver |
| **Constrain format** | "Use bullet points" | (no format → wall of text) | Depot inspector — checks the code is tidy before letting the courier out |
| **Separate sections** | `---` between context and question | Everything jumbled together | Courier-side view of Separate sections — affects how the courier loads, reads, or delivers the parcels |
| **Limit scope** | "answers questions based on provided documents" | "You are a general-purpose AI" | Courier-side view of Limit scope — affects how the courier loads, reads, or delivers the parcels |

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## What Goes Wrong — Common Prompt Failures

| Problem | Cause | Fix | How to detect | 🚚 Courier |
|---|---|---|---| --- |
| Hallucination | Rules too weak or model ignores them | Stronger constraints, lower temperature | Faithfulness score < 0.8 in evaluator | Courier invents facts not in its parcel — tighten prompt rules or lower temperature |
| Verbose answers | No length constraint | Add "Keep answers under 200 words" | Token count > 500 output tokens | Courier rambles for 500+ tokens — add word limit to shipping manifest to control fuel waste |
| Ignores citations | Model doesn't see "[Document chunk N]" pattern | Add example output in prompt | Missing `[Document chunk` in answer | Courier forgets to label which parcel it read — show citation example on the shipping manifest |
| Wrong language | User asks in Dutch, prompt is English | Add "Answer in the same language as the question" | Manual review | Shipping manifest pinned to the saddle — Wrong language: User asks in Dutch, prompt is English · Add "Answer in the same language as the |
| Off-topic | Context chunks are irrelevant | Better chunking/retrieval, not a prompt fix | Answer relevance score < 0.5 | Courier got wrong parcels from the warehouse — fix GPS search, not the shipping manifest |

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## Cloud vs Local — How Prompts Behave Differently

The same prompt produces different quality answers depending on the model:

| Aspect | Claude 3.5 Sonnet (AWS) | GPT-4o (Azure) | llama3.2 (Local) | 🚚 Courier |
|---|---|---|---| --- |
| **Instruction following** | Excellent — follows rules precisely | Very good — sometimes verbose | Good — occasionally ignores minor rules | How precisely the courier obeys the shipping manifest on the shipping manifest |
| **Citation accuracy** | Almost always cites correctly | Usually cites, sometimes forgets | May not cite consistently | Receipts the courier hands over — which parcels the answer came from |
| **"I don't know" response** | Reliably says it when context is empty | Usually says it | Sometimes tries to answer anyway | What the courier wrote and brought back to the customer |
| **Temperature sensitivity** | Very responsive to 0.1 | Responsive | Less precise control | How predictable the courier's writing is — low = same words every trip, high = the courier gets creative |
| **Recommended for** | Production (highest quality) | Production (good balance) | Development and testing | Practice run for the courier — Recommended for: Production (highest quality) · Production (good balance) · Development and testing |
| **Cost per query** | ~$0.0065 | ~$0.005 | **$0** | AWS fuel costs $0.0065 a trip, Azure $0.005, your own llama3.2 grazes free in the back yard. |

**Practical advice:**
- **Develop and iterate** with `CLOUD_PROVIDER=local` — test prompt changes for free
- **Validate** with a cloud provider before deploying — run the evaluation suite (#14)
- **Monitor** faithfulness scores (#16) — if they drop, the prompt needs adjustment

- 🚚 **Courier:** The shipping manifest: shipping manifest (system prompt) + shipping manifest (retrieved chunks) + the customer's specific request.

---

## Self-Test Questions

After reading this, can you answer:

### Tier 1 — Must understand

- [ ] What is a system prompt and why does every RAG request need one?
- [ ] Why does Rule 1 say "ONLY use context" — what happens without it?
- [ ] What do `{context}` and `{question}` get replaced with at runtime?
- [ ] Why does the conversational prompt include `{history}`?

### Tier 2 — Should understand

- [ ] How many tokens does the system prompt add per request? What's the cost impact?
- [ ] Why is Rule 7 ("Never make up info") a repeat of Rule 1?
- [ ] How would you modify the prompt if users ask questions in Dutch?
- [ ] What's the cost difference between `top_k=5` and `top_k=3` at 1000 queries/day?

### Tier 3 — AI engineering territory

- [ ] How would you A/B test two different prompts? (Hint: evaluation framework, #14)
- [ ] When should you add "Answer in bullet points" vs "Answer in complete sentences"?
- [ ] If the faithfulness score drops after changing the prompt, what do you check first?
- [ ] How does prompt length interact with the model's context window limit?

- 🚚 **Courier:** Sending the courier on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

Now you know how the LLM gets its instructions. Next:

- **File #13:** [`src/rag/chain.py`](rag-chain-deep-dive.md) — the orchestrator that puts prompts + embeddings + search together into the full RAG pipeline
- **File #14:** [`src/evaluation/evaluator.py`](evaluation-framework-deep-dive.md) — how to measure if your prompt changes actually improved things

📖 **Related docs:**
- [RAG Concepts → How RAG Works](rag-concepts.md#how-rag-works-step-by-step)
- [Chat Endpoint Deep Dive](../architecture-and-design/api-routes/chat-endpoint-explained.md)
- [Cost Analysis](cost-analysis.md)
- [LLM Interface Deep Dive (#7)](llm-interface-deep-dive.md)

- 🚚 **Courier:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
