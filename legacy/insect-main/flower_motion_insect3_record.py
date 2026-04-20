from pathlib import Path
from datetime import datetime
import os
import time

import cv2
import numpy as np
from ultralytics import YOLO
from tensorflow import keras


# =========================
# 設定
# =========================

# アザミ花YOLO detector
FLOWER_MODEL_PATH = r"C:\Users\zuizui\mc\runs\cirsium_detect\weights\best.pt"

# 3クラス昆虫 classifier
INSECT3_MODEL_PATH = r"C:\Users\zuizui\mc\insect3_dataset\insect3_classifier.keras"
INSECT3_CLASSES_PATH = r"C:\Users\zuizui\mc\insect3_dataset\classes.npy"

# カメラなら 0
# 動画で試すなら r"C:\Users\zuizui\mc\test_video.mp4"
VIDEO_SOURCE = 0

OUTPUT_DIR = Path(r"C:\Users\zuizui\mc\flower_insect3_events")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# =========================
# アザミ花検出：厳しめ設定
# =========================

# 誤検出が多いので高め
FLOWER_CONF_THRES = 0.65

# ROI拡張幅。広すぎると余計な揺れを拾うので少し控えめ
FLOWER_EXPAND_RATIO = 0.15

# 何フレームごとに花を再検出するか
FLOWER_DETECT_EVERY = 10

# 花を何回連続で見失ったら「花なし」とするか
MAX_FLOWER_MISSING = 3

# 花bboxの面積フィルタ
# 画面全体に対するbbox面積の割合
MIN_FLOWER_AREA_RATIO = 0.002
MAX_FLOWER_AREA_RATIO = 0.25

# 花bboxの縦横比フィルタ
MIN_FLOWER_ASPECT = 0.4
MAX_FLOWER_ASPECT = 2.5

# 何回連続で検出されたら正式に花ROIとして採用するか
FLOWER_STABLE_REQUIRED = 2


# =========================
# 背景差分
# =========================

WARMUP_FRAMES = 30
MOTION_RATIO_THRES = 0.008
MIN_AREA = 80


# =========================
# 昆虫分類
# =========================

CLASSIFIER_IMAGE_SIZE = (128, 128)

# 昆虫分類器の信頼度閾値
# 誤録画が多ければ 0.80〜0.85
# 録画漏れが多ければ 0.65〜0.70
INSECT_CONF_THRES = 0.75

CLASSIFY_EVERY = 3

# motion 後、何秒 classifier を起こし続けるか
CLASSIFIER_ACTIVE_SEC = 2.0


# =========================
# 録画停止
# =========================

STOP_AFTER_NO_INSECT_SEC = 2.0


# =========================
# 保存・表示
# =========================

SAVE_FPS = 20.0
SHOW_WINDOWS = True


# =========================
# モデル読み込み
# =========================

if not os.path.exists(FLOWER_MODEL_PATH):
    raise FileNotFoundError(f"花YOLOモデルがありません: {FLOWER_MODEL_PATH}")

if not os.path.exists(INSECT3_MODEL_PATH):
    raise FileNotFoundError(f"昆虫3クラス分類モデルがありません: {INSECT3_MODEL_PATH}")

if not os.path.exists(INSECT3_CLASSES_PATH):
    raise FileNotFoundError(f"classes.npy がありません: {INSECT3_CLASSES_PATH}")

flower_model = YOLO(FLOWER_MODEL_PATH)
insect_model = keras.models.load_model(INSECT3_MODEL_PATH)
insect_classes = np.load(INSECT3_CLASSES_PATH, allow_pickle=True)

print("昆虫クラス:", insect_classes)


# =========================
# カメラ初期化
# =========================

cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    raise RuntimeError("カメラ/動画を開けませんでした。")

ret, frame = cap.read()
if not ret:
    raise RuntimeError("最初のフレームを読めませんでした。")

H, W = frame.shape[:2]

# 背景差分器
back_sub = cv2.createBackgroundSubtractorMOG2(
    history=120,
    varThreshold=40,
    detectShadows=False
)

kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))


# =========================
# 状態変数
# =========================

frame_count = 0

last_flower_det = None
pending_flower_det = None
flower_stable_count = 0
flower_missing_count = 0

last_motion_time = 0.0
last_insect_time = 0.0

recording = False
writer = None
current_video_path = None

last_pred_label = "none"
last_pred_conf = 0.0
last_crop_box = None


# =========================
# 関数
# =========================

