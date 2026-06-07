# Phase 6 機械学習モデル設計・評価計画

作成日: 2026-06-06
更新日: 2026-06-07
対象ブランチ: `phase6-model-training`
ステータス: MVP実装・検証完了
進捗: 100%（P0/MVP。P1/P2は後続改善候補）

## 1. 目的

Phase 6では、Phase 5で作成した艇単位の学習用データセットを使い、各艇の1着確率を予測する機械学習モデルを作る。

MVPでは、まずLightGBMによる二値分類モデルを作る。

```text
1 race_id x 1 boat_no = 1 training row
target = target_win
```

1艇ごとの`target_win`確率を出したあと、同一`race_id`内の6艇の確率合計が1になるよう正規化する。これにより、Phase 7の予測APIやPhase 8の画面で「各艇の1着確率」として扱える出力を作る。

Phase 6のゴールは「高精度モデルを作り切ること」ではなく、以下を再現可能なパイプラインとして固定すること。

- Phase 5のParquet datasetを読み込める
- 学習、検証、テストを時系列で分割できる
- 未来情報を特徴量へ混ぜない
- LightGBMのベースラインモデルを学習できる
- 評価指標を計算できる
- MLflowへparams、metrics、artifactsを記録できる
- モデルファイルとfeature listを保存できる
- pytestで主要ロジックを固定できる

## 2. 前提

Phase 6は以下の成果物を前提にする。

| Phase | 前提成果物 | Phase 6での用途 |
|---|---|---|
| Phase 2 | `racer_period_stats` | 選手基礎能力特徴量 |
| Phase 3 | `races`、`race_entries`、`race_results`、`payouts` | 出走表、教師ラベル、将来の回収率検証 |
| Phase 4 | `pre_race_entry_infos`、`weather_observations`、`odds_snapshot_entries`、`live_fetch_status` | 展示後/オッズ込みモデルの入力 |
| Phase 5 | `data/processed/features/*.parquet`、`.schema.json` | 学習用datasetの直接入力 |

現時点でPhase 5が確認済みのmodel view:

- `pre_race_no_odds`
- `pre_race_with_odds`
- `exhibition_with_odds`

Phase 6 MVPでは、まず`pre_race_no_odds`を主入力にする。これは展示・気象・オッズに依存しないため、過去データを広く使ったベースラインを作りやすい。

## 3. Phase 6で作るもの

### 3.1 MVP成果物

| 成果物 | 内容 |
|---|---|
| 学習CLI | Phase 5 Parquetを入力し、モデル学習、評価、保存、MLflow記録を行う |
| Dataset loader | schema JSONとParquetを読み、必要カラムを検証する |
| 時系列split | `race_date`でtrain/valid/testを分割し、同一レースを複数splitへ分けない |
| 前処理 | feature/target分離、ID列除外、カテゴリ列処理、欠損処理 |
| LightGBM baseline | `target_win`二値分類モデル |
| レース内正規化 | 同一`race_id`内の予測確率合計を1にする |
| 評価レポート | Log Loss、Brier Score、的中率、segment別指標 |
| MLflow記録 | params、metrics、feature list、model artifact、evaluation JSON |
| pytest | split、leakage、preprocess、normalization、metric計算を固定する |

### 3.2 想定ディレクトリ

Phase 6実装時に追加する候補。

```text
apps/api/app/ml/
  __init__.py
  dataset.py
  preprocessing.py
  split.py
  train.py
  evaluate.py
  registry.py

apps/api/tests/ml/
  __init__.py
  test_dataset.py
  test_preprocessing.py
  test_split.py
  test_evaluate.py

scripts/
  phase6_train_model.py

data/processed/models/
  .gitkeep

data/processed/reports/
  .gitkeep
```

生成済みモデル、評価レポート、MLflow runはGit管理しない。Gitに入れるのは`.gitkeep`とソースコード、テスト、ドキュメントだけにする。

## 4. Phase 6でまだ作らないもの

以下はPhase 6 MVPから外す。

