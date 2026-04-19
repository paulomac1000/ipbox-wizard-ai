"""
Fingerprint computation for VCR cassettes.

Fingerprint = deterministic hash of:
  - ipbox_algorytm.md content
  - scenario YAML content
  - LLM provider name
  - LLM model name

Change to any component → cassette invalidated → re-record triggered.
"""

from __future__ import annotations

import hashlib
from pathlib import Path


# Prompt template version — bump when prompt format changes
PROMPT_TEMPLATE_VERSION = "1"

# Path to algorithm source
ALGORITHM_PATH = Path(__file__).parent.parent.parent.parent / "ipbox_algorytm.md"


def _file_hash(path: Path) -> str:
    """Compute SHA-256 hash of file content, return first 16 hex chars."""
    if not path.exists():
        return "0000000000000000"
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()[:16]


def _content_hash(content: str) -> str:
    """Compute SHA-256 hash of string content."""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]


def compute_fingerprint(
    scenario_path: Path,
    provider: str,
    model: str,
) -> str:
    """
    Compute fingerprint for (algorithm + scenario + provider + model).
    
    Format: "v{version}_{algo_hash}_{scenario_hash}_{provider}_{model_hash}"
    
    Example: "v1_a3f8b2c1d4e5f6a7_b1c2d3e4f5a6b7c8_google_gemini-2.0-flash"
    """
    algo_hash = _file_hash(ALGORITHM_PATH)
    scenario_hash = _file_hash(scenario_path)
    model_hash = _content_hash(model)[:8]

    return (
        f"v{PROMPT_TEMPLATE_VERSION}"
        f"_{algo_hash}"
        f"_{scenario_hash}"
        f"_{provider}"
        f"_{model_hash}"
    )


def fingerprint_changed(
    stored_fingerprint: str,
    current_fingerprint: str,
) -> bool:
    """Check if fingerprint has changed."""
    return stored_fingerprint != current_fingerprint


def explain_fingerprint_change(
    stored: str,
    current: str,
) -> list[str]:
    """
    Explain what changed between fingerprints.
    
    Returns list of human-readable change descriptions.
    """
    changes = []
    
    stored_parts = stored.split("_")
    current_parts = current.split("_")
    
    if len(stored_parts) < 5 or len(current_parts) < 5:
        return ["Unrecognized fingerprint format"]
    
    labels = [
        "prompt_template_version",
        "algorithm_hash",
        "scenario_hash",
        "provider",
        "model_hash",
    ]
    
    for i, label in enumerate(labels):
        if i < len(stored_parts) and i < len(current_parts):
            if stored_parts[i] != current_parts[i]:
                changes.append(
                    f"{label}: {stored_parts[i]} → {current_parts[i]}"
                )
    
    return changes if changes else ["No changes (fingerprints identical)"]


def get_algorithm_hash() -> str:
    """Get just the algorithm file hash (for manifest)."""
    return _file_hash(ALGORITHM_PATH)