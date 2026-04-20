from ultralytics import YOLO

DATA_YAML = r"C:\Users\zuizui\mc\cirsium_yolo\data.yaml"

def main():
    model = YOLO("yolo11n.pt")

    model.train(
        data=DATA_YAML,
        epochs=50,
        imgsz=640,
        batch=16,
        device="cpu",
        project=r"C:\Users\zuizui\mc\runs",
        name="cirsium_detect",
        exist_ok=True
    )

if __name__ == "__main__":
    main()