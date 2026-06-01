# PolliPi Task Plan

## Needed now

### Task 1: Fix iPad preview-based ROI drawing

The user must be able to draw a ROI directly on a still camera preview image from `/preview`.

Acceptance criteria:

- Works on iPad Safari
- Works with mouse on desktop if possible
- Rectangle overlay is visible and aligned with the preview image
- ROI converts to 640 × 360 monitor coordinates
- `roi_x`, `roi_y`, `roi_w`, and `roi_h` fields are auto-filled
- `/start` includes ROI only when valid
- Clear ROI and Use full frame work
- Review events still works

### Task 2: Preserve autonomous field operation

Recording must continue after iPad, phone tethering, or Wi-Fi disconnects.

Acceptance criteria:

- `autonomous_mode` persists settings when enabled
- `systemd` keeps API running
- recording loop continues without browser connection
- README clearly states field operation behavior

### Task 3: Clarify recording modes in UI and logs

PolliPi should explicitly support and log the method being compared:

- ordinary timelapse
- motion-triggered recording
- hybrid timelapse + motion-triggered recording
- adaptive timelapse
- ROI-based motion detection
- tracked ROI detection later

Acceptance criteria:

- `recording_mode` or `method_mode` is clear in `/start`, `/status`, and logs
- README explains what each mode means
- modes are not conflated with insect classification

## Useful next

### Task 4: Add optional lightweight flower/head ROI tracking

Use template matching to keep ROI on the focal flower/head when it moves slightly in wind.

Acceptance criteria:

- `roi_tracking=true` works
- tracking score appears in `/status`
- `event_log.csv` records tracked ROI
- fixed ROI mode still works
- full frame mode still works
- tracking follows flower/head, not insects

### Task 5: Improve image/event review into positive/negative/unclear correction workflow

The system may automatically pre-sort images or candidate events, but the user should only correct wrong labels. Remove repeated “this classification is OK” style workflow from normal use.

Acceptance criteria:

- positive / negative / unclear categories are visible
- user can quickly mark positive, negative, or unclear
- false positive reason can be selected for negative events
- label export still works
- no unnecessary confirmation step is required

### Task 6: Camera-specific profiles and behavior

Make camera roles explicit:

- `zuizui2.local` = AI Camera
- `zuizui3.local` = NoIR Wide
- other `zuizui*.local` = Module 3 / Module 3 Wide unless configured otherwise

Acceptance criteria:

- camera profile is visible in UI
- AI Camera is treated as a comparison/detection-test unit, not an insect classifier by default
- NoIR is treated as low-light/night-capable only with illumination notes

### Task 7: Add analysis scripts for method validation

Create scripts for method comparison:

- summarize recording modes
- summarize motion candidates
- summarize false positives
- compare timelapse vs motion-triggered vs hybrid vs ROI modes
- train lightweight positive/negative event filter later
- apply filter to next-day data later

## Future / not now

- YOLO flower detection
- automatic ROI suggestion
- insect species identification
- continuous video recording
- cloud upload
- database migration
- strict multi-camera synchronization
- full neural network training on Pi
