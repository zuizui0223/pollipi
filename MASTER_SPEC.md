# PolliPi Master Specification

## Core concept

PolliPi is a field camera workflow for comparing plant–insect interaction recording methods under real field conditions.

The first goal is not novelty for its own sake and not a fully autonomous insect classifier. The first goal is to make a robust field system that can compare recording modes:

1. user-scheduled ordinary timelapse
2. motion-triggered recording
3. hybrid timelapse + motion-triggered recording
4. adaptive timelapse where recording effort can change with detected activity
5. flower/head ROI-based motion detection
6. optional ROI tracking around the focal flower/head
7. later lightweight machine-learning filtering using field-collected labels

The core biological unit is a candidate event at a focal flower/head, not generic motion anywhere in the image.

The core data unit is:

```text
flower_id × timestamp × recording_mode × candidate event × camera/device metadata × ROI metadata × manual/automatic label
```

## Primary scientific workflow

PolliPi should allow the user to compare the following methods:

### Basic recording methods

1. **Ordinary timelapse**  
   User specifies interval, e.g. every 5 s, 10 s, 30 s, or 60 s. PolliPi records at that interval regardless of motion.

2. **Motion-triggered recording**  
   PolliPi checks low-resolution frames and saves images when image-difference/motion criteria are met.

3. **Hybrid timelapse + motion-triggered recording**  
   PolliPi always saves scheduled timelapse images, and additionally saves event images when motion is detected between scheduled frames.

### Intermediate recording methods

4. **Adaptive timelapse**  
   PolliPi changes recording interval based on recent activity, e.g. shorter interval when candidate activity is frequent and longer interval when quiet.

5. **Flower/head ROI-based motion detection**  
   The user draws a ROI around the focal flower/head on the iPad preview. Motion detection runs inside that ROI, not across the full background.

6. **Tracked flower/head ROI**  
   The user selects the flower/head ROI, and PolliPi keeps that ROI on the focal flower/head when it moves slightly in wind. Motion inside that tracked ROI becomes the candidate event.

### Later machine-learning workflow

7. **Automatic positive/negative pre-classification**  
   Field images/events are automatically sorted into positive, negative, and unclear groups using motion/anomaly features or a lightweight model.

8. **Human correction, not confirmation**  
   The user should only correct wrong labels. The UI should not force repeated “this classification is OK” confirmation.

9. **Same-day or next-day learning**  
   When power/Wi-Fi returns, reviewed labels can be used to train or update a lightweight model. The trained model can be used in the next recording session.

## Core field workflow

1. User powers on the Pi in the field.
2. PolliPi starts as a `systemd` service.
3. User connects by iPad only when needed.
4. User chooses recording mode: timelapse, motion-triggered, hybrid, adaptive, or ROI-based.
5. If ROI mode is used, user draws a rectangle around the focal flower/head directly on the camera preview.
6. User starts recording with autonomous operation.
7. The program continues even if the iPad or phone tethering/Wi-Fi disconnects.
8. PolliPi saves images, event logs, motion metrics, and labels.
9. User later reviews positive/negative/unclear groups and corrects wrong classifications.
10. When power/Wi-Fi is available, labels can be used for model training or updating.

## Camera roles

- `zuizui2.local` is the Raspberry Pi AI Camera unit.
- `zuizui3.local` is the Camera Module 3 NoIR Wide / infrared-capable unit.
- Other `zuizui*.local` units are ordinary Camera Module 3 / Module 3 Wide units unless specified otherwise.

### Camera Module 3 / Module 3 Wide

Primary daylight field unit. Use for ordinary timelapse, motion-triggered, hybrid, adaptive, and ROI-based daytime recording.

### AI Camera (`zuizui2.local`)

Use as a comparison unit and for testing lightweight on-device detection possibilities. The default IMX500 model is not an insect classifier. AI Camera results should not be treated as insect species identification unless a dedicated model is trained and validated.

### NoIR Wide (`zuizui3.local`)

Use for low-light or night-capable trials with appropriate IR illumination notes. NoIR/IR data should be treated as a separate camera/illumination condition and not directly mixed with daylight RGB without recording illumination details.

## What we prioritize now

1. Field recording modes that can be compared.
2. iPad usability.
3. Autonomous operation after Wi-Fi/tethering disconnects.
4. Visual ROI drawing on the camera preview.
5. Flower/head ROI tracking after ROI drawing works.
6. Positive/negative/unclear review with easy correction.
7. Label export and later lightweight model updating.

## What we do not prioritize now

- full insect species identification
- YOLO as the first ROI solution
- continuous video recording
- cloud upload
- database migration
- strict multi-camera synchronization
- full neural network training on the Pi as the first learning method

## ROI policy

ROI is not just a UI detail. ROI defines the focal biological unit.

The required immediate feature is: user sees the camera preview on iPad and draws a rectangle around the focal flower/head with a finger. PolliPi converts that rectangle to 640 × 360 monitor coordinates and sends it in `/start`.

Automatic flower detection may be added later only as an optional suggestion. Manual ROI drawing must remain available.

ROI tracking should track the flower/head, not insects.

## Review and learning policy

Images/events should be automatically pre-grouped as positive, negative, or unclear when possible.

The user should correct wrong labels. The workflow should not require a repeated “this classification is OK” confirmation.

Later learning should start with simple, inspectable models such as logistic regression, random forest, or simple image/anomaly features. The first target is positive vs negative candidate event filtering, not species identification.

## Decision rule

When choosing between two designs, prefer the option that:

1. works in the field
2. can be operated from iPad
3. continues after Wi-Fi/tethering disconnects
4. preserves recording-mode comparison
5. preserves event logs and labels
6. uses less power
7. is testable this week

## Instruction for AI assistants

Before making suggestions or code changes, read:

- `MASTER_SPEC.md`
- `DECISIONS.md`
- `TASKS.md`
- `CHANGELOG_AI.md`
- `HANDOFF.md`
- `FIELD_METHOD_ROADMAP.md`

Treat these as the source of truth unless the user explicitly overrides them.
