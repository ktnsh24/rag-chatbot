"""
Evaluation Test Dataset (Golden Dataset)

This YAML-like structure defines the test cases for evaluating RAG quality.
Each case has:
    - question: What the user asks
    - expected_keywords: Words that SHOULD appear in a good answer
    - context_chunks: Simulated retrieval results (text + relevance score)
    - min_retrieval_score: Minimum acceptable retrieval quality
    - min_faithfulness: Minimum acceptable faithfulness

Add new cases whenever you:
    1. Find a question the system answers poorly → fix it → add the case
    2. Upload a new type of document → test key questions from it
    3. Change chunk_size, overlap, or model → verify existing cases still pass

AI Engineering principle: Your golden dataset should GROW over time.
Every bug you fix should become a test case. This is how you build confidence.
"""

GOLDEN_DATASET = [
    {
        "id": "refund_basic",
        "category": "policy",
        "question": "What is the refund policy?",
        "expected_keywords": ["refund", "14", "days", "business"],
        "expected_not_in_answer": ["helicopter", "unicorn", "free money"],
        "context_chunks": [
            ("Refunds are processed within 14 business days of receiving the returned item.", 0.95),
            ("To request a refund, email support@example.com with your order number.", 0.88),
            ("Products must be returned in original, unopened packaging.", 0.82),
        ],
        "min_retrieval_score": 0.8,
        "min_faithfulness": 0.8,
    },
    {
        "id": "refund_digital",
        "category": "policy",
        "question": "Can I get a refund on digital products?",
        "expected_keywords": ["digital", "non-refundable", "final"],
        "expected_not_in_answer": [],
        "context_chunks": [
            ("Digital products and gift cards are non-refundable.", 0.93),
            ("All sales of downloadable content are final.", 0.87),
            ("If a digital product is defective, contact support for a replacement.", 0.75),
        ],
        "min_retrieval_score": 0.7,
        "min_faithfulness": 0.8,
    },
    {
        "id": "shipping_return",
        "category": "logistics",
        "question": "Who pays for return shipping?",
        "expected_keywords": ["shipping", "customer", "responsibility"],
        "expected_not_in_answer": [],
        "context_chunks": [
            ("Return shipping costs are the customer's responsibility.", 0.91),
            ("Free shipping on orders over 50 euros does not apply to returns.", 0.78),
        ],
        "min_retrieval_score": 0.7,
        "min_faithfulness": 0.8,
    },
    {
        "id": "no_context_available",
        "category": "edge_case",
        "question": "What is the meaning of life?",
        "expected_keywords": ["don't have", "information", "documents"],
        "expected_not_in_answer": ["42", "happiness", "purpose"],
        "context_chunks": [
            ("Our company sells electronics and accessories.", 0.15),
        ],
        "min_retrieval_score": 0.0,
        "min_faithfulness": 0.9,
    },
    {
        "id": "ambiguous_question",
        "category": "edge_case",
        "question": "How long?",
        "expected_keywords": [],
        "expected_not_in_answer": [],
        "context_chunks": [
            ("Refunds are processed within 14 business days.", 0.45),
            ("Shipping takes 3-5 business days.", 0.42),
        ],
        "min_retrieval_score": 0.3,
        "min_faithfulness": 0.7,
    },
]
