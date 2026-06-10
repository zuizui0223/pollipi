import { signal } from '@preact/signals';
import type { TrainingStatus } from '../api/types';

export const trainingStatus = signal<TrainingStatus | null>(null);
export const trainingMessage = signal<string>('positive / negative の確認済み画像を読み込み中...');
