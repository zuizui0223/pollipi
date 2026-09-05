# V3–TNOA controlled-real benchmark

Status: **pre-data protocol**. This benchmark is the next empirical generation after the two fresh synthetic bridge generations. It is deliberately application-independent and must be run before using a natural-history application as confirmatory evidence.

## 1. Scientific question

The controlled-real generation tests the two-layer principle directly:

> **Can independently observed nuisance evidence license an upstream representation change that improves usable target/process evidence, while a downstream TNOA layer preserves the same false-support semantics and refuses certainty when target and nuisance remain jointly supported?**

The benchmark is not a pollination detector test. PolliPi is only one acquisition platform.

## 2. Why this generation is needed

The current synthetic evidence established two facts that must both be respected.

1. Correctly coupled target-free temporal reference information repeatedly improves representation quality and can increase downstream safe coverage.
2. Applying V3 without sufficient representation entitlement can remove target geometry in low-nuisance windows; improved representation quality also does not, by itself, guarantee acceptable downstream false certainty.

Therefore the controlled-real benchmark adds a **representation-entitlement gate** upstream of V3, mirroring TNOA's evidence-entitlement gate downstream.

No third rescue model is fitted in the completed synthetic world.

## 3. Two entitlement layers

### Layer R — representation entitlement

Let a target-free nuisance-reference sequence be `R[1:T]`.

The predeclared activity score is

\[
A_R = \sqrt{\operatorname{mean}_{t,z}\left(R_{t,z}-\bar R_z\right)^2}/255.
\]

`A_R` uses only the target-free reference stream. It does not use target truth, target scores, nuisance labels from the primary image, or downstream TNOA outcomes.

A development-only threshold `tau_R` is calibrated from prospectively designated **nuisance-off** reference blocks so that empirical false activation on those development blocks is no greater than `alpha_R = 0.05` under the strict rule

\[
\text{V3 entitled} \iff A_R > \tau_R.
\]

If V3 is not entitled, the upstream representation remains raw. A quiet reference is **not** evidence that the target/process is absent.

### Layer S — semantic entitlement

After the chosen representation is formed, TNOA retains its own support semantics and `alpha_S = 0.05` calibration. TNOA is not allowed to inherit certainty from the representation layer.

Thus:

- Layer R asks whether the evidence licenses changing the representation;
- Layer S asks whether the resulting evidence licenses a semantic decision.

These are separate contracts.

## 4. Controlled physical world

The setup must provide three independent streams:

1. **primary visual stream** — contains the local target/process and any imposed nuisance;
2. **target-free nuisance reference** — contains nuisance carriers but excludes the target/process by design;
3. **independent target/process truth** — a programmed schedule, instrumented actuator, independent sensor, or blinded external annotation that is never passed to V3.

A low-cost implementation may use a deterministic local moving marker/object for target truth and separately controlled illumination, camera perturbation, or moving background material for nuisance. The scientific contract does not depend on the object class.

## 5. Frozen factorial conditions

Each independent trial belongs to one of ten physical cells:

`target_state`:

- `absent`
- `present`

crossed with `nuisance_family`:

- `none`
- `photometric_shared`
- `rigid_shared`
- `nonrigid_shared`
- `local_nonshared`

Interpretation:

- shared nuisance families should be represented in the target-free reference;
- `local_nonshared` is a boundary condition in which the primary stream contains nuisance that the reference does not carry;
- target presence is set by the independent schedule and never inferred from the primary image for truth.

The benchmark may add descriptive nuisance metadata, but it may not create new confirmatory cells after heldout scoring begins.

## 6. Sequence contract

The first controlled-real generation freezes:

- sequence length `T = 9`;
- V3 temporal rank `K = 3`;
- fixed frame interval declared before recording;
- fixed primary and nuisance-reference regions before scoring;
- one independent trial may not cross a setup/reset boundary;
- raw frames and timestamps are retained losslessly or with a predeclared lossless luminance representation;
- no V3 or TNOA scoring occurs during acquisition.

The interval is a property of the physical setup and must be fixed before data collection. It is not tuned on heldout target outcomes.

## 7. Scoring arms

Every heldout trial is replayed through the following frozen arms.

