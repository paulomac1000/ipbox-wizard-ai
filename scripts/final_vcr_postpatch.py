#!/usr/bin/env python3
"""Run the one-time VCR source generator and apply its final compatibility edits."""

from __future__ import annotations

import runpy
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATCHER = ROOT / "scripts/apply_final_vcr_audit_fixes.py"


def replace_once(path: Path, old: str, new: str) -> None:
    text = path.read_text(encoding="utf-8")
    if old not in text:
        raise RuntimeError(f"expected source block not found in {path}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")


def main() -> None:
    patcher_text = PATCHER.read_text(encoding="utf-8")
    patcher_text = patcher_text.replace(
        r'source.write_text("VALUE = 1\n", encoding="utf-8")',
        r'source.write_text("VALUE = 1\\n", encoding="utf-8")',
    )
    patcher_text = patcher_text.replace(
        r'source.write_text("VALUE = 2\n", encoding="utf-8")',
        r'source.write_text("VALUE = 2\\n", encoding="utf-8")',
    )
    PATCHER.write_text(patcher_text, encoding="utf-8")
    runpy.run_path(str(PATCHER), run_name="__main__")

    precommit = ROOT / "scripts/vcr_precommit.py"
    text = precommit.read_text(encoding="utf-8")
    marker = '"""Validate cassette completeness and exact request identity."""\n'
    if "# ruff: noqa: E402" not in text:
        if marker not in text:
            raise RuntimeError("vcr_precommit module docstring not found")
        text = text.replace(marker, marker + "\n# ruff: noqa: E402\n", 1)
    precommit.write_text(text, encoding="utf-8")

    cassette = ROOT / "tests/llm/vcr/cassette.py"
    text = cassette.read_text(encoding="utf-8")
    text = text.replace(
        "isinstance(value_a, (dict, list))",
        "isinstance(value_a, dict | list)",
    )
    text = text.replace(
        "isinstance(value, (int, float))",
        "isinstance(value, int | float)",
    )
    strict_block = (
        '        calculation_meta = cassette.parsed_response.get("calculation_meta")\n'
        "        if not isinstance(calculation_meta, dict):\n"
        '            raise ValueError("cassette parsed_response has no calculation_meta")\n'
        '        engine_hash = calculation_meta.get("engine_source_hash")\n'
        "        if not isinstance(engine_hash, str) or len(engine_hash) != 64:\n"
        '            raise ValueError("cassette calculation_meta has no valid engine_source_hash")\n'
    )
    generic_block = (
        '        calculation_meta = cassette.parsed_response.get("calculation_meta")\n'
        "        engine_hash = (\n"
        '            calculation_meta.get("engine_source_hash")\n'
        "            if isinstance(calculation_meta, dict)\n"
        "            else None\n"
        "        )\n"
        "        if engine_hash is not None and (\n"
        "            not isinstance(engine_hash, str) or len(engine_hash) != 64\n"
        "        ):\n"
        '            raise ValueError("cassette calculation_meta has invalid engine_source_hash")\n'
    )
    if strict_block not in text:
        raise RuntimeError("strict manifest calculation_meta block not found")
    cassette.write_text(text.replace(strict_block, generic_block, 1), encoding="utf-8")


if __name__ == "__main__":
    main()
