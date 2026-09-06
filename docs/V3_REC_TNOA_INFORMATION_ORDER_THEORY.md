# V3–REC–TNOA information-order theory

Status: **conceptual-mathematical core**. This note unifies the sister architecture at the level of information order. It does not change the closed REC H1–H5 manuscript or the frozen TNOA Paper-1 claim, and it does not assert real-domain V3 performance.

## 1. One mathematical object: the compatible-world fiber

Let `W` be a latent world, `theta(W)` the scientific query, and

`O : W -> X`

an observation map.

For realized world `w`, define the compatible-world fiber

`F_O(w) = {w' : O(w') = O(w)}`.

The corresponding identified set is

`I_O(w) = {theta(w') : w' in F_O(w)}`.

Everything below is an order statement about these fibers.

## 2. Theorem A — side-information refinement

Let an additional channel be

`R : W -> Z`,

and retain the original observation rather than replace it:

`O_plus(w) = (O(w), R(w))`.

Then

`F_O_plus(w) subseteq F_O(w)`

and therefore

`I_O_plus(w) subseteq I_O(w)`.

### Proof

Any world matching both `O(w)` and `R(w)` necessarily matches `O(w)`. QED.

This is the generic mathematical role of a target-free reference. It may give strict refinement, no refinement, or an empirically miscalibrated restriction in an implementation; the structural theorem only says that *retained valid side information cannot make the compatible set larger*.

## 3. Theorem B — downstream post-processing cannot recover lost distinctions

Let

`C : X -> Z`

be any deterministic downstream transformation and define

`O_C = C o O`.

Then

`F_O(w) subseteq F_O_C(w)`

and

`I_O(w) subseteq I_O_C(w)`.

### Proof

If `O(w') = O(w)`, then applying the same deterministic function gives `C(O(w')) = C(O(w))`. QED.

### Corollary — no downstream recovery

If two worlds `w1,w2` have

`O(w1) = O(w2)`

but

`theta(w1) != theta(w2)`,

then no deterministic downstream algorithm `G` using only `O` can distinguish them, because

`G(O(w1)) = G(O(w2))`.

This is the abstract form of both:

- REC's statement that perfect downstream semantics cannot reconstruct a true row that never entered the record;
- TNOA's statement that a later classifier cannot reconstruct distinctions already removed by semantic coarsening.

## 4. REC as support-selection coarsening

Let a full exposure ledger contain rows indexed by `i in Omega`, with event truth `E_i` and record-entry indicator `K_i`.

Define the entered event log as the deterministic selection map

`L_enter = S_K(L_full) = {row_i : K_i = 1}`.

Unless all omitted rows are recoverable from retained provenance, `S_K` is many-to-one: distinct full ledgers can produce the same entered event log.

### Proposition C — shadow composition is not identified from the selected log

Fix any entered rows. Construct two full ledgers with identical `K=1` rows but different event truth on `K=0` exposures. They have the same selected log but different

`q_shadow = P(E=1 | K=0)`.

Therefore the event log alone cannot identify shadow composition.

This is the REC non-identifiability witness expressed as a fiber statement.

## 5. Exposure-ledger refinement identifies the denominator, not automatically the shadow biology

Retain a gate-independent exposure universe and entry provenance:

`O_ledger = (Omega, K, entered_rows)`.

Relative to the event log alone, this is side information and therefore refines the compatible-world set.

It identifies:

- the number and identity of `K=0` exposure opportunities;
- layer-specific A/R/K provenance when retained.

But if `E_i` for `K=0` remains unobserved, multiple shadow truth assignments are still compatible. Thus denominator identification is weaker than biological point identification.

This reproduces the REC distinction:

`Omega necessary != Omega sufficient`.

## 6. TNOA as semantic coarsening

Let `E_rich` retain separate positive target, nuisance, observability and attribution support, including unresolved states.

Let

`c(E_rich)`

be a deterministic binary or otherwise coarser decision.

By Theorem B,

`F_E_rich(w) subseteq F_c(E_rich)(w)`.

Semantic coarsening cannot create information about distinctions that it discards.

## 7. V3/reference refinement is the opposite-signed operation

V3/reference-guided theory is not another coarsening stage. Its generic role is to retain side information about measurement state.

For

`Y = F(S,M)`

and target-free reference `R`, let the reference restrict compatible measurement states to `M(R)` and define

`S_F(Y,R) = {s : exists m in M(R) with F(s,m)=Y}`.

