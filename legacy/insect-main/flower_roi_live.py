from ultralytics import YOLO
import cv2
import time

# ===== 設定 =====
MODEL_PATH = r"C:\Users\zuizui\mc\runs\cirsium_detect\weights\best.pt"
VIDEO_SOURCE = 0   # USBカメラなら0, 動画ファイルならパス文字列
CONF_THRES = 0.25
EXPAND_RATIO = 0.15
DETECT_EVERY = 10   # 10フレームごとに花再検出
SHOW_FPS = True

model = YOLO(MODEL_PATH)
cap = cv2.VideoCapture(VIDEO_SOURCE)

if not cap.isOpened():
    raise RuntimeError("カメラ/動画を開けませんでした。")

last_roi = None
frame_count = 0
prev_time = time.time()

def detect_best_flower(frame):
    results = model.predict(source=frame, conf=CONF_THRES, save=False, verbose=False)
    r = results[0]
    if r.boxes is None or len(r.boxes) == 0:
        return None

    boxes = r.boxes
    confs = boxes.conf.cpu().numpy()
    best_idx = confs.argmax()
    x1, y1, x2, y2 = boxes.xyxy.cpu().numpy()[best_idx].astype(int)

    h, w = frame.shape[:2]
    bw = x2 - x1
    bh = y2 - y1
    pad_x = int(bw * EXPAND_RATIO)
    pad_y = int(bh * EXPAND_RATIO)

    rx1 = max(0, x1 - pad_x)
    ry1 = max(0, y1 - pad_y)
    rx2 = min(w, x2 + pad_x)
    ry2 = min(h, y2 + pad_y)

    return {
        "bbox": (x1, y1, x2, y2),
        "roi": (rx1, ry1, rx2, ry2),
        "conf": float(confs[best_idx]),
    }

while True:
    ret, frame = cap.read()
    if not ret:
        break

    frame_count += 1

    if frame_count % DETECT_EVERY == 1 or last_roi is None:
        det = detect_best_flower(frame)
        if det is not None:
            last_roi = det

    vis = frame.copy()

    if last_roi is not None:
        x1, y1, x2, y2 = last_roi["bbox"]
        rx1, ry1, rx2, ry2 = last_roi["roi"]
        conf = last_roi["conf"]

        cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)
        cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)
        cv2.putText(
            vis,
            f"flower {conf:.2f}",
            (x1, max(20, y1 - 8)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 0),
            2,
            cv2.LINE_AA,
        )

    if SHOW_FPS:
        now = time.time()
        fps = 1.0 / max(now - prev_time, 1e-6)
        prev_time = now
        cv2.putText(
            vis,
            f"FPS: {fps:.1f}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (255, 255, 255),
            2,
            cv2.LINE_AA,
        )

    cv2.imshow("flower roi live", vis)

    key = cv2.waitKey(1) & 0xFF
    if key == 27 or key == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()