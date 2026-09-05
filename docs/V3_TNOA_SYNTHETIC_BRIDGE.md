# V3–TNOA fresh synthetic bridge — frozen protocol

Status: **post-V3, pre-bridge-outcome protocol.** The V3 synthetic result was already known before this bridge hypothesis was formulated. This generation therefore uses a fresh master seed and a new development/heldout split. It must not be described as preregistered before V3.

## 1. Question

The bridge tests the two-layer prediction:

> At the same positive-support false-certainty budget, does a correctly coupled V3 representation allow TNOA to make more safe determinate target/nuisance decisions than the raw representation, and does breaking temporal reference coupling remove part of that gain?

This is stronger than asking whether V3 improves frame classification accuracy. It asks whether upstream representation changes **decision entitlement** at a fixed error meaning.

## 2. Frozen source methods

### V3

Use the already-frozen V3 representation unchanged:

- sequence length `T=9`;
- temporal rank `K=3`;
- same nine synthetic scenarios;
- same target path and nuisance generators;
- same PolliPi V1 downstream observer;
- no V3 parameter or V1 threshold search.

### TNOA

Pin the reusable TNOA decision API to repository commit:

`zuizui0223/tnoa@40fa8f66132cd86bdd5294b7360e024d13f9d9c4`

Use its `Evidence` and `classify` semantics unchanged.

This bridge is dynamic-window only. It does not add a quiet baseline scenario, so TNOA `B` is outside the present experiment.

## 3. Fresh generation

- master seed: `20260906`;
- replicates per scenario: `96`;
- development replicates: indices `0..47`;
- heldout replicates: indices `48..95`;
- scenarios:
  - `target_only`;
  - `target_plus_wind`;
  - `target_plus_shadow`;
  - `target_plus_shake`;
  - `target_plus_local_sway`;
  - `wind_only`;
  - `shadow_only`;
  - `shake_only`;
  - `local_sway_only`.

All representation arms share the same latent primary world within replicate/scenario.

## 4. Three representation arms

### Raw

No nuisance-reference projection.

- target score = fraction of the nine frames classified by unchanged V1 as `uncertain_local_activity` or `strong_visitation_candidate`;
- nuisance score = fraction of the nine frames classified by unchanged V1 as `environmental_noise`.

### Matched V3

Use the correctly coupled target-free temporal reference.

- target score = V1 local-candidate fraction after matched V3 projection;
- nuisance score = V3 `explained_primary_energy_fraction` from the matched reference.

### Time-broken V3

Use the deterministic time-permuted target-free reference already defined by V3.

- target score = V1 local-candidate fraction after time-broken V3 projection;
- nuisance score = V3 `explained_primary_energy_fraction` from the time-broken reference.

The time-broken arm is a coupling-specific negative control. It preserves reference data quantity and marginal frame content while breaking event-level temporal ordering.

## 5. Risk-semantic calibration

The numerical score thresholds are **not** shared across representations. The error semantics are shared.

This follows TNOA's threshold-portability principle: when a representation changes, recalibrate the score mapping rather than inheriting a raw threshold with a changed meaning.

Frozen support budget:

`alpha = 0.05`.

### Target-support calibration

For each representation arm separately:

1. use development nuisance-only worlds as negative families;
2. candidate target score thresholds are all observed development score values plus a threshold above the maximum;
3. choose the **lowest** threshold for which the empirical false target-support rate is `<= alpha` in **every** nuisance-only family;
4. do not use target-positive development recall to choose among valid thresholds.

Negative families:

- `wind_only`;
- `shadow_only`;
- `shake_only`;
- `local_sway_only`.

### Nuisance-support calibration

For each representation arm separately:

1. use development `target_only` worlds as the negative family;
2. candidate nuisance thresholds are all observed development score values plus a threshold above the maximum;
3. choose the **lowest** threshold with empirical false nuisance-support rate `<= alpha`;
4. do not use nuisance-positive development recall to choose among valid thresholds.

The bridge does not calibrate an absence channel.

## 6. TNOA evidence mapping

