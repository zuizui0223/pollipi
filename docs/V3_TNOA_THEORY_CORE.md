# V3–TNOA theory core — information refinement, representation entitlement, and semantic entitlement

Status: **pre-empirical mathematical core**. These statements separate what follows from the architecture alone from what still requires empirical validation. The purpose is not to prove that a particular V3 implementation works in nature. It is to recover the strongest application-independent propositions that are true before real-data validation.

## 1. Central conceptual claim

The two-layer architecture is best understood as an information-order problem.

- **V3-side question:** can extra target-free reference information refine the observation before interpretation?
- **TNOA-side question:** after observing evidence, is a unique semantic statement licensed, or must uncertainty be retained?

The symmetry is therefore not “noise removal versus classification.” It is:

> **refine information upstream when justified; do not coarsen meaning downstream before entitlement.**

This distinction makes the mathematical and empirical burdens different. Information-order and non-identifiability statements can be proved structurally. Performance and transport of a particular estimator remain empirical.

## 2. Compatible-world notation

Let `Ω` be a set of possible latent worlds. A world `ω ∈ Ω` contains whatever latent variables are scientifically relevant, including target process `S`, nuisance process `N`, and any other hidden state.

For any observation map `X : Ω -> Xspace`, define the compatible-world fiber

\[
\mathcal C_X(x)=\{\omega\in\Omega:X(\omega)=x\}.
\]

For an estimand `θ : Ω -> Θ`, define its identified set under observation `X=x` as

\[
\mathcal I_X(x)=\{\theta(\omega):\omega\in\mathcal C_X(x)\}.
\]

Point identification means `I_X(x)` is a singleton. Partial identification means it is not.

This notation allows V3 and TNOA to be placed in the same mathematical frame.

## 3. Proposition 1 — reference refinement can only shrink compatible sets

Let `Y` denote the primary observation and `R` an additional target-free reference observation. Then

\[
\mathcal C_{(Y,R)}(y,r)\subseteq \mathcal C_Y(y).
\]

Therefore, for every estimand `θ`,

\[
\boxed{\mathcal I_{(Y,R)}(y,r)\subseteq\mathcal I_Y(y).}
\]

### Proof

Every world compatible with `(Y,R)=(y,r)` necessarily satisfies `Y=y`; hence it is already in `C_Y(y)`. Applying `θ` to a subset cannot create values outside the larger identified set. ∎

### Interpretation

Adding a reference channel cannot make the *available information* worse. It may be uninformative, in which case the inclusion is equality. It is informative exactly when the inclusion is strict for a scientifically relevant estimand.

This is an information theorem, not a claim that every algorithm using `R` improves performance.

## 4. Proposition 2 — deterministic semantic coarsening can only expand compatible sets

Let `E` be a rich evidence record and let `C=c(E)` be a deterministic coarsening, such as mapping a process-preserving record to a binary label. For any realized `e`,

\[
\mathcal C_E(e)\subseteq \mathcal C_C(c(e)),
\]

so

\[
\boxed{\mathcal I_E(e)\subseteq\mathcal I_C(c(e)).}
\]

### Proof

If `E(ω)=e`, then necessarily `c(E(ω))=c(e)`. Thus every world in the fine-record fiber belongs to the coarsened fiber. ∎

### V3–TNOA duality

Propositions 1 and 2 are exact duals in the information partial order:

\[
\sigma(Y)\subseteq\sigma(Y,R)
\]

for reference augmentation, whereas

\[
\sigma(c(E))\subseteq\sigma(E)
\]

for semantic coarsening.

Thus the architectural direction is mathematically asymmetric but conceptually symmetric:

- V3/reference acquisition moves **upward** toward a finer information partition;
- premature TNOA-to-binary collapse moves **downward** toward a coarser partition.

## 5. Proposition 3 — primary-only additive separation is non-identifiable without restrictions

Consider the additive observation model

\[
Y=S+N.
\]

If no additional restrictions are imposed, `S` and `N` are not separately identifiable from `Y`.

### Proof by construction

For any perturbation `Δ` of compatible dimension, define

\[
S'=S+\Delta,\qquad N'=N-\Delta.
\]

Then

\[
S'+N'=S+N=Y.
\]

Infinitely many distinct decompositions therefore produce the same primary observation. ∎

### Consequence

A target-free reference, structural assumption, intervention, negative control, or other external restriction is not merely convenient. Some additional information is mathematically necessary if the scientific aim is to distinguish target and nuisance contributions rather than only predict labels.

