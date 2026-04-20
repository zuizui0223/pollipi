import os
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import LabelEncoder

# ===== 設定 =====
DATASET_DIR = os.environ.get("DATASET_DIR", "inat_lepidoptera_japan")
X_PATH = os.path.join(DATASET_DIR, "X_uint8.npy")
Y_PATH = os.path.join(DATASET_DIR, "y_species.npy")

TEST_SIZE = 0.5
RANDOM_STATE = 42

# 保存先
X_TRAIN_PATH = os.path.join(DATASET_DIR, "X_train_uint8.npy")
X_TEST_PATH = os.path.join(DATASET_DIR, "X_test_uint8.npy")
Y_TRAIN_PATH = os.path.join(DATASET_DIR, "y_train.npy")
Y_TEST_PATH = os.path.join(DATASET_DIR, "y_test.npy")
CLASSES_PATH = os.path.join(DATASET_DIR, "classes.npy")

print("前処理済みデータを読み込みます...")
X = np.load(X_PATH)
y_species = np.load(Y_PATH, allow_pickle=True)

print(f"元の総画像数: {len(X)}")
print(f"元の画像形状: {X.shape[1:]}")
print(f"元のユニーク種数: {len(np.unique(y_species))}")

# ラベルを文字列として統一
y_species = np.array([str(v).strip() for v in y_species], dtype=object)

# クラスごとのサンプル数を数える
unique_labels, counts = np.unique(y_species, return_counts=True)

# サンプル数が2未満のクラスを除外
valid_labels = set(unique_labels[counts >= 2])
filtered_indices = [i for i, label in enumerate(y_species) if label in valid_labels]

# 初期化
X_filtered = np.array([], dtype=np.uint8)
y_filtered_species = np.array([], dtype=object)
y_filtered = np.array([], dtype=np.int64)
label_encoder = None
num_classes = 0

X_train = np.array([], dtype=np.uint8)
X_test = np.array([], dtype=np.uint8)
y_train = np.array([], dtype=np.int64)
y_test = np.array([], dtype=np.int64)

if len(filtered_indices) == 0:
    print("訓練/テスト分割に必要な十分なサンプルを持つクラスがありません。")
else:
    X_filtered = X[filtered_indices]
    y_filtered_species = y_species[filtered_indices]

    # 文字列ラベルを 0,1,2,... に変換
    label_encoder = LabelEncoder()
    y_filtered = label_encoder.fit_transform(y_filtered_species)
    num_classes = len(label_encoder.classes_)

    # stratify 付きで分割
    X_train, X_test, y_train, y_test = train_test_split(
        X_filtered,
        y_filtered,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=y_filtered
    )

    # 保存
    np.save(X_TRAIN_PATH, X_train)
    np.save(X_TEST_PATH, X_test)
    np.save(Y_TRAIN_PATH, y_train)
    np.save(Y_TEST_PATH, y_test)
    np.save(CLASSES_PATH, label_encoder.classes_)

print("\nデータセットの準備が完了しました。")
print(f"フィルタ後の総画像数: {len(X_filtered)}")
print(f"画像の形状: {X_filtered.shape[1:] if X_filtered.size > 0 else 'N/A'}")
print(f"クラス数: {num_classes}")
print(f"訓練データ数: {len(X_train)}")
print(f"テストデータ数: {len(X_test)}")

if label_encoder is not None:
    print("\n先頭20クラスだけ表示します:")
    for i, class_name in enumerate(label_encoder.classes_[:20]):
        print(f"  {i}: {class_name}")
    if len(label_encoder.classes_) > 20:
        print(f"... and {len(label_encoder.classes_) - 20} more classes")

    print("\n保存完了:")
    print(f"  {X_TRAIN_PATH}")
    print(f"  {X_TEST_PATH}")
    print(f"  {Y_TRAIN_PATH}")
    print(f"  {Y_TEST_PATH}")
    print(f"  {CLASSES_PATH}")