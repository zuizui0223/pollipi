# V14c cross-repository interface claim boundary

PolliPi PR #59 exports existing PolliPi decision states as **ordinal target evidence** only.

That adapter must not be conflated with the frozen InsePi V14b closed-world target rule.

## PolliPi contract

- `no_activity` -> 0.0 target evidence;
- `environmental_noise` -> 0.0 target evidence;
- `uncertain_local_activity` -> 0.5 target evidence;
- `strong_visitation_candidate` -> 1.0 target evidence.

The scale is ordinal, not a calibrated probability. It does not certify a visit, nuisance truth, observability, or biological absence.

## InsePi V14b closed-world rule is different

The V14b synthetic target observer uses the structural rule:

`direct_target_signal_fraction > 0 -> target_supported`.

That rule is a property of the synthetic closed-world generator/observer pair. It is **not** the operational rule for PolliPi, and the V14b Pi3=0 versus Pi3>0 phase boundary must not be interpreted as a PolliPi field threshold.

Therefore:

- PolliPi's 0.5 and 1.0 ordinal levels are not Pi3 amplitudes;
- PolliPi's 0.0 does not prove target absence;
- `environmental_noise` does not become nuisance truth;
- the V14b result that positive Pi3 levels share a decision surface is not evidence that real PolliPi target strength above zero is irrelevant.

The intended connection is architectural only:

`PolliPi -> target-evidence channel`

`InsePi -> independent nuisance / observability / attribution logic`.

Empirical mapping from PolliPi outputs or raw camera measurements into a dimensionless phase coordinate belongs to a later validation generation and requires its own calibration/measurement contract.
