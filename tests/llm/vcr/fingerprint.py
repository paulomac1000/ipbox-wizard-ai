"""Exact identity of the algorithm, scenario and API request."""

from __future__ import annotations

import hashlib
from pathlib import Path

FINGERPRINT_NAMESPACE = "canonical"
ALGORITHM_PATH = Path(__file__).resolve().parents[3] / "ipbox_algorytm.md"


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def content_hash(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def compute_fingerprint(scenario_path: Path, request_hash: str) -> str:
    material = "\0".join(
        (
            FINGERPRINT_NAMESPACE,
            file_hash(ALGORITHM_PATH),
            file_hash(scenario_path),
            request_hash,
        )
    )
    return f"{FINGERPRINT_NAMESPACE}_{content_hash(material)}"
