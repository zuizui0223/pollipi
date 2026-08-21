"""Policy-level contradiction benchmark for parallel PolliPi/InsePi development.

This module intentionally does *not* import InsePi.  It exposes PolliPi's own
response to a small, deterministic set of latent ecological/observation
conditions.  The sibling InsePi repository implements the same scenario IDs
from its noise-first point of view.  The two JSONL traces can then be joined
without forcing either project to adopt the other's assumptions.

The benchmark is deliberately one layer above rendered pixels.  It asks a
narrow question first: when the latent world contains a true local visit and a
specific observation disturbance, what does the current PolliPi decision rule
do?  Visual/hardware-in-the-loop parity is a later benchmark layer.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
from pathlib import Path
from typing import Iterable

from pollipi_analysis.pipeline import ClassifierConfig, classify_features
from pollipi_analysis.schemas.features import MeshFeatures


CONTRADICTION_SCHEMA = "pollipi-insepi-contradiction-v1"


@dataclass(frozen=True, slots=True)
class ContrastScenario:
    scenario_id: str
    true_visit: bool
    noise_source: str
    noise_confidence: float
    event_visibility: float


@dataclass(frozen=True, slots=True)
class PolliPiContrastResult:
    schema: str
    scenario_id: str
    true_visit: bool
    noise_source: str
    noise_confidence: float
    event_visibility: float
    pollipi_state: str
    pollipi_reason: str
    capture_posture: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


# Keep these IDs stable.  InsePi carries the same latent contract but computes
# observability/risk rather than PolliPi mesh states.
CONTRAST_SCENARIOS: tuple[ContrastScenario, ...] = (
    ContrastScenario("quiet_absence", False, "stable_scene", 1.00, 0.00),
    ContrastScenario("clean_visit", True, "stable_scene", 1.00, 1.00),
    ContrastScenario("wind_absence", False, "background_vegetation_motion", 0.95, 0.00),
    ContrastScenario("wind_visit", True, "background_vegetation_motion", 0.95, 0.65),
    ContrastScenario("shake_absence", False, "global_camera_shake", 0.95, 0.00),
    ContrastScenario("shake_visit", True, "global_camera_shake", 0.95, 0.55),
    ContrastScenario("shadow_absence", False, "shadow_transient", 0.95, 0.00),
    ContrastScenario("shadow_visit", True, "shadow_transient", 0.95, 0.60),
    ContrastScenario("occluded_visit", True, "occlusion", 0.95, 0.18),
    ContrastScenario("blurred_visit", True, "blur_or_focus_loss", 0.95, 0.22),
    ContrastScenario("clutter_visit", True, "multi_object_clutter", 0.95, 0.70),
    ContrastScenario("unknown_visit", True, "unknown", 0.80, 0.55),
)


def synthesize_mesh_features(scenario: ContrastScenario) -> MeshFeatures:
    """Translate latent truth into deterministic PolliPi-like mesh evidence.

    The translation models measurement consequences, not desired decisions:
    local visits add compact evidence; broad vegetation, shake and shadows add
    common-mode evidence; occlusion/blur attenuate local evidence; clutter
    disperses it.  The ordinary PolliPi classifier then decides from those
    features unchanged.
    """

    # Quiet background defaults.
    active = 0.004
    component = 1
    concentration = 0.08
    spatial = 0.82
    offset_active = 0.004
    offset_agreement = 0.10
    global_sync = 0.0008
    global_shift = 0.10
    max_pool = 0.0

    if scenario.true_visit:
        visibility = scenario.event_visibility
        active += 0.075 * visibility
        component = 2
        concentration = 0.20 + 0.58 * visibility
        spatial = 0.55 + 0.32 * visibility
        offset_active = active * 0.95
        offset_agreement = 0.20 + 0.58 * visibility
        # A visible local event still contributes some frame-level synchrony.
        # Without this measurement consequence the existing PolliPi quiet gate
        # would (correctly for its inputs) interpret an impossible combination:
        # high compact activity with essentially zero global residual signal.
        global_sync = max(global_sync, 0.003 + 0.035 * visibility)
        max_pool = max(0.018, 0.065 * visibility)

    source = scenario.noise_source
    strength = scenario.noise_confidence
    if source == "background_vegetation_motion":
        active = max(active, 0.52 * strength)
        component = max(component, 7)
        concentration *= 0.65
        spatial = min(spatial, 0.30)
        offset_active = max(offset_active, 0.48 * strength)
        offset_agreement *= 0.65
        global_sync = max(global_sync, 0.10 * strength)
    elif source == "global_camera_shake":
        active = max(active, 0.36 * strength)
        component = max(component, 8)
        concentration *= 0.60
        spatial = min(spatial, 0.42)
        offset_active = max(offset_active, 0.34 * strength)
        global_sync = max(global_sync, 0.72 * strength)
        global_shift = max(global_shift, 4.2 * strength)
    elif source == "shadow_transient":
        active = max(active, 0.28 * strength)
        component = max(component, 8)
        concentration *= 0.70
        spatial = min(spatial, 0.46)
        offset_active = max(offset_active, 0.26 * strength)
        global_sync = max(global_sync, 0.58 * strength)
    elif source == "occlusion":
        # A real visit is mostly hidden: only a faint compact residue survives.
        active = min(active, 0.010)
        component = 1
        concentration = 0.30
        spatial = 0.76
        offset_active = 0.009
        offset_agreement = 0.38
        global_sync = 0.001
        max_pool = 0.035
    elif source == "blur_or_focus_loss":
        active = min(active, 0.012)
        component = 1
        concentration = 0.28
        spatial = 0.72
        offset_active = 0.011
        offset_agreement = 0.34
        global_sync = 0.001
        max_pool = 0.042
    elif source == "multi_object_clutter":
        active = max(active, 0.31)
        component = max(component, 5)
        concentration = min(concentration, 0.31)
        spatial = min(spatial, 0.29)
        offset_active = max(offset_active, 0.28)
        offset_agreement = min(offset_agreement, 0.32)
        global_sync = max(global_sync, 0.09)
    elif source == "unknown":
        active = max(active, 0.11)
        component = max(component, 3)
        concentration = min(concentration, 0.44)
        spatial = min(spatial, 0.54)
        offset_active = max(offset_active, 0.10)
        offset_agreement = min(offset_agreement, 0.36)
        global_sync = max(global_sync, 0.08)

    return MeshFeatures(
        active_cell_proportion=float(active),
        largest_component_cells=int(component),
        concentration=float(concentration),
        spatial_concentration=float(spatial),
        offset_active_cell_proportion=float(offset_active),
        offset_agreement=float(offset_agreement),
        persistence=0.50 if scenario.true_visit else 0.05,
        centroid_x=0.5 if scenario.true_visit else None,
        centroid_y=0.5 if scenario.true_visit else None,
        centroid_displacement=0.08 if scenario.true_visit else None,
        path_efficiency=0.75 if scenario.true_visit else None,
        active_set_jaccard=0.45 if scenario.true_visit else 0.0,
        global_synchrony=float(global_sync),
        estimated_global_shift=float(global_shift),
        cell_size=16,
        active_proportion_mean=float(active),
        active_proportion_max=float(max_pool),
    )


def capture_posture_for_state(state: str) -> str:
    """Summarise the direction of PolliPi's current evidence allocation."""

    if state == "strong_visitation_candidate":
        return "candidate_priority"
    if state == "uncertain_local_activity":
        return "candidate_caution"
    if state == "environmental_noise":
        return "noise_suppressed"
    if state == "no_activity":
        return "quiet_sparse"
    return "unknown"


def run_contradiction_scenarios(
    scenarios: Iterable[ContrastScenario] = CONTRAST_SCENARIOS,
    *,
    classifier: ClassifierConfig | None = None,
) -> list[PolliPiContrastResult]:
    """Run the stable latent scenario contract through PolliPi unchanged."""

    cfg = classifier or ClassifierConfig()
    rows: list[PolliPiContrastResult] = []
    for scenario in scenarios:
        state, reason = classify_features(synthesize_mesh_features(scenario), cfg)
        rows.append(
            PolliPiContrastResult(
                schema=CONTRADICTION_SCHEMA,
                scenario_id=scenario.scenario_id,
                true_visit=scenario.true_visit,
                noise_source=scenario.noise_source,
                noise_confidence=scenario.noise_confidence,
                event_visibility=scenario.event_visibility,
                pollipi_state=state,
                pollipi_reason=reason,
                capture_posture=capture_posture_for_state(state),
            )
        )
    return rows


def write_contradiction_trace_jsonl(path: str | Path) -> Path:
    """Write a portable trace that can be joined with the InsePi trace."""

    output = Path(path)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as handle:
        for row in run_contradiction_scenarios():
            handle.write(json.dumps(row.to_dict(), sort_keys=True) + "\n")
    return output
