# PolliPi Field Method Roadmap

This document is the current source of truth for the user’s intended field workflow.

## Main goal

PolliPi should allow comparison of different field recording methods for plant–insect interaction monitoring.

The first goal is not full automation. The first goal is to record comparable data under several modes and evaluate which mode is practical in the field.

## Recording methods to compare

### Level 1: Basic methods

#### 1. Ordinary timelapse

The user chooses the interval.

Examples:

- 5 s
- 10 s
- 30 s
- 60 s

PolliPi saves images at that interval regardless of motion.

Purpose:

- baseline method
- comparable observation effort
- useful for ecological analysis

#### 2. Motion-triggered recording

PolliPi checks low-resolution frames for motion or image difference and saves images only when motion is detected.

Purpose:

- reduce storage
- reduce review effort
- test how much visit-like activity is captured without scheduled timelapse

Limitation:

- whole-frame motion can be caused by wind, shadows, leaves, or camera shake
- this is not insect classification

#### 3. Hybrid timelapse + motion-triggered recording

PolliPi always saves scheduled timelapse images and additionally saves motion-triggered event images between scheduled frames.

Purpose:

- preserve constant observation effort
- add event candidates for efficient review
- compare scheduled images and event images separately

### Level 2: Intermediate methods

#### 4. Adaptive timelapse

PolliPi changes the interval based on recent activity.

Example:

- quiet period: longer interval
- frequent candidate activity: shorter interval

Purpose:

- reduce battery/storage during quiet periods
- increase temporal resolution when insect activity may be high

#### 5. Flower/head ROI-based motion detection

The user draws a rectangle around the focal flower/head on the iPad preview. PolliPi detects motion only inside that ROI.

Purpose:

- focus on events occurring on the biological subject
- reduce background false positives from moving leaves, shadows, and non-focal flowers

This is the current highest-priority missing usability feature.

#### 6. Tracked flower/head ROI

After the user selects the focal flower/head, PolliPi optionally tracks that ROI as the flower moves in wind.

Purpose:

- keep the ROI on the flower/head
- reduce false positives and false negatives caused by wind movement

Important:

- track the flower/head, not insects
- use lightweight template matching first
- do not use YOLO every frame

### Level 3: Learning-assisted methods

#### 7. Automatic positive/negative/unclear pre-classification

Saved images or candidate events are automatically pre-sorted as:

- positive
- negative
- unclear

The user corrects wrong labels. The workflow should not require repeated “this classification is OK” confirmation.

Purpose:

- reduce manual review effort
- prepare training labels

#### 8. Same-day / next-day lightweight learning

When power and Wi-Fi are available, corrected labels can be used to train or update a lightweight model.

The trained model can be used in the next recording session.

First target:

- positive vs negative event/image filtering

Not first target:

- insect species identification

## Field operation requirement

PolliPi must continue recording after iPad, phone tethering, or Wi-Fi disconnects.

The user may:

1. connect iPad or phone hotspot
2. set recording mode and ROI
3. start autonomous recording
4. walk away

The program should keep running on the Raspberry Pi.

## Camera roles

### Module 3 / Module 3 Wide

Primary daylight camera for most field recording methods.

Use for:

- ordinary timelapse
- motion-triggered recording
- hybrid recording
- adaptive timelapse
- ROI-based daytime monitoring

### AI Camera (`zuizui2.local`)

Comparison and detection-test camera.

Use for:

- comparing image quality and event capture with Module 3
- testing simple on-device detection possibilities

Important:

- default AI Camera model is not an insect classifier
- do not treat default detections as insect species identification

### NoIR Wide (`zuizui3.local`)

Low-light or night-capable camera.

Use for:

- dusk/night trials
- infrared illumination experiments

Important:

- NoIR needs appropriate IR illumination in darkness
- record IR wavelength/power/illumination in `notes`
- do not mix daylight RGB and IR data without treating camera/illumination as a different condition

## Current blocker

The PWA still does not reliably allow the user to draw a ROI directly on the camera preview/monitor image.

This must be fixed before ROI tracking or learning features are prioritized.

## Current immediate implementation target

Fix iPad preview-based ROI drawing:

1. user taps `Preview / Set ROI`
2. app fetches still image from `/preview`
3. user draws rectangle around flower/head
4. rectangle is visible and aligned
5. coordinates convert to 640 × 360 monitor coordinates
6. ROI fields auto-fill
7. `/start` includes ROI only when valid
8. Clear ROI and Use full frame work
9. Review events still works

## Later validation questions

After core functions work, field tests should compare:

- ordinary timelapse vs motion-triggered vs hybrid
- full-frame motion detection vs ROI-based motion detection
- fixed ROI vs tracked ROI
- Module 3 vs AI Camera vs NoIR where appropriate
- manual review effort before/after positive/negative pre-classification
- Day 1 labels improving Day 2 filtering
