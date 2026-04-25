# 📚 Documentation Reading Order

> A guided path through the rag-chatbot documentation. Start at Level 1 and work your way down.

---

## Level 1 — Start Here (The Big Picture)

Read these first to understand what this project is and how it works.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 1 | [README.md](../README.md) | Project overview, features, tech stack, quick start | The stable notice board — what the donkey does, what tools it carries, how to get it started in 60 seconds |
| 2 | [RAG Concepts](ai-engineering/rag-concepts.md) | What is RAG? Embeddings, vector search, retrieval — explained simply | The donkey's training manual — why it checks the backpack instead of answering from memory |
| 3 | [Architecture Overview](architecture-and-design/architecture.md) | System diagram, component relationships, data flow | The delivery route map — all roads, stops, and handoffs from question to answer |

---

## Level 2 — Setup & Run It

Now get the project running on your machine.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 4 | [Getting Started](setup-and-tooling/getting-started.md) | Install dependencies, configure .env, run locally | load up the donkey — install the gear, fill the backpack, send it on the first test run |
| 5 | [Poetry Guide](setup-and-tooling/poetry-guide.md) | Python dependency management with Poetry | How to stock the supply shed — every tool and library the donkey needs, pinned and reproducible |
| 6 | [Debugging Guide](setup-and-tooling/debugging-guide.md) | Common errors and how to fix them | What to do when the donkey trips — common falls and how to get it back on the road |

---

## Level 3 — Understand the Code (Core Pipeline)

Deep dives into each component of the RAG pipeline, in data-flow order.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 7 | [Ingestion Pipeline](ai-engineering/ingestion-pipeline-deep-dive.md) | How documents are chunked, embedded, and stored | The post office pre-sorting the mail — cut into bags, GPS-labelled, shelved before the donkey arrives |
| 8 | [Vector Store Interface](ai-engineering/vectorstore-interface-deep-dive.md) | The abstract vector store contract | The warehouse door rules — any warehouse that follows this contract can work with the donkey |
| 9 | [Vector Store Providers](ai-engineering/vectorstore-providers-deep-dive.md) | ChromaDB (local), DynamoDB (AWS), Azure AI Search — how each works | Three warehouses the donkey can use — local barn (ChromaDB), AWS depot (DynamoDB), Azure hub (AI Search) |
| 10 | [RAG Chain](ai-engineering/rag-chain-deep-dive.md) | The orchestrator: retrieval → reranking → LLM → response | The donkey's full delivery run — retrieve bags → rerank by relevance → load backpack → write the answer |
| 11 | [LLM Interface](ai-engineering/llm-interface-deep-dive.md) | The abstract LLM contract | The writing desk rules — any LLM that follows this contract can sit at the donkey's desk |
| 12 | [LLM Providers](ai-engineering/llm-providers-deep-dive.md) | Ollama (local), Bedrock (AWS), Azure OpenAI — how each works | Three writers at the desk — local llama, AWS Claude, Azure GPT — same contract, different handwriting |
| 13 | [Prompts](ai-engineering/prompts-deep-dive.md) | System prompts, RAG prompt templates, prompt engineering | The delivery note template — standing orders + cargo manifest + customer request, formatted perfectly |

---

## Level 4 — Understand the API

How the FastAPI server exposes the RAG pipeline.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 14 | [API Routes Overview](architecture-and-design/api-routes-explained.md) | All endpoints at a glance | The stable's front door signs — all entry points, what goes in, what comes out |
| 15 | [Chat Endpoint](architecture-and-design/api-routes/chat-endpoint-explained.md) | The main RAG endpoint — query → answer | The main delivery window — hand in a question, the donkey brings back a grounded answer |
| 16 | [Documents Endpoint](architecture-and-design/api-routes/documents-endpoint-explained.md) | Upload, list, delete documents | The intake desk — drop off new documents, check what's in stock, remove old ones |
| 17 | [Evaluate Endpoint](architecture-and-design/api-routes/evaluate-endpoint-explained.md) | Run evaluation suites via API | The quality inspector's window — trigger scoring runs without touching the code |
| 18 | [Health Endpoint](architecture-and-design/api-routes/health-endpoint-explained.md) | Health checks and readiness | The stable health check — is the donkey awake, loaded up, and ready to run? |
| 19 | [Metrics Endpoint](architecture-and-design/api-routes/metrics-endpoint-explained.md) | Prometheus metrics | The donkey's logbook — Prometheus reads delivery counts, latencies, and costs |
| 20 | [Queries Endpoint](architecture-and-design/api-routes/queries-endpoint-explained.md) | Query history and stats | The trip history board — every question the donkey has answered, with scores |
| 21 | [Pydantic Models](reference/pydantic-models.md) | Request/response schemas | The parcel size rules — the exact shape every request and response must fit before the donkey touches it |
| 22 | [API Reference](reference/api-reference.md) | Full API spec | The full catalogue of doors — every endpoint, every field, every status code |

---

## Level 5 — Cloud Infrastructure

