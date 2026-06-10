import { h } from 'preact';
import { useRef, useEffect } from 'preact/hooks';
import { useSignal } from '@preact/signals';
import type { Camera } from '../api/types';
import type { RoiRect, DisplayRect, DragPoint, DragMode } from '../lib/roi';
import {
  normalizeRoi,
  roiToDisplayRect,
  displayRectToRoi,
  displayRectToRoiRect,
  getRoiDragMode,
  updateDisplayRoiRect,
  defaultCenteredRoi,
  pointInImage,
  MONITOR_WIDTH,
  MONITOR_HEIGHT,
} from '../lib/roi';
import * as s from '../styles/components.css';

interface Props {
  camera: Camera;
  onRoiAccepted: (roi: RoiRect) => void;
  onRedraw: () => void;
  onCancel: () => void;
  onReadjustAngle: () => void;
  message?: string;
}

function drawBoxOnElement(box: HTMLElement, rect: DisplayRect) {
  box.style.display = 'block';
  box.style.left = `${rect.left}px`;
  box.style.top = `${rect.top}px`;
  box.style.width = `${rect.width}px`;
  box.style.height = `${rect.height}px`;
}

function drawBoxFromPoints(box: HTMLElement, start: DragPoint, end: DragPoint) {
  drawBoxOnElement(box, {
    left: Math.min(start.x, end.x),
    top: Math.min(start.y, end.y),
    width: Math.abs(end.x - start.x),
    height: Math.abs(end.y - start.y),
  });
}

