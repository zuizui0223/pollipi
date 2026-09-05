# V3 temporal nuisance-subspace benchmark — frozen before execution

Status: **simulation-only next-generation method specification. No runtime or field-capture behaviour changes.**

## Why V3 exists

V2 established that event-matched target-free reference information can contain useful nuisance information, but a universal single-frame pixel-subtraction rule failed under spatial mismatch. Diagnostics localized two distinct seams:

- broad wind/shake: shift is identifiable, but finite spatial support/boundary residuals remain after pixelwise alignment;
- compact local sway: oracle alignment is clean, but the shift is not identifiable from a single pair.

V3 therefore stops requiring spatial correspondence. It asks whether nuisance can instead be represented by a **low-dimensional temporal subspace** learned only from a target-free reference sequence.

## Core method

For a sequence of `T=9` primary frames and a target-free reference sequence:

1. subtract each channel's own clean background;
2. flatten the reference deltas to a `T × P` matrix;
3. compute its singular-value decomposition;
4. retain the first `K=3` **temporal** left-singular vectors as the nuisance basis `U`;
5. for every primary pixel time series `d`, remove the reference-explained temporal component `U U^T d`;
6. reconstruct residual primary frames and pass each frame to the **unchanged PolliPi V1 `pipeline.analyze()`** classifier.

The reference and primary are not required to share pixel coordinates, object locations, or spatial carriers. Only temporal nuisance structure is shared.

The method also reports the fraction of primary temporal energy explained by the reference subspace. That quantity is nuisance evidence, not a probability of biological absence.

No target label, target mask, target location, scenario identity or V1 decision enters the temporal basis or projection.

## Synthetic sequence worlds

Each replicate has nine frames. The local biological target, when present, follows a monotonic traversing trajectory during the central five frames. Nuisance processes vary across time.

### Target-bearing

- `target_only`
- `target_plus_wind`
- `target_plus_shadow`
- `target_plus_shake`
- `target_plus_local_sway`

### Nuisance-only

- `wind_only`
- `shadow_only`
- `shake_only`
- `local_sway_only`

### Nuisance construction

- **wind:** broad spatial carrier with a shared time-varying amplitude; reference uses a different spatial carrier/phase and gain;
- **shadow:** broad mask with shared temporal darkening profile; reference mask occupies a different spatial region;
- **shake:** primary and reference have different scene textures but share a two-axis camera-motion time course;
- **local sway:** a compact nuisance oscillates spatially in both channels at different image locations but with the same temporal phase/frequency.

Reference frames contain **no biological target**. Mild independent reference sensor noise and gain mismatch are present by default.

## Three frozen reference conditions

1. `matched_temporal_reference` — target-free reference has the same nuisance temporal driver but independent spatial realization;
2. `time_permuted_reference` — the same target-free reference frames are permuted in time, preserving their marginal spatial/energy content while breaking event-level temporal coupling;
3. `no_reference` — uncorrected primary sequence.

The permutation is deterministic within a replicate and is never selected using outcomes.

## Evaluation

The frozen V1 classifier runs independently on each residual frame against the original primary background.

A frame is a local candidate if V1 returns `uncertain_local_activity` or `strong_visitation_candidate`.

Report:

- target-frame recall for each target-bearing scenario;
- mixed-target recall averaged over the four target+nuisance scenarios;
- nuisance-only false-local frame rate;
- local-sway-only false-local frame rate;
- broad nuisance false-local frame rate averaged over wind/shadow/shake;
- target episode recall: proportion of target-bearing replicates with at least two local-candidate target frames;
- nuisance false-episode rate: proportion of nuisance-only replicates containing at least two consecutive local-candidate frames;
- balanced utility = `(mixed_target_frame_recall + 1 - nuisance_false_frame_rate) / 2`;
- reference-explained primary energy fraction.

## Frozen replication

- sequence length: `9` frames;
- temporal rank: `K=3`;
- replicates: `48` per scenario;
- master seed: `20260905`;
- all three reference conditions use the same primary latent world within each replicate.

## Frozen promotion rule

V3 is promoted from simulation hypothesis to a **temporal-reference candidate** only if all are true:

1. matched-reference mixed-target frame recall exceeds no-reference by at least `0.15`;
2. matched-reference nuisance false-frame rate is at least `0.10` lower than no-reference;
3. matched-reference balanced utility exceeds time-permuted-reference by at least `0.10`;
4. matched-reference target-only frame recall is no more than `0.05` below no-reference;
5. matched-reference local-sway false-frame rate is at least `0.30` lower than no-reference;
6. matched-reference broad-nuisance false-frame rate is no more than `0.05` above no-reference.

Scientific promotion is never a CI success condition. Any failed criterion is retained without tuning `K`, sequence length, nuisance amplitudes, permutation, target path or V1 thresholds.

## Claim boundary

A positive result would support only:

> In controlled synthetic sequences, target-free reference data can provide a spatially non-corresponding temporal nuisance subspace that improves separation of shared disturbance from a traversing local target before an unchanged downstream observer, and the benefit depends on correct temporal coupling.

It would not establish physical wind identity, field performance, deep-learning superiority, biological absence, or live adaptive-capture readiness.

A positive V3 result would justify designing a real fixed-interval multi-frame shadow audit. A negative result would require a more flexible learned/uncertainty-aware temporal representation rather than further single-frame tuning.
