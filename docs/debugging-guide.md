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

---

## VS Code Debugger Setup

### Step 1: Open the project in VS Code

```bash
code /home/ketan-odido/maestro/rag-chatbot
```

Or: File → Open Folder → select `rag-chatbot/`

### Step 2: Select the Python interpreter

1. Press `Ctrl+Shift+P` (Command Palette)
2. Type: `Python: Select Interpreter`
3. Choose: `('.venv': venv) ./venv/bin/python`

If you don't see it:
- Make sure you ran `poetry install` first
- Make sure `poetry config virtualenvs.in-project true` was set
- Click "Enter interpreter path" and type: `/home/ketan-odido/maestro/rag-chatbot/.venv/bin/python`

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

| Configuration | What it does |
| --- | --- |
| **RAG Chatbot — Debug Server** | Starts the FastAPI server with debugger attached. Use this for testing endpoints. |
| **RAG Chatbot — Debug Tests** | Runs all pytest tests with debugger. Use this when a test fails and you want to step through it. |
| **RAG Chatbot — Debug Single Test File** | Runs only the currently open test file. Fastest for debugging one test. |

### Step 6: Set breakpoints

Click in the **gutter** (the space to the left of line numbers) to set a red dot.

**Recommended breakpoints for understanding the flow:**

| File | Line | Why |
| --- | --- | --- |
| `src/main.py` | Line inside `lifespan()` | See what happens at startup |
| `src/api/routes/chat.py` | First line of `chat()` | See every incoming chat request |
| `src/rag/chain.py` | Inside `query()` | See RAG retrieval + generation |
| `src/llm/aws_bedrock.py` | Inside `generate()` | See the Bedrock API call |
| `src/llm/azure_openai.py` | Inside `generate()` | See the Azure OpenAI API call |
| `src/vectorstore/base.py` | Inside `search()` | See vector search results |
| `src/rag/ingestion.py` | Inside `chunk_document()` | See how documents are split |

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

Open another terminal (or use Swagger UI) and send a request:

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question": "What is this?"}'
```

If you have a breakpoint in `chat()`, VS Code will:
1. **Pause execution** at the breakpoint
2. **Highlight the current line** in yellow
3. Show you the **Variables panel** on the left
4. Show the **Call Stack** (how we got here)

### Step 9: Inspect variables when breakpoint hits

When the debugger pauses, you can:

| Action | How | Example |
| --- | --- | --- |
| **See variable values** | Look at the Variables panel | `body.question = "What is this?"` |
| **Hover over a variable** | Move mouse over it in the code | Shows the value in a tooltip |
| **Evaluate an expression** | Type in the Debug Console (bottom) | `len(search_results)` → `5` |
| **Step over** | Press `F10` | Execute current line, move to next |
| **Step into** | Press `F11` | Go inside the function call |
| **Step out** | Press `Shift+F11` | Finish current function, go back to caller |
| **Continue** | Press `F5` | Run until next breakpoint |
| **Stop** | Press `Shift+F5` | Stop the debugger |

---

## PyCharm Debugger Setup

### Step 1: Open the project in PyCharm

File → Open → select `/home/ketan-odido/maestro/rag-chatbot/`

### Step 2: Configure the Python interpreter

1. File → Settings → Project → Python Interpreter
2. Click the gear icon → Add Interpreter → Existing
3. Select: `/home/ketan-odido/maestro/rag-chatbot/.venv/bin/python`
4. Click OK

### Step 3: Create a Run Configuration

1. Run → Edit Configurations → + → Python
2. Configure:
   - **Name**: RAG Chatbot Server
   - **Module name**: `uvicorn` (not Script path)
   - **Parameters**: `src.main:app --reload --port 8000`
   - **Working directory**: `/home/ketan-odido/maestro/rag-chatbot`
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

---

## Debugger quick reference

| Action | VS Code | PyCharm |
| --- | --- | --- |
| Start debugging | `F5` | `Shift+F9` |
| Set breakpoint | Click gutter / `F9` | Click gutter / `Ctrl+F8` |
| Step over | `F10` | `F8` |
| Step into | `F11` | `F7` |
| Step out | `Shift+F11` | `Shift+F8` |
| Continue | `F5` | `F9` |
| Stop | `Shift+F5` | `Ctrl+F2` |
| Evaluate expression | Debug Console | Alt+F8 |

---

## What to debug in this project

### Understanding the request flow

Set breakpoints in this order to follow a chat request through the entire system:

```
1. src/api/middleware/logging.py    → dispatch()       # Request enters
2. src/api/routes/chat.py           → chat()           # Route handler
3. src/rag/chain.py                 → query()          # RAG orchestrator
4. src/llm/aws_bedrock.py           → get_embedding()  # Question → vector
5. src/vectorstore/aws_opensearch.py → search()        # Vector search
6. src/llm/aws_bedrock.py           → generate()       # LLM generates answer
7. src/api/routes/chat.py           → return response  # Response sent
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
