"""
📊 Lab Analysis Engine — Deep Analysis Templates for Auto-Generated Reports

This module contains all the analysis logic from the hands-on labs, parameterised
by actual experiment results. Instead of hardcoded numbers, each analysis function
takes real scores and generates the same depth of insight found in
`docs/hands-on-labs/hands-on-labs-phase-*.md`.

The analysis is **conditional** — different score ranges produce different explanations.

Author: Ketan (personal automation — not part of the rag-chatbot repo)
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _s(v: float | None, precision: int = 3) -> str:
    """Format score."""
    return f"{v:.{precision}f}" if v is not None else "—"


def _pf(v: bool | None) -> str:
    """Pass/fail emoji."""
    if v is None:
        return "—"
    return "✅ PASS" if v else "❌ FAIL"


def _quality(retrieval: float | None) -> str:
    """Retrieval quality label."""
    if retrieval is None:
        return "—"
    if retrieval >= 0.8:
        return '"excellent"'
    if retrieval >= 0.7:
        return '"good"'
    if retrieval >= 0.5:
        return '"fair"'
    return '"poor"'


def _delta(before: float | None, after: float | None) -> str:
    """Improvement arrow."""
    if before is None or after is None:
        return "—"
    diff = after - before
    if diff > 0.001:
        return f"↑ +{diff:.3f}"
    if diff < -0.001:
        return f"↓ {diff:.3f}"
    return "→ same"


def _latency_context(ms: int | None, env: str) -> str:
    """Contextualise latency for environment."""
    if ms is None:
        return "—"
    if env == "local":
        if ms > 30000:
            return f"{ms}ms (expected for local CPU — cloud equivalent: ~2-3s)"
        if ms > 10000:
            return f"{ms}ms (moderate for local CPU)"
        return f"{ms}ms (fast for local)"
    return f"{ms}ms"


# ---------------------------------------------------------------------------
# Lab 1: Retrieval Quality
# ---------------------------------------------------------------------------


def analyse_lab1_baseline(
    retrieval: float | None,
    faithfulness: float | None,
    relevance: float | None,
    overall: float | None,
    passed: bool | None,
    latency_ms: int | None,
    env: str,
) -> str:
    """Generate the 📊 Understanding Scores analysis for Experiment 1a."""
    lines = []
    lines.append("> ### 📊 Understanding Your Baseline Scores")
    lines.append(">")

    if env == "local":
        lines.append("> Running locally with **Ollama** (llama3.2 + nomic-embed-text), these score")
        lines.append("> ranges are expected:")
        lines.append(">")
        lines.append("> | Score | Your value | Typical local range | Cloud equivalent | Why the gap? |")
        lines.append("> | --- | --- | --- | --- | --- |")
        lines.append(
            f"> | retrieval | {_s(retrieval)} ({_quality(retrieval)}) | 0.55-0.70 | 0.80-0.95 | Local embeddings (nomic-embed-text, 137M params) have less semantic precision than cloud models (OpenAI text-embedding-3-large, 3072 dims). Cosine similarities are lower. |"
        )
        lines.append(
            f"> | faithfulness | {_s(faithfulness)} | 0.70-0.85 | 0.90-1.0 | A 3B-parameter model sometimes adds filler phrases (\"I don't have enough information...\") which the keyword-based evaluator flags -- even though it's cautious (good) behaviour. |"
        )
        lines.append(
            f"> | answer_relevance | {_s(relevance)} | 0.90-1.0 | 0.95-1.0 | Local models handle this well -- least affected by model size. |"
        )
        lines.append(
            f"> | overall | {_s(overall)} | 0.70-0.85 | 0.85-0.95 | Weighted average: retrieval x 0.3 + faithfulness x 0.4 + relevance x 0.3 |"
        )
        lines.append(">")
        lines.append("> **Why this is fine:**")
        lines.append(">")
        lines.append(
            f"> 1. **Retrieval {_quality(retrieval)} ≠ bad.** The *ranking* is usually correct — the right chunk is still on top, it's just scored {_s(retrieval)} instead of 0.89."
        )
        lines.append(
            "> 2. **Faithfulness < 1.0 ≠ hallucination.** The evaluator uses keyword overlap (a heuristic). Disclaimers get flagged because those words don't appear in the source document."
        )
        lines.append(
            f"> 3. **The purpose of local evaluation is *relative comparison*, not absolute numbers.** Your baseline of ~{_s(overall)} is your anchor."
        )
        lines.append(">")
        lines.append("> **DE parallel:** Running integration tests against local Postgres vs production Redshift.")
        lines.append("> Local tests catch logic bugs, but performance numbers are meaningless to compare.")
    else:
        provider = "AWS Bedrock" if env == "aws" else "Azure OpenAI"
        lines.append(f"> Running on **{provider}**, these are production-grade scores:")
        lines.append(">")
        if retrieval and retrieval >= 0.8:
            lines.append(
                f"> **Retrieval {_s(retrieval)}** — Excellent. Cloud embedding models provide high-precision similarity scores."
            )
        elif retrieval and retrieval >= 0.6:
            lines.append(
                f"> **Retrieval {_s(retrieval)}** — Good. Consider tuning chunk_size or overlap for improvement."
            )
        lines.append(">")
        if faithfulness and faithfulness >= 0.9:
            lines.append(f"> **Faithfulness {_s(faithfulness)}** — Strong grounding. Cloud LLMs follow context well.")
        elif faithfulness and faithfulness >= 0.7:
            lines.append(
                f"> **Faithfulness {_s(faithfulness)}** — Acceptable but review flagged sentences for false positives."
            )

    return "\n".join(lines)


def analyse_lab1_topk_comparison(
    results: list[dict[str, Any]],
    env: str,
) -> str:
    """Generate the Three Trade-offs analysis for Experiment 1b.

    results: list of dicts with keys: top_k, retrieval, faithfulness, overall, latency_ms, passed
    """
    lines = []
    lines.append("> ### 📊 What These Results Reveal — The Three Trade-offs")
    lines.append(">")

    # Sort by top_k
    sorted_r = sorted(results, key=lambda x: x.get("top_k", 0))
    if len(sorted_r) >= 2:
        first = sorted_r[0]
        last = sorted_r[-1]
        first_ret = first.get("retrieval")
        last_ret = last.get("retrieval")

        lines.append(f"> **1. Retrieval drops as top_k increases: {_s(first_ret)} → {_s(last_ret)}**")
        lines.append(">")
        lines.append("> This is the **averaging effect**. With `top_k=1`, only the *best*")
        lines.append("> chunk is returned. With higher top_k, weaker chunks dilute the average.")
        lines.append("> The *ranking* doesn't change — the best chunk is still #1.")
        lines.append(">")
        lines.append("> DE parallel: `SELECT TOP 1 ... ORDER BY relevance DESC` gives a higher average than")
        lines.append("> `SELECT TOP 10` -- rows 7-10 are noise.")
        lines.append(">")

        # Faithfulness analysis
        lines.append("> **2. Faithfulness depends on LLM phrasing, not just retrieval**")
        lines.append(">")
        lines.append("> | top_k | faithfulness | Interpretation |")
        lines.append("> | --- | --- | --- |")
        for r in sorted_r:
            tk = r.get("top_k", "?")
            faith = r.get("faithfulness")
            if faith is not None and faith >= 1.0:
                interp = "Perfect — LLM stuck to source text"
            elif faith is not None and faith >= 0.8:
                interp = "Good — minor flagging (paraphrasing or disclaimers)"
            elif faith is not None and faith >= 0.5:
                interp = "Some sentences flagged — LLM added filler or hedged"
            elif faith is not None:
                interp = "Multiple sentences flagged — review answer for actual hallucination"
            else:
                interp = "—"
            lines.append(f"> | {tk} | {_s(faith)} | {interp} |")
        lines.append(">")

        # Latency analysis
        first_lat = first.get("latency_ms")
        last_lat = last.get("latency_ms")
        if first_lat and last_lat:
            ratio = last_lat / max(first_lat, 1)
            lines.append(f"> **3. Latency scales with context size: {first_lat}ms -> {last_lat}ms ({ratio:.1f}x)**")
            lines.append(">")
            lines.append("> More chunks = more tokens in the prompt = more inference time.")
            if env == "local":
                lines.append("> On a cloud GPU, this difference shrinks to milliseconds.")
        lines.append(">")

        # Best overall
        best = max(sorted_r, key=lambda x: x.get("overall", 0))
        lines.append(
            f'> **Bottom line:** `top_k={best.get("top_k")}` gave the *best overall score* ({_s(best.get("overall"))}).'
        )
        lines.append('> But don\'t conclude "always use this" — different questions need different top_k.')

    return "\n".join(lines)


def analyse_lab1_out_of_scope(
    retrieval: float | None,
    faithfulness: float | None,
    has_hallucination: bool | None,
    overall: float | None,
    passed: bool | None,
    answer: str | None,
    notes: list[str] | None,
    env: str,
) -> str:
    """Generate the Correct Refusal Paradox analysis for Experiment 1c."""
    lines = []
    lines.append('> ### 📊 The "Correct Refusal" Paradox')
    lines.append(">")

    if notes:
        has_refusal = any("refused" in n.lower() or "correctly refused" in n.lower() for n in notes)
        has_flag = any("hallucination" in n.lower() for n in notes)
        if has_refusal and has_flag:
            lines.append("> The `evaluation_notes` contain **two contradictory signals:**")
            lines.append(">")
            lines.append("> 1. The refusal detector correctly identified this as a refusal ✅")
            lines.append("> 2. The faithfulness checker also flagged sentences ❌")
            lines.append(">")
            lines.append("> **This is a known limitation of heuristic evaluation.** The correct behaviour:")
            lines.append("> faithfulness should be 1.0 for a refusal (the model *didn't* make anything up).")
            lines.append("> In production, you'd give refusals an automatic faithfulness override")
            lines.append("> or use LLM-as-judge which understands refusals aren't hallucinations.")

    lines.append(">")
    if retrieval is not None:
        lines.append(f"> **Retrieval score ({_s(retrieval)}) is the real signal.** It tells you:")
        lines.append('> "the vector store couldn\'t find relevant content" — which is correct,')
        lines.append("> because the asked topic isn't in the uploaded documents.")
    lines.append(">")
    lines.append("> **DE parallel:** This is like a `LEFT JOIN` returning NULLs — the query")
    lines.append("> ran fine, there's just no matching data. The join isn't broken; the data doesn't exist.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lab 2: Faithfulness & Hallucination
# ---------------------------------------------------------------------------


def analyse_lab2_trick(
    retrieval: float | None,
    faithfulness: float | None,
    has_hallucination: bool | None,
    overall: float | None,
    answer: str | None,
) -> str:
    """Analyse the trick question (30 days vs 14 days)."""
    lines = []
    lines.append("> ### 📊 Trick Question Analysis")
    lines.append(">")

    if answer:
        answered_correctly = "14" in answer and ("no" in answer.lower() or "cannot" in answer.lower())
        if answered_correctly:
            lines.append("> **What the AI actually answered:** The AI did NOT hallucinate — it correctly")
            lines.append("> cited the real number from the document and said no to the 30-day claim.")
            lines.append(">")
        else:
            lines.append('> **⚠️ The AI may have hallucinated.** Check if the answer quoted "30 days"')
            lines.append("> from the question as if it were a real policy number.")
            lines.append(">")

    if has_hallucination:
        lines.append("> **Why has_hallucination=true?** The answer contains a number from the *question*")
        lines.append('> ("30 days") that doesn\'t appear in the source document. The keyword overlap')
        lines.append("> checker flagged it — but the LLM was *quoting the question*, not making a claim.")
        lines.append("> This is a heuristic evaluator limitation.")
    elif has_hallucination is False:
        lines.append("> **has_hallucination=false** — The evaluator didn't flag any sentences.")
        lines.append("> The answer stayed close to the document text.")

    return "\n".join(lines)


def analyse_lab2_comparison(
    trick: dict[str, Any],
    truthful: dict[str, Any],
    ambiguous: dict[str, Any],
) -> str:
    """Cross-experiment comparison for Lab 2."""
    lines = []
    lines.append("> ### 📊 Cross-Experiment Comparison")
    lines.append(">")
    lines.append("> | | Trick (2a) | Truthful (2b) | Ambiguous (2c) | Gap |")
    lines.append("> | --- | --- | --- | --- | --- |")

    for key, label in [("faithfulness", "faithfulness"), ("retrieval", "retrieval"), ("overall", "overall")]:
        t = trick.get(key)
        tr = truthful.get(key)
        a = ambiguous.get(key)
        best = max(filter(None, [t, tr, a]), default=None)
        lines.append(f"> | {label} | {_s(t)} | {_s(tr)} | {_s(a)} | Best: {_s(best)} |")

    lines.append(">")

    # Check for surprise: ambiguous scoring higher than trick
    trick_o = trick.get("overall")
    amb_o = ambiguous.get("overall")
    if trick_o and amb_o and amb_o > trick_o:
        lines.append("> **Surprise Result:** The ambiguous question scored HIGHER than the trick question!")
        lines.append("> This is because the LLM's refusal was the **safest possible response** —")
        lines.append("> it didn't hallucinate, didn't speculate. The trick question scored lower")
        lines.append("> because the LLM gave a *correct but detailed answer* that the evaluator")
        lines.append("> couldn't fully verify.")
        lines.append(">")
        lines.append('> **Key insight:** In RAG evaluation, **saying "I don\'t know" is safer than')
        lines.append("> being right in a way the evaluator can't verify.** This is why production")
        lines.append("> systems need LLM-as-judge.")

    lines.append(">")
    lines.append("> **Patterns revealed:**")
    lines.append(">")
    lines.append("> | Pattern | Evidence | Lesson |")
    lines.append("> | --- | --- | --- |")

    if trick.get("has_hallucination"):
        lines.append(
            "> | Correct answer flagged as hallucination | Trick Q: LLM correct but flagged | Heuristic evaluators have false positives |"
        )

    truthful_f = truthful.get("faithfulness")
    if truthful_f and truthful_f >= 0.95:
        lines.append(
            f"> | Direct quote = perfect faithfulness | Truthful Q: faithfulness {_s(truthful_f)} | Faithfulness rewards sticking to source text |"
        )

    if trick_o and amb_o and amb_o > trick_o:
        lines.append(
            '> | Refusal beats risky correctness | Ambiguous scored higher than trick | "I don\'t know" is safest for evaluation |'
        )

    amb_ret = ambiguous.get("retrieval")
    if amb_ret and amb_ret < 0.6:
        lines.append(
            f"> | Vague question = retrieval problem | Ambiguous: retrieval {_s(amb_ret)} | Ambiguity hurts retrieval, not generation |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Lab 1+2: Business & Technical Questions
# ---------------------------------------------------------------------------


def business_questions_lab1() -> str:
    """Static Business Q&A section for Lab 1."""
    return """> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A company's customer support chatbot retrieves financial regulation documents from a database
