# V3–TNOA trajectory bridge — frozen fresh-generation protocol

Status: **post-failure method revision, frozen before trajectory-bridge outcomes.**

The first fresh V3–TNOA bridge increased safe unique-process coverage but failed the absolute false-certainty gate because the frame-fraction target adapter under-supported targets in genuine target+nuisance superposition.

This generation changes **only the implicated target-evidence representation**. V3, TNOA semantics, nuisance evidence, risk budget and promotion gates remain frozen.

## 1. Failure being addressed

Bridge generation 1 used:

`target_score = fraction of frames classified as local candidates`.

Under `alpha=0.05` family-conditional target-support calibration, matched V3 required target score `>=4/9`. Although frozen V3 target-only frame recall was `0.625`, only `0.0833` of heldout target-only sequences became final T decisions, and most true target+nuisance worlds were forced to unique N.

The failure is therefore localized to the **sequence-level target observer**, not to the V3 nuisance representation or TNOA decision vocabulary.

## 2. Existing observation-safe trajectory representation

PolliPi already contains shadow-only multi-frame trajectory diagnostics that predate this bridge revision:

- `path_efficiency = net displacement / total path length`;
- `mean_step`;
- `reversal_rate` based on negative dot products of consecutive step vectors;
- `track_frames`.

The existing implementation explicitly interprets high path efficiency as a directed traverse and low path efficiency as back-and-forth sway. These features are explainable geometry derived from observed centroids; they do not use target truth or class identity.

This generation reuses that existing representation rather than inventing a post-hoc target-specific feature family.

## 3. Frozen target score

For each 9-frame sequence and representation arm:

1. run the unchanged PolliPi V1 observer on every frame exactly as in bridge generation 1;
2. retain centroids only from frames whose V1 state is `uncertain_local_activity` or `strong_visitation_candidate`;
3. let `candidate_fraction = local_candidate_frames / 9`;
4. if fewer than two local-candidate centroids exist, set trajectory target score to `0`;
5. otherwise compute the existing shadow trajectory features over the retained centroid sequence;
6. define:

`trajectory_target_score = candidate_fraction * path_efficiency * (1 - reversal_rate)`.

All three factors are in `[0,1]`; no fitted weights are introduced.

The score rewards repeated local evidence with a directed non-reversing trajectory. It does not use target-frame truth, scenario identity, nuisance family, target location or TNOA outcome.

## 4. Frozen components retained from bridge generation 1

Unchanged:

- V3 sequence length `T=9`;
- V3 temporal rank `K=3`;
- raw, matched V3 and time-broken V3 representation arms;
- raw nuisance score = V1 environmental-noise frame fraction;
- V3 nuisance score = reference-explained primary energy fraction;
- TNOA pinned decision API at `zuizui0223/tnoa@40fa8f66132cd86bdd5294b7360e024d13f9d9c4`;
- `deviation_observed=True` and `observable=True` for all dynamic synthetic windows;
- no coupled-response or absence channel;
- support calibration semantics `alpha=0.05`;
- target support calibrated against every nuisance-only family;
- nuisance support calibrated against target-only worlds;
- same TNOA latent-entitlement truth definitions;
- same primary metrics;
- same paired-bootstrap structure;
- same seven scientific promotion gates.

No threshold from the failed bridge is reused numerically; the score representation changed, so each arm is recalibrated on development data to the same error semantics.

## 5. Fresh generation

Use a new untouched synthetic generation:

- master seed: `20260907`;
- replicates per scenario: `96`;
- development replicates: `0..47`;
- heldout replicates: `48..95`;
- paired-bootstrap resamples: `5,000`;
- bootstrap seed: `2026090701`.

The failed `20260906` bridge worlds are not used for target-score threshold selection or heldout scoring in this generation.

## 6. Frozen promotion rule

Use exactly the same gates as bridge generation 1:

1. matched V3 safe unique-process coverage exceeds raw by at least `0.10`;
2. paired-bootstrap 95% lower bound for matched minus raw safe coverage is `>0`;
3. matched V3 safe unique-process coverage exceeds time-broken V3 by at least `0.05`;
4. paired-bootstrap 95% lower bound for matched minus time-broken safe coverage is `>0`;
5. matched V3 pooled false-certainty rate is `<=0.10` and no more than `0.01` above raw;
6. matched V3 target-only T rate is no more than `0.05` below raw;
7. matched V3 forced-unique T/N rate in target+nuisance worlds is no more than `0.05` above raw.

Scientific promotion remains separate from CI success.

## 7. Interpretation

A positive result would support a stronger two-layer claim:

> A correctly coupled nuisance representation plus an observation-safe multi-frame target representation can increase TNOA safe decision coverage under fixed error semantics while preserving genuine target+nuisance superposition.

A negative result will be retained. In particular, the false-certainty ceiling will not be relaxed and the 20260906 heldout generation will not be rescored with the new target observer as confirmatory evidence.
