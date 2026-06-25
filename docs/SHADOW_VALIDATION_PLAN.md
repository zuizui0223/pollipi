# PolliPi Shadow Validation Plan

本書は、PolliPi の mesh 判定および three-stage probe-only shadow 出力が「実際の訪花」に
どれだけ対応するかを検証するための研究計画である。本書はデータ解析計画であり、
**コード・Pi runtime・service・deploy 設定・既存 CSV・画像を一切変更しない**。

> 重要な前提
> - `strong_visitation_candidate` は **訪花確定ではない**。
> - 訪花の有無・訪花者群は、保存された高解像度タイムラプス JPEG を人が確認して初めて評価する。
> - 本フェーズでは **live adaptive capture / live burst を有効化しない**（shadow のみ）。
> - Pi は simulation / parameter search / pandas / matplotlib を実行しない。解析は dev 機側で行う。

---

## 1. 目的・スコープ
- mesh パイプライン（pipeline.py）と three-stage controller（three_stage.py）が出力する
  decision state / would-be mode が、人手ラベルした実訪花とどれだけ一致するかを定量化する。
- 誤検知（false trigger）・見逃し（false negative）・分類群別検出率・環境要因別の偏りを評価する。
- 「保存枚数」「trigger 回数」を訪花頻度と同一視せず、**検出確率 × 観測努力**で扱う解析を確立する。
- 本書の成果は、後続の virtual burst shadow（HYBRID_CAPTURE_ROADMAP.md）と
  fixed / pure trigger / hybrid 比較研究の入力となる。

## 2. ログの正準（データソースの役割）
本プロジェクトのログは役割を固定する（詳細は `SHADOW_LOG_DATA_CONTRACT_V2.md`）。

| ログ | 役割 | 備考 |
|---|---|---|
| `adaptive_probe_shadow-1.csv` | **一次ログ** | probe 毎 1 行・15 列・世代一貫。解析の主入力。 |
| `adaptive_decisions.csv` | **補助ログ** | high-res 保存時の決定記録（6 列）。 |
| `adaptive_metrics.csv` | **一次解析から除外** | 同一ファイル内に 6/30/37 列が混在する legacy/mixed schema。 |

## 2.1 現行 v1 ログの追跡限界（重要）
- 現行 v1 の `adaptive_probe_shadow-1.csv`（15 列）には、`device_id` / `run_id` / `timezone` /
  `saved_image_filename` / `scheduled_highres_timestamp` / `policy_profile_id` /
  `simulation_run_id` / `source_server_build` / `source_web_build` が
  **完全には記録されていない**。
- そのため現行データの結合は、**Pi の保存先・時刻近傍・status 記録・ファイル mtime** などに依存する
  **暫定的な復元**である。
- **厳密な run 単位追跡は v2 schema 導入後に初めて可能**になる（`SHADOW_LOG_DATA_CONTRACT_V2.md`）。
- v1 ログからの推定結合結果には **`join_confidence`（または同等の品質区分）** を付けて扱う。

## 3. 人手ラベル CSV（`visit_labels.csv`）
高解像度 JPEG 1 枚を 1 行としてラベル付けする。列は以下の **18 列に固定**する
（各列の型・必須区分・入力時点・記入規則は `templates/visit_labels_data_dictionary.md`、
雛形は `templates/visit_labels.example.csv` を参照）。

```
label_id, reviewer_id, reviewed_at, device_id, run_id, image_filename,
highres_captured_at, timezone, visit_present, visitor_taxon, visitor_count,
behavior, on_focal_flower, confidence, image_quality, occlusion,
false_trigger_cause, notes
```

- 結合キー: `device_id` ＋ `image_filename`（補助に `run_id` / `highres_captured_at`）。
- **`visit_present` が訪花の唯一の真値**。mesh の `strong_visitation_candidate` 等は
  この表に**書かず**、probe ログから結合する（§4）。
- **`false_trigger_cause` は「probe で candidate が出たが visit_present=0」の場合のみ**入力する、
  candidate 誤作動の原因分析フィールドであり訪花真値ではない（定義は data dictionary）。
