# V3–TNOA controlled-real benchmark

Status: **pre-data protocol**. This benchmark is the next empirical generation after the two fresh synthetic bridge generations. It is deliberately application-independent and must be run before using a natural-history application as confirmatory evidence.

Reference physical implementation: `V3_TNOA_CONTROLLED_REAL_BENCH_V1.md`.

## 1. Scientific question

> **Can independently observed nuisance evidence license an upstream representation change that improves usable target/process evidence, while a downstream TNOA layer preserves the same false-support semantics and refuses certainty when target and nuisance remain jointly supported?**

The benchmark is not a pollination detector test. PolliPi is only one acquisition platform.

## 2. Why this generation is needed

The current synthetic evidence established two facts that must both be respected.

1. Correctly coupled target-free temporal reference information repeatedly improves representation quality and can increase downstream safe coverage.
2. Applying V3 without sufficient representation entitlement can remove target geometry in low-nuisance windows; improved representation quality also does not, by itself, guarantee acceptable downstream false certainty.

Therefore the controlled-real benchmark adds a **representation-entitlement gate** upstream of V3, mirroring TNOA's evidence-entitlement gate downstream. No third rescue model is fitted in the completed synthetic world.

## 3. Two entitlement layers

### Layer R — representation entitlement

Let a target-free nuisance-reference sequence be `R[1:T]`. The predeclared activity score is

\[
A_R = \sqrt{\operatorname{mean}_{t,z}\left(R_{t,z}-\bar R_z\right)^2}/255.
\]

`A_R` uses only the target-free reference stream. It does not use target truth, nuisance truth, target scores, primary-image nuisance labels, or downstream TNOA outcomes.

A development-only threshold `tau_R` is calibrated from prospectively designated **nuisance-off** trials so empirical false activation is no greater than `alpha_R = 0.05` under

\[
\text{V3 entitled} \iff A_R > \tau_R.
\]

If V3 is not entitled, the upstream representation remains raw. A quiet reference is **not** evidence that the target/process is absent.

### Layer S — semantic entitlement

After representation is selected, TNOA retains its own support semantics and `alpha_S = 0.05` calibration. TNOA is not allowed to inherit certainty from the representation layer.

- Layer R asks whether evidence licenses changing representation.
- Layer S asks whether resulting evidence licenses a semantic decision.

These are separate contracts.

## 4. Controlled physical world: four distinct objects

The setup must preserve four logically distinct objects.

1. **Primary visual stream** — contains the local target/process and any imposed nuisance.
2. **Target-free nuisance reference** — algorithm input containing nuisance carriers while excluding the target/process by design.
3. **Independent nuisance truth** — controller/event log stating which nuisance family was physically commanded. It is never derived from the nuisance-reference image.
4. **Independent target/process truth** — programmed schedule, actuator log, independent sensor, or blinded external annotation that is never passed to V3.

The nuisance-reference source must be distinct from both truth sources. Target truth and nuisance truth may share a physical controller only if they are logged as separately identifiable channels with immutable schedules.

A low-cost implementation may use a deterministic moving marker for target truth and separately controlled illumination, camera perturbation, compliant background motion, and local-only motion for nuisance truth. The scientific contract does not depend on object class.

## 5. Frozen factorial conditions

Each independent trial belongs to one of ten physical cells.

`target_state`: `absent` or `present`.

Crossed with `nuisance_family`:

- `none`
- `photometric_shared`
- `rigid_shared`
- `nonrigid_shared`
- `local_nonshared`

Shared nuisance families should be represented in the target-free reference. `local_nonshared` is a falsification condition in which the primary contains nuisance that the reference does not carry. Target presence and nuisance family are set by independent schedules, never inferred from images for truth.

## 6. Sequence contract

The first controlled-real generation freezes:

- sequence length `T = 9`;
- V3 temporal rank `K = 3`;
- fixed frame interval declared before recording;
- fixed primary and nuisance-reference regions before scoring;
- one independent trial may not cross a setup/reset boundary;
- raw frames and timestamps retained losslessly or as a predeclared lossless luminance representation;
- no V3 or TNOA scoring during acquisition.

