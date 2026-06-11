import { h } from 'preact';
import { useEffect } from 'preact/hooks';
import { useSignal } from '@preact/signals';
import { selectedGalleryCamera, selectedCollection } from '../state/gallery';
import { cameras } from '../state/devices';
import { deviceUrl, fetchImages, deleteImage, labelImage, deleteAllImages } from '../api/client';
import type { ImageInfo, ImagesResponse } from '../api/types';
import { formatCaptureTime, formatBytes } from '../lib/formatting';
import * as s from '../styles/components.css';

export function Gallery() {
  const images = useSignal<ImageInfo[]>([]);
  const imageCount = useSignal(0);
  const totalSize = useSignal(0);
  const imageDir = useSignal('保存先を読み込み中...');
  const loadError = useSignal('');
  const deletingAll = useSignal(false);

  const camera = selectedGalleryCamera.value;
  const collection = selectedCollection.value;
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
      const resp = await fetchImages(camera, collection);
      images.value = resp.images;
      imageCount.value = resp.image_count;
      totalSize.value = resp.total_size_bytes;
      imageDir.value = resp.image_dir;
      if (collection === 'all') camera.imageCount = resp.image_count;
      loadError.value = '';
    } catch (err: unknown) {
      loadError.value = `画像一覧を取得できません: ${(err as Error).message}`;
    }
  }

  useEffect(() => {
    void load();
  }, [camera?.baseUrl, collection]);

  async function handleLabel(filename: string, label: string) {
    if (!camera) return;
    try {
      await labelImage(camera, filename, label);
      await load();
    } catch (err: unknown) {
      alert(`ラベルを保存できませんでした: ${(err as Error).message}`);
    }
  }

  async function handleDelete(filename: string) {
    if (!camera) return;
    if (!confirm(`${camera.camera_label} のこの写真を削除しますか？\n${filename}`)) return;
    try {
      await deleteImage(camera, filename);
      await load();
    } catch (err: unknown) {
      alert(`削除できませんでした: ${(err as Error).message}`);
    }
  }

  async function handleDeleteAll() {
    if (!camera) return;
    if (camera.status && camera.status.running) {
      alert('全削除の前に、この観察機の撮影を停止してください。');
      return;
    }
    const count = Number.isFinite(camera.imageCount) ? `${camera.imageCount} 枚の` : '';
    if (!confirm(`${camera.camera_label} の${count}保存画像をすべて削除しますか？\n\n削除後は元に戻せません。`)) return;
    deletingAll.value = true;
    try {
      const result = await deleteAllImages(camera);
      alert(`${result.deleted_count} 枚を削除しました。`);
      await load();
    } catch (err: unknown) {
      alert(`全削除できませんでした: ${(err as Error).message}`);
    } finally {
      deletingAll.value = false;
    }
  }

  const zipHref = camera
    ? deviceUrl(camera, `/exports/images.zip?collection=${collection}`)
    : undefined;
  const zipLabel =
    collection === 'all' ? '全画像とログをZIP保存' : `${collection} をZIP保存`;

  return (
    <section class={s.galleryPanel} aria-label="撮影フォルダ">
      <div class={s.galleryHeader}>
        <div>
          <p class={s.sectionTitle}>撮影フォルダ</p>
          <h2>画像を確認・整理</h2>
          <p class={s.hint}>all / positive / negative を各台ごとに確認できます。</p>
        </div>
        {/* Camera selector */}
        <div class={s.gallerySwitch} role="group" aria-label="観察機選択">
          {cameraList.map((cam) => (
            <button
              key={cam.coordinator_device_id ? `coordinator-${cam.coordinator_device_id}` : cam.baseUrl}
              class={`${s.galleryTab}${
                camera &&
                (
                  (cam.coordinator_device_id && camera.coordinator_device_id === cam.coordinator_device_id) ||
                  (!cam.coordinator_device_id && camera.baseUrl === cam.baseUrl)
                )
                  ? ' ' + s.galleryTabSelected
                  : ''
              }`}
              type="button"
              onClick={() => {
                selectedGalleryCamera.value = cam;
              }}
            >
              {cam.camera_label || cam.device_name || cam.baseUrl}
            </button>
          ))}
        </div>
        <a
          class={`${s.downloadLink}${!camera ? ' ' + s.downloadLinkDisabled : ''}`}
          href={zipHref}
          download
        >
          {zipLabel}
        </a>
        {collection === 'all' && (
          <button
            class={s.btnDanger}
            type="button"
            onClick={handleDeleteAll}
            disabled={deletingAll.value}
          >
            全画像を削除
          </button>
        )}
      </div>

      {/* Collection tabs */}
      <div class={s.collectionSwitch} role="group" aria-label="表示フォルダ">
        {(['all', 'positive', 'negative'] as const).map((col) => (
          <button
            key={col}
            class={`${s.collectionTab}${collection === col ? ' ' + s.collectionTabSelected : ''}`}
            type="button"
            onClick={() => {
              selectedCollection.value = col;
            }}
          >
            {col}
          </button>
        ))}
      </div>

      <div class={s.folderSummary}>
        <span>{camera ? `${camera.camera_label} / ${collection}` : '観察機未選択'}</span>
        <span>{imageCount.value > 0 ? `${imageCount.value} 枚` : '-'}</span>
        <span>{totalSize.value > 0 ? formatBytes(totalSize.value) : ''}</span>
      </div>
      <p class={s.folderPath}>{imageDir.value}</p>

      <div class={s.galleryGrid}>
        {!camera && (
          <p class={s.galleryEmpty}>観察機が登録されていません。</p>
        )}
        {camera && loadError.value && (
          <p class={s.galleryEmpty}>{loadError.value}</p>
        )}
        {camera && !loadError.value && images.value.length === 0 && (
          <p class={s.galleryEmpty}>画像はまだありません。</p>
        )}
        {camera &&
          !loadError.value &&
          images.value.map((img) => {
            const imageCategory = img.final_category || img.label || 'unclear';
            const labelClass =
              imageCategory === 'positive'
                ? s.labelPositive
                : imageCategory === 'negative'
                ? s.labelNegative
                : s.labelUnclear;
            const downloadUrl = deviceUrl(
              camera,
              `${img.url}${img.url.includes('?') ? '&' : '?'}download=true`,
            );
            return (
              <article key={img.filename} class={s.galleryItem}>
                <img
                  class={s.galleryItemImg}
                  src={deviceUrl(camera, img.url)}
                  alt={img.filename}
                  loading="lazy"
                />
                <div class={s.galleryDetail}>
                  <span>{formatCaptureTime(img.captured_at)}</span>
                  <span>{formatBytes(img.size_bytes)}</span>
                </div>
                <p class={`${s.labelBadge} ${labelClass}`}>
                  {imageCategory} / {img.category_source || img.review_status || 'auto'}
                </p>
                <a
                  href={downloadUrl}
                  download={img.filename}
                  style={{ display: 'block', padding: '0 10px 4px', fontSize: '13px', color: 'var(--leaf)' }}
                >
                  iPadに保存
                </a>
                <div class={s.reviewActions}>
                  <button
                    class={s.labelPositive}
                    type="button"
                    style={{ border: 0, borderRadius: '8px', cursor: 'pointer', padding: '6px' }}
                    onClick={() => handleLabel(img.filename, 'positive')}
                  >
                    Positive
                  </button>
                  <button
                    class={s.labelNegative}
                    type="button"
                    style={{ border: 0, borderRadius: '8px', cursor: 'pointer', padding: '6px' }}
                    onClick={() => handleLabel(img.filename, 'negative')}
                  >
                    Negative
                  </button>
                  <button
                    class={s.labelUnclear}
                    type="button"
                    style={{ border: 0, borderRadius: '8px', cursor: 'pointer', padding: '6px', gridColumn: '1 / -1' }}
                    onClick={() => handleLabel(img.filename, 'unlabeled')}
                  >
                    Unclear
                  </button>
                </div>
                <button
                  class={s.deleteImageBtn}
                  type="button"
                  onClick={() => handleDelete(img.filename)}
                >
                  削除
                </button>
              </article>
            );
          })}
      </div>
    </section>
  );
}
