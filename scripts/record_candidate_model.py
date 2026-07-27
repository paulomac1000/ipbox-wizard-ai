#!/usr/bin/env python3
"""Register candidate profiles, then use the hardened resumable recorder."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

candidate_models = importlib.import_module("tests.llm.candidate_models")
candidate_models.register_candidate_models()
record_model = importlib.import_module("scripts.record_model")


if __name__ == "__main__":
    raise SystemExit(record_model.main())
