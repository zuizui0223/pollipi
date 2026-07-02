# PolliPi 現行運用ガイド

この文書は、現在5台に配布済みの PolliPi（packaged artifact）を、研究室Wi-Fiまたはインターネットなしの野外routerで使うための操作手順です。

## まず知っておくこと

- PolliPiの主記録は、指定間隔で保存される**高解像度JPEGタイムラプス**です。
- 低解像度probeは既定で5秒ごとに動きますが、probe JPEGは保存しません。
- mesh判定は補助メタデータです。`strong_visitation_candidate` は訪花確認ではありません。
- `live adaptive` は現在OFFです。shadow modeは「次にどの間隔を選ぶか」を記録するだけで、実際の撮影間隔を変えません。
- iPadは操作・確認用です。Start済みのPiは、iPadやrouterとの接続が切れても予定撮影を続ける設計です。
- 中央サーバー／coordinatorは、現在の同一LAN内5台運用では使いません。

## 画面の見方

### 上部: Field mode

- `sec baseline`: 保存する高解像度JPEGの間隔。通常は **30 sec**。
- `Resume autonomously after Pi restart`: ONにしてStartすると、Pi再起動後に同じ撮影設定で再開するための設定を保存します。
- `Approved policy profile`: Webの4モード（①plain／②motion／③classified／④video）は対応する canary プロファイルを自動選択します。コード既定は `three_stage_default_v1`。
- `Start all` / `Stop all`: iPadに登録されたPiへ直接送信します。中央サーバーを経由しません。

### 各Piカード

- `stopped`: 撮影停止中です。
- `capturing`: 高解像度タイムラプス中です。
- `High-res interval`: 実際のJPEG保存間隔。
- `Saved photos`: 今回のsessionで保存した高解像度JPEG数です。
- `Last saved`: 最後に高解像度JPEGを保存した時刻です。ここが更新されれば撮影成功です。
- カード上の写真: 最新保存済みJPEGです。撮影中も最後に保存された画像を表示します。
- `Probe interval`: 低解像度解析の間隔。現在は通常5 sec。
- `Would-be mode` / `Would-be interval`: shadow modeが提案する仮想の次段階。実際の撮影間隔は変わりません。
- `Shadow only`: `on` であることを確認します。
- `Policy profile`: 開始時に選んだprofileです。
- `server ... / bundled web ...`: server artifactに埋め込まれたbuild情報です。web-only更新後は、実際に配信中のPWA buildと異なる場合があります。現在のPWA versionは `/app/build-info.json` で確認します。

通常のカードはMJPEGを自動で開きません。これにより、5台を一覧表示してもカメラやWi-Fiを不要に占有しません。ライブプレビューは今後、必要な1台だけを明示的に開く機能として扱います。

## 研究室Wi-Fiでの使い方

1. iPadとPiを同じWi-Fiに接続します。
2. 任意のPiで `http://<PiのIP>:8000/app/` をSafariで開きます。
3. ホーム画面に追加する場合は、Safariの共有メニューから追加します。
4. `Add Raspberry Pi` に他のPiのIPを1台ずつ入力します。例: `192.168.11.18`。
5. 5台がonlineになることを確認します。
6. `30 sec baseline`、`three_stage_default_v1`、`Resume autonomously after Pi restart` を設定します。
7. `Start all` を押します。
8. 各カードで `capturing`、`High-res interval = 30 sec`、`Shadow only = on` を確認します。
9. 少なくとも2回以上、`Saved photos` と `Last saved` が進むことを確認してからiPadを閉じます。

## 野外routerだけでの使い方

WANやSIMは不要です。routerは、PiとiPadを同一LANへ入れるためのWi-Fi親機として使います。

### router設定

- SSID・パスワードを固定する。
- DHCPをONにする。
- Guest networkやAP/client isolationをOFFにする。
- 5台のPiへDHCP reservationを設定する。Pi側へ固定IPを直接書き込むより安全です。
- 例として `192.168.8.0/24` を使うなら、Piを `.11` から `.15` に予約します。

### iPad側

- field routerのSSIDへ接続します。
- 必要なら機内モードをONにしてWi-Fiだけ有効にします。
- 研究室のIP登録は、field routerの予約IPへ置き換えます。
- まずconsole用Piの `http://192.168.8.11:8000/app/` を開き、残り4台を登録します。

### field sessionの開始

1. routerを起動します。
2. Piを起動します。
3. iPadをrouterへ接続します。
4. 5台がonlineになったことを確認します。
5. `30 sec baseline`、`three_stage_default_v1`、autonomous resumeを設定します。
6. Start allを押します。
7. 各Piで`Saved photos`と`Last saved`が進むことを確認します。

## 途中でiPad・routerが切れたとき

- iPadが切れても、Start済みのPiは予定撮影を続ける設計です。
- routerが切れても、Pi内の撮影処理とSD保存は続く設計です。
- router復帰後、Piが再接続すればiPadから再びstatusを読めます。
- ただし野外投入前に、5台それぞれで「iPad断」「router断」「Pi再起動」を実機確認してください。

## session終了

- `Stop all` を押すと、autonomous resume用の設定も消えます。
- 保存JPEGとshadow CSVは各PiのSDカードに残ります。
- 画像を消す操作は、回収・バックアップ完了後に別途行います。

## 迷ったときの確認順

1. iPadとPiが同じSSID／同じLANにいるか。
2. PiのIPをSafariで直接開けるか。例: `http://192.168.11.17:8000/device`。
3. `Saved photos` と `Last saved` が進んでいるか。
4. PWAのbuild表示が配布済みbuildと一致しているか。
5. 新UIが見えないときはSafariを閉じて開き直すか、URL末尾に `?build=<commit>` を付けて開きます。