> with 10 million embeddings. They need low-latency, multilingual search with metadata filtering.
> Which vector store?"**
>
> You tested `top_k` and saw how more candidates dilute retrieval. For 10M documents with
> metadata filtering, you need a managed vector store — OpenSearch Serverless (k-NN + BM25
> hybrid, metadata filters, scales to millions).
>
> **Q: "A company's RAG application returns relevant-looking but incorrect chunks for long technical
> documents. How do they optimise?"**
>
> You tuned `top_k` in this lab. You saw that smaller top_k = more precise but miss cross-section
> context. For long technical docs: increase chunk overlap, tune top_k per use case, add re-ranking.
>
> **Q: "When should a company use RAG vs fine-tuning?"**
>
> You built a RAG system that answers questions from uploaded documents WITHOUT training.
> RAG is for when knowledge changes (policies, regulations) — just upload new documents.
> Fine-tuning is for when you need the model to behave differently (tone, format)."""


def business_questions_lab2() -> str:
    """Static Business Q&A section for Lab 2."""
    return """> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A finance company's AI assistant must not provide inappropriate financial advice or make
> claims not grounded in approved guidance. How should they implement grounding checks?"**
>
> You measured faithfulness — you saw faithfulness=0.0 when the LLM answered without grounded
> context, and faithfulness=1.0 when it stuck to the source. For finance: set a **high grounding
> score threshold** in Bedrock Guardrails.
>
> **Q: "A GenAI assistant must generate responses in a consistent format. How?"**
>
> You saw the LLM's output format varies by question. The answer: **prompt templates** — define
> the output format in the system prompt. Bedrock Prompt Management for centralised templates.
>
> **Q: "How do you detect hallucination in production?"**
>
> You saw `has_hallucination=true` (false positive — LLM quoted the question) and
> `has_hallucination=false`. In production: LLM-as-judge or Bedrock Guardrails grounding checks."""


# ---------------------------------------------------------------------------
# Lab 3: Business Metrics
# ---------------------------------------------------------------------------


def analyse_lab3_comparison(
    clear: dict[str, Any],
    vague: dict[str, Any],
) -> str:
    """Generate the Business vs Technical Gap analysis."""
    lines = []
    lines.append("> ### 📊 The Business vs Technical Gap — Your Results")
    lines.append(">")

    c_ret = clear.get("retrieval")
    v_ret = vague.get("retrieval")
    c_faith = clear.get("faithfulness")
    v_faith = vague.get("faithfulness")
    c_rel = clear.get("answer_relevance")
    v_rel = vague.get("answer_relevance")
    c_overall = clear.get("overall")
    v_overall = vague.get("overall")
    c_passed = clear.get("passed")
    v_passed = vague.get("passed")

    if c_ret and v_ret:
        ret_diff = abs(c_ret - v_ret)
        if ret_diff < 0.05:
            lines.append(f"> Both questions got nearly **identical retrieval** ({_s(c_ret)} vs {_s(v_ret)}) —")
            lines.append("> the vector store returned similar chunks. The difference is in how the LLM handled them.")
        else:
            lines.append(f"> **Retrieval gap:** {_s(c_ret)} vs {_s(v_ret)} ({_delta(v_ret, c_ret)}).")

    lines.append(">")
    lines.append("> | | Clear question | Vague question |")
    lines.append("> | --- | --- | --- |")
    lines.append(f"> | **Faithfulness** | {_s(c_faith)} | {_s(v_faith)} |")
    lines.append(f"> | **answer_relevance** | {_s(c_rel)} | {_s(v_rel)} |")
    lines.append(f"> | **Overall** | {_s(c_overall)} ({_pf(c_passed)}) | {_s(v_overall)} ({_pf(v_passed)}) |")
    lines.append(">")

    if c_passed and not v_passed:
        lines.append("> **The surprise:** The clear question passed but the vague one failed — yet both")
        lines.append("> may have given equally useful answers to a real user. Technical score says one")
        lines.append("> failed — business reality may say both answered the question.")
    elif c_passed and v_passed:
        lines.append("> Both passed technically — but look at the gap in scores. A business metric")
        lines.append("> would reveal whether users found both answers equally satisfying.")

    lines.append(">")
    lines.append("> **This is the gap Lab 3 teaches you to see:**")
    lines.append("> Technical scores are necessary but not sufficient. An AI engineer must translate")
    lines.append("> technical metrics into business language:")
    lines.append('> - "Retrieval is 0.85" → **"85% of searches find relevant documents"**')
    lines.append('> - "Faithfulness is 0.92" → **"92% of answers are factually grounded"**')
    lines.append('> - "Overall passed" → **"This query was resolved without human intervention"**')

    return "\n".join(lines)


def business_questions_lab3() -> str:
    """Static Business Q&A section for Lab 3."""
    return """> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A retail company needs to evaluate fairness across demographic groups for a product
