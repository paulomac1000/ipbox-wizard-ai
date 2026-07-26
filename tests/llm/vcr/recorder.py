"""Fail-closed record/playback implementation."""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..client import LLMResponse
from ..request_spec import LLMRequestSpec
from .cassette import (
    Cassette,
    CassetteManifest,
    CassetteMeta,
    parsed_response_equal_ignoring_meta_timestamp,
)
from .config import VCRConfig
from .fingerprint import compute_fingerprint


class CassetteError(RuntimeError):
    pass


class CassetteMissingError(CassetteError):
    pass


class CassetteStaleError(CassetteError):
    pass


class RecordingRejectedError(CassetteError):
    pass


class VCRRecorder:
    def __init__(self, config: VCRConfig):
        self.config = config
        self.manifest = CassetteManifest.load(config.manifest_path, config.model)

    def get_or_record(
        self,
        *,
        scenario: dict[str, Any],
        scenario_path: Path,
        request: LLMRequestSpec,
        api_call: Callable[[LLMRequestSpec], LLMResponse] | None,
        validate_response: Callable[[str], dict[str, Any]],
    ) -> tuple[LLMResponse, dict[str, Any]]:
        scenario_id = str(scenario["meta"]["id"])
        request_hash = request.request_hash()
        fingerprint = compute_fingerprint(scenario_path, request_hash)
        path = self.config.cassette_path(scenario_id)

        if self.config.is_playback:
            return self._playback(path, scenario_id, request_hash, fingerprint, validate_response)
        if api_call is None:
            raise ValueError("record/none mode requires an API callback")
        if self.config.is_none:
            response = api_call(request)
            self._require_complete(response)
            self._require_requested_model(response, request.model)
            parsed = validate_response(response.content)
            return response, parsed
        return self._record(
            path=path,
            scenario=scenario,
            request=request,
            request_hash=request_hash,
            fingerprint=fingerprint,
            api_call=api_call,
            validate_response=validate_response,
        )

    def _playback(
        self,
        path: Path,
        scenario_id: str,
        request_hash: str,
        fingerprint: str,
        validate_response: Callable[[str], dict[str, Any]],
    ) -> tuple[LLMResponse, dict[str, Any]]:
        if not path.exists():
            raise CassetteMissingError(
                f"Missing cassette for {scenario_id} and model {self.config.model}"
            )
        cassette = Cassette.load(path)
        if cassette.meta.requested_model != self.config.model:
            raise CassetteStaleError("Cassette requested_model does not match LLM_MODEL")
        if cassette.meta.returned_model != self.config.model:
            raise CassetteStaleError("Cassette returned_model does not match LLM_MODEL")
        if cassette.meta.request_hash != request_hash:
            raise CassetteStaleError("Cassette request hash does not match the exact request")
        if cassette.meta.fingerprint != fingerprint:
            raise CassetteStaleError("Cassette fingerprint is stale")
        entry = self.manifest.entries.get(scenario_id)
        if not isinstance(entry, dict):
            raise CassetteStaleError("Cassette is missing from the model manifest")
        if entry.get("file") != path.name:
            raise CassetteStaleError("Manifest filename mismatch")
        if entry.get("request_hash") != request_hash or entry.get("fingerprint") != fingerprint:
            raise CassetteStaleError("Manifest identity mismatch")
        parsed = validate_response(cassette.response)
        if not parsed_response_equal_ignoring_meta_timestamp(parsed, cassette.parsed_response):
            raise CassetteStaleError("Stored parsed_response differs from reparsed response")
        response = LLMResponse(
            content=cassette.response,
            request_id=cassette.meta.request_id,
            requested_model=cassette.meta.requested_model,
            returned_model=cassette.meta.returned_model,
            finish_reason=cassette.meta.finish_reason,
            native_finish_reason=cassette.meta.native_finish_reason,
            system_fingerprint=cassette.meta.system_fingerprint,
            prompt_tokens=cassette.meta.prompt_tokens,
            completion_tokens=cassette.meta.completion_tokens,
            total_tokens=cassette.meta.total_tokens,
            cost=cassette.meta.cost,
        )
        try:
            self._require_complete(response)
        except RecordingRejectedError as exc:
            raise CassetteStaleError(
                f"Cassette finish_reason must be 'stop', got {response.finish_reason!r}"
            ) from exc
        return response, parsed

    def _record(
        self,
        *,
        path: Path,
        scenario: dict[str, Any],
        request: LLMRequestSpec,
        request_hash: str,
        fingerprint: str,
        api_call: Callable[[LLMRequestSpec], LLMResponse],
        validate_response: Callable[[str], dict[str, Any]],
    ) -> tuple[LLMResponse, dict[str, Any]]:
        scenario_id = str(scenario["meta"]["id"])
        if path.exists():
            try:
                return self._playback(
                    path,
                    scenario_id,
                    request_hash,
                    fingerprint,
                    validate_response,
                )
            except CassetteError as exc:
                raise CassetteStaleError(
                    "Refusing to overwrite an existing cassette. Validate the change, "
                    "delete the stale cassette explicitly, and record again."
                ) from exc
        if scenario_id in self.manifest.entries:
            raise CassetteStaleError(
                "Manifest entry exists without its cassette. Repair or delete the stale "
                "entry explicitly before recording."
            )

        started = time.monotonic()
        response = api_call(request)
        duration = time.monotonic() - started
        try:
            self._require_complete(response)
        except RecordingRejectedError:
            self._save_rejected(scenario, request_hash, response, "incomplete finish reason")
            raise
        if response.returned_model != request.model:
            reason = (
                f"returned_model={response.returned_model!r} does not match "
                f"requested model {request.model!r}"
            )
            self._save_rejected(scenario, request_hash, response, reason)
            raise RecordingRejectedError(reason)
        try:
            parsed = validate_response(response.content)
        except Exception as exc:
            self._save_rejected(scenario, request_hash, response, str(exc))
            raise RecordingRejectedError(
                f"Response failed schema/semantic validation; cassette not saved: {exc}"
            ) from exc

        meta = CassetteMeta(
            scenario_id=scenario_id,
            scenario_name=str(scenario["meta"]["name"]),
            provider=self.config.provider,
            requested_model=request.model,
            returned_model=response.returned_model,
            fingerprint=fingerprint,
            request_hash=request_hash,
            recorded_at=datetime.now(UTC).isoformat(),
            request_id=response.request_id,
            finish_reason=response.finish_reason,
            native_finish_reason=response.native_finish_reason,
            system_fingerprint=response.system_fingerprint,
            prompt_tokens=response.prompt_tokens,
            completion_tokens=response.completion_tokens,
            total_tokens=response.total_tokens,
            cost=response.cost,
            recording_duration_seconds=round(duration, 3),
        )
        cassette = Cassette(meta=meta, response=response.content, parsed_response=parsed)
        cassette.save(path)
        self.manifest.update(cassette, path.name)
        self.manifest.save(self.config.manifest_path)
        return response, parsed

    @staticmethod
    def _require_complete(response: LLMResponse) -> None:
        if response.finish_reason != "stop":
            raise RecordingRejectedError(
                f"Response finish_reason={response.finish_reason!r}; response rejected"
            )

    @staticmethod
    def _require_requested_model(response: LLMResponse, requested_model: str) -> None:
        if response.returned_model != requested_model:
            raise RecordingRejectedError(
                f"returned_model={response.returned_model!r} does not match "
                f"requested model {requested_model!r}"
            )

    def _save_rejected(
        self,
        scenario: dict[str, Any],
        request_hash: str,
        response: LLMResponse,
        reason: str,
    ) -> None:
        model_dir = self.config.rejected_root / self.config.model_slug
        model_dir.mkdir(parents=True, exist_ok=True)
        scenario_id = str(scenario["meta"]["id"])
        path = model_dir / f"{scenario_id}.json"
        path.write_text(
            json.dumps(
                {
                    "scenario_id": scenario_id,
                    "model": self.config.model,
                    "request_hash": request_hash,
                    "reason": reason,
                    "response": response.content,
                    "metadata": {
                        "request_id": response.request_id,
                        "returned_model": response.returned_model,
                        "finish_reason": response.finish_reason,
                        "native_finish_reason": response.native_finish_reason,
                        "prompt_tokens": response.prompt_tokens,
                        "completion_tokens": response.completion_tokens,
                        "total_tokens": response.total_tokens,
                        "cost": response.cost,
                    },
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
