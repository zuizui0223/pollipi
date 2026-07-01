import { h } from 'preact';
import {
  approvedPolicyProfiles,
  autonomousMode,
  CAPTURE_MODE_PROFILE,
  captureMode,
  fastIntervalSec,
  intervalSec,
  type CaptureMode,
} from '../state/session';
import * as s from '../styles/components.css';

interface Props {
  onStartAll: () => Promise<void>;
  onStopAll: () => Promise<void>;
}

const MODE_HINT: Record<CaptureMode, string> = {
  plain: 'Fixed-interval stills only — no adaptation, no video.',
  motion:
    'Any motion (wind, shadow, insect alike) speeds up stills, then settles. No video. '
    + 'Adaptive needs the Pi live env flag, else it falls back to the fixed interval.',
  classified:
    'Noise is filtered; a local candidate speeds up stills (no video). '
    + 'Adaptive needs the Pi live env flag, else it falls back to the fixed interval.',
  video:
    'Like Classified, but a strong candidate also records a short video clip (a confirmation '
    + 'aid and high-info visit footage, not a confirmed visit). Needs the Pi live env flag.',
};

export function FieldControls({ onStartAll, onStopAll }: Props) {
  const mode = captureMode.value;
  const profileId = CAPTURE_MODE_PROFILE[mode];
  const profile = profileId
    ? approvedPolicyProfiles.value.find((p) => p.profile_id === profileId)
    : undefined;
  const liveProfileMissing =
    profileId != null
    && approvedPolicyProfiles.value.length > 0
    && (!profile || !profile.live_allowed);
  const adaptive = mode !== 'plain';
  const fastTooHigh = adaptive && fastIntervalSec.value >= intervalSec.value;
  return (
    <section class={s.controlPanel} aria-label="field control">
      <div>
        <p class={s.sectionTitle}>FIELD MODE</p>
        <h2>Autonomous scheduled mesh timelapse</h2>
        <label class={s.intervalInputWrap}>
          <input
            class={s.intervalInputField}
            id="interval-input"
            type="number"
            min={1}
            max={3600}
            inputMode="decimal"
            value={intervalSec.value}
            onInput={(e) => {
              intervalSec.value = Number((e.target as HTMLInputElement).value);
            }}
          />
          <span>sec normal interval</span>
        </label>
        {adaptive && (
          <label class={s.intervalInputWrap}>
            <input
              class={s.intervalInputField}
              id="fast-interval-input"
              type="number"
              min={1}
              max={3600}
              inputMode="decimal"
              value={fastIntervalSec.value}
              onInput={(e) => {
                fastIntervalSec.value = Number((e.target as HTMLInputElement).value);
              }}
            />
            <span>sec fast interval (active motion)</span>
          </label>
        )}
        {fastTooHigh && (
          <p class={s.hint} style={{ color: '#c0392b' }}>
            Fast interval must be shorter than the normal interval.
          </p>
        )}
        <p class={s.hint}>
          Shadow mode logs mesh decisions while the high-res timelapse interval stays fixed.
        </p>
      </div>

      <div class={s.fieldBasicGrid}>
        <p class={s.sectionTitle} style={{ gridColumn: '1 / -1' }}>
          Runtime
        </p>
        <label class={s.autoToggle} style={{ gridColumn: '1 / -1' }}>
          <input
            class={s.autoToggleInput}
            type="checkbox"
            checked={autonomousMode.value}
            onChange={() => {
              autonomousMode.value = !autonomousMode.value;
            }}
          />
          <span>Resume autonomously after Pi restart</span>
        </label>
        <label class={s.profileSelectWrap} style={{ gridColumn: '1 / -1' }}>
          <span>Capture mode</span>
          <select
            class={s.profileSelect}
            value={mode}
            onChange={(e) => {
              captureMode.value = (e.target as HTMLSelectElement).value as CaptureMode;
            }}
          >
            <option value="plain">① Plain timelapse (fixed interval)</option>
            <option value="motion">② Motion-reactive (faster on any motion, no video)</option>
            <option value="classified">③ Classified adaptive (faster stills, no video)</option>
            <option value="video">④ Classified + video (strong → video clip)</option>
          </select>
        </label>
        <p class={s.hint} style={{ gridColumn: '1 / -1' }}>
          {MODE_HINT[mode]}
        </p>
        {liveProfileMissing && (
          <p class={s.hint} style={{ gridColumn: '1 / -1', color: '#c0392b' }}>
            This mode's policy profile is unavailable or not live-allowed on the selected unit;
            it will fall back to the fixed interval.
          </p>
        )}
      </div>

      <div class={s.groupActions}>
        <button class={s.btnPrimary} type="button" onClick={onStartAll} disabled={fastTooHigh}>
          Start all
        </button>
        <button class={s.btnDanger} type="button" onClick={onStopAll}>
          Stop all
        </button>
      </div>
    </section>
  );
}
