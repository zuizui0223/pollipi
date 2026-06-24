import { signal } from '@preact/signals';
import type { PolicyProfile } from '../api/types';

// Active field controls. The old ROI / ML / motion-trigger mode state was removed
// because the active workflow is scheduled mesh timelapse with shadow-mode validation.
export const intervalSec = signal<number>(30);
export const autonomousMode = signal<boolean>(false);
export const policyProfileId = signal<string>('');
export const approvedPolicyProfiles = signal<PolicyProfile[]>([]);

export const syncLabel = signal<string>('Loading status...');
