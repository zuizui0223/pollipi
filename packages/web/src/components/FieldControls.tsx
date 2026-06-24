import { h } from 'preact';
import {
  adaptiveMaxIntervalSec,
  adaptiveMinIntervalSec,
  adaptiveTimelapseMode,
  autonomousMode,
  intervalSec,
} from '../state/session';
import * as s from '../styles/components.css';

interface Props {
  onStartAll: () => Promise<void>;
  onStopAll: () => Promise<void>;
}

export function FieldControls({ onStartAll, onStopAll }: Props) {
  const minInterval = adaptiveMinIntervalSec.value;
  const maxInterval = adaptiveMaxIntervalSec.value;
  const intervalRangeInvalid =
    Number.isFinite(minInterval) && Number.isFinite(maxInterval) && maxInterval < minInterval;

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
            inputMode="decimal"
            value={intervalSec.value}
            onInput={(e) => {
              intervalSec.value = Number((e.target as HTMLInputElement).value);
            }}
          />
          <span>sec baseline</span>
        </label>
        <p class={s.hint}>
          Shadow mode logs mesh decisions while preserving the scheduled interval. Enable adaptive only after field validation.
        </p>
      </div>

      <div class={s.fieldBasicGrid}>
        <p class={s.sectionTitle} style={{ gridColumn: '1 / -1' }}>
          Adaptive interval bounds
        </p>
        <label class={s.advancedGridLabel}>
          min interval (sec)
          <input
            type="number"
            min={1}
            value={adaptiveMinIntervalSec.value}
            onInput={(e) => {
              adaptiveMinIntervalSec.value = Number((e.target as HTMLInputElement).value);
            }}
          />
        </label>
        <label class={s.advancedGridLabel}>
          max interval (sec)
          <input
            type="number"
            min={1}
            value={adaptiveMaxIntervalSec.value}
            onInput={(e) => {
              adaptiveMaxIntervalSec.value = Number((e.target as HTMLInputElement).value);
            }}
          />
        </label>
        {intervalRangeInvalid && (
          <p class={s.hint} style={{ gridColumn: '1 / -1', color: 'var(--stop)' }}>
            Max interval must be greater than or equal to min interval.
          </p>
        )}
        <label class={s.autoToggle} style={{ gridColumn: '1 / -1' }}>
          <input
            class={s.autoToggleInput}
            type="checkbox"
            checked={adaptiveTimelapseMode.value}
            onChange={() => {
              adaptiveTimelapseMode.value = !adaptiveTimelapseMode.value;
            }}
          />
          <span>Enable adaptive interval</span>
        </label>
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
      </div>

      <div class={s.groupActions}>
        <button class={s.btnPrimary} type="button" onClick={onStartAll}>
          Start all
        </button>
        <button class={s.btnDanger} type="button" onClick={onStopAll}>
          Stop all
        </button>
      </div>
    </section>
  );
}
