# Phase 5 特徴量設計・学習用データセット作成 設計書

作成日: 2026-06-03
更新日: 2026-06-03
ステータス: 設計ドキュメント作成済み / 実装未着手
進捗目安: 5%

## 1. Phase 5の目的

Phase 5では、Phase 2からPhase 4で蓄積したDBを使い、機械学習モデルが読める特徴量テーブルと学習用データセットを作る。

MVPでは、1レース6艇それぞれを1行とし、「その艇が1着になるか」を二値分類の教師ラベルにする。Phase 6のLightGBMモデルにそのまま渡せる、再現可能で未来情報混入のないデータセットを作ることを目標にする。

Phase 5完了時点で目指す状態:

- `race_id`と`boat_no`単位の特徴量行を作れる
- 1着ラベル、2連対ラベル、3連対ラベル候補を作れる
- 過去成績、選手、出走表、レース場、季節、直前情報、気象、単勝オッズを特徴量化できる
- 未来情報混入を防ぐルールをコードとテストで固定できる
- 学習用datasetをPostgreSQLまたはParquetへ保存できる
- 欠損、範囲外、重複、join率を品質チェックできる
- Phase 6で学習scriptから安定して読み込める

## 2. 前提

前提となる成果物:

- Phase 2: `racer_period_stats`、`racer_period_stats_raw`
- Phase 3: `races`、`race_entries`、`race_results`、`payouts`、`race_card_raw`、`race_result_raw`
- Phase 4: `pre_race_entry_infos`、`weather_observations`、`odds_snapshots`、`odds_snapshot_entries`
- 共通: `data_sources`、`ingestion_runs`、`raw_files`

引き継ぐ原則:

- joinキーは必ず`race_id`を使う
- 艇単位特徴量の主キーは`(race_id, boat_no)`にする
- Rawファイルを特徴量生成の主入力にしない。DB正規化済みテーブルから作る
- `race_results`、`payouts`は教師ラベルや検証用であり、予測時特徴量に混ぜない
- 当日予測で使えない情報を学習時特徴量に入れない
- オッズありモデルとオッズなしモデルを分けられるようにする

## 3. Phase 5でまだ作らないもの

以下はPhase 5では作らない。

- LightGBMなどの本格モデル学習
- ハイパーパラメータ探索
- SHAP、Feature Importanceレポート
- 買い目生成
- 期待値に基づく購入判断
- バックテストの詳細シミュレーション
- Web API/画面への予測結果表示
- 記者予想特徴量

## 4. 入力データと利用方針

| 入力 | 用途 | 注意 |
|---|---|---|
| `races` | レース日、場、R番号、距離など | すべての特徴量の親 |
| `race_entries` | 艇番、選手登番、級別、支部、モーター、ボート | 予測時に使える出走表情報 |
| `race_results` | 着順、進入、ST、決まり手 | 教師ラベル、過去成績集計に使う。対象レース自身は除外 |
| `payouts` | 払戻、人気 | 回収率/期待値検証用。予測特徴量には入れない |
| `racer_period_stats` | 期別勝率、級別など | 対象レース日以前に確定している期の値だけ使う |
| `pre_race_entry_infos` | 展示タイム、チルト、展示進入、展示ST | 展示後モデル用。展示前モデルでは除外 |
| `weather_observations` | 気温、水温、風、波、天候 | 展示後/直前モデル用 |
| `odds_snapshot_entries` | 単勝オッズ | オッズ込みモデル用。オッズなしモデルでは除外 |

## 5. データ粒度

MVPの基本粒度:

```text
1 race_id x 1 boat_no = 1 feature row
```

1レースは原則6行になる。

主キー候補:

```text
(race_id, boat_no, feature_set_version)
```

保存先候補:

- PostgreSQL: 再利用しやすい正規化済み特徴量テーブル
- Parquet: 学習処理で高速に読み込むdataset
- `data/processed/features/`: Parquet保存先候補

## 6. 目的変数

MVPで作る目的変数:

| カラム | 定義 | 用途 |
|---|---|---|
| `target_win` | `finish_position = 1`なら1 | Phase 6 MVPの主目的 |
| `target_top2` | `finish_position <= 2`なら1 | 後続モデル候補 |
| `target_top3` | `finish_position <= 3`なら1 | 後続モデル候補 |
| `finish_position` | 実着順 | 分析/検証用。特徴量には使わない |

