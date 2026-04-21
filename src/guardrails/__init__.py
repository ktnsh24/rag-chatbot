"""
Guardrails — Input/output safety for the RAG pipeline.

Provides multi-layered protection:
    - Input guardrails: block prompt injection, toxic content, PII in queries
    - Output guardrails: redact PII from LLM responses, detect hallucination signals

Implementations:
    - aws_guardrails.py    → Bedrock Guardrails + Amazon Comprehend
    - azure_guardrails.py  → Azure AI Content Safety + Azure AI Language
    - local_guardrails.py  → Regex patterns + rule-based (no cloud needed)
"""
