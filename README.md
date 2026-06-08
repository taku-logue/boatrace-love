# BOATRACE=LOVE

BOATRACE=LOVE MVPのローカル分析ダッシュボード用リポジトリです。

## 現在の進捗

- Phase 0: 完了
- Phase 1: 完了
- Phase 2: 完了
- Phase 3: MVP完了
- Phase 4: MVP完了
- Phase 5: MVP完了
- Phase 6: MVP完了
- Phase 7: MVP完了
- Phase 8: MVP完了
- Phase 9: MVP完了

## Git管理状況

- ローカルGit: 初期化済み
- GitHubリポジトリ: https://github.com/taku-logue/boatrace-love
- リモート: `origin`
- 公開状態: `main` push済み

GitHub公開は完了済み。Phase 2以降は作業ブランチを切って進める。

## 主要ドキュメント

- `docs/BOATRACE_ANALYTICS_ROADMAP.md`: 全体ロードマップ
- `docs/PROJECT_STRUCTURE_AND_FILE_INVENTORY.md`: 現在のフォルダ・ファイル構成と配置ルール
- `docs/PHASE2_RACER_PERIOD_STATS_INGESTION.md`: Phase 2の目的、タスク、完了条件、優先順位
- `docs/PHASE3_RACE_RESULTS_AND_CARDS_INGESTION.md`: Phase 3の目的、完了条件、後続の堅牢化候補
- `docs/PHASE4_REALTIME_DATA_INGESTION.md`: Phase 4の目的、タスク、完了条件、優先順位
- `docs/PHASE5_FEATURE_ENGINEERING.md`: Phase 5の目的、タスク、完了条件、優先順位
- `docs/PHASE6_MODEL_TRAINING.md`: Phase 6の目的、タスク、完了条件、優先順位
- `docs/PHASE7_PREDICTION_API.md`: Phase 7の目的、タスク、完了条件、優先順位
- `docs/PHASE8_WEB_FRONTEND.md`: Phase 8の目的、タスク、完了条件、優先順位
- `docs/PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md`: Phase 9の目的、タスク、完了条件、優先順位

## 起動方法

Docker Desktopを起動した状態で、以下を実行します。

```bash
docker compose up -d --build
```

## サービスURL

- Web Dashboard: http://localhost:3000
- API health: http://localhost:8000/health
- API DB health: http://localhost:8000/db/health
- API version: http://localhost:8000/version
- API latest model: http://localhost:8000/models/latest
- API prediction example: http://localhost:8000/races/20260528_01_01/prediction
- Web prediction dashboard: http://localhost:3000?raceId=20260528_01_01
- Prefect Server: http://localhost:4200
- MLflow Tracking: http://localhost:5000

## 開発コマンド

API:

```bash
cd apps/api
uv run ruff format .
uv run ruff check .
uv run mypy app
uv run pytest
```

Web:

```bash
cd apps/web
pnpm format
pnpm lint
pnpm test:e2e
```

## DBマイグレーション確認

```bash
docker compose exec api uv run alembic current
docker compose exec api uv run alembic upgrade head
docker compose exec postgres psql -U boatrace -d boatrace_love -c "\\dt"
```

## Prefect確認

```bash
cd apps/api
uv run python ../../scripts/check_prefect.py
```

Prefect Serverは http://localhost:4200 で確認できます。

Phase 3のPrefect Flow確認:

```bash
cd apps/api
PREFECT_API_URL=http://127.0.0.1:4200/api uv run python ../../scripts/phase3_prefect_flow.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --dry-run \
  --skip-quality \
  --sleep-seconds 0
```

## MLflow確認

```bash
cd apps/api
uv run python ../../scripts/check_mlflow.py
```

MLflow Trackingは http://localhost:5000 で確認できます。

## Phase 7 API確認

```bash
curl http://localhost:8000/models/latest
curl http://localhost:8000/races/20260528_01_01/prediction
```

## Phase 8 Web確認

Docker Compose起動後、`http://localhost:3000?raceId=20260528_01_01`で予測ダッシュボードを確認する。

表示されるもの:

- API、DB、最新modelの状態
- `raceId`入力フォーム
- 6艇の予測順位、艇番、選手、級別、1着確率
- model contractとtop pick

## Phase 9 バックテスト確認

単勝期待値と均等買いバックテストを実行する。

```bash
cd apps/api
uv run python ../../scripts/phase9_backtest_win.py \
  --from-date 2026-06-01 \
  --to-date 2026-06-01 \
  --venue-code 23 \
  --min-expected-value 1.0 \
  --max-races 12
```

出力先:

- `data/processed/reports/phase9/*.summary.json`
- `data/processed/reports/phase9/*.bets.csv`

