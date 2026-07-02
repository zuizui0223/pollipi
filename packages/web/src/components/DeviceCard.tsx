import { h } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import { useSignal } from '@preact/signals';

import type { Camera, DeviceInfo, StartPayload, StatusResponse, SystemInfo } from '../api/types';
import {
  deleteCoordinatorDevice,
  deviceUrl,
  fetchDevice,
  getMjpegStreamUrl,
  fetchStatus,
  fetchSystem,
  postStart,
  postStop,
} from '../api/client';
import {
  autonomousMode,
  captureModeStartFields,
  intervalSec,
} from '../state/session';
import { removeCamera } from '../state/devices';
import { coordinatorBaseUrl } from '../state/coordinator';
import { formatBytes, formatCaptureTime } from '../lib/formatting';
import { StoragePanel } from './StoragePanel';
import * as s from '../styles/components.css';

interface Props {
  camera: Camera;
  index: number;
  onUpdated: () => void;
}

type ConnectionState = 'online' | 'degraded' | 'reconnecting' | 'offline' | 'stale';

const BLANK_IMAGE_SRC = 'data:image/gif;base64,R0lGODlhAQABAIAAAAAAAP///ywAAAAAAQABAAACAUwAOw==';

function buildStartPayload() {
  const interval = intervalSec.value;
  if (!Number.isFinite(interval) || interval < 1 || interval > 3600) {
    alert('Capture interval must be between 1 and 3600 seconds.');
    return null;
  }

  const payload: StartPayload = {
    interval_sec: interval,
    autonomous_mode: autonomousMode.value,
    adaptive_timelapse_mode: false,
    mesh_shadow_mode: true,
    ...captureModeStartFields(),
  };
  return payload;
}

function applyDeviceInfo(camera: Camera, device: DeviceInfo) {
  Object.assign(camera, {
    device_id: device.device_id || camera.device_id,
    device_name: device.device_name || camera.device_name,
    camera_label: device.camera_label || camera.camera_label,
    camera_model: device.camera_model || camera.camera_model,
    camera_profile: device.camera_profile || camera.camera_profile,
    is_ai_camera: Boolean(device.is_ai_camera),
    is_noir: Boolean(device.is_noir),
    is_wide: Boolean(device.is_wide),
    build_info: device.build_info || camera.build_info,
  });
}

function applyStatus(camera: Camera, next: StatusResponse) {
  Object.assign(camera, {
    device_id: next.device_id || camera.device_id,
    device_name: next.device_name || camera.device_name,
    camera_label: next.camera_label || camera.camera_label,
    camera_model: next.camera_model || camera.camera_model,
    camera_profile: next.camera_profile || camera.camera_profile,
    is_ai_camera: Boolean(next.is_ai_camera),
    is_noir: Boolean(next.is_noir),
    is_wide: Boolean(next.is_wide),
  });
}

function shortCommit(value?: string | null): string {
  if (!value) return 'unknown';
  return value.length > 12 ? value.slice(0, 12) : value;
}

function seconds(value?: number | null): string {
  return Number.isFinite(value) ? `${value} sec` : '-';
}

function latestImageUrl(camera: Camera, status: StatusResponse): string {
  const url = new URL(deviceUrl(camera, '/latest'));
  url.searchParams.set(
    'capture',
    `${status.last_capture_time || ''}:${status.last_image || ''}`,
  );
  return url.toString();
}

