# Refine before loss: an information-order theory for scientific observation

Status: **conceptual-mathematical draft**. This manuscript candidate is intentionally broader than the V3 implementation and does not require a real-data performance result for its structural claims. Empirical transport remains a separate validation problem.

## Abstract

Scientific observations can lose information in more than one way. Additional reference measurements may refine what latent states remain compatible with a record; selection mechanisms may remove entire exposure opportunities before a row exists; and later semantic decisions may collapse distinctions that were retained in the record. These operations are often treated separately as denoising, missing detection, or classification uncertainty. We formulate them in a common information order using compatible-world fibers. Retaining side information can only preserve or contract the compatible set. Any deterministic post-processing can only preserve or expand it, so distinctions collapsed by upstream selection or semantic coarsening cannot be reconstructed by downstream algorithms alone. Record-entry selection is a special support-deleting post-processing: the same entered event log can arise from full exposure worlds with different shadow composition. A gate-independent exposure ledger identifies the omitted denominator but not, by itself, the biology of omitted exposures. For reference-guided measurement decomposition, we show that an additive target/nuisance decomposition is not identified from the primary observation alone; that orthogonal projection improves target-to-nuisance energy ratio exactly when nuisance capture exceeds target capture; and that no nonzero reference-only projector is uniformly non-harmful for an unrestricted target class. The information-safe alternative is reversible or set-valued decomposition: retain both explained and residual components, or propagate a reference-derived compatible measurement-state set into a compatible target set. We then connect these results to process-preserving semantic inference, where deterministic coarsening expands compatible states and unresolved cases should remain unresolved. The resulting architecture separates three operations—reference refinement, record-entry selection, and semantic coarsening—and yields a simple design rule: add information before irreversible loss, preserve provenance where rows can disappear, and do not force semantic distinctions that the retained information cannot identify.

## 1. Introduction

Scientific sensing rarely observes a target process directly. A measurement is produced by an interaction between the process of interest, measurement-side state, acquisition decisions, and downstream interpretation. A conventional pipeline often treats these problems in sequence: improve the signal, detect an event, save a record, classify the record, and analyze the resulting table. That sequence hides an important distinction. Some operations add information, whereas others remove distinctions from the scientific record.

We consider three operations.

First, a measurement system may retain an additional reference channel. Examples include a target-free image region, a control sensor, an independent exposure ledger, or another measurement that constrains nuisance or observation state. If the original observation is retained, this is an information refinement.

Second, an operational entry mechanism may select which exposure opportunities become rows in a scientific record. Once unentered opportunities disappear from the retained data, the selected event table is compatible with multiple full exposure worlds.

Third, an entered rich evidence record may be mapped to a smaller semantic vocabulary. A binary target/not-target decision, for example, can collapse target+nuisance superposition and unresolved evidence into states that are no longer distinguishable downstream.

These operations have different scientific meanings, but they share a simple mathematical structure. We represent an observation by the set of latent worlds compatible with it. Additional retained information refines this set. Deterministic post-processing cannot split an equivalence class that has already been collapsed. Selection and semantic coarsening are therefore information-loss operations; reference augmentation is the opposite-signed operation.

This paper develops that compatible-set calculus and derives consequences for measurement design, record-entry auditing, and semantic decision systems. The claims are structural. They do not require that a particular physical reference be informative, that a particular detector be accurate, or that a method transport across applications. Those are empirical questions that begin only after the information contract has been specified.

## 2. Compatible-world formulation

Let `W` denote a latent world, `theta(W)` the scientific estimand or query, and `O(W)` the retained observation.

For realized world `w`, define the compatible-world fiber

`F_O(w) = {w' : O(w') = O(w)}`

and the identified set

`I_O(w) = {theta(w') : w' in F_O(w)}`.

A query is point identified at `w` when `I_O(w)` is a singleton. Otherwise the observation supports a set of possible answers.

This formulation is intentionally agnostic about whether the retained object is an image, acoustic trace, event table, exposure ledger, or semantic record.

### Proposition 1 — retained side information refines compatible worlds

Let `R(W)` be an additional retained channel and

`O_plus(W) = (O(W), R(W))`.

Then

`F_O_plus(w) subseteq F_O(w)`

and hence

`I_O_plus(w) subseteq I_O(w)`.

The proof is immediate: matching both channels implies matching the original channel.

The proposition does not say that every physical reference produces a *strict* refinement. A useless reference may leave the fiber unchanged. A miscalibrated algorithm may also impose an invalid restriction. The structural result applies to retained valid information.

### Proposition 2 — deterministic post-processing cannot refine compatible worlds

Let `C` be any deterministic transformation of the retained observation and define

`O_C = C o O`.

Then

`F_O(w) subseteq F_O_C(w)`

and

`I_O(w) subseteq I_O_C(w)`.

Thus downstream processing cannot recreate distinctions absent from its input.