注意:

- 欠場、失格、不成立などの扱いはPhase 5で明示的に決める
- MVPでは、通常完走レースを中心にdatasetを作る
- 特殊ケースは除外理由を`exclude_reason`として残す

## 7. 特徴量グループ

### 7.1 出走表特徴量

| 特徴量 | 元テーブル | 優先度 |
|---|---|---|
| 艇番 | `race_entries.boat_no` | P0 |
| 選手登番 | `race_entries.racer_registration_no` | P0 |
| 級別 | `race_entries.racer_class` | P0 |
| 支部 | `race_entries.branch` | P0 |
| モーター番号 | `race_entries.motor_no` | P0 |
| ボート番号 | `race_entries.boat_no_assigned` | P0 |
| レース場 | `races.venue_code` | P0 |
| R番号 | `races.race_no` | P0 |
| 距離 | `races.distance_m` | P1 |
| グレード | `races.grade` | P1 |

### 7.2 選手基礎特徴量

| 特徴量 | 元テーブル | 優先度 |
|---|---|---|
| 期別勝率/2連対率/3連対率 | `racer_period_stats` | P0 |
| 級別 | `racer_period_stats`または`race_entries` | P0 |
| 支部 | `racer_period_stats`または`race_entries` | P0 |
| 直近30走の1着率/2連対率/3連対率 | `race_results`過去分 | P1 |
| 直近60走の1着率/2連対率/3連対率 | `race_results`過去分 | P1 |
| 平均ST、ST標準偏差 | `race_results`過去分 | P1 |
| コース別成績 | `race_results.entry_course` | P1 |
| 当地成績 | `races.venue_code` + `race_results` | P1 |

### 7.3 レース場・環境特徴量

| 特徴量 | 元テーブル | 優先度 |
|---|---|---|
| 場コード | `races.venue_code` | P0 |
| R番号 | `races.race_no` | P0 |
| 月、季節、曜日 | `races.race_date` | P0 |
| 気温、水温、風速、波高 | `weather_observations` | P0 |
| 風向 | `weather_observations.wind_direction` | P1 |
| 天候 | `weather_observations.weather` | P1 |
| 場別イン逃げ率 | 過去`race_results` | P1 |

### 7.4 直前・展示特徴量

| 特徴量 | 元テーブル | 優先度 |
|---|---|---|
| 展示タイム | `pre_race_entry_infos.exhibition_time` | P0 |
| チルト | `pre_race_entry_infos.tilt_angle` | P0 |
| 展示進入 | `pre_race_entry_infos.start_exhibition_course` | P0 |
| 展示ST | `pre_race_entry_infos.start_exhibition_timing` | P0 |
| 部品交換 | `pre_race_entry_infos.raw_values` | P1 |
| 展示タイム順位 | 同一`race_id`内で算出 | P1 |
| 展示タイム平均との差 | 同一`race_id`内で算出 | P1 |

### 7.5 オッズ特徴量

| 特徴量 | 元テーブル | 優先度 |
|---|---|---|
| 単勝オッズ | `odds_snapshot_entries` | P0 |
| 単勝人気順位 | 同一snapshot内で算出 | P0 |
| 市場確率 | `1 / odds`から算出 | P1 |
| オッズsnapshot時刻 | `odds_snapshots.fetched_at` | P1 |
| オッズ変化率 | 複数snapshot | P2 |
| 複勝/2連系/3連系オッズ | Phase 4拡張後 | P2 |

## 8. 未来情報混入防止ルール

Phase 5で最重要のルール:

- 対象レース自身の`race_results`を特徴量集計に含めない
- 対象レース日より後の`racer_period_stats`を使わない
- rolling成績は対象レースより前のレースだけで集計する
- `payouts`は特徴量にしない
- `finish_position`、`decision`、`result_status`は目的変数/検証用であり特徴量にしない
- オッズなしモデルでは`odds_snapshot_entries`を使わない
- 展示前モデルでは`pre_race_entry_infos`と`weather_observations`を使わない

テストで固定すること:

