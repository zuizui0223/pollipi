import { h } from 'preact';
import { useEffect } from 'preact/hooks';
import { useSignal } from '@preact/signals';
import { selectedGalleryCamera } from '../state/gallery';
import {
  fetchTrainingStatus,
  startTraining as apiStartTraining,
  resetTrainingModel as apiResetTraining,
} from '../api/client';
import type { TrainingStatus } from '../api/types';
import * as s from '../styles/components.css';

export function TrainingPanel() {
  const trainingStatus = useSignal<TrainingStatus | null>(null);
  const trainingMsg = useSignal('positive / negative の確認済み画像を読み込み中...');
  const busy = useSignal(false);

  const camera = selectedGalleryCamera.value;

  async function load() {
    if (!camera) return;
    try {
      const status = await fetchTrainingStatus(camera.baseUrl);
      trainingStatus.value = status;
      trainingMsg.value = status.message;
    } catch (err: unknown) {
      trainingMsg.value = `学習状態を取得できません: ${(err as Error).message}`;
    }
  }

  useEffect(() => {
    void load();
  }, [camera?.baseUrl]);

  async function handleStartTraining() {
    if (!camera) return;
    if (!confirm(`${camera.camera_label} の positive / negative を使って再学習しますか？`)) return;
    busy.value = true;
    try {
      await apiStartTraining(camera.baseUrl);
      await load();
    } catch (err: unknown) {
      alert(`再学習できませんでした: ${(err as Error).message}`);
    } finally {
      busy.value = false;
    }
  }

  async function handleReset() {
    if (!camera) return;
    if (!confirm(`${camera.camera_label} の学習済みモデルを破棄しますか？`)) return;
    busy.value = true;
    try {
      await apiResetTraining(camera.baseUrl);
      await load();
    } catch (err: unknown) {
      alert(`モデルを破棄できませんでした: ${(err as Error).message}`);
    } finally {
      busy.value = false;
    }
  }

  const st = trainingStatus.value;

  return (
    <section class={s.trainingPanel} aria-label="二値機械学習">
      <div>
        <p class={s.sectionTitle}>SAME-DAY LEARNING</p>
        <h2>帰宅後・給電時の再学習準備</h2>
        <p>{trainingMsg.value}</p>
      </div>
      <dl class={s.trainingMetrics}>
        <div class={s.trainingMetricsCell}>
          <dt class={s.metricsDt}>positive</dt>
          <dd class={s.metricsDd}>{st ? String(st.positive_count) : '-'}</dd>
        </div>
        <div class={s.trainingMetricsCell}>
          <dt class={s.metricsDt}>negative</dt>
          <dd class={s.metricsDd}>{st ? String(st.negative_count) : '-'}</dd>
        </div>
        <div class={s.trainingMetricsCell}>
          <dt class={s.metricsDt}>model</dt>
          <dd class={s.metricsDd}>{st ? (st.model_available ? 'available' : 'none') : '-'}</dd>
        </div>
      </dl>
      <div class={s.groupActions}>
        <button
          class={s.btnPrimary}
          type="button"
          onClick={handleStartTraining}
          disabled={busy.value || !camera}
        >
          この観察機で再学習
        </button>
        <button
          class={s.btnSecondary}
          type="button"
          onClick={handleReset}
          disabled={busy.value || !camera}
        >
          モデルを破棄
        </button>
      </div>
    </section>
  );
}
