import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from tensorflow.keras import layers
from tensorflow.keras.preprocessing.image import ImageDataGenerator

# ===== 設定 =====
DATASET_DIR = r"C:\Users\zuizui\mc\insect3_dataset"
MODEL_PATH = os.path.join(DATASET_DIR, "insect3_classifier.keras")

IMAGE_SIZE = (128, 128)
BATCH_SIZE = 32
EPOCHS = 25

X_train = np.load(os.path.join(DATASET_DIR, "X_train_uint8.npy"))
X_test = np.load(os.path.join(DATASET_DIR, "X_test_uint8.npy"))
y_train = np.load(os.path.join(DATASET_DIR, "y_train.npy"))
y_test = np.load(os.path.join(DATASET_DIR, "y_test.npy"))
classes = np.load(os.path.join(DATASET_DIR, "classes.npy"), allow_pickle=True)

X_train = X_train.astype("float32") / 255.0
X_test = X_test.astype("float32") / 255.0

num_classes = len(classes)

print(f"X_train: {X_train.shape}")
print(f"X_test : {X_test.shape}")
print(f"classes: {classes}")

datagen = ImageDataGenerator(
    rotation_range=20,
    width_shift_range=0.15,
    height_shift_range=0.15,
    zoom_range=0.15,
    horizontal_flip=True,
    fill_mode="nearest"
)

train_generator = datagen.flow(
    X_train,
    y_train,
    batch_size=BATCH_SIZE,
    shuffle=True
)

model = keras.Sequential([
    keras.Input(shape=IMAGE_SIZE + (3,)),

    layers.Conv2D(32, 3, activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(64, 3, activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(128, 3, activation="relu"),
    layers.MaxPooling2D(),

    layers.Conv2D(256, 3, activation="relu"),
    layers.MaxPooling2D(),

    layers.Flatten(),
    layers.Dense(128, activation="relu"),
    layers.Dropout(0.4),
    layers.Dense(num_classes, activation="softmax")
])

model.compile(
    optimizer="adam",
    loss="sparse_categorical_crossentropy",
    metrics=["accuracy"]
)

model.summary()

callbacks = [
    keras.callbacks.EarlyStopping(
        monitor="val_loss",
        patience=5,
        restore_best_weights=True
    ),
    keras.callbacks.ModelCheckpoint(
        MODEL_PATH,
        monitor="val_loss",
        save_best_only=True
    )
]

history = model.fit(
    train_generator,
    epochs=EPOCHS,
    validation_data=(X_test, y_test),
    callbacks=callbacks,
    verbose=1
)

loss, acc = model.evaluate(X_test, y_test, verbose=0)

print("\n学習完了")
print(f"Test loss: {loss:.4f}")
print(f"Test accuracy: {acc:.4f}")

model.save(MODEL_PATH)
print(f"保存: {MODEL_PATH}")

np.save(os.path.join(DATASET_DIR, "history_loss.npy"), np.array(history.history["loss"]))
np.save(os.path.join(DATASET_DIR, "history_val_loss.npy"), np.array(history.history["val_loss"]))
np.save(os.path.join(DATASET_DIR, "history_accuracy.npy"), np.array(history.history["accuracy"]))
np.save(os.path.join(DATASET_DIR, "history_val_accuracy.npy"), np.array(history.history["val_accuracy"]))