# legacy/

Archived code that is **not used by the current ①②③④ capture runtime** and
**not needed for the publication**. Kept for history/reference; nothing here is
imported by the live packages, bundled into the Pi artifact, or run in CI.
Restore any item with `git mv` (full history is preserved).

Paths mirror where each file used to live.

| Archived path | Was | Why legacy |
|---|---|---|
| `root/pollipi_mesh_simulation_rounds.py` | repo root | Superseded 6-round mesh study (searched+evaluated on the same synthetic data → FP-heavy, near-degenerate policy). Replaced by `pollipi_analysis.simulation.runtime_bridge`. A reproducibility copy also lives in OneDrive. |
| `packages/analysis/mesh/motion.py` | `pollipi_analysis/mesh/motion.py` | Issue-14 standalone two-state mesh-motion detector (old proportion metric). Not in the ①②③④ path, which uses `pipeline.analyze` + `ThreeStageController`. |
| `packages/analysis/simulation/{run,__main__}.py` | `pollipi_analysis/simulation/` | Legacy pairwise policy search CLI that wrote `legacy_pairwise_policy.json` (the Pi never loaded it). `runtime_bridge` is the sole official Mode-3 export. |
| `packages/analysis/policy_profiles/three_stage_sensitive_v1.json` | analysis policy_profiles | Early "sensitive" comparison profile; not one of the four live modes (which use the `*_canary_v1` profiles) nor the code default (`three_stage_default_v1`). |
| `packages/analysis/tests/test_mesh_simulation_policy.py` | analysis tests | Tested the archived `analyze_mesh_motion`. |
| `packages/server/services/{motion,mesh_motion}.py` | `visit_monitor_server/services/` | Dead server wrappers over `mesh/motion.py`; no route imported them. |
| `packages/server/tests/test_issue14_mesh_motion.py` | server tests | Tested the archived mesh-motion service chain. |
| `packages/coordinator/` | workspace package `@visit-monitor/coordinator` | Optional multi-Pi aggregator. The field deployment runs each Pi standalone; the coordinator is not part of the published edge-capture methodology. |

The archived tests reference their co-located archived modules and are **not**
wired into CI; treat them as documentation of how the legacy code behaved.
