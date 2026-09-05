# V2 shift-identifiability diagnostic — frozen before execution

Status: **diagnostic only; no method promotion and no threshold tuning.**

## Purpose

V2.1 increased mixed-target recall but worsened nuisance false-event rate and selected all 25 candidate translations across the benchmark. Before attempting another fix, test whether the injected 2 px reference displacement is identifiable from the single primary/reference frame pair under the frozen trimmed-residual objective.

## Frozen design

Use the same synthetic worlds, master seed `20260905`, 64 replicates per scenario, and the same `shift2_reference` generator used in the failed robustness test.

Exclude `target_only` because it has no nuisance delta and therefore no meaningful injected reference displacement to recover.

For every remaining replicate:

1. reproduce the injected reference shift `(dy_true, dx_true)` from the frozen reference RNG seed;
2. the alignment target is the inverse shift `(-dy_true, -dx_true)`;
3. evaluate all 25 V2.1 candidate translations using the unchanged 10% trimmed residual-energy objective;
4. record the selected shift, exact inverse-shift match, Manhattan error, whether error <= 1 px, best loss, second-best loss and their margin.

## Report

- exact inverse-shift recovery rate overall;
- recovery rate within Manhattan distance <= 1;
- mean and median Manhattan error;
- exact recovery by nuisance family (`wind`, `shadow`, `shake`, `local_sway`);
- exact recovery separately for target-bearing versus nuisance-only worlds;
- mean and median best-vs-second loss margin;
- number of distinct selected shifts.

## Interpretation

This diagnostic does not have a promotion threshold. It determines the next method class.

If exact recovery is low and loss margins are small, single-pair translation is weakly identified; stop tuning it and move to multi-frame temporal or low-rank/learned nuisance representations.

If recovery is high but downstream nuisance FPR remains high, the issue lies after alignment (projection or classifier interaction) rather than shift identifiability.
