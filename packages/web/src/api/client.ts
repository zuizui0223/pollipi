import type {
  DeviceInfo,
  StatusResponse,
  SystemInfo,
  ImagesResponse,
  EventsResponse,
  EventInfo,
  TrainingStatus,
  DeleteImagesResponse,
  StartPayload,
} from './types';

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
  const localHostname = hostname.includes('.') ? hostname : `${hostname}.local`;
  return `http://${localHostname}:8000`;
}

export async function apiRequest<T = unknown>(
  baseUrl: string,
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${baseUrl}${path}`, options);
  if (!response.ok) {
    let detail = `HTTP ${response.status}`;
    try {
      const body = await response.json();
      detail = body.detail || detail;
    } catch (_) {}
    throw new Error(detail);
  }
  const contentType = response.headers.get('content-type') || '';
  return (
    contentType.includes('application/json') ? response.json() : response.text()
  ) as Promise<T>;
}

export async function fetchDevice(baseUrl: string): Promise<DeviceInfo> {
  return apiRequest<DeviceInfo>(baseUrl, '/device');
}

export async function fetchStatus(baseUrl: string): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(baseUrl, '/status');
}

export async function fetchSystem(baseUrl: string): Promise<SystemInfo> {
  return apiRequest<SystemInfo>(baseUrl, '/system');
}

export async function postStart(baseUrl: string, payload: StartPayload): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(baseUrl, '/start', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function postStop(baseUrl: string): Promise<StatusResponse> {
  return apiRequest<StatusResponse>(baseUrl, '/stop', { method: 'POST' });
}

export async function fetchImages(baseUrl: string, collection: string): Promise<ImagesResponse> {
  return apiRequest<ImagesResponse>(
    baseUrl,
    `/images?limit=40&collection=${encodeURIComponent(collection)}`,
  );
}

export async function deleteImage(baseUrl: string, filename: string): Promise<void> {
  return apiRequest<void>(baseUrl, `/images/${encodeURIComponent(filename)}`, {
    method: 'DELETE',
  });
}

export async function labelImage(
  baseUrl: string,
  filename: string,
  label: string,
): Promise<void> {
  return apiRequest<void>(baseUrl, `/images/${encodeURIComponent(filename)}/label`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ label }),
  });
}

export async function deleteAllImages(baseUrl: string): Promise<DeleteImagesResponse> {
  return apiRequest<DeleteImagesResponse>(baseUrl, '/images', {
    method: 'DELETE',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ confirm: 'DELETE_ALL' }),
  });
}

export async function fetchEvents(baseUrl: string, category: string): Promise<EventsResponse> {
  return apiRequest<EventsResponse>(
    baseUrl,
    `/events?limit=80&category=${encodeURIComponent(category)}`,
  );
}

export async function saveEventReview(
  baseUrl: string,
  eventId: string,
  payload: Partial<EventInfo>,
): Promise<void> {
  return apiRequest<void>(baseUrl, `/events/${encodeURIComponent(eventId)}/label`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

export async function fetchTrainingStatus(baseUrl: string): Promise<TrainingStatus> {
  return apiRequest<TrainingStatus>(baseUrl, '/training/status');
}

export async function startTraining(baseUrl: string): Promise<void> {
  return apiRequest<void>(baseUrl, '/training/start', { method: 'POST' });
}

export async function resetTrainingModel(baseUrl: string): Promise<void> {
  return apiRequest<void>(baseUrl, '/training/model', { method: 'DELETE' });
}
