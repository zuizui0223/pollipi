# AI Change Log

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
