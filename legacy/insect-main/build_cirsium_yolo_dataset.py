import random
import shutil
from pathlib import Path

# ===== 設定 =====
SOURCE_DIR = Path(r"C:\Users\zuizui\mc\cirsium_all")
OUTPUT_DIR = Path(r"C:\Users\zuizui\mc\cirsium_yolo")

TRAIN_RATIO = 0.8
VAL_RATIO = 0.1
TEST_RATIO = 0.1
SEED = 42

CLASS_NAMES = ["cirsium_flower"]
VALID_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".JPG", ".JPEG", ".PNG", ".BMP", ".WEBP"}


def ensure_dir(path: Path):
    path.mkdir(parents=True, exist_ok=True)


def find_image_files(source_dir: Path):
    return [
        p for p in source_dir.iterdir()
        if p.is_file() and p.suffix in VALID_IMAGE_EXTS
    ]


def find_label_files(source_dir: Path):
    return [
        p for p in source_dir.iterdir()
        if p.is_file() and p.suffix.lower() == ".txt" and p.name != "classes.txt"
    ]


def find_image_label_pairs(source_dir: Path):
    image_files = find_image_files(source_dir)
    label_files = find_label_files(source_dir)

    image_map = {p.stem: p for p in image_files}
    label_map = {p.stem: p for p in label_files if p.stat().st_size > 0}

    common_keys = sorted(set(image_map.keys()) & set(label_map.keys()))
    image_only = sorted(set(image_map.keys()) - set(label_map.keys()))
    label_only = sorted(set(label_map.keys()) - set(image_map.keys()))

    pairs = [(image_map[k], label_map[k]) for k in common_keys]

    print(f"画像数         : {len(image_files)}")
    print(f"ラベル数       : {len(label_files)}")
    print(f"有効ラベル数   : {len(label_map)}")
    print(f"一致ペア数     : {len(pairs)}")
    print(f"画像のみ       : {len(image_only)}")
    print(f"ラベルのみ     : {len(label_only)}")

    if image_only:
        print("\n[画像のみの例]")
        for x in image_only[:10]:
            print(" ", x)

    if label_only:
        print("\n[ラベルのみの例]")
        for x in label_only[:10]:
            print(" ", x)

    return pairs


def make_output_dirs(base_dir: Path):
    for split in ["train", "val", "test"]:
        ensure_dir(base_dir / "images" / split)
        ensure_dir(base_dir / "labels" / split)


def write_data_yaml(base_dir: Path, class_names):
    yaml_path = base_dir / "data.yaml"
    with open(yaml_path, "w", encoding="utf-8") as f:
        f.write(f"path: {base_dir.as_posix()}\n")
        f.write("train: images/train\n")
        f.write("val: images/val\n")
        f.write("test: images/test\n\n")
        f.write("names:\n")
        for i, name in enumerate(class_names):
            f.write(f"  {i}: {name}\n")
    return yaml_path


def split_pairs(pairs, train_ratio, val_ratio, test_ratio, seed=42):
    total = train_ratio + val_ratio + test_ratio
    if abs(total - 1.0) > 1e-8:
        raise ValueError("TRAIN_RATIO + VAL_RATIO + TEST_RATIO は 1.0 にしてください")

    random.seed(seed)
    pairs = pairs[:]
    random.shuffle(pairs)

    n = len(pairs)
    n_train = int(n * train_ratio)
    n_val = int(n * val_ratio)

    train_pairs = pairs[:n_train]
    val_pairs = pairs[n_train:n_train + n_val]
    test_pairs = pairs[n_train + n_val:]

    return train_pairs, val_pairs, test_pairs


def copy_split(pairs, split_name: str, output_dir: Path):
    img_out = output_dir / "images" / split_name
    lbl_out = output_dir / "labels" / split_name

    for img_path, label_path in pairs:
        shutil.copy2(img_path, img_out / img_path.name)
        shutil.copy2(label_path, lbl_out / label_path.name)


def main():
    print("画像とラベルの対応を確認します...")
    pairs = find_image_label_pairs(SOURCE_DIR)

    if len(pairs) == 0:
        raise RuntimeError("一致する画像+ラベルのペアが見つかりません。上の一覧を確認してください。")

    print("\n出力フォルダを作成します...")
    make_output_dirs(OUTPUT_DIR)

    print("train / val / test に分割します...")
    train_pairs, val_pairs, test_pairs = split_pairs(
        pairs, TRAIN_RATIO, VAL_RATIO, TEST_RATIO, seed=SEED
    )

    print(f"train: {len(train_pairs)}")
    print(f"val  : {len(val_pairs)}")
    print(f"test : {len(test_pairs)}")

    print("ファイルをコピーします...")
    copy_split(train_pairs, "train", OUTPUT_DIR)
    copy_split(val_pairs, "val", OUTPUT_DIR)
    copy_split(test_pairs, "test", OUTPUT_DIR)

    print("data.yaml を作成します...")
    yaml_path = write_data_yaml(OUTPUT_DIR, CLASS_NAMES)

    print("\n完了")
    print(f"YOLOデータセット: {OUTPUT_DIR}")
    print(f"data.yaml       : {yaml_path}")


if __name__ == "__main__":
    main()