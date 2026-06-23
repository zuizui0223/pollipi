import { signal } from '@preact/signals';

// Active field controls. The old ROI / ML / motion-trigger mode state was removed
// because the active workflow is scheduled mesh timelapse with shadow-mode validation.
export const intervalSec = signal<number>(10);
export const autonomousMode = signal<boolean>(false);
export const adaptiveTimelapseMode = signal<boolean>(false);
export const adaptiveMinIntervalSec = signal<number>(15);
export const adaptiveMaxIntervalSec = signal<number>(3600);
export const adaptiveWindowSec = signal<number>(300);

// Optional session metadata retained with scheduled timelapse records.
export const siteId = signal<string>('');
export const flowerId = signal<string>('');
export const plantSpecies = signal<string>('');
export const observer = signal<string>('');
export const notes = signal<string>('');
export const comparisonSessionId = signal<string>('');
export const cameraRole = signal<string>('');
export const methodMode = signal<string>('');

export const syncLabel = signal<string>('状態を読み込み中...');

export function getSessionMetadata(): Record<string, string | undefined> {
  return {
    site_id: siteId.value || undefined,
    flower_id: flowerId.value || undefined,
    plant_species: plantSpecies.value || undefined,
    observer: observer.value || undefined,
    notes: notes.value || undefined,
    comparison_session_id: comparisonSessionId.value || undefined,
    camera_role: cameraRole.value || undefined,
    method_mode: methodMode.value || undefined,
  };
}
