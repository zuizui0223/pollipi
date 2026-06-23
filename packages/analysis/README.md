# pollipi-analysis

Pure-Python analysis core for PolliPi's local-first **adaptive timelapse**. No
FastAPI, no Picamera2, no required filesystem dependency. The Pi runtime and the
laptop simulator import the **same** feature, classifier, and policy functions
from here, so calibration matches production.

See [../../ADAPTIVE_TIMELAPSE_METHOD.md](../../ADAPTIVE_TIMELAPSE_METHOD.md) for
the method, and
[../../docs/SHADOW_MODE_LOGGING_CONTRACT.md](../../docs/SHADOW_MODE_LOGGING_CONTRACT.md)
for the shadow-mode log format.

## Layout

```
src/pollipi_analysis/
  schemas/      states, MeshFeatures, MeshDecision, ShadowDecisionRecord
  mesh/         rectangular baseline + half-cell offset (hex for comparison)
  features/     registration, brightness normalization, residual, features
  policy/       state-driven interval policy
  pipeline.py   5-step explainable three-state decision
  shadow.py     pure shadow-mode runner (no timing change, no image saved)
  simulation/   reproducible scenarios + parameter search + CSV/plot
```

## Run

```bash
python -m pytest -q                                   # pure tests, no hardware
python -m pollipi_analysis.simulation --seed 7 --out-dir sim_out
```

The simulation is deterministic for a fixed seed and writes
`scenario_decisions.csv`, `parameter_search.csv`, `pareto_front.csv`,
`shadow_*.csv`, and `pareto.png` (plot needs the optional `plot` extra).

## Decision states

`environmental_noise`, `uncertain_local_activity`, `strong_visitation_candidate`,
plus resting `no_activity`. A state is **never** a confirmed pollinator visit; it
only informs whether the next scheduled interval should be shorter, unchanged, or
longer. Live adaptive control is **not** enabled — shadow mode logs only.
