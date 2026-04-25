# Deep Dive: Vector Store Providers — AWS OpenSearch, AWS DynamoDB, Azure AI Search & Local ChromaDB

> **Study order:** #10 · **Difficulty:** ★★☆☆☆ (you know OpenSearch for logs — the new part is *vector search*)  
>
> **Files:** [`src/vectorstore/aws_opensearch.py`](../../src/vectorstore/aws_opensearch.py) · [`src/vectorstore/aws_dynamodb.py`](../../src/vectorstore/aws_dynamodb.py) · [`src/vectorstore/azure_ai_search.py`](../../src/vectorstore/azure_ai_search.py) · [`src/vectorstore/local_chromadb.py`](../../src/vectorstore/local_chromadb.py)  
>
> **Prerequisite:** [#9 — The Vector Store Interface](vectorstore-interface-deep-dive.md)  
>
> **Part of:** [Architecture Overview](../architecture-and-design/architecture.md)

---

## Table of Contents

1. [Why These Files Matter](#why-these-files-matter)
2. [The Three Providers Side by Side](#side-by-side-all-three-providers)
3. [DE Parallel — What You Already Know](#de-parallel--what-you-already-know)
4. [Concept 1: HNSW and Cosine Similarity — How Vector Search Actually Works](#concept-1-hnsw-and-cosine-similarity--how-vector-search-actually-works)
5. [AWS: The Index Schema — k-NN Mapping](#aws-the-index-schema--k-nn-mapping)
6. [AWS: `store_vectors()` — Indexing Documents One by One](#aws-store_vectors--indexing-documents-one-by-one)
7. [AWS: `search()` — The k-NN Query](#aws-search--the-k-nn-query)
8. [AWS: `delete_document()` — Delete by Query](#aws-delete_document--delete-by-query)
9. [AWS: OpenSearch Serverless — Cost and Architecture](#aws-opensearch-serverless--cost-and-architecture)
10. [AWS DynamoDB: The Cheap Alternative — $0/month Vector Store](#aws-dynamodb-the-cheap-alternative--0month-vector-store)
11. [Azure: The Index Schema — SearchIndex with VectorSearch](#azure-the-index-schema--searchindex-with-vectorsearch)
11. [Azure: The Index Schema — SearchIndex with VectorSearch](#azure-the-index-schema--searchindex-with-vectorsearch)
12. [Azure: `store_vectors()` — Batch Upload Documents](#azure-store_vectors--batch-upload-documents)
13. [Azure: `search()` — The VectorizedQuery](#azure-search--the-vectorizedquery)
14. [Azure: `delete_document()` — Search Then Delete Pattern](#azure-delete_document--search-then-delete-pattern)
15. [Azure: AI Search — Cost and Architecture](#azure-ai-search--cost-and-architecture)
16. [Local: The Class Structure — ChromaDB](#local-the-class-structure--chromadb)
17. [Local: `store_vectors()` — Upsert in One Call](#local-store_vectors--upsert-in-one-call)
18. [Local: `search()` — Built-in HNSW](#local-search--built-in-hnsw)
19. [Local: `delete_document()` — Metadata Filtering](#local-delete_document--metadata-filtering)
20. [Cost Comparison — All Three Providers](#cost-comparison--all-three-providers)
21. [Where the Vector Stores Sit in the RAG Pipeline](#where-the-vector-stores-sit-in-the-rag-pipeline)
22. [Self-Test Questions](#self-test-questions)
23. [What to Study Next](#what-to-study-next)

---

## Why These Files Matter

In file #9 you learned the **interface** for storing and searching vectors. These three files are the **implementations** — the actual calls to AWS OpenSearch, Azure AI Search, and local ChromaDB. If the LLM provider files (#8) were "DynamoDB vs CosmosDB vs SQLite calls for an LLM," these files are **"OpenSearch vs Azure Search vs ChromaDB calls for semantic search."**

You may have used OpenSearch for log aggregation in your DE work. Here both platforms are used for a completely different purpose: **finding document chunks that are semantically similar to a question.**

| What you'll learn | DE parallel | 🫏 Donkey |
| --- | --- | --- |
| How to create a vector index on both platforms | How to create an OpenSearch index for logs | AWS search hub — How to create a vector index on both platforms: How to create an OpenSearch index for logs |
| How HNSW (vector search algorithm) works | How an inverted index works for text search | HNSW stadium-sign layers let the GPS warehouse robot find nearest backpack in ~9 jumps |
| How k-NN / vector queries find similar vectors | How Elasticsearch `match` queries find matching documents | K-NN searches the GPS warehouse for the 5 nearest backpack coordinates to the question |
| Cost differences between managed vector stores | Cost differences between DynamoDB on-demand vs provisioned | AWS-side stable yard — Cost differences between managed vector stores: Cost differences between DynamoDB on-demand vs provisioned |

- 🫏 **Donkey:** Understanding why the stable was built this way — every architectural choice is a trade-off the head groom made deliberately.

---

## The Providers Side by Side

| Aspect | AWS OpenSearch Serverless | AWS DynamoDB (cheap) | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **SDK** | `opensearchpy` | `boto3` (already installed) | `azure-search-documents` | OpenSearch sorting office — SDK: opensearchpy · boto3 (already installed) · azure-search-documents |
| **Auth** | AWS SigV4 (IAM roles) | AWS SigV4 (IAM roles) | API key (`AzureKeyCredential`) | Where parcels are dropped at the stable — Auth: AWS SigV4 (IAM roles) · AWS SigV4 (IAM roles) · API key (AzureKeyCredential) |
| **Index creation** | JSON mappings (OpenSearch native) | DynamoDB table (PK/SK) | Python objects (`SearchIndex`, `SearchField`) | OpenSearch sorting office — Index creation: JSON mappings (OpenSearch native) · DynamoDB table (PK/SK) · Python objects (SearchIndex, SearchField) |
| **Vector field type** | `knn_vector` | JSON string (embedding) | `SearchFieldDataType.Collection(Edm.Single)` | Data type declaring this field stores GPS coordinates for the warehouse robot |
| **Dimensions** | 1024 (matches Titan) | Any (auto, stored as JSON) | 1536 (matches text-embedding-3-small) | GPS stamp on the parcel — Dimensions: 1024 (matches Titan) · Any (auto, stored as JSON) · 1536 (matches text-embedding-3-small) |
| **Algorithm** | HNSW via `nmslib` engine | **Brute-force cosine** (in Python) | HNSW via `HnswAlgorithmConfiguration` | HNSW lets the donkey skim stadium signs; brute-force cosine makes it read every shelf label by hand. |
| **Distance metric** | `cosinesimil` | Cosine (numpy) | Cosine (default) | All three GPS warehouses measure 'how close' the same way — cosine angle between the backpack's coordinates. |
| **Store operation** | `index()` one at a time | `batch_writer()` | `upload_documents()` in batches of 1000 | Donkey-side view of Store operation — affects how the donkey loads, reads, or delivers the cargo |
| **Search operation** | `knn` query in JSON body | Query all + numpy cosine | `VectorizedQuery` object | How the GPS warehouse robot finds the 5 nearest backpacks to the question's coordinates |
| **Delete operation** | `delete_by_query()` (native) | GSI query + `batch_writer()` | Search + `delete_documents()` (two-step) | The customer's question that goes on the delivery note |
| **Minimum cost** | **~$350/month** | **~$0/month** (free tier) | **~$75/month** (Basic), Free tier available | Cost of keeping the donkey fed — Minimum cost: ~$350/month · ~$0/month (free tier) · ~$75/month (Basic), Free tier available |
| **Best for** | Production (>10K chunks) | Portfolio / dev (<10K chunks) | Production + dev | OpenSearch scales to millions of backpack chunks; DynamoDB works for under 10,000 |

- 🫏 **Donkey:** Choosing which stable to work with — AWS Bedrock, Azure OpenAI, or a local Ollama barn each offer different donkeys at different prices.

---

## DE Parallel — What You Already Know

```
┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│  OPENSEARCH FOR LOGS (what you know)     │   │  OPENSEARCH FOR VECTORS (AWS impl.)      │
│                                          │   │                                          │
│  Index mapping:                          │   │  Index mapping:                          │
│    "message": {"type": "text"}           │   │    "embedding": {"type": "knn_vector",   │
│    "timestamp": {"type": "date"}         │   │                  "dimension": 1024}      │
│    "level": {"type": "keyword"}          │   │    "text": {"type": "text"}              │
│                                          │   │                                          │
│  Query:                                  │   │  Query:                                  │
│    {"match": {"message": "error 500"}}   │   │    {"knn": {"embedding": {"vector": [...],│
│    → finds docs containing those words   │   │                           "k": 5}}}      │
│                                          │   │    → finds docs with similar vectors      │
│                                          │   │                                          │
│  Search type: KEYWORD (exact words)      │   │  Search type: SEMANTIC (meaning)          │
└──────────────────────────────────────────┘   └──────────────────────────────────────────┘

┌──────────────────────────────────────────┐   ┌──────────────────────────────────────────┐
│  AZURE SEARCH (text search)              │   │  AZURE AI SEARCH FOR VECTORS (Azure impl.)│
│                                          │   │                                          │
│  SearchClient.search(                    │   │  SearchClient.search(                    │
│    search_text="error 500"               │   │    search_text=None,                     │
│  )                                       │   │    vector_queries=[VectorizedQuery(       │
│  → finds docs containing those words     │   │        vector=[...], k=5)]               │
│                                          │   │  )                                       │
│  Search type: KEYWORD                    │   │  → finds docs with similar vectors        │
│                                          │   │  Search type: SEMANTIC                    │
└──────────────────────────────────────────┘   └──────────────────────────────────────────┘
```

- 🫏 **Donkey:** Running multiple donkeys on the same route to confirm that AI engineering and data engineering practices mirror each other.

---

## Concept 1: HNSW and Cosine Similarity — How Vector Search Actually Works

Both AWS and Azure use the **same algorithm** (HNSW) and the **same distance metric** (cosine similarity). This concept applies to both.

### Cosine similarity (the distance metric)

Cosine similarity measures the **angle** between two vectors, not the distance. Two vectors pointing in the same direction have cosine similarity = 1.0 (identical meaning). Two vectors pointing in opposite directions have cosine similarity = 0.0 (completely unrelated).

```
                       "refund policy"
                      ↗ [0.12, -0.45, 0.78]
                    /
                  /  angle = small → similarity = 0.98
                /
              ↗ [0.11, -0.44, 0.79]
              "how to get money back"


              ↗ [0.88, 0.23, -0.56]
             "what's the weather"
              
              angle = large → similarity = 0.15
```

**DE parallel:** In text search, relevance is based on word frequency (TF-IDF). In vector search, relevance is based on the angle between meaning-vectors. The concept of "relevance score" exists in both — it's just calculated differently.

### HNSW (the algorithm)

HNSW stands for **Hierarchical Navigable Small World**. It's the algorithm that makes vector search fast. Without it, searching means comparing your query vector against EVERY stored vector (slow). HNSW builds a graph structure that lets you jump to the right neighbourhood quickly.

```
Without HNSW (brute force):  Compare query against ALL 25,000 vectors → slow (seconds)
With HNSW (indexed):         Navigate the graph to the right area → fast (milliseconds)
```

**DE parallel:** HNSW is to vector search what a B-tree index is to SQL queries. Without it → full table scan. With it → efficient lookup.

Both providers implement HNSW but configure it differently:

| Config | AWS OpenSearch | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- |
| Algorithm | `"name": "hnsw"` in JSON | `HnswAlgorithmConfiguration()` object | How the warehouse measures which backpacks are nearest to the customer's question |
| Engine | `nmslib` | Azure-managed (not configurable) | Azure's hub manages the HNSW engine — you can't pick nmslib like in AWS |
| Search accuracy | `ef_search: 512` | Default (auto-tuned) | Stable broke down — donkey couldn't complete the trip, customer sees an error |
| Distance metric | `"cosinesimil"` | Cosine (default, not specified) | Both warehouses default to cosine — same compass bearing, just spelled differently in the config file. |

- 🫏 **Donkey:** The compass bearing between two GPS coordinates — donkeys pointed the same direction are talking about the same topic.

---

## AWS: The Index Schema — k-NN Mapping

**The code (`aws_opensearch.py`, `_ensure_index()`):**

```python
def _ensure_index(self):
    if not self._client.indices.exists(self.index_name):
        body = {
            "settings": {
                "index": {
                    "knn": True,                          # Enable vector search
                    "knn.algo_param.ef_search": 512,      # Search accuracy
                }
            },
            "mappings": {
                "properties": {
                    "embedding": {
                        "type": "knn_vector",             # ⭐ Vector field
                        "dimension": 1024,                # Must match Titan (1024 floats)
                        "method": {
                            "name": "hnsw",
                            "space_type": "cosinesimil",
                            "engine": "nmslib",
                        },
                    },
                    "text": {"type": "text"},
                    "document_id": {"type": "keyword"},
                    "document_name": {"type": "keyword"},
                    "page_number": {"type": "integer"},
                    "chunk_index": {"type": "integer"},
                }
            },
        }
        self._client.indices.create(self.index_name, body=body)
```

### What each setting means

| Setting | Value | What it does | DE parallel | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| `"knn": True` | Enable | Turns on vector search for this index | Like enabling full-text search | Flips the switch for GPS-coordinate search on this particular warehouse index |
| `"dimension": 1024` | 1024 | The vector size — MUST match Titan | Like column length (`VARCHAR(1024)`) | Every GPS coordinate in this warehouse must have exactly 1024 numbers to work |
| `"hnsw"` | Algorithm | The search algorithm | Like B-tree for regular indexes | How the warehouse measures which backpacks are nearest to the customer's question |
| `"cosinesimil"` | Distance | Measures angle between vectors | Like matching function in text search | Cosine distance calculates how similar two GPS coordinates are by measuring angle |
| `"ef_search": 512` | Accuracy | Nodes to check during search | Like scan depth in a tree index | Stable broke down — donkey couldn't complete the trip, customer sees an error |

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## AWS: `store_vectors()` — Indexing Documents One by One

**The code (`aws_opensearch.py`):**

```python
async def store_vectors(self, document_id, document_name, texts, embeddings, metadatas=None) -> int:
    for i, (text, embedding) in enumerate(zip(texts, embeddings)):
        metadata = metadatas[i] if metadatas else {}
        doc = {
            "embedding": embedding,
            "text": text,
            "document_id": document_id,
            "document_name": document_name,
            "chunk_index": i,
            "page_number": metadata.get("page_number"),
        }
        self._client.index(
            index=self.index_name,
            body=doc,
            id=f"{document_id}_{i}",          # Deterministic ID
        )

    self._client.indices.refresh(self.index_name)  # Make searchable immediately
    return len(texts)
```

**Key observations:**

- Indexes **one at a time** in a loop — like `put_item()` in a loop
- `indices.refresh()` forces immediate searchability (without it, up to 1 second delay)
- For production, you'd use the `_bulk` API — same as DynamoDB's `batch_write_item`

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## AWS: `search()` — The k-NN Query

**The code (`aws_opensearch.py`):**

```python
async def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
    body = {
        "size": top_k,
        "query": {
            "knn": {
                "embedding": {
                    "vector": query_embedding,    # The question vector
                    "k": top_k,                   # How many neighbors
                }
            }
        },
    }

    response = self._client.search(index=self.index_name, body=body)

    results = []
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        results.append(
            VectorSearchResult(
                text=source["text"],
                document_name=source["document_name"],
                score=hit["_score"],              # Cosine similarity (0.0–1.0)
                page_number=source.get("page_number"),
                metadata={...},
            )
        )
    return results
```

**The k-NN query is JSON-based** — you build a dict, send it, parse a dict. Same pattern as every OpenSearch query you've written for logs.

**DE parallel — keyword vs vector search:**

```
OpenSearch TEXT search (logs):              OpenSearch VECTOR search (RAG):
─────────────────────────────               ────────────────────────────────
{"match": {"message": "error"}}             {"knn": {"embedding": {"vector": [...], "k": 5}}}

Finds documents containing "error"          Finds vectors closest to your vector
Scoring: TF-IDF (word frequency)            Scoring: cosine similarity (meaning closeness)
```

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## AWS: `delete_document()` — Delete by Query

**The code (`aws_opensearch.py`):**

```python
async def delete_document(self, document_id: str) -> int:
    body = {"query": {"term": {"document_id": document_id}}}
    response = self._client.delete_by_query(index=self.index_name, body=body)
    deleted = response.get("deleted", 0)
    return deleted
```

**Simple and native.** OpenSearch has a built-in `delete_by_query` — one call deletes all matching documents. This is the same API you'd use for log cleanup.

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## AWS: OpenSearch Serverless — Cost and Architecture

**The connection setup (`aws_opensearch.py`, `__init__()`):**

```python
def __init__(self, endpoint: str, index_name: str, region: str):
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, "aoss")  # "aoss" = OpenSearch Serverless

    self._client = OpenSearch(
        hosts=[{"host": endpoint.replace("https://", ""), "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        timeout=30,
    )
```

| Aspect | Value | 🫏 Donkey |
| --- | --- | --- |
| Auth | AWS SigV4 via IAM roles (`AWSV4SignerAuth`) | Amazon's loading dock — Auth: AWS SigV4 via IAM roles (AWSV4SignerAuth) |
| Service code | `"aoss"` (not `"es"`) | Donkey-side view of Service code — affects how the donkey loads, reads, or delivers the cargo |
| Scaling | Auto-scales with OCUs (OpenSearch Compute Units) | Amazon's index room — Scaling: Auto-scales with OCUs (OpenSearch Compute Units) |
| Minimum OCUs | 4 (2 indexing + 2 search) | Donkey-side view of Minimum OCUs — affects how the donkey loads, reads, or delivers the cargo |
| Minimum cost | **~$350/month** ($0.24/hr × 4 OCUs × 730 hrs) | Cost of keeping the donkey fed — Minimum cost: ~$350/month ($0.24/hr × 4 OCUs × 730 hrs) |

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## AWS DynamoDB: The Cheap Alternative — $0/month Vector Store

**File:** [`src/vectorstore/aws_dynamodb.py`](../../src/vectorstore/aws_dynamodb.py)

OpenSearch Serverless costs ~$350/month minimum. For a portfolio project with < 10,000 document chunks, that's not justified. The DynamoDB vector store provides the **same search results** at **$0/month** by trading HNSW indexing for brute-force cosine similarity in Python.

### How it works

```
OpenSearch:  Query vector → HNSW graph traversal → top_k results     (milliseconds)
DynamoDB:    Query vector → Load ALL vectors → numpy cosine → sort → top_k results  (tens of ms)
```

Brute-force is *more accurate* than HNSW (it checks every vector, not an approximation). It's just slower at scale. For < 10,000 chunks, the difference is negligible.

### Table schema

```
Table: rag-chatbot-vectors
├── PK: collection (S)    ← partition key, groups vectors by collection
├── SK: chunk_id (S)      ← sort key, format: {document_id}#{chunk_index}
├── text (S)              ← the original text chunk
├── document_id (S)       ← which document this chunk belongs to
├── document_name (S)     ← original filename
├── embedding (S)         ← JSON-encoded list of floats
├── chunk_index (N)       ← position within the document
└── page_number (N)       ← page in the original document

GSI: document-id-index
├── PK: collection (S)
└── SK: document_id (S)   ← enables efficient delete_document()
```

**DE parallel:** This is a standard DynamoDB table with a GSI — exactly what you build for customer data in your daily work. The only unusual part is the `embedding` field, which stores a JSON string of 768–1536 floats.

### The search algorithm

```python
# 1. Load all vectors for this collection (DynamoDB Query, not Scan)
all_items = table.query(KeyConditionExpression=Key("collection").eq(name))

# 2. Compute cosine similarity for each chunk
for item in all_items:
    chunk_vec = np.array(json.loads(item["embedding"]))
    similarity = np.dot(query_vec, chunk_vec) / (norm_q * norm_c)

# 3. Sort by similarity, return top_k
results.sort(key=lambda x: x.score, reverse=True)
return results[:top_k]
```

### Performance characteristics

| Chunks in collection | Search latency | Acceptable? | 🫏 Donkey |
| --- | --- | --- | --- |
| 100 | ~10ms | ✅ Instant | Donkey-side view of 100 — affects how the donkey loads, reads, or delivers the cargo |
| 1,000 | ~50ms | ✅ Fast | Donkey-side view of 1,000 — affects how the donkey loads, reads, or delivers the cargo |
| 5,000 | ~200ms | ✅ Acceptable | Donkey-side view of 5,000 — affects how the donkey loads, reads, or delivers the cargo |
| 10,000 | ~500ms | ⚠️ Noticeable | Stable broke down — donkey couldn't complete the trip, customer sees an error |
| 50,000+ | ~2–5s | ❌ Use OpenSearch instead | AWS search hub — 50,000+: ~2–5s · ❌ Use OpenSearch instead |

### How to enable it

Set **one env variable** in `.env`:

```bash
CLOUD_PROVIDER=aws
VECTOR_STORE_TYPE=dynamodb    # ← This overrides OpenSearch with DynamoDB
```

The factory in `chain.py` creates the DynamoDB vector store instead of OpenSearch. Everything else (Bedrock LLM, S3 storage, DynamoDB history) stays the same.

### Cost comparison

| | OpenSearch Serverless | DynamoDB Vector Store | 🫏 Donkey |
| --- | --- | --- | --- |
| Monthly cost | ~$350 | ~$0 (free tier) | Stable's monthly feed bill — Monthly cost: ~$350 · ~$0 (free tier) |
| Search speed | ~5ms (HNSW) | ~50ms (brute-force, 1K chunks) | HNSW stadium signs find backpacks 10× faster than checking every chunk one by one |
| Search accuracy | Approximate (HNSW) | **Exact** (checks every vector) | HNSW GPS shortcuts are approximate; brute-force checks every backpack's exact coordinates |
| Max practical size | Millions of chunks | ~10,000 chunks | OpenSearch's warehouse handles millions of backpacks; DynamoDB slows down above 10,000 |
| New dependency | `opensearch-py` | **None** (boto3 already installed) | AWS search hub — New dependency: opensearch-py · None (boto3 already installed) |
| Best for | Production at scale | Portfolio, development, testing | OpenSearch is the busy city depot; DynamoDB is the cheap shed out back, perfect while you're still learning the routes. |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Azure: The Index Schema — SearchIndex with VectorSearch

**The code (`azure_ai_search.py`, `_ensure_index()`):**

```python
def _ensure_index(self):
    index = SearchIndex(
        name=self.index_name,
        fields=[
            SearchField(name="id", type=SearchFieldDataType.String, key=True),
            SearchField(name="text", type=SearchFieldDataType.String, searchable=True),
            SearchField(name="document_id", type=SearchFieldDataType.String, filterable=True),
            SearchField(name="document_name", type=SearchFieldDataType.String),
            SearchField(name="page_number", type=SearchFieldDataType.Int32),
            SearchField(name="chunk_index", type=SearchFieldDataType.Int32),
            SearchField(
                name="embedding",
                type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
                vector_search_dimensions=1536,               # ⭐ 1536 — matches text-embedding-3-small
                vector_search_profile_name="default-profile",
            ),
        ],
        vector_search=VectorSearch(
            algorithms=[HnswAlgorithmConfiguration(name="default-hnsw")],
            profiles=[VectorSearchProfile(name="default-profile", algorithm_configuration_name="default-hnsw")],
        ),
    )
    self._index_client.create_or_update_index(index)
```

### Side-by-side: AWS vs Azure index creation

| Aspect | AWS OpenSearch | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- |
| **Style** | JSON mappings (dict) | Python objects (`SearchField`, `SearchIndex`) | Donkey-side view of Style — affects how the donkey loads, reads, or delivers the cargo |
| **Vector field** | `"type": "knn_vector"` | `SearchFieldDataType.Collection(Edm.Single)` | Declares a field as GPS coordinates instead of plain text or numbers |
| **Dimensions** | `"dimension": 1024` | `vector_search_dimensions=1536` | AWS expects 1024-digit GPS coordinates; Azure expects 1536-digit coordinates |
| **Algorithm config** | Inline in field mapping | Separate `VectorSearch` + `VectorSearchProfile` | AWS embeds HNSW settings in field JSON; Azure separates them into profile objects |
| **Key field** | Auto-generated `_id` | Explicit `key=True` field | Donkey-side view of Key field — affects how the donkey loads, reads, or delivers the cargo |
| **Create method** | `indices.create(name, body)` | `create_or_update_index(index_obj)` | The actual cargo text inside the backpack the donkey is carrying |

**DE parallel:** AWS OpenSearch is like defining a DynamoDB table with raw CloudFormation JSON. Azure AI Search is like using Terraform resource objects — more structured, more typed, but conceptually the same thing: "create an index with these fields and this algorithm."

### ⚠️ Dimension difference matters

```
AWS:   dimension: 1024  ← because Titan Embeddings v2 produces 1024 floats
Azure: dimensions: 1536 ← because text-embedding-3-small produces 1536 floats
```

The vector store dimensions **must** match the embedding model. If you use Azure's text-embedding-3-small (1536-dim) but point at an OpenSearch index (1024-dim), indexing fails. **You cannot mix providers.**

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Azure: `store_vectors()` — Batch Upload Documents

**The code (`azure_ai_search.py`):**

```python
async def store_vectors(self, document_id, document_name, texts, embeddings, metadatas=None) -> int:
    documents = []
    for i, (text, embedding) in enumerate(zip(texts, embeddings)):
        metadata = metadatas[i] if metadatas else {}
        documents.append({
            "id": f"{document_id}_{i}",
            "text": text,
            "embedding": embedding,
            "document_id": document_id,
            "document_name": document_name,
            "chunk_index": i,
            "page_number": metadata.get("page_number"),
        })

    # Upload in batches of 1000
    batch_size = 1000
    for batch_start in range(0, len(documents), batch_size):
        batch = documents[batch_start:batch_start + batch_size]
        self._search_client.upload_documents(documents=batch)

    return len(texts)
```

### Key differences from AWS

| Aspect | AWS OpenSearch | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- |
| **Approach** | Index one at a time in a loop | Build a list, then upload in batches | Donkey-side view of Approach — affects how the donkey loads, reads, or delivers the cargo |
| **API call** | `client.index()` per document | `upload_documents(batch)` per 1000 docs | Door the customer knocks on — API call: client.index() per document · upload_documents(batch) per 1000 docs |
| **23 chunks** | 23 API calls + 1 refresh | 1 API call (all 23 in one batch) | AWS warehouses each of 23 backpacks separately; Azure loads all 23 in one shipment |
| **Refresh** | Manual `indices.refresh()` needed | Automatic (no refresh call) | How quickly newly-sorted mail shows up on the warehouse shelves |

**DE parallel:** AWS OpenSearch's `index()` in a loop is like DynamoDB's `put_item()` in a loop. Azure's `upload_documents(batch)` is like DynamoDB's `batch_write_item()` but with a 1000-item limit instead of 25.

**Azure is more efficient here** — fewer network round trips for the same number of chunks.

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Azure: `search()` — The VectorizedQuery

**The code (`azure_ai_search.py`):**

```python
async def search(self, query_embedding: list[float], top_k: int = 5) -> list[VectorSearchResult]:
    vector_query = VectorizedQuery(
        vector=query_embedding,
        k_nearest_neighbors=top_k,
        fields="embedding",                    # Which field to search
    )

    results = self._search_client.search(
        search_text=None,                       # ⭐ No text search — vector only
        vector_queries=[vector_query],
    )

    search_results = []
    for result in results:
        search_results.append(
            VectorSearchResult(
                text=result["text"],
                document_name=result["document_name"],
                score=result["@search.score"],  # Cosine similarity
                page_number=result.get("page_number"),
                metadata={...},
            )
        )
    return search_results
```

### Side-by-side: AWS vs Azure search

```python
# AWS OPENSEARCH                                # AZURE AI SEARCH
body = {                                        vector_query = VectorizedQuery(
    "size": top_k,                                  vector=query_embedding,
    "query": {                                      k_nearest_neighbors=top_k,
        "knn": {                                    fields="embedding",
            "embedding": {                      )
                "vector": query_embedding,      results = client.search(
                "k": top_k,                         search_text=None,
            }                                       vector_queries=[vector_query],
        }                                       )
    },
}
response = client.search(index=idx, body=body)

# PARSE RESPONSE                                # PARSE RESPONSE
for hit in response["hits"]["hits"]:            for result in results:
    hit["_score"]                                   result["@search.score"]
    hit["_source"]["text"]                          result["text"]
```

**Key differences:**

| Aspect | AWS OpenSearch | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- |
| **Query style** | JSON body dict | Python objects (`VectorizedQuery`) | AWS takes raw JSON to search the GPS warehouse; Azure uses typed query objects |
| **Text search** | Separate query type (`match`) | `search_text=None` disables text search | The customer's question that goes on the delivery note |
| **Score field** | `hit["_score"]` | `result["@search.score"]` | How confidently the warehouse says 'this backpack matches' — higher = closer GPS hit |
| **Response parsing** | `response["hits"]["hits"]` → `["_source"]` | Direct field access on result object | Label on the original mail item the backpack was sliced from |

**Azure is more Pythonic** — typed objects instead of nested dicts. AWS is more "raw JSON" — same style as regular OpenSearch queries.

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Azure: `delete_document()` — Search Then Delete Pattern

**The code (`azure_ai_search.py`):**

```python
async def delete_document(self, document_id: str) -> int:
    # Step 1: Find all chunks for this document
    results = self._search_client.search(
        search_text="*",
        filter=f"document_id eq '{document_id}'",
        select=["id"],                          # Only fetch the ID field
    )

    # Step 2: Collect the IDs
    doc_ids = [{"id": result["id"]} for result in results]

    if not doc_ids:
        return 0

    # Step 3: Delete by IDs
    self._search_client.delete_documents(documents=doc_ids)
    return len(doc_ids)
```

### Key difference: two-step vs one-step delete

| | AWS OpenSearch | Azure AI Search | 🫏 Donkey |
| --- | --- | --- | --- |
| **Method** | `delete_by_query(filter)` — one call | Search → collect IDs → `delete_documents(ids)` — two calls | Donkey-side view of Method — affects how the donkey loads, reads, or delivers the cargo |
| **Why?** | OpenSearch has native `delete_by_query` | Azure AI Search requires explicit document IDs for deletion | AWS search hub — Why?: OpenSearch has native delete_by_query · Azure AI Search requires explicit document IDs for deletion |
| **DE parallel** | `DELETE FROM table WHERE doc_id = 'x'` | `SELECT id FROM table WHERE doc_id = 'x'` then `DELETE FROM table WHERE id IN (...)` | Donkey-side view of DE parallel — affects how the donkey loads, reads, or delivers the cargo |

This is a design limitation of Azure AI Search — there's no `delete_by_filter` API. You must find the IDs first, then delete them explicitly.

- 🫏 **Donkey:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for donkeys on the Azure route.

---

## Azure: AI Search — Cost and Architecture

**The connection setup (`azure_ai_search.py`, `__init__()`):**

```python
def __init__(self, endpoint: str, api_key: str, index_name: str):
    credential = AzureKeyCredential(api_key)

    self._search_client = SearchClient(
        endpoint=endpoint,
        index_name=index_name,
        credential=credential,
    )
    self._index_client = SearchIndexClient(
        endpoint=endpoint,
        credential=credential,
    )
```

### Two clients, one service

| Client | Purpose | DE parallel | 🫏 Donkey |
| --- | --- | --- | --- |
| `SearchClient` | Data operations (search, upload, delete) | DynamoDB `Table` resource (read/write) | Amazon's loading dock — SearchClient: Data operations (search, upload, delete) · DynamoDB Table resource (read/write) |
| `SearchIndexClient` | Management operations (create/update index) | DynamoDB `client` (create table) | AWS-side stable yard — SearchIndexClient: Management operations (create/update index) · DynamoDB client (create table) |

### Authentication: simple API key

Azure AI Search uses **API keys** — just a string. Much simpler than AWS SigV4 (which requires credential chains, region, service codes).

```python
# AWS (complex)                                  # Azure (simple)
credentials = boto3.Session().get_credentials()  credential = AzureKeyCredential(api_key)
auth = AWSV4SignerAuth(credentials, region, "aoss")
```

**For production:** Azure also supports Managed Identity (Azure RBAC) — similar to IAM roles but configured via `DefaultAzureCredential()`.

### Cost tiers

| Tier | Cost | Storage | Replicas | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Free** | $0/month | 50 MB, 3 indexes | None | No-charge bale from the stable — Free: $0/month · 50 MB, 3 indexes · None |
| **Basic** | ~$75/month | 2 GB | Up to 3 | Fuel-and-feed bill for keeping the donkey and stable running |
| **Standard S1** | ~$250/month | 25 GB | Up to 12 | Fuel-and-feed bill for keeping the donkey and stable running |

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Cost Comparison — All Three Providers

| | AWS OpenSearch Serverless | Azure AI Search (Basic) | **Local ChromaDB** | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Minimum cost** | **~$350/month** | **~$75/month** | **$0/month** | Stable's monthly feed bill — Minimum cost: ~$350/month · ~$75/month · $0/month |
| **Free tier** | ❌ No | ✅ Yes (50 MB, 3 indexes) | ✅ Always free | No-charge bale from the stable — Free tier: ❌ No · ✅ Yes (50 MB, 3 indexes) · ✅ Always free |
| **Scaling** | Auto (OCUs) | Manual (tier upgrade) | Single machine only | How the stable adds or removes donkeys when delivery volume changes |
| **For learning/dev** | Expensive — paying for idle | Cheap — free tier works | **Best — zero cost, zero setup** | Local ChromaDB is a free shelf in your own garage; cloud GPS warehouses charge rent even when no donkey visits. |
| **For production** | Good if already on AWS | Good if already on Azure | Not suitable (no HA, no scaling) | AWS-side stable yard — For production: Good if already on AWS · Good if already on Azure · Not suitable (no HA, no scaling) |

### Why this matters more than LLM cost

From doc #8 (LLM Providers), the LLM cost difference is ~$30/month at 1000 queries/day. The **vector store cost difference is ~$275/month**. The vector store drives the cloud decision more than the LLM. Local ChromaDB eliminates this cost entirely for development.

```
┌────────────────────────────────────────────────────────┐
│  Monthly cost at 1000 queries/day                      │
│                                                        │
│  AWS:   LLM ~$160 + OpenSearch ~$350 = ~$510/month     │
│  Azure: LLM ~$130 + AI Search  ~$75  = ~$205/month     │
│  Local: LLM $0    + ChromaDB   $0    = ~$0/month       │
│                                                        │
│  Azure is ~60% cheaper than AWS (vector store).        │
│  Local is free — perfect for development.              │
└────────────────────────────────────────────────────────┘
```

- 🫏 **Donkey:** The feed bill — how much hay (tokens) the donkey eats per delivery, and how to reduce waste without starving it.

---

## Local: The Class Structure — ChromaDB

ChromaDB is an **embedded vector database** — it runs inside your Python process (no external server needed). Think of it as **SQLite for vectors**.

**The code (`local_chromadb.py`, `__init__`):**

```python
class ChromaDBVectorStore(BaseVectorStore):

    def __init__(
        self,
        collection_name: str = "rag-chatbot-vectors",
        persist_directory: str | None = None,
    ):
        if persist_directory:
            self._client = chromadb.PersistentClient(
                path=persist_directory,
                settings=ChromaSettings(anonymized_telemetry=False),
            )
        else:
            self._client = chromadb.Client(
                settings=ChromaSettings(anonymized_telemetry=False),
            )

        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},   # Same algorithm as cloud providers
        )
```

### Comparison with cloud providers

| Aspect | AWS OpenSearch | Azure AI Search | **Local ChromaDB** | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Client setup** | `OpenSearch(hosts, auth, ssl)` | `SearchClient(endpoint, credential)` | `chromadb.PersistentClient(path, settings)` | OpenSearch sorting office — Client setup: OpenSearch(hosts, auth, ssl) · SearchClient(endpoint, credential) · chromadb.PersistentClient(path, settings) |
| **Auth** | SigV4 (IAM roles) | API key | **None** | Stable's front door — Auth: SigV4 (IAM roles) · API key · None |
| **Index creation** | JSON mappings, explicit dimensions | Python objects, explicit dimensions | **Auto-detect dimensions** | Length of the donkey's GPS coordinate — more digits = finer location, more storage |
| **Algorithm** | HNSW (nmslib engine) | HNSW (Azure-managed) | HNSW (built-in) | All three warehouses use HNSW stadium signs, but Azure's engine is managed automatically |
| **Distance** | `cosinesimil` | Cosine (default) | `cosine` (configured via metadata) | All three GPS warehouses pick backpacks by cosine angle — same bearing, three spellings of the word. |
| **Persistence** | Always (cloud) | Always (cloud) | Optional (in-memory or SQLite) | Stable diary records — Persistence: Always (cloud) · Always (cloud) · Optional (in-memory or SQLite) |

**DE parallel:** ChromaDB is like SQLite — in-memory for speed, persistent for durability. No server to install, no auth to configure. Just `chromadb.PersistentClient(path)` and go.

- 🫏 **Donkey:** Your own backyard barn — no cloud costs, full control, ChromaDB SQLite under the floor.

---

## Local: `store_vectors()` — Upsert in One Call

**The code (`local_chromadb.py`, `store_vectors()`):**

```python
ids = [f"{document_id}_{i}" for i in range(len(texts))]
chunk_metadatas = [{
    "document_id": document_id,
    "document_name": document_name,
    "chunk_index": i,
    "page_number": metadata.get("page_number", 0),
} for i, metadata in ...]

self._collection.upsert(
    ids=ids,
    embeddings=embeddings,
    documents=texts,
    metadatas=chunk_metadatas,
)
```

### Side-by-side: all three providers

| Aspect | AWS OpenSearch | Azure AI Search | **Local ChromaDB** | 🫏 Donkey |
| --- | --- | --- | --- | --- |
| **Method** | `client.index()` per doc | `upload_documents(batch)` | `collection.upsert()` | Donkey-side view of Method — affects how the donkey loads, reads, or delivers the cargo |
| **23 chunks** | 23 API calls + refresh | 1 API call (batch 1000) | **1 Python call** | ChromaDB's local barn loads all 23 backpacks instantly without any network trips |
| **Upsert** | Manual (index with same ID) | Manual (upload overwrites) | **Native** — `upsert()` | Donkey-side view of Upsert — affects how the donkey loads, reads, or delivers the cargo |
| **Refresh** | Manual `indices.refresh()` | Automatic | **Instant** (in-memory) | Stable diary records — Refresh: Manual indices.refresh() · Automatic · Instant (in-memory) |
| **Network** | 23 HTTP requests | 1 HTTP request | **0 HTTP requests** | Stable's front door — Network: 23 HTTP requests · 1 HTTP request · 0 HTTP requests |

- 🫏 **Donkey:** Converting text into GPS coordinates so the warehouse robot can find the nearest shelf in ~9 checks using stadium-sign HNSW layers.

---

## Local: `search()` — Built-in HNSW

**The code (`local_chromadb.py`, `search()`):**

```python
results = self._collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k,
    include=["documents", "metadatas", "distances"],
)

# Convert distance to similarity score
distance = results["distances"][0][i]
score = 1.0 - distance    # ChromaDB returns distance, we want similarity
```

### The distance-to-similarity conversion

ChromaDB returns **distances** (lower = more similar), but our `VectorSearchResult` expects a **similarity score** (higher = more similar). The conversion: `score = 1.0 - distance`.

| Provider | Returns | Score meaning | 🫏 Donkey |
| --- | --- | --- | --- |
| AWS OpenSearch | `_score` (similarity) | Higher = more similar (0.0–1.0) | OpenSearch sorting office — AWS OpenSearch: _score (similarity) · Higher = more similar (0.0–1.0) |
| Azure AI Search | `@search.score` (similarity) | Higher = more similar | Azure's GPS warehouse returns higher scores when backpacks are closer to the question |
| **ChromaDB** | `distances` (distance) | **Lower** = more similar → we convert: `1 - distance` | ChromaDB's local barn returns lower distances for closer backpacks — we invert for consistency |

### Side-by-side: search queries

```python
# AWS OPENSEARCH (JSON body)               # AZURE AI SEARCH (typed objects)
body = {                                    vector_query = VectorizedQuery(
    "size": top_k,                              vector=query_embedding,
    "query": {"knn": {"embedding": {            k_nearest_neighbors=top_k,
        "vector": query_embedding,              fields="embedding",
        "k": top_k,                         )
    }}}                                     results = client.search(
}                                               search_text=None,
resp = client.search(index=idx, body=body)      vector_queries=[vector_query],
                                            )

# LOCAL CHROMADB (Python native)
results = self._collection.query(
    query_embeddings=[query_embedding],
    n_results=top_k,
)
```

**ChromaDB is the most Pythonic** — no JSON to build, no typed query objects. Just pass the embedding and number of results.

- 🫏 **Donkey:** The warehouse robot dispatched to find the right backpack shelf — it uses GPS coordinates (embeddings) to locate the nearest relevant chunks in ~9 hops.

---

## Local: `delete_document()` — Metadata Filtering

**The code (`local_chromadb.py`, `delete_document()`):**

```python
results = self._collection.get(
    where={"document_id": document_id},
    include=[],
)

if results["ids"]:
    self._collection.delete(ids=results["ids"])
```

### Comparison: deletion patterns

| Provider | Approach | Steps | 🫏 Donkey |
| --- | --- | --- | --- |
| AWS OpenSearch | `delete_by_query(filter)` | **1 call** — native filter-delete | Amazon's index room — AWS OpenSearch: delete_by_query(filter) · 1 call — native filter-delete |
| Azure AI Search | `search(filter)` → `delete_documents(ids)` | **2 calls** — find then delete | Azure's warehouse requires two trips: first find the backpack IDs, then delete them |
| **ChromaDB** | `get(where)` → `delete(ids)` | **2 calls** — find then delete | ChromaDB's barn also needs two steps: query for backpack IDs then delete them |

ChromaDB follows the same two-step pattern as Azure AI Search: find the IDs first, then delete by ID.

- 🫏 **Donkey:** The parcels being ingested — split into backpack-sized chunks, GPS-stamped, and shelved in the warehouse for the donkey to retrieve later.

---

## Where the Vector Stores Sit in the RAG Pipeline

```
INGESTION:
  chunks + embeddings → store_vectors() → Vector store index
                                          
  AWS:   aws_opensearch.py → index() one by one → OpenSearch index (1024-dim)
  Azure: azure_ai_search.py → upload_documents() in batch → AI Search index (1536-dim)
  Local: local_chromadb.py → upsert() in one call → ChromaDB collection (768-dim)

QUERY:
  question embedding → search() → vector query → top 5 results

  AWS:   knn query (JSON body)          → response["hits"]["hits"]
  Azure: VectorizedQuery (Python object) → iterate results directly
  Local: collection.query()             → results["documents"][0]

  All three return the same VectorSearchResult → sent to LLM as context
```

- 🫏 **Donkey:** The donkey checks its backpack full of retrieved document chunks before answering — no guessing from memory.

---

## Self-Test Questions

| Question | Answer | Concept it tests | 🫏 Donkey |
| --- | --- | --- | --- |
| "What happens if you set dimension: 512 but your embeddings are 1024 floats?" | Indexing fails — dimension mismatch. Both platforms enforce this. | Dimension matching | GPS warehouse rejects 1024-digit coordinates when configured for 512-digit addresses |
| "What's the difference between `knn` query and `match` query in OpenSearch?" | `match` searches by keywords (text). `knn` searches by vector similarity (meaning). | Semantic vs keyword search | AWS search hub — "What's the difference between knn query and match query in OpenSearch?": match searches by keywords (text). knn searches by vector similarity |
| "Why does Azure need two steps to delete but AWS only needs one?" | Azure AI Search has no `delete_by_filter`. You must find IDs first, then delete them explicitly. OpenSearch has native `delete_by_query`. | API design differences | OpenSearch sorting office — "Why does Azure need two steps to delete but AWS only needs one?": Azure AI Search has no delete_by_filter. You must |
| "Why does Azure use `search_text=None` in vector search?" | The `search()` method supports both text and vector search. `search_text=None` disables text search, so only the vector query runs. | Hybrid search capability | Azure's warehouse can search by GPS coordinates and keywords — None disables keyword search |
| "Could you use Azure AI Search with AWS Bedrock embeddings (Titan, 1024-dim)?" | Technically yes — configure the index for 1024 dimensions. But you'd need cross-cloud networking and auth. Not practical. | Provider coupling | The donkey could in theory pick backpacks from Azure's hub while writing on AWS, but cross-cloud plumbing makes it impractical |
| "Why is OpenSearch Serverless so much more expensive than Azure AI Search?" | Minimum 4 OCUs (2 indexing + 2 search) at $0.24/hr each. Azure Basic is a fixed $75/month. Different pricing models. | Cost architecture | OpenSearch sorting office — "Why is OpenSearch Serverless so much more expensive than Azure AI Search?": Minimum 4 OCUs (2 indexing + 2 search) at |
| "Could you replace either with PostgreSQL + pgvector?" | Yes — pgvector adds vector search to PostgreSQL. Same `BaseVectorStore` interface, different implementation. | Strategy pattern | You could swap in PostgreSQL's pgvector warehouse — same GPS backpack interface, different building |
| "What happens to ChromaDB data when you restart the app?" | In-memory mode: lost. Persistent mode (`CHROMA_PERSIST_DIRECTORY`): saved to SQLite on disk. | Persistence | In-memory barn forgets all backpacks on restart; persistent barn saves SQLite to disk |
| "Why does ChromaDB not need a dimension configuration?" | It auto-detects from the first embedding. The first `upsert()` sets the dimension for the collection. | Dimension management | The local barn auto-detects GPS coordinate length from the first backpack it receives |
| "Why does ChromaDB return distances instead of similarity scores?" | Different convention. Our code converts: `score = 1.0 - distance`. Both OpenSearch and ChromaDB use cosine internally — they just report the result differently. | Score conversion | Amazon's index room — "Why does ChromaDB return distances instead of similarity scores?": Different convention. Our code converts: score = 1.0 - distance. Both OpenSearch |

- 🫏 **Donkey:** Sending the donkey on 25 standard test deliveries (golden dataset) to verify it returns the right packages every time.

---

## What to Study Next

Now that you've seen how vectors are stored and searched on **all three platforms**, study the pipeline that **creates** them:

- **File #11:** [`src/rag/ingestion.py`](ingestion-pipeline-deep-dive.md) — the ETL pipeline that reads documents, chunks them, embeds them, and stores them. This is where your DE skills apply most directly.

📖 **Related docs:**

- [How Services Work → OpenSearch](../architecture-and-design/how-services-work.md#amazon-opensearch-serverless--how-vector-search-works)
- [RAG Concepts → How Vector Search Works](rag-concepts.md#how-vector-search-actually-works)
- [RAG Concepts → Dimensions Must Match](rag-concepts.md#dimensions-must-match-between-model-and-store)
- [Cost Analysis](cost-analysis.md)
- [The Vector Store Interface (file #9)](vectorstore-interface-deep-dive.md)
- [LLM Providers (file #8)](llm-providers-deep-dive.md)

- 🫏 **Donkey:** The route map for tomorrow's training run — follow these signposts to deepen your understanding of the delivery system.