export function RoiEditor({ camera, onRoiAccepted, onRedraw, onCancel, onReadjustAngle, message }: Props) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const imgRef = useRef<HTMLImageElement>(null);
  const boxRef = useRef<HTMLSpanElement>(null);

  const imgReady = useSignal(false);
  const editingRoi = useSignal<RoiRect | null>(normalizeRoi(camera.editing_roi));
  const editorMessage = useSignal(message || '静止画像の上でROIを指定してください。');
  const loadError = useSignal(false);

  // Load the preview image
  useEffect(() => {
    const img = imgRef.current;
    if (!img) return;
    imgReady.value = false;
    loadError.value = false;
    img.src = `${camera.baseUrl}/preview?t=${Date.now()}`;
  }, [camera.baseUrl]);

  // When editingRoi changes, update the box position
  useEffect(() => {
    const img = imgRef.current;
    const box = boxRef.current;
    if (!img || !box || !imgReady.value) return;
    const roi = editingRoi.value;
    if (!roi) {
      box.style.display = 'none';
      return;
    }
    const rect = roiToDisplayRect(roi, img);
    if (rect) drawBoxOnElement(box, rect);
  }, [editingRoi.value, imgReady.value]);

  // Setup pointer/touch/mouse drawing
  useEffect(() => {
    const wrap = wrapRef.current;
    const img = imgRef.current;
    const box = boxRef.current;
    if (!wrap || !img || !box) return;

    let drawing = false;
    let startPoint: DragPoint | null = null;
    let previousRoi: RoiRect | null = null;
    let dragMode: DragMode = { type: 'draw' };
    let baseRect: DisplayRect | null = null;
    let currentRect: DisplayRect | null = null;
    let usedPointer = false;

    const begin = (event: PointerEvent | TouchEvent | MouseEvent) => {
      if ('type' in event && event.type.startsWith('touch') && usedPointer) return;
      const point = pointInImage(event as MouseEvent, img);
      if (!point) return;
      event.preventDefault();
      drawing = true;
      startPoint = point;
      previousRoi = normalizeRoi(editingRoi.value);
      baseRect = roiToDisplayRect(previousRoi, img);
      dragMode = getRoiDragMode(point, baseRect);
      currentRect = dragMode.type === 'draw' ? null : baseRect;
      if (currentRect) drawBoxOnElement(box, currentRect);
      else drawBoxFromPoints(box, point, point);
      if ('pointerId' in event && wrap.setPointerCapture) {
        usedPointer = true;
        wrap.setPointerCapture((event as PointerEvent).pointerId);
      }
    };

    const move = (event: PointerEvent | TouchEvent | MouseEvent) => {
      if ('type' in event && event.type.startsWith('touch') && usedPointer) return;
      if (!drawing || !startPoint) return;
      const point = pointInImage(event as MouseEvent, img);
      if (!point) return;
      event.preventDefault();
      if (dragMode.type === 'draw') {
        drawBoxFromPoints(box, startPoint, point);
      } else {
        currentRect = updateDisplayRoiRect(dragMode, baseRect!, startPoint, point);
        drawBoxOnElement(box, currentRect);
      }
    };

    const end = (event: PointerEvent | TouchEvent | MouseEvent) => {
      if ('type' in event && event.type.startsWith('touch') && usedPointer) return;
      if (!drawing || !startPoint) return;
      const point = pointInImage(event as MouseEvent, img);
      const origin = startPoint;
      drawing = false;
      startPoint = null;
      if (!point) return;
      event.preventDefault();
      const roi =
        dragMode.type === 'draw'
          ? displayRectToRoi(origin, point)
          : displayRectToRoiRect(currentRect, point.width, point.height);
      if (roi) {
        editingRoi.value = roi;
        editorMessage.value = 'ROIを指定しました。よければ「このROIで決定」を押してください。';
      } else {
        editingRoi.value = previousRoi;
        editorMessage.value = 'ROI is too small. Please draw a larger rectangle.';
      }
    };

    if (window.PointerEvent) {
      wrap.addEventListener('pointerdown', begin as EventListener);
      wrap.addEventListener('pointermove', move as EventListener);
      wrap.addEventListener('pointerup', end as EventListener);
      wrap.addEventListener('pointercancel', end as EventListener);
    }
    wrap.addEventListener('touchstart', begin as EventListener, { passive: false });
    wrap.addEventListener('touchmove', move as EventListener, { passive: false });
    wrap.addEventListener('touchend', end as EventListener, { passive: false });
    wrap.addEventListener('mousedown', begin as EventListener);
    wrap.addEventListener('mousemove', move as EventListener);
    wrap.addEventListener('mouseup', end as EventListener);

    return () => {
      if (window.PointerEvent) {
        wrap.removeEventListener('pointerdown', begin as EventListener);
        wrap.removeEventListener('pointermove', move as EventListener);
        wrap.removeEventListener('pointerup', end as EventListener);
        wrap.removeEventListener('pointercancel', end as EventListener);
      }
      wrap.removeEventListener('touchstart', begin as EventListener);
      wrap.removeEventListener('touchmove', move as EventListener);
      wrap.removeEventListener('touchend', end as EventListener);
      wrap.removeEventListener('mousedown', begin as EventListener);
      wrap.removeEventListener('mousemove', move as EventListener);
      wrap.removeEventListener('mouseup', end as EventListener);
    };
  }, [imgReady.value]);

  function handleAccept() {
    const roi = normalizeRoi(editingRoi.value);
    if (!roi) {
      alert('静止画像の上でROIを指定してください。');
      return;
    }
    onRoiAccepted(roi);
  }

  function handleRedraw() {
    editingRoi.value = defaultCenteredRoi();
    editorMessage.value = 'ROIをリセットしました。静止画像の上でROIをもう一度指定してください。';
    onRedraw();
  }

  const roiText = editingRoi.value
    ? `ROI: 編集中 x=${editingRoi.value.roi_x}, y=${editingRoi.value.roi_y}, w=${editingRoi.value.roi_w}, h=${editingRoi.value.roi_h}`
    : 'ROI: 未設定';

  return (
    <div class={s.roiDrawer}>
      <p class={s.roiStatus}>{editorMessage.value}</p>
      <div ref={wrapRef} class={s.roiPreviewWrap}>
        <img
          ref={imgRef}
          class={`${s.roiPreviewImg}${imgReady.value ? ' ' + s.roiPreviewImgReady : ''}`}
          alt="ROI preview"
          draggable={false}
          onLoad={() => {
            imgReady.value = true;
          }}
          onError={() => {
            loadError.value = true;
            editorMessage.value = 'プレビューを取得できません。カメラ接続を確認してください。';
          }}
        />
        <span
          ref={boxRef}
          class={s.roiBox}
          style={{ display: 'none' }}
        />
        {!imgReady.value && !loadError.value && (
          <p style={{ color: 'var(--muted)', margin: 0 }}>静止画像を読み込み中...</p>
        )}
        {loadError.value && (
          <p style={{ color: 'var(--stop)', margin: 0 }}>プレビュー取得失敗</p>
        )}
      </div>
      <p class={s.roiStatus}>{roiText}</p>
      <div class={s.roiEditorActions}>
        <button class={s.btnPrimary} type="button" onClick={handleAccept}>
          このROIで決定
        </button>
        <button class={s.btnSecondary} type="button" onClick={handleRedraw}>
          リセット
        </button>
        <button class={s.btnSecondary} type="button" onClick={onReadjustAngle}>
          画角を再調整
        </button>
        <button class={s.btnSecondary} type="button" onClick={onCancel}>
          戻る
        </button>
      </div>
    </div>
  );
}