### Corollary 2.1 — no downstream recovery of a collapsed distinction

If `O(w1)=O(w2)` but `theta(w1) != theta(w2)`, then every downstream deterministic rule `G(O)` takes the same value on `w1` and `w2`. The query is not point identifiable from `O`, regardless of downstream classifier sophistication.

This corollary is the common mathematical skeleton behind upstream row-loss irreversibility and downstream semantic-coarsening irreversibility.

## 3. Record-entry selection as support loss

Consider a predefined exposure universe `Omega`. For exposure `i`, let `K_i` indicate operational record entry and let `E_i` denote the target event truth or process state.

The full exposure ledger contains all opportunities. The selected event log retains only rows with `K_i=1`.

### Proposition 3 — selected event logs do not identify shadow composition

Fix all entered rows. Two full exposure worlds may agree on every retained row while assigning different event truth to `K=0` exposures. They produce the same event log but different

`q_shadow = P(E=1 | K=0)`.

Therefore `q_shadow` is not identified from the entered event log alone.

This is not a statement about detector quality. It is a statement about the observation map: row deletion is many-to-one.

### Proposition 4 — an exposure ledger identifies the denominator but not necessarily shadow biology

Retaining `(Omega,K)` for all exposure opportunities refines the selected log. It identifies the number and identity of non-entered opportunities. But if `E_i` remains unresolved for those rows, multiple shadow truth assignments remain compatible.

Thus denominator identification and biological identification are distinct.

### Proposition 5 — reference information intended to audit selection must survive selection

Suppose a reference exists for every exposure but is stored only when `K=1`. Worlds that differ only in shadow reference values remain observationally equivalent. No downstream algorithm can reconstruct those values.

If the reference is instead retained independently of `K`, the resulting observation refines the selected-only record and may distinguish shadow worlds.

The design consequence is strong: a reference cannot audit an entry mechanism if the entry mechanism itself determines whether the reference survives.

## 4. Reference-guided measurement refinement

Let a primary measurement be generated by

`Y = F(S,M)`,

where `S` is the target/process state and `M` is measurement-side latent state, including nuisance, visibility, geometry, or sensor state.

A target-free reference does not need to identify a named nuisance. It may instead restrict the compatible measurement-state set to `M(R)`.

Define

`S_F(Y,R) = {s : exists m in M(R) such that F(s,m)=Y}`.

### Proposition 6 — measurement-state refinement contracts the target-compatible set

If

`M(R2) subseteq M(R1)`,

then

`S_F(Y,R2) subseteq S_F(Y,R1)`.

No linearity or Gaussian assumption is needed.

### Proposition 7 — coverage transfers through a valid compatible measurement-state set

If the true measurement state is contained in `M_alpha(R)` with probability at least `1-alpha`, then the true target state is contained in the induced `S_F(Y,R)` with probability at least `1-alpha`, assuming the forward model used to define the compatible relation is valid.

This identifies the empirical burden precisely: not to prove the set-contraction theorem, but to calibrate a physically meaningful `M_alpha(R)` and justify the forward relation.

## 5. Additive special case and the limit of subtraction

For the additive model

`Y=S+N`,

the primary observation alone does not identify `S` and `N`: for any admissible `Delta`,

`S'=S+Delta`, `N'=N-Delta`

produces the same `Y`.

If a reference yields a nuisance-compatible set `N(R)`, then

`S(Y,R) = {Y-n : n in N(R)}`.

### Proposition 8 — additive compatible-set geometry

Under a norm metric,

`diam S(Y,R) = diam N(R)`.

The reference contracts target uncertainty exactly to the extent that it contracts nuisance uncertainty.

### Proposition 9 — projection improves energy ratio only under differential capture

For orthogonal projector `P`, define

`a_S = ||PS||^2 / ||S||^2`

and

`a_N = ||PN||^2 / ||N||^2`.

After residualization `Z=(I-P)Y`, the target-to-nuisance energy-ratio gain is

`(1-a_S)/(1-a_N)`.

Hence the ratio improves if and only if

`a_N > a_S`.

A reference may be highly active and still be harmful if it captures target structure at least as strongly as nuisance structure.

### Proposition 10 — universal non-harm is impossible for nonzero projection on an unrestricted target class

For any nonzero orthogonal projector, its range contains a nonzero target vector. That target is completely removed by residualization.

Therefore no nonzero reference-only projector can guarantee non-harm for every admissible target unless the target class is restricted.

## 6. Reversible decomposition instead of destructive correction

The preceding impossibility result applies to replacing the observation by the residual alone. It does not imply that computing a decomposition is harmful.

Let

`E = PY`,

`Z = (I-P)Y`.

### Proposition 11 — two-channel linear decomposition is reversible

`Y = E + Z`.

If both channels are retained without lossy alteration, the decomposition is exactly invertible. The irreversible step is discarding one channel, not computing the decomposition.

