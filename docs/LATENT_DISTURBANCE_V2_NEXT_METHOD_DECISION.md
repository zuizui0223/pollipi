# V2 next-method decision rule

Status: **frozen before oracle-shift diagnostic results are read.**

The project has already tried the minimal unaligned scalar projection and one label-free single-pair alignment revision. Further arbitrary tuning is prohibited. The next method class is chosen from the oracle diagnostic as follows.

## Decision tree

### A. Oracle-shift wind/shake remain noisy

If the oracle inverse shift still leaves high nuisance false-event rates for wind or shake, then shift estimation is not the main seam for those families.

Next method class:

- boundary/valid-overlap-aware nuisance representation;
- or a low-rank spatiotemporal nuisance field that does not require exact pixel subtraction.

Do **not** tune V1 classifier thresholds to absorb border artefacts.

### B. Oracle-shift wind/shake become clean but estimated alignment remains noisy

Then the primary seam is alignment estimation.

Next method class:

- multi-frame reference alignment / temporal registration;
- exploit disturbance persistence across several probes rather than one pair.

Do not keep changing single-pair loss trimming.

### C. Local sway oracle clean, estimated alignment noisy

Then local sway requires temporal structure because the compact nuisance is target-like in a single pair.

Next method class:

- multi-frame trajectory/oscillation nuisance embedding;
- direction reversal, recurrence, path efficiency, cross-reference synchrony.

This directly implements the original V2 concept: infer shared disturbance from its temporal signature rather than classify one frame pair.

### D. Oracle remains noisy for local sway too

Then local nuisance and biological target are not separable by reference subtraction alone in the current spatial representation.

Next method class:

- multi-frame latent state inference with explicit uncertainty/abstention;
- potentially learned or low-rank reference-conditioned embeddings.

### E. Border excess is high in oracle-shift broad nuisances

Treat spatial support loss as part of the measurement model. The next representation must preserve/declare valid support rather than fabricate zero-filled pixels.

## Field boundary

No branch in this decision tree authorizes live adaptive capture. Real field promotion requires a later fixed-interval shadow design with independent/manual event truth and target-free nuisance evidence.
