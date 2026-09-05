# V3–TNOA trajectory bridge — result

Status: **promotion failed. Multi-frame target geometry improved overlap preservation and false certainty, but exposed a new overprojection / representation-entitlement boundary. No rescue tuning.**

Canonical summary: `results/v3_tnoa_trajectory_bridge_summary_v1.json`.

Source workflow: `33950889927`.

Artifact digest: `sha256:a106ea0b20b0ec6b7c9cff79b7d0633606962f8d277f0ac978009388c99c7e59`.

## 1. What changed

The failed 20260906 bridge used local-candidate frame fraction as the sequence target score. The 20260907 generation changed only that implicated target representation, using pre-existing PolliPi shadow trajectory geometry:

`target_score = candidate_fraction × path_efficiency × (1 - reversal_rate)`.

V3 `T=9/K=3`, TNOA semantics, nuisance evidence, `alpha=0.05`, development/heldout calibration logic and all seven promotion gates remained unchanged.

## 2. Trajectory evidence helped the joint architecture

Compared with raw representation, matched V3 achieved:

- safe unique-process coverage: **0.7750 -> 0.8542**;
- contrast: **+0.0792**;
- paired-bootstrap 95% CI: **+0.0500 to +0.1083**;
- pooled false certainty: **0.3125 -> 0.2407**;
- contrast: **-0.0718**;
- paired-bootstrap 95% CI: **-0.1042 to -0.0394**;
- target+nuisance overlap abstention: **0.2969 -> 0.4635**;
- forced unique T/N in true overlap: **0.7031 -> 0.5365**.

Matched V3 also exceeded time-broken V3 in safe unique-process coverage:

- time-broken: **0.7833**;
- matched: **0.8542**;
- difference: **+0.0708**;
- paired-bootstrap 95% CI: **+0.0292 to +0.1125**.

Thus the trajectory revision did what the first bridge diagnosis predicted in one important respect: it recovered more positive target support inside genuine target+nuisance worlds, causing TNOA to retain more explicit overlap U instead of collapsing them to unique N.

## 3. But the frozen joint promotion still failed

Three of seven gates failed:

1. matched-minus-raw safe coverage was `+0.0792`, below the frozen `+0.10` threshold, despite a positive paired interval;
2. matched pooled false certainty was `0.2407`, still above the frozen absolute ceiling `0.10`;
3. target-only final T rate fell from raw `0.8750` to matched V3 `0.2708`, violating the target-retention guardrail.

The scientific promotion status therefore remains:

> **not promoted to a joint V3–TNOA candidate architecture.**

The absolute false-certainty ceiling is not relaxed merely because the direction of improvement is favorable.

## 4. New failure localization: unconditional projection can erase useful target geometry

The target-only trajectory diagnostics reveal why target retention failed.

### Raw target-only

- local-candidate fraction mean: approximately **0.3588**;
- path efficiency mean: approximately **0.8948**;
- reversal rate mean: **0.0000**;
- target score mean: approximately **0.3491**;
- calibrated target threshold: **0.2222**;
- heldout final T rate: **0.8750**.

### Matched-V3 target-only

- local-candidate fraction mean: approximately **0.3472**;
- path efficiency mean: approximately **0.7829**;
- reversal rate mean: approximately **0.0729**;
- target score mean: approximately **0.2753**;
- calibrated target threshold: **0.3333**;
- heldout final T rate: **0.2708**.

The original V3 frame-level target-only recall was only mildly reduced (`0.6583 -> 0.6250`). The much larger sequence-level T loss appears only once trajectory geometry and fixed-risk target calibration are considered.

This indicates a new representation problem:

> **a target-free reference is not automatically an entitled nuisance correction.**

In nuisance-free target-only worlds, the reference contains sensor noise rather than a true shared nuisance process. A rank-3 basis estimated from a short nine-frame noise sequence can nevertheless overlap by chance with some temporal components of the target trajectory. Applying the projection unconditionally can therefore alter target geometry even when there is little nuisance to remove.

This is an **overprojection / representation-entitlement problem**, not evidence that TNOA should loosen its semantics.

## 5. Why this strengthens the V3–TNOA symmetry

The two-layer architecture now exposes a deeper common rule.

TNOA already requires positive support before making a target, nuisance or absence claim.

The trajectory bridge suggests that the upstream representation should obey an analogous rule:

> **Do not apply a nuisance-removal transformation merely because a target-free reference exists; establish that the reference is sufficiently coupled to the nuisance structure relevant to the primary stream.**

Thus V3 itself may require an entitlement gate:

- reference available ≠ relevant nuisance support;
- target-free ≠ safe to subtract;
- explained subspace ≠ nuisance truth;
- quiet residual ≠ absence.

This is not yet a validated new method. It is the failure-localized design implication of the fresh trajectory bridge.

## 6. Current strongest scientific conclusion

Across the two fresh bridge generations:

1. correctly coupled V3 repeatedly increased safe unique-process coverage relative to raw and time-broken controls;
2. adding existing trajectory evidence significantly reduced false certainty and increased explicit target+nuisance overlap abstention;
3. nevertheless, end-to-end promotion failed because absolute false certainty remained too high and unconditional V3 projection substantially reduced target-only decision support.

Therefore the useful result is not “V3 + TNOA is solved.” It is:

> **Representation quality and decision entitlement are distinct. Reference-based nuisance removal can add usable information, but applying the representation without evidence that correction is warranted can itself destroy target evidence. TNOA's fixed-risk abstention layer exposes this failure even when ordinary representation-level accuracy improves.**

## 7. Stop condition for synthetic rescue

Do not immediately add another fitted score or relax the frozen gates.

The current generations have already localized two distinct interfaces:

- target process representation needs multi-frame evidence rather than frame count alone;
- nuisance correction itself needs evidence of relevant coupling before it is applied.

The next method generation, if pursued, should be specified as a new **reference-entitlement / selective-projection** problem on a fresh generation, not as further tuning of the 20260906 or 20260907 heldout results.

A stronger alternative is to carry this architecture into a controlled real experiment where true nuisance-on / nuisance-off blocks and independent target truth make the correction-entitlement question directly testable.

## 8. Claim boundary

Do not claim:

- successful end-to-end V3–TNOA validation;
- false-certainty control at 0.10;
- that trajectory evidence solves all overlap cases;
- that reference availability alone justifies projection;
- field performance or universal domain transfer.

The retained positive findings are paired synthetic contrasts under fresh seeds; the retained adverse findings are equally part of the method result.
