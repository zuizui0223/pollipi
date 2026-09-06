# V3–TNOA reversible-decomposition corollaries

Status: **mathematical companion to `V3_TNOA_THEORY_CORE.md`**. These results refine the generic architecture without adding an empirical claim.

## 1. The decomposition pair itself is reversible

Let `P` be any linear operator of compatible dimension and define

\[
E=PY,\qquad Z=(I-P)Y.
\]

Then

\[
\boxed{Y=E+Z.}
\]

Therefore the map

\[
D_P:Y\mapsto(E,Z)
\]

is injective, with inverse `(E,Z) -> E+Z`.

For an orthogonal nuisance projector this means that **reference-explained and residual channels together retain the complete primary observation exactly**, provided neither channel is subsequently quantized or discarded in a lossy way.

Raw storage is therefore mathematically redundant when both components are retained losslessly, although keeping raw is still useful for audit, provenance and protection against numerical/implementation mistakes.

## 2. Residual-only replacement is the destructive step

The residual map

\[
Y\mapsto Z=(I-P)Y
\]

is generally non-injective whenever `P` has nonzero range.

If `v` lies in `range(P)`, then for any `Y`,

\[
(I-P)(Y+v)=(I-P)Y.
\]

Distinct raw observations can therefore become identical residual observations.

Thus the epistemically consequential operation is **not decomposition**. It is discarding one branch of the decomposition.

This changes the generic V3 interpretation:

> computing nuisance-explained structure is information-safe when the complementary residual is retained; treating the residual as the only surviving observation is an irreversible coarsening.

## 3. Representation entitlement is needed for suppression, not for decomposition

Because `(E,Z)` is reversible, there is no information-theoretic need to ask permission before computing the decomposition itself.

Representation entitlement is required when the system intends to do something irreversible or semantically loaded, for example:

- discard `E` and keep only `Z`;
- suppress or downweight raw evidence because it is called nuisance;
- let `E` directly create a nuisance conclusion;
- let quiet `Z` create target-absence evidence;
- trigger a live action that cannot later be reconstructed from the full record.

The safer architecture is therefore:

\[
(Y,R)
\to
(R,E,Z,\text{raw audit})
\to
\text{calibrated evidence channels}
\to
\text{TNOA decision or U}.
\]

Layer-R entitlement governs **use and suppression**, not the mere existence of derived channels.

## 4. Decision-risk monotonicity under reference refinement

Consider any decision problem with latent world `omega`, action `a`, loss `L(a,omega)` and any fixed probability distribution over worlds.

Let `R*(X)` denote the minimum expected loss achievable by all decision rules measurable with respect to observation `X`.

Because `Y` is a deterministic projection of `(Y,R)`, every rule based on `Y` can also be implemented from `(Y,R)` by ignoring `R`. Hence

\[
\boxed{R^*(Y,R)\le R^*(Y).}
\]

This is the decision-theoretic version of compatible-set refinement.

A retained reference **cannot worsen the best achievable decision risk**, because the decision maker remains free not to use it.

A particular algorithm can still worsen performance if it forces an inappropriate use of the reference. That is an algorithm restriction, not a property of the information itself.

## 5. Decision-risk monotonicity under semantic coarsening

Let rich evidence be `E` and a deterministic coarsening be `C=c(E)`.

Every decision rule based on `C` can be reproduced from `E` by first applying `c`. Therefore

\[
\boxed{R^*(E)\le R^*(C).}
\]

Semantic coarsening cannot improve the best achievable decision risk for a fixed decision problem.

Again, equality is possible when the discarded information is irrelevant to the chosen loss. Strict inequality occurs whenever the lost distinction matters.

## 6. Exact sister-method duality

The two statements can now be expressed at three equivalent levels.

### Compatible-world level

\[
\mathcal C_{Y,R}\subseteq\mathcal C_Y,
\qquad
\mathcal C_E\subseteq\mathcal C_{c(E)}.
\]

### Information / sigma-algebra level

\[
\sigma(Y)\subseteq\sigma(Y,R),
\qquad
\sigma(c(E))\subseteq\sigma(E).
\]

### Optimal decision-risk level

\[
R^*(Y,R)\le R^*(Y),
\qquad
R^*(E)\le R^*(c(E)).
\]

Thus the conceptual symmetry is exact:

- adding independent retained information upstream weakly improves the information order;
- discarding distinctions downstream weakly worsens the information order.

## 7. The revised mathematical answer for V3

The generic V3 method should therefore be defined as **reference-guided reversible decomposition**, not as nuisance subtraction.

The minimal information-preserving output is

\[
\boxed{(R,\;PY,\;(I-P)Y)}
\]

plus enough provenance to reproduce `P`.

Keeping raw `Y` as well is recommended for audit but is not mathematically required if the decomposition pair is stored losslessly.

What still requires empirical validation is not whether this decomposition preserves information—it does by construction—but whether the derived channels make scientifically relevant target/nuisance evidence easier to identify under finite sampling and real physical coupling.

## 8. Consequence for the V3–TNOA paper logic

This removes one conceptual burden from the empirical study.

The paper no longer needs to establish that V3 is a universally safe **correction**. Universal safe correction is impossible over unrestricted targets.

Instead it can make a stronger and cleaner conceptual proposal:

> **retain richer information, expose a reversible decomposition, and postpone irreversible suppression or semantic commitment until calibrated evidence warrants it.**

TNOA supplies the downstream half of that rule by preserving T/N overlap, no-support and unresolved states instead of forcing binary closure.
