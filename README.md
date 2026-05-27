# PolliPi Field Observer

Raspberry Pi 5 と Camera Module 3 / AI Camera を Picamera2 で制御する FastAPI サーバーです。
画像は標準で実行ユーザーの `~/pollipi_timelapse/images` に JPEG として保存されます。
別の保存先を使う場合は `POLLIPI_IMAGE_DIR` 環境変数を設定できます。
同梱の iPad 向け PWA から、登録した台数分の観察機の撮影開始・停止、画角確認、
画像整理、自律タイムラプス運行を行えます。

## 野外調査向けの構成

1台で観察する場合の推奨構成は、Raspberry Pi が現場用 Wi-Fi を提供し、iPad は必要な時だけ接続する形です。

1. 設置時に iPad を観察機の Wi-Fi（例: `PolliPi-site01`）へ接続します。
2. Safari で `http://pollipi.local:8000/app/` を開き、ホーム画面に追加します。
3. `自律運行` と必要なら `背景差分で撮影間隔を自動調整` を有効にして撮影を開始します。
4. iPad や携帯が離れても、画像保存と自動間隔切替は Raspberry Pi 単独で継続します。
5. 回収時に再び Wi-Fi に接続して、撮影画像と判定履歴を確認します。

携帯テザリングは初期設定やソフトウェア更新には便利ですが、観察運行中の必須条件ではありません。
GitHub はソースコードと導入手順の配布場所として利用し、実際の操作画面は各 Pi が配信します。

複数台を同時に一つの画面で監視・開始停止する調査では、iPad とすべての Pi が同じネットワークに
存在する必要があります。その場合は、電池式の小型Wi-Fiルーターを現場ネットワークにするか、
1台の Pi を親ホットスポットにして他の Pi をそこへ接続する構成にします。撮影開始後は、
ネットワークがなくなっても各 Pi の `自律運行` が単独で継続します。

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

## Raspberry Pi への配置

同じ `pollipi_api_server.py` を Camera Module 3 と AI Camera の両方で利用できます。
観察機を増やす場合も、各 Pi に同じファイルを配置し、起動時の環境変数で名称を設定します。
Windows PC の PowerShell で、このフォルダから次を実行して転送します。

```powershell
ssh zuizui0223@zuizui.local "mkdir -p /home/zuizui0223/pollipi_timelapse"
scp .\pollipi_api_server.py .\README.md zuizui0223@zuizui.local:/home/zuizui0223/pollipi_timelapse/
scp -r .\web zuizui0223@zuizui.local:/home/zuizui0223/pollipi_timelapse/

ssh zuizui0223@zuizui2.local "mkdir -p /home/zuizui0223/pollipi_timelapse"
scp .\pollipi_api_server.py .\README.md zuizui0223@zuizui2.local:/home/zuizui0223/pollipi_timelapse/
scp -r .\web zuizui0223@zuizui2.local:/home/zuizui0223/pollipi_timelapse/
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

## 観察機名を設定して起動

Camera Module 3 側:

```bash
ssh zuizui0223@zuizui.local "cd /home/zuizui0223/pollipi_timelapse && POLLIPI_DEVICE_NAME='Site 01' POLLIPI_CAMERA_LABEL='Module 3 Wide' POLLIPI_CAMERA_MODEL='imx708_wide' .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000"
```

AI Camera 側:

```bash
ssh zuizui0223@zuizui2.local "cd /home/zuizui0223/pollipi_timelapse && POLLIPI_DEVICE_NAME='Site 02' POLLIPI_CAMERA_LABEL='AI Camera' POLLIPI_CAMERA_MODEL='imx500' .venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000"
```

各 API はそれぞれ `http://zuizui.local:8000` と
`http://zuizui2.local:8000` でアクセスします。

## 自動起動と自律運行

電源が復帰した時にも観察を再開できるように、API を `systemd` サービスとして起動します。
`Environment=` の表示名は観察機ごとに変更してください。

```bash
sudo tee /etc/systemd/system/pollipi.service >/dev/null <<'EOF'
[Unit]
Description=PolliPi Field Observer API
After=network.target

[Service]
User=zuizui0223
WorkingDirectory=/home/zuizui0223/pollipi_timelapse
Environment="POLLIPI_DEVICE_NAME=Site 01"
Environment="POLLIPI_CAMERA_LABEL=Module 3 Wide"
Environment=POLLIPI_CAMERA_MODEL=imx708_wide
ExecStart=/home/zuizui0223/pollipi_timelapse/.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now pollipi.service
```

アプリで `自律運行` を選んで開始すると、撮影設定は標準で
`~/pollipi_timelapse/autonomous_run.json` に保存されます。通信が切れても撮影は継続し、
Pi が再起動してサービスが戻ると撮影を再開します。`停止` を押すと再開設定も解除されます。

## Pi を現場用 Wi-Fi にする

