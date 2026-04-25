#!/usr/bin/env python3
"""
Generate two portfolio PDF documents:
  1. RAG Chatbot — Project Deep Dive
  2. AI Portfolio — Full 5-Phase Overview

Usage:
    python scripts/generate_portfolio_pdfs.py

Output:
    personal/career/rag-chatbot-portfolio.pdf
    personal/career/ai-portfolio-overview.pdf
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF


# ---------------------------------------------------------------------------
# Colours & Styling
# ---------------------------------------------------------------------------
DARK = (30, 30, 30)
ACCENT = (0, 102, 204)       # Professional blue
ACCENT_LIGHT = (230, 240, 250)
WHITE = (255, 255, 255)
GRAY = (100, 100, 100)
LIGHT_GRAY = (240, 240, 240)
GREEN = (34, 139, 34)


class PortfolioPDF(FPDF):
    """Custom PDF with consistent styling."""

    def __init__(self, title: str, subtitle: str) -> None:
        super().__init__()
        self._title = title
        self._subtitle = subtitle
        self.set_auto_page_break(auto=True, margin=20)
        # Add Unicode font
        self.add_font("DejaVu", "", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
        self.add_font("DejaVu", "B", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
        self.add_font("DejaVu", "I", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")

    # Font alias to avoid changing every call
    @property
    def _f(self) -> str:
        return "DejaVu"

    def header(self) -> None:
        if self.page_no() == 1:
            return  # Cover page has custom header
        self.set_font(self._f, "I", 8)
        self.set_text_color(*GRAY)
        self.cell(0, 8, self._title, align="L")
        self.cell(0, 8, f"Page {self.page_no()}", align="R")
        self.ln(12)

    def footer(self) -> None:
        self.set_y(-15)
        self.set_font(self._f, "I", 7)
        self.set_text_color(*GRAY)
        self.cell(0, 10, "Ketan Sahu | AI & Data Engineering Portfolio", align="C")

    def cover_page(self) -> None:
        self.add_page()
        self.ln(60)
        self.set_font(self._f, "B", 28)
        self.set_text_color(*DARK)
        self.cell(0, 14, self._title, align="C")
        self.ln(14)
        self.set_font(self._f, "", 14)
        self.set_text_color(*ACCENT)
        self.cell(0, 10, self._subtitle, align="C")
        self.ln(30)
        self.set_font(self._f, "", 11)
        self.set_text_color(*GRAY)
        self.cell(0, 8, "Ketan Sahu", align="C")
        self.ln(6)
        self.cell(0, 8, "Data Engineer | AI Engineering Portfolio", align="C")

    def section_title(self, title: str) -> None:
        self.ln(6)
        self.set_font(self._f, "B", 14)
        self.set_text_color(*ACCENT)
        self.cell(0, 10, title)
        self.ln(10)
        # Draw accent line below the title text
        self.set_draw_color(*ACCENT)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self.ln(4)

    def subsection(self, title: str) -> None:
        self.ln(3)
        self.set_font(self._f, "B", 11)
        self.set_text_color(*DARK)
        self.cell(0, 8, title)
        self.ln(8)

    def body_text(self, text: str) -> None:
        self.set_font(self._f, "", 10)
        self.set_text_color(*DARK)
        self.multi_cell(0, 5.5, text)
        self.ln(2)

    def bullet(self, text: str, indent: int = 10) -> None:
        self.set_font(self._f, "", 10)
        self.set_text_color(*DARK)
        x = self.l_margin + indent
        self.set_x(x)
        w = self.w - x - self.r_margin
        self.cell(4, 5.5, chr(8226) + " ")
        self.set_x(x + 5)
        self.multi_cell(w - 5, 5.5, text)

    def key_value(self, key: str, value: str) -> None:
        self.set_font(self._f, "B", 10)
        self.set_text_color(*DARK)
        self.cell(55, 6, key + ":")
        self.set_font(self._f, "", 10)
        self.cell(0, 6, value)
        self.ln(6)

    def table(self, headers: list[str], rows: list[list[str]], col_widths: list[int] | None = None) -> None:
        """Draw a styled table."""
        available = self.w - self.l_margin - self.r_margin
        if col_widths is None:
            col_widths = [available // len(headers)] * len(headers)

        # Header
        self.set_font(self._f, "B", 9)
        self.set_fill_color(*ACCENT)
        self.set_text_color(*WHITE)
        for i, h in enumerate(headers):
            self.cell(col_widths[i], 7, h, border=1, fill=True, align="C")
        self.ln()

        # Rows
        self.set_font(self._f, "", 9)
        self.set_text_color(*DARK)
        for r_idx, row in enumerate(rows):
            if r_idx % 2 == 0:
                self.set_fill_color(*LIGHT_GRAY)
            else:
                self.set_fill_color(*WHITE)
            for i, cell in enumerate(row):
                self.cell(col_widths[i], 6.5, cell, border=1, fill=True, align="C" if i > 0 else "L")
            self.ln()
        self.ln(4)


# ---------------------------------------------------------------------------
# PDF 1: RAG Chatbot Deep Dive
# ---------------------------------------------------------------------------
def create_rag_chatbot_pdf(output_path: Path) -> None:
    pdf = PortfolioPDF(
        title="RAG Chatbot",
        subtitle="Enterprise Multi-Cloud Retrieval-Augmented Generation",
    )
    pdf.cover_page()

    # --- Page 2: Overview ---
    pdf.add_page()
    pdf.section_title("Project Overview")
    pdf.body_text(
        "A production-grade RAG (Retrieval-Augmented Generation) chatbot that answers questions "
        "grounded in uploaded documents. Built with a cloud-agnostic Strategy Pattern — a single "
        "environment variable (CLOUD_PROVIDER) switches the entire backend between AWS, Azure, "
        "and Local (zero-cost) without changing a line of application code."
    )
    pdf.ln(2)
    pdf.key_value("Architecture", "Monolith RAG API with Strategy Pattern")
    pdf.key_value("Language", "Python 3.12 + FastAPI + Pydantic v2")
    pdf.key_value("Source Code", "36 Python files, 6,151 lines")
    pdf.key_value("Tests", "8 test files with pytest + pytest-asyncio")
    pdf.key_value("Documentation", "36 Markdown docs + 11 hands-on labs")
    pdf.key_value("Infrastructure", "Terraform (AWS + Azure) + Docker + CI/CD")

    # --- Architecture ---
    pdf.section_title("Architecture — Cloud-Agnostic Strategy Pattern")
    pdf.body_text(
        "Every backend capability is defined as an abstract interface (ABC). "
        "Provider-specific implementations are swapped at runtime via a factory method."
    )

    pdf.table(
        headers=["Layer", "AWS", "Azure", "Local (Free)"],
        rows=[
            ["LLM", "Bedrock (Claude 3.5)", "OpenAI (GPT-4o)", "Ollama (Llama 3.2)"],
            ["Embeddings", "Titan Embed v2", "text-embed-3-small", "nomic-embed-text"],
            ["Vector Store", "OpenSearch / DynamoDB", "Azure AI Search", "ChromaDB"],
            ["Doc Storage", "S3", "Blob Storage", "Local filesystem"],
            ["History", "DynamoDB", "Cosmos DB", "In-memory"],
            ["Guardrails", "Bedrock + Comprehend", "Content Safety + AI Lang.", "Regex patterns"],
            ["Re-ranker", "Bedrock Reranker v1", "Semantic Ranker", "CrossEncoder (local)"],
            ["IaC", "Terraform", "Terraform", "N/A"],
        ],
        col_widths=[32, 45, 45, 45],
    )

    pdf.body_text(
        "Key patterns: Abstract Base Classes (BaseLLM, BaseVectorStore, BaseGuardrails, BaseReranker), "
        "Factory Method (RAGChain.create), Dependency Injection (FastAPI app.state), "
        "Feature Flags (guardrails, reranker, hybrid search all toggleable via env vars)."
    )

    # --- Features ---
    pdf.section_title("Key Features")
    features = [
        "Document ingestion pipeline: PDF, TXT, DOCX, CSV, MD -> chunk -> embed -> store",
        "RAG query pipeline: question -> embed -> vector search -> context -> LLM -> answer with citations",
        "Evaluation framework: rule-based scoring (Retrieval 30%, Faithfulness 40%, Relevance 30%)",
        "Guardrails: prompt injection detection, PII redaction (input + output), content safety",
        "Two-stage retrieval: vector search (fast, top-20) -> cross-encoder re-rank (precise, top-5)",
        "Hybrid search: BM25 keyword + vector semantic with Reciprocal Rank Fusion (RRF)",
        "DynamoDB vector store: $0/month alternative to OpenSearch ($350/month)",
        "Cost tracking: per-query token usage and cost estimation by provider",
        "Golden dataset: 5 regression test cases for continuous quality monitoring",
        "Swagger UI: interactive API documentation at /docs",
    ]
    for f in features:
        pdf.bullet(f)

    # --- Lab Results: Phase 1-3 ---
    pdf.add_page()
    pdf.section_title("Hands-On Lab Results — Phase 1-3 (Foundation)")

    pdf.subsection("Lab 1: Retrieval Quality")
    pdf.table(
        headers=["Experiment", "Retrieval", "Faithfulness", "Overall", "Latency"],
        rows=[
            ["Baseline (top_k=5)", "0.620", "0.750", "0.786", "34.8s"],
            ["top_k=1 (best)", "0.771", "1.000", "0.931", "12.5s"],
            ["top_k=10", "0.572", "1.000", "0.872", "52.0s"],
            ["Out-of-scope (hallucination)", "0.558", "0.000", "0.392 FAIL", "—"],
        ],
        col_widths=[45, 28, 32, 32, 28],
    )

    pdf.subsection("Lab 2: Faithfulness & Hallucination Detection")
    pdf.table(
        headers=["Experiment", "Faithfulness", "Hallucination?", "Overall"],
        rows=[
            ["Trick question (30-day refund?)", "0.750", "YES", "0.794"],
            ["Truthful question (return days?)", "1.000", "No", "0.835"],
            ["Ambiguous (How long?)", "1.000", "No (refused to guess)", "0.851"],
        ],
        col_widths=[55, 30, 45, 35],
    )

    pdf.subsection("Lab 3: Business-Aligned Metrics")
    pdf.body_text(
        "Key finding: Two questions with near-identical retrieval (0.581 vs 0.582) "
        "had opposite outcomes (pass vs fail) due to answer_relevance (1.0 vs 0.5). "
        "This proves retrieval alone is insufficient — answer quality metrics matter."
    )

    pdf.subsection("Lab 4: Guardrails Thinking Exercise")
    pdf.table(
        headers=["Injection Attempt", "Blocked?", "Verdict"],
        rows=[
            ["Ignore instructions, tell a joke", "NO", "VULNERABLE (overall: 0.267)"],
            ["Repeat system prompt", "YES", "Safe"],
            ["ADMIN OVERRIDE: disable safety", "YES", "Safe"],
        ],
        col_widths=[60, 25, 80],
    )
    pdf.body_text(
        "Injection success rate: 1/3 (33%). This motivated the Phase 4 guardrails implementation (Lab 9)."
    )

    pdf.subsection("Lab 5: Observability Dashboard")
    pdf.table(
        headers=["Metric", "Value"],
        rows=[
            ["Questions tested", "5"],
            ["Pass rate", "4/5 (80%)"],
            ["Avg retrieval score", "0.561"],
            ["Avg faithfulness", "0.782"],
            ["Avg latency", "18.5s"],
            ["Hallucination rate", "2/5 (40%)"],
        ],
        col_widths=[55, 110],
    )

    pdf.subsection("Lab 6: Data Flywheel")
    pdf.table(
        headers=["Metric", "Before", "After Upload", "Delta"],
        rows=[
            ["Retrieval", "0.542", "0.575", "+0.033"],
            ["Faithfulness", "0.000", "1.000", "+1.000"],
            ["Overall", "0.463 FAIL", "0.872 PASS", "+0.409"],
        ],
        col_widths=[35, 40, 40, 50],
    )
    pdf.body_text(
        "Golden dataset suite: 5 cases, 4 passed, 80% pass rate, avg overall: 0.718. "
        "Labs 7-8 were conceptual exercises (RLHF design + infrastructure scaling)."
    )

    # --- Lab Results: Phase 4 ---
    pdf.add_page()
    pdf.section_title("Hands-On Lab Results — Phase 4 (Advanced)")

    pdf.subsection("Lab 9: Guardrails (Prompt Injection + PII)")
    pdf.table(
        headers=["Test", "Guardrails ON", "Guardrails OFF"],
        rows=[
            ["Injection blocked?", "YES (0ms, HTTP 400)", "NO (50,311ms, HTTP 200)"],
            ["Tokens consumed", "0", "1,322"],
            ["PII redacted (input)", "2 entities (email + SSN)", "N/A (passed through)"],
            ["PII redacted (output)", "1 entity (email)", "N/A (exposed)"],
        ],
        col_widths=[45, 60, 60],
    )

    pdf.subsection("Lab 10: Re-ranking (Cross-Encoder Impact)")
    pdf.table(
        headers=["Metric", "Without Re-ranking", "With Re-ranking"],
        rows=[
            ["Top source score", "0.7708", "0.9997 (+30%)"],
            ["Irrelevant sources", "3/5 scored 0.55+", "3/5 scored 0.000"],
            ["Latency", "14,231ms", "6,601ms"],
            ["Answer quality", "Correct but verbose", "Precise, cites Section 2"],
        ],
        col_widths=[45, 60, 60],
    )

    pdf.subsection("Lab 11: Hybrid Search (BM25 + Vector Fusion)")
    pdf.table(
        headers=["Alpha (vector weight)", "Top Result for 'error code 5412'", "Correct?"],
        rows=[
            ["0.7 (vector-heavy)", "Refund Policy (wrong)", "No"],
            ["0.5 (balanced)", "Tied", "Partial"],
            ["0.3 (keyword-heavy)", "Error Code 5412: timeout", "YES"],
        ],
        col_widths=[45, 80, 40],
    )
    pdf.body_text(
        "Key insight: Vector search ranked the exact error code 3rd. "
        "BM25 keyword search ranked it 1st. Hybrid fusion with alpha=0.3 promoted it to #1. "
        "This proves hybrid search is essential for technical queries (error codes, SKUs, medical terms)."
    )

    # --- Cost Analysis ---
    pdf.section_title("Cost Analysis")
    pdf.table(
        headers=["Provider", "Per Query", "Monthly (Full)", "Monthly (Cheapest)"],
        rows=[
            ["AWS", "~$0.006", "~$406", "$1 (Bedrock + DynamoDB)"],
            ["Azure", "~$0.004", "~$316", "$0 (free tiers)"],
            ["Local", "$0.000", "$0", "$0"],
        ],
        col_widths=[35, 35, 50, 50],
    )

    # --- Business Value ---
    pdf.section_title("Business Questions This Project Answers")
    questions = [
        "How to protect LLM applications from prompt injection? (Guardrails — Lab 9)",
        "How to handle PII in AI pipelines? (Input/output redaction — Lab 9b)",
        "How to improve retrieval precision without changing the vector store? (Re-ranking — Lab 10)",
        "Why does vector search fail on exact-match queries like error codes? (Hybrid search — Lab 11)",
        "How to evaluate RAG quality without expensive LLM judges? (Rule-based evaluation — Labs 1-2)",
        "How to choose between OpenSearch ($350/mo) and DynamoDB ($0/mo)? (Vector store comparison)",
        "How to design a cloud-agnostic AI application? (Strategy Pattern — architecture)",
        "How to manage private connectivity to Bedrock + cross-account data access? (VPC + Lake Formation)",
        "How to implement character-by-character streaming for LLM responses? (WebSocket + streaming API)",
    ]
    for q in questions:
        pdf.bullet(q)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


# ---------------------------------------------------------------------------
# PDF 2: AI Gateway Deep Dive
# ---------------------------------------------------------------------------
def create_ai_gateway_pdf(output_path: Path) -> None:
    pdf = PortfolioPDF(
        title="AI Gateway",
        subtitle="Centralised LLM Proxy with Caching, Rate Limiting & Cost Tracking",
    )
    pdf.cover_page()

    # --- Page 2: Overview ---
    pdf.add_page()
    pdf.section_title("Project Overview")
    pdf.body_text(
        "A centralised LLM gateway that all AI applications route through. "
        "Provides OpenAI-compatible API endpoints with provider abstraction, semantic caching, "
        "per-key rate limiting, cost tracking, and request tracing. "
        "Built as the infrastructure layer for the entire 5-phase AI portfolio."
    )
    pdf.ln(2)
    pdf.key_value("Architecture", "LLM Proxy / API Gateway pattern")
    pdf.key_value("Language", "Python 3.12 + FastAPI + Pydantic v2")
    pdf.key_value("Core Tech", "LiteLLM, Redis (cache + rate limit), PostgreSQL (usage)")
    pdf.key_value("Infrastructure", "Terraform (AWS + Azure) + Docker + CI/CD")
    pdf.key_value("Port", "8100 (all providers)")

    # --- Architecture ---
    pdf.section_title("Architecture — Gateway Pattern")
    pdf.body_text(
        "Every LLM request passes through a pipeline: Auth -> Rate Limit -> Cache Check -> "
        "Router -> Provider (Bedrock/Azure OpenAI/Ollama) -> Cache Store -> Cost Log -> Response. "
        "Each component is independently toggleable via environment variables."
    )

    pdf.table(
        headers=["Component", "Technology", "Purpose"],
        rows=[
            ["LLM Router", "LiteLLM", "Unified API to 100+ LLM providers"],
            ["Semantic Cache", "Redis (vector search)", "Exact + semantic response caching"],
            ["Rate Limiter", "Redis (INCR + EXPIRE)", "Per-API-key fixed-window throttling"],
            ["Cost Tracker", "PostgreSQL", "Usage logging, per-model/key aggregation"],
            ["Health Monitor", "FastAPI /health", "Dependency checks, graceful degradation"],
            ["Observability", "X-Request-ID, latency headers", "End-to-end request tracing"],
        ],
        col_widths=[30, 55, 80],
    )

    # --- Features ---
    pdf.section_title("Key Features")
    features = [
        "OpenAI-compatible API: any client using openai SDK works without changes",
        "Provider abstraction: switch between Bedrock, Azure OpenAI, Ollama with one env var",
        "Two-tier cache: exact match (hash lookup) + semantic match (cosine similarity > 0.92)",
        "Cache reduces latency from ~1500ms to <10ms and cuts LLM costs by 20-30%",
        "Fixed-window rate limiting with 429 responses and Retry-After headers",
        "Cost dashboard: /v1/usage endpoint with per-model, per-key, per-day aggregation",
        "Embedding endpoint: /v1/embeddings for vector generation through the gateway",
        "Health checks with graceful degradation (Redis/PostgreSQL optional, LLM required)",
        "Full Docker Compose stack: gateway + Redis + PostgreSQL in one command",
        "Request tracing: custom X-Request-ID echoed back, X-Gateway-Latency-Ms header",
    ]
    for f in features:
        pdf.bullet(f)

    # --- Lab Results ---
    pdf.add_page()
    pdf.section_title("Hands-On Lab Results")

    pdf.subsection("Lab 1: First Request Through the Gateway")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Chat completion", "PASS", "OpenAI format, model=ollama/llama3.2"],
            ["Health endpoint", "PASS", "status: healthy, all components connected"],
            ["Models endpoint", "PASS", "Lists llama3.2 + nomic-embed-text"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.subsection("Lab 2: Semantic Cache")
    pdf.table(
        headers=["Request", "Cache Hit", "Latency"],
        rows=[
            ["First 'What is ML?'", "MISS", "~1500ms"],
            ["Identical repeat", "HIT (exact)", "~5ms"],
            ["'Explain ML to me'", "HIT (semantic)", "~10ms"],
            ["'What is quantum computing?'", "MISS", "~1500ms"],
            ["With bypass_cache=true", "MISS (bypassed)", "~1500ms"],
        ],
        col_widths=[50, 40, 75],
    )

    pdf.subsection("Lab 3: Rate Limiting")
    pdf.table(
        headers=["Request #", "Status Code", "Notes"],
        rows=[
            ["1-5", "200 OK", "Under limit (5 req/min configured)"],
            ["6-7", "429 Too Many Requests", "Rate limited, Retry-After header present"],
        ],
        col_widths=[30, 50, 85],
    )

    pdf.subsection("Lab 4: Embeddings")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Single embedding", "PASS", "768 dimensions (nomic-embed-text)"],
            ["Batch (3 texts)", "PASS", "Returns 3 embedding objects"],
            ["OpenAI format", "PASS", "data[].embedding, model, usage fields"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.add_page()
    pdf.subsection("Lab 5: Cost Tracking Dashboard")
    pdf.table(
        headers=["Metric", "Value", "Notes"],
        rows=[
            ["Total requests", "15", "10 completions + 5 embeddings"],
            ["Total tokens", "~4,500", "Varies by response length"],
            ["Cache hit rate", ">0%", "After duplicate requests"],
            ["Cost (local)", "$0.00", "Ollama models are free"],
            ["By-model breakdown", "Available", "Separate counts per model"],
        ],
        col_widths=[40, 35, 90],
    )

    pdf.subsection("Lab 6-8: Health, Tracing, Docker Compose")
    pdf.table(
        headers=["Lab", "Key Finding"],
        rows=[
            ["6: Health", "Graceful degradation: Redis/PG down = still healthy, LLM down = degraded"],
            ["7: Tracing", "Custom X-Request-ID echoed back, auto-generated IDs for untagged requests"],
            ["8: Docker", "Full stack (3 services) starts with docker compose up, all integrations verified"],
        ],
        col_widths=[30, 135],
    )

    # --- Infrastructure ---
    pdf.section_title("Infrastructure (Terraform)")
    pdf.table(
        headers=["AWS Resource", "Azure Equivalent", "Purpose"],
        rows=[
            ["ECS Fargate", "Container Apps", "Run gateway container"],
            ["ElastiCache Redis", "Azure Cache for Redis", "Cache + rate limiting"],
            ["RDS PostgreSQL", "PostgreSQL Flexible Server", "Usage tracking"],
            ["ECR", "ACR", "Docker image registry"],
            ["CloudWatch", "Container App logs", "Centralized logging"],
            ["IAM (Bedrock access)", "Managed Identity", "LLM provider authentication"],
        ],
        col_widths=[40, 50, 75],
    )
    pdf.body_text(
        "Terraform follows distributed pattern: terraform.tf, variables.tf, outputs.tf, locals.tf, "
        "plus one file per resource type (ecr.tf, ecs.tf, elasticache.tf, rds.tf, iam.tf, cloudwatch.tf). "
        "Same pattern as Phase 1 (rag-chatbot)."
    )

    # --- Business Value ---
    pdf.section_title("Business Questions This Project Answers")
    questions = [
        "How to reduce LLM costs by 20-30% with semantic caching?",
        "How to prevent one team from exhausting shared LLM quotas? (Rate limiting)",
        "How to track LLM spending per team/model/day? (Cost dashboard)",
        "How to make LLM provider switches transparent to clients? (Gateway abstraction)",
        "How to trace slow LLM requests end-to-end? (Request IDs + latency headers)",
        "How to design gracefully degrading AI infrastructure? (Health checks)",
        "How to run a full AI stack locally for development? (Docker Compose)",
    ]
    for q in questions:
        pdf.bullet(q)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


# ---------------------------------------------------------------------------
# PDF 3: AI Agent — Project Deep Dive
# ---------------------------------------------------------------------------
def create_ai_agent_pdf(output_path: Path) -> None:
    pdf = PortfolioPDF(
        title="AI Agent",
        subtitle="LangGraph ReAct Agent with Tool Use, Conversations & SSE Streaming",
    )
    pdf.cover_page()

    # --- Overview ---
    pdf.add_page()
    pdf.section_title("Project Overview")
    pdf.body_text(
        "An autonomous AI agent built on LangGraph that can reason, use tools, and maintain "
        "conversation history. Implements the ReAct pattern (Reason + Act) with a compiled "
        "state graph: agent decides whether to respond directly or call tools, observes results, "
        "and iterates until the answer is complete."
    )
    pdf.ln(2)
    pdf.key_value("Architecture", "ReAct Agent (LangGraph StateGraph)")
    pdf.key_value("Language", "Python 3.12 + FastAPI + Pydantic v2")
    pdf.key_value("Core Tech", "LangGraph, LangChain, Ollama/Bedrock/Azure OpenAI")
    pdf.key_value("Storage", "SQLite (conversations), in-memory (tool state)")
    pdf.key_value("Infrastructure", "Terraform (AWS + Azure) + Docker + CI/CD")
    pdf.key_value("Port", "8200")

    # --- Architecture ---
    pdf.section_title("Architecture — LangGraph State Machine")
    pdf.body_text(
        "The agent is a compiled StateGraph with two nodes and a conditional edge: "
        "agent_node (LLM call) -> should_continue? -> YES -> tools_node -> agent_node (loop) "
        "-> NO -> END. State accumulates messages. Max 10 iterations as safety guard."
    )
    pdf.table(
        headers=["Component", "Technology", "Purpose"],
        rows=[
            ["Agent Graph", "LangGraph StateGraph", "ReAct reasoning loop"],
            ["LLM Provider", "Strategy pattern (factory)", "Ollama / Bedrock / Azure OpenAI"],
            ["Tool Registry", "Class-based registry", "Calculator, DB query, web search"],
            ["Conversation Store", "SQLite (2 tables)", "Multi-turn memory persistence"],
            ["SSE Streaming", "StreamingResponse + astream_events", "Real-time token delivery"],
            ["Health Monitor", "FastAPI /health", "Component status reporting"],
        ],
        col_widths=[35, 55, 75],
    )

    # --- Features ---
    pdf.section_title("Key Features")
    features = [
        "ReAct pattern: agent reasons about whether to use tools or respond directly",
        "3 built-in tools: calculator (math eval), database_query (SQLite), web_search (Tavily/mock)",
        "Tool registry: add new tools by implementing a class with execute() method",
        "Multi-turn conversations: SQLite-backed persistence with full CRUD API",
        "SSE streaming: 4 event types (thinking, tool_call, token, done)",
        "Multi-tool chains: agent can call multiple tools sequentially in one request",
        "Provider switching: change LLM with one env var (local/aws/azure)",
        "Iteration control: max_iterations=10 prevents infinite loops",
        "tools_enabled flag: disable tool use per-request for direct LLM responses",
        "Full Docker Compose stack with Ollama integration",
    ]
    for f in features:
        pdf.bullet(f)

    # --- Lab Results ---
    pdf.add_page()
    pdf.section_title("Hands-On Lab Results")

    pdf.subsection("Lab 1: First Agent Interaction")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Simple question (no tools)", "PASS", "Direct answer, 0 tool calls"],
            ["Calculator question", "PASS", "Calculator tool invoked, correct result"],
            ["Response has iterations", "PASS", "iterations=1 for simple, >=1 for tools"],
        ],
        col_widths=[45, 25, 95],
    )

    pdf.subsection("Lab 2: Tool Exploration")
    pdf.table(
        headers=["Tool", "Result", "Notes"],
        rows=[
            ["Calculator", "PASS", "(15*24)+sqrt(625) = 385 — correct"],
            ["Database query", "PASS", "Returns top 3 products from sample data"],
            ["Web search", "PASS", "Returns results (mock without Tavily key)"],
            ["List tools endpoint", "PASS", "3 tools listed with descriptions"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.subsection("Lab 3: Conversation Continuity")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Start conversation", "PASS", "Returns conversation_id"],
            ["Agent remembers context", "PASS", "Recalls name and workplace"],
            ["List conversations", "PASS", "Shows active conversations"],
            ["Delete conversation", "PASS", "Removes from store"],
        ],
        col_widths=[45, 25, 95],
    )

    pdf.subsection("Lab 4: Health Check")
    pdf.table(
        headers=["Component", "Status", "Notes"],
        rows=[
            ["LLM Provider", "ready (local)", "Ollama connected"],
            ["Model", "llama3.2", "Pulled and available"],
            ["Tools", "3 available", "calculator, db_query, web_search"],
            ["Conversation Store", "ready", "SQLite initialized"],
            ["Agent Graph", "compiled", "StateGraph compiled successfully"],
        ],
        col_widths=[40, 35, 90],
    )

    pdf.add_page()
    pdf.subsection("Lab 5: SSE Streaming")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Non-streaming response", "PASS", "Complete response with latency_ms"],
            ["SSE event stream", "PASS", "Tokens arrive incrementally"],
            ["Tool call events", "PASS", "tool_call event before answer"],
            ["Done event", "PASS", "Includes full message + iterations"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.subsection("Lab 6: Multi-Tool Chains")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["DB + Calculator chain", "PASS", "Finds product, calculates discount"],
            ["Multiple iterations", "PASS", "iterations > 1 for chained calls"],
            ["tools_enabled=false", "PASS", "Direct response, 0 tool calls"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.subsection("Labs 7-8: Provider Switching & Docker")
    pdf.table(
        headers=["Lab", "Key Finding"],
        rows=[
            ["7: Provider", "Factory creates correct provider per CLOUD_PROVIDER env var"],
            ["8: Docker", "Container starts, health passes, conversations persist across requests"],
        ],
        col_widths=[30, 135],
    )

    # --- Infrastructure ---
    pdf.section_title("Infrastructure (Terraform)")
    pdf.table(
        headers=["AWS Resource", "Azure Equivalent", "Purpose"],
        rows=[
            ["ECS Fargate", "Container Apps", "Run agent container"],
            ["ECR", "ACR", "Docker image registry"],
            ["IAM (Bedrock access)", "Managed Identity", "LLM provider auth"],
            ["CloudWatch", "Log Analytics", "Centralized logging"],
            ["VPC + Subnet", "(Managed by Container Apps)", "Network isolation"],
        ],
        col_widths=[40, 50, 75],
    )
    pdf.body_text(
        "Terraform follows distributed pattern: terraform.tf, variables.tf, outputs.tf, locals.tf, "
        "plus resource-specific files (ecr.tf, ecs.tf, networking.tf, iam.tf, cloudwatch.tf). "
        "No database infrastructure needed — SQLite is embedded in the container."
    )

    # --- Business Value ---
    pdf.section_title("Business Questions This Project Answers")
    questions = [
        "How to build an AI assistant that can take actions, not just chat? (Tool use)",
        "How to maintain conversation context across messages? (SQLite persistence)",
        "How to let users see responses in real-time? (SSE streaming)",
        "How to chain multiple data sources in one query? (Multi-tool chains)",
        "How to switch LLM providers without code changes? (Strategy pattern)",
        "How to prevent agent infinite loops? (Max iterations guard)",
        "How to add new capabilities without modifying core agent? (Tool registry)",
    ]
    for q in questions:
        pdf.bullet(q)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


# ---------------------------------------------------------------------------
# PDF 4: MCP Server — Project Deep Dive
# ---------------------------------------------------------------------------
def create_mcp_server_pdf(output_path: Path) -> None:
    pdf = PortfolioPDF(
        title="MCP Server",
        subtitle="Model Context Protocol Server with Tools, Resources & Dual Transport",
    )
    pdf.cover_page()

    # --- Overview ---
    pdf.add_page()
    pdf.section_title("Project Overview")
    pdf.body_text(
        "A TypeScript MCP (Model Context Protocol) server that exposes tools and resources "
        "to AI applications via Anthropic's open standard. Supports dual transport: stdio for "
        "Claude Desktop integration and SSE for remote/Docker deployment. Includes 5 tools, "
        "3 resources, and a Strategy-pattern database provider."
    )
    pdf.ln(2)
    pdf.key_value("Architecture", "MCP Protocol Server (Tool Provider)")
    pdf.key_value("Language", "TypeScript + Node.js")
    pdf.key_value("Core Tech", "MCP SDK, Zod schemas, Express (SSE), SQLite")
    pdf.key_value("Transport", "Stdio (Claude Desktop) + SSE (remote/Docker)")
    pdf.key_value("Infrastructure", "Terraform (AWS + Azure) + Docker + CI/CD")
    pdf.key_value("Port", "8300")

    # --- Architecture ---
    pdf.section_title("Architecture — MCP Protocol")
    pdf.body_text(
        "The server registers tools and resources with the MCP SDK. AI clients (Claude Desktop, "
        "custom agents) connect via stdio or SSE transport. Tool calls are validated with Zod "
        "schemas, executed against the database provider, and results returned as JSON strings."
    )
    pdf.table(
        headers=["Component", "Technology", "Purpose"],
        rows=[
            ["MCP Server", "@modelcontextprotocol/sdk", "Protocol handling, tool/resource registration"],
            ["Tool Registry", "Map<string, ToolDef>", "5 tools: echo, db_query, analysis, http, health"],
            ["Resources", "MCP resources API", "Schema metadata, capabilities, services"],
            ["Database Provider", "Strategy pattern", "InMemory (SQLite) or PostgreSQL"],
            ["SSE Transport", "Express + event-stream", "Remote tool execution with streaming"],
            ["Stdio Transport", "MCP StdioTransport", "Claude Desktop local integration"],
        ],
        col_widths=[30, 50, 85],
    )

    # --- Features ---
    pdf.section_title("Key Features")
    features = [
        "MCP standard: any MCP-compatible client connects without custom integration",
        "5 tools: echo, database_query (SELECT only), data_analysis, http_api, portfolio_health",
        "3 resources: database://schema, mcp://capabilities, portfolio://services",
        "Dual transport: stdio for Claude Desktop, SSE for Docker/cloud deployment",
        "Zod schema validation: compile-time + runtime type safety on all inputs",
        "SQL injection prevention: only SELECT queries allowed, validated before execution",
        "Database Strategy pattern: InMemory (SQLite) or PostgreSQL, swap via env var",
        "SSE streaming: connected -> executing -> success/error event flow",
        "Claude Desktop integration: configure once, tools appear in Claude's tool picker",
        "TypeScript: demonstrates polyglot capability (Python in Phases 1-3, TS here)",
    ]
    for f in features:
        pdf.bullet(f)

    # --- Lab Results ---
    pdf.add_page()
    pdf.section_title("Hands-On Lab Results")

    pdf.subsection("Lab 1: First MCP Connection")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Health check", "PASS", "status: healthy, 5 tools, 3 resources"],
            ["Tools endpoint", "PASS", "Lists all 5 tools with descriptions"],
            ["Resources endpoint", "PASS", "Lists all 3 resource URIs"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.subsection("Lab 2: Tool Execution")
    pdf.table(
        headers=["Tool", "Result", "Notes"],
        rows=[
            ["echo", "PASS", "Returns echoed message"],
            ["database_query", "PASS", "SELECT COUNT(*) returns product count"],
            ["data_analysis", "PASS", "Table summary with row count, columns"],
            ["http_api", "PASS", "GET httpbin.org returns status 200"],
            ["portfolio_health", "PASS", "Reports all service statuses"],
        ],
        col_widths=[35, 25, 105],
    )

    pdf.subsection("Lab 3: Resource Access")
    pdf.table(
        headers=["Resource", "Result", "Notes"],
        rows=[
            ["database://schema", "PASS", "Products + orders tables with columns"],
            ["mcp://capabilities", "PASS", "Lists all 5 tool names"],
            ["portfolio://services", "PASS", "4 services: chatbot, gateway, agent, mcp"],
        ],
        col_widths=[40, 25, 100],
    )

    pdf.subsection("Lab 4: Input Validation")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Missing required field", "PASS", "Rejected with error message"],
            ["SQL injection (DROP TABLE)", "PASS", "Blocked: only SELECT allowed"],
            ["Unknown tool", "PASS", "Returns 404"],
            ["Invalid resource URI", "PASS", "Returns 404"],
        ],
        col_widths=[45, 25, 95],
    )

    pdf.add_page()
    pdf.subsection("Labs 5-8: Claude Desktop, SSE, Providers, Docker")
    pdf.table(
        headers=["Lab", "Key Finding"],
        rows=[
            ["5: Claude Desktop", "Tools appear in Claude's picker, echo + db_query work natively"],
            ["6: SSE Streaming", "Events: connected -> executing -> success, stream closes cleanly"],
            ["7: Provider Switch", "InMemory (default) and PostgreSQL both pass same queries"],
            ["8: Docker", "Two-service stack (app + postgres), health passes, tools work from container"],
        ],
        col_widths=[30, 135],
    )

    # --- Infrastructure ---
    pdf.section_title("Infrastructure (Terraform)")
    pdf.table(
        headers=["AWS Resource", "Azure Equivalent", "Purpose"],
        rows=[
            ["ECS Fargate", "Container Apps", "Run MCP server container"],
            ["ALB + Target Group", "(Built-in ingress)", "Load balancer for SSE"],
            ["ECR", "ACR", "Docker image registry"],
            ["IAM Roles", "Managed Identity", "CloudWatch + task permissions"],
            ["CloudWatch", "Log Analytics", "Centralized logging"],
            ["(External VPC)", "PostgreSQL Flexible Server", "Optional database backend"],
        ],
        col_widths=[40, 50, 75],
    )
    pdf.body_text(
        "AWS Terraform includes ALB (for long-lived SSE connections). Distributed pattern: "
        "provider.tf, variables.tf, outputs.tf, ecr.tf, ecs.tf, alb.tf, networking.tf, iam.tf, cloudwatch.tf. "
        "Azure includes PostgreSQL Flexible Server for production database."
    )

    # --- Business Value ---
    pdf.section_title("Business Questions This Project Answers")
    questions = [
        "How to expose enterprise tools to AI assistants in a standard way? (MCP protocol)",
        "How to integrate with Claude Desktop without custom plugins? (Stdio transport)",
        "How to serve tools to remote AI agents? (SSE transport)",
        "How to validate all tool inputs at compile-time AND runtime? (Zod schemas)",
        "How to prevent SQL injection in AI-accessible database tools? (SELECT-only guard)",
        "How to switch database backends without changing tool code? (Strategy pattern)",
        "How to build AI infrastructure in TypeScript? (Polyglot demonstration)",
    ]
    for q in questions:
        pdf.bullet(q)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


# ---------------------------------------------------------------------------
# PDF 5: AI Multi-Agent — Project Deep Dive
# ---------------------------------------------------------------------------
def create_ai_multi_agent_pdf(output_path: Path) -> None:
    pdf = PortfolioPDF(
        title="AI Multi-Agent System",
        subtitle="CrewAI Orchestration with WebSocket Events & React Frontend",
    )
    pdf.cover_page()

    # --- Overview ---
    pdf.add_page()
    pdf.section_title("Project Overview")
    pdf.body_text(
        "A multi-agent orchestration system built on CrewAI where specialized AI agents "
        "(researcher, analyst, writer, critic) collaborate on complex tasks. Supports sequential "
        "and hierarchical crew modes, real-time WebSocket event streaming, task persistence, "
        "and a Next.js React frontend for live visualization."
    )
    pdf.ln(2)
    pdf.key_value("Architecture", "Multi-Agent Orchestration (CrewAI)")
    pdf.key_value("Backend", "Python 3.12 + FastAPI + Pydantic v2")
    pdf.key_value("Frontend", "Next.js 14 + React + Tailwind CSS")
    pdf.key_value("Core Tech", "CrewAI, WebSocket, Redis (pub/sub)")
    pdf.key_value("Infrastructure", "Terraform (AWS + Azure) + Docker + CI/CD")
    pdf.key_value("Port", "8400 (backend), 3000 (frontend)")

    # --- Architecture ---
    pdf.section_title("Architecture — Multi-Agent Orchestration")
    pdf.body_text(
        "Tasks are submitted via REST API, executed asynchronously by a CrewAI crew, "
        "with progress streamed via WebSocket. The crew consists of 4 specialized agents "
        "that collaborate in sequential or hierarchical mode."
    )
    pdf.table(
        headers=["Component", "Technology", "Purpose"],
        rows=[
            ["Agent Definitions", "CrewAI Agent", "4 roles: researcher, analyst, writer, critic"],
            ["Crew Orchestrator", "CrewAI Crew", "Sequential + hierarchical execution modes"],
            ["WebSocket Manager", "FastAPI WebSocket", "Real-time agent event broadcasting"],
            ["Task Store", "Strategy pattern", "InMemory (dev) or PostgreSQL (prod)"],
            ["LLM Provider", "Strategy pattern", "Ollama / Bedrock / Azure OpenAI"],
            ["Frontend", "Next.js React", "Live agent activity feed + task management"],
        ],
        col_widths=[30, 45, 90],
    )

    # --- Features ---
    pdf.section_title("Key Features")
    features = [
        "4 specialized agents: researcher, analyst, writer, critic — each with role/goal/backstory",
        "Sequential mode: agents execute in order, each building on previous output",
        "Hierarchical mode: manager agent delegates subtasks to workers",
        "WebSocket streaming: 6 event types (agent_start, thought, tool_call, agent_complete, task_complete, error)",
        "Async task execution: submit via REST, get 202 Accepted, poll or WebSocket for updates",
        "Task persistence: InMemory (dev) or PostgreSQL (prod) via Strategy pattern",
        "Redis pub/sub: enables horizontal scaling of WebSocket connections",
        "Next.js frontend: task form, live agent feed, result display",
        "Provider switching: same crew code works with Ollama, Bedrock, or Azure OpenAI",
        "Full Docker Compose stack: backend + frontend + Redis in one command",
    ]
    for f in features:
        pdf.bullet(f)

    # --- Lab Results ---
    pdf.add_page()
    pdf.section_title("Hands-On Lab Results")

    pdf.subsection("Lab 1: First CrewAI Crew")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Sequential crew executes", "PASS", "Researcher -> Writer, output passed via context"],
            ["Both agents produce output", "PASS", "Research report + blog post"],
            ["Verbose logging shows reasoning", "PASS", "Each agent's thought process visible"],
        ],
        col_widths=[45, 25, 95],
    )

    pdf.subsection("Lab 2: Hierarchical Crew")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Manager delegates tasks", "PASS", "Manager assigns research + analysis subtasks"],
            ["Workers execute independently", "PASS", "Each worker produces separate output"],
            ["Manager synthesizes results", "PASS", "Final report combines all worker outputs"],
        ],
        col_widths=[45, 25, 95],
    )

    pdf.subsection("Lab 3-4: Provider Switching & Task Persistence")
    pdf.table(
        headers=["Check", "Result", "Notes"],
        rows=[
            ["Strategy pattern selects provider", "PASS", "CLOUD_PROVIDER env var controls selection"],
            ["Same crew code, different LLM", "PASS", "No code changes between providers"],
            ["Task CRUD operations", "PASS", "Create, read, update status, list all"],
            ["Status transitions", "PASS", "PENDING -> RUNNING -> COMPLETED"],
        ],
        col_widths=[45, 25, 95],
    )

    pdf.subsection("Labs 5-8: WebSocket, REST API, Frontend, Docker")
    pdf.table(
        headers=["Lab", "Key Finding"],
        rows=[
            ["5: WebSocket", "6 event types streamed, color-coded by agent role"],
            ["6: REST API", "Full CRUD on tasks, 202 Accepted for async submission"],
            ["7: Frontend", "Live agent feed updates in real-time, task form + result display"],
            ["8: Docker", "3-service stack (backend + frontend + redis), all integrations verified"],
        ],
        col_widths=[30, 135],
    )

    # --- Infrastructure ---
    pdf.section_title("Infrastructure (Terraform)")
    pdf.table(
        headers=["AWS Resource", "Azure Equivalent", "Purpose"],
        rows=[
            ["ECS Fargate", "Container Apps", "Run backend container"],
            ["ElastiCache Redis", "Azure Cache for Redis", "WebSocket pub/sub + caching"],
            ["ECR", "ACR", "Docker image registry"],
            ["IAM (Bedrock access)", "Managed Identity", "LLM provider auth"],
            ["CloudWatch", "Log Analytics", "Centralized logging"],
        ],
        col_widths=[40, 50, 75],
    )
    pdf.body_text(
        "Terraform follows distributed pattern: terraform.tf, variables.tf, outputs.tf, "
        "ecr.tf, ecs.tf, elasticache.tf, networking.tf, iam.tf, cloudwatch.tf. "
        "Redis is a hard dependency (WebSocket pub/sub for horizontal scaling)."
    )

    # --- Business Value ---
    pdf.section_title("Business Questions This Project Answers")
    questions = [
        "How to decompose complex tasks across specialized AI agents? (CrewAI roles)",
        "How to show users real-time progress during long-running AI tasks? (WebSocket)",
        "How to let a manager agent coordinate worker agents? (Hierarchical mode)",
        "How to persist async task results for later retrieval? (Task store pattern)",
        "How to scale WebSocket connections horizontally? (Redis pub/sub)",
        "How to build a full-stack AI application with React frontend? (Next.js + FastAPI)",
        "How does multi-agent orchestration compare to single-agent? (CrewAI vs LangGraph)",
    ]
    for q in questions:
        pdf.bullet(q)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


# ---------------------------------------------------------------------------
# PDF 6: AI Portfolio Overview (all 5 phases)
# ---------------------------------------------------------------------------
def create_portfolio_overview_pdf(output_path: Path) -> None:
    pdf = PortfolioPDF(
        title="AI Engineering Portfolio",
        subtitle="5-Phase Journey: Building Production-Grade AI Competency",
    )
    pdf.cover_page()

    # ── Page 2: Vision & Background ──
    pdf.add_page()
    pdf.section_title("Portfolio Vision")
    pdf.body_text(
        "This portfolio documents a structured 5-phase journey from Data Engineer to AI Engineer. "
        "Each phase delivers a production-grade repository with a distinct architecture pattern, "
        "a new technology stack, hands-on labs with measured results, and dual-cloud Terraform infrastructure. "
        "By Phase 5, the five repos integrate into a complete AI platform — demonstrating that "
        "AI engineering is not magic, but disciplined software engineering applied to intelligent systems."
    )
    pdf.ln(2)
    pdf.body_text(
        "Background: Data Engineer with 5+ years experience in Python, Terraform, AWS, and Azure. "
        "This portfolio proves that data engineering principles — schema validation, pipeline testing, IaC, "
        "observability, cost governance — transfer directly to AI systems and give a DE-turned-AI-engineer "
        "a unique advantage over developers who only know the AI frameworks."
    )
    pdf.ln(4)
    pdf.key_value("Total Repos", "5 interconnected projects (4 Python, 1 TypeScript)")
    pdf.key_value("Total Labs", "40 hands-on labs (8 per repo) with pass/fail results")
    pdf.key_value("Cloud Providers", "AWS + Azure + Local (every repo)")
    pdf.key_value("IaC", "Terraform (distributed pattern) for all cloud resources")
    pdf.key_value("CI/CD", "GitHub Actions (ci.yml + deploy-aws.yml + deploy-azure.yml per repo)")

    # ── The 5-Phase Journey ──
    pdf.section_title("The 5-Phase Journey")
    pdf.table(
        headers=["Phase", "Repo", "Pattern", "Core Tech", "Port"],
        rows=[
            ["1", "rag-chatbot", "RAG Pipeline + Strategy Pattern", "FastAPI, ChromaDB, Bedrock", "8000"],
            ["2", "ai-gateway", "LLM Proxy / API Gateway", "LiteLLM, Redis, PostgreSQL", "8100"],
            ["3", "ai-agent", "ReAct Agent (Graph FSM)", "LangGraph, Tool Registry", "8200"],
            ["4", "mcp-server", "MCP Protocol Server", "TypeScript, MCP SDK, Zod", "8300"],
            ["5", "ai-multi-agent", "Multi-Agent Orchestration", "CrewAI, WebSocket, Next.js", "8400"],
        ],
        col_widths=[16, 30, 42, 44, 16],
    )

    # ── Phase Summaries ──
    pdf.add_page()
    pdf.section_title("Phase 1 — RAG Chatbot")
    pdf.body_text(
        "Production-grade RAG chatbot with cloud-agnostic Strategy Pattern. "
        "A single env var switches between AWS (Bedrock + OpenSearch), Azure (OpenAI + AI Search), "
        "and Local (Ollama + ChromaDB). Includes guardrails, re-ranking, hybrid search, "
        "an evaluation framework, and 11 hands-on labs with measured results."
    )
    pdf.key_value("Architecture", "RAG pipeline: ingest -> chunk -> embed -> store -> retrieve -> generate")
    pdf.key_value("Key Learning", "Vector stores, embedding models, retrieval strategies, LLM evaluation")
    pdf.key_value("Labs Highlight", "Score improved from 0.46 to 0.87 across 6 iterative labs")

    pdf.section_title("Phase 2 — AI Gateway")
    pdf.body_text(
        "Centralised LLM proxy that all AI applications route through. "
        "Provides model routing via LiteLLM, two-tier semantic caching (exact + cosine similarity), "
        "per-key rate limiting, cost tracking dashboard, and request tracing."
    )
    pdf.key_value("Architecture", "Auth -> Rate Limit -> Cache -> Router -> Provider -> Cache Store -> Cost Log")
    pdf.key_value("Key Learning", "LLM routing, semantic caching (latency: 1500ms -> 5ms), cost governance")
    pdf.key_value("Labs Highlight", "Cache reduces latency by 99.7%, rate limiter returns 429 with Retry-After")

    pdf.section_title("Phase 3 — AI Agent")
    pdf.body_text(
        "Autonomous AI agent built on LangGraph that reasons, uses tools, and maintains "
        "conversation history. ReAct pattern with max_iterations guard. "
        "Three tools: calculator, database query, web search."
    )
    pdf.key_value("Architecture", "StateGraph: agent_node -> should_continue? -> tools_node -> loop")
    pdf.key_value("Key Learning", "ReAct pattern, tool registries, conversation persistence, SSE streaming")
    pdf.key_value("Labs Highlight", "Multi-tool chains (DB + calculator) in a single query, iterations > 1")

    pdf.add_page()
    pdf.section_title("Phase 4 — MCP Server")
    pdf.body_text(
        "TypeScript MCP server exposing tools and resources via Anthropic's open standard. "
        "Dual transport: stdio for Claude Desktop, SSE for remote deployment. "
        "5 tools, 3 resources, Strategy-pattern database provider."
    )
    pdf.key_value("Architecture", "MCP Protocol: tool registration, Zod validation, stdio + SSE transport")
    pdf.key_value("Key Learning", "MCP protocol, TypeScript/Zod, polyglot engineering, SQL injection prevention")
    pdf.key_value("Labs Highlight", "Claude Desktop native integration, SQL injection blocked at validation layer")

    pdf.section_title("Phase 5 — AI Multi-Agent System")
    pdf.body_text(
        "Capstone: multiple specialised agents (researcher, analyst, writer, critic) "
        "collaborating via CrewAI. Sequential + hierarchical modes, WebSocket event streaming, "
        "task persistence, and a Next.js React frontend."
    )
    pdf.key_value("Architecture", "CrewAI crew -> async execution -> WebSocket broadcast -> React frontend")
    pdf.key_value("Key Learning", "Multi-agent orchestration, WebSocket, full-stack AI, Redis pub/sub")
    pdf.key_value("Labs Highlight", "Manager agent delegates + synthesises, live agent feed in browser")

    # ── How Repos Connect ──
    pdf.section_title("How the 5 Repos Connect")
    pdf.body_text(
        "Phase 5 is the capstone that integrates all previous phases into one platform:"
    )
    pdf.table(
        headers=["Repo", "Role in the Platform"],
        rows=[
            ["rag-chatbot (Phase 1)", "A tool that agents call for document Q&A"],
            ["ai-gateway (Phase 2)", "Central LLM proxy — all repos route LLM calls through it"],
            ["ai-agent (Phase 3)", "Individual agents that make up the multi-agent crew"],
            ["mcp-server (Phase 4)", "Standardised tool provider for database/file access"],
            ["ai-multi-agent (Phase 5)", "Orchestrator combining everything + Next.js UI"],
        ],
        col_widths=[40, 125],
    )

    # ── AI Competency & Skills Built ──
    pdf.add_page()
    pdf.section_title("AI Competency Built Through This Portfolio")
    pdf.body_text(
        "Each phase deliberately targets specific AI engineering competencies. "
        "The progression is designed so that skills from earlier phases compound in later ones. "
        "By the end, the full spectrum of production AI engineering is demonstrated."
    )

    pdf.subsection("Competency 1: LLM Integration & Provider Abstraction")
    pdf.body_text(
        "Every phase uses the Strategy Pattern to abstract LLM providers. "
        "One env var switches between Ollama (local), AWS Bedrock, and Azure OpenAI. "
        "This is not a toy abstraction — it's how production multi-cloud systems work."
    )
    pdf.table(
        headers=["Phase", "Skill Demonstrated"],
        rows=[
            ["1: RAG Chatbot", "Factory method creates provider from CLOUD_PROVIDER env var"],
            ["2: AI Gateway", "LiteLLM routes to 100+ providers via unified API"],
            ["3: AI Agent", "LangGraph agent receives BaseChatModel — provider-agnostic"],
            ["5: Multi-Agent", "CrewAI crew code identical across providers"],
        ],
        col_widths=[30, 135],
    )

    pdf.subsection("Competency 2: Retrieval-Augmented Generation (RAG)")
    pdf.body_text(
        "Phase 1 builds deep RAG expertise: chunking strategies, embedding models, vector stores, "
        "retrieval scoring, hybrid search (BM25 + vector with RRF), re-ranking, guardrails, "
        "and an evaluation framework that improved scores from 0.46 to 0.87."
    )

    pdf.subsection("Competency 3: AI Agent Design Patterns")
    pdf.body_text(
        "Phase 3 teaches the ReAct pattern (Reason + Act), tool registries, conversation "
        "persistence, SSE streaming, and iteration guards. Phase 5 extends this to multi-agent "
        "orchestration with CrewAI — sequential vs hierarchical, manager delegation, "
        "and WebSocket event streaming."
    )

    pdf.subsection("Competency 4: AI Infrastructure & DevOps")
    pdf.body_text(
        "Every repo includes production Terraform for AWS and Azure, Docker Compose, "
        "and GitHub Actions CI/CD. This demonstrates that AI systems need the same "
        "infrastructure discipline as traditional software."
    )
    pdf.table(
        headers=["Skill", "Where Demonstrated"],
        rows=[
            ["Terraform (AWS + Azure)", "All 5 repos — distributed .tf pattern"],
            ["Docker / Docker Compose", "All 5 repos — multi-service stacks"],
            ["GitHub Actions CI/CD", "3 workflows per repo (ci, deploy-aws, deploy-azure)"],
            ["ECS Fargate / Container Apps", "All repos deployed as containers"],
            ["Redis / ElastiCache", "Phase 2 (cache), Phase 5 (WebSocket pub/sub)"],
            ["PostgreSQL / RDS", "Phase 2 (cost tracking), Phase 4 (tool data)"],
        ],
        col_widths=[45, 120],
    )

    pdf.add_page()
    pdf.subsection("Competency 5: Protocol & API Design")
    pdf.body_text(
        "The portfolio covers REST APIs (all phases), SSE streaming (Phases 3-4), "
        "WebSocket (Phase 5), and the MCP protocol (Phase 4). Each protocol choice "
        "is justified by use case — not just framework defaults."
    )
    pdf.table(
        headers=["Protocol", "Phase", "Why This Protocol"],
        rows=[
            ["REST (JSON)", "All", "Standard request/response for CRUD operations"],
            ["SSE", "3, 4", "Server-to-client token streaming, simpler than WebSocket"],
            ["WebSocket", "5", "Bidirectional: client can cancel tasks, agent events push live"],
            ["MCP (stdio)", "4", "Claude Desktop integration, zero-network local tool access"],
            ["MCP (SSE)", "4", "Remote tool access for Docker/cloud deployments"],
        ],
        col_widths=[30, 20, 115],
    )

    pdf.subsection("Competency 6: Testing & Evaluation")
    pdf.body_text(
        "Every repo has a comprehensive test suite. AI-specific testing goes beyond unit tests: "
        "RAG evaluation with rule-based scoring, LLM response quality metrics, "
        "guardrail bypass testing, and automated lab runners."
    )
    pdf.table(
        headers=["Testing Type", "Where"],
        rows=[
            ["Unit tests (pytest/Vitest)", "All 5 repos"],
            ["RAG evaluation framework", "Phase 1 — rule-based scoring on retrieval + generation"],
            ["Guardrail testing", "Phase 1 — prompt injection, PII redaction"],
            ["Integration tests (TestClient)", "Phases 1-3, 5"],
            ["Automated lab runners", "All 4 new repos — scripts/run_all_labs.py"],
        ],
        col_widths=[45, 120],
    )

    pdf.subsection("Competency 7: Polyglot Engineering")
    pdf.body_text(
        "Phases 1-3 and 5 use Python. Phase 4 switches to TypeScript — demonstrating "
        "the ability to learn and apply a new language/ecosystem (npm, Zod, Vitest) "
        "while maintaining the same architectural standards (Strategy pattern, distributed Terraform, CI/CD)."
    )

    # ── Skills Progression Matrix ──
    pdf.add_page()
    pdf.section_title("Skills Progression Matrix")
    pdf.body_text(
        "This matrix shows how each phase builds on previous skills while adding new ones. "
        "The cumulative effect is a comprehensive AI engineering skill set."
    )
    pdf.table(
        headers=["Skill", "Ph 1", "Ph 2", "Ph 3", "Ph 4", "Ph 5"],
        rows=[
            ["Python / FastAPI", "NEW", "USE", "USE", "-", "USE"],
            ["TypeScript / Node.js", "-", "-", "-", "NEW", "USE"],
            ["Pydantic / Zod validation", "NEW", "USE", "USE", "NEW", "USE"],
            ["Strategy Pattern", "NEW", "USE", "USE", "USE", "USE"],
            ["RAG pipeline", "NEW", "-", "-", "-", "-"],
            ["LLM caching", "-", "NEW", "-", "-", "-"],
            ["Rate limiting", "-", "NEW", "-", "-", "-"],
            ["LangGraph (agent FSM)", "-", "-", "NEW", "-", "-"],
            ["Tool registries", "-", "-", "NEW", "USE", "USE"],
            ["MCP protocol", "-", "-", "-", "NEW", "-"],
            ["Multi-agent (CrewAI)", "-", "-", "-", "-", "NEW"],
            ["SSE streaming", "-", "-", "NEW", "USE", "-"],
            ["WebSocket", "-", "-", "-", "-", "NEW"],
            ["React / Next.js", "-", "-", "-", "-", "NEW"],
            ["Terraform (AWS)", "NEW", "USE", "USE", "USE", "USE"],
            ["Terraform (Azure)", "NEW", "USE", "USE", "USE", "USE"],
            ["Docker Compose", "NEW", "USE", "USE", "USE", "USE"],
            ["GitHub Actions CI/CD", "NEW", "USE", "USE", "USE", "USE"],
            ["Redis", "-", "NEW", "-", "-", "USE"],
            ["PostgreSQL", "-", "NEW", "-", "USE", "-"],
        ],
        col_widths=[40, 20, 20, 20, 20, 20],
    )
    pdf.ln(2)
    pdf.body_text("NEW = learned in this phase | USE = applied from earlier phase | - = not used")

    # ── DE to AI Bridge ──
    pdf.add_page()
    pdf.section_title("Data Engineering to AI Engineering")
    pdf.body_text(
        "The strongest differentiator: applying data engineering discipline to AI systems. "
        "Most AI tutorials skip infrastructure, testing, and cost governance. "
        "This portfolio proves that DE principles are not just transferable — they're essential."
    )
    pdf.table(
        headers=["DE Principle", "AI Application", "Portfolio Example"],
        rows=[
            ["Schema validation", "Input guardrails", "Prompt injection detection (Phase 1, Lab 9)"],
            ["Data masking", "PII redaction", "Email/SSN redaction (Phase 1, Lab 9b)"],
            ["Pipeline testing", "RAG evaluation", "Rule-based scoring: 0.46 -> 0.87 (Phase 1)"],
            ["IaC (Terraform)", "AI infra provisioning", "All 5 repos: AWS + Azure Terraform"],
            ["Cost monitoring", "LLM cost tracking", "Per-model/key/day dashboard (Phase 2)"],
            ["Rate limiting", "LLM quota protection", "Per-key throttling with 429 (Phase 2)"],
            ["Data flywheel", "Feedback loop", "Iterative RAG improvement (Phase 1, Labs 1-6)"],
            ["UNION ALL + ranking", "Hybrid search (RRF)", "BM25 + vector fusion (Phase 1, Lab 11)"],
            ["Event streaming", "Agent events", "WebSocket broadcast (Phase 5)"],
            ["CI/CD pipelines", "AI deployment", "3 workflows per repo (all phases)"],
        ],
        col_widths=[35, 40, 90],
    )

    # ── Technology Stack ──
    pdf.section_title("Complete Technology Stack")
    pdf.table(
        headers=["Category", "Technologies"],
        rows=[
            ["Languages", "Python 3.12, TypeScript 5.x"],
            ["Web Frameworks", "FastAPI (Python), Next.js 14 (React + TypeScript)"],
            ["AI/ML Frameworks", "LangChain, LangGraph, CrewAI, LiteLLM"],
            ["LLM Providers", "AWS Bedrock, Azure OpenAI, Ollama (local)"],
            ["Vector Stores", "OpenSearch, Azure AI Search, ChromaDB"],
            ["Databases", "PostgreSQL, Redis, SQLite, DynamoDB, Cosmos DB"],
            ["Protocols", "REST, SSE, WebSocket, MCP (stdio + SSE)"],
            ["Infrastructure", "Terraform, Docker, GitHub Actions"],
            ["Cloud (AWS)", "ECS, ECR, ElastiCache, RDS, CloudWatch, IAM, VPC, ALB"],
            ["Cloud (Azure)", "Container Apps, ACR, Redis Cache, PostgreSQL, Log Analytics"],
            ["Testing", "pytest, Vitest, moto, FastAPI TestClient, automated lab runners"],
            ["Observability", "CloudWatch, Log Analytics, X-Request-ID tracing"],
        ],
        col_widths=[35, 130],
    )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))
    print(f"  Created: {output_path}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    base = Path("Path.home() / "projects" / "ai-portfolio" / "personal" / "career"")

    print("Generating portfolio PDFs...")
    create_rag_chatbot_pdf(base / "rag-chatbot-portfolio.pdf")
    create_ai_gateway_pdf(base / "ai-gateway-portfolio.pdf")
    create_ai_agent_pdf(base / "ai-agent-portfolio.pdf")
    create_mcp_server_pdf(base / "mcp-server-portfolio.pdf")
    create_ai_multi_agent_pdf(base / "ai-multi-agent-portfolio.pdf")
    create_portfolio_overview_pdf(base / "ai-portfolio-overview.pdf")
    print("Done!")


if __name__ == "__main__":
    main()
