# Independent visit-event truth contract

## Why this file exists

PolliPi's field-validation claims compare **when different policies would have
captured true flower-visitation events**. Therefore the visit truth must exist
independently of the still images selected by PolliPi.

An image-level label file such as `visit_labels.csv` is useful for reviewing
saved JPEGs, but it cannot establish visits that happened between those JPEGs.
It is therefore **not sufficient as the primary truth source** for the fixed /
motion-reactive / classified / random timing comparison.

The paper-level `visits.csv` must be generated from an independent reference
channel that observes the run without depending on PolliPi's capture policy.

## Required columns

```text
event_id,start,end,truth_source
```

Optional but recommended columns:

```text
visitor_group,reviewer_id,confidence,reference_file,notes
```

### event_id

Unique within a run. Example: `V0001`.

### start / end

Either:

- seconds from the first probe timestamp; or
- ISO-8601 timestamps compatible with the run clock.

`end >= start` and the event must lie inside the probe opportunity range.

### truth_source

Must be one of:

```text
continuous_reference_video
high_frequency_reference_video
controlled_event_schedule
independent_sensor
```

These names intentionally exclude PolliPi-selected stills.

The primary flower-visitation application should normally use
`continuous_reference_video` or a sufficiently dense independent reference
video.

## Recommended metadata

### visitor_group

Broad group when identifiable, for example:

```text
bee
fly
butterfly_moth
beetle
other_insect
unknown
```

Do not force a taxonomic assignment when the reference does not support it.

### confidence

Recommended values:

```text
high
medium
low
```

The primary analysis should retain all predeclared eligible truth events. A
high-confidence-only analysis may be reported as sensitivity analysis, not used
post hoc to rescue the main result.

### reference_file

Filename or stable identifier of the continuous/high-frequency reference source
from which the event was annotated.

## Event definition

One biologically continuous visit should be one event window. The annotation
protocol should be frozen before the main held-out field scoring.

A visit begins when the visitor first makes the predeclared focal interaction
with the flower/display and ends when that continuous interaction ends.

If two visitors overlap in time they may be represented as separate event rows.
The input preflight will warn about overlapping windows because one still can
then capture more than one event.

## Forbidden circular truth

Do not construct `visits.csv` by:

- reviewing only Mode-③ candidate windows;
- reviewing only times when any PolliPi policy saved a still;
- treating `strong_visitation_candidate` as a true visit;
- defining event boundaries from PolliPi's LOW/MID/HIGH transitions;
- dropping reference-video intervals because PolliPi did not capture anything.

Those procedures make the truth depend on the method being evaluated and can
artificially inflate apparent capture performance.

## Relationship to visit_labels.csv

`visit_labels.csv` answers:

> What is visible in this saved high-resolution PolliPi image?

`visits.csv` answers:

> What true visit events occurred during this run, regardless of whether PolliPi
> saved an image at that time?

The field-validation analysis uses `visits.csv` for event-capture truth.
Image-level labels may be joined later for image quality, visitor identity or
behavioral analyses.

## Example

See `docs/templates/visit_events.example.csv`.

## Fail-closed behavior

The paper-level field-validation preflight rejects a visits file when:

- required columns are missing;
- event IDs are duplicated or empty;
- truth_source is not one of the independent sources above;
- timestamps cannot be parsed;
- end < start;
- an event lies outside the run opportunity range.

This guarantees that a result artifact cannot silently use
policy-selected still images as its declared primary truth.
