import { signal, computed } from '@preact/signals';
import { fetchCoordinatorDevices } from '../api/client';
import type { Camera, CoordinatorDevice } from '../api/types';
import { loadCameras, saveCameras } from '../lib/storage';
import { selectedGalleryCamera } from './gallery';

function initCamera(raw: Partial<Camera>): Camera {
  return {
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
    status: raw.status || null,
    previousImage: raw.previousImage || null,
    build_info: raw.build_info,
    camera_role: raw.camera_role || null,
    comparison_session_id: raw.comparison_session_id || null,
  };
}

const _cameras = signal<Camera[]>(loadCameras().map((camera) => initCamera(camera)));

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
  list[index] = initCamera({ ...list[index], ...patch });
  _cameras.value = list;
}

export function updateCameraRef(camera: Camera): void {
  const index = _cameras.value.indexOf(camera);
  if (index >= 0) {
    const next = [..._cameras.value];
    next[index] = initCamera(camera);
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
  if (existing >= 0) list[existing] = initCamera(camera);
  else list.push(initCamera(camera));
  _cameras.value = list;
  saveCameras(list);
}

export function removeCamera(cameraOrBaseUrl: Camera | string): void {
  const list = _cameras.value.filter((camera) => {
    if (typeof cameraOrBaseUrl === 'string') return camera.baseUrl !== cameraOrBaseUrl;
    if (cameraOrBaseUrl.coordinator_device_id) {
      return camera.coordinator_device_id !== cameraOrBaseUrl.coordinator_device_id;
    }
    return camera.baseUrl !== cameraOrBaseUrl.baseUrl;
  });
  _cameras.value = list;
  saveCameras(list);
}

export function persistCameras(): void {
  saveCameras(_cameras.value);
}

function sameCamera(left: Camera, right: Camera): boolean {
  if (left.coordinator_device_id && right.coordinator_device_id) {
    return left.coordinator_device_id === right.coordinator_device_id;
  }
  if (left.managed_by_coordinator || right.managed_by_coordinator) {
    return left.device_id === right.device_id && left.device_id !== '';
  }
  return left.baseUrl === right.baseUrl || left.device_id === right.device_id;
}

export function coordinatorDeviceToCamera(
  baseUrl: string,
  device: CoordinatorDevice,
  previous?: Camera,
): Camera {
  return initCamera({
    address: device.address,
    baseUrl,
    apiPathPrefix: device.api_path_prefix,
    coordinator_device_id: device.id,
    managed_by_coordinator: true,
    device_id: device.device_id,
    device_name: device.device_name,
    camera_label: device.display_name || device.camera_label,
    camera_model: device.camera_model,
    camera_profile: device.camera_profile,
    is_ai_camera: device.is_ai_camera,
    is_noir: device.is_noir,
    is_wide: device.is_wide,
    previousImage: previous?.previousImage || null,
    build_info: previous?.build_info,
    camera_role: previous?.camera_role || null,
    comparison_session_id: previous?.comparison_session_id || null,
  });
}

export async function syncDevices(baseUrl: string): Promise<number> {
  const devices = await fetchCoordinatorDevices(baseUrl);
  const previousCameras = _cameras.value;
  const coordinatorCameras = devices.map((device) => {
    const previous = previousCameras.find((camera) =>
      camera.coordinator_device_id === device.id ||
      camera.device_id === device.device_id ||
      camera.address === device.address,
    );
    return coordinatorDeviceToCamera(baseUrl, device, previous);
  });
  const localCameras = previousCameras.filter((camera) => !camera.managed_by_coordinator);
  const nextCameras = [...localCameras, ...coordinatorCameras];
  setCameras(nextCameras);

  const selected = selectedGalleryCamera.value;
  if (selected) {
    selectedGalleryCamera.value = nextCameras.find((camera) => sameCamera(camera, selected)) || null;
  }
  if (!selectedGalleryCamera.value && coordinatorCameras[0]) {
    selectedGalleryCamera.value = coordinatorCameras[0];
  }
  return coordinatorCameras.length;
}

export { initCamera };
