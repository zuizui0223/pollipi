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
3. 比較調査では `研究用：定間隔 + 動き時に追加撮影（推奨）` と `自律運行` を有効にして撮影を開始します。
4. iPad や携帯が離れても、定間隔撮影と動き候補の追加保存は Raspberry Pi 単独で継続します。
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
ExecStart=/home/zuizui0223/pollipi_timelapse/.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000 --timeout-graceful-shutdown 3
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now pollipi.service
```

`--timeout-graceful-shutdown 3` は、画角モニターなどの持続接続が残っていても、
サービス更新や再起動が長時間停止待ちにならないための設定です。

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

### Field mode start form

野外で迷わず開始できるよう、PWA の開始フォームは Field mode を標準表示にしています。
通常表示されるのは `site_id`、`flower_id`、`plant_species`、`method_mode`、撮影間隔、
背景差分の自動調整、各観察機カードの `画角を確認`、`ROIを指定`、必要な場合の `花の揺れに追従`、
開始・停止だけです。ROI はプレビュー画像上で花や花序を囲むのが標準で、数値入力は不要です。

`Advanced settings` には、`observer`、`notes`、`comparison_session_id`、`camera_role`、
`pixel_difference`、`motion_ratio`、`idle_interval_sec`、`detection_interval_sec`、
および生の `roi_x`、`roi_y`、`roi_w`、`roi_h` を置いています。各観察機カードの
`Advanced ROI tracking` には `roi_search_margin` と `roi_tracking_min_score` があります。
これらはデバッグや比較実験用で、通常の現地操作では開かなくて大丈夫です。

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
- 比較研究向けの定間隔撮影 + 動き候補追加撮影と観察努力ログ
- iPad への個別画像保存、`all` / `positive` / `negative` の ZIP 回収
- 全体画像、虫あり候補 (`positive`)、虫なし候補 (`negative`) の3フォルダ閲覧とラベル修正
- 調査日をまたいで累積する確認済み画像による二値モデル学習と、保存写真だけへの低負荷現地判定
- 通信切断や電源復帰後にも撮影を続ける自律運行

iPad の Safari で共有ボタンから「ホーム画面に追加」を選ぶと、PolliPi を
アプリアイコンのように起動できます。App Store 公開なしでも利用者へこの導入手順と
Pi 用プログラムを GitHub から配布できます。画面は 4 秒ごとに状態を更新します。
`画角モニター` は設置時の向き確認用です。長時間観察ではモニターを停止し、
自律運行を使う方が電力消費を抑えられます。

## AI Camera の簡易物体検出試験

`zuizui2.local` の AI Camera (`imx500`) にはセンサー内でニューラルネット推論を
実行する機能があります。標準でインストールされる MobileNet SSD は一般物体の検出用で、
標準ラベルに `insect` はありません。したがって昆虫の種類判別には専用の学習モデルが
必要ですが、AI Camera と Module 3 の検出方式を分けて試す第一段階として利用できます。

`imx500_detect_test.py` は AI Camera だけで短時間の物体検出を行い、枠付きの確認画像と
JSON 結果を `~/pollipi_timelapse/imx500_detect_trials/` に保存します。カメラを一つの
プロセスだけで使用するため、試験中は AI Camera 側の API サービスを一時停止します。

```bash
ssh zuizui0223@zuizui2.local
sudo systemctl stop pollipi.service
cd /home/zuizui0223/pollipi_timelapse
python3 imx500_detect_test.py --duration-sec 15 --threshold 0.55
sudo systemctl start pollipi.service
```

PWA に AI Camera を登録すると、その観察機のカードに `AI検出モニター` ボタンが表示されます。
このボタンでは、IMX500 標準モデルが検出した対象に枠・名前・信頼度を重ねて画角を確認できます。
AIモデルの読み込みには開始時に数秒かかります。この表示は保存画像には追加されません。
現在は通常のタイムラプス撮影とカメラを共用するため、AI検出モニターは撮影停止中の確認用です。

APIから枠付きモニターを確認する場合:

```bash
curl "http://zuizui2.local:8000/mjpeg?detect=true" --output ai-monitor.mjpeg
```

この結果は AI Camera の標準モデルによる一般物体検出です。Module 3 側で動かしている
背景差分は「動いた候補」を検出する方法なので、同じ場所と時間帯で保存結果を比較すると、
将来の昆虫専用モデル設計や省電力な撮影間隔調整の検討材料になります。

公式資料: [Raspberry Pi AI Camera documentation](https://www.raspberrypi.com/documentation/accessories/ai-camera.html)

## 研究設計: 比較できる記録を残す

PolliPi の主データには `研究用：定間隔 + 動き時に追加撮影（推奨）` を使います。
このモードは `interval_sec` ごとに `scheduled_*.jpg` を必ず保存し、その間に背景差分で
動き候補を検知すると `event_*.jpg` を追加保存します。動きだけを頼りにすると小型・低速の
昆虫や花上で静止する訪花を落としやすいため、`scheduled_*.jpg` を観察努力が一定な比較用
データ、`event_*.jpg` を確認効率を上げる補助データとして分けます。

各チェック時点は `~/pollipi_timelapse/images/observation_events.csv` に記録されます。
`capture_type` は `scheduled`、`scheduled_event`、`event`、`none` のいずれかです。
訪花頻度や Module 3 / AI Camera 間の捕捉率比較では、まず `scheduled` と
`scheduled_event` を同じ撮影間隔・同じ観察時間で集計し、`event` は補助解析に分けます。

Module 3 と AI Camera を比較するフィールド試験では、次を固定または交替させて記録します。

- 同じ対象植物、花序の範囲、距離、画角、撮影間隔、撮影時間帯、観察時間
- 左右や場所の差がカメラ差にならないよう、別日または時間ブロックでカメラ位置を交替
- 一部の画像を人が同定して基準データにし、画像差分や AI 出力の見落とし・誤検出を評価
- 標準 IMX500 モデルの名前は一般物体ラベルであり、昆虫の種同定結果として扱わない

`背景差分で撮影間隔を自動調整` と `動いた時だけ撮影` は、省電力や候補抽出の探索試験には
使えますが、観察努力が一定ではありません。定間隔調査の生の訪花数と直接比較する場合は、
撮影機会の差を補正する検証が必要です。

## Methods paper workflow: event-based and human-in-the-loop monitoring

PolliPi は、直接観察・通常タイムラプス・イベントベースタイムラプスを同じ調査単位で比較するための
フィールドワークフローとして設計しています。中心になるデータ単位は `event_log.csv` に保存される
候補相互作用イベントです。各イベントには、対象花、植物種、観察者、カメラプロファイル、ROI、
背景差分の指標、後日の手動レビュー結果をまとめて残します。

PWA の `EVENT REVIEW` では、候補イベントを iPad で確認し、`insect`、`non_insect`、`unclear` を
ラベルできます。風、影、花の揺れ、カメラ揺れ、非昆虫物体、照明変化などの false positive reason も
記録できます。レビュー済みイベントは `/events/export_labels.csv` からCSVとして出力でき、将来の
軽量な insect / non-insect フィルタ更新に使う教師データになります。この版では、昆虫の種同定、
ニューラルネットワーク学習、動画記録、クラウド同期は行いません。

例1: Module 3 vs AI Camera comparison

- 両方の観察機に同じ `comparison_session_id` を入れる
- Module 3 側は `camera_role=module3_reference`、AI Camera 側は `camera_role=ai_camera_test` にする
- `event_count`、motion metrics、false positive reason、画像品質を比較する

例2: Direct observation benchmark

- 30-60分の人による直接観察と同時に PolliPi を動かす
- `site_id`、`flower_id`、`plant_species`、`observer` を入れる
- `method_mode=direct_observation_parallel` として開始する
- セッション後にイベントをレビューし、人が記録した訪花と PolliPi の候補イベントを照合する

例3: Same-day learning preparation

- 日中にイベント候補を蓄積する
- 夕方または帰室後に 50-200 件ほどを `EVENT REVIEW` でラベルする
- `/events/export_labels.csv` を出力する
- 将来版の軽量モデル更新やイベントフィルタ調整に使う

注意: 背景差分とblob特徴量は昆虫分類ではありません。風、影、花の動き、照明変化は false positive を
生みます。MEE-1 の目的は、それらの誤検出も含めて検証可能なログにすることです。

## Camera comparison experiments

Module 3 Wide と AI Camera を横に並べて比較する時は、同じ `comparison_session_id` を使い、
各カメラに `camera_role` を割り当てます。PWA の開始フォームに `site_id`、`flower_id`、
`observer`、`notes`、`comparison_session_id`、`camera_role` を入れて開始すると、
`/status`、`adaptive_metrics.csv`、`event_log.csv` にカメラ情報と調査メタデータが一緒に残ります。
厳密な同時シャッター同期はまだ行わず、同じ撮影間隔・同じ観察時間帯で後から比較します。

Module 3 Wide 側の起動例:

```bash
POLLIPI_DEVICE_NAME='Site 01' \
POLLIPI_CAMERA_LABEL='Module 3 Wide' \
POLLIPI_CAMERA_MODEL='imx708_wide' \
POLLIPI_CAMERA_PROFILE=module3_wide_daylight \
POLLIPI_IS_AI_CAMERA=false \
POLLIPI_IS_NOIR=false \
POLLIPI_IS_WIDE=true \
.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

