# AI Change Log

## 2026-06-02

- Added onboarding support for `zuizui5.local` as a standard daylight Camera Module 3 Wide PolliPi unit.
- Updated `deploy_pollipi_pi.ps1` to set `POLLIPI_DEVICE_ID` explicitly, defaulting to the hostname without `.local`.
- Added `DEVICE_ONBOARDING.md` with deployment and verification steps for future Pi/camera additions.
- Documented the expected `zuizui5` profile: `module3_wide_daylight`, `is_ai_camera=false`, `is_noir=false`, `is_wide=true`.

- Simplified the iPad event/image review workflow into automatic Positive / Negative / Unclear grouping plus direct manual correction.
- `/events` now adds derived review fields: `auto_category`, `final_category`, `category_source`, `review_status`, and `final_label`.
- Added `/events?category=positive|negative|unclear|all` filtering while preserving existing label/site/flower/session filters.
- `events/export_labels.csv` now includes automatic category, manual label, final label/category, category source, and review status.
- Replaced the event review confirmation-style flow with tabs and quick correction buttons: `Positive`, `Negative`, and `Unclear`.
- Removed the normal gallery `この分類でOK` confirmation action; users now correct only wrong labels instead of confirming every candidate.
- Kept deep learning, YOLO, species identification, video-first workflow, and database/cloud migration out of this phase.

- Simplified the iPad camera-angle and ROI workflow.
- Added a clear sequence in the PWA: `画角を確認` -> `この画角でOK` -> frozen still frame -> `ROIを指定` -> `このROIで決定`.
- Simplified normal ROI controls so only the current-step buttons are visible. The ROI editor now shows only `このROIで決定`, `リセット`, and `戻る`.
- Fixed the stuck `画角: 確認済み` UI state: confirmed angle now shows `画角を再調整`, confirmed ROI shows `ROIを再指定`, and start is blocked until the angle has been confirmed.
- Split ROI editing state from confirmed recording ROI so re-editing after `画角を再調整` no longer snaps back to the old confirmed ROI.
- The frozen ROI editor now supports redrawing, dragging inside the rectangle to move it, and dragging an edge/corner to resize it.
- Added per-device UI state for angle confirmation, pending ROI, and stale ROI.
- Starting capture is blocked when a previously selected ROI is stale after camera-angle readjustment.
- `画角を再調整` clears or invalidates the old ROI and returns the user to live camera-angle checking.
- Kept backend camera lifecycle behavior, `/mjpeg`, `/preview`, `/start`, ROI drawing, ROI tracking, event review, autonomous mode, and training status intact.

- Fixed a Picamera2 lifecycle conflict between `/preview`, `/mjpeg`, and `/start`.
- Added an in-memory latest-preview JPEG cache. `/mjpeg` now updates the cache, and `/preview` returns the cached frame when a monitor stream is active or has just run.
- Wrapped standalone preview capture and timelapse camera initialization with the shared camera lock.
- `/start` continues to stop the MJPEG monitor before starting the capture loop, with a longer cleanup wait.
- `/preview` now returns a JSON 503 error on capture failure instead of falling through to a plain internal server error.
- Verified on `zuizui.local`: preview alone returns JPEG, MJPEG followed by preview returns JPEG, MJPEG during `/start` starts timelapse without camera acquire/init conflict logs.
- Deployed the fix to `zuizui.local`, `zuizui2.local`, `zuizui3.local`, and `zuizui4.local`.

## 2026-06-01

- Enabled optional lightweight flower/head ROI tracking from the iPad PWA.
- Reconnected the existing backend template-matching tracker to the UI: draw a fixed ROI first, turn `ROI追跡` ON, then start recording.
- Tracking targets the selected flower/head, not insects; the backend keeps the first low-resolution ROI patch as a fixed template and searches near the previous ROI.
- Tracking failures keep the previous ROI, and metrics remain available as `roi_tracking_score`, `roi_tracking_success`, `roi_shift_x`, and `roi_shift_y`.
- Kept YOLO, species identification, neural network training, video recording, and database/cloud migration out of this phase.

- Simplified the PolliPi PWA start form into a field-first mode.
- Kept essential field inputs visible: `site_id`, `flower_id`, `plant_species`, `method_mode`, interval, `auto_mode`, ROI setup, ROI tracking, start, and stop.
- Moved advanced/debug settings under collapsible sections:
  `observer`, `notes`, `comparison_session_id`, `camera_role`, `pixel_difference`, `motion_ratio`,
  `idle_interval_sec`, `detection_interval_sec`, raw ROI coordinates, `roi_search_margin`, and
  `roi_tracking_min_score`.
- Preserved backend behavior, event review, `/events`, `/events/{event_id}/label`, and label export.
- Did not add YOLO, species identification, video recording, database migration, or cloud upload.