def detect_flower(frame):
    """
    全画面からアザミ花を検出し、
    conf・面積・縦横比の条件を満たす中で一番confが高いbboxを返す。
    """
    results = flower_model.predict(
        source=frame,
        conf=FLOWER_CONF_THRES,
        save=False,
        verbose=False
    )

    r = results[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None

    candidates = []

    for box in r.boxes:
        x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0].astype(int)
        conf = float(box.conf.cpu().numpy()[0])

        bw = max(1, x2 - x1)
        bh = max(1, y2 - y1)

        area_ratio = (bw * bh) / float(W * H)
        aspect = bw / float(bh)

        # 面積フィルタ
        if area_ratio < MIN_FLOWER_AREA_RATIO:
            continue
        if area_ratio > MAX_FLOWER_AREA_RATIO:
            continue

        # 縦横比フィルタ
        if aspect < MIN_FLOWER_ASPECT:
            continue
        if aspect > MAX_FLOWER_ASPECT:
            continue

        candidates.append((conf, x1, y1, x2, y2, area_ratio, aspect))

    if len(candidates) == 0:
        return None

    # conf最大の候補を採用
    candidates.sort(reverse=True, key=lambda z: z[0])
    conf, x1, y1, x2, y2, area_ratio, aspect = candidates[0]

    bw = x2 - x1
    bh = y2 - y1

    pad_x = int(bw * FLOWER_EXPAND_RATIO)
    pad_y = int(bh * FLOWER_EXPAND_RATIO)

    rx1 = max(0, x1 - pad_x)
    ry1 = max(0, y1 - pad_y)
    rx2 = min(W, x2 + pad_x)
    ry2 = min(H, y2 + pad_y)

    return {
        "bbox": (x1, y1, x2, y2),
        "roi": (rx1, ry1, rx2, ry2),
        "conf": conf,
        "area_ratio": area_ratio,
        "aspect": aspect
    }


def reset_insect_state():
    global last_pred_label, last_pred_conf, last_crop_box
    last_pred_label = "none"
    last_pred_conf = 0.0
    last_crop_box = None


def calc_motion_in_roi(frame, roi_box):
    """
    ROI内の背景差分を計算し、動いたブロブを元画像座標で返す。
    """
    rx1, ry1, rx2, ry2 = roi_box
    roi = frame[ry1:ry2, rx1:rx2]

    if roi.size == 0:
        return 0.0, None, []

    roi_h, roi_w = roi.shape[:2]

    small_w, small_h = 320, 240
    small = cv2.resize(roi, (small_w, small_h))

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    fg = back_sub.apply(gray)

    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel_open)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel_close)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)

    clean = fg.copy()
    moving_boxes_global = []

    scale_x = roi_w / small_w
    scale_y = roi_h / small_h

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]

        if area < MIN_AREA:
            clean[labels == i] = 0
            continue

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        # small座標 → ROI座標 → 全体画像座標
        gx1 = int(rx1 + x * scale_x)
        gy1 = int(ry1 + y * scale_y)
        gx2 = int(rx1 + (x + w) * scale_x)
        gy2 = int(ry1 + (y + h) * scale_y)

        moving_boxes_global.append((gx1, gy1, gx2, gy2, int(area)))

    motion_ratio = cv2.countNonZero(clean) / clean.size
    return motion_ratio, clean, moving_boxes_global


def expand_box(box, ratio=0.7):
    """
    動いた領域を少し広げて crop する。
    """
    x1, y1, x2, y2, area = box

    bw = x2 - x1
    bh = y2 - y1

    pad_x = int(bw * ratio)
    pad_y = int(bh * ratio)

    nx1 = max(0, x1 - pad_x)
    ny1 = max(0, y1 - pad_y)
    nx2 = min(W, x2 + pad_x)
    ny2 = min(H, y2 + pad_y)

    return nx1, ny1, nx2, ny2


def classify_crop(frame, crop_box):
    """
    crop画像を3クラス分類する。
    """
    x1, y1, x2, y2 = crop_box
    crop = frame[y1:y2, x1:x2]

    if crop.size == 0:
        return "none", 0.0

    crop_rgb = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
    crop_resized = cv2.resize(crop_rgb, CLASSIFIER_IMAGE_SIZE)

    x = crop_resized.astype("float32") / 255.0
    x = np.expand_dims(x, axis=0)

    pred = insect_model.predict(x, verbose=0)[0]

    cls_id = int(np.argmax(pred))
    conf = float(np.max(pred))
    label = str(insect_classes[cls_id])

    return label, conf


def start_recording(vis_frame):
    global writer, recording, current_video_path

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_video_path = OUTPUT_DIR / f"insect3_event_{timestamp}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(current_video_path),
        fourcc,
        SAVE_FPS,
        (W, H)
    )

    recording = True
    print(f"[START] {last_pred_label} {last_pred_conf:.2f} 録画開始: {current_video_path}")


def stop_recording(reason=""):
    global writer, recording, current_video_path

    if writer is not None:
        writer.release()

    print(f"[STOP] 録画停止: {current_video_path} {reason}")

    writer = None
    recording = False
    current_video_path = None


def draw_text(vis, text, y, color=(255, 255, 255)):
    cv2.putText(
        vis,
        text,
        (20, y),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.75,
        color,
        2,
        cv2.LINE_AA
    )


