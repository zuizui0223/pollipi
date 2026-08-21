import json

from pollipi_analysis.simulation.contradiction import (
    CONTRADICTION_SCHEMA,
    CONTRAST_SCENARIOS,
    run_contradiction_scenarios,
    write_contradiction_trace_jsonl,
)


def _by_id():
    return {row.scenario_id: row for row in run_contradiction_scenarios()}


def test_contrast_scenario_ids_are_unique_and_schema_is_stable():
    ids = [scenario.scenario_id for scenario in CONTRAST_SCENARIOS]
    assert len(ids) == len(set(ids))
    assert all(row.schema == CONTRADICTION_SCHEMA for row in run_contradiction_scenarios())


def test_clean_signal_and_quiet_absence_separate_as_expected():
    rows = _by_id()
    assert rows["quiet_absence"].pollipi_state == "no_activity"
    assert rows["clean_visit"].pollipi_state == "strong_visitation_candidate"
    assert rows["clean_visit"].capture_posture == "candidate_priority"


def test_broad_disturbance_can_suppress_a_true_visit_candidate():
    rows = _by_id()
    assert rows["wind_visit"].true_visit is True
    assert rows["wind_visit"].pollipi_state == "environmental_noise"
    assert rows["wind_visit"].capture_posture == "noise_suppressed"
    assert rows["shake_visit"].pollipi_state == "environmental_noise"
    assert rows["shadow_visit"].pollipi_state == "environmental_noise"


def test_occlusion_and_blur_preserve_faint_uncertainty_instead_of_false_certainty():
    rows = _by_id()
    assert rows["occluded_visit"].pollipi_state == "uncertain_local_activity"
    assert rows["blurred_visit"].pollipi_state == "uncertain_local_activity"


def test_trace_is_portable_jsonl(tmp_path):
    output = write_contradiction_trace_jsonl(tmp_path / "pollipi.jsonl")
    records = [json.loads(line) for line in output.read_text(encoding="utf-8").splitlines()]
    assert len(records) == len(CONTRAST_SCENARIOS)
    assert records[0]["schema"] == CONTRADICTION_SCHEMA
    assert {record["scenario_id"] for record in records} == {
        scenario.scenario_id for scenario in CONTRAST_SCENARIOS
    }
