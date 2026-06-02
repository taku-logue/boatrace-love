# BOATRACE=LOVE プロジェクト構成・ファイル台帳

作成日: 2026-05-30
更新日: 2026-06-01
対象ブランチ: `codex/phase3-race-database`

このドキュメントは、他のAIエージェントが現在のリポジトリ構成を取り違えずに把握するための台帳である。

## 1. 読み方

このドキュメントでいう「完全なファイル構成」は、Git管理対象にするべきソース、設定、ドキュメント、空ディレクトリ保持用`.gitkeep`の一覧を指す。

以下はソースではないため、ファイル単位では台帳に含めない。

- `.env`
- `apps/api/.venv/`
- `apps/api/.uv-cache/`
- `apps/api/.prefect/`
- `apps/web/node_modules/`
- `apps/web/.next/`
- `__pycache__/`
- `.pytest_cache/`
- `.ruff_cache/`
- `.mypy_cache/`
- `mlruns/`
- `data/tmp/`
- `data/raw/**`配下の実データ
- `data/interim/**`配下の中間データ
- `data/processed/**`配下の生成済みデータ

Rawデータ、解凍済みTXT、Parquet、MLflow run、Prefect local DB、テストレポートはローカル生成物として扱う。Gitへ入れるのは配置を維持する`.gitkeep`だけにする。

## 2. 全体構成

```text
BOATRACE=LOVE/
  apps/
    api/                  FastAPI、SQLAlchemy、Alembic、Python ingestion
    web/                  Next.js dashboard
  data/                   ローカルデータ置き場。実データは原則Git管理しない
  docs/                   ロードマップ、フェーズ設計、構成台帳
  scripts/                ローカル実行用の確認・取得・投入スクリプト
  docker-compose.yml      ローカル統合環境
  README.md               開発者向け入口
```

現在の中心はPhase 3で、`apps/api/app/ingestion/race_cards/`、`apps/api/app/ingestion/race_results/`、`apps/api/app/models/race_*`、`scripts/phase3_*`が主作業範囲である。

## 3. Git管理対象の完全なファイル構成

