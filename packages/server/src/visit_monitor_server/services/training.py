"""Candidate-only visit/noise classifier training."""
from __future__ import annotations

import json
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

from visit_monitor_server.config import IMAGE_DIR, MODEL_DIR, MODEL_INFO_PATH, MODEL_PATH
from visit_monitor_server.services.event_log import canonical_review_label, read_event_rows


class BinaryTrainer:
    """Train and query a local classifier from human-reviewed candidate events."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.running = False
        self.trained_at: Optional[str] = None
        self.validation_accuracy: Optional[float] = None
        self.message = "No model trained yet. Review motion candidates as visit/noise before training."

    def status(self):
        from visit_monitor_server.api.schemas.training import TrainingStatusResponse

        candidates = self._reviewed_candidate_rows()
        positive_count = sum(1 for row in candidates if self._row_label(row) == "visit")
        negative_count = sum(1 for row in candidates if self._row_label(row) == "noise")
        reviewed_count = positive_count + negative_count
        if MODEL_INFO_PATH.is_file() and self.trained_at is None:
            try:
                info = json.loads(MODEL_INFO_PATH.read_text(encoding="utf-8"))
                self.trained_at = info.get("trained_at")
                self.validation_accuracy = info.get("validation_accuracy")
            except (OSError, json.JSONDecodeError):
                pass

        with self._lock:
            return TrainingStatusResponse(
                running=self.running,
                positive_count=positive_count,
                negative_count=negative_count,
                auto_labeled_count=0,
                reviewed_count=reviewed_count,
                model_available=MODEL_PATH.is_file(),
                trained_at=self.trained_at,
                validation_accuracy=self.validation_accuracy,
                message=self.message,
            )

    def start(self):
        status = self.status()
        if status.running:
            return status
        if status.positive_count < 2 or status.negative_count < 2:
            raise ValueError(
                "Training needs at least 2 reviewed visit and 2 reviewed noise candidate events."
            )
        with self._lock:
            self.running = True
            self.message = "Training candidate classifier on reviewed visit/noise events."
        threading.Thread(target=self._train, name="pollipi-candidate-training", daemon=True).start()
        return self.status()

    def reset_model(self):
        with self._lock:
            if self.running:
                raise ValueError("Cannot discard model while training is running.")
            for path in (MODEL_PATH, MODEL_INFO_PATH):
                if path.is_file():
                    path.unlink()
            self.trained_at = None
            self.validation_accuracy = None
            self.message = "Model discarded. Reviewed candidate labels are retained for later retraining."
        return self.status()

    def _train(self) -> None:
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            samples = []
            labels_list: list[int] = []
            for row in self._reviewed_candidate_rows():
                label = self._row_label(row)
                if label not in {"visit", "noise"}:
                    continue
                filename = Path(row.get("image_filename", "")).name
                if not filename:
                    continue
                image_path = IMAGE_DIR / filename
                if not image_path.is_file():
                    continue
                feature = self._image_feature(image_path)
                if feature is None:
                    continue
                samples.append(feature)
                labels_list.append(1 if label == "visit" else 0)

            if labels_list.count(1) < 2 or labels_list.count(0) < 2:
                raise RuntimeError("Too few readable reviewed candidate images for training.")

            features = np.asarray(samples, dtype=np.float32)
            targets = np.asarray(labels_list, dtype=np.int32)
            train_indices = list(range(len(targets)))
            test_indices: list[int] = []
            if labels_list.count(1) >= 5 and labels_list.count(0) >= 5:
                for label_value in (0, 1):
                    matching = [i for i, value in enumerate(labels_list) if value == label_value]
                    test_indices.extend(matching[::5])
                train_indices = [i for i in train_indices if i not in test_indices]

            svm = cv2.ml.SVM_create()
            svm.setType(cv2.ml.SVM_C_SVC)
            svm.setKernel(cv2.ml.SVM_RBF)
            svm.setC(2.0)
            svm.setGamma(0.01)
            svm.train(features[train_indices], cv2.ml.ROW_SAMPLE, targets[train_indices])
            accuracy = None
            if test_indices:
                _, prediction = svm.predict(features[test_indices])
                accuracy = float(
                    (prediction.reshape(-1).astype(np.int32) == targets[test_indices]).mean()
                )
            MODEL_DIR.mkdir(parents=True, exist_ok=True)
            svm.save(str(MODEL_PATH))
            trained_at = datetime.now().astimezone().isoformat(timespec="seconds")
            MODEL_INFO_PATH.write_text(
                json.dumps(
                    {
                        "trained_at": trained_at,
                        "positive_count": labels_list.count(1),
                        "negative_count": labels_list.count(0),
                        "validation_accuracy": accuracy,
                        "feature": "HOG grayscale 64x64",
                        "classifier": "OpenCV SVM RBF",
                        "training_scope": "reviewed_candidate_events_only",
                        "positive_label": "visit",
                        "negative_label": "noise",
                    },
                    ensure_ascii=True,
                    indent=2,
                ),
                encoding="utf-8",
            )
            with self._lock:
                self.trained_at = trained_at
                self.validation_accuracy = accuracy
                self.message = (
                    "Training complete. Validation accuracy is shown only after enough reviewed candidates."
                    if accuracy is None
                    else f"Training complete. Hold-out accuracy: {accuracy:.1%}."
                )
        except Exception as exc:
            with self._lock:
                self.message = f"Training error: {exc}"
        finally:
            with self._lock:
                self.running = False

    @staticmethod
    def _image_feature(image_path: Path):
        import cv2  # type: ignore

        image = cv2.imread(str(image_path), cv2.IMREAD_GRAYSCALE)
        if image is None:
            return None
        resized = cv2.resize(image, (64, 64))
        hog = cv2.HOGDescriptor((64, 64), (16, 16), (8, 8), (8, 8), 9)
        return hog.compute(resized).reshape(-1)

    def predict(self, image_path: Path) -> Optional[str]:
        if not MODEL_PATH.is_file():
            return None
        try:
            import cv2  # type: ignore
            import numpy as np  # type: ignore

            feature = self._image_feature(image_path)
            if feature is None:
                return None
            svm = cv2.ml.SVM_load(str(MODEL_PATH))
            _, prediction = svm.predict(np.asarray([feature], dtype=np.float32))
            return "visit" if int(prediction.reshape(-1)[0]) == 1 else "noise"
        except Exception:
            return None

    @staticmethod
    def _row_label(row: dict[str, str]) -> str:
        return canonical_review_label(row.get("review_label") or row.get("manual_label"))

    @classmethod
    def _reviewed_candidate_rows(cls) -> list[dict[str, str]]:
        return [row for row in read_event_rows() if cls._row_label(row) in {"visit", "noise"}]
