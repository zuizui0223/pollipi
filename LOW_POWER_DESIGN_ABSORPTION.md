# Low-Power Design Absorption Plan

This document explains how to absorb the useful design ideas from the two legacy prototype files into PolliPi, then remove the standalone prototypes to keep the repository clean for publication.

Legacy prototype files:

- `訪花イベント検出（AI)`
- `訪花イベント検出（モジュール３）`

## Principle

Do not copy these prototypes directly into production.

Absorb only the low-power design ideas that match the current PolliPi roadmap.

The production PolliPi system should remain:

- FastAPI + PWA based
- iPad-operable
- autonomous after Wi-Fi/iPad disconnects
- low-power by default
- JPEG/timelapse/event-log oriented, not continuous video-first
- suitable for comparing field recording methods

## Designs to absorb from `訪花イベント検出（モジュール３）`

This prototype is useful as the conceptual source for low-power ROI-local motion detection.

Absorb these ideas:

1. Use a low-resolution stream for detection.
2. Crop detection to the selected flower/head ROI.
3. Compare current ROI frame with previous ROI frame.
4. Compute `changed_area`.
5. Compute largest moving blob / contour area when available.
6. Classify motion size roughly as small / medium / large.
7. Require several consecutive positive frames before triggering.
8. Use a cooldown period after a trigger.
9. Save debug/metric information for later review.
10. Log ROI and motion metrics for every candidate event.

Do not absorb as-is:

- fixed hard-coded ROI
- local Qt preview window
- H.264 video-first recording
- separate `~/visit_detect` directory structure
- standalone loop outside FastAPI
- mandatory OpenCV-heavy design if a lighter implementation already exists

## Designs to absorb from `訪花イベント検出（AI)`

This prototype is useful only for AI Camera-specific comparison and possible future on-device detection tests.

Absorb these ideas:

1. AI detection boxes can be checked against the selected flower/head ROI.
2. Log detection class, confidence, and bounding box when AI Camera is used.
3. Require consecutive hits before triggering.
4. Use cooldown to avoid repeated saves.
5. Treat AI Camera as a camera-specific comparison mode.

Do not absorb as-is:

- treating the default IMX500 model as insect identification
- H.264 video-first recording
- hard-coded ROI
- local Qt preview
- production dependence on AI Camera
- species-level claims without a validated insect model

## Low-power production design

PolliPi should minimize power use by default:

1. Use scheduled JPEG timelapse as the baseline.
2. Use low-resolution frames for motion/anomaly checks.
3. Use ROI-local checks when ROI is available.
4. Use consecutive-frame confirmation before saving event images.
5. Use cooldown to avoid repeated saves from the same movement.
6. Avoid continuous video recording as a default mode.
7. Avoid continuous neural-network inference as a default mode.
8. Use AI Camera detection only as an optional camera-specific test.
9. Train/update lightweight models only when power/Wi-Fi are available.
10. Log enough metrics to evaluate false positives, false negatives, storage cost, and review effort.

## Production features to implement before deleting prototypes

The two legacy prototype files should only be deleted after PolliPi has absorbed the following features into production code:

### Module 3 / general camera absorption

- ROI-local motion detection works from PWA-selected ROI.
- Candidate events log `changed_area` or equivalent motion score.
- Candidate events log blob/contour-like metrics if available, such as `largest_blob_area` or `small_blob_count`.
- Candidate events support consecutive-frame confirmation.
- Candidate events support cooldown.
- Metrics are written to `event_log.csv` and/or `adaptive_metrics.csv`.

### AI Camera absorption

- AI Camera remains optional and camera-specific.
- If AI detection is used, detected boxes can be compared with the selected ROI.
- AI detection metadata are logged as optional fields only for AI Camera sessions.
- Documentation clearly states that the default IMX500 model is not an insect classifier.

## Cleanup rule

After the above designs are absorbed and tested, delete the legacy files:

- `訪花イベント検出（AI)`
- `訪花イベント検出（モジュール３）`

Before deletion, ensure README or documentation preserves the design history briefly, without keeping duplicate runnable scripts in the top-level repository.

Recommended final cleanup:

1. Move useful logic into `pollipi_api_server.py` or well-named modules.
2. Ensure PWA and API expose the corresponding controls/metrics.
3. Update README.
4. Update `HANDOFF.md`.
5. Delete the two legacy prototype files.

## Current priority remains unchanged

Do not start prototype absorption until iPad preview-based ROI drawing works.

Current immediate task remains:

- Fix visual ROI drawing on preview.

Next after ROI drawing works:

- Absorb low-power ROI-local motion ideas from `訪花イベント検出（モジュール３）`.
