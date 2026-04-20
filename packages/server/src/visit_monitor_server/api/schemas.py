from typing import Literal

from pydantic import BaseModel, Field


PipelineStage = Literal[
    "idle",
    "warming_up",
    "tracking_flower",
    "monitoring_motion",
    "classifying_insect",
    "recording",
]

ModelRuntime = Literal["unconfigured", "onnx", "tflite", "ncnn", "rpk"]


class HealthResponse(BaseModel):
    status: Literal["ok"] = "ok"
    service: Literal["visit-monitor-server"] = "visit-monitor-server"
    version: str


class RuntimeStatusResponse(BaseModel):
    stage: PipelineStage = "idle"
    flower_detection_enabled: bool = Field(default=False)
    model_runtime: ModelRuntime = "unconfigured"
    active_recording: bool = Field(default=False)
