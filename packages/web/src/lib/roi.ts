export const MONITOR_WIDTH = 640;
export const MONITOR_HEIGHT = 360;
export const MIN_ROI_SIZE = 8;

export interface RoiRect {
  roi_x: number;
  roi_y: number;
  roi_w: number;
  roi_h: number;
}

export interface DisplayRect {
  left: number;
  top: number;
  width: number;
  height: number;
}

export interface DragPoint {
  x: number;
  y: number;
  width: number;
  height: number;
}

export type DragMode =
  | { type: 'draw' }
  | { type: 'move' }
  | { type: 'resize'; left: boolean; right: boolean; top: boolean; bottom: boolean };

export function clamp(value: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, value));
}

export function normalizeRoi(rawRoi: Partial<RoiRect> | null | undefined): RoiRect | null {
  if (!rawRoi) return null;
  let x = Math.round(Number(rawRoi.roi_x));
  let y = Math.round(Number(rawRoi.roi_y));
  let w = Math.round(Number(rawRoi.roi_w));
  let h = Math.round(Number(rawRoi.roi_h));
  if (![x, y, w, h].every(Number.isFinite) || w <= 0 || h <= 0) return null;
  x = clamp(x, 0, MONITOR_WIDTH - 1);
  y = clamp(y, 0, MONITOR_HEIGHT - 1);
  w = clamp(w, 1, MONITOR_WIDTH - x);
  h = clamp(h, 1, MONITOR_HEIGHT - y);
  return { roi_x: x, roi_y: y, roi_w: w, roi_h: h };
}

export function defaultCenteredRoi(): RoiRect {
  const roi_w = 240;
  const roi_h = 160;
  return {
    roi_x: Math.round((MONITOR_WIDTH - roi_w) / 2),
    roi_y: Math.round((MONITOR_HEIGHT - roi_h) / 2),
    roi_w,
    roi_h,
  };
}

export function pointInImage(
  event: MouseEvent | TouchEvent | PointerEvent,
  image: HTMLElement,
): DragPoint | null {
  const rect = image.getBoundingClientRect();
  const source =
    'touches' in event
      ? event.touches[0] || event.changedTouches[0]
      : (event as MouseEvent | PointerEvent);
  if (!source || rect.width <= 0 || rect.height <= 0) return null;
  return {
    x: clamp((source as { clientX: number }).clientX - rect.left, 0, rect.width),
    y: clamp((source as { clientY: number }).clientY - rect.top, 0, rect.height),
    width: rect.width,
    height: rect.height,
  };
}

export function displayRectToRoi(start: DragPoint, end: DragPoint): RoiRect | null {
  const left = Math.min(start.x, end.x);
  const top = Math.min(start.y, end.y);
  const width = Math.abs(end.x - start.x);
  const height = Math.abs(end.y - start.y);
  if (width < MIN_ROI_SIZE || height < MIN_ROI_SIZE) return null;
  return normalizeRoi({
    roi_x: Math.round((left * MONITOR_WIDTH) / start.width),
    roi_y: Math.round((top * MONITOR_HEIGHT) / start.height),
    roi_w: Math.round((width * MONITOR_WIDTH) / start.width),
    roi_h: Math.round((height * MONITOR_HEIGHT) / start.height),
  });
}

export function roiToDisplayRect(roi: RoiRect | null, imageEl: HTMLElement): DisplayRect | null {
  const normalized = normalizeRoi(roi);
  if (!normalized) return null;
  const imageRect = imageEl.getBoundingClientRect();
  if (imageRect.width <= 0 || imageRect.height <= 0) return null;
  return {
    left: (normalized.roi_x * imageRect.width) / MONITOR_WIDTH,
    top: (normalized.roi_y * imageRect.height) / MONITOR_HEIGHT,
    width: (normalized.roi_w * imageRect.width) / MONITOR_WIDTH,
    height: (normalized.roi_h * imageRect.height) / MONITOR_HEIGHT,
  };
}

export function displayRectToRoiRect(
  rect: DisplayRect | null,
  displayWidth: number,
  displayHeight: number,
): RoiRect | null {
  if (!rect || rect.width < MIN_ROI_SIZE || rect.height < MIN_ROI_SIZE) return null;
  return normalizeRoi({
    roi_x: Math.round((rect.left * MONITOR_WIDTH) / displayWidth),
    roi_y: Math.round((rect.top * MONITOR_HEIGHT) / displayHeight),
    roi_w: Math.round((rect.width * MONITOR_WIDTH) / displayWidth),
    roi_h: Math.round((rect.height * MONITOR_HEIGHT) / displayHeight),
  });
}

export function getRoiDragMode(point: DragPoint, rect: DisplayRect | null): DragMode {
  if (!rect) return { type: 'draw' };
  const handle = 18;
  const insideX = point.x >= rect.left && point.x <= rect.left + rect.width;
  const insideY = point.y >= rect.top && point.y <= rect.top + rect.height;
  if (!insideX || !insideY) return { type: 'draw' };
  const nearLeft = Math.abs(point.x - rect.left) <= handle;
  const nearRight = Math.abs(point.x - (rect.left + rect.width)) <= handle;
  const nearTop = Math.abs(point.y - rect.top) <= handle;
  const nearBottom = Math.abs(point.y - (rect.top + rect.height)) <= handle;
  if (nearLeft || nearRight || nearTop || nearBottom) {
    return { type: 'resize', left: nearLeft, right: nearRight, top: nearTop, bottom: nearBottom };
  }
  return { type: 'move' };
}

export function clampDisplayRoiRect(
  rect: DisplayRect,
  displayWidth: number,
  displayHeight: number,
): DisplayRect {
  const width = clamp(rect.width, MIN_ROI_SIZE, displayWidth);
  const height = clamp(rect.height, MIN_ROI_SIZE, displayHeight);
  return {
    left: clamp(rect.left, 0, displayWidth - width),
    top: clamp(rect.top, 0, displayHeight - height),
    width,
    height,
  };
}

export function updateDisplayRoiRect(
  mode: DragMode,
  baseRect: DisplayRect,
  start: DragPoint,
  point: DragPoint,
): DisplayRect {
  const dx = point.x - start.x;
  const dy = point.y - start.y;
  let next = { ...baseRect };
  if (mode.type === 'move') {
    next.left += dx;
    next.top += dy;
  } else if (mode.type === 'resize') {
    if (mode.left) {
      next.left = baseRect.left + dx;
      next.width = baseRect.width - dx;
    }
    if (mode.right) next.width = baseRect.width + dx;
    if (mode.top) {
      next.top = baseRect.top + dy;
      next.height = baseRect.height - dy;
    }
    if (mode.bottom) next.height = baseRect.height + dy;
  }
  if (next.width < 0) {
    next.left += next.width;
    next.width = Math.abs(next.width);
  }
  if (next.height < 0) {
    next.top += next.height;
    next.height = Math.abs(next.height);
  }
  return clampDisplayRoiRect(next, point.width, point.height);
}
