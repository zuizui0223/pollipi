# V3 real-data validation audit — generic method, PolliPi implementation

Status: **pre-data real-world protocol. The scientific method is application-independent; PolliPi is one available acquisition platform. No live adaptive action or field-domain claim is licensed by this document.**

Canonical scientific scope: `LATENT_DISTURBANCE_V3_GENERAL_METHOD.md`.

## 1. Purpose

V3 simulation showed that a target-free reference can supply a spatially non-corresponding temporal nuisance subspace that improves separation of shared disturbance from a localized target/process, including under one-frame lag and 75% temporal coupling.

The next test changes domains rather than tuning simulation parameters:

> **Does the frozen V3 temporal representation improve recovery of an independently known local target/process and rejection of shared nuisance in real fixed-interval visual sequences when nuisance-reference information is defined independently of target truth?**

This is **not a pollination-specific question**. Flower visitation is one possible validation application because PolliPi already supplies suitable hardware and provenance. Other valid applications include animal passage, outdoor small-object/event monitoring, plant/phenology imaging, microscopy, controlled laboratory motion, or other visual systems with an independently measurable local signal and shared disturbance.

## 2. Three streams must remain distinct

### 2.1 Primary visual stream

The full fixed-interval image sequence containing the focal target/process and nuisance. In the PolliPi implementation this is the 640 x 360 low-resolution probe sequence.

### 2.2 Nuisance-reference stream — algorithm input

Generation 1 may use a **prospectively declared target-free rectangle within the same frame** or a separately recorded target-free reference stream.

The reference:

- is fixed before target/process truth is inspected;
- excludes the focal target/process by design;
- may contain vegetation motion, illumination change, vibration, camera motion or other nuisance carriers;
- is allowed to be spatially unrelated to the focal target;
- is passed to V3 only as temporal reference information.

If the target/process enters or contaminates the reference, that is **reference contamination**, not evidence that the target is absent. Contaminated or unresolved windows stay in the audit ledger and are handled under the frozen scoring manifest.

### 2.3 Independent target/process truth — never algorithm input

Truth must come from an independent source appropriate to the application and is never passed to V3.

Examples:

- independent camera or manual annotation;
- controlled object/event schedule;
- instrumented actuator or motion stage;
- laboratory reference sensor;
- for PolliPi visitation studies, the existing TNOA Phase-B independent biological reference.

The nuisance-reference stream and target/process truth source are deliberately different objects.

## 3. Acquisition mode

The first PolliPi implementation uses a **standalone development/validation recorder**. It must not run concurrently with `pollipi.service` and must not enable a PolliPi live policy.

For one collection block it records:

- one 640 x 360 Y-luminance frame every prospectively declared interval (default 5 s);
- every frame as lossless PGM;
- wall-clock and monotonic timestamps;
- frame SHA-256;
- collection/run metadata;
- a fixed nuisance-reference ROI;
- a manifest with `live_adaptive_actions=false`.

The recorder does **not** run V3, V1, target classification or field threshold selection during collection.

A non-PolliPi validation system may use a different recorder so long as the same separation, timing, provenance and blinding requirements are preserved.

## 4. Required prospective metadata

Before recording, provide:

- `collection_id`;
- `prospective_role`: `development` or `heldout`;
- recording date/day;
- scene/setup ID;
- recording block;
- comparison session ID;
- primary device/source ID;
- nuisance-reference definition and source ID;
- independent target/process-truth source ID;
- frame count chosen before collection;
- probe/frame interval chosen before collection;
- maximum acceptable timing error chosen before collection.

For the PolliPi implementation, the first nuisance reference is `x0,y0,x1,y1` inside the 640 x 360 frame. It must have positive area and lie completely inside the frame.

Application-specific metadata such as site, organism, flower, laboratory condition or object class are optional descriptors, not part of the generic method definition.

## 5. Fixed V3 method for real-data replay

Initial replay inherits the frozen simulation representation unchanged:

- sequence length `T=9`;
- temporal rank `K=3`;
- reference basis obtained only from target-free nuisance-reference data;
- no target mask, truth label, scenario label or downstream decision enters the basis;
- downstream observer/configuration is frozen at the source commit used for collection.

No heldout score may be used to choose `K`, window length, reference region/source, downstream threshold or temporal alignment.

## 6. Window construction

Candidate windows must:

- contain 9 consecutive recorded frames from one collection/block;
- never cross run/setup/block boundaries;
- satisfy the prospectively declared timing-error bound;
- retain hashes and source filenames/IDs;
- carry reference-contamination state: `clean`, `contaminated`, or `unresolved`;
- carry independent target/process truth.

Overlapping windows may be retained descriptively, but confirmatory uncertainty must be grouped at a leakage-safe unit such as:

`recording day x scene/setup x recording block`.

## 7. Blinding and truth

- annotators or truth operators do not see V1/V3 scores or decisions;
- unresolved truth remains unresolved;
- reference contamination is annotated separately from target truth;
- where human annotation is used, a prospectively declared subset should be independently double-annotated before scoring;
- where machine/instrument truth is used, its error/tolerance must be specified before scoring.

For PolliPi biological validation, the existing Phase-B minimum of 20% double annotation remains applicable.

## 8. Development versus heldout

### Development blocks

May be used only to verify:

- frame integrity and hashes;
- timing;
- reference extraction;
- independent truth join;
- reference-contamination workflow;
- V3 executes correctly on real arrays.

They must not be used to tune the heldout reference definition, `T=9`, `K=3`, or downstream thresholds based on target outcome.

### Heldout blocks

Remain untouched until a separate scoring manifest freezes:

- exact primary estimand;
- reference-contamination handling;
- minimum number of independent scoring blocks;
- uncertainty procedure;
- matched-reference / negative-control / raw comparison;
- promotion/falsification criteria.

Until then, `heldout_scoring_allowed=false`.

## 9. Required negative control

The confirmatory generation must include a reference control that preserves reference data but destroys the relevant coupling without using outcomes, for example a deterministic within-block circular shift or predeclared permutation.

The core scientific comparison remains:

1. correctly coupled target-free reference;
2. frozen time-broken/mismatched reference control;
3. raw/no-reference baseline.

This comparison, rather than the ecological application, is the central test of the method.

## 10. Acquisition readiness criteria

A collection is structurally suitable only if:

- at least 9 consecutive frames exist;
- every registered frame exists and matches its checksum;
- timestamps are strictly increasing;
- measured frame timing stays inside the prospective error bound;
- the reference definition is valid and predeclared;
- algorithmic/live actions did not affect acquisition;
- an independent target/process truth source was expected before collection.

It becomes suitable for truth preparation only after the operator verifies that the independent truth material was actually captured and archived.

## 11. Claim boundary

Passing intake does not establish real-world V3 performance.

Do not infer:

- a named physical nuisance such as wind from temporal components alone;
- target/process absence from a quiet residual;
- universal domain transfer;
- field-optimal `K=3`;
- arbitrary synchronization tolerance;
- live adaptive-control readiness;
- that the scientific scope is limited to pollination, insects, flowers or ecology.

## 12. PolliPi's role

PolliPi is retained as a **validation harness** because it already provides fixed-interval camera acquisition, provenance, shadow-only safeguards and independent annotation infrastructure. A successful PolliPi test would be one real-domain demonstration of the general method, not the definition of the method itself.
