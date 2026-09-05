# V2 oracle-shift failure attribution diagnostic — frozen before execution

Status: **diagnostic only.** No method promotion, classifier tuning, or field action is authorized by this test.

## Purpose

The V2.1 label-free aligner recovers injected shifts almost perfectly for wind, shadow and shake but never for local sway. Yet V2.1 nuisance false-event rates remain high for wind and shake. This diagnostic separates two failure locations:

1. **alignment estimation failure** — the chosen shift is wrong;
2. **post-alignment representation failure** — even the true inverse shift leaves a residual representation that the frozen V1 classifier interprets as local activity.

## Frozen comparison

Use the same `shift2_reference` worlds, master seed `20260905`, 64 replicates per scenario and unchanged V1 `pipeline.analyze()`.

For each replicate compare:

- `exact_reference`: the original event-matched target-free reference before artificial spatial degradation;
- `oracle_shift_reference`: the degraded shift2 reference restored with the known inverse injected shift, then projected with the frozen V2 scalar nuisance loading;
- `estimated_shift_v2_1`: the label-free V2.1 alignment result;
- `shift2_unaligned`: the degraded reference without alignment;
- `no_reference`.

The oracle arm uses injected simulation metadata and is **not** a deployable method. It exists only to localize failure.

## Outcomes

For all conditions report the same target/noise metrics used previously:

- mixed-target recall;
- nuisance-only false-event rate;
- balanced utility;
- target-only recall;
- per-scenario local-candidate rates.

For nuisance-only worlds additionally report residual absolute-energy concentration in a frozen 4-pixel image border after projection:

`border_excess = (border residual-energy fraction) / (border pixel-area fraction)`.

A value substantially above 1 means residual error is concentrated near frame boundaries.

## Interpretation rules

No pass/fail threshold is used. Interpret by nuisance family:

- if `oracle_shift_reference` is clean but `estimated_shift_v2_1` is not, the main failure is shift estimation;
- if both oracle and estimated shift remain noisy, the failure lies in projection/boundary handling or V1 interaction after alignment;
- if `exact_reference` is clean while oracle shift is noisy and border excess is high, the artificial shift/crop operation creates a boundary-information problem that cannot be solved by translation estimation alone.

This diagnostic decides whether the next method should be multi-frame alignment, valid-overlap/boundary-aware projection, or a more flexible spatiotemporal nuisance representation.