AI Camera 側の起動例:

```bash
POLLIPI_DEVICE_NAME='Site 02' \
POLLIPI_CAMERA_LABEL='AI Camera' \
POLLIPI_CAMERA_MODEL='imx500' \
POLLIPI_CAMERA_PROFILE=ai_camera_daylight \
POLLIPI_IS_AI_CAMERA=true \
POLLIPI_IS_NOIR=false \
POLLIPI_IS_WIDE=false \
.venv/bin/python -m uvicorn pollipi_api_server:app --host 0.0.0.0 --port 8000
```

比較手順:

- Module 3 Wide と AI Camera を同じ対象植物・同じ花・近い画角に設置する
- PWA に両方の観察機を登録する
- 両方に同じ `comparison_session_id` を使う
- Module 3 側は `camera_role=module3_reference`、AI Camera 側は `camera_role=ai_camera_test` として開始する
- 回収後に `adaptive_metrics.csv` と `event_log.csv` を比べ、撮影枚数、動き候補数、イベント候補数、保存効率を集計する

この段階では AI 昆虫分類、NoIR 専用補正、動画記録、厳密な同期は実装していません。目的は、
後で Camera Module 3 Wide と AI Camera の捕捉率や誤検出傾向を比較できるログを確実に残すことです。

## Phase 1 field-method improvements

