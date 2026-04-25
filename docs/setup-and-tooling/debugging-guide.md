# Debugging Guide — VS Code & PyCharm

## Table of Contents

- [Why debugging matters for this project](#why-debugging-matters-for-this-project)
- [VS Code Debugger Setup](#vs-code-debugger-setup)
  - [Step 1: Open the project in VS Code](#step-1-open-the-project-in-vs-code)
  - [Step 2: Select the Python interpreter](#step-2-select-the-python-interpreter)
  - [Step 3: Load your .env file](#step-3-load-your-env-file)
  - [Step 4: Open the Run and Debug panel](#step-4-open-the-run-and-debug-panel)
  - [Step 5: Pick a debug configuration](#step-5-pick-a-debug-configuration)
  - [Step 6: Set breakpoints](#step-6-set-breakpoints)
  - [Step 7: Start debugging](#step-7-start-debugging)
  - [Step 8: Send a request while debugging](#step-8-send-a-request-while-debugging)
  - [Step 9: Inspect variables when breakpoint hits](#step-9-inspect-variables-when-breakpoint-hits)
- [PyCharm Debugger Setup](#pycharm-debugger-setup)
  - [Step 1: Open the project in PyCharm](#step-1-open-the-project-in-pycharm)
  - [Step 2: Configure the Python interpreter](#step-2-configure-the-python-interpreter)
  - [Step 3: Create a Run Configuration](#step-3-create-a-run-configuration)
  - [Step 4: Set breakpoints](#step-4-set-breakpoints)
  - [Step 5: Start debugging](#step-5-start-debugging)
- [Debugger quick reference](#debugger-quick-reference)
- [What to debug in this project](#what-to-debug-in-this-project)
- [Common debugging scenarios](#common-debugging-scenarios)

---

## Why debugging matters for this project

This project has many moving parts:
- FastAPI receives a request
- Middleware logs it
- The route handler processes it
- The RAG chain coordinates retrieval + generation
- The LLM client talks to AWS/Azure
- The vector store does similarity search

When something goes wrong, `print()` statements won't cut it. You need to:
- **Stop execution at a specific line** (breakpoint)
- **Inspect variables** (what does this dict actually contain?)
- **Step through code line by line** (follow the exact flow)
- **Evaluate expressions** (what would `result.score > 0.8` return?)

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

## VS Code Debugger Setup

### Step 1: Open the project in VS Code

```bash
code <project-root>/rag-chatbot
```

Or: File → Open Folder → select `rag-chatbot/`

### Step 2: Select the Python interpreter

1. Press `Ctrl+Shift+P` (Command Palette)
2. Type: `Python: Select Interpreter`
3. Choose: `('.venv': venv) ./venv/bin/python`

If you don't see it:
- Make sure you ran `poetry install` first
- Make sure `poetry config virtualenvs.in-project true` was set
- Click "Enter interpreter path" and type: `<project-root>/rag-chatbot/.venv/bin/python`

### Step 3: Load your .env file

The debug configuration (`.vscode/launch.json`) already includes:

```json
"envFile": "${workspaceFolder}/.env"
```

This means VS Code will automatically load your `.env` file when debugging. You don't need to run `source .env` manually.

### Step 4: Open the Run and Debug panel

Click the play icon with a bug in the left sidebar (or press `Ctrl+Shift+D`).

### Step 5: Pick a debug configuration

In the dropdown at the top, you'll see three options:

| Configuration | What it does | 🫏 Donkey |
| --- | --- | --- |
| **RAG Chatbot — Debug Server** | Starts the FastAPI server with debugger attached. Use this for testing endpoints. | Saddlebag check 🫏 |
| **RAG Chatbot — Debug Tests** | Runs all pytest tests with debugger. Use this when a test fails and you want to step through it. | Saddlebag check 🫏 |
| **RAG Chatbot — Debug Single Test File** | Runs only the currently open test file. Fastest for debugging one test. | Saddlebag check 🫏 |

### Step 6: Set breakpoints

Click in the **gutter** (the space to the left of line numbers) to set a red dot.

**Recommended breakpoints for understanding the flow:**

| File | Line | Why | 🫏 Donkey |
| --- | --- | --- | --- |
| `src/main.py` | Line inside `lifespan()` | See what happens at startup | 🫏 On the route |
| `src/api/routes/chat.py` | First line of `chat()` | See every incoming chat request | Stable door 🚪 |
| `src/rag/chain.py` | Inside `query()` | See RAG retrieval + generation | Saddlebag check 🫏 |
| `src/llm/aws_bedrock.py` | Inside `generate()` | See the Bedrock API call | The donkey 🐴 |
| `src/llm/azure_openai.py` | Inside `generate()` | See the Azure OpenAI API call | The donkey 🐴 |
| `src/vectorstore/base.py` | Inside `search()` | See vector search results | GPS warehouse 🗺️ |
| `src/rag/ingestion.py` | Inside `chunk_document()` | See how documents are split | Saddlebag piece 📦 |

### Step 7: Start debugging

1. Select **"RAG Chatbot — Debug Server"** from the dropdown
2. Click the green play button (or press `F5`)
3. You'll see in the terminal:
   ```
   INFO     Starting rag-chatbot
   INFO     Environment: dev
   INFO     Cloud Provider: aws
   INFO     Uvicorn running on http://0.0.0.0:8000
   ```
4. The server is now running with the debugger attached

### Step 8: Send a request while debugging

Open another terminal (or use Swagger UI) and send a request.

In **Swagger UI** (`http://localhost:8000/docs`) → `POST /api/chat` → **"Try it out"**:

```json
{"question": "What is this?"}
```

Click **"Execute"**.

If you have a breakpoint in `chat()`, VS Code will:
1. **Pause execution** at the breakpoint
2. **Highlight the current line** in yellow
3. Show you the **Variables panel** on the left
4. Show the **Call Stack** (how we got here)

### Step 9: Inspect variables when breakpoint hits

When the debugger pauses, you can:

| Action | How | Example | 🫏 Donkey |
| --- | --- | --- | --- |
| **See variable values** | Look at the Variables panel | `body.question = "What is this?"` | 🫏 On the route |
| **Hover over a variable** | Move mouse over it in the code | Shows the value in a tooltip | 🫏 On the route |
| **Evaluate an expression** | Type in the Debug Console (bottom) | `len(search_results)` → `5` | Report card 📝 |
| **Step over** | Press `F10` | Execute current line, move to next | 🫏 On the route |
| **Step into** | Press `F11` | Go inside the function call | 🫏 On the route |
| **Step out** | Press `Shift+F11` | Finish current function, go back to caller | 🫏 On the route |
| **Continue** | Press `F5` | Run until next breakpoint | 🫏 On the route |
| **Stop** | Press `Shift+F5` | Stop the debugger | Hoof check 🔧 |

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

## PyCharm Debugger Setup

### Step 1: Open the project in PyCharm

File → Open → select the `rag-chatbot/` project folder

### Step 2: Configure the Python interpreter

1. File → Settings → Project → Python Interpreter
2. Click the gear icon → Add Interpreter → Existing
3. Select: `<project-root>/rag-chatbot/.venv/bin/python`
4. Click OK

### Step 3: Create a Run Configuration

1. Run → Edit Configurations → + → Python
2. Configure:
   - **Name**: RAG Chatbot Server
   - **Module name**: `uvicorn` (not Script path)
   - **Parameters**: `src.main:app --reload --port 8000`
   - **Working directory**: `<project-root>/rag-chatbot`
   - **Environment variables**: Click `...` → Load from `.env`
   - **Python interpreter**: `.venv/bin/python`

### Step 4: Set breakpoints

Same as VS Code — click in the gutter to set red dots.

### Step 5: Start debugging

Click the green bug icon (not the green play icon — the bug icon starts with debugger).

Or: Run → Debug 'RAG Chatbot Server'

PyCharm's debugger has the same controls:
- **F8** = Step Over
- **F7** = Step Into
- **Shift+F8** = Step Out
- **F9** = Resume (Continue)

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

## Debugger quick reference

| Action | VS Code | PyCharm | 🫏 Donkey |
| --- | --- | --- | --- |
| Start debugging | `F5` | `Shift+F9` | Hoof check 🔧 |
| Set breakpoint | Click gutter / `F9` | Click gutter / `Ctrl+F8` | 🫏 On the route |
| Step over | `F10` | `F8` | 🫏 On the route |
| Step into | `F11` | `F7` | 🫏 On the route |
| Step out | `Shift+F11` | `Shift+F8` | 🫏 On the route |
| Continue | `F5` | `F9` | 🫏 On the route |
| Stop | `Shift+F5` | `Ctrl+F2` | 🫏 On the route |
| Evaluate expression | Debug Console | Alt+F8 | Report card 📝 |

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

## What to debug in this project

### 🤖 AI Pipeline Breakpoints — Chat Query (Read Path)

These are the most important breakpoints to understand **how AI/RAG works** step by step.
Set them all, press F5, send a chat question from http://localhost:8000/docs, and step through.

#### File: `src/rag/chain.py` — `query()` method (⭐ start here)

This is the central AI orchestrator. Set breakpoints on all 5 steps:

| Step | Line (approx) | Code | What to inspect | AI concept you're seeing | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| **1. Embed** | 188 | `query_embedding = await self._llm.get_embedding(question)` | Hover `query_embedding` → 768 floats representing your question's meaning | **Text → Vector embedding** | The donkey 🐴 |
| **2. Search** | 191 | `search_results = await self._vector_store.search(` | Hover `search_results` → list of chunks with similarity scores (0.0–1.0) | **HNSW vector similarity search** | Saddlebag piece 📦 |
| **3. Context** | 204 | `context_texts = [result.text for result in search_results]` | Hover `context_texts` → the actual text chunks the LLM will read | **RAG context building** | The donkey 🐴 |
| **4. Generate** | 207 | `llm_response = await self._llm.generate(` | After step-over: hover `llm_response` → the LLM's answer + token count | **LLM text generation** | The donkey 🐴 |
| **5. Cost** | 223 | `token_usage = {` | Hover to see input/output tokens + estimated $ cost | **Token counting & cost estimation** | Cargo unit ⚖️ |

**What to look for:**
- **Step 1**: The embedding is a list of ~768 floats (nomic-embed-text). Each number captures a dimension of meaning.
- **Step 2**: Check `result.score` — values close to 1.0 mean high similarity. If scores are all low (<0.5), your documents may not contain relevant info.
- **Step 3**: This is what the LLM actually "sees" as context. If the answer is wrong, the problem is usually here — wrong chunks retrieved.
- **Step 4**: `llm_response.text` is the raw answer. `llm_response.input_tokens` shows how many tokens the prompt consumed.
- **Step 5**: Local (Ollama) cost is always $0. Cloud providers charge per token.

#### File: `src/llm/local_ollama.py` — Inside the LLM calls

Go deeper to see the raw HTTP communication with Ollama:

| Method | Line (approx) | Code | What to inspect | AI concept | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| `generate()` | ~87 | `response = await self._client.post(` | Step over → hover `response` → see the raw JSON Ollama returns (model, created_at, response text) | **LLM HTTP API call** | The donkey 🐴 |
| `get_embedding()` | ~135 | `response = await self._client.post(` | Step over → hover `response` → see the raw embedding array from nomic-embed-text | **Embedding API call** | Stable door 🚪 |
| `get_embeddings_batch()` | ~167 | `response = await self._client.post(` | Same as above but for multiple texts at once (used during document upload) | **Batch embedding** | GPS warehouse 🗺️ |

**What to look for:**
- In `generate()`: The request body contains the full prompt with context. You can see exactly what question + context is sent to the LLM.
- In `get_embedding()`: The response contains an `embedding` field — a list of 768 floats. Each float is one dimension of meaning.

#### File: `src/vectorstore/local_chromadb.py` — Inside vector search

| Method | Line (approx) | Code | What to inspect | AI concept | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| `search()` | ~116 | `results = self._collection.query(` | Step over → hover `results` → see `distances`, `documents`, `metadatas` | **ChromaDB HNSW k-NN search** | Local barn 🏚️ |
| `store_vectors()` | ~104 | `self._collection.upsert(` | See the chunk IDs, texts, and embeddings being stored | **Vector indexing** | Saddlebag piece 📦 |

**What to look for:**
- `results['distances']` — lower = more similar (ChromaDB uses distance, not similarity score)
- `results['documents']` — the actual text chunks returned
- `results['metadatas']` — document name, chunk index, etc.

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.

---

### 📥 AI Pipeline Breakpoints — Document Ingestion (Write Path)

Set these when uploading a document to see the full ETL-for-AI pipeline:

#### File: `src/rag/chain.py` — `ingest()` method

| Step | Line (approx) | Code | What to inspect | AI concept | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| **1. Parse** | 140 | `text = read_document(filename, content)` | Hover `text` → raw text extracted from your PDF/DOCX/TXT | **Document parsing** | 🫏 On the route |
| **2. Chunk** | 144 | `chunks = chunk_document(` | Hover `chunks` → list of overlapping text pieces (1000 chars each, 200 overlap) | **Text chunking (RecursiveCharacterTextSplitter)** | Saddlebag piece 📦 |
| **3. Embed** | ~152 | `embeddings = await self._llm.get_embeddings_batch(chunks)` | Hover `embeddings` → N×768 matrix (N chunks, each with 768-dim vector) | **Batch embedding generation** | The donkey 🐴 |
| **4. Store** | ~156 | `stored = await self._vector_store.store_vectors(` | Step over → see how many vectors were indexed in ChromaDB | **Vector storage & HNSW indexing** | Local barn 🏚️ |

**What to look for:**
- **Step 2**: Check `len(chunks)` — a 10-page PDF might produce 50+ chunks. Check if chunks make sense (not cut mid-sentence).
- **Step 3**: Check `len(embeddings)` — should equal `len(chunks)`. Each embedding is 768 floats.
- **Step 3**: Try `len(embeddings[0])` in the Debug Console → should be 768 (nomic-embed-text dimensions).

#### File: `src/rag/ingestion.py` — Chunking internals

| Function | Line | What to inspect | AI concept | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| `read_document()` | Start of function | `filename` and `content` → see what format was uploaded | **Multi-format document parsing** | 🫏 On the route |
| `chunk_document()` | After `text_splitter.split_text()` | The `chunks` list → see exactly where the text was split and how overlap works | **Chunking strategy** | Saddlebag piece 📦 |

**Try in the Debug Console:**
```python
len(chunks)                    # How many chunks?
len(chunks[0])                 # Characters in first chunk (~1000)
chunks[0][:200]                # First 200 chars of first chunk
chunks[1][:200]                # First 200 chars of second chunk — should overlap with end of chunks[0]
```

---

### 🎯 Quick Start — Minimum 4 Breakpoints

If you just want to see the entire AI pipeline with minimum effort, set breakpoints on these **4 lines in `src/rag/chain.py` → `query()`**:

```
Line 188  →  query_embedding = await self._llm.get_embedding(question)
Line 191  →  search_results = await self._vector_store.search(...)
Line 204  →  context_texts = [result.text for result in search_results]
Line 207  →  llm_response = await self._llm.generate(...)
```

Then:
1. Press **F5** (select "RAG Chatbot — Debug Server")
2. Open http://localhost:8000/docs in your browser
3. Try the **POST /api/chat** endpoint with a question
4. VS Code will pause at each breakpoint — use **F10** (step over) to move through
5. Hover over variables to see the AI data at each stage

---

### Understanding the request flow

Set breakpoints in this order to follow a chat request through the entire system:

```
1. src/api/middleware/logging.py    → dispatch()       # Request enters
2. src/api/routes/chat.py           → chat()           # Route handler
3. src/rag/chain.py                 → query()          # RAG orchestrator
4. src/llm/aws_bedrock.py           → get_embedding()  # Question → vector
5. src/vectorstore/aws_opensearch.py → search()        # Vector search
6. src/llm/aws_bedrock.py           → generate()       # LLM generates answer
7. src/api/routes/chat.py           → inline eval      # Heuristic evaluation (I30)
8. src/monitoring/query_logger.py   → log_query()      # JSONL structured log (I30)
9. src/api/routes/chat.py           → return response  # Response sent
```

### Understanding document ingestion

```
1. src/api/routes/documents.py → upload_document()  # File received
2. src/rag/chain.py            → ingest_document()  # Orchestrator
3. src/rag/ingestion.py        → read_document()    # PDF/TXT parsing
4. src/rag/ingestion.py        → chunk_document()   # Text splitting
5. src/llm/aws_bedrock.py      → get_embeddings_batch()  # Vectorization
6. src/vectorstore/...         → store_vectors()     # Saved to vector DB
```

---

## Common debugging scenarios

### "Why is the answer wrong?"

Set a breakpoint in `src/rag/chain.py` → `query()` and inspect:
- `search_results` — are the right chunks being retrieved?
- `context_texts` — is the context sent to the LLM correct?
- `llm_response.text` — what did the LLM actually return?

### "Why is it slow?"

Set breakpoints before and after each major step in `query()`:
- Embedding generation: how long?
- Vector search: how long?
- LLM generation: how long?

### "Why did ingestion fail?"

Set a breakpoint in `src/rag/ingestion.py` → `read_document()`:
- Is the file content correct (not empty)?
- Is the PDF readable?
- How many chunks were created?

- 🫏 **Donkey:** Checking the donkey's hooves, saddle straps, and GPS signal before concluding it's lost — most delivery failures have a simple root cause.
