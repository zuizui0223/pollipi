import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# ===== 設定 =====
DATASET_DIR = os.environ.get("DATASET_DIR", "inat_lepidoptera_japan")
MODEL_STEM = os.environ.get("MODEL_STEM", "cnn_lepidoptera")

IMAGE_SIZE = (128, 128)
BATCH_SIZE = 32
EPOCHS = 30

MODEL_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}.keras")

# ===== データ読み込み =====
X_TRAIN_PATH = os.path.join(DATASET_DIR, "X_train_uint8.npy")
X_TEST_PATH = os.path.join(DATASET_DIR, "X_test_uint8.npy")
Y_TRAIN_PATH = os.path.join(DATASET_DIR, "y_train.npy")
Y_TEST_PATH = os.path.join(DATASET_DIR, "y_test.npy")
CLASSES_PATH = os.path.join(DATASET_DIR, "classes.npy")

print("分割済みデータを読み込みます...")
X_train = np.load(X_TRAIN_PATH)
X_test = np.load(X_TEST_PATH)
y_train = np.load(Y_TRAIN_PATH)
y_test = np.load(Y_TEST_PATH)
classes = np.load(CLASSES_PATH, allow_pickle=True)

print(f"X_train shape (raw): {X_train.shape}")
print(f"X_test shape (raw): {X_test.shape}")
print(f"y_train shape: {y_train.shape}")
print(f"y_test shape: {y_test.shape}")

# ===== 正規化 =====
X_train = X_train.astype("float32") / 255.0
X_test = X_test.astype("float32") / 255.0

num_classes = len(classes)

if num_classes == 0 or len(X_train) == 0 or len(y_train) == 0:
    print("訓練データが不足しているため、モデルを訓練できません。")
    raise SystemExit

print(f"\nモデルを訓練します。クラス数: {num_classes}、訓練データ数: {len(X_train)}")

# ===== データ拡張 =====
datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.2,
    height_shift_range=0.2,
    shear_range=0.2,
    zoom_range=0.2,
    horizontal_flip=True,
    fill_mode="nearest"
)

train_generator = datagen.flow(
    X_train,
    y_train,
    batch_size=BATCH_SIZE,
    shuffle=True
)

# ===== モデル構築 =====
model = keras.Sequential([
    keras.Input(shape=IMAGE_SIZE + (3,)),
    layers.Conv2D(32, (3, 3), activation="relu"),
    layers.MaxPooling2D((2, 2)),

    layers.Conv2D(64, (3, 3), activation="relu"),
    layers.MaxPooling2D((2, 2)),

    layers.Conv2D(128, (3, 3), activation="relu"),
    layers.MaxPooling2D((2, 2)),

    layers.Flatten(),
    layers.Dense(64, activation="relu"),
    layers.Dropout(0.3),
    layers.Dense(num_classes, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

# ===== コールバック =====
callbacks = [
    keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True
    ),
    keras.callbacks.ModelCheckpoint(
        filepath=MODEL_PATH,
        monitor="val_loss",
        save_best_only=True
    )
]

# ===== 学習 =====
history = model.fit(
    train_generator,
    epochs=EPOCHS,
    validation_data=(X_test, y_test),
    callbacks=callbacks,
    verbose=1
)

print("\nモデルの訓練が完了しました。")

# ===== 最終評価 =====
test_loss, test_acc = model.evaluate(X_test, y_test, verbose=0)
print(f"Test loss: {test_loss:.4f}")
print(f"Test accuracy: {test_acc:.4f}")

# ===== 保存 =====
model.save(MODEL_PATH)
print(f"モデルを保存しました: {MODEL_PATH}")

# history も保存
np.save(os.path.join(DATASET_DIR, "history_loss.npy"), np.array(history.history["loss"]))
np.save(os.path.join(DATASET_DIR, "history_val_loss.npy"), np.array(history.history["val_loss"]))
np.save(os.path.join(DATASET_DIR, "history_accuracy.npy"), np.array(history.history["accuracy"]))
np.save(os.path.join(DATASET_DIR, "history_val_accuracy.npy"), np.array(history.history["val_accuracy"]))

print("学習履歴も保存しました。")