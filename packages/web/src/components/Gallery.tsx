import { h } from 'preact';
import { useEffect } from 'preact/hooks';
import { useSignal } from '@preact/signals';

import { selectedGalleryCamera } from '../state/gallery';
import { cameras } from '../state/devices';
import { deviceUrl, fetchImages, deleteImage, deleteAllImages, bulkDeleteImages } from '../api/client';
import type { ImageInfo } from '../api/types';
import { formatCaptureTime, formatBytes } from '../lib/formatting';
import * as s from '../styles/components.css';

export function Gallery() {
  const images = useSignal<ImageInfo[]>([]);
  const imageCount = useSignal(0);
  const totalSize = useSignal(0);
  const imageDir = useSignal('Loading saved images...');
  const loadError = useSignal('');
  const deleting = useSignal(false);
  const selectMode = useSignal(false);
  const selectedFilenames = useSignal<Set<string>>(new Set());

  const camera = selectedGalleryCamera.value;
  const cameraList = cameras.value;

  async function load() {
    if (!camera) {
      images.value = [];
      imageCount.value = 0;
      totalSize.value = 0;
      imageDir.value = 'Add a Raspberry Pi to view saved images.';
      loadError.value = '';
      return;
    }
    try {
      const response = await fetchImages(camera);
      images.value = response.images;
      imageCount.value = response.image_count;
      totalSize.value = response.total_size_bytes;
      imageDir.value = response.image_dir;
      camera.imageCount = response.image_count;
      selectedFilenames.value = new Set(
        [...selectedFilenames.value].filter((filename) => response.images.some((image) => image.filename === filename)),
      );
      loadError.value = '';
    } catch (error: unknown) {
      loadError.value = `Could not load the image list: ${(error as Error).message}`;
    }
  }

  useEffect(() => {
    void load();
  }, [camera?.baseUrl]);

  async function handleDelete(filename: string) {
    if (!camera) return;
    if (!confirm(`Delete this scheduled timelapse image from ${camera.camera_label}?\n${filename}`)) return;
    try {
      await deleteImage(camera, filename);
      await load();
    } catch (error: unknown) {
      alert(`Delete failed: ${(error as Error).message}`);
    }
  }

  async function handleDeleteAll() {
    if (!camera) return;
    if (camera.status?.running) {
      alert('Stop this Raspberry Pi before deleting all images.');
      return;
    }
    if (!confirm(`Delete all saved scheduled timelapse images from ${camera.camera_label}?\n\nThis cannot be undone.`)) return;
    deleting.value = true;
    try {
      const result = await deleteAllImages(camera);
      alert(`Deleted ${result.deleted_count} image(s).`);
      await load();
    } catch (error: unknown) {
      alert(`Delete all failed: ${(error as Error).message}`);
    } finally {
      deleting.value = false;
    }
  }

  function toggleSelect(filename: string) {
    const next = new Set(selectedFilenames.value);
    if (next.has(filename)) next.delete(filename);
    else next.add(filename);
    selectedFilenames.value = next;
  }

  async function handleBulkDelete() {
    if (!camera || selectedFilenames.value.size === 0 || deleting.value) return;
    if (!confirm(`Delete ${selectedFilenames.value.size} selected scheduled timelapse image(s)?`)) return;
    deleting.value = true;
    try {
      const result = await bulkDeleteImages(camera, [...selectedFilenames.value]);
      alert(`Deleted ${result.deleted_count} image(s).`);
      selectedFilenames.value = new Set();
      await load();
    } catch (error: unknown) {
      alert(`Delete failed: ${(error as Error).message}`);
    } finally {
      deleting.value = false;
    }
  }

  const zipHref = camera ? deviceUrl(camera, '/exports/images.zip') : undefined;

  return (
    <section class={s.galleryPanel} aria-label="Scheduled timelapse images">
      <div class={s.galleryHeader}>
        <div>
          <p class={s.sectionTitle}>SCHEDULED TIMELAPSE</p>
          <h2>Review saved images</h2>
          <p class={s.hint}>
            This gallery contains scheduled timelapse images and shadow logs only. Candidate events and ML labels are not part of the active path.
          </p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <a class={`${s.downloadLink}${!camera ? ` ${s.downloadLinkDisabled}` : ''}`} href={zipHref} download>
            Download images and shadow log ZIP
          </a>
          {camera && (
            <button
              class={s.btnSecondary}
              type="button"
              onClick={() => {
                selectMode.value = !selectMode.value;
                selectedFilenames.value = new Set();
              }}
            >
              {selectMode.value ? 'Clear selection' : 'Select images'}
            </button>
          )}
          {selectMode.value && selectedFilenames.value.size > 0 && (
            <button class={s.btnDanger} type="button" onClick={handleBulkDelete} disabled={deleting.value}>
              Delete selected ({selectedFilenames.value.size})
            </button>
          )}
          {camera && !selectMode.value && (
            <button class={s.btnDanger} type="button" onClick={handleDeleteAll} disabled={deleting.value}>
              Delete all images
            </button>
          )}
        </div>
      </div>

      <div class={s.gallerySwitch} role="group" aria-label="Device selection">
        {cameraList.map((item) => (
          <button
            key={item.coordinator_device_id ? `coordinator-${item.coordinator_device_id}` : item.baseUrl}
            class={`${s.galleryTab}${camera && ((item.coordinator_device_id && camera.coordinator_device_id === item.coordinator_device_id) || (!item.coordinator_device_id && camera.baseUrl === item.baseUrl)) ? ` ${s.galleryTabSelected}` : ''}`}
            type="button"
            onClick={() => { selectedGalleryCamera.value = item; }}
          >
            {item.camera_label || item.device_name || item.baseUrl}
          </button>
        ))}
      </div>

      <div class={s.folderSummary}>
        <span>{camera ? camera.camera_label : 'No device selected'}</span>
        <span>{imageCount.value > 0 ? `${imageCount.value} images` : '-'}</span>
        <span>{totalSize.value > 0 ? formatBytes(totalSize.value) : ''}</span>
      </div>
      <p class={s.folderPath}>{imageDir.value}</p>

      <div class={s.galleryGrid}>
        {!camera && <p class={s.galleryEmpty}>No Raspberry Pi is registered.</p>}
        {camera && loadError.value && <p class={s.galleryEmpty}>{loadError.value}</p>}
        {camera && !loadError.value && images.value.length === 0 && <p class={s.galleryEmpty}>No scheduled timelapse images yet.</p>}
        {camera && !loadError.value && images.value.map((image) => {
          const selected = selectedFilenames.value.has(image.filename);
          const downloadUrl = deviceUrl(camera, `${image.url}${image.url.includes('?') ? '&' : '?'}download=true`);
          return (
            <article
              key={image.filename}
              class={`${s.galleryItem}${selected ? ` ${s.galleryItemSelected}` : ''}`}
              style={selectMode.value ? { cursor: 'pointer' } : undefined}
              onClick={selectMode.value ? () => toggleSelect(image.filename) : undefined}
            >
              <img class={s.galleryItemImg} src={deviceUrl(camera, image.url)} alt={image.filename} loading="lazy" />
              <div class={s.galleryDetail}>
                <span>{formatCaptureTime(image.captured_at)}</span>
                <span>{formatBytes(image.size_bytes)}</span>
              </div>
              <a
                href={downloadUrl}
                download={image.filename}
                style={{ display: 'block', padding: '0 10px 4px', fontSize: '13px', color: 'var(--leaf)' }}
                onClick={selectMode.value ? (event) => event.stopPropagation() : undefined}
              >
                Save to iPad
              </a>
              {!selectMode.value && (
                <button class={s.deleteImageBtn} type="button" onClick={() => void handleDelete(image.filename)}>
                  Delete
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
