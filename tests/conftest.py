from __future__ import annotations

import os

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--run-llm", action="store_true", default=False)
    parser.addoption(
        "--vcr-mode",
        choices=("playback", "record", "none"),
        default=None,
    )
    parser.addoption("--llm-model", default=None)
    parser.addoption("--scenario", default=None)


def pytest_configure(config: pytest.Config) -> None:
    if mode := config.getoption("--vcr-mode"):
        os.environ["VCR_MODE"] = mode
    if model := config.getoption("--llm-model"):
        os.environ["LLM_MODEL"] = model


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    if config.getoption("--run-llm"):
        return
    marker = pytest.mark.skip(reason="LLM tests require --run-llm")
    for item in items:
        if "llm" in item.keywords:
            item.add_marker(marker)
