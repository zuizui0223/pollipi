import { signal } from '@preact/signals';
import type { Camera } from '../api/types';

export const selectedGalleryCamera = signal<Camera | null>(null);
export const selectedCollection = signal<'all' | 'positive' | 'negative'>('all');
