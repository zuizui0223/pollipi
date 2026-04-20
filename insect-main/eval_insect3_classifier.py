import os
import numpy as np
import tensorflow as tf
from tensorflow import keras
from sklearn.metrics import classification_report, confusion_matrix, accuracy_score

DATASET_DIR = r"C:\Users\zuizui\mc\insect3_dataset"
MODEL_PATH = os.path.join(DATASET_DIR, "insect3_classifier.keras")

X_test = np.load(os.path.join(DATASET_DIR, "X_test_uint8.npy"))
y_test = np.load(os.path.join(DATASET_DIR, "y_test.npy"))
classes = np.load(os.path.join(DATASET_DIR, "classes.npy"), allow_pickle=True)

X_test = X_test.astype("float32") / 255.0

model = keras.models.load_model(MODEL_PATH)

pred = model.predict(X_test, batch_size=32)
y_pred = np.argmax(pred, axis=1)
max_prob = np.max(pred, axis=1)

acc = accuracy_score(y_test, y_pred)

print(f"Accuracy: {acc:.4f}")
print("\nClassification report:")
print(classification_report(
    y_test,
    y_pred,
    target_names=[str(c) for c in classes],
    zero_division=0
))

print("\nConfusion matrix:")
print(confusion_matrix(y_test, y_pred))

print("\nPrediction confidence:")
print(f"mean max_prob: {max_prob.mean():.4f}")
print(f"min max_prob : {max_prob.min():.4f}")
print(f"max max_prob : {max_prob.max():.4f}")

# confidence しきい値ごとの採用率
for th in [0.5, 0.6, 0.7, 0.8, 0.9]:
    accepted = max_prob >= th
    if accepted.sum() == 0:
        print(f"threshold {th}: accepted 0")
    else:
        acc_th = accuracy_score(y_test[accepted], y_pred[accepted])
        print(f"threshold {th}: accepted {accepted.sum()} / {len(y_test)}, acc among accepted = {acc_th:.4f}")