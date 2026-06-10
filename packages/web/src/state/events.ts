import { signal } from '@preact/signals';

export type EventCategory = 'all' | 'positive' | 'negative' | 'unclear';
export const selectedEventCategory = signal<EventCategory>('all');
