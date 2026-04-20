import os
import numpy as np
from sklearn.model_selection import train_test_split

# ===== 設定 =====
SEED = 42
TEST_SIZE = 0.2

# 各クラスの枚数を揃える
# Noneなら一番少ないクラスに合わせる
# 例: 5000 にすると最大5000枚
MAX_PER_CLASS = None

SOURCE = {
    "lepidoptera": r"C:\Users\zuizui\mc\inat_lepidoptera_japan\X_uint8.npy",
    "hymenoptera": r"C:\Users\zuizui\mc\inat_hymenoptera_japan\X_uint8.npy",
    "diptera": r"C:\Users\zuizui\mc\inat_diptera_japan\X_uint8.npy",
}

OUTPUT_DIR = r"C:\Users\zuizui\mc\insect3_dataset"
os.makedirs(OUTPUT_DIR, exist_ok=True)

rng = np.random.default_rng(SEED)

class_names = list(SOURCE.keys())
counts = {}

print("データを読み込みます...")

for class_name, path in SOURCE.items():
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{class_name} の X_uint8.npy がありません:\n{path}\n"
            "先に local_preprocess.py でその分類群の X_uint8.npy を作ってください。"
        )

    X = np.load(path)
    counts[class_name] = len(X)
    print(f"{class_name}: {len(X)} 枚")

min_count = min(counts.values())

if MAX_PER_CLASS is None:
    target_n = min_count
else:
    target_n = min(min_count, MAX_PER_CLASS)

print(f"\n各クラスから使う枚数: {target_n}")

Xs = []
ys = []

for class_idx, class_name in enumerate(class_names):
    X = np.load(SOURCE[class_name])

    idx = rng.choice(len(X), size=target_n, replace=False)
    X_sub = X[idx]
    y_sub = np.full(target_n, class_idx, dtype=np.int64)

    Xs.append(X_sub)
    ys.append(y_sub)

X_all = np.concatenate(Xs, axis=0)
y_all = np.concatenate(ys, axis=0)

perm = rng.permutation(len(X_all))
X_all = X_all[perm]
y_all = y_all[perm]

X_train, X_test, y_train, y_test = train_test_split(
    X_all,
    y_all,
    test_size=TEST_SIZE,
    random_state=SEED,
    stratify=y_all
)

np.save(os.path.join(OUTPUT_DIR, "X_train_uint8.npy"), X_train)
np.save(os.path.join(OUTPUT_DIR, "X_test_uint8.npy"), X_test)
np.save(os.path.join(OUTPUT_DIR, "y_train.npy"), y_train)
np.save(os.path.join(OUTPUT_DIR, "y_test.npy"), y_test)
np.save(os.path.join(OUTPUT_DIR, "classes.npy"), np.array(class_names, dtype=object))

with open(os.path.join(OUTPUT_DIR, "class_counts.txt"), "w", encoding="utf-8") as f:
    f.write("Original counts\n")
    for k, v in counts.items():
        f.write(f"{k}\t{v}\n")
    f.write(f"\nUsed per class\t{target_n}\n")
    f.write(f"Train\t{len(X_train)}\n")
    f.write(f"Test\t{len(X_test)}\n")

print("\n完了")
print(f"X_train: {X_train.shape}")
print(f"X_test : {X_test.shape}")
print(f"classes: {class_names}")
print(f"保存先: {OUTPUT_DIR}")