"""Route handler for /roi/suggest."""
from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from visit_monitor_server.api.schemas.roi import RoiSuggestionResponse
from visit_monitor_server.config import FLOWER_ROI_MODEL, MONITOR_SIZE
from visit_monitor_server.services import get_controller

router = APIRouter(tags=["roi"])


@router.get("/roi/suggest", response_model=RoiSuggestionResponse)
def suggest_roi() -> RoiSuggestionResponse:
    model_path = Path(FLOWER_ROI_MODEL).expanduser() if FLOWER_ROI_MODEL else None
    if model_path is None or not model_path.is_file():
        return RoiSuggestionResponse(
            available=False,
            suggested=False,
            model_path=str(model_path) if model_path else None,
            message="No flower ROI model is configured. Use manual ROI drawing.",
        )
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return RoiSuggestionResponse(
            available=False,
            suggested=False,
            model_path=str(model_path),
            message="OpenCV is not available, so automatic ROI suggestion is disabled.",
        )
    try:
        frame_bytes = get_controller().preview_frame()
        image_array = np.frombuffer(frame_bytes, dtype=np.uint8)
        image = cv2.imdecode(image_array, cv2.IMREAD_GRAYSCALE)
        if image is None:
            raise ValueError("preview image could not be decoded")
        resized = cv2.resize(image, MONITOR_SIZE)
        detector = cv2.CascadeClassifier(str(model_path))
        if detector.empty():
            return RoiSuggestionResponse(
                available=False,
                suggested=False,
                model_path=str(model_path),
                message="The configured ROI model could not be loaded.",
            )
        boxes = detector.detectMultiScale(resized, scaleFactor=1.08, minNeighbors=3, minSize=(20, 20))
        if len(boxes) == 0:
            return RoiSuggestionResponse(
                available=True,
                suggested=False,
                model_path=str(model_path),
                message="No flower-like ROI was suggested. Use manual drawing.",
            )
        x, y, w, h = max(boxes, key=lambda item: int(item[2]) * int(item[3]))
        x = max(0, min(int(x), MONITOR_SIZE[0] - 1))
        y = max(0, min(int(y), MONITOR_SIZE[1] - 1))
        w = max(1, min(int(w), MONITOR_SIZE[0] - x))
        h = max(1, min(int(h), MONITOR_SIZE[1] - y))
        return RoiSuggestionResponse(
            available=True,
            suggested=True,
            roi_x=x,
            roi_y=y,
            roi_w=w,
            roi_h=h,
            model_path=str(model_path),
            message="Suggested ROI from the configured lightweight model. Check and edit before starting.",
        )
    except Exception as exc:
        return RoiSuggestionResponse(
            available=True,
            suggested=False,
            model_path=str(model_path),
            message=f"ROI suggestion failed safely: {exc}",
        )