- 旧案の `light_level` は含めない（将来の環境メタデータ結合で扱う）。

## 4. 結合ルール（probe_shadow ↔ 保存 JPEG）
- 一次キーは `device_id` ＋ **`saved_image_filename`**（現行ログには未実装。将来列として
  `SHADOW_LOG_DATA_CONTRACT_V2.md` に定義）。
- 現行ログのみで結合する場合の暫定規則：probe 行のうち `actual_highres_saved=True` の行を、
  対応する高解像度保存に **時刻近傍（±probe_interval/2 = ±2.5 秒）** で対応付ける。
- `visit_labels.csv` は `device_id` ＋ `image_filename` で probe / decisions に結合する。

### 4.1 v2 導入前の暫定結合アルゴリズム
v1 ログに `saved_image_filename` / `run_id` 等が無いため、以下の手順で暫定結合し、
品質を `join_confidence` として付与する。

1. **機体識別（primary candidate）**: device の保存先（storage location）と device identity を
   最初の機体識別に使う（ログは Pi ごとに保存されるため、保存元 Pi = `device_id`）。
2. **probe row ↔ 高解像度 JPEG**: probe 行のうち **`actual_highres_saved=True`** を優先候補とする。
3. **時差計算**: `probe_timestamp` と `highres_captured_at` の**絶対時差**を計算する。
4. **基準**: **±`probe_interval_sec` / 2**（現在の標準設定なら **±2.5 秒**）。
5. **同率候補の順位付け**: 複数候補があるときは
   ① 時差最小 → ② `actual_highres_saved=True` → ③ ファイル mtime の順で順位付けする。
6. **`join_confidence` の付与**:
   - `high`: `actual_highres_saved=True` かつ時差 ≤ 2.5 秒
   - `medium`: 時差 ≤ 5 秒だが直接対応列なし
   - `low`: 時差 > 5 秒、または run 境界・再起動境界をまたぐ
   - `unmatched`: 対応する probe または JPEG が無い

**品質層の扱い**:
- `low` / `unmatched` は主解析から**除外せず、品質層として別集計**する。
- **`high` confidence のみの感度分析**を併せて行い、結合品質依存のバイアスを点検する。

## 5. event window 定義
- **anchor window**: 各高解像度アンカー（既定 30 秒間隔）の `±15 秒` を 1 観測窓とする。
- **candidate event**: local candidate（uncertain または strong）が連続する probe 区間を 1 イベント。
  strong を中心に前後 10–15 秒（probe 2–3 個）を 1 評価窓とする。
- 窓長（10 / 15 / 30 秒）は感度パラメータとして比較する。

## 6. 評価指標
precision / recall / false trigger rate（環境要因→strong）/ false negative rate（人手=訪花だが strong 無し）/
分類群別検出率 / 条件別（風・雲影・花揺れ）誤検知率 / 1 個体滞在による重複 burst の補正。

> 解析原則：**保存枚数・trigger 回数 ≠ 訪花頻度**。
> 訪花頻度は「窓あたり検出率 × 有効観測窓数」で推定し、観測努力を明示的に扱う。

### 6.1 probe 間隔と recall の条件付け（短時間訪花）
- reported recall は「高解像度画像で真値確認可能な訪花」かつ
  「訪花滞在時間が probe 間隔と同程度以上の訪花」に**条件付く**。
- **probe = 5 秒より短い訪花**は candidate 生成前に終了しうるため、通常の recall とは別に
  **short-duration undercount** として扱う。
- 滞在時間が人手で判定可能な場合は、**<5 s / 5–15 s / >15 s の層別 recall** を報告する。
- 滞在時間が判定不能な場合は `duration_class = unknown` 相当として別層に残し、
  **完全ケースだけで結論を出さない**。

## 7. 時刻・run 境界・再起動の扱い（品質管理）
- **device clock / timezone**: 各 Pi のローカル時刻（JST, +09:00）を一次とし、解析時に UTC へ正規化する。
  device 間の時計ずれは結合誤差になり得るため、各 run でデバイス時刻のオフセットを記録する。
  将来は `timezone` をログ列として保持する（`SHADOW_LOG_DATA_CONTRACT_V2.md`）。
