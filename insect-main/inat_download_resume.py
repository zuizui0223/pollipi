#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import json
import os
import re
import time
from pathlib import Path
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

API_URL = "https://api.inaturalist.org/v1/observations"


def parse_args():
    parser = argparse.ArgumentParser(description="Resumable iNaturalist image downloader")
    parser.add_argument("--out-dir", default="inat_dataset")
    parser.add_argument("--taxon-ids", default="47217,47224,47192")
    parser.add_argument("--place-id", default="6737")
    parser.add_argument("--per-page", type=int, default=200)
    parser.add_argument("--max-images", type=int, default=10000)
    parser.add_argument("--max-pages", type=int, default=100000)
    parser.add_argument("--photos-per-observation", type=int, default=1)
    parser.add_argument("--image-size", choices=["square", "small", "medium", "large", "original"], default="large")
    parser.add_argument("--quality-grade", default="research", choices=["research", "casual"])
    parser.add_argument("--photo-license", default="any")
    parser.add_argument("--year", type=int, default=None)
    parser.add_argument("--sleep-sec", type=float, default=0.3)
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--group-by-label", action="store_true")
    return parser.parse_args()


def make_session():
    session = requests.Session()
    retry = Retry(
        total=5,
        read=5,
        connect=5,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["GET"],
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "inat-downloader/1.0"})
    return session


def slugify(text):
    text = text or "unknown"
    text = text.strip()
    text = re.sub(r"[^\w\-\. ]+", "_", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"_+", "_", text)
    return text[:120] if text else "unknown"


def upgrade_inat_photo_url(url, size="large"):
    if not url:
        return url
    return re.sub(r"/(square|small|medium|large|original)\.", f"/{size}.", url)


def guess_ext(url):
    path = urlparse(url).path.lower()
    for ext in [".jpg", ".jpeg", ".png", ".webp"]:
        if path.endswith(ext):
            return ext
    return ".jpg"


def parse_lat_lon(obs):
    lat, lon = None, None
    location = obs.get("location")
    if isinstance(location, str) and "," in location:
        try:
            lat_s, lon_s = location.split(",", 1)
            lat, lon = float(lat_s), float(lon_s)
        except Exception:
            pass

    if lat is None or lon is None:
        geojson = obs.get("geojson") or {}
        coords = geojson.get("coordinates")
        if isinstance(coords, list) and len(coords) >= 2:
            try:
                lon, lat = float(coords[0]), float(coords[1])
            except Exception:
                pass

    return lat, lon


def load_seen_photo_ids(csv_path):
    seen = set()
    if not csv_path.exists():
        return seen
    with csv_path.open("r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            pid = row.get("photo_id")
            if pid:
                seen.add(str(pid))
    return seen


def ensure_metadata_header(csv_path):
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "obs_id", "photo_id", "taxon_name", "species_guess", "user_login",
            "observed_on", "latitude", "longitude", "image_url", "local_path",
            "license_code", "attribution", "year_filter", "place_id", "taxon_ids"
        ])


def append_metadata(csv_path, row):
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            row["obs_id"], row["photo_id"], row["taxon_name"], row["species_guess"],
            row["user_login"], row["observed_on"], row["latitude"], row["longitude"],
            row["image_url"], row["local_path"], row["license_code"], row["attribution"],
            row["year_filter"], row["place_id"], row["taxon_ids"]
        ])


def load_checkpoint(checkpoint_path):
    if checkpoint_path.exists():
        with checkpoint_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"next_page": 1, "downloaded_images": 0}


def save_checkpoint(checkpoint_path, checkpoint):
    with checkpoint_path.open("w", encoding="utf-8") as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)


def fetch_json(session, params, timeout):
    response = session.get(API_URL, params=params, timeout=timeout)
    response.raise_for_status()
    return response.json()


