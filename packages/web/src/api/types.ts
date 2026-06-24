/** Device info returned by GET /device */
export interface BuildInfo {
  app_version: string;
  git_commit: string;
  build_timestamp: string;
  deployment_mode: string;
  web_build_id: string;
}

export interface DeviceInfo {
  device_id: string;
  device_name: string;
  camera_label: string;
  camera_model: string;
  camera_profile: string;
  is_ai_camera: boolean;
  is_noir: boolean;
  is_wide: boolean;
  build_info?: BuildInfo;
}

export interface CoordinatorUser {
  email: string;
  username: string;
  group: string;
}

export interface CoordinatorAuthResponse {
  access_token?: string;
  tokens?: Record<string, string>;
  user?: CoordinatorUser;
}

export interface CoordinatorDeviceCreatePayload {
  address: string;
  base_url: string;
  display_name?: string;
  device_secret?: string;
  verify_connection?: boolean;
}

export interface CoordinatorDevice {
  id: number;
  address: string;
  base_url: string;
  api_path_prefix: string;
  device_id: string;
  device_name: string;
  display_name: string;
  camera_label: string;
  camera_model: string;
  camera_profile: string;
  is_ai_camera: boolean;
  is_noir: boolean;
  is_wide: boolean;
  last_status?: StatusResponse | null;
  last_error?: string | null;
  last_seen_at?: string | null;
}

export interface CoordinatorDeviceList {
  devices: CoordinatorDevice[];
}

/** Active status returned by GET /status, POST /start, and POST /stop. */
export interface StatusResponse {
  device_id: string;
  device_name: string;
  camera_label: string;
  camera_model: string;
  camera_profile: string;
  is_ai_camera: boolean;
  is_noir: boolean;
  is_wide: boolean;
  running: boolean;
  lifecycle_state?: string;
  last_error?: string | null;
  preview_subscriber_count?: number;
  preview_latest_frame_age_sec?: number | null;
  preview_producer_state?: string;
  capture_count: number;
  interval_sec: number | null;
  next_interval_sec?: number | null;
  last_capture_time: string | null;
  last_image: string | null;
  autonomous_mode: boolean;
  adaptive_timelapse_mode: boolean;
  mesh_shadow_mode: boolean;
  interval_reason: string | null;
  message: string;
  camera_role: string | null;
  comparison_session_id: string | null;
  mesh_decision?: string | null;
  mesh_reason?: string | null;
  mesh_active_cell_proportion?: number | null;
  mesh_offset_agreement?: number | null;
  mesh_global_synchrony?: number | null;
  probe_interval_sec?: number | null;
  would_be_mode?: string | null;
  would_be_interval_sec?: number | null;
  live_adaptive_enabled?: boolean;
}

/** System info from GET /system. */
export interface SystemInfo {
  storage_free_bytes: number;
  undervoltage_now: boolean;
  undervoltage_occurred: boolean;
}

/** Scheduled image info from GET /images. */
export interface ImageInfo {
  filename: string;
  url: string;
  captured_at: string | null;
  size_bytes: number;
}

export interface ImagesResponse {
  image_count: number;
  total_size_bytes: number;
  image_dir: string;
  images: ImageInfo[];
}

export interface DeleteImagesResponse {
  deleted_count: number;
  message?: string;
}

/** Persistent camera entry used by the iPad PWA. */
export interface Camera {
  address: string;
  baseUrl: string;
  apiPathPrefix?: string;
  coordinator_device_id?: number;
  managed_by_coordinator?: boolean;
  device_id: string;
  device_name: string;
  camera_label: string;
  camera_model: string;
  camera_profile: string;
  is_ai_camera: boolean;
  is_noir: boolean;
  is_wide: boolean;
  status: StatusResponse | null;
  previousImage: string | null;
  build_info?: BuildInfo;
  camera_role?: string | null;
  comparison_session_id?: string | null;
  /** Cached image count from the last /images fetch. */
  imageCount?: number;
}

/** Minimal active payload for POST /start. */
export interface StartPayload {
  interval_sec: number;
  autonomous_mode: boolean;
  adaptive_timelapse_mode: boolean;
  mesh_shadow_mode: boolean;
}
