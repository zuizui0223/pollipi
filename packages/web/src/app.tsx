import { h } from 'preact';
import { useEffect } from 'preact/hooks';

import './styles/index.css';

import { postStart, postStop } from './api/client';
import type { Camera, StartPayload } from './api/types';
import { CoordinatorPanel } from './components/CoordinatorPanel';
import { DeviceForm } from './components/DeviceForm';
import { DeviceGrid } from './components/DeviceGrid';
import { FieldControls } from './components/FieldControls';
import { getCameras } from './state/devices';
import { selectedGalleryCamera } from './state/gallery';
import {
  adaptiveMaxIntervalSec,
  adaptiveMinIntervalSec,
  adaptiveTimelapseMode,
  autonomousMode,
  getSessionMetadata,
  intervalSec,
  syncLabel,
} from './state/session';
import { formatSyncTime } from './lib/formatting';
import * as s from './styles/components.css';

function startPayloadFor(_camera: Camera): StartPayload {
  return {
    interval_sec: intervalSec.value,
    auto_mode: false,
    motion_trigger_mode: false,
    hybrid_mode: false,
    ml_assist_mode: false,
    autonomous_mode: autonomousMode.value,
    adaptive_timelapse_mode: adaptiveTimelapseMode.value,
    adaptive_min_interval_sec: adaptiveMinIntervalSec.value,
    adaptive_max_interval_sec: adaptiveMaxIntervalSec.value,
    mesh_shadow_mode: !adaptiveTimelapseMode.value,
    idle_interval_sec: intervalSec.value,
    detection_interval_sec: intervalSec.value,
    pixel_difference: 30,
    motion_ratio: 0.01,
    ...getSessionMetadata(),
  };
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
    syncLabel.value = `last sync ${formatSyncTime(new Date())}`;
  }

  async function startAll() {
    const cameras = getCameras();
    if (cameras.length === 0) return;
    syncLabel.value = 'starting all units...';
    const results = await Promise.allSettled(
      cameras.map((camera) => postStart(camera, startPayloadFor(camera))),
    );
    const rejected = results.filter((result) => result.status === 'rejected');
    syncLabel.value = rejected.length
      ? `${rejected.length} unit(s) failed to start`
      : `all units started ${formatSyncTime(new Date())}`;
  }

  async function stopAll() {
    const cameras = getCameras();
    if (cameras.length === 0) return;
    syncLabel.value = 'stopping all units...';
    const results = await Promise.allSettled(cameras.map((camera) => postStop(camera)));
    const rejected = results.filter((result) => result.status === 'rejected');
    syncLabel.value = rejected.length
      ? `${rejected.length} unit(s) failed to stop`
      : `all units stopped ${formatSyncTime(new Date())}`;
  }

  return (
    <>
      <header class={s.heroLayout}>
        <div>
          <p class={s.eyebrow}>PolliPi Field Console</p>
          <h1 class={s.h1}>Visit Monitor</h1>
          <p class={s.lead}>
            Status-first control for autonomous Raspberry Pi timelapse units on the field LAN.
          </p>
        </div>
        <p class={s.sensor}>{syncLabel.value}</p>
      </header>
      <main class={s.mainLayout}>
        <FieldControls onStartAll={startAll} onStopAll={stopAll} />
        <CoordinatorPanel />
        <DeviceForm onCameraAdded={refreshWorkspace} />
        <DeviceGrid onRefresh={refreshWorkspace} />
      </main>
      <footer class={s.footerLayout}>
        <span>PolliPi active mesh runtime</span>
        <span>{cameraList.length} observation unit{cameraList.length === 1 ? '' : 's'}</span>
      </footer>
    </>
  );
}