Phase 1 では、直接観察・通常タイムラプス・PolliPiイベント検出を後で比較できるよう、
撮影時の調査メタデータ、ROI、イベントログを記録します。`/start` には任意で
`site_id`、`flower_id`、`observer`、`notes` を渡せます。これらは
`adaptive_metrics.csv`、`observation_events.csv`、`event_log.csv` に保存されます。

ROI を指定すると、低解像度モニターフレーム `640 x 360` のうち、その範囲だけで背景差分を
計算します。たとえば花だけを囲むことで、背景の枝葉や人の影によるノイズを減らせます。
ROI を指定しなければ従来通り全画面で判定します。

```bash
curl -X POST http://zuizui.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{
    "interval_sec": 60,
    "hybrid_mode": true,
    "site_id": "site_A",
    "flower_id": "plant_03_flower_01",
    "observer": "Zuizui",
    "notes": "south plot, sunny",
    "roi_x": 180,
    "roi_y": 70,
    "roi_w": 260,
    "roi_h": 180
  }'
```

`event_log.csv` は後の方法比較で使う「候補相互作用イベント」の単位です。動き候補が出た時だけ
`event_id`、時刻、画像名、調査メタデータ、差分スコア、ROI情報、風のような大面積変化の目印を
記録します。`manual_label`、`manual_taxon`、`manual_notes` は後日の手動レビュー用の空欄です。

現在の制限として、これは昆虫分類ではありません。風、影、花や葉の揺れでも false positive が
発生し、小さい昆虫や静止中の訪花は false negative になる可能性があります。その誤差を
`event_log.csv` と後日の手動レビューで評価する設計です。

## Phase 2 blob-based motion filtering

Phase 2 では、Phase 1 の背景差分マスクに軽量な連結成分解析を追加します。ROI が指定されている場合は
ROI内、指定がない場合は低解像度フレーム全体で、変化したピクセルのまとまりを blob として数えます。
追加で `num_blobs`、`largest_blob_area`、`largest_blob_ratio`、`small_blob_count`、`motion_type` を
`/status`、`adaptive_metrics.csv`、`event_log.csv` に記録します。

`motion_type` は次の5種類です。