Every sequence is a dynamic synthetic window, therefore:

- `deviation_observed=True`;
- `observable=True`;
- `target_supported = target_score >= calibrated_target_threshold`;
- `nuisance_supported = nuisance_score >= calibrated_nuisance_threshold`;
- `coupled_response_supported=False`;
- `attribution_supported=False`.

The reusable TNOA `classify` function then returns B/T/N/U and a reason.

No latent scenario label is passed to TNOA.

## 7. Latent entitlement truth for evaluation only

Known synthetic process truth defines the evaluation target:

- `target_only` -> uniquely target-supported truth; correct determinate decision is `T`;
- nuisance-only scenarios -> uniquely nuisance-supported truth; correct determinate decision is `N`;
- target+nuisance scenarios -> genuine superposition; forcing unique `T` or `N` is false certainty and `U` is the safe final decision.

For mixed target+nuisance worlds, `U / target_nuisance_overlap` is more informative than other U reasons, but any U avoids the false unique decision. Both total overlap abstention and explicit overlap-reason rate are reported.

## 8. Primary metrics

### 8.1 Safe unique-process coverage

Among heldout unique-process worlds (`target_only` plus four nuisance-only families):

`safe_unique_coverage = correct T or N decisions / unique-process worlds`.

This is the primary coverage estimand.

### 8.2 False-certainty rate

Across all heldout dynamic worlds:

- target-only: `N` is false certainty;
- nuisance-only: `T` is false certainty;
- target+nuisance: either unique `T` or unique `N` is false certainty;
- `U` is not false certainty.

Report the pooled rate and process-family rates.

### 8.3 Overlap preservation

Among target+nuisance worlds report:

- U rate;
- `target_nuisance_overlap` reason rate;
- forced unique T/N rate.

### 8.4 Target-only retention

Report heldout `T` rate for `target_only` to guard against gaining nuisance rejection by deleting the target signal.

### 8.5 Support-level calibration checks

On heldout data report:

- false target-support rate separately for each nuisance-only family;
- maximum nuisance-family false target-support rate;
- false nuisance-support rate in target-only worlds.

These are empirical fresh-generation checks, not distribution-free guarantees.

## 9. Paired uncertainty

Representation arms share the same replicate/scenario worlds.

For heldout replicate indices, compute paired bootstrap confidence intervals with:

- `5,000` bootstrap resamples;
- replicate index as the resampling unit across all scenarios;
- seed `2026090601`.

Report 95% percentile intervals for:

- matched minus raw safe unique-process coverage;
- matched minus time-broken safe unique-process coverage;
- matched minus raw false-certainty rate.

## 10. Frozen promotion rule

The two-layer synthetic bridge is promoted to a **joint V3–TNOA candidate architecture** only if all are true on the fresh heldout generation:

1. matched V3 safe unique-process coverage exceeds raw by at least `0.10`;
2. the paired-bootstrap 95% lower bound for matched minus raw safe coverage is `> 0`;
3. matched V3 safe unique-process coverage exceeds time-broken V3 by at least `0.05`;
4. the paired-bootstrap 95% lower bound for matched minus time-broken safe coverage is `> 0`;
5. matched V3 pooled false-certainty rate is `<= 0.10` and no more than `0.01` above raw;
6. matched V3 target-only `T` rate is no more than `0.05` below raw;
7. matched V3 does not increase the forced-unique T/N rate in target+nuisance worlds by more than `0.05` relative to raw.

No criterion is a CI success condition. Failed scientific criteria are retained as results rather than tuned away.

## 11. Interpretation boundary

A positive bridge result would support:

> In a fresh controlled synthetic generation, a correctly coupled target-free temporal nuisance representation can increase TNOA's safely resolvable target/nuisance coverage under a fixed positive-support error semantics, beyond both raw representation and a time-broken reference control.

It would not establish:

- real-field performance;
- biological absence;
- physical nuisance identity;
- universal benefit across sensing domains;
- statistical independence of evidence channels;
- that V3 is required for TNOA;
- that TNOA validates V3 outside this synthetic bridge.
