import os
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# ===== 設定 =====
DATASET_DIR = os.environ.get("DATASET_DIR", "inat_lepidoptera_japan")
X_TRAIN_PATH = os.path.join(DATASET_DIR, "X_train_uint8.npy")
X_TEST_PATH = os.path.join(DATASET_DIR, "X_test_uint8.npy")
Y_TRAIN_PATH = os.path.join(DATASET_DIR, "y_train.npy")
Y_TEST_PATH = os.path.join(DATASET_DIR, "y_test.npy")

BATCH_SIZE = 32

print("分割済みデータを読み込みます...")
X_train = np.load(X_TRAIN_PATH)
X_test = np.load(X_TEST_PATH)
y_train = np.load(Y_TRAIN_PATH)
y_test = np.load(Y_TEST_PATH)

print(f"X_train shape (raw): {X_train.shape}")
print(f"X_test shape (raw): {X_test.shape}")
print(f"y_train shape: {y_train.shape}")
print(f"y_test shape: {y_test.shape}")

# uint8 -> float32, 0-1 正規化
X_train = X_train.astype("float32") / 255.0
X_test = X_test.astype("float32") / 255.0

print("\n正規化後:")
print(f"X_train dtype: {X_train.dtype}, min={X_train.min():.3f}, max={X_train.max():.3f}")
print(f"X_test dtype: {X_test.dtype}, min={X_test.min():.3f}, max={X_test.max():.3f}")

# データ拡張
datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode='nearest'
)

# ジェネレータ作成
train_generator = datagen.flow(
    X_train,
    y_train,
    batch_size=BATCH_SIZE,
    shuffle=True
)

print("\nデータ拡張ジェネレータが設定されました。")
print(f"train_generator batch_size: {train_generator.batch_size}")
print(f"1エポックあたりのステップ数: {len(train_generator)}")

# 動作確認として1バッチ取り出す
X_batch, y_batch = next(train_generator)
print("\nサンプルバッチ確認:")
print(f"X_batch shape: {X_batch.shape}")
print(f"y_batch shape: {y_batch.shape}")
print(f"X_batch dtype: {X_batch.dtype}")
print(f"X_batch min/max: {X_batch.min():.3f} / {X_batch.max():.3f}")

print("\nテストデータは拡張せず、そのまま使います。")
print(f"X_test shape: {X_test.shape}")
print(f"y_test shape: {y_test.shape}")