生成reportはGit管理しない。

## 確認済み

- `docker compose`で`postgres`、`api`、`web`、`prefect-server`、`mlflow`が起動する
- `GET /health`、`GET /db/health`、`GET /version`が成功する
- Web DashboardがHTTP 200を返す
- Alembic初期テーブルがDBに存在する
- API/Web Dockerfileが存在し、ビルドできる
- `.env.example`に主要な環境変数が揃っている
- Rawデータ保存ディレクトリと`.gitkeep`が整備されている
- APIの`ruff check`、`ruff format --check`、`mypy`、`pytest`が成功する
- Webの`format:check`、`lint`、`test:e2e`が成功する
- PrefectサンプルFlowが成功する
- MLflow dummy runが登録できる
- `GET /models/latest`が最新model bundleを返す
- `GET /races/20260528_01_01/prediction`が6艇分の1着確率を返す
- Web DashboardがPhase 7 APIを使い、`raceId=20260528_01_01`の6艇予測ランキングを表示する
- Desktop/mobile幅でWeb Dashboardの表示を確認済み
- Phase 9 CLIが単勝期待値、均等買いbacktest、summary JSON、bets CSVを生成する
- 2026-06-01、場23、12Rで単勝backtestを実走済み

## Phase 3 現状メモ

詳細は`docs/PHASE3_RACE_RESULTS_AND_CARDS_INGESTION.md`を参照。

- 番組表Bファイルと競走成績Kファイルの取得、解凍、パース、正規化、DB Upsert処理を実装済み
- Phase 3の`download_files`、`raw_files`、`ingestion_runs`連携、Raw行保存、SHA-256、文字コードメタデータを実装済み
- DB上では`races`、`race_entries`、`race_results`、`payouts`、`race_card_raw`、`race_result_raw`への投入を確認済み
- `--from-date`、`--to-date`、`--only`、`--venue-code`、`--dry-run`、`--skip-download`、`--skip-quality`で対象を制御できる
- HTTP取得はtimeout、通信エラー、408、429、5xxを指数バックオフで再試行し、404は`not_found`として非リトライ扱いにする
- 払戻は単勝、複勝、2連単、2連複、拡連複、3連単、3連複を保存できる
- データ品質チェック、DB実体を使ったUpsert冪等性pytest、Prefect Flow dry-runは確認済み
- Phase 3 MVPの残タスクはなし。複数日・複数場の長めの再実行検証、年代差分や特殊払戻の実例が出た場合のfixture追加は後続の堅牢化として扱う

## Phase 3 実行コマンド

dry-run:

```bash
cd apps/api
uv run python ../../scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --dry-run
```

通常実行:

```bash
cd apps/api
uv run python ../../scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --http-retries 3 \
  --http-backoff-seconds 2 \
  --sleep-seconds 0
```

既存LZHを使った再実行:

```bash
cd apps/api
uv run python ../../scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --skip-download \
  --sleep-seconds 0
```

場コードを絞る検証:

```bash
cd apps/api
uv run python ../../scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --venue-code 23 \
  --dry-run
```

Docker ComposeのAPIコンテナから実行する場合:

```bash
docker compose exec api uv run python /scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --dry-run
```

## Phase 4 現状メモ

詳細は`docs/PHASE4_REALTIME_DATA_INGESTION.md`を参照。

- Phase 4 MVPは完了
- 当日開催場、出走表、直前情報、単勝オッズの取得/parser/load導線を実装済み
- `live_fetch_status`、`weather_observations`、`pre_race_entry_infos`、`odds_snapshots`、`odds_snapshot_entries`を現行schemaとして使用
- Raw HTMLは`data/raw/html/{race_cards|exhibition|odds}/YYYYMMDD/`に保存し、`raw_files`、SHA-256、取得URL、`ingestion_runs`へ記録する
- `phase4_run_live_pipeline.py`で対象日、場、R、取得種別、dry-run、sleep、retry/backoff、timeoutを指定できる
- `phase4_prefect_flow.py`はPhase 4 CLIを呼ぶ薄いPrefect wrapper
- `phase4_check_quality.py`で出走表、直前情報、気象、単勝オッズ、取得失敗status、parser行数異常を検査できる
- 2026-06-01、場コード23、1Rの通常CLI実行とPrefect dry-runを確認済み
- Phase 4 MVPの残タスクはなし
- 単勝以外のオッズ、部品交換専用カラム、1日全場の通常実行リハーサル、API確認エンドポイントは後続候補

## Phase 4 実行コマンド

DB migration:

```bash
cd apps/api
uv run alembic upgrade head
```

dry-run:

