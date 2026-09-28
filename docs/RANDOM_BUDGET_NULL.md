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

## Multiple runs / devices

Randomisation must be performed **within each run**.

Do not pool all probe opportunities across devices, days, flowers, or runs and
then redistribute a global image budget. Each run keeps its own Mode ③ still
budget, duration, probe opportunities, and annotated visit windows.

For a multi-run paper-level test, combine run-level evidence with a predeclared
aggregate statistic or generate a joint null by independently randomising within
each run on every Monte Carlo replicate. Do not move captures between runs.

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
