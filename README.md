# PolliPi Timelapse API

Raspberry Pi 5 と Camera Module 3 を Picamera2 で制御する FastAPI サーバーです。
画像は `/home/zuizui0223/pollipi_timelapse/images` に JPEG として保存されます。

## 実機構成

2026-05-26 に `rpicam-hello --list-cameras` で確認した構成:

| ホスト | 用途 | 認識されたセンサー | 最大解像度 |
| --- | --- | --- | --- |
| `zuizui.local` | Camera Module 3 Wide | `imx708_wide` | 4608 x 2592 |
| `zuizui2.local` | Raspberry Pi AI Camera | `imx500` | 4056 x 3040 |

## Raspberry Pi の準備

Camera Module 3 を接続し、Raspberry Pi OS でカメラが認識されることを確認します。

```bash
rpicam-hello
```

必要なパッケージと Python 環境を準備します。`Picamera2`、FastAPI、Uvicorn は
OS のパッケージを利用するため、仮想環境には `--system-site-packages` を指定します。

```bash
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-fastapi python3-uvicorn
mkdir -p /home/zuizui0223/pollipi_timelapse/images
cd /home/zuizui0223/pollipi_timelapse
python3 -m venv --system-site-packages .venv
```

`pollipi_api_server.py` とこの `README.md` を
`/home/zuizui0223/pollipi_timelapse/` に配置してください。

## 2 台の Raspberry Pi への配置

この API の通常のタイムラプス撮影は、Camera Module 3 と AI Camera の両方で
同じ `pollipi_api_server.py` を利用できます。Windows PC の PowerShell で、
このフォルダから次を実行して各 Raspberry Pi に転送します。

```powershell
ssh zuizui0223@zuizui.local "mkdir -p /home/zuizui0223/pollipi_timelapse"
scp .\pollipi_api_server.py .\README.md zuizui0223@zuizui.local:/home/zuizui0223/pollipi_timelapse/

ssh zuizui0223@zuizui2.local "mkdir -p /home/zuizui0223/pollipi_timelapse"
scp .\pollipi_api_server.py .\README.md zuizui0223@zuizui2.local:/home/zuizui0223/pollipi_timelapse/
```

各 Raspberry Pi に SSH 接続し、依存パッケージをインストールします。

Camera Module 3 を接続した `zuizui.local`:

```bash
ssh zuizui0223@zuizui.local
sudo apt update
sudo apt install -y python3-picamera2 python3-venv python3-fastapi python3-uvicorn
mkdir -p /home/zuizui0223/pollipi_timelapse/images
cd /home/zuizui0223/pollipi_timelapse
python3 -m venv --system-site-packages .venv
```

AI Camera を接続した `zuizui2.local`:

```bash
ssh zuizui0223@zuizui2.local
sudo apt update
sudo apt full-upgrade -y
sudo apt install -y python3-picamera2 python3-venv python3-fastapi python3-uvicorn imx500-all
sudo reboot
```

再起動後、再度 `zuizui2.local` に SSH 接続して API の環境を作成します。

```bash
mkdir -p /home/zuizui0223/pollipi_timelapse/images
cd /home/zuizui0223/pollipi_timelapse
python3 -m venv --system-site-packages .venv
```

## 起動

Camera Module 3 側:

```bash
ssh zuizui0223@zuizui.local "cd /home/zuizui0223/pollipi_timelapse && .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000"
```

AI Camera 側:

```bash
ssh zuizui0223@zuizui2.local "cd /home/zuizui0223/pollipi_timelapse && .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000"
```

各 API はそれぞれ `http://zuizui.local:8000` と
`http://zuizui2.local:8000` でアクセスします。

## API

タイムラプスを開始します。`interval_sec` は 1 以上 3600 以下の秒数です。
すでに撮影中の場合は停止してから、新しい間隔で撮影を再開します。

```bash
curl -X POST http://zuizui.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 10}'

curl -X POST http://zuizui2.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 10}'
```

状態を取得します。

```bash
curl http://zuizui.local:8000/status
curl http://zuizui2.local:8000/status
```

最新画像を取得します。

```bash
curl http://zuizui.local:8000/latest --output latest-module3.jpg
curl http://zuizui2.local:8000/latest --output latest-ai-camera.jpg
```

タイムラプスを停止します。

```bash
curl -X POST http://zuizui.local:8000/stop
curl -X POST http://zuizui2.local:8000/stop
```

`/status` は次の項目を JSON で返します。

```json
{
  "running": true,
  "interval_sec": 10.0,
  "capture_count": 3,
  "last_capture_time": "2026-05-26T14:30:10+09:00",
  "last_image": "/home/zuizui0223/pollipi_timelapse/images/image_20260526_143010_123456.jpg",
  "message": "Timelapse running."
}
```
