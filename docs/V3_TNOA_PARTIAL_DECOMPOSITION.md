# V3–TNOA partial-decomposition theory

Status: **mathematical companion**. This replaces the idea that the generic method must estimate one corrected image with a stronger set-valued formulation that preserves reference uncertainty.

## 1. From point correction to partial decomposition

Let the primary observation satisfy

\[
Y=S+N,
\]

where `S` is the local target/process contribution and `N` the nuisance contribution.

Suppose the target-free reference does not identify one exact nuisance realization. Instead it yields a compatible nuisance set

\[
\mathcal N(R)\subseteq\mathcal H.
\]

Define the compatible target/process set

\[
\boxed{
\mathcal S(Y,R)=Y-\mathcal N(R)
=\{Y-n:n\in\mathcal N(R)\}.
}
\]

This is the natural reference-guided partial-identification object. A point V3 correction is only one optional selection from this set.

## 2. Proposition — coverage transfers exactly through additive decomposition

If the true nuisance satisfies

\[
N\in\mathcal N(R),
\]

then, because `S=Y-N`, necessarily

\[
\boxed{S\in\mathcal S(Y,R).}
\]

Therefore, for a random reference-derived set with coverage

\[
P\{N\in\mathcal N_\alpha(R)\}\ge 1-\alpha_R,
\]

we immediately obtain

\[
\boxed{
P\{S\in\mathcal S_\alpha(Y,R)\}\ge 1-\alpha_R.
}
\]

No additional approximation is introduced by the set transformation when `Y` is treated as exactly observed.

### Interpretation

A calibrated nuisance uncertainty set induces a calibrated target uncertainty set automatically. This is a more direct representation-entitlement contract than deciding whether one point subtraction is “safe.”

## 3. Proposition — identified-set diameter equals nuisance-set diameter

For any norm-induced metric, the map

\[
n\mapsto Y-n
\]

is an isometry. Hence

\[
\boxed{
\operatorname{diam}\mathcal S(Y,R)
=
\operatorname{diam}\mathcal N(R).
}
\]

Thus in the exact additive model, uncertainty in the target decomposition is exactly the remaining uncertainty in nuisance contribution.

If a reference refines the nuisance set from `N0` to `N(R)` with

\[
\mathcal N(R)\subseteq\mathcal N_0,
\]

then

\[
\mathcal S(Y,R)\subseteq\mathcal S_0(Y)
\]

and

\[
\operatorname{diam}\mathcal S(Y,R)
\le
\operatorname{diam}\mathcal S_0(Y).
\]

Strict nuisance-set contraction gives strict target-set contraction whenever the diameter decreases.

## 4. Exact-reference and no-reference limits

### Exact nuisance reference

If

\[
\mathcal N(R)=\{N\},
\]

then

\[
\mathcal S(Y,R)=\{Y-N\}=\{S\},
\]

so target contribution is point identified.

### Uninformative reference

If

\[
\mathcal N(R)=\mathcal N_0,
\]

then the reference provides no contraction and target identification is unchanged.

The theory therefore measures reference value by **identified-set contraction**, not by whether a particular correction score improves.

## 5. Corollary with primary-measurement uncertainty

If primary observation itself is only known to lie in a set `Yset` and nuisance lies in `Nset`, define

\[
\mathcal S=\{y-n:y\in\mathcal Y,\;n\in\mathcal N\}.
\]

If

\[
P(Y\in\mathcal Y)\ge1-\alpha_Y
\]

and

\[
P(N\in\mathcal N)\ge1-\alpha_N,
\]

then by the union bound

\[
\boxed{
P(S\in\mathcal S)\ge1-(\alpha_Y+\alpha_N).
}
\]

Moreover

\[
\operatorname{diam}(\mathcal S)
\le
\operatorname{diam}(\mathcal Y)+\operatorname{diam}(\mathcal N).
\]

This links naturally to TNOA observability `O`: uncertainty in the primary measurement and uncertainty in nuisance attribution are different sources and should remain separate.

## 6. Relation to projection V3

The current temporal-subspace V3 produces a point decomposition

\[
\hat N=PY,\qquad \hat S=(I-P)Y.
\]

The set-valued theory shows that this point pair should be viewed as a summary, not the generic epistemic object.

A future implementation may construct a nuisance set around the reference-derived subspace, for example from:

- finite-sample subspace uncertainty;
- reference contamination uncertainty;
- coupling uncertainty;
- lag/alignment uncertainty;
- multiple admissible nuisance ranks or components fixed before heldout evaluation.

The scientific output can then preserve the resulting `Sset` rather than collapsing it to one corrected sequence.

## 7. TNOA interface

Let `Q(S)` be a target/process property queried downstream.

The set-valued representation enables three qualitatively different situations:

1. **robust positive support:** the calibrated target evidence condition is supported across all or a predeclared sufficient subset of compatible `S`;
2. **robust nuisance explanation / lack of target support:** target support is not established, but this still does not create biological absence evidence;
3. **representation ambiguity:** compatible `S` values support different process interpretations, so the representation layer itself remains unresolved.

Case 3 should propagate to TNOA as unresolved evidence rather than being forced into one corrected image and one semantic label.

TNOA then adds a second layer of uncertainty for target/nuisance coexistence, observability and semantic attribution.

## 8. Stronger sister-method symmetry

TNOA already treats an estimand as partially identified when retained semantic evidence does not justify a point conclusion.

The V3 sister method can now do the same **before semantics**:

\[
\boxed{
\text{reference uncertainty}
\to
\text{nuisance compatible set}
\to
\text{target compatible set}
\to
\text{TNOA evidence}
\to
\text{decision or U}.
}
\]

Thus the two layers are not merely both “uncertainty-aware.” They both use the same mathematical strategy:

> **retain the compatible set until independent information justifies contraction.**

## 9. What this solves without real data

Under the additive/set assumptions, the following are exact:

- reference refinement contracts nuisance-compatible sets only when it adds information;
- target-compatible sets contract by the same translated set geometry;
- nuisance-set coverage transfers to target-set coverage;
- point identification occurs only when nuisance uncertainty collapses sufficiently;
- forcing one nuisance realization is not mathematically required.

Real data are needed to determine how narrow and well-calibrated `N(R)` can be for a physical reference—not to establish the set-propagation mathematics.

## 10. Revised conceptual claim

The V3 line can therefore be proposed more generally as:

> **reference-guided partial decomposition: use independent reference information to contract the set of nuisance-compatible explanations, propagate that contraction to the target-compatible signal set, and defer irreversible suppression or semantic commitment until the remaining uncertainty warrants it.**

This is the closest mathematical sister to TNOA's process-preserving partial-identification architecture.
