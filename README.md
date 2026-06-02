# BOATRACE=LOVE

BOATRACE=LOVE MVPのローカル分析ダッシュボード用リポジトリです。

## 現在の進捗

- Phase 0: 完了
- Phase 1: 完了
- Phase 2: 完了
- Phase 3: 進行中

## Git管理状況

- ローカルGit: 初期化済み
- GitHubリポジトリ: https://github.com/taku-logue/boatrace-love
- リモート: `origin`
- 公開状態: `main` push済み

GitHub公開は完了済み。Phase 2以降は作業ブランチを切って進める。

## 主要ドキュメント

- `docs/BOATRACE_ANALYTICS_ROADMAP.md`: 全体ロードマップ
- `docs/PROJECT_STRUCTURE_AND_FILE_INVENTORY.md`: 現在のフォルダ・ファイル構成と配置ルール
- `docs/PHASE3_RACE_RESULTS_AND_CARDS_INGESTION.md`: Phase 3の現状、完了条件、残タスク
- `docs/PHASE4_REALTIME_DATA_INGESTION.md`: Phase 4の目的、タスク、完了条件、優先順位

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

## Phase 3 現状メモ

詳細は`docs/PHASE3_RACE_RESULTS_AND_CARDS_INGESTION.md`を参照。

- 番組表Bファイルと競走成績Kファイルの取得、解凍、パース、正規化、DB Upsert処理を実装済み
- Phase 3の`download_files`、`raw_files`、`ingestion_runs`連携、Raw行保存、SHA-256、文字コードメタデータを実装済み
- DB上では`races`、`race_entries`、`race_results`、`payouts`、`race_card_raw`、`race_result_raw`への投入を確認済み
- `--from-date`、`--to-date`、`--only`、`--venue-code`、`--dry-run`、`--skip-download`、`--skip-quality`で対象を制御できる
- HTTP取得はtimeout、通信エラー、408、429、5xxを指数バックオフで再試行し、404は`not_found`として非リトライ扱いにする
- 払戻は単勝、複勝、2連単、2連複、拡連複、3連単、3連複を保存できる
- データ品質チェック、DB実体を使ったUpsert冪等性pytest、Prefect Flow dry-runは確認済み
- 残タスクは複数日・複数場の長めの再実行検証、年代差分や特殊払戻の実例が出た場合のfixture追加

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
