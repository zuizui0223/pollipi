import { h } from 'preact';
import { useEffect } from 'preact/hooks';
import { useSignal } from '@preact/signals';
import { selectedGalleryCamera } from '../state/gallery';
import { selectedEventCategory } from '../state/events';
import type { EventCategory } from '../state/events';
import { deviceUrl, fetchEvents, saveEventReview, bulkDeleteEvents } from '../api/client';
import type { EventInfo } from '../api/types';
import * as s from '../styles/components.css';

type EventDeleteScope = 'event_only' | 'event_and_event_image';

export function EventReview() {
  const events = useSignal<EventInfo[]>([]);
  const eventCount = useSignal(0);
  const loadError = useSignal('');
  const selectedEventIds = useSignal<Set<string>>(new Set());
  const deleteScope = useSignal<EventDeleteScope>('event_only');
  const deleting = useSignal(false);
  const deleteMessage = useSignal('');

  const camera = selectedGalleryCamera.value;
  const category = selectedEventCategory.value;

  async function load() {
    if (!camera) {
      events.value = [];
      eventCount.value = 0;
      loadError.value = '';
      selectedEventIds.value = new Set();
      return;
    }
    try {
      const resp = await fetchEvents(camera, category);
      const visibleIds = new Set(resp.events.map((ev) => ev.event_id));
      events.value = resp.events;
      eventCount.value = resp.event_count;
      selectedEventIds.value = new Set([...selectedEventIds.value].filter((id) => visibleIds.has(id)));
      loadError.value = '';
    } catch (err: unknown) {
      loadError.value = `Could not load events: ${(err as Error).message}`;
    }
  }

  useEffect(() => {
    void load();
  }, [camera?.baseUrl, category]);

  async function handleLabel(
    eventId: string,
    manualLabel: string,
    taxon: string,
    reason: string,
    notes: string,
  ) {
    if (!camera) return;
    try {
      await saveEventReview(camera, eventId, {
        manual_label: manualLabel,
        manual_taxon: taxon,
        false_positive_reason: manualLabel === 'noise' ? reason : '',
        manual_notes: notes,
      } as any);
      await load();
    } catch (err: unknown) {
      alert(`Could not save event review: ${(err as Error).message}`);
    }
  }

  function toggleSelect(eventId: string) {
    const next = new Set(selectedEventIds.value);
    if (next.has(eventId)) {
      next.delete(eventId);
    } else {
      next.add(eventId);
    }
    selectedEventIds.value = next;
  }

  function selectAllVisible() {
    selectedEventIds.value = new Set(events.value.map((ev) => ev.event_id));
  }

  function clearSelection() {
    selectedEventIds.value = new Set();
    deleteMessage.value = '';
  }

  async function handleBulkDelete() {
    if (!camera || selectedEventIds.value.size === 0 || deleting.value) return;
    const selectedCount = selectedEventIds.value.size;
    const scopeLabel = deleteScope.value === 'event_only'
      ? 'event records only'
      : 'event records and event JPEGs';
    if (!window.confirm(`Delete ${selectedCount} selected candidate event(s)?\nScope: ${scopeLabel}\nScheduled baseline timelapse images will not be deleted.`)) {
      return;
    }
    deleting.value = true;
    deleteMessage.value = '';
    try {
      const result = await bulkDeleteEvents(camera, [...selectedEventIds.value], deleteScope.value);
      const failures = result.failed || [];
      selectedEventIds.value = new Set();
      await load();
      deleteMessage.value = failures.length
        ? `Deleted ${result.deleted_count} event(s), ${result.image_deleted_count} event image(s). Failed: ${failures.map((f) => `${f.event_id}: ${f.reason}`).join('; ')}`
        : `Deleted ${result.deleted_count} event(s), ${result.image_deleted_count} event image(s).`;
    } catch (err: unknown) {
      deleteMessage.value = `Delete failed: ${(err as Error).message}`;
    } finally {
      deleting.value = false;
    }
  }

  const exportHref = camera ? deviceUrl(camera, '/events/export_labels.csv') : undefined;
  const selectedCount = selectedEventIds.value.size;

  return (
    <section class={s.eventReviewPanel} aria-label="event review">
      <div class={s.galleryHeader}>
        <div>
          <p class={s.sectionTitle}>EVENT REVIEW</p>
          <h2>Candidate event review</h2>
          <p class={s.hint}>Review motion candidates and remove noisy candidate records when needed.</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <a
            class={`${s.downloadLink}${!camera ? ' ' + s.downloadLinkDisabled : ''}`}
            href={exportHref}
            download
          >
            Export labels CSV
          </a>
        </div>
      </div>

      <div class={s.folderSummary}>
        <span>{camera ? camera.camera_label : 'No device selected'}</span>
        <span>{eventCount.value} {category} events</span>
        <span>{selectedCount} selected</span>
      </div>

      <div class={s.collectionSwitch} role="group" aria-label="event category filter">
        {(['all', 'positive', 'negative', 'unclear'] as EventCategory[]).map((cat) => (
          <button
            key={cat}
            class={`${s.collectionTab}${category === cat ? ' ' + s.collectionTabSelected : ''}`}
            type="button"
            onClick={() => {
              selectedEventCategory.value = cat;
              clearSelection();
            }}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      {camera && !loadError.value && events.value.length > 0 && (
        <div class={s.eventBulkBar}>
          <button class={s.btnSecondary} type="button" onClick={selectAllVisible}>
            Select all
          </button>
          <button class={s.btnSecondary} type="button" onClick={clearSelection} disabled={selectedCount === 0 || deleting.value}>
            Clear
          </button>
          <label class={s.eventDeleteOption}>
            <input
              type="checkbox"
              checked={deleteScope.value === 'event_and_event_image'}
              disabled={deleting.value}
              onChange={(e) => {
                deleteScope.value = (e.target as HTMLInputElement).checked ? 'event_and_event_image' : 'event_only';
              }}
            />
            Delete event JPEGs too
          </label>
          <button
            class={s.btnDanger}
            type="button"
            onClick={handleBulkDelete}
            disabled={selectedCount === 0 || deleting.value}
          >
            {deleting.value ? 'Deleting...' : `Delete selected (${selectedCount})`}
          </button>
        </div>
      )}
      {deleteMessage.value && <p class={s.eventDeleteMessage}>{deleteMessage.value}</p>}

      <div class={s.eventGrid}>
        {!camera && <p class={s.galleryEmpty}>Select a device to review events.</p>}
        {camera && loadError.value && <p class={s.galleryEmpty}>{loadError.value}</p>}
        {camera && !loadError.value && events.value.length === 0 && (
          <p class={s.galleryEmpty}>No candidate events yet.</p>
        )}
        {camera &&
          !loadError.value &&
          events.value.map((ev) => {
            const isSelected = selectedEventIds.value.has(ev.event_id);
            return (
              <EventItem
                key={ev.event_id}
                camera={camera}
                event={ev}
                onLabel={handleLabel}
                isSelected={isSelected}
                onToggleSelect={() => toggleSelect(ev.event_id)}
              />
            );
          })}
      </div>
    </section>
  );
}

interface EventItemProps {
  camera: { baseUrl: string; camera_label: string };
  event: EventInfo;
  onLabel: (
    eventId: string,
    label: string,
    taxon: string,
    reason: string,
    notes: string,
  ) => Promise<void>;
  isSelected: boolean;
  onToggleSelect: () => void;
}

function EventItem({ camera, event: ev, onLabel, isSelected, onToggleSelect }: EventItemProps) {
  const taxon = useSignal(ev.manual_taxon || '');
  const reason = useSignal(ev.false_positive_reason || '');
  const notes = useSignal(ev.manual_notes || '');
  const imageMissing = useSignal(false);

  const category = ev.final_category || 'unclear';
  const source = ev.category_source || 'auto';
  const reviewStatus = ev.review_status || 'motion_candidate';
  const reviewLabel = normalizeReviewLabel(ev.review_label || ev.manual_label || '');
  const categoryClass =
    category === 'positive'
      ? s.categoryPositive
      : category === 'negative'
      ? s.categoryNegative
      : s.categoryUnclear;
  const imgSrc = ev.image_url ? deviceUrl(camera, ev.image_url) : '';

  return (
    <article class={`${s.eventItem}${isSelected ? ' ' + s.eventItemSelected : ''}`}>
      <label class={s.eventSelectLabel}>
        <input
          type="checkbox"
          checked={isSelected}
          onChange={onToggleSelect}
        />
        <span>Select candidate</span>
      </label>
      {imgSrc && !imageMissing.value ? (
        <img
          style={{ display: 'block', width: '100%', aspectRatio: '4 / 3', objectFit: 'cover', background: '#dde2d7' }}
          src={imgSrc}
          alt={ev.image_filename || ev.event_id}
          loading="lazy"
          onError={() => {
            imageMissing.value = true;
          }}
        />
      ) : (
        <div
          style={{
            display: 'grid',
            placeItems: 'center',
            width: '100%',
            aspectRatio: '4 / 3',
            background: '#dde2d7',
            color: '#5e675c',
            fontWeight: 700,
          }}
        >
          No image
        </div>
      )}
      <div class={s.eventMeta}>
        <strong>{ev.timestamp || '-'}</strong>
        <span class={`${s.categoryBadge} ${categoryClass}`}>
          {category} / {source} / {reviewStatus}
        </span>
        <span>{ev.device_name || camera.camera_label} / {ev.camera_profile || '-'}</span>
        <span>
          site {ev.site_id || '-'} / flower {ev.flower_id || '-'} / plant {ev.plant_species || '-'}
        </span>
        <span>
          motion {ev.motion_score || '-'} / changed {ev.changed_area_ratio || '-'} / blob {ev.largest_blob_ratio || '-'}
        </span>
        <span>
          wind {ev.wind_like_motion || '-'} / type {ev.motion_type || '-'} / auto {ev.auto_category || '-'}
        </span>
        <span>
          floral {ev.floral_zone_score || '-'} / control {ev.background_control_score || '-'} / cells {ev.changed_cell_count || '-'}
        </span>
        <span>{ev.candidate_reasons || '-'}</span>
      </div>
      <div class={s.eventReviewForm}>
        <input
          placeholder="manual taxon"
          value={taxon.value}
          onInput={(e) => {
            taxon.value = (e.target as HTMLInputElement).value;
          }}
        />
        <select
          value={reason.value}
          onChange={(e) => {
            reason.value = (e.target as HTMLSelectElement).value;
          }}
        >
          {['', 'wind', 'shadow', 'flower_movement', 'camera_shake', 'non_insect_object', 'lighting_change', 'unclear', 'other'].map(
            (v) => (
              <option key={v} value={v}>
                {v || 'false positive reason'}
              </option>
            ),
          )}
        </select>
        <input
          placeholder="manual notes"
          value={notes.value}
          style={{ gridColumn: '1 / -1' }}
          onInput={(e) => {
            notes.value = (e.target as HTMLInputElement).value;
          }}
        />
        <div class={s.eventReviewActions}>
          {([['visit', 'Visit'], ['noise', 'Noise'], ['unclear', 'Unclear']] as const).map(
            ([val, text]) => (
              <button
                key={val}
                type="button"
                class={`${
                  val === 'visit'
                    ? s.quickLabelPositive
                    : val === 'noise'
                    ? s.quickLabelNegative
                    : s.quickLabelUnclear
                }${reviewLabel === val ? ' ' + s.quickLabelSelected : ''}`}
                style={{ border: 0, borderRadius: '8px', cursor: 'pointer', padding: '8px' }}
                onClick={() => onLabel(ev.event_id, val, taxon.value, reason.value, notes.value)}
              >
                {text}
              </button>
            ),
          )}
        </div>
      </div>
    </article>
  );
}

function normalizeReviewLabel(value: string): string {
  return ({
    insect: 'visit',
    positive: 'visit',
    visit: 'visit',
    non_insect: 'noise',
    negative: 'noise',
    noise: 'noise',
    unclear: 'unclear',
  } as Record<string, string>)[value] || '';
}