```text
.
├── .env.example
├── .gitignore
├── README.md
├── docker-compose.yml
├── apps/
│   ├── api/
│   │   ├── .dockerignore
│   │   ├── Dockerfile
│   │   ├── alembic.ini
│   │   ├── pyproject.toml
│   │   ├── uv.lock
│   │   ├── alembic/
│   │   │   ├── README
│   │   │   ├── env.py
│   │   │   ├── script.py.mako
│   │   │   └── versions/
│   │   │       ├── 2aa075ebabae_add_phase3_tables_for_race_cards_and_.py
│   │   │       ├── b48e5d316863_create_phase2_racer_period_stats_tables.py
│   │   │       ├── d5f2f8a0c1e4_repair_phase3_phase2_raw_constraint.py
│   │   │       └── fea2050a2b26_create_initial_metadata_tables.py
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py
│   │   │   ├── core/
│   │   │   │   ├── __init__.py
│   │   │   │   └── config.py
│   │   │   ├── db/
│   │   │   │   ├── __init__.py
│   │   │   │   └── session.py
│   │   │   ├── ingestion/
│   │   │   │   ├── archive.py
│   │   │   │   ├── encoding.py
│   │   │   │   ├── race_downloads.py
│   │   │   │   ├── race_id.py
│   │   │   │   ├── race_quality.py
│   │   │   │   ├── race_cards/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── layouts.py
│   │   │   │   │   ├── load.py
│   │   │   │   │   ├── normalize.py
│   │   │   │   │   └── parse.py
│   │   │   │   ├── race_results/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── layouts.py
│   │   │   │   │   ├── load.py
│   │   │   │   │   ├── normalize.py
│   │   │   │   │   └── parse.py
│   │   │   │   └── racer_period_stats/
│   │   │   │       └── layouts.py
│   │   │   └── models/
│   │   │       ├── __init__.py
│   │   │       ├── base.py
│   │   │       ├── downloads.py
│   │   │       ├── management.py
│   │   │       ├── payouts.py
│   │   │       ├── race_cards.py
│   │   │       ├── race_master.py
│   │   │       ├── race_results.py
│   │   │       └── racer_period_stats.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── test_main.py
│   │       └── ingestion/
│   │           ├── test_phase3_download_retry.py
│   │           ├── test_race_downloads.py
│   │           ├── test_race_id.py
│   │           ├── test_race_parsers.py
│   │           ├── test_race_quality.py
│   │           ├── test_race_upserts_db.py
│   │           ├── test_race_upserts.py
│   │           └── test_racer_period_stats_parse.py
│   └── web/
│       ├── .dockerignore
│       ├── .gitignore
│       ├── Dockerfile
│       ├── README.md
│       ├── eslint.config.mjs
│       ├── next.config.ts
│       ├── package.json
│       ├── playwright.config.ts
│       ├── pnpm-lock.yaml
│       ├── pnpm-workspace.yaml
│       ├── postcss.config.mjs
│       ├── tsconfig.json
│       ├── src/
│       │   └── app/
│       │       ├── favicon.ico
│       │       ├── globals.css
│       │       ├── layout.tsx
│       │       └── page.tsx
│       └── tests/
│           └── dashboard.spec.ts
├── data/
│   ├── .gitkeep
│   ├── external/
│   │   └── .gitkeep
│   ├── interim/
│   │   └── .gitkeep
│   ├── processed/
│   │   └── .gitkeep
│   └── raw/
│       ├── .gitkeep
│       ├── extracted/
│       │   ├── .gitkeep
│       │   ├── race_cards/
│       │   │   └── .gitkeep
│       │   ├── race_results/
│       │   │   └── .gitkeep
│       │   └── racer_period_stats/
│       │       └── .gitkeep
│       ├── html/
│       │   ├── .gitkeep
│       │   ├── exhibition/
│       │   │   └── .gitkeep
│       │   ├── odds/
│       │   │   └── .gitkeep
│       │   └── race_cards/
│       │       └── .gitkeep
│       ├── odds/
│       │   └── .gitkeep
│       └── official_downloads/
│           ├── .gitkeep
│           ├── race_cards/
│           │   └── .gitkeep
│           ├── race_results/
│           │   └── .gitkeep
│           └── racer_period_stats/
│               └── .gitkeep
├── docs/
│   ├── BOATRACE_ANALYTICS_ROADMAP.md
│   ├── PHASE0_REQUIREMENTS_AND_VALIDATION.md
│   ├── PHASE1_PROJECT_SETUP.md
│   ├── PHASE2_RACER_PERIOD_STATS_INGESTION.md
│   ├── PHASE3_RACE_RESULTS_AND_CARDS_INGESTION.md
│   ├── PHASE4_REALTIME_DATA_INGESTION.md
│   └── PROJECT_STRUCTURE_AND_FILE_INVENTORY.md
└── scripts/
    ├── check_mlflow.py
    ├── check_prefect.py
    ├── phase2_discover_racer_period_stats.py
    ├── phase2_run_all_pipeline.py
    ├── phase3_prefect_flow.py
    └── phase3_run_all_pipeline.py
```

## 4. 主要ディレクトリの責務

| パス | 責務 | Git管理方針 |
|---|---|---|
| `apps/api/app/main.py` | FastAPIエントリーポイント | 管理する |
| `apps/api/app/core/` | API設定 | 管理する |
| `apps/api/app/db/` | SQLAlchemy接続 | 管理する |
| `apps/api/app/models/` | DBモデル | 管理する |
| `apps/api/app/ingestion/` | 取得、解凍、文字コード、パース、正規化、DB投入の部品 | 管理する |
| `apps/api/alembic/` | DB migration | 管理する |
| `apps/api/tests/` | API/Pythonテスト | 管理する |
| `apps/web/src/` | Next.js App Router | 管理する |
| `apps/web/tests/` | Web E2E | 管理する |
| `data/raw/official_downloads/` | 公式から取得した圧縮ファイルの保存先 | `.gitkeep`だけ管理する |
| `data/raw/extracted/` | 解凍済みRaw TXTの保存先 | `.gitkeep`だけ管理する |
| `data/raw/html/` | HTML取得結果の保存先 | `.gitkeep`だけ管理する |
| `data/interim/` | 中間生成データ | `.gitkeep`だけ管理する |
| `data/processed/` | 学習・分析用の生成済みデータ | `.gitkeep`だけ管理する |
| `docs/` | 設計・進捗・引き継ぎ文書 | 管理する |
| `scripts/` | 手動実行するフェーズ別スクリプト | 管理する |

## 5. 現在の処理構成

### Phase 0

ドキュメント中心。要件、MVPスコープ、評価指標、データ利用方針を`docs/PHASE0_REQUIREMENTS_AND_VALIDATION.md`に固定している。

### Phase 1

Docker Compose、FastAPI、Next.js、PostgreSQL、Prefect、MLflow、Alembicの土台。主な対象は`docker-compose.yml`、`apps/api/`、`apps/web/`。

### Phase 2

レーサー期別成績の取得、LZH解凍、パース、DB投入。主な対象は以下。

