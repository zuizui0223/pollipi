import tensorflow as tf
from pathlib import Path

MODEL_PATH = r"C:\Users\zuizui\mc\insect3_dataset\insect3_classifier.keras"
OUT_PATH = r"C:\Users\zuizui\mc\insect3_dataset\insect3_classifier.tflite"

model = tf.keras.models.load_model(MODEL_PATH)

converter = tf.lite.TFLiteConverter.from_keras_model(model)

# まずは float32 TFLite。安定優先。
tflite_model = converter.convert()

Path(OUT_PATH).write_bytes(tflite_model)

print(f"保存しました: {OUT_PATH}")
print(f"サイズ: {Path(OUT_PATH).stat().st_size / 1024 / 1024:.2f} MB")