```bash
cd apps/api
uv run python ../../scripts/phase4_run_live_pipeline.py \
  --race-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --only all \
  --dry-run \
  --sleep-seconds 0
```

通常実行:

```bash
cd apps/api
uv run python ../../scripts/phase4_run_live_pipeline.py \
  --race-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --only all \
  --sleep-seconds 0 \
  --http-retries 1
```

品質チェック:

```bash
cd apps/api
uv run python ../../scripts/phase4_check_quality.py \
  --race-date 2026-06-01
```

## Phase 5 現状メモ

詳細は`docs/PHASE5_FEATURE_ENGINEERING.md`を参照。

- Phase 5 MVPは完了
- `apps/api/app/features/`に特徴量生成、ラベル生成、リーク検知、品質チェック、Parquet出力、過去成績集計を実装済み
- `scripts/phase5_build_features.py`で対象期間、場コード、R番号、model view、dry-run、Parquet出力、data root、品質チェックskipを指定できる
- `pre_race_no_odds`は2026-05-30分で1080行、45カラムのdataset生成、品質チェック、Parquet保存、schema記録を確認済み
- `pre_race_with_odds`は2026-06-01 場23 1Rで6行、49カラムのdataset生成、品質チェック、Parquet保存、schema記録を確認済み
- `exhibition_with_odds`は2026-06-01 場23 1Rで6行、63カラムのdataset生成、品質チェック、Parquet保存、schema記録を確認済み
- Phase 5 MVPの残タスクはなし。モデル学習、期待値、買い目、バックテスト、単勝以外のオッズ特徴量はPhase 6以降へ送る

## Phase 5 実行コマンド

Docker ComposeのAPIコンテナから実行する場合:

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --model-view pre_race_no_odds \
  --feature-set-version boat_features_v1 \
  --dry-run
```

展示・オッズ込みviewを1R単位で確認する場合:

```bash
docker compose exec -T api env PYTHONUNBUFFERED=1 uv run python /scripts/phase5_build_features.py \
  --from-date 2026-06-01 \
  --to-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --model-view exhibition_with_odds \
  --feature-set-version boat_features_v1
```

## Phase 6 現状メモ

詳細は`docs/PHASE6_MODEL_TRAINING.md`を参照。

- Phase 6 MVPは完了
- Phase 5のParquet/schemaを検証し、`exclude_reason is null`かつ6艇完全・勝者1艇のレースを学習対象にする
- `race_date`でtrain/valid/testを時系列分割し、同一`race_id`を複数splitへ跨がせない
- `boat_no`は識別子として除外し、枠番特徴量`frame_no`へ変換する
- LightGBMで`target_win`を学習し、同一レース内の1着確率合計を1へ正規化する
- Log Loss、Brier Score、Race hit rate、Probability sum errorを評価する
- model bundle、前処理設定、feature importance、予測Parquet、評価JSONを保存する
- MLflowへparams、metrics、model、report artifactsを記録する
- MLflow client/serverは`2.22.2`で揃え、run台帳とartifactは`mlruns/`へ永続化する
- 2026-05-28から2026-05-30の432完全レースで実走済み
- test Log Lossは0.363987、Brier Scoreは0.110115、Race hit rateは50.62%
- `ruff format --check`、`ruff check`、`mypy app`、`pytest 63 passed`、Docker build/CLI実行を確認済み

## Phase 6 実行コマンド

最初に3日以上のPhase 5 datasetを生成する。

```bash
cd apps/api
uv run python ../../scripts/phase5_build_features.py \
  --from-date 2026-05-28 \
  --to-date 2026-05-30 \
  --model-view pre_race_no_odds \
  --feature-set-version boat_features_v1
```

ローカル実行:

```bash
cd apps/api
uv run python ../../scripts/phase6_train_model.py \
  --dataset ../../data/processed/features/dataset_boat_features_v1_pre_race_no_odds.parquet \
  --schema ../../data/processed/features/dataset_boat_features_v1_pre_race_no_odds.schema.json \
  --target target_win \
  --model-name lgbm_win_v1 \
  --experiment-name boatrace_phase6_baseline \
  --tracking-uri http://127.0.0.1:5000
```

Docker ComposeのAPIコンテナから実行する場合:

```bash
docker compose exec -T api uv run python /scripts/phase6_train_model.py \
  --dataset /data/processed/features/dataset_boat_features_v1_pre_race_no_odds.parquet \
  --schema /data/processed/features/dataset_boat_features_v1_pre_race_no_odds.schema.json \
  --target target_win \
  --model-name lgbm_win_v1 \
  --experiment-name boatrace_phase6_baseline
```

生成済みdataset、model、report、MLflow runはGit管理しない。P1のオッズ/展示込みモデル比較、segment評価、Calibrationは後続改善候補とする。
