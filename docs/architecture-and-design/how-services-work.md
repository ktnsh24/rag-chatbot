# How the AI Services Work — Under the Hood

> **Who is this for?** You've read the overview docs and know *what* each service
> does. This guide explains *how* each service actually works internally — the
> mechanics, the API actions, the data flow, and what happens on the cloud side
> when your code calls these services.

---

## Table of Contents

1. [Amazon Bedrock — How LLM Inference Works](#amazon-bedrock--how-llm-inference-works)
2. [Amazon Titan Embeddings — How Text Becomes Numbers](#amazon-titan-embeddings--how-text-becomes-numbers)
3. [Amazon OpenSearch Serverless — How Vector Search Works](#amazon-opensearch-serverless--how-vector-search-works)
4. [Azure OpenAI — How GPT Processes Your Request](#azure-openai--how-gpt-processes-your-request)
5. [Azure AI Search — How Vector Indexing Works](#azure-ai-search--how-vector-indexing-works)
6. [Amazon DynamoDB — How Key-Value Lookups Work](#amazon-dynamodb--how-key-value-lookups-work)
7. [Azure Cosmos DB — How Partitioned NoSQL Works](#azure-cosmos-db--how-partitioned-nosql-works)
8. [How All Services Connect — End-to-End Request Flow](#how-all-services-connect--end-to-end-request-flow)

---

## Amazon Bedrock — How LLM Inference Works

### What happens when you call Bedrock?

When our code in `src/llm/aws_bedrock.py` calls `self._runtime_client.converse(...)`,
here's what happens step by step:

```
Your Python code (src/llm/aws_bedrock.py)
    │
    ▼
boto3 client serialises your request to JSON
    │
    ▼
HTTPS POST → bedrock-runtime.eu-central-1.amazonaws.com
    │       (signed with AWS SigV4 — your IAM credentials)
    │
    ▼
AWS Bedrock Runtime service receives the request
    │
    ├── 1. Validates your IAM permissions (bedrock:InvokeModel)
    ├── 2. Checks your model access (did you enable Claude?)
    ├── 3. Routes to the correct model provider (Anthropic for Claude)
    │
    ▼
Anthropic's Claude model (running on AWS GPUs)
    │
    ├── 4. Tokenises your text (breaks it into tokens)
    │       "What is the refund policy?" → ["What", " is", " the", " refund", " policy", "?"]
    │
    ├── 5. Processes tokens through the neural network
    │       (billions of matrix multiplications across GPU cores)
    │       This is the actual "thinking" — takes 1-10 seconds
    │
    ├── 6. Generates output tokens one at a time (autoregressive)
    │       Token 1: "Based"
    │       Token 2: " on"
    │       Token 3: " the"
    │       Token 4: " context"
    │       ... (until max_tokens or stop sequence)
    │
    ▼
Response flows back through Bedrock → boto3 → your code
```

### The Converse API — what each parameter does

Here's our actual code with every parameter explained:

```python
# src/llm/aws_bedrock.py — the actual API call

response = self._runtime_client.converse(

    # WHICH MODEL to use
    # Format: "provider.model-name-version"
    # Bedrock normalises this so you don't need provider-specific formats
    modelId="anthropic.claude-3-5-sonnet-20241022-v2:0",

    # WHAT TO SEND — the conversation messages
    # Bedrock uses the same format regardless of which model you pick
    messages=[
        {
            "role": "user",           # Who is speaking (user or assistant)
            "content": [
                {"text": user_message}  # The actual text to send
            ]
        }
    ],

    # SYSTEM INSTRUCTIONS — rules the model must follow
    # This is separate from messages because it has special treatment:
    # the model treats it as persistent instructions, not a conversation turn
    system=[
        {"text": system_prompt}
    ],

    # GENERATION SETTINGS — control the output
    inferenceConfig={
        "maxTokens": 2048,       # Stop generating after 2048 tokens (~1500 words)
                                  # Prevents runaway responses and controls cost

        "temperature": 0.1,       # Randomness: 0.0 = always pick the most likely
                                  # next token, 1.0 = more random/creative
                                  # We use 0.1 for RAG because we want factual,
                                  # consistent answers (not creative writing)

        "topP": 0.9,             # Nucleus sampling: only consider tokens that make
                                  # up the top 90% probability mass
                                  # Together with low temperature, this ensures
                                  # very focused, predictable output
    },
)
```

### The response — what comes back

```python
# What Bedrock returns:
{
    "output": {
        "message": {
            "role": "assistant",
            "content": [
                {
                    "text": "Based on the context, refunds are processed within 14 days..."
                }
            ]
        }
    },
    "usage": {
        "inputTokens": 1250,      # How many tokens were in your request
        "outputTokens": 180,       # How many tokens the model generated
        "totalTokens": 1430        # Total (this is what you pay for)
    },
    "stopReason": "end_turn",      # Why the model stopped generating:
                                    #   "end_turn" = finished naturally
                                    #   "max_tokens" = hit the 2048 limit
                                    #   "stop_sequence" = hit a custom stop word
    "metrics": {
        "latencyMs": 2340          # How long the model took (in milliseconds)
    }
}
```

### AWS API actions used

| boto3 method | AWS API action | When it happens | IAM permission | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| `converse()` | `bedrock-runtime:Converse` | Every chat query | `bedrock:InvokeModel` | The donkey 🐴 |
| `invoke_model()` | `bedrock-runtime:InvokeModel` | Every embedding request | `bedrock:InvokeModel` | The donkey 🐴 |

### How the Converse API differs from InvokeModel

Bedrock has two APIs:

- **InvokeModel** (older): You must format the request body in each model's native
  format (different JSON structure for Claude vs Llama vs Titan).
- **Converse** (newer, what we use): Universal format — same JSON structure for
  every model. Bedrock translates it for you.

We use `Converse` for chat (universal format) and `InvokeModel` for embeddings
(because Converse doesn't support embedding models yet).

- 🫏 **Donkey:** The donkey itself — it carries the question in, consults the backpack, and writes the answer on the way back.

---

## Amazon Titan Embeddings — How Text Becomes Numbers

### What happens when you create an embedding?

```
Your text: "What is the refund policy?"
    │
    ▼
src/llm/aws_bedrock.py → invoke_model()
    │
    ▼
Amazon Titan Embeddings v2 model:
    │
    ├── 1. TOKENISE: Split text into subword tokens
    │       "What" "is" "the" "ref" "##und" "policy" "?"
    │
    ├── 2. ENCODE: Pass tokens through transformer layers
    │       Each token gets a 1024-dimensional representation
    │       The model has learned what words "mean" from training
    │       on billions of text examples
    │
    ├── 3. POOL: Combine all token vectors into one
    │       Usually "mean pooling" — average all token vectors
    │       Result: one vector representing the entire text
    │
    ├── 4. NORMALISE: Scale the vector to unit length
    │       This makes cosine similarity = dot product (faster math)
    │
    ▼
Output: [0.0234, -0.0891, 0.1245, 0.0567, ..., -0.0123]
        ← ─────────── 1024 floating-point numbers ──────────── →
```

### The actual API call

```python
# src/llm/aws_bedrock.py — embedding request

response = self._runtime_client.invoke_model(
    modelId="amazon.titan-embed-text-v2:0",       # The embedding model
    body=json.dumps({"inputText": text}),           # Your text as JSON
    contentType="application/json",                 # Always JSON
)

result = json.loads(response["body"].read())
embedding = result["embedding"]  # → list of 1024 floats
```

### What the numbers mean

Each of the 1024 numbers captures a different aspect of the text's meaning.
We don't know exactly what each dimension represents (they're learned during
training), but intuitively:

```
Dimension 0:   might capture "is this about a person or a thing?"
Dimension 1:   might capture "is this formal or casual?"
Dimension 2:   might capture "is this a question or a statement?"
...
Dimension 1023: might capture some other semantic feature

These are rough intuitions — in reality, each dimension captures
a complex combination of many linguistic features.
```

### Why 1024 dimensions?

- More dimensions = more nuanced meaning captured
- But also: more storage space, slower similarity calculation
- 1024 is a good balance between quality and efficiency

| Model | Dimensions | Quality | Speed | Storage per chunk | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| Titan Embeddings v2 | 1024 | Good | Fast | 4 KB | GPS warehouse 🗺️ |
| OpenAI text-embedding-3-small | 1536 | Better | Fast | 6 KB | The donkey 🐴 |
| OpenAI text-embedding-3-large | 3072 | Best | Slower | 12 KB | The donkey 🐴 |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Amazon OpenSearch Serverless — How Vector Search Works

### What is OpenSearch?

OpenSearch is a **search engine** (fork of Elasticsearch). It stores documents
and lets you search them. Traditionally, it uses **keyword search** (match words).
The **k-NN plugin** adds **vector search** (match meaning).

### What happens when you store a vector?

```
src/vectorstore/aws_opensearch.py → store_vectors()
    │
    ▼
For each chunk, sends an INDEX request:
    │
    ├── Document: {
    │     "embedding": [0.0234, -0.0891, ...],    ← 1024 floats
    │     "text": "Refunds are processed within...", ← original text
    │     "document_id": "abc-123",                  ← which PDF it came from
    │     "document_name": "refund-policy.pdf",      ← human-readable name
    │     "chunk_index": 7                           ← 8th chunk in this document
    │   }
    │
    ▼
OpenSearch receives the document:
    │
    ├── 1. Stores the raw document in a Lucene segment (on disk/SSD)
    │
    ├── 2. Adds the embedding to the HNSW graph (vector index)
    │       This is the key part — the vector gets a "position" in the graph
    │       connected to its nearest neighbours
    │
    ├── 3. Indexes the text field (inverted index for keyword search)
    │
    └── 4. After refresh(): makes the document searchable
```

### How HNSW vector search works (step by step)

HNSW (Hierarchical Navigable Small World) is the algorithm that makes
vector search fast. Here's how it works:

**Building the index (when you store vectors):**

```
Imagine adding points to a multi-layer graph:

Layer 2 (sparse):    [A] ─────────────────── [D]
                      Few nodes, long connections
                      → Used for big jumps

Layer 1 (medium):    [A] ──── [B] ──── [C] ── [D]
                      More nodes, medium connections
                      → Used for medium jumps

Layer 0 (dense):     [A] [B] [C] [D] [E] [F] [G] [H]
                      All nodes, short connections
                      → Used for fine-grained search

When you add a new vector:
  1. Randomly assign it a layer (higher layers are rarer)
  2. Starting from the top layer, find the nearest existing node
  3. Connect the new vector to its nearest neighbours at each layer
  4. These connections form the "navigable small world" graph
```

**Searching (when you query):**

```
Query: "How do I get my money back?" → embedding [0.82, -0.15, 0.43, ...]
    │
    ▼
Start at Layer 2 (top):
    │   Compare query to [A] and [D]
    │   [D] is closer → move to [D]
    │
    ▼
Drop to Layer 1:
    │   From [D], compare to neighbours [B], [C]
    │   [C] is closest → move to [C]
    │
    ▼
Drop to Layer 0 (bottom):
    │   From [C], compare to all nearby neighbours
    │   [C] → [E] → [F] → check neighbours of each
    │   Converge on the k nearest vectors
    │
    ▼
Results: [F, E, C, G, B] ← top 5 nearest vectors, sorted by similarity

This is MUCH faster than comparing to all N vectors (brute force)
  Brute force: O(N) — check every vector
  HNSW:        O(log N) — follow the graph connections
  
  With 1 million chunks:
    Brute force: 1,000,000 comparisons
    HNSW:        ~20 comparisons (!!!)
```

### The actual search API call

```python
# src/vectorstore/aws_opensearch.py — the search query

body = {
    "size": 5,           # Return top 5 results (top_k)
    "query": {
        "knn": {         # Use k-NN (k-Nearest Neighbours) search
            "embedding": {
                "vector": query_embedding,    # The query vector [0.82, -0.15, ...]
                "k": 5,                       # Find 5 nearest neighbours
            }
        }
    },
}

response = self._client.search(index=self.index_name, body=body)

# Response structure:
{
    "hits": {
        "total": {"value": 5},
        "hits": [
            {
                "_score": 0.95,               # Cosine similarity (0 to 1)
                "_source": {
                    "text": "Refunds are processed within 14 business days...",
                    "document_id": "abc-123",
                    "document_name": "refund-policy.pdf",
                    "chunk_index": 7
                }
            },
            {
                "_score": 0.89,               # Second most similar
                "_source": {
                    "text": "To request a refund, contact customer service...",
                    ...
                }
            },
            # ... 3 more results
        ]
    }
}
```

### OpenSearch API actions used in this project

| Python method | OpenSearch action | When it happens | 🫏 Donkey |
| --- | --- | --- | --- |
| `client.indices.create()` | `PUT /index-name` | Once, at startup (creates the index) | 🫏 On the route |
| `client.index()` | `PUT /index-name/_doc/id` | For each chunk during document ingestion | backpack piece 📦 |
| `client.indices.refresh()` | `POST /index-name/_refresh` | After ingestion (makes new docs searchable) | Pre-sort 📮 |
| `client.search()` | `POST /index-name/_search` | Every chat query (vector similarity search) | GPS warehouse 🗺️ |
| `client.delete_by_query()` | `POST /index-name/_delete_by_query` | When deleting a document | 🫏 On the route |

### How authentication works

OpenSearch Serverless uses **AWS SigV4** authentication (same as all AWS services).
Our code creates a signer:

```python
# src/vectorstore/aws_opensearch.py

credentials = boto3.Session().get_credentials()
auth = AWSV4SignerAuth(credentials, region, "aoss")  # "aoss" = OpenSearch Serverless

# Every HTTP request to OpenSearch gets signed with your AWS credentials
# No API keys needed — uses your IAM role
```

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Azure OpenAI — How GPT Processes Your Request

### What happens when you call Azure OpenAI?

The flow is similar to Bedrock, but with different APIs:

```
Your Python code (src/llm/azure_openai.py)
    │
    ▼
openai SDK serialises your request to JSON
    │
    ▼
HTTPS POST → https://your-resource.openai.azure.com/
              openai/deployments/gpt-4o/chat/completions?api-version=2024-10-01-preview
    │
    ▼
Azure OpenAI Service:
    │
    ├── 1. Validates API key or Managed Identity token
    ├── 2. Checks your deployment quota (tokens per minute)
    ├── 3. Routes to the GPT-4o model instance
    │
    ▼
GPT-4o model (running on Azure's GPU clusters):
    │
    ├── 4. Tokenises using tiktoken (OpenAI's tokeniser)
    │       "What is the refund policy?" → [3923, 374, 279, 32873, 4947, 30]
    │
    ├── 5. Processes through transformer layers (same as Bedrock conceptually)
    │
    ├── 6. Generates output tokens (autoregressive, one at a time)
    │
    ▼
Response flows back through Azure → openai SDK → your code
```

### The actual API call

```python
# src/llm/azure_openai.py — the actual API call

response = await self._client.chat.completions.create(

    # WHICH MODEL — this is your deployment name, not the model name
    # You create deployments in Azure AI Studio
    model="gpt-4o",

    # MESSAGES — the conversation
    messages=[
        {
            "role": "system",          # System instructions
            "content": system_prompt    # "You are a helpful assistant..."
        },
        {
            "role": "user",            # The user's question + context
            "content": user_message    # "Context: [...] Question: What is..."
        }
    ],

    # GENERATION SETTINGS
    temperature=0.1,     # Low = factual and consistent
    max_tokens=2048,     # Max output length
)
```

### Bedrock vs Azure OpenAI — side by side

| Aspect | Bedrock (our AWS code) | Azure OpenAI (our Azure code) | 🫏 Donkey |
| --- | --- | --- | --- |
| Python SDK | `boto3` | `openai` (same as OpenAI's SDK!) | The donkey 🐴 |
| Auth | IAM SigV4 (automatic) | API key or Managed Identity | Stable door 🚪 |
| API style | `converse()` — universal format | `chat.completions.create()` — OpenAI format | The donkey 🐴 |
| Async | ❌ boto3 is sync | ✅ `AsyncAzureOpenAI` | The donkey 🐴 |
| Models | Claude, Llama, Titan, Mistral | GPT-4, GPT-4o, GPT-3.5 | The donkey 🐴 |
| Embedding call | `invoke_model()` — separate API | `embeddings.create()` — same SDK | Stable door 🚪 |
| Streaming | `converse_stream()` | `stream=True` parameter | 🫏 On the route |

### Embedding with Azure OpenAI

```python
# src/llm/azure_openai.py — embedding request

response = await self._client.embeddings.create(
    model="text-embedding-3-small",     # Deployment name
    input=text,                          # Your text
)

embedding = response.data[0].embedding  # → list of 1536 floats
```

Note: Azure OpenAI embeddings have **1536 dimensions** vs Titan's **1024**.
This means they're slightly more expressive but take more storage space.

- 🫏 **Donkey:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for donkeys on the Azure route.

---

## Azure AI Search — How Vector Indexing Works

### What is Azure AI Search?

A fully managed search service (like OpenSearch, but Azure-native). It supports:

- **Full-text search** (keyword matching — like Google)
- **Vector search** (similarity matching — what we use)
- **Hybrid search** (both at once)

### How storing vectors works

```
src/vectorstore/azure_ai_search.py → store_vectors()
    │
    ▼
For each chunk, creates an UPLOAD action:
    │
    ├── Document: {
    │     "id": "abc-123_7",                          ← unique ID
    │     "embedding": [0.0234, -0.0891, ...],        ← 1536 floats
    │     "text": "Refunds are processed within...",   ← original text
    │     "document_id": "abc-123",                    ← source document
    │     "document_name": "refund-policy.pdf"         ← human name
    │   }
    │
    ▼
Azure AI Search receives the batch:
    │
    ├── 1. Validates against the index schema (correct fields? right dimensions?)
    ├── 2. Stores the document
    ├── 3. Updates the vector index (similar to HNSW — Azure uses a proprietary algorithm)
    ├── 4. Updates the inverted index (for text fields)
    └── 5. Document is immediately searchable (no refresh needed, unlike OpenSearch)
```

### The search API call

```python
# src/vectorstore/azure_ai_search.py — the actual search

from azure.search.documents.models import VectorizedQuery

# Create a vector query
vector_query = VectorizedQuery(
    vector=query_embedding,        # Your question as a vector [0.82, -0.15, ...]
    k_nearest_neighbors=5,         # Find 5 most similar
    fields="embedding",            # Search in the "embedding" field
)

# Execute the search
results = search_client.search(
    search_text=None,              # No keyword search (pure vector)
    vector_queries=[vector_query], # Vector search only
)

# Results come back sorted by similarity (highest first)
for result in results:
    print(result["text"])          # The chunk text
    print(result["@search.score"]) # Similarity score (0 to 1)
```

### OpenSearch vs Azure AI Search — side by side

| Aspect | OpenSearch Serverless | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- |
| Vector algorithm | HNSW (open-source) | Proprietary (HNSW-based) | GPS warehouse 🗺️ |
| Dimensions | 1024 (Titan) | 1536 (OpenAI) | The donkey 🐴 |
| Auth | AWS SigV4 | API key or Managed Identity | Stable door 🚪 |
| Min cost | ~$350/month ⚠️ | **Free tier available** ✅ | Feed bill 🌾 |
| Refresh needed? | Yes (`_refresh` after indexing) | No (immediate) | 🫏 On the route |
| Python SDK | `opensearch-py` | `azure-search-documents` | AWS search hub 🔍 |
| Query format | JSON body with `knn` | `VectorizedQuery` object | GPS warehouse 🗺️ |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Amazon DynamoDB — How Key-Value Lookups Work

### What happens when you store a conversation message?

```
src/history/aws_dynamodb.py → add_message()
    │
    ▼
self.table.put_item(Item={
    "session_id": "abc-123",           ← Partition key
    "timestamp": "2026-03-29T10:00",   ← Sort key
    "role": "user",
    "content": "What is the refund policy?"
})
    │
    ▼
DynamoDB receives the request:
    │
    ├── 1. HASH the partition key "abc-123"
    │       → Determines which physical partition stores this item
    │       → DynamoDB has many partitions spread across servers
    │
    ├── 2. WRITE to that partition
    │       → Item is stored sorted by the sort key (timestamp)
    │       → This is why retrieval by session_id is O(1) — DynamoDB
    │         knows exactly which partition to look in
    │
    ├── 3. REPLICATE across 3 Availability Zones
    │       → Your data is stored in 3 separate data centres
    │       → Even if one data centre goes down, your data is safe
    │
    └── 4. Return success
```

### What happens when you retrieve conversation history?

```
src/history/aws_dynamodb.py → get_history()
    │
    ▼
self.table.query(
    KeyConditionExpression=Key("session_id").eq("abc-123"),
    ScanIndexForward=False,    # Newest first
    Limit=10,                  # Last 10 messages
)
    │
    ▼
DynamoDB processes the query:
    │
    ├── 1. HASH "abc-123" → go to the right partition (instant, O(1))
    │
    ├── 2. Within that partition, items are already sorted by timestamp
    │       ScanIndexForward=False → read from the end (newest first)
    │       Limit=10 → stop after 10 items
    │
    ├── 3. Return 10 items (already sorted, no computation needed)
    │
    ▼
Result: Latest 10 messages in the conversation, in ~5ms
```

### Why this is fast

```
DynamoDB partitions (simplified):

Partition A: sessions starting with "a..." → stored on Server 1
Partition B: sessions starting with "b..." → stored on Server 2
Partition C: sessions starting with "c..." → stored on Server 3
...

Query for session_id="abc-123":
  1. Hash "abc-123" → Partition A → Server 1
  2. Binary search within partition for timestamp range
  3. Return results

Total time: 1-5 milliseconds (regardless of table size!)
This is why DynamoDB is called "single-digit millisecond latency"
```

### DynamoDB API actions used

| Python method | DynamoDB API action | When it happens | 🫏 Donkey |
| --- | --- | --- | --- |
| `table.put_item()` | `PutItem` | Storing each message (user + assistant) | 🫏 On the route |
| `table.query()` | `Query` | Loading conversation history for context | Trip log 📒 |
| `table.batch_writer()` | `BatchWriteItem` | Deleting all messages in a session | Trip log 📒 |

- 🫏 **Donkey:** The mechanics of the stable — understanding how each piece fits so you can maintain and extend the system.

---

## Azure Cosmos DB — How Partitioned NoSQL Works

### How it compares to DynamoDB

Cosmos DB and DynamoDB are very similar — both are partitioned NoSQL databases.
The main difference is terminology and pricing:

| Concept | DynamoDB | Cosmos DB | 🫏 Donkey |
| --- | --- | --- | --- |
| Data unit | Item | Document | 🫏 On the route |
| Primary key | Partition key + Sort key | Partition key + id | 🫏 On the route |
| Throughput | Read/Write Capacity Units | Request Units (RU) | 🫏 On the route |
| Query language | Key conditions + filters | **SQL syntax** ✅ | 🫏 On the route |
| Serverless mode | On-demand | Serverless | 🫏 On the route |
| Free tier | 25 GB + 25 RCU/WCU | 1000 RU/s + 25 GB | Free hay 🌿 |

### The big advantage: SQL queries

Cosmos DB lets you write SQL to query JSON documents:

```sql
-- Get last 10 messages for a session (from src/history/azure_cosmosdb.py)
SELECT TOP 10 *
FROM c
WHERE c.session_id = 'abc-123'
ORDER BY c.timestamp DESC
```

This is much more familiar than DynamoDB's `KeyConditionExpression` syntax.

### How partitioning works

```
Cosmos DB container: "conversations"
Partition key: /session_id

Session "abc-123" → Partition A (all messages for this session together)
Session "def-456" → Partition B
Session "ghi-789" → Partition C

When you query WHERE c.session_id = 'abc-123':
  → Cosmos DB knows to look ONLY in Partition A
  → This is called a "single-partition query" — very fast (~5ms)
  → If you query WITHOUT session_id, it scans ALL partitions (slow, expensive)
```

### Request Units (RU) — how Cosmos DB charges

Every operation costs RUs:

| Operation | Cost | 🫏 Donkey |
| --- | --- | --- |
| Read 1 document (1 KB) by id + partition key | 1 RU | 🫏 On the route |
| Write 1 document (1 KB) | 5 RU | 🫏 On the route |
| Query returning 5 documents | ~5-10 RU | 🫏 On the route |
| Cross-partition query | 10-100+ RU ⚠️ | 🫏 On the route |

In serverless mode: $0.25 per million RU. For our conversation history,
each chat exchange costs ~11 RU (5 RU write user + 5 RU write assistant + 1 RU read).

- 🫏 **Donkey:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for donkeys on the Azure route.

---

## How All Services Connect — End-to-End Request Flow

### Full flow: User asks "What is the refund policy?"

Here's every service call that happens, in order, with timing:

```
Browser → POST /api/chat {"message": "What is the refund policy?", "session_id": "abc-123"}
    │
    │ ① LOAD HISTORY (DynamoDB or Cosmos DB)                    ~5ms
    │   → Query by session_id, get last 10 messages
    │   → Result: [{"role": "user", "content": "Hi"}, {"role": "assistant", ...}]
    │
    │ ② EMBED THE QUESTION (Bedrock Titan or Azure OpenAI)     ~100ms
    │   → Send "What is the refund policy?" to embedding model
    │   → Result: [0.82, -0.15, 0.43, ..., 0.91] (1024 or 1536 floats)
    │
    │ ③ SEARCH FOR SIMILAR CHUNKS (OpenSearch or AI Search)     ~50ms
    │   → Send the embedding vector to vector store
    │   → k-NN search: find 5 closest vectors in the index
    │   → Result: 5 text chunks with similarity scores
    │     [
    │       (0.95, "Refunds are processed within 14 business days..."),
    │       (0.89, "To request a refund, contact customer service..."),
    │       (0.82, "Refund requests must include the order number..."),
    │       (0.71, "Products must be in original packaging..."),
    │       (0.68, "Digital products are non-refundable...")
    │     ]
    │
    │ ④ BUILD THE PROMPT                                        ~1ms
    │   → Combine: system instructions + conversation history + 5 chunks + question
    │   → "You are a helpful assistant... Context: [chunk1] [chunk2]...
    │      Question: What is the refund policy?"
    │
    │ ⑤ GENERATE ANSWER (Bedrock Claude or Azure GPT-4o)       ~2000ms
    │   → Send the complete prompt to the LLM
    │   → Model reads context, generates answer
    │   → Result: "Based on the documents, the refund policy states:
    │              - Refunds are processed within 14 business days [chunk 1]
    │              - You must contact customer service [chunk 2]
    │              - Include your order number [chunk 3]..."
    │   → Token usage: 1250 input + 180 output = 1430 total
    │
    │ ⑥ SAVE TO HISTORY (DynamoDB or Cosmos DB)                 ~5ms
    │   → Store user message: {session_id, "user", "What is the refund policy?"}
    │   → Store assistant message: {session_id, "assistant", "Based on the docs..."}
    │
    │ ⑦ RETURN RESPONSE                                         ~1ms
    │
    ▼
Browser ← 200 OK {
    "answer": "Based on the documents, the refund policy states:...",
    "sources": [{"text": "Refunds are processed...", "score": 0.95}, ...],
    "token_usage": {"input": 1250, "output": 180, "cost_usd": 0.0043}
}

TOTAL TIME: ~2.2 seconds (LLM generation dominates)
TOTAL COST: ~$0.004 (less than half a cent per question)
```

### Service call summary

| Step | Service | API action | Time | Cost | 🫏 Donkey |
| --- | --- | --- | --- | --- | --- |
| ① Load history | DynamoDB / Cosmos DB | Query | ~5ms | ~$0.000001 | AWS depot 🏭 |
| ② Embed question | Bedrock Titan / Azure OpenAI | InvokeModel / embeddings.create | ~100ms | ~$0.000002 | The donkey 🐴 |
| ③ Vector search | OpenSearch / AI Search | k-NN search | ~50ms | ~$0.0001 | AWS search hub 🔍 |
| ④ Build prompt | (local, no service call) | — | ~1ms | $0 | Delivery note 📋 |
| ⑤ Generate answer | Bedrock Claude / Azure GPT-4o | Converse / chat.completions | ~2000ms | ~$0.004 | The donkey 🐴 |
| ⑥ Save history | DynamoDB / Cosmos DB | PutItem × 2 | ~5ms | ~$0.000003 | AWS depot 🏭 |
| **Total** | | | **~2.2s** | **~$0.004** | Feed bill 🌾 |

> **Key insight:** The LLM generation (step ⑤) takes 90% of the time and 99% of
> the cost. Everything else is nearly free and nearly instant. This is why
> choosing the right LLM model matters so much — it's where your money goes.

- 🫏 **Donkey:** The step-by-step route map showing every checkpoint the donkey passes from question intake to answer delivery.