The standard bench-v1 reference interval is 0.5 s. A different interval requires a different setup generation and a regenerated plan before development acquisition; it is not tuned on target outcomes.

## 7. Scoring arms

Every heldout trial is replayed through:

1. `raw`;
2. `matched_v3_always`;
3. `matched_v3_entitled` — V3 only when Layer-R support is present, otherwise raw;
4. `time_broken_v3_entitled` — deterministic time-broken reference with the same Layer-R rule;
5. `no_reference` — raw audit arm.

The key comparison is `matched_v3_entitled` versus raw and time-broken. Always-on V3 is retained specifically to test overprojection.

## 8. Development and heldout split

Trials are assigned prospectively by `recording day × setup × block`.

Development data may be used only to:

- validate acquisition and joins;
- calibrate `tau_R` using nuisance-truth=`none` reference activity only;
- calibrate representation-specific TNOA support thresholds under frozen `alpha_S = 0.05` semantics;
- verify scoring code.

Target-positive development recall may be reported but may not be optimized.

Heldout trials remain unopened until thresholds, controls, exclusions, uncertainty procedures, and promotion criteria are hashed and frozen.

Planned minimum per physical cell: 12 development and 24 heldout trials.

## 9. Primary estimands

### Representation layer

- false V3 activation rate when nuisance truth is `none`;
- V3 activation rate for each shared-nuisance truth family;
- activation in `local_nonshared` as a diagnostic;
- target-only degradation under always-on versus entitled V3.

### Semantic layer

Using the same TNOA definitions across arms:

- pooled false-certainty rate;
- safe unique-process coverage;
- target-only T-support rate;
- nuisance-only N-support rate;
- mixed target+nuisance overlap-preserving U rate;
- forced-unique rate in mixed trials;
- reason-coded U decomposition.

The same support-error semantics, not the same numeric score threshold, are transported across representations.

## 10. Frozen controls

Required controls:

- correct nuisance reference;
- deterministic time-broken reference;
- no-reference/raw baseline;
- `local_nonshared` physical nuisance condition;
- target-only nuisance-off condition.

A method that improves shared-nuisance cases while damaging target-only trials without an entitlement gate is not promoted.

## 11. Uncertainty

Confirmatory uncertainty is grouped by the prospectively declared independent block unit. Frame-level or overlapping-window rows are not independent replicates. Paired comparisons use the same physical trials across arms; resampling operates on whole independent blocks.

## 12. Promotion rule

Promotion requires all eight on untouched heldout data:

1. Layer-R false activation on nuisance-off trials `<= 0.10` and within its predeclared tolerance relative to development calibration;
2. `matched_v3_entitled` safe unique-process coverage exceeds raw by at least `+0.10`;
3. paired 95% interval for that gain has lower bound `> 0`;
4. `matched_v3_entitled` exceeds time-broken safe coverage by at least `+0.05` with paired 95% interval lower bound `> 0`;
5. pooled false certainty for `matched_v3_entitled <= 0.10` and is not worse than raw by more than `+0.01`;
6. target-only T-support loss versus raw is `<= 0.05`;
7. forced-unique rate in mixed target+nuisance trials is not worse than raw by more than `+0.05`;
8. entitled V3 improves target-only preservation relative to always-on V3.

Failure of any criterion is retained as an adverse result. No within-generation rescue threshold is permitted after heldout opening.

## 13. Claim boundary

Passing supports only:

> **A target-free reference can provide evidence that licenses a representation change, and separating that entitlement from downstream semantic entitlement can improve safe inference in a controlled real visual system.**

It does not establish universal nuisance removal, causal identification of named natural disturbances, cross-domain transfer without validation, target absence from a quiet residual, live adaptive-control readiness, or mandatory use of V3/TNOA in every visual pipeline.