- **run 境界**: 1 回の start→stop を 1 run とする。run 境界をまたぐ streak / mode 状態は
  **連続評価しない**（three-stage の streak は run 内でのみ有効）。
- **capture 再開 / service 再起動**: 再起動や再 start で capture_count は 0 に戻り、
  three-stage state も初期化される。**再起動直後の最初の reference frame までは評価対象外**とする。
- **run_id 不在時の処理**: 現行ログに `run_id` 列が無いため、暫定的に
  「同一 device で時間的に連続し、`would_be_mode` が一度 `LOW` 起点に初期化された区間」を 1 run と推定する。
  推定 run には `run_id = inferred_<device>_<start_ts>` を付与し、確定 run（将来列）と区別する。

## 8. 評価不能区間の除外ルール（品質管理）
- **高解像度 JPEG が存在しない区間は評価不能として除外する。**
  probe 行が存在しても、対応する高解像度 JPEG が（削除・未保存・別保存先などで）ディスクに無い場合、
  その窓は precision/recall の母数から外し、`excluded_reason = no_highres_image` として記録する。
- 同様に、reference frame 取得前（`waiting_for_reference_frame`）の probe、
  カメラエラー区間、device clock 異常区間も除外する。
- 除外率（評価不能窓 / 全窓）自体を品質指標として報告する。

### 8.1 欠損の非無作為性とバイアス（必須）
- JPEG 欠損区間は主解析から除外するが、**「無作為な欠損」とは仮定しない**。
- 除外率を **device / 日付 / 時刻帯 / would-be mode / candidate 有無 / run 境界 / 再起動前後** で報告する。
- 欠損が candidate や環境条件と相関する場合、**precision / recall の推定が偏る可能性**を明記する。
- 主解析の分母は**有効 JPEG のある評価窓**とし、**除外窓数・除外理由を別表**として必ず示す。
- 感度分析として、**欠損窓を全て偽陰性と仮定した下限**と、
  **欠損窓を主解析と同率と仮定した参考値**のような**範囲提示**を検討する。

## 9. 解析パイプライン（dev 機・Pi では実行しない）
```
analysis_offline/            # pandas / matplotlib は dev 機のみ
  load_probe_log.py          # 一次: adaptive_probe_shadow-1.csv
  load_decisions.py          # 補助: adaptive_decisions.csv
  load_labels.py             # visit_labels.csv
  join.py                    # device_id + saved_image_filename(暫定: 時刻近傍)
  quality.py                 # §7-8 の run境界・除外ルール
  metrics.py                 # §6 の指標
  figures.py                 # §10 の図
```
`adaptive_metrics.csv` はロードしない（legacy/mixed）。

## 10. 図案
- confusion matrix（strong vs 人手確定訪花）
- mode transition timeline（LOW/MID/HIGH の時系列、保存 JPEG と重畳）
- profile 別比較（default vs sensitive）
- 検出確率 vs 光量・風・時刻
- GB/day と Wh/day の比較

## 11. 限界・前提
- synthetic 由来の閾値は **field 未検証**（`validation_status = synthetic_only`）。
- **probe = 5 秒**のため、**5 秒未満の短時間訪花は見逃しうる**。検出遅延と probe 頻度の評価は
  `HYBRID_CAPTURE_ROADMAP.md` で扱う。
- mesh state は訪花確定ではない。最終判定は常に人手レビューに依る。

## 付録: Phase 0 で確認済みの運用事実（2026-06-25 時点）
- 5 台の Pi: server artifact = `082537b`、PWA build = `9e17204`（build 不一致は事実だが
  `packages/server/src` の diff は空＝runtime source は同一）。
- 高解像度保存・`/latest`・Stop 後保持は zuizui 90 秒試験で **正常**を確認。
  過去に画像が 0 枚だった理由は **原因未特定**（API 削除 / 手動 / 別保存先 / cleanup / 直近未稼働のいずれか）。
- `adaptive_metrics.csv` は schema 混在を実測（6/30/37 列）。一次解析から除外する根拠。