When a more informative reference validly contracts `M(R)`, the compatible target set contracts.

Thus:

- V3/reference refinement tends toward smaller compatible sets;
- REC row selection tends to collapse distinct full exposure worlds into the same entered log;
- TNOA semantic coarsening tends to collapse distinct rich evidence states into the same downstream label.

## 8. The fundamental three-operation order

The sister architecture can therefore be written as:

```text
SIDE INFORMATION / REFINEMENT
    retain primary + reference
    compatible fiber contracts or stays equal

SUPPORT SELECTION / REC
    drop non-entered rows unless Omega/provenance is retained
    distinct full exposure worlds can collapse

SEMANTIC COARSENING / TNOA downstream collapse
    map rich evidence to fewer states
    compatible fiber expands or stays equal
```

The key rule is not that all three modules must be used. It is:

> **Add information before irreversible loss; preserve provenance at support-selection boundaries; preserve multiplicity at semantic boundaries.**

## 9. Theorem D — post-selection side information cannot repair a side channel that was never retained for omitted rows

Suppose a reference `R_i` exists in the physical world for every `i in Omega`, but the data system stores `R_i` only when `K_i=1`.

Then the retained observation is

`O_post = {entered row_i, R_i : K_i=1}`.

For any two worlds that agree on all `K=1` rows and references but differ only in `R_i` or `E_i` on `K=0` exposures,

`O_post(w1) = O_post(w2)`.

No downstream algorithm can recover those omitted reference values or use them to split the shadow-world fiber.

By contrast, storing

`O_pre = (Omega, K, R_all, entered_rows)`

before / independently of entry yields a refinement of `O_post` and may split those worlds.

### Design consequence

A reference intended to audit selection must be collected or retained independently of the selection rule it is meant to audit.

## 10. Theorem E — optimal decision-risk order

For a fixed finite decision problem and loss, if observation `O2` refines `O1` because `O1 = h(O2)` for some deterministic `h`, then the minimum achievable risk under `O2` is no greater than under `O1`.

Reason: any rule using `O1` can be emulated by an `O2` rule that first computes `h` and ignores the extra information.

Therefore:

- retained valid side information cannot worsen the *optimal* risk;
- support or semantic coarsening cannot improve the *optimal* risk;
- an implemented learner can nevertheless perform worse because it may use richer information badly or fail to represent the correct compatible sets.

This distinction explains why the synthetic V3–TNOA bridge could show genuine information gain while still failing the frozen false-certainty gate.

## 11. Non-commutation of observation and loss

The timing of information retention matters.

If a side channel is retained for every exposure before selection, it can inform both entered and shadow exposures.

If selection occurs first and the side channel is stored only for selected rows, the shadow side information is gone. No later transformation can reconstruct it without additional assumptions.

So, in general,

`retain-reference-before-selection`

is strictly more informative than

`select-first-then-retain-reference-on-selected-rows`.

This is a design theorem, not merely an implementation preference.

## 12. Relation to current repositories

### PolliPi / V3 theory

Hosts executable witnesses for:

- reference refinement;
- reversible / set-valued measurement decomposition;
- projection trade-offs;
- compatible-set and decision-risk monotonicity.

### REC

Owns the support-selection problem:

- `Omega`;
- A/R/K provenance;
- shadow composition;
- ecological-estimand distortion caused by entry selection;
- transport of entry correction.

Current REC H1–H5 remains a separate closed empirical manuscript.

### TNOA

Owns semantic entitlement:

- positive non-complementary evidence axes;
- T/N/U and observability / attribution boundaries;
- partial identification;
- safe resolvable coverage under a false-certainty budget;
- consequences of later semantic coarsening.

## 13. What is structural versus empirical

Structural, no field data required:

- side-information fiber contraction;
- post-processing fiber expansion;
- no-downstream-recovery corollary;
- REC selected-log non-identifiability;
- exposure-ledger denominator refinement;
- semantic-coarsening monotonicity;
- optimal decision-risk order;
- pre-selection retention dominance over selected-only side-information retention.

Empirical:

- whether a physical reference is scientifically informative;
- whether its compatible set is calibrated;
- how strong REC selection is in a real system;
- how often TNOA evidence is uniquely resolvable;
- how approximate observers behave at finite sample size;
- transport across contexts.

## 14. Compact synthesis

The three sister operations are best summarized as:

> **Refine before loss. Audit what selection removes. Preserve what semantics cannot yet resolve.**

Or operationally:

> **add without discarding; select with provenance; interpret without forcing.**
