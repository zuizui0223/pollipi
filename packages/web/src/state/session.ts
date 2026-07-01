import { signal } from '@preact/signals';
import type { PolicyProfile, StartPayload } from '../api/types';

// Active field controls. The old ROI / ML / motion-trigger mode state was removed
// because the active workflow is scheduled mesh timelapse with shadow-mode validation.
export const intervalSec = signal<number>(30); // normal (baseline / LOW) interval
export const fastIntervalSec = signal<number>(10); // high-frequency (MID) interval; must be < normal
export const autonomousMode = signal<boolean>(false);
export const policyProfileId = signal<string>('');
export const approvedPolicyProfiles = signal<PolicyProfile[]>([]);

// The four user-facing capture modes. Each maps to a policy profile (or none) and
// whether to request live adaptive timing. Live still also needs the Pi env flag.
// Methodology: ①②③ are STILLS-only so they compare on the same output (capture
// timing vs a fixed still budget); ④ adds video as a separate hybrid.
//   (1) plain      : fixed-interval stills, no adaptation.
//   (2) motion     : any motion -> faster stills (no classification, no video).
//   (3) classified : noise filtered; local candidate -> faster stills (no video).
//   (4) video      : like ③, but a strong candidate also records a short video clip.
export type CaptureMode = 'plain' | 'motion' | 'classified' | 'video';
export const captureMode = signal<CaptureMode>('plain');
export const CAPTURE_MODE_PROFILE: Record<CaptureMode, string | null> = {
  plain: null,
  motion: 'three_stage_motion_canary_v1',
  classified: 'three_stage_canary_v1',
  video: 'three_stage_video_canary_v1',
};

/** Start-payload fields for the selected capture mode (profile + live request +
 * the user's high-frequency interval). Plain mode sends none of these. */
export function captureModeStartFields(): Partial<StartPayload> {
  const profile = CAPTURE_MODE_PROFILE[captureMode.value];
  if (!profile) return {};
  return {
    policy_profile_id: profile,
    live_adaptive_requested: true,
    fast_interval_sec: fastIntervalSec.value,
  };
}

export const syncLabel = signal<string>('Loading status...');
