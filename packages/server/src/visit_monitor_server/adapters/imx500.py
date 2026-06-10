"""IMX500 AI camera adapter.

Thin wrapper that wires up picamera2.devices.IMX500 for object-detection
monitoring.  Import of picamera2 is deferred so that this module can be
imported on non-Pi machines without error.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass  # type stubs only


def load_imx500(model_path: str):
    """Return (imx500, intrinsics) or raise ImportError if unavailable."""
    from picamera2.devices import IMX500  # type: ignore
    from picamera2.devices.imx500 import NetworkIntrinsics  # type: ignore

    imx500 = IMX500(model_path)
    intrinsics = imx500.network_intrinsics or NetworkIntrinsics()
    intrinsics.task = "object detection"
    intrinsics.update_with_defaults()
    return imx500, intrinsics


def render_detections(image, outputs, imx500, intrinsics, metadata, threshold: float, labels: list[str]) -> bytes:
    """Overlay bounding-box annotations and return JPEG bytes."""
    import cv2  # type: ignore
    import numpy as np  # type: ignore  # noqa: F401

    if outputs is not None:
        _, input_height = imx500.get_input_size()
        boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]
        if intrinsics.bbox_normalization:
            boxes = boxes / input_height
        if intrinsics.bbox_order == "xy":
            boxes = boxes[:, [1, 0, 3, 2]]
        for box, score, category in zip(boxes, scores, classes):
            if float(score) <= threshold:
                continue
            x, y, width, height = imx500.convert_inference_coords(box, metadata, None)
            cat = int(category)
            label = labels[cat] if cat < len(labels) else f"class_{cat}"
            caption = f"{label} {float(score):.2f}"
            cv2.rectangle(image, (x, y), (x + width, y + height), (0, 255, 0), 2)
            cv2.putText(
                image, caption, (x + 3, max(y + 16, 16)),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 255), 1,
            )

    encoded, buffer = cv2.imencode(".jpg", image)
    if not encoded:
        raise RuntimeError("AI monitor JPEG encoding failed.")
    return buffer.tobytes()
