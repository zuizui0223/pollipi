"""PolliPi adapter for the canonical one-shot V7 pixel artifact.

This module does not generate V7 pixels and does not import InsePi.  It verifies
an externally materialised NPZ artifact, passes only frame/background arrays into
PolliPi's existing ``analyze`` front end, and attaches latent metadata only after
the decision has been made.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path

import numpy as np

from pollipi_analysis.pipeline import analyze


ARTIFACT_SCHEMA = "pollipi-insepi-v7-pixel-artifact-v1"
TRACE_SCHEMA = "pollipi-insepi-v7-pollipi-trace-v1"


@dataclass(frozen=True, slots=True)
class V7ArtifactManifest:
    schema: str
    world_spec_sha256: str
    world_fingerprint: str
    condition_count: int
    shape: tuple[int, int]
    npz_sha256: str


@dataclass(frozen=True, slots=True)
class PolliPiV7Result:
    schema: str
    condition_id: str
    family: str
    tier: int
    replicate: int
    true_visit: bool
    event_visibility: float
    intensity: float
    pollipi_state: str
    pollipi_reason: str
    global_synchrony: float
    active_cell_proportion: float
    estimated_global_shift: float

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_v7_artifact(
    npz_path: str | Path,
    manifest_path: str | Path,
    *,
    expected_world_spec_sha256: str | None = None,
) -> tuple[V7ArtifactManifest, np.ndarray, np.ndarray, list[dict[str, object]]]:
    npz_file = Path(npz_path)
    raw = json.loads(Path(manifest_path).read_text(encoding="utf-8"))
    if raw.get("schema") != ARTIFACT_SCHEMA:
        raise ValueError("unexpected V7 artifact schema")
    manifest = V7ArtifactManifest(
        schema=str(raw["schema"]),
        world_spec_sha256=str(raw["world_spec_sha256"]),
        world_fingerprint=str(raw["world_fingerprint"]),
        condition_count=int(raw["condition_count"]),
        shape=tuple(int(v) for v in raw["shape"]),
        npz_sha256=str(raw["npz_sha256"]),
    )
    if _sha256_file(npz_file) != manifest.npz_sha256:
        raise ValueError("V7 artifact SHA-256 mismatch")
    if expected_world_spec_sha256 is not None and manifest.world_spec_sha256 != expected_world_spec_sha256:
        raise ValueError("V7 world-spec fingerprint mismatch")

    with np.load(npz_file, allow_pickle=False) as payload:
        backgrounds = payload["backgrounds"].astype(np.uint8)
        frames = payload["frames"].astype(np.uint8)
        metadata = json.loads(str(payload["metadata_json"].item()))
    if backgrounds.shape != frames.shape or backgrounds.ndim != 3:
        raise ValueError("invalid V7 pixel tensor shapes")
    if backgrounds.shape[0] != manifest.condition_count:
        raise ValueError("V7 condition count mismatch")
    if tuple(backgrounds.shape[1:]) != manifest.shape:
        raise ValueError("V7 image shape mismatch")
    if len(metadata) != manifest.condition_count:
        raise ValueError("V7 metadata count mismatch")
    condition_ids = [str(row["condition_id"]) for row in metadata]
    if len(condition_ids) != len(set(condition_ids)):
        raise ValueError("duplicate V7 condition IDs")
    return manifest, backgrounds, frames, metadata


def run_v7_artifact(
    npz_path: str | Path,
    manifest_path: str | Path,
    *,
    expected_world_spec_sha256: str | None = None,
) -> tuple[V7ArtifactManifest, list[PolliPiV7Result]]:
    manifest, backgrounds, frames, metadata = read_v7_artifact(
        npz_path,
        manifest_path,
        expected_world_spec_sha256=expected_world_spec_sha256,
    )
    rows: list[PolliPiV7Result] = []
    for index, meta in enumerate(metadata):
        # Hidden truth is not passed to analyze().
        decision = analyze(frames[index], backgrounds[index])
        features = decision.features
        rows.append(PolliPiV7Result(
            schema=TRACE_SCHEMA,
            condition_id=str(meta["condition_id"]),
            family=str(meta["family"]),
            tier=int(meta["tier"]),
            replicate=int(meta["replicate"]),
            true_visit=bool(meta["true_visit"]),
            event_visibility=float(meta["event_visibility"]),
            intensity=float(meta["intensity"]),
            pollipi_state=str(decision.state),
            pollipi_reason=decision.reason,
            global_synchrony=float(features.global_synchrony),
            active_cell_proportion=float(features.active_cell_proportion),
            estimated_global_shift=float(features.estimated_global_shift),
        ))
    return manifest, rows


def write_v7_trace_jsonl(
    npz_path: str | Path,
    manifest_path: str | Path,
    trace_path: str | Path,
    *,
    source_commit: str,
    expected_world_spec_sha256: str | None = None,
) -> Path:
    if not source_commit:
        raise ValueError("source_commit provenance is required")
    manifest, rows = run_v7_artifact(
        npz_path,
        manifest_path,
        expected_world_spec_sha256=expected_world_spec_sha256,
    )
    output = Path(trace_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    provenance = {
        "record_type": "provenance",
        "schema": TRACE_SCHEMA,
        "source_commit": source_commit,
        "world_fingerprint": manifest.world_fingerprint,
        "world_spec_sha256": manifest.world_spec_sha256,
        "pixel_artifact_sha256": manifest.npz_sha256,
        "condition_count": manifest.condition_count,
    }
    with output.open("w", encoding="utf-8") as handle:
        handle.write(json.dumps(provenance, sort_keys=True) + "\n")
        for row in rows:
            payload = row.to_dict()
            payload["record_type"] = "result"
            handle.write(json.dumps(payload, sort_keys=True) + "\n")
    return output
