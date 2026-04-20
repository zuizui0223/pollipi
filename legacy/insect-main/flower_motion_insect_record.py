from ultralytics import YOLO
from pathlib import Path
import cv2
import time
from datetime import datetime
import os

# =========================
# 設定
# =========================

# アザミ花 detector
FLOWER_MODEL_PATH = r"C:\Users\zuizui\mc\runs\cirsium_detect\weights\best.pt"

# 昆虫 detector
# ここは昆虫YOLO detectモデルの best.pt に差し替える
# 例: r"C:\Users\zuizui\mc\runs\insect_detect\weights\best.pt"
INSECT_MODEL_PATH = r"C:\Users\zuizui\mc\runs\insect_detect\weights\best.pt"

# カメラなら 0
# 動画で試すなら r"C:\Users\zuizui\mc\test_video.mp4"
VIDEO_SOURCE = 0

OUTPUT_DIR = Path(r"C:\Users\zuizui\mc\flower_insect_events")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 花検出
FLOWER_CONF_THRES = 0.30
FLOWER_EXPAND_RATIO = 0.20
FLOWER_DETECT_EVERY = 15  # 花ROIを何フレームごとに更新するか

# 背景差分トリガー
MOTION_RATIO_THRES = 0.008   # 0.005〜0.02で調整
MIN_AREA = 80                # 小さいノイズ除去
WARMUP_FRAMES = 30           # 背景モデルの初期学習中はトリガーしない

# 昆虫YOLO
INSECT_CONF_THRES = 0.25
INSECT_DETECT_EVERY = 3       # motion発生中に何フレームごとに昆虫YOLOを呼ぶか
YOLO_ACTIVE_SEC = 2.0         # motion後、何秒YOLOを起こし続けるか

# 録画停止
STOP_AFTER_NO_INSECT_SEC = 2.0

# 保存
SAVE_FPS = 20.0
SHOW_WINDOWS = True

# =========================
# モデル確認
# =========================

if not os.path.exists(FLOWER_MODEL_PATH):
    raise FileNotFoundError(f"花モデルが見つかりません: {FLOWER_MODEL_PATH}")

if not os.path.exists(INSECT_MODEL_PATH):
    raise FileNotFoundError(
        "昆虫モデルが見つかりません。\n"
        f"現在の指定: {INSECT_MODEL_PATH}\n"
        "INSECT_MODEL_PATH を昆虫YOLO detectモデルの best.pt に差し替えてください。"
    )

flower_model = YOLO(FLOWER_MODEL_PATH)
insect_model = YOLO(INSECT_MODEL_PATH)

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
# Raspberry PiではCNTが使えるならCNT推奨。
# まずWindows/通常OpenCVでも動くMOG2で作る。
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

recording = False
writer = None
current_video_path = None

last_motion_time = 0.0
last_insect_time = 0.0
last_insect_dets = []


# =========================
# 関数
# =========================

