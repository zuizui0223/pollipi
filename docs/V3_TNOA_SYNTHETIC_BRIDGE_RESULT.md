# V3–TNOA fresh synthetic bridge — result

Status: **scientific promotion failed; positive coverage gains and adverse false-certainty result retained. No rescue tuning.**

Canonical machine-readable summary: `results/v3_tnoa_synthetic_bridge_summary_v1.json`.

Source workflow: `33950390877`.

Artifact digest: `sha256:eb949ab961a863df1cbe278bbe716eedc7451c581094d23baa55d3350fd626a2`.

## 1. Question

The fresh bridge asked whether a correctly coupled V3 representation could increase TNOA's safe determinate coverage under the same positive-support false-certainty semantics (`alpha=0.05`) relative to both raw representation and a time-broken V3 control.

The bridge hypothesis was formulated **after** the original V3 result. A fresh master seed (`20260906`) and separate 48-development / 48-heldout split were therefore used.

## 2. Positive result: V3 increased safe unique-process coverage

Heldout safe unique-process coverage was:

- raw: **0.6000**;
- time-broken V3: **0.6667**;
- matched V3: **0.8167**.

Contrasts:

- matched − raw: **+0.2167**;
- paired-bootstrap 95% CI: **+0.2042 to +0.2333**;
- matched − time-broken: **+0.1500**;
- paired-bootstrap 95% CI: **+0.1207 to +0.1792**.

Thus the increase was not reproduced by merely passing an equally sized time-broken reference through the same architecture.

This is a real joint-layer result: after representation-specific thresholds were recalibrated to the same error semantics, correctly coupled V3 made more unique target/nuisance worlds safely resolvable.

## 3. Adverse result: false certainty remained far too high

The frozen joint promotion rule also required matched-V3 pooled false certainty to be at most `0.10` and no more than `0.01` above raw.

Observed heldout pooled false-certainty rates were:

- raw: **0.3333**;
- time-broken V3: **0.3727**;
- matched V3: **0.3194**.

Matched V3 was slightly lower than raw (`−0.0139`; paired-bootstrap 95% CI `−0.0440` to `+0.0139`), but the absolute rate remained far above the frozen `0.10` ceiling.

Therefore:

> **The joint V3–TNOA architecture was not promoted.**

Six of seven frozen criteria passed; the absolute false-certainty gate failed.

## 4. Where the false certainty came from

The failure is not mainly a nuisance-only false-support problem.

For matched V3 on heldout data:

- maximum target false-support across nuisance-only families: **0.0000**;
- nuisance false-support in target-only worlds: **0.0208**.

Those support-level error checks were small.

The dominant problem was **target+nuisance superposition**.

Matched-V3 mixed-world results:

- overlap abstention rate: **0.2865**;
- explicit `target_nuisance_overlap` reason rate: **0.2865**;
- forced unique T/N rate: **0.7135**.

Thus most true T+N worlds received only nuisance support and became unique `N`, which is false certainty under the known synthetic process truth.

By mixed family, matched-V3 target-support / U rates were approximately:

- target + wind: target support `0.083`, U `0.083`;
- target + shadow: target support `0.083`, U `0.083`;
- target + shake: target support `0.438`, U `0.438`;
- target + local sway: target support `0.542`, U `0.542`.

Nuisance support was effectively present throughout these matched-reference mixed worlds. The missing ingredient was therefore sufficient **positive target support** to preserve overlap.

## 5. Why the target interface became conservative

The bridge intentionally recalibrated score thresholds rather than inheriting raw thresholds after representation changes.

Target-support thresholds were:

- raw: **> 1.0**, effectively disabling target support;
- time-broken V3: **0.7778** of sequence frames;
- matched V3: **0.4444** of sequence frames (`4/9`).

The raw target observer had to shut down because the hard nuisance family could mimic its simple frame-fraction score while preserving the development false-support criterion.

Matched V3 made this substantially better, but `4/9` remained demanding. In the earlier frozen V3 generation, target-only **target-frame recall was 0.625**, yet the present bridge's heldout target-only final `T` rate was only **0.0833**.

This distinction is diagnostic:

- local target evidence still exists in the residual representation;
- the sequence-level target adapter used by the bridge does not summarize that evidence efficiently enough under the risk contract.

The present adapter was only:

> fraction of frames called local candidates by the unchanged V1 observer.

It ignores trajectory direction, recurrence structure, reversal, path efficiency and other multi-frame target evidence.

## 6. TNOA exposed a failure that ordinary accuracy could hide

V3 alone had already shown strong frame-level benefits. If the analysis stopped at recall/FPR or balanced utility, the method could look essentially solved.

The TNOA bridge asks a stricter question:

> Does the improved representation justify the biological/process statement being made?

The answer in this generation is:

- **yes**, V3 increases uniquely resolvable target/nuisance coverage;
- **no**, the current target-evidence interface does not yet preserve enough target support in genuine T+N superposition to meet the prefrozen false-certainty ceiling.

This is exactly the value of the two-layer architecture. Representation improvement and decision entitlement are not interchangeable.

## 7. Failure localization

The evidence currently supports the following diagnosis:

### V3 nuisance representation

**Supported as useful.**

Matched reference improved safe unique coverage over both raw and time-broken controls with positive paired-bootstrap intervals.

### TNOA nuisance evidence interface

**Not the principal seam in this generation.**

Heldout target-only nuisance false support was `0.0208`, and nuisance-only worlds were strongly recoverable under matched V3.

### Target evidence interface

**Principal unresolved seam.**

The frame-fraction target score is too lossy for the fixed-alpha contract, especially when target and nuisance coexist.

This maps to a TNOA **representation defect** rather than a reason to redefine T/N/U or relax the false-certainty criterion.

## 8. Next method generation

Do **not** retune the current heldout target threshold or relax the `0.10` promotion ceiling.

The next generation should freeze a new target observer **before a fresh seed is generated**.

The evidence-based candidate is multi-frame local-process representation using observation-safe features such as:

- monotonic or coherent displacement;
- path efficiency;
- reversal / return-to-origin behavior;
- temporal recurrence;
- spatial support continuity;
- reference synchrony versus residual independence.

This follows the earlier V2 diagnosis that compact local sway and traversing local targets require temporal structure rather than single-frame or frame-count reasoning.

The nuisance representation `T=9`, `K=3` and V3 reference method should remain frozen while only the implicated target observer is changed.

## 9. Claim boundary

The safe current conclusion is:

> In a fresh controlled synthetic generation, correctly coupled V3 representation increased TNOA's safely resolvable unique-process coverage relative to both raw and time-broken representations under the same development false-support semantics. However, the joint architecture failed its prefrozen absolute false-certainty gate because the current frame-fraction target observer under-supported targets in genuine target+nuisance superposition. The joint architecture is therefore not yet promoted.

Do not claim:

- successful end-to-end V3–TNOA validation;
- field performance;
- universal false-certainty control;
- biological absence;
- that the failed gate should be removed because coverage improved.
