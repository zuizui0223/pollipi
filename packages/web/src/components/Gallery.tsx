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
  const imageDir = useSignal('保存先を読み込み中...');
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
      imageDir.value = '観察機を追加すると保存画像を表示できます。';
      loadError.value = '';
      return;
    }
    try {
      const response = await fetchImages(camera, 'all');
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
      loadError.value = `画像一覧を取得できません: ${(error as Error).message}`;
    }
  }

  useEffect(() => {
    void load();
  }, [camera?.baseUrl]);

  async function handleDelete(filename: string) {
    if (!camera) return;
    if (!confirm(`${camera.camera_label} のこの予定撮影画像を削除しますか？\n${filename}`)) return;
    try {
      await deleteImage(camera, filename);
      await load();
    } catch (error: unknown) {
      alert(`削除できませんでした: ${(error as Error).message}`);
    }
  }

  async function handleDeleteAll() {
    if (!camera) return;
    if (camera.status?.running) {
      alert('全削除の前に、この観察機の撮影を停止してください。');
      return;
    }
    if (!confirm(`${camera.camera_label} の保存済み予定撮影画像をすべて削除しますか？\n\n削除後は元に戻せません。`)) return;
    deleting.value = true;
    try {
      const result = await deleteAllImages(camera);
      alert(`${result.deleted_count} 枚を削除しました。`);
      await load();
    } catch (error: unknown) {
      alert(`全削除できませんでした: ${(error as Error).message}`);
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
    if (!confirm(`選択した ${selectedFilenames.value.size} 枚の予定撮影画像を削除しますか？`)) return;
    deleting.value = true;
    try {
      const result = await bulkDeleteImages(camera, [...selectedFilenames.value]);
      alert(`${result.deleted_count} 枚を削除しました。`);
      selectedFilenames.value = new Set();
      await load();
    } catch (error: unknown) {
      alert(`削除できませんでした: ${(error as Error).message}`);
    } finally {
      deleting.value = false;
    }
  }

  const zipHref = camera ? deviceUrl(camera, '/exports/images.zip?collection=all') : undefined;

  return (
    <section class={s.galleryPanel} aria-label="予定撮影画像">
      <div class={s.galleryHeader}>
        <div>
          <p class={s.sectionTitle}>SCHEDULED TIMELAPSE</p>
          <h2>予定撮影画像を確認・整理</h2>
          <p class={s.hint}>ここには予定タイムラプス画像だけが保存されます。候補event画像や機械学習ラベルはありません。</p>
        </div>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center', flexWrap: 'wrap' }}>
          <a class={`${s.downloadLink}${!camera ? ` ${s.downloadLinkDisabled}` : ''}`} href={zipHref} download>
            画像とshadow logをZIP保存
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
              {selectMode.value ? '選択解除' : '選択モード'}
            </button>
          )}
          {selectMode.value && selectedFilenames.value.size > 0 && (
            <button class={s.btnDanger} type="button" onClick={handleBulkDelete} disabled={deleting.value}>
              選択を削除 ({selectedFilenames.value.size})
            </button>
          )}
          {camera && !selectMode.value && (
            <button class={s.btnDanger} type="button" onClick={handleDeleteAll} disabled={deleting.value}>
              全画像を削除
            </button>
          )}
        </div>
      </div>

      <div class={s.gallerySwitch} role="group" aria-label="観察機選択">
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
        <span>{camera ? camera.camera_label : '観察機未選択'}</span>
        <span>{imageCount.value > 0 ? `${imageCount.value} 枚` : '-'}</span>
        <span>{totalSize.value > 0 ? formatBytes(totalSize.value) : ''}</span>
      </div>
      <p class={s.folderPath}>{imageDir.value}</p>

      <div class={s.galleryGrid}>
        {!camera && <p class={s.galleryEmpty}>観察機が登録されていません。</p>}
        {camera && loadError.value && <p class={s.galleryEmpty}>{loadError.value}</p>}
        {camera && !loadError.value && images.value.length === 0 && <p class={s.galleryEmpty}>予定撮影画像はまだありません。</p>}
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
                iPadに保存
              </a>
              {!selectMode.value && (
                <button class={s.deleteImageBtn} type="button" onClick={() => void handleDelete(image.filename)}>
                  削除
                </button>
              )}
            </article>
          );
        })}
      </div>
    </section>
  );
}