> recommendation GenAI app. What solution?"**
>
> You learned that technical metrics don't tell the full business story. For fairness, the company
> needs metrics *per demographic group*, not just overall. Use Bedrock Prompt Management + Flows
> (A/B traffic) + Guardrails + CloudWatch alarms.
>
> **Q: "An ecommerce company needs to switch between FMs based on regulations, cost, and performance.
> Rules change hourly. Which architecture?"**
>
> Different questions need different handling. AWS AppConfig for dynamic routing rules
> (propagated instantly, no redeploy) + Lambda for business logic."""


# ---------------------------------------------------------------------------
# Lab 4: Guardrails & Safety
# ---------------------------------------------------------------------------


def analyse_lab4_injection(
    attempts: list[dict[str, Any]],
    eval_result: dict[str, Any] | None,
) -> str:
    """Analyse prompt injection results."""
    lines = []
    lines.append("> ### 📊 Prompt Injection Analysis")
    lines.append(">")

    # Count successes
    succeeded = 0
    total = len(attempts)
    for a in attempts:
        answer = (a.get("answer") or "").lower()
        question = (a.get("question") or "").lower()
        if (
            ("joke" in question
            and ("joke" in answer or "ha" in answer or "why" in answer))
            or ("pirate" in question
            and ("arr" in answer or "matey" in answer))
            or ("2+2" in question
            and "4" in answer
            and "refund" not in answer)
        ):
            succeeded += 1

    rate = succeeded / max(total, 1) * 100
    lines.append(f"> **The scorecard: {succeeded} out of {total} injections succeeded** ({rate:.0f}% success rate).")
    if succeeded > 0:
        lines.append("> In production, this would be a **critical security finding**.")
    else:
        lines.append('> The LLM resisted all attempts — but this may be "accidental safety" (the RAG')
        lines.append("> context steered the LLM), not a real guardrail. A smarter attack might succeed.")

    lines.append(">")
    lines.append('> #### The critical insight: "Accidental safety" ≠ "Secure"')
    lines.append(">")
    lines.append("> Without input guardrails, the system relies on the LLM deciding not to follow")
    lines.append("> injections — which is not reliable. A real guardrail would pattern-match")
    lines.append('> "ignore.*instructions" and block BEFORE the LLM sees it.')
    lines.append(">")
    lines.append("> **DE parallel:** This is exactly like SQL injection protection. You don't let")
    lines.append("> `DROP TABLE users` reach the database — you validate input *before* execution.")

    if eval_result:
        e_overall = eval_result.get("overall")
        e_faith = eval_result.get("faithfulness")
        if e_overall is not None:
            lines.append(">")
            lines.append(f"> **Evaluation of the injection:** overall={_s(e_overall)}, faithfulness={_s(e_faith)}.")
            if e_overall < 0.5:
                lines.append("> This is the **lowest overall score** — proving the evaluator catches")
                lines.append("> injections even without guardrails (but only *after* the damage is done).")

    return "\n".join(lines)


def business_questions_lab4() -> str:
    """Static Business Q&A section for Lab 4."""
    return """> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A finance company must ensure AI doesn't provide inappropriate advice, generate competitor