# =========================
# メインループ
# =========================

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    now = time.time()

    vis = frame.copy()

    # =========================
    # 1. 花検出を定期更新
    # =========================

    if frame_count % FLOWER_DETECT_EVERY == 1 or last_flower_det is None:
        det = detect_flower(frame)

        if det is not None:
            pending_flower_det = det
            flower_stable_count += 1
            flower_missing_count = 0

            # 連続して検出されたら正式採用
            if flower_stable_count >= FLOWER_STABLE_REQUIRED:
                last_flower_det = pending_flower_det

        else:
            flower_missing_count += 1
            flower_stable_count = 0
            pending_flower_det = None

            # 花を連続で見失ったら、花なし扱い
            if flower_missing_count >= MAX_FLOWER_MISSING:
                last_flower_det = None
                reset_insect_state()

                if recording:
                    stop_recording(reason="[flower lost]")

    # =========================
    # 2. 花がないなら全部スキップ
    # =========================

    if last_flower_det is None:
        draw_text(vis, "flower not detected: recording disabled", 30, (0, 0, 255))

        if recording:
            stop_recording(reason="[no flower]")

        if SHOW_WINDOWS:
            cv2.imshow("flower motion -> insect3 classifier -> record", vis)
            key = cv2.waitKey(1) & 0xFF
            if key == ord("q") or key == 27:
                break

        continue

    # =========================
    # 3. 花がある場合だけ ROI処理
    # =========================

    motion_ratio = 0.0
    motion_mask = None
    moving_boxes = []

    motion_triggered = False
    classifier_active = False
    insect_confirmed = False

    fx1, fy1, fx2, fy2 = last_flower_det["bbox"]
    rx1, ry1, rx2, ry2 = last_flower_det["roi"]
    fconf = last_flower_det["conf"]
    farea = last_flower_det.get("area_ratio", 0.0)
    faspect = last_flower_det.get("aspect", 0.0)

    # 花bbox: 緑、ROI: 赤
    cv2.rectangle(vis, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
    cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)

    # =========================
    # 4. ROI内背景差分
    # =========================

    motion_ratio, motion_mask, moving_boxes = calc_motion_in_roi(frame, last_flower_det["roi"])

    if frame_count > WARMUP_FRAMES and motion_ratio > MOTION_RATIO_THRES and len(moving_boxes) > 0:
        motion_triggered = True
        last_motion_time = now

    # motion 後、一定時間 classifier を有効化
    if now - last_motion_time <= CLASSIFIER_ACTIVE_SEC:
        classifier_active = True

    # classifier が非アクティブなら予測を古くしすぎない
    if not classifier_active and not recording:
        reset_insect_state()

    # =========================
    # 5. classifier active のときだけ昆虫分類
    # =========================

    if classifier_active and frame_count % CLASSIFY_EVERY == 1 and len(moving_boxes) > 0:
        biggest = max(moving_boxes, key=lambda b: b[4])
        crop_box = expand_box(biggest, ratio=0.7)
        last_crop_box = crop_box

        label, conf = classify_crop(frame, crop_box)
        last_pred_label = label
        last_pred_conf = conf

    # =========================
    # 6. 高信頼度なら昆虫確認 → 録画開始
    # =========================

    if last_pred_conf >= INSECT_CONF_THRES:
        insect_confirmed = True
        last_insect_time = now

        if not recording:
            start_recording(vis)

    # =========================
    # 7. 描画
    # =========================

    # 動体ブロブ: 黄色
    for mb in moving_boxes:
        mx1, my1, mx2, my2, area = mb
        cv2.rectangle(vis, (mx1, my1), (mx2, my2), (0, 255, 255), 1)

    # 分類crop: 青
    if last_crop_box is not None:
        cx1, cy1, cx2, cy2 = last_crop_box
        cv2.rectangle(vis, (cx1, cy1), (cx2, cy2), (255, 0, 0), 2)

    draw_text(vis, f"flower {fconf:.2f} area {farea:.3f} asp {faspect:.2f}", 30)
    draw_text(vis, f"motion_ratio {motion_ratio:.4f}", 60)
    draw_text(
        vis,
        f"motion_trigger {motion_triggered}",
        90,
        (0, 255, 255) if motion_triggered else (180, 180, 180)
    )
    draw_text(
        vis,
        f"classifier_active {classifier_active}",
        120,
        (0, 255, 255) if classifier_active else (180, 180, 180)
    )
    draw_text(
        vis,
        f"pred {last_pred_label} {last_pred_conf:.2f}",
        150,
        (255, 0, 0) if insect_confirmed else (180, 180, 180)
    )
    draw_text(
        vis,
        f"recording {recording}",
        180,
        (0, 0, 255) if recording else (180, 180, 180)
    )

    # =========================
    # 8. 録画中なら書き込み、昆虫判定が消えたら停止
    # =========================

    if recording and writer is not None:
        writer.write(vis)

        if now - last_insect_time > STOP_AFTER_NO_INSECT_SEC:
            stop_recording(reason="[no insect]")
            reset_insect_state()

    # =========================
    # 9. 表示
    # =========================

    if SHOW_WINDOWS:
        cv2.imshow("flower motion -> insect3 classifier -> record", vis)

        if motion_mask is not None:
            cv2.imshow("motion mask in ROI", motion_mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break


# =========================
# 終了処理
# =========================

cap.release()

if recording:
    stop_recording(reason="[program end]")

cv2.destroyAllWindows()
print("終了")