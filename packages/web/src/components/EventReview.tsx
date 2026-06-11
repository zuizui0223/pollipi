import { h } from 'preact';
import { useEffect } from 'preact/hooks';
import { useSignal } from '@preact/signals';
import { selectedGalleryCamera } from '../state/gallery';
import { selectedEventCategory } from '../state/events';
import type { EventCategory } from '../state/events';
import { cameras } from '../state/devices';
import { deviceUrl, fetchEvents, saveEventReview } from '../api/client';
import type { EventInfo } from '../api/types';
import * as s from '../styles/components.css';

export function EventReview() {
  const events = useSignal<EventInfo[]>([]);
  const eventCount = useSignal(0);
  const loadError = useSignal('');

  const camera = selectedGalleryCamera.value;
  const category = selectedEventCategory.value;

  async function load() {
    if (!camera) {
      events.value = [];
      eventCount.value = 0;
      loadError.value = '';
      return;
    }
    try {
      const resp = await fetchEvents(camera, category);
      events.value = resp.events;
      eventCount.value = resp.event_count;
      loadError.value = '';
    } catch (err: unknown) {
      loadError.value = `イベントを取得できません: ${(err as Error).message}`;
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
        false_positive_reason: manualLabel === 'non_insect' ? reason : '',
        manual_notes: notes,
      } as any);
      await load();
    } catch (err: unknown) {
      alert(`Event reviewを保存できませんでした: ${(err as Error).message}`);
    }
  }

  const exportHref = camera ? deviceUrl(camera, '/events/export_labels.csv') : undefined;

  return (
    <section class={s.eventReviewPanel} aria-label="event review">
      <div class={s.galleryHeader}>
        <div>
          <p class={s.sectionTitle}>EVENT REVIEW</p>
          <h2>候補イベントを確認</h2>
          <p class={s.hint}>
            候補を自動で Positive / Negative / Unclear に分けます。間違っているものだけ修正してください。
          </p>
        </div>
        <a
          class={`${s.downloadLink}${!camera ? ' ' + s.downloadLinkDisabled : ''}`}
          href={exportHref}
          download
        >
          Export labels CSV
        </a>
      </div>

      <div class={s.folderSummary}>
        <span>{camera ? camera.camera_label : '観察機未選択'}</span>
        <span>
          {eventCount.value} {category} events
        </span>
      </div>

      {/* Category tabs */}
      <div class={s.collectionSwitch} role="group" aria-label="event category filter">
        {(['all', 'positive', 'negative', 'unclear'] as EventCategory[]).map((cat) => (
          <button
            key={cat}
            class={`${s.collectionTab}${category === cat ? ' ' + s.collectionTabSelected : ''}`}
            type="button"
            onClick={() => {
              selectedEventCategory.value = cat;
            }}
          >
            {cat.charAt(0).toUpperCase() + cat.slice(1)}
          </button>
        ))}
      </div>

      <div class={s.eventGrid}>
        {!camera && <p class={s.galleryEmpty}>観察機を選択してください。</p>}
        {camera && loadError.value && <p class={s.galleryEmpty}>{loadError.value}</p>}
        {camera && !loadError.value && events.value.length === 0 && (
          <p class={s.galleryEmpty}>イベント候補はまだありません。</p>
        )}
        {camera &&
          !loadError.value &&
          events.value.map((ev) => (
            <EventItem key={ev.event_id} camera={camera} event={ev} onLabel={handleLabel} />
          ))}
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
}

function EventItem({ camera, event: ev, onLabel }: EventItemProps) {
  const taxon = useSignal(ev.manual_taxon || '');
  const reason = useSignal(ev.false_positive_reason || '');
  const notes = useSignal(ev.manual_notes || '');

  const category = ev.final_category || 'unclear';
  const source = ev.category_source || 'auto';
  const reviewStatus = ev.review_status || 'auto_grouped';

  const categoryClass =
    category === 'positive'
      ? s.categoryPositive
      : category === 'negative'
      ? s.categoryNegative
      : s.categoryUnclear;

  const imgSrc = ev.image_url ? deviceUrl(camera, ev.image_url) : '';

  return (
    <article class={`${s.eventItem}`}>
      {imgSrc && (
        <img
          style={{ display: 'block', width: '100%', aspectRatio: '4 / 3', objectFit: 'cover', background: '#dde2d7' }}
          src={imgSrc}
          alt={ev.image_filename || ev.event_id}
          loading="lazy"
        />
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
          motion {ev.motion_score || '-'} / changed {ev.changed_area_ratio || '-'} / blob{' '}
          {ev.largest_blob_ratio || '-'}
        </span>
        <span>
          wind {ev.wind_like_motion || '-'} / type {ev.motion_type || '-'} / auto{' '}
          {ev.auto_category || '-'}
        </span>
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
          {([['insect', 'Positive'], ['non_insect', 'Negative'], ['unclear', 'Unclear']] as const).map(
            ([val, text]) => (
              <button
                key={val}
                type="button"
                class={`${
                  val === 'insect'
                    ? s.quickLabelPositive
                    : val === 'non_insect'
                    ? s.quickLabelNegative
                    : s.quickLabelUnclear
                }${ev.manual_label === val ? ' ' + s.quickLabelSelected : ''}`}
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
