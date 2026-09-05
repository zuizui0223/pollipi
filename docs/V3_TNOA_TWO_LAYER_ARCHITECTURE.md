# V3–TNOA two-layer architecture

Status: **cross-method scientific architecture. This document adds no new field-performance claim.**

## 1. Core principle

The shared methodological principle is:

> **Ambiguity should be decomposed at the layer where it arises, and unresolved evidence should remain unresolved rather than being collapsed into a convenient binary label.**

V3 and TNOA act at different layers of the observation chain.

- **V3** addresses **representation ambiguity** in the recorded signal: how much of a local visual change is explainable by a shared exogenous temporal process represented in a target-free reference?
- **TNOA** addresses **decision entitlement** after evidence has been represented: what positive target, nuisance and observability evidence exists, and does it justify a unique decision?

The methods are therefore complementary rather than redundant.

## 2. Layer 1 — V3: signal-space decomposition

Let the primary image sequence be

\[
Y(t)=S(t)+N_p(t)+E_p(t),
\]

where `S` is the local target/process signal, `N_p` is nuisance expressed in the primary stream and `E_p` is residual measurement noise.

A target-free reference supplies

\[
R(t)=N_r(t)+E_r(t).
\]

V3 estimates a low-dimensional temporal basis `U` from `R` and decomposes each primary pixel time series `d` into

\[
d_{N}=UU^Td,
\]

and

\[
d_{residual}=d-UU^Td.
\]

The V3 output is therefore a **representation decomposition**:

1. a reference-explained component;
2. a residual component;
3. diagnostics describing how much of the primary temporal energy is explained by the reference representation.

V3 does **not** establish that the explained component is physically `wind`, `shadow`, `vibration` or any other named cause. It also does not establish that the residual is biological truth.

In particular:

\[
\boxed{d_{residual} \neq S_{truth}}
\]

and

\[
\boxed{\text{low explained nuisance} \not\Rightarrow \text{no nuisance}}.
\]

## 3. Layer 2 — TNOA: evidence-space decomposition

TNOA receives represented evidence and keeps epistemically distinct channels separate:

\[
(T,C,N,O,A^-).
\]

Its final vocabulary remains

\[
B+\{T,N,U\}.
\]

TNOA does not define nuisance as `1-T`, observability as `1-N`, or target absence as low target evidence. Target and nuisance evidence may both be positive, and unresolved attribution remains `U` when no unique decision is justified.

Thus the two layers have parallel non-complementary rules:

- V3: reference-explained component and residual are **not complements with biological semantics**;
- TNOA: target, nuisance, observability and absence evidence are **not complements with decision semantics**.

## 4. Interface contract

A valid V3 → TNOA implementation must preserve the following boundaries.

### 4.1 Residual stream → target observer

The V3 residual may be supplied to a target observer as a representation intended to reduce shared nuisance burden.

This does not certify target presence. The target observer still produces positive target evidence `T`, not truth.

### 4.2 Reference-explained component → candidate nuisance evidence

V3's explained-energy fraction or related diagnostics may be inputs to a nuisance observer only after independent calibration.

They must **not** be copied directly into `N_supported=true` merely because the reference explains substantial variance.

A V3 quantity answers:

> how much temporal structure is represented by the target-free reference?

A TNOA nuisance decision answers:

> is there sufficient positive evidence for an exogenous process that changes the observation problem?

Those are related but not identical questions.

### 4.3 Quiet residual ≠ target absence

A quiet V3 residual must never manufacture `A-`.

\[
\boxed{\text{quiet residual} \not\Rightarrow A^-}
\]

Certified absence still requires its own independently validated channel.

### 4.4 V3 failure does not force a semantic label

If matched reference fails to improve representation, the case may reflect:

- a representation defect;
- weak or mismatched reference coupling;
- genuine information absence;
- target+nuisance superposition outside the current representation family.

TNOA may therefore retain `U`; V3 failure is not automatically evidence for `T`, `N` or baseline.

### 4.5 Observability remains separate

V3 is not an observability certificate. `O` must still evaluate whether the primary channel preserved enough spatial, photometric and temporal support for the requested inference.

## 5. Mapping to the TNOA contradiction taxonomy

The V3 development history already maps naturally onto TNOA's four contradiction classes.

### Representation defect

V2 exact-reference subtraction worked under ideal correspondence but failed under spatial mismatch. The information existed, but the representation was inadequate. V3 changed the representation from pixel correspondence to shared temporal subspace.

### Information absence / unsupported information status

