# V2 oracle-shift failure attribution result

Status: **diagnostic complete. The V2 failure separates into two different mechanisms.**

Source workflow: `33934738580`.

Artifact id: `9959794143`.

Artifact digest: `sha256:72405bad72418db5b31e422ab7be0cadb2125db03eda75dd619c7428d3938276`.

Result JSON SHA-256: `1d2ed5d1626ba454e3ea5ae127bce9ff4626e9de950bc4601c5fdca402ad8550`.

## Aggregate comparison

| condition | mixed-target recall | nuisance false-event rate | balanced utility |
| --- | ---: | ---: | ---: |
| exact event-matched reference | **1.0000** | **0.0000** | **1.0000** |
| oracle inverse shift | 0.8906 | 0.2344 | 0.8281 |
| estimated V2.1 shift | 0.8711 | 0.3906 | 0.7402 |
| shifted reference, unaligned | 0.6914 | 0.3047 | 0.6934 |
| no reference | 0.2969 | 0.2383 | 0.5293 |

The oracle shift improves the shifted-reference representation substantially but does **not** reproduce the exact-reference result. Therefore spatial alignment is necessary but not sufficient.

## Nuisance-specific localization

### Local sway — alignment/identifiability seam

Nuisance-only local-candidate rates:

- exact reference: `0.0000`;
- oracle shift: `0.0000`;
- estimated V2.1 shift: `0.6250`;
- unaligned shift: `0.6563`;
- no reference: `0.9531`.

The separate shift-identifiability diagnostic found exact shift recovery `0/128` for local sway. Because oracle alignment removes the false local signal while the estimated alignment does not, the local-sway failure is primarily a **single-pair identifiability problem**. A compact swaying nuisance is too target-like in one frame pair.

Next representation: multi-frame temporal nuisance evidence (reversal, recurrence, path efficiency, reference synchrony), not more single-pair trimming.

### Wind and shake — post-alignment support seam

Under oracle alignment:

- wind nuisance false-local rate = `0.4375`;
- shake nuisance false-local rate = `0.5000`.

Yet their injected shifts are recovered almost perfectly by the V2.1 objective (`99.2%` wind, `100%` shake). Therefore shift estimation is not the principal explanation for these false events.

Oracle residual energy is disproportionately concentrated at the fixed 4-pixel image border:

- wind border excess = `2.961x`;
- shake border excess = `2.626x`.

The exact unshifted reference produces zero residual and zero nuisance false events. This supports a **support/boundary-information failure**: translating a finite target-free reference loses/perturbs information at the frame edges, and pixelwise projection turns those unsupported regions into structured residuals that V1 may interpret as local motion.

Next representation: valid-support/boundary-aware or low-rank nuisance fields; do not tune V1 thresholds to hide the artefact.

### Shadow

Oracle shift remains clean (`0.0000` false-local rate) despite some border residual concentration. Thus border concentration is not by itself sufficient for a false event; interaction between the nuisance geometry and downstream spatial features matters.

## Revised V2 architecture

The data no longer support one universal single-pair subtraction rule. The next method should be explicitly two-layer:

1. **broad/shared nuisance layer** — estimate global/shared disturbance while preserving valid spatial support rather than forcing exact pixel subtraction across unsupported borders;
2. **local/target-like nuisance layer** — use multi-frame temporal evidence to distinguish recurrent/oscillatory nuisance from a traversing biological target.

Both layers should output residual uncertainty rather than force a target/no-target label.

This is closer to the original research goal than the initial V2 scalar subtraction: infer latent nuisance structure before biological interpretation, and retain what cannot be separated as uncertainty.

## Field boundary

V2/V2.1 is **not** promoted to real field shadow collection as a finished correction method. The branch is valuable as a complete mechanism/failure study and should be merged as research evidence before starting the next method generation.
