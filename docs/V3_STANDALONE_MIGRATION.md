# V3 standalone migration

Status: **canonical scientific home moved**.

The V3 reference-guided information-refinement line has moved to:

`https://github.com/zuizui0223/v3`

Canonical standalone merge:

`41e3b8df015489df55e6656add368d8b776426a3`

## What remains in PolliPi

PolliPi retains the historical V2/V3 simulation implementations, fixed PolliPi observer adapters, trajectory bridge implementation, Pi capture/intake tools and physical validation harness. These files are retained for provenance and reproducibility; they no longer define the canonical V3 scientific API.

## What moved to `v3`

- application-independent compatible-world / identified-set theory;
- reversible reference-guided decomposition;
- exact projection target/nuisance trade-off;
- set-valued partial decomposition;
- general forward-model formulation;
- finite decision-risk and information-order witnesses;
- V3/REC/TNOA sister-method boundary;
- standalone temporal-subspace decomposition API;
- 12-theorem ledger;
- frozen synthetic/bridge evidence summary;
- current theory manuscript draft;
- PolliPi source provenance map.

## Development rule

New V3 scientific-method development should occur in `zuizui0223/v3`.

PolliPi should change only when a V3 method needs a PolliPi-specific acquisition/validation adapter. PolliPi-specific validation must not silently redefine the generic V3 theory.

REC (`zuizui0223/rec`) and TNOA (`zuizui0223/tnoa`) remain separate sister methods/papers.