def download_image(session, url, dest_path, timeout):
    tmp_path = dest_path.with_suffix(dest_path.suffix + ".part")
    with session.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with tmp_path.open("wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    os.replace(tmp_path, dest_path)


def main():
    args = parse_args()

    if args.per_page < 1 or args.per_page > 200:
        raise ValueError("--per-page は 1〜200 にしてください")

    out_dir = Path(args.out_dir)
    images_dir = out_dir / "images"
    csv_path = out_dir / "metadata.csv"
    checkpoint_path = out_dir / "checkpoint.json"

    out_dir.mkdir(parents=True, exist_ok=True)
    images_dir.mkdir(parents=True, exist_ok=True)

    ensure_metadata_header(csv_path)
    seen_photo_ids = load_seen_photo_ids(csv_path)
    checkpoint = load_checkpoint(checkpoint_path)
    session = make_session()

    page = int(checkpoint.get("next_page", 1))
    downloaded_images = int(checkpoint.get("downloaded_images", len(seen_photo_ids)))

    print(f"保存先: {out_dir.resolve()}")
    print(f"既知 photo_id 数: {len(seen_photo_ids)}")
    print(f"再開ページ: {page}")
    print(f"最大画像数: {args.max_images}")

    base_params = {
        "taxon_id": args.taxon_ids,
        "place_id": args.place_id,
        "per_page": args.per_page,
        "quality_grade": args.quality_grade,
        "photo_license": args.photo_license,
        "order_by": "created_at",
        "order": "desc",
        "has[]": "photos",
    }
    if args.year is not None:
        base_params["year"] = args.year

    first_page = True

    try:
        while page <= args.max_pages and downloaded_images < args.max_images:
            params = dict(base_params)
            params["page"] = page

            print(f"\n[page {page}] 取得中...")
            data = fetch_json(session, params=params, timeout=args.timeout)

            if first_page:
                print(f"API total_results = {data.get('total_results')}")
                first_page = False

            results = data.get("results", [])
            if not results:
                print("結果がありません。終了します。")
                break

            added_this_page = 0

            for obs in results:
                obs_id = obs.get("id")
                taxon = obs.get("taxon") or {}
                taxon_name = taxon.get("name") or obs.get("species_guess") or "unknown"
                species_guess = obs.get("species_guess") or ""
                user_login = (obs.get("user") or {}).get("login", "")
                observed_on = obs.get("observed_on") or ""
                latitude, longitude = parse_lat_lon(obs)

                photos = obs.get("photos") or []
                per_obs_saved = 0

                for photo in photos:
                    if per_obs_saved >= args.photos_per_observation:
                        break
                    if downloaded_images >= args.max_images:
                        break

                    photo_id = photo.get("id")
                    if photo_id is None:
                        continue
                    photo_id_str = str(photo_id)

                    if photo_id_str in seen_photo_ids:
                        continue

                    image_url = upgrade_inat_photo_url(photo.get("url"), args.image_size)
                    if not image_url:
                        continue

                    label_slug = slugify(taxon_name)
                    save_dir = images_dir / label_slug if args.group_by_label else images_dir
                    save_dir.mkdir(parents=True, exist_ok=True)

                    ext = guess_ext(image_url)
                    filename = f"obs_{obs_id}_photo_{photo_id}{ext}"
                    dest_path = save_dir / filename

                    try:
                        download_image(session, image_url, dest_path, timeout=args.timeout)
                    except Exception as e:
                        print(f"  download failed: obs={obs_id}, photo={photo_id}, err={e}")
                        continue

                    append_metadata(csv_path, {
                        "obs_id": obs_id,
                        "photo_id": photo_id,
                        "taxon_name": taxon_name,
                        "species_guess": species_guess,
                        "user_login": user_login,
                        "observed_on": observed_on,
                        "latitude": latitude,
                        "longitude": longitude,
                        "image_url": image_url,
                        "local_path": str(dest_path),
                        "license_code": photo.get("license_code") or "",
                        "attribution": photo.get("attribution") or "",
                        "year_filter": args.year if args.year is not None else "",
                        "place_id": args.place_id,
                        "taxon_ids": args.taxon_ids,
                    })

                    seen_photo_ids.add(photo_id_str)
                    downloaded_images += 1
                    added_this_page += 1
                    per_obs_saved += 1

                    print(f"  saved #{downloaded_images}: obs={obs_id}, photo={photo_id}, label={taxon_name}")

                if downloaded_images >= args.max_images:
                    break

            checkpoint["next_page"] = page + 1
            checkpoint["downloaded_images"] = downloaded_images
            save_checkpoint(checkpoint_path, checkpoint)

            print(f"[page {page}] 追加保存数: {added_this_page}")
            page += 1
            time.sleep(args.sleep_sec)

    except KeyboardInterrupt:
        print("\n中断しました。checkpoint.json から再開できます。")
        checkpoint["next_page"] = page
        checkpoint["downloaded_images"] = downloaded_images
        save_checkpoint(checkpoint_path, checkpoint)
        return

    print("\n完了")
    print(f"総保存画像数: {downloaded_images}")
    print(f"metadata: {csv_path}")
    print(f"checkpoint: {checkpoint_path}")


if __name__ == "__main__":
    main()