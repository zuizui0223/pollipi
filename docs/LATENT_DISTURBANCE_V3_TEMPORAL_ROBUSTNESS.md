# V3 temporal-coupling robustness — frozen before execution

Status: **simulation-only secondary robustness specification. No parameter tuning or runtime changes.**

## Why this test exists

The primary V3 temporal-subspace benchmark passed all six frozen promotion criteria, but its narrowest margin was the balanced-utility advantage over a fully time-permuted reference (`+0.102604` against a `0.10` threshold).

The next question is therefore not whether another rank or threshold can improve the result. It is whether the already-promoted V3 method retains useful information when temporal coupling is imperfect in two simple, predeclared ways that are plausible for real synchronized observation streams.

## Frozen method

Keep all primary V3 choices unchanged:

- `T=9` frames;
- temporal rank `K=3`;
- the same primary worlds and nuisance amplitudes;
- the same target path;
- the same target-free reference spatial carriers;
- the unchanged PolliPi V1 `pipeline.analyze()` downstream classifier;
- `48` replicates per scenario;
- master seed `20260905`.

No target labels or V1 outcomes are used to repair the reference.

## Frozen reference conditions

1. `matched_temporal_reference` — unchanged positive V3 reference.
2. `lag1_reference` — the target-free reference nuisance delta is delayed by exactly one frame; the first delta is repeated at the leading edge. This creates a deterministic one-probe timing mismatch without changing spatial carrier or total sequence length.
3. `partial75_reference` — `75%` of the event-matched reference delta is mixed with `25%` of a deterministic within-replicate time-permuted reference delta. This preserves most shared process information while injecting an unrelated temporal component.
4. `no_reference` — uncorrected primary sequence.

The lag and 75% mixture are fixed before aggregate results are inspected.

## Metrics

Use the same metrics as primary V3:

- mixed-target frame recall;
- target-only frame recall;
- nuisance-only false-local frame rate;
- local-sway-only false-local frame rate;
- broad-nuisance false-local frame rate;
- target episode recall;
- nuisance false-episode rate;
- balanced utility.

## Frozen robustness promotion rule

V3 is promoted from a temporal-reference candidate to a **temporally robust simulation candidate** only if all are true:

### One-frame lag

1. `lag1_reference` balanced utility exceeds no-reference by at least `0.08`;
2. `lag1_reference` nuisance false-frame rate is at least `0.08` lower than no-reference;
3. `lag1_reference` target-only frame recall is no more than `0.06` below no-reference;
4. `lag1_reference` local-sway false-frame rate is at least `0.25` lower than no-reference;
5. `lag1_reference` broad-nuisance false-frame rate is no more than `0.05` above no-reference.

### 75% temporal coupling

6. `partial75_reference` balanced utility exceeds no-reference by at least `0.10`;
7. `partial75_reference` nuisance false-frame rate is at least `0.10` lower than no-reference;
8. `partial75_reference` target-only frame recall is no more than `0.06` below no-reference;
9. `partial75_reference` local-sway false-frame rate is at least `0.25` lower than no-reference;
10. `partial75_reference` broad-nuisance false-frame rate is no more than `0.05` above no-reference.

Scientific promotion is not a CI success condition. Failure is retained without changing `K`, lag size, 75% fraction, sequence length, target path, nuisance amplitudes or V1 thresholds.

## Interpretation boundary

A positive result would justify moving V3 to a real fixed-interval, synchronized multi-frame shadow audit. It would not establish tolerance to arbitrary clock drift, missing frames, real wind identity, field accuracy or live adaptive-capture readiness.

A negative result would define temporal synchronization as a hard requirement and would motivate explicit lag-aware/uncertainty-aware modeling rather than post-hoc threshold tuning.