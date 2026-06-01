# AI Change Log

## 2026-06-01

- Simplified the PolliPi PWA start form into a field-first mode.
- Kept essential field inputs visible: `site_id`, `flower_id`, `plant_species`, `method_mode`, interval, `auto_mode`, ROI setup, ROI tracking, start, and stop.
- Moved advanced/debug settings under collapsible sections:
  `observer`, `notes`, `comparison_session_id`, `camera_role`, `pixel_difference`, `motion_ratio`,
  `idle_interval_sec`, `detection_interval_sec`, raw ROI coordinates, `roi_search_margin`, and
  `roi_tracking_min_score`.
- Preserved backend behavior, event review, `/events`, `/events/{event_id}/label`, and label export.
- Did not add YOLO, species identification, video recording, database migration, or cloud upload.
