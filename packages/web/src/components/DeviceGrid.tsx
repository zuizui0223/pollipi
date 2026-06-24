import { h } from 'preact';
import { cameras } from '../state/devices';
import { selectedGalleryCamera } from '../state/gallery';
import { DeviceCard } from './DeviceCard';
import * as s from '../styles/components.css';

interface Props {
  onRefresh: () => Promise<void>;
}

export function DeviceGrid({ onRefresh }: Props) {
  const cameraList = cameras.value;

  if (cameraList.length === 0) {
    return (
      <section class={s.cameraGrid} aria-label="Device status">
        <p class={s.cameraEmpty}>Add a device to get started.</p>
      </section>
    );
  }

  return (
    <section class={s.cameraGrid} aria-label="Device status">
      {cameraList.map((camera, index) => (
        <DeviceCard
          key={camera.coordinator_device_id ? `coordinator-${camera.coordinator_device_id}` : camera.baseUrl}
          camera={camera}
          index={index}
          onUpdated={onRefresh}
        />
      ))}
    </section>
  );
}
