# PolliPi Active System Audit

Issue #15 active definition: autonomous scheduled timelapse, lightweight mesh
analysis, compact metadata logging, status-first iPad control, and no active ML,
manual ROI, candidate-event, or training workflow.

## Retain

- `packages/server/src/visit_monitor_server/api/routes/capture.py`: `/start`,
  `/stop`, `/status` remain the active control/status boundary.
- `packages/server/src/visit_monitor_server/api/routes/device.py`: `/device`
  and `/system` remain available; device-list polling should use `/status` only.
- `packages/server/src/visit_monitor_server/api/routes/preview.py`: `/latest`,
  `/preview`, `/mjpeg` remain for latest image and explicit one-device monitor
  use. MJPEG must not auto-open from the device list.
- `packages/server/src/visit_monitor_server/services/controller.py`: retained
  for lifecycle, bounded stop, diagnostics, and autonomous resume.
- `packages/server/src/visit_monitor_server/services/capture_loop.py`: retained
  as the current runtime loop, now active only for scheduled mesh shadow/adaptive
  operation unless legacy routes are enabled.
- `packages/web/src/app.tsx`: retained as the active status-first console.
- `packages/web/src/components/DeviceGrid.tsx`,
  `packages/web/src/components/DeviceCard.tsx`, `packages/web/src/components/DeviceForm.tsx`:
  retained as active device operation surfaces.
- `packages/analysis`: retained as the pure laptop/Pi-shared analysis package.

## Replace

- `visit_monitor_server.services.motion`: replace old blob/ROI-centered motion
  semantics with a thin adapter around `pollipi_analysis.mesh` and eventual
  runtime integration modules.
- `visit_monitor_server.services.capture_loop`: replace large mode branches with
  a smaller runtime package split: camera producer, scheduler, metadata storage,
  and analysis integration.
- `packages/web/src/components/FieldControls.tsx`: replaced with active
  baseline/min/max/adaptive/autonomous controls.
- `packages/web/src/api/types.ts`: replace wide legacy status/control contracts
  with minimal contracts after the five Pi artifact versions are unified.

## Compat

- `packages/server/src/visit_monitor_server/api/routes/events.py`: compatibility
  route only, mounted under `/compat` when `POLLIPI_ENABLE_LEGACY_ROUTES=1`.
- `packages/server/src/visit_monitor_server/api/routes/training.py`: compatibility
  route only, mounted under `/compat` when legacy routes are enabled.
- `packages/server/src/visit_monitor_server/api/routes/roi.py`: compatibility
  route only, mounted under `/compat` when legacy routes are enabled.
- `packages/web/src/components/Gallery.tsx`, `EventReview.tsx`,
  `TrainingPanel.tsx`, `RoiEditor.tsx`: retained in source for compatibility and
  history, removed from active navigation.
- Root `pollipi_api_server.py`, root `web/`, `dist/`, and `legacy/`: keep until
  Issue #11 finishes artifact unification across all five Pi devices.

## Delete Later

- Manual one-flower ROI fields and tracking fields in `StartRequest` and
  `StatusResponse` after all five Pi artifacts no longer need them.
- `services/training.py`, model export/import state, and training UI/state after
  confirming no deployed Pi still calls them.
- Candidate event review schemas and tests after compatibility routes have been
  unused for one field cycle.
- Old auto/motion-trigger/hybrid branches in `capture_loop.py` after
  `POLLIPI_ENABLE_LEGACY_ROUTES` is removed.

## Active Route Set

Default active route set:

- `/device`
- `/system`
- `/status`
- `/start`
- `/stop`
- `/latest`
- `/preview`
- `/mjpeg`
- image management routes for explicit operator maintenance

Compatibility route set, only when `POLLIPI_ENABLE_LEGACY_ROUTES=1`:

- `/compat/events`
- `/compat/events/*`
- `/compat/training/*`
- `/compat/roi/suggest`

## Active Runtime Decisions

- `mesh_shadow_mode=true`: log mesh metadata and keep scheduled interval.
- `adaptive_timelapse_mode=true`: use shared `pollipi_analysis.policy` to choose
  the next scheduled interval.
- No active mode writes candidate-event logs or persists event-only images.
- No active mode uses ML prediction or model training.
- Manual ROI and ROI tracking are rejected from `/start` unless legacy mode is
  explicitly enabled.
