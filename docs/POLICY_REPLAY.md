# Policy replay — comparing ①②③ on one real record

`pollipi_analysis.replay` answers the study question offline: on the **same**
field recording, what would each capture policy have done?

- **① fixed** — plain fixed-interval timelapse (no adaptation)
- **② any-motion** — faster stills on ANY motion (wind / shadow / insect alike)
- **③ classified** — noise filtered; local candidate → faster stills; strong → video clip

Every policy is replayed through the *same* `ThreeStageController` the Pi runs, so
the control logic is identical to production — only the decision-state sequence is
read from the field log. This makes ③'s value measurable: fewer wasted captures
than ② on wind/shadow, and escalation on real visits that ① at a slow interval
misses (the capture-rate vs storage/energy balance).

## Input

A per-run probe log written by the Pi during any classified (③) run — even in
pure shadow mode (no capture-timing change):

```
~/pollipi_timelapse/images/adaptive_probe_shadow_v2_<run_id>.csv
```

It records one row per 5 s probe with the mesh `decision_state`, so all three
policies can be reconstructed from it. On external USB the file follows the
active image directory.

## Run

```bash
# from packages/analysis (or with pollipi_analysis on PYTHONPATH)
python -m pollipi_analysis.replay adaptive_probe_shadow_v2_<run_id>.csv --fixed-interval 30
```

Output columns: `stills`, `clips`, `video_s`, `storage_MB` (and `visit%` / `lat_s`
when annotations are supplied). `3 actual(log)` echoes what the run itself saved,
as a fidelity cross-check against the replayed `3 classified`.

Useful flags: `--low/--mid/--video-duration/--cooldown` (override the ③ controller
shape), `--still-kb/--video-mbps` (storage model), `--json`.

## Visit capture-rate (ground truth)

To measure how many real visits each policy caught, annotate visit windows in a
CSV and pass `--visits`:

```csv
start,end
2026-07-04T10:12:35,2026-07-04T10:12:48
930,948
```

Each value is either an ISO timestamp (matching `probe_timestamp`, e.g. copied
from an image filename) or plain seconds from the run start. Establish ground
truth from the saved stills / clips / `shadow_evidence/` image pairs. The report
then adds `visit%` (fraction of windows with ≥1 capture) and `lat_s` (mean time
from visit start to first capture) per policy.
