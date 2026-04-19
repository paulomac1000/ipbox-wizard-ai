#!/usr/bin/env python3
"""
VCR Pre-commit Check.

Validates that cassettes are up-to-date with algorithm changes.
Blocks commit if algorithm changed but cassettes are stale.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.llm.vcr import VCRConfig, CassetteManifest, compute_fingerprint


def check_vcr_freshness() -> int:
    """Check if cassettes are fresh. Returns 0 if OK, 1 if stale."""
    config = VCRConfig()
    manifest = CassetteManifest.load(config.manifest_path)
    
    scenarios_dir = Path("tests/llm/scenarios")
    algorithm_path = Path("ipbox_algorytm.md")
    
    if not scenarios_dir.exists():
        print("⚠️  No scenarios directory found")
        return 0
    
    stale = []
    
    for scenario_file in sorted(scenarios_dir.glob("*.yaml")):
        scenario_id = scenario_file.stem
        
        current_fp = compute_fingerprint(
            scenario_path=scenario_file,
            provider=config.provider,
            model=config.model,
        )
        
        stored_fp = manifest.get_fingerprint(scenario_id)
        
        if stored_fp is None:
            stale.append((scenario_id, "no cassette recorded"))
            continue
        
        if stored_fp != current_fp:
            stale.append((scenario_id, f"fingerprint changed"))
    
    if stale:
        print("❌ VCR cassettes are STALE:")
        for sid, reason in stale:
            print(f"   - {sid}: {reason}")
        print("\n💡 To update cassettes, run:")
        print("   VCR_MODE=record pytest tests/llm/ -v --run-llm --tb=short")
        return 1
    
    print("✅ All VCR cassettes are fresh")
    return 0


def main() -> int:
    """Main entry point."""
    # Check if algorithm was modified
    algorithm_path = Path("ipbox_algorytm.md")
    
    if not algorithm_path.exists():
        print("Algorithm file not found in current directory")
        return 0
    
    # Only check if we're in a git repo with changes
    import subprocess
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        changed_files = result.stdout.strip().split("\n")
        
        if "ipbox_algorytm.md" in changed_files:
            print("📝 Algorithm file modified — checking cassette freshness...")
            return check_vcr_freshness()
    except Exception:
        # Not a git repo or git not available
        pass
    
    return 0


if __name__ == "__main__":
    sys.exit(main())