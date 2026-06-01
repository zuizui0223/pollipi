# AI Change Log

## 2026-06-01 — Field-method roadmap refocus

The user clarified that the immediate goal is to compare field recording methods, not to chase novelty or full automation first.

### Refocused main goal

PolliPi should compare these recording methods:

1. user-scheduled ordinary timelapse
2. motion-triggered recording
3. hybrid timelapse + motion-triggered recording
4. adaptive timelapse based on activity
5. flower/head ROI-based motion detection
6. tracked flower/head ROI detection
7. later positive/negative learning-assisted filtering

### Current highest-priority blocker

The PWA still does not reliably allow the user to draw a ROI directly on the camera preview/monitor image.

This must be fixed before ROI tracking or learning features are prioritized.

### Field operation requirement

Recording must continue after iPad, phone tethering, or Wi-Fi disconnects. The Pi should run autonomously after the user starts recording.

### Camera roles clarified

- `zuizui2.local` = AI Camera
- `zuizui3.local` = NoIR Wide / infrared-capable unit
- other `zuizui*.local` units = Module 3 / Module 3 Wide unless configured otherwise

### New shared document

Added `FIELD_METHOD_ROADMAP.md` as the current roadmap for recording-mode comparison.

### Updated shared documents

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`

### Do next

Fix iPad preview-based ROI drawing.

### Do not do next

- YOLO
- automatic flower detection
- insect species identification
- video recording
- cloud upload
- database migration
- strict multi-camera synchronization

## 2026-06-01 — Earlier field-mode UI work

- Simplified the PolliPi PWA start form into a field-first mode.
- Kept essential field inputs visible: `site_id`, `flower_id`, `plant_species`, `method_mode`, interval, `auto_mode`, ROI setup, ROI tracking, start, and stop.
- Moved advanced/debug settings under collapsible sections: `observer`, `notes`, `comparison_session_id`, `camera_role`, `pixel_difference`, `motion_ratio`, `idle_interval_sec`, `detection_interval_sec`, raw ROI coordinates, `roi_search_margin`, and `roi_tracking_min_score`.
- Preserved backend behavior, event review, `/events`, `/events/{event_id}/label`, and label export.
- Did not add YOLO, species identification, video recording, database migration, or cloud upload.
