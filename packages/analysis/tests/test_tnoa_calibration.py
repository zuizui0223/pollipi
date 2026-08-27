from __future__ import annotations

from pathlib import Path

import pytest

from pollipi_analysis.tnoa_calibration import (
    assert_not_runtime_usable,
    load_manifest,
    validate_unfrozen_manifest,
)

ROOT = Path(__file__).resolve().parents[3]
MANIFEST = ROOT / "calibration" / "tnoa_field_calibration_unfrozen_v1.json"


def test_unfrozen_manifest_has_no_field_thresholds() -> None:
    payload = load_manifest(MANIFEST)
    validate_unfrozen_manifest(payload)
    assert payload["target"]["high_threshold"] is None
    assert payload["nuisance"]["familywise_false_attribution_alpha"] is None
    assert payload["observability"]["support_rule"] is None
    assert payload["coupled"]["enabled_for_target_rescue"] is False
    assert payload["target_absence"]["channel_status"] == "unavailable"


def test_unfrozen_manifest_cannot_drive_runtime() -> None:
    payload = load_manifest(MANIFEST)
    with pytest.raises(RuntimeError, match="not frozen"):
        assert_not_runtime_usable(payload)
