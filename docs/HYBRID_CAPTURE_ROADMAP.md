# PolliPi Hybrid Capture Roadmap

本書は、PolliPi の最終目的（訪花頻度・訪花者の出現に応じて高解像度撮影間隔を自動調整する）に
向けたロードマップである。**本書は設計計画であり、コード・Pi runtime・service・deploy 設定・
既存 CSV・画像を一切変更しない。** live 化は将来、明示承認＋field validation を経てのみ行う。

> 現段階の方針
> - **live adaptive capture / live burst を有効化しない。**
> - 追加 burst は、まず **virtual burst shadow（仮想記録）として推定**する。
> - `strong_visitation_candidate` は訪花確定ではない。

---

## 1. 最終目的
訪花頻度・訪花者群の出現に応じて高解像度タイムラプス間隔を自動調整し、
- 誤検知 / 見逃し / 昆虫群による検出率差 / 1 個体滞在の重複 burst / 風・影・花揺れバイアス
を訪花頻度推定の偏りに直結させないこと。

## 2. 比較する 3 方式
| 方式 | 内容 |
|---|---|
| **A. Fixed** | 30 秒固定高解像度撮影（アンカーのみ） |
| **B. Pure trigger** | 検出時だけ高解像度 burst、アンカー撮影なし |
| **C. Hybrid** | 30 秒固定アンカー ＋ strong candidate 時に追加 burst |

### 比較指標
訪花イベント再現率 / 訪花者群・種同定成功率 / 滞在時間推定誤差 / 訪花頻度推定の偏り /
誤 trigger 率 / 見逃し率 / 保存枚数 / GB·day / Wh·day / カメラ・Pi の温度・安定性 / 人手アノテーション時間。

> 解析原則：**保存画像数・trigger 回数を訪花頻度と同一視しない。**
> 検出確率と観測努力を明示的に扱う（`SHADOW_VALIDATION_PLAN.md` §6, §8）。

## 3. 固定アンカーを残す理由
- 訪花頻度比較の **基準観測努力**を保持するため。
- adaptive burst の有無で観察確率が変わることを **補正可能**にするため。
- pure trigger の検出漏れを評価する **基準**を残すため。

## 3.1 方式比較の公平性（交絡の回避）
- **最初の方式比較は、同一の固定アンカー JPEG と probe log から offline / virtual に再構成**する
  （A=固定はそのまま、B=pure trigger・C=hybrid は同一データからの仮想再構成）。
- これにより、**Module3 Wide / AI Camera(imx500) / NoIR の機種差、サイト・花種・時刻・天候の差**を
  **方式差と混同しない**。
- 実際の **live 比較**へ進む場合は、**同一 device 内で方式を日・時間帯・地点ごとに交互配置する
  within-device counterbalance** を基本とする。
- `device` / `site` / `date` / `time-of-day` / `camera profile` を、解析の
  **層別因子またはランダム効果候補**として記録する。
- **pure trigger と hybrid の比較**では、保存枚数だけでなく
  **有効観測窓数・検出確率・欠損率**を併記する。

## 4. virtual burst shadow（まず shadow で推定）
実際に burst を撮る前に、probe 判定列から「この判定なら追加 burst を撮っていた」を
**オフライン（または on-Pi の追記列）で再構成**する。
| パラメータ | 候補グリッド |
|---|---|
| trigger 条件 | strong 単発 / MID→HIGH 遷移 / strong 連続 |
| burst 枚数 | 1 / 3 / 4 |
| burst 時刻 | 直後 / +1s / +2s / +4s |
| cooldown | 10 / 20 / 30s |
| 上限 | 毎時 / 毎日 |

出力（仮想）：予測追加保存枚数・予測容量(GB/day)・固定 30 秒基準に対する追加観測努力。

## 5. probe 頻度と検出遅延
- 現行 **probe = 5 秒**のため、**5 秒未満の短時間訪花は捕捉できない可能性**がある。
- virtual burst 評価では必ず **probe 頻度 × 検出遅延（trigger→burst 時刻）** を併記し、
  「検出できていない訪花」を観測努力の偏りとして扱う。
- 将来の burst 実装時は、probe 頻度の引き上げによる検出遅延短縮と電力・熱・保存量のトレードオフを評価する。

## 6. 段階方針（live 化の順序）
1. **shadow**（現状）: would-be LOW/MID/HIGH を記録、capture timing は固定 30 秒・live OFF。
2. **virtual burst shadow**: §4 を offline 推定し、容量・観測努力・検出遅延を見積もる。
3. **field validation**: `SHADOW_VALIDATION_PLAN.md` の人手ラベルで precision/recall/偏りを評価。
4. **将来 live**（承認必須）: 下記 §8 の最小 live 候補から段階導入。
   - `live_allowed` / `live_adaptive_enabled` のガード解除は **ユーザー明示承認時のみ**。

## 7. R1（monitor subscriber 残留）は独立した技術課題
Phase 0 の確認済み事実：
- 実 TCP 接続数が 0 でも `preview_subscriber_count` が残る（stale 化）。
- `subs == 0` を条件にした idle shutdown が発動しない。
- 結果として monitor producer が停止しない。

これは **訪花判定（mesh / three-stage）の問題ではない**。
**電力消費・カメラ占有・監視（MJPEG）可用性の技術課題**として、本ロードマップから独立させて扱う。

将来の設計候補（実装は本書の範囲外・別課題として管理）：
- 接続ごとの subscriber ID
- `last_seen` の記録
- stale subscriber の定期回収
- capture 開始時の server 側 `stop_monitor` 強制
- capture 中の monitor producer 強制停止
- `request.is_disconnected` 等を使う切断検知
- raw integer counter 依存の廃止

## 8. 将来の最初の live 候補（field validation 後）
- **30 秒固定アンカーを維持**し、**`MID→HIGH` 遷移時だけ追加高解像度 JPEG を 1 枚**保存する。
  （最小の追加観測努力で、強い活動時のみ時間分解能を上げる。）
- **3 枚・4 枚 burst** は、まず **virtual burst shadow** で見積もり、**field validation 後**の候補として扱う
  （即時の live 実装はしない）。
- いずれも `live_allowed=false` を維持したまま、shadow / virtual で十分な根拠を得てから提案する。

## 8.1 live burst 移行の定量 gate（将来決定）
live adaptive / live burst を検討する前に、次の各項目について **事前登録（pre-registration）または
事前合意**が必要とする。**数値は現時点で固定しない**（field validation の結果を見てから決める）。

- 最小評価窓数
- 最小調査日数
- device / site / camera profile ごとの最小サンプル
- candidate precision の下限
- false trigger rate の上限
- 短時間訪花の層別 recall の下限
- unknown / low `join_confidence` の許容率
- JPEG 欠損率の上限
- 追加 burst による GB/day と Wh/day の上限
- **R1（monitor subscriber 残留）が解消されていること**
- 高解像度保存・Stop 後保持の **再現試験が複数機で通ること**

> **これらの gate を満たすまで、live adaptive / live burst は有効化しない。**

## 9. 未決事項・前提
- どの profile（default / sensitive）を主に検証するか。
- virtual burst の初期パラメータ範囲の確定。
- live 化判断に必要な field validation のサンプル量。
- R1 技術課題の優先度（電力・可用性の観点）と対応時期。
