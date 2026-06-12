import { h } from 'preact';
import { useSignal } from '@preact/signals';
import type { Camera } from '../api/types';
import { resolveBaseUrl, fetchDevice, createCoordinatorDevice } from '../api/client';
import { getCameras, addOrReplaceCamera, initCamera, syncDevices } from '../state/devices';
import { coordinatorBaseUrl, coordinatorOnline } from '../state/coordinator';
import * as s from '../styles/components.css';

interface Props {
  onCameraAdded: () => Promise<void>;
}

export function DeviceForm({ onCameraAdded }: Props) {
  const address = useSignal('');
  const deviceSecret = useSignal('');
  const busy = useSignal(false);
  const error = useSignal('');

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if (busy.value) return;
    const rawAddress = address.value.trim();
    const rawSecret = deviceSecret.value.trim();
    if (!rawAddress) return;
    busy.value = true;
    error.value = '';
    try {
      let baseUrl: string;
      try {
        baseUrl = resolveBaseUrl(rawAddress);
      } catch (_) {
        error.value = '観察機名を確認してください。例: pi@pollipi1';
        return;
      }
      const device = await fetchDevice(baseUrl);
      const cameras = getCameras();
      const existing = cameras.findIndex(
        (item) => item.baseUrl === baseUrl || item.device_id === device.device_id,
      );
      if (coordinatorOnline.value && coordinatorBaseUrl.value) {
        const coordinatorUrl = coordinatorBaseUrl.value.replace(/\/+$/, '');
        await createCoordinatorDevice(coordinatorUrl, {
          address: rawAddress,
          base_url: baseUrl,
          display_name: device.camera_label || undefined,
          device_secret: rawSecret || undefined,
          verify_connection: true,
        });
        await syncDevices(coordinatorUrl);
      } else {
        const old = existing >= 0 ? cameras[existing] : ({} as Partial<Camera>);
        const camera = initCamera({
          ...device,
          address: rawAddress,
          baseUrl,
          roi: old.roi || null,
          editing_roi: null,
          angle_confirmed: Boolean(old.angle_confirmed),
          roi_stale: Boolean(old.roi_stale || old.roi_pending),
          roi_pending: false,
          roi_tracking: Boolean(old.roi_tracking),
          roi_search_margin: old.roi_search_margin || 30,
          roi_tracking_min_score: old.roi_tracking_min_score || 0.45,
        });
        addOrReplaceCamera(camera);
      }
      address.value = '';
      deviceSecret.value = '';
      await onCameraAdded();
    } catch (err: unknown) {
      error.value = `観察機に接続できません: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  return (
    <section class={s.devicesPanel} aria-label="観察機の登録">
      <div>
        <p class={s.sectionTitle}>観察機</p>
        <h2>Raspberry Pi を追加</h2>
        <p class={s.hint}>
          <code>pi@pollipi1</code> のように入れると <code>http://pollipi1.local:8000</code>{' '}
          へ接続します。IP アドレス直接入力も可能です。
        </p>
      </div>
      <form class={s.deviceForm} onSubmit={handleSubmit}>
        <input
          class={s.deviceFormInput}
          type="text"
          placeholder="pi@pollipi1"
          autoCapitalize="none"
          autoComplete="off"
          required
          value={address.value}
          onInput={(e) => {
            address.value = (e.target as HTMLInputElement).value;
          }}
          disabled={busy.value}
        />
        <input
          class={s.deviceFormInput}
          type="password"
          placeholder="Device secret (coordinator only)"
          autoCapitalize="none"
          autoComplete="off"
          value={deviceSecret.value}
          onInput={(e) => {
            deviceSecret.value = (e.target as HTMLInputElement).value;
          }}
          disabled={busy.value}
        />
        <button class={s.btnPrimary} type="submit" disabled={busy.value}>
          {busy.value ? '接続中...' : '追加'}
        </button>
        {error.value && (
          <p style={{ color: 'var(--stop)', fontSize: '13px', margin: '4px 0 0', gridColumn: '1 / -1' }}>
            {error.value}
          </p>
        )}
      </form>
    </section>
  );
}
