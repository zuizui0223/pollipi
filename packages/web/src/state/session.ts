import { signal } from '@preact/signals';
import type { PolicyProfile, StartPayload } from '../api/types';

// Active field controls. The old ROI / ML / motion-trigger mode state was removed
// because the active workflow is scheduled mesh timelapse with shadow-mode validation.
export const intervalSec = signal<number>(30);
export const autonomousMode = signal<boolean>(false);
export const policyProfileId = signal<string>('');
export const approvedPolicyProfiles = signal<PolicyProfile[]>([]);

// The three user-facing capture modes. Each maps to a policy profile (or none) and
// whether to request live adaptive timing. Live still also needs the Pi env flag.
//   (1) plain      : fixed-interval stills, no adaptation.
//   (2) motion     : any motion -> faster stills (no classification, no video).
//   (3) classified : noise filtered; ambiguous -> faster stills; strong -> video clip.
export type CaptureMode = 'plain' | 'motion' | 'classified';
export const captureMode = signal<CaptureMode>('plain');
export const CAPTURE_MODE_PROFILE: Record<CaptureMode, string | null> = {
  plain: null,
  motion: 'three_stage_motion_canary_v1',
  classified: 'three_stage_video_canary_v1',
};

/** Start-payload fields for the selected capture mode (profile + live request). */
export function captureModeStartFields(): Partial<StartPayload> {
  const profile = CAPTURE_MODE_PROFILE[captureMode.value];
  return profile ? { policy_profile_id: profile, live_adaptive_requested: true } : {};
}

export const syncLabel = signal<string>('Loading status...');
