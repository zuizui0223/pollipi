"""Motion detection algorithms extracted from TimelapseController.

All functions are pure (no I/O) and work on numpy arrays so they can be
unit-tested without a camera attached.
"""
from __future__ import annotations

from typing import Optional


def detect_motion(
    frame,
    background,
    pixel_difference: int,
    motion_ratio: float,
    roi: Optional[tuple[int, int, int, int]] = None,
    control_roi: Optional[tuple[int, int, int, int]] = None,
    grid_shape: tuple[int, int] = (4, 4),
    monitor_size: tuple[int, int] = (640, 360),
):
    """
    Compare *frame* against *background* and return ``(metrics, detected, new_background)``.

    Parameters
    ----------
    frame:
        Raw lores YUV420 array from the camera.
    background:
        Previous luminance plane (or ``None`` on first call).
    pixel_difference:
        Per-pixel absolute difference threshold.
    motion_ratio:
        Minimum fraction of changed pixels to consider motion.
    roi:
        Optional ``(x, y, w, h)`` region of interest.
    monitor_size:
        ``(width, height)`` of the lores monitor frame.

    Returns
    -------
    tuple[dict, bool, array]
        *metrics* dict, *detected* bool, updated *background* array.
    """
    import numpy as np

    w, h = monitor_size
    full_luminance = frame[:h, :w].astype(np.float32)
    roi_used = roi is not None
    if roi_used:
        x, y, width, height = roi
        luminance = full_luminance[y:y + height, x:x + width]
    else:
        x, y, width, height = None, None, None, None
        luminance = full_luminance
    mean_brightness = float(luminance.mean())
    control_luminance = None
    if control_roi is not None:
        cx, cy, cwidth, cheight = control_roi
        control_luminance = full_luminance[cy:cy + cheight, cx:cx + cwidth]
    else:
        cx, cy, cwidth, cheight = None, None, None, None
    rows, cols = grid_shape
    metrics: dict = {
        "motion_score": None,
        "changed_area_ratio": None,
        "mean_brightness": mean_brightness,
        "brightness_delta": None,
        "roi_used": roi_used,
        "roi_x": x,
        "roi_y": y,
        "roi_w": width,
        "roi_h": height,
        "roi_semantics": "floral_display_zone",
        "control_roi_used": control_roi is not None,
        "control_roi_x": cx,
        "control_roi_y": cy,
        "control_roi_w": cwidth,
        "control_roi_h": cheight,
        "floral_zone_score": None,
        "background_control_score": None,
        "zone_minus_control_score": None,
        "grid_rows": rows,
        "grid_cols": cols,
        "changed_cell_count": 0,
        "changed_cell_ratio": None,
        "local_compactness": None,
        "whole_frame_change_score": None,
        "previous_frame_elapsed_sec": None,
        "robust_background_score": None,
        "candidate_reasons": "",
        "wind_like_motion": False,
        "num_blobs": 0,
        "largest_blob_area": 0,
        "largest_blob_ratio": None,
        "small_blob_count": 0,
        "motion_type": "none",
    }
    if background is None:
        return metrics, False, luminance

    changed = np.abs(luminance - background) >= pixel_difference
    changed_area_ratio = float(changed.mean())
    whole_changed = np.abs(full_luminance - float(background.mean())) >= pixel_difference
    whole_frame_change_score = float(whole_changed.mean())
    control_score = None
    if control_luminance is not None:
        control_changed = np.abs(control_luminance - float(background.mean())) >= pixel_difference
        control_score = float(control_changed.mean())
    grid_metrics = grid_change_metrics(changed, rows, cols)
    brightness_delta = abs(float(mean_brightness - float(background.mean())))
    blob_m = blob_metrics(changed)
    motion_type = classify_motion(
        changed_area_ratio=changed_area_ratio,
        brightness_delta=brightness_delta,
        largest_blob_ratio=blob_m["largest_blob_ratio"] or 0.0,
        small_blob_count=blob_m["small_blob_count"],
        motion_ratio=motion_ratio,
    )
    metrics.update(
        {
            "motion_score": changed_area_ratio,
            "changed_area_ratio": changed_area_ratio,
            "floral_zone_score": changed_area_ratio,
            "background_control_score": control_score,
            "zone_minus_control_score": None if control_score is None else changed_area_ratio - control_score,
            "whole_frame_change_score": whole_frame_change_score,
            **grid_metrics,
            "brightness_delta": brightness_delta,
            "wind_like_motion": motion_type == "wind_like_large_motion" or changed_area_ratio >= 0.20,
            **blob_m,
            "motion_type": motion_type,
            "candidate_reasons": candidate_reasons(motion_type, changed_area_ratio, control_score, grid_metrics),
        }
    )
    detected = motion_type == "small_object_motion"
    if not detected:
        background = (background * 0.9) + (luminance * 0.1)
    return metrics, detected, background


