from __future__ import annotations

from pathlib import Path

import pytest

from scripts.vcr_paths import DEFAULT_CASSETTE_ROOT, DEFAULT_REJECTED_ROOT
from tests.llm.vcr.config import VCRConfig


def _clear_vcr_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in (
        "VCR_MODE",
        "LLM_PROVIDER",
        "LLM_MODEL",
        "VCR_CASSETTES_ROOT",
        "VCR_REJECTED_ROOT",
    ):
        monkeypatch.delenv(name, raising=False)


def test_vcr_config_uses_shared_scoped_storage_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _clear_vcr_environment(monkeypatch)

    config = VCRConfig()

    assert config.cassettes_root == DEFAULT_CASSETTE_ROOT.resolve()
    assert config.rejected_root == DEFAULT_REJECTED_ROOT.resolve()


@pytest.mark.parametrize("name", ("VCR_CASSETTES_ROOT", "VCR_REJECTED_ROOT"))
def test_vcr_config_rejects_empty_storage_roots(
    monkeypatch: pytest.MonkeyPatch,
    name: str,
) -> None:
    _clear_vcr_environment(monkeypatch)
    monkeypatch.setenv(name, "   ")

    with pytest.raises(ValueError, match=rf"{name} must not be empty"):
        VCRConfig()


def test_record_all_models_executes_shared_rejected_root_resolver() -> None:
    root = Path(__file__).parents[2]
    shell = (root / "scripts/record_all_models.sh").read_text(encoding="utf-8")
    executable = "\n".join(line for line in shell.splitlines() if not line.lstrip().startswith("#"))

    assert "from scripts.vcr_paths import resolve_rejected_root" in executable
    assert "print(resolve_rejected_root())" in executable
    assert 'export VCR_REJECTED_ROOT="$vcr_rejected_root"' in executable
    assert "python scripts/local_env.py" not in executable
    assert "--get VCR_REJECTED_ROOT" not in executable
    assert "source .env" not in executable
    assert "eval " not in executable
