# PolliPi AI Handoff

This file is the relay handoff note between Claude, Codex, and ChatGPT.
Read this file before starting any task. Update it when you finish.
Do not assume previous chat context.

## Source of truth files

Before starting, read:
- MASTER_SPEC.md
- DECISIONS.md
- TASKS.md
- CHANGELOG_AI.md
- HANDOFF.md
- FIELD_METHOD_ROADMAP.md

## Project concept

PolliPi is a field-adaptive, human-in-the-loop, event-based timelapse workflow
for comparing plant-insect interaction recording methods (7 modes, from standard
timelapse to tracked ROI detection). Goal is MEE-oriented method validation.

Core data unit:
  flower_id x timestamp x recording_mode x candidate event x camera metadata x ROI metadata x label

## Current deployment state (roi-track1, 2026-06-01)

All 4 Pis have been updated:
- zuizui.local  (Module 3 Wide)
- zuizui2.local (AI Camera / IMX500)
- zuizui3.local (NoIR Wide)
- zuizui4.local (Module 3 Wide)

### What roi-track1 changed

Optional lightweight flower/head ROI tracking is now usable from the iPad PWA.

Workflow:
  1. Use "ROIを指定" to draw a fixed ROI on the still /preview image.
  2. Turn "ROI追跡" ON.
  3. Start recording.
  4. /start includes roi_x/y/w/h plus roi_tracking=true, roi_search_margin, and roi_tracking_min_score.

Backend tracking behavior:
  - Target is the selected flower/head, not insects.
  - First low-resolution ROI luminance patch is stored as a fixed template.
  - During recording, template matching searches near the previous ROI.
  - If score >= roi_tracking_min_score, the ROI moves with the flower/head.
  - If tracking fails, the previous ROI is kept.
  - Template is not updated during recording, so insects should not pull the ROI away.
  - Logged/status metrics: roi_tracking_score, roi_tracking_success, roi_shift_x, roi_shift_y.

### ROI drawing system (structure is correct, was only a visibility bug)

These functions exist and are structurally correct in current app.js:
  openRoiPreview(camera)        -- fetches /preview, shows roi-drawer
  setupRoiDrawing(camera)       -- attaches pointer/touch/mouse listeners to roi-wrap
  setupRoiDrawingTarget(...)    -- event handler (begin/move/end)
  pointInImage(event, image)    -- coordinates relative to image rect
  displayRectToRoi(start, end)  -- converts display px to 640x360 monitor coords
  drawRoiBoxFromPoints(box,s,e) -- draws yellow overlay (FIXED)
  renderRoiBoxOnImage(...)      -- shows stored ROI on image (FIXED)
  setCameraRoi(camera, roi)     -- stores ROI, fills inputs, updates display
  clearCameraRoi(camera)        -- clears ROI
  useFullFrame(camera)          -- clears ROI + unchecks tracking
  renderCameraRoi(camera)       -- full ROI state refresh (FIXED)

Touch/pointer handling:
  - touch-action: none on .roi-preview-wrap (CSS) prevents scroll during draw
  - PointerEvents + touch fallback both implemented
  - setPointerCapture used for drag-outside-element support
  - MIN_ROI_SIZE = 8px minimum drawn rectangle size

### Files changed in roi-track1

- web/index.html
- web/app.js
- web/app.css
- README.md
- CHANGELOG_AI.md
- HANDOFF.md

### Checks run

- python -m py_compile pollipi_api_server.py imx500_detect_test.py: passed
- node --check web/app.js using bundled Codex Node: passed
- Import/minimal FastAPI route checks on local PC: not run because local Python lacks FastAPI.
- Deployed to all 4 Pis with deploy_pollipi_pi.ps1.
- Verified /status, /device, /events?limit=1, and /app/ respond on all 4 Pis.
- Verified zuizui.local serves app.js/app.css version v=20260601-roi-track1.

## Next recommended task

### Step 1 (required): iPad field test

Physically test ROI drawing and ROI tracking on iPad Safari with zuizui.local.

Acceptance tests:
  1. Open http://zuizui.local:8000/app/ in Safari
  2. Register camera: zuizui.local or zuizui0223@zuizui
  3. Tap "ROIを指定" on camera card
  4. Verify "Preview loading..." message appears immediately
  5. Verify camera still image loads (16:9 format)
  6. Drag finger to draw a rectangle over the focal flower
  7. Verify yellow rectangle appears DURING drag
  8. Release finger
  9. Verify ROI status shows "ROI: x=... y=... w=... h=..."
  10. Turn ROI追跡 ON
  11. Tap Start -> confirm /start payload includes roi_x, roi_y, roi_w, roi_h, roi_tracking=true
      (check Safari DevTools > Network, or look at Pi server logs)
  12. Confirm status shows ROI tracking score/success/shift while running
  13. Tap "ROIを解除" -> status shows full-frame ROI and start omits ROI fields
  14. Verify event review section still works

### Step 2 (after iPad confirms working): Push to GitHub

GitHub may still be out of sync if this workspace has no git remote/token.
Push these files when a safe route is available:
  web/index.html
  web/app.js
  web/app.css
  README.md
  CHANGELOG_AI.md
  HANDOFF.md

### Step 3 (next feature): Choose from TASKS.md

After ROI drawing is confirmed:
  - Task 2: Verify autonomous mode (systemd) works on all 4 Pis
  - Task 5: Grouped event review workflow (not per-item confirmation buttons)

## Do not do

- YOLO or automatic flower detection
- Species identification
- Neural network training
- Video recording
- Cloud upload
- Database migration
- Rewriting the drawing system (structure is correct)

## Known issues

1. GitHub out of sync with Pi. Push required.
2. /preview endpoint requires camera not locked by another process.
   If timelapse is running, preview still works (uses timelapse camera).
   If another process holds the camera, preview fails (onerror message shown).
3. ROI tracking is implemented and deployed, but still needs a physical windy-flower field test.

## Last updated

2026-06-01 by Codex
Task: Optional lightweight flower/head ROI tracking enabled and deployed to all 4 Pis.
