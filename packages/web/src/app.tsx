import { h } from 'preact';
import { useEffect } from 'preact/hooks';

import './styles/index.css';

import { fetchPolicyProfiles, postStart, postStop } from './api/client';
import type { Camera, StartPayload } from './api/types';
import { DeviceForm } from './components/DeviceForm';
import { DeviceGrid } from './components/DeviceGrid';
import { FieldControls } from './components/FieldControls';
import { Gallery } from './components/Gallery';
import { getCameras } from './state/devices';
import { selectedGalleryCamera } from './state/gallery';
import {
  autonomousMode,
  approvedPolicyProfiles,
  intervalSec,
  policyProfileId,
  syncLabel,
} from './state/session';
import { formatSyncTime } from './lib/formatting';
import * as s from './styles/components.css';

function startPayloadFor(_camera: Camera): StartPayload {
  const payload: StartPayload = {
    interval_sec: intervalSec.value,
    autonomous_mode: autonomousMode.value,
    adaptive_timelapse_mode: false,
    mesh_shadow_mode: true,
  };
  if (policyProfileId.value) payload.policy_profile_id = policyProfileId.value;
  return payload;
}

export function App() {
  const cameraList = getCameras();

  useEffect(() => {
    const cameras = getCameras();
    if (!selectedGalleryCamera.value && cameras.length > 0) {
      selectedGalleryCamera.value = cameras[0];
    }
    if (cameras.length > 0 && approvedPolicyProfiles.value.length === 0) {
      void loadPolicyProfiles(cameras[0]);
    }
  }, [cameraList.length]);

  async function loadPolicyProfiles(camera: Camera) {
    try {
      const response = await fetchPolicyProfiles(camera);
      approvedPolicyProfiles.value = response.profiles;
      if (!policyProfileId.value) {
        policyProfileId.value = response.default_profile_id;
      }
    } catch (error: unknown) {
      syncLabel.value = `policy profiles unavailable: ${(error as Error).message}`;
    }
  }

  async function refreshWorkspace() {
    const cameras = getCameras();
    if (!selectedGalleryCamera.value && cameras.length > 0) {
      selectedGalleryCamera.value = cameras[0];
    }
    if (cameras.length > 0) {
      await loadPolicyProfiles(cameras[0]);
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
          <h1 class={s.h1}>Field Console</h1>
          <p class={s.lead}>
            Direct local control for Raspberry Pi timelapse units on the same Wi-Fi network.
          </p>
          <p class={s.hint}>
            Add each Pi by its IP address below. A coordinator or internet connection is not required for normal field use.
          </p>
        </div>
        <p class={s.sensor}>{syncLabel.value}</p>
      </header>
      <main class={s.mainLayout}>
        <FieldControls onStartAll={startAll} onStopAll={stopAll} />
        <DeviceForm onCameraAdded={refreshWorkspace} />
        <DeviceGrid onRefresh={refreshWorkspace} />
        <Gallery />
      </main>
      <footer class={s.footerLayout}>
        <span>PolliPi shadow-mode field runtime</span>
        <span>{cameraList.length} observation unit{cameraList.length === 1 ? '' : 's'}</span>
      </footer>
    </>
  );
}
