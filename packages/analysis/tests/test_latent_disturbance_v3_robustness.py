import numpy as np

from pollipi_analysis.simulation.latent_disturbance_v3_robustness import (
    CONDITIONS,
    _lag1_reference,
    _partial75_reference,
    evaluate_v3_robustness,
)
from pollipi_analysis.simulation.latent_disturbance_v3_temporal_subspace import (
    generate_temporal_world,
)


def test_lag1_is_exactly_one_frame_delay_after_first_frame():
    w = generate_temporal_world("target_plus_wind", 123)
    d = w.reference_frames - w.reference_background[None, :, :]
    lag = _lag1_reference(w) - w.reference_background[None, :, :]
    assert np.allclose(lag[0], d[0])
    assert np.allclose(lag[1:], d[:-1])


def test_partial75_is_deterministic_and_differs_from_matched():
    w = generate_temporal_world("target_plus_local_sway", 456)
    a = _partial75_reference(w, 999)
    b = _partial75_reference(w, 999)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, w.reference_frames)


def test_robustness_contract_is_reproducible_without_requiring_promotion():
    a = evaluate_v3_robustness(n_reps=2, seed=20260905)
    b = evaluate_v3_robustness(n_reps=2, seed=20260905)
    assert a == b
    assert tuple(a["conditions"]) == CONDITIONS
    assert len(a["promotion_rule"]["criteria"]) == 10
    assert isinstance(a["promotion_rule"]["promoted_to_temporally_robust_simulation_candidate"], bool)
