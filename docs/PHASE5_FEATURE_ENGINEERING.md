# Phase 5 特徴量設計・学習用データセット作成

作成日: 2026-06-03
更新日: 2026-06-05
対象ブランチ: `phase5-feature-engineering`
ステータス: MVP完了
進捗: 100%

## 1. 目的

Phase 5では、Phase 2からPhase 4までにDBへ蓄積したデータを使い、Phase 6の機械学習モデルへ渡せる艇単位の学習用データセットを作る。

MVPの単位は次の通り。

```text
1 race_id x 1 boat_no = 1 feature row
```

Phase 5 MVPでは、以下を完了条件にした。

- 出走表、選手期別成績、過去成績、直前情報、気象、単勝オッズをDBから結合できる
- `target_win`、`target_top2`、`target_top3`、`exclude_reason`を生成できる
- `pre_race_no_odds`、`pre_race_with_odds`、`exhibition_with_odds`の3種類のmodel viewを切り替えられる
- 結果系カラムや目的変数が特徴量側に混入しないことをコードとテストで検知できる
- 欠損フラグ、重複、6艇揃い、目的変数整合、必須特徴量欠損、Phase 4 status/parser errorを品質チェックできる
- Parquetへ保存し、保存後に読み戻してschema台帳を残せる
- Docker ComposeのAPIコンテナからCLIで再現できる

## 2. 現在の完了状態

Phase 5 MVPは完了。

確認済みの実DB/CLI結果:

| model view | 対象 | 結果 | 保存 |
|---|---|---:|---|
| `pre_race_no_odds` | 2026-05-30 全場 | 1080行 / 45カラム、品質チェックpass | `dataset_boat_features_v1_pre_race_no_odds.parquet` |
| `pre_race_with_odds` | 2026-06-01 場23 1R | 6行 / 49カラム、品質チェックpass | `dataset_boat_features_v1_pre_race_with_odds.parquet` |
| `exhibition_with_odds` | 2026-06-01 場23 1R | 6行 / 63カラム、品質チェックpass | `dataset_boat_features_v1_exhibition_with_odds.parquet` |

各Parquetの横に`.schema.json`を出力し、行数、カラム数、dtype一覧を保存する。

補足:

- 2026-06-01 場23の教師ラベルはPhase 3 CLIで`race_results`を追加投入し、12R/72行を確認した。
- 2026-06-01 場23のPhase 4データは1R分が揃っていたため、Phase 5 CLIへ`--race-no`を追加し、完全な6艇sliceとして検証した。
- 全12RのPhase 4補完実行はタイムアウトした。これはPhase 4運用リハーサル側の課題であり、Phase 5 MVPの完了条件からは外す。

## 3. 実装範囲

### 3.1 Feature modules

| ファイル | 役割 |
|---|---|
| `apps/api/app/features/labels.py` | `race_results`から`target_win`、`target_top2`、`target_top3`、`exclude_reason`を作る |
| `apps/api/app/features/leakage.py` | `finish_position`、`result_status`、`target_*`などの未来情報混入を検知する |
| `apps/api/app/features/aggregations.py` | 直近30/60/90走、コース別、場別の過去成績特徴量をshift付きで作る |
| `apps/api/app/features/build.py` | DBから出走表、期別成績、過去成績、直前情報、気象、単勝オッズ、ラベルを結合する |
| `apps/api/app/features/quality.py` | 学習用datasetの品質チェックとPhase 4 status/parser error確認を行う |
| `apps/api/app/features/export.py` | Parquet保存、保存後読み戻し、schema JSON出力を行う |

### 3.2 CLI

`scripts/phase5_build_features.py`で以下を指定できる。

```text
--from-date
--to-date
--venue-code
--race-no
--feature-set-version
--model-view pre_race_no_odds|pre_race_with_odds|exhibition_with_odds
--output-format parquet
--data-root
--skip-quality
--dry-run
```

Docker ComposeのAPIコンテナからの実行例:

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-06-01 \
  --to-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --model-view exhibition_with_odds \
  --feature-set-version boat_features_v1
