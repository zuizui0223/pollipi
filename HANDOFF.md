# PolliPi AI Handoff

This file is the relay handoff note between Claude, Codex, and ChatGPT. Each AI must update this file at the end of its work so the next AI knows exactly what changed, what was tested, what failed, and what should happen next.

## Rule

Before starting any task, read:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`
- `HANDOFF.md`

After finishing any task, update `HANDOFF.md`.

Do not assume previous chat context. Use this file as the relay handoff.

## Current project concept

PolliPi is a field-adaptive, human-in-the-loop, event-based timelapse workflow for plant–insect interaction monitoring.

The core data unit is:

```text
flower_id × timestamp × candidate event × camera metadata × manual review label
```

## Current priority

Fix iPad preview-based ROI drawing first.

Then:

1. optional lightweight ROI tracking
2. positive/negative/unclear review workflow
3. simplified field-mode start UI
4. analysis scripts for method validation

## Latest handoff

### Last owner

ChatGPT

### Last completed work

Created shared management files:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`
- `HANDOFF.md`

### Current blocker

ROI drawing on the iPad preview is still not reliably working.

Manual numeric `roi_x`, `roi_y`, `roi_w`, and `roi_h` input is impractical in the field.

### Next recommended task

Implement or fix manual ROI rectangle drawing on a still preview image from `GET /preview`.

### Acceptance criteria

- works on iPad Safari
- works with desktop mouse if possible
- visible rectangle overlay
- coordinates convert to 640 × 360 monitor coordinates
- ROI fields auto-fill
- `/start` includes ROI only when valid
- Clear ROI and Use full frame work
- Review events remains functional
- README is updated

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
