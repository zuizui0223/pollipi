# V3–TNOA general forward-model formulation

Status: **structural generalization**. The additive model is retained as an analytically transparent special case, not as a requirement of the method.

## 1. Why the additive model is not enough as the generic definition

The convenient model

\[
Y=S+N
\]

captures superposed motion/variation but does not literally describe every observation defect. Occlusion, blur, saturation, exposure changes, geometric camera motion and nonlinear sensor response need not be additive in image space.

The general theory therefore uses a forward model

\[
\boxed{Y=F(S,M)}
\]

where:

- `S` is the target/process state of interest;
- `M` collects measurement-side latent state, including nuisance processes, geometry, visibility and sensor effects;
- `F` may be nonlinear and need not be invertible.

A target-excluding reference `R` supplies additional information about `M`; it is not direct target truth.

### Terminology note

“Independent reference” in this theory means **an additional retained observation channel whose scientific definition does not use the target answer being inferred**. It does **not** require statistical independence between `R`, `S` and `M`. Indeed, a useful reference is expected to be statistically dependent on relevant parts of `M`.

The information-refinement theorem also assumes **non-destructive acquisition**: retaining `R` does not replace or alter the already-defined primary record `Y`. If installing or measuring the reference physically perturbs the primary process, that is a different joint forward model and must be represented explicitly.

## 2. Compatible measurement-state set

Let the reference induce a compatible set

\[
\mathcal M(R).
\]

This may contain multiple nuisance types or unnamed measurement states. The theory does not require identifying a physical label such as `wind`.

For primary observation `Y=y`, define the compatible target/process set

\[
\boxed{
\mathcal S_F(y,R)
=
\{s:\exists m\in\mathcal M(R)\text{ such that }F(s,m)=y\}.
}
\]

This is the generic reference-guided partial-identification object.

## 3. Theorem — reference refinement contracts the target-compatible set for any forward model

Suppose two reference states satisfy

\[
\mathcal M(R_2)\subseteq\mathcal M(R_1).
\]

Then

\[
\boxed{
\mathcal S_F(y,R_2)
\subseteq
\mathcal S_F(y,R_1).
}
\]

### Proof

If `s` belongs to `S_F(y,R2)`, there exists an `m` in `M(R2)` with `F(s,m)=y`. Since `M(R2)` is a subset of `M(R1)`, the same `m` witnesses membership of `s` in `S_F(y,R1)`. ∎

No linearity, Gaussian noise, optical-flow model or projection assumption is needed.

## 4. Theorem — measurement-state coverage transfers to target-state coverage

Let the true world satisfy

\[
Y=F(S,M).
\]

For any reference-derived compatible set `M_alpha(R)`, define

\[
\mathcal S_{F,\alpha}(Y,R)
=
\{s:\exists m\in\mathcal M_\alpha(R),\;F(s,m)=Y\}.
\]

Whenever the true measurement state is covered,

\[
M\in\mathcal M_\alpha(R),
\]

the true target state is automatically covered because the true pair `(S,M)` itself witnesses

\[
S\in\mathcal S_{F,\alpha}(Y,R).
\]

Therefore, if

\[
P\{M\in\mathcal M_\alpha(R)\}\ge 1-\alpha_R,
\]

then

\[
\boxed{
P\{S\in\mathcal S_{F,\alpha}(Y,R)\}\ge 1-\alpha_R.
}
\]

This is a general coverage-transfer result and does not require an additive observation model.

### Important boundary

A smaller compatible set is useful only if it remains **valid**. Arbitrarily excluding the true measurement state can make the target set narrow while destroying coverage. Thus reference refinement has two distinct requirements:

1. **contraction** — exclude measurement states that are no longer compatible with the reference;
2. **calibration / validity** — retain the true measurement state at the declared coverage level.

The first is set geometry; the second is an empirical or assumption-based entitlement condition.

## 5. Additive model as a special case

For

\[
F(S,N)=S+N,
\]

the generic compatible set becomes

\[
\mathcal S_F(Y,R)=Y-\mathcal N(R).
\]

In this special case translation/reflection is an isometry, giving the stronger exact result

\[
\operatorname{diam}\mathcal S_F(Y,R)
=
\operatorname{diam}\mathcal N(R).
\]

Thus the additive model is useful because it yields closed-form uncertainty geometry, not because the general framework depends on additive pixels.

## 6. Reference value is about valid state restriction, not physical naming

The reference is scientifically useful when it **validly excludes** measurement-side states that would otherwise remain compatible with the primary observation.

Therefore the generic question is

> **How much does a calibrated reference contract the compatible measurement-state set relevant to the target query?**

not

> **Can the system correctly name the disturbance?**

A reference may be informative about shared motion/illumination structure even when the physical source identity remains unresolved.

## 7. Causal-claim boundary

The compatible-set theorem is an identification statement, not automatically a causal theorem.

Calling an explained component the *causal contribution* of wind, camera shake or another named source requires additional structural or interventional assumptions linking the reference, latent measurement state and primary observation.

Without those assumptions the safe claim is:

> **reference-supported measurement-state contribution / compatible explanation**

rather than named causal attribution.

Controlled interventions may later identify a physical cause, but the general method does not require such naming to refine the observation problem.

## 8. TNOA connection

The general forward-model formulation gives the same architecture at two layers:

1. reference information validly contracts `M(R)` and therefore `S_F(Y,R)`;
2. TNOA contracts semantic compatible states only when positive calibrated evidence warrants it;
3. if either layer remains non-singleton, unresolved structure is preserved rather than forced to a point label.

The common mathematical operation is **valid compatible-set contraction under added justified information**.

## 9. Practical implication

The current temporal-subspace V3 is one computational approximation to this general idea. It should not define the theory.

The theory survives replacement of the temporal projector by:

- nonlinear nuisance models;
- optical-flow or geometric latent-state models;
- learned reference embeddings;
- photometric forward models;
- acoustic or other sensor-domain reference models;
- set-valued or probabilistic nuisance representations.

What must remain invariant is the information contract: reference information may refine compatible measurement states, but unsupported restrictions or semantic conclusions are not allowed.
