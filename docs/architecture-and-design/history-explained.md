# Conversation History — Deep Dive

> `src/history/` — Store and retrieve chat messages so the LLM remembers previous questions.

> **DE verdict: ★★☆☆☆ — The code is DynamoDB/CosmosDB CRUD you've done before.**
> But the _reason_ this exists is pure AI — LLMs are stateless, so you need to
> store conversation history externally and feed it back into every prompt.

> **Related docs:**
> - [Chat Endpoint Deep Dive](api-routes/chat-endpoint-explained.md) — the route that uses history
> - [Document Storage Deep Dive](storage-explained.md) — the other "DE-familiar" storage layer
> - [Infrastructure Deep Dive](infra-explained.md) — Terraform that creates these tables
> - [RAG Concepts → Tokens](../ai-engineering/rag-concepts.md#what-is-a-token) — history = more input tokens = higher cost

---

## Table of Contents

- [Conversation History — Deep Dive](#conversation-history--deep-dive)
  - [Table of Contents](#table-of-contents)
  - [What This Module Does](#what-this-module-does)
  - [Why Does a RAG App Need Conversation History?](#why-does-a-rag-app-need-conversation-history)
    - [The fundamental problem: LLMs have no memory](#the-fundamental-problem-llms-have-no-memory)
    - [The solution: stuff history into the prompt](#the-solution-stuff-history-into-the-prompt)
    - [The DE analogy](#the-de-analogy)
  - [The Three Files](#the-three-files)
  - [base.py — The Interface](#basepy--the-interface)
    - [Key design decisions](#key-design-decisions)
  - [aws\_dynamodb.py — Amazon DynamoDB Implementation](#aws_dynamodbpy--amazon-dynamodb-implementation)
    - [Table schema](#table-schema)
    - [The query pattern](#the-query-pattern)
    - [Batch delete for sessions](#batch-delete-for-sessions)
    - [TTL — auto-cleanup](#ttl--auto-cleanup)
  - [azure\_cosmosdb.py — Azure Cosmos DB Implementation](#azure_cosmosdbpy--azure-cosmos-db-implementation)
    - [Container schema](#container-schema)
    - [Key difference from DynamoDB: Cosmos needs a unique `id`](#key-difference-from-dynamodb-cosmos-needs-a-unique-id)
    - [SQL-like query API](#sql-like-query-api)
    - [Async native](#async-native)
    - [TTL via Terraform](#ttl-via-terraform)
  - [AWS vs Azure — Side-by-Side Comparison](#aws-vs-azure--side-by-side-comparison)
    - [The code patterns side by side](#the-code-patterns-side-by-side)
  - [How History Gets Used in the Chat Pipeline](#how-history-gets-used-in-the-chat-pipeline)
  - [The Token Cost of History](#the-token-cost-of-history)
    - [The trade-off](#the-trade-off)
  - [DE vs AI Engineer — What Each Sees](#de-vs-ai-engineer--what-each-sees)
  - [Self-Check Questions](#self-check-questions)
    - [Answers](#answers)

---

## What This Module Does

One sentence: **Saves every chat message (user questions + AI answers) so the LLM
can see previous conversation turns when answering follow-up questions.**

```
User: "What is the refund policy?"
AI:   "Refunds are processed within 14 days..."

User: "What about digital products?"      ← follow-up — "what about" makes no sense
AI:   ???                                     without knowing the previous topic

With history:
    Prompt includes:
    - Previous: "What is the refund policy?" → "Refunds are processed within 14 days..."
    - Current: "What about digital products?"
    → AI understands "what about" refers to refunds
```

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Why Does a RAG App Need Conversation History?

### The fundamental problem: LLMs have no memory

Every LLM call is **completely independent**. The model doesn't remember what you asked
one second ago. This is unlike a database connection that maintains session state.

```
Call 1: "What is the refund policy?"    → "Refunds are processed within 14 days."
Call 2: "What about digital products?"  → "I don't know what you're referring to." ❌
```

The LLM sees Call 2 in complete isolation. The words "what about" have no referent.

### The solution: stuff history into the prompt

```
Call 2 prompt (with history):

    Previous conversation:
    User: "What is the refund policy?"
    Assistant: "Refunds are processed within 14 days."

    Current question: "What about digital products?"

→ Now the LLM understands: "digital products" + "refund" context = refund policy for digital products
```

This is why conversation history exists — to **simulate memory** by replaying past
messages in every prompt.

### The DE analogy

Think of it like a stored procedure that has no session state:
- Each call gets only its input parameters
- If you want context from previous calls, you must pass it explicitly
- History storage = the table where you log inputs/outputs for replay

- 🫏 **Donkey:** The donkey's trip log — it remembers what was said 3 questions ago so it doesn't re-ask for your address.

---

## The Three Files

```
src/history/
├── base.py              # Abstract interface
├── aws_dynamodb.py      # DynamoDB implementation (partition key = session_id)
└── azure_cosmosdb.py    # Cosmos DB implementation (partition key = session_id)
```

> **📝 Local mode note:** When running with `CLOUD_PROVIDER=local`, conversation
> history is not yet persisted — each server restart starts fresh. The Local
> provider focuses on LLM + vector store. Adding a local history backend
> (e.g., SQLite) would follow the same `BaseConversationHistory` interface.

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## base.py — The Interface

```python
@dataclass
class ConversationMessage:
    """A single message in a conversation."""
    session_id: str     # Groups messages into conversations: "sess-abc-123"
    role: str           # Who sent it: "user" or "assistant"
    content: str        # The message text
    timestamp: datetime # When it was sent (for ordering)
```

The `BaseConversationHistory` abstract class defines three operations:

| Method | What it does | DE equivalent | 🫏 Donkey |
| --- | --- | --- | --- |
| `add_message()` | Store one message | `INSERT INTO messages VALUES (...)` | Donkey-side view of add_message() — affects how the donkey loads, reads, or delivers the cargo |
| `get_history()` | Get last N messages for a session | `SELECT * FROM messages WHERE session_id = ? ORDER BY timestamp DESC LIMIT 10` | Trip log 📒 |
| `delete_session()` | Delete all messages for a session | `DELETE FROM messages WHERE session_id = ?` | Trip log 📒 |

### Key design decisions

**session_id as partition key** — All messages for one conversation live together.
Query pattern is always "get all messages for session X, ordered by time." This is
the same partition key strategy you'd use in DynamoDB for any time-series data.

**role field ("user" / "assistant")** — The LLM API requires messages labelled by role.
When you replay history in the prompt, each message must say who sent it:

```json
[
    {"role": "user", "content": "What is the refund policy?"},
    {"role": "assistant", "content": "Refunds are processed within 14 days..."},
    {"role": "user", "content": "What about digital products?"}
]
```

**limit parameter (default 10)** — You don't replay ALL history, only the last 10
messages. More history = more input tokens = more cost. This is a trade-off between
context quality and cost (explained in detail in [The Token Cost of History](#the-token-cost-of-history)).

- 🫏 **Donkey:** The universal bag fitting — any donkey (AWS, Azure, local) accepts the same harness so you can swap providers without re-training the rider.

---

## aws_dynamodb.py — Amazon DynamoDB Implementation

### Table schema

```
Table: rag-chatbot-dev-conversations
    PK (partition key) = session_id  (String)
    SK (sort key)      = timestamp   (String, ISO-8601)

    Attributes:
        role     (String) — "user" or "assistant"
        content  (String) — the message text

    TTL: expires_at — auto-delete old conversations
```

This is standard DynamoDB single-table design. You've built this before.

### The query pattern

```python
# Get last 10 messages for a session (newest first, then reverse)
response = self.table.query(
    KeyConditionExpression=Key("session_id").eq(session_id),
    ScanIndexForward=False,  # newest first
    Limit=limit,
)
messages.reverse()  # back to chronological order
```

**Why query newest-first then reverse?** Because DynamoDB's `Limit` applies _before_
any offset. If you query oldest-first with Limit=10, you get the _first_ 10 messages
ever — not the _latest_ 10. Querying newest-first with Limit=10 gives you the latest,
then you reverse to put them in chronological order for the prompt.

This is the same pattern you'd use in any time-series DynamoDB query in production DE work.

### Batch delete for sessions

```python
# Delete all messages for a session
with self.table.batch_writer() as batch:
    for item in response.get("Items", []):
        batch.delete_item(Key={"session_id": ..., "timestamp": ...})
```

Standard batch_writer pattern — DynamoDB doesn't have `DELETE WHERE partition_key = X`,
so you query all items first, then batch-delete them.

### TTL — auto-cleanup

```hcl
# In Terraform (infra/aws/dynamodb.tf)
ttl {
    attribute_name = "expires_at"
    enabled        = true
}
```

Conversations auto-expire after 7 days. No cron job needed — DynamoDB handles deletion.
This keeps costs down and avoids storing stale data forever.

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## azure_cosmosdb.py — Azure Cosmos DB Implementation

### Container schema

```
Account: ragchatbotdev-cosmos
Database: rag-chatbot
Container: conversations
    Partition key: /session_id

    Document shape:
    {
        "id": "uuid-auto-generated",        ← Cosmos requires a unique id
        "session_id": "sess-abc-123",        ← partition key
        "role": "user",
        "content": "What is the refund policy?",
        "timestamp": "2026-04-08T14:30:00Z"
    }
```

### Key difference from DynamoDB: Cosmos needs a unique `id`

DynamoDB uses `session_id + timestamp` as a composite key. Cosmos DB requires a
globally unique `id` field, so the code generates a UUID for every message:

```python
item = {
    "id": str(uuid.uuid4()),  # ← Cosmos requirement, DynamoDB doesn't need this
    "session_id": message.session_id,
    "role": message.role,
    "content": message.content,
    "timestamp": message.timestamp.isoformat(),
}
await container.create_item(body=item)
```

### SQL-like query API

Cosmos DB uses SQL syntax for queries — very different from DynamoDB's `Key("pk").eq()`:

```python
query = (
    "SELECT TOP @limit * FROM c "
    "WHERE c.session_id = @session_id "
    "ORDER BY c.timestamp DESC"
)
parameters = [
    {"name": "@limit", "value": limit},
    {"name": "@session_id", "value": session_id},
]
```

This feels more natural if you come from SQL. DynamoDB's `KeyConditionExpression` is
more verbose but more explicit about what operations are allowed on keys.

### Async native

```python
# Cosmos DB SDK is natively async
from azure.cosmos.aio import CosmosClient

# True await — not a thread pool workaround
async for item in container.query_items(query=query, parameters=parameters, partition_key=session_id):
    items.append(item)
```

### TTL via Terraform

```hcl
# In infra/azure/cosmosdb.tf
default_ttl = 604800  # 7 days in seconds
```

Same concept as DynamoDB TTL — conversations auto-expire.

- 🫏 **Donkey:** The Azure hub — Azure AI Search and Cosmos DB serve as the GPS-indexed warehouse and trip-log database for donkeys on the Azure route.

---

## AWS vs Azure — Side-by-Side Comparison

| Aspect | AWS DynamoDB | Azure Cosmos DB | 🫏 Donkey |
| --- | --- | --- | --- |
| **SDK** | `boto3` (sync) | `azure-cosmos` (async native) | Azure trip-log 📒 |
| **Key design** | Composite: `session_id` (PK) + `timestamp` (SK) | `id` (unique) + `session_id` (partition key) | Trip log 📒 |
| **Unique ID** | Not needed — PK+SK is unique | Required — `id` field with UUID | Tracking number stamped on the parcel so the donkey can find it again |
| **Query language** | `KeyConditionExpression` (DynamoDB-specific) | SQL-like syntax (`SELECT`, `WHERE`, `ORDER BY`) | AWS depot 🏭 |
| **Get latest N** | `ScanIndexForward=False, Limit=N` + reverse | `SELECT TOP N ... ORDER BY timestamp DESC` + reverse | Test delivery 🧪 |
| **Batch delete** | `batch_writer()` + loop | `async for` + `delete_item()` one by one | Donkey can run other errands while waiting for the warehouse to respond |
| **TTL** | `expires_at` attribute | `default_ttl` on container (seconds) | Stable stall 🐎 |
| **Cost (serverless)** | ~$0 idle, $1.25/M writes, $0.25/M reads | ~$0 idle, ~$0.28/M RUs | Feed bill 🌾 |
| **Consistency** | Eventually consistent (default) | Session consistency (configured) | Trip log 📒 |

### The code patterns side by side

```python
# AWS: Write a message
self.table.put_item(Item={
    "session_id": message.session_id,
    "timestamp": message.timestamp.isoformat(),
    "role": message.role,
    "content": message.content,
})

# Azure: Write a message
await container.create_item(body={
    "id": str(uuid.uuid4()),              # ← extra field
    "session_id": message.session_id,
    "timestamp": message.timestamp.isoformat(),
    "role": message.role,
    "content": message.content,
})
```

```python
# AWS: Get last 10 messages
response = self.table.query(
    KeyConditionExpression=Key("session_id").eq(session_id),
    ScanIndexForward=False,
    Limit=10,
)

# Azure: Get last 10 messages
query = "SELECT TOP 10 * FROM c WHERE c.session_id = @sid ORDER BY c.timestamp DESC"
async for item in container.query_items(query=query, partition_key=session_id):
    items.append(item)
```

- 🫏 **Donkey:** The AWS depot — DynamoDB and OpenSearch serve as the GPS-indexed warehouse and trip-log database for donkeys running the cloud route.

---

## How History Gets Used in the Chat Pipeline

This is where the AI insight lives — history is fetched _before_ the LLM call and
injected into the prompt:

```
POST /api/chat  {"question": "What about digital products?", "session_id": "sess-abc-123"}
    │
    ├── [1] history.get_history("sess-abc-123", limit=10)
    │       → Returns last 10 messages:
    │         [{"role": "user", "content": "What is the refund policy?"},
    │          {"role": "assistant", "content": "Refunds are processed within 14 days..."}]
    │
    ├── [2] Embed current question → vector
    ├── [3] Search vector store → relevant chunks
    │
    ├── [4] Build prompt:
    │       System: "You are a helpful assistant..."
    │       History: [user: "What is the refund policy?", assistant: "Refunds are..."]
    │       Context: [chunk 1, chunk 2, chunk 3]
    │       Question: "What about digital products?"
    │
    ├── [5] LLM generates answer
    │
    ├── [6] history.add_message(role="user", content="What about digital products?")
    │       history.add_message(role="assistant", content="For digital products, refunds...")
    │
    └── [7] Return response
```

**Steps 6 is critical** — both the question AND the answer are saved. On the next
question, `get_history()` returns all previous turns, including this one.

- 🫏 **Donkey:** The donkey's trip log — it remembers what was said 3 questions ago so it doesn't re-ask for your address.

---

## The Token Cost of History

Here's the AI engineering insight a DE wouldn't think about:

**Every history message becomes input tokens in the next prompt.**

```
Message 1 (user):      "What is the refund policy?"                → ~10 tokens
Message 2 (assistant): "Refunds are processed within 14 days..."   → ~50 tokens
Message 3 (user):      "What about digital products?"              → ~8 tokens
Message 4 (assistant): "For digital products, refunds take 5..."   → ~45 tokens
Message 5 (user):      "Can I get store credit instead?"           → ~10 tokens
─────────────────────────────────────────────────────────────────────
Total history tokens: ~123 input tokens added to EVERY subsequent prompt
```

With the default `limit=10` (10 messages = 5 conversation turns):

| Messages in history | Extra input tokens | Extra cost per query (Claude) | 🫏 Donkey |
| --- | --- | --- | --- |
| 0 (first question) | 0 | $0.000 | Free hay 🌿 |
| 2 (1 turn) | ~60 | $0.00018 | Free hay 🌿 |
| 6 (3 turns) | ~180 | $0.00054 | Free hay 🌿 |
| 10 (5 turns) | ~300 | $0.00090 | Free hay 🌿 |
| 20 (10 turns) | ~600 | $0.00180 | Free hay 🌿 |

**This is why there's a limit.** Without it, a 50-message conversation would add ~1500
tokens to every prompt — tripling the cost per query for diminishing returns.

### The trade-off

| Fewer history messages | More history messages | 🫏 Donkey |
| --- | --- | --- |
| Lower cost per query | Higher cost per query | Feed bill 🌾 |
| Less context for follow-ups | Better understanding of conversation | Trip log 📒 |
| User may need to repeat context | Smooth, natural conversation | Trip log 📒 |
| `limit=4` is minimum for usable follow-ups | `limit=20` is maximum before costs explode | Feed bill 🌾 |

The default `limit=10` is a good balance — 5 conversation turns gives enough context
for most follow-up questions without excessive token costs.

- 🫏 **Donkey:** The donkey's trip log — it remembers what was said 3 questions ago so it doesn't re-ask for your address.

---

## DE vs AI Engineer — What Each Sees

| Aspect | What a DE sees | What an AI Engineer sees | 🫏 Donkey |
| --- | --- | --- | --- |
| `ConversationMessage` model | Standard message table schema | Token budget — each message costs tokens in the next prompt | Cargo unit ⚖️ |
| `add_message()` | Insert row, done | Must save BOTH user and assistant messages for complete replay | Donkey-side view of add_message() — affects how the donkey loads, reads, or delivers the cargo |
| `get_history(limit=10)` | Pagination, standard | Token cost control — limit = max tokens spent on history | Cargo unit ⚖️ |
| `delete_session()` | Cleanup, standard | Privacy + cost — old sessions = wasted storage + prompt bloat | Delivery note 📋 |
| TTL (7 days) | Standard data retention | Context window management — conversations older than 7 days aren't useful | Trip log 📒 |
| `session_id` | Partition key for grouping | Session isolation — one user's history never leaks into another's prompt | Alternative stable 🏗️ |
| Sort by timestamp | Standard ordering | Chronological replay is required — LLM needs messages in order | Donkey replays the trip log in order — out-of-order messages would confuse the next answer |

- 🫏 **Donkey:** Like a well-trained donkey that knows this part of the route by heart — reliable, consistent, and essential to the delivery system.

---

## Self-Check Questions

Test your understanding:

1. **Why do LLMs need external conversation history?** Why can't the LLM just remember?
2. **What happens if you don't include history in the prompt?** What does "What about digital products?" return?
3. **Why is `limit=10` the default?** What's the trade-off?
4. **Why must you save BOTH user and assistant messages?** What breaks if you only save user messages?
5. **A conversation has 50 messages. With `limit=10`, which 10 are used?** The first 10 or the last 10?
6. **How many extra input tokens does 10 history messages add?** Roughly.
7. **Why does Cosmos DB need a UUID `id` field but DynamoDB doesn't?**

### Answers

1. LLMs are stateless — every API call is independent with no memory. History must be stored externally and replayed in the prompt.
2. The LLM sees "What about digital products?" with no context. It would answer generically or say "I don't know what you're referring to."
3. Trade-off: more history = better follow-up understanding but more input tokens (cost). 10 messages (5 turns) is enough for most conversations without excessive cost (~300 extra tokens).
4. The LLM needs to see both sides of the conversation to understand context. If it only sees user messages, it doesn't know what it previously said and may contradict itself.
5. The **last** 10 — query sorts by timestamp DESC with Limit=10, then reverses. Recent context matters more than what was asked 30 messages ago.
6. Roughly 300 tokens (~30 tokens per message × 10 messages). At $0.003/1K tokens (Claude input), that's ~$0.0009 extra per query.
7. DynamoDB uses a composite key (session_id + timestamp) which is naturally unique. Cosmos DB requires a standalone `id` field for document identity.

- 🫏 **Donkey:** A quick quiz for the trainee stable hand — answer these to confirm the key donkey delivery concepts have landed.
