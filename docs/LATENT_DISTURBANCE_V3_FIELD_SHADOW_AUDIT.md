# V3 real-data field shadow audit — prospective acquisition and scoring gate

Status: **pre-data real-field protocol. No live adaptive action and no field V3 claim are licensed by this document.**

## 1. Purpose

V3 simulation showed that a target-free reference can supply a spatially non-corresponding temporal nuisance subspace that improves separation of shared disturbance from local target motion, including under one-frame lag and 75% temporal coupling.

The next test changes domains rather than tuning simulation parameters:

> **Does the frozen V3 temporal representation improve biological target recovery and nuisance rejection on real fixed-interval flower-camera sequences when nuisance reference information is defined independently of biological truth?**

## 2. Three streams must remain distinct

### 2.1 Primary visual stream

The full PolliPi low-resolution frame sequence containing the focal flower/scene. This is the stream on which the unchanged V1 observer is ultimately scored.

### 2.2 Nuisance-reference stream — algorithm input

V3 field generation 1 uses a **prospectively declared target-free rectangle within the same low-resolution frame**.

The rectangle:

- is fixed before biological truth labels are inspected;
- is outside the focal flower/target zone;
- may contain vegetation, illumination changes, camera motion and other environmental carriers;
- is allowed to be spatially unrelated to the focal target;
- is passed to V3 only as a temporal reference sequence.

A target/insect entering this rectangle is **reference contamination**, not evidence of absence. Contaminated or unresolved windows are retained in the audit ledger and handled under the frozen scoring manifest rather than silently treated as clean reference.

A later generation may test a companion-camera nuisance reference. It is not mixed into this first field generation.

### 2.3 Independent biological-truth stream — never algorithm input

Biological truth comes from the existing TNOA Phase-B independent reference contract and is never passed to V3.

Use the existing truth states:

- `no_insect`;
- `insect_in_context`;
- `target_contact`;
- `visit_event`;
- `truth_unresolved`.

The truth source must have its own `reference_source_id`. The nuisance-reference ROI and the biological-truth reference are deliberately different objects.

## 3. Acquisition mode

The audit recorder is **standalone and development/validation only**. It must not run concurrently with `pollipi.service` and must not enable a PolliPi live policy.

For one collection block it records:

- one 640 x 360 Y-luminance probe every prospectively declared interval (default 5 s);
- every probe as a lossless PGM file;
- frame timestamp and monotonic timestamp;
- frame SHA-256;
- collection/run metadata;
- the fixed nuisance-reference ROI;
- a manifest that explicitly records `live_adaptive_actions=false`.

The recorder does **not** run V3, V1, target classification or field threshold selection during collection.

## 4. Required prospective metadata

Before recording, provide:

- `collection_id`;
- `prospective_role`: `development` or `heldout`;
- `recording_day`;
- `site_id`;
- `focal_scene_id`;
- `recording_block`;
- `comparison_session_id`;
- `primary_device_id`;
- `plant_species` if applicable;
- `nuisance_reference_roi = x0,y0,x1,y1` in the 640 x 360 probe frame;
- `truth_reference_source_id`;
- `frame_count` chosen before collection;
- `probe_interval_sec` chosen before collection;
- `max_timing_error_sec` chosen before collection.

The nuisance ROI must have positive area and lie completely inside the frame.

## 5. Fixed V3 method for field replay

Field replay initially inherits the frozen simulation representation unchanged:

- sequence length `T=9`;
- temporal rank `K=3`;
- reference basis obtained only from the target-free nuisance-reference ROI;
- no target mask, biological truth, scenario label or V1 result enters the basis;
- downstream observer is the existing V1 `pipeline.analyze()` configuration frozen at the source commit used for the collection.

No field score is allowed to choose `K`, window length, ROI, V1 thresholds or reference alignment after heldout truth is inspected.

## 6. Window construction

Candidate field windows must:

- contain 9 consecutive recorded probes from one collection/run;
- never cross a run or recording-block boundary;
- satisfy the prospectively declared timing-error bound;
- retain all frame hashes and source filenames;
- carry a reference-contamination state: `clean`, `contaminated`, or `unresolved`;
- carry biological truth from the independent reference stream.

Overlapping windows may be retained for descriptive visualization, but confirmatory uncertainty must be grouped at the minimum leakage-safe unit:

`recording day x focal scene x recording block`.

## 7. Blinding and truth

Use the existing Phase-B principle:

- annotators do not see V1/V3 scores or decisions;
- at least 20% of registered truth material is independently double-annotated;
- adjudication is completed before heldout algorithm scoring;
- `truth_unresolved` remains unresolved.

Additionally annotate whether the nuisance-reference ROI contains a biological target. This annotation is about reference contamination only and is not fed back into the V3 basis construction.

## 8. Development versus heldout

### Development blocks

May be used only to verify:

- frame integrity and hashes;
- timing;
- ROI extraction;
- independent truth join;
- reference-contamination annotation workflow;
- V3 code executes on real image arrays.

Development blocks must not be used to tune `T=9`, `K=3`, the nuisance ROI of a heldout block, or V1 thresholds based on biological outcome.

### Heldout blocks

Remain untouched until a separate **field scoring manifest** freezes:

- the exact primary estimand;
- reference-contamination handling;
- minimum number of scoring blocks selected prospectively;
- paired block-bootstrap or equivalent uncertainty procedure;
- the matched-reference / negative-control / raw comparison;
- field promotion criteria.

Until that manifest exists, `heldout_scoring_allowed=false`.

## 9. Negative control

The field scoring generation must include a time-coupling negative control constructed without using outcomes, e.g. deterministic within-block circular/permuted nuisance-reference time order.

The scientific comparison is therefore:

1. matched real nuisance-reference timing;
2. frozen time-broken nuisance-reference control;
3. raw/no-reference V1.

## 10. Acquisition readiness criteria

A collection is structurally suitable for V3 window preparation only if:

- at least 9 consecutive frames exist;
- every registered frame exists and matches its SHA-256;
- timestamps are strictly increasing;
- measured inter-probe timing stays inside the prospectively declared error bound;
- the nuisance ROI is valid for the recorded dimensions;
- `live_adaptive_actions=false`;
- the independent biological-truth source was expected before collection.

It becomes suitable for Phase-B truth preparation only after the operator verifies and records that the independent truth stream was actually captured and archived.

## 11. Claim boundary

Passing acquisition intake does not establish V3 field performance. A field biological claim requires frozen heldout scoring after independent truth annotation.

Do not infer:

- physical wind identity from temporal components;
- biological absence from a quiet residual;
- field-optimal `K=3`;
- arbitrary synchronization tolerance;
- live adaptive-capture readiness.
