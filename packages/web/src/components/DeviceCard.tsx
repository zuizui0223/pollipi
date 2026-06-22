import { h } from 'preact';
import { useRef, useEffect } from 'preact/hooks';
import { useSignal, useComputed } from '@preact/signals';
import type { Camera, StatusResponse } from '../api/types';
import type { RoiRect } from '../lib/roi';
import { normalizeRoi, roiToDisplayRect, defaultCenteredRoi, MONITOR_WIDTH, MONITOR_HEIGHT } from '../lib/roi';
import { formatCaptureTime, formatBytes } from '../lib/formatting';
import { persistCameras, removeCamera, syncWorkflowAliases } from '../state/devices';
import {
  intervalSec,
  autoMode,
  motionTriggerMode,
  hybridMode,
  autonomousMode,
  mlAssistMode,
  idleIntervalSec,
  detectionIntervalSec,
  pixelDifference,
  motionRatio,
  getSessionMetadata,
  adaptiveTimelapseMode,
  adaptiveMinIntervalSec,
  adaptiveWindowSec,
} from '../state/session';
import { deviceUrl, postStart, postStop, fetchStatus, fetchSystem, fetchDevice, deleteCoordinatorDevice } from '../api/client';
import { coordinatorBaseUrl, coordinatorOnline } from '../state/coordinator';
import { RoiEditor } from './RoiEditor';
import * as s from '../styles/components.css';

interface Props {
  camera: Camera;
  index: number;
  onUpdated: () => void;
}

function getStartPayload(camera: Camera) {
  const interval = intervalSec.value;
  if (!Number.isFinite(interval) || interval < 1 || interval > 3600) {
    alert('撮影間隔は 1 秒以上 3600 秒以下で入力してください。');
    return null;
  }
  const idle = idleIntervalSec.value;
  const detection = detectionIntervalSec.value;
  const pd = pixelDifference.value;
  const mr = motionRatio.value;
  const isAuto = autoMode.value || motionTriggerMode.value || hybridMode.value;
  if (isAuto && (!Number.isFinite(idle) || idle < 1 || idle > 3600 ||
    !Number.isFinite(detection) || detection < 1 || detection > 3600)) {
    alert('自動間隔は 1 秒以上 3600 秒以下で入力してください。');
    return null;
  }
  if (!Number.isFinite(pd) || pd < 1 || pd > 255) {
    alert('pixel_difference は 1 以上 255 以下で入力してください。');
    return null;
  }
  if (!Number.isFinite(mr) || mr < 0.0001 || mr > 1) {
    alert('motion_ratio は 0.0001 以上 1 以下で入力してください。');
    return null;
  }
  if (!camera.angleConfirmed) {
    alert('撮影前に画角を確認してください。');
    return null;
  }
  const drawnRoi = normalizeRoi(camera.roi);
  if (camera.roiStale && drawnRoi) {
    alert('画角を再調整したため、ROIをもう一度指定してください。');
    return null;
  }
  const adaptive = adaptiveTimelapseMode.value;
  const adaptiveMin = adaptiveMinIntervalSec.value;
  const adaptiveWin = adaptiveWindowSec.value;
  if (adaptive && (!Number.isFinite(adaptiveMin) || adaptiveMin < 1 || adaptiveMin > 3600 ||
    !Number.isFinite(adaptiveWin) || adaptiveWin < 60 || adaptiveWin > 3600)) {
    alert('適応型タイムラプスの設定値を確認してください (最小間隔 1~3600秒, ウィンドウ 60~3600秒)。');
    return null;
  }
  const metadata = getSessionMetadata();
  const payload: Record<string, unknown> = {
    interval_sec: interval,
    auto_mode: autoMode.value,
    motion_trigger_mode: motionTriggerMode.value,
    hybrid_mode: hybridMode.value,
    ml_assist_mode: mlAssistMode.value,
    autonomous_mode: autonomousMode.value,
    adaptive_timelapse_mode: adaptive,
    adaptive_min_interval_sec: adaptiveMin,
    adaptive_window_sec: adaptiveWin,
    idle_interval_sec: idle,
    detection_interval_sec: detection,
    pixel_difference: Math.round(pd),
    motion_ratio: mr,
    ...metadata,
  };
  if (drawnRoi) {
    payload.roi_x = drawnRoi.roi_x;
    payload.roi_y = drawnRoi.roi_y;
    payload.roi_w = drawnRoi.roi_w;
    payload.roi_h = drawnRoi.roi_h;
    payload.roi_tracking = camera.roi_tracking;
    if (camera.roi_tracking) {
      payload.roi_search_margin = camera.roi_search_margin;
      payload.roi_tracking_min_score = camera.roi_tracking_min_score;
    }
  }
  return payload;
}

