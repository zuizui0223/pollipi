import { h } from 'preact';
import { useSignal } from '@preact/signals';

import {
  clearCoordinatorTokens,
  coordinatorLogin,
  coordinatorMe,
  coordinatorRegister,
  createCoordinatorDevice,
  fetchCoordinatorDevices,
  saveCoordinatorUrl,
} from '../api/client';
import type { Camera, CoordinatorDevice } from '../api/types';
import {
  coordinatorBaseUrl,
  coordinatorMessage,
  coordinatorOnline,
  coordinatorUser,
} from '../state/coordinator';
import { getCameras, initCamera, setCameras } from '../state/devices';
import { selectedGalleryCamera } from '../state/gallery';
import * as s from '../styles/components.css';

function coordinatorDeviceToCamera(baseUrl: string, device: CoordinatorDevice): Camera {
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
  });
}

async function syncDevices(baseUrl: string): Promise<number> {
  const devices = await fetchCoordinatorDevices(baseUrl);
  const coordinatorCameras = devices.map((device) => coordinatorDeviceToCamera(baseUrl, device));
  const localCameras = getCameras().filter((camera) => !camera.managed_by_coordinator);
  setCameras([...localCameras, ...coordinatorCameras]);
  if (!selectedGalleryCamera.value && coordinatorCameras[0]) {
    selectedGalleryCamera.value = coordinatorCameras[0];
  }
  return coordinatorCameras.length;
}

export function CoordinatorPanel() {
  const busy = useSignal(false);
  const email = useSignal('');
  const username = useSignal('');
  const password = useSignal('');
  const piAddress = useSignal('');
  const piBaseUrl = useSignal('');
  const piName = useSignal('');
  const verifyConnection = useSignal(true);

  async function handleLogin(e: Event) {
    e.preventDefault();
    busy.value = true;
    coordinatorMessage.value = 'Connecting to coordinator...';
    try {
      const baseUrl = coordinatorBaseUrl.value.replace(/\/+$/, '');
      await coordinatorLogin(baseUrl, email.value, password.value);
      coordinatorUser.value = await coordinatorMe(baseUrl);
      coordinatorOnline.value = true;
      const count = await syncDevices(baseUrl);
      coordinatorMessage.value = `Coordinator connected. Synced ${count} device${count === 1 ? '' : 's'}.`;
    } catch (err: unknown) {
      coordinatorOnline.value = false;
      coordinatorMessage.value = `Coordinator login failed: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleRegister() {
    busy.value = true;
    coordinatorMessage.value = 'Creating coordinator user...';
    try {
      const baseUrl = coordinatorBaseUrl.value.replace(/\/+$/, '');
      await coordinatorRegister(baseUrl, email.value, username.value, password.value);
      await coordinatorLogin(baseUrl, email.value, password.value);
      coordinatorUser.value = await coordinatorMe(baseUrl);
      coordinatorOnline.value = true;
      coordinatorMessage.value = 'Coordinator user created and signed in.';
    } catch (err: unknown) {
      coordinatorMessage.value = `Coordinator registration failed: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleSync() {
    busy.value = true;
    try {
      const baseUrl = coordinatorBaseUrl.value.replace(/\/+$/, '');
      saveCoordinatorUrl(baseUrl);
      coordinatorUser.value = await coordinatorMe(baseUrl);
      coordinatorOnline.value = true;
      const count = await syncDevices(baseUrl);
      coordinatorMessage.value = `Synced ${count} coordinator device${count === 1 ? '' : 's'}.`;
    } catch (err: unknown) {
      coordinatorMessage.value = `Coordinator sync failed: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function handleAddDevice(e: Event) {
    e.preventDefault();
    busy.value = true;
    try {
      const baseUrl = coordinatorBaseUrl.value.replace(/\/+$/, '');
      await createCoordinatorDevice(baseUrl, {
        address: piAddress.value,
        base_url: piBaseUrl.value,
        display_name: piName.value || undefined,
        verify_connection: verifyConnection.value,
      });
      piAddress.value = '';
      piBaseUrl.value = '';
      piName.value = '';
      const count = await syncDevices(baseUrl);
      coordinatorMessage.value = `Device registered. Synced ${count} coordinator device${count === 1 ? '' : 's'}.`;
    } catch (err: unknown) {
      coordinatorMessage.value = `Device registration failed: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  function handleLogout() {
    clearCoordinatorTokens();
    coordinatorUser.value = null;
    coordinatorOnline.value = false;
    coordinatorMessage.value = 'Coordinator token cleared.';
  }

  return (
    <section class={s.devicesPanel} aria-label="Coordinator">
      <div>
        <p class={s.sectionTitle}>Coordinator</p>
        <h2>中央サーバー</h2>
        <p class={s.hint}>{coordinatorMessage.value}</p>
        {coordinatorUser.value && (
          <p class={s.hint}>
            {coordinatorUser.value.username} / {coordinatorUser.value.email}
          </p>
        )}
      </div>
      <div style={{ display: 'grid', gap: '12px', minWidth: 'min(520px, 100%)' }}>
        <form class={s.deviceForm} onSubmit={handleLogin}>
          <input
            class={s.deviceFormInput}
            type="url"
            value={coordinatorBaseUrl.value}
            onInput={(e) => {
              coordinatorBaseUrl.value = (e.target as HTMLInputElement).value;
            }}
            placeholder="http://coordinator.local:8001"
          />
          <input
            type="email"
            value={email.value}
            onInput={(e) => {
              email.value = (e.target as HTMLInputElement).value;
            }}
            placeholder="email"
          />
          <input
            type="text"
            value={username.value}
            onInput={(e) => {
              username.value = (e.target as HTMLInputElement).value;
            }}
            placeholder="username for register"
          />
          <input
            type="password"
            value={password.value}
            onInput={(e) => {
              password.value = (e.target as HTMLInputElement).value;
            }}
            placeholder="password"
          />
          <button class={s.btnPrimary} type="submit" disabled={busy.value}>
            Login
          </button>
          <button class={s.btnSecondary} type="button" onClick={handleRegister} disabled={busy.value}>
            Register
          </button>
          <button class={s.btnGhost} type="button" onClick={handleSync} disabled={busy.value}>
            Sync
          </button>
          <button class={s.btnRemoveCamera} type="button" onClick={handleLogout}>
            Logout
          </button>
        </form>
        {coordinatorOnline.value && (
          <form class={s.deviceForm} onSubmit={handleAddDevice}>
            <input
              class={s.deviceFormInput}
              type="text"
              value={piAddress.value}
              onInput={(e) => {
                piAddress.value = (e.target as HTMLInputElement).value;
              }}
              placeholder="pi@pollipi1"
            />
            <input
              class={s.deviceFormInput}
              type="url"
              required
              value={piBaseUrl.value}
              onInput={(e) => {
                piBaseUrl.value = (e.target as HTMLInputElement).value;
              }}
              placeholder="http://pollipi1.local:8000"
            />
            <input
              type="text"
              value={piName.value}
              onInput={(e) => {
                piName.value = (e.target as HTMLInputElement).value;
              }}
              placeholder="display name"
            />
            <label class={s.autoToggle}>
              <input
                class={s.autoToggleInput}
                type="checkbox"
                checked={verifyConnection.value}
                onChange={(e) => {
                  verifyConnection.value = (e.target as HTMLInputElement).checked;
                }}
              />
              <span>verify</span>
            </label>
            <button class={s.btnPrimary} type="submit" disabled={busy.value}>
              Add via Coordinator
            </button>
          </form>
        )}
      </div>
    </section>
  );
}

