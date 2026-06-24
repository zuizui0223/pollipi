import { h } from 'preact';
import {
  autonomousMode,
  intervalSec,
} from '../state/session';
import * as s from '../styles/components.css';

interface Props {
  onStartAll: () => Promise<void>;
  onStopAll: () => Promise<void>;
}

export function FieldControls({ onStartAll, onStopAll }: Props) {
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
          <span>sec baseline</span>
        </label>
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
