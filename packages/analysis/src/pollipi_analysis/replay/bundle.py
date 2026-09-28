"""Build an auditable PolliPi field-validation result bundle.

The bundle freezes:
- input manifest and truth/probe hashes from preflight;
- exact analysis-module source hashes;
- frozen analysis parameters;
- machine-readable result JSON;
- human-readable report;
- SHA-256 of every emitted artifact.

No result is produced when input preflight fails.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union

import importlib

compare_module = importlib.import_module("pollipi_analysis.replay.compare")
field_module = importlib.import_module("pollipi_analysis.replay.field_validation")
joint_module = importlib.import_module("pollipi_analysis.replay.joint")
preflight_module = importlib.import_module("pollipi_analysis.replay.preflight")
from pollipi_analysis.replay.field_validation import (
    DEFAULT_BOOTSTRAP_REPS,
    DEFAULT_BOOTSTRAP_SEED,
    DEFAULT_NONINFERIORITY_MARGIN,
    analyze_field_validation,
    format_field_validation_report,
)
from pollipi_analysis.replay.joint import load_joint_manifest
from pollipi_analysis.replay.preflight import preflight_field_inputs

SCHEMA = "pollipi-field-validation-bundle-v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _module_source_hash(module) -> tuple[str, str]:
    path = Path(module.__file__).resolve()
    return path.name, _sha256(path)


def _analysis_code_provenance() -> dict:
    modules = {
        "compare": compare_module,
        "joint": joint_module,
        "preflight": preflight_module,
        "field_validation": field_module,
    }
    rows = {}
    for name, module in modules.items():
        filename, digest = _module_source_hash(module)
        rows[name] = {"file": filename, "sha256": digest}
    canonical = json.dumps(
        {name: row["sha256"] for name, row in sorted(rows.items())},
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return {
        "modules": rows,
        "analysis_code_fingerprint": hashlib.sha256(canonical).hexdigest(),
    }


@dataclass(frozen=True)
class BundleBuildResult:
    ok: bool
    output_dir: str
    bundle_manifest: str
    input_preflight: str
    validation_json: Optional[str]
    validation_report: Optional[str]
    status: str

    def as_dict(self) -> dict:
        return {
            "ok": self.ok,
            "status": self.status,
            "output_dir": self.output_dir,
            "bundle_manifest": self.bundle_manifest,
            "input_preflight": self.input_preflight,
            "validation_json": self.validation_json,
            "validation_report": self.validation_report,
        }


def build_field_validation_bundle(
    manifest: Union[str, Path],
    output_dir: Union[str, Path],
    *,
    bootstrap_reps: int = DEFAULT_BOOTSTRAP_REPS,
    bootstrap_seed: int = DEFAULT_BOOTSTRAP_SEED,
    noninferiority_margin: float = DEFAULT_NONINFERIORITY_MARGIN,
    random_reps: int = 10_000,
    random_seed: int = 20260928,
    random_anchor_first: bool = True,
) -> BundleBuildResult:
    manifest_path = Path(manifest).resolve()
    out = Path(output_dir).resolve()
    out.mkdir(parents=True, exist_ok=True)

    preflight_path = out / "pollipi_field_input_preflight_v1.json"
    result_path = out / "pollipi_field_validation_v1.json"
    report_path = out / "pollipi_field_validation_v1.txt"
    bundle_path = out / "pollipi_field_validation_bundle_v1.json"

    preflight = preflight_field_inputs(manifest_path)
    preflight_payload = preflight.as_dict()
    preflight_path.write_text(
        json.dumps(preflight_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    code = _analysis_code_provenance()
    parameters = {
        "bootstrap_reps": bootstrap_reps,
        "bootstrap_seed": bootstrap_seed,
        "noninferiority_margin": noninferiority_margin,
        "random_reps": random_reps,
        "random_seed": random_seed,
        "random_anchor_first": random_anchor_first,
    }

    if not preflight.ok:
        bundle_payload = {
            "schema": SCHEMA,
            "status": "input_preflight_failed",
            "input_fingerprint": preflight.input_fingerprint,
            "analysis_code": code,
            "parameters": parameters,
            "artifacts": {
                "input_preflight": {
                    "file": preflight_path.name,
                    "sha256": _sha256(preflight_path),
                }
            },
            "errors": list(preflight.errors),
            "warnings": list(preflight.warnings),
        }
        bundle_path.write_text(
            json.dumps(bundle_payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return BundleBuildResult(
            ok=False,
            output_dir=str(out),
            bundle_manifest=str(bundle_path),
            input_preflight=str(preflight_path),
            validation_json=None,
            validation_report=None,
            status="input_preflight_failed",
        )

    runs = load_joint_manifest(manifest_path)
    summary = analyze_field_validation(
        runs,
        bootstrap_reps=bootstrap_reps,
        bootstrap_seed=bootstrap_seed,
        noninferiority_margin=noninferiority_margin,
        random_reps=random_reps,
        random_seed=random_seed,
        random_anchor_first=random_anchor_first,
    )
    result_payload = summary.as_dict()
    result_payload["input_preflight"] = preflight_payload
    result_payload["analysis_code"] = code
    result_path.write_text(
        json.dumps(result_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        format_field_validation_report(summary) + "\n",
        encoding="utf-8",
    )

    artifacts = {
        "input_preflight": {
            "file": preflight_path.name,
            "sha256": _sha256(preflight_path),
        },
        "validation_json": {
            "file": result_path.name,
            "sha256": _sha256(result_path),
        },
        "validation_report": {
            "file": report_path.name,
            "sha256": _sha256(report_path),
        },
    }
    canonical = json.dumps(
        {
            "input_fingerprint": preflight.input_fingerprint,
            "analysis_code_fingerprint": code["analysis_code_fingerprint"],
            "parameters": parameters,
            "artifact_hashes": {
                name: item["sha256"] for name, item in sorted(artifacts.items())
            },
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")

    bundle_payload = {
        "schema": SCHEMA,
        "status": "complete",
        "input_fingerprint": preflight.input_fingerprint,
        "analysis_code": code,
        "parameters": parameters,
        "claim_gates": result_payload["claim_gates"],
        "artifacts": artifacts,
        "bundle_fingerprint": hashlib.sha256(canonical).hexdigest(),
    }
    bundle_path.write_text(
        json.dumps(bundle_payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    return BundleBuildResult(
        ok=True,
        output_dir=str(out),
        bundle_manifest=str(bundle_path),
        input_preflight=str(preflight_path),
        validation_json=str(result_path),
        validation_report=str(report_path),
        status="complete",
    )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the auditable PolliPi field-validation v1 result bundle."
    )
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--bootstrap-reps", type=int, default=DEFAULT_BOOTSTRAP_REPS)
    parser.add_argument("--bootstrap-seed", type=int, default=DEFAULT_BOOTSTRAP_SEED)
    parser.add_argument(
        "--noninferiority-margin",
        type=float,
        default=DEFAULT_NONINFERIORITY_MARGIN,
    )
    parser.add_argument("--random-reps", type=int, default=10_000)
    parser.add_argument("--random-seed", type=int, default=20260928)
    parser.add_argument("--random-free-first", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = build_field_validation_bundle(
        args.manifest,
        args.output_dir,
        bootstrap_reps=args.bootstrap_reps,
        bootstrap_seed=args.bootstrap_seed,
        noninferiority_margin=args.noninferiority_margin,
        random_reps=args.random_reps,
        random_seed=args.random_seed,
        random_anchor_first=not args.random_free_first,
    )
    if args.json:
        print(json.dumps(result.as_dict(), indent=2, ensure_ascii=False))
    else:
        print(f"bundle status={result.status}")
        print(f"bundle_manifest={result.bundle_manifest}")
        print(f"input_preflight={result.input_preflight}")
        if result.validation_json:
            print(f"validation_json={result.validation_json}")
        if result.validation_report:
            print(f"validation_report={result.validation_report}")
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
