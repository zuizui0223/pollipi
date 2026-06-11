import { signal, computed } from '@preact/signals';
import type { Camera } from '../api/types';
import { loadCameras, saveCameras } from '../lib/storage';
import { normalizeRoi } from '../lib/roi';

function syncWorkflowAliases(camera: Camera): Camera {
  const confirmedROI = normalizeRoi(camera.roi);
  const editingROI = normalizeRoi(camera.editing_roi);
  camera.angleConfirmed = Boolean(camera.angle_confirmed);
  camera.confirmedROI = confirmedROI;
  camera.editingROI = editingROI;
  camera.roiStale = Boolean(camera.roi_stale);
  camera.roiConfirmed = Boolean(confirmedROI && !camera.roiStale);
  return camera;
}

function initCamera(raw: Partial<Camera>): Camera {
  const camera: Camera = {
    address: raw.address || '',
    baseUrl: raw.baseUrl || '',
    apiPathPrefix: raw.apiPathPrefix,
    coordinator_device_id: raw.coordinator_device_id,
    managed_by_coordinator: Boolean(raw.managed_by_coordinator),
    device_id: raw.device_id || '',
    device_name: raw.device_name || '',
    camera_label: raw.camera_label || 'PolliPi Camera',
    camera_model: raw.camera_model || '',
    camera_profile: raw.camera_profile || '',
    is_ai_camera: Boolean(raw.is_ai_camera),
    is_noir: Boolean(raw.is_noir),
    is_wide: Boolean(raw.is_wide),
    roi: normalizeRoi(raw.roi),
    editing_roi: null,
    angle_confirmed: Boolean(raw.angle_confirmed),
    roi_stale: Boolean(raw.roi_stale),
    roi_pending: false,
    roi_tracking: Boolean(raw.roi_tracking),
    roi_search_margin: raw.roi_search_margin || 30,
    roi_tracking_min_score: raw.roi_tracking_min_score || 0.45,
    // runtime
    angleConfirmed: false,
    confirmedROI: null,
    editingROI: null,
    roiStale: false,
    roiConfirmed: false,
    status: null,
    previousImage: null,
    monitoring: false,
    aiMonitoring: false,
    manualPreview: false,
  };
  syncWorkflowAliases(camera);
  return camera;
}

const _cameras = signal<Camera[]>(loadCameras().map((c) => initCamera(c)));

export const cameras = computed(() => _cameras.value);

export function getCameras(): Camera[] {
  return _cameras.value;
}

export function setCameras(list: Camera[]): void {
  _cameras.value = list;
  saveCameras(list);
}

export function updateCamera(index: number, patch: Partial<Camera>): void {
  const list = [..._cameras.value];
  const camera = { ...list[index], ...patch };
  syncWorkflowAliases(camera);
  list[index] = camera;
  _cameras.value = list;
}

export function updateCameraRef(camera: Camera): void {
  const list = _cameras.value;
  const index = list.indexOf(camera);
  if (index >= 0) {
    const next = [...list];
    syncWorkflowAliases(camera);
    next[index] = { ...camera };
    _cameras.value = next;
  }
}

export function addOrReplaceCamera(camera: Camera): void {
  const list = [..._cameras.value];
  const existing = list.findIndex(
    (item) =>
      (camera.coordinator_device_id && item.coordinator_device_id === camera.coordinator_device_id) ||
      item.baseUrl === camera.baseUrl ||
      item.device_id === camera.device_id,
  );
  syncWorkflowAliases(camera);
  if (existing >= 0) list[existing] = camera;
  else list.push(camera);
  _cameras.value = list;
  saveCameras(list);
}

export function removeCamera(cameraOrBaseUrl: Camera | string): void {
  const list = _cameras.value.filter((c) => {
    if (typeof cameraOrBaseUrl === 'string') return c.baseUrl !== cameraOrBaseUrl;
    if (cameraOrBaseUrl.coordinator_device_id) {
      return c.coordinator_device_id !== cameraOrBaseUrl.coordinator_device_id;
    }
    return c.baseUrl !== cameraOrBaseUrl.baseUrl;
  });
  _cameras.value = list;
  saveCameras(list);
}

export function persistCameras(): void {
  saveCameras(_cameras.value);
}

export { syncWorkflowAliases, initCamera };
