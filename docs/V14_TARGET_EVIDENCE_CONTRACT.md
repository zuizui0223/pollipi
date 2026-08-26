# V14 target-evidence contract

PolliPi's mesh state is **target evidence**, not a confirmed insect visit and not a measurement of nuisance truth.

For the V14 cross-observer model, the existing four states are exported through a deliberately ordinal reference scale:

| PolliPi state | V14 target-evidence score | Interpretation |
|---|---:|---|
| `no_activity` | 0.0 | no retained target evidence |
| `environmental_noise` | 0.0 | PolliPi rejected the motion as target evidence; nuisance truth is not asserted |
| `uncertain_local_activity` | 0.5 | intermediate target evidence |
| `strong_visitation_candidate` | 1.0 | strong target candidate, still not confirmed visitation |

The numeric values are not calibrated probabilities. They exist only to provide a portable monotone interface for the target axis in the V14 target–nuisance–observability model.

## Separation contract

PolliPi must not export any of the following as part of this adapter:

- nuisance source truth;
- false-event/missed-event/attribution risk;
- observation availability or unobservability;
- confirmed visit truth.

Those quantities are deliberately assessed elsewhere so that contradictions between biological evidence and observation-process evidence remain visible.

A future visit-validation generation must evaluate PolliPi evidence against independent insect/visit truth conditional on independently assessed observation support.
