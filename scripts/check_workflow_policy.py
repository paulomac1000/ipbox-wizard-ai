#!/usr/bin/env python3
"""Run the vendored, byte-verified ai-skills workflow policy auditor."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

_REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
_VENDOR_ROOT = _REPOSITORY_ROOT / "vendor" / "ai-skills"
_TOOLS = _VENDOR_ROOT / "skills" / "ci-cd-architect" / "tools"
_CONTRACTS = _VENDOR_ROOT / "contracts"
_POLICY_PATH = _TOOLS / "check_github_actions_policy.py"


def _load_policy() -> ModuleType:
    for directory in (_TOOLS, _CONTRACTS):
        value = str(directory)
        if value not in sys.path:
            sys.path.insert(0, value)

    spec = importlib.util.spec_from_file_location(
        "_ipbox_vendored_github_actions_policy",
        _POLICY_PATH,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load vendored workflow policy from {_POLICY_PATH}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_policy = _load_policy()

Finding = _policy.Finding
audit_workflow = _policy.audit_workflow
audit_repository = _policy.audit_repository
workflow_paths = _policy.workflow_paths
read_utf8_bounded = _policy.read_utf8_bounded
_event_names = _policy._event_names
main = _policy.main


if __name__ == "__main__":
    raise SystemExit(main())