## 6. Proposition 4 — exact projection trade-off

Let `P` be an orthogonal projector onto a reference-derived temporal subspace. Let

\[
Y=S+N,
\]

and define the residual representation

\[
Z=(I-P)Y.
\]

For nonzero `S` and `N`, define the fractions of target and nuisance energy captured by the reference subspace:

\[
a_S=\frac{\|PS\|^2}{\|S\|^2},\qquad
 a_N=\frac{\|PN\|^2}{\|N\|^2}.
\]

Then

\[
\|(I-P)S\|^2=(1-a_S)\|S\|^2,
\]

\[
\|(I-P)N\|^2=(1-a_N)\|N\|^2.
\]

If signal-to-nuisance energy ratio is defined as

\[
\mathrm{SNR}_E=\frac{\|S\|^2}{\|N\|^2},
\]

then, whenever residual nuisance energy is nonzero,

\[
\boxed{
\frac{\mathrm{SNR}_{E,\mathrm{after}}}{\mathrm{SNR}_{E,\mathrm{before}}}
=
\frac{1-a_S}{1-a_N}.
}
\]

Therefore

\[
\boxed{\mathrm{SNR}_{E,\mathrm{after}}>\mathrm{SNR}_{E,\mathrm{before}}
\iff a_N>a_S.}
\]

### Meaning

The mathematically correct question is not “does the reference explain a lot of variation?” It is:

> **Does the reference-derived subspace explain a larger fraction of nuisance energy than of target energy?**

Reference activity alone is insufficient to answer that question.

## 7. Corollary 4a — overprojection is unavoidable when target overlaps the nuisance subspace

If `N=0` and `PS != 0`, then

\[
\|(I-P)S\|<\|S\|.
\]

If `S` lies entirely in the range of `P`, then

\[
(I-P)S=0.
\]

Thus a nuisance projection can erase a genuine target even in a target-free reference design. Spatial separation between reference and target does not by itself imply temporal-subspace orthogonality.

This is the exact mathematical form of the overprojection failure observed in the fresh bridges.

## 8. Proposition 5 — no nontrivial reference-only projection can guarantee universal target preservation

Suppose a representation rule chooses a nonzero projector `P_R` using only target-free reference information `R`. Assume the admissible target class contains arbitrary nonzero vectors in the observation space.

If the rule ever applies a nonzero `P_R`, there exists an admissible target `S` such that

\[
(I-P_R)S=0.
\]

### Proof

A nonzero orthogonal projector has a nontrivial range. Choose any nonzero `S` in `range(P_R)`. Then `P_RS=S`, so `(I-P_R)S=0`. ∎

### Consequence

A reference-only gate cannot provide a universal non-harm guarantee unless at least one of the following is added:

1. the target class is structurally restricted away from the nuisance subspace;
2. an independent target-preservation channel is available;
3. the raw representation is retained so that projection is not an irreversible replacement;
4. the method accepts an unresolved/abstaining state rather than claiming corrected truth.

This is a structural impossibility result. No amount of threshold tuning removes it over an unrestricted target class.

## 9. Proposition 6 — augmentation is information-safe; replacement need not be

Let the V3 decomposition produce

\[
\hat N=PY,\qquad Z=(I-P)Y.
\]

Define the **augmented representation**

\[
A=(Y,R,\hat N,Z).
\]

Because `Nhat` and `Z` are deterministic functions of `(Y,R)` and `Y,R` are retained explicitly,

\[
\boxed{\sigma(A)=\sigma(Y,R).}
\]

Hence the augmented representation is information-equivalent to the full rich input. Every decision rule available before decomposition remains available afterward simply by ignoring the derived channels.

By contrast, if the downstream system receives only

\[
Z=(I-P)Y,
\]

then the map may be non-injective and information may be lost. For example, if `P=I`, every `Y` maps to `Z=0`.

### Design consequence — the mathematical default

The safest generic architecture is therefore not

\[
Y\rightarrow Z\rightarrow\text{decision},
\]

but

\[
\boxed{
(Y,R)
\rightarrow
(Y,R,\hat N,Z,E_R)
\rightarrow
\text{TNOA evidence / U / decision}
}
\]

where `E_R` records support for interpreting the derived nuisance representation.

**V3 should augment evidence rather than overwrite observation.**

This converts representation entitlement from permission to destroy raw information into permission to *use a derived channel as explanatory evidence*.

