# V2.1 alignment-aware nuisance projection result

Status: **adverse. The alignment revision improves target recall but worsens nuisance false events and is not promoted.**

Source workflow: `33934445009`.

Artifact id: `9959684467`.

Artifact digest: `sha256:1d5997def4332cc465d197af9d5a47c01e991b1c1f4f52ad143ac2969ae75f8c`.

Result JSON SHA-256: `5c8d63556d059ee0d576d9f9769b692d35674b63e8a5465b1b89231ebbe193cf`.

## Aggregate result

| condition | mixed-target recall | nuisance false-event rate | balanced utility | target-only recall |
| --- | ---: | ---: | ---: | ---: |
| aligned V2.1 | **0.8711** | **0.3906** | 0.7402 | 1.0000 |
| unaligned 2 px V2 | 0.6914 | 0.3047 | 0.6934 | 1.0000 |
| no reference | 0.2969 | 0.2383 | 0.5293 | 1.0000 |

The alignment search recovers more mixed target signal, but the nuisance false-event rate rises further. Two of five frozen promotion criteria therefore fail:

- nuisance FPR must remain within no-reference + 0.05: **fail**;
- balanced-utility gain versus unaligned must be at least 0.08: **fail** (`+0.0469`).

`promoted_to_simulation_robust_field_shadow_candidate=false`.

## Failure localization

Aligned nuisance-only local-candidate rates:

- wind: `0.4375`;
- shadow: `0.0000`;
- shake: `0.5000`;
- local sway: `0.6250`.

The search uses all `25/25` candidate shifts across the stochastic set rather than concentrating on a small subset. This is consistent with a weakly identified or flat alignment objective rather than reliable recovery of the injected offset.

## Interpretation

The failure is informative:

1. nuisance reference information is useful — recall remains much higher than no-reference;
2. exact/gain/partial-coupling references work well;
3. small spatial mismatch is the critical seam;
4. a single-frame trimmed residual-energy search does not solve that seam and can turn broad nuisance into local residual structure.

Therefore we should **not** tune the trim fraction, shift range or V1 classifier thresholds to rescue V2.1.

## Next step: identifiability diagnostic

Before designing another correction, measure whether the alignment problem itself is identifiable in these synthetic worlds.

The diagnostic should regenerate the same 2 px reference perturbations while recording the injected `(dy, dx)` metadata, run the frozen V2.1 aligner, and report:

- exact inverse-shift recovery rate;
- mean Manhattan shift error;
- per-nuisance recovery rates;
- alignment-loss margin between the best and second-best candidate.

If true shifts are poorly recovered, the next method must use multi-frame temporal structure or a low-rank/learned nuisance representation rather than more single-pair spatial tuning.
