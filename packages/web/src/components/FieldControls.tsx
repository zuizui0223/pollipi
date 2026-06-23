import { h } from 'preact';
import {
  adaptiveMaxIntervalSec,
  adaptiveMinIntervalSec,
  adaptiveTimelapseMode,
  autonomousMode,
  cameraRole,
  comparisonSessionId,
  flowerId,
  intervalSec,
  notes,
  observer,
  plantSpecies,
  siteId,
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
          Shadow mode logs mesh decisions while preserving the scheduled interval. Enable adaptive only after field validation.
        </p>
      </div>

      <div class={s.fieldBasicGrid}>
        <p class={s.sectionTitle} style={{ gridColumn: '1 / -1' }}>
          Active policy
        </p>
        <label class={s.advancedGridLabel}>
          min interval
          <input
            type="number"
            min={1}
            max={3600}
            value={adaptiveMinIntervalSec.value}
            onInput={(e) => {
              adaptiveMinIntervalSec.value = Number((e.target as HTMLInputElement).value || 15);
            }}
          />
        </label>
        <label class={s.advancedGridLabel}>
          max interval
          <input
            type="number"
            min={1}
            max={3600}
            value={adaptiveMaxIntervalSec.value}
            onInput={(e) => {
              adaptiveMaxIntervalSec.value = Number((e.target as HTMLInputElement).value || 3600);
            }}
          />
        </label>
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

        <details class={s.advancedFields} style={{ gridColumn: '1 / -1' }}>
          <summary class={s.advancedFieldsSummary}>Field metadata</summary>
          <div class={s.advancedGrid}>
            {[
              ['site_id', siteId],
              ['flower_id', flowerId],
              ['plant_species', plantSpecies],
              ['observer', observer],
              ['comparison_session_id', comparisonSessionId],
              ['camera_role', cameraRole],
              ['notes', notes],
            ].map(([label, sig]) => (
              <label class={s.advancedGridLabel} key={label as string}>
                {label as string}
                <input
                  type="text"
                  value={(sig as any).value}
                  onInput={(e) => {
                    (sig as any).value = (e.target as HTMLInputElement).value;
                  }}
                />
              </label>
            ))}
          </div>
        </details>
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
