import { h } from 'preact';
import { useSignal } from '@preact/signals';
import { resolveBaseUrl, fetchDevice, createCoordinatorDevice } from '../api/client';
import { addOrReplaceCamera, initCamera, syncDevices } from '../state/devices';
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
        error.value = 'Check the device address. Example: pi@pollipi1';
        return;
      }
      const device = await fetchDevice(baseUrl);
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
        const camera = initCamera({
          ...device,
          address: rawAddress,
          baseUrl,
        });
        addOrReplaceCamera(camera);
      }
      address.value = '';
      deviceSecret.value = '';
      await onCameraAdded();
    } catch (err: unknown) {
      error.value = `Could not connect to the device: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  return (
    <section class={s.devicesPanel} aria-label="Device registration">
      <div>
        <p class={s.sectionTitle}>Devices</p>
        <h2>Add Raspberry Pi</h2>
        <p class={s.hint}>
          Enter <code>pi@pollipi1</code> to connect to <code>http://pollipi1.local:8000</code>.
          Direct IP addresses are also supported.
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
          {busy.value ? 'Connecting...' : 'Add'}
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
