"""Phase 3: per-frame shadow A/B comparison helpers used by the Pi runtime."""
from __future__ import annotations

from pollipi_analysis.abtest import ab_step, summarize_ab_rows


def test_ab_step_agreement_and_aggressiveness() -> None:
    same = ab_step("no_activity", 30.0, "no_activity", 30.0)
    assert same["agree"] and not same["b_more_aggressive"] and not same["a_more_aggressive"]

    # B proposes a shorter next interval -> B is more aggressive (more power).
    b_more = ab_step("no_activity", 30.0, "strong_visitation_candidate", 5.0)
    assert not b_more["agree"]
    assert b_more["b_more_aggressive"] and not b_more["a_more_aggressive"]

    a_more = ab_step("strong_visitation_candidate", 5.0, "no_activity", 30.0)
    assert a_more["a_more_aggressive"] and not a_more["b_more_aggressive"]


def test_summarize_from_boolean_rows() -> None:
    rows = [
        {"a_state": "no_activity", "b_state": "no_activity", "agree": True, "b_more_aggressive": False},
        {"a_state": "no_activity", "b_state": "strong_visitation_candidate", "agree": False, "b_more_aggressive": True},
    ]
    s = summarize_ab_rows(rows)
    assert s["n_frames"] == 2
    assert s["agreement_rate"] == 0.5
    assert s["b_more_aggressive"] == 1
    assert s["b_strong"] == 1


def test_summarize_derives_flags_from_intervals_and_parses_strings() -> None:
    # Rows as they would be parsed back from the Pi CSV (strings, no bool flags).
    rows = [
        {
            "a_state": "no_activity",
            "b_state": "strong_visitation_candidate",
            "a_would_be_next_interval_sec": "30.0",
            "b_would_be_next_interval_sec": "5.0",
        },
        {
            "a_state": "no_activity",
            "b_state": "no_activity",
            "a_would_be_next_interval_sec": "30.0",
            "b_would_be_next_interval_sec": "30.0",
        },
    ]
    s = summarize_ab_rows(rows)
    assert s["agreement_rate"] == 0.5
    assert s["b_more_aggressive"] == 1
    assert s["a_more_aggressive"] == 0