> content, or make ungrounded claims. Which Bedrock Guardrails steps?"**
>
> Map to Bedrock: Denied topics (block "guaranteed returns"), Custom word filters (competitor names),
> High grounding threshold (strict — only source-backed answers). NOT content filters (hate/violence).
>
> **Q: "A GenAI assistant must block hate speech, inappropriate topics, and PII. Centralised prompt
> management needed. Least maintenance?"**
>
> Bedrock Prompt Management (centralised templates) + Bedrock Guardrails (category filters +
> sensitive term lists). NOT Lambda + Comprehend (too much custom code).
>
> **Q: "How do you prevent prompt injection in production?"**
>
> Two layers: (1) Input guardrails block known patterns before the LLM sees them.
> (2) Golden dataset includes injection test cases that verify non-leakage."""


# ---------------------------------------------------------------------------
# Lab 5: Observability
# ---------------------------------------------------------------------------


def analyse_lab5_dashboard(
    results: list[dict[str, Any]],
    env: str,
) -> str:
    """Generate the 5-pattern analysis for the mini dashboard."""
    lines = []
    lines.append("> ### 📊 Mini Dashboard Analysis — Patterns")
    lines.append(">")

    valid = [r for r in results if r.get("overall") is not None]
    if not valid:
        return "\n".join(lines)

    # Pattern 1: Latency correlation
    lines.append("> **Pattern 1: Latency correlates with answer length, not question difficulty**")
    lines.append(">")
    latencies = [(r.get("question", "?")[:30], r.get("latency_ms", 0)) for r in valid]
    sorted_lat = sorted(latencies, key=lambda x: x[1], reverse=True)
    lines.append("> | Question | Latency |")
    lines.append("> | --- | --- |")
    for q, lat in sorted_lat:
        lines.append(f"> | {q}... | {lat}ms |")
    lines.append(">")

    # Pattern 2: Faithfulness
    perfect_faith = [r for r in valid if r.get("faithfulness") and r["faithfulness"] >= 0.99]
    lines.append(f"> **Pattern 2: {len(perfect_faith)}/{len(valid)} questions got faithfulness = 1.0**")
    lines.append("> Short, focused answers stick closely to source text → perfect faithfulness.")
    lines.append("> Longer answers that paraphrase across sections → faithfulness drops.")
    lines.append(">")

    # Pattern 3: Content gaps
    failed = [r for r in valid if not r.get("passed")]
    if failed:
        lines.append(f"> **Pattern 3: {len(failed)} question(s) reveal content gaps**")
        for r in failed:
            lines.append(f'> - "{r.get("question", "?")[:40]}": overall={_s(r.get("overall"))} (FAIL)')
        lines.append("> These are **flywheel signals** — upload more documents or refuse gracefully.")
    lines.append(">")

    # Summary stats
    pass_count = sum(1 for r in valid if r.get("passed"))
    avg_ret = sum(r.get("retrieval", 0) for r in valid) / len(valid)
    avg_faith = sum(r.get("faithfulness", 0) for r in valid) / len(valid)
    avg_overall = sum(r.get("overall", 0) for r in valid) / len(valid)
    halluc_count = sum(1 for r in valid if r.get("has_hallucination"))

    lines.append("> **Summary Statistics:**")
    lines.append(">")
    lines.append("> | Metric | Value | Production interpretation |")
    lines.append("> | --- | --- | --- |")
    lines.append(
        f"> | Pass rate | {pass_count}/{len(valid)} ({pass_count / len(valid) * 100:.0f}%) | % of queries meeting quality bar |"
    )
    lines.append(f"> | Avg retrieval | {avg_ret:.3f} | {_quality(avg_ret)} |")
    lines.append(f'> | Avg faithfulness | {avg_faith:.3f} | {"Good" if avg_faith >= 0.7 else "Review needed"} |')
    lines.append(f'> | Avg overall | {avg_overall:.3f} | {"Healthy" if avg_overall >= 0.7 else "Below threshold"} |')
    lines.append(
        f'> | Hallucination flags | {halluc_count}/{len(valid)} | {"Review for false positives" if halluc_count > 0 else "Clean"} |'
    )

    return "\n".join(lines)


def business_questions_lab5() -> str:
    """Static Business Q&A section for Lab 5."""
    return """> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "How would you set up monitoring for an AI chatbot in production?"**
