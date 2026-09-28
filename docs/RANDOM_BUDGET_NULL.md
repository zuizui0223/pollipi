# Equal-budget random temporal-allocation null

## Purpose

PolliPi's primary field question is not only whether classified adaptive sampling
beats fixed or motion-reactive sampling. It is also whether **using observed
activity to decide *when* to spend a fixed still-image budget contains real
temporal information**.

The random-budget null therefore asks:

> Given exactly the same number of high-resolution stills as Mode ③ classified
> adaptive, how many true visitation events would be captured if those stills
> were placed uniformly at random over the same available probe opportunities?

This is a temporal-allocation null. It is not a random classifier and it does not
change the mesh states.

## Primary null

For one run, let:

- O = the ordered low-resolution probe opportunities available to every replayed policy;
- N3 = the number of high-resolution stills allocated by Mode ③;
- R3 = the event-level visit capture rate of Mode ③.

The primary random schedule preserves the first mandatory capture at the first
probe opportunity, because the replayed field schedules all begin with a capture.
The remaining N3 - 1 stills are sampled uniformly without replacement from the
remaining probe opportunities.

Repeat this B = 10,000 times with frozen seed 20260928.

For random replicate b, compute event-level visit capture rate Rb using the same
independently annotated visit windows as the fixed/motion/classified comparison.

Report:

- mean(Rb);
- empirical 5th, 50th, and 95th percentiles;
- R3 - mean(Rb), in percentage points;
- one-sided Monte Carlo p-value

```text
p = (1 + number of Rb >= R3) / (B + 1)
```

The +1 correction prevents an estimated p-value of exactly zero.

## Primary interpretation

The predeclared directional test is:

```text
H0: Mode ③ visit capture is compatible with equal-budget random temporal allocation.
H1: Mode ③ visit capture is greater than equal-budget random temporal allocation.
```

Use alpha = 0.05 for the one-sided randomization test.

A small p-value supports only the statement that **the temporal allocation rule
uses information associated with visit timing better than uniform random
allocation under the same still budget and opportunity set**.

It does not by itself establish:

- unbiased visitation abundance;
- species-level identification accuracy;
- generalization to other plants, sites, seasons, or camera placements;
- lower energy use unless energy is measured;
- superiority to every possible adaptive scheduler.

## Sensitivity analysis

Run the same null with the first capture randomised as well
(`anchor_first=False`, CLI: `--random-free-first`).

The anchor-preserving result is primary because it matches the actual scheduling
contract. The fully random result is a sensitivity analysis, not a replacement
chosen after looking at results.

## Multiple runs / devices — frozen paper-level test

Randomisation must be performed **within each run**.

Do not pool all probe opportunities across devices, days, flowers, or runs and
then redistribute a global image budget. Each run keeps its own Mode ③ still
budget, duration, probe opportunities, and annotated visit windows.

The paper-level primary statistic is now frozen as the **micro-average event
capture rate**:

```text
R_micro = total Mode-③-captured visit events / total annotated visit events
```

This weights each independently annotated visit event equally.

For every Monte Carlo replicate, every run is independently randomised using its
own unchanged Mode-③ still budget and opportunity set. The replicate-level null
statistic is the corresponding pooled captured-event count divided by the same
fixed total number of annotated visits.

The primary one-sided joint p-value is:

```text
p_micro = (1 + number of null R_micro >= observed R_micro) / (B + 1)
```

with `B = 10,000`, master seed `20260928`, and `alpha = 0.05`.

### Run-balanced sensitivity statistic

Because high-visit runs contribute more events to the micro-average, report a
second, predeclared **macro-average run capture rate**:

```text
R_macro = mean(run-level visit capture rate)
```

over runs containing at least one annotated visit.

The macro-average is a sensitivity analysis, not a replacement primary endpoint.
Report its random-null mean, q05/q50/q95, effect difference, and one-sided
Monte Carlo p-value alongside the primary micro result.

### Reproducible run-specific random streams

Each run/replicate random stream is deterministically derived from:

```text
master seed × replicate index × run_id
```

using SHA-256 before seeding Python's PRNG. Therefore reordering rows in the
manifest cannot change the exact joint null result.

### Joint manifest

Use a CSV with required columns:

```text
run_id,probe_log,visits_csv
```

and optional per-run runtime intervals:

```text
low_interval_sec,mid_interval_sec,high_interval_sec
```

Relative file paths are resolved against the manifest location. `run_id` must
be unique. Runs with zero annotated visits may remain in the manifest and retain
their resource budget, but they do not enter the macro-average denominator.

Canonical command:

```bash
python -m pollipi_analysis.replay.joint joint_manifest.csv \
  --random-reps 10000 \
  --random-seed 20260928
```

Repeat with `--random-free-first` as the fully random first-capture sensitivity
analysis. JSON output is available with `--json`.

## Relationship to the other PolliPi baselines

The four scientific references answer different questions:

1. **Fixed timelapse** — does adaptation improve event capture over ordinary fixed effort?
2. **Motion-reactive** — does classifying environmental noise reduce wasted dense capture?
3. **Equal-budget random allocation** — does activity-informed timing itself contain useful information?
4. **Mode ③ classified adaptive** — the proposed stills-only policy.

Mode ④ video is not included in this primary stills-only comparison.

## Implementation

The canonical implementation is:

`packages/analysis/src/pollipi_analysis/replay/compare.py`

Functions:

- `replay_random_budget`;
- `random_budget_baseline`;
- `compare` (automatically attaches the null when visit annotations are supplied).

Default CLI behavior with `--visits` runs 10,000 random schedules. Use:

```bash
python -m pollipi_analysis.replay.compare RUN.csv \
  --visits visits.csv \
  --random-reps 10000 \
  --random-seed 20260928
```

and repeat with `--random-free-first` for the sensitivity analysis.

The implementation uses only the Python standard library for the randomisation
layer and is deterministic for a fixed seed.
