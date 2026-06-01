# PolliPi AI Changelog

This file is the shared status log for Codex, Claude, and ChatGPT. Read it before making suggestions or code changes.

## 2026-06-01 — Shared management files created

### Current project concept

PolliPi is a field-adaptive, human-in-the-loop, event-based timelapse workflow for plant–insect interaction monitoring.

The core data unit is:

```text
flower_id × timestamp × candidate event × camera metadata × manual review label
```

### Implemented / reportedly deployed

- FastAPI backend
- iPad PWA
- timelapse capture
- autonomous mode
- camera metadata
- `plant_species` and `method_mode`
- `event_log.csv`
- `adaptive_metrics.csv`
- `/events` API
- `/events/{event_id}/label` API
- `/events/export_labels.csv`
- PWA Review events UI
- false-positive reason logging
- reported deployment to:
  - Module 3: `http://zuizui.local:8000/app/`
  - AI Camera: `http://zuizui2.local:8000/app/`

### Current priority

Fix iPad preview-based ROI rectangle drawing.

### Current blocker

The user cannot reliably set ROI by drawing a rectangle on the preview/monitor image. Manual numeric `roi_x`, `roi_y`, `roi_w`, and `roi_h` input is impractical in field conditions.

### Next task

Implement visual ROI drawing on a still preview image from `GET /preview`.

Acceptance criteria:

- works on iPad Safari
- visible rectangle overlay
- coordinates convert to 640 × 360
- ROI fields auto-fill
- `/start` includes ROI only when valid
- Clear ROI and Use full frame work
- event review remains functional

### Do not do now

- YOLO
- automatic flower detection
- ROI tracking
- neural network training
- species identification
- video recording
- database migration
- cloud upload

### AI coordination rule

Before making changes, read:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`

Summarize the current status in a few bullets, then proceed only with the requested task.
