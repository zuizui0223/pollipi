import shutil
from pathlib import Path

# ===== 設定 =====
SOURCE_DIR = Path(r"C:\Users\zuizui\mc\inat_cirsium_japan\images")
OUTPUT_DIR = Path(r"C:\Users\zuizui\mc\cirsium_all")

VALID_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}


def main():
    if not SOURCE_DIR.exists():
        raise FileNotFoundError(f"元フォルダが見つかりません: {SOURCE_DIR}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    image_files = [
        p for p in SOURCE_DIR.rglob("*")
        if p.is_file() and p.suffix.lower() in VALID_EXTS
    ]

    print(f"見つかった画像数: {len(image_files)}")

    if len(image_files) == 0:
        raise RuntimeError("画像が見つかりません。SOURCE_DIR を確認してください。")

    copied = 0
    for i, src in enumerate(image_files, start=1):
        dst = OUTPUT_DIR / src.name

        if dst.exists():
            dst = OUTPUT_DIR / f"{src.stem}_{i}{src.suffix}"

        shutil.copy2(src, dst)
        copied += 1

    print("\n完了")
    print(f"出力先: {OUTPUT_DIR}")
    print(f"コピー枚数: {copied}")


if __name__ == "__main__":
    main()