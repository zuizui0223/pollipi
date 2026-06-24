import { h } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import { useSignal } from '@preact/signals';

import type { Camera, DeviceInfo, StatusResponse } from '../api/types';
import {
  deleteCoordinatorDevice,
  fetchDevice,
  fetchStatus,
  getMjpegStreamUrl,
  postStart,
  postStop,
} from '../api/client';
import {
  autonomousMode,
  intervalSec,
  policyProfileId,
} from '../state/session';
import { removeCamera } from '../state/devices';
import { coordinatorBaseUrl } from '../state/coordinator';
import { formatCaptureTime } from '../lib/formatting';
import * as s from '../styles/components.css';

interface Props {
  camera: Camera;
  index: number;
  onUpdated: () => void;
}

type ConnectionState = 'online' | 'degraded' | 'reconnecting' | 'offline' | 'stale';

function buildStartPayload() {
  const interval = intervalSec.value;
  if (!Number.isFinite(interval) || interval < 1 || interval > 3600) {
    alert('Capture interval must be between 1 and 3600 seconds.');
    return null;
  }

  return {
    interval_sec: interval,
    autonomous_mode: autonomousMode.value,
    adaptive_timelapse_mode: false,
    mesh_shadow_mode: true,
    policy_profile_id: policyProfileId.value,
  };
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

function meshDecisionLabel(status: StatusResponse | null): string {
  const state = (status as any)?.mesh_decision;
  if (state === 'strong_visitation_candidate') return 'strong activity';
  if (state === 'uncertain_local_activity') return 'uncertain activity';
  if (state === 'environmental_noise') return 'environmental noise';
  if (state === 'no_activity') return 'no activity';
  return 'waiting';
}

function shortCommit(value?: string | null): string {
  if (!value) return 'unknown';
  return value.length > 12 ? value.slice(0, 12) : value;
}

function seconds(value?: number | null): string {
  return Number.isFinite(value) ? `${value} sec` : '-';
}

export function DeviceCard({ camera, index, onUpdated }: Props) {
  const busy = useSignal(false);
  const status = useSignal<StatusResponse | null>(null);
  const message = useSignal('Reading status...');
  const connectionState = useSignal<ConnectionState>('stale');
  const imageReady = useSignal(false);
  const hasImage = useSignal(false);
  const imageRef = useRef<HTMLImageElement>(null);

  const pollDelayMs = useRef(5000);
  const refreshInFlight = useRef(false);
  const refreshGeneration = useRef(0);

  function updateFromStatus(next: StatusResponse) {
    status.value = next;
    applyStatus(camera, next);

    message.value = next.mesh_reason || next.interval_reason || next.message || 'Status updated.';

    const image = imageRef.current;
    if (next.running) {
      imageReady.value = false;
      hasImage.value = false;
      image?.removeAttribute('src');
      return;
    }

    const streamUrl = getMjpegStreamUrl(camera);
    if (image && image.src !== streamUrl) {
      imageReady.value = false;
      hasImage.value = false;
      image.onload = () => {
        imageReady.value = true;
        hasImage.value = true;
      };
      image.onerror = () => {
        imageReady.value = false;
        hasImage.value = false;
      };
      image.src = streamUrl;
    }
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
      const [device, next] = await Promise.all([
        fetchDevice(camera, { signal: controller.signal }).catch(() => null),
        fetchStatus(camera, { signal: controller.signal }),
      ]);
      if (generation !== refreshGeneration.current) return;

      if (device) applyDeviceInfo(camera, device);
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
    };
  }, [camera.baseUrl]);

  async function handleStart() {
    const payload = buildStartPayload();
    if (!payload) return;

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
  const isCapturing = Boolean(current?.running);
  const shadowOnly = current
    ? current.mesh_shadow_mode && !current.adaptive_timelapse_mode && !current.live_adaptive_enabled
    : null;
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
            {(build?.deployment_mode || 'unknown')} / commit {shortCommit(build?.git_commit)} / web {build?.web_build_id || 'unknown'}
          </p>
        </div>
        <span class={`${s.pill} ${pillClass}`}>{pillText}</span>
      </div>

      <div class={s.imageFrame}>
        {!isCapturing && (
          <img
            ref={imageRef}
            class={`${s.imageFrameImg}${imageReady.value ? ` ${s.imageFrameImgReady}` : ''}`}
            alt="Idle MJPEG live preview"
            draggable={false}
          />
        )}
        {isCapturing && <p class={s.imageFrameEmpty}>Capturing</p>}
        {!isCapturing && !hasImage.value && <p class={s.imageFrameEmpty}>Starting live preview</p>}
      </div>

      <dl class={s.metrics}>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>High-res interval</dt>
          <dd class={s.metricsDd}>{seconds(current?.interval_sec)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Probe interval</dt>
          <dd class={s.metricsDd}>{seconds(current?.probe_interval_sec)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Would-be mode</dt>
          <dd class={s.metricsDd}>{current?.would_be_mode || meshDecisionLabel(current)}</dd>
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
      </dl>

      <p class={s.cameraMessage}>
        {(current as any)?.mesh_reason || (current as any)?.interval_reason || message.value}
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

      <details class={s.debugDetails}>
        <summary class={s.debugDetailsSummary}>Connection details</summary>
        <p class={s.debugStatus}>lifecycle: {(current as any)?.lifecycle_state || '-'}</p>
        <p class={s.debugStatus}>preview producer: {(current as any)?.preview_producer_state || '-'}</p>
        <p class={s.debugStatus}>simulation: {current?.simulation_run_id || '-'}</p>
        <p class={s.debugStatus}>kind: {current?.kind || '-'}</p>
        <p class={s.debugStatus}>last capture: {formatCaptureTime(current?.last_capture_time)}</p>
        <p class={s.debugStatus}>connection: {connectionState.value}</p>
      </details>
    </article>
  );
}
