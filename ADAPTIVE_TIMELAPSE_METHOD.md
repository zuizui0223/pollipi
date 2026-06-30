# PolliPi Adaptive Timelapse Method

This document describes the active, non-ML adaptive timelapse method implemented
in `packages/analysis` (Issues #13/#14/#15). It is the authoritative description
of the analysis behaviour; the Pi runtime and the laptop simulator import the
same functions from `pollipi_analysis`.

## 1. Research design (what this is and is not)

PolliPi is **not** a motion-triggered camera and **not** an automatic pollinator
classifier. It is a **local-first adaptive timelapse** system:

- The **scheduled timelapse images are the primary scientific record.**
- Motion analysis is used **only** to decide whether the *next* scheduled
  interval should be shorter, unchanged, or longer.
- A detected motion pattern is **never** reported as a confirmed pollinator
  visit. Confirmed visitation is evaluated later from the scheduled timelapse
  images, accounting for the variable sampling effort introduced by adaptive
  intervals.

There is no per-motion image stream and no event-review queue. The only image
record is the scheduled timelapse.

## 2. Decision states

Exactly three *active* states are produced from an analysed frame pair, plus a
resting state used by the policy:

| State | Meaning |
|---|---|
| `environmental_noise` | broad / common-mode change (wind, global shadow, camera shake) |
| `uncertain_local_activity` | localised but ambiguous change (low SNR, mixed target+noise) |
| `strong_visitation_candidate` | compact, concentrated, offset-mesh-agreeing localised motion |
| `no_activity` | below the activity threshold (resting) |

These are defined once in `pollipi_analysis.schemas.states`.

## 3. Interval policy

Stateless mapping from a decision state to the interval that *would* be used next
(`pollipi_analysis.policy.state_policy.plan_next_interval`):

```
environmental_noise         -> retain baseline interval, or cautiously lengthen
no_activity                 -> move gradually toward the maximum interval
uncertain_local_activity    -> retain baseline interval (log metadata only)
strong_visitation_candidate -> shorten ONLY the next scheduled interval
```

The baseline is never mutated, so a strong candidate shortens **only the next**
capture (`transient=True`); the schedule then returns to baseline unless another
strong candidate occurs.

> Adaptive interval control is **not enabled**. The policy output is currently
> recorded in shadow mode only (Section 6).

## 4. Mesh analysis

Whole-frame **overlapping spatial meshes**, not manually drawn floral ROI:

- **Working baseline:** a rectangular mesh plus a second rectangular mesh shifted
  by approximately half a cell (`rectangular_offset_baseline`). The offset mesh
  gives robustness to arbitrary cell-border crossings.
- A **hexagonal** layout is implemented for comparison only
  (`pollipi_analysis.mesh.grid.hexagonal_cells`) and must not replace the
  rectangular baseline prematurely (Issue #14).

### Pipeline (`pollipi_analysis.pipeline.analyze`)

1. optional small global translation registration (estimate + correct a few-px
   shift; the residual magnitude is itself a camera-shake feature)
2. optional global brightness normalization (remove a uniform illumination
   offset, e.g. a passing cloud)
3. residual motion image (`|frame - background|`)
4. overlapping mesh aggregation (primary + half-cell offset)
5. explainable, rule-based three-state decision

> **Temporal-median background subtraction is deliberately not in the default
> path.** Synthetic tests showed it can erase small, weak targets together with
> background noise, so it is not assumed to be beneficial.

### Explainable features (`pollipi_analysis.schemas.features.MeshFeatures`)

cell-level residual activity, active-cell proportion, connected-component size,
concentration, spatial concentration, offset-mesh agreement (a *spatial*
co-location score: the score-weighted active-cell centroid distance between the
primary and half-cell-offset meshes, normalised over ~2 cells — high when both
meshes localise activity to the same place, low for equal-magnitude activity at
different places), global synchrony, estimated global camera shift. The vector
also logs, as **evidence only** (not used by the V1 decision), persistence,
centroid displacement, the active-set Jaccard overlap across frames, and the
shadow-only track-window path efficiency. Every decision logs these values so it
is auditable after the fact.

### Rule cascade

The cascade (`classify_features`) is intentionally ordered: resting → common-mode
rejection (broad synchrony, broad active proportion, large diffuse component,
global camera shift, spatial scatter) → strong localised candidate (concentration
+ spatial concentration + spatial offset agreement + bounded active proportion) →
uncertain residual.

> **V1 scope (honest):** the V1 runtime decision uses **no multi-frame trajectory
> reasoning**. There is no oscillation / return-to-origin rejection (an earlier
> such rule was unsatisfiable under the current metric definitions and was
> removed) and no path-efficiency override in the runtime path — the
> path-efficiency track override exists only in offline shadow-mode analysis and
> does not affect live capture. Genuine multi-frame trajectory / oscillation
> discrimination is a **V2 candidate**, deliberately not implemented here.

## 5. Current simulation conclusion

Reproducible synthetic exploration (`python -m pollipi_analysis.simulation`,
fixed seed) over labelled scenarios shows:

- broad wind, camera shake, and global/moving shadow are reliably **rejected**;
- clean localised and boundary-crossing target trajectories are **retained** as
  strong candidates (candidate recall = 1.0, false-trigger rate = 0.0 on the
  Pareto front at `cell_size=32`);
- mixed target+wind, target+shadow, target+local-sway, and low-SNR targets
  **remain difficult** (they fall into `no_activity` / `environmental_noise` /
  `uncertain_local_activity` inconsistently).

**Therefore the synthetic thresholds are not field-ready.** The next required
stage is **shadow mode on real fixed-interval Pi imagery** (Section 6), not live
adaptive control.

## 6. Shadow mode

Shadow mode replays the live fixed-interval timelapse and records, per scheduled
capture, what the policy *would* have decided — without changing capture timing
and without saving any per-motion image. See
[docs/SHADOW_MODE_LOGGING_CONTRACT.md](docs/SHADOW_MODE_LOGGING_CONTRACT.md).

Pure runner: `pollipi_analysis.shadow.run_shadow_mode`.

## 7. Running it

```bash
cd packages/analysis
python -m pytest -q                                  # pure tests, no hardware
python -m pollipi_analysis.simulation --seed 7 --out-dir sim_out
```

The simulation writes `scenario_decisions.csv`, `parameter_search.csv`,
`pareto_front.csv`, per-scenario `shadow_*.csv`, and `pareto.png` (if matplotlib
is installed). All outputs are deterministic for a fixed seed.

## 8. What must still be validated on real Pi data

- Threshold calibration against real fixed-interval imagery (synthetic only here).
- Whether brightness normalization / registration help or hurt on real frames.
- Separation of low-SNR and mixed target+environment cases.
- Only after shadow-mode evidence: enabling live adaptive interval control.
