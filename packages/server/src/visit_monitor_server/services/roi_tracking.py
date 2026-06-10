"""ROI template-matching tracker extracted from TimelapseController."""
from __future__ import annotations

from typing import Optional

from visit_monitor_server.config import MONITOR_SIZE


def new_roi_tracker(roi: Optional[tuple[int, int, int, int]], enabled: bool) -> Optional[dict]:
    """
    Create a fresh tracker state dict, or return ``None`` if tracking is disabled.
    """
    if not (enabled and roi is not None):
        return None
    x, y, width, height = roi
    return {
        "template": None,
        "initial_roi": (x, y, width, height),
        "current_roi": (x, y, width, height),
        "success": False,
        "score": None,
    }


def tracking_roi_for_frame(
    frame,
    tracker: Optional[dict],
    roi_search_margin: int,
    roi_tracking_min_score: float,
) -> Optional[tuple[int, int, int, int]]:
    """Update *tracker* in-place and return the active ROI for this frame."""
    if tracker is None:
        return None
    import numpy as np

    luminance = frame[: MONITOR_SIZE[1], : MONITOR_SIZE[0]].astype(np.float32)
    current_roi = tracker["current_roi"]
    x, y, width, height = current_roi
    if tracker["template"] is None:
        tracker["template"] = luminance[y: y + height, x: x + width].copy()
        tracker["score"] = 1.0
        tracker["success"] = True
        return current_roi

    best_roi, best_score = match_template_near_roi(
        luminance, tracker["template"], current_roi, roi_search_margin
    )
    tracker["score"] = best_score
    if best_roi is not None and best_score is not None and best_score >= roi_tracking_min_score:
        tracker["current_roi"] = best_roi
        tracker["success"] = True
    else:
        tracker["success"] = False
    return tracker["current_roi"]


def match_template_near_roi(
    luminance,
    template,
    current_roi: tuple[int, int, int, int],
    search_margin: int,
) -> tuple[Optional[tuple[int, int, int, int]], Optional[float]]:
    """NCC-based template match within a search window around *current_roi*."""
    import numpy as np

    x, y, width, height = current_roi
    margin = max(0, int(search_margin))
    search_x0 = max(0, x - margin)
    search_y0 = max(0, y - margin)
    search_x1 = min(MONITOR_SIZE[0], x + width + margin)
    search_y1 = min(MONITOR_SIZE[1], y + height + margin)
    search = luminance[search_y0:search_y1, search_x0:search_x1]
    if search.shape[0] < height or search.shape[1] < width:
        return current_roi, None

    try:
        import cv2  # type: ignore

        result = cv2.matchTemplate(
            search.astype(np.float32), template.astype(np.float32), cv2.TM_CCOEFF_NORMED
        )
        _, best_score, _, best_location = cv2.minMaxLoc(result)
        best_x = search_x0 + int(best_location[0])
        best_y = search_y0 + int(best_location[1])
        return (best_x, best_y, width, height), float(best_score)
    except Exception:
        pass

    # Pure-numpy fallback (slower but dependency-free)
    template_small = template
    search_small = search
    scale = max(1, min(width, height) // 80)
    if scale > 1:
        template_small = template[::scale, ::scale]
        search_small = search[::scale, ::scale]
    th, tw = template_small.shape
    sh, sw = search_small.shape
    if sh < th or sw < tw:
        return current_roi, None
    template_centered = template_small - float(template_small.mean())
    template_norm = float(np.sqrt((template_centered * template_centered).sum()))
    if template_norm <= 1e-6:
        return current_roi, None
    best_score_val = -1.0
    best_xy = (0, 0)
    for yy in range(0, sh - th + 1):
        for xx in range(0, sw - tw + 1):
            patch = search_small[yy: yy + th, xx: xx + tw]
            patch_centered = patch - float(patch.mean())
            patch_norm = float(np.sqrt((patch_centered * patch_centered).sum()))
            if patch_norm <= 1e-6:
                continue
            score = float((template_centered * patch_centered).sum() / (template_norm * patch_norm))
            if score > best_score_val:
                best_score_val = score
                best_xy = (xx, yy)
    best_x = search_x0 + int(best_xy[0] * scale)
    best_y = search_y0 + int(best_xy[1] * scale)
    return (
        max(0, min(best_x, MONITOR_SIZE[0] - width)),
        max(0, min(best_y, MONITOR_SIZE[1] - height)),
        width,
        height,
    ), best_score_val


def tracking_metrics(
    tracker: Optional[dict],
    active_roi: Optional[tuple[int, int, int, int]],
    roi_search_margin: int,
    roi_tracking_min_score: float,
) -> dict:
    """Return a flat metrics dict describing the current tracker state."""
    initial = tracker["initial_roi"] if tracker else None
    tracked = tracker["current_roi"] if tracker else active_roi
    shift_x = tracked[0] - initial[0] if initial and tracked else None
    shift_y = tracked[1] - initial[1] if initial and tracked else None
    return {
        "roi_tracking": bool(tracker is not None),
        "roi_tracking_success": bool(tracker.get("success")) if tracker else False,
        "roi_tracking_score": tracker.get("score") if tracker else None,
        "roi_search_margin": roi_search_margin,
        "roi_tracking_min_score": roi_tracking_min_score,
        "initial_roi_x": initial[0] if initial else None,
        "initial_roi_y": initial[1] if initial else None,
        "initial_roi_w": initial[2] if initial else None,
        "initial_roi_h": initial[3] if initial else None,
        "tracked_roi_x": tracked[0] if tracked else None,
        "tracked_roi_y": tracked[1] if tracked else None,
        "tracked_roi_w": tracked[2] if tracked else None,
        "tracked_roi_h": tracked[3] if tracked else None,
        "roi_shift_x": shift_x,
        "roi_shift_y": shift_y,
    }
