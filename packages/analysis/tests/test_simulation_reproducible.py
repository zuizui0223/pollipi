from __future__ import annotations

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.simulation.search import pareto_front, run_search
from pollipi_analysis.simulation.synthetic import simulate_pair


def test_simulation_is_deterministic_for_fixed_seed() -> None:
    import numpy as np

    a_bg, a_fr = simulate_pair("localized_trajectory", seed=7)
    b_bg, b_fr = simulate_pair("localized_trajectory", seed=7)
    assert np.array_equal(a_bg, b_bg)
    assert np.array_equal(a_fr, b_fr)


def test_search_reports_recall_and_false_trigger_metrics() -> None:
    rows = run_search(seed=7)
    assert rows
    for row in rows:
        assert 0.0 <= row["candidate_recall"] <= 1.0
        assert 0.0 <= row["false_trigger_rate"] <= 1.0


def test_a_zero_false_trigger_config_with_recall_exists_on_the_front() -> None:
    rows = run_search(seed=7)
    front = pareto_front(rows)
    assert any(r["false_trigger_rate"] == 0.0 and r["candidate_recall"] >= 0.5 for r in front)
