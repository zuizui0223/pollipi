import { h } from 'preact';
import { useEffect } from 'preact/hooks';

import './styles/index.css';

import { postStart, postStop } from './api/client';
import type { Camera, StartPayload } from './api/types';
import { DeviceForm } from './components/DeviceForm';
import { DeviceGrid } from './components/DeviceGrid';
import { EventReview } from './components/EventReview';
import { FieldControls } from './components/FieldControls';
import { Gallery } from './components/Gallery';
import { TrainingPanel } from './components/TrainingPanel';
import { getCameras } from './state/devices';
import { selectedGalleryCamera } from './state/gallery';
import {
  autoMode,
  autonomousMode,
  detectionIntervalSec,
  getSessionMetadata,
  hybridMode,
  idleIntervalSec,
  intervalSec,
  mlAssistMode,
  motionRatio,
  motionTriggerMode,
  pixelDifference,
  syncLabel,
} from './state/session';
import { formatSyncTime } from './lib/formatting';
import { normalizeRoi } from './lib/roi';
import * as s from './styles/components.css';

function startPayloadFor(camera: Camera): StartPayload {
  const roi = normalizeRoi(camera.roi);
  const payload: StartPayload = {
    interval_sec: intervalSec.value,
    auto_mode: autoMode.value,
    motion_trigger_mode: motionTriggerMode.value,
    hybrid_mode: hybridMode.value,
    ml_assist_mode: mlAssistMode.value,
    autonomous_mode: autonomousMode.value,
    idle_interval_sec: idleIntervalSec.value,
    detection_interval_sec: detectionIntervalSec.value,
    pixel_difference: Math.round(pixelDifference.value),
    motion_ratio: motionRatio.value,
    ...getSessionMetadata(),
  };
  if (roi && !camera.roi_stale) {
    payload.roi_x = roi.roi_x;
    payload.roi_y = roi.roi_y;
    payload.roi_w = roi.roi_w;
    payload.roi_h = roi.roi_h;
    payload.roi_tracking = camera.roi_tracking;
    payload.roi_search_margin = camera.roi_search_margin;
    payload.roi_tracking_min_score = camera.roi_tracking_min_score;
  }
  return payload;
}

export function App() {
  const cameraList = getCameras();

  useEffect(() => {
    const cameras = getCameras();
    if (!selectedGalleryCamera.value && cameras.length > 0) {
      selectedGalleryCamera.value = cameras[0];
    }
  }, [cameraList.length]);

  async function refreshWorkspace() {
    const cameras = getCameras();
    if (!selectedGalleryCamera.value && cameras.length > 0) {
      selectedGalleryCamera.value = cameras[0];
    }
    syncLabel.value = `最終同期 ${formatSyncTime(new Date())}`;
  }

  async function startAll() {
    const cameras = getCameras();
    if (cameras.length === 0) return;
    const missingAngle = cameras.filter((camera) => !camera.angle_confirmed);
    if (missingAngle.length > 0) {
      alert('全機開始の前に、各観察機で画角を確認してください。');
      return;
    }
    syncLabel.value = '全機を開始しています...';
    const results = await Promise.allSettled(
      cameras.map((camera) => postStart(camera.baseUrl, startPayloadFor(camera))),
    );
    const rejected = results.filter((result) => result.status === 'rejected');
    syncLabel.value = rejected.length
      ? `${rejected.length} 台を開始できませんでした`
      : `全機開始 ${formatSyncTime(new Date())}`;
  }

  async function stopAll() {
    const cameras = getCameras();
    if (cameras.length === 0) return;
    syncLabel.value = '全機を停止しています...';
    const results = await Promise.allSettled(cameras.map((camera) => postStop(camera.baseUrl)));
    const rejected = results.filter((result) => result.status === 'rejected');
    syncLabel.value = rejected.length
      ? `${rejected.length} 台を停止できませんでした`
      : `全機停止 ${formatSyncTime(new Date())}`;
  }

  function focusEventReview() {
    document.querySelector('[aria-label="event review"]')?.scrollIntoView({ behavior: 'smooth' });
  }

  return (
    <>
      <header class={s.heroLayout}>
        <div>
          <p class={s.eyebrow}>PolliPi Field Console</p>
          <h1 class={s.h1}>Visit Monitor</h1>
          <p class={s.lead}>
            現地の Raspberry Pi カメラを登録し、画角確認、ROI 指定、撮影、画像整理、イベント確認まで同じ画面で扱います。
          </p>
        </div>
        <p class={s.sensor}>{syncLabel.value}</p>
      </header>
      <main class={s.mainLayout}>
        <FieldControls
          onStartAll={startAll}
          onStopAll={stopAll}
          onReviewEvents={focusEventReview}
        />
        <DeviceForm onCameraAdded={refreshWorkspace} />
        <DeviceGrid onRefresh={refreshWorkspace} />
        <Gallery />
        <EventReview />
        <TrainingPanel />
      </main>
      <footer class={s.footerLayout}>
        <span>PolliPi visit-monitor monorepo frontend</span>
        <span>{cameraList.length} observation unit{cameraList.length === 1 ? '' : 's'}</span>
      </footer>
    </>
  );
}

