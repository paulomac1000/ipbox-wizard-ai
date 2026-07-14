"""
VCR Recorder — record and playback logic.

Main responsibilities:
1. Determine if cassette should be used or recorded
2. Execute playback or make API call
3. Parse and cache response data
4. Update manifest
"""

from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path

from ..output_schema import OUTPUT_JSON_SCHEMA
from ..request_spec import LLMRequestSpec
from .cassette import Cassette, CassetteManifest, CassetteMeta, CassetteTurn
from .config import VCRConfig
from .fingerprint import (
    compute_fingerprint,
    explain_fingerprint_change,
    fingerprint_changed,
    get_algorithm_hash,
)


class VCRRecorder:
    """Main VCR interface for record/playback operations."""

    def __init__(self, config: VCRConfig):
        self.config = config
        self.manifest = CassetteManifest.load(config.cassettes_root / "_manifest.yaml")
        self._stats = {
            "playback_hits": 0,
            "recordings": 0,
            "invalidations": 0,
            "errors": 0,
        }

    def get_or_record(
        self,
        scenario_id: str,
        scenario_path: Path,
        prompt: str,
        system_prompt: str = "",
        *,
        api_call_fn: Callable[[str], str],
        scenario_name: str = "",
    ) -> str:
        """
        Get response from cassette or record new one.

        Args:
            scenario_id: Scenario identifier (e.g., "01_basic_linear")
            scenario_path: Path to scenario YAML file
            prompt: Full prompt to send to LLM
            api_call_fn: Function that calls the LLM API
            scenario_name: Human-readable scenario name for metadata

        Returns:
            LLM response string (from cassette or fresh)
        """
        # NONE mode: bypass VCR entirely
        if self.config.is_none:
            return api_call_fn(prompt)

        # Calculate current fingerprint
        current_fp = compute_fingerprint(
            scenario_path=scenario_path,
            provider=self.config.provider,
            model=self.config.model,
            system_prompt=system_prompt,
        )

        cassette_path = self.config.cassette_path(scenario_id)

        # Decide: record or playback?
        should_record = self._should_record(
            scenario_id=scenario_id,
            cassette_path=cassette_path,
            current_fingerprint=current_fp,
        )

        if not should_record:
            # PLAYBACK mode
            return self._playback(cassette_path, scenario_id, prompt, system_prompt=system_prompt)

        if self.config.is_playback:
            # PLAYBACK but cassette missing/stale: FAIL
            raise CassetteNotFoundError(
                f"Cassette for '{scenario_id}' is missing or stale, "
                f"but VCR_MODE=playback prevents recording.\n"
                f"Run with VCR_MODE=auto or VCR_MODE=record to update cassettes.\n"
                f"Fingerprint: {current_fp}"
            )

        # RECORD mode (or AUTO with missing/stale cassette)
        return self._record(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            cassette_path=cassette_path,
            prompt=prompt,
            system_prompt=system_prompt,
            fingerprint=current_fp,
            api_call_fn=api_call_fn,
        )

    def _should_record(
        self,
        scenario_id: str,
        cassette_path: Path,
        current_fingerprint: str,
    ) -> bool:
        """Determine if we need to record a new cassette."""
        # Forced record mode
        if self.config.is_record:
            return True

        # Cassette file doesn't exist
        if not cassette_path.exists():
            print(f"  📼 No cassette for {scenario_id} → will record")
            return True

        # Check manifest for fingerprint (fast path)
        stored_fp = self.manifest.get_fingerprint(scenario_id)
        if stored_fp is None:
            print(f"  📼 No fingerprint in manifest for {scenario_id} → will record")
            return True

        # Fingerprint changed → algorithm or scenario updated
        if fingerprint_changed(stored_fp, current_fingerprint):
            changes = explain_fingerprint_change(stored_fp, current_fingerprint)
            print(f"  📼 Fingerprint changed for {scenario_id}:")
            for change in changes:
                print(f"      → {change}")
            self._stats["invalidations"] += 1
            return True

        # Check staleness (only in AUTO mode)
        if self.config.is_auto and self._is_stale(cassette_path):
            print(
                f"  📼 Cassette {scenario_id} older than {self.config.max_age_days}d → will refresh"
            )
            return True

        return False

    def _is_stale(self, cassette_path: Path) -> bool:
        """Check if cassette is older than max_age_days."""
        if self.config.max_age_days <= 0:
            return False

        try:
            cassette = Cassette.load(cassette_path)
            recorded = datetime.fromisoformat(cassette.meta.recorded_at)
            age = datetime.now(UTC) - recorded
            return age > timedelta(days=self.config.max_age_days)
        except Exception:
            return True  # Corrupted cassette → re-record

    def _playback(
        self, cassette_path: Path, scenario_id: str, prompt: str, system_prompt: str = ""
    ) -> str:
        """Play back response from cassette."""
        cassette = Cassette.load(cassette_path)

        if not cassette.is_valid:
            raise CassetteCorruptedError(f"Cassette {scenario_id} is empty or corrupted")

        # Check prompt hash
        current_prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        stored_prompt_hash = cassette.turns[0].prompt_hash if cassette.turns else ""
        if not stored_prompt_hash:
            raise ValueError(
                f"Cassette {scenario_id} has no prompt_hash — re-record with current format."
            )
        if stored_prompt_hash != current_prompt_hash:
            raise ValueError(
                f"Prompt hash mismatch for '{scenario_id}': "
                f"stored={stored_prompt_hash}, current={current_prompt_hash}. "
                f"This indicates the algorithm or scenario prompt generation has changed. "
                f"Run in record mode to update the cassette."
            )

        # Check system_prompt_hash (allow old cassettes where it's empty)
        if system_prompt:
            current_system_prompt_hash = hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[
                :16
            ]
            stored_system_prompt_hash = (
                cassette.turns[0].system_prompt_hash if cassette.turns else ""
            )
            if not stored_system_prompt_hash:
                raise ValueError(f"Cassette {scenario_id} has no system_prompt_hash — re-record.")
            if stored_system_prompt_hash != current_system_prompt_hash:
                raise ValueError(
                    f"System prompt hash mismatch for '{scenario_id}': "
                    f"stored={stored_system_prompt_hash}, current={current_system_prompt_hash}. "
                    f"This indicates the system prompt has changed. "
                    f"Run in record mode to update the cassette."
                )

        # Check request_hash (v3+ cassettes require it)
        stored_request_hash = cassette.turns[0].request_hash if cassette.turns else ""
        if not stored_request_hash:
            raise ValueError(
                f"Cassette {scenario_id} has no request_hash (format version < 3). "
                f"Re-record with cassette_format_version=3."
            )
        current_spec = LLMRequestSpec(
            provider=self.config.provider,
            model=self.config.model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.0,
            max_tokens=16000,
            json_schema=OUTPUT_JSON_SCHEMA,
        )
        current_request_hash = current_spec.compute_hash()
        if stored_request_hash != current_request_hash:
            raise ValueError(
                f"Request hash mismatch for '{scenario_id}': "
                f"stored={stored_request_hash}, current={current_request_hash}. "
                f"This indicates the full request specification has changed."
            )

        self._stats["playback_hits"] += 1
        recorded_date = cassette.meta.recorded_at[:10]
        print(f"  ▶️  Playback: {scenario_id} (recorded: {recorded_date})")

        return cassette.response

    def _record(
        self,
        scenario_id: str,
        scenario_name: str,
        cassette_path: Path,
        prompt: str,
        system_prompt: str = "",
        *,
        fingerprint: str = "",
        api_call_fn: Callable[[str], str],
    ) -> str:
        """Record new cassette from API call."""
        print(
            f"  🔴 Recording: {scenario_id} "
            f"(provider={self.config.provider}, model={self.config.model})"
        )

        start_time = time.time()

        try:
            response = api_call_fn(prompt)
        except Exception as e:
            self._stats["errors"] += 1
            raise RecordingError(f"Failed to record cassette for {scenario_id}: {e}") from e

        duration = time.time() - start_time

        if not response or not response.strip():
            self._stats["errors"] += 1
            raise RecordingError(f"Empty response for {scenario_id} — cassette not saved.")

        # Create turn with response
        prompt_hash = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]
        spec = LLMRequestSpec(
            provider=self.config.provider,
            model=self.config.model,
            system_prompt=system_prompt,
            user_prompt=prompt,
            temperature=0.0,
            max_tokens=16000,
            json_schema=OUTPUT_JSON_SCHEMA,
        )
        request_hash = spec.compute_hash()
        system_prompt_hash = (
            hashlib.sha256(system_prompt.encode("utf-8")).hexdigest()[:16] if system_prompt else ""
        )

        turn = CassetteTurn(
            role="user",
            prompt=prompt if self.config.save_full_prompt else "",
            response=response,
            prompt_hash=prompt_hash,
            request_hash=request_hash,
            system_prompt_hash=system_prompt_hash,
        )

        # Create metadata
        meta = CassetteMeta(
            scenario_id=scenario_id,
            scenario_name=scenario_name,
            provider=self.config.provider,
            model=self.config.model,
            fingerprint=fingerprint,
            recording_duration_seconds=round(duration, 2),
            prompt_tokens_estimate=len(prompt) // 4,
            response_tokens_estimate=len(response) // 4,
            algorithm_hash=get_algorithm_hash(),
        )

        # Try to parse response for cached sections
        from ..runner import LLMTestRunner

        runner = LLMTestRunner.__new__(LLMTestRunner)
        runner.algorithm_path = "ipbox_algorytm.md"
        parsed = runner._extract_tags(response) if hasattr(runner, "_extract_tags") else {}

        # Build cassette
        cassette = Cassette(
            meta=meta,
            turns=[turn],
            parsed_result_yaml=parsed.get("result"),
            parsed_classifications=parsed.get("classifications"),
            parsed_monthly_W=parsed.get("monthly_W"),
            parsed_tests=parsed.get("tests"),
            parsed_stops_reviews=parsed.get("stops_reviews"),
        )

        # Atomic write: save cassette to temp file, then rename
        import tempfile

        cassette_dir = cassette_path.parent
        cassette_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            mode="w", dir=cassette_dir, suffix=".tmp", prefix=cassette_path.stem + "_", delete=False
        ) as tmp_file:
            cassette.save(Path(tmp_file.name))
        Path(tmp_file.name).replace(cassette_path)

        # Update manifest atomically
        manifest_path = self.config.cassettes_root / "_manifest.yaml"
        self.manifest.update(
            scenario_id=scenario_id,
            fingerprint=fingerprint,
            filename=cassette_path.name,
        )
        with tempfile.NamedTemporaryFile(
            mode="w",
            dir=self.config.cassettes_root,
            suffix=".tmp",
            prefix="_manifest_",
            delete=False,
        ) as tmp_manifest:
            self.manifest.save(Path(tmp_manifest.name))
        Path(tmp_manifest.name).replace(manifest_path)

        self._stats["recordings"] += 1
        print(f"  💾 Saved: {cassette_path.name} ({duration:.1f}s)")

        return response

    @property
    def stats(self) -> dict:
        """Get recording/playback statistics."""
        return dict(self._stats)

    def print_stats(self) -> None:
        """Print session statistics."""
        s = self._stats
        total = s["playback_hits"] + s["recordings"]
        print("\n📼 VCR Stats:")
        print(f"   Playback hits:  {s['playback_hits']}")
        print(f"   Recordings:   {s['recordings']}")
        print(f"   Invalidations: {s['invalidations']}")
        print(f"   Errors:       {s['errors']}")
        if total > 0:
            pct = (s["playback_hits"] / total) * 100
            print(f"   API calls saved: {pct:.0f}%")


# ============================================================================
# Exceptions
# ============================================================================


class CassetteNotFoundError(Exception):
    """Cassette required but not found (in playback mode)."""

    pass


class CassetteCorruptedError(Exception):
    """Cassette file is corrupted or invalid."""

    pass


class RecordingError(Exception):
    """Failed to record cassette."""

    pass
