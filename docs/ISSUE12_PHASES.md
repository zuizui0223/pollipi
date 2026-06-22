# Issue 12 implementation notes

PolliPi is an activity-informed scheduled timelapse system, not a pure motion-trigger camera.

## Phase 1: candidate-first review

- Motion creates candidate evidence.
- Human review labels are `visit`, `noise`, or `unclear`.
- Legacy labels are interpreted for compatibility:
  - `insect` / `positive` -> `visit`
  - `non_insect` / `negative` -> `noise`
- `unclear` remains reviewable but is excluded from candidate training by default.

## Phase 2: ROI redesign

- The existing manually drawn ROI is treated as a `floral_display_zone`.
- The API accepts an optional background-control ROI.
- Candidate evidence includes floral-zone score, control-zone score, zone-minus-control score, grid changed-cell metrics, compactness, whole-frame score, and candidate reasons.
- ROI tracking is kept as scene/zone registration evidence; failures are logged and do not suppress scheduled capture.

## Phase 3: candidate-only ML

- Training reads reviewed candidate records from `event_log.csv`.
- Only `visit` and `noise` reviewed candidate rows are used.
- Unreviewed scheduled images and `unclear` candidates are excluded.
- The current local model remains a small offline OpenCV SVM, using candidate images as the input set.

## Phase 4: adaptive scheduler

- Adaptive mode keeps scheduled capture as the backbone.
- Candidate evidence updates the next scheduled interval.
- Decisions are smoothed and written to `adaptive_decisions.csv`.
- The decision log records previous interval, new interval, activity score, candidate rate, visit-likeness, noise-likeness, and reason.