def grid_change_metrics(mask, rows: int, cols: int) -> dict:
    import numpy as np

    rows = max(1, rows)
    cols = max(1, cols)
    height, width = mask.shape
    changed_cells = 0
    cell_scores = []
    for y0 in np.linspace(0, height, rows, endpoint=False, dtype=int):
        y1 = min(height, y0 + max(1, height // rows))
        for x0 in np.linspace(0, width, cols, endpoint=False, dtype=int):
            x1 = min(width, x0 + max(1, width // cols))
            score = float(mask[y0:y1, x0:x1].mean()) if y1 > y0 and x1 > x0 else 0.0
            cell_scores.append(score)
            if score > 0:
                changed_cells += 1
    total_cells = rows * cols
    changed_cell_ratio = changed_cells / total_cells if total_cells else 0.0
    local_compactness = max(cell_scores) / (sum(cell_scores) + 1e-9) if cell_scores else 0.0
    return {
        "changed_cell_count": changed_cells,
        "changed_cell_ratio": changed_cell_ratio,
        "local_compactness": local_compactness,
    }


def candidate_reasons(
    motion_type: str,
    floral_zone_score: float,
    control_score: Optional[float],
    grid_metrics: dict,
) -> str:
    reasons = [motion_type]
    if control_score is not None:
        reasons.append("zone_gt_control" if floral_zone_score > control_score else "control_matches_zone")
    if (grid_metrics.get("local_compactness") or 0) >= 0.45:
        reasons.append("localized_change")
    if (grid_metrics.get("changed_cell_ratio") or 0) >= 0.5:
        reasons.append("broad_zone_change")
    return ";".join(reasons)


def blob_metrics(mask) -> dict:
    """Connected-component analysis on a boolean change mask."""
    height, width = mask.shape
    total_pixels = height * width
    visited = mask.copy()
    num_blobs = 0
    largest_blob_area = 0
    small_blob_count = 0
    small_blob_max = max(20, int(total_pixels * 0.03))

    for start_y, start_x in zip(*mask.nonzero()):
        if not visited[start_y, start_x]:
            continue
        num_blobs += 1
        visited[start_y, start_x] = False
        area = 0
        stack = [(int(start_y), int(start_x))]
        while stack:
            y, x = stack.pop()
            area += 1
            for next_y, next_x in (
                (y - 1, x), (y + 1, x), (y, x - 1), (y, x + 1),
                (y - 1, x - 1), (y - 1, x + 1), (y + 1, x - 1), (y + 1, x + 1),
            ):
                if 0 <= next_y < height and 0 <= next_x < width and visited[next_y, next_x]:
                    visited[next_y, next_x] = False
                    stack.append((next_y, next_x))
        largest_blob_area = max(largest_blob_area, area)
        if 4 <= area <= small_blob_max:
            small_blob_count += 1

    largest_blob_ratio = (largest_blob_area / total_pixels) if total_pixels else None
    return {
        "num_blobs": num_blobs,
        "largest_blob_area": largest_blob_area,
        "largest_blob_ratio": largest_blob_ratio,
        "small_blob_count": small_blob_count,
    }


def classify_motion(
    changed_area_ratio: float,
    brightness_delta: float,
    largest_blob_ratio: float,
    small_blob_count: int,
    motion_ratio: float,
) -> str:
    """Rule-based motion type classifier. Returns one of the motion-type strings."""
    if changed_area_ratio < motion_ratio:
        return "none"
    if abs(brightness_delta) >= 20 and changed_area_ratio >= 0.05:
        return "global_brightness_change"
    if changed_area_ratio >= 0.20 or largest_blob_ratio >= 0.15:
        return "wind_like_large_motion"
    if small_blob_count > 0:
        return "small_object_motion"
    return "noisy_motion"
