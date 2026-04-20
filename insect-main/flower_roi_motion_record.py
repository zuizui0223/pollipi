from ultralytics import YOLO
from pathlib import Path
import cv2
import time
from datetime import datetime

# ===== 設定 =====
MODEL_PATH = r"C:\Users\zuizui\mc\runs\cirsium_detect\weights\best.pt"

# 0 = PCのカメラ
# 動画で試すなら r"C:\Users\zuizui\mc\test_video.mp4" みたいに変える
VIDEO_SOURCE = 0

OUTPUT_DIR = Path(r"C:\Users\zuizui\mc\flower_events")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

CONF_THRES = 0.30
EXPAND_RATIO = 0.20

# 花検出は毎フレームではなく、何フレームごとにやるか
DETECT_EVERY = 10

# ROI内の動き検出パラメータ
MOTION_RATIO_THRES = 0.008   # 小さいほど敏感。0.005〜0.02くらいで調整
MIN_AREA = 80                # 小さいノイズ除去

# 録画停止までの猶予
STOP_AFTER_NO_MOTION_SEC = 2.0

# 録画FPS
SAVE_FPS = 20.0

# ===== 初期化 =====
model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    raise RuntimeError("カメラ/動画を開けませんでした。")

ret, frame = cap.read()
if not ret:
    raise RuntimeError("最初のフレームを読めませんでした。")

H, W = frame.shape[:2]

# 背景差分器：まずはOpenCV標準のMOG2
back_sub = cv2.createBackgroundSubtractorMOG2(
    history=120,
    varThreshold=40,
    detectShadows=False
)

last_det = None
frame_count = 0

recording = False
writer = None
last_motion_time = 0
current_video_path = None

kernel_open = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
kernel_close = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (11, 11))


def detect_flower(frame):
    results = model.predict(
        source=frame,
        conf=CONF_THRES,
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

    pad_x = int(bw * EXPAND_RATIO)
    pad_y = int(bh * EXPAND_RATIO)

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
    rx1, ry1, rx2, ry2 = roi_box
    roi = frame[ry1:ry2, rx1:rx2]

    if roi.size == 0:
        return 0.0, None

    small = cv2.resize(roi, (320, 240))
    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)

    fg = back_sub.apply(gray)

    fg = cv2.morphologyEx(fg, cv2.MORPH_OPEN, kernel_open)
    fg = cv2.morphologyEx(fg, cv2.MORPH_CLOSE, kernel_close)

    # 小さい連結成分を除去
    num_labels, labels, stats, _ = cv2.connectedComponentsWithStats(fg, connectivity=8)
    clean = fg.copy()
    for i in range(1, num_labels):
        area = stats[i, cv2.CC_STAT_AREA]
        if area < MIN_AREA:
            clean[labels == i] = 0

    motion_ratio = cv2.countNonZero(clean) / clean.size
    return motion_ratio, clean


def start_recording(frame):
    global writer, recording, current_video_path

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    current_video_path = OUTPUT_DIR / f"flower_event_{timestamp}.mp4"

    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(
        str(current_video_path),
        fourcc,
        SAVE_FPS,
        (W, H)
    )

    recording = True
    print(f"[START] 録画開始: {current_video_path}")


def stop_recording():
    global writer, recording, current_video_path

    if writer is not None:
        writer.release()

    print(f"[STOP] 録画停止: {current_video_path}")

    writer = None
    recording = False
    current_video_path = None


while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1
    now = time.time()

    # 花を定期的に再検出
    if frame_count % DETECT_EVERY == 1 or last_det is None:
        det = detect_flower(frame)
        if det is not None:
            last_det = det

    vis = frame.copy()
    motion_ratio = 0.0
    motion_mask = None

    if last_det is not None:
        x1, y1, x2, y2 = last_det["bbox"]
        rx1, ry1, rx2, ry2 = last_det["roi"]
        conf = last_det["conf"]

        motion_ratio, motion_mask = calc_motion_in_roi(frame, last_det["roi"])

        # 枠描画
        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)

        cv2.putText(
            vis,
            f"flower {conf:.2f} motion {motion_ratio:.4f}",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA
        )

        # 動きがあれば録画開始/継続
        if motion_ratio > MOTION_RATIO_THRES:
            last_motion_time = now
            if not recording:
                start_recording(frame)

    else:
        cv2.putText(
            vis,
            "flower not detected",
            (20, 35),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 0, 255),
            2,
            cv2.LINE_AA
        )

    # 録画中なら保存
    if recording and writer is not None:
        writer.write(vis)

        # 一定時間動きがなければ停止
        if now - last_motion_time > STOP_AFTER_NO_MOTION_SEC:
            stop_recording()

    cv2.imshow("flower ROI motion recorder", vis)

    if motion_mask is not None:
        cv2.imshow("motion mask in ROI", motion_mask)

    key = cv2.waitKey(1) & 0xFF
    if key == ord("q") or key == 27:
        break

cap.release()

if recording:
    stop_recording()

cv2.destroyAllWindows()
print("終了")