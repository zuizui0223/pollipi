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

Fix iPad preview-based ROI drawing first.

Then:

1. preserve autonomous field operation after Wi-Fi/tethering disconnects
2. clarify recording modes in UI/logs
3. optional lightweight ROI tracking
4. positive/negative/unclear correction-based review workflow
5. camera-specific profiles for Module 3, AI Camera, and NoIR Wide
6. analysis scripts for method validation

## Latest handoff

### Last owner

ChatGPT

### Last completed work

Refocused the project management documents around the user's clarified goal: staged comparison of field recording methods rather than novelty-first automation.

Updated:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`
- `HANDOFF.md`

Added:

- `FIELD_METHOD_ROADMAP.md`

### Current blocker

ROI drawing on the iPad preview is still not reliably working.

The user can see the monitor angle, but cannot draw a rectangle directly on that camera view to select the flower/head as ROI. Manual numeric `roi_x`, `roi_y`, `roi_w`, and `roi_h` input is not acceptable in field conditions.

### Next recommended task

Implement or fix manual ROI rectangle drawing on a still preview image from `GET /preview`.

This task should be completed before ROI tracking, learning, or UI refinements.

### Acceptance criteria

- works on iPad Safari
- works with desktop mouse if possible
- visible rectangle overlay on the preview image
- overlay is aligned with the image
- coordinates convert to 640 × 360 monitor coordinates
- ROI fields auto-fill
- `/start` includes ROI only when valid
- Clear ROI and Use full frame work
- Review events remains functional
- README and `HANDOFF.md` are updated

### Do not do next

- YOLO
- automatic flower detection
- species identification
- neural network training
- video recording
- cloud upload
- database migration

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
