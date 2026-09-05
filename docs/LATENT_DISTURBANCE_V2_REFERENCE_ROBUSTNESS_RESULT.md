# V2 reference-degradation robustness result

Status: **adverse under the frozen robustness rule.** The exact-reference mechanism remains positive, but the minimal unaligned linear projection is not promoted to field-shadow use.

Source workflow: `33934280470`.

Artifact id: `9959633777`.

Artifact digest: `sha256:90308c8c6dd7a5c758d1f564f7eab7ed1c2a36faab4e00a65a09acd07fa0a497`.

Result JSON SHA-256: `2546651fb9b751b18de6d12e981d0bed41b93def39c32c5c4eb0735128206229`.

## Aggregate result

| condition | mixed-target recall | nuisance false-event rate | balanced utility | target-only recall |
| --- | ---: | ---: | ---: | ---: |
| gain + sensor noise | **1.0000** | **0.0000** | **1.0000** | 1.0000 |
| 2 px spatial mismatch | 0.6914 | **0.3047** | 0.6934 | 1.0000 |
| 75% partial coupling | 0.9922 | **0.0000** | 0.9961 | 1.0000 |
| no reference | 0.2969 | 0.2383 | 0.5293 | 1.0000 |

Four of five frozen criteria pass. The failed criterion is:

> every degraded-reference nuisance false-event rate must be no more than `0.05` above no-reference.

No-reference FPR is `0.2383`, so the allowed upper bound is `0.2883`; the 2 px shift condition is `0.3047`.

Therefore `promoted_to_reference_robust_candidate=false`.

## Failure localization

Under 2 px reference misalignment, nuisance-only local-candidate rates are:

- wind: `0.1406`;
- shadow: `0.2656`;
- shake: `0.1562`;
- local sway: `0.6562`.

At the same time mixed-target recall improves substantially over no-reference (`0.6914` vs `0.2969`). Thus the failure is not lack of useful nuisance information. The problem is that a spatially displaced nuisance template leaves structured residual edges that the unchanged V1 classifier can interpret as local activity.

## Scientific interpretation

The primary exact-reference result was not a generic artefact of giving the model another image: gain/noise mismatch and 75% partial coupling remain strongly positive. But pixelwise nuisance subtraction is too sensitive to small spatial displacement.

This creates a clean method boundary:

> **reference information is useful, but reference-to-primary alignment is part of the observation model.**

The next test must therefore target alignment itself, not retune V1 thresholds or weaken the FPR criterion.

## Next method step

V2.1 should estimate a small translation between reference nuisance delta and primary delta **without biological labels**, then perform the same one-dimensional nuisance projection. The alignment objective must be robust to a compact target so target pixels do not determine the shift.

A suitable fixed design is a ±2 px translation search minimizing a trimmed residual-energy objective that discards the largest 10% of residual magnitudes. The downstream V1 classifier remains fixed.
