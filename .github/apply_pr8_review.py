from pathlib import Path


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected exactly one match, found {count}")
    return text.replace(old, new, 1)


benchmark = Path("tests/unit/test_final_benchmark_gate.py")
text = benchmark.read_text(encoding="utf-8")

text = replace_once(
    text,
    "printf 'python %s\\\\n' \"$*\" >> \"$COMMAND_LOG\"\n",
    "printf 'python %s\\\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
    "printf 'api_key=%s\\\\n' \"${OPENROUTER_API_KEY:-}\" >> \"${COMMAND_LOG}.env\"\n",
    "python stub API-key log",
)
text = replace_once(
    text,
    "printf '{command} %s\\\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
    "if [[ \"${{FAIL_COMMAND:-}}\" == \"{command}\" ]]; then\n",
    "printf '{command} %s\\\\n' \"$*\" >> \"$COMMAND_LOG\"\n"
    "printf 'api_key=%s\\\\n' \"${{OPENROUTER_API_KEY:-}}\" >> \"${{COMMAND_LOG}}.env\"\n"
    "if [[ \"${{FAIL_COMMAND:-}}\" == \"{command}\" ]]; then\n",
    "shell stub API-key log",
)
text = replace_once(
    text,
    '''    env = os.environ.copy()
    env.update(
        {
            "PATH": f"{fake_bin}:{env['PATH']}",
            "COMMAND_LOG": str(command_log),
            "VCR_REJECTED_ROOT": str(tmp_path / "rejected"),
            "MAX_COST_PER_MODEL_USD": "1",
            "MAX_TOTAL_COST_USD": "2",
        }
    )
''',
    '''    parent_path = os.environ.get("PATH", "/usr/bin:/bin")
    env = {
        "PATH": f"{fake_bin}:{parent_path}",
        "COMMAND_LOG": str(command_log),
        "VCR_REJECTED_ROOT": str(tmp_path / "rejected"),
        "MAX_COST_PER_MODEL_USD": "1",
        "MAX_TOTAL_COST_USD": "2",
    }
''',
    "hermetic workflow environment",
)
text = replace_once(
    text,
    "def test_all_model_workflow_generates_one_report_before_artifact_upload() -> None:\n",
    "def test_paid_workflow_enforces_static_execution_contract_and_step_ordering() -> None:\n",
    "broad test name",
)
text = replace_once(
    text,
    '''    assert result.returncode == 0, result.stderr
    assert command_log.read_text(encoding="utf-8").splitlines() == expected
''',
    '''    assert result.returncode == 0, result.stderr
    assert command_log.read_text(encoding="utf-8").splitlines() == expected
    api_key_log = Path(f"{command_log}.env")
    assert api_key_log.read_text(encoding="utf-8").splitlines() == ["api_key="] * len(
        expected
    )
''',
    "offline API-key assertion",
)
benchmark.write_text(text, encoding="utf-8")

safety = Path("tests/unit/test_paid_recording_safety.py")
text = safety.read_text(encoding="utf-8")
text = replace_once(
    text,
    '''        ("LLM_MAX_COST_PER_MODEL_USD", "0"),
        ("LLM_MAX_COST_PER_MODEL_USD", "-1"),
        ("LLM_MAX_COST_PER_MODEL_USD", "nan"),
        ("LLM_MAX_COST_PER_MODEL_USD", "not-a-number"),
        ("LLM_MAX_TOTAL_COST_USD", "0"),
        ("LLM_MAX_TOTAL_COST_USD", "-1"),
        ("LLM_MAX_TOTAL_COST_USD", "inf"),
        ("LLM_MAX_TOTAL_COST_USD", "not-a-number"),
''',
    '''        ("LLM_MAX_COST_PER_MODEL_USD", "0"),
        ("LLM_MAX_COST_PER_MODEL_USD", "-1"),
        ("LLM_MAX_COST_PER_MODEL_USD", "nan"),
        ("LLM_MAX_COST_PER_MODEL_USD", "inf"),
        ("LLM_MAX_COST_PER_MODEL_USD", ""),
        ("LLM_MAX_COST_PER_MODEL_USD", "not-a-number"),
        ("LLM_MAX_TOTAL_COST_USD", "0"),
        ("LLM_MAX_TOTAL_COST_USD", "-1"),
        ("LLM_MAX_TOTAL_COST_USD", "nan"),
        ("LLM_MAX_TOTAL_COST_USD", "inf"),
        ("LLM_MAX_TOTAL_COST_USD", ""),
        ("LLM_MAX_TOTAL_COST_USD", "not-a-number"),
''',
    "symmetric invalid limit matrix",
)
text = replace_once(
    text,
    '''    def __init__(self, cost: object, *, status_code: int = 200) -> None:
        self.cost = cost
        self.status_code = status_code
''',
    '''    def __init__(
        self,
        cost: object,
        *,
        status_code: int = 200,
        json_error: Exception | None = None,
    ) -> None:
        self.cost = cost
        self.status_code = status_code
        self.json_error = json_error
''',
    "paid response JSON error support",
)
text = replace_once(
    text,
    '''    def json(self) -> dict:
        return {
''',
    '''    def json(self) -> dict:
        if self.json_error is not None:
            raise self.json_error
        return {
''',
    "paid response JSON error raise",
)
marker = '''
def test_direct_live_client_fails_closed_when_provider_cost_is_missing(
'''
new_test = '''
def test_direct_live_client_fails_closed_on_unparsable_http_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    monkeypatch.setenv("LLM_PROVIDER", "openrouter")
    monkeypatch.setenv("LLM_MAX_COST_PER_MODEL_USD", "1")
    monkeypatch.setenv("LLM_MAX_TOTAL_COST_USD", "2")
    calls = 0

    def post(*args: object, **kwargs: object) -> _PaidResponse:
        nonlocal calls
        calls += 1
        return _PaidResponse(
            None,
            status_code=502,
            json_error=ValueError("provider returned HTML"),
        )

    monkeypatch.setattr("tests.llm.client.requests.post", post)
    client = LLMClient(enforce_cost_limits=True)

    with pytest.raises(requests.HTTPError, match="HTTP 502"):
        client.call({"model": MODEL})
    with pytest.raises(PaidCostLimitError, match="could not be cost-accounted"):
        client.raise_if_cost_limit_exceeded()
    with pytest.raises(PaidCostLimitError, match="could not be cost-accounted"):
        client.call({"model": MODEL})
    assert calls == 1


def test_direct_live_client_fails_closed_when_provider_cost_is_missing(
'''
text = replace_once(text, marker, new_test, "unparsable HTTP-error regression")
safety.write_text(text, encoding="utf-8")
