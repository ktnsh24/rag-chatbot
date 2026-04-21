# Hands-On Labs — Phase 1: Foundation Skills

---

## Table of Contents

- [Cost Estimation — Local vs Cloud](#cost-estimation--local-vs-cloud)
  - [Local (current setup) — FREE](#local-current-setup--free)
  - [AWS — Estimated cost for running these labs](#aws--estimated-cost-for-running-these-labs)
  - [Azure — Estimated cost for running these labs](#azure--estimated-cost-for-running-these-labs)
  - [Summary](#summary)
- [Setup — Upload a Test Document (Do This First)](#setup--upload-a-test-document-do-this-first)
- [🫏 The Donkey Analogy — Understanding Phase 1 Metrics](#-the-donkey-analogy--understanding-phase-1-metrics)
- [Lab 1: Retrieval Quality — "Did I find the right chunks?"](#lab-1-retrieval-quality--did-i-find-the-right-chunks)
  - [Experiment 1a — Baseline retrieval](#experiment-1a--baseline-retrieval)
  - [Experiment 1b — Change top_k and see the impact](#experiment-1b--change-top_k-and-see-the-impact)
  - [Experiment 1c — Ask something NOT in the document](#experiment-1c--ask-something-not-in-the-document)
  - [What you learned](#what-you-learned)
- [Lab 2: Faithfulness & Hallucination — "Is the AI making things up?"](#lab-2-faithfulness--hallucination--is-the-ai-making-things-up)
  - [Experiment 2a — Trick question (partial context)](#experiment-2a--trick-question-partial-context)
  - [Experiment 2b — Compare with a truthful question](#experiment-2b--compare-with-a-truthful-question)
  - [Experiment 2c — Edge case: ambiguous question](#experiment-2c--edge-case-ambiguous-question)
  - [What you learned](#what-you-learned-1)
- [Phase 1 Labs — Skills Checklist](#phase-1-labs--skills-checklist)

---

## Cost Estimation — Local vs Cloud

All three phases of labs work **locally for free**. If you later switch to cloud providers,
here's what it costs:

### Local (current setup) — FREE

| Component | Tool | Cost |
| --- | --- | --- |
| LLM | Ollama + llama3.2 (3B) | **$0** — runs on your CPU |
| Embeddings | nomic-embed-text (137M) | **$0** — runs on your CPU |
| Vector store | ChromaDB (local file) | **$0** — local SQLite |
| API server | Uvicorn (local) | **$0** — runs on your machine |
| **Total for all labs** | | **$0** |

### AWS — Estimated cost for running these labs

| Component | AWS Service | Cost per lab session (~50 queries) | Monthly if left running |
| --- | --- | --- | --- |
| LLM | Bedrock (Claude 3 Haiku) | ~$0.02 (input+output tokens) | Pay per use only |
| Embeddings | Bedrock (Titan Embed v2) | ~$0.001 | Pay per use only |
| Vector store | OpenSearch Serverless | ⚠️ **~$350/month minimum** (4 OCUs) | Avoid for portfolio |
| Vector store (alt) | DynamoDB + local embeddings | ~$0 (free tier: 25GB + 25 RCU/WCU) | $0 in free tier |
| API server | ECS Fargate (0.25 vCPU, 0.5GB) | ~$0.01/hour when running | ~$7/month if 24/7 |
| API server (alt) | Lambda + API Gateway | ~$0 for lab traffic | $0 in free tier |
| Logs | CloudWatch | ~$0 | $0 in free tier |
| **Total (cheapest path)** | Bedrock + DynamoDB + Lambda | **~$0.03 per lab session** | **~$1/month** |
| **Total (full stack)** | Bedrock + OpenSearch + ECS | **~$0.03 per lab session** | **⚠️ ~$360/month** |

> **Recommendation:** Use Bedrock (pay-per-use) + DynamoDB (free tier) + Lambda (free tier).
> Avoid OpenSearch Serverless for portfolio work — the $350/month minimum is not justified.

### Azure — Estimated cost for running these labs

| Component | Azure Service | Cost per lab session (~50 queries) | Monthly if left running |
| --- | --- | --- | --- |
| LLM | Azure OpenAI (GPT-4o mini) | ~$0.01 (input+output tokens) | Pay per use only |
| Embeddings | Azure OpenAI (text-embedding-3-small) | ~$0.001 | Pay per use only |
| Vector store | Azure AI Search (Free tier) | **$0** | $0 (free tier: 3 indexes, 50MB) |
| Vector store (paid) | Azure AI Search (Basic) | ~$0 for lab traffic | ~$75/month |
| API server | Azure Container Apps | ~$0 (free tier: 180K vCPU-sec/month) | $0 in free tier |
| Logs | Azure Monitor | ~$0 | $0 in free tier |
| **Total (cheapest path)** | OpenAI + AI Search free + Container Apps free | **~$0.01 per lab session** | **~$0/month** |
| **Total (paid tier)** | OpenAI + AI Search Basic + Container Apps | **~$0.01 per lab session** | **~$75/month** |

> **Recommendation:** Azure's free tiers are more generous for this use case. AI Search
> free tier (3 indexes, 50MB) is enough for all labs. Container Apps free tier handles
> portfolio-level traffic easily.

### Summary

| Stack | Per lab session | Monthly (always on) | Best for |
| --- | --- | --- | --- |
| **Local (Ollama)** | $0 | $0 | Learning, experimenting (current) |
| **AWS (cheapest)** | ~$0.03 | ~$1 | Proving cloud deployment skills |
| **Azure (cheapest)** | ~$0.01 | ~$0 | Best free tier for portfolio |
| **AWS (full)** | ~$0.03 | ~$360 | ⚠️ Production only |
| **Azure (paid)** | ~$0.01 | ~$75 | Production staging |

---

## Setup — Upload a Test Document (Do This First)

Create a file called `test-policy.txt` with this content:

```text
REFUND POLICY

Section 1: General Returns
All products can be returned within 14 business days of purchase.
Products must be in original, unopened packaging.
To request a refund, email support@example.com with your order number.

Section 2: Digital Products
Digital products and gift cards are non-refundable.
All sales of downloadable content are final.
If a digital product is defective, contact support for a replacement.

Section 3: Shipping Returns
Return shipping costs are the customer's responsibility.
Free shipping on orders over 50 euros does not apply to returns.
International returns must include a customs declaration form.
```

Upload it via **Swagger UI** (`http://localhost:8000/docs`):

1. Find `POST /api/documents/upload`
2. Click **"Try it out"**
3. Click **"Choose File"** and select `test-policy.txt`
4. Click **"Execute"**

You'll use this document for all Phase 1 labs.

---

## 🫏 The Donkey Analogy — Understanding Phase 1 Metrics

Imagine you own a donkey that delivers packages in a village. You give the donkey
an address, it walks to a shelf of packages, picks some, and delivers them to the
customer. Phase 1 metrics measure **how well the donkey does its job:**

| Metric | Donkey version | What it really measures |
| --- | --- | --- |
| **retrieval** | Did the donkey grab the **right packages** from the shelf? If you asked for "refund policy" and it brought back 3 refund-related packages out of 5 total, that's decent retrieval. If it brought back 5 packages about office furniture — terrible retrieval. | How relevant are the chunks the vector store returned for your question. |
| **faithfulness** | Did the donkey **only deliver what it picked up**, or did it add random items from its own pocket? If the customer opens the delivery and finds exactly what was on the shelf — faithful. If the donkey added a sandwich it found on the road — hallucination. | Does the LLM answer contain ONLY information from the retrieved chunks, or did it make things up? |
| **answer_relevance** | Did the customer **get what they actually asked for?** The donkey might faithfully deliver the right packages from the shelf, but if the customer asked "what's the return window?" and the answer talks about shipping costs — irrelevant. | Does the answer actually address the question that was asked? |
| **overall** | The donkey's **performance review** — a weighted average: 30% right packages (retrieval) + 40% didn't add extras (faithfulness) + 30% customer got what they asked for (relevance). A score of 0.70+ means the donkey gets to keep its job. | Weighted combination: retrieval x 0.3 + faithfulness x 0.4 + relevance x 0.3. |
| **latency** | **How long** did the donkey take to walk to the shelf, pick packages, and deliver? A village donkey (local Ollama) takes 10–60 seconds. A racing donkey (cloud GPU) takes 1–3 seconds. | Total time from question to answer, including embedding, retrieval, and LLM generation. |
| **top_k** | How many packages you **told the donkey to grab** from the shelf. `top_k=1` means "bring me only the single best match" (fast, precise, but risky if the answer spans multiple sections). `top_k=10` means "bring 10 packages" (slower, noisier, but the right one is probably in there somewhere). | Number of document chunks retrieved from the vector store per query. |

**The key trade-off you'll discover in Lab 1:**

```text
top_k=1:  🫏 grabs 1 package  → fast, precise, but might miss context
top_k=5:  🫏 grabs 5 packages → balanced (the default)
top_k=10: 🫏 grabs 10 packages → slow, noisy, but nothing is missed
```

The donkey's dilemma: grab fewer packages (high retrieval score, risk missing info)
or grab more (low retrieval score, but safer for complex questions). This is the
**retrieval-faithfulness trade-off** — the foundation of every RAG system.

---

## Lab 1: Retrieval Quality — "Did I find the right chunks?"

**Skill:** Retrieval quality measurement and tuning

**Time:** 30 minutes

**What you'll understand after:** Why `top_k` matters, how to measure retrieval quality, how one parameter change ripples through the entire pipeline.

**Maps to:** Phase 1, item 2 (`src/api/routes/`) + Phase 3, item 14 (`src/evaluation/evaluator.py`)

### Experiment 1a — Baseline retrieval

Ask a question you KNOW the answer to.

In **Swagger UI** → `POST /api/evaluate` → **"Try it out"**, enter:

```json
{
  "question": "What is the refund policy for digital products?"
}
```

Click **"Execute"**.

📝 **Write down your baseline:**

| Score | Your value | Quality label |
|---|---|---|
| retrieval | ___ | ___ |
| faithfulness | ___ | ___ |
| answer_relevance | ___ | ___ |
| overall | ___ | ___ |
| latency | ___s | ___ |

> **What to expect (local):** retrieval 0.55–0.70, faithfulness 0.70–0.85, answer_relevance 0.90–1.0, overall 0.70–0.85, latency 10–60s on CPU.

> ### 📊 Understanding "Fair" Scores — Why They're Expected with a Local Model
>
> If you're running locally with **llama3.2** + **nomic-embed-text**, you'll
> likely see scores like these:
>
> | Score | Typical local value | Cloud equivalent | Why the gap? |
> |---|---|---|---|
> | retrieval | 0.55–0.70 ("fair") | 0.80–0.95 ("excellent") | Local embeddings (nomic-embed-text, 137M params) have less semantic precision than cloud models (OpenAI text-embedding-3-large, 3072 dims). Cosine similarities are lower, dragging the average down. |
> | faithfulness | 0.70–0.85 | 0.90–1.0 | A 3B-parameter model sometimes adds filler phrases like "I don't have enough information to fully answer…" which the keyword-based evaluator flags as not grounded in context — even though it's a cautious (good) behaviour, not hallucination. |
> | answer_relevance | 0.90–1.0 | 0.95–1.0 | Local models handle this well — if the question keywords appear in the answer, the score is high. Least affected by model size. |
> | overall | 0.70–0.85 | 0.85–0.95 | Weighted average: retrieval × 0.3 + faithfulness × 0.4 + relevance × 0.3 |
> | passed | ✅ True (≥ 0.7) | ✅ True | The 0.7 pass threshold is deliberately set to accommodate local models |
>
> **Why this is fine:**
>
> 1. **Retrieval "fair" ≠ bad.** It means the vector store found *relevant* chunks,
>    but cosine distances from a small embedding model are naturally lower. The *ranking*
>    is usually correct — the right chunk is still on top, it's just scored 0.62 instead of 0.89.
>
> 2. **Faithfulness < 1.0 ≠ hallucination.** The evaluator uses keyword overlap, which is a
>    *heuristic*. When the LLM adds a polite disclaimer ("Based on the provided context…" or
>    "I don't have enough information…"), those words don't appear in the source document →
>    they get flagged. In production, you'd use **LLM-as-judge** (a second LLM evaluating the
>    first) which understands that disclaimers aren't hallucinations.
>
> 3. **The purpose of local evaluation is *relative comparison*, not absolute numbers.**
>    Your baseline overall score is your anchor. When you change `top_k` in Experiment 1b,
>    you're looking at *whether the score goes up or down* — not whether it hits 0.95.
>
> **DE parallel:** This is like running integration tests against a local Postgres vs the
> production Redshift. The local tests catch logic bugs, but performance numbers are
> meaningless to compare — different hardware, different scale. Same idea here.

### Experiment 1b — Change top_k and see the impact

In **Swagger UI** → `POST /api/evaluate` → **"Try it out"**:

**With top_k=1** (only 1 chunk sent to LLM):

```json
{
  "question": "What is the refund policy for digital products?",
  "top_k": 1
}
```

**With top_k=10** (10 chunks — more context but more noise):

```json
{
  "question": "What is the refund policy for digital products?",
  "top_k": 10
}
```

📝 **Record your results:**

| top_k | retrieval | faithfulness | overall | latency | What happened? |
|---|---|---|---|---|---|
| 1 | ___ | ___ | ___ | ___s | ___ |
| 5 (default) | ___ | ___ | ___ | ___s | ___ |
| 10 | ___ | ___ | ___ | ___s | ___ |

> **What to expect (local):** top_k=1 typically scores highest retrieval (0.70–0.80) but risks missing multi-section context. top_k=10 dilutes retrieval (0.45–0.60) but provides more context. Latency scales roughly linearly with top_k.

**Expected pattern:**

| top_k | Expected retrieval | Your result | Expected faithfulness | Your result | Why |
|---|---|---|---|---|---|
| 1 | Higher (only best chunk) | ___ | May drop (missing context) | ___ | Only 1 chunk → focused answer, no filler sentences |
| 5 | Balanced | ___ | Balanced | ___ | Middle ground — LLM may add disclaimer |
| 10 | Lower (diluted by weak chunks) | ___ | May improve (more context) | ___ | All context available → confident answer |

> ### 📊 What These Results Reveal — The Three Trade-offs
>
> **1. Retrieval drops as top_k increases**
>
> This is the **averaging effect**. With `top_k=1`, ChromaDB returns only the *best*
> chunk (Section 2: Digital Products). With `top_k=10`, it must return 10
> chunks — but `test-policy.txt` only has ~3 relevant sections. Chunks 4–10 are low-relevance
> filler that drags the average down. The *ranking* didn't change — the best chunk is still #1.
>
> DE parallel: `SELECT TOP 1 ... ORDER BY relevance DESC` gives a higher average than
> `SELECT TOP 10` — because rows 7–10 are noise.
>
> **2. Faithfulness depends on LLM phrasing, not just retrieval**
>
> | top_k | faithfulness | Why |
> |---|---|---|
> | 1 | (your value) | One focused chunk → LLM answers with bullet points straight from the document → no filler |
> | 5 | (your value) | Middle amount of context → LLM hedges with "I don't have enough information…" → that sentence gets flagged |
> | 10 | (your value) | All context available → LLM feels confident → cites document directly → no disclaimers |
>
> The evaluator uses **keyword overlap** to check each sentence against the source.
> A polite disclaimer has words that don't appear in `test-policy.txt` → flagged as
> "not grounded." This is a limitation of the heuristic evaluator. In production,
> **LLM-as-judge** would understand that disclaimers aren't hallucinations.
>
> **3. Latency scales with context size**
>
> More chunks = more tokens in the prompt = more inference time on a local CPU.
> With `top_k=10`, the LLM processes ~4× more context than `top_k=1`. On a cloud GPU,
> this difference shrinks to milliseconds — but locally, it's the difference between
> seconds and nearly a minute.
>
> **Bottom line:** `top_k=1` typically gives the *best overall score* for single-section questions.
> But don't conclude "always use top_k=1" — try Experiment 1c with a question that
> spans multiple sections. That's where `top_k=1` will fail and `top_k=5` wins.

### Experiment 1c — Ask something NOT in the document

In **Swagger UI** → `POST /api/evaluate`, enter:

```json
{
  "question": "What is the company policy on remote work?"
}
```

**What to observe:** Retrieval score should be LOW (no relevant chunks). A good AI says "I don't have that information." A bad AI hallucinate an answer. Check `has_hallucination` in the response.

📝 **Results:**

| Metric | Value | Interpretation |
| --- | --- | --- |
| retrieval | ___ | ChromaDB returned *something* — but nothing relevant |
| faithfulness | ___ | Evaluator flagged sentences as "not from context" |
| has_hallucination | ___ | Check the analysis below |
| answer_relevance | ___ | ___ |
| overall | ___ | ___ |
| evaluation_notes | ___ | ___ |

> **What to expect (local):** retrieval 0.40–0.60 (irrelevant chunks returned), faithfulness near 0.0 (refusal gets flagged), overall below 0.5 (FAIL). The failure is correct — see analysis below.

> ### 📊 The "Correct Refusal" Paradox
>
> Look at the `evaluation_notes` — they contain **two contradictory signals:**
>
> 1. `ℹ️ Model correctly refused to answer (no relevant context)` — the refusal detector triggered ✅
> 2. `⚠️ HALLUCINATION: 2 sentences may not be from context` — the faithfulness checker also triggered ❌
>
> **What happened:** The LLM answered something like: *"I don't have enough information...
> The context only discusses [topics from other documents in your vector store]..."*
>
> The refusal detector correctly identified this as a refusal. But the faithfulness evaluator
> *also* ran and flagged sentences — the LLM described *what the irrelevant chunks contained*,
> and those descriptive sentences contain words that don't match the chunk content closely
> enough → flagged.
>
> **Why faithfulness may be 0.0:** The LLM described *what the irrelevant chunks contained*.
> Those descriptive sentences contain words that don't match the chunk content closely enough → flagged.
>
> **This is a known limitation of heuristic evaluation.** The correct behaviour is:
> faithfulness should be 1.0 for a refusal (the model *didn't* make anything up). In
> production, you'd either:
> - Give refusals an automatic faithfulness = 1.0 override
> - Use LLM-as-judge which understands refusals aren't hallucinations
>
> **The retrieval score is the real signal here.** It tells you: "the vector store
> couldn't find relevant content" — which is correct, because remote work policy isn't
> in `test-policy.txt`.
>
> **DE parallel:** This is like a `LEFT JOIN` returning NULLs — the query ran fine,
> there's just no matching data. The join isn't broken; the data doesn't exist.

### What you learned

The **retrieval-faithfulness trade-off** played out with real numbers:

- **top_k=1:** highest retrieval, best overall — precise but risky for multi-section questions
- **top_k=5:** balanced retrieval, solid overall — the safe default
- **top_k=10:** lowest retrieval, lower overall — noisy retrieval but enough context for faithful answers
- **Out-of-scope question:** low retrieval, low overall — **failed** ❌ (correct behaviour!)

The surprise: `top_k=1` scored highest *for this question*. But this question lives in a single section. Questions that span multiple sections (like "summarise the entire refund policy") would fail at `top_k=1`.

The out-of-scope question revealed a **real limitation**: the heuristic evaluator gives faithfulness=0.0 for refusals, when it should give 1.0. This is why production systems use LLM-as-judge.

This trade-off is the first thing an AI engineer checks when debugging a bad answer: "Was the retrieval good? Or did the LLM get bad chunks?"

**✅ Skill unlocked:** You can measure retrieval quality, explain why `top_k` matters, diagnose whether a bad answer is a retrieval problem or a generation problem, and identify evaluator limitations.

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A company's customer support chatbot retrieves financial regulation documents from a database with 10 million embeddings. They need low-latency, multilingual search with metadata filtering. Which vector store?"**
>
> You know from Lab 1 that retrieval quality depends on the vector store + embedding model.
> You tested `top_k` and saw how more candidates dilute retrieval. For 10M documents with
> metadata filtering, you need a managed vector store (OpenSearch Serverless or Azure AI Search),
> not brute-force DynamoDB. You'd pick **OpenSearch Serverless** because it supports k-NN + BM25
> hybrid natively, handles metadata filters (date, agency, type), and scales to millions.
> *(Answer: A — OpenSearch Serverless + Bedrock Knowledge Bases)*
>
> **Q: "A company's RAG application returns relevant-looking but incorrect chunks for long technical documents. How do they optimise?"**
>
> You tuned `rag_chunk_size` and `top_k` in this lab. You saw that smaller chunks = more precise
> but miss cross-section context. For long technical docs, you'd recommend: increase chunk overlap
> (Lab 1 parameter), tune top_k per use case, and add re-ranking (Lab 10).
>
> **Q: "When should a company use RAG vs fine-tuning?"**
>
> You built a RAG system that answers questions from uploaded documents WITHOUT training.
> You know RAG is for when the knowledge changes (policies, regulations) — you just upload
> new documents. Fine-tuning is for when you need the model to behave differently (tone, format).
> Your Lab 1 experience: upload `test-policy.txt` → instantly answerable. No training needed.

---

## Lab 2: Faithfulness & Hallucination — "Is the AI making things up?"

**Skill:** Hallucination detection, faithfulness evaluation

**Time:** 20 minutes

**What you'll understand after:** What hallucination looks like in numbers, why faithfulness gets the highest weight (40%) in the overall score, and how to catch it.

**Maps to:** Phase 3, item 14 (`src/evaluation/evaluator.py` → `_evaluate_faithfulness()`)

### Experiment 2a — Trick question (partial context)

The document says "14 business days" — ask a slightly different question:

In **Swagger UI** → `POST /api/evaluate`, enter:

```json
{
  "question": "Can I get a refund after 30 days?"
}
```

**What to observe:** The document says 14 days. If the AI answers "Yes, within 30 days" — that's hallucination. Check:

- `faithfulness` — should be < 1.0 if it hallucinated
- `has_hallucination: true` — the evaluator caught it
- `evaluation_notes` — will say "⚠️ HALLUCINATION: X sentences may not be from context"

📝 **Results:**

| Metric | Value | Interpretation |
| --- | --- | --- |
| retrieval | ___ | ___ |
| faithfulness | ___ | ___ |
| has_hallucination | ___ | ___ |
| answer_relevance | ___ | ___ |
| overall | ___ | ___ |

> **What to expect (local):** retrieval 0.55–0.70 (found the right section), faithfulness 0.60–0.85, has_hallucination may be true (see analysis below). The LLM may correctly say "14 days" while quoting "30 days" from the question — which the evaluator flags.

**What to look for in the AI's answer:** Did it say "Yes, within 30 days" (hallucination) or
"No, the maximum return period is 14 business days" (correct)? Check the actual response carefully.

**Why has_hallucination may be true:** If the LLM's answer contains "30
days" — a number from the *question* that doesn't appear in `test-policy.txt` — the keyword
overlap checker flags it. But the LLM was *quoting the question*, not making a claim.
This is another heuristic evaluator limitation — it can't distinguish "the LLM is
referencing the user's question" from "the LLM invented a number."

### Experiment 2b — Compare with a truthful question

In **Swagger UI** → `POST /api/evaluate`, enter:

```json
{
  "question": "How many days do I have to return a product?"
}
```

**What to observe:** This should have HIGH faithfulness because the answer comes directly from the document ("14 business days").

📝 **Results:**

| Metric | Value | Interpretation |
| --- | --- | --- |
| retrieval | ___ | ___ |
| faithfulness | ___ | ___ |
| has_hallucination | ___ | ___ |
| answer_relevance | ___ | ___ |
| overall | ___ | ___ |
| latency | ___s | ___ |

> **What to expect (local):** retrieval 0.65–0.80 (direct keyword match helps), faithfulness near 1.0 (answer comes straight from document), overall should pass comfortably.

📝 **Compare:**

| | Experiment 2a (trick) | Experiment 2b (truthful) | Gap |
| --- | --- | --- | --- |
| faithfulness | ___ | ___ | The gap IS the hallucination signal |
| has_hallucination | ___ | ___ | 2a may be flagged because LLM quoted "30 days" from the question |
| retrieval | ___ | ___ | "How many days" matches the document better than "after 30 days" |
| latency | ___s | ___s | Shorter answers = fewer output tokens = faster |

### Experiment 2c — Edge case: ambiguous question

In **Swagger UI** → `POST /api/evaluate`, enter:

```json
{
  "question": "How long?"
}
```

**What to observe:** Vague question → retrieval finds multiple chunks (14 days for refunds? 3-5 days for shipping?) → answer may mix topics → faithfulness may drop.

📝 **Results:**

| Metric | Value | Interpretation |
| --- | --- | --- |
| retrieval | ___ | Lowest retrieval — "how long?" is too vague for precise vector search |
| faithfulness | ___ | ___ |
| has_hallucination | ___ | ___ |
| answer_relevance | ___ | ___ |
| overall | ___ | ___ |

> **What to expect (local):** retrieval 0.40–0.55 (vague query = poor embedding match), faithfulness may be high if the model refuses to guess. overall may surprise you — see analysis below.

**What to look for:** Did the LLM refuse to guess ("I don't have enough information...")? Or did it pick a topic and answer it? A refusal is actually the safest response for evaluation.

> ### 📊 Surprise Result — Why Did the Ambiguous Question Score HIGHER Than the Trick Question?
>
> | Experiment | Question | overall | Why |
> | --- | --- | --- | --- |
> | 2a (trick) | "Can I get a refund after 30 days?" | (your value) | LLM answered correctly but quoted "30 days" → flagged |
> | 2c (ambiguous) | "How long?" | (your value) | LLM refused to guess → refusal = faithfulness 1.0 |
>
> The ambiguous question scored *higher* because the LLM's refusal was the **safest
> possible response**. It didn't hallucinate, didn't speculate, and the refusal detector
> gave it credit. The trick question scored lower because the LLM gave a *correct but
> detailed answer* that happened to reference "30 days" from the question.
>
> **Key insight:** In RAG evaluation, **saying "I don't know" is safer than being
> right in a way the evaluator can't verify.** This is why production systems need
> LLM-as-judge — a heuristic evaluator penalises correct answers that reference the
> question's own terms.
>
> **Which score dropped the most?** Retrieval — because "How long?" has almost
> no semantic signal for the embedding model to work with. It matched weakly against
> everything. This confirms: **vague questions are a retrieval problem**, not a
> generation problem.

### What you learned

Faithfulness = "does the answer stick to the context?" It gets 40% weight because hallucination is the **most dangerous failure mode** in AI. A wrong answer that sounds confident is worse than no answer at all.

The evaluator catches hallucination by: splitting the answer into sentences → extracting keywords → checking if ≥50% of keywords appear in the retrieved context. Sentences that fail this check are flagged.

**Your experiments revealed three patterns:**

| Pattern | Evidence | Lesson |
| --- | --- | --- |
| Correct answer flagged as hallucination | 2a: LLM may say "No, not after 30 days" — correct, but flagged | Heuristic evaluators have false positives |
| Direct quote = perfect faithfulness | 2b: LLM quoted "14 business days" directly → high faithfulness | Faithfulness rewards sticking to source text |
| Refusal beats risky correctness | 2c may score higher than 2a | "I don't know" is the safest answer for evaluation |
| Vague question = retrieval problem | 2c: retrieval dropped significantly | Ambiguity hurts retrieval, not generation |

**✅ Skill unlocked:** You can detect hallucination, understand the faithfulness score, and explain why it gets 40% weight. You can tell the difference between a retrieval problem (wrong chunks) and a generation problem (hallucinated from good chunks). You can also identify when the *evaluator itself* is wrong — a critical skill for AI engineering.

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A finance company's AI assistant must not provide inappropriate financial advice or make claims not grounded in approved guidance. How should they implement grounding checks?"**
>
> You measured faithfulness in this lab — you saw faithfulness drop when the LLM answered without
> grounded context (Experiment 2a), and faithfulness approach 1.0 when it stuck to the source (2b).
> For a finance company, you'd set a **high grounding score threshold** in Bedrock Guardrails.
> "High" means strict — only answers well-supported by the source documents pass through.
> A low threshold would let ungrounded claims through, which is exactly what you saw fail in 2a.
>
> **Q: "A GenAI assistant must generate responses in a consistent format (summary, risk classification, flagged terms). How?"**
>
> You saw in Lab 2 that the LLM's output format varies by question (short vs long, structured vs rambling).
> The answer is **prompt templates** — define the output format in the system prompt. Amazon Bedrock
> Prompt Management lets you centrally manage these templates. Your Lab 2 experience: the trick question
> (2a) got a long narrative answer; the direct question (2b) got a short factual answer. A template
> would enforce consistent structure regardless of the question.
>
> **Q: "How do you detect hallucination in production?"**
>
> You ran 3 experiments and saw `has_hallucination` flagged in 2a (possible false positive — LLM quoted the question)
> and clean results in 2b and 2c. You know heuristic evaluators have false positives.
> In production, you'd use LLM-as-judge (a second model evaluating the first) or Bedrock Guardrails
> grounding checks — both understand context better than keyword overlap.

---

## Phase 1 Labs — Skills Checklist

After completing Labs 1 and 2, check off:

| # | Skill | Lab | Can you explain it? |
|---|---|---|---|
| 1 | Retrieval quality measurement | Lab 1 | [ ] Yes |
| 2 | Retrieval-faithfulness trade-off | Lab 1 | [ ] Yes |
| 3 | top_k tuning and its impact | Lab 1 | [ ] Yes |
| 4 | Hallucination detection | Lab 2 | [ ] Yes |
| 5 | Faithfulness scoring and weight | Lab 2 | [ ] Yes |
| 6 | Diagnosing retrieval vs generation problems | Lab 2 | [ ] Yes |

---

> **Next:** [Phase 2 Labs](hands-on-labs-phase-2.md) — Business metrics, guardrails, and observability.
