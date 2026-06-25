# visit_labels Data Dictionary

`visit_labels.csv`（人手ラベル）の列定義。雛形は `visit_labels.example.csv`。
本表は **人手による訪花真値**を記録するためのもので、mesh / three-stage の判定
（`strong_visitation_candidate` 等）は**この表に書かない**。mesh 判定は
`adaptive_probe_shadow-1.csv`（一次ログ）から `device_id` ＋ `image_filename` で結合する。

> 役割の分離（最重要）
> - **`visit_present`**: 画像を見て人が決める**訪花の真値**（0/1）。これがラベルの中心。
> - **`false_trigger_cause`**: 「probe が candidate を出したのに `visit_present=0`」だった場合に限り、
>   その**誤作動の原因**を記録する分析用フィールド。**訪花真値ではない**。

## 入力2段階
- **(I) blind image labeling**: probe ログを見ずに画像だけで判定する段階。
- **(R) probe結合後 reconciliation**: probe ログと candidate window を突き合わせた後の段階。

## 列定義
| 列名 | 型 | 必須区分 | 入力時点 | 許容値 / 記入規則 | 欠損時の扱い | 研究上の意味 |
|---|---|---|---|---|---|---|
| `label_id` | string | 必須 | (I) | 一意。例 `L0001` | 不可（必須） | 行の一意識別 |
| `reviewer_id` | string | 必須 | (I) | 仮名/コード。実名は使わない | 不可 | レビュア間一致(IRR)評価 |
| `reviewed_at` | datetime(ISO8601, tz offset付) | 必須 | (I) | 例 `2099-05-01T10:15:30+09:00` | 不可 | レビュー時刻の監査 |
| `device_id` | string | 必須 | (I) | Pi 識別子（結合キー） | 不可 | device 横断の結合・層別 |
| `run_id` | string | 条件付き必須 | (R) | 1 回の start→stop。v1で不明なら推定値 `inferred_<device>_<ts>` | 推定値可・空は不可 | run 単位追跡（VALIDATION §7） |
| `image_filename` | string | 必須 | (I) | 対象高解像度 JPEG 名（結合キー） | 不可 | probe / decisions との結合 |
| `highres_captured_at` | datetime(ISO8601, tz offset付) | 必須 | (I) | 画像の撮影時刻 | 不可 | 時系列整列・window 対応 |
| `timezone` | string(IANA) | 必須 | (I) | 例 `Asia/Tokyo` | 既定 `Asia/Tokyo` | device clock 正規化 |
| `visit_present` | int(0/1) | 必須 | (I) | 1=訪花あり, 0=なし | 不可 | **訪花の唯一の真値** |
| `visitor_taxon` | string | 条件付き必須 | (I) | `visit_present=1` のとき記入。例 `Apis_sp`/`Bombus_sp`/`Syrphidae`/`unknown` | `visit_present=0` は空 | 訪花者群・種同定 |
| `visitor_count` | int(>=0) | 条件付き必須 | (I) | `visit_present=1` のとき>=1, `=0` のとき 0 | 0 で補完 | 個体数・重複 burst 補正 |
| `behavior` | enum | 条件付き必須 | (I) | `visiting`/`passing`/`resting`/`none` | `none` で補完 | 滞在/通過の区別 |
| `on_focal_flower` | int(0/1) | 条件付き必須 | (I) | 1=焦点花上, 0=非焦点 | `visit_present=0` は 0 | 焦点花の訪花に限定した解析 |
| `confidence` | int(1-3) | 必須 | (I) | 1=低,2=中,3=高 | 不可 | ラベル確信度の重み付け |
| `image_quality` | enum | 必須 | (I) | `good`/`blurred`/`overexposed`/`dark`/`unusable` | 不可 | 品質管理・評価可否判断 |
| `occlusion` | enum | 必須 | (I) | `none`/`partial`/`heavy` | 既定 `none` | 遮蔽による見落とし評価 |
| `false_trigger_cause` | enum | 条件付き必須 | (R) | 下記「入力規則」参照 | 既定 空欄 | **candidate 誤作動の原因分析（真値ではない）** |
| `notes` | string | 任意 | (I)/(R) | 自由記述（カンマは避ける） | 空可 | 補足 |

## `false_trigger_cause` の入力規則（限定）
- **入力対象は次の場合のみ**: probe ログ上で candidate event が存在し、その candidate 評価窓に対する
  人手判定が **`visit_present=0`** であるとき。
- **blind image labeling 段階（I）では原則空欄**にする。
- probe ログとの結合・candidate window の再確認（R）後に、
  `wind` / `cloud_shadow` / `flower_sway` / `camera_shake` / `non_focal_insect` / `unknown`
  などを入力する。
- **candidate が存在しない通常の非訪花画像では空欄**にする。
- 繰り返し: `false_trigger_cause` は訪花真値ではなく、**candidate 誤作動の原因分析用**である。

## 注意
- 実 Pi 名・実画像名・実時刻・実観察者名は雛形に使わない（`visit_labels.example.csv` は架空）。
- ISO 8601 日時には必ず timezone offset を付ける。
- mesh 判定列（decision_state 等）はここに持たず、probe ログから結合する。