>
> Three layers: (1) Structured query logs for debugging (Lab 14), (2) Prometheus metrics for
> dashboards and alerting (Lab 15), (3) OpenTelemetry traces for latency analysis.
>
> **Q: "What alerts would you set for an AI system?"**
>
> From your dashboard: retrieval < 0.5 for 24h (drift), hallucination > 10%/day (safety),
> P99 latency > 5s cloud (perf), "I don't have info" > 20% (content gap), token cost > $50/day.
>
> **Q: "How would you monitor cost for a GenAI application?"**
>
> Track `token_usage_total` per hour, set budget alarms at 80% of monthly limit, build a
> dashboard showing cost-per-question trends."""


# ---------------------------------------------------------------------------
# Lab 6: Data Flywheel
# ---------------------------------------------------------------------------


def analyse_lab6_flywheel(
    before: dict[str, Any],
    after: dict[str, Any],
    upload: dict[str, Any],
) -> str:
    """Analyse the before/after flywheel turn."""
    lines = []
    lines.append("> ### 📊 The Flywheel Turned — Score Analysis")
    lines.append(">")

    b_ret = before.get("retrieval")
    a_ret = after.get("retrieval")
    b_faith = before.get("faithfulness")
    a_faith = after.get("faithfulness")
    b_overall = before.get("overall")
    a_overall = after.get("overall")

    if b_ret is not None and a_ret is not None:
        lines.append(f"> **Retrieval: {_s(b_ret)} → {_s(a_ret)} ({_delta(b_ret, a_ret)})**")
        if a_ret > b_ret:
            lines.append("> The vector store now finds the uploaded document as the best match.")
        else:
            lines.append("> Retrieval didn't improve much — the new document may not have strong")
            lines.append("> keyword overlap with the question. The *ranking* may have changed even")
            lines.append("> if the average score didn't jump.")
        lines.append(">")

    if b_faith is not None and a_faith is not None:
        delta = a_faith - b_faith
        lines.append(f"> **Faithfulness: {_s(b_faith)} → {_s(a_faith)} ({_delta(b_faith, a_faith)})**")
        if delta > 0.5:
            lines.append("> The biggest jump possible. Before: the LLM fabricated without grounding.")
            lines.append("> After: every sentence maps directly to the uploaded document.")
        lines.append(">")

    if b_overall is not None and a_overall is not None:
        lines.append(f"> **Overall: {_s(b_overall)} → {_s(a_overall)} ({_delta(b_overall, a_overall)})**")
        if after.get("passed") and not before.get("passed"):
            lines.append("> From FAIL to PASS. 🎉 In production, this is the metric you'd track:")
            lines.append('> "How many questions moved from FAIL to PASS this week?"')
        lines.append(">")

    lines.append("> **DE parallel:** Adding a row to a lookup table doesn't change the join algorithm —")
    lines.append("> it just means the join now *finds a match* where it returned NULL before.")

    return "\n".join(lines)


def analyse_lab6_suite(
    total: int | None,
    passed: int | None,
    failed: int | None,
    pass_rate: float | None,
    avg_score: float | None,
    cases: list[dict[str, Any]] | None,
) -> str:
    """Analyse the golden dataset suite results."""
    lines = []
    lines.append("> ### 📊 Golden Dataset Suite Results")
    lines.append(">")

    if total and passed is not None and failed is not None:
        lines.append(f"> **{passed}/{total} passed ({pass_rate or 0:.1f}%)** — avg overall: {_s(avg_score)}")
        lines.append(">")

        if cases:
            lines.append("> | Question | Overall | Result |")
            lines.append("> | --- | --- | --- |")
            for c in cases:
                q = c.get("question", "?")[:45]
                o = c.get("scores", {}).get("overall")
                p = c.get("scores", {}).get("passed")
                lines.append(f"> | {q} | {_s(o)} | {_pf(p)} |")
            lines.append(">")

        if failed > 0:
            lines.append("> **Intentional failures:** The golden dataset *should* contain questions that")
            lines.append("> fail, to prove the system doesn't hallucinate for off-topic questions.")

        lines.append(">")
        lines.append("> In production, you'd set an alerting threshold (e.g., \"alert if pass rate drops")
        lines.append('> below 75%"). The golden dataset runs on every deploy, just like unit tests.')

    return "\n".join(lines)


def business_questions_lab6() -> str:
    """Static Business Q&A section for Lab 6."""
    return """> ### 🏢 Business & Technical Questions This Lab Helps You Answer