export function DeviceCard({ camera, index, onUpdated }: Props) {
  const busy = useSignal(false);
  const status = useSignal<StatusResponse | null>(null);
  const system = useSignal<SystemInfo | null>(null);
  const message = useSignal('Reading status...');
  const connectionState = useSignal<ConnectionState>('stale');
  const previewReady = useSignal(false);
  const previewHasFrame = useSignal(false);
  const latestReady = useSignal(false);
  const latestHasImage = useSignal(false);
  // imageRef is used only for the latest saved JPEG during capture.
  const imageRef = useRef<HTMLImageElement>(null);
  // previewRef is used only while stopped, then explicitly released at Start.
  const previewRef = useRef<HTMLImageElement>(null);
  const previewUrlRef = useRef('');
  const latestCaptureToken = useRef('');
  const captureRunning = Boolean(status.value?.running);

  const pollDelayMs = useRef(5000);
  const refreshInFlight = useRef(false);
  const refreshGeneration = useRef(0);

  function updateFromStatus(next: StatusResponse) {
    status.value = next;
    applyStatus(camera, next);
    message.value = next.mesh_reason || next.interval_reason || next.message || 'Status updated.';
  }

  function clearImageElement(image: HTMLImageElement) {
    image.onload = null;
    image.onerror = null;
    image.removeAttribute('src');
    image.src = BLANK_IMAGE_SRC;
    image.removeAttribute('src');
  }

  function releasePreviewStream(image = previewRef.current) {
    previewUrlRef.current = '';
    previewReady.value = false;
    previewHasFrame.value = false;
    if (!image) return;
    clearImageElement(image);
  }

  function releaseLatestImage(image = imageRef.current) {
    latestCaptureToken.current = '';
    latestReady.value = false;
    latestHasImage.value = false;
    if (!image) return;
    clearImageElement(image);
  }

  async function refresh() {
    if (refreshInFlight.current) return;

    refreshInFlight.current = true;
    const generation = ++refreshGeneration.current;
    const controller = new AbortController();
    const timeout = window.setTimeout(
      () => controller.abort(),
      document.hidden ? 9000 : 4500,
    );

    try {
      connectionState.value = status.value ? 'reconnecting' : 'stale';
      const [device, next, sys] = await Promise.all([
        fetchDevice(camera, { signal: controller.signal }).catch(() => null),
        fetchStatus(camera, { signal: controller.signal }),
        fetchSystem(camera, { signal: controller.signal }).catch(() => null),
      ]);
      if (generation !== refreshGeneration.current) return;

      if (device) applyDeviceInfo(camera, device);
      if (sys) system.value = sys;
      updateFromStatus(next);
      connectionState.value = 'online';
      pollDelayMs.current = document.hidden ? 15000 : 5000;
    } catch (error: unknown) {
      connectionState.value = status.value ? 'degraded' : 'offline';
      pollDelayMs.current = Math.min(
        30000,
        Math.max(5000, Math.round(pollDelayMs.current * 1.7 + Math.random() * 500)),
      );
      message.value = `Connection failed: ${(error as Error).message}`;
    } finally {
      window.clearTimeout(timeout);
      refreshInFlight.current = false;
    }
  }

  // Exactly one idle monitor per visible card. Removing src closes the
  // MJPEG request before high-resolution scheduled capture begins.
  useEffect(() => {
    const image = previewRef.current;
    if (captureRunning || !image) {
      releasePreviewStream();
      return undefined;
    }

    const streamUrl = getMjpegStreamUrl(camera);
    if (previewUrlRef.current === streamUrl && image.getAttribute('src')) {
      return () => {
        releasePreviewStream(image);
      };
    }

    releaseLatestImage();
    previewUrlRef.current = streamUrl;
    previewReady.value = false;
    previewHasFrame.value = false;
    image.onload = () => {
      previewReady.value = true;
      previewHasFrame.value = true;
    };
    image.onerror = () => {
      previewReady.value = false;
      previewHasFrame.value = false;
    };
    image.src = streamUrl;

    return () => {
      releasePreviewStream(image);
    };
  }, [
    camera.baseUrl,
    camera.apiPathPrefix,
    camera.managed_by_coordinator,
    captureRunning,
  ]);

  useEffect(() => {
    const image = imageRef.current;
    const currentStatus = status.value;

    if (!captureRunning || !currentStatus || !image) {
      if (!captureRunning) releaseLatestImage();
      return undefined;
    }

    releasePreviewStream();

    if (!currentStatus.last_image) {
      latestReady.value = false;
      latestHasImage.value = false;
      latestCaptureToken.current = '';
      clearImageElement(image);
      return undefined;
    }

    const captureToken = `${currentStatus.last_capture_time || ''}:${currentStatus.last_image || ''}`;
    if (latestCaptureToken.current === captureToken && image.getAttribute('src')) {
      return undefined;
    }

    latestCaptureToken.current = captureToken;
    latestReady.value = false;
    latestHasImage.value = false;
    image.onload = () => {
      latestReady.value = true;
      latestHasImage.value = true;
    };
    image.onerror = () => {
      latestReady.value = false;
      latestHasImage.value = false;
    };
    image.src = latestImageUrl(camera, currentStatus);
    return undefined;
  }, [
    camera.baseUrl,
    camera.apiPathPrefix,
    camera.managed_by_coordinator,
    captureRunning,
    status.value?.last_capture_time,
    status.value?.last_image,
  ]);

  useEffect(() => {
    let cancelled = false;
    let timer = 0;

    async function tick() {
      if (cancelled) return;
      await refresh();
      if (cancelled) return;
      const delay = document.hidden
        ? Math.max(15000, pollDelayMs.current)
        : pollDelayMs.current;
      timer = window.setTimeout(() => void tick(), delay);
    }

    void tick();
    return () => {
      cancelled = true;
      window.clearTimeout(timer);
      refreshGeneration.current += 1;
      releasePreviewStream();
      releaseLatestImage();
    };
  }, [camera.baseUrl]);

  async function handleStart() {
    const payload = buildStartPayload();
    if (!payload) return;

    // Release the browser-side live stream before asking the Pi to open its
    // scheduled capture camera. The server also stops its monitor as a guard.
    releasePreviewStream();

    busy.value = true;
    try {
      updateFromStatus((await postStart(camera, payload as any)) as StatusResponse);
      onUpdated();
    } catch (error: unknown) {
      message.value = `Start failed: ${(error as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleStop() {
    busy.value = true;
    try {
      updateFromStatus((await postStop(camera)) as StatusResponse);
      onUpdated();
    } catch (error: unknown) {
      message.value = `Stop failed: ${(error as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleRemove() {
    if (!confirm(`${camera.camera_label || camera.baseUrl} will be removed from this iPad. Captured images stay on the Raspberry Pi.`)) {
      return;
    }

    const legacyCamera = camera as any;
    if (legacyCamera.managed_by_coordinator && legacyCamera.coordinator_device_id) {
      const coordinatorUrl = coordinatorBaseUrl.value;
      if (coordinatorUrl) {
        try {
          await deleteCoordinatorDevice(coordinatorUrl, legacyCamera.coordinator_device_id);
        } catch (error: unknown) {
          alert(`Coordinator removal failed: ${(error as Error).message}`);
          return;
        }
      }
    }

    removeCamera(camera);
    onUpdated();
  }

  const current = status.value;
  const build = camera.build_info;
  const isCapturing = captureRunning;
  const shadowOnly = current
    ? current.mesh_shadow_mode && !current.adaptive_timelapse_mode && !current.live_adaptive_enabled
    : null;

  // Storage of the ACTIVE capture directory (USB when switched to it, else SD).
  const sys = system.value;
  const onUsb = sys ? /\/(media|mnt)\//.test(sys.storage_path) : false;
  const storageText = sys
    ? `${formatBytes(sys.storage_free_bytes)} free`
    : '-';
  const storageSub = sys ? `${onUsb ? 'USB' : 'SD'} · ${sys.storage_percent_used}% used` : '';
  // Power: no fuel gauge on a plain power bank, so show input-rail voltage
  // (battery-health proxy) + undervoltage flag. null voltage = no PMIC.
  const undervolt = sys?.undervoltage_now
    ? 'low now'
    : sys?.undervoltage_occurred
      ? 'dipped'
      : sys
        ? 'OK'
        : '';
  const powerText = sys && sys.supply_voltage_v != null
    ? `${sys.supply_voltage_v.toFixed(2)}V`
    : sys
      ? undervolt || 'n/a'
      : '-';
  const powerBad = Boolean(sys?.undervoltage_now || sys?.undervoltage_occurred);
  const pillClass = connectionState.value === 'offline'
    ? s.pillOffline
    : !current
      ? s.pillOffline
      : current.running
        ? s.pillRunning
        : s.pillStopped;
  const pillText = connectionState.value === 'offline'
    ? 'offline'
    : !current
      ? 'checking'
      : current.lifecycle_state === 'stopping'
        ? 'stopping'
        : current.lifecycle_state === 'error'
          ? 'error'
          : current.running
            ? 'capturing'
            : 'stopped';

  return (
    <article class={`${s.cameraCard}${camera.is_noir ? ` ${s.cameraCardNoir}` : ''}`}>
      <div class={s.cameraHeader}>
        <div>
          <p class={s.cameraLabel}>
            OBSERVATION UNIT {index + 1} / {camera.device_name || camera.device_id}
          </p>
          <h2>{camera.camera_label || 'PolliPi Camera'}</h2>
          <p class={s.sensor}>
            {camera.camera_model || '-'} / {camera.camera_profile || 'unspecified'} / {camera.baseUrl}
          </p>
          <p class={s.sensor}>
            server {shortCommit(build?.git_commit)} / bundled web {build?.web_build_id || 'unknown'}
          </p>
        </div>
        <span class={`${s.pill} ${pillClass}`}>{pillText}</span>
      </div>

      <div class={s.imageFrame}>
        {!isCapturing && (
          <>
            <img
              ref={previewRef}
              class={`${s.imageFrameImg}${previewReady.value ? ` ${s.imageFrameImgReady}` : ''}`}
              alt="Live framing monitor"
              draggable={false}
            />
            {!previewHasFrame.value && (
              <p class={s.imageFrameEmpty}>Starting live monitor</p>
            )}
          </>
        )}

        {isCapturing && (
          <>
            <img
              ref={imageRef}
              class={`${s.imageFrameImg}${latestReady.value ? ` ${s.imageFrameImgReady}` : ''}`}
              alt="Latest saved timelapse image"
              draggable={false}
            />
            {!latestHasImage.value && (
              <p class={s.imageFrameEmpty}>Saving first scheduled photo...</p>
            )}
          </>
        )}
      </div>

      <dl class={s.metrics}>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>High-res interval</dt>
          <dd class={s.metricsDd}>{seconds(current?.interval_sec)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Saved photos</dt>
          <dd class={s.metricsDd}>{current ? current.capture_count : '-'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Last saved</dt>
          <dd class={s.metricsDd}>{formatCaptureTime(current?.last_capture_time)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Probe interval</dt>
          <dd class={s.metricsDd}>{seconds(current?.probe_interval_sec)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Would-be mode</dt>
          <dd class={s.metricsDd}>{current?.would_be_mode || '-'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Would-be interval</dt>
          <dd class={s.metricsDd}>{seconds(current?.would_be_interval_sec)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Shadow only</dt>
          <dd class={s.metricsDd}>{shadowOnly === null ? '-' : shadowOnly ? 'on' : 'off'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Policy profile</dt>
          <dd class={s.metricsDd}>{current?.policy_profile_id || 'unknown'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Storage free</dt>
          <dd class={s.metricsDd}>
            {storageText}
            {storageSub && <span class={s.metricsSub}>{storageSub}</span>}
          </dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Power (in)</dt>
          <dd class={s.metricsDd} style={powerBad ? 'color:var(--danger,#c0392b)' : undefined}>
            {powerText}
            {sys && sys.supply_voltage_v != null && (
              <span class={s.metricsSub}>{undervolt}</span>
            )}
          </dd>
        </div>
      </dl>

      <p class={s.cameraMessage}>
        {current?.last_capture_time
          ? `Latest scheduled JPEG: ${formatCaptureTime(current.last_capture_time)}. ${message.value}`
          : message.value}
      </p>

      <div class={s.cardActions}>
        <button
          class={s.btnPrimary}
          type="button"
          onClick={handleStart}
          disabled={busy.value || Boolean(current?.running)}
        >
          {busy.value ? 'Working...' : 'Start'}
        </button>
        <button
          class={s.btnSecondary}
          type="button"
          onClick={handleStop}
          disabled={busy.value || !current?.running}
        >
          Stop
        </button>
        <button class={s.btnSecondary} type="button" onClick={() => void refresh()} disabled={busy.value}>
          Refresh
        </button>
        <button class={s.btnRemoveCamera} type="button" onClick={() => void handleRemove()} disabled={busy.value}>
          Remove
        </button>
      </div>

      <StoragePanel camera={camera} capturing={isCapturing} />

      <details class={s.debugDetails}>
        <summary class={s.debugDetailsSummary}>Connection details</summary>
        <p class={s.debugStatus}>lifecycle: {current?.lifecycle_state || '-'}</p>
        <p class={s.debugStatus}>preview subscribers: {current?.preview_subscriber_count ?? '-'}</p>
        <p class={s.debugStatus}>preview producer: {current?.preview_producer_state || '-'}</p>
        <p class={s.debugStatus}>simulation: {current?.simulation_run_id || '-'}</p>
        <p class={s.debugStatus}>kind: {current?.kind || '-'}</p>
        <p class={s.debugStatus}>live allowed: {current?.live_allowed ? 'true' : 'false'}</p>
        <p class={s.debugStatus}>connection: {connectionState.value}</p>
      </details>
    </article>
  );
}