1. `raw` — no upstream correction;
2. `matched_v3_always` — correctly coupled V3 applied to every trial; retained as a diagnostic for overprojection;
3. `matched_v3_entitled` — correctly coupled V3 applied only when Layer-R support is present, otherwise raw representation;
4. `time_broken_v3_entitled` — deterministic time-broken reference control with the same Layer-R rule;
5. `no_reference` — equivalent to raw for the representation layer and retained for audit clarity.

The key method comparison is `matched_v3_entitled` versus `raw` and `time_broken_v3_entitled`. `matched_v3_always` is not the proposed final policy; it tests the representation-entitlement hypothesis directly.

## 8. Development and heldout split

Trials are assigned prospectively by `recording day x setup x block`.

Development data may be used only to:

- validate acquisition and joins;
- calibrate `tau_R` using nuisance-off reference activity only;
- calibrate representation-specific TNOA support thresholds under the frozen `alpha_S = 0.05` semantics;
- verify that the predeclared scoring code runs.

Target-positive development recall may be reported but may not be optimized.

Heldout trials remain unopened until all thresholds, reference controls, exclusion rules, uncertainty procedures, and promotion criteria are hashed and frozen.

Planned minimum per physical cell:

- 12 development trials;
- 24 heldout trials.

Counts may be increased before any heldout score is computed, but not reduced after scoring begins.

## 9. Primary estimands

### Representation layer

- false V3 activation rate on nuisance-off heldout trials;
- V3 activation rate on each shared-nuisance family;
- activation rate on `local_nonshared` as a diagnostic, not as evidence of correctness;
- target-only degradation of target/process geometry under `matched_v3_always` versus `matched_v3_entitled`.

### Semantic layer

Using the same TNOA definitions across arms:

- pooled false-certainty rate;
- safe unique-process coverage;
- target-only T-support rate;
- nuisance-only N-support rate;
- mixed target+nuisance overlap-preserving U rate;
- forced-unique rate in mixed target+nuisance trials;
- reason-coded U decomposition.

The same support-error semantics, not the same numeric score threshold, are transported across representations.

## 10. Frozen negative controls

Required controls:

- correct nuisance reference;
- deterministic time-broken reference;
- no-reference/raw baseline;
- `local_nonshared` physical nuisance condition;
- target-only nuisance-off condition to detect overprojection.

A method that improves shared-nuisance cases while damaging target-only trials without an entitlement gate is not promoted.

## 11. Uncertainty

Confirmatory uncertainty is grouped by the prospectively declared independent block unit. Frame-level or overlapping-window rows are not treated as independent replicates.

Paired comparisons should use the same physical trials across representation arms. Bootstrap or permutation resampling must resample whole independent blocks.

## 12. Promotion rule

Promotion to a real-data two-layer candidate requires all of the following on untouched heldout data:

1. Layer-R false activation on nuisance-off trials `<= 0.10` and no worse than its predeclared tolerance relative to development calibration;
2. `matched_v3_entitled` safe unique-process coverage exceeds raw by at least `+0.10`;
3. the paired 95% interval for that coverage gain has lower bound `> 0`;
4. `matched_v3_entitled` exceeds `time_broken_v3_entitled` safe coverage by at least `+0.05` with paired 95% interval lower bound `> 0`;
5. pooled false certainty for `matched_v3_entitled <= 0.10` and is not worse than raw by more than `+0.01`;
6. target-only T-support loss versus raw is `<= 0.05`;
7. forced-unique rate in mixed target+nuisance trials is not worse than raw by more than `+0.05`;
8. `matched_v3_entitled` improves target-only preservation relative to `matched_v3_always`, demonstrating that Layer R adds value rather than merely relabelling V3.

Failure of any criterion is retained as an adverse result. No within-generation rescue threshold is permitted after heldout opening.

## 13. Claim boundary

Passing this controlled-real generation would support only:

> **A target-free reference can provide evidence that licenses a representation change, and separating that entitlement from downstream semantic entitlement can improve safe inference in a controlled real visual system.**

It would not establish:

- universal nuisance removal;
- causal identification of named disturbances such as wind;
- transfer to ecology, microscopy, industry, or any other domain without validation;
- target absence from a quiet residual;
- live adaptive-control readiness;
- that V3 or TNOA is required in every visual pipeline.
