import { signal } from '@preact/signals';
import type { Camera } from '../api/types';

export const selectedGalleryCamera = signal<Camera | null>(null);