- `none`: 閾値未満の変化
- `small_object_motion`: 小さいblobを含む、訪花昆虫候補として保存する動き
- `wind_like_large_motion`: 花全体、葉、背景植生などが大きく動いた可能性が高い変化
- `global_brightness_change`: 影や露出変化のように画面全体の明るさが変わった可能性が高い変化
- `noisy_motion`: 小さい候補にも大面積変化にも分類しにくいノイズ的な変化

イベント候補として `event_log.csv` に入るのは主に `small_object_motion` です。これにより、風で花全体が
揺れる場面や、雲・影で明るさが変わる場面を、訪花候補から少し分けて扱えます。ただし、昆虫が大きく写る、
花そのものが小さく揺れる、複数の小さい影が出るなどの場合はまだ誤判定が残ります。Phase 2 の目的は
昆虫分類ではなく、後で false positive / false negative / review time / storage efficiency を評価するための
特徴量を増やすことです。

## Human-in-the-loop event review

`event_log.csv` に保存された動き候補は、PWA の `EVENT REVIEW` で確認できます。各イベントについて、
画像、時刻、`site_id`、`flower_id`、`camera_profile`、`motion_score` を見ながら
`insect`、`non_insect`、`unclear` の手動ラベルを付けられます。必要に応じて `manual_taxon`、
`manual_notes`、false positive の理由も記録します。

false positive reason は `wind`、`shadow`、`flower_movement`、`camera_shake`、
`non_insect_object`、`unclear`、`other` から選びます。

```bash
curl http://zuizui.local:8000/events

curl -X POST http://zuizui.local:8000/events/evt_20260528_120000_000000_abcd1234/label \
  -H "Content-Type: application/json" \
  -d '{"manual_label": "non_insect", "false_positive_reason": "wind", "manual_notes": "flower moved in wind"}'

curl -OJ http://zuizui.local:8000/events/export_labels.csv
```

`events/export_labels.csv` は、将来の insect / non-insect 分類器を作るための教師データとして使う想定です。
現時点ではニューラルネットワークやモデル更新は実装していません。調査当日の夕方などに人がイベントを確認し、
ラベル付きCSVを作っておけば、将来版ではその日のうちに軽量モデルを更新する流れへつなげられます。

PWA の画面には、この設計が対応する研究ギャップを表示します。画像は原本の `images/`
を必ず残し、まず自動判定による学習データ用の仮ラベルとして `images/positive/` と
`images/negative/` にも登録されます。iPad ではすべてを1枚ずつ分類する必要はなく、
基本は自動振り分けのまま使い、間違いを見つけた時だけ `positiveに修正` または
`negativeに修正` を押します。重要な画像だけ `この分類でOK` として確認済みにできます。
可能なファイルシステムでは原画像へのハードリンクを
作成するため余分な容量消費を抑え、対応しない USB 保存装置ではコピーへ切り替わります。
自動ラベルは昆虫または訪花の確定記録ではないため、重要な解析では誤分類だけ重点的に確認してください。

## 日をまたぐ二値学習と省電力運用

`positive` と `negative` は自動判定結果として削除しない限り Raspberry Pi に累積します。したがって、
1日目の調査画像を自動振り分けし、必要な誤分類だけ iPad で修正して、帰宅後に充電器と Wi-Fi に接続して
`この観察機で再学習` を押すと、2日目以降は前日までのデータを使ったモデルを利用できます。
各 Pi は設置場所やカメラが違うため、学習モデルも観察機ごとに作成・表示します。

PWA の `学習済みモデルで保存写真を positive / negative に仮分類（低負荷）` を有効にすると、
学習済みの OpenCV SVM モデルが、新たに保存された写真だけを判定して仮フォルダへ振り分けます。
動画を常時ニューラル推論するのではなく、すでに保存する画像にだけ処理を追加するため、
現地バッテリーの負荷を抑えます。また、モデル判定で定間隔撮影の有無や撮影努力を変えないため、
Module 3 と AI Camera の比較データを保ちやすい設計です。

学習は撮影停止中のみ開始でき、最低 `positive` 2枚と `negative` 2枚が必要です。
精度表示を得るには各ラベル5枚以上、研究用途ではより多くの人手確認画像を蓄積してください。
試行学習や誤ったラベルで作成したモデルは、PWA の `モデルを破棄` で消去できます。
画像ラベルは残るため、修正後に再学習できます。

## iPad への画像回収

