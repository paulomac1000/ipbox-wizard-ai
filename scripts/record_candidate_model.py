#!/usr/bin/env python3
"""Register candidate profiles, then use the hardened resumable recorder."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests.llm.candidate_models import register_candidate_models  # noqa: E402

register_candidate_models()

from scripts.record_model import main  # noqa: E402


if __name__ == "__main__":
    raise SystemExit(main())
