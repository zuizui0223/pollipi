from ultralytics import YOLO

MODEL_PATH = r"C:\Users\zuizui\mc\runs\cirsium_detect\weights\best.pt"
SOURCE_DIR = r"C:\Users\zuizui\mc\cirsium_100"

def main():
    model = YOLO(MODEL_PATH)

    model.predict(
        source=SOURCE_DIR,
        imgsz=640,
        conf=0.25,
        save=True,
        project=r"C:\Users\zuizui\mc\runs",
        name="cirsium_predict",
        exist_ok=True
    )

if __name__ == "__main__":
    main()