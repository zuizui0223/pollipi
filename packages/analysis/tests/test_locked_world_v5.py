from collections import Counter

import pytest
from pollipi_analysis.simulation.locked_world_v5 import (
    CONTRACT_FINGERPRINT,
    CONTRACT_INSEPI_COMMIT,
    CONTRACT_POLLIPI_COMMIT,
    DISTURBANCE_FAMILIES,
    build_registry,
    derive_competition_seed,
    derive_seed_registry,
    suite_fingerprint,
)


def test_locked_v5_contract_uses_shifted_world_and_prevalence_regimes():
    registry = build_registry(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT)
    assert len(registry) == 180
    counts = Counter((row.prevalence_regime, row.true_visit) for row in registry)
    assert counts == {
        ("rare", False): 48,
        ("rare", True): 12,
        ("balanced", False): 30,
        ("balanced", True): 30,
        ("common", False): 12,
        ("common", True): 48,
    }
    assert {row.disturbance_family for row in registry} == set(DISTURBANCE_FAMILIES)
    assert suite_fingerprint(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT) == CONTRACT_FINGERPRINT


def test_locked_v5_seeds_are_commit_derived_and_fail_closed():
    first = derive_seed_registry(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT, count=9)
    assert first == derive_seed_registry(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT, count=9)
    changed = derive_seed_registry("2" * 40, CONTRACT_INSEPI_COMMIT, count=9)
    assert first != changed
    with pytest.raises(ValueError, match="full hexadecimal commit SHA"):
        derive_seed_registry("short", CONTRACT_INSEPI_COMMIT, count=1)


def test_competition_seed_is_commit_derived_but_domain_separated():
    world_seed = derive_seed_registry(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT, count=1)[0]
    competition_seed = derive_competition_seed(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT)
    assert competition_seed == derive_competition_seed(CONTRACT_POLLIPI_COMMIT, CONTRACT_INSEPI_COMMIT)
    assert competition_seed != world_seed
