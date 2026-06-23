import { h } from 'preact';
import { useEffect, useRef } from 'preact/hooks';
import { useSignal } from '@preact/signals';

import type { Camera, StatusResponse } from '../api/types';
import {
  deleteCoordinatorDevice,
  deviceUrl,
  fetchStatus,
  postStart,
  postStop,
} from '../api/client';
import {
  adaptiveMaxIntervalSec,
  adaptiveMinIntervalSec,
  adaptiveTimelapseMode,
  adaptiveWindowSec,
  autonomousMode,
  getSessionMetadata,
  intervalSec,
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
    alert('撮影間隔は1秒以上3600秒以下で入力してください。');
    return null;
  }

  const adaptiveEnabled = adaptiveTimelapseMode.value;
  const minInterval = adaptiveMinIntervalSec.value;
  const maxInterval = adaptiveMaxIntervalSec.value;
  const windowSec = adaptiveWindowSec.value;
  if (
    adaptiveEnabled &&
    (!Number.isFinite(minInterval) ||
      !Number.isFinite(maxInterval) ||
      !Number.isFinite(windowSec) ||
      minInterval < 1 ||
      maxInterval < minInterval ||
      maxInterval > 3600 ||
      windowSec < 60 ||
      windowSec > 3600)
  ) {
    alert('適応型タイムラプスの設定値を確認してください。');
    return null;
  }

  // Active intent. The fixed legacy fields below are temporary server-compatibility
  // values and are not exposed as active UI controls.
  return {
    interval_sec: interval,
    autonomous_mode: autonomousMode.value,
    adaptive_timelapse_mode: adaptiveEnabled,
    adaptive_min_interval_sec: minInterval,
    adaptive_max_interval_sec: maxInterval,
    adaptive_window_sec: windowSec,
    mesh_shadow_mode: !adaptiveEnabled,
    ...getSessionMetadata(),

    auto_mode: false,
    motion_trigger_mode: false,
    hybrid_mode: false,
    ml_assist_mode: false,
    idle_interval_sec: interval,
    detection_interval_sec: interval,
    pixel_difference: 30,
    motion_ratio: 0.01,
  };
}

function meshDecisionLabel(status: StatusResponse | null): string {
  const state = (status as any)?.mesh_decision;
  if (state === 'strong_visitation_candidate') return '強い局所活動';
  if (state === 'uncertain_local_activity') return '局所活動・保留';
  if (state === 'environmental_noise') return '環境ノイズ';
  if (state === 'no_activity') return '活動なし';
  return '判定待ち';
}

export function DeviceCard({ camera, index, onUpdated }: Props) {
  const busy = useSignal(false);
  const status = useSignal<StatusResponse | null>(null);
  const message = useSignal('状態を読み込み中...');
  const connectionState = useSignal<ConnectionState>('stale');
  const imageReady = useSignal(false);
  const hasImage = useSignal(false);
  const imageRef = useRef<HTMLImageElement>(null);

  const pollDelayMs = useRef(5000);
  const refreshInFlight = useRef(false);
  const refreshGeneration = useRef(0);

  function updateFromStatus(next: StatusResponse) {
    status.value = next;
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

    message.value = next.mesh_reason || next.interval_reason || next.message || '状態を更新しました。';

    if (next.last_image && next.last_image !== (camera as any).previousImage) {
      const image = imageRef.current;
      if (image) {
        image.onload = () => {
          imageReady.value = true;
          hasImage.value = true;
        };
        image.onerror = () => {
          imageReady.value = false;
        };
        image.src = deviceUrl(
          camera,
          `/latest?capture=${encodeURIComponent(next.last_capture_time || String(Date.now()))}`,
        );
        (camera as any).previousImage = next.last_image;
      }
    } else if (!next.last_image) {
      imageReady.value = false;
      hasImage.value = false;
      imageRef.current?.removeAttribute('src');
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
      const next = (await fetchStatus(camera, {
        signal: controller.signal,
      })) as StatusResponse;
      if (generation !== refreshGeneration.current) return;

      updateFromStatus(next);
      connectionState.value = 'online';
      pollDelayMs.current = document.hidden ? 15000 : 5000;
    } catch (error: unknown) {
      connectionState.value = status.value ? 'degraded' : 'offline';
      pollDelayMs.current = Math.min(
        30000,
        Math.max(5000, Math.round(pollDelayMs.current * 1.7 + Math.random() * 500)),
      );
      message.value = `接続できません: ${(error as Error).message}`;
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
      message.value = `開始できません: ${(error as Error).message}`;
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
      message.value = `停止できません: ${(error as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleRemove() {
    if (!confirm(`${camera.camera_label} の登録をこのiPadから削除しますか？\n撮影画像はRaspberry Piに残ります。`)) {
      return;
    }

    const legacyCamera = camera as any;
    if (legacyCamera.managed_by_coordinator && legacyCamera.coordinator_device_id) {
      const coordinatorUrl = coordinatorBaseUrl.value;
      if (coordinatorUrl) {
        try {
          await deleteCoordinatorDevice(coordinatorUrl, legacyCamera.coordinator_device_id);
        } catch (error: unknown) {
          alert(`Coordinatorでの削除に失敗しました: ${(error as Error).message}`);
          return;
        }
      }
    }

    removeCamera(camera);
    onUpdated();
  }

  const current = status.value;
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
      ? '確認中'
      : current.lifecycle_state === 'stopping'
        ? '停止処理中'
        : current.lifecycle_state === 'error'
          ? 'error'
          : current.running
            ? '撮影中'
            : '停止中';

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
        </div>
        <span class={`${s.pill} ${pillClass}`}>{pillText}</span>
      </div>

      <div class={s.imageFrame}>
        <img
          ref={imageRef}
          class={`${s.imageFrameImg}${imageReady.value ? ` ${s.imageFrameImgReady}` : ''}`}
          alt="最新タイムラプス画像"
          draggable={false}
        />
        {!hasImage.value && <p class={s.imageFrameEmpty}>最新画像を待っています</p>}
      </div>

      <dl class={s.metrics}>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>状態</dt>
          <dd class={s.metricsDd}>{meshDecisionLabel(current)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>次回間隔</dt>
          <dd class={s.metricsDd}>{(current as any)?.next_interval_sec ?? '-'} 秒</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>最終撮影</dt>
          <dd class={s.metricsDd}>{formatCaptureTime(current?.last_capture_time)}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>接続</dt>
          <dd class={s.metricsDd}>{connectionState.value}</dd>
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
          {busy.value ? '処理中...' : '開始'}
        </button>
        <button
          class={s.btnSecondary}
          type="button"
          onClick={handleStop}
          disabled={busy.value || !current?.running}
        >
          停止
        </button>
        <button class={s.btnSecondary} type="button" onClick={() => void refresh()} disabled={busy.value}>
          更新
        </button>
        <button class={s.btnRemoveCamera} type="button" onClick={() => void handleRemove()} disabled={busy.value}>
          削除
        </button>
      </div>

      <details class={s.roiAdvanced}>
        <summary class={s.roiAdvancedSummary}>接続・ビルド詳細</summary>
        <p class={s.roiStatus}>lifecycle: {(current as any)?.lifecycle_state || '-'}</p>
        <p class={s.roiStatus}>preview producer: {(current as any)?.preview_producer_state || '-'}</p>
        <p class={s.roiStatus}>
          ライブモニターは安定性検証まで保留中です。通常のカードはMJPEGを開きません。
        </p>
      </details>
    </article>
  );
}
