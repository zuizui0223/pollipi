from ultralytics import YOLO
from pathlib import Path
import cv2

# ===== 設定 =====
MODEL_PATH = r"C:\Users\zuizui\mc\runs\cirsium_detect\weights\best.pt"
SOURCE_IMAGE = r"C:\Users\zuizui\mc\cirsium_all\obs_100046009_photo_166931553.jpg"
OUTPUT_DIR = Path(r"C:\Users\zuizui\mc\roi_test")

CONF_THRES = 0.25
EXPAND_RATIO = 0.30   # bbox を 30% 広げる

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

model = YOLO(MODEL_PATH)

# 推論
results = model.predict(
    source=SOURCE_IMAGE,
    conf=CONF_THRES,
    save=False,
    verbose=False
)

result = results[0]
img = cv2.imread(SOURCE_IMAGE)
h, w = img.shape[:2]

if result.boxes is None or len(result.boxes) == 0:
    print("花が検出されませんでした。")
    raise SystemExit

# 一番信頼度の高い bbox を使う
boxes = result.boxes
confs = boxes.conf.cpu().numpy()
best_idx = confs.argmax()

xyxy = boxes.xyxy.cpu().numpy()[best_idx]
x1, y1, x2, y2 = xyxy.astype(int)

# bbox を少し広げる
bw = x2 - x1
bh = y2 - y1

pad_x = int(bw * EXPAND_RATIO)
pad_y = int(bh * EXPAND_RATIO)

rx1 = max(0, x1 - pad_x)
ry1 = max(0, y1 - pad_y)
rx2 = min(w, x2 + pad_x)
ry2 = min(h, y2 + pad_y)

roi = img[ry1:ry2, rx1:rx2].copy()

# 元画像に bbox と ROI 枠を描く
vis = img.copy()
cv2.rectangle(vis, (x1, y1), (x2, y2), (0, 255, 0), 2)      # 元の bbox
cv2.rectangle(vis, (rx1, ry1), (rx2, ry2), (0, 0, 255), 2)  # 拡張 ROI

# 保存
boxed_path = OUTPUT_DIR / "flower_detected.jpg"
roi_path = OUTPUT_DIR / "flower_roi.jpg"

cv2.imwrite(str(boxed_path), vis)
cv2.imwrite(str(roi_path), roi)

print(f"検出画像を保存: {boxed_path}")
print(f"ROI画像を保存: {roi_path}")
print(f"bbox: {(x1, y1, x2, y2)}")
print(f"roi : {(rx1, ry1, rx2, ry2)}")