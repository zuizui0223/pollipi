# Legacy ROI / ML / Event Path — Removal & Compatibility Plan

Issue #15 requires moving legacy active functionality **out of the main path**
(not merely hiding it in the UI), after auditing dependencies and classifying
each surface as **retain / replace / compat / delete**.

This document is the classification and the staged plan. The pure analysis
replacement (`packages/analysis`, three-state mesh + shadow mode) already exists
and is tested; the server/web deletions below are **staged, not yet executed**,
because they must be validated against a runnable FastAPI server and the Preact
web build before the active main path can be cut over safely.

## Scope of legacy functionality to remove from the active path

manual one-flower ROI · ROI tracking · ML assist · model training/export/import ·
candidate-event collection and review · event/training polling · user-facing
blob/pixel threshold tuning.

## Server (`packages/server/src/visit_monitor_server`)

| Path | Class | Action |
|---|---|---|
| `api/routes/capture.py` (`/start` `/stop` `/status`) | retain | active control/status boundary |
| `api/routes/device.py`, `api/routes/preview.py` | retain | device list + explicit single-device monitor |
| `api/routes/images.py` | replace | keep scheduled-timelapse gallery; drop candidate-image listing |
| `api/routes/roi.py` + `api/schemas/roi.py` | delete | remove ROI entry/tracking endpoints from `router.py` |
| `api/routes/training.py` + `api/schemas/training.py` | delete | remove model train/export/import endpoints |
| `api/routes/events.py` | delete | remove candidate-event review queue endpoints |
| `services/roi_tracking.py` | delete | no ROI in the active design |
| `services/training.py` | delete | no ML training in the active design |
| `services/event_log.py` | replace | replace candidate-event log with compact shadow metadata log |
| `services/motion.py` | replace | thin adapter over `pollipi_analysis.pipeline` (three-state) |
| `services/capture_loop.py` | replace | remove ML-confidence coupling and `adaptive_*.jpg` per-candidate image saving; add shadow-mode metadata logging only |
| `services/mesh_motion.py` | compat | already a thin wrapper over `pollipi_analysis.mesh`; keep until callers move to the three-state API |
| `services/mesh_simulator.py` | compat → delete | superseded by `pollipi_analysis.simulation`; keep only until `test_issue14` is repointed |
| `api/schemas/capture.py` | replace | shrink to status-only + shadow fields; drop ROI/ML/candidate fields |
| `config.py` | replace | drop ROI/ML/training config; keep capture + mesh/shadow fields |

### Key coupling to cut in `capture_loop.py`

`services/capture_loop.py` currently maps `mesh_decision` into ML confidence
scoring and saves a full-resolution `adaptive_*.jpg` per candidate. Both violate
the active design:

- remove `_label_captured_image` / `ml_assist_mode` / `MODEL_PATH` usage;
- remove `insect_candidate`-based `visit_likeness` / `noise_likeness`;
- remove per-candidate image writes (no image-per-motion-event storage);
- replace the adaptive branch with shadow-mode logging via
  `pollipi_analysis.shadow` (no timing change until live adaptation is approved).

## Web (`packages/web/src`)

| Path | Class | Action |
|---|---|---|
| `components/DeviceCard.tsx`, `DeviceForm.tsx`, `DeviceGrid.tsx`, `CoordinatorPanel.tsx` | retain | status-first device console |
| `components/RoiEditor.tsx` + `lib/roi.ts` | delete | no spatial ROI selection UI |
| `components/TrainingPanel.tsx` | delete | no ML training UI |
| `components/EventReview.tsx` | delete | no candidate-event review queue |
| `components/Gallery.tsx` | replace | scheduled-timelapse gallery only |
| `components/FieldControls.tsx` | replace | baseline/min/max + shadow toggle only; remove blob/pixel threshold tuning |
| `api/types.ts`, `api/client.ts` | replace | shrink contracts to status + shadow once server routes are removed |
| `state/*` | replace | drop event/training polling; single-flight status polling only (Issue #13) |

## Removal sequence (each step independently testable)

1. **Repoint tests** off `visit_monitor_server.services.mesh_simulator` onto
   `pollipi_analysis.simulation`; have `services/motion.py` call
   `pollipi_analysis.pipeline.analyze`.
2. **Server routes:** unregister `roi`, `training`, `events` from `router.py`;
   delete the route + schema modules; run server tests.
3. **capture_loop:** strip ML coupling and per-candidate image writes; wire
   shadow-mode logging; run lifecycle tests (Issue #13).
4. **Web:** delete `RoiEditor`, `TrainingPanel`, `EventReview` and their nav
   entries; trim `FieldControls`; shrink `api/types.ts`.
5. **Contracts:** shrink `api/schemas/capture.py` and `packages/contracts` to the
   minimal status + shadow surface; regenerate the `dist/` artifact.

## Compatibility kept on purpose

- Root `pollipi_api_server.py` and root `web/` remain as documented legacy until
  all five Pi devices run the packaged artifact (see `REPO_CLEANUP_AUDIT.md`).
- `services/mesh_motion.py` stays as a compat wrapper so the cutover is incremental.

## Validation required before executing steps 2–5

A runnable FastAPI server (`fastapi`, `uvicorn`, `httpx`) and the pnpm/Vite web
build must be available so each deletion is verified green. The pure
`packages/analysis` replacement is already validated here without that
environment.
