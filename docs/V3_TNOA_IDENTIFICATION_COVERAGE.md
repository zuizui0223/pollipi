# V3–TNOA resolvable-coverage monotonicity

Status: **structural identification theorem**. This links reference refinement directly to the TNOA idea of safely resolvable coverage without requiring a particular classifier.

## 1. Point-identification indicator

Let `X` be an observation and `theta` a scientific estimand. For world `omega`, define

\[
J_X(\omega)
=
\mathbf 1\left\{
\left|\mathcal I_X(X(\omega))\right|=1
\right\}.
\]

`J_X=1` means the estimand is uniquely determined over all worlds compatible with the retained observation.

For any probability distribution over worlds, define ideal safely resolvable coverage

\[
C_X=P\{J_X=1\}.
\]

This is an identification quantity, not a classifier accuracy.

## 2. Theorem — reference refinement cannot reduce ideal resolvable coverage

Suppose `X2` refines `X1`, meaning every `X2` compatible-world fiber is a subset of the corresponding `X1` fiber. In particular, `(Y,R)` refines `Y`.

Then for every world

\[
\boxed{J_{X2}(\omega)\ge J_{X1}(\omega).}
\]

Consequently, under any distribution over worlds,

\[
\boxed{C_{X2}\ge C_{X1}.}
\]

### Proof

If `J_X1(omega)=1`, then `theta` has one value on the entire coarse compatible set. A refined compatible set is a subset of that set, so `theta` still has that same single value. Cases that were already resolvable remain resolvable; some ambiguous cases may become resolvable. ∎

## 3. Dual theorem — semantic coarsening cannot increase ideal resolvable coverage

If `C=c(E)` is a deterministic coarsening of rich evidence `E`, then `E` refines `C`. Therefore

\[
\boxed{J_E(\omega)\ge J_C(\omega)}
\]

pointwise and

\[
\boxed{C_E\ge C_C.}
\]

Thus reference acquisition and semantic coarsening are exact opposites for ideal identification coverage.

## 4. Why this does not guarantee an implemented V3 system improves measured coverage

The theorem assumes the downstream system has access to the true compatible-set structure induced by the retained information.

An implemented pipeline may violate that ideal because it:

- replaces rich input with a non-injective residual;
- uses a misspecified target observer;
- uses a misspecified nuisance observer;
- forces a point estimate where a set should be retained;
- miscalibrates evidence support;
- confuses overlap with a unique nuisance decision.

Therefore empirical loss of target evidence after V3 does not contradict the theorem. It diagnoses a **representation/observer approximation defect** between the rich information actually retained and the compatible-set geometry represented by the implemented observer.

## 5. Interpretation of the fresh V3–TNOA bridge failures

The fresh bridges showed that matched V3 added usable information but the approximate end-to-end observer still produced excessive false certainty or lost target-only support.

The structural theorem clarifies the diagnosis:

> **The information source can be beneficial while the implemented mapping from that information to supported compatible sets is still inadequate.**

This is precisely why TNOA's distinction between representation defect and information absence matters.

## 6. Set-valued implementation target

The partial-decomposition formulation provides a route closer to the theorem.

Instead of one residual point estimate, retain

\[
\mathcal S(Y,R)=Y-\mathcal N(R).
\]

If reference information contracts `N(R)`, then `S(Y,R)` contracts without deleting previously compatible raw states outside the calibrated nuisance restriction.

A downstream query should become uniquely decidable only when the compatible set itself supports one answer.

## 7. Core sister-method statement

At the ideal identification level:

\[
\boxed{
\text{reference refinement can only preserve/increase resolvable coverage,}
}
\]

while

\[
\boxed{
\text{semantic coarsening can only preserve/decrease resolvable coverage.}
}
\]

This is the cleanest mathematical expression of the V3–TNOA symmetry.
