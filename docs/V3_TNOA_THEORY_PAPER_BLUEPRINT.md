# Theory paper blueprint — refine before deciding

Status: **conceptual/mathematical paper route**. This paper route is deliberately separated from the controlled-real validation route. Real data may strengthen transport claims but are not required for the structural theorems below.

## Working title

**Refine before deciding: an information-order theory for reference-guided observation and uncertainty-preserving inference**

Alternative:

**Decompose without discarding: reference-guided partial identification before semantic commitment**

## 1. Core question

Many sensing pipelines perform two irreversible operations too early:

1. they replace a rich observation with one “corrected” representation;
2. they replace process-preserving evidence with one semantic label.

The paper asks:

> **What can be established mathematically if independent reference information is treated as information refinement rather than correction, and semantic decisions are treated as compatible-set contraction rather than forced classification?**

## 2. Central answer

The paper's central statement is:

> **Independent reference information should contract the set of measurement-side explanations, decomposition should remain reversible or set-valued, and semantic commitment should occur only when the resulting compatible set supports a unique conclusion.**

Compact rule:

> **decompose without discarding; contract with independent information; interpret without forcing.**

## 3. Main contributions

### Contribution 1 — information-order duality

For primary observation `Y` and retained reference `R`,

\[
\mathcal I_{Y,R}\subseteq\mathcal I_Y.
\]

For rich evidence `E` and deterministic semantic coarsening `c(E)`,

\[
\mathcal I_E\subseteq\mathcal I_{c(E)}.
\]

Reference augmentation and semantic coarsening therefore move in opposite directions in the same information partial order.

### Contribution 2 — primary-only decomposition non-identifiability

For `Y=S+N`, infinitely many `(S,N)` pairs produce the same `Y` without additional restrictions. A reference or other identifying restriction is mathematically necessary if target/nuisance contribution is the estimand.

### Contribution 3 — exact projection tradeoff and impossibility

For an orthogonal reference-derived projector `P`, define target and nuisance capture fractions `a_S` and `a_N`. Energy-SNR improves exactly when

\[
a_N>a_S.
\]

Any nonzero reference-only projector has an admissible target in its range and therefore cannot universally preserve an unrestricted target class.

This proves that “target-free reference” does not imply “safe subtraction.”

### Contribution 4 — reversible decomposition

The pair

\[
(PY,(I-P)Y)
\]

is exactly invertible because the components sum to `Y`. Information loss occurs when one branch is discarded, not when the decomposition is computed.

### Contribution 5 — reference-guided partial decomposition

If the reference yields a nuisance-compatible set `N(R)`, define

\[
\mathcal S(Y,R)=Y-\mathcal N(R).
\]

Then nuisance-set coverage transfers directly to target-set coverage and, in the additive normed case,

\[
\operatorname{diam}\mathcal S(Y,R)=\operatorname{diam}\mathcal N(R).
\]

Reference value is therefore expressible as compatible-set contraction rather than point-estimator accuracy.

### Contribution 6 — general nonlinear forward-model theorem

For arbitrary

\[
Y=F(S,M),
\]

if a reference contracts the compatible measurement-state set from `M1` to `M2 subset M1`, then the compatible target set contracts as well. No additive pixel model is needed for the core information theorem.

### Contribution 7 — decision-risk and resolvable-coverage monotonicity

Retaining `(Y,R)` cannot worsen optimal decision risk because any `Y`-only decision rule remains available. Deterministic coarsening cannot improve optimal decision risk because it restricts the rule class.

Likewise, ideal point-identification coverage is monotone:

- reference refinement can only preserve/increase safely resolvable coverage;
- semantic coarsening can only preserve/decrease it.

## 4. Relationship to TNOA

TNOA Paper 1 remains a separate closed-world decision-architecture paper.

The present theory paper uses TNOA as the downstream sister principle:

- upstream: refine the retained observation / compatible measurement states;
- downstream: preserve process distinctions and U until semantic entitlement exists.

The symmetry is mathematical, not an assertion that both papers require the same empirical evidence.

## 5. What can be claimed without real data

The following are theorem/structural claims and can stand without field observations:

1. compatible-set refinement under added retained information;
2. compatible-set expansion under deterministic coarsening;
3. additive primary-only non-identifiability;
4. projection SNR tradeoff `a_N > a_S`;
5. universal non-harm impossibility for nonzero projectors over unrestricted targets;
6. exact reversibility of explained+residual decomposition;
7. nuisance-set to target-set coverage transfer;
8. identified-set diameter equality in the additive case;
9. general forward-model set-contraction theorem;
10. optimal-decision-risk monotonicity;
11. ideal resolvable-coverage monotonicity.

