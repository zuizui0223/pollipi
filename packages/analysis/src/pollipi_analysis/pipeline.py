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
    # faint-compact target recovery: a low-SNR target's cell-mean activity can fall
    # below the quiet threshold while the per-cell max-pool aggregation still keeps
    # its small compact hot-spot. On an otherwise-quiet frame a max-pool peak in
    # (0, faint_max_pool_proportion] with low mean activity escalates to uncertain.
    faint_max_pool_proportion: float = 0.06
    faint_local_active_proportion: float = 0.02
    # broad common-mode (environmental noise) gates
    broad_synchrony: float = 0.18
    broad_active_proportion: float = 0.45
    broad_component_fraction: float = 0.25
    shake_shift_px: float = 2.5
    scatter_spatial_concentration: float = 0.35
    # strong localised candidate gates. strong_concentration 0.40 (not 0.35): a
    # swaying flower produced a low-concentration (~0.38) compact blob that squeaked
    # past 0.35 and fired a false video; real targets sit at >=0.49, so 0.40 rejects
    # the sway with no measured loss of real-target strong detection.
    strong_concentration: float = 0.40
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
        # Faint-compact target recovery: the cell mean missed it, but the max-pool
        # aggregation kept a small compact peak (a low-SNR visitor). Escalate to
        # uncertain instead of resting. Uncertain only — never strong/video — so a
        # stray quiet-frame peak costs at most a faster still, never a clip.
        max_pool = f.active_proportion_max or 0.0
        if (
            0.0 < max_pool <= cfg.faint_max_pool_proportion
            and f.active_cell_proportion <= cfg.faint_local_active_proportion
        ):
            return UNCERTAIN_LOCAL_ACTIVITY, "faint_compact_max_pool"
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
    # NOTE: a former "oscillation_return_to_origin" rule
    # (active_set_jaccard >= 0.6 AND persistence <= 0.25) was removed: with the
    # current metric definitions it is unsatisfiable (Jaccard >= 0.6 forces
    # persistence >= 0.6), so it never fired. Genuine multi-frame oscillation /
    # return-to-origin discrimination is a V2 candidate, not implemented in V1.
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