```

## 4. 作成済み特徴量

### 4.1 出走表・レース基礎

- `race_id`
- `race_date`
- `venue_code`
- `race_no`
- `grade`
- `distance_m`
- `boat_no`
- `racer_registration_no`
- `racer_name`
- `racer_class`
- `branch`
- `motor_no`
- `boat_no_assigned`

### 4.2 選手期別成績

- `period_year`
- `period_term`
- `racer_period_class`
- `racer_period_branch`
- `racer_win_rate`
- `racer_top2_rate`

期別成績は、レース日以前に利用可能とみなせる期だけをjoinする。前期は5月1日、後期は11月1日を利用可能日の近似として扱う。

### 4.3 過去成績集計

すべて対象レース自身を含めないshift付き集計。

- `recent_win_rate_30`
- `recent_win_rate_60`
- `recent_win_rate_90`
- `recent_top2_rate_30`
- `recent_top2_rate_60`
- `recent_top2_rate_90`
- `recent_top3_rate_30`
- `recent_top3_rate_60`
- `recent_top3_rate_90`
- `course_win_rate`
- `course_top2_rate`
- `course_top3_rate`
- `venue_win_rate`
- `venue_top2_rate`
- `venue_top3_rate`

### 4.4 直前・展示・気象

`model_view='exhibition_with_odds'`で利用する。

- `exhibition_time`
- `tilt_angle`
- `start_exhibition_course`
- `start_exhibition_timing`
- `parts_replaced_count`
- `has_parts_replaced`
- `exhibition_time_rank`
- `exhibition_time_diff`
- `weather`
- `temperature`
- `wind_direction`
- `wind_speed`
- `water_temperature`
- `wave_height`

### 4.5 単勝オッズ

`model_view='pre_race_with_odds'`または`model_view='exhibition_with_odds'`で利用する。

- `win_odds`
- `win_popularity`
- `market_probability`
- `odds_fetched_at`

Phase 4 MVPでは単勝オッズのみを保存している。複勝、2連単、2連複、3連単、3連複などのオッズ特徴量はPhase 4拡張後に追加する。

### 4.6 欠損・品質補助

- `is_missing_period_stats`
- `is_missing_pre_race`
- `is_missing_weather`
- `is_missing_odds`

## 5. 目的変数

| カラム | 定義 | 用途 |
|---|---|---|
| `target_win` | `finish_position == 1` | Phase 6 MVPの主目的変数 |
| `target_top2` | `finish_position <= 2` | 後続モデル評価用 |
| `target_top3` | `finish_position <= 3` | 後続モデル評価用 |
| `exclude_reason` | 欠場、失格、着順欠損などの除外理由 | 学習対象filter用 |

`finish_position`自体は特徴量に入れない。

## 6. 品質チェック

`validate_dataset_quality()`で確認する項目:

- datasetが空ではない
- `(race_id, boat_no)`が重複しない
- 1レース内の`target_win`合計が1を超えない
- 通常6艇レースでは`target_win=1`、`target_top2=2`、`target_top3=3`になる
- `race_count * 6`に対する行充足率が95%以上
- `racer_class`、`racer_win_rate`が存在し、欠損率が5%以下
- `is_missing_*`欠損フラグが存在する
- view別必須特徴量が存在し、欠損率が5%以下
- Phase 4由来のviewでは`live_fetch_status.status='failed'`がなく、`parser_error_count=0`

`export_dataset_to_parquet()`では、保存後に読み戻して行数とカラム順を確認し、`.schema.json`へschemaを記録する。

## 7. 完了タスク

| ID | 優先度 | タスク | 状態 |
|---|---|---|---|
| P5-001 | P0 | Phase 5用ブランチと設計docを作る | 完了 |
| P5-002 | P0 | `(race_id, boat_no)`単位のdataset粒度を固定する | 完了 |
| P5-003 | P0 | `target_win`、`target_top2`、`target_top3`を生成する | 完了 |
| P5-004 | P0 | 未来情報混入防止ルールを実装・pytest化する | 完了 |
| P5-005 | P0 | `apps/api/app/features/`とtestsを追加する | 完了 |
| P5-101 | P0 | 出走表・レース基礎特徴量を作る | 完了 |
| P5-102 | P0 | レーサー期別特徴量をas-of joinする | 完了 |
| P5-103 | P0 | 教師ラベルを結合する | 完了 |
| P5-104 | P0 | 気象特徴量をjoinする | 完了 |
| P5-105 | P0 | 展示・部品交換特徴量をjoinする | 完了 |
| P5-106 | P0 | 単勝オッズ特徴量をjoinする | 完了 |
| P5-107 | P0 | 欠損フラグ列をdatasetへ追加する | 完了 |
| P5-201 | P0 | Phase 5 CLIを作る | 完了 |
| P5-202 | P0 | Parquet保存とschema記録を作る | 完了 |
| P5-203 | P0 | dataset品質チェックを作る | 完了 |
| P5-204 | P0 | Phase 5 pytestを追加する | 完了 |
| P5-205 | P0 | ruff、format、mypy、pytestを通す | 完了 |
| P5-301 | P1 | 直近30/60/90走特徴量を作る | 完了 |
| P5-302 | P1 | コース別成績特徴量を作る | 完了 |
| P5-303 | P1 | 場別成績特徴量を作る | 完了 |
| P5-304 | P1 | 展示タイム順位・平均との差を作る | 完了 |
| P5-305 | P1 | 単勝人気順位・市場確率を作る | 完了 |
| P5-306 | P1 | 場別の勝率/2連対率/3連対率を過去成績から作る | 完了 |

Phase 5 MVPとしての未完了タスクはなし。

## 8. Phase 6以降へ送るもの

以下はPhase 5 MVPの完了条件から外し、後続Phaseで扱う。

- LightGBMなどのモデル学習
- ハイパーパラメータ探索
- SHAP/Feature Importance
- 期待値計算
- 買い目生成
- バックテスト
- DB上の永続Feature Storeテーブル
- Phase 5専用Prefect Flow
- 単勝以外のオッズ特徴量
- 記者予想特徴量
- 直接対決、同期、同支部などの関係特徴量
- モーター・ボートの高度な履歴特徴量

## 9. 検証ログ

2026-06-05時点で確認済み。

```bash
cd apps/api
uv run ruff format app tests ../../scripts
uv run ruff check app tests ../../scripts
uv run mypy app
uv run pytest tests/features -q
uv run pytest -q
```

結果:

```text
All checks passed
Success: no issues found in 44 source files
19 passed
52 passed
```

Docker Compose上の実DB確認:

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --model-view pre_race_no_odds \
  --feature-set-version boat_features_v1
```

