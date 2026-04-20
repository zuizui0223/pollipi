from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Mapping


class ModelRuntime(StrEnum):
    ONNX = "onnx"
    TFLITE = "tflite"
    NCNN = "ncnn"
    RPK = "rpk"
    PYTHON = "python"


@dataclass(slots=True, frozen=True)
class ModelArtifact:
    name: str
    runtime: ModelRuntime
    model_path: Path
    input_width: int
    input_height: int
    labels: tuple[str, ...] = ()
    metadata: Mapping[str, str] = field(default_factory=dict)
