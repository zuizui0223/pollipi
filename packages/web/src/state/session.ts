import { signal } from '@preact/signals';

// Active field controls. The old ROI / ML / motion-trigger mode state was removed
// because the active workflow is scheduled mesh timelapse with shadow-mode validation.
export const intervalSec = signal<number>(30);
export const autonomousMode = signal<boolean>(false);
export const policyProfileId = signal<string>('three_stage_default_v1');

export const approvedPolicyProfiles = [
  {
    id: 'three_stage_default_v1',
    label: 'three-stage default',
    simulationRunId: 'issue27-three-stage-baseline',
    kind: 'three_stage',
  },
  {
    id: 'three_stage_sensitive_v1',
    label: 'three-stage sensitive',
    simulationRunId: 'issue27-three-stage-sensitive',
    kind: 'three_stage',
  },
];

export const syncLabel = signal<string>('Loading status...');
