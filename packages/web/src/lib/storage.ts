import type { Camera } from '../api/types';

export const STORAGE_KEY = 'pollipi.observationDevices.v2';

export function loadCameras(): Camera[] {
  try {
    return JSON.parse(window.localStorage.getItem(STORAGE_KEY) || '[]');
  } catch (_) {
    return [];
  }
}

export function saveCameras(cameras: Camera[]): void {
  const persistent = cameras.map((camera) => ({
    address: camera.address,
    baseUrl: camera.baseUrl,
    apiPathPrefix: camera.apiPathPrefix,
    coordinator_device_id: camera.coordinator_device_id,
    managed_by_coordinator: Boolean(camera.managed_by_coordinator),
    device_id: camera.device_id,
    device_name: camera.device_name,
    camera_label: camera.camera_label,
    camera_model: camera.camera_model,
    camera_profile: camera.camera_profile,
    is_ai_camera: camera.is_ai_camera,
    is_noir: camera.is_noir,
    is_wide: camera.is_wide,
  }));
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(persistent));
}
