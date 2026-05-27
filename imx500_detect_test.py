"""Run a short headless object-detection trial on a Raspberry Pi AI Camera."""

from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import cv2

from picamera2 import Picamera2
from picamera2.devices import IMX500
from picamera2.devices.imx500 import NetworkIntrinsics


DEFAULT_MODEL = "/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk"
DEFAULT_OUTPUT_DIR = Path.home() / "pollipi_timelapse" / "imx500_detect_trials"
COCO_LABELS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck", "boat",
    "traffic light", "fire hydrant", "-", "stop sign", "parking meter", "bench", "bird", "cat",
    "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe", "-", "backpack",
    "umbrella", "-", "-", "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
    "sports ball", "kite", "baseball bat", "baseball glove", "skateboard", "surfboard",
    "tennis racket", "bottle", "-", "wine glass", "cup", "fork", "knife", "spoon", "bowl",
    "banana", "apple", "sandwich", "orange", "broccoli", "carrot", "hot dog", "pizza",
    "donut", "cake", "chair", "couch", "potted plant", "bed", "-", "dining table", "-",
    "-", "toilet", "-", "tv", "laptop", "mouse", "remote", "keyboard", "cell phone",
    "microwave", "oven", "toaster", "sink", "refrigerator", "-", "book", "clock", "vase",
    "scissors", "teddy bear", "hair drier", "toothbrush",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Capture one annotated result and JSON summary from the Raspberry Pi AI Camera."
    )
    parser.add_argument("--duration-sec", type=float, default=15, help="Trial duration in seconds.")
    parser.add_argument("--threshold", type=float, default=0.55, help="Minimum detection confidence.")
    parser.add_argument("--model", default=DEFAULT_MODEL, help="IMX500 object detection model file.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Result folder.")
    return parser.parse_args()


def label_for(category: int, labels: list[str]) -> str:
    if 0 <= category < len(labels):
        return labels[category]
    return f"class_{category}"


def parse_detections(
    metadata: dict,
    imx500: IMX500,
    picam2: Picamera2,
    intrinsics: NetworkIntrinsics,
    threshold: float,
    labels: list[str],
) -> list[dict]:
    outputs = imx500.get_outputs(metadata, add_batch=True)
    if outputs is None:
        return []

    input_width, input_height = imx500.get_input_size()
    boxes, scores, classes = outputs[0][0], outputs[1][0], outputs[2][0]
    if intrinsics.bbox_normalization:
        boxes = boxes / input_height
    if intrinsics.bbox_order == "xy":
        boxes = boxes[:, [1, 0, 3, 2]]

    detections = []
    for box, score, category in zip(boxes, scores, classes):
        if float(score) <= threshold:
            continue
        x, y, width, height = imx500.convert_inference_coords(box, metadata, picam2)
        category_number = int(category)
        detections.append(
            {
                "label": label_for(category_number, labels),
                "category": category_number,
                "confidence": round(float(score), 4),
                "box": [int(x), int(y), int(width), int(height)],
            }
        )
    return detections


def draw_detections(frame, detections: list[dict]) -> None:
    for detection in detections:
        x, y, width, height = detection["box"]
        text = f'{detection["label"]} {detection["confidence"]:.2f}'
        cv2.rectangle(frame, (x, y), (x + width, y + height), (0, 255, 0), 2)
        cv2.putText(frame, text, (x + 4, max(y + 18, 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 0, 255), 2)


def main() -> None:
    args = parse_args()
    if args.duration_sec <= 0:
        raise SystemExit("--duration-sec must be greater than 0.")
    if not 0 < args.threshold <= 1:
        raise SystemExit("--threshold must be between 0 and 1.")

    output_dir = args.output_dir.expanduser()
    output_dir.mkdir(parents=True, exist_ok=True)
    trial_id = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    image_path = output_dir / f"imx500_detection_{trial_id}.jpg"
    report_path = output_dir / f"imx500_detection_{trial_id}.json"

    imx500 = IMX500(args.model)
    intrinsics = imx500.network_intrinsics or NetworkIntrinsics()
    intrinsics.task = "object detection"
    intrinsics.update_with_defaults()
    labels = list(intrinsics.labels or COCO_LABELS)

    picam2 = Picamera2(imx500.camera_num)
    config = picam2.create_preview_configuration(
        main={"size": (1280, 720), "format": "RGB888"},
        controls={"FrameRate": intrinsics.inference_rate},
        buffer_count=12,
    )
    frames_checked = 0
    detections_by_label: Counter[str] = Counter()
    best_detections: list[dict] = []
    best_frame = None
    best_score = (-1, -1.0)
    started_at = datetime.now().astimezone().isoformat(timespec="seconds")

    try:
        imx500.show_network_fw_progress_bar()
        picam2.start(config, show_preview=False)
        end_time = time.monotonic() + args.duration_sec
        while time.monotonic() < end_time:
            request = picam2.capture_request()
            try:
                metadata = request.get_metadata()
                frame = request.make_array("main")
                detections = parse_detections(metadata, imx500, picam2, intrinsics, args.threshold, labels)
            finally:
                request.release()
            frames_checked += 1
            detections_by_label.update(detection["label"] for detection in detections)
            top_confidence = max((detection["confidence"] for detection in detections), default=0.0)
            score = (len(detections), top_confidence)
            if best_frame is None or score > best_score:
                best_score = score
                best_detections = detections
                best_frame = frame.copy()
    finally:
        picam2.stop()
        picam2.close()

    if best_frame is None:
        raise RuntimeError("No camera frames were received.")
    draw_detections(best_frame, best_detections)
    cv2.imwrite(str(image_path), best_frame)

    report = {
        "trial_started_at": started_at,
        "trial_finished_at": datetime.now().astimezone().isoformat(timespec="seconds"),
        "camera": "Raspberry Pi AI Camera (IMX500)",
        "model": args.model,
        "threshold": args.threshold,
        "duration_sec": args.duration_sec,
        "frames_checked": frames_checked,
        "annotated_image": str(image_path),
        "best_detections": best_detections,
        "detections_by_label": dict(detections_by_label),
        "insect_label_in_standard_model": "insect" in labels,
        "note": "The standard COCO-style model is not an insect classifier.",
    }
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
