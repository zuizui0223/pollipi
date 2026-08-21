# PolliPi × InsePi contradiction benchmark

## Why this exists

PolliPi and InsePi should not be merged into one classifier yet. They inspect the
same ecological observation from different directions:

- **PolliPi:** where should finite capture effort be allocated to recover local
  visitation evidence?
- **InsePi:** when is the observation process confounded, and which false-event,
  missed-event, or attribution risk is active?

The disagreement is therefore potentially informative. This benchmark keeps the
implementations independent and compares only their emitted traces.

## V1 latent contract

Both repositories implement the stable schema
`pollipi-insepi-contradiction-v1` and these scenario IDs independently:

- `quiet_absence`, `clean_visit`
- `wind_absence`, `wind_visit`
- `shake_absence`, `shake_visit`
- `shadow_absence`, `shadow_visit`
- `occluded_visit`, `blurred_visit`, `clutter_visit`, `unknown_visit`

Each scenario carries latent simulator truth:

```text
true_visit
noise_source
noise_confidence
event_visibility
```

PolliPi translates that latent condition into synthetic mesh evidence and then
uses the existing `classify_features()` unchanged. The output trace records:

```text
scenario_id
true_visit
noise_source
pollipi_state
pollipi_reason
capture_posture
```

The InsePi sibling trace records its independent observability decision and risk
scores. A comparator joins the traces by `scenario_id` after both decisions have
already been made.

## What V1 is testing

V1 is a **policy-level** contradiction simulation. It is not evidence that the
vision front ends already recover these latent variables in real field video.
The purpose is to expose where the current decision principles necessarily pull
capture effort in different directions before spending effort on a shared visual
benchmark.

Expected high-value tensions include:

| Latent condition | PolliPi tendency | InsePi tendency | Why useful |
| --- | --- | --- | --- |
| true visit + broad vegetation motion | environmental noise / suppress candidate allocation | high false-event risk / audit | separates biological absence from poor observability |
| true visit + camera shake | environmental noise | high false-event risk / audit | tests whether rejecting shake creates missed-event bias |
| true visit + moving shadow | environmental noise | false + missed-event risk / audit | tests photometric selection bias |
| true visit + clutter | diffuse/noise | high attribution risk / audit | identifies cases where local-event counting and causal attribution diverge |
| true visit + occlusion/blur | faint/uncertain local activity | high missed-event risk / audit | complementary rather than contradictory; both call for caution |

## Development rule

Do **not** tune PolliPi thresholds to agree with InsePi. Repeated disagreement is
first logged as evidence. A rule is changed only after independent truth/audit
shows that one failure mode is systematic.

## Next layers

1. **V1 policy contradiction:** current module; deterministic latent conditions.
2. **V2 visual contradiction:** render the same pixels and run both front ends.
3. **V3 replay:** run both on fixed-interval flower-camera sequences with human
   visit labels and condition labels.
4. **V4 field allocation:** compare fixed, PolliPi-only, InsePi audit-priority,
   and disagreement-priority capture under the same storage/power budget.

The main scientific endpoint is not agreement. It is whether disagreement
predicts false visits, missed visits, attribution failures, or biased ecological
rates better than either system alone.