def detect_flower(frame):
    """
    全画面からアザミ花を検出し、一番confが高い花bboxを返す。
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

    boxes = r.boxes
    confs = boxes.conf.cpu().numpy()
    best_idx = confs.argmax()

    x1, y1, x2, y2 = boxes.xyxy.cpu().numpy()[best_idx].astype(int)
    conf = float(confs[best_idx])

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
        "conf": conf
    }


def calc_motion_in_roi(frame, roi_box):
    """
    花ROI内だけ背景差分する。
    戻り値:
      motion_ratio: 前景ピクセル比
      motion_mask: 表示用マスク
      moving_boxes: 前景ブロブbboxのリスト（ROI座標）
    """
    rx1, ry1, rx2, ry2 = roi_box
    roi = frame[ry1:ry2, rx1:rx2]

    if roi.size == 0:
        return 0.0, None, []

    # 軽量化のため小さくする
    small = cv2.resize(roi, (320, 240))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    fg = back_sub.apply(gray)

    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel_open)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel_close)

    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)

    clean = fg.copy()
    moving_boxes = []

    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]

        if area < MIN_AREA:
            clean[labels == i] = 0
            continue

        x = stats[i, cv2.CC_STAT_LEFT]
        y = stats[i, cv2.CC_STAT_TOP]
        w = stats[i, cv2.CC_STAT_WIDTH]
        h = stats[i, cv2.CC_STAT_HEIGHT]

        moving_boxes.append((x, y, x + w, y + h, area))

    motion_ratio = cv2.countNonZero(clean) / clean.size

    return motion_ratio, clean, moving_boxes


def detect_insects_in_roi(frame, roi_box):
    """
    背景差分でトリガーされたときだけ呼ぶ。
    花ROI内に昆虫YOLOをかけ、bboxを元画像座標に戻す。
    """
    rx1, ry1, rx2, ry2 = roi_box
    roi = frame[ry1:ry2, rx1:rx2]

    if roi.size == 0:
        return []

    results = insect_model.predict(
        source=roi,
        conf=INSECT_CONF_THRES,
        save=False,
        verbose=False
    )

    r = results[0]

    if r.boxes is None or len(r.boxes) == 0:
        return []

    dets = []

    for box in r.boxes:
        x1, y1, x2, y2 = box.xyxy.cpu().numpy()[0].astype(int)
        conf = float(box.conf.cpu().numpy()[0])
        cls_id = int(box.cls.cpu().numpy()[0])

        # ROI座標から全体画像座標へ戻す
        gx1 = rx1 + x1
        gy1 = ry1 + y1
        gx2 = rx1 + x2
        gy2 = ry1 + y2

        dets.append({
            "bbox": (gx1, gy1, gx2, gy2),
            "conf": conf,
            "cls_id": cls_id
        })

    return dets


def start_recording(frame):
    global writer, recording, current_video_path

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_video_path = OUTPUT_DIR / f"insect_event_{timestamp}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(current_video_path),
        fourcc,
        SAVE_FPS,
        (W, H)
    )

    recording = True
    print(f"[START] 昆虫確認。録画開始: {current_video_path}")


def stop_recording():
    global writer, recording, current_video_path

    if writer is not None:
        writer.release()

    print(f"[STOP] 昆虫消失。録画停止: {current_video_path}")

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

    # 1. 花ROIを定期更新
    if frame_count % FLOWER_DETECT_EVERY == 1 or last_flower_det is None:
        det = detect_flower(frame)
        if det is not None:
            last_flower_det = det

    vis = frame.copy()
    motion_ratio = 0.0
    motion_mask = None
    motion_triggered = False
    yolo_active = False

    # 2. 花ROIがある場合だけ背景差分
    if last_flower_det is not None:
        fx1, fy1, fx2, fy2 = last_flower_det["bbox"]
        rx1, ry1, rx2, ry2 = last_flower_det["roi"]
        fconf = last_flower_det["conf"]

        # 花bbox 緑、ROI 赤
        cv2.rectangle(vis, (fx1, fy1), (fx2, fy2), (0, 255, 0), 2)
        cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)

        # 3. ROI内の背景差分
        motion_ratio, motion_mask, moving_boxes = calc_motion_in_roi(frame, last_flower_det["roi"])

        if frame_count > WARMUP_FRAMES and motion_ratio > MOTION_RATIO_THRES:
            motion_triggered = True
            last_motion_time = now

        # motion後、数秒だけYOLO active
        if now - last_motion_time <= YOLO_ACTIVE_SEC:
            yolo_active = True

        # 4. motion trigger時だけ昆虫YOLO
        if yolo_active and frame_count % INSECT_DETECT_EVERY == 1:
            last_insect_dets = detect_insects_in_roi(frame, last_flower_det["roi"])

        # 5. 昆虫YOLOで確認できたら録画開始/継続
        if len(last_insect_dets) > 0:
            last_insect_time = now

            for det in last_insect_dets:
                ix1, iy1, ix2, iy2 = det["bbox"]
                iconf = det["conf"]
                cls_id = det["cls_id"]

                cv2.rectangle(vis, (ix1, iy1), (ix2, iy2), (255, 0, 0), 2)
                cv2.putText(
                    vis,
                    f"insect {cls_id} {iconf:.2f}",
                    (ix1, max(20, iy1 - 8)),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 0, 0),
                    2,
                    cv2.LINE_AA
                )

            if not recording:
                start_recording(vis)

        # 表示情報
        draw_text(vis, f"flower {fconf:.2f}", 30)
        draw_text(vis, f"motion_ratio {motion_ratio:.4f}", 60)
        draw_text(vis, f"motion_trigger {motion_triggered}", 90, (0, 255, 255) if motion_triggered else (180, 180, 180))
        draw_text(vis, f"insect_yolo_active {yolo_active}", 120, (0, 255, 255) if yolo_active else (180, 180, 180))
        draw_text(vis, f"insect_dets {len(last_insect_dets)}", 150, (255, 0, 0) if len(last_insect_dets) > 0 else (180, 180, 180))

    else:
        draw_text(vis, "flower not detected", 30, (0, 0, 255))

    # 6. 録画中なら保存
    if recording and writer is not None:
        writer.write(vis)

        if now - last_insect_time > STOP_AFTER_NO_INSECT_SEC:
            stop_recording()
            last_insect_dets = []

    # 7. 表示
    if SHOW_WINDOWS:
        cv2.imshow("flower motion -> insect YOLO -> record", vis)

        if motion_mask is not None:
            cv2.imshow("motion mask in flower ROI", motion_mask)

        key = cv2.waitKey(1) & 0xFF
        if key == ord("q") or key == 27:
            break


cap.release()

if recording:
    stop_recording()

cv2.destroyAllWindows()
print("終了")