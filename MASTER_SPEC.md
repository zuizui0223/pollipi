# PolliPi Master Specification

## Core concept

PolliPi is a field-adaptive, human-in-the-loop, event-based timelapse workflow for monitoring plant–insect interaction events.

PolliPi is not primarily a fully autonomous insect species classifier. The core scientific unit is a candidate interaction event associated with a focal flower or flower head.

The core data unit is:

```text
flower_id × timestamp × candidate interaction event × camera/device metadata × manual review label
```

## MEE-oriented scientific goal

PolliPi aims to support a possible Methods in Ecology and Evolution-style method paper by enabling:

1. scheduled timelapse recording
2. flower/head ROI-based motion detection
3. optional lightweight ROI tracking
4. candidate event logging
5. same-day human review
6. export of reviewed labels for same-day or next-day lightweight model updating
7. benchmark comparison against direct observation and ordinary timelapse

## Core field workflow

1. User opens PolliPi PWA on iPad.
2. User checks the camera preview.
3. User draws a rectangle around the focal flower/head as ROI.
4. Optional: user enables lightweight ROI tracking.
5. PolliPi records timelapse images.
6. Motion detection runs inside the ROI or tracked ROI.
7. Candidate events are written to `event_log.csv`.
8. User reviews candidate events on iPad.
9. User labels each event as `insect`, `non_insect`, or `unclear`.
10. Reviewed labels are exported as training-ready CSV.

## What we prioritize

- iPad usability in the field
- low power use
- stable operation on Raspberry Pi
- verifiable event logs
- flower-specific candidate events
- simple CSV-based workflow
- method validation
- direct observation comparison
- review time and storage reduction

## What we do not prioritize now

- YOLO
- automatic flower detection
- insect species identification
- neural network training
- continuous video recording
- cloud upload
- database migration
- strict multi-camera synchronization

## Current development priority

Priority 1: Make ROI selection usable from the iPad preview.

Priority 2: Allow optional lightweight ROI tracking using template matching.

Priority 3: Ensure `event_log.csv` and Review events workflow remain stable.

Priority 4: Add analysis scripts for method validation and same-day model preparation.

## ROI policy

The primary ROI workflow is manual drawing on the iPad preview.

Automatic flower detection may be added later only as an optional ROI suggestion feature. Manual confirmation must remain available.

ROI tracking should track the focal flower/head, not insects.

## AI policy

AI should first be used as a lightweight event filter trained from reviewed candidate events.

Do not start with species identification.

The first learning target is insect vs non-insect candidate event classification.

## Decision rule

When choosing between two designs, prefer the option that:

1. works in the field
2. can be operated from iPad
3. preserves `event_log.csv`
4. uses less power
5. is testable this week
6. supports the methods-paper validation workflow

## Instruction for AI assistants

Before making suggestions or code changes, read:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`

Treat these as the source of truth unless the user explicitly overrides them.
