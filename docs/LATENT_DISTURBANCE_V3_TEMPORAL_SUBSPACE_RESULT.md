# V3 temporal nuisance-subspace result

Status: **positive simulation result; promoted to temporal-reference candidate under all six frozen criteria.**

Protocol: `docs/LATENT_DISTURBANCE_V3_TEMPORAL_SUBSPACE.md`.

GitHub Actions run: `33935214319`.

Artifact: `latent-disturbance-v3-temporal-subspace-result` (`9959942782`).

Artifact digest: `sha256:10c5c679a73f08d9289fb633addc9129c4b71e1c74167d55999e7e657f613cb5`.

## Main comparison

The downstream observer was the unchanged PolliPi V1 `pipeline.analyze()` classifier. The only change was whether a target-free reference sequence supplied a rank-3 temporal nuisance subspace before V1.

| Metric | Matched temporal reference | Time-permuted reference | No reference |
|---|---:|---:|---:|
| Mixed target frame recall | 0.692708 | 0.591667 | 0.436458 |
| Nuisance false-frame rate | 0.027199 | 0.131366 | 0.298611 |
| Local-sway false-frame rate | 0.108796 | 0.412037 | 1.000000 |
| Broad-nuisance false-frame rate | 0.000000 | 0.037809 | 0.064815 |
| Target episode recall | 0.958333 | 0.904167 | 0.566667 |
| Nuisance false-episode rate | 0.041667 | 0.177083 | 0.250000 |
| Target-only frame recall | 0.625000 | 0.645833 | 0.658333 |
| Balanced utility | 0.832755 | 0.730150 | 0.568924 |

## Frozen promotion criteria

All six prespecified criteria passed.

1. Mixed-target recall gain vs no reference: `+0.256250` (required `>=0.15`) — **pass**.
2. Nuisance false-frame reduction vs no reference: `0.271412` (required `>=0.10`) — **pass**.
3. Balanced-utility gain vs time-permuted reference: `+0.102604` (required `>=0.10`) — **pass**.
4. Target-only recall loss vs no reference: `0.033333` (allowed `<=0.05`) — **pass**.
5. Local-sway false-frame reduction vs no reference: `0.891204` (required `>=0.30`) — **pass**.
6. Broad-nuisance false-frame rate: `0.000000`, below the no-reference value `0.064815` and therefore within the allowed `+0.05` bound — **pass**.

The third criterion is the narrowest margin: matched temporal coupling exceeds the time-permuted control by only `0.102604` in balanced utility against a frozen `0.10` threshold. This motivates a separate, frozen temporal-coupling robustness test rather than post-result tuning of rank, sequence length, nuisance amplitudes, target path or V1 thresholds.

## Scenario-level interpretation

Matched temporal reference completely removed V1 local-candidate frames for the three broad nuisance-only scenarios (`wind_only`, `shadow_only`, `shake_only`) in this synthetic benchmark. It also reduced the difficult `local_sway_only` false-frame rate from `1.000000` without reference to `0.108796` despite the reference nuisance occupying a different image location.

For mixed target+nuisance sequences, matched-reference target-frame recall was:

- target + wind: `0.670833`;
- target + shadow: `0.637500`;
- target + shake: `0.716667`;
- target + local sway: `0.745833`.

The temporal representation therefore recovered signal in the exact failure classes that defeated the single-pair V2/V2.1 spatial subtraction family.

## Scientific conclusion

> **In controlled synthetic sequences, a target-free reference can supply a spatially non-corresponding low-dimensional temporal nuisance representation that improves separation of shared disturbance from a traversing local target before an unchanged downstream observer. The advantage is partly dependent on correct temporal coupling, because time permutation weakens both nuisance rejection and target recovery.**

This is materially stronger than the V2 result because the reference carrier can be at a different image location and can have different spatial structure. The useful information is the shared temporal process rather than pixel correspondence.

## Hard boundary

This remains simulation-only. Do not claim:

- physical wind identification;
- field accuracy;
- biological absence from a low residual;
- that rank `K=3` is field-optimal;
- deep-learning superiority;
- live adaptive-capture readiness.

The result justifies a robustness test for imperfect temporal coupling and, if that survives, a fixed-interval multi-frame field shadow audit.