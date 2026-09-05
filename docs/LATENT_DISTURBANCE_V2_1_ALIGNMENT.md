# V2.1 alignment-aware nuisance projection — frozen before execution

Status: **post-failure method revision.** This responds only to the failure localized in the frozen V2 reference-degradation test. V1 classifier thresholds, primary worlds, target/nuisance amplitudes, replicate count and seed remain unchanged.

## Failure being addressed

The unaligned `shift2_reference` arm improved mixed-target recall (`0.6914` vs `0.2969` no-reference) but raised nuisance false-event rate to `0.3047`, above the frozen acceptable bound `0.2883`.

The observed failure pattern is consistent with spatially displaced nuisance boundaries leaving local residual edges.

## V2.1 method

For an available reference, search integer translations

`dy, dx in {-2,-1,0,1,2}`

of the reference nuisance delta relative to the primary background.

For each candidate shift:

1. shift the reference delta without wrap-around;
2. fit the same clipped scalar loading `alpha` used in V2;
3. form residual `d_primary - alpha * d_reference_shifted`;
4. compute alignment loss as the mean absolute residual after discarding the largest 10% of absolute residual pixels.

Choose the `(dy, dx)` with minimum trimmed residual loss. The 10% trim prevents a compact biological target from dominating alignment.

No target label, target mask, scenario identity or V1 decision is available to the alignment search.

## Frozen evaluation

Use the **same 2 px degraded reference worlds** and compare:

- `shift2_unaligned` — already tested V2 projection;
- `shift2_aligned_v2_1` — V2.1 alignment search then projection;
- `no_reference`.

Use 64 paired replicates per scenario and master seed `20260905`.

## Frozen promotion rule

V2.1 is promoted to a **simulation-robust field-shadow candidate** only if all are true:

1. aligned mixed-target recall exceeds no-reference by at least `0.10`;
2. aligned nuisance false-event rate is no more than `0.05` above no-reference;
3. aligned balanced utility exceeds unaligned shift2 by at least `0.08`;
4. aligned target-only recall is no more than `0.05` below no-reference;
5. the fitted alignment is not hard-coded: at least two distinct `(dy, dx)` values are selected across stochastic replicates.

No shift range, trim fraction, threshold or world parameter is changed after aggregate results are observed.

## Interpretation boundary

Passing permits only the next step: **real fixed-interval shadow data collection with primary and target-free reference evidence**. It does not enable live adaptation and does not identify physical wind as a causal variable.

Failing means the simple aligned linear projection remains insufficient; the next representation must move to more flexible low-rank or learned spatiotemporal nuisance embeddings rather than further threshold tuning.