- `apps/api/app/ingestion/archive.py`
- `apps/api/app/ingestion/encoding.py`
- `apps/api/app/ingestion/racer_period_stats/layouts.py`
- `apps/api/app/models/downloads.py`
- `apps/api/app/models/management.py`
- `apps/api/app/models/racer_period_stats.py`
- `scripts/phase2_*`

### Phase 3

番組表Bファイルと競走成績Kファイルの取得、解凍、パース、正規化、DB投入。主な対象は以下。

- `apps/api/app/ingestion/race_id.py`
- `apps/api/app/ingestion/race_downloads.py`
- `apps/api/app/ingestion/race_quality.py`
- `apps/api/app/ingestion/race_cards/`
- `apps/api/app/ingestion/race_results/`
- `apps/api/app/models/race_master.py`
- `apps/api/app/models/race_cards.py`
- `apps/api/app/models/race_results.py`
- `apps/api/app/models/payouts.py`
- `scripts/phase3_*`

現在のPhase 3実行導線は`scripts/phase3_run_all_pipeline.py`に集約している。このスクリプトはB/KファイルのURL生成、ダウンロード、LZH解凍、文字コード判定、`download_files`/`raw_files`/`ingestion_runs`記録、Raw行保存、正規化テーブルUpsert、品質チェックまでを担当する。Prefectから実行する場合は`scripts/phase3_prefect_flow.py`がこのCLIを呼び出す。

### Phase 4

当日リアルタイムデータ取得の設計段階。目的、取得対象、追加テーブル案、タスク、完了条件は`docs/PHASE4_REALTIME_DATA_INGESTION.md`にまとめている。

Phase 4の実装候補:

- `apps/api/app/ingestion/live/`
- `apps/api/tests/ingestion/live/`
- `scripts/phase4_run_live_pipeline.py`
- `scripts/phase4_prefect_flow.py`

## 6. データ配置ルール

公式Rawデータは再配布しない。Gitには入れない。

正しい配置:

```text
data/raw/official_downloads/racer_period_stats/
data/raw/official_downloads/race_cards/
data/raw/official_downloads/race_results/
data/raw/extracted/racer_period_stats/
data/raw/extracted/race_cards/
data/raw/extracted/race_results/
```

置かないもの:

```text
data/B260530.TXT
data/K260530.TXT
data/*.lzh
data/*:Zone.Identifier
```

ルート直下の`data/*.TXT`や`data/*.lzh`は、分類ミスとして削除対象にする。

## 7. 今回整理した内容

2026-06-01に追加で整理した内容:

- Phase 2の`download_files`、`racer_period_stats_raw`、`racer_period_stats`を作るmigrationを復旧した
- Phase 3 migrationをPhase 2 migrationの後続へ接続し、Phase 2成果物を落とす不要なdropを除去した
- 既存DB向けに`uq_racer_period_stats_raw_file_line`を復旧するrepair migrationを追加した
- `apps/api/app/ingestion/race_downloads.py`を追加し、B/KファイルURL、保存パス、日付範囲、場コード絞り込みを共通化した
- `scripts/phase3_run_all_pipeline.py`を台帳付きCLIへ更新した
- `docker-compose.yml`のAPIサービスへ`./data:/data`と`./scripts:/scripts`を追加した
- Phase 3用pytestを追加し、URL生成、保存パス、`race_id`、B/Kパース、正規化の基本仕様を固定した
- Raw行Upsert時に最新の`raw_file_id`へ更新されることをpytestで固定した
- `apps/api/app/ingestion/race_quality.py`を追加し、レース数、出走数、結合率、着順、ST/進入/艇番、払戻、Raw parse statusを検証できるようにした
- PostgreSQL実体を使ったUpsert冪等性pytestを追加した
- `scripts/phase3_prefect_flow.py`を追加し、Phase 3 CLIをPrefect Flowから実行できるようにした
- `PREFECT_API_URL=http://127.0.0.1:4200/api`でPhase 3 Flow dry-run Completedを確認した
- HTTP取得のリトライ方針を定義し、timeout、通信エラー、408、429、5xxの指数バックオフ再試行を実装した
- 実データの払戻欄をもとに合成fixtureを拡充し、単勝、複勝、2連単、2連複、拡連複、3連単、3連複を保存できるようにした
- 解凍失敗、パース失敗、品質チェック失敗の自動部分再開は、現時点では実装しない判断にした
- README、ロードマップ、Phase 3設計書、構成台帳を現状へ更新した

削除したGit管理対象:

