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

A target-free reference `R` supplies information about `M`, not direct target truth.

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

## 4. Additive model as a special case

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

## 5. Reference value is about state restriction, not physical naming

The reference is scientifically useful when it excludes measurement-side states that would otherwise remain compatible with the primary observation.

Therefore the generic question is

> **How much does the reference contract the compatible measurement-state set relevant to the target query?**

not

> **Can the system correctly name the disturbance?**

A reference may be informative about shared motion/illumination structure even when the physical source identity remains unresolved.

## 6. Causal-claim boundary

The compatible-set theorem is an identification statement, not automatically a causal theorem.

Calling an explained component the *causal contribution* of wind, camera shake or another named source requires additional structural or interventional assumptions linking the reference, latent measurement state and primary observation.

Without those assumptions the safe claim is:

> **reference-supported measurement-state contribution / compatible explanation**

rather than named causal attribution.

Controlled interventions may later identify a physical cause, but the general method does not require such naming to refine the observation problem.

## 7. TNOA connection

The general forward-model formulation gives the same architecture at two layers:

1. reference information contracts `M(R)` and therefore `S_F(Y,R)`;
2. TNOA contracts semantic compatible states only when positive calibrated evidence warrants it;
3. if either layer remains non-singleton, unresolved structure is preserved rather than forced to a point label.

The common mathematical operation is **compatible-set contraction under added justified information**.

## 8. Practical implication

The current temporal-subspace V3 is one computational approximation to this general idea. It should not define the theory.

The theory survives replacement of the temporal projector by:

- nonlinear nuisance models;
- optical-flow or geometric latent-state models;
- learned reference embeddings;
- photometric forward models;
- acoustic or other sensor-domain reference models;
- set-valued or probabilistic nuisance representations.

What must remain invariant is the information contract: reference information may refine compatible measurement states, but unsupported restrictions or semantic conclusions are not allowed.
