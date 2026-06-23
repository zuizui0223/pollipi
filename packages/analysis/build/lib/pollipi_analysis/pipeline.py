"""End-to-end explainable three-state mesh decision.

Pipeline (Issue #14):

1. optional small global translation registration
2. optional global brightness normalization
3. residual motion image
4. overlapping mesh aggregation (rectangular baseline + half-cell offset)
5. explainable rule-based three-state decision

The output is a :class:`MeshDecision` whose ``state`` is one of the canonical
decision states. A state is never a confirmed pollinator visit; it only informs
whether the *next* scheduled interval should be shorter, unchanged, or longer.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from pollipi_analysis.features.compute import FeatureConfig, compute_features
from pollipi_analysis.schemas.decision import MeshDecision
from pollipi_analysis.schemas.features import MeshFeatures
from pollipi_analysis.schemas.states import (
    ENVIRONMENTAL_NOISE,
    NO_ACTIVITY,
    STRONG_VISITATION_CANDIDATE,
    UNCERTAIN_LOCAL_ACTIVITY,
    DecisionState,
)


@dataclass(frozen=True)
class ClassifierConfig:
    # resting / no-activity gate
    quiet_synchrony: float = 0.0015
    quiet_active_proportion: float = 0.015
    # broad common-mode (environmental noise) gates
    broad_synchrony: float = 0.18
    broad_active_proportion: float = 0.45
    broad_component_fraction: float = 0.25
    shake_shift_px: float = 2.5
    oscillation_overlap: float = 0.6
    oscillation_persistence_max: float = 0.25
    scatter_spatial_concentration: float = 0.35
    # strong localised candidate gates
    strong_concentration: float = 0.35
    strong_spatial_concentration: float = 0.70
    strong_offset_agreement: float = 0.45
    local_active_proportion_max: float = 0.25


@dataclass(frozen=True)
class PipelineConfig:
    features: FeatureConfig = FeatureConfig()
    classifier: ClassifierConfig = ClassifierConfig()


def classify_features(features: MeshFeatures, cfg: ClassifierConfig) -> tuple[DecisionState, str]:
    """Apply the explainable rule cascade to a feature vector.

    Returns ``(state, reason)`` where ``reason`` is a stable token naming the
    branch that fired. Order is intentional: broad-common-mode guard -> resting
    -> remaining common-mode rejection -> strong localised candidate -> uncertain
    residual.
    """
    f = features
    n_cells_component_gate = max(4, int(round((1.0 / max(cfg.broad_component_fraction, 1e-6)))))

    # 1. resting state — only when there is no broad common-mode signal.
    # A full-frame illumination change has global_synchrony ≥ broad_synchrony
    # even though brightness normalisation zeroes out active_cell_proportion;
    # skipping this gate for such frames lets the broad-synchrony rule below fire.
    if (
        f.global_synchrony < cfg.quiet_synchrony
        or f.active_cell_proportion < cfg.quiet_active_proportion
    ) and f.global_synchrony < cfg.broad_synchrony:
        return NO_ACTIVITY, "below_active_cell_threshold"

    # 2. broad / common-mode motion -> environmental noise
    if f.global_synchrony >= cfg.broad_synchrony:
        return ENVIRONMENTAL_NOISE, "broad_global_synchrony"
    if f.active_cell_proportion >= cfg.broad_active_proportion:
        return ENVIRONMENTAL_NOISE, "broad_active_cell_proportion"
    if f.largest_component_cells >= n_cells_component_gate and f.spatial_concentration < cfg.strong_spatial_concentration:
        return ENVIRONMENTAL_NOISE, "large_diffuse_connected_component"
    if f.estimated_global_shift >= cfg.shake_shift_px:
        return ENVIRONMENTAL_NOISE, "global_camera_shift"
    if f.direction_reversal >= cfg.oscillation_overlap and f.persistence <= cfg.oscillation_persistence_max:
        return ENVIRONMENTAL_NOISE, "oscillation_return_to_origin"
    if f.spatial_concentration < cfg.scatter_spatial_concentration:
        return ENVIRONMENTAL_NOISE, "spatially_scattered_motion"

    # 3. strong localised visitation candidate
    if (
        f.concentration >= cfg.strong_concentration
        and f.spatial_concentration >= cfg.strong_spatial_concentration
        and f.active_cell_proportion <= cfg.local_active_proportion_max
        and f.offset_agreement >= cfg.strong_offset_agreement
    ):
        return STRONG_VISITATION_CANDIDATE, "localized_concentrated_offset_agreement"

    # 4. localised but ambiguous (low SNR, mixed target+noise) -> uncertain
    return UNCERTAIN_LOCAL_ACTIVITY, "localized_but_ambiguous"


def analyze(
    frame,
    background,
    *,
    config: Optional[PipelineConfig] = None,
    previous_active_cells: Optional[set[tuple[int, int]]] = None,
    previous_centroid: Optional[tuple[float, float]] = None,
) -> MeshDecision:
    """Run the full pipeline on one frame pair and return a three-state decision."""
    cfg = config or PipelineConfig()
    features, active = compute_features(
        frame,
        background,
        config=cfg.features,
        previous_active_cells=previous_active_cells,
        previous_centroid=previous_centroid,
    )
    state, reason = classify_features(features, cfg.classifier)
    return MeshDecision(state=state, reason=reason, features=features, active_cells=frozenset(active))
