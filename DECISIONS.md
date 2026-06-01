# PolliPi Design Decisions

## Decision 1: PolliPi is not a fully autonomous insect classifier

PolliPi is a field-adaptive, human-in-the-loop monitoring workflow.

Reason: For ecological and methods-paper validation, verifiable candidate interaction events are more important than immediate species-level automation.

## Decision 2: The primary ROI workflow is manual drawing on iPad preview

The user should draw a rectangle around the focal flower/head on the preview image.

Reason: Typing `roi_x`, `roi_y`, `roi_w`, and `roi_h` is impractical in field conditions. Manual ROI drawing is robust, low-power, and does not require a trained flower detector.

Rejected for now: Fully automatic YOLO-based flower ROI detection.

Future: Add optional AI-suggested ROI only after manual ROI drawing is stable.

## Decision 3: ROI tracking should be lightweight and optional

Tracking should use simple template matching on low-resolution frames.

Reason: Flowers move in wind, so fixed ROI can fail. However, constant YOLO inference is too heavy for field battery operation.

Rejected for now: YOLO every frame.

## Decision 4: Track the flower, not the insect

The tracking target is the focal flower/head ROI.

Reason: If the tracker follows insects, the ROI will drift away from the focal flower. The biological unit is flower-specific interaction, not free insect movement.

## Decision 5: Event log is the core data product

`event_log.csv` is the central output for method validation.

It should contain:

- device metadata
- camera metadata
- `site_id`
- `flower_id`
- `plant_species`
- ROI information
- motion metrics
- manual review labels
- false positive reason

## Decision 6: Same-day learning starts with lightweight models

Use reviewed events to train insect vs non-insect event filters.

Preferred first models:

- logistic regression
- random forest

Rejected for now: deep neural network training on Pi.

## Decision 7: Method paper first, full automation later

For a possible Methods in Ecology and Evolution-style paper, the priority is to show:

- detection performance
- false positive reasons
- review time reduction
- storage reduction
- field usability
- ability to generate same-day labelled data

## Decision 8: GitHub is the shared project memory

Codex, Claude, and ChatGPT should use the files below as shared context:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`

Do not rely on memory from a previous chat when these files disagree.
