export type PipelineStage =
  | "idle"
  | "warming_up"
  | "tracking_flower"
  | "monitoring_motion"
  | "classifying_insect"
  | "recording";

export interface ServiceHealth {
  status: "ok";
  service: "visit-monitor-server";
  version: string;
}

export interface RuntimeStatus {
  stage: PipelineStage;
  flowerDetectionEnabled: boolean;
  modelRuntime: "unconfigured" | "onnx" | "tflite" | "ncnn" | "rpk";
  activeRecording: boolean;
}

export interface EventSummary {
  id: string;
  startedAt: string;
  label: string | null;
  confidence: number | null;
  assetPath: string;
}

export interface ConfigSnapshot {
  cameraSource: "picamera2" | "video_file" | "mjpeg";
  previewEnabled: boolean;
  recordingDirectory: string;
}
