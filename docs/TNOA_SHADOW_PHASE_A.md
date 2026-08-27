# TNOA Phase A on Raspberry Pi — shadow-only evidence contract

## Purpose

This phase adds process-preserving evidence logging to the existing PolliPi capture loop **without changing capture timing or licensing any field accuracy claim**.

Every low-resolution probe now produces a separate per-run file:

```text
tnoa_observation_v1_<run_id>.csv
```

The existing `adaptive_probe_shadow_v2_<run_id>.csv`, scheduled high-resolution record, candidate evidence pairs, video logic, policy profiles and three-gate live-adaptive protection remain separate and unchanged in meaning.

## Evidence written on each probe

### T — direct target evidence

T is the existing PolliPi ordinal target-evidence adapter:

```text
no_activity                  -> 0.0
environmental_noise          -> 0.0
uncertain_local_activity     -> 0.5
strong_visitation_candidate  -> 1.0
```

It remains ordinal evidence, not a calibrated probability and not confirmed visitation.

### N — nuisance diagnostics

Phase A records raw positive-nuisance candidate features from the mesh representation:

- `global_synchrony`;
- `estimated_global_shift`;
- `active_cell_proportion`;
- `largest_component_cells`;
- `spatial_concentration`.

No field nuisance threshold is frozen yet. In particular, PolliPi `environmental_noise` is **not** copied into `N_supported=true`.

### O — observability diagnostics

From the actual YUV420 probe, Phase A records:

- luminance mean and standard deviation;
- near-black and near-saturated fractions;
- a lightweight spatial-gradient magnitude;
- expected and measured probe interval and their absolute error;
- frame availability.

ROI/flower-zone support is explicitly unavailable in this first phase. These values are raw measurement diagnostics, not calibrated observability support.

### C — target-coupled response

Unavailable in Phase A. PolliPi direct target evidence is not reused as a second response channel.

### A- — target-absence evidence

Unavailable. Low T, good O, quiet background or environmental-noise classification never creates biological absence evidence.

## Fail-closed observation state

Until field calibration is preregistered/frozen, every Phase-A record is intentionally:

```text
calibration_status = unavailable
observation_state  = U
u_reason           = field_calibration_pending
would_be_action    = observe_only
action_applied     = false
```

The first probe uses `u_reason=reference_frame_pending` because the pairwise PolliPi decision has no previous frame yet.

This is deliberate. Phase A is for collecting the evidence needed to calibrate T/N/O/C and compare it with manual truth; it cannot silently promote synthetic/development thresholds into live field decisions.

## Join keys

The TNOA log carries:

- `run_id` and probe timestamp;
- device identity;
- PolliPi decision state/reason;
- saved still filename or video filename where applicable;
- candidate evidence-event filenames;
- policy profile and simulation provenance.

This lets the TNOA record be joined to the existing probe log, scheduled high-resolution images and candidate evidence pairs without modifying those contracts.

## Capture boundary

`tnoa_shadow.py` has no camera-control API. The Pi still obeys the existing PolliPi policy and the existing three-gate live-adaptive guard. TNOA Phase A does not shorten intervals, trigger videos or certify visits/absences.

## Next gate

Before any TNOA evidence can control capture or produce field-supported B/T/N/U states:

1. collect fixed-interval field sequences and manual labels;
2. define independent truth/annotation for target, nuisance and observability;
3. freeze target and nuisance operational error criteria and O rules;
4. replay the same records under fixed, any-motion, existing classified-adaptive and candidate TNOA policies;
5. only then consider a canary profile with live actions behind the existing device/profile/session gates.
