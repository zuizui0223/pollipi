from __future__ import annotations

import json
from pathlib import Path


def test_theorem_ledger_is_complete_and_keeps_empirical_boundary_explicit() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    path = repo_root / "results" / "v3_tnoa_theorem_ledger_v1.json"
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["schema"] == "v3-tnoa-theorem-ledger-v1"
    assert payload["paper_route"] == "conceptual-mathematical"
    assert payload["field_data_required_for_structural_claims"] is False

    theorems = payload["theorems"]
    assert len(theorems) == 11
    ids = [row["id"] for row in theorems]
    assert len(set(ids)) == len(ids)
    assert ids == [f"T{index}_{suffix}" for index, suffix in [
        (1, "reference_refinement"),
        (2, "semantic_coarsening"),
        (3, "additive_nonidentifiability"),
        (4, "projection_energy_tradeoff"),
        (5, "universal_nonharm_impossibility"),
        (6, "reversible_decomposition"),
        (7, "decision_risk_order"),
        (8, "partial_decomposition_coverage"),
        (9, "additive_diameter_equality"),
        (10, "general_forward_model_contraction"),
        (11, "resolvable_coverage_monotonicity"),
    ]]
    assert all(row["requires_real_data"] is False for row in theorems)
    assert all(row["assumptions"] for row in theorems)
    assert all(row["proof_type"] for row in theorems)
    assert all(row["empirical_boundary"] for row in theorems)
    assert payload["overall_empirical_boundary"]