export function DeviceCard({ camera, index, onUpdated }: Props) {
  // Local UI state
  const monitoring = useSignal(false);
  const aiMonitoring = useSignal(false);
  const busy = useSignal(false);
  const message = useSignal('接続しています...');
  const status = useSignal<StatusResponse | null>(null);
  const storage = useSignal('-');
  const power = useSignal('-');
  const buildDetails = useSignal('build unknown');

  // ROI state
  const confirmedRoi = useSignal<RoiRect | null>(normalizeRoi(camera.roi));
  const editingRoi = useSignal<RoiRect | null>(null);
  const roiDrawerOpen = useSignal(false);
  const angleConfirmed = useSignal(camera.angle_confirmed);
  const roiStale = useSignal(camera.roi_stale);
  const roiTracking = useSignal(camera.roi_tracking);
  const roiSearchMargin = useSignal(camera.roi_search_margin);
  const roiTrackingMinScore = useSignal(camera.roi_tracking_min_score);

  // Image frame
  const imageRef = useRef<HTMLImageElement>(null);
  const imageWrapRef = useRef<HTMLDivElement>(null);
  const monitorRoiBoxRef = useRef<HTMLSpanElement>(null);
  const imgReady = useSignal(false);
  const hasImage = useSignal(false);

  const roiConfirmed = useComputed(
    () => Boolean(confirmedRoi.value && !roiStale.value),
  );

  // Sync camera state from signals back to the camera object (for persistence)
  function syncBack() {
    camera.angle_confirmed = angleConfirmed.value;
    camera.roi = confirmedRoi.value;
    camera.roi_stale = roiStale.value;
    camera.roi_tracking = roiTracking.value;
    camera.roi_search_margin = roiSearchMargin.value;
    camera.roi_tracking_min_score = roiTrackingMinScore.value;
    syncWorkflowAliases(camera);
    persistCameras();
  }

  // Render ROI box on monitor image
  useEffect(() => {
    const img = imageRef.current;
    const box = monitorRoiBoxRef.current;
    const wrap = imageWrapRef.current;
    if (!img || !box || !wrap || !imgReady.value) return;

    const st = status.value || {};
    const trackedRoi =
      (st as any).tracked_roi_w
        ? normalizeRoi({
            roi_x: (st as any).tracked_roi_x,
            roi_y: (st as any).tracked_roi_y,
            roi_w: (st as any).tracked_roi_w,
            roi_h: (st as any).tracked_roi_h,
          })
        : null;
    const roi =
      (st as any).roi_tracking && trackedRoi ? trackedRoi : confirmedRoi.value;
    if (!roi) {
      box.style.display = 'none';
      return;
    }
    const imageRect = img.getBoundingClientRect();
    const wrapRect = wrap.getBoundingClientRect();
    box.style.display = 'block';
    box.style.left = `${imageRect.left - wrapRect.left + (roi.roi_x / MONITOR_WIDTH) * imageRect.width}px`;
    box.style.top = `${imageRect.top - wrapRect.top + (roi.roi_y / MONITOR_HEIGHT) * imageRect.height}px`;
    box.style.width = `${(roi.roi_w / MONITOR_WIDTH) * imageRect.width}px`;
    box.style.height = `${(roi.roi_h / MONITOR_HEIGHT) * imageRect.height}px`;
  }, [confirmedRoi.value, imgReady.value, status.value]);

  async function handleStart() {
    const payload = getStartPayload(camera);
    if (!payload) return;
    monitoring.value = false;
    busy.value = true;
    try {
      const result = await postStart(camera, payload as any);
      camera.previousImage = null;
      status.value = result;
      updateFromStatus(result);
    } catch (err: unknown) {
      message.value = `接続できません: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleStop() {
    monitoring.value = false;
    busy.value = true;
    try {
      const result = await postStop(camera);
      status.value = result;
      updateFromStatus(result);
    } catch (err: unknown) {
      message.value = `接続できません: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  function updateFromStatus(st: StatusResponse) {
    status.value = st;
    Object.assign(camera, {
      device_id: st.device_id || camera.device_id,
      device_name: st.device_name || camera.device_name,
      camera_label: st.camera_label || camera.camera_label,
      camera_model: st.camera_model || camera.camera_model,
      camera_profile: st.camera_profile || camera.camera_profile,
      is_ai_camera: Boolean(st.is_ai_camera),
      is_noir: Boolean(st.is_noir),
      is_wide: Boolean(st.is_wide),
      camera_role: st.camera_role || camera.camera_role,
      comparison_session_id: st.comparison_session_id || camera.comparison_session_id,
    });

    const msg = st.auto_mode && st.interval_reason ? st.interval_reason : st.message;
    message.value = `${msg}${st.autonomous_mode && st.running ? ' / 自律運行' : ''}`;

    if (!monitoring.value && st.last_image && st.last_image !== camera.previousImage) {
      const img = imageRef.current;
      if (img) {
        img.onload = () => {
          imgReady.value = true;
          hasImage.value = true;
        };
        img.src = deviceUrl(camera, `/latest?capture=${encodeURIComponent(st.last_capture_time || String(Date.now()))}`);
        camera.previousImage = st.last_image;
      }
    } else if (!st.last_image) {
      imgReady.value = false;
      hasImage.value = false;
      const img = imageRef.current;
      if (img) {
        img.classList.remove('ready');
        img.removeAttribute('src');
      }
    }
  }

  async function refreshBuildInfo() {
    try {
      const device = await fetchDevice(camera);
      camera.build_info = device.build_info;
      const info = device.build_info;
      const commit = info?.git_commit && info.git_commit !== 'unknown' ? info.git_commit : 'unknown';
      const mode = info?.deployment_mode || 'unknown';
      const web = info?.web_build_id && info.web_build_id !== 'unknown' ? info.web_build_id : 'unknown';
      buildDetails.value = `${mode} / ${commit} / ${web}`;
    } catch (_) {
      buildDetails.value = 'build unknown';
    }
  }

  async function refreshCamera() {
    try {
      const st = await fetchStatus(camera) as StatusResponse;
      updateFromStatus(st);
      await refreshBuildInfo();
      // system info
      try {
        const sys = await fetchSystem(camera);
        storage.value = `${formatBytes(sys.storage_free_bytes)} 空き`;
        power.value = sys.undervoltage_now ? '電圧低下中' : sys.undervoltage_occurred ? '電圧低下履歴' : '電圧OK';
      } catch (_) {
        storage.value = '-';
        power.value = '-';
      }
    } catch (err: unknown) {
      // offline
      monitoring.value = false;
      message.value = `接続できません: ${(err as Error).message}`;
    }
  }

  // Expose refresh to parent via prop callback
  useEffect(() => {
    let cancelled = false;
    async function tick() {
      if (!cancelled) await refreshCamera();
    }
    void tick();
    const id = window.setInterval(() => {
      void tick();
    }, 5000);
    return () => {
      cancelled = true;
      window.clearInterval(id);
    };
  }, [camera.baseUrl]);

  // Angle / monitor workflow
  function openAngleMonitor() {
    // Mark ROI stale if there's one
    if (normalizeRoi(confirmedRoi.value)) {
      roiStale.value = true;
      angleConfirmed.value = false;
      editingRoi.value = null;
      syncBack();
      message.value = '画角を変更した場合は、ROIをもう一度指定してください。';
    }
    roiDrawerOpen.value = false;
    angleConfirmed.value = false;
    syncBack();
    startMonitor(false);
    message.value = '画角確認中です。花が画面中央付近に入るようにカメラを調整してください。';
  }

  function confirmAngle() {
    stopMonitor();
    angleConfirmed.value = true;
    syncBack();
    openRoiPreview({ message: '画角を固定しました。静止画像の上でROIを指定してください。', forceReselect: true });
  }

  function startMonitor(ai: boolean) {
    monitoring.value = true;
    aiMonitoring.value = ai;
    const img = imageRef.current;
    if (!img) return;
    img.onload = () => {
      imgReady.value = true;
      hasImage.value = true;
    };
    img.onerror = () => {
      monitoring.value = false;
      message.value = '画面を取得できません';
    };
    img.src = deviceUrl(camera, `/mjpeg?detect=${ai ? 'true' : 'false'}&t=${Date.now()}`);
  }

  function stopMonitor() {
    monitoring.value = false;
    aiMonitoring.value = false;
    const st = status.value;
    const img = imageRef.current;
    if (!img) return;
    if (st && st.last_image) {
      img.src = deviceUrl(camera, `/latest?capture=${encodeURIComponent(st.last_capture_time || String(Date.now()))}`);
    } else {
      imgReady.value = false;
      hasImage.value = false;
      img.removeAttribute('src');
    }
  }

  function toggleMonitor(ai: boolean) {
    if (monitoring.value && aiMonitoring.value === ai) {
      stopMonitor();
      message.value = ai ? 'AI検出モニターを停止しました。' : '画角モニターを停止しました。';
      return;
    }
    if (ai && status.value && status.value.running) {
      alert('AI検出モニターは撮影を停止してから使用してください。');
      return;
    }
    startMonitor(ai);
    message.value = ai
      ? 'AI検出モニター表示中（保存されません）。'
      : '画角確認中です。花が画面中央付近に入るようにカメラを調整してください。';
  }

  function openRoiPreview(opts: { message?: string; forceReselect?: boolean } = {}) {
    if (!angleConfirmed.value && !opts.forceReselect) {
      alert('先に「画角を確認」して、「この画角でOK」を押してください。');
      return;
    }
    stopMonitor();
    // Start with existing or default ROI
    const initial =
      opts.forceReselect || roiStale.value
        ? defaultCenteredRoi()
        : normalizeRoi(confirmedRoi.value) || defaultCenteredRoi();
    editingRoi.value = initial;
    camera.editing_roi = initial;
    roiDrawerOpen.value = true;
    if (opts.message) message.value = opts.message;
  }

  function handleRoiAccepted(roi: RoiRect) {
    confirmedRoi.value = roi;
    roiStale.value = false;
    editingRoi.value = null;
    camera.roi = roi;
    camera.editing_roi = null;
    camera.roi_stale = false;
    camera.angle_confirmed = true;
    angleConfirmed.value = true;
    syncBack();
    roiDrawerOpen.value = false;
    message.value = 'このROIを設定しました。';
  }

  function handleRoiRedraw() {
    editingRoi.value = defaultCenteredRoi();
    camera.editing_roi = editingRoi.value;
    message.value = 'ROIをリセットしました。静止画像の上でROIをもう一度指定してください。';
  }

  function handleRoiCancel() {
    editingRoi.value = null;
    camera.editing_roi = null;
    roiDrawerOpen.value = false;
    syncBack();
    message.value = 'ROI指定から戻りました。';
  }

  function handleReadjustAngle() {
    if (normalizeRoi(confirmedRoi.value)) roiStale.value = true;
    angleConfirmed.value = false;
    editingRoi.value = null;
    camera.editing_roi = null;
    roiDrawerOpen.value = false;
    syncBack();
    openAngleMonitor();
    message.value = '画角を変更した場合は、ROIをもう一度指定してください。';
  }

  function clearRoi() {
    confirmedRoi.value = null;
    editingRoi.value = null;
    roiStale.value = false;
    roiTracking.value = false;
    camera.roi = null;
    camera.editing_roi = null;
    camera.roi_stale = false;
    camera.roi_tracking = false;
    syncBack();
    message.value = 'ROIを解除しました。動き検出は全画面で行います。';
  }

  async function handleRemove() {
    if (!confirm(`${camera.camera_label} の登録をこの iPad から削除しますか？\n撮影画像は Raspberry Pi に残ります。`)) return;
    if (camera.managed_by_coordinator && camera.coordinator_device_id) {
      const coordinatorUrl = coordinatorBaseUrl.value;
      if (coordinatorUrl) {
        try {
          await deleteCoordinatorDevice(coordinatorUrl, camera.coordinator_device_id);
        } catch (err: any) {
          alert(`Coordinator での削除に失敗しました: ${err.message}`);
          return;
        }
      }
    }
    removeCamera(camera);
    onUpdated();
  }

  // ROI status text
  const roiStatusText = (() => {
    const editing = editingRoi.value;
    const roi = confirmedRoi.value;
    if (roiDrawerOpen.value && editing) {
      return `ROI: 編集中 x=${editing.roi_x}, y=${editing.roi_y}, w=${editing.roi_w}, h=${editing.roi_h}`;
    }
    if (roi && roiStale.value) return 'ROI: 再指定が必要';
    if (roi && !roiStale.value) return `ROI: 設定済み x=${roi.roi_x}, y=${roi.roi_y}, w=${roi.roi_w}, h=${roi.roi_h}`;
    return 'ROI: 未設定';
  })();

  // Tracking status
  const trackingStatusText = (() => {
    const st = (status.value || {}) as any;
    const roi = confirmedRoi.value;
    if (!roi && !st.tracked_roi_w) return '花の揺れに追従: OFF';
    if (!st.roi_tracking && !roiTracking.value) return '花の揺れに追従: OFF';
    const score = st.roi_tracking_score == null ? '-' : Number(st.roi_tracking_score).toFixed(2);
    const ok = st.roi_tracking_success ? '追跡中' : '前回ROIを保持';
    const sx = st.roi_shift_x == null ? '-' : st.roi_shift_x;
    const sy = st.roi_shift_y == null ? '-' : st.roi_shift_y;
    return `花の揺れに追従: ON / score ${score} / ${ok} / shift x=${sx}, y=${sy}`;
  })();

  const st = status.value;
  const pillClass = !st ? s.pillOffline : st.running ? s.pillRunning : s.pillStopped;
  const pillText = !st ? '確認中' : st.running ? '撮影中' : '停止中';

  const badges = [
    camera.is_ai_camera ? 'AI' : null,
    camera.is_noir ? 'IR / NoIR' : null,
    camera.is_wide ? 'Wide' : null,
    camera.camera_profile || null,
    camera.camera_role || (st && (st as any).camera_role) || null,
    camera.comparison_session_id || (st && (st as any).comparison_session_id) || null,
  ].filter(Boolean) as string[];

  const isAiCamera =
    camera.is_ai_camera || (camera.camera_model || '').toLowerCase() === 'imx500';

  return (
    <article class={`${s.cameraCard}${camera.is_noir ? ' ' + s.cameraCardNoir : ''}`}>
      {/* Header */}
      <div class={s.cameraHeader}>
        <div>
          <p class={s.cameraLabel}>
            OBSERVATION UNIT {index + 1} / {camera.device_name || camera.device_id}
          </p>
          <h2>{camera.camera_label || 'PolliPi Camera'}</h2>
          <p class={s.sensor}>
            {camera.camera_model || '-'} / {camera.camera_profile || 'unspecified'} /{' '}
            {camera.baseUrl}
          </p>
          {badges.length > 0 && (
            <div class={s.cameraBadgesWrap}>
              {badges.map((b) => (
                <span key={b} class={s.cameraBadge}>
                  {b}
                </span>
              ))}
            </div>
          )}
        </div>
        <span class={`${s.pill} ${pillClass}`}>{pillText}</span>
      </div>

      {/* Image frame */}
      <div ref={imageWrapRef} class={s.imageFrame}>
        <img
          ref={imageRef}
          class={`${s.imageFrameImg}${imgReady.value ? ' ' + s.imageFrameImgReady : ''}`}
          alt="観察機の画像"
          draggable={false}
        />
        <span
          ref={monitorRoiBoxRef}
          class={s.monitorRoiBox}
          style={{ display: 'none' }}
        />
        {!hasImage.value && (
          <p class={s.imageFrameEmpty}>最新画像を待っています</p>
        )}
      </div>

      {/* ROI Panel */}
      <section class={s.roiPanel}>
        <div class={s.workflowStatus}>
          <span class={s.workflowStatusSpan}>
            画角: {angleConfirmed.value ? '確認済み' : '未確認'}
          </span>
          <span class={s.workflowStatusSpan}>
            ROI:{' '}
            {roiDrawerOpen.value && editingRoi.value
              ? '編集中'
              : roiConfirmed.value
              ? '設定済み'
              : confirmedRoi.value && roiStale.value
              ? '再指定が必要'
              : '未設定'}
          </span>
        </div>
        <div class={s.roiActions}>
          {/* Angle check button */}
          {!roiDrawerOpen.value && !(monitoring.value && !aiMonitoring.value) && (
            <button class={s.btnSecondary} type="button" onClick={openAngleMonitor}>
              {angleConfirmed.value ? '画角を再調整' : '画角を確認'}
            </button>
          )}
          {/* Confirm angle button */}
          {!roiDrawerOpen.value && monitoring.value && !aiMonitoring.value && (
            <button class={s.btnSecondary} type="button" onClick={confirmAngle}>
              この画角でOK
            </button>
          )}
          {/* ROI specify button */}
          {!roiDrawerOpen.value && angleConfirmed.value && !(monitoring.value && !aiMonitoring.value) && (
            <button
              class={s.btnSecondary}
              type="button"
              onClick={() => openRoiPreview()}
              disabled={!angleConfirmed.value}
            >
              {roiConfirmed.value ? 'ROIを再指定' : 'ROIを指定'}
            </button>
          )}
          {/* ROI clear button */}
          {!roiDrawerOpen.value && roiConfirmed.value && (
            <button class={s.btnSecondary} type="button" onClick={clearRoi}>
              ROIを解除
            </button>
          )}
        </div>

        <p class={s.roiStatus}>{roiStatusText}</p>
        <p class={s.roiStatus} style={{ fontSize: '12px' }}>
          ROIは640 x 360の監視フレーム上で保存されます。
        </p>

        {/* ROI Tracking toggle */}
        <label class={s.roiTrackToggle}>
          <input
            type="checkbox"
            checked={roiTracking.value}
            style={{ width: '20px', height: '20px', accentColor: 'var(--leaf)' }}
            onChange={(e) => {
              const checked = (e.target as HTMLInputElement).checked;
              if (checked && !normalizeRoi(confirmedRoi.value)) {
                alert('先に「ROIを指定」で観察したい範囲を指定してください。');
                (e.target as HTMLInputElement).checked = false;
                return;
              }
              roiTracking.value = checked;
              camera.roi_tracking = checked;
              persistCameras();
            }}
          />
          <span>花の揺れに追従: {roiTracking.value ? 'ON' : 'OFF'}</span>
        </label>

        <details class={s.roiAdvanced}>
          <summary class={s.roiAdvancedSummary}>ROI追跡の詳細設定</summary>
          <div style={{ display: 'grid', gap: '8px', marginTop: '8px' }}>
            <label class={s.advancedGridLabel}>
              roi_search_margin
              <input
                type="number"
                min={0}
                max={160}
                inputMode="numeric"
                value={roiSearchMargin.value}
                onInput={(e) => {
                  roiSearchMargin.value = Number((e.target as HTMLInputElement).value || 30);
                  camera.roi_search_margin = roiSearchMargin.value;
                  persistCameras();
                }}
              />
            </label>
            <label class={s.advancedGridLabel}>
              roi_tracking_min_score
              <input
                type="number"
                min={-1}
                max={1}
                step={0.05}
                inputMode="decimal"
                value={roiTrackingMinScore.value}
                onInput={(e) => {
                  roiTrackingMinScore.value = Number((e.target as HTMLInputElement).value || 0.45);
                  camera.roi_tracking_min_score = roiTrackingMinScore.value;
                  persistCameras();
                }}
              />
            </label>
          </div>
        </details>

        <p class={s.roiStatus}>{trackingStatusText}</p>

        {/* ROI Editor drawer */}
        {roiDrawerOpen.value && (
          <RoiEditor
            camera={{ ...camera, editing_roi: editingRoi.value }}
            onRoiAccepted={handleRoiAccepted}
            onRedraw={handleRoiRedraw}
            onCancel={handleRoiCancel}
            onReadjustAngle={handleReadjustAngle}
            message={message.value}
          />
        )}
      </section>

      {/* Metrics */}
      <dl class={s.metrics}>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>撮影枚数</dt>
          <dd class={s.metricsDd}>{st ? String(st.capture_count) : '-'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>間隔</dt>
          <dd class={s.metricsDd}>{st && st.interval_sec ? `${st.interval_sec} 秒` : '-'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>最終撮影</dt>
          <dd class={s.metricsDd}>{st ? formatCaptureTime(st.last_capture_time) : '-'}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>動き候補</dt>
          <dd class={s.metricsDd}>
            {st && st.auto_mode
              ? `${st.motion_type || 'motion'} / ${
                  st.motion_score === null
                    ? '基準作成中'
                    : `${(Number(st.motion_score || 0) * 100).toFixed(2)}%`
                }`
              : 'OFF'}
          </dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>保存容量</dt>
          <dd class={s.metricsDd}>{storage.value}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>電源状態</dt>
          <dd class={s.metricsDd}>{power.value}</dd>
        </div>
        <div class={s.metricsCell}>
          <dt class={s.metricsDt}>Build</dt>
          <dd class={s.metricsDd}>{buildDetails.value}</dd>
        </div>
      </dl>

      <p class={s.cameraMessage}>{message.value}</p>

      {/* Card actions */}
      <div class={s.cardActions}>
        <button
          class={s.btnPrimary}
          type="button"
          onClick={handleStart}
          disabled={busy.value}
        >
          撮影開始
        </button>
        <button
          class={s.btnSecondary}
          type="button"
          onClick={handleStop}
          disabled={busy.value}
        >
          停止
        </button>
        <button
          class={`${s.btnMonitor}${monitoring.value && !aiMonitoring.value ? ' ' + s.btnMonitorActive : ''}`}
          type="button"
          onClick={() => toggleMonitor(false)}
          style={{ display: 'none' }}
        >
          {monitoring.value && !aiMonitoring.value ? '閉じる' : '画角を確認'}
        </button>
        {isAiCamera && (
          <button
            class={`${s.btnAiMonitor}${aiMonitoring.value ? ' ' + s.btnAiMonitorActive : ''}`}
            type="button"
            onClick={() => toggleMonitor(true)}
          >
            {aiMonitoring.value ? 'AIモニター停止' : 'AI検出モニター'}
          </button>
        )}
        <button class={s.btnRemoveCamera} type="button" onClick={handleRemove}>
          登録を削除
        </button>
      </div>
    </article>
  );
}
