from __future__ import annotations

import pytest

from visit_monitor_server.services.audit_runtime import (
    AuditProbeSample,
    AuditWindowCoordinator,
    audit_draw,
    deterministic_uniform,
)


def _sample(index: int, *, included: bool = False) -> AuditProbeSample[str, str]:
    return AuditProbeSample(
        opportunity_id=f"opp-{index}",
        probe_timestamp=f"t-{index}",
        primary=f"primary-{index}",
        reference=f"reference-{index}",
        selected=index % 2 == 0,
        audit_included=included,
        inclusion_probability=0.25,
    )


def test_deterministic_uniform_matches_v3_fixed_vector() -> None:
    assert deterministic_uniform("opp-1", seed="seed-v1") == pytest.approx(
        0.8457453414784079
    )
    assert deterministic_uniform("opp-2", seed="seed-v1") == pytest.approx(
        0.08523008482549485
    )


def test_equal_rates_make_selection_change_only_the_stratum_label() -> None:
    selected = audit_draw(
        "opp-2", selected=True, seed="seed-v1", q_selected=0.2, q_omitted=0.2
    )
    omitted = audit_draw(
        "opp-2", selected=False, seed="seed-v1", q_selected=0.2, q_omitted=0.2
    )
    assert selected.uniform_draw == omitted.uniform_draw
    assert selected.included is True
    assert omitted.included is True
    assert selected.inclusion_probability == omitted.inclusion_probability == 0.2
    assert selected.stratum == "selected"
    assert omitted.stratum == "omitted"


def test_zero_omitted_probability_fails_closed() -> None:
    with pytest.raises(ValueError, match="q_omitted"):
        audit_draw(
            "opp-1", selected=False, seed="seed-v1", q_selected=0.2, q_omitted=0.0
        )


def test_nine_probe_window_emits_only_when_future_context_exists() -> None:
    coordinator: AuditWindowCoordinator[str, str] = AuditWindowCoordinator(window_size=9)
    emitted = []
    for index in range(9):
        window = coordinator.add(_sample(index, included=index == 4))
        if window is not None:
            emitted.append(window)
    assert len(emitted) == 1
    assert emitted[0].centre_opportunity_id == "opp-4"
    assert [sample.opportunity_id for sample in emitted[0].samples] == [
        f"opp-{index}" for index in range(9)
    ]
    assert coordinator.completed_centres == ("opp-4",)
    assert coordinator.incomplete_included_centres == ()


def test_overlapping_audit_centres_are_not_collapsed() -> None:
    coordinator: AuditWindowCoordinator[str, str] = AuditWindowCoordinator(window_size=9)
    emitted = []
    for index in range(10):
        window = coordinator.add(_sample(index, included=index in {4, 5}))
        if window is not None:
            emitted.append(window)
    assert [window.centre_opportunity_id for window in emitted] == ["opp-4", "opp-5"]
    assert [sample.opportunity_id for sample in emitted[1].samples] == [
        f"opp-{index}" for index in range(1, 10)
    ]


def test_edge_audit_draws_remain_explicitly_incomplete() -> None:
    coordinator: AuditWindowCoordinator[str, str] = AuditWindowCoordinator(window_size=9)
    for index in range(9):
        coordinator.add(_sample(index, included=index in {0, 4, 8}))
    assert coordinator.completed_centres == ("opp-4",)
    assert coordinator.incomplete_included_centres == ("opp-0", "opp-8")


def test_duplicate_opportunity_id_fails_closed() -> None:
    coordinator: AuditWindowCoordinator[str, str] = AuditWindowCoordinator(window_size=9)
    coordinator.add(_sample(0))
    with pytest.raises(ValueError, match="duplicate"):
        coordinator.add(_sample(0))


def test_window_size_must_be_odd() -> None:
    with pytest.raises(ValueError, match="odd"):
        AuditWindowCoordinator(window_size=8)