- 買い目生成
- 期待値による購入判断
- 本格バックテスト
- 3連単組み合わせ確率モデル
- ランキング学習
- レース単位の多クラス分類
- Optunaによる本格探索
- SHAPによる詳細説明レポート
- FastAPIの予測エンドポイント
- Web画面表示
- DB上のモデル管理テーブル
- Prefectによる定期学習Flow

これらはPhase 7以降、またはPhase 9のバックテスト・期待値分析で扱う。

## 5. 入力dataset仕様

Phase 6 MVPの入力はPhase 5 CLIで生成したParquet。

例:

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-05-28 \
  --to-date 2026-05-30 \
  --model-view pre_race_no_odds \
  --feature-set-version boat_features_v1
```

入力ファイル:

```text
data/processed/features/dataset_boat_features_v1_pre_race_no_odds.parquet
data/processed/features/dataset_boat_features_v1_pre_race_no_odds.schema.json
```

Phase 6 CLIは、dataset pathを明示できるようにする。

```bash
cd apps/api
uv run python ../../scripts/phase6_train_model.py \
  --dataset ../../data/processed/features/dataset_boat_features_v1_pre_race_no_odds.parquet \
  --schema ../../data/processed/features/dataset_boat_features_v1_pre_race_no_odds.schema.json \
  --target target_win \
  --model-name lgbm_win_v1 \
  --experiment-name boatrace_phase6_baseline
