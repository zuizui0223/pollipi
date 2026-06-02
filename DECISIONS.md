# PolliPi Design Decisions

## Decision 1: First goal is recording-method comparison

PolliPi is first a field system for comparing recording methods:

- ordinary timelapse
- motion-triggered recording
- hybrid timelapse + motion-triggered recording
- adaptive timelapse
- flower/head ROI-based motion detection
- tracked flower/head ROI detection
- later lightweight machine-learning filtering

Reason: The user wants to compare practical field recording methods before emphasizing novelty claims.

## Decision 2: PolliPi is not primarily a fully autonomous insect classifier

PolliPi should eventually support machine learning, but the first goal is robust field recording, event logging, review, and method comparison.

Reason: For ecological use and possible methods-paper validation, verifiable recording modes and labels are more important than immediate species-level automation.

## Decision 3: Autonomous field operation is non-negotiable

Once started, the program must keep running even if iPad, phone tethering, or Wi-Fi disconnects.

Reason: In the field, the user may set up the system and then walk away. Recording must continue on the Raspberry Pi alone.

## Decision 4: The primary ROI workflow is manual drawing on iPad preview

The user should draw a rectangle around the focal flower/head directly on the camera preview image.

Reason: Typing `roi_x`, `roi_y`, `roi_w`, and `roi_h` is impractical in field conditions. The user can see the monitor angle but currently cannot select the subject directly on that view. This must be fixed.

Rejected for now: Fully automatic YOLO-based flower ROI detection.

Future: Add optional AI-suggested ROI only after manual ROI drawing is stable.

## Decision 5: ROI defines the biological subject

ROI should focus on the focal flower/head. Motion outside the ROI is background. The goal is to detect events occurring on or around the selected subject, not generic background motion.

Reason: Wind-driven leaves, shadows, and background movement produce false positives in whole-frame motion detection.

## Decision 6: ROI tracking should follow the flower/head, not the insect

If enabled, tracking should use lightweight template matching to keep the ROI on the focal flower/head as it moves in wind.

Reason: Tracking insects would move the ROI away from the biological subject. Constant YOLO inference is too heavy for the current field-power target.

## Decision 7: Image/event review should be correction-based

Images or events can be automatically pre-classified as positive, negative, or unclear. The user should correct wrong labels. The UI should not repeatedly ask “this classification is OK”.

Reason: Field review should be fast. The user wants automatic sorting first and manual correction afterward.

## Decision 8: Same-day/next-day learning starts with lightweight models

When power/Wi-Fi is available, accumulated positive/negative labels can be used to train or update a lightweight model. The trained model can then be used during the next recording session.

Preferred first models:

- motion/anomaly feature rules
- logistic regression
- random forest
- lightweight image features

Rejected for now: deep neural network training on the Pi as the first method.

## Decision 9: Camera roles are fixed by hostname

- `zuizui2.local` = Raspberry Pi AI Camera
- `zuizui3.local` = Camera Module 3 NoIR Wide / infrared-capable unit
- `zuizui5.local` = Camera Module 3 Wide / standard daylight unit
- other `zuizui*.local` units = ordinary Camera Module 3 / Module 3 Wide unless specified otherwise

These roles should be reflected in camera profiles, README, and comparison logic.

## Decision 10: Camera-specific behavior should be explicit

- Module 3 / Module 3 Wide is the primary daylight recording unit.
- AI Camera can be used for simple detection experiments, but the default IMX500 model is not an insect classifier.
- NoIR Wide can enable low-light or night trials only with appropriate IR illumination, and such data must be treated as a distinct condition.
- `zuizui5.local` should use the same Module 3 Wide daylight behavior as other standard daylight units.

## Decision 11: Event log and labels are core outputs

`event_log.csv`, image labels, and exported label CSVs are the central data products for method validation and later learning.

They should contain:

- recording mode
- device and camera metadata
- `site_id`
- `flower_id`
- `plant_species`
- ROI information
- motion metrics
- automatic label/category
- corrected label/category
- false positive reason when available

## Decision 12: GitHub is the shared project memory

Codex, Claude, and ChatGPT should use the files below as shared context:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`
- `HANDOFF.md`
- `FIELD_METHOD_ROADMAP.md`

Do not rely on memory from a previous chat when these files disagree.