- 対象レース自身をrolling集計から除外できている
- future dateの期別成績をjoinしない
- dataset内で`target_*`や結果系カラムがfeature columnsに混ざらない

## 9. 欠損処理ルール

初期方針:

- P0特徴量の欠損は品質チェックで警告または除外
- P1/P2特徴量の欠損は欠損フラグを追加して補完
- 数値特徴量は原則`NULL`を残し、モデル前処理で扱う
- カテゴリ特徴量は`unknown`を許容するかPhase 5で決める
- 除外した行は`exclude_reason`に理由を残す

欠損フラグ例:

- `is_missing_period_stats`
- `is_missing_weather`
- `is_missing_pre_race`
- `is_missing_odds`

## 10. 推奨テーブル案

Phase 5で追加候補のテーブル:

| テーブル | 目的 | 主なキー |
|---|---|---|
| `feature_sets` | 特徴量セット定義とversion管理 | `id` |
| `boat_feature_snapshots` | 艇単位特徴量の保存 | `(race_id, boat_no, feature_set_id)` |
| `training_datasets` | 学習dataset出力単位の台帳 | `id` |
| `training_dataset_rows` | dataset行の参照/抽出結果 | `(dataset_id, race_id, boat_no)` |

MVPではテーブルを増やしすぎず、まずParquet出力から始めてもよい。

Parquet候補:

```text
data/processed/features/phase5_boat_features_v1.parquet
data/processed/features/phase5_training_dataset_v1.parquet
```

## 11. ディレクトリ案

Phase 5で追加する候補:

```text
apps/api/app/features/
  __init__.py
  labels.py
  leakage.py
  build.py
  quality.py
  export.py

apps/api/tests/features/
  test_labels.py
  test_leakage.py
  test_build.py
  test_quality.py

scripts/
  phase5_build_features.py
  phase5_check_features.py
  phase5_prefect_flow.py

data/processed/features/
  .gitkeep
```

配置方針:

- DB読み出し、特徴量生成ロジックは`apps/api/app/features/`へ置く
- CLIは`scripts/phase5_build_features.py`へ置く
- PrefectはCLIを薄く呼ぶwrapperにする
- 実データParquetはGit管理しない

## 12. CLI案

```bash
cd apps/api
uv run python ../../scripts/phase5_build_features.py \
  --from-date 2026-05-30 \
  --to-date 2026-06-01 \
  --feature-set-version boat_features_v1 \
  --model-view pre_race_with_odds \
  --output-format parquet \
  --dry-run
```

引数案:

```text
--from-date
--to-date
--venue-code
--feature-set-version
--model-view pre_race_no_odds|pre_race_with_odds|exhibition_with_odds
--output-format parquet|db
--data-root
--dry-run
--skip-quality
```

## 13. 品質チェック案

Phase 5品質チェック:

- 1レースあたりfeature rowが原則6件
- `(race_id, boat_no)`が重複しない
- `target_win`の合計が通常レースでは1
- `target_top2`の合計が通常レースでは2
- `target_top3`の合計が通常レースでは3
- P0特徴量の欠損率が閾値以下
- `race_entries`と`race_results`のjoin率が閾値以上
- `racer_period_stats` join率が閾値以上
- 結果系カラムがfeature columnsに混入していない
- 日付分割時に学習期間より未来の情報を使っていない
- 出力Parquetの行数、カラム数、schemaが記録されている

## 14. タスク一覧と優先順位

優先度:

| 優先度 | 意味 |
|---|---|
| P0 | Phase 5 MVP完了に必須 |
| P1 | Phase 5内で完了させたい |
| P2 | Phase 6以降へ送ってよい |

### 14.1 P0: 設計・土台

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P5-001 | Phase 5用ブランチを作る | 未着手 | `codex/phase5-feature-engineering`などで作業する |
| P5-002 | 特徴量の粒度を確定する | 未着手 | `(race_id, boat_no)`を基本行に固定する |
| P5-003 | 目的変数を定義する | 未着手 | `target_win`、`target_top2`、`target_top3`を生成できる |
| P5-004 | 未来情報混入ルールを文書化する | 未着手 | 禁止カラム、as-of条件、rolling除外条件を明文化する |
| P5-005 | Phase 5ディレクトリを作る | 未着手 | `apps/api/app/features/`、`apps/api/tests/features/`を作る |

