# Deep Dive: LLM Providers — AWS Bedrock, Azure OpenAI & Local Ollama

> **Study order:** #8 · **Difficulty:** ★★☆☆☆ (you know boto3 and API clients — the new part is *what* you're calling)  
>
> **Files:** [`src/llm/aws_bedrock.py`](../../src/llm/aws_bedrock.py) · [`src/llm/azure_openai.py`](../../src/llm/azure_openai.py) · [`src/llm/local_ollama.py`](../../src/llm/local_ollama.py)  
>
> **Prerequisite:** [#7 — The LLM Interface (`base.py`)](llm-interface-deep-dive.md)  
>
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why This File Matters](#why-this-file-matters)
2. [DE Parallel — What You Already Know](#de-parallel--what-you-already-know)
3. [The Three Providers Side by Side](#the-three-providers-side-by-side)
4. [AWS: The Class Structure — Bedrock](#aws-the-class-structure--bedrock)
5. [AWS: Concept 1 — The Converse API (`generate()`)](#aws-concept-1--the-converse-api-generate)
6. [AWS: Concept 2 — The Invoke Model API (`get_embedding()`)](#aws-concept-2--the-invoke-model-api-get_embedding)
7. [Azure: The Class Structure — Azure OpenAI](#azure-the-class-structure--azure-openai)
8. [Azure: Concept 1 — The ChatCompletion API (`generate()`)](#azure-concept-1--the-chatcompletion-api-generate)
9. [Azure: Concept 2 — The Embeddings API (`get_embedding()`)](#azure-concept-2--the-embeddings-api-get_embedding)
10. [Local: The Class Structure — Ollama](#local-the-class-structure--ollama)
11. [Local: Concept 1 — The Chat API (`generate()`)](#local-concept-1--the-chat-api-generate)
12. [Local: Concept 2 — The Embed API (`get_embedding()`)](#local-concept-2--the-embed-api-get_embedding)
13. [All Three: Batch Embedding — Different Capabilities](#all-three-batch-embedding--different-capabilities)
14. [Concept: Two Models, One Class — All Providers Do This](#concept-two-models-one-class--all-providers-do-this)
15. [Cost Comparison — All Three Providers](#cost-comparison--all-three-providers)
16. [Where the LLM Providers Sit in the RAG Pipeline](#where-the-llm-providers-sit-in-the-rag-pipeline)
17. [Self-Test Questions](#self-test-questions)
18. [What to Study Next](#what-to-study-next)

---

## Why This File Matters

In file #7 (`base.py`) you learned the **interface** — the abstract contract. These three files are the **implementations** — the actual API calls that talk to AWS Bedrock, Azure OpenAI, and local Ollama. If `base.py` was the `BaseStorage` interface, these are the `DynamoDBStorage`, `PostgreSQLStorage`, and `SQLiteStorage` classes.

**The Strategy Pattern in action:** The rest of the codebase calls `llm.generate()` and `llm.get_embedding()` without knowing which provider is behind it. Swapping from AWS to Azure to Local means changing ONE environment variable — the code stays the same.

| What you'll learn | DE parallel | 🫏 Donkey |
|---|---| --- |
| How to call an LLM via boto3 (AWS), openai SDK (Azure), and httpx (Local) | How to call DynamoDB vs CosmosDB vs SQLite | Three ways to hire the same donkey from three different stables — same job, different paperwork |
| Three different API shapes for the same operation | Three different SDKs for the same storage pattern | Stable's front-door interface — how outside callers talk to the donkey |
| How embedding models are called on each platform | How secondary indexes work on each platform | Coordinates inked on the saddlebag — How embedding models are called on each platform: How secondary indexes work on each platform |
| Cost differences between providers (including $0 local) | Cost differences between AWS, Azure, and local services | Cost of keeping the donkey fed — Cost differences between providers (including $0 local): Cost differences between AWS, Azure, and local services |

- 🫏 **Donkey:** Think of this as the orientation briefing given to a new donkey before its first delivery run — it sets the context for everything that follows.

---

## DE Parallel — What You Already Know

```
┌─────────────────────────────────────────┐    ┌─────────────────────────────────────────┐
│  YOUR DYNAMODB CODE (what you know)     │    │  BEDROCK CODE (AWS provider)            │
│                                         │    │                                         │
│  client = boto3.client("dynamodb")      │    │  client = boto3.client("bedrock-runtime")│
│  response = client.get_item(...)        │    │  response = client.converse(...)         │
│  data = response["Item"]                │    │  text = response["output"]["message"]    │
└─────────────────────────────────────────┘    └─────────────────────────────────────────┘

┌─────────────────────────────────────────┐    ┌─────────────────────────────────────────┐
│  YOUR COSMOSDB/POSTGRES CODE (if any)   │    │  AZURE OPENAI CODE (Azure provider)     │
│                                         │    │                                         │
│  client = CosmosClient(endpoint, key)   │    │  client = AsyncAzureOpenAI(endpoint, key)│
│  response = container.query_items(...)  │    │  response = client.chat.completions...  │
│  data = response[0]                     │    │  text = choice.message.content           │
└─────────────────────────────────────────┘    └─────────────────────────────────────────┘
```

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## The Three Providers Side by Side

Before diving into each, here's the big picture comparison:

| Aspect | AWS Bedrock (`aws_bedrock.py`) | Azure OpenAI (`azure_openai.py`) | **Local Ollama (`local_ollama.py`)** | 🫏 Donkey |
|---|---|---|---| --- |
| **SDK** | `boto3` (AWS SDK) | `openai` (OpenAI SDK with Azure config) | `httpx` (plain HTTP client) | Each stable hands you a different intake form for the same donkey-hiring job |
| **Generation model** | Claude 3.5 Sonnet | GPT-4o | Llama 3.2 / Mistral | Three different writing donkeys to choose from — Claude, GPT-4o, or a local Llama |
| **Embedding model** | Amazon Titan v2 (1024 dim) | text-embedding-3-small (1536 dim) | nomic-embed-text (768 dim) | Coordinates inked on the saddlebag — Embedding model: Amazon Titan v2 (1024 dim) · text-embedding-3-small (1536 dim) · nomic-embed-text (768 dim) |
| **Generation API** | Converse API (Bedrock-specific) | ChatCompletion API (OpenAI standard) | `/api/chat` (Ollama REST) | Three different doorways for handing the donkey the question — same delivery, different door |
| **Embedding API** | Invoke Model (raw, manual JSON) | Embeddings API (typed SDK) | `/api/embed` (Ollama REST) | Three different counters for getting cargo GPS-stamped — same address job, different counter |
| **Auth** | IAM roles / AWS credentials | API key or Managed Identity | **None** — localhost | Door the customer knocks on — Auth: IAM roles / AWS credentials · API key or Managed Identity · None — localhost |
| **Batch embeddings** | ❌ Not native (loops one by one) | ✅ Native (send list, get list) | ✅ Native (send list, get list) | Azure and Ollama GPS-stamp whole batches; Bedrock's Titan stamps cargo one piece at a time |
| **Async** | ❌ Sync boto3 (wrapped in async) | ✅ True async (`AsyncAzureOpenAI`) | ✅ True async (`httpx.AsyncClient`) | Can multiple deliveries run at once? Azure and Ollama yes; Bedrock pretends but actually queues |
| **Input token price** | $0.003 / 1K | $0.0025 / 1K | **$0.00** | Bedrock charges $3 per million input hay bales; Azure charges $2.50; Ollama is free |
| **Output token price** | $0.015 / 1K | $0.01 / 1K | **$0.00** | Bedrock charges $15 per million output tokens; Azure charges $10; Ollama is free |
| **Quality** | ★★★★★ | ★★★★★ | ★★★☆☆ | Donkey-side view of Quality — affects how the donkey loads, reads, or delivers the cargo |
| **Offline** | ❌ | ❌ | ✅ | Donkey-side view of Offline — affects how the donkey loads, reads, or delivers the cargo |

- 🫏 **Donkey:** Choosing which stable to work with — AWS Bedrock, Azure OpenAI, or a local Ollama barn each offer different donkeys at different prices.

---

## AWS: The Class Structure — Bedrock

**The code (`aws_bedrock.py`, lines 29–50):**
```python
class BedrockLLM(BaseLLM):

    def __init__(self, model_id: str, region: str):
        self.model_id = model_id                           # Claude 3.5 Sonnet (for generation)
        self.region = region
        self._runtime_client = boto3.client(               # The boto3 client — same as yours
            "bedrock-runtime", region_name=region
        )
        self._embedding_model_id = "amazon.titan-embed-text-v2:0"  # Titan (for embeddings)
```

| Element | What it is | DE parallel | 🫏 Donkey |
|---|---|---| --- |
| `boto3.client("bedrock-runtime")` | The service client | `boto3.client("dynamodb")` | Phone number to ring AWS's donkey-rental desk before any trip can be booked |
| `model_id` (Claude) | Which LLM to call for generation | Which table to query | Naming which exact donkey (Claude) you want from the AWS stable's pen |
| `_embedding_model_id` (Titan) | Which model to call for embeddings | Which GSI to query | Titan is the GPS stamper in AWS's stable — converts cargo text to coordinates |

**Why `bedrock-runtime` not `bedrock`?** Two separate APIs:
- `bedrock` = management (list models, manage permissions) — like `dynamodb` for creating tables
- `bedrock-runtime` = inference (send prompts, get answers) — like `dynamodb` for read/write operations

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## AWS: Concept 1 — The Converse API (`generate()`)

**The code (`aws_bedrock.py`, lines 52–101):**
```python
response = self._runtime_client.converse(
    modelId=self.model_id,
    messages=[{"role": "user", "content": [{"text": user_message}]}],
    system=[{"text": system_prompt}],
    inferenceConfig={
        "maxTokens": 2048,
        "temperature": temperature,
        "topP": 0.9,
    },
)

# Parse response
output_text = response["output"]["message"]["content"][0]["text"]
usage = response.get("usage", {})
input_tokens = usage.get("inputTokens", 0)
output_tokens = usage.get("outputTokens", 0)
```

### Key characteristics of the Converse API

- **Unified interface** — works the same for Claude, Titan, Llama, Mistral
- **Dict-based** — you build request dicts manually, parse response dicts manually
- **Sync** — boto3 is synchronous (the `async` on the method is just for interface compatibility)
- **System message** is a separate parameter (`system=[...]`), not part of `messages`

### Request structure

```
converse(
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",   ← Which model
    messages=[{"role": "user", "content": [{"text": "..."}]}],  ← Conversation
    system=[{"text": "You are a helpful assistant..."}],    ← System instructions (separate)
    inferenceConfig={"maxTokens": 2048, "temperature": 0.1, "topP": 0.9},
)
```

### Response structure

```python
response = {
    "output": {"message": {"content": [{"text": "The refund policy states..."}]}},
    "usage": {"inputTokens": 1430, "outputTokens": 70},
    "stopReason": "end_turn"
}
```

- 🫏 **Donkey:** The stable's front door — defined entry points where questions arrive and answers depart.

---

## AWS: Concept 2 — The Invoke Model API (`get_embedding()`)

**The code (`aws_bedrock.py`, lines 103–118):**
```python
response = self._runtime_client.invoke_model(
    modelId=self._embedding_model_id,       # "amazon.titan-embed-text-v2:0"
    body=json.dumps({"inputText": text}),    # Manual JSON serialisation
    contentType="application/json",
)
result = json.loads(response["body"].read())
return result["embedding"]                   # [0.12, -0.45, ...] (1024 floats)
```

**Why a different API than Converse?** The Converse API is for chat (messages in, message out). Embedding models don't "chat" — they take text in and return numbers out. Different shape = different API.

**Note the manual JSON handling:** `json.dumps()` for the request, `json.loads(response["body"].read())` for the response. The Invoke Model API is a raw HTTP wrapper — you handle serialisation yourself.

| Titan Embeddings v2 | Value | 🫏 Donkey |
|---|---| --- |
| Model ID | `amazon.titan-embed-text-v2:0` | Blank cargo manifest — Model ID: amazon.titan-embed-text-v2:0 |
| Output dimensions | **1024** floats | Length of the donkey's GPS coordinate — more digits = finer location, more storage |
| Max input | 8,192 tokens | Titan accepts up to 8,192 hay bales of input text before it hits its limit |
| Cost | $0.00002 / 1K tokens | Titan GPS-stamping costs only $0.02 per million tokens — 150× cheaper than generation |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Azure: The Class Structure — Azure OpenAI

**The code (`azure_openai.py`, lines 30–64):**
```python
class AzureOpenAILLM(BaseLLM):

    def __init__(
        self,
        endpoint: str,
        api_key: str,
        deployment_name: str,
        api_version: str,
        embedding_deployment: str,
    ):
        self.deployment_name = deployment_name                # GPT-4o (for generation)
        self.embedding_deployment = embedding_deployment      # text-embedding-3-small (for embeddings)
        self._client = AsyncAzureOpenAI(                      # The OpenAI SDK — configured for Azure
            azure_endpoint=endpoint,
            api_key=api_key,
            api_version=api_version,
        )
```

### Key differences from Bedrock

| Aspect | AWS Bedrock | Azure OpenAI | 🫏 Donkey |
|---|---|---| --- |
| SDK | `boto3` (AWS-specific) | `openai` (industry standard, Azure-configured) | AWS makes you learn boto3-speak; Azure speaks the OpenAI lingua franca everyone already knows |
| Client | `boto3.client("bedrock-runtime")` | `AsyncAzureOpenAI(endpoint, key, version)` | boto3 hands you a generic AWS handle; Azure hands you a typed donkey-shaped client |
| Auth | IAM roles / env vars (AWS credentials) | API key or Managed Identity (Azure RBAC) | Entry gate to the stable — Auth: IAM roles / env vars (AWS credentials) · API key or Managed Identity (Azure RBAC) |
| Model reference | `model_id` (full ARN-like string) | `deployment_name` (you name it when deploying) | Mechanical groom — Model reference: model_id (full ARN-like string) · deployment_name (you name it when deploying) |
| Async | Sync (boto3 doesn't support async) | **True async** (`AsyncAzureOpenAI`) | Azure's donkey juggles parallel trips natively; AWS's donkey runs trips one after another |

**DE parallel:** This is like the difference between using `boto3` for DynamoDB vs using `psycopg2` for PostgreSQL. Different SDK, different connection pattern, but the operations are conceptually the same (query, insert, delete).

**Why "deployment_name" not "model_id"?** In Azure, you first **deploy** a model to your resource, giving it a name (e.g., `"gpt-4o"`). Then you reference it by that deployment name. In AWS, you reference the model directly by its ID. Think of it like: AWS = calling the model by its "real name," Azure = calling it by a nickname you assigned.

- 🫏 **Donkey:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for donkeys on the Azure route.

---

## Azure: Concept 1 — The ChatCompletion API (`generate()`)

**The code (`azure_openai.py`, lines 66–108):**
```python
response = await self._client.chat.completions.create(
    model=self.deployment_name,
    messages=[
        {"role": "system", "content": system_prompt},      # System message IN the messages list
        {"role": "user", "content": user_message},
    ],
    temperature=temperature,
    max_tokens=2048,
    top_p=0.9,
)

choice = response.choices[0]
usage = response.usage
return LLMResponse(
    text=choice.message.content or "",
    input_tokens=usage.prompt_tokens if usage else 0,      # Note: "prompt_tokens" not "inputTokens"
    output_tokens=usage.completion_tokens if usage else 0,  # Note: "completion_tokens" not "outputTokens"
)
```

### Side-by-side: AWS vs Azure generation call

```python
# AWS BEDROCK                                    # AZURE OPENAI
self._runtime_client.converse(                   await self._client.chat.completions.create(
    modelId=self.model_id,                           model=self.deployment_name,
    messages=[{                                      messages=[
        "role": "user",                                  {"role": "system", "content": sys_prompt},
        "content": [{"text": user_msg}]                  {"role": "user", "content": user_msg},
    }],                                              ],
    system=[{"text": sys_prompt}],                   # system is INSIDE messages ↑
    inferenceConfig={                                temperature=temperature,
        "maxTokens": 2048,                           max_tokens=2048,
        "temperature": temperature,                  top_p=0.9,
        "topP": 0.9,                             )
    },
)

# PARSE RESPONSE                                 # PARSE RESPONSE
resp["output"]["message"]["content"][0]["text"]   resp.choices[0].message.content
resp["usage"]["inputTokens"]                      resp.usage.prompt_tokens
resp["usage"]["outputTokens"]                     resp.usage.completion_tokens
```

### Key differences

| Aspect | AWS Bedrock | Azure OpenAI | 🫏 Donkey |
|---|---|---| --- |
| **System prompt** | Separate `system=[...]` parameter | Inside `messages` as `{"role": "system", ...}` | Customer's written brief — System prompt: Separate system=[...] parameter · Inside messages as {"role": "system", ...} |
| **Response parsing** | Dict keys: `response["output"]["message"]...` | Typed objects: `response.choices[0].message.content` | The actual cargo text inside the backpack the donkey is carrying |
| **Token naming** | `inputTokens` / `outputTokens` | `prompt_tokens` / `completion_tokens` | AWS calls hay bales "inputTokens"; Azure calls them "prompt_tokens" — same hay |
| **Async** | Sync call (despite `async def`) | True `await` — non-blocking | Stable gate — refuses harmful or off-topic deliveries before the donkey leaves |
| **Content format** | Nested: `[{"text": "..."}]` | Flat string: `"..."` | Stable inspector — checks the code is tidy before letting the donkey out |

**The function is the same.** Both send a system prompt + user message + settings, get back text + token counts. The `LLMResponse` dataclass normalises the differences — the rest of the codebase never knows which provider was used.

- 🫏 **Donkey:** The stable's front door — defined entry points where questions arrive and answers depart.

---

## Azure: Concept 2 — The Embeddings API (`get_embedding()`)

**The code (`azure_openai.py`, lines 110–124):**
```python
response = await self._client.embeddings.create(
    model=self.embedding_deployment,   # "text-embedding-3-small"
    input=text,                         # Just the text — no JSON wrapping needed
)
return response.data[0].embedding      # [0.12, -0.45, ...] (1536 floats)
```

### Side-by-side: AWS vs Azure embedding call

```python
# AWS BEDROCK (manual JSON)                       # AZURE OPENAI (typed SDK)
self._runtime_client.invoke_model(                await self._client.embeddings.create(
    modelId=self._embedding_model_id,                 model=self.embedding_deployment,
    body=json.dumps({"inputText": text}),             input=text,
    contentType="application/json",               )
)
result = json.loads(response["body"].read())      return response.data[0].embedding
return result["embedding"]
```

**Notice how much simpler the Azure call is.** No `json.dumps()`, no `json.loads()`, no `response["body"].read()`. The OpenAI SDK handles serialisation — you pass a string, get back a typed object.

| text-embedding-3-small | Value | 🫏 Donkey |
|---|---| --- |
| Deployment | `text-embedding-3-small` | Map pin attached to the cargo — Deployment: text-embedding-3-small |
| Output dimensions | **1536** floats (not 1024!) | Length of the donkey's GPS coordinate — more digits = finer location, more storage |
| Max input | 8,191 tokens | Azure's embedding model accepts up to 8,191 tokens of cargo text per coordinate request |
| Cost | $0.00002 / 1K tokens | Azure's GPS stamper charges $0.02 per million tokens — same pricing as AWS Titan |

### ⚠️ Critical: Dimension difference

AWS Titan produces **1024** dimensions. Azure text-embedding-3-small produces **1536** dimensions. Ollama nomic-embed-text produces **768** dimensions. This means:
- Your vector store index must match the embedding model's dimension
- You **cannot** mix embeddings from different models — a 1024-dim vector can't be compared to a 1536-dim vector
- If you switch providers, you must **re-embed all documents**

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Local: The Class Structure — Ollama

**The code (`local_ollama.py`, `__init__`):**
```python
class OllamaLLM(BaseLLM):

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model_name: str = "llama3.2",
        embedding_model: str = "nomic-embed-text",
    ):
        self.base_url = base_url.rstrip("/")
        self.model_name = model_name
        self.embedding_model = embedding_model
        self._client = httpx.AsyncClient(base_url=self.base_url, timeout=120.0)
```

### Comparison with the other providers

| Aspect | AWS Bedrock | Azure OpenAI | **Local Ollama** | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Client** | `boto3.client("bedrock-runtime")` | `AsyncAzureOpenAI(endpoint, key)` | `httpx.AsyncClient(base_url)` | Three constructors for three stables — AWS handle, Azure typed client, or a plain knock on localhost |
| **Auth** | IAM credentials (auto from env) | API key in constructor | **None** — localhost, no auth | Entry gate to the stable — Auth: IAM credentials (auto from env) · API key in constructor · None — localhost, no auth |
| **Two models** | `model_id` + `_embedding_model_id` | `deployment_name` + `embedding_deployment` | `model_name` + `embedding_model` | Robot stable hand — Two models: model_id + _embedding_model_id · deployment_name + embedding_deployment · model_name + embedding_model |
| **Timeout** | boto3 default | openai default | 120s (local models can be slow on CPU) | How long to wait before giving up — the local donkey gets 2 minutes because CPU is slow |

**Why httpx instead of a dedicated Ollama SDK?** Ollama's REST API is simple enough that a generic HTTP client works perfectly. No need for another dependency. And `httpx` is already in `pyproject.toml` (used for testing too).

**DE parallel:** Ollama is like running a local PostgreSQL server — you install it, it runs as a daemon, your app connects to it via localhost. The difference: PostgreSQL stores data, Ollama runs inference.

- 🫏 **Donkey:** Your own backyard barn — no cloud costs, full control, ChromaDB SQLite under the floor.

---

## Local: Concept 1 — The Chat API (`generate()`)

**The code (`local_ollama.py`, `generate()`):**

```python
response = await self._client.post(
    "/api/chat",
    json={
        "model": self.model_name,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": False,
        "options": {
            "temperature": temperature,
            "top_p": 0.9,
            "num_predict": 2048,
        },
    },
)
data = response.json()

return LLMResponse(
    text=data["message"]["content"],
    input_tokens=data.get("prompt_eval_count", 0),
    output_tokens=data.get("eval_count", 0),
    model_id=self.model_name,
)
```

### Side-by-side: all three providers

```python
# AWS BEDROCK                              # AZURE OPENAI
client.converse(                           await client.chat.completions.create(
    modelId=self.model_id,                     model=self.deployment_name,
    messages=[{                                messages=[
        "role": "user",                            {"role": "system", "content": sys},
        "content": [{"text": msg}]                 {"role": "user", "content": msg},
    }],                                        ],
    system=[{"text": sys}],                    temperature=temp,
    inferenceConfig={"temperature": temp},     max_tokens=2048,
)                                          )

# LOCAL OLLAMA
await self._client.post("/api/chat", json={
    "model": self.model_name,
    "messages": [
        {"role": "system", "content": sys},
        {"role": "user", "content": msg},
    ],
    "stream": False,
    "options": {"temperature": temp, "num_predict": 2048},
})
```

**Key observations:**
- Ollama's chat format is **identical** to Azure OpenAI's (`system` + `user` messages in a list)
- `"stream": False` tells Ollama to return the complete response at once (not token-by-token)
- `"num_predict"` is Ollama's name for `max_tokens` — maximum tokens to generate
- Token counting: `prompt_eval_count` = input tokens, `eval_count` = output tokens

### Error handling — the friendly "Ollama not running" check

```python
except httpx.ConnectError:
    raise RuntimeError(
        "Ollama is not running. Start it with: ollama serve "
        "(or install: curl -fsSL https://ollama.com/install.sh | sh)"
    )
```

If Ollama isn't running, you get a clear error message instead of a cryptic `ConnectionRefusedError`.

- 🫏 **Donkey:** The stable's front door — defined entry points where questions arrive and answers depart.

---

## Local: Concept 2 — The Embed API (`get_embedding()`)

**The code (`local_ollama.py`, `get_embedding()`):**

```python
response = await self._client.post(
    "/api/embed",
    json={
        "model": self.embedding_model,
        "input": text,
    },
)
data = response.json()
return data["embeddings"][0]    # [0.12, -0.45, ...] (768 floats)
```

### Side-by-side: all three providers

```python
# AWS BEDROCK (manual JSON)                # AZURE OPENAI (typed SDK)
client.invoke_model(                       await client.embeddings.create(
    modelId=self._embedding_model_id,          model=self.embedding_deployment,
    body=json.dumps({"inputText": text}),      input=text,
    contentType="application/json",        )
)                                          return resp.data[0].embedding
result = json.loads(resp["body"].read())
return result["embedding"]

# LOCAL OLLAMA (simple HTTP)
await self._client.post("/api/embed", json={
    "model": self.embedding_model,
    "input": text,
})
return data["embeddings"][0]
```

**Ollama's embedding API is the simplest of the three.** No `json.dumps()`, no typed objects — just send text, get back a list of floats.

### Dimensions: 768 vs 1024 vs 1536

| Model | Provider | Dimensions | Quality | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| nomic-embed-text | Local (Ollama) | **768** | Good | Local GPS uses 768 coordinates per address — compact and free |
| Titan v2 | AWS Bedrock | **1024** | Good | AWS GPS uses 1024 coordinates per address — middle ground for precision and cost |
| text-embedding-3-small | Azure OpenAI | **1536** | Best | Azure GPS uses 1536 coordinates per address — most precise stamps |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## All Three: Batch Embedding — Different Capabilities

**AWS Bedrock (`aws_bedrock.py`, lines 120–130):**
```python
async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
    """Titan doesn't have a native batch API, so we call one at a time."""
    embeddings = []
    for text in texts:
        embedding = await self.get_embedding(text)    # N API calls
        embeddings.append(embedding)
    return embeddings
```

**Azure OpenAI (`azure_openai.py`, lines 126–137):**
```python
async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
    """Azure OpenAI supports batch embedding natively."""
    response = await self._client.embeddings.create(
        model=self.embedding_deployment,
        input=texts,                                   # 1 API call — send ALL texts at once
    )
    return [item.embedding for item in response.data]
```

**Local Ollama (`local_ollama.py`):**
```python
async def get_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
    """Ollama supports batch embedding natively."""
    response = await self._client.post(
        "/api/embed",
        json={"model": self.embedding_model, "input": texts},  # 1 API call
    )
    return response.json()["embeddings"]
```

### The difference matters for ingestion

| | AWS Bedrock | Azure OpenAI | **Local Ollama** | 🫏 Donkey |
|---|---|---|---| --- |
| **42 chunks** | 42 API calls (42 network round trips) | **1 API call** (1 network round trip) | **1 API call** (localhost) | Bedrock GPS-stamps 42 backpack chunks in 42 trips; Azure and Ollama batch them all |
| **Latency** | 42 × ~50ms = ~2.1 seconds | ~200ms total | ~300ms total | Cost of keeping the donkey fed — Latency: 42 × ~50ms = ~2.1 seconds · ~200ms total · ~300ms total |
| **Why?** | Titan has no batch endpoint | OpenAI SDK accepts a list natively | Ollama `/api/embed` accepts a list natively | Whether the GPS counter takes a whole sack of cargo at once or insists on one piece at a time |

**DE parallel:** This is like DynamoDB's `batch_write_item` (limited to 25 items) vs PostgreSQL's multi-row `INSERT INTO ... VALUES (), (), ()` (unlimited). Azure has the better batch story here.

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Concept: Two Models, One Class — All Providers Do This

All three providers use **two different models** behind the same class:

```
BedrockLLM class                              AzureOpenAILLM class
├── generate()       → Claude 3.5 Sonnet     ├── generate()       → GPT-4o
├── get_embedding()  → Titan Embeddings v2    ├── get_embedding()  → text-embedding-3-small
└── Same boto3 client                         └── Same openai client

OllamaLLM class
├── generate()       → llama3.2
├── get_embedding()  → nomic-embed-text
└── Same httpx client
```

**Why?** Because generation and embedding are fundamentally different operations:

| | Language Model | Embedding Model | 🫏 Donkey |
|---|---|---| --- |
| **Purpose** | Generate text | Convert text → numbers | Donkey-side view of Purpose — affects how the donkey loads, reads, or delivers the cargo |
| **Output** | Variable-length text | Fixed-size float array | Donkey-side view of Output — affects how the donkey loads, reads, or delivers the cargo |
| **Cost** | Expensive | Cheap (100×–250× less) | What the stable charges this month — Cost: Expensive · Cheap (100×–250× less) |
| **Speed** | 1–5 seconds | ~50ms | Donkey-side view of Speed — affects how the donkey loads, reads, or delivers the cargo |

The class groups them by **provider** (who you're calling), not by **function** (what you're doing). This makes sense because auth, region, and client setup are per-provider.

- 🫏 **Donkey:** Choosing which stable to work with — AWS Bedrock, Azure OpenAI, or a local Ollama barn each offer different donkeys at different prices.

---

## Cost Comparison — All Three Providers

### Per-query cost

```
┌──────────────────────────────────────────────────────────────────────┐
│  Same RAG query on all three providers (typical)                      │
│                                                                      │
│  AWS BEDROCK (Claude 3.5 Sonnet + Titan)                            │
│    Embed question: 30 tokens × $0.00002/1K     = $0.0000006  ≈ FREE │
│    Generate:                                                         │
│      Input:  1430 tokens × $0.003/1K            = $0.00429          │
│      Output: 70 tokens   × $0.015/1K            = $0.00105          │
│    Total:                                         $0.00534  ≈ $0.005 │
│                                                                      │
│  AZURE OPENAI (GPT-4o + text-embedding-3-small)                     │
│    Embed question: 30 tokens × $0.00002/1K     = $0.0000006  ≈ FREE │
│    Generate:                                                         │
│      Input:  1430 tokens × $0.0025/1K           = $0.003575         │
│      Output: 70 tokens   × $0.01/1K             = $0.0007           │
│    Total:                                         $0.004275 ≈ $0.004 │
│                                                                      │
│  LOCAL OLLAMA (Llama 3.2 + nomic-embed-text)                        │
│    Embed question:  $0.00                                            │
│    Generate:         $0.00                                            │
│    Total:            $0.00  ← runs on your hardware                   │
│                                                                      │
│  Azure is ~20% cheaper than AWS. Local is free.                      │
└──────────────────────────────────────────────────────────────────────┘
```

### Monthly cost at 1000 queries/day

| | AWS Bedrock | Azure OpenAI | **Local Ollama** | 🫏 Donkey |
|---|---|---|---| --- |
| LLM cost | ~$160/month | ~$130/month | **$0/month** | Monthly hay bill — local donkey eats free, cloud donkeys cost $130–160 at this volume |
| Vector store | ~$350/month (OpenSearch) | ~$75/month (AI Search) | **$0/month** (ChromaDB) | AWS search hub — Vector store: ~$350/month (OpenSearch) · ~$75/month (AI Search) · $0/month (ChromaDB) |
| **Total** | **~$510/month** | **~$205/month** | **$0/month** | Donkey-hire fee — Total: ~$510/month · ~$205/month · $0/month |

**⚠️ The vector store is the biggest cost difference** — not the LLM. OpenSearch Serverless has a high minimum ($350/month). Azure AI Search Basic is much cheaper ($75/month). This often drives the cloud choice more than the LLM pricing.

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Where the LLM Providers Sit in the RAG Pipeline

```
USER: "What is the refund policy?"
         │
         ▼
┌──────────────────────────────────────────────────────────────────────┐
│                        RAG Pipeline                                 │
│                                                                     │
│  Step 1: EMBED the question                                        │
│     AWS:   aws_bedrock.py → invoke_model(Titan)      → 1024 floats  │
│     Azure: azure_openai.py → embeddings.create()    → 1536 floats  │
│     Local: local_ollama.py → /api/embed              → 768 floats   │
│                                                                     │
│  Step 2: SEARCH the vector store         (not this file)           │
│     AWS:   opensearch.py → knn query (1024-dim index)               │
│     Azure: ai_search.py → vector query (1536-dim index)             │
│     Local: local_chromadb.py → collection.query (768-dim)           │
│                                                                     │
│  Step 3: GENERATE the answer                                       │
│     AWS:   aws_bedrock.py → converse(Claude)                       │
│     Azure: azure_openai.py → chat.completions.create(GPT-4o)       │
│     Local: local_ollama.py → /api/chat(Llama 3.2)                  │
│                                                                     │
│  The rest of the code doesn't know or care which provider was used. │
└──────────────────────────────────────────────────────────────────────┘
```

- 🫏 **Donkey:** The donkey checks its backpack full of retrieved document chunks before answering — no guessing from memory.

---

## Self-Test Questions

| Question | Answer | Concept it tests | 🫏 Donkey |
|---|---|---| --- |
| "Why does Azure put the system prompt inside `messages` but Bedrock has a separate `system` parameter?" | API design difference. Same effect — the LLM gets system instructions either way. The `BaseLLM` interface hides this. | API abstraction | Different ways to slip standing orders into the delivery note — donkey doesn't care which |
| "What happens if you use Azure embeddings (1536-dim) with an OpenSearch index configured for 1024-dim?" | Indexing fails — dimension mismatch. You must match embedding model to vector store config. | Dimension matching | Coordinates inked on the saddlebag — "What happens if you use Azure embeddings (1536-dim) with an OpenSearch index configured for 1024-dim?": Indexing fails — dimension |
| "Why is Azure's batch embedding faster than Bedrock's?" | Azure's API natively accepts a list of texts. Bedrock's Titan has no batch endpoint, so it loops internally. Network round trips: 1 vs N. | API capabilities | One trip to the GPS counter with the whole sack beats 42 separate trips for the same cargo |
| "Could you use Claude (Bedrock) for generation but text-embedding-3-small (Azure) for embeddings?" | Technically yes — but you'd need two clients and the auth complexity doubles. The Strategy Pattern groups by provider for simplicity. | Architecture trade-offs | Could the donkey wear an AWS saddle and Azure GPS at once? Yes, but doubles the paperwork |
| "Why is `AsyncAzureOpenAI` truly async but `boto3` is not?" | The OpenAI SDK was built async-first. boto3 was built in 2015 before async was common in Python. You'd need `aioboto3` for true async Bedrock calls. | SDK maturity | Azure's stable was built async-first; AWS's older stable still hands deliveries one at a time |
| "Which provider should you choose?" | Depends: Azure is cheaper (especially vector store), AWS keeps data in your existing AWS account, Local is free and offline. Run evaluation on both cloud providers — answer quality may differ between Claude and GPT-4o. Use Local for development. | Provider selection | Which stable to rent from? Run the report card on both donkeys before committing the herd |
| "What happens if Ollama isn't running when the app starts?" | `httpx.ConnectError` → RuntimeError with instructions to run `ollama serve`. Clear error message, not a cryptic crash. | Local error handling | If the local donkey is asleep you get a clear "wake me with `ollama serve`" message, not a crash |
| "Why does Ollama use `httpx` instead of a dedicated SDK?" | Ollama's REST API is simple (2 endpoints: `/api/chat` and `/api/embed`). `httpx` is already a dependency — no need for another package. | Dependency management | The local stable's door has only two knobs, so a generic key (httpx) opens it fine |

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

Now that you've seen how **all three** LLM providers work, study where the results are **stored and searched**:
- **File #9:** [`src/vectorstore/base.py`](vectorstore-interface-deep-dive.md) — the abstract interface for vector storage (like `base.py` was for LLMs)
- **File #10:** [`src/vectorstore/`](vectorstore-providers-deep-dive.md) — the concrete vector store implementations (AWS OpenSearch + Azure AI Search + Local ChromaDB)

📖 **Related docs:**
- [AWS Services → Bedrock](../architecture-and-design/aws-services.md#amazon-bedrock)
- [How Services Work → Bedrock](../architecture-and-design/how-services-work.md#amazon-bedrock--how-llm-inference-works)
- [Cost Analysis](cost-analysis.md)
- [The LLM Interface (file #7)](llm-interface-deep-dive.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