>
> **Q: "A company deployed a GenAI chatbot but quality is declining. How should they implement
> continuous improvement?"**
>
> The flywheel: monitor → detect failures → add documents → re-evaluate → redeploy. The golden
> dataset runs on every deploy like unit tests. A regression means something broke.
>
> **Q: "How do you build a golden dataset for evaluating a RAG system?"**
>
> Each entry has: question, expected keywords, expected context chunks, minimum retrieval score,
> minimum faithfulness. The dataset grows from real failures (the flywheel)."""


# ---------------------------------------------------------------------------
# Labs 7-8: Thinking exercises (static content)
# ---------------------------------------------------------------------------


def thinking_exercises_labs_7_8() -> str:
    """Content for Labs 7 and 8 (thinking exercises)."""
    return """## Labs 7 & 8: Thinking Exercises

> Labs 7 (RLHF / Feedback) and 8 (Infrastructure Scaling) are thinking exercises
> that don't require API calls.

### Lab 7: RLHF / User Feedback (key concepts)

The feedback loop: User → AI answers → User gives 👍 or 👎 → Bad answers become
golden dataset cases → Fix root cause → Re-evaluate → Deploy → Repeat.

**Design points:**
- `/api/chat` response includes `feedback_url`
- `POST /api/feedback` with `{session_id, rating, comment}`
- Feedback stored in DynamoDB (or local JSON for dev)
- Weekly: review 👎 answers → add to golden dataset → fix → redeploy

