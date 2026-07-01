import { h } from 'preact';
import { useSignal } from '@preact/signals';

import type { Camera, StorageInfo } from '../api/types';
import { fetchStorage, setStorage } from '../api/client';
import { formatBytes } from '../lib/formatting';
import * as s from '../styles/components.css';

interface Props {
  camera: Camera;
  capturing: boolean;
}

function targetLabel(path: string, info: StorageInfo): string {
  const target = info.targets.find((t) => t.path === path);
  if (!target) return path;
  const free = formatBytes(target.storage_free_bytes);
  const tags = [target.is_default ? 'SD default' : target.kind, target.writable ? null : 'read-only']
    .filter(Boolean)
    .join(', ');
  return `${target.label} — ${target.path} (${free} free${tags ? `, ${tags}` : ''})`;
}

/**
 * Per-device storage selector. Each Pi has its own SD card / USB drive, so the
 * control lives on the device card. Switching is only permitted while capture is
 * stopped (the server enforces this too, returning 409), so the Apply button is
 * disabled during capture.
 */
export function StoragePanel({ camera, capturing }: Props) {
  const info = useSignal<StorageInfo | null>(null);
  const selectedPath = useSignal('');
  const manualPath = useSignal('');
  const busy = useSignal(false);
  const message = useSignal('');
  const loaded = useSignal(false);

  async function load() {
    busy.value = true;
    message.value = 'Reading storage...';
    try {
      const next = await fetchStorage(camera);
      info.value = next;
      selectedPath.value = next.current_path;
      loaded.value = true;
      message.value = '';
    } catch (error: unknown) {
      message.value = `Storage unavailable: ${(error as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  async function apply() {
    const current = info.value;
    if (!current) return;
    const chosen = manualPath.value.trim() || selectedPath.value;
    if (!chosen) return;
    // Selecting the SD default clears the persisted override (null path).
    const payload = chosen === current.default_path ? null : chosen;
    busy.value = true;
    message.value = 'Applying...';
    try {
      const next = await setStorage(camera, payload);
      info.value = next;
      selectedPath.value = next.current_path;
      manualPath.value = '';
      message.value = `Saving to ${next.current_path}`;
    } catch (error: unknown) {
      message.value = `Change failed: ${(error as Error).message}`;
    } finally {
      busy.value = false;
    }
  }

  const current = info.value;

  return (
    <details
      class={s.debugDetails}
      onToggle={(event) => {
        if ((event.currentTarget as HTMLDetailsElement).open && !loaded.value) void load();
      }}
    >
      <summary class={s.debugDetailsSummary}>Storage / USB</summary>

      {current ? (
        <div>
          <p class={s.debugStatus}>current: {current.current_path}</p>
          <p class={s.debugStatus}>
            default (SD): {current.default_path}
            {current.current_path === current.default_path ? ' (in use)' : ''}
          </p>

          <select
            class={s.profileSelect}
            value={selectedPath.value}
            disabled={busy.value || capturing}
            onChange={(event) => {
              selectedPath.value = (event.currentTarget as HTMLSelectElement).value;
              manualPath.value = '';
            }}
          >
            {current.targets.map((target) => (
              <option value={target.path} key={target.path}>
                {targetLabel(target.path, current)}
              </option>
            ))}
          </select>

          <input
            class={s.deviceFormInput}
            type="text"
            placeholder="or type a path, e.g. /media/pi/USB128/images"
            value={manualPath.value}
            disabled={busy.value || capturing}
            onInput={(event) => {
              manualPath.value = (event.currentTarget as HTMLInputElement).value;
            }}
          />

          <div class={s.cardActions}>
            <button
              class={s.btnSecondary}
              type="button"
              onClick={() => void apply()}
              disabled={busy.value || capturing}
            >
              {busy.value ? 'Working...' : 'Apply storage'}
            </button>
            <button
              class={s.btnSecondary}
              type="button"
              onClick={() => void load()}
              disabled={busy.value}
            >
              Refresh
            </button>
          </div>

          {capturing && (
            <p class={s.debugStatus}>Stop capture to change the storage location.</p>
          )}
        </div>
      ) : (
        <p class={s.debugStatus}>{message.value || 'Open to load storage options.'}</p>
      )}

      {current && message.value && <p class={s.debugStatus}>{message.value}</p>}
    </details>
  );
}
