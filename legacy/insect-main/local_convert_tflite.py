import os
import numpy as np
import tensorflow as tf
from tensorflow import keras

# ===== 設定 =====
DATASET_DIR = os.environ.get("DATASET_DIR", "inat_lepidoptera_japan")
MODEL_STEM = os.environ.get("MODEL_STEM", "cnn_lepidoptera")

MODEL_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}.keras")
X_TRAIN_PATH = os.path.join(DATASET_DIR, "X_train_uint8.npy")
CLASSES_PATH = os.path.join(DATASET_DIR, "classes.npy")

TFLITE_INT8_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}_int8.tflite")
TFLITE_FLOAT_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}_float32.tflite")
LABELS_TXT_PATH = os.path.join(DATASET_DIR, "labels.txt")

REPRESENTATIVE_SAMPLES = 200

print("学習済みKerasモデルを読み込みます...")
model = keras.models.load_model(MODEL_PATH)

print("代表データセット用の学習画像を読み込みます...")
X_train = np.load(X_TRAIN_PATH)

# uint8 -> float32, 0-1
X_train = X_train.astype("float32") / 255.0

print(f"X_train shape: {X_train.shape}")

# ラベル保存
classes = np.load(CLASSES_PATH, allow_pickle=True)
with open(LABELS_TXT_PATH, "w", encoding="utf-8") as f:
    for i, name in enumerate(classes):
        f.write(f"{i}\t{name}\n")

print(f"labels.txt を保存しました: {LABELS_TXT_PATH}")

# ===== まず float32 TFLite を保存（安全版）=====
print("\nfloat32 TFLite に変換中...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

with open(TFLITE_FLOAT_PATH, "wb") as f:
    f.write(tflite_model)

print(f"float32 TFLite 保存完了: {TFLITE_FLOAT_PATH}")

# ===== representative dataset =====
def representative_dataset():
    n = min(REPRESENTATIVE_SAMPLES, len(X_train))
    for i in range(n):
        sample = X_train[i:i+1]
        yield [sample.astype(np.float32)]

# ===== full INT8 quantization =====
print("\nINT8 TFLite に変換中...")
converter = tf.lite.TFLiteConverter.from_keras_model(model)
converter.optimizations = [tf.lite.Optimize.DEFAULT]
converter.representative_dataset = representative_dataset

# 入出力も int8 に固定
converter.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
converter.inference_input_type = tf.int8
converter.inference_output_type = tf.int8

tflite_quant_model = converter.convert()

with open(TFLITE_INT8_PATH, "wb") as f:
    f.write(tflite_quant_model)

print(f"INT8 TFLite 保存完了: {TFLITE_INT8_PATH}")

# ===== 確認 =====
print("\n保存ファイル:")
print(f"  {TFLITE_FLOAT_PATH}")
print(f"  {TFLITE_INT8_PATH}")
print(f"  {LABELS_TXT_PATH}")

print("\n変換完了。")
print("普通の Raspberry Pi では、まず INT8 版を試すのがおすすめです。")