import os
import numpy as np
import pandas as pd
from PIL import Image

# ===== 設定 =====
DATASET_DIR = os.environ.get("DATASET_DIR", "inat_lepidoptera_japan")
METADATA_CSV = os.path.join(DATASET_DIR, "metadata.csv")
IMAGE_SIZE = (128, 128)

# 保存先
OUTPUT_X = os.path.join(DATASET_DIR, "X_uint8.npy")
OUTPUT_Y = os.path.join(DATASET_DIR, "y_species.npy")
OUTPUT_LABEL_COUNTS = os.path.join(DATASET_DIR, "label_counts.csv")

print("metadata.csv を読み込みます...")
df = pd.read_csv(METADATA_CSV)

# species_guess があればそれを優先、なければ taxon_name を使う
def choose_label(row):
    sg = row.get("species_guess", None)
    tn = row.get("taxon_name", None)

    if pd.notna(sg) and str(sg).strip() not in ["", "None", "nan"]:
        return str(sg).strip()
    if pd.notna(tn) and str(tn).strip() not in ["", "None", "nan"]:
        return str(tn).strip()
    return None

df["label"] = df.apply(choose_label, axis=1)

# ラベルと画像パスがある行だけ残す
df = df[df["label"].notna()].copy()

# local_path が存在するものだけ使う
df["local_path"] = df["local_path"].astype(str)
df = df[df["local_path"].apply(os.path.exists)].copy()

print(f"使用候補画像数: {len(df)}")

images = []
labels = []

print("画像の読み込み、リサイズ、配列化を開始します...")
for i, row in df.iterrows():
    img_path = row["local_path"]
    label = row["label"]

    try:
        img = Image.open(img_path).convert("RGB")
        img = img.resize(IMAGE_SIZE)
        img_array = np.array(img, dtype=np.uint8)   # まず uint8 で保持
        images.append(img_array)
        labels.append(label)

        if len(images) % 500 == 0:
            print(f"{len(images)} 枚処理済み")
    except Exception as e:
        print(f"画像 {img_path} の処理中にエラー: {e}")

X = np.array(images, dtype=np.uint8)
y_species = np.array(labels, dtype=object)

print("\n前処理完了")
print(f"総画像数: {len(X)}")
print(f"画像 shape: {X.shape}")
print(f"ユニーク種数: {len(np.unique(y_species))}")

# 保存
np.save(OUTPUT_X, X)
np.save(OUTPUT_Y, y_species)

# ラベル数も保存
label_counts = pd.Series(y_species).value_counts()
label_counts.to_csv(OUTPUT_LABEL_COUNTS, header=["count"])

print("\n保存完了")
print(f"X: {OUTPUT_X}")
print(f"y_species: {OUTPUT_Y}")
print(f"label_counts: {OUTPUT_LABEL_COUNTS}")