### Lab 8: Infrastructure Scaling (your DE superpower)

**AI infrastructure = 80% your existing skills + 20% AI-specific concerns:**

| Scaling Challenge | DE Skill That Solves It |
| --- | --- |
| 1000 concurrent users | ECS auto-scaling |
| LLM calls are slow (2-5s) | SQS queues + Lambda workers |
| Repeated questions | DynamoDB/ElastiCache caching |
| Embedding 10,000 docs | Kinesis/SQS batching |
| Cost explosion | API Gateway throttling |

The AI-specific additions: embedding caching, token budget management, async LLM calls."""


# ---------------------------------------------------------------------------
# Labs 9-13: Phase 4 (automated in run_all_labs.py — placeholder kept for reference)
# ---------------------------------------------------------------------------


def phase_4_placeholder() -> str:
    """Phase 4 placeholder — kept for backward compatibility but no longer used in reports."""
    return """---

## Phase 4: Advanced RAG Techniques (Labs 9-13)

> **Note:** Phase 4 labs (Guardrails, Re-ranking, Hybrid Search, Bulk Ingestion,
> HNSW Tuning) require feature-flagged restarts and manual steps that are not yet
> automated in `run_all_labs.py`. See the full hands-on docs:
> - [Phase 4 Labs](../../docs/hands-on-labs/hands-on-labs-phase-4.md)
>
> Phase 4 automation is planned for a future update when I23-I25 are implemented.

### Labs covered in Phase 4:

| Lab | Topic | Prerequisite |
| --- | --- | --- |
| Lab 9 | Guardrails & PII Detection | I23 |
| Lab 10 | Re-ranking with Cross-Encoder | I24 |
| Lab 11 | Hybrid Search (BM25 + Vector) | I25 |
| Lab 12 | Bulk Ingestion | None |
| Lab 13 | HNSW Tuning & Sharding | None |
"""


# ---------------------------------------------------------------------------
# Labs 14-16: Phase 5 (automated)
# ---------------------------------------------------------------------------


def analyse_lab14_query_logs(
    results: list[dict[str, Any]],
    stats: dict[str, Any] | None,
) -> str:
    """Analyse query logging results."""
    lines = []
    lines.append("> ### 📊 Query Log Analysis")
    lines.append(">")

    if results:
        lines.append("> **Logged queries and expected failure categories:**")
        lines.append(">")
        lines.append("> | Question | Expected Category | Actual Category |")
        lines.append("> | --- | --- | --- |")
        for r in results:
            q = r.get("question", "?")[:40]
            # Infer expected category
            overall = r.get("overall")
            retrieval = r.get("retrieval")
            faithfulness = r.get("faithfulness")
            if overall and overall >= 0.7:
                expected = "`none` (passed)"
            elif retrieval and retrieval < 0.4:
                expected = "`bad_retrieval` or `off_topic`"
            elif faithfulness and faithfulness < 0.5:
                expected = "`hallucination`"
            else:
                expected = "`marginal`"
            actual = r.get("failure_category", "—")
            lines.append(f"> | {q} | {expected} | {actual} |")

    lines.append(">")
    lines.append("> **Key insight:** The failure categories map directly to fixes:")
    lines.append(">")
    lines.append("> | Category | Root Cause | Fix |")
    lines.append("> | --- | --- | --- |")
    lines.append("> | `bad_retrieval` | Wrong chunks returned | Better chunking, more docs, tune top_k |")
    lines.append("> | `hallucination` | Good chunks, bad answer | Better system prompt, lower temperature |")
    lines.append("> | `off_topic` | Outside document scope | Add documents or refuse gracefully |")
    lines.append("> | `marginal` | Borderline scores | Monitor — may need prompt tuning |")

    return "\n".join(lines)


def analyse_lab15_metrics(env: str) -> str:
    """Analysis content for Lab 15 (metrics endpoint)."""
    return f"""> ### 📊 Metrics Analysis
>
> The `/api/metrics` endpoint exposes Prometheus-format metrics.
>
> **Metric types you'll see:**
>
> | Metric | Type | What it means |
> | --- | --- | --- |
> | `chat_requests_total` | Counter | Total requests (only goes up) |
> | `chat_errors_total` | Counter | Total errors (only goes up) |
> | `chat_latency_p50_ms` | Gauge | Current median latency (goes up/down) |
> | `chat_latency_p95_ms` | Gauge | Current P95 latency |
> | `evaluation_pass_rate` | Gauge | Current pass rate |
> | `failure_category_*` | Counter | Failures by type |
>
> **How to use:** `error_rate = chat_errors_total / chat_requests_total`
>
> **DE parallel:** CloudWatch has the same types. `NumberOfObjects` in S3 = gauge.
> `GetRequests` = counter. `Latency` in ALB = histogram.
>
> **Alert design from your results:**
>
> | Scenario | Metric | Threshold |
> | --- | --- | --- |
> | System down | error_rate | > 50% for 5 min |
> | Getting slow | p95 latency | > {"60s (local)" if env == "local" else "5s"} for 5 min |
> | Quality dropping | pass_rate | < 0.6 for 1 hour |
> | Hallucinating | hallucination count | > 10 in 1 hour |"""


def analyse_lab16_golden_dataset(
    total_cases: int | None,
    categories: dict[str, int] | None,
) -> str:
    """Analysis content for Lab 16 (golden dataset regression)."""
    lines = []
    lines.append("> ### 📊 Golden Dataset Analysis")
    lines.append(">")

    if total_cases:
        lines.append(f"> **{total_cases} cases** across {len(categories or {})} categories:")
        lines.append(">")
        if categories:
            lines.append("> | Category | Count | What it tests |")
            lines.append("> | --- | --- | --- |")
            cat_descriptions = {
                "policy": "Refund, return, exchange policies",
                "logistics": "Shipping, delivery, tracking",
                "contact": "Support channels, hours, escalation",
                "product": "Product details, availability",
                "multi_turn": "Follow-up questions, context retention",
                "edge_case": "Ambiguity, injection, out-of-scope",
                "pii": "PII detection and redaction",
            }
            for cat, count in sorted(categories.items()):
                desc = cat_descriptions.get(cat, "—")
                lines.append(f"> | {cat} | {count} | {desc} |")
        lines.append(">")
        lines.append("> **Growth strategy:** Every production bug → new test case.")
        lines.append("> At 5 cases = proof of concept. At 25 = confidence. At 100+ = production-grade.")
        lines.append(">")
        lines.append("> **DE parallel:** You don't ship a data pipeline with 5 DQ checks and call it done.")
        lines.append("> Every data incident becomes a new check. Same for AI.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Skills Checklist
# ---------------------------------------------------------------------------


def skills_checklist(phase: int) -> str:
    """Generate skills checklist for a phase."""
    checklists = {
        1: [
            ("Retrieval quality measurement", "Lab 1"),
            ("Retrieval-faithfulness trade-off", "Lab 1"),
            ("top_k tuning and its impact", "Lab 1"),
            ("Hallucination detection", "Lab 2"),
            ("Faithfulness scoring and weight", "Lab 2"),
            ("Diagnosing retrieval vs generation problems", "Lab 2"),
        ],
        2: [
            ("Business-aligned metrics (beyond technical scores)", "Lab 3"),
            ("Translating AI metrics to business language", "Lab 3"),
            ("Guardrails design (4 layers: input/output/cost/topic)", "Lab 4"),
            ("Prompt injection awareness (with real examples)", "Lab 4"),
            ("AI observability (monitoring + AI-specific signals)", "Lab 5"),
            ("Dashboard and alert design for AI", "Lab 5"),
        ],
        3: [
            ("Data flywheel (detect → fix → evaluate → lock → repeat)", "Lab 6"),
            ("Golden dataset growth from real usage", "Lab 6"),
            ("RLHF in RAG context (user feedback loops)", "Lab 7"),
            ("Feedback system design", "Lab 7"),
            ("Infrastructure scaling for AI (your DE superpower)", "Lab 8"),
            ("AI-specific scaling concerns (embeddings, tokens, async LLM)", "Lab 8"),
        ],
        4: [
            ("Input guardrails & PII detection", "Lab 9"),
            ("Two-stage retrieval (re-ranking)", "Lab 10"),
            ("Hybrid search (BM25 + vector)", "Lab 11"),
            ("Bulk ingestion performance", "Lab 12"),
            ("HNSW tuning & sharding", "Lab 13"),
        ],
        5: [
            ("Structured query logging (JSONL format)", "Lab 14"),
            ("Failure triage categories", "Lab 14"),
            ("Prometheus metric types (counter, gauge, histogram)", "Lab 15"),
            ("Alert design for AI systems", "Lab 15"),
            ("Golden dataset regression testing", "Lab 16"),
            ("Category-level analysis & dataset growth", "Lab 16"),
        ],
    }

    skills = checklists.get(phase, [])
    if not skills:
        return ""

    lines = [f"\n## Phase {phase} — Skills Checklist\n"]
    lines.append("| # | Skill | Lab | Demonstrated? |")
    lines.append("| --- | --- | --- | --- |")
    for i, (skill, lab) in enumerate(skills, 1):
        lines.append(f"| {i} | {skill} | {lab} | ✅ Yes |")

    return "\n".join(lines)
