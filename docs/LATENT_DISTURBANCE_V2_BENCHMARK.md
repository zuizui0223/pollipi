# V2 latent-disturbance benchmark — frozen before execution

Status: **simulation-only benchmark specification. No runtime or field-capture behaviour changes.**

## Question

Can a target-free reference channel carrying the same latent visual disturbance improve recovery of a local biological signal when target and nuisance occur together?

The benchmark deliberately does **not** ask whether a new classifier can be tuned to synthetic labels. The downstream PolliPi V1 `pipeline.analyze()` classifier remains unchanged. V2 changes only the pre-classification observation representation.

## Three frozen reference conditions

For the same latent primary scene, compare:

1. `correct_reference`: a target-free reference frame generated from the **same nuisance realization** as the primary frame;
2. `corrupted_reference`: a target-free reference generated from a **different nuisance realization/phase**, preserving nuisance class and approximate scale but breaking the event-level coupling;
3. `no_reference`: the current primary observation without reference subtraction.

The correct reference is informative about nuisance but never contains the biological target. The corrupted reference is a falsification control: any generic extra-image benefit should also appear there.

## Frozen nuisance estimator

Let

`d_primary = primary_frame - background`

and

`d_reference = reference_frame - background`.

For a supplied reference, estimate one nuisance-loading coefficient

`alpha = clip(<d_primary,d_reference> / <d_reference,d_reference>, 0, 1.5)`

and form

`d_residual = d_primary - alpha * d_reference`.

The V2 corrected frame is `background + d_residual`.

No biological label, target location, target mask, scenario name or downstream V1 decision is used when estimating `alpha`.

This is intentionally a minimal reference-guided nuisance projection, not a claim that the final field method must remain linear.

## Synthetic worlds

Each stochastic replicate contains a clean background plus zero or one local target and zero or one nuisance component.

### Target-bearing scenarios

- `target_only`
- `target_plus_wind`
- `target_plus_shadow`
- `target_plus_shake`
- `target_plus_local_sway`

### Nuisance-only controls

- `wind_only`
- `shadow_only`
- `shake_only`
- `local_sway_only`

The target is present only in the primary channel. Correct-reference frames never contain target signal.

## Outcomes

All three reference conditions are passed to the **same frozen V1** `pipeline.analyze()`.

A target-bearing replicate is counted as retained if the V1 state is either:

- `uncertain_local_activity`, or
- `strong_visitation_candidate`.

A nuisance-only replicate is counted as a false event if the V1 state is either of those same two local-candidate states.

Report:

- mixed-target recall (excluding `target_only`);
- target-only recall;
- nuisance-only false-event rate;
- balanced utility = `(mixed_target_recall + (1 - nuisance_false_event_rate)) / 2`;
- per-scenario rates;
- fitted `alpha` distribution.

## Frozen promotion rule

Before seeing aggregate results, V2 is promoted from simulation hypothesis to a candidate method only if **all** are true:

1. correct-reference mixed-target recall is at least `0.10` higher than no-reference;
2. correct-reference nuisance false-event rate is no higher than no-reference;
3. correct-reference balanced utility is at least `0.08` higher than corrupted-reference;
4. correct-reference target-only recall is no more than `0.05` below no-reference.

Failure of any criterion is retained as an adverse result; thresholds or scenarios are not retuned to rescue the hypothesis.

## Replication

Use `64` stochastic replicates per scenario by default with deterministic seeds derived from a fixed master seed. The same primary latent world is reused across the three reference conditions within a replicate, so comparisons are paired by construction.

## Claim boundary

A positive result would support only:

> In a controlled synthetic setting, event-matched target-free reference information can improve separation of shared nuisance from local target signal before the existing PolliPi classifier, and this benefit disappears when the reference coupling is broken.

It would **not** establish field wind inference, causal identification of physical wind, superiority of a trained deep model, field-ready thresholds, or live adaptive capture safety.

A positive simulation result justifies real fixed-interval reference/primary shadow collection. A negative result rejects this minimal nuisance-projection mechanism and requires a different V2 representation before field promotion.