画像一覧の各写真にある `iPadに保存` を押すと、その JPEG を iPad で開く、または
ダウンロードできます。Safari の表示になった場合は共有メニューから `画像を保存` または
`ファイルに保存` を選びます。`全画像とログをZIP保存` は画像に加えて
`observation_events.csv`、`adaptive_metrics.csv`、`image_labels.csv`、モデル情報が
存在する場合に同梱します。`positive をZIP保存` と `negative をZIP保存` は、
確認済み学習データの回収やバックアップに利用できます。

iPad への保存後も Raspberry Pi の原画像は残ります。調査データを失わないよう、
ZIP の内容を確認してからアプリの削除操作を使う運用にしています。

設計の根拠:
[Droissart et al. 2021, PICT](https://doi.org/10.1111/2041-210X.13618) /
[Pegoraro et al. 2020](https://doi.org/10.1042/ETLS20190074) /
[Naqvi et al. 2022](https://doi.org/10.1002/ece3.8962) /
[Watazu et al. 2025](https://doi.org/10.1002/aps3.70023) /
[Roy et al. 2016](https://doi.org/10.1371/journal.pone.0150794) /
[Gibson et al. 2011](https://doi.org/10.1111/j.1600-0706.2010.18927.x) /
[Høye et al. 2025](https://doi.org/10.1016/j.cois.2025.101367)

## 現地運用の保存容量と電源状態

PWA の各観察機カードには、画像保存先の空き容量と Raspberry Pi の電圧状態を表示します。
`保存容量` は `POLLIPI_IMAGE_DIR` が置かれているストレージの空き容量です。USB SSD や
USB メモリへ保存する場合は、マウントした保存先をサービス環境変数に指定します。

```ini
Environment="POLLIPI_IMAGE_DIR=/media/zuizui0223/POLLIPI/images"
```

`電源状態` は Raspberry Pi の `vcgencmd get_throttled` を使って、現在または起動後に
電圧低下が起きたかを表示します。一般的なモバイルバッテリーは、USB接続だけでは残量％を
Raspberry Pi に通知しません。残量％をアプリに表示するには、残量情報を読み出せる
UPS HAT または電源計測機器を追加する設計が必要です。Pi 5 とUSB保存装置を同時に使う
現地運用では、十分な5 V出力とケーブル品質も重要です。

```bash
curl http://zuizui.local:8000/system
```

公式資料:
[Raspberry Pi power supply requirements](https://www.raspberrypi.com/documentation/installation/installing/raspberry-pi.html#power-supply) /
[`vcgencmd get_throttled`](https://www.raspberrypi.com/documentation/computers/os.html#vcgencmd)

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
curl "http://zuizui.local:8000/images?limit=40&collection=positive"
curl "http://zuizui.local:8000/images?limit=40&collection=negative"
```

一覧にある画像を取得、または削除します。削除は元に戻せません。

```bash
curl http://zuizui.local:8000/images/image_20260526_143010_123456.jpg --output selected.jpg
curl -X DELETE http://zuizui.local:8000/images/image_20260526_143010_123456.jpg
```

画像単体または ZIP を iPad/PC にダウンロードします。

```bash
curl -OJ "http://zuizui.local:8000/images/image_20260526_143010_123456.jpg?download=true"
curl -OJ "http://zuizui.local:8000/exports/images.zip?collection=all"
curl -OJ "http://zuizui.local:8000/exports/images.zip?collection=positive"
curl -OJ "http://zuizui.local:8000/exports/images.zip?collection=negative"
```

画像ラベルを iPad または API から必要な分だけ修正し、帰宅後に学習を開始します。

```bash
curl -X POST http://zuizui.local:8000/images/event_20260527_130821_230183.jpg/label \
  -H "Content-Type: application/json" \
  -d '{"label": "positive"}'

curl -X POST http://zuizui.local:8000/images/event_20260527_130821_230183.jpg/label \
  -H "Content-Type: application/json" \
  -d '{"label": "confirmed"}'

curl http://zuizui.local:8000/training/status
curl -X POST http://zuizui.local:8000/training/start
curl -X DELETE http://zuizui.local:8000/training/model
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

比較研究に推奨するハイブリッド観察を開始します。定間隔画像は必ず保存され、間隔の間に
動き候補があると追加画像を保存します。`detection_interval_sec` は追加候補を確認する間隔です。

```bash
curl -X POST http://zuizui.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 60, "hybrid_mode": true, "ml_assist_mode": true, "autonomous_mode": true, "detection_interval_sec": 3}'
```

ハイブリッド観察の努力量と画像種別は
`~/pollipi_timelapse/images/observation_events.csv` に保存されます。

通常のタイムラプスとは別に、動き候補が出た時だけ撮影して保存する観察もできます。
PWA の `動いた時だけ撮影（画像差分）` を有効にするか、APIで次のように開始します。
`detection_interval_sec` は低解像度で動きを確認する間隔で、候補を検知した時だけ
`motion_*.jpg` が保存されます。虫の確定判定ではないため、葉や影の動きも保存候補になります。

```bash
curl -X POST http://zuizui.local:8000/start \
  -H "Content-Type: application/json" \
  -d '{"interval_sec": 60, "motion_trigger_mode": true, "autonomous_mode": true, "detection_interval_sec": 3}'
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

## Setting camera angle and ROI from the iPad

The iPad PWA separates camera-angle checking from ROI selection.

1. Open the PWA for a device, for example `http://zuizui.local:8000/app/`.
2. Tap `画角を確認` to open the live low-power monitor.
3. Adjust the camera so the focal flower/head is near the center of the image.
4. Tap `この画角でOK`. PolliPi closes the live monitor and fetches a still frame from `/preview`.
5. Draw a rectangle around the flower or flower head on the frozen still image.
6. If needed, drag inside the rectangle to move it, drag an edge or corner to resize it, or use `リセット` to redraw it.
7. Tap `このROIで決定` to save the ROI.
8. Start recording. The backend receives the current valid ROI in the `/start` payload.

The main card shows `画角: 確認済み` and `ROI: 設定済み` after this sequence. If the camera angle is changed later,
tap `画角を再調整`; the old ROI is cleared or marked invalid, and the user must select the flower again from the new
still frame. PolliPi blocks starting with a stale ROI so old coordinates are not silently reused after camera movement.

Use `ROIを解除` to return to full-frame motion detection. When ROI is cleared, the `/start` request omits
`roi_x`, `roi_y`, `roi_w`, and `roi_h`. Restricting motion detection to the flower area helps reduce false positives
from moving leaves, background vegetation, and shadows.

Optional lightweight ROI tracking can be enabled with `花の揺れに追従` after a fixed ROI has been drawn. Tracking targets
the selected flower/head, not insects. On the first low-resolution frame, PolliPi stores the ROI luminance patch as
a template. During recording it searches near the previous ROI and, when the template match score is high enough,
moves the ROI with the flower/head before motion detection. If matching fails, it keeps the previous ROI. The
template is not updated during recording, which reduces the risk that a visiting insect pulls the ROI away from the
flower. Tracking metrics are stored as `roi_tracking_score`, `roi_tracking_success`, `roi_shift_x`, and
`roi_shift_y` in `/status`, `adaptive_metrics.csv`, and `event_log.csv`.

Automatic flower detection is not implemented in this field workflow. Future versions may use a flower detector to
suggest ROI automatically. This version does not use YOLO, species identification, neural network training, or video
recording.

## NoIR / infrared camera setup

PolliPi can register a Raspberry Pi Camera Module 3 NoIR unit as a separate observation device. The backend uses
environment variables to mark the camera profile, and the iPad PWA shows an `IR / NoIR` badge when the device reports
`POLLIPI_IS_NOIR=true`.

Recommended NoIR environment values:

```bash
POLLIPI_CAMERA_LABEL="Module 3 NoIR Wide"
POLLIPI_CAMERA_MODEL=imx708_noir_wide
POLLIPI_CAMERA_PROFILE=module3_noir_wide_ir
POLLIPI_IS_AI_CAMERA=false
POLLIPI_IS_NOIR=true
POLLIPI_IS_WIDE=true
```

For comparison experiments, use `camera_role=noir_test` and write the IR illuminator wavelength and power in `notes`,
for example `850nm IR LED, low power`. NoIR/IR images should not be compared directly with daylight RGB images without
recording the illumination condition.

When the new Pi is connected to the same network, the prepared Windows deployment script can copy the current source
files and set the NoIR service profile:

```powershell
$env:POLLIPI_DEPLOY_PASSWORD = "your_pi_password"
.\deploy_pollipi_pi.ps1 -HostName zuizui3.local -Preset module3-noir-wide
```

The script syncs only source files (`pollipi_api_server.py`, `README.md`, `imx500_detect_test.py`, and `web/`) and
then restarts `pollipi.service`. It does not copy captured images, logs, CSV event data, or runtime caches.
