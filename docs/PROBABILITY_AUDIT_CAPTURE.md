# Probability audit capture (shadow-only)

Status: **default OFF experimental acquisition support** for the prospective same-universe benchmark defined in `zuizui0223/v3`.

This feature does not promote adaptive capture and does not define biological truth.

## What it does

When explicitly enabled, every existing low-resolution PolliPi probe still runs through the unchanged mesh/TNOA shadow pipeline. In parallel, PolliPi:

1. builds the canonical opportunity ID
   `device_id|run_id|probe_timestamp`;
2. reproduces the deterministic probability-audit draw used by `v3.audit_sampling`;
3. retains a bounded in-memory centred probe window;
4. for an included centre, saves the complete centred window after future context exists;
5. writes the full low-resolution Y plane as a lossless `.npy` audit copy;
6. writes a predeclared target-free ROI as a separate lossless `.npy` reference channel;
7. records included centres that cannot obtain a complete window at run edges.

Overlapping audit centres remain distinct sampled opportunities. Physical frames may therefore appear in more than one saved window; the opportunity/centre metadata are never collapsed.

## What it does not do

The audit path does **not**:

- change high-resolution capture timing;
- alter the three-stage policy decision;
- enable live adaptive acquisition;
- declare the reference ROI to be nuisance truth;
- infer visit/no-visit truth;
- infer physical nuisance truth;
- prove that the reference is scientifically informative;
- make a corrected/residual image the only retained representation.

The full Y-plane file is an audit copy. A reference crop that is derived from the same camera image is not automatically additional information relative to every possible primary representation. The analysis-side primary representation and reference channel must therefore be frozen before held-out scoring, and their actual estimand-relevant value must be checked with the V3 audit-burden / constrained-proxy tools.

## Required environment variables

The feature is disabled unless:

```text
POLLIPI_AUDIT_ENABLED=true
```

When enabled, all of the following must be supplied explicitly:

```text
POLLIPI_AUDIT_SEED=<frozen reproducibility seed>
POLLIPI_AUDIT_Q_SELECTED=<0 < p <= 1>
POLLIPI_AUDIT_Q_OMITTED=<0 < p <= 1>
POLLIPI_AUDIT_REFERENCE_ROI=x0,y0,x1,y1
```

The ROI uses normalized coordinates and must satisfy:

```text
0 <= x0 < x1 <= 1
0 <= y0 < y1 <= 1
```

Optional:

```text
POLLIPI_AUDIT_WINDOW_PROBES=9
```

The window size must be an odd integer >= 3. Nine probes is the current V3 temporal-window reference, not a universal scientific constant.

If audit capture is enabled with invalid/missing settings, application startup fails closed instead of silently collecting a different sample.

## Selection stratum

The on-device audit draw records:

```text
selected := would_be_mode != LOW
```

This is the `would_be_nonlow` shadow-policy surface. Actual recorded high-resolution selection remains available independently in the ordinary probe log and can be analyzed later as a different REC selection rule.

Equal `Q_SELECTED` and `Q_OMITTED` give a policy-independent audit inclusion probability. Unequal rates are permitted only because both remain strictly positive and each draw stores its actual inclusion probability.

## Storage layout

For run `<run_id>`:

```text
<image_dir>/probability_audit/<run_id>/
  config.json
  audit_draws.csv
  run_summary.json
  windows/
    <centre_opportunity_id>/
      manifest.json
      00_primary.npy
      00_reference.npy
      ...
```

`config.json` deliberately leaves biological and physical truth fields null. Truth is joined later from independent audit video/review or controlled intervention sources.

## Safety boundary

The instrumentation rejects a run if PolliPi's live adaptive gates would actually activate while probability audit capture is enabled. The prospective benchmark is shadow-only until development, freeze, and held-out audit are complete.

The scientific contract, partial-truth bounds, reference-portfolio analysis, and constrained-proxy realizability tests remain canonical in `zuizui0223/v3`.
