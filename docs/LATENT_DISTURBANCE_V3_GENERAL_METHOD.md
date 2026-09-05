# V3 latent-disturbance method — application-independent scientific scope

Status: **canonical scientific framing for the V3 method. PolliPi is one validation instrument, not the scope of the method.**

## 1. Core problem

The method addresses a generic visual-observation problem:

> A recorded image sequence contains a **localized target/process signal** mixed with **shared exogenous disturbance**. Can a target-free reference stream reveal the disturbance process well enough to preserve the localized signal without recognizing the target itself?

The target does not have to be a pollinator, insect, flower visit or even a biological object. The current implementation is a method for fixed-interval visual time series with:

- a primary image sequence containing the signal of interest;
- a target-free reference sequence or reference region that is exposed to some of the same nuisance process;
- an independent truth source for evaluating the target/process of interest.

Examples include, but are not limited to:

- animal passage or behavior under vegetation motion, illumination changes or camera vibration;
- phenology or plant-motion observations under wind and moving shadows;
- small-object/event detection in outdoor monitoring;
- laboratory or microscopy sequences with shared vibration/illumination nuisance;
- industrial or environmental imaging where local change is embedded in common-mode disturbance.

These are examples of the measurement structure, not claims of demonstrated performance in each domain.

## 2. Scientific object

Let the observed primary sequence be

`Y(t) = S(t) + N_p(t) + E_p(t)`

where:

- `S(t)` is the localized target/process signal of interest;
- `N_p(t)` is disturbance expressed in the primary view;
- `E_p(t)` is residual measurement noise.

A target-free reference provides

`R(t) = N_r(t) + E_r(t)`.

The method does **not** require `N_p(t)` and `N_r(t)` to be spatially identical. It asks whether they share a low-dimensional temporal driver.

From the reference sequence, V3 estimates a temporal basis `U` by singular-value decomposition. For each primary pixel time series `d`, the reference-explained component is

`d_N = U U^T d`,

and the residual passed to a downstream observer is

`d_residual = d - U U^T d`.

The scientific quantity is therefore not “wind detection”. It is **reference-explained temporal nuisance structure**.

## 3. What makes the method different from target recognition

V3 does not require:

- target identity;
- a target detector;
- target class labels during nuisance estimation;
- pixel correspondence between primary and reference;
- naming the physical nuisance process.

Target labels are used only for independent evaluation. A quiet residual is not biological absence, and a large reference-explained fraction is not proof of any named physical cause.

## 4. Frozen synthetic evidence already obtained

The current PolliPi synthetic implementation is an instrumented test bed for the generic method.

Matched target-free temporal reference versus no reference:

- mixed target-frame recall: `0.436458 -> 0.692708`;
- nuisance false-frame rate: `0.298611 -> 0.027199`;
- local-sway false-frame rate: `1.000000 -> 0.108796`;
- target-episode recall: `0.566667 -> 0.958333`;
- balanced utility: `0.568924 -> 0.832755`.

A time-permuted reference produced intermediate balanced utility `0.730150`. The matched condition exceeded it by `+0.102604`. All six frozen primary promotion criteria passed.

Under one-frame lag and 75% temporal coupling, all ten frozen robustness criteria also passed.

These results support the method as a **simulation candidate**, not as a pollination-specific field result.

## 5. Required validation structure in any application

A valid real-data test requires three logically distinct streams:

1. **Primary stream** — the image sequence containing the target/process and nuisance.
2. **Nuisance-reference stream** — target-free information exposed to some shared exogenous disturbance and used by V3.
3. **Independent target/process truth** — an evaluation source that is never passed to V3.

The third stream need not be biological truth. It can be any independent ground truth appropriate to the application: manual annotation, an independent camera, controlled event schedule, instrumented actuator, known object trajectory, laboratory reference sensor, etc.

## 6. Confirmatory comparison

For any domain, the core comparison should remain:

1. correctly coupled target-free reference;
2. a predeclared time-broken or mismatched reference negative control;
3. no-reference/raw baseline.

A convincing result requires improvement in the target/process estimand and nuisance rejection, while the negative control shows that the benefit depends on genuine coupling rather than merely adding extra data.

## 7. Field/laboratory validation should not be restricted to pollination

PolliPi is convenient because hardware, fixed-interval acquisition, provenance and independent annotation infrastructure already exist. It is **one implementation path only**.

The next empirical validation should be chosen for identifiability and experimental control, not because the repository was originally built for flower visits. A strong first validation could use any scene where:

- the local target/process can be independently established;
- a target-free nuisance reference can be specified prospectively;
- shared disturbance varies enough to create false local evidence;
- matched, time-broken and no-reference conditions can be compared on untouched data.

## 8. Claim boundary

The current evidence supports:

> In controlled synthetic visual sequences, a target-free spatially non-corresponding reference can define a low-dimensional temporal nuisance subspace that improves separation of shared disturbance from a localized target/process before an unchanged downstream observer, and the benefit depends on temporal coupling.

It does not yet support:

- universal performance across imaging domains;
- physical identification of wind, illumination or vibration;
- biological absence;
- field-optimal rank or window length;
- live adaptive control;
- a claim restricted to pollination ecology.

## 9. Paper framing

The paper should therefore be framed as a **general visual measurement / nuisance-separation method**, with PolliPi or another real system serving as a validation platform.

The application question is secondary:

`Can this system detect visits better?`

The methodological question is primary:

> **Can target-free reference information identify shared temporal disturbance strongly enough to recover local signal without target recognition or spatial correspondence?**