```

## 6. 学習対象と除外列

### 6.1 目的変数

MVPの目的変数:

- `target_win`

後続候補:

- `target_top2`
- `target_top3`

### 6.2 学習から除外する列

以下は識別子、目的変数、結果系、監査用のため、特徴量には入れない。

- `race_id`
- `race_date`
- `boat_no`
- `racer_registration_no`
- `racer_name`
- `target_win`
- `target_top2`
- `target_top3`
- `exclude_reason`
- `finish_position`
- `result_status`
- `decision`
- `start_timing`
- `payout_yen`
- `popularity`
- `odds_fetched_at`

`boat_no`は枠番として強い特徴量になる可能性があるが、MVPではID/枠の扱いを明示的に検討するため一旦除外候補に入れる。実装時に「枠番特徴量として使う」判断をする場合は、`boat_no`ではなく`frame_no`など意味が明確な列へ変換して使う。

### 6.3 欠損処理

LightGBMは数値欠損を扱えるため、数値列の欠損は原則そのまま残す。

カテゴリ列は以下のいずれかで扱う。

- pandas `category`へ変換し、LightGBMのcategorical featureとして渡す
- 初期実装では文字列を明示的にカテゴリコード化し、mappingをartifactへ保存する

欠損フラグ列:

- `is_missing_period_stats`
- `is_missing_pre_race`
- `is_missing_weather`
- `is_missing_odds`

これらは品質・欠損パターンを学習に伝える特徴量として残す。

## 7. データ分割

Phase 6ではランダム分割を禁止する。

理由:

- 未来のレース情報が過去の学習に混ざるリスクがある
- 同一日・同一開催の傾向がtrain/testに漏れると評価が楽観的になる
- 実運用は「過去で学習し、未来を予測する」形になる

MVPのsplit方針:

```text
train: 古い期間
valid: trainより後の期間
test : validより後の期間
```

制約:

- `race_date`を基準に分ける
- 同一`race_id`は必ず同じsplitへ入れる
- splitごとに少なくとも一定数のレースが必要
- データが少なすぎる場合は学習を失敗させ、エラー理由を表示する

ローカルDBの2026-05-28から2026-05-30を使い、432完全レースで時系列splitとbaseline評価を確認した。ただし3日間は性能を確定するには短いため、長期間の期間外評価は後続のモデル改善で行う。

## 8. 評価指標

MVPで必須にする指標:

| 指標 | 用途 |
|---|---|
| Log Loss | 確率予測の主指標 |
| Brier Score | 確率の校正具合を見る |
| Race hit rate | 各レースで最も高い確率の艇が1着だった割合 |
| Mean predicted winner probability | 的中艇へどの程度確率を置けたか |
| Probability sum error | レース内正規化後、6艇の確率合計が1からずれていないか |

P1で追加する指標:

- AUC
- Calibration table
- 場別Log Loss
- グレード別Log Loss
- 月別/季節別Log Loss
- model view別比較

回収率、期待値、払戻を使ったシミュレーションはPhase 9の主対象にする。Phase 6では、オッズ込みmodel viewで`market_probability`との差分を分析できるように準備する程度に留める。

## 9. MLflow記録

Phase 6 MVPでは、学習実行ごとにMLflowへ記録する。

### 9.1 params

- `model_name`
- `model_view`
- `feature_set_version`
- `target`
- `dataset_path`
- `dataset_sha256`
- `schema_path`
- `schema_sha256`
- `train_start_date`
- `train_end_date`
- `valid_start_date`
- `valid_end_date`
- `test_start_date`
- `test_end_date`
- LightGBM hyperparameters

### 9.2 metrics

- `valid_log_loss`
- `valid_brier_score`
- `valid_race_hit_rate`
- `test_log_loss`
- `test_brier_score`
- `test_race_hit_rate`
- `test_probability_sum_error_max`

### 9.3 artifacts

- `model.pkl`またはLightGBM native model
- `feature_columns.json`
- `categorical_columns.json`
- `preprocessing_config.json`
- `evaluation_report.json`
- `feature_importance.csv`
- 入力schema JSONのcopy

MLflow client/serverは`2.22.2`へ揃える。Tracking serverは`mlruns/mlflow.db`へrun台帳、`mlruns/artifacts/`へartifactを永続化する。READMEのMLflow確認コマンドと整合させる。

## 10. モデル出力仕様

Phase 6の予測出力は、Phase 7 APIへ渡せる形を意識する。

艇単位の出力:

| カラム | 内容 |
|---|---|
| `race_id` | レースID |
| `boat_no` | 艇番 |
| `raw_win_probability` | LightGBMの生確率 |
| `win_probability` | レース内正規化後の1着確率 |
| `model_name` | モデル名 |
| `model_version` | モデルバージョンまたはMLflow run id |
| `predicted_at` | 予測生成時刻 |

レース単位の制約:

- `win_probability`の合計は1.0に近い
- 6艇揃っていないレースは評価対象から除外、または`exclude_reason`を付ける
- 同一`race_id, boat_no, model_version`は一意に扱えるようにする

## 11. タスク一覧と優先順位

優先度:

| 優先度 | 意味 |
|---|---|
| P0 | Phase 6 MVP完了に必須 |
| P1 | Phase 6内でできれば入れたい |
| P2 | Phase 7以降、またはモデル改善フェーズでよい |

### 11.1 P0: 土台（完了）

| ID | タスク | 完了条件 | 状態 |
|---|---|---|---|
| P6-001 | Phase 6用ブランチを作る | `phase6-model-training`などの作業ブランチで開始する | 完了 |
| P6-002 | ML依存関係を確認・追加する | `lightgbm`、`scikit-learn`、必要なら`joblib`が`pyproject.toml`とlockに入っている | 完了 |
| P6-003 | Phase 6用module構成を作る | `apps/api/app/ml/`と`apps/api/tests/ml/`を追加する | 完了 |
| P6-004 | 学習CLIを作る | `scripts/phase6_train_model.py --help`が通る | 完了 |
| P6-005 | 出力ディレクトリを整備する | `data/processed/models/.gitkeep`、`data/processed/reports/.gitkeep`を追加する | 完了 |

### 11.2 P0: Dataset読み込み・検証（完了）

| ID | タスク | 完了条件 | 状態 |
|---|---|---|---|
| P6-101 | Phase 5 Parquet loaderを作る | dataset pathとschema pathを受け取り、DataFrameを返せる | 完了 |
| P6-102 | schema整合を検査する | schema JSONの行数、カラム、dtypeとParquet実体の不整合を検知する | 完了 |
| P6-103 | feature/target分離を作る | 除外列、target列、feature列を明示的に返せる | 完了 |
| P6-104 | leakage guardを学習前に実行する | 結果系/target系カラムがfeatureに混ざった場合に失敗する | 完了 |
| P6-105 | `exclude_reason`処理を固定する | MVPでは`exclude_reason is null`かつ6艇完全レースだけを学習対象にする | 完了 |

### 11.3 P0: Split・前処理（完了）

| ID | タスク | 完了条件 | 状態 |
|---|---|---|---|
| P6-201 | 時系列splitを実装する | `race_date`でtrain/valid/testを分け、同一`race_id`が跨がらない | 完了 |
| P6-202 | データ不足エラーを実装する | split不能なdatasetでは理由付きで失敗する | 完了 |
| P6-203 | 数値/カテゴリ列を分離する | feature列の型ごとに処理方針を決められる | 完了 |
| P6-204 | 前処理設定をartifact化する | feature columns、categorical columns、mapping/configをJSON保存できる | 完了 |

### 11.4 P0: 学習・評価・保存（完了）

| ID | タスク | 完了条件 | 状態 |
|---|---|---|---|
| P6-301 | LightGBM baselineを学習する | `target_win`の二値分類モデルが学習できる | 完了 |
| P6-302 | レース内確率正規化を実装する | 同一`race_id`内の`win_probability`合計が1.0に近い | 完了 |
| P6-303 | 評価指標を計算する | Log Loss、Brier Score、Race hit rate、probability sum errorを出せる | 完了 |
| P6-304 | feature importanceを出力する | CSVまたはJSONで保存できる | 完了 |
| P6-305 | model artifactを保存する | `data/processed/models/`へモデルを保存できる | 完了 |
| P6-306 | MLflowへ記録する | params、metrics、artifactsがMLflow UIで確認できる | 完了 |

### 11.5 P0: テスト・ドキュメント（完了）

| ID | タスク | 完了条件 | 状態 |
|---|---|---|---|
| P6-401 | pytestを追加する | loader、split、preprocess、normalization、metricsの基本仕様を固定する | 完了 |
| P6-402 | 品質コマンドを通す | `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通る | 完了 |
| P6-403 | READMEとロードマップを更新する | 実行コマンド、検証結果、残タスクを反映する | 完了 |
| P6-404 | Phase 6 docを更新する | 進捗、完了/未完了、検証ログを反映する | 完了 |

