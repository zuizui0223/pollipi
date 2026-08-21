from pollipi_analysis.simulation.portable_visual_v2 import (
    PORTABLE_VISUAL_V2_FINGERPRINT,
    SCENARIO_IDS,
    suite_fingerprint,
)
from pollipi_analysis.simulation.visual_contradiction_v2 import run_visual_contradiction_v2


def test_portable_visual_world_fingerprint_is_stable():
    assert suite_fingerprint() == PORTABLE_VISUAL_V2_FINGERPRINT


def test_v2_runs_real_pollipi_front_end_deterministically():
    first = run_visual_contradiction_v2()
    second = run_visual_contradiction_v2()
    assert [row.to_dict() for row in first] == [row.to_dict() for row in second]
    assert [row.scenario_id for row in first] == list(SCENARIO_IDS)
    assert all(row.pollipi_state in {
        "no_activity", "environmental_noise", "uncertain_local_activity", "strong_visitation_candidate"
    } for row in first)
    print("POLLIPI_V2", [(row.scenario_id, row.true_visit, row.pollipi_state, row.pollipi_reason) for row in first])
