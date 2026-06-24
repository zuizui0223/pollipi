import { h } from 'preact';
import { useSignal } from '@preact/signals';

import { fetchDevice, resolveBaseUrl } from '../api/client';
import { addOrReplaceCamera, initCamera } from '../state/devices';
import * as s from '../styles/components.css';

interface Props {
  onCameraAdded: () => Promise<void>;
}

export function DeviceForm({ onCameraAdded }: Props) {
  const address = useSignal('');
  const busy = useSignal(false);
  const error = useSignal('');

  async function handleSubmit(e: Event) {
    e.preventDefault();
    if (busy.value) return;

    const rawAddress = address.value.trim();
    if (!rawAddress) return;

    busy.value = true;
    error.value = '';
    try {
      let baseUrl: string;
      try {
        baseUrl = resolveBaseUrl(rawAddress);
      } catch (_) {
        error.value = 'Check the Pi address. Example: 192.168.8.11 or http://192.168.8.11:8000';
        return;
      }

      const device = await fetchDevice(baseUrl);
      const camera = initCamera({
        ...device,
        address: rawAddress,
        baseUrl,
      });
      addOrReplaceCamera(camera);

      address.value = '';
      await onCameraAdded();
    } catch (err: unknown) {
      error.value = `Could not connect to the Pi: ${(err as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  return (
    <section class={s.devicesPanel} aria-label="Pi registration">
      <div>
        <p class={s.sectionTitle}>Direct local connection</p>
        <h2>Add Raspberry Pi</h2>
        <p class={s.hint}>
          Add each Pi directly by its local IP address. Example: <code>192.168.8.11</code>.
          For field work, use the DHCP-reserved addresses on the field router.
        </p>
      </div>
      <form class={s.deviceForm} onSubmit={handleSubmit}>
        <input
          class={s.deviceFormInput}
          type="text"
          placeholder="192.168.8.11"
          autoCapitalize="none"
          autoComplete="off"
          required
          value={address.value}
          onInput={(e) => {
            address.value = (e.target as HTMLInputElement).value;
          }}
          disabled={busy.value}
        />
        <button class={s.btnPrimary} type="submit" disabled={busy.value}>
          {busy.value ? 'Connecting...' : 'Add Pi'}
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