## 10. Proposition 7 — augmentation weakly dominates replacement for downstream decision rules

Let `D_aug` be the set of all decision rules measurable with respect to augmented representation `A`, and `D_raw` the set available from `(Y,R)`. Since `σ(A)=σ(Y,R)`,

\[
D_{aug}=D_{raw}
\]

when all raw channels are retained.

If a restricted downstream implementation uses only residual `Z`, its rule class `D_Z` satisfies

\[
D_Z\subseteq D_{aug},
\]

with strict inclusion whenever `Z` is not sufficient for `(Y,R)`.

Therefore any apparent gain from forcing every downstream decision through `Z` is an implementation restriction, not an information-theoretic necessity.

## 11. Proposition 8 — positive-only evidence cannot certify absence without an additional identifying restriction

Let `E+` denote a positive-evidence record with no independently validated negative-evidence channel `A-`. Suppose an observed evidence value `e` is compatible both with

- a world in which the target is absent, and
- a world in which the target is present but unsupported by the positive observer.

Then target presence is not point identified at `e`.

In particular, if such a target-present compatible world cannot be excluded, the safe upper endpoint of target-presence compatibility remains 1.

This is the TNOA-side analogue of Proposition 3: lack of an identifying channel cannot be repaired by semantic relabelling.

## 12. The two-layer theorem-like architecture

The preceding propositions imply a clean separation of responsibilities.

### Layer I — information acquisition / refinement

Acquire `R` only if it is scientifically independent of target truth and potentially informative about nuisance. Proposition 1 guarantees that retaining `(Y,R)` cannot enlarge compatible-world sets.

### Layer R — representation decomposition

Construct nuisance-explained and residual channels, but retain raw `Y`. Proposition 6 guarantees that decomposition is then information-safe. Projection quality is summarized by the unresolved contrast `a_N-a_S`; Proposition 4 shows exactly when energy-ratio improvement occurs.

### Layer S — semantic entitlement

Use calibrated positive evidence and preserve overlap/no-support as `U` when unique attribution is not licensed. Proposition 2 explains why premature coarsening can only weaken identification.

The conceptual chain is therefore

\[
\boxed{
\text{world}
\to
\text{rich observation}
\to
\text{non-destructive decomposition}
\to
\text{process-preserving evidence}
\to
\text{entitled decision or U}
}
\]

rather than

\[
\text{world}\to\text{corrected image}\to\text{binary label}.
\]

## 13. What is mathematically solved now

The following claims do **not** require field data once the stated assumptions are accepted:

1. primary-only additive target/nuisance decomposition is non-identifiable without restrictions;
2. adding a reference channel weakly refines identified sets;
3. deterministic semantic coarsening weakly enlarges identified sets;
4. orthogonal nuisance projection improves energy SNR exactly when `a_N > a_S`;
5. unconditional projection can erase target signal;
6. no nonzero reference-only projector universally preserves an unrestricted target class;
7. retaining raw + derived channels avoids representation-level information loss;
8. positive-only evidence cannot prove absence when target-present compatible worlds remain.

These are the conceptual/mathematical core of the sister-method symmetry.

## 14. What remains empirical

Mathematics alone does not establish:

- that a physical target-free reference has useful coupling to real nuisance;
- that `a_N` tends to exceed `a_S` in a target domain;
- that a learned or estimated subspace is stable under finite sampling;
- that a particular target observer extracts useful evidence from the augmented channels;
- transfer across ecological, laboratory, microscopy, industrial, or other visual domains.

Those are estimator- and data-generating-process claims.

## 15. Revised conceptual proposal

The strongest application-independent proposal is now:

> **Do not treat nuisance inference as image correction. Treat it as information refinement. Acquire independent reference information, decompose the observation without discarding the raw channel, record the nuisance-explained and residual components as separate evidence, and let a downstream entitlement layer decide whether those components justify a unique interpretation.**

This formulation is more general than wind detection, motion compensation, or any particular biological application.

## 16. Compact symmetry with TNOA

| Upstream side | Downstream side |
|---|---|
| add independent reference information | preserve independent evidence axes |
| refine compatible-world sets | avoid premature quotient/coarsening |
| decompose but retain raw | decide or retain U |
| projection can overreach | classification can overclaim |
| representation entitlement | semantic entitlement |

The shared rule is:

\[
\boxed{\text{unsupported transformation and unsupported conclusion are the same epistemic error at different layers.}}
\]
