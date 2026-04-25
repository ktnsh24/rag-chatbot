# Hands-On Labs — Phase 3: Production AI Engineering Skills

---

## Table of Contents

- [🫏 The Donkey Analogy — Understanding Phase 3 Concepts](#-the-donkey-analogy--understanding-phase-3-concepts)
- [Lab 6: Data Flywheel — "How does the system get smarter over time?"](#lab-6-data-flywheel--how-does-the-system-get-smarter-over-time)
  - [The data flywheel concept](#the-data-flywheel-concept)
  - [Experiment 6a — Find a question that gets a bad score](#experiment-6a--find-a-question-that-gets-a-bad-score)
  - [Experiment 6b — Fix the issue (add the missing document)](#experiment-6b--fix-the-issue-add-the-missing-document)
  - [Experiment 6c — Re-evaluate (did the flywheel turn?)](#experiment-6c--re-evaluate-did-the-flywheel-turn)
  - [Experiment 6d — Lock it in (add to golden dataset)](#experiment-6d--lock-it-in-add-to-golden-dataset)
  - [What you learned](#what-you-learned)
- [Lab 7: Reinforcement from Human Feedback (Conceptual)](#lab-7-reinforcement-from-human-feedback-conceptual)
  - [The concept](#the-concept)
  - [Think about this: Design a feedback system](#think-about-this-design-a-feedback-system)
  - [What you learned](#what-you-learned-1)
- [Lab 8: Infrastructure Scaling (Your DE Superpower)](#lab-8-infrastructure-scaling-your-de-superpower)
  - [Why this is YOUR advantage](#why-this-is-your-advantage)
  - [Experiment 8a — Map your DE skills to AI scaling](#experiment-8a--map-your-de-skills-to-ai-scaling)
  - [Experiment 8b — Design for 10,000 users](#experiment-8b--design-for-10000-users)
  - [What you learned](#what-you-learned-2)
- [Phase 3 Labs — Skills Checklist](#phase-3-labs--skills-checklist)
- [All Labs Complete — Full Skills Summary](#all-labs-complete--full-skills-summary)

---

## 🫏 The Donkey Analogy — Understanding Phase 3 Concepts

Phase 1 measured the donkey. Phase 2 asked if it's useful and safe. Phase 3 is about
**making the donkey get better over time** — and preparing for when the whole
village starts using it.

| Concept | Donkey version | What it really means | How it's calculated | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **data flywheel** | A customer asks for "remote work policy" but the donkey has no such package on the shelf. It delivers the wrong thing. You **notice the failure**, go buy the right package, put it on the shelf, and next time the donkey delivers it perfectly. Each fix makes the system smarter. Repeat forever. | Detect bad answer → diagnose root cause → fix (add document, tune prompt) → verify with evaluation → lock with golden dataset → repeat. | Not a formula — it's a process loop. Detect (overall < 0.70) → diagnose (which sub-score failed?) → fix (add doc, tune prompt, adjust top_k) → evaluate (re-run same query) → lock (add to golden dataset). Each cycle = one flywheel turn. | Delivery note 📋 |
| **before/after scores** | Before you added the remote work policy package: overall = 0.46 (❌ FAIL). After adding it: overall = 0.87 (✅ PASS). That delta IS the flywheel turning. If the score didn't improve — your fix didn't work. | Run the same evaluation before and after a change. The score delta proves your fix worked (or didn't). | `delta = score_after - score_before`. Positive = improvement. E.g. before: overall=0.46, after: overall=0.87 → **delta = +0.41**. Run the exact same question with the exact same evaluator to get a fair comparison. | Report card 📝 |
| **golden dataset** | A **checklist of test deliveries** you run every morning. "Deliver refund policy — did it arrive? ✅. Deliver remote work policy — did it arrive? ✅." If tomorrow a delivery fails that passed yesterday — something broke overnight. | A curated set of question/expected-answer pairs that you run as regression tests. Like `dbt test` for your AI system. | `pass_count / total_cases × 100`. Run all golden questions through the pipeline, evaluate each. E.g. 18 of 20 pass → **90% pass rate**. If a case that passed yesterday now fails → regression detected. | Feed bill 🌾 |
| **RLHF (human feedback)** | After each delivery, the customer gives a **thumbs up 👍 or thumbs down 👎**. Over time, you learn: the donkey is great at refund questions but terrible at HR questions. You focus training on HR. | Reinforcement Learning from Human Feedback — collecting user ratings to identify weak spots and prioritise improvements. | `positive / (positive + negative) × 100` per category. E.g. refund questions: 45👍 / 50 total = **90%** satisfaction. HR questions: 3👍 / 20 total = **15%**. Focus improvement effort on lowest-rated categories. | Feed bill 🌾 |
| **scaling** | One donkey serves 10 villagers. What about 10,000? You need: **more donkeys** (horizontal scaling), **faster routes** (caching), **a traffic cop** (load balancer), and **a warehouse manager** (queue system). This is where your DE skills shine — ECS, SQS, auto-scaling are the same patterns. | Horizontal scaling (ECS tasks), caching (reduce redundant LLM calls), load balancing, queue-based processing — all standard DE infrastructure. | Throughput = `successful_requests / time_seconds`. Capacity test: increase concurrent users until p95 latency exceeds SLA. E.g. 50 concurrent → p95=2s ✅. 200 concurrent → p95=12s ❌. Scale trigger found at ~100 concurrent. | The donkey 🐴 |

**The Phase 3 insight:** Building a chatbot is a weekend project. **Continuously
improving** a chatbot — detect regression, fix it, lock the fix, scale it — that's
what makes you an AI engineer. The donkey doesn't get smarter on its own. You turn
the flywheel.

- 🫏 **Donkey:** A practice delivery run — the donkey completes a structured exercise to build muscle memory before real production routes.

---

## Lab 6: Data Flywheel — "How does the system get smarter over time?"

**Skill:** Continuous improvement loop, feedback collection, golden dataset growth

**Time:** 20 minutes

**What you'll understand after:** Why AI systems must improve continuously (not just deploy-and-forget), and how the golden dataset grows from real usage.

**Maps to:** Phase 3, items 14–15 (`src/evaluation/evaluator.py` + `golden_dataset.py`)

### The data flywheel concept

```
Users ask questions
  → AI answers (some good, some bad)
    → You collect feedback (scores, thumbs-up/down)
      → Bad answers become new golden dataset cases
        → You fix the issue (better chunking, better prompt, more docs)
          → Re-evaluate: scores improve
            → Deploy improved version
              → Users ask questions (loop continues)
```

DE parallel: This is exactly your CI/CD feedback loop — test fails → fix → deploy → monitor. But for AI, the "tests" grow from real user interactions.

### Experiment 6a — Find a question that gets a bad score

In **Swagger UI** → `POST /api/evaluate`, enter:

```json
{
  "question": "What is your remote work policy?"
}
```

📝 **Record the failing scores:**

| Score | Value | 🫏 Donkey |
|---|---| --- |
| retrieval | ___ | 🫏 On the route |
| faithfulness | ___ | backpack match 🫏 |
| overall | ___ | 🫏 On the route |
| passed | ___ | 🫏 On the route |

> **What to expect (local):** retrieval 0.40–0.60 (found something but not about remote work), faithfulness near 0.0 (answer not grounded), overall below 0.5 (FAIL). This is the correct failure — the document doesn't exist yet.

> ### 📊 Why These Scores Are Exactly What We Expected
>
> **Retrieval** — ChromaDB returned *something*, but nothing about remote work.
> The chunks came from `test-policy.txt` (refund policy). A low retrieval score means
> "the best chunks I found are barely related."
>
> **Faithfulness near 0.0** — This is the key signal. The LLM tried to answer using
> refund-policy chunks as context, and the evaluator found **zero overlap** between the
> answer and the source material. Every sentence was flagged as "not grounded."
>
> **Overall below 0.5** — Below the 0.7 threshold → **FAIL**. This question is a
> perfect flywheel candidate: real users would ask it, and the system can't answer it.
>
> DE parallel: This is like a data quality check failing — missing data in the source
> table causes downstream reports to return nulls. The fix isn't the query — it's the data.

This is a **flywheel signal**: users are asking about something your documents don't cover.

### Experiment 6b — Fix the issue (add the missing document)

Create `remote-work-policy.txt`:

```text
REMOTE WORK POLICY

All employees may work remotely up to 3 days per week.
Remote work must be approved by your direct manager.
Equipment for home office is provided by the company up to 500 euros.
```

Upload it via **Swagger UI** → `POST /api/documents/upload`:

1. Click **"Try it out"**
2. Click **"Choose File"** and select `remote-work-policy.txt`
3. Click **"Execute"**

### Experiment 6c — Re-evaluate (did the flywheel turn?)

In **Swagger UI** → `POST /api/evaluate`, enter the same question again:

```json
{
  "question": "What is your remote work policy?"
}
```

📝 **Compare before and after:**

| Score | Before (6a) | After (6c) | Improved? | 🫏 Donkey |
|---|---|---|---| --- |
| retrieval | ___ | ___ | ___ | 🫏 On the route |
| faithfulness | ___ | ___ | ___ | backpack match 🫏 |
| overall | ___ | ___ | ___ | 🫏 On the route |
| passed | ___ | ___ | ___ | 🫏 On the route |

> **What to expect (local):** retrieval should improve modestly, faithfulness should jump dramatically (from near 0 to near 1.0), overall should go from FAIL to PASS. The biggest change is faithfulness — the LLM now has real source material to cite.

> ### 📊 The Flywheel Turned — Here's What Each Score Change Tells You
>
> **Retrieval: modest improvement** — ChromaDB now finds
> the remote-work-policy chunk, but the score only went up slightly because the
> embedding similarity between the question and the new document isn't dramatically
> higher than the old "best match" from the refund policy. The *ranking* changed
> (remote work policy is now #1), even though the *score* only nudged up.
>
> DE parallel: Adding a row to a lookup table doesn't change the join algorithm —
> it just means the join now *finds a match* where it returned NULL before.
>
> **Faithfulness: near 0 → near 1.0** — The biggest jump possible. Before,
> the LLM fabricated an answer with no grounding. After, every sentence in the answer
> maps directly to the uploaded document. This is the difference between "hallucinating
> because there's nothing to cite" and "answering accurately from a real source."
>
> **Overall: from FAIL to solid PASS** — The weighted
> combination of retrieval + faithfulness produced a significant improvement. In
> production, this is the metric you'd track on a dashboard: "How many questions
> moved from FAIL to PASS this week?"
>
> **Answer preview:** The LLM should now cite the remote work policy directly —
> "3 days per week", "approved by manager", "500 euros equipment" — straight from the document.

Retrieval should jump from near-0 to 0.7+. Faithfulness should be high. Overall should pass. **You just completed one rotation of the data flywheel.**

### Experiment 6d — Lock it in (add to golden dataset)

Open `src/evaluation/golden_dataset.py` and add this case at the end of the `GOLDEN_DATASET` list:

```python
{
    "id": "remote_work",
    "category": "hr",
    "question": "What is the remote work policy?",
    "expected_keywords": ["remote", "3", "days", "week", "manager"],
    "expected_not_in_answer": [],
    "context_chunks": [
        ("All employees may work remotely up to 3 days per week.", 0.92),
        ("Remote work must be approved by your direct manager.", 0.88),
    ],
    "min_retrieval_score": 0.7,
    "min_faithfulness": 0.8,
},
```

Now run the suite to verify:

In **Swagger UI** → `POST /api/evaluate/suite`, send an empty body:

```json
{}
```

📝 **Record:** total_cases=**___**, passed=**___**, failed=**___** (pass rate: **___%**, avg overall: **___**)

> ### 📊 Golden Dataset Suite — Individual Results
>
> | Question | Overall | Result |
> |---|---|---|
> | What is the refund policy? | ___ | ___ |
> | Can I get a refund on digital products? | ___ | ___ |
> | Who pays for return shipping? | ___ | ___ |
> | What is the meaning of life? | ___ | ___ |
> | How long? | ___ | ___ |
>
> **Suite latency:** ___ms — local Ollama processing evaluations sequentially.
>
> **The intentional failure:** "What is the meaning of life?" is a
> **guardrail question** — it's designed to fail because your knowledge base doesn't
> contain philosophy. This is expected and correct: the golden dataset *should* contain
> questions that fail, to prove your system doesn't hallucinate answers for off-topic
> questions.
>
> **Pass rate interpretation** — In production, you'd set an alerting threshold (e.g., "alert
> if pass rate drops below 75%"). The golden dataset runs on every deploy, just like
> unit tests. A regression means something broke.

**You should see 6 cases now (5 original + 1 new). The golden dataset grew from real usage. This IS the data flywheel.**

### What you learned

The data flywheel is a continuous improvement loop:

1. **Detect** — find questions that get low scores (production monitoring catches these)
2. **Fix** — add documents, improve prompts, tune chunking
3. **Evaluate** — re-run evaluation to confirm improvement
4. **Lock** — add the question to the golden dataset so it never regresses
5. **Repeat** — in production, this is automated (log bad answers → review weekly → fix → redeploy)

**✅ Skill unlocked:** You understand the data flywheel pattern, you've executed it manually, and you can explain how it works in production (automated feedback collection replaces your manual steps).

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A company deployed a GenAI chatbot but quality is declining over time. How should they implement continuous improvement?"**
>
> You executed the flywheel in Lab 6: found a failing question (6a: "remote work" → overall FAIL),
> uploaded the missing document (6b), re-evaluated (6c: overall PASS, significant improvement), and
> locked it in the golden dataset (6d). In production, this is automated: monitor → detect failures
> → add documents → re-evaluate → redeploy. The golden dataset runs on every deploy like unit tests.
>
> **Q: "A company needs to evaluate prompt variants weekly and compare performance. How?"**
>
> Lab 6d showed you the golden dataset suite: 5 questions evaluated, pass rate calculated. For
> comparing two prompts, you'd run the suite against each variant and compare metrics side by side.
> Bedrock model evaluation jobs do this natively — run the same dataset against different prompts/models
> and get comparison metrics.
>
> **Q: "How do you build a golden dataset for evaluating a RAG system?"**
>
> You built one in Lab 6d — each entry has: question, expected keywords, expected context chunks,
> minimum retrieval score, minimum faithfulness. The dataset grows from real failures (the flywheel).
> You started with 5 cases and grew to 6 by adding the "remote work" question that failed.

> ### 📊 Lab 6 Results Summary
>
> | Experiment | What Happened | Key Metric |
> |---|---|---|
> | 6a — Find failing question | "What is your remote work policy?" → FAIL | overall=___, faithfulness=___ |
> | 6b — Upload missing document | `remote-work-policy.txt` uploaded | ✅ Document indexed |
> | 6c — Re-evaluate after fix | Same question → PASS | overall=___ (improvement) 🎉 |
> | 6d — Golden dataset suite | ___ cases evaluated | ___/___ passed (___%), avg=___ |
>
> **The flywheel in numbers:** One document upload caused a dramatic improvement in overall
> score and took faithfulness from near 0 to near 1.0. This is the production pattern:
> monitor → detect → fix → verify → lock → repeat.
>
> **Update (I32):** The golden dataset was later expanded from 5 to 25 cases across 7
> categories (policy, logistics, contact, product, multi_turn, edge_case, pii) — see
> [Phase 5 Labs](hands-on-labs-phase-5.md) → Lab 16 for the full regression testing workflow.---

- 🫏 **Donkey:** A practice delivery run — the donkey completes a structured exercise to build muscle memory before real production routes.

## Lab 7: Reinforcement from Human Feedback (Conceptual)

**Skill:** Understanding RLHF loops, user feedback integration

**Time:** 15 minutes (thinking exercise — no code yet)

**What you'll understand after:** How user feedback improves AI systems without retraining the model.

**Maps to:** The feedback collection piece that powers the data flywheel in production.

### The concept

RLHF in production RAG is simpler than it sounds. It's NOT retraining the LLM. It's:

```
User asks question → AI answers → User gives 👍 or 👎
                                         │
                        ┌────────────────┤
                        ▼                ▼
                    👍 Good:          👎 Bad:
                    Log as example    → WHY was it bad?
                    of working well     → Retrieval (wrong chunks)?
                                        → Hallucination (made up facts)?
                                        → Off-topic (didn't answer question)?
                                        → Incomplete (missed key info)?
                                      → Add to golden dataset as failing case
                                      → Fix the root cause
                                      → Re-evaluate
```

### Think about this: Design a feedback system

📝 **Answer these questions (write your design):**

**Q1: Where would you add a thumbs-up/down button?**

Your design: ___

<details>
<summary>Click to reveal example design</summary>

1. The `/api/chat` response includes a `feedback_url` field
2. The UI shows 👍 👎 buttons after each answer
3. Clicking sends `POST /api/feedback` with `{session_id, rating, comment}`
4. Feedback is stored in DynamoDB (or a local JSON file for dev)
5. Weekly: review 👎 answers → add worst ones to golden dataset → fix → redeploy

</details>

**Q2: What data would you store for each feedback event?**

Your design: ___

<details>
<summary>Click to reveal example schema</summary>

```python
{
    "session_id": "uuid",
    "question": "What is the remote work policy?",
    "answer_preview": "Based on the documents...",
    "rating": "thumbs_down",
    "comment": "Answer was about refund policy, not remote work",  # optional
    "scores": {
        "retrieval": 0.35,
        "faithfulness": 0.82,
        "overall": 0.55
    },
    "timestamp": "2026-04-13T10:30:00Z",
    "root_cause": null  # filled in during weekly review
}
```

</details>

**Q3: How does this connect to the data flywheel (Lab 6)?**

Your design: ___

<details>
<summary>Click to reveal the connection</summary>

The feedback system is the **automated version** of what you did manually in Lab 6:

| Lab 6 (manual) | Production (automated) | 🫏 Donkey |
|---|---| --- |
| You noticed a question failed | Monitoring alerts on low scores | Tachograph 📊 |
| You uploaded a missing document | Content team adds documents | 🫏 On the route |
| You re-evaluated | CI/CD re-runs evaluation suite | Report card 📝 |
| You added to golden dataset | Script auto-adds 👎 cases to golden dataset | Test delivery 🧪 |

The human feedback replaces your manual observation. The flywheel spins automatically.

</details>

### What you learned

This is what companies mean by "reinforcement learning loops" for RAG systems. You're not training the model — you're training the **system** (better docs, better prompts, better chunking) based on human feedback.

**✅ Skill unlocked:** You can explain RLHF in RAG context, propose a feedback collection design, and describe how it feeds the data flywheel.

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A company needs to implement A/B testing across multiple foundation models. How should they collect and compare performance data?"**
>
> Lab 7 taught you feedback collection design: session_id, question, answer, rating, scores, timestamp.
> For A/B testing, you'd add a `model_variant` field to each feedback event. The weekly review
> compares metrics per variant: "Prompt A got 85% thumbs-up, Prompt B got 72%." This maps directly
> to Bedrock Flows (traffic splitting) + CloudWatch (metric comparison).
>
> **Q: "How should a company handle user feedback to improve GenAI quality without retraining the model?"**
>
> You designed this in Lab 7: collect 👍/👎 → review 👎 answers weekly → identify root cause
> (retrieval problem? hallucination? content gap?) → fix the system (add docs, tune prompts,
> adjust chunking). No model retraining needed. This is the RAG advantage over fine-tuning.

- 🫏 **Donkey:** A practice delivery run — the donkey completes a structured exercise to build muscle memory before real production routes.

---

## Lab 8: Infrastructure Scaling (Your DE Superpower)

**Skill:** Scaling AI systems for production load

**Time:** 15 minutes (thinking exercise — maps to your existing DE skills)

**What you'll understand after:** How your existing Terraform/ECS/SQS skills directly apply to AI infrastructure, and what the AI-specific additions are.

**Maps to:** Your daily DE work (proxy APIs, batch jobs, shared infra) applied to AI workloads.

### Why this is YOUR advantage

**Most AI engineers can build a chatbot but can't deploy it at scale.** They struggle with exactly the production infrastructure you've been building for years — ECS, Terraform, IAM, DynamoDB, Kinesis, API Gateway.

### Experiment 8a — Map your DE skills to AI scaling

📝 **Fill in the "Your DE skill" column from your own experience:**

| Scaling challenge | AI system need | Your DE skill that solves it | 🫏 Donkey |
|---|---|---| --- |
| 1000 concurrent users | Horizontal scaling | ___ | 🫏 On the route |
| LLM calls are slow (2-5s) | Async processing | ___ | The donkey 🐴 |
| Repeated questions | Caching | ___ | 🫏 On the route |
| Embedding 10,000 docs | Batch processing | ___ | GPS warehouse 🗺️ |
| Vector store overload | Read replicas | ___ | GPS warehouse 🗺️ |
| Cost explosion | Rate limiting | ___ | Feed bill 🌾 |
| Multi-region | Low latency globally | ___ | 🫏 On the route |

<details>
<summary>Click to reveal the mapping</summary>

| Scaling challenge | AI system need | Your DE skill that solves it | 🫏 Donkey |
|---|---|---| --- |
| 1000 concurrent users | Horizontal scaling | ECS auto-scaling (you configure this daily) | 🫏 On the route |
| LLM calls are slow (2-5s) | Async processing | SQS queues + Lambda workers (you built this in proxy) | The donkey 🐴 |
| Repeated questions | Caching | DynamoDB/ElastiCache — cache answer by question hash | AWS depot 🏭 |
| Embedding 10,000 docs | Batch processing | Kinesis/SQS batching (you built Kinesis in proxy) | GPS warehouse 🗺️ |
| Vector store overload | Read replicas | OpenSearch replicas (same as RDS read replicas) | AWS search hub 🔍 |
| Cost explosion | Rate limiting | API Gateway throttling (you configured this) | Feed bill 🌾 |
| Multi-region | Low latency globally | CloudFront + regional deployments (standard infra) | Robot hand 🤖 |

</details>

### Experiment 8b — Design for 10,000 users

Think about this: your company wants to deploy this chatbot for 10,000 customer support agents.

📝 **Answer these architecture questions:**

**Q1: What would you change in ECS?**
Your answer: ___

**Q2: Where would you add a queue?**
Your answer: ___

**Q3: What would you cache?**
Your answer: ___

**Q4: How would you monitor cost?**
Your answer: ___

<details>
<summary>Click to reveal example architecture</summary>

1. **ECS:** min_tasks=5, max_tasks=50, CPU scaling at 60%, memory 2GB per task (LLM calls are I/O bound, not CPU bound — so scale on request count, not CPU)
2. **Queue:** SQS between API Gateway and the chat endpoint — decouple user request from LLM call. Return a job_id immediately, poll for result. This prevents timeouts on slow LLM responses.
3. **Cache:** DynamoDB or ElastiCache. Key = hash(question + top_k). TTL = 1 hour for FAQ-type questions, 0 for unique questions. Cache embeddings separately (they don't change unless the document changes).
4. **Cost:** CloudWatch alarm on `token_usage_total` metric per hour. Budget alert at 80% of monthly limit. Dashboard showing cost per question (token cost / request count).

</details>

### What you learned

AI infrastructure scaling is **80% your existing skills + 20% AI-specific concerns**. The AI-specific parts are:

- **Caching embeddings** (vectors don't change unless documents change)
- **Managing LLM token budgets** (cost scales with usage, not with infrastructure)
- **Async LLM calls** (2-5 second response times need decoupling)
- **Vector store sizing** (dimensions × document count = storage requirement)

Everything else — ECS, SQS, DynamoDB, API Gateway, CloudWatch, Terraform — you already know.

**✅ Skill unlocked:** You can confidently discuss AI infrastructure scaling because it maps directly to your daily work. In an interview, you can say: "I've scaled ECS services handling X requests/day, and AI workloads need the same patterns plus embedding caching and token budget management."

> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A React app using AppSync + Lambda (RequestResponse) has timeouts on complex GenAI questions. How to fix the performance?"**
>
> Lab 8 taught you that LLM calls are slow (2-5s cloud, 40s+ local). The problem is synchronous
> invocation — Lambda waits for the full LLM response. The fix is **streaming** — return tokens
> as they're generated, so the user sees the answer building in real time. The answer uses
> AWS Amplify AI Kit for streaming GraphQL responses. NOT increasing Lambda timeout (that's
> a band-aid), NOT SQS polling (adds complexity and latency).
>
> **Q: "An ecommerce system needs to switch between FMs without code deployment, with rules that change hourly. How?"**
>
> Lab 8's architecture exercise asked you to design for 10,000 users with dynamic routing.
> The answer uses AWS AppConfig (propagates changes instantly to all Lambda instances) +
> Lambda business logic (evaluates user tier, transaction value, regulatory zone) + single
> API Gateway endpoint (no per-model routing). NOT Lambda env vars (require redeploy),
> NOT API Gateway stage variables (don't support complex business rules).
>
> **Q: "A company needs to choose between OpenSearch Serverless, Aurora pgvector, S3 Vectors, and Neptune for their vector store. They have 10M embeddings and need metadata filtering with minimal operational overhead."**
>
> Lab 8 mapped your DE skills to AI infrastructure. You know DynamoDB (from I22) is great for
> small scale (~$0/month), but 10M embeddings need a proper vector index. OpenSearch Serverless
> gives you: managed k-NN search, metadata filtering (publication date, agency, type), multi-language
> support, and integration with Bedrock Knowledge Bases. Aurora pgvector requires you to manage
> the database. S3 Vectors doesn't support filterable metadata. Neptune is for graph data, not
> vector search.

- 🫏 **Donkey:** Blueprints for building the stable — run one command and the whole building appears, fences and all.

---

## Phase 3 Labs — Skills Checklist

After completing Labs 6, 7, and 8, check off:

| # | Skill | Lab | Can you explain it? | 🫏 Donkey |
|---|---|---|---| --- |
| 1 | Data flywheel (detect → fix → evaluate → lock → repeat) | Lab 6 | [ ] Yes | Report card 📝 |
| 2 | Golden dataset growth from real usage | Lab 6 | [ ] Yes | Test delivery 🧪 |
| 3 | RLHF in RAG context (user feedback loops) | Lab 7 | [ ] Yes | backpack check 🫏 |
| 4 | Feedback system design | Lab 7 | [ ] Yes | Feed bill 🌾 |
| 5 | Connection between feedback and data flywheel | Lab 7 | [ ] Yes | Feed bill 🌾 |
| 6 | Infrastructure scaling for AI (your DE superpower) | Lab 8 | [ ] Yes | Stable blueprint 🏗️ |
| 7 | AI-specific scaling concerns (embeddings, tokens, async LLM) | Lab 8 | [ ] Yes | The donkey 🐴 |

- 🫏 **Donkey:** A practice delivery run — the donkey completes a structured exercise to build muscle memory before real production routes.

---

## All Labs Complete — Full Skills Summary

| # | Skill | Phase | Lab | 🫏 Donkey |
|---|---|---|---| --- |
| 1 | Retrieval quality measurement | Phase 1 | Lab 1 | backpack fetch 🎒 |
| 2 | Retrieval-faithfulness trade-off | Phase 1 | Lab 1 | backpack match 🫏 |
| 3 | top_k tuning and its impact | Phase 1 | Lab 1 | 🫏 On the route |
| 4 | Hallucination detection | Phase 1 | Lab 2 | Memory drift ⚠️ |
| 5 | Faithfulness scoring and weight | Phase 1 | Lab 2 | Report card 📝 |
| 6 | Diagnosing retrieval vs generation problems | Phase 1 | Lab 2 | 🫏 On the route |
| 7 | Business-aligned metrics | Phase 2 | Lab 3 | Tachograph 📊 |
| 8 | Translating AI metrics to business language | Phase 2 | Lab 3 | Tachograph 📊 |
| 9 | Guardrails design (4 layers) | Phase 2 | Lab 4 | Gate rule 🚧 |
| 10 | Prompt injection awareness | Phase 2 | Lab 4 | Delivery note 📋 |
| 11 | AI observability | Phase 2 | Lab 5 | 🫏 On the route |
| 12 | Dashboard and alert design for AI | Phase 2 | Lab 5 | 🫏 On the route |
| 13 | Data flywheel | Phase 3 | Lab 6 | 🫏 On the route |
| 14 | Golden dataset growth from real usage | Phase 3 | Lab 6 | Test delivery 🧪 |
| 15 | RLHF in RAG context | Phase 3 | Lab 7 | backpack check 🫏 |
| 16 | Feedback system design | Phase 3 | Lab 7 | Feed bill 🌾 |
| 17 | Infrastructure scaling for AI | Phase 3 | Lab 8 | Stable blueprint 🏗️ |
| 18 | AI-specific scaling concerns | Phase 3 | Lab 8 | 🫏 On the route |

**Additional skills not covered in the rag-chatbot but important to know about:**

| # | Skill | What it is | Covered in future projects? | Where to learn it | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| 19 | **A/B testing for AI** | Deploy two prompt versions, measure which performs better | ✅ Yes — when deploying to AWS/Azure, you'll set up traffic splitting with API Gateway / Azure Front Door | Same as A/B testing in web — split traffic, compare metrics | Delivery note 📋 |
| 20 | **Model versioning** | Track which model version produced which answers | ✅ Yes — V2 of rag-chatbot will add MLflow integration for experiment tracking | MLflow, Weights & Biases, or simple git tags | backpack check 🫏 |
| 21 | **Embedding drift detection** | New documents change the vector space — old embeddings may become stale | ✅ Partially — Lab 5's retrieval monitoring concept extends directly to drift alerts. Full implementation in V2 with scheduled re-evaluation | Monitor average retrieval scores over time (Lab 5 concept) | backpack fetch 🎒 |
| 22 | **Cost optimisation** | Prompt compression, caching, model routing (cheap model for easy questions, expensive for hard) | ✅ Yes — when deploying to AWS Bedrock or Azure OpenAI, cost tracking becomes real (see [Cost Estimation](hands-on-labs-phase-1.md#cost-estimation--local-vs-cloud)) | Extend `src/rag/chain.py` with model routing logic | The donkey 🐴 |
| 23 | **Multi-modal RAG** | Images, tables, PDFs with charts — not just text | ⬜ Future project — requires a separate repo with vision models (GPT-4o, Claude 3.5 Sonnet) | Not in current rag-chatbot scope | The donkey 🐴 |
| 24 | **Compliance & audit logging** | Log every AI decision for regulatory compliance | ✅ Partially — the logging middleware already captures request/response. Full audit trail (immutable, tamper-proof) is a V2 feature | Extend `src/api/middleware/` to log full request/response | Stable door 🚪 |

> ### 📋 Skills Coverage Summary
>
> **Covered in these labs (rag-chatbot V1):** Skills 1–18 are fully covered across
> Phases 1–3 with hands-on experiments and real results.
>
> **Covered when you deploy to cloud:** Skills 19 (A/B testing), 20 (model versioning),
> 22 (cost optimisation) become real when you switch from local Ollama to AWS Bedrock
> or Azure OpenAI. The architecture is already designed for this — see
> `src/config.py` → `cloud_provider` setting.
>
> **Partially covered, extended in V2:** Skills 21 (drift detection) and 24 (compliance
> logging) have foundations in the current codebase (retrieval monitoring, request logging)
> but full implementation requires scheduled jobs and immutable log storage.
>
> **Not yet covered:** Skill 23 (multi-modal RAG) requires a different architecture
> and vision-capable models. This would be a separate project/repo.

- 🫏 **Donkey:** A practice delivery run — the donkey completes a structured exercise to build muscle memory before real production routes.

---

> **Previous:** [Phase 2 Labs](hands-on-labs-phase-2.md) — Business metrics, guardrails, observability.
>
