import pytest

from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
)
from pollipi_analysis.target_evidence import TargetEvidenceRecord, to_target_evidence


def test_reference_mapping_is_ordinal_not_probability_claim() -> None:
    assert to_target_evidence(NO_ACTIVITY).score == 0.0
    assert to_target_evidence(ENVIRONMENTAL_NOISE).score == 0.0
    assert to_target_evidence(UNCERTAIN_LOCAL_ACTIVITY).score == 0.5
    assert to_target_evidence(STRONG_VISITATION_CANDIDATE).score == 1.0
    assert to_target_evidence(STRONG_VISITATION_CANDIDATE).scale == "ordinal-v14-reference"


def test_environmental_noise_state_is_not_exported_as_nuisance_truth() -> None:
    record = to_target_evidence(ENVIRONMENTAL_NOISE)
    payload = record.to_dict()
    assert payload == {
        "source_state": "environmental_noise",
        "score": 0.0,
        "scale": "ordinal-v14-reference",
        "confirmed_visit": False,
    }
    assert "nuisance" not in payload
    assert "observability" not in payload


def test_target_evidence_can_never_be_marked_confirmed_visit() -> None:
    with pytest.raises(ValueError, match="confirmed visitation"):
        TargetEvidenceRecord(
            source_state=STRONG_VISITATION_CANDIDATE,
            score=1.0,
            confirmed_visit=True,
        )


def test_unknown_state_fails_closed() -> None:
    with pytest.raises(ValueError, match="unsupported PolliPi state"):
        to_target_evidence("visit")  # type: ignore[arg-type]
