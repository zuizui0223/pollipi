# V2 reference-degradation robustness — frozen after primary benchmark, before execution

Status: **post-primary robustness specification.** The primary exact-reference result is already known and is not re-used as a promotion criterion here.

## Question

Does the V2 benefit persist when the target-free reference is still event-matched but is no longer an exact pixel-level nuisance copy?

The primary latent worlds, target amplitudes, nuisance amplitudes, master seed, replicate count and downstream PolliPi V1 classifier remain unchanged.

## Frozen reference conditions

For each primary latent world, compare:

1. `no_reference` — unchanged V1 input;
2. `gain_noise_reference` — correct nuisance delta multiplied by a random gain in `[0.70, 1.30]` plus independent Gaussian reference noise (`sd=2.5` luminance units);
3. `shift2_reference` — correct nuisance delta spatially displaced by a random non-zero shift with maximum absolute displacement `2 px`, plus Gaussian noise (`sd=1.5`);
4. `partial75_reference` — `0.75 * correct_nuisance + 0.25 * corrupted_nuisance` plus Gaussian noise (`sd=1.5`).

All degraded references remain target-free. No target mask, target location, scenario label or V1 decision enters the nuisance estimator.

## Outcomes

Same definitions as the primary benchmark:

- mixed-target recall;
- target-only recall;
- nuisance-only false-event rate;
- balanced utility;
- per-scenario local-candidate rate.

Use `64` deterministic replicates per scenario and master seed `20260905`, paired across conditions.

## Frozen robustness promotion rule

The minimal linear V2 representation is promoted from an oracle-like simulation mechanism to a **reference-robust simulation candidate** only if all are true:

1. `gain_noise_reference` mixed-target recall exceeds `no_reference` by at least `0.10`;
2. `shift2_reference` mixed-target recall exceeds `no_reference` by at least `0.10`;
3. `partial75_reference` balanced utility exceeds `no_reference` by at least `0.08`;
4. every degraded-reference nuisance false-event rate is no more than `0.05` above `no_reference`;
5. every degraded-reference target-only recall is no more than `0.05` below `no_reference`.

No degradation parameter or threshold is changed after aggregate results are observed.

## Interpretation boundary

Passing this test would justify **real fixed-interval shadow collection with a reference stream/region**. It would still not justify live capture decisions or a claim that physical wind is identified.

Failing this test means the exact-reference primary result is too oracle-like for this linear projection to advance; the next method would need a representation tolerant of spatial/temporal mismatch (for example learned or low-rank spatiotemporal nuisance embeddings) before field use.
