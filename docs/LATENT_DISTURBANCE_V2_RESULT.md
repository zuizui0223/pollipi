# V2 latent-disturbance primary benchmark result

Status: **positive under the frozen promotion rule, but the exact-reference arm is an oracle-like upper bound and is not yet a field claim.**

Source workflow: `33934058487` on branch `feature/latent-disturbance-v2-benchmark`.

Artifact: `latent-disturbance-v2-result`, artifact id `9959556875`, artifact digest `sha256:bf51c5311ab247c0c59e859c6fee5116beddb878a5cbca6fcc9031f154d5951e`.

Result JSON SHA-256: `66d2d8f5524bfe627dc0635844c504fd20557f50a8a6f381c3ac1853c5151198`.

## Frozen primary result

The downstream PolliPi V1 classifier was unchanged. Only the pre-classification representation differed.

| condition | mixed-target recall | nuisance false-event rate | balanced utility | target-only recall |
| --- | ---: | ---: | ---: | ---: |
| correct event-matched reference | **1.0000** | **0.0000** | **1.0000** | 1.0000 |
| corrupted reference | 0.3984 | 0.2383 | 0.5801 | 1.0000 |
| no reference | 0.2969 | 0.2383 | 0.5293 | 1.0000 |

All four prespecified promotion criteria passed:

1. mixed-target recall gain versus no-reference >= 0.10: **pass** (`+0.7031`);
2. nuisance false-event rate no worse than no-reference: **pass** (`0.0000` vs `0.2383`);
3. balanced utility gain versus corrupted-reference >= 0.08: **pass** (`+0.4199`);
4. target-only recall loss <= 0.05: **pass** (`0.0000` loss).

Therefore `promoted_to_candidate_method=true` for the simulation hypothesis.

## Scenario detail

With no reference, the frozen V1 classifier retained:

- target + wind: `0/64`;
- target + shadow: `12/64`;
- target + shake: `0/64`;
- target + local sway: `64/64`.

With the exact event-matched reference, all four mixed-target scenarios were retained `64/64` and all four nuisance-only scenarios were rejected `64/64`.

Corrupting the reference coupling removed most of the benefit: target + wind remained `0/64`, target + shadow `10/64`, target + shake `28/64`, while local-sway nuisance itself became a false local candidate in `61/64` replicates.

## Interpretation

This is a **mechanism existence test**, not a realistic field-performance estimate.

The result shows that, in these controlled worlds, target-free information about the event-matched nuisance contains enough information to reconstruct a residual representation on which the unchanged V1 classifier recovers local target signal. The benefit is not explained by merely supplying an extra image, because a nuisance-class-matched but event-decoupled reference performs much worse.

However, the correct reference shares the exact nuisance realization with the primary channel. This is intentionally an upper-bound condition. Perfect `1.0 / 0.0` performance should therefore **not** be presented as expected field accuracy.

## Next required test

Before any field-shadow promotion, degrade the correct reference without changing the primary worlds or V1 classifier:

- amplitude mismatch + sensor noise;
- small spatial misalignment;
- partial rather than exact nuisance coupling.

Those degradation levels and pass/fail rules must be frozen before execution. If benefit collapses under small realistic mismatch, the current V2 representation is too oracle-like for field promotion even though the primary mechanism test is positive.
