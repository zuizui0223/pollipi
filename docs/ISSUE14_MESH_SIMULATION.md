# Issue 14 Mesh Motion Calibration

PolliPi keeps scheduled timelapse images as the primary field record. Mesh motion
analysis only writes compact metadata and can shorten or lengthen the next
scheduled interval; it does not create an unbounded image-per-event stream and it
does not claim a confirmed visit.

> **Scope note.** This page documents the original Issue-14 mesh-motion
> calibration (`pollipi_analysis.mesh.motion`), an exploratory standalone path.
> It is **not** the production Mode-③ runtime classifier
> (`pollipi_analysis.pipeline.classify_features`), which is described in
> `ADAPTIVE_TIMELAPSE_METHOD.md`. The production runtime uses a **spatial**
> offset-mesh agreement (centroid co-location, not proportion difference) and
> performs **no** oscillation / return-to-origin rejection — that is a V2
> candidate. The `return-to-origin` / `oscillation` items below apply only to
> this legacy calibration module.

The current implementation is a deterministic rectangular mesh baseline with a
half-cell offset mesh. Hex cells remain the preferred final layout, but the
rectangular baseline is easier to test on the existing Pi/server stack and keeps
the API shape compatible with a future hex implementation.

The simulator covers these calibration cases:

- `localized_trajectory`: small localized movement, expected `visitation_candidate`.
- `broad_wind`: broad structured motion, expected `environmental_noise`.
- `camera_shake`: common-mode frame shift, expected `environmental_noise`.
- `oscillation`: repeated local return-to-origin style motion, expected noise when
  previous active cells overlap strongly.
- `shadow`: broad brightness change, expected `environmental_noise`.

Thresholds are intentionally rule-based and logged as explainable features:
active-cell proportion, largest component size, concentration, offset agreement,
global synchrony, transition score, and return-to-origin score.