The information-safe design is therefore not generically “subtract nuisance.” It is “retain reference-explained and residual structure, then defer interpretation.” Raw `Y` may additionally be stored as an audit redundancy.

## 7. Semantic evidence and coarsening

Suppose an entered record retains separate positive evidence for target, nuisance, observability, attribution, and unresolved states. A later binary or otherwise smaller vocabulary is a deterministic coarsening.

### Proposition 12 — semantic coarsening cannot increase point-identification coverage

Because coarsening expands compatible fibers, any query point identified from the coarsened state was already point identified from the richer state. The converse need not hold.

Thus ideal safely resolvable coverage is monotone non-increasing under semantic coarsening.

## 8. Decision-theoretic information order

Compatible-set order has an equivalent consequence for decision problems.

### Proposition 13 — richer retained observations cannot worsen optimal risk

For any fixed finite action space and loss, if `O1=h(O2)` then the minimum achievable expected risk using `O2` is no greater than using `O1`. A decision maker with `O2` can always ignore the extra information and emulate the best `O1` rule.

This is an optimal-information statement, not a guarantee about a particular algorithm. A misspecified learner may use richer information badly and perform worse empirically.

This distinction separates information value from implementation quality.

## 9. The three-operation architecture

The structural results yield three different operations.

### Reference refinement

Retain additional valid side information.

Effect: compatible sets contract or stay equal; optimal risk can improve or stay equal.

### Record-entry selection

Map a full exposure universe to selected rows.

Effect: distinct full exposure worlds can collapse to the same retained event log; shadow support and composition may become unidentified.

### Semantic coarsening

Map a rich entered evidence state to fewer labels.

Effect: compatible sets expand or stay equal; point-identification coverage can fall.

These are not three implementations of one algorithm. They are three directions in an information order.

## 10. Why operation order matters

Side information retained before / independently of support selection can inform shadow exposures. Side information stored only for selected rows cannot.

Likewise, rich semantic evidence retained before a binary decision remains available for later reanalysis; information discarded by the binary map does not.

A general design principle follows:

> **Information useful for auditing an irreversible operation must be retained before or independently of that operation.**

This applies to reference regions, exposure ledgers, calibration channels, provenance, and semantic reason codes.

## 11. Relation to the three sister methods

The current implementations occupy different parts of this theory.

- Reference-guided V3 work provides constructive computational approximations to measurement-state refinement.
- REC formalizes support selection before a row exists and demonstrates ecological consequences of record-entry selection.
- TNOA formalizes process-preserving semantic evidence and abstention after a row exists.

Their shared principle is not “use all three.” It is:

> **Refine before loss. Audit what selection removes. Preserve what semantics cannot resolve.**

## 12. Structural claims versus empirical claims

The propositions above are mathematical statements under their stated assumptions. Field data are not required to prove them.

Empirical evidence is required for:

- whether a physical reference strictly contracts a scientifically relevant compatible measurement-state set;
- calibration and finite-sample coverage of that set;
- magnitude and context dependence of record-entry selection;
- practical T/N/U resolution rates;
- approximation error of a learned or projected representation;
- transport to a new application;
- named causal attribution of a disturbance without additional structural or interventional assumptions.

This separation prevents a common category error: treating lack of field validation as a weakness of a structural theorem, or treating a structural theorem as evidence that a particular sensor implementation works in the field.

## 13. Discussion

The usual language of “noise correction” encourages point replacement: estimate a nuisance contribution, subtract it, and proceed as though the residual were the target. The information-order view suggests a different default. A reference should first be treated as side information that contracts compatible measurement states. A computational decomposition may be retained reversibly or propagated as a set. Only then should downstream evidence semantics determine whether a unique interpretation is warranted.

The same logic clarifies record-entry bias. A perfect classifier cannot classify a row that does not exist. Once exposure opportunities are deleted without an independent denominator or reference, the missing distinctions belong to an upstream fiber that no downstream semantics can split. Likewise, once a rich evidence state is collapsed to a binary label, later analysis cannot recover the discarded semantic distinctions from that label alone.

The framework therefore changes the design question from “How do we make the final classifier more accurate?” to three questions: What additional information can refine the observation problem? Which operations irreversibly delete support? Which semantic distinctions are actually identified by the retained evidence?

## 14. Conclusion

Scientific observation pipelines should be ordered by information, not only by computation. Retained side information can refine compatible worlds; record-entry selection can delete exposure support; semantic coarsening can erase distinctions within entered records. Downstream algorithms cannot reconstruct distinctions already collapsed upstream, but independently retained references and provenance can prevent some losses from becoming irreversible.

The compact rule is:

> **add without discarding; select with provenance; interpret without forcing.**

Real-data studies remain essential for estimating how informative a physical reference is, how strong selection is, and how well computational approximations behave. They are tests of application and transport, not prerequisites for the structural information-order results themselves.
