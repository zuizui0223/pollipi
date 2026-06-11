import { signal, computed } from '@preact/signals';

export const intervalSec = signal<number>(10);
export const autoMode = signal<boolean>(false);
export const motionTriggerMode = signal<boolean>(false);
export const hybridMode = signal<boolean>(false);
export const autonomousMode = signal<boolean>(false);
export const mlAssistMode = signal<boolean>(false);
export const adaptiveTimelapseMode = signal<boolean>(false);
export const adaptiveMinIntervalSec = signal<number>(15);
export const adaptiveWindowSec = signal<number>(300);
export const idleIntervalSec = signal<number>(60);
export const detectionIntervalSec = signal<number>(3);
export const pixelDifference = signal<number>(30);
export const motionRatio = signal<number>(0.01);

export const siteId = signal<string>('');
export const flowerId = signal<string>('');
export const plantSpecies = signal<string>('');
export const observer = signal<string>('');
export const notes = signal<string>('');
export const comparisonSessionId = signal<string>('');
export const cameraRole = signal<string>('');
export const methodMode = signal<string>('');

export const syncLabel = signal<string>('状態を読み込み中...');

export const anyAutoMode = computed(
  () => autoMode.value || motionTriggerMode.value || hybridMode.value,
);

export function selectExclusiveMode(selected: 'auto' | 'motion' | 'hybrid' | 'none'): void {
  if (selected === 'auto') {
    if (!autoMode.value) {
      motionTriggerMode.value = false;
      hybridMode.value = false;
      autoMode.value = true;
    } else {
      autoMode.value = false;
    }
  } else if (selected === 'motion') {
    if (!motionTriggerMode.value) {
      autoMode.value = false;
      hybridMode.value = false;
      motionTriggerMode.value = true;
    } else {
      motionTriggerMode.value = false;
    }
  } else if (selected === 'hybrid') {
    if (!hybridMode.value) {
      autoMode.value = false;
      motionTriggerMode.value = false;
      hybridMode.value = true;
    } else {
      hybridMode.value = false;
    }
  } else {
    autoMode.value = false;
    motionTriggerMode.value = false;
    hybridMode.value = false;
  }
}

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