- `data/B260530.TXT`
- `data/K260530.TXT`
- `data/b260530.lzh:Zone.Identifier`
- `data/k260530.lzh:Zone.Identifier`
- `data/raw/lzh/.gitkeep`

削除したローカル生成物:

- `data/b260530.lzh`
- `data/k260530.lzh`
- `data/tmp/`
- `apps/api/.uv-cache/`
- `apps/api/.prefect/`
- `apps/api/.pytest_cache/`
- `apps/api/.ruff_cache/`
- `apps/api/.mypy_cache/`
- `apps/web/.next/`
- `apps/web/playwright-report/`
- `apps/web/test-results/`
- `mlruns/`
- `__pycache__/`

追加した配置:

- `data/raw/extracted/race_cards/.gitkeep`
- `data/raw/extracted/race_results/.gitkeep`
- `data/raw/extracted/racer_period_stats/.gitkeep`

修正した構成:

- `.gitignore`に`apps/api/.uv-cache/`、`apps/api/.prefect/`、`data/tmp/`、`data/*.TXT`、`*:Zone.Identifier`を追加した
- `apps/web/README.md`をcreate-next-appの雛形からプロジェクト用READMEへ置き換えた
- `apps/api/app/ingestion/race_cards/parse.py`の途中importを解消した
- `apps/api/app/ingestion/race_results/parse.py`の重複import、重複関数定義を解消した
- `scripts/phase3_run_all_pipeline.py`の未使用importを削除した
- Pythonファイル全体を`ruff format`で整形した
- `ruff check`、`ruff format --check`、`mypy app`、`pytest`の通過を確認した

追加整理した一時スクリプト:

- `scripts/phase2_check_racer_period_stats_layout.py`を削除した
- `scripts/phase2_parse_racer_period_stats.py`を削除した
- `scripts/phase2_ingest_racer_period_stats.py`を削除した
- `scripts/phase2_ingest_parsed_stats.py`を削除した
- `scripts/phase3_check_parser.py`を削除した
- `scripts/phase3_load_local_sample.py`を削除した

削除理由:

- 固定パスや先頭数行だけを使う手動確認スクリプトだった
- `phase2_run_all_pipeline.py`または`phase3_run_all_pipeline.py`と責務が重複していた
- DB保存の途中工程だけを実行するサンプルで、現在の運用導線として残すと混乱しやすい

追加整理したWeb雛形ファイル:

- `apps/web/public/file.svg`を削除した
- `apps/web/public/globe.svg`を削除した
- `apps/web/public/next.svg`を削除した
- `apps/web/public/vercel.svg`を削除した
- `apps/web/public/window.svg`を削除した
- `apps/web/AGENTS.md`を削除した
- `apps/web/CLAUDE.md`を削除した

削除理由:

- Next.js初期雛形のSVGで、現在の画面・CSS・テストから参照されていなかった
- `AGENTS.md`/`CLAUDE.md`は実行時にも開発コマンドにも不要で、引き継ぎ情報は`docs/`へ集約する方針にした

## 8. まとめなかったもの

`scripts/`は現時点ではフラットなまま維持する。ただし、残す対象は「実行導線として意味があるもの」に絞る。

理由:

- `phase2_`、`phase3_`の接頭辞で責務が明確
- 一時確認やサンプル投入は削除済み
- 既存ドキュメントや実行コマンドへの影響が大きい
- Phase 3の正式CLI化またはPrefect Flow化の時点で、`scripts/phase2/`、`scripts/phase3/`、`scripts/ops/`へ移すほうが安全

`apps/api/app/ingestion/race_cards/`と`apps/api/app/ingestion/race_results/`も統合しない。

理由:

- BファイルとKファイルはレイアウト、Raw行、正規化、保存先が異なる
- 共通化は`race_id.py`、解凍、文字コード、download/raw/run記録側に寄せるほうがよい

## 9. 次に整理する候補

Phase 3完了前に整理したいもの:

- 新CLIで3日全場、1か月などの長めの台帳付き再実行を検証する
- 古い年代や特殊払戻の実例が出たら、parser versionとfixtureを追加する
- `scripts/`をサブディレクトリへ移動する場合は、Phase 4以降のFlow配置方針と同時に行う

## 10. 確認コマンド

Git管理対象の確認:

```bash
git ls-files
git status --short
```

無視される生成物の確認:

```bash
git status --ignored --short
```

Python品質チェック:

```bash
cd apps/api
uv run ruff check app tests ../../scripts
uv run ruff format --check app tests ../../scripts
uv run mypy app
uv run pytest
```

Web品質チェック:

```bash
cd apps/web
pnpm format:check
pnpm lint
pnpm test:e2e
```
