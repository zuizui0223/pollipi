# PolliPi field-validation analysis v1

## Purpose

This is the frozen paper-level analysis contract for PolliPi Issue #81.

It evaluates the same independently annotated field runs under three still-image
policies plus the equal-budget random temporal-allocation null:

1. Mode 1 — fixed timelapse;
2. Mode 2 — motion-reactive adaptive timelapse;
3. Mode 3 — classified adaptive timelapse;
4. equal-budget random temporal allocation.

Mode 4 video is not part of the primary stills-only comparison.

## Primary hypotheses and gates

### H1 — classified adaptive versus fixed

Estimand:

```text
Delta_31 = visit_capture_rate(Mode 3) - visit_capture_rate(Mode 1)
```

Uncertainty is estimated by percentile cluster bootstrap with **run as the
resampling unit**.

Default:

- 10,000 bootstrap replicates;
- seed `20260928`;
- 95% percentile interval.

H1 is supported only when:

```text
lower_95(Delta_31) > 0
```

A positive point estimate with a confidence interval crossing zero is not enough
to pass the frozen H1 gate.

### H2 — classified adaptive versus motion-reactive

H2 contains two required components.

#### H2a: visit-capture non-inferiority

Estimand:

```text
Delta_32 = visit_capture_rate(Mode 3) - visit_capture_rate(Mode 2)
```

The absolute non-inferiority margin is frozen at **0.05**, i.e. 5 percentage
points.

Mode 3 is non-inferior only when:

```text
lower_95(Delta_32) > -0.05
```

#### H2b: non-visit recording-cost reduction

For each policy, a still is counted as a visit-overlapping still when its capture
timestamp lies inside at least one independently annotated visit interval.
Otherwise it is a non-visit still.

The resource proxy is:

```text
nonvisit_stills_per_hour = nonvisit_stills / observed run duration
```

The H2 cost estimand is:

```text
Delta_cost =
    nonvisit_stills_per_hour(Mode 3)
  - nonvisit_stills_per_hour(Mode 2)
```

Cost reduction is supported only when:

```text
upper_95(Delta_cost) < 0
```

H2 passes only if **both H2a and H2b pass**.

This metric is a recording/capture-operation proxy. It is not electrical energy
unless Wh is measured independently.

### Equal-budget random temporal allocation

The primary randomization test remains defined in
[`RANDOM_BUDGET_NULL.md`](RANDOM_BUDGET_NULL.md).

The paper-level primary statistic is event-weighted micro-average visit capture,
with randomisation performed separately within every run using that run's exact
Mode-3 still budget and probe opportunities.

Random timing is supported only when:

```text
Mode3 - random_mean > 0
AND
one_sided_Monte_Carlo_p < 0.05
```

The run-balanced macro-average remains a sensitivity analysis.

## Overall primary result

The machine-readable result contains these gates:

```text
h1_supported
h2_capture_noninferior
h2_cost_reduction_supported
h2_supported
random_timing_supported
all_primary_criteria_supported
```

`all_primary_criteria_supported` is true only when:

```text
H1 passes
AND H2 passes
AND random timing passes
```

The software does not rescue a failed criterion by choosing a different endpoint,
margin, weighting rule, random seed, or confidence interval after the results are
seen.

## Reported policy metrics

For each of Modes 1–3, report:

- total annotated visits;
- visits captured;
- event-level visit capture rate;
- total stills;
- stills per hour;
- stills overlapping true visit windows;
- visit-overlapping stills per true visit;
- non-visit still count;
- non-visit stills per hour.

`visit-overlapping stills per visit` is not automatically a measure of image
quality. If image usability is reviewed separately, that should be added as a
separate truth field rather than inferred from timing overlap.

## Resampling unit

The cluster bootstrap resamples **runs**, not individual visit events.

This preserves within-run dependence caused by:

- shared weather and illumination;
- shared flower/plant identity;
- the same camera placement;
- the same controller state history;
- temporally clustered visits.

For visit-capture contrasts, only runs containing at least one annotated visit
enter the bootstrap sampling frame.

For the non-visit still burden, all positive-duration runs enter the bootstrap
sampling frame, including zero-visit runs.

## Canonical input

Use the same joint manifest as the random-budget analysis:

```text
run_id,probe_log,visits_csv,low_interval_sec,mid_interval_sec,high_interval_sec
```

Required fields:

- `run_id`;
- `probe_log`;
- `visits_csv`.

Interval columns are optional and default to the current three-stage defaults.

Relative paths are resolved against the manifest directory.

## Canonical command

```bash
python -m pollipi_analysis.replay.field_validation joint_manifest.csv \
  --bootstrap-reps 10000 \
  --bootstrap-seed 20260928 \
  --noninferiority-margin 0.05 \
  --random-reps 10000 \
  --random-seed 20260928 \
  --output-json results/pollipi_field_validation_v1.json
```

Use `--random-free-first` only for the already-predeclared sensitivity analysis
where the first capture is randomised too.

## Result artifact

The JSON schema identifier is:

```text
pollipi-field-validation-v1
```

It includes:

- all policy aggregates;
- all run-level metrics;
- H1 bootstrap estimate and 95% interval;
- H2 capture bootstrap estimate and 95% interval;
- H2 non-visit still-burden bootstrap estimate and 95% interval;
- the complete joint random-budget null result;
- all frozen claim gates.

The result should be archived without manual editing whether the outcome is
positive, mixed, or adverse.

## Claim boundary

Even if all primary gates pass, the supported claim remains narrow:

> Under the evaluated field runs and opportunity sets, classifier-informed
> adaptive temporal allocation captured more true visitation events than fixed
> timelapse, retained non-inferior event capture relative to motion-reactive
> sampling while reducing non-visit recording burden, and outperformed
> equal-budget uniform random temporal allocation.

Passing these gates does not by itself establish:

- unbiased visitation abundance;
- universal superiority across plants/sites/seasons;
- species identification accuracy;
- lower electrical energy without direct Wh measurement;
- causal identification of wind/shadow classes;
- superiority to every possible adaptive scheduling algorithm.
