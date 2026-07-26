"""Safely load allowlisted local recording settings from the repository `.env`."""

from __future__ import annotations

import ast
import os
import re
import stat
import sys
from collections.abc import MutableMapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"
_ALLOWED_KEYS = frozenset(
    {
        "OPENROUTER_API_KEY",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "LLM_MAX_COST_PER_MODEL_USD",
        "LLM_MAX_TOTAL_COST_USD",
        "LLM_RECORDING_STARTED_AT",
        "VCR_MODE",
        "VCR_CASSETTES_ROOT",
        "VCR_REJECTED_ROOT",
    }
)
_KEY_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")


def _parse_value(raw: str, *, line_number: int) -> str:
    value = raw.strip()
    if not value:
        return ""
    if value[0] in {'"', "'"}:
        try:
            parsed = ast.literal_eval(value)
        except (SyntaxError, ValueError) as exc:
            raise ValueError(f".env line {line_number}: invalid quoted value") from exc
        if not isinstance(parsed, str):
            raise ValueError(f".env line {line_number}: quoted value must be text")
        return parsed
    if " #" in value:
        value = value.split(" #", 1)[0].rstrip()
    if any(character in value for character in ("\n", "\r", "\0")):
        raise ValueError(f".env line {line_number}: value contains a forbidden character")
    return value


def load_local_env(
    path: Path = DEFAULT_ENV_PATH,
    *,
    environ: MutableMapping[str, str] | None = None,
) -> tuple[str, ...]:
    """Load missing allowlisted variables without evaluating shell syntax.

    Existing process variables always win. Unknown keys are ignored, and the
    file is parsed as data rather than sourced as a shell script.
    """
    target = environ if environ is not None else os.environ
    if not path.exists():
        return ()
    if not path.is_file():
        raise ValueError(f"local env path is not a file: {path}")

    mode = stat.S_IMODE(path.stat().st_mode)
    if mode & (stat.S_IRGRP | stat.S_IROTH):
        print(
            f"WARNING: {path} is readable by group/others; prefer chmod 600 {path}",
            file=sys.stderr,
        )

    loaded: list[str] = []
    for line_number, raw_line in enumerate(path.read_text(encoding="utf-8-sig").splitlines(), 1):
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line.removeprefix("export ").lstrip()
        if "=" not in line:
            raise ValueError(f".env line {line_number}: expected KEY=VALUE")
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not _KEY_PATTERN.fullmatch(key):
            raise ValueError(f".env line {line_number}: invalid variable name {key!r}")
        if key not in _ALLOWED_KEYS or key in target:
            continue
        target[key] = _parse_value(raw_value, line_number=line_number)
        loaded.append(key)
    return tuple(loaded)
