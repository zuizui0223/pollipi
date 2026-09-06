from __future__ import annotations

from typing import NamedTuple

from pollipi_analysis.v3_tnoa_theory import identified_set


class World(NamedTuple):
    y: int
    r: int
    rich: str
    coarse: int
    theta: str


def _point_identified(worlds: tuple[World, ...], observation, world: World) -> bool:
    values = identified_set(worlds, observation, observation(world), lambda w: w.theta)
    return len(values) == 1


def _coverage(worlds: tuple[World, ...], observation) -> float:
    return sum(_point_identified(worlds, observation, world) for world in worlds) / len(worlds)


def test_reference_refinement_is_pointwise_monotone_for_identification() -> None:
    worlds = (
        World(0, 0, "a", 1, "target"),
        World(0, 1, "b", 1, "nuisance"),
        World(1, 0, "c", 0, "target"),
        World(1, 1, "d", 0, "target"),
    )
    coarse = lambda w: w.y
    refined = lambda w: (w.y, w.r)

    for world in worlds:
        assert int(_point_identified(worlds, refined, world)) >= int(
            _point_identified(worlds, coarse, world)
        )
    assert _coverage(worlds, refined) >= _coverage(worlds, coarse)
    assert _coverage(worlds, refined) == 1.0
    assert _coverage(worlds, coarse) == 0.5


def test_semantic_coarsening_cannot_increase_identification_coverage() -> None:
    worlds = (
        World(0, 0, "T", 1, "target-only"),
        World(0, 0, "U-overlap", 1, "target+nuisance"),
        World(0, 0, "N", 0, "nuisance-only"),
        World(0, 0, "B", 0, "baseline"),
    )
    rich = lambda w: w.rich
    coarsened = lambda w: w.coarse

    for world in worlds:
        assert int(_point_identified(worlds, rich, world)) >= int(
            _point_identified(worlds, coarsened, world)
        )
    assert _coverage(worlds, rich) == 1.0
    assert _coverage(worlds, coarsened) == 0.0
