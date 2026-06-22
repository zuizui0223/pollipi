import type { RoiRect } from '../lib/roi';

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

/** Status returned by GET /status, POST /start, POST /stop */
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
  capture_count: number;
  interval_sec: number | null;
  last_capture_time: string | null;
  last_image: string | null;
  auto_mode: boolean;
  motion_trigger_mode: boolean;
  hybrid_mode: boolean;
  autonomous_mode: boolean;
  ml_assist_mode: boolean;
  adaptive_timelapse_mode: boolean;
  motion_score: number | null;
  motion_type: string | null;
  interval_reason: string | null;
  message: string;
  camera_role: string | null;
  comparison_session_id: string | null;
  roi_tracking: boolean;
  roi_tracking_score: number | null;
  roi_tracking_success: boolean;
  roi_shift_x: number | null;
  roi_shift_y: number | null;
  tracked_roi_x: number | null;
  tracked_roi_y: number | null;
  tracked_roi_w: number | null;
  tracked_roi_h: number | null;
  roi_semantics?: string | null;
  control_roi_used?: boolean;
  control_roi_x?: number | null;
  control_roi_y?: number | null;
  control_roi_w?: number | null;
  control_roi_h?: number | null;
  floral_zone_score?: number | null;
  background_control_score?: number | null;
  zone_minus_control_score?: number | null;
  grid_rows?: number;
  grid_cols?: number;
  changed_cell_count?: number;
  changed_cell_ratio?: number | null;
  local_compactness?: number | null;
  whole_frame_change_score?: number | null;
  previous_frame_elapsed_sec?: number | null;
  robust_background_score?: number | null;
  candidate_reasons?: string | null;
}

/** System info from GET /system */
export interface SystemInfo {
  storage_free_bytes: number;
  undervoltage_now: boolean;
  undervoltage_occurred: boolean;
}

/** Image info from GET /images */
export interface ImageInfo {
  filename: string;
  url: string;
  captured_at: string | null;
  size_bytes: number;
  label: string | null;
  review_status: string | null;
  final_category: string | null;
  category_source: string | null;
}

/** Images list response */
export interface ImagesResponse {
  image_count: number;
  total_size_bytes: number;
  image_dir: string;
  images: ImageInfo[];
}

/** Event info from GET /events */
export interface EventInfo {
  event_id: string;
  timestamp: string | null;
  image_url: string | null;
  image_filename: string | null;
  final_category: string | null;
  category_source: string | null;
  review_status: string | null;
  manual_label: string | null;
  review_label: string | null;
  manual_taxon: string | null;
  false_positive_reason: string | null;
  manual_notes: string | null;
  device_name: string | null;
  camera_profile: string | null;
  site_id: string | null;
  flower_id: string | null;
  plant_species: string | null;
  motion_score: string | null;
  changed_area_ratio: string | null;
  largest_blob_ratio: string | null;
  wind_like_motion: string | null;
  motion_type: string | null;
  auto_category: string | null;
  floral_zone_score?: string | null;
  background_control_score?: string | null;
  zone_minus_control_score?: string | null;
  changed_cell_count?: string | null;
  changed_cell_ratio?: string | null;
  local_compactness?: string | null;
  candidate_reasons?: string | null;
}

/** Events list response */
export interface EventsResponse {
  event_count: number;
  events: EventInfo[];
}

/** Training status from GET /training/status */
export interface TrainingStatus {
  positive_count: number;
  negative_count: number;
  model_available: boolean;
  message: string;
}

/** Delete images response */
export interface DeleteImagesResponse {
  deleted_count: number;
  message?: string;
}

export interface BulkDeleteEventFailure {
  event_id: string;
  reason: string;
}

export interface BulkDeleteEventsResponse {
  deleted_count: number;
  image_deleted_count: number;
  failed: BulkDeleteEventFailure[];
  message?: string;
}

/** The full camera object used in frontend state */
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
  roi: RoiRect | null;
  editing_roi: RoiRect | null;
  angle_confirmed: boolean;
  roi_stale: boolean;
  roi_pending: boolean;
  roi_tracking: boolean;
  roi_search_margin: number;
  roi_tracking_min_score: number;
  // derived / runtime
  angleConfirmed: boolean;
  confirmedROI: RoiRect | null;
  editingROI: RoiRect | null;
  roiStale: boolean;
  roiConfirmed: boolean;
  status: StatusResponse | null;
  previousImage: string | null;
  monitoring: boolean;
  aiMonitoring: boolean;
  manualPreview: boolean;
  imageCount?: number;
  // from status updates
  camera_role?: string | null;
  comparison_session_id?: string | null;
  build_info?: BuildInfo;
}

/** Start payload for POST /start */
export interface StartPayload {
  interval_sec: number;
  auto_mode: boolean;
  motion_trigger_mode: boolean;
  hybrid_mode: boolean;
  ml_assist_mode: boolean;
  autonomous_mode: boolean;
  adaptive_timelapse_mode: boolean;
  adaptive_min_interval_sec?: number;
  adaptive_window_sec?: number;
  idle_interval_sec: number;
  detection_interval_sec: number;
  pixel_difference: number;
  motion_ratio: number;
  site_id?: string;
  flower_id?: string;
  plant_species?: string;
  observer?: string;
  notes?: string;
  comparison_session_id?: string;
  camera_role?: string;
  method_mode?: string;
  roi_x?: number;
  roi_y?: number;
  roi_w?: number;
  roi_h?: number;
  control_roi_x?: number;
  control_roi_y?: number;
  control_roi_w?: number;
  control_roi_h?: number;
  roi_grid_rows?: number;
  roi_grid_cols?: number;
  roi_tracking?: boolean;
  roi_search_margin?: number;
  roi_tracking_min_score?: number;
}