結果:

```text
1080行 / 45カラム
row_completeness_rate: 100.00%
品質チェックpass
Parquet保存pass
```

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-06-01 \
  --to-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --model-view pre_race_with_odds \
  --feature-set-version boat_features_v1
```

結果:

```text
6行 / 49カラム
row_completeness_rate: 100.00%
missing_rate_win_odds: 0.00%
品質チェックpass
Parquet保存pass
```

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-06-01 \
  --to-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --model-view exhibition_with_odds \
  --feature-set-version boat_features_v1
```

結果:

```text
6行 / 63カラム
row_completeness_rate: 100.00%
missing_rate_exhibition_time: 0.00%
missing_rate_wind_speed: 0.00%
missing_rate_win_odds: 0.00%
品質チェックpass
Parquet保存pass
```

## 10. 注意点

- 生成済みParquetとschema JSONは`data/processed/features/`に出るが、Git管理しない。
- Phase 5 CLIはPhase 6の学習入力を作るための導線であり、モデル学習はまだ行わない。
- `pre_race_no_odds`は展示・気象・オッズを使わない事前予測用view。
- `pre_race_with_odds`は単勝オッズ込み、展示なしの比較用view。
- `exhibition_with_odds`は展示・気象・単勝オッズ込みの直前予測用view。
- Phase 4の全場/全Rリハーサルは運用検証として後続で実施する。Phase 5 MVPは、完全に揃った6艇sliceで3ビューの生成・品質・保存を確認済み。
