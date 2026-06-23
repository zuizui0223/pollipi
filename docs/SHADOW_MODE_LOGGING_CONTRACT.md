# Shadow-Mode Logging Contract

Shadow mode observes the live, **fixed-interval** timelapse and records what the
adaptive policy *would* have done — without ever changing capture timing and
without saving a per-motion image. It produces the evidence needed to calibrate
thresholds on real Pi data before any live adaptive control is enabled.

Source of truth: `pollipi_analysis.schemas.shadow` (`ShadowDecisionRecord`,
`SHADOW_LOG_COLUMNS`, `SHADOW_LOG_VERSION`).

## Guarantees

- `applied` is **always `False`** in shadow mode. The real interval is unchanged.
- `current_interval_sec` is the real, unchanged scheduled interval.
- `would_be_next_interval_sec` is advisory only and never acted on.
- **No image path field exists.** Shadow mode must not persist motion frames; the
  only image record remains the scheduled timelapse.
- One row is appended per scheduled capture (compact metadata, in-memory by
  default; flushed to CSV/JSONL).

## Record / CSV columns

`SHADOW_LOG_VERSION = "shadow-1"`. Columns are append-only and stably ordered
(`SHADOW_LOG_COLUMNS`); never reorder or remove a column without bumping the
version so historical logs stay parseable.

| Column | Meaning |
|---|---|
| `schema_version` | log format version (`shadow-1`) |
| `device_id` | Pi identifier |
| `frame_index` | sequential index of the scheduled capture |
| `captured_at` | capture timestamp |
| `current_interval_sec` | real (unchanged) interval |
| `would_be_next_interval_sec` | advisory policy output |
| `applied` | always `False` in shadow mode |
| `decision_state` | one of the canonical decision states |
| `reason` | stable token naming the rule branch that fired |
| `activity_score` | policy activity score (0–1) |
| `active_cell_proportion` … `mesh_layout` | the `MeshFeatures` evidence |

## Producing a log

```python
from pollipi_analysis.policy.state_policy import IntervalBounds
from pollipi_analysis.shadow import run_shadow_mode

records = run_shadow_mode(
    frames,                                   # scheduled timelapse frames
    bounds=IntervalBounds(baseline_interval_sec=60, min_interval_sec=10, max_interval_sec=180),
    device_id="zuizui4",
)
rows = [r.to_row() for r in records]          # CSV rows, SHADOW_LOG_COLUMNS order
json_rows = [r.to_json() for r in records]    # JSONL alternative
```

## How the Pi runtime should wire this

1. Keep the existing fixed-interval scheduler **unchanged**.
2. On each scheduled capture, compute features against the previous scheduled
   frame (or a maintained reference) using `pollipi_analysis.pipeline.analyze`.
3. Append one `ShadowDecisionRecord` (compact metadata only).
4. Do **not** change the interval and do **not** save the analysed frame.

This is the gating step before enabling live adaptive control: collect shadow
logs on real imagery, confirm the decision distribution is sane, then revisit
thresholds. Live adaptation stays disabled until then.
