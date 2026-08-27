# TNOA Phase B — independent truth annotation and calibration gate

## Current state

Phase A writes one fail-closed `tnoa_observation_v1_<run_id>.csv` row per low-resolution Pi probe. Those rows contain algorithm evidence but remain `U / field_calibration_pending / observe_only`.

Phase B does **not** turn those raw values into field decisions. It establishes the independent truth material needed to calibrate and test them.

## Four truth layers

The annotation contract follows the InsePi V15 visit-observation design.

1. **Biological-event truth**, from an independent reference channel:
   - `no_insect`;
   - `insect_in_context`;
   - `target_contact`;
   - `visit_event`;
   - `truth_unresolved`.
2. **Target-coupled response truth**:
   - `present`;
   - `absent`;
   - `unresolved`.
   A resolved `present` requires resolved `target_contact` or `visit_event` truth.
3. **Exogenous nuisance truth**, multi-label, recording both physical family and inferential effect.
4. **Primary-stream observability truth**:
   - `observable`;
   - `compromised`;
   - `unobservable`.

The reference stream establishes biological truth and is never passed to the algorithm under test. If reference truth is unresolved, the row remains `truth_unresolved`; it is not relabelled `no_insect`.

## Blinded sheet generation

Generate an annotation sheet from a Pi TNOA log with:

```bash
python tools/tnoa_prepare_annotation.py prepare \
  tnoa_observation_v1_<run_id>.csv \
  annotation_<run_id>.csv \
  --site-id <site> \
  --flower-id <flower> \
  --plant-species <species> \
  --focal-scene-id <scene> \
  --recording-block <block> \
  --reference-source-id <independent-reference>
```

The output deliberately excludes:

- target ordinal score;
- nuisance diagnostics;
- observability diagnostics;
- TNOA state/reason;
- capture-policy recommendation.

Annotators therefore do not see the algorithm's answer while creating truth.

After annotation:

```bash
python tools/tnoa_prepare_annotation.py validate annotation_<run_id>.csv
```

The validator rejects logically circular coupling labels and unknown nuisance families/effects.

## Nuisance labels

Registered physical families in v1 are:

- wind-driven focal-target motion;
- camera shake;
- moving shadow;
- illumination change;
- occlusion;
- blur;
- non-target actor;
- other exogenous process.

Separately record whether the nuisance can `mimic`, `mask`, `corrupt_attribution`, or `degrade_observation`.

Insect-driven flower response belongs to the coupled truth layer, not nuisance, even when the pixel motion looks similar.

## Leakage-safe split

The minimum split group is:

```text
recording day x focal scene/flower x recording block
```

Frames/probes from one group cannot be split between development/calibration and held-out validation. At least 20% of truth material remains registered for independent double annotation; adjudication occurs before algorithm scoring.

## Pre-data calibration manifest

`calibration/tnoa_field_calibration_unfrozen_v1.json` is intentionally incomplete.

It contains no:

- target field thresholds;
- nuisance field alpha;
- O support thresholds;
- coupled-response/link thresholds;
- target-absence rule.

It also sets:

```text
heldout_scoring_allowed = false
live_tnoa_capture_actions_allowed = false
```

The V14b synthetic `alpha=0.05` and other synthetic/development thresholds are **not** copied into field defaults.

A later calibration generation may produce a new `frozen_field_calibration` manifest only after development/calibration truth has been evaluated and before held-out outcomes are inspected. Until that happens, Pi-side TNOA remains shadow-only.
