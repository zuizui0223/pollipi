from __future__ import annotations

from typing import NamedTuple

from pollipi_analysis.v3_tnoa_decision_risk import (
    decomposition_pair_is_reversible,
    minimum_empirical_risk,
)


class World(NamedTuple):
    y: int
    r: int
    rich: str
    coarse: int
    truth: int


def zero_one_loss(action: int, world: World) -> float:
    return 0.0 if action == world.truth else 1.0


def test_reference_refinement_cannot_worsen_best_empirical_decision_risk() -> None:
    worlds = (
        World(y=0, r=0, rich="a", coarse=0, truth=0),
        World(y=0, r=1, rich="b", coarse=0, truth=1),
    )
    risk_y = minimum_empirical_risk(
        worlds, observation=lambda w: w.y, actions=(0, 1), loss=zero_one_loss
    )
    risk_yr = minimum_empirical_risk(
        worlds, observation=lambda w: (w.y, w.r), actions=(0, 1), loss=zero_one_loss
    )
    assert risk_y == 0.5
    assert risk_yr == 0.0
    assert risk_yr <= risk_y


def test_semantic_coarsening_cannot_improve_best_empirical_decision_risk() -> None:
    worlds = (
        World(y=0, r=0, rich="target-only", coarse=1, truth=0),
        World(y=0, r=0, rich="target-plus-nuisance", coarse=1, truth=1),
    )
    risk_rich = minimum_empirical_risk(
        worlds, observation=lambda w: w.rich, actions=(0, 1), loss=zero_one_loss
    )
    risk_coarse = minimum_empirical_risk(
        worlds, observation=lambda w: w.coarse, actions=(0, 1), loss=zero_one_loss
    )
    assert risk_rich == 0.0
    assert risk_coarse == 0.5
    assert risk_rich <= risk_coarse


def test_reversible_decomposition_pair_reconstructs_raw() -> None:
    assert decomposition_pair_is_reversible(
        explained=(1.0, 0.0, -2.0),
        residual=(2.0, 4.0, 1.0),
        raw=(3.0, 4.0, -1.0),
    )