If neither primary nor target-free reference contains information capable of distinguishing target/process signal from nuisance, the correct result is unresolved rather than forced recovery.

### Process coupling / superposition

A real target/process and nuisance may coexist. V3 may reduce a shared component while leaving genuine overlap. TNOA must preserve that possibility instead of interpreting the residual as a pure target state.

### Definition defect

If a downstream rule equates low residual activity with absence or high explained variance with named nuisance truth, the error is semantic/definitional rather than a reason to retune V3.

## 6. Empirical evidence already available

The current synthetic V3 generation supports Layer 1 as a candidate representation:

- mixed target-frame recall: `0.436458 -> 0.692708` for raw/no-reference → matched temporal reference;
- nuisance false-frame rate: `0.298611 -> 0.027199`;
- local-sway false-frame rate: `1.000000 -> 0.108796`;
- balanced utility: `0.568924 -> 0.832755`;
- time-permuted reference balanced utility: `0.730150`;
- all six prefrozen primary promotion criteria passed;
- all ten prefrozen one-frame-lag / 75%-coupling robustness criteria passed.

This supports temporal coupling as useful information in controlled synthetic visual worlds. It does not yet validate the full V3 → TNOA architecture on real held-out data.

## 7. Stronger joint hypothesis

The most informative next hypothesis is not merely that V3 increases raw classification accuracy.

TNOA already defines a risk-controlled operating principle:

\[
\text{choose tolerated false certainty }\alpha,\text{ then measure safely resolvable coverage}.
\]

The joint architecture therefore predicts:

> **At the same prefrozen false-certainty budget `alpha`, adding a correctly coupled V3 representation before TNOA should increase safely resolvable coverage compared with a raw/no-reference representation, while a time-broken or mismatched reference should not reproduce the same gain.**

A generic primary joint estimand is

\[
\Delta C_{\alpha}
=
C_{\alpha}(\text{matched V3} \rightarrow \text{TNOA})
-
C_{\alpha}(\text{raw} \rightarrow \text{TNOA}).
\]

The negative-control contrast is

\[
\Delta C_{coupling}
=
C_{\alpha}(\text{matched V3} \rightarrow \text{TNOA})
-
C_{\alpha}(\text{time-broken V3} \rightarrow \text{TNOA}).
\]

A positive method result requires both:

1. false-certainty risk remains inside the same frozen contract;
2. safely resolvable coverage increases specifically when the nuisance reference is correctly coupled.

This turns the two-layer idea into a falsifiable measurement claim rather than a conceptual analogy.

## 8. Joint real-data validation structure

Any application can test the architecture using three independent streams:

1. **primary visual sequence** — target/process plus nuisance;
2. **target-free nuisance reference** — V3 algorithm input;
3. **independent target/process truth** — evaluation only.

The confirmatory comparison should freeze:

- raw/no-reference → TNOA;
- matched V3 → TNOA;
- time-broken/mismatched V3 → TNOA;
- the same false-certainty budget `alpha`;
- the same held-out block definition and uncertainty procedure.

Recommended primary outcome:

- safely resolvable coverage at fixed `alpha`.

Recommended guardrails:

- target false certainty;
- nuisance false certainty;
- unresolved fraction and its reason decomposition;
- target/process estimand error;
- reference contamination / coupling quality.

## 9. Paper architecture

The strongest long-term framing is a two-layer observation architecture:

```text
world / process
    ↓
primary signal + shared exogenous disturbance
    ↓
[V3: representation decomposition]
reference-explained nuisance structure + residual signal
    ↓
independent evidence channels T / C / N / O / optional A-
    ↓
[TNOA: decision entitlement]
B / T / N / U
    ↓
ecology / monitoring / downstream decision
```

The conceptual symmetry is:

> **V3 decomposes ambiguity in signal representation; TNOA decomposes ambiguity in inferential entitlement.**

The shared principle is stronger than either slogan alone:

> **decompose what can be supported, preserve what cannot yet be resolved, and never manufacture a negative conclusion from missing positive evidence.**

## 10. Claim boundary

Current evidence supports V3 only as a synthetic temporal-reference candidate and TNOA as a closed-world process-preserving sensing architecture.

Do not yet claim:

- that V3 + TNOA improves real ecological inference;
- universal performance across imaging domains;
- physical identification of nuisance sources;
- certified target absence from a residual stream;
- statistical independence between V3-derived and other evidence channels;
- live adaptive-control readiness.

Those require prospectively frozen real held-out validation.