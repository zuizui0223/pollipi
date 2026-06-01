# PolliPi Task Plan

## Needed now

### Task 1: Fix iPad ROI drawing

User must be able to draw ROI on a still preview image from `/preview`.

Acceptance criteria:

- Works on iPad Safari
- Works with mouse on desktop
- Rectangle overlay is visible
- ROI converts to 640 × 360 coordinates
- `roi_x`, `roi_y`, `roi_w`, and `roi_h` fields are auto-filled
- `/start` includes ROI only when valid
- Clear ROI and Use full frame work
- Review events still works

### Task 2: Keep event review stable

The Review events workflow must continue working after ROI changes.

Acceptance criteria:

- `/events` works
- `/events/{event_id}/label` works
- `/events/export_labels.csv` works
- Save label button works in the PWA

### Task 3: Update README

Explain ROI drawing from iPad preview.

## Useful next

### Task 4: Add optional lightweight ROI tracking

Use template matching to keep ROI on the focal flower/head.

Acceptance criteria:

- `roi_tracking=true` works
- tracking score appears in `/status`
- `event_log.csv` records tracked ROI
- fixed ROI mode still works
- full frame mode still works

### Task 5: Add analysis scripts

Create scripts for method validation:

- summarize events
- summarize false positives
- train lightweight insect/non-insect filter
- apply filter to next-day `event_log.csv`

## Future / not now

- YOLO flower detection
- automatic ROI suggestion
- insect species identification
- neural network training
- video recording
- cloud upload
- database migration
- strict multi-camera synchronization