### 14.2 P0: MVP特徴量

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P5-101 | 出走表特徴量を作る | 未着手 | 艇番、選手、級別、支部、モーター、ボート、場、R番号を生成 |
| P5-102 | レーサー期別特徴量をjoinする | 未着手 | 対象日以前の期別成績をjoinできる |
| P5-103 | レース結果から教師ラベルを作る | 未着手 | `target_win`などを生成できる |
| P5-104 | 気象特徴量をjoinする | 未着手 | `weather_observations`を`race_id`でjoinできる |
| P5-105 | 展示特徴量をjoinする | 未着手 | `pre_race_entry_infos`を`race_id, boat_no`でjoinできる |
| P5-106 | 単勝オッズ特徴量をjoinする | 未着手 | latest snapshotまたは指定snapshotをjoinできる |
| P5-107 | 欠損フラグを作る | 未着手 | P0/P1欠損状態を明示できる |

### 14.3 P0: 出力・品質

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P5-201 | 特徴量生成CLIを作る | 未着手 | 対象期間、場、model view、dry-runを指定できる |
| P5-202 | Parquet出力を作る | 未着手 | `data/processed/features/`へ保存できる |
| P5-203 | 品質チェックを作る | 未着手 | 行数、欠損、重複、join率、target整合を検査できる |
| P5-204 | pytestを追加する | 未着手 | labels、leakage、build、qualityの基本仕様を固定する |
| P5-205 | API品質コマンドを通す | 未着手 | ruff/format/mypy/pytestが通る |

### 14.4 P1: 拡張特徴量

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P5-301 | 直近30/60/90走特徴量を作る | 未着手 | 対象レース前だけでrolling集計できる |
| P5-302 | コース別成績を作る | 未着手 | 進入コース別の1着率/連対率を作れる |
| P5-303 | 当地成績を作る | 未着手 | 場別の過去成績を作れる |
| P5-304 | 展示順位/平均との差を作る | 未着手 | 同一レース内で相対値を作れる |
| P5-305 | 単勝人気順位/市場確率を作る | 未着手 | 単勝オッズから算出できる |
| P5-306 | 場別傾向特徴量を作る | 未着手 | イン逃げ率などを過去データから作れる |

### 14.5 P2: 後続候補

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P5-401 | 複勝/2連系/3連系オッズ特徴量を作る | 未着手 | Phase 4で取得後に追加 |
| P5-402 | 記者予想特徴量を作る | 未着手 | Phase 4/後続で取得可否確認後 |
| P5-403 | 部品交換専用特徴量を作る | 未着手 | `raw_values`から専用カラム化方針を決める |
| P5-404 | DB保存テーブルを作る | 未着手 | Parquet運用で不足したら追加 |
| P5-405 | Prefect Flow化する | 未着手 | CLIが安定してから薄いwrapperを作る |

## 15. Phase 5完了条件

Phase 5の完了条件:

- `(race_id, boat_no)`単位のfeature rowsを生成できる
- `target_win`を持つ学習用datasetを作れる
- 出走表、選手期別、気象、展示、単勝オッズのMVP特徴量が入っている
- オッズなし/ありのfeature viewを切り替えられる
- 未来情報混入防止ルールがpytestで固定されている
- P0特徴量の欠損、重複、join率を品質チェックできる
- ParquetまたはDBへdatasetを保存できる
- README、ロードマップ、構成台帳にPhase 5実行手順が反映されている
- `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通る

## 16. 最初に進める順番

推奨順:

1. `apps/api/app/features/`と`apps/api/tests/features/`を作る
2. label生成の`labels.py`とpytestを作る
3. leakage防止の`leakage.py`とpytestを作る
4. 出走表 + 結果labelだけの最小datasetを作る
5. 期別成績、気象、展示、単勝オッズを順番にjoinする
6. 欠損/重複/join率の品質チェックを作る
7. Parquet出力CLIを作る
8. README、ロードマップ、構成台帳を更新する

最初の実装単位は、`--from-date`、`--to-date`、`--model-view pre_race_no_odds`で、出走表と結果だけを使った`target_win`付きdatasetをdry-run/Parquet出力できるところまでにする。