Raspberry Pi OS Bookworm 以降では、公式ドキュメントの NetworkManager 方式でホットスポットを作成できます。
現在つないでいる Wi-Fi は切断されるため、最初はモニターまたはキーボードを使える場所で設定してください。

```bash
sudo nmcli device wifi hotspot ssid PolliPi-site01 password 'change-this-password'
```

iPad の Wi-Fi 設定で `PolliPi-site01` に接続した後、Pi のアドレスを確認して
`http://<Piのアドレス>:8000/app/` を開きます。1台ずつ独立して設置する観察機には、
別の SSID（`PolliPi-site02` など）を設定できます。同時操作する複数台は、
個別ホットスポットにはせず同じ親ネットワークへ接続してください。

公式資料: [Host a wireless network from your Raspberry Pi](https://www.raspberrypi.com/documentation/configuration/wireless/wireless-access-point.md)

## iPad 操作画面（PWA）

iPad を Raspberry Pi と同じ Wi-Fi ネットワークに接続し、Safari でいずれかの
観察機の URL を開きます。開いた Pi は自動的に登録され、`Raspberry Pi を追加` 欄へ
`zuizui0223@zuizui2` のように SSH 接続で使う名前を入力すると、アプリが
`http://zuizui2.local:8000` へ変換して接続します。登録は iPad 内に保存されます。

```text
http://zuizui.local:8000/app/
http://zuizui2.local:8000/app/
```

画面でできること:

- 台数を固定しない Raspberry Pi 観察機の登録・削除
- 登録した観察機の最新画像表示
- 各カメラの撮影中 / 停止中、撮影枚数、現在間隔、最終撮影時刻の確認
- 1 - 3600 秒の撮影間隔設定
- 全観察機同時または個別の撮影開始・停止
- 各 Raspberry Pi の保存画像フォルダ一覧表示
- 不要な撮影画像の削除（確認画面あり）
- `画角モニター` ボタンによる 640 x 360 / 約4fps の低負荷 MJPEG 構図確認（撮影前・撮影中に利用可能、保存されない）
- 表示中の観察機の写真全削除（撮影停止と確認ダイアログが必要）
- 背景差分による昆虫候補検出と省電力の自動撮影間隔切替
- 通信切断や電源復帰後にも撮影を続ける自律運行

iPad の Safari で共有ボタンから「ホーム画面に追加」を選ぶと、PolliPi を
アプリアイコンのように起動できます。App Store 公開なしでも利用者へこの導入手順と
Pi 用プログラムを GitHub から配布できます。画面は 4 秒ごとに状態を更新します。
`画角モニター` は設置時の向き確認用です。長時間観察ではモニターを停止し、
自律運行を使う方が電力消費を抑えられます。

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

観察機の表示名とカメラ情報を取得します。PWA はこの情報を利用して台数可変のカードを表示します。

```bash
curl http://zuizui.local:8000/device
```

最新画像を取得します。

```bash
curl http://zuizui.local:8000/latest --output latest-module3.jpg
curl http://zuizui2.local:8000/latest --output latest-ai-camera.jpg
```

保存画像一覧を取得します。`limit` には最大 200 枚まで指定できます。

```bash
curl "http://zuizui.local:8000/images?limit=40"
```

一覧にある画像を取得、または削除します。削除は元に戻せません。

```bash
curl http://zuizui.local:8000/images/image_20260526_143010_123456.jpg --output selected.jpg
curl -X DELETE http://zuizui.local:8000/images/image_20260526_143010_123456.jpg
```

現在の画角確認用 JPEG を1枚取得します。撮影開始前にも利用でき、この画像は
保存フォルダや撮影枚数には追加されません。

```bash
curl http://zuizui.local:8000/preview --output preview.jpg
```

画角の低負荷 MJPEG モニターを取得します。ブラウザの `画角モニター` ボタンが利用する
ストリームで、保存画像には追加されません。撮影開始・停止時にはモニターが自動終了します。

```bash
curl http://zuizui.local:8000/mjpeg --output monitor.mjpeg
```

保存画像をすべて削除します。撮影停止中のみ実行でき、削除は元に戻せません。

```bash
curl -X DELETE http://zuizui.local:8000/images \
  -H "Content-Type: application/json" \
  -d '{"confirm": "DELETE_ALL"}'
```

背景差分による自動間隔調整を開始します。低解像度の輝度差分で動き候補を判定し、
候補がない時は間隔を長くして消費電力と保存枚数を抑えます。昆虫の分類ではないため、
風で揺れる葉や影の変化も候補として記録される場合があります。

```bash
curl -X POST http://zuizui.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 60, "auto_mode": true, "autonomous_mode": true, "idle_interval_sec": 60, "detection_interval_sec": 3}'
```

自動モードの判定履歴は各 Raspberry Pi の
`~/pollipi_timelapse/images/adaptive_metrics.csv` に保存されます。

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
