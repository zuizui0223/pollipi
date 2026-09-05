# Standard controlled-real bench v1 for V3–TNOA

Status: **pre-data reference implementation**. This bench is one reproducible way to test the application-independent method; it is not part of the method definition.

## 1. Purpose

Create real camera sequences in which four things are independently known:

1. the local target/process is present or absent;
2. a nuisance is physically imposed or absent;
3. a target-free visual reference is available to V3;
4. target truth and nuisance truth are logged independently of that visual reference.

The benchmark tests two separate entitlements:

- **Layer R — representation entitlement:** is there enough target-free reference evidence to justify changing the representation with V3?
- **Layer S — semantic entitlement:** after representation, is there enough evidence to make a T/N decision rather than preserve U?

## 2. Reference bench identities

The recommended first implementation uses these logical IDs:

- `setup_id = controlled-real-bench-v1`
- `primary_source_id = fixed-camera-primary-v1`
- `nuisance_reference_source_id = target-free-reference-roi-v1`
- `nuisance_truth_source_id = nuisance-controller-log-v1`
- `target_truth_source_id = target-controller-log-v1`
- `target_truth_schedule_id = target-schedule-v1`
- `nuisance_truth_schedule_id = nuisance-schedule-v1`

A different physical implementation must use different IDs and regenerate the plan before acquisition.

## 3. Physical layout

Use one fixed camera on a rigid support. Divide the visible scene into two non-overlapping regions:

### Primary region
Contains the deterministic local target plus nuisance carriers.

Recommended target: a high-contrast marker moved on a repeatable one-way path by a programmable actuator or other deterministic mechanism. The target controller log defines target truth; image detection never defines target truth.

### Target-free nuisance-reference region
Contains nuisance carriers but the target cannot physically enter it. It may use a separate leaf/fabric element, diffuse reference surface, or other structure affected by shared nuisance. This region is algorithm input only.

The reference region must be fixed before development outcomes are inspected.

## 4. Independent truth channels

### Target truth
A programmed target schedule or actuator log states whether the target/process was present and its timing. It is not derived from V3, V1, TNOA, or image classification.

### Nuisance truth
A separate controller/event log states which nuisance family was physically commanded for each trial. The nuisance truth log is not the target-free image reference.

For manually actuated nuisances, the operator must follow the pre-generated trial plan and record command start/stop in the nuisance-truth ledger before scoring.

## 5. Five nuisance families

The physical identity may vary, but the causal structure must match these cells.

### `none`
No deliberate nuisance. Camera, target support, reference carrier, and illumination remain nominally stable.

### `photometric_shared`
A lamp/LED or controlled occluder changes illumination across both primary and reference regions without intentionally moving the target.

### `rigid_shared`
A reproducible camera/support perturbation produces shared rigid image motion across both regions.

### `nonrigid_shared`
A fan or controlled airflow drives spatially distinct compliant elements in primary and reference regions. They need not move pixel-for-pixel together; the intended common cause is the shared actuator.

### `local_nonshared`
A nuisance moves only in the primary region while the target-free reference remains shielded/static. This is an essential falsification cell: Layer R should not infer a shared nuisance merely because the primary looks disturbed.

## 6. Target states

Each nuisance family is crossed with:

- `target_state = absent`
- `target_state = present`

Target-present trials use the same predeclared target trajectory regardless of nuisance family. Target-absent trials do not substitute a different visual object.

## 7. Acquisition timing

Reference configuration:

- grayscale or luminance frames are acceptable;
- `sequence_length = 9` is frozen;
- `temporal_rank = 3` is frozen;
- nominal `frame_interval_s = 0.5` for bench v1;
- one scored sequence therefore spans 4 s between first and last frame.

The 0.5 s interval is an engineering reference choice, not a universal method parameter. If the physical camera/actuator cannot meet it reliably, change the setup ID and interval **before any development acquisition**, regenerate the plan, and preserve the new plan hash. Do not change interval based on outcome performance.

## 8. Trial counts and randomization

Use the deterministic planner with the frozen seed unless a new pre-data generation is explicitly created:

- 10 physical cells per balanced round;
- 12 development rounds = 120 development trials;
- 24 heldout rounds = 240 heldout trials;
- 360 total trials;
- each round contains every target × nuisance cell exactly once;
- within-round order is seed-randomized;
- the trial-plan SHA-256 is archived before acquisition.

## 9. Layer-R calibration

For each sequence, compute target-free reference temporal RMS activity `A_R`.

Calibrate `tau_R` using only **development trials with nuisance truth = none** and frozen `alpha_R = 0.05`.

The representation-entitled arm applies V3 only when:

`A_R > tau_R`.

Do not use target-positive recall or heldout outcomes to choose `tau_R`.

## 10. Layer-S evaluation

TNOA remains downstream and independent, with frozen `alpha_S = 0.05` support semantics.

The benchmark compares:

1. raw representation;
2. matched V3 always-on;
3. matched V3 only when Layer R entitles representation change;
4. time-broken/mismatched V3 under the same Layer-R rule;
5. raw/no-reference audit arm.

A representation improvement is not allowed to create semantic certainty automatically.

## 11. Primary diagnostic contrasts

The bench is designed to answer four concrete questions:

1. Does matched target-free reference outperform time-broken reference?
2. Does Layer-R gating protect target-only/no-nuisance trials from V3 overprojection?
3. Does Layer-R gating still allow V3 to improve shared-nuisance trials?
4. Under the same semantic error budget, does Layer S gain safe coverage without excessive false certainty?

## 12. Stop rule

No heldout result may trigger a within-generation threshold, feature, rank, timing, ROI, or nuisance-family revision.

Any failed criterion is a retained boundary result. A revised method requires a new generation, new plan hash, and new heldout data.
