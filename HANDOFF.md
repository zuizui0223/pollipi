# PolliPi AI Handoff

This file is the relay handoff note between Claude, Codex, and ChatGPT. Each AI must update this file at the end of its work so the next AI knows exactly what changed, what was tested, what failed, and what should happen next.

## Rule

Before starting any task, read:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`
- `HANDOFF.md`
- `FIELD_METHOD_ROADMAP.md`
- `LOW_POWER_DESIGN_ABSORPTION.md`

After finishing any task, update `HANDOFF.md`.

Do not assume previous chat context. Use this file as the relay handoff.

## Current project concept

PolliPi is a field system for comparing recording methods for plant–insect interaction monitoring.

The user wants to compare:

1. user-scheduled ordinary timelapse
2. motion-triggered recording
3. hybrid timelapse + motion-triggered recording
4. adaptive timelapse
5. flower/head ROI-based motion detection
6. tracked flower/head ROI detection
7. later positive/negative learning-assisted filtering

The core data unit is:

```text
flower_id × timestamp × recording_mode × candidate event × camera metadata × ROI metadata × label
```

## Current priority

The user reports that Codex has implemented and deployed ROI tracking to four Raspberry Pi units, but the code was not pushed to GitHub.

The immediate priority is now:

1. Sync the deployed code back to GitHub.
2. Verify the actual deployed files match the reported behavior.
3. Run an iPad field usability test for ROI drawing and ROI tracking.
4. Only after GitHub is synced, proceed to low-power ROI-local motion detection improvements.

## Latest handoff

### Last owner

ChatGPT, based on Codex's reported final message from the user.

### Last reported Codex work

Codex reported that ROI tracking was implemented and deployed to four devices:

- `zuizui`
- `zuizui2`
- `zuizui3`
- `zuizui4`

Reported behavior:

- `/start` includes `roi_x`, `roi_y`, `roi_w`, `roi_h` when ROI is set.
- `/start` includes `roi_tracking=true`, `roi_search_margin`, and `roi_tracking_min_score` when tracking is enabled.
- On successful tracking, ROI moves with flower/head movement.
- On tracking failure, the previous ROI is retained.
- The tracking template is not updated during recording, so insects are less likely to pull the ROI away from the flower/head.
- Logs/status include existing schema fields:
  - `roi_tracking_score`
  - `roi_tracking_success`
  - `roi_shift_x`
  - `roi_shift_y`
- PWA version reported as `v=20260601-roi-track1`.

Reported checks:

- `python -m py_compile pollipi_api_server.py imx500_detect_test.py` OK.
- `web/app.js` syntax check OK.
- Deployed to four units: `zuizui`, `zuizui2`, `zuizui3`, `zuizui4`.
- All four units responded to:
  - `/status`
  - `/device`
  - `/events?limit=1`
  - `/app/`

### Important limitation

GitHub was not updated by Codex. Therefore, the repository may not contain the deployed ROI tracking code.

Do not assume GitHub matches the deployed Pi state until code is pushed or synced back.

### Not tested

- Real iPad field test under wind-driven flower movement.
- Actual ROI tracking performance on moving flowers.
- Local PC FastAPI import test, because FastAPI is unavailable on the local PC.

### Current blocker

The deployed code and GitHub repository are out of sync.

### Next recommended task

Sync the deployed Pi code back to GitHub before any new feature work.

The next implementation task should be one of:

1. From the Pi, commit and push the deployed files to GitHub; or
2. From Codex, generate a patch containing the deployed changes and push it to GitHub.

### After sync, next recommended task

Perform iPad field usability testing:

- Can the user easily set ROI on the iPad?
- Is ROI drawing usable enough in the field?
- Does ROI tracking behave under wind?
- Are tracking score/success/shift visible and logged?

### Do not do next

- Do not start low-power prototype absorption until GitHub contains the deployed ROI tracking code.
- Do not delete legacy prototype files yet.
- Do not implement YOLO.
- Do not implement species identification.
- Do not implement video-first workflow.
- Do not implement database/cloud migration.

## Handoff update template

Copy and update this section at the end of each AI task:

```md
## Handoff YYYY-MM-DD HH:MM JST

### Owner
Codex / Claude / ChatGPT

### Task
Short task description

### Files changed
- file1
- file2

### What changed
- item
- item

### Tests run
- item
- item

### Not tested
- item
- item

### Known issues
- item
- item

### Next recommended task
One task only.

### Do not do next
- YOLO
- species identification
- video recording
- database migration
```