### 11.6 P1: モデル比較・分析

| ID | タスク | 完了条件 |
|---|---|---|
| P6-501 | `pre_race_with_odds`モデルを作る | オッズ込みdatasetで学習・評価できる |
| P6-502 | `exhibition_with_odds`モデルを作る | 展示/気象/オッズ込みdatasetで学習・評価できる |
| P6-503 | `target_top2`モデルを作る | 2連対確率のbaselineを評価できる |
| P6-504 | `target_top3`モデルを作る | 3連対確率のbaselineを評価できる |
| P6-505 | segment別評価を追加する | 場別、グレード別、月別の評価表を出せる |
| P6-506 | Calibration tableを出す | 予測確率帯ごとの実績率を確認できる |

### 11.7 P2: 後続候補

| ID | タスク | 完了条件 |
|---|---|---|
| P6-601 | Optuna探索を追加する | MLflowに探索結果を記録できる |
| P6-602 | SHAP分析を追加する | summary artifactを保存できる |
| P6-603 | Prefect Flow化する | 手動CLIが安定してから薄いwrapperを作る |
| P6-604 | モデルregistry方針を決める | Phase 7 APIが読むmodel versionを固定できる |
| P6-605 | ランキング/多クラスモデルを検討する | 二値分類baselineと比較できる |

## 12. Phase 6完了条件

Phase 6 MVPは、以下をすべて満たしたときに100%完了とする。

