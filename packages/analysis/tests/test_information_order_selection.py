from __future__ import annotations

from pollipi_analysis.information_order_selection import (
    Exposure,
    augmentation_refines,
    compatible_indices,
    exposure_denominator_ledger,
    full_reference_ledger,
    postprocessing_can_separate,
    postprocessing_expands,
    selected_event_log,
    selected_reference_log,
    shadow_count,
    shadow_prevalence,
)


def test_side_information_refines_fiber() -> None:
    worlds = (
        ("same-primary", "ref-a", "theta-a"),
        ("same-primary", "ref-b", "theta-b"),
        ("other-primary", "ref-a", "theta-c"),
    )
    primary = lambda w: w[0]
    reference = lambda w: w[1]

    assert augmentation_refines(worlds, primary, reference, 0)
    assert compatible_indices(worlds, primary, 0) == frozenset({0, 1})
    assert compatible_indices(worlds, lambda w: (w[0], w[1]), 0) == frozenset({0})


def test_deterministic_postprocessing_expands_fiber() -> None:
    worlds = ("T", "U-overlap", "N")
    rich = lambda w: w
    binary = lambda x: 1 if x in {"T", "U-overlap"} else 0

    assert postprocessing_expands(worlds, rich, binary, 0)
    assert compatible_indices(worlds, rich, 0) == frozenset({0})
    assert compatible_indices(worlds, lambda w: binary(rich(w)), 0) == frozenset({0, 1})


def _worlds_same_log_different_shadow_truth():
    common_entered = Exposure("e0", True, 1, "entered-ref")
    return (
        (
            common_entered,
            Exposure("e1", False, 0, "shadow-a"),
            Exposure("e2", False, 0, "shadow-b"),
        ),
        (
            common_entered,
            Exposure("e1", False, 1, "shadow-a"),
            Exposure("e2", False, 1, "shadow-b"),
        ),
    )


def test_rec_selected_log_cannot_identify_shadow_composition() -> None:
    worlds = _worlds_same_log_different_shadow_truth()

    assert selected_event_log(worlds[0]) == selected_event_log(worlds[1])
    assert shadow_prevalence(worlds[0]) == 0.0
    assert shadow_prevalence(worlds[1]) == 1.0
    assert compatible_indices(worlds, selected_event_log, 0) == frozenset({0, 1})


def test_exposure_ledger_identifies_shadow_denominator_but_not_truth() -> None:
    worlds = _worlds_same_log_different_shadow_truth()
    assert exposure_denominator_ledger(worlds[0]) == exposure_denominator_ledger(worlds[1])
    assert shadow_count(worlds[0]) == shadow_count(worlds[1]) == 2
    assert shadow_prevalence(worlds[0]) != shadow_prevalence(worlds[1])

    # A different full world can share the same entered event log while changing
    # the number of shadow opportunities; the denominator ledger splits it.
    shorter = (
        Exposure("e0", True, 1, "entered-ref"),
        Exposure("e1", False, 0, "shadow-a"),
    )
    expanded = worlds + (shorter,)
    assert compatible_indices(expanded, selected_event_log, 0) == frozenset({0, 1, 2})
    assert compatible_indices(expanded, exposure_denominator_ledger, 0) == frozenset({0, 1})


def test_reference_retained_before_selection_splits_worlds_that_selected_only_reference_cannot() -> None:
    world_a = (
        Exposure("e0", True, 1, "entered-ref"),
        Exposure("e1", False, 0, "shadow-ref-a"),
    )
    world_b = (
        Exposure("e0", True, 1, "entered-ref"),
        Exposure("e1", False, 0, "shadow-ref-b"),
    )
    worlds = (world_a, world_b)

    assert selected_reference_log(world_a) == selected_reference_log(world_b)
    assert full_reference_ledger(world_a) != full_reference_ledger(world_b)
    assert compatible_indices(worlds, selected_reference_log, 0) == frozenset({0, 1})
    assert compatible_indices(worlds, full_reference_ledger, 0) == frozenset({0})


def test_downstream_algorithm_cannot_split_already_collapsed_values() -> None:
    worlds = _worlds_same_log_different_shadow_truth()
    retained_a = selected_event_log(worlds[0])
    retained_b = selected_event_log(worlds[1])
    assert retained_a == retained_b

    downstream = lambda log: (len(log), tuple(row[1] for row in log))
    assert not postprocessing_can_separate(retained_a, retained_b, downstream)
