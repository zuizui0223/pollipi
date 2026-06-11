import { signal } from '@preact/signals';
import {
  getCoordinatorAccessToken,
  getSavedCoordinatorUrl,
} from '../api/client';
import type { CoordinatorUser } from '../api/types';

export const coordinatorBaseUrl = signal<string>(getSavedCoordinatorUrl());
export const coordinatorUser = signal<CoordinatorUser | null>(null);
export const coordinatorOnline = signal<boolean>(Boolean(getCoordinatorAccessToken()));
export const coordinatorMessage = signal<string>(
  getCoordinatorAccessToken() ? 'Coordinator token saved.' : 'Coordinator is not connected.',
);