- Phase 5 Parquet datasetを入力にして学習CLIを実行できる
- `target_win`のLightGBM baselineを学習できる
- train/valid/testを時系列で分割できる
- 同一`race_id`が複数splitへ跨がらない
- 結果系/target系カラムがfeatureに混入しない
- レース内正規化後の確率合計を検証できる
- Log Loss、Brier Score、Race hit rateを計算できる
- MLflowへparams、metrics、model、feature list、evaluation reportを記録できる
- モデルartifactを`data/processed/models/`へ保存できる
- 主要ロジックのpytestがある
- `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通る
- README、ロードマップ、Phase 6 doc、構成台帳が同期されている

## 13. 最初に進める順番

推奨順:

1. `phase6-model-training`ブランチを作る
2. `lightgbm`、`scikit-learn`、`joblib`の依存関係を追加する
3. `apps/api/app/ml/`と`apps/api/tests/ml/`を作る
4. Phase 5 dataset loaderとschema検証を作る
5. feature/target分離とleakage guardを作る
6. 時系列splitを作る
7. LightGBM baselineを学習する
8. レース内確率正規化と評価指標を作る
9. MLflow loggingとartifact保存を作る
10. pytestと品質コマンドを通す
11. README、ロードマップ、Phase 6 doc、構成台帳を更新する

## 14. 注意点

- 2026-05-28から2026-05-30の3日分はbaselineの動作検証には使えるが、モデル性能を確定するにはまだ短い。Phase 6ではパイプラインの正しさを優先する。
- 評価でランダムsplitを使わない。
- `payouts`や払戻情報をPhase 6の特徴量へ入れない。
- オッズ込みモデルとオッズなしモデルは必ず分ける。
- `market_probability`を使う場合は、オッズが取得できた時点の予測という前提をdocとMLflow paramsに残す。
- 生成済みモデル、レポート、MLflow runはGit管理しない。

## 15. 実装・検証結果

2026-06-07にP0/MVPを完了した。

実装:

- `apps/api/app/ml/dataset.py`: Parquet/schema検証、対象行抽出、6艇完全レース抽出、feature/target分離、leakage guard
- `apps/api/app/ml/split.py`: `race_date`によるtrain/valid/test分割、レース重複・データ不足検査
- `apps/api/app/ml/preprocessing.py`: 数値・真偽値・カテゴリ列処理、未知カテゴリ処理、設定JSONの保存・読み戻し
- `apps/api/app/ml/train.py`: LightGBM二値分類、early stopping、予測、feature importance、modelの保存・読み戻し
- `apps/api/app/ml/evaluate.py`: レース内確率正規化、Log Loss、Brier Score、Race hit rate、確率合計誤差
- `apps/api/app/ml/registry.py`: MLflow params、metrics、model bundle、report artifacts記録
- `scripts/phase6_train_model.py`: 読み込みからMLflow記録までの学習CLI
- dataset/schemaのSHA-256をevaluation report、model metadata、MLflow paramsへ記録

実データ検証:

| 項目 | 結果 |
|---|---|
| Phase 5入力 | 2026-05-28から2026-05-30、2,832行、472レース、45カラム |
| 学習対象 | `exclude_reason is null`かつ6艇完全、勝者1艇の432レース |
| train | 2026-05-28、804行、134レース |
| valid | 2026-05-29、816行、136レース |
| test | 2026-05-30、972行、162レース |
| valid Log Loss | 0.365700 |
| test Log Loss | 0.363987 |
| test Brier Score | 0.110115 |
| test Race hit rate | 50.62% |
| test Probability sum error max | `2.220446049250313e-16` |
| MLflow run | `daa591bbeaf04bea86b011fbde7c00ef` |

品質検証:

```text
ruff format --check: 95 files already formatted
ruff check: All checks passed
mypy app: 51 source files / no issues
pytest: 63 passed
Docker API image build: pass
Docker内 phase6_train_model.py --help: pass
Docker内 学習CLI + MLflow記録: pass
MLflow container再作成後のrun/artifact再取得: pass
API GET /health: pass
```

P1/P2のモデル比較、segment評価、Calibration、Optuna、SHAP、Prefect Flow化はMVP完了条件に含めず、Phase 7以降と並行して必要性を判断する。
