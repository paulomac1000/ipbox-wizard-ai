from os import environ, getenv

import pytest
from dotenv import load_dotenv


def pytest_addoption(parser):
    parser.addoption(
        "--run-llm",
        action="store_true",
        default=False,
        help="Run LLM scenario tests (requires OPENROUTER_API_KEY)",
    )
    parser.addoption(
        "--vcr-mode",
        action="store",
        default=None,
        choices=["playback", "auto", "record", "none"],
        help="VCR mode: playback (use cassettes), auto (use or record), record (always record), none (bypass VCR)",  # noqa: E501
    )


def pytest_collection_modifyitems(config, items):
    """Propagate VCR mode to environment variable."""
    vcr_mode = config.getoption("--vcr-mode", default=None)
    if vcr_mode:
        environ["VCR_MODE"] = vcr_mode


@pytest.fixture(scope="session", autouse=True)
def load_env():
    load_dotenv()


@pytest.fixture(scope="session")
def openrouter_api_key():
    return getenv("OPENROUTER_API_KEY")


@pytest.fixture(scope="session")
def llm_model():
    return getenv("LLM_MODEL", "google/gemini-3.5-flash")
