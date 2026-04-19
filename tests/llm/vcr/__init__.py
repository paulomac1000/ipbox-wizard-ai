"""
VCR (Virtual Cassette Recorder) module for LLM tests.

This module provides recording and playback functionality for LLM responses,
significantly reducing API costs and enabling deterministic testing.

Usage:
    from tests.llm.vcr import VCRRecorder, VCRConfig, VCRMode
    
    recorder = VCRRecorder(VCRConfig())
    response = recorder.get_or_record(
        scenario_id="01_basic_linear",
        scenario_path=Path("scenarios/01_basic_linear.yaml"),
        prompt=prompt,
        api_call_fn=lambda p: llm_client.call(p),
    )
"""

from .config import VCRConfig, VCRMode
from .fingerprint import compute_fingerprint, fingerprint_changed
from .cassette import Cassette, CassetteManifest
from .recorder import VCRRecorder

__all__ = [
    "VCRConfig",
    "VCRMode",
    "compute_fingerprint",
    "fingerprint_changed",
    "Cassette",
    "CassetteManifest",
    "VCRRecorder",
]