How the project deploys to AWS and Azure.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 23 | [How Services Work](architecture-and-design/how-services-work.md) | Service integration patterns | How the donkey coordinates with all the stables across the network — handshakes and contracts |
| 24 | [AWS Services](architecture-and-design/aws-services.md) | DynamoDB, S3, Bedrock, IAM — AWS-specific setup | The AWS stable — DynamoDB shelf, S3 barn, Bedrock writer, IAM gate that controls who enters |
| 25 | [Azure Services](architecture-and-design/azure-services.md) | Cosmos DB, Blob Storage, Azure OpenAI — Azure-specific setup | The Azure stable — Cosmos shelf, Blob barn, Azure OpenAI writer, same donkey different postcode |
| 26 | [Infrastructure (Terraform)](architecture-and-design/infra-explained.md) | Terraform modules for AWS and Azure | The blueprints for building the stable — run one command, the whole building appears |
| 27 | [Terraform Guide](setup-and-tooling/terraform-guide.md) | How to run terraform apply/destroy | How to use the blueprints — build it, inspect it, tear it down safely |
| 28 | [Storage Explained](architecture-and-design/storage-explained.md) | Vector stores, document stores, conversation history | Where the donkey parks packages overnight — vector shelf, document barn, trip log |
| 29 | [CI/CD](architecture-and-design/cicd-explained.md) | GitHub Actions pipeline | The robot stable hand — tests and redeploys the donkey automatically on every code push |

---

## Level 6 — Evaluation & Testing

How to measure quality and run the 58-experiment lab suite.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 30 | [Evaluation Framework](ai-engineering/evaluation-framework-deep-dive.md) | Retrieval, faithfulness, answer relevance — how scoring works | The donkey's report card — did it grab the right bags? Was the answer faithful to the contents? |
| 31 | [Metrics Deep Dive](ai-engineering/metrics-deep-dive.md) | Prometheus metrics, latency tracking, cost tracking | The tachograph — every delivery time, token cost, and quality score recorded and graphed |
| 32 | [Golden Dataset](ai-engineering/golden-dataset-deep-dive.md) | The 25-question benchmark suite | The 25 standard test deliveries — the benchmark every donkey run must pass before going to production |
| 33 | [Testing](ai-engineering/testing.md) | Unit tests, integration tests, evaluation tests | Quality gates before every delivery — unit checks per component, full-run integration, and scoring tests |
| 34 | [Cost Analysis](ai-engineering/cost-analysis.md) | Token costs per provider, budget tracking | How much each trip costs in tokens — per provider, per query, with monthly budget projections |
| 35 | [Monitoring](reference/monitoring.md) | Prometheus + Grafana setup | The CCTV and dashboards — Prometheus counts every move, Grafana shows it on a live screen |

---

## Level 7 — Hands-On Labs (Do the Exercises)

Run all 58 experiments yourself — follow Phase 1 → 5 in order.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 36 | [Phase 1 — Foundation](hands-on-labs/hands-on-labs-phase-1.md) | Basic queries, top_k tuning, first evaluation | First solo trips — basic deliveries, tune the backpack size, read the first report card |
| 37 | [Phase 2 — Bridge Skills](hands-on-labs/hands-on-labs-phase-2.md) | Multi-turn, injection tests, tracing, dashboards | Advanced trips — multi-leg journeys, injection attack tests, live GPS tracking on the dashboard |
| 38 | [Phase 3 — Production AI](hands-on-labs/hands-on-labs-phase-3.md) | Document upload, golden dataset, guardrails | Real-world runs — upload your own docs, run the 25-question benchmark, add safety guardrails |
| 39 | [Phase 4 — Advanced RAG](hands-on-labs/hands-on-labs-phase-4.md) | Query types, reranking, multi-doc, HNSW indexing | Expert tricks — rerank packages by quality, handle multi-doc loads, tune the HNSW stadium signs |
| 40 | [Phase 5 — Full Suite](hands-on-labs/hands-on-labs-phase-5.md) | Run all 25 golden questions + edge cases | The final exam — all 25 golden deliveries plus edge cases, one complete run to prove the system works |

---

## Level 8 — Results & Comparison (Read Last)

After running the labs, read the results to see how Local, Azure, and AWS compare.

| # | Document | What you'll learn | 🫏 Donkey |
|---|----------|-------------------|-----------|
| 41 | [AWS Cloud Labs Results](aws-cloud-labs-results.md) | 4 AWS runs, root causes, fixes, donkey analogy | The AWS trip report — 4 runs, what broke, what was fixed, full donkey post-mortem included |
| 42 | [3-Way Comparison](../scripts/lab_results/local-vs-azure-comparison.md) | Local vs Azure vs AWS — head-to-head on all 40 experiments | Three stables, one race — local barn vs Azure vs AWS across all 40 experiments, winner per metric |
| 43 | [History Explained](architecture-and-design/history-explained.md) | Conversation history and session management | The donkey's memory between trips — how it remembers what you said 3 questions ago without losing the thread |

---

## Quick Reference

- **"I want to run it"** → Start at doc #4 (Getting Started)
- **"I want to understand RAG"** → Start at doc #2 (RAG Concepts)
- **"I want to see results"** → Jump to doc #41 (AWS Results) and #42 (3-Way Comparison)
- **"I want to deploy to AWS"** → Read docs #24–27
- **"I want to run the labs"** → Read docs #36–40
