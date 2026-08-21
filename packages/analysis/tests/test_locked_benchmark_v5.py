import json

import pytest
from pollipi_analysis.simulation.locked_benchmark_v5 import write_locked_trace_jsonl
from pollipi_analysis.simulation.locked_world_v5 import (
    CONTRACT_INSEPI_COMMIT,
    CONTRACT_POLLIPI_COMMIT,
)


def test_locked_v5_trace_is_provenance_pinned_and_one_output_only(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pollipi_analysis.simulation.locked_benchmark_v5._checkout_state",
        lambda: (CONTRACT_POLLIPI_COMMIT, True),
    )
    path = tmp_path / "locked-v5.jsonl"
    write_locked_trace_jsonl(
        path,
        pollipi_commit_sha=CONTRACT_POLLIPI_COMMIT,
        insepi_commit_sha=CONTRACT_INSEPI_COMMIT,
    )
    records = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]
    assert records[0]["pollipi_source_commit"] == CONTRACT_POLLIPI_COMMIT
    assert records[0]["insepi_source_commit"] == CONTRACT_INSEPI_COMMIT
    assert len([row for row in records if row["record_type"] == "result"]) == 180
    with pytest.raises(FileExistsError):
        write_locked_trace_jsonl(
            path,
            pollipi_commit_sha=CONTRACT_POLLIPI_COMMIT,
            insepi_commit_sha=CONTRACT_INSEPI_COMMIT,
        )


def test_locked_v5_trace_rejects_nonfrozen_checkout(tmp_path, monkeypatch):
    monkeypatch.setattr(
        "pollipi_analysis.simulation.locked_benchmark_v5._checkout_state",
        lambda: ("2" * 40, True),
    )
    with pytest.raises(RuntimeError, match="does not match checkout HEAD"):
        write_locked_trace_jsonl(
            tmp_path / "locked-v5.jsonl",
            pollipi_commit_sha=CONTRACT_POLLIPI_COMMIT,
            insepi_commit_sha=CONTRACT_INSEPI_COMMIT,
        )
