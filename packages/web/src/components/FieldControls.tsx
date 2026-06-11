import { h } from 'preact';
import {
  intervalSec,
  autoMode,
  motionTriggerMode,
  hybridMode,
  autonomousMode,
  mlAssistMode,
  idleIntervalSec,
  detectionIntervalSec,
  pixelDifference,
  motionRatio,
  siteId,
  flowerId,
  plantSpecies,
  observer,
  notes,
  comparisonSessionId,
  cameraRole,
  methodMode,
  selectExclusiveMode,
  anyAutoMode,
  adaptiveTimelapseMode,
  adaptiveMinIntervalSec,
  adaptiveWindowSec,
} from '../state/session';
import * as s from '../styles/components.css';

interface Props {
  onStartAll: () => Promise<void>;
  onStopAll: () => Promise<void>;
  onReviewEvents: () => void;
}

export function FieldControls({ onStartAll, onStopAll, onReviewEvents }: Props) {
  const isAuto = anyAutoMode.value;
  const isMotion = motionTriggerMode.value;
  const isHybrid = hybridMode.value;

  const detectionLabel = isMotion || isHybrid ? '候補チェック' : '動き候補あり';
  const autoHelp = isHybrid
    ? '研究用: 定間隔写真を必ず保存し、動き候補があれば追加撮影します。'
    : isMotion
    ? '低解像度で動きを見て、候補が出た時だけ保存します。'
    : '背景差分で候補がない時は間隔を長くし、候補があれば短くします。';

  return (
    <section class={s.controlPanel} aria-label="撮影設定">
      {/* Column 1: Basic interval + mode */}
      <div>
        <p class={s.sectionTitle}>FIELD MODE</p>
        <h2>現地で使う基本設定</h2>
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
          <span>秒</span>
        </label>
        <p class={s.hint}>
          まず「画角を確認」でカメラを合わせ、「この画角でOK」後に「ROIを指定」で観察したい範囲を指定します。
        </p>
        <label class={s.autoToggle} style={{ marginTop: '10px' }}>
          <input
            class={s.autoToggleInput}
            type="checkbox"
            checked={autoMode.value}
            onChange={() => selectExclusiveMode('auto')}
          />
          <span>背景差分で撮影間隔を自動調整</span>
        </label>
      </div>

      {/* Column 2: Session metadata + advanced */}
      <div class={s.fieldBasicGrid}>
        <p class={s.sectionTitle} style={{ gridColumn: '1 / -1' }}>
          調査メタデータ
        </p>
        <label class={s.advancedGridLabel}>
          site_id
          <input
            type="text"
            placeholder="site_A"
            autoCapitalize="none"
            value={siteId.value}
            onInput={(e) => {
              siteId.value = (e.target as HTMLInputElement).value;
            }}
          />
        </label>
        <label class={s.advancedGridLabel}>
          flower_id
          <input
            type="text"
            placeholder="plant_03_flower_01"
            autoCapitalize="none"
            value={flowerId.value}
            onInput={(e) => {
              flowerId.value = (e.target as HTMLInputElement).value;
            }}
          />
        </label>
        <label class={s.advancedGridLabel}>
          plant_species
          <input
            type="text"
            placeholder="Cirsium sp."
            autoCapitalize="none"
            value={plantSpecies.value}
            onInput={(e) => {
              plantSpecies.value = (e.target as HTMLInputElement).value;
            }}
          />
        </label>
        <label class={s.advancedGridLabel}>
          method_mode
          <input
            type="text"
            placeholder="event_based_timelapse"
            autoCapitalize="none"
            value={methodMode.value}
            onInput={(e) => {
              methodMode.value = (e.target as HTMLInputElement).value;
            }}
          />
        </label>

        <details class={s.advancedFields} style={{ gridColumn: '1 / -1' }}>
          <summary class={s.advancedFieldsSummary}>Advanced settings</summary>
          <div class={s.advancedGrid}>
            <label class={s.advancedGridLabel}>
              observer
              <input
                type="text"
                placeholder="observer"
                value={observer.value}
                onInput={(e) => {
                  observer.value = (e.target as HTMLInputElement).value;
                }}
              />
            </label>
            <label class={s.advancedGridLabel}>
              comparison_session_id
              <input
                type="text"
                placeholder="2026-plotA-pair01"
                autoCapitalize="none"
                value={comparisonSessionId.value}
                onInput={(e) => {
                  comparisonSessionId.value = (e.target as HTMLInputElement).value;
                }}
              />
            </label>
            <label class={s.advancedGridLabel}>
              camera_role
              <input
                type="text"
                placeholder="module3_reference / ai_camera_test"
                autoCapitalize="none"
                value={cameraRole.value}
                onInput={(e) => {
                  cameraRole.value = (e.target as HTMLInputElement).value;
                }}
              />
            </label>
            <label class={s.advancedGridLabel}>
              pixel_difference
              <input
                type="number"
                min={1}
                max={255}
                inputMode="numeric"
                value={pixelDifference.value}
                onInput={(e) => {
                  pixelDifference.value = Number((e.target as HTMLInputElement).value);
                }}
              />
            </label>
            <label class={s.advancedGridLabel}>
              motion_ratio
              <input
                type="number"
                min={0.0001}
                max={1}
                step={0.0001}
                inputMode="decimal"
                value={motionRatio.value}
                onInput={(e) => {
                  motionRatio.value = Number((e.target as HTMLInputElement).value);
                }}
              />
            </label>
            {/* idle_interval - hidden when motionTrigger or hybrid mode */}
            {!isMotion && !isHybrid && (
              <label class={s.advancedGridLabel}>
                idle_interval_sec
                <span style={{ display: 'flex', gap: '6px', alignItems: 'baseline' }}>
                  <input
                    type="number"
                    min={1}
                    max={3600}
                    value={idleIntervalSec.value}
                    onInput={(e) => {
                      idleIntervalSec.value = Number((e.target as HTMLInputElement).value);
                    }}
                  />
                  秒
                </span>
              </label>
            )}
            <label class={s.advancedGridLabel}>
              <span>{detectionLabel} (detection_interval_sec)</span>
              <input
                type="number"
                min={1}
                max={3600}
                value={detectionIntervalSec.value}
                onInput={(e) => {
                  detectionIntervalSec.value = Number((e.target as HTMLInputElement).value);
                }}
              />
            </label>
            <label class={s.advancedGridLabel}>
              notes
              <input
                type="text"
                placeholder="weather, block, treatment"
                value={notes.value}
                onInput={(e) => {
                  notes.value = (e.target as HTMLInputElement).value;
                }}
              />
            </label>

            {/* Advanced modes */}
            <div class={s.advancedModes} style={{ gridColumn: '1 / -1' }}>
              <p class={s.hint}>{autoHelp}</p>
              <label class={s.autoToggle}>
                <input
                  class={s.autoToggleInput}
                  type="checkbox"
                  checked={motionTriggerMode.value}
                  onChange={() => selectExclusiveMode('motion')}
                />
                <span>動いた時だけ撮影</span>
              </label>
              <label class={s.autoToggle}>
                <input
                  class={s.autoToggleInput}
                  type="checkbox"
                  checked={hybridMode.value}
                  onChange={() => selectExclusiveMode('hybrid')}
                />
                <span>研究用: 定間隔 + 動いた時に追加撮影</span>
              </label>
              <label class={s.autoToggle}>
                <input
                  class={s.autoToggleInput}
                  type="checkbox"
                  checked={autonomousMode.value}
                  onChange={() => {
                    autonomousMode.value = !autonomousMode.value;
                  }}
                />
                <span>自律運行（通信が切れても継続）</span>
              </label>
              <label class={s.autoToggle}>
                <input
                  class={s.autoToggleInput}
                  type="checkbox"
                  checked={mlAssistMode.value}
                  onChange={() => {
                    mlAssistMode.value = !mlAssistMode.value;
                  }}
                />
                <span>保存写真を positive / negative に仮分類</span>
              </label>
              <label class={s.autoToggle}>
                <input
                  class={s.autoToggleInput}
                  type="checkbox"
                  checked={adaptiveTimelapseMode.value}
                  onChange={() => {
                    adaptiveTimelapseMode.value = !adaptiveTimelapseMode.value;
                  }}
                />
                <span>適応型タイムラプス（候補が多い時に間隔を短縮）</span>
              </label>
              {adaptiveTimelapseMode.value && (
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '10px', marginTop: '8px', padding: '10px', background: '#f8f8f0', borderRadius: '12px', border: '1px solid var(--line)', gridColumn: '1 / -1' }}>
                  <label class={s.advancedGridLabel}>
                    最小間隔 (秒)
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
                    適応ウィンドウ (秒)
                    <input
                      type="number"
                      min={60}
                      max={3600}
                      value={adaptiveWindowSec.value}
                      onInput={(e) => {
                        adaptiveWindowSec.value = Number((e.target as HTMLInputElement).value || 300);
                      }}
                    />
                  </label>
                </div>
              )}
            </div>
          </div>
        </details>
      </div>

      {/* Column 3: Group actions */}
      <div class={s.groupActions}>
        <button class={s.btnPrimary} type="button" onClick={onStartAll}>
          全機を開始
        </button>
        <button class={s.btnDanger} type="button" onClick={onStopAll}>
          全機を停止
        </button>
        <button class={s.btnSecondary} type="button" onClick={onReviewEvents}>
          イベント確認
        </button>
      </div>
    </section>
  );
}
