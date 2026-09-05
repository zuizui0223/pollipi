# V3 temporal-coupling robustness result

Status: **positive; all 10 frozen robustness criteria passed. V3 is promoted to a temporally robust simulation candidate.**

Protocol: `docs/LATENT_DISTURBANCE_V3_TEMPORAL_ROBUSTNESS.md`.

GitHub Actions run: `33937674461`.

Artifact: `latent-disturbance-v3-temporal-robustness-result` (`9960746398`).

Artifact digest: `sha256:d6fee8e0cb669a1ee186b3eb933972e87a0e97b4ffc689e25560f5d300255554`.

## Main result

The promoted V3 rank-3 temporal nuisance subspace was re-tested without changing sequence length, rank, target path, nuisance amplitudes or the downstream PolliPi V1 classifier.

| Metric | Matched | 1-frame lag | 75% temporal coupling | No reference |
|---|---:|---:|---:|---:|
| Mixed target frame recall | 0.692708 | 0.653125 | 0.637500 | 0.436458 |
| Target-only frame recall | 0.625000 | 0.654167 | 0.658333 | 0.658333 |
| Nuisance false-frame rate | 0.027199 | 0.084491 | 0.070023 | 0.298611 |
| Local-sway false-frame rate | 0.108796 | 0.247685 | 0.266204 | 1.000000 |
| Broad-nuisance false-frame rate | 0.000000 | 0.030093 | 0.004630 | 0.064815 |
| Target episode recall | 0.958333 | 0.954167 | 0.891667 | 0.566667 |
| Nuisance false-episode rate | 0.041667 | 0.067708 | 0.104167 | 0.250000 |
| Balanced utility | 0.832755 | 0.784317 | 0.783738 | 0.568924 |

## Frozen criteria

All ten prespecified criteria passed.

### One-frame lag

- balanced-utility gain vs no reference: `+0.215394` (required `>=0.08`);
- nuisance false-frame reduction: `0.214120` (required `>=0.08`);
- target-only recall loss: `0.004167` (allowed `<=0.06`);
- local-sway false-frame reduction: `0.752315` (required `>=0.25`);
- broad-nuisance FPR difference vs no reference: `-0.034722` (allowed `<=+0.05`).

### 75% temporal coupling

- balanced-utility gain vs no reference: `+0.214815` (required `>=0.10`);
- nuisance false-frame reduction: `0.228588` (required `>=0.10`);
- target-only recall loss: `0.000000` (allowed `<=0.06`);
- local-sway false-frame reduction: `0.733796` (required `>=0.25`);
- broad-nuisance FPR difference vs no reference: `-0.060185` (allowed `<=+0.05`).

## Interpretation

The main V3 result is therefore not restricted to a perfectly synchronized synthetic reference. A one-frame temporal mismatch reduces performance relative to the fully matched reference, as expected, but the reference remains strongly informative relative to no reference. Likewise, retaining only 75% event-matched temporal structure still preserves substantial target recovery and nuisance rejection.

The result supports the method-level statement:

> **The useful reference signal is a shared temporal disturbance structure rather than pixel correspondence, and in these controlled sequences that structure remains useful under modest timing and coupling degradation.**

This is the point at which additional synthetic tuning should stop. The next test should move domains: real fixed-interval multi-frame imagery with a prospectively defined target-free reference stream or region, independent biological labels, and the V3 representation evaluated in shadow mode only.

## Hard boundary

Do not claim:

- tolerance to arbitrary timing drift, dropped frames or asynchronous cameras;
- physical wind identification;
- field accuracy;
- biological absence when reference-explained energy is high;
- that rank `K=3` is field-optimal;
- live adaptive-capture readiness.

The appropriate next evidence is a real-data shadow audit, not further synthetic parameter search.