"""
Test Data Configuration Loader

Loads document-specific test data from YAML config files.
This allows swapping test-policy.txt for any other document
by just editing a YAML file — no Python code changes needed.

Usage:
    from config.test_data_loader import load_test_config, get_default_config_path  # noqa: E501

    config = load_test_config()  # loads default (test-policy.yaml)
    config = load_test_config("/path/to/my-document.yaml")  # custom config
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


def get_default_config_path() -> Path:
    """Return path to the default test-policy.yaml config."""
    return Path(__file__).resolve().parent / "test-data" / "test-policy.yaml"


def load_test_config(config_path: str | Path | None = None) -> dict[str, Any]:
    """Load test data configuration from a YAML file.

    Args:
        config_path: Path to a YAML config file. If None, loads the default
                     test-policy.yaml.

    Returns:
        Dictionary with keys: document, golden_dataset, lab_questions
    """
    config_path = get_default_config_path() if config_path is None else Path(config_path)

    # If path doesn't exist, try resolving as a filename in the test-data/ dir
    if not config_path.exists():
        test_data_dir = Path(__file__).resolve().parent / "test-data"
        candidate = test_data_dir / config_path.name
        if candidate.exists():
            config_path = candidate

    if not config_path.exists():
        raise FileNotFoundError(
            f"Test data config not found: {config_path}\n"
            f"Tried also: scripts/config/test-data/{config_path.name}\n"
            f"Create one by copying: cp scripts/config/test-data/test-policy.yaml scripts/config/test-data/my-document.yaml"
        )

    with open(config_path) as f:
        config = yaml.safe_load(f)

    # Validate required top-level keys
    required_keys = {"document", "golden_dataset", "lab_questions"}
    missing = required_keys - set(config.keys())
    if missing:
        raise ValueError(f"Config file missing required keys: {missing}")

    return config


def golden_dataset_from_config(config: dict[str, Any]) -> list[dict[str, Any]]:
    """Convert YAML golden dataset format to the Python format expected by the evaluator.

    Transforms context_chunks from {text, score} dicts to (text, score) tuples.
    """
    dataset = []
    for case in config["golden_dataset"]:
        entry = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected_keywords": case.get("expected_keywords", []),
            "expected_not_in_answer": case.get("expected_not_in_answer", []),
            "context_chunks": [
                (chunk["text"], chunk["score"])
                for chunk in case.get("context_chunks", [])
            ],
            "min_retrieval_score": case.get("min_retrieval_score", 0.7),
            "min_faithfulness": case.get("min_faithfulness", 0.8),
        }
        dataset.append(entry)
    return dataset


def lab_questions_from_config(config: dict[str, Any]) -> dict[str, Any]:
    """Return the lab_questions section of the config."""
    return config.get("lab_questions", {})
