# PolliPi Shadow Log Data Contract (v2 proposal)

本書は、shadow validation の解析が依拠するログのデータ契約を定義する。
**本書は契約（仕様）の定義であり、コード・Pi runtime・service・既存 CSV・画像を一切変更しない。**
実装は別途、明示承認を得てから行う。

---

## 1. 現行ログの実態（Phase 0 実測, 2026-06-25）
| ファイル | 列数 | 状態 | 最新例 |
|---|---|---|---|
| `adaptive_probe_shadow-1.csv` | 15 | 世代一貫・最新が更新中 | probe 毎 1 行 |
| `adaptive_decisions.csv` | 6 | 一貫 | high-res 保存時に追記 |
| `adaptive_metrics.csv` | **6 / 30 / 37 が混在** | **legacy / mixed-schema** | 例: zuizui で 6×16, 30×15, 37×8 行 |

`adaptive_probe_shadow-1.csv`（15 列）:
`probe_timestamp, probe_interval_sec, would_be_mode, would_be_interval_sec, decision_state,
decision_reason, local_candidate_streak, quiet_streak, high_elapsed_sec, high_remaining_sec,
actual_highres_saved, next_highres_due_at, policy_name, policy_version, validation_status`

## 1.1 現行 v1 ログの追跡限界（重要）
- 現行 v1 の `adaptive_probe_shadow-1.csv`（15 列）には、`device_id` / `run_id` / `timezone` /
  `saved_image_filename` / `scheduled_highres_timestamp` / `policy_profile_id` /
  `simulation_run_id` / `source_server_build` / `source_web_build` が
  **完全には記録されていない**。
- したがって現行データの結合は **Pi の保存先・時刻近傍・status 記録・ファイル mtime** に依存する
  **暫定的な復元**であり、**厳密な run 単位追跡は本書 v2 schema 導入後に初めて可能**になる。
- v1 からの推定結合結果には **`join_confidence`（または同等の品質区分）** を付与して扱う。

## 2. 正準ログの役割定義
| ログ | 役割 | 解析での扱い |
|---|---|---|
| `adaptive_probe_shadow-1.csv` | **一次ログ (primary)** | 全解析の主入力 |
| `adaptive_decisions.csv` | **補助ログ (auxiliary)** | high-res 保存イベントの裏取り |
| `adaptive_metrics.csv` | **除外 (excluded)** | 一次解析に使用しない |

## 3. `adaptive_metrics.csv` を一次解析から除外する根拠
- 同一ファイル内で列数が混在（6 / 30 / 37）。これはログ生成が `write_header = not file.exists()`
  であり、**最初に作成したビルドのヘッダのまま追記**され続けるため、ビルド世代をまたいで
  行スキーマが食い違うことに起因する。
- 一部の Pi では先頭行が 2026-05-26 の 6 列 `insect_candidate` 形式（旧称）であり、
  現行 schema と一致しない。
- したがって **legacy / mixed-schema として一次解析対象外**とする。参考・履歴としてのみ保持する。

## 4. 将来の必須結合列（v2）
保存された高解像度 JPEG と probe を**確実に**結合するために、将来のログ schema には次を追加する。

| 列 | 定義 | 目的 |
|---|---|---|
| `saved_image_filename` | その probe で保存された高解像度 JPEG のファイル名（未保存は空） | probe ↔ 実保存 JPEG の確実な結合キー |
| `scheduled_highres_timestamp` | 固定アンカー（高解像度）撮影の予定/実時刻 | probe 時刻と高解像度撮影時刻の区別 |
| `run_id` | 1 回の start→stop を識別する実行 ID | run 境界・再起動の扱い（VALIDATION_PLAN §7） |
| `schema_version` | ログ schema の世代 | 混在防止・後方互換管理 |
| `device_id` | デバイス識別子 | device 横断の結合 |
| `policy_profile_id` | 適用 profile（例: three_stage_default_v1） | profile 別比較 |
| `simulation_run_id` | 由来する simulation run | synthetic 閾値の追跡 |

### 4.1 将来メタデータ候補（追加）
| 列 | 定義 | 目的 |
|---|---|---|
| `source_server_build` | 実行中 server artifact の git commit（例: 082537b） | runtime 由来の追跡・build 不一致の検出 |
| `source_web_build` | PWA build id（例: 9e17204…） | PWA/server 不一致の記録 |
| `image_sha256` | 保存 JPEG の SHA256 | 画像の同定・改変/重複検出・証跡 |
| `timezone` | デバイスのタイムゾーン（例: Asia/Tokyo, +09:00） | device clock 正規化（VALIDATION_PLAN §7） |

## 5. schema_version 運用ルール（必須）
- **run ごとに新規ログファイルを作る**（例: `adaptive_probe_shadow_<schema_version>_<run_id>.csv`）。
  これにより 1 ファイル内のスキーマ混在を構造的に防ぐ。
- **`schema_version` が変わる場合は既存 CSV へ追記しない。** 新スキーマは必ず新ファイル
  （新ヘッダ）で開始する。
- **legacy `adaptive_metrics.csv` は一次解析対象外**（履歴保持のみ）。

## 6. 後方互換・移行方針
- 既存の `adaptive_probe_shadow-1.csv` / `adaptive_decisions.csv` / `adaptive_metrics.csv` は
  **破壊・移動・上書きしない**（証跡として保持）。
- v2 列は**新ファイル**で導入し、旧ファイルとは時刻・device_id で後方結合する。
- 解析側は `schema_version` を見てローダを切り替える。

## 7. 適用範囲（重要）
本書は **データ契約の定義のみ**である。
ログ生成コード・Pi runtime・service・deploy 設定の変更は本書の範囲外であり、
別途の明示承認を得てから実装する。現段階では **コードを変更しない**。