Synthetic examples may illustrate these statements but are not used as substitutes for field truth.

## 6. What should remain explicitly empirical

Do not claim without external validation:

- that a given physical reference is informative about real nuisance;
- that `a_N > a_S` in a target domain;
- finite-sample stability of a nuisance subspace;
- calibration of a reference-derived compatible set;
- downstream observer accuracy in nature;
- transport between domains;
- named causal attribution to wind, illumination, shake or another physical cause without additional intervention/structure.

These become future validation questions, not logical prerequisites for the theory paper.

## 7. Proposed paper structure

### Introduction

1. sensing pipelines often collapse uncertainty twice: during representation and during semantics;
2. target recognition does not solve exogenous observation-process ambiguity;
3. existing correction language encourages point replacement;
4. propose information refinement + partial decomposition + entitlement.

### Theory 1 — information partitions

Define latent worlds, compatible fibers and identified sets.

Prove reference refinement and semantic-coarsening duality.

### Theory 2 — why primary-only separation fails

Additive non-identifiability witness.

Generalize to arbitrary forward model.

### Theory 3 — why subtraction can overreach

Derive `a_N > a_S` SNR condition.

Prove universal target-preservation impossibility.

### Theory 4 — the non-destructive solution

Prove reversible decomposition.

Introduce set-valued nuisance/target compatibility.

Derive coverage and diameter results.

### Theory 5 — decision implications

Prove optimal-risk and resolvable-coverage monotonicity.

Connect to TNOA decision entitlement and U.

### Illustrations

Use finite-world and finite-dimensional executable witnesses already committed in the repository.

Optionally use the existing V3 synthetic generations as a cautionary illustration that an informative reference can coexist with a poor forced observer.

### Discussion

Separate structural guarantees from empirical transport.

Emphasize that the theory does not require naming the nuisance cause.

## 8. Figure plan

### Figure 1 — information-order duality

`Y -> (Y,R)` shown as partition refinement; `E -> c(E)` shown as partition coarsening.

Main visual claim: upstream enrichment and downstream collapse move in opposite directions.

### Figure 2 — primary-only non-identifiability and reference contraction

Multiple `(S,N)` decompositions map to one `Y`; adding reference restrictions contracts `N(R)` and translates directly to `S(Y,R)`.

### Figure 3 — projection phase plane

Axes `a_S` and `a_N`.

Diagonal `a_N=a_S` is the exact no-gain boundary.

Above diagonal: energy-SNR gain. Below: harm. Target-only overprojection shown at `N=0` as a separate impossibility panel.

### Figure 4 — reversible versus destructive representation

Panel A: keep `PY` and `(I-P)Y`, reconstruct `Y` exactly.

Panel B: discard `PY`, show multiple raw observations collapse to same residual.

### Figure 5 — two-layer compatible-set pipeline

`M(R) -> S_F(Y,R) -> T/C/N/O/(A-) -> B/T/N/U`.

Show uncertainty sets contracting only when justified information arrives.

## 9. Executable mathematics

Canonical witnesses currently live in:

- `pollipi_analysis.v3_tnoa_theory`;
- `pollipi_analysis.v3_tnoa_decision_risk`;
- `pollipi_analysis.v3_tnoa_partial_decomposition`;
- corresponding theory tests.

These are not numerical simulations of field performance. They are executable checks of the finite-world / finite-dimensional propositions.

## 10. Main novelty statement

Avoid claiming novelty as “a better nuisance remover.”

The stronger novelty candidate is:

> **a unified information-order formulation in which independent reference channels refine measurement-compatible states, nuisance decomposition is retained reversibly or set-valuedly, and downstream process semantics are allowed to contract only under explicit entitlement.**

The closest sister statement to TNOA is:

> **Reference refinement and semantic preservation are dual operations on uncertainty: one adds distinctions before inference; the other prevents unsupported distinctions from being discarded.**

## 11. One-sentence paper conclusion

> **The mathematically safe response to observation-process ambiguity is not to manufacture one corrected signal, but to retain independent reference information, preserve a reversible or set-valued decomposition, and postpone semantic commitment until the compatible state set has genuinely contracted.**
