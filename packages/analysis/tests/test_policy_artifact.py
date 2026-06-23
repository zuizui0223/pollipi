"""Phase C/D: cost-weighted selection + Pi-loadable policy artifact (Issue #21)."""
from __future__ import annotations

import json

import pytest

pytest.importorskip("numpy")

from pollipi_analysis.features.compute import FeatureConfig
from pollipi_analysis.pipeline import ClassifierConfig, PipelineConfig
from pollipi_analysis.policy.artifact import (
    POLICY_SCHEMA_VERSION,
    PolicyMeta,
    build_policy,
    load_policy,
    write_policy,
)
from pollipi_analysis.simulation.search import CostWeights, run_search, select_policy


def test_run_search_reports_cost_and_select_picks_minimum() -> None:
    rows = run_search(seed=7)
    assert all("cost" in r for r in rows)
    chosen = select_policy(rows)
    assert chosen["cost"] == min(r["cost"] for r in rows)


def test_false_strong_is_penalised_far_more_than_a_target_miss() -> None:
    w = CostWeights()
    assert w.false_strong > w.target_miss > w.false_uncertain


def test_policy_round_trips_through_json(tmp_path) -> None:
    config = PipelineConfig(
        features=FeatureConfig(cell_size=32, pixel_difference=25),
        classifier=ClassifierConfig(strong_spatial_concentration=0.70),
    )
    meta = PolicyMeta(policy_name="simulation_informed", policy_version="1", seed=7)
    path = write_policy(tmp_path / "simulation_informed_policy.json", config, meta)

    loaded_config, loaded_meta = load_policy(path)
    assert loaded_config.features == config.features
    assert loaded_config.classifier == config.classifier
    assert loaded_meta.policy_name == "simulation_informed"
    assert loaded_meta.validation_status == "synthetic_only"


def test_policy_json_contains_only_pi_compatible_fields() -> None:
    config = PipelineConfig()
    policy = build_policy(config, PolicyMeta(policy_name="p", policy_version="1"))
    assert policy["schema"] == POLICY_SCHEMA_VERSION
    assert set(policy) == {"schema", "policy_name", "policy_version", "validation_status", "metadata", "feature", "classifier"}
    # feature/classifier must be plain numeric/bool config, no callables/objects.
    serialised = json.dumps(policy)  # raises if anything is non-serialisable
    assert "matplotlib" not in serialised and "pandas" not in serialised


def test_unvalidated_status_words_are_rejected() -> None:
    config = PipelineConfig()
    with pytest.raises(ValueError):
        build_policy(config, PolicyMeta(policy_name="p", policy_version="1", validation_status="production"))


def test_bad_schema_fails_loudly() -> None:
    with pytest.raises(ValueError):
        load_policy({"schema": "policy-999", "feature": {}, "classifier": {}, "policy_name": "x", "policy_version": "1"})
