import type {
  DeviceInfo,
  StatusResponse,
  PolicyProfilesResponse,
  SystemInfo,
  ImagesResponse,
  DeleteImagesResponse,
  StartPayload,
  Camera,
  CoordinatorAuthResponse,
  CoordinatorDevice,
  CoordinatorDeviceCreatePayload,
  CoordinatorDeviceList,
  CoordinatorUser,
} from './types';

const ACCESS_TOKEN_KEY = 'pollipi.coordinator.accessToken';
const REFRESH_TOKEN_KEY = 'pollipi.coordinator.refreshToken';
const COORDINATOR_URL_KEY = 'pollipi.coordinator.baseUrl';

export type ApiTarget = string | Pick<Camera, 'baseUrl' | 'apiPathPrefix' | 'managed_by_coordinator'>;

export function getCoordinatorAccessToken(): string {
  return window.localStorage.getItem(ACCESS_TOKEN_KEY) || '';
}

export function setCoordinatorTokens(response: CoordinatorAuthResponse): void {
  if (response.access_token) window.localStorage.setItem(ACCESS_TOKEN_KEY, response.access_token);
  const refreshToken = response.tokens?.['Token.Refresh'] || response.tokens?.Refresh;
  if (refreshToken) window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
}

export function clearCoordinatorTokens(): void {
  window.localStorage.removeItem(ACCESS_TOKEN_KEY);
  window.localStorage.removeItem(REFRESH_TOKEN_KEY);
}

export function getSavedCoordinatorUrl(): string {
  return window.localStorage.getItem(COORDINATOR_URL_KEY) || window.location.origin;
}

export function saveCoordinatorUrl(baseUrl: string): void {
  window.localStorage.setItem(COORDINATOR_URL_KEY, baseUrl.replace(/\/+$/, ''));
}

function baseUrlOf(target: ApiTarget): string {
  return typeof target === 'string' ? target : target.baseUrl;
}

export function apiPath(target: ApiTarget, path: string): string {
  return typeof target !== 'string' && target.apiPathPrefix
    ? `${target.apiPathPrefix}${path}`
    : path;
}

export function deviceUrl(target: ApiTarget, path: string): string {
  const url = new URL(`${baseUrlOf(target)}${apiPath(target, path)}`);
  if (typeof target !== 'string' && target.managed_by_coordinator) {
    const token = getCoordinatorAccessToken();
    if (token) url.searchParams.set('access_token', token);
  }
  return url.toString();
}

export function resolveBaseUrl(value: string): string {
  const input = value.trim();
  if (/^https?:\/\//i.test(input)) {
    const url = new URL(input);
    url.pathname = '';
    url.search = '';
    url.hash = '';
    return url.origin;
  }
  const hostname = input.includes('@') ? input.split('@').pop()! : input;
  if (!hostname || /[/?#]/.test(hostname)) throw new Error('Invalid device name');
  return `http://${hostname.includes('.') ? hostname : `${hostname}.local`}:8000`;
}

export async function apiRequest<T = unknown>(
  target: ApiTarget,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const headers = new Headers(options.headers || {});
  const requestPath = apiPath(target, path);
  if (requestPath.startsWith('/api/')) {
    const token = getCoordinatorAccessToken();
    if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);
  }
  const response = await fetch(`${baseUrlOf(target)}${requestPath}`, { ...options, headers });
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  return ((response.headers.get('content-type') || '').includes('application/json')
    ? response.json()
    : response.text()) as Promise<T>;
}

export async function fetchDevice(target: ApiTarget, options: RequestInit = {}): Promise<DeviceInfo> {
  return apiRequest<DeviceInfo>(target, '/device', options);
}

export async function fetchStatus(target: ApiTarget, options: RequestInit = {}): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(target, '/status', options);
}

export async function fetchPolicyProfiles(target: ApiTarget, options: RequestInit = {}): Promise<PolicyProfilesResponse> {
  return apiRequest<PolicyProfilesResponse>(target, '/policy-profiles', options);
}

export async function fetchSystem(target: ApiTarget, options: RequestInit = {}): Promise<SystemInfo> {
  return apiRequest<SystemInfo>(target, '/system', options);
}

export async function postStart(target: ApiTarget, payload: StartPayload): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(target, '/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function postStop(target: ApiTarget): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(target, '/stop', { method: 'POST' });
}

export async function fetchImages(target: ApiTarget): Promise<ImagesResponse> {
  return apiRequest<ImagesResponse>(target, '/images?limit=40');
}

export async function deleteImage(target: ApiTarget, filename: string): Promise<void> {
  return apiRequest<void>(target, `/images/${encodeURIComponent(filename)}`, { method: 'DELETE' });
}

export async function deleteAllImages(target: ApiTarget): Promise<DeleteImagesResponse> {
  return apiRequest<DeleteImagesResponse>(target, '/images', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm: 'DELETE_ALL' }),
  });
}

export async function bulkDeleteImages(target: ApiTarget, filenames: string[]): Promise<DeleteImagesResponse> {
  return apiRequest<DeleteImagesResponse>(target, '/images/bulk-delete', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ filenames }),
  });
}

export async function coordinatorLogin(baseUrl: string, username: string, password: string): Promise<CoordinatorAuthResponse> {
  const result = await apiRequest<CoordinatorAuthResponse>(baseUrl, '/api/user/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ username, password }),
  });
  setCoordinatorTokens(result);
  saveCoordinatorUrl(baseUrl);
  return result;
}

export async function coordinatorRegister(baseUrl: string, email: string, username: string, password: string): Promise<void> {
  await apiRequest(baseUrl, '/api/user/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, username, password }),
  });
  saveCoordinatorUrl(baseUrl);
}

export async function coordinatorMe(baseUrl: string): Promise<CoordinatorUser> {
  const response = await apiRequest<{ user: CoordinatorUser }>(baseUrl, '/api/user/me');
  return response.user;
}

export async function fetchCoordinatorDevices(baseUrl: string): Promise<CoordinatorDevice[]> {
  const response = await apiRequest<CoordinatorDeviceList>(baseUrl, '/api/devices');
  return response.devices;
}

export async function createCoordinatorDevice(baseUrl: string, payload: CoordinatorDeviceCreatePayload): Promise<CoordinatorDevice> {
  return apiRequest<CoordinatorDevice>(baseUrl, '/api/devices', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function stopCoordinatorDevices(baseUrl: string, deviceIds: number[]): Promise<void> {
  await apiRequest(baseUrl, '/api/orchestration/stop', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ device_ids: deviceIds }),
  });
}

export async function deleteCoordinatorDevice(baseUrl: string, deviceId: number): Promise<void> {
  await apiRequest<void>(baseUrl, `/api/devices/${deviceId}`, { method: 'DELETE' });
}

export function getMjpegStreamUrl(target: ApiTarget): string {
  return deviceUrl(target, '/mjpeg');
}
