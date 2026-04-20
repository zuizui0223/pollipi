import os
import numpy as np
import tensorflow as tf
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import matplotlib.pyplot as plt
import seaborn as sns

# ===== 設定 =====
DATASET_DIR = os.environ.get("DATASET_DIR", "inat_lepidoptera_japan")
MODEL_STEM = os.environ.get("MODEL_STEM", "cnn_lepidoptera")

TFLITE_MODEL_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}_int8.tflite")
X_TEST_PATH = os.path.join(DATASET_DIR, "X_test_uint8.npy")
Y_TEST_PATH = os.path.join(DATASET_DIR, "y_test.npy")
CLASSES_PATH = os.path.join(DATASET_DIR, "classes.npy")

REPORT_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}_classification_report.txt")
CONFUSION_NPY_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}_confusion_matrix.npy")
CONFUSION_PNG_PATH = os.path.join(DATASET_DIR, f"{MODEL_STEM}_confusion_matrix_top30.png")

TOP_N_CONFUSION = 30  # 可視化する上位クラス数

# ===== データ読み込み =====
print("テストデータとクラス名を読み込みます...")
X_test = np.load(X_TEST_PATH)
y_test = np.load(Y_TEST_PATH)
classes = np.load(CLASSES_PATH, allow_pickle=True)

print(f"X_test raw shape: {X_test.shape}")
print(f"y_test shape: {y_test.shape}")
print(f"クラス数: {len(classes)}")

# uint8 -> float32, 0-1
X_test = X_test.astype("float32") / 255.0

# ===== TFLite モデル読み込み =====
print("\nTFLite モデルを読み込みます...")
interpreter = tf.lite.Interpreter(model_path=TFLITE_MODEL_PATH)
interpreter.allocate_tensors()

input_details = interpreter.get_input_details()
output_details = interpreter.get_output_details()

print("入力テンソル情報:")
print(input_details)
print("\n出力テンソル情報:")
print(output_details)

input_index = input_details[0]["index"]
output_index = output_details[0]["index"]
input_dtype = input_details[0]["dtype"]
output_dtype = output_details[0]["dtype"]

input_scale, input_zero_point = input_details[0]["quantization"]
output_scale, output_zero_point = output_details[0]["quantization"]

print(f"\n入力 dtype: {input_dtype}, quantization: {(input_scale, input_zero_point)}")
print(f"出力 dtype: {output_dtype}, quantization: {(output_scale, output_zero_point)}")

def prepare_input(sample):
    """
    sample: shape (1, H, W, C), float32 in [0,1]
    """
    if input_dtype == np.float32:
        return sample.astype(np.float32)

    elif input_dtype == np.int8:
        if input_scale == 0:
            raise ValueError("input_scale が 0 です。量子化パラメータを確認してください。")
        q = np.round(sample / input_scale + input_zero_point)
        q = np.clip(q, -128, 127).astype(np.int8)
        return q

    elif input_dtype == np.uint8:
        if input_scale == 0:
            raise ValueError("input_scale が 0 です。量子化パラメータを確認してください。")
        q = np.round(sample / input_scale + input_zero_point)
        q = np.clip(q, 0, 255).astype(np.uint8)
        return q

    else:
        raise ValueError(f"未対応の入力 dtype: {input_dtype}")

def dequantize_output(output):
    if output_dtype == np.float32:
        return output.astype(np.float32)

    elif output_dtype == np.int8:
        return (output.astype(np.float32) - output_zero_point) * output_scale

    elif output_dtype == np.uint8:
        return (output.astype(np.float32) - output_zero_point) * output_scale

    else:
        raise ValueError(f"未対応の出力 dtype: {output_dtype}")

# ===== 推論 =====
print("\nTFLite 推論を開始します...")
predictions = []

for i in range(len(X_test)):
    input_data = np.expand_dims(X_test[i], axis=0)  # (1, 128, 128, 3)
    input_data = prepare_input(input_data)

    interpreter.set_tensor(input_index, input_data)
    interpreter.invoke()

    output_data = interpreter.get_tensor(output_index)
    output_data = dequantize_output(output_data)

    predictions.append(output_data[0])

    if (i + 1) % 500 == 0:
        print(f"{i + 1} / {len(X_test)} 枚 推論済み")

predictions = np.array(predictions)
y_pred = np.argmax(predictions, axis=1)

# ===== 評価 =====
accuracy = accuracy_score(y_test, y_pred)
print(f"\nTFLite モデルのテスト精度: {accuracy:.4f}")

# classification report
report = classification_report(
    y_test,
    y_pred,
    labels=np.arange(len(classes)),
    target_names=[str(c) for c in classes],
    zero_division=0
)

print("\n分類レポート:")
print(report)

with open(REPORT_PATH, "w", encoding="utf-8") as f:
    f.write(report)

print(f"\n分類レポート保存: {REPORT_PATH}")

# confusion matrix
cm = confusion_matrix(y_test, y_pred, labels=np.arange(len(classes)))
np.save(CONFUSION_NPY_PATH, cm)
print(f"混同行列保存: {CONFUSION_NPY_PATH}")

# ===== 上位クラスだけ可視化 =====
true_counts = np.bincount(y_test, minlength=len(classes))
top_indices = np.argsort(true_counts)[::-1][:TOP_N_CONFUSION]

cm_top = cm[np.ix_(top_indices, top_indices)]
top_names = [str(classes[i]) for i in top_indices]

plt.figure(figsize=(16, 13))
sns.heatmap(
    cm_top,
    annot=False,
    fmt="d",
    cmap="Blues",
    xticklabels=top_names,
    yticklabels=top_names
)
plt.xlabel("予測ラベル")
plt.ylabel("真のラベル")
plt.title(f"TFLite 混同行列（出現頻度上位 {TOP_N_CONFUSION} クラス）")
plt.xticks(rotation=90)
plt.yticks(rotation=0)
plt.tight_layout()
plt.savefig(CONFUSION_PNG_PATH, dpi=200)
plt.show()

print(f"混同行列画像保存: {CONFUSION_PNG_PATH}")
print("\n評価完了。")