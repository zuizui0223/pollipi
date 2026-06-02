# PolliPi Task Plan

## Needed now

### Task 1: Fix and simplify camera/ROI workflow before field testing

The monitor → angle confirmation → ROI selection → start workflow must be reliable and simple.

Current critical issues:

1. `/mjpeg`, `/preview`, and `/start` must not conflict over Picamera2.
2. After `画角を再調整`, the user must be able to change the ROI.
3. The ROI editor currently appears to snap the rectangle back to the old position after dragging; this must be fixed.
4. User-facing wording should use `ROIを指定` rather than `花を囲む`.
5. The ROI controls are too complicated. Normal field UI should avoid showing too many actions such as `ROIを指定`, `ROIを解除`, `やり直す`, and `キャンセル` all at once.

Required simplified field workflow:

1. `画角を確認`
2. `この画角でOK`
3. `ROIを指定`
4. `このROIで決定`
5. `撮影開始`

Simplification rule:

- Normal screen should show only the minimum controls needed for the current step.
- Do not show `ROIを解除`, `やり直す`, and `キャンセル` together in the main field workflow.
- `ROIを解除` should be hidden in Advanced or shown only after ROI has already been set.
- `やり直す` should be replaced by a simple `リセット` inside the ROI editor if needed.
- `キャンセル` should be inside the ROI editor only, not in the normal main workflow.
- Prefer one primary button per step.

Acceptance criteria:

- `/preview` alone returns JPEG
- `/mjpeg?detect=false` returns MJPEG stream
- `/preview` still returns JPEG after MJPEG has been opened
- `/start` does not trigger `Camera in Running state trying acquire()`
- no `Camera __init__ sequence did not complete` error in normal monitor → ROI → start workflow
- `画角を再調整` marks the old ROI as stale or clears it
- after re-adjusting the angle, the user can draw/move/resize a new ROI
- dragging the ROI does not snap back to the old location
- ROI editor has only three main actions:
  - `このROIで決定`
  - `リセット`
  - `戻る`
- `リセット` resets the editable ROI for the current still preview, not the previous confirmed ROI
- `戻る` leaves the editor without overwriting the confirmed ROI
- `このROIで決定` confirms the currently edited ROI
- normal UI wording uses `ROIを指定`, `このROIで決定`, and `ROIを解除`
- avoid user-facing wording `花を囲む` if it causes confusion

### Task 2: Simplify image/event review into automatic positive/negative/unclear correction workflow

The current review workflow is too confirmation-heavy. The user wants automatic pre-classification first, then manual correction only.

Acceptance criteria:

- images/events are initially grouped as `positive`, `negative`, or `unclear`
- unreviewed images are not shown only as “unclassified” if motion/anomaly information is available
- initial grouping can use simple image-difference / motion metrics first
- user can quickly change a label to positive / negative / unclear
- no “この分類でOK” / “this classification is OK” confirmation is required
- iPad “保存” tab is removed or hidden if it is only for saving/confirming classifications
- label export still works
- corrected labels override automatic labels

### Task 3: Preserve autonomous field operation

Recording must continue after iPad, phone tethering, or Wi-Fi disconnects.

Acceptance criteria:

- `autonomous_mode` persists settings when enabled
- `systemd` keeps API running
- recording loop continues without browser connection
- README clearly states field operation behavior

### Task 4: Clarify recording modes in UI and logs

PolliPi should explicitly support and log the method being compared:

- ordinary timelapse
- motion-triggered recording
- hybrid timelapse + motion-triggered recording
- adaptive timelapse
- ROI-based motion detection
- tracked ROI detection

Acceptance criteria:

- `recording_mode` or `method_mode` is clear in `/start`, `/status`, and logs
- README explains what each mode means
- modes are not conflated with insect classification

## Useful next

### Task 5: Improve low-power ROI-local motion detection

Use low-resolution ROI-local image difference rather than whole-frame or high-power inference when ROI is available.

Acceptance criteria:

- ROI-local motion score is logged
- changed area / largest blob-like metric is logged if available
- consecutive-frame confirmation is used before event creation
- cooldown avoids duplicate event bursts
- no continuous YOLO or video-first workflow is introduced

### Task 6: Add camera-specific profiles and behavior

Make camera roles explicit:

- `zuizui2.local` = AI Camera
- `zuizui3.local` = NoIR Wide
- `zuizui5.local` = Module 3 Wide
- other `zuizui*.local` = Module 3 / Module 3 Wide unless configured otherwise

Acceptance criteria:

- camera profile is visible in UI
- AI Camera is treated as a comparison/detection-test unit, not an insect classifier by default
- NoIR is treated as low-light/night-capable only with illumination notes
- `zuizui5.local` works as a standard daylight Module 3 Wide unit

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
