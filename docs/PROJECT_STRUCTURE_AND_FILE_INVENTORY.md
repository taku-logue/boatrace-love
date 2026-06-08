# BOATRACE=LOVE プロジェクト構成・ファイル台帳

作成日: 2026-05-30
更新日: 2026-06-08
対象ブランチ: `phase9-backtesting-ev-analysis`

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
- `apps/web/.pnpm-store/`
- `apps/web/playwright-report/`
- `apps/web/test-results/`
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

Phase 9 MVPまで完了済み。現在はPhase 7予測APIをNext.js Web画面から利用し、指定`raceId`の6艇1着確率ランキングを確認できるうえ、Phase 9 CLIで単勝期待値と均等買いバックテストを実行できる。次の中心はPhase 10の運用・監視、またはPhase 9 P1の予測snapshot保存/segment評価/Web期待値表示である。

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
│   │   │       ├── 2401a26dff2a_add_phase4_tables_for_realtime_data.py
│   │   │       ├── 6c2f1a91b8e7_realign_phase4_live_snapshot_tables.py
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
│   │   │   ├── backtesting/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── engine.py
│   │   │   │   └── schemas.py
│   │   │   ├── features/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── aggregations.py
│   │   │   │   ├── build.py
│   │   │   │   ├── export.py
│   │   │   │   ├── labels.py
│   │   │   │   ├── leakage.py
│   │   │   │   └── quality.py
│   │   │   ├── ml/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dataset.py
│   │   │   │   ├── evaluate.py
│   │   │   │   ├── preprocessing.py
│   │   │   │   ├── registry.py
│   │   │   │   ├── split.py
│   │   │   │   └── train.py
│   │   │   ├── prediction/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── errors.py
│   │   │   │   ├── features.py
│   │   │   │   ├── model_store.py
│   │   │   │   ├── schemas.py
│   │   │   │   └── service.py
│   │   │   ├── routers/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── dependencies.py
│   │   │   │   ├── models.py
│   │   │   │   └── predictions.py
│   │   │   ├── ingestion/
│   │   │   │   ├── archive.py
│   │   │   │   ├── encoding.py
│   │   │   │   ├── html_fetcher.py
│   │   │   │   ├── race_downloads.py
│   │   │   │   ├── race_id.py
│   │   │   │   ├── race_quality.py
│   │   │   │   ├── live/
│   │   │   │   │   ├── __init__.py
│   │   │   │   │   ├── load.py
│   │   │   │   │   └── parse.py
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
│   │   │       ├── odds.py
│   │   │       ├── payouts.py
│   │   │       ├── pre_race_info.py
│   │   │       ├── race_cards.py
│   │   │       ├── race_master.py
│   │   │       ├── race_results.py
│   │   │       └── racer_period_stats.py
│   │   └── tests/
│   │       ├── __init__.py
│   │       ├── conftest.py
│   │       ├── test_main.py
│   │       ├── backtesting/
│   │       │   ├── __init__.py
│   │       │   └── test_engine.py
│   │       ├── features/
│   │       │   ├── __init__.py
│   │       │   ├── test_aggregations.py
│   │       │   ├── test_build.py
│   │       │   ├── test_export.py
│   │       │   ├── test_labels.py
│   │       │   ├── test_leakage.py
│   │       │   └── test_quality.py
│   │       ├── ml/
│   │       │   ├── __init__.py
│   │       │   ├── test_dataset.py
│   │       │   ├── test_evaluate.py
│   │       │   ├── test_preprocessing.py
│   │       │   ├── test_split.py
│   │       │   └── test_train.py
│   │       ├── prediction/
│   │       │   ├── __init__.py
│   │       │   ├── helpers.py
│   │       │   ├── test_model_store.py
│   │       │   ├── test_prediction_features.py
│   │       │   ├── test_prediction_routes.py
│   │       │   └── test_prediction_service.py
│   │       └── ingestion/
│   │           ├── live/
│   │           │   ├── test_load_db.py
│   │           │   └── test_parse.py
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
│       ├── .prettierignore
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
│   │   ├── .gitkeep
│   │   ├── features/
│   │   │   └── .gitkeep
│   │   ├── models/
│   │   │   └── .gitkeep
│   │   └── reports/
│   │       └── .gitkeep
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
│   ├── PHASE5_FEATURE_ENGINEERING.md
│   ├── PHASE6_MODEL_TRAINING.md
│   ├── PHASE7_PREDICTION_API.md
│   ├── PHASE8_WEB_FRONTEND.md
│   ├── PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md
│   └── PROJECT_STRUCTURE_AND_FILE_INVENTORY.md
└── scripts/
    ├── check_mlflow.py
    ├── check_prefect.py
    ├── phase2_discover_racer_period_stats.py
    ├── phase2_run_all_pipeline.py
    ├── phase3_prefect_flow.py
    ├── phase3_run_all_pipeline.py
    ├── phase4_check_quality.py
    ├── phase4_prefect_flow.py
    ├── phase4_run_live_pipeline.py
    ├── phase5_build_features.py
    ├── phase6_train_model.py
    └── phase9_backtest_win.py
```

## 4. 主要ディレクトリの責務

| パス | 責務 | Git管理方針 |
|---|---|---|
| `apps/api/app/main.py` | FastAPIエントリーポイント | 管理する |
| `apps/api/app/core/` | API設定 | 管理する |
| `apps/api/app/db/` | SQLAlchemy接続 | 管理する |
| `apps/api/app/models/` | DBモデル | 管理する |
| `apps/api/app/ingestion/` | 取得、解凍、文字コード、パース、正規化、DB投入の部品 | 管理する |
| `apps/api/app/features/` | Phase 5特徴量dataset生成 | 管理する |
| `apps/api/app/ml/` | Phase 6 dataset検証、前処理、学習、評価、MLflow記録 | 管理する |
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

## 4.1 ファイル別役割台帳

Phase 5以降の作業者は、まずこの節を読んでから対象ファイルを開く。ここでは「どのファイルが何を担当しているか」「どのフェーズの成果物か」「次フェーズで触る可能性があるか」を整理する。

### ルート・環境設定

| ファイル | 役割 | 主な利用者/呼び出し元 | Phase 5以降の注意 |
|---|---|---|---|
| `.env.example` | ローカル環境変数の雛形。DB、Prefect、MLflowなどの接続情報を示す | 開発者、Docker Compose、API設定 | 実値は`.env`に置く。`.env`はGit管理しない |
| `.gitignore` | Rawデータ、仮想環境、cache、生成物をGitから除外する | Git | `data/raw/**`は実データを入れない。`.gitkeep`だけ例外 |
| `docker-compose.yml` | PostgreSQL、API、Web、Prefect、MLflowのローカル統合環境 | 開発者、CI候補 | APIは`/data/processed/models`からPhase 7 model bundleを読む。MLflow台帳/artifactは`mlruns/`へ永続化 |
| `README.md` | 開発者向け入口。進捗、起動方法、主要コマンドをまとめる | 人間、AIエージェント | 詳細は各Phase docへ誘導する。長い設計はdocsへ寄せる |

### API基盤

| ファイル | 役割 | 主な利用者/呼び出し元 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/Dockerfile` | APIコンテナのビルド定義。7-ZipとLightGBM用`libgomp1`を含む | Docker Compose | 追加ライブラリは`pyproject.toml`とOS runtimeの両方を確認する |
| `apps/api/pyproject.toml` | Python依存関係、ruff、mypy設定。LightGBM/scikit-learn/joblibを含む | `uv`、品質チェック | ML依存を更新したらlockとDocker buildを確認する |
| `apps/api/uv.lock` | Python依存関係のlock | `uv` | 手動編集しない。依存追加後に`uv`で更新 |
| `apps/api/app/main.py` | FastAPIアプリ本体。health/db/versionとPhase 7 routerの入口 | API server、Web | router追加時はここでincludeする |
| `apps/api/app/core/config.py` | `.env`から設定を読むPydantic Settings。DB/model root/default modelを持つ | DB接続、アプリ設定 | 追加envはここに定義する。Docker内は`/data`、ローカルはrepo内`data`を読む |
| `apps/api/app/db/session.py` | SQLAlchemy engine、DB疎通確認、FastAPI用`get_db` dependency | API、scripts、tests | requestごとのSession注入はここを使う |

### Alembic / DB Migration

| ファイル | 役割 | 主な利用者/呼び出し元 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/alembic.ini` | Alembic設定ファイル | `uv run alembic ...` | DB URLは`env.py`が`.env`値で上書きする |
| `apps/api/alembic/env.py` | SQLAlchemyモデルを読み込み、Alembicへmetadataを渡す | Alembic | 新モデルを追加したら`app.models.__init__`経由で読み込まれるか確認 |
| `apps/api/alembic/script.py.mako` | migration生成テンプレート | Alembic | 通常触らない |
| `fea2050a2b26_create_initial_metadata_tables.py` | `data_sources`、`ingestion_runs`、`raw_files`など初期メタデータテーブル | Alembic | 全Phaseの台帳基盤 |
| `b48e5d316863_create_phase2_racer_period_stats_tables.py` | Phase 2のレーサー期別成績Raw/正規化テーブル | Alembic | 選手特徴量の元データ |
| `d5f2f8a0c1e4_repair_phase3_phase2_raw_constraint.py` | 既存DB向けのPhase 2/3制約repair | Alembic | 削除しない。途中DBの救済用 |
| `2aa075ebabae_add_phase3_tables_for_race_cards_and_.py` | Phase 3のレース、出走表、結果、払戻テーブル | Alembic | Phase 5特徴量生成の中核 |
| `2401a26dff2a_add_phase4_tables_for_realtime_data.py` | 初期Phase 4 migration。旧案のテーブルを作る | Alembic | 後続repairがあるため単独で最終形と見なさない |
| `6c2f1a91b8e7_realign_phase4_live_snapshot_tables.py` | Phase 4現行schemaへ整合させるrepair migration | Alembic | Phase 4以降の正しいhead。`alembic current`はこれになる |

### SQLAlchemy Models

| ファイル | 役割 | 主なテーブル/クラス | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/app/models/base.py` | SQLAlchemy Declarative Base | `Base` | 全モデルの基底 |
| `apps/api/app/models/__init__.py` | モデルの集約import。Alembicがmetadataへ全モデルを載せるための入口 | 全モデル | 新モデル追加時はここへexportする |
| `apps/api/app/models/management.py` | 取得元、取得run、Raw file台帳 | `DataSource`, `IngestionRun`, `RawFile` | データ再現性と監査の中心 |
| `apps/api/app/models/downloads.py` | 公式LZHダウンロード単位の台帳 | `DownloadFile` | Phase 2/3の取得ファイル単位 |
| `apps/api/app/models/racer_period_stats.py` | レーサー期別成績Raw/正規化 | `RacerPeriodStatRaw`, `RacerPeriodStat` | 選手能力特徴量の元 |
| `apps/api/app/models/race_master.py` | レース場とレースmaster | `Venue`, `Race` | すべてのPhaseを`race_id`で接続する中核 |
| `apps/api/app/models/race_cards.py` | 番組表Rawと出走艇情報 | `RaceCardRaw`, `RaceEntry` | 出走表特徴量、選手/モーター/ボート特徴量の入口 |
| `apps/api/app/models/race_results.py` | 競走成績Rawと艇別結果 | `RaceResultRaw`, `RaceResult` | 教師ラベル、過去成績特徴量の入口 |
| `apps/api/app/models/payouts.py` | 払戻情報 | `Payout` | 回収率/期待値/バックテストの入口 |
| `apps/api/app/models/pre_race_info.py` | 当日直前情報、展示、気象、水面、取得status | `LiveFetchStatus`, `WeatherObservation`, `PreRaceEntryInfo` | 展示後特徴量と当日補正の入口 |
| `apps/api/app/models/odds.py` | オッズsnapshotと組番別オッズ | `OddsSnapshot`, `OddsSnapshotEntry` | 期待値計算、オッズ込み/なしモデル比較の入口 |

### Ingestion 共通部品

| ファイル | 役割 | 主な利用者/呼び出し元 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/app/ingestion/archive.py` | LZH解凍処理 | Phase 2/3 CLI | 新しい公式圧縮ファイル取得が必要な場合に再利用 |
| `apps/api/app/ingestion/encoding.py` | 公式TXTの文字コード判定/読み込み補助 | Phase 2/3 parser | TXT系Rawを増やす場合に再利用 |
| `apps/api/app/ingestion/race_id.py` | `YYYYMMDD_VV_RR`形式の`race_id`生成 | Phase 3/4 parser | Phase 5以降でも必ずこのIDでjoinする |
| `apps/api/app/ingestion/race_downloads.py` | B/KファイルのURL生成、保存パス、日付範囲、場コードfilter | Phase 3 CLI/tests | 過去データ再取得時の入口 |
| `apps/api/app/ingestion/race_quality.py` | Phase 3の正規化データ品質チェック | Phase 3 CLI/tests | 学習前データ検査へ発展可能 |
| `apps/api/app/ingestion/html_fetcher.py` | Phase 4 HTML取得、Raw保存パス、SHA-256、RawFile用パス生成 | Phase 4 CLI | 当日HTML取得を増やす場合はここを使う |

### Phase 2/3 Parser・Loader

| ファイル | 役割 | 主な入出力 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/app/ingestion/racer_period_stats/layouts.py` | レーサー期別成績の固定長layout定義 | Raw TXT -> field定義 | 選手特徴量の項目確認に使う |
| `apps/api/app/ingestion/race_cards/layouts.py` | 番組表Bファイルの固定長layout定義 | Raw TXT -> field定義 | 出走表parserの項目確認に使う |
| `apps/api/app/ingestion/race_cards/parse.py` | 番組表BファイルをRaw/正規化候補へparse | B TXT -> records | 欠損や年代差分が出たらここを修正 |
| `apps/api/app/ingestion/race_cards/normalize.py` | 番組表の正規化補助 | parsed fields -> normalized values | 特徴量用の整形と混同しない |
| `apps/api/app/ingestion/race_cards/load.py` | `races`、`race_card_raw`、`race_entries`へUpsert | records -> DB | Phase 4当日出走表もここを再利用 |
| `apps/api/app/ingestion/race_results/layouts.py` | 競走成績Kファイルの固定長layout定義 | Raw TXT -> field定義 | 結果項目確認に使う |
| `apps/api/app/ingestion/race_results/parse.py` | 競走成績KファイルをRaw/正規化候補へparse | K TXT -> records | 払戻/着順/決まり手の入口 |
| `apps/api/app/ingestion/race_results/normalize.py` | 競走成績の正規化補助 | parsed fields -> normalized values | 教師ラベル生成時に参照 |
| `apps/api/app/ingestion/race_results/load.py` | `races`、`race_result_raw`、`race_results`、`payouts`へUpsert | records -> DB | 教師データの保存先 |

### Phase 4 Live Ingestion

| ファイル | 役割 | 主な入出力 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/app/ingestion/live/__init__.py` | Phase 4 parser/load関数の公開口 | import集約 | scriptsからここ経由でimportする |
| `apps/api/app/ingestion/live/parse.py` | 当日HTML parser。開催場、出走表、直前情報、単勝オッズを抽出 | HTML -> records | 実HTMLをtestsへ入れない。合成HTMLでfixture追加 |
| `apps/api/app/ingestion/live/load.py` | 当日直前情報、気象、オッズ、取得statusをDBへUpsert | records -> DB | snapshotの一意キーは`fetched_at`込み |

### Phase 5 Features

| ファイル | 役割 | 主な入出力 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/app/features/__init__.py` | Phase 5特徴量packageの入口 | import集約 | 公開関数が増えたら整理する |
| `apps/api/app/features/labels.py` | `race_results`から`target_win`、`target_top2`、`target_top3`、`exclude_reason`を生成 | result records -> labels DataFrame | 結果系カラムを特徴量として混ぜない |
| `apps/api/app/features/leakage.py` | 結果系カラムや`target_*`混入の検知 | DataFrame -> validation | 学習用最終dfではなく特徴量X側にかける |
| `apps/api/app/features/build.py` | 出走表、期別成績、過去成績、展示/気象、単勝オッズを結合するfeature builderと、label付きtraining dataset builder | DB -> feature DataFrame | Phase 7ではlabelなし`build_feature_dataset`を使う。`build_training_dataset`はPhase 6学習用 |
| `apps/api/app/features/quality.py` | dataset品質チェックとPhase 4 status/parser error検査 | DataFrame -> metrics/error | 6艇充足率、必須特徴量欠損、欠損フラグ、top2/top3整合を検査する |
| `apps/api/app/features/export.py` | datasetをParquetへ保存し、読み戻し検証後にschema JSONを出す | DataFrame -> Parquet + schema | 生成物は`data/processed/features/`へ出すがGit管理しない |
| `apps/api/app/features/aggregations.py` | 直近30/60/90走、コース別、場別の過去成績をshift付きで集計する | history DataFrame -> aggregate features | 対象レース自身の結果を特徴量へ入れない |

### Phase 6 Machine Learning

| ファイル | 役割 | 主な入出力 | Phase 7以降の注意 |
|---|---|---|---|
| `apps/api/app/ml/__init__.py` | Phase 6 ML packageの入口 | import集約 | 公開APIを増やす場合だけ整理する |
| `apps/api/app/ml/dataset.py` | Phase 5 Parquet/schema検証、対象行・6艇完全レース抽出、feature/target分離、leakage guard | Parquet + schema -> PreparedDataset | Phase 7推論でも同じ除外列と`frame_no`契約を使う |
| `apps/api/app/ml/split.py` | `race_date`によるtrain/valid/test時系列分割 | DataFrame -> TimeSplit | ランダムsplitへ置き換えない |
| `apps/api/app/ml/preprocessing.py` | 数値/真偽値/カテゴリ列処理、未知カテゴリmapping、設定JSONの保存・読み戻し | feature DataFrame -> LightGBM入力 | 推論時は学習済みmappingを必ず再利用する |
| `apps/api/app/ml/train.py` | LightGBM学習、early stopping、予測、feature importance、joblib保存・読み戻し | train/valid -> model artifact | Phase 7はmodel bundleと同じfeature順を使う |
| `apps/api/app/ml/evaluate.py` | レース内確率正規化と確率評価指標 | raw probability -> normalized probability + metrics | Phase 7 APIの確率正規化でも再利用する |
| `apps/api/app/ml/registry.py` | MLflowへparams、metrics、model/report artifactsを記録 | local artifacts -> MLflow run | tracking URIはローカル`127.0.0.1:5000`、Docker内`mlflow:5000` |

### Phase 7 Prediction API

| ファイル | 役割 | 主な入出力 | Phase 8以降の注意 |
|---|---|---|---|
| `apps/api/app/prediction/__init__.py` | Phase 7 prediction packageの入口 | import集約 | 公開口が増えたら整理する |
| `apps/api/app/prediction/errors.py` | API error contract | internal error -> JSON response | error codeをWeb側と揃える |
| `apps/api/app/prediction/schemas.py` | model metadata、prediction、errorのPydantic schema | Python object -> OpenAPI/JSON | Phase 8 Webがこのresponseを表示する。Phase 9の期待値APIでも契約を崩さない |
| `apps/api/app/prediction/model_store.py` | file-based model store。latest解決、artifact検証、model/preprocessor load、cache | `data/processed/models` -> LoadedModelBundle | 任意pathを読ませない。model bundle契約を崩さない |
| `apps/api/app/prediction/features.py` | 指定`race_id`の推論feature整形、6艇チェック、metadata/feature分離 | DB feature DataFrame -> PreparedPredictionFeatures | `target_*`、結果系、払戻系をfeatureへ混ぜない |
| `apps/api/app/prediction/service.py` | model view検証、前処理、LightGBM推論、レース内確率正規化、rank付け | Session + race_id -> PredictionResponse | feature列の不足/余剰を黙って補完しない |
| `apps/api/app/routers/__init__.py` | FastAPI router packageの入口 | import集約 | router追加時に整理する |
| `apps/api/app/routers/dependencies.py` | ModelStore/PredictionServiceのFastAPI dependency | settings -> dependency singleton | testsでは`dependency_overrides`で差し替える |
| `apps/api/app/routers/models.py` | `GET /models/latest` | HTTP -> ModelMetadataResponse | Phase 8のmodel状態表示で使用中 |
| `apps/api/app/routers/predictions.py` | `GET /races/{race_id}/prediction` | HTTP -> PredictionResponse | Phase 8の予測比較tableで使用中 |

### Phase 9 Backtesting

| ファイル | 役割 | 主な入出力 | Phase 10以降の注意 |
|---|---|---|---|
| `apps/api/app/backtesting/__init__.py` | Phase 9 backtesting packageの入口 | import集約 | 公開口が増えたら整理する |
| `apps/api/app/backtesting/schemas.py` | backtest設定、単勝オッズ、単勝払戻、bet candidate、summary、resultの型 | Python object -> dict/JSON/CSV | DB永続化前のreport契約。列名を変える時はWeb/分析側と同期する |
| `apps/api/app/backtesting/engine.py` | 単勝期待値計算、最新単勝オッズ取得、単勝払戻取得、PredictionService実行、filter、均等買いsummary、report保存 | DB + model -> summary JSON + bets CSV | P0は単勝のみ。複数券種やsnapshot保存はここへ混ぜすぎず拡張単位を分ける |

### Scripts

| ファイル | 役割 | 主な利用者/呼び出し元 | Phase 5以降の注意 |
|---|---|---|---|
| `scripts/check_prefect.py` | Prefect疎通確認 | 開発者 | Prefect Server起動確認用 |
| `scripts/check_mlflow.py` | MLflow dummy run確認 | 開発者 | Phase 5/6の実験管理前に確認 |
| `scripts/phase2_discover_racer_period_stats.py` | レーサー期別成績の取得対象探索 | 開発者 | Phase 2補助 |
| `scripts/phase2_run_all_pipeline.py` | Phase 2の取得/解凍/parse/load実行CLI | 開発者、Prefect候補 | 選手成績再投入時に使う |
| `scripts/phase3_run_all_pipeline.py` | Phase 3のB/K取得/解凍/parse/load/品質チェックCLI | 開発者、Prefect | 過去レースDB構築の主導線 |
| `scripts/phase3_prefect_flow.py` | Phase 3 CLIをPrefectから呼ぶwrapper | Prefect | ロジックはCLI側に置く |
| `scripts/phase4_run_live_pipeline.py` | Phase 4当日HTML取得/Raw保存/DB保存/台帳記録CLI | 開発者、Prefect | 当日取得の主導線。高頻度実行しない |
| `scripts/phase4_prefect_flow.py` | Phase 4 CLIをPrefectから呼ぶwrapper | Prefect | ロジックはCLI側に置く |
| `scripts/phase4_check_quality.py` | Phase 4品質チェックCLI | 開発者、CI候補 | 取得後/学習前の検査に使う |
| `scripts/phase5_build_features.py` | Phase 5特徴量dataset生成CLI | 開発者、Phase 6 | 期間、場、R、view、dry-run、Parquet保存、data root、品質skipを指定できる。Prefect wrapperはPhase 6以降候補 |
| `scripts/phase6_train_model.py` | Phase 5 datasetの検証、時系列split、前処理、LightGBM学習、評価、保存、MLflow記録を行うCLI | 開発者、Phase 7 | 生成物はGit管理しない。`--skip-mlflow`は隔離テスト用途 |
| `scripts/phase9_backtest_win.py` | Phase 9単勝期待値・均等買いbacktest CLI。summary JSONとbets CSVを出力する | 開発者、Phase 10候補 | 生成reportは`data/processed/reports/phase9/`へ出す。P0は単勝のみ |

### Tests

| ファイル | 役割 | 対象 | Phase 5以降の注意 |
|---|---|---|---|
| `apps/api/tests/test_main.py` | API health系の最小テスト | FastAPI | API router追加時の基本確認 |
| `apps/api/tests/ingestion/test_racer_period_stats_parse.py` | Phase 2 parser基本仕様 | 期別成績 | 選手成績parser変更時に更新 |
| `apps/api/tests/ingestion/test_race_downloads.py` | B/K URL、保存パス、日付範囲、venue filter | Phase 3 download helper | 過去データ取得仕様の固定 |
| `apps/api/tests/ingestion/test_phase3_download_retry.py` | Phase 3 HTTP retry/backoff仕様 | Phase 3 CLI helper | retry挙動変更時に更新 |
| `apps/api/tests/ingestion/test_race_id.py` | `race_id`形式 | Phase 3/4共通 | joinキーなので壊さない |
| `apps/api/tests/ingestion/test_race_parsers.py` | B/K parser基本仕様 | Phase 3 parser | 実Rawをそのまま入れない |
| `apps/api/tests/ingestion/test_race_upserts.py` | SQL発行なしのUpsert仕様 | Phase 3 load | DB非依存の仕様確認 |
| `apps/api/tests/ingestion/test_race_upserts_db.py` | PostgreSQL実体でのUpsert冪等性 | Phase 3 load | DBがなければskipする設計 |
| `apps/api/tests/ingestion/test_race_quality.py` | Phase 3品質チェック仕様 | race_quality | 学習前検査へ発展可能 |
| `apps/api/tests/ingestion/live/test_parse.py` | Phase 4 live parser仕様 | live/parse | 合成HTMLで仕様固定 |
| `apps/api/tests/ingestion/live/test_load_db.py` | Phase 4 DB Upsert冪等性 | live/load | PostgreSQL実体で確認 |
| `apps/api/tests/features/test_labels.py` | 目的変数生成仕様 | features/labels | 欠場/失格などの扱いを追加する |
| `apps/api/tests/features/test_leakage.py` | 未来情報混入検知仕様 | features/leakage | 禁止カラム追加時に更新 |
| `apps/api/tests/features/test_build.py` | model view別dataset build仕様 | features/build | 実DBではなくmock中心。integration testは今後追加 |
| `apps/api/tests/features/test_quality.py` | dataset品質チェック仕様 | features/quality | 欠損閾値や通常レース判定を変える場合に更新 |
| `apps/api/tests/features/test_export.py` | Parquet保存、読み戻し、schema JSON出力仕様 | features/export | 出力形式を増やす場合に更新 |
| `apps/api/tests/features/test_aggregations.py` | 過去成績集計のリーク防止仕様 | features/aggregations | windowや集計粒度を増やす場合に更新 |
| `apps/api/tests/ml/test_dataset.py` | Parquet/schema、完全レース抽出、feature/target分離、leakage仕様 | ml/dataset | 入力契約変更時に更新 |
| `apps/api/tests/ml/test_split.py` | 時系列splitとrace_id非重複仕様 | ml/split | split戦略変更時に更新 |
| `apps/api/tests/ml/test_preprocessing.py` | category mapping、未知値、feature drift仕様 | ml/preprocessing | 推論前処理と同期する |
| `apps/api/tests/ml/test_evaluate.py` | レース内正規化と評価指標仕様 | ml/evaluate | 確率出力契約の回帰防止 |
| `apps/api/tests/ml/test_train.py` | LightGBM学習、予測、importance、model保存smoke | ml/train | LightGBM更新時の最小確認 |
| `apps/api/tests/prediction/helpers.py` | Phase 7テスト用の小さいmodel bundle生成helper | prediction tests | 本番artifactをテストへ混ぜない |
| `apps/api/tests/prediction/test_model_store.py` | latest解決、artifact読込、不正identifier拒否 | prediction/model_store | model bundle契約変更時に更新 |
| `apps/api/tests/prediction/test_prediction_features.py` | 推論feature整形、target除外、6艇不足error | prediction/features | 予測入力契約の回帰防止 |
| `apps/api/tests/prediction/test_prediction_service.py` | 推論service、確率合計、feature drift error | prediction/service | model/preprocess契約の回帰防止 |
| `apps/api/tests/prediction/test_prediction_routes.py` | `/models/latest`、`/races/{race_id}/prediction`、error JSON | FastAPI routers | Web/API間のHTTP contract |
| `apps/api/tests/backtesting/test_engine.py` | 単勝期待値、filter、対象0件summary、ROI/的中率集計 | backtesting/engine | Phase 9の期待値/回収率契約の回帰防止 |

### Docs

| ファイル | 役割 | Phase 5以降の注意 |
|---|---|---|
| `docs/BOATRACE_ANALYTICS_ROADMAP.md` | 全体ロードマップとPhase別進捗 | Phase変更時に要更新 |
| `docs/PHASE0_REQUIREMENTS_AND_VALIDATION.md` | 要件、MVP範囲、評価指標、データ利用方針 | 予測対象や評価指標を変える時に参照 |
| `docs/PHASE1_PROJECT_SETUP.md` | Docker/API/Web/DB/Prefect/MLflow基盤 | 環境変更時に更新 |
| `docs/PHASE2_RACER_PERIOD_STATS_INGESTION.md` | レーサー期別成績取り込み仕様 | 選手特徴量の元データ仕様 |
| `docs/PHASE3_RACE_RESULTS_AND_CARDS_INGESTION.md` | 番組表/結果/払戻取り込み仕様 | 教師データと過去特徴量の元 |
| `docs/PHASE4_REALTIME_DATA_INGESTION.md` | 当日出走表/直前情報/気象/オッズ取り込み仕様 | 当日予測特徴量の元 |
| `docs/PHASE5_FEATURE_ENGINEERING.md` | 特徴量設計、学習用データセット作成の完了条件と証跡 | Phase 6の学習入力を作る前の最初の参照先 |
| `docs/PHASE6_MODEL_TRAINING.md` | 機械学習モデル、評価、MLflow記録の設計・完了タスク・実走証跡 | Phase 7でmodel bundle契約を確認する最初の参照先 |
| `docs/PHASE7_PREDICTION_API.md` | 予測APIの目的、P0/P1/P2タスク、完了条件、API契約 | Phase 7実装時の最初の参照先 |
| `docs/PHASE8_WEB_FRONTEND.md` | Web予測ダッシュボードの目的、P0/P1/P2タスク、完了条件、検証証跡 | Phase 8 Web UIやPhase 9画面拡張前の参照先 |
| `docs/PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md` | 単勝期待値、均等買いbacktest、P0/P1/P2タスク、完了条件、検証証跡 | Phase 9 P1やPhase 10日次評価前の参照先 |
| `docs/PROJECT_STRUCTURE_AND_FILE_INVENTORY.md` | この台帳。構成、役割、引き継ぎ情報 | 他AIエージェントの最初の入口 |

### Web App

| ファイル | 役割 | Phase 5以降の注意 |
|---|---|---|
| `apps/web/package.json` | Web依存関係とnpm/pnpm scripts | UI追加時にscripts確認 |
| `apps/web/src/app/layout.tsx` | Next.js App Routerの全体layout | 共通meta/themeを置く |
| `apps/web/src/app/page.tsx` | Phase 8予測ダッシュボード。API/DB/model status、`raceId`入力、6艇予測ranking、model contract、top pickを表示する | Phase 9で期待値/買い目/バックテストを足す場合はcomponent分割を検討する |
| `apps/web/src/app/globals.css` | Tailwind/global CSS | UI方針に沿って更新 |
| `apps/web/tests/dashboard.spec.ts` | Phase 8予測ダッシュボードのE2E。起動、API/model表示、6艇tableを確認する | 画面変更時に更新 |
| `apps/web/playwright.config.ts` | Web E2E設定 | dev server/port変更時に更新 |
| `apps/web/next.config.ts` | Next.js設定 | API proxy等が必要なら更新 |
| `apps/web/eslint.config.mjs` | ESLint設定 | TypeScript/React品質 |
| `apps/web/.prettierignore` | Web整形対象から依存/ビルド/Playwright生成物を外す | 生成物を増やしたら追記 |
| `apps/web/postcss.config.mjs` | PostCSS/Tailwind処理 | 通常触らない |
| `apps/web/tsconfig.json` | TypeScript設定 | 型生成導入時に調整 |

### Data Directories

| パス | 役割 | Git管理 |
|---|---|---|
| `data/raw/official_downloads/racer_period_stats/` | 公式レーサー期別成績LZH保存先 | `.gitkeep`のみ |
| `data/raw/official_downloads/race_cards/` | 公式番組表B LZH保存先 | `.gitkeep`のみ |
| `data/raw/official_downloads/race_results/` | 公式競走成績K LZH保存先 | `.gitkeep`のみ |
| `data/raw/extracted/racer_period_stats/` | 解凍済み期別成績TXT保存先 | `.gitkeep`のみ |
| `data/raw/extracted/race_cards/` | 解凍済みB TXT保存先 | `.gitkeep`のみ |
| `data/raw/extracted/race_results/` | 解凍済みK TXT保存先 | `.gitkeep`のみ |
| `data/raw/html/race_cards/` | 当日出走表HTML保存先 | `.gitkeep`のみ |
| `data/raw/html/exhibition/` | 直前情報HTML保存先 | `.gitkeep`のみ |
| `data/raw/html/odds/` | オッズHTML保存先 | `.gitkeep`のみ |
| `data/interim/` | 中間生成物置き場 | `.gitkeep`のみ |
| `data/processed/` | 学習/分析用生成済みデータ置き場 | `.gitkeep`のみ |
| `data/processed/features/` | Phase 5特徴量Parquet出力先 | `.gitkeep`のみ。生成ParquetはGit管理しない |
| `data/processed/models/` | Phase 6 model bundle出力先 | `.gitkeep`のみ。joblib/JSONはGit管理しない |
| `data/processed/reports/` | Phase 6評価レポート、importance、予測Parquet、Phase 9 backtest report出力先 | `.gitkeep`のみ。生成物はGit管理しない |

## 4.2 Phase 10以降の作業者向け読み順

Phase 10以降、またはPhase 9 P1/P2を担当するAIエージェントは、次の順番で読むと取り違えにくい。

1. `docs/PROJECT_STRUCTURE_AND_FILE_INVENTORY.md`
2. `docs/PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md`
3. `docs/PHASE8_WEB_FRONTEND.md`
4. `docs/PHASE7_PREDICTION_API.md`
5. `docs/PHASE6_MODEL_TRAINING.md`
6. `docs/PHASE5_FEATURE_ENGINEERING.md`
7. `docs/BOATRACE_ANALYTICS_ROADMAP.md`のPhase 9以降
8. `apps/api/app/backtesting/`
9. `scripts/phase9_backtest_win.py`
10. `apps/api/app/prediction/`
11. `apps/api/app/routers/`
12. `apps/web/src/app/page.tsx`
13. `apps/api/app/ml/`
14. `apps/api/app/features/`
15. `apps/api/app/models/`

Phase 10以降で学習済みmodel/API/backtestを使う場合の基本方針:

- model bundleは`model.joblib`、`model_metadata.json`、`feature_columns.json`、`categorical_columns.json`、`preprocessing_config.json`を一組として扱う
- 推論featureの列順、カテゴリmapping、`frame_no`変換は学習時と一致させる
- 艇ごとの生確率は`normalize_probabilities_by_race`でレース内合計1へ正規化する
- 6艇が揃っていない入力を通常予測として扱わない
- `race_id`、`race_date`、`boat_no`はmetadataとして保持し、モデル特徴量へ直接入れない
- 結果系、払戻、`target_*`は予測時特徴量へ混ぜない
- APIへモデルversionを公開する場合はlocal timestampまたはMLflow run idとの対応を固定する
- Phase 9 P0の期待値は単勝のみ。`expected_value = win_probability * win_odds`で、生成reportは`data/processed/reports/phase9/`へ保存する
- backtest reportはGit管理しない。比較が必要な場合はsummary JSONの主要値をdocsへ転記する

不用意に変更しないほうがよいもの:

- `race_id`生成仕様
- Alembicの既存revision順序
- `data/raw/**`のGit管理方針
- Phase 2/3/4のRaw台帳記録方針
- `scripts/phase3_run_all_pipeline.py`と`scripts/phase4_run_live_pipeline.py`のCLI引数互換性
- Phase 6 model bundle内のfeature順と前処理mapping

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

当日リアルタイムデータ取得のMVP導線は完了済み。当日開催場、出走表、直前情報、気象、単勝オッズの取得、Raw保存、DB保存、品質チェック、Prefect dry-runまで確認済み。

Phase 4の主な対象:

- `apps/api/app/ingestion/html_fetcher.py`
- `apps/api/app/ingestion/live/`
- `apps/api/tests/ingestion/live/`
- `apps/api/app/models/pre_race_info.py`
- `apps/api/app/models/odds.py`
- `apps/api/alembic/versions/2401a26dff2a_add_phase4_tables_for_realtime_data.py`
- `apps/api/alembic/versions/6c2f1a91b8e7_realign_phase4_live_snapshot_tables.py`
- `scripts/phase4_run_live_pipeline.py`
- `scripts/phase4_prefect_flow.py`
- `scripts/phase4_check_quality.py`

### Phase 5

特徴量設計・学習用dataset作成のMVPは完了済み。

Phase 5の主な対象:

- `apps/api/app/features/`
- `apps/api/tests/features/`
- `scripts/phase5_build_features.py`
- `data/processed/features/`
- `docs/PHASE5_FEATURE_ENGINEERING.md`

現在のPhase 5実行導線は`scripts/phase5_build_features.py`に集約している。このスクリプトはDB正規化済みテーブルから`race_id, boat_no`単位の特徴量行を作り、目的変数を結合し、品質チェックを行い、dry-runまたはParquet出力を行う。

確認済み:

- `pre_race_no_odds`: 2026-05-30全場で1080行、45カラム、品質チェックpass、Parquet保存pass
- `pre_race_with_odds`: 2026-06-01 場23 1Rで6行、49カラム、品質チェックpass、Parquet保存pass
- `exhibition_with_odds`: 2026-06-01 場23 1Rで6行、63カラム、品質チェックpass、Parquet保存pass

Phase 5 MVPの残タスクはなし。モデル学習、期待値、買い目生成、バックテストはPhase 6以降へ送る。

### Phase 6

機械学習モデル作成のMVPは完了済み。Phase 5 Parquet/schemaを入力に、対象レース検証、時系列split、前処理、LightGBM学習、レース内確率正規化、評価、artifact保存、MLflow記録までをCLIへ集約している。

Phase 6の主な対象:

- `apps/api/app/ml/`
- `apps/api/tests/ml/`
- `scripts/phase6_train_model.py`
- `data/processed/models/`
- `data/processed/reports/`

現在のPhase 6実行導線は`scripts/phase6_train_model.py`に集約している。`exclude_reason is null`かつ6艇完全・勝者1艇のレースだけを使い、`boat_no`はmetadataとして保持しながら`frame_no`特徴量へ変換する。

確認済み:

- 2026-05-28から2026-05-30のPhase 5 dataset: 2,832行、472レース、45カラム
- 完全レース抽出後: 432レース
- train 134レース、valid 136レース、test 162レース
- test Log Loss 0.363987、Brier Score 0.110115、Race hit rate 50.62%
- MLflow run `daa591bbeaf04bea86b011fbde7c00ef`
- MLflow 2.22.2のSQLite台帳/artifactを`mlruns/`へ永続化し、container再作成後もrunを再取得できる
- Docker build、Docker内学習CLI、API health
- `ruff format --check`、`ruff check`、`mypy app`、`pytest 63 passed`

P1/P2のオッズ/展示込みモデル比較、segment評価、Calibration、Optuna、SHAP、Prefect Flowは後続改善候補。

### Phase 7

予測APIのMVPは完了済み。Phase 6のfile-based model bundleを読み込み、指定`race_id`の6艇について1着確率を返すFastAPI endpointを実装している。

Phase 7の主な対象:

- `apps/api/app/prediction/`
- `apps/api/app/routers/`
- `apps/api/app/features/build.py`
- `apps/api/app/core/config.py`
- `apps/api/app/db/session.py`
- `apps/api/tests/prediction/`
- `docs/PHASE7_PREDICTION_API.md`

現在のPhase 7 API導線:

- `GET /models/latest`: 最新model bundleのmetadataを返す
- `GET /races/{race_id}/prediction`: 指定raceの6艇へ正規化済み1着確率を返す

確認済み:

- model bundle: `data/processed/models/lgbm_win_v1/20260607T144526Z`
- `GET /models/latest`: HTTP 200、`model_name=lgbm_win_v1`、`model_version=20260607T144526Z`
- `GET /races/20260528_01_01/prediction`: HTTP 200、6 entries、`probability_sum=1.0`
- Docker Compose API containerで同endpointを確認済み
- `ruff format .`、`ruff check .`、`mypy app`、`pytest 74 passed`

P1/P2の`pre_race_with_odds`/`exhibition_with_odds`予測、予測snapshot保存、今日の開催/レース一覧、OpenAPI example拡充、期待値、買い目生成、バックテストは後続改善候補。

### Phase 8

WebフロントエンドのMVPは完了済み。Phase 7予測APIをNext.jsのserver componentから呼び、指定`raceId`の6艇1着確率ランキングをローカル画面で確認できる。

Phase 8の主な対象:

- `apps/web/src/app/page.tsx`
- `apps/web/src/app/layout.tsx`
- `apps/web/tests/dashboard.spec.ts`
- `apps/web/.gitignore`
- `apps/web/.prettierignore`
- `docs/PHASE8_WEB_FRONTEND.md`

現在のPhase 8 Web導線:

- `http://localhost:3000?raceId=20260528_01_01`: 予測ダッシュボード
- `GET /health`: API status panel
- `GET /db/health`: Database status panel
- `GET /models/latest`: Model status / Model Contract panel
- `GET /races/{race_id}/prediction`: Prediction Board table / Top Pick panel

確認済み:

- Web画面で`BOATRACE=LOVE`、`raceId=20260528_01_01`、6艇table、model contract、top pickを表示できる
- desktop幅でページ全体の横スクロールなし
- mobile幅でページ全体の横スクロールなし。テーブルのみ内部横スクロール
- Web整形、ESLint、Docker build、Playwright E2E `1 passed`

P1/P2の日付/場/R selector、レース詳細panel、期待値ranking、買い目候補UI、バックテスト画面、model性能画面は後続改善候補。

### Phase 9

バックテスト・期待値分析のMVPは完了済み。Phase 7の予測サービス、Phase 4の単勝オッズ、Phase 3の単勝払戻を結合し、単勝期待値と均等買いbacktestをCLIで実行できる。

Phase 9の主な対象:

- `apps/api/app/backtesting/`
- `apps/api/tests/backtesting/`
- `scripts/phase9_backtest_win.py`
- `data/processed/reports/phase9/`
- `docs/PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md`

現在のPhase 9実行導線:

```bash
cd apps/api
uv run python ../../scripts/phase9_backtest_win.py \
  --from-date 2026-06-01 \
  --to-date 2026-06-01 \
  --venue-code 23 \
  --min-expected-value 1.0 \
  --max-races 12
```

確認済み:

- DB上の単勝オッズは`odds_snapshot_entries` 84行
- DB上の払戻は`payouts` 3370行
- 単勝オッズと単勝払戻が重なるraceは2026-06-01 場23の12R
- 対象0件でもsummary JSON/bets CSVを保存して正常終了する
- 2026-06-01 場23 12R、`min_expected_value=0`: evaluated_races 12、evaluated_candidates 72、bet_count 72、hit_count 12、roi 0.473611
- 2026-06-01 場23 12R、`min_expected_value=1.0`: evaluated_races 12、evaluated_candidates 72、bet_count 29、hit_count 1、roi 0.068966
- `ruff check`、`mypy app`、`pytest 78 passed`

P1/P2の予測snapshot保存、条件preset、segment評価、オッズ時刻選択、Web期待値表示、複数券種、Kelly基準、DB永続化は後続改善候補。

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
data/raw/html/race_cards/YYYYMMDD/
data/raw/html/exhibition/YYYYMMDD/
data/raw/html/odds/YYYYMMDD/
data/processed/features/
data/processed/models/
data/processed/reports/
data/processed/reports/phase9/
```

置かないもの:

```text
data/B260530.TXT
data/K260530.TXT
data/*.lzh
data/*:Zone.Identifier
data/raw/html/YYYYMMDD/
```

ルート直下の`data/*.TXT`、`data/*.lzh`、分類なしの`data/raw/html/YYYYMMDD/`は、分類ミスとして整理対象にする。ただし`data/raw/**`配下の実データはGit管理外のローカル生成物であり、検証用途への影響を確認してから移動または削除する。

## 7. 今回整理した内容

2026-06-08にPhase 9実装で整理した内容:

- `docs/PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md`を追加した
- `phase9-backtesting-ev-analysis`ブランチを作成した
- Phase 9 MVPを、単勝期待値計算と均等買いbacktestをCLIで再現できる導線として実装した
- `apps/api/app/backtesting/`へschema、backtest engine、report出力を追加した
- `scripts/phase9_backtest_win.py`を追加し、日付範囲、場、R、model、stake、EV/オッズ/rank条件、出力先を指定できるようにした
- `apps/api/tests/backtesting/`を追加し、期待値計算、filter、対象0件summary、ROI/的中率集計を固定した
- 2026-06-01 場23の12Rで単勝オッズと単勝払戻が重なることを確認した
- `min_expected_value=0`で72候補/12的中/roi 0.473611、`min_expected_value=1.0`で29候補/1的中/roi 0.068966の実走reportを生成した
- reportは`data/processed/reports/phase9/`へ保存し、Git管理しない方針にした
- `ruff check`、`mypy app`、`pytest 78 passed`を確認した
- README、ロードマップ、構成台帳、Phase 9 docへPhase 9 MVP完了状態を反映した
- P1/P2として、予測snapshot保存、条件preset、segment評価、オッズ時刻選択、Web期待値表示、複数券種、Kelly基準、DB永続化を残した

2026-06-08にPhase 8実装で整理した内容:

- `docs/PHASE8_WEB_FRONTEND.md`を追加した
- `phase8-web-frontend`ブランチを作成した
- Phase 8 MVPを、Phase 7予測APIをNext.js画面から呼び出し、指定`raceId`の6艇1着確率ランキングを表示するWebダッシュボードとして実装した
- `apps/web/src/app/page.tsx`へAPI/DB/model status、`raceId`入力、Prediction Board、Model Contract、Top Pickを実装した
- `apps/web/src/app/layout.tsx`のmetadataと言語設定をBOATRACE=LOVE向けに更新した
- `apps/web/tests/dashboard.spec.ts`を予測ランキング表示のE2Eへ更新した
- `apps/web/.prettierignore`を追加し、`.pnpm-store`、Playwright report/test-results、`.next`などの生成物を整形対象から外した
- `apps/web/.gitignore`へ`.pnpm-store`を追加した
- Docker Compose Web containerで`http://localhost:3000?raceId=20260528_01_01`の表示を確認した
- Browserでdesktop/mobile幅を確認し、mobileではページ全体の横スクロールを出さず、tableのみ内部スクロールにした
- Web整形、ESLint、Docker build、Playwright E2E `1 passed`を確認した
- README、ロードマップ、構成台帳、Web READMEへPhase 8 MVP完了状態を反映した
- P1/P2として、日付/場/R selector、レース詳細panel、期待値ranking、買い目候補UI、バックテスト画面、model性能画面を残した

2026-06-08にPhase 7実装で整理した内容:

- `docs/PHASE7_PREDICTION_API.md`を追加した
- `phase7-prediction-api`ブランチを作成した
- Phase 7 MVPを、Phase 6のmodel bundleをFastAPIから読み、指定`race_id`の6艇へ正規化済み1着確率を返すAPIとして実装した
- `apps/api/app/features/build.py`へlabelなし`build_feature_dataset`を追加し、`build_training_dataset`は従来どおりlabel結合用として残した
- `apps/api/app/prediction/`へmodel store、推論feature整形、schema、error、prediction serviceを追加した
- `apps/api/app/routers/`へ`GET /models/latest`と`GET /races/{race_id}/prediction`を追加した
- `.env.example`と`docker-compose.yml`へ`MODEL_ROOT`、`DEFAULT_MODEL_NAME`、`DEFAULT_MODEL_VIEW`、`PREDICTION_CACHE_ENABLED`を追加した
- `apps/api/tests/prediction/`を追加し、model store、feature整形、service、router contractを固定した
- Docker Compose API containerで`/models/latest`と`/races/20260528_01_01/prediction`のHTTP 200を確認した
- `ruff format .`、`ruff check .`、`mypy app`、`pytest 74 passed`を確認した
- P1/P2として、`pre_race_with_odds`、`exhibition_with_odds`、予測snapshot保存、今日のレース一覧、期待値、買い目生成、バックテストを残した

2026-06-07にPhase 6実装で整理した内容:

- `phase6-model-training`ブランチを作成した
- `lightgbm`、`scikit-learn`、`joblib`をAPIの直接依存へ追加した
- `apps/api/app/ml/`へdataset、split、preprocessing、train、evaluate、registryを実装した
- `apps/api/tests/ml/`へloader、split、preprocess、normalization、metrics、artifact読み戻し、LightGBM smokeの11テストを追加した
- `scripts/phase6_train_model.py`へ学習・評価・保存・MLflow記録の主導線を集約した
- dataset/schemaのSHA-256をevaluation report、model metadata、MLflow paramsへ記録した
- `data/processed/models/`と`data/processed/reports/`を追加し、生成物はGit管理外とした
- API Docker imageへLightGBM実行に必要な`libgomp1`を追加した
- MLflow client/serverを`2.22.2`へ揃え、SQLite台帳とartifactを`mlruns/`へ永続化した
- 2026-05-28から2026-05-30の432完全レースでLightGBM baselineを実走した
- MLflow run `daa591bbeaf04bea86b011fbde7c00ef`でparams、metrics、model、reportsを確認し、container再作成後も再取得した
- `ruff format --check`、`ruff check`、`mypy app`、`pytest 63 passed`を確認した
- mainがPhase 5完了状態を含んでいることを確認し、Phase 2/3ブランチはmainの祖先だったためマージせず削除した
- 古いPhase 3由来のstashは、mainに取り込むべき差分ではなく旧一時スクリプト/旧docを含むため破棄した
- pytest/ruff/mypy cache、`__pycache__`、Phase 5検証用Parquet/schema、誤配置の`data/raw/html/20260601/`、ローカルMLflow runを削除した
- `docs/PHASE6_MODEL_TRAINING.md`を追加した
- Phase 6 MVPを`target_win`のLightGBM二値分類baselineとして定義した
- Phase 5 Parquet dataset、schema JSON、時系列split、未来情報混入防止、レース内確率正規化、評価指標、MLflow記録、model artifact保存を完了条件にした
- Phase 6のP0/P1/P2タスクと完了条件を整理した
- README、ロードマップ、構成台帳へPhase 6 docと現状ステータスを反映した

2026-06-05にPhase 5向けに整理した内容:

- `apps/api/app/features/build.py`がCLIコマンド文字列だけになっていた破損を修正し、正式なdataset builderへ復旧した
- `fetch_base_features`、`add_racer_period_stats`、`add_historical_performance_features`、`add_pre_race_features`、`add_odds_features`、`build_training_dataset`を実装した
- `scripts/phase5_build_features.py`をDocker APIコンテナでもimportできるように`/app`をimport pathへ追加した
- `scripts/phase5_build_features.py`へ`--venue-code`、`--race-no`、`--data-root`、`--skip-quality`を追加した
- Phase 5品質チェックへmodel view別必須特徴量、6艇充足率、`target_top2`/`target_top3`整合、欠損フラグ、Phase 4 status/parser error検査を追加した
- `apps/api/app/features/export.py`でParquet保存後の読み戻し検証と`.schema.json`出力を実装した
- `apps/api/app/features/aggregations.py`で直近30/60/90走、コース別、場別の1着率/2連対率/3連対率をshift付きで生成できるようにした
- 期別成績joinを`period_year <= race_year`から、前期5月1日/後期11月1日を利用可能日の近似とするas-of判定へ改善した
- `apps/api/app/ingestion/html_fetcher.py`のrepo root検出を固定`parents[4]`から親ディレクトリ探索へ変更し、Docker内`/app/app/...`配置でもPhase 4 CLI import時に落ちないようにした
- Phase 3 CLIで2026-06-01 場23の`race_results`を追加投入し、12R/72行の教師ラベルを確認した
- `data/processed/features/.gitkeep`を追加し、Parquet出力先ディレクトリをGit上でも保持するようにした
- `pre_race_no_odds`は2026-05-30全場で1080行、45カラム、品質チェックpass、Parquet保存passを確認した
- `pre_race_with_odds`は2026-06-01 場23 1Rで6行、49カラム、品質チェックpass、Parquet保存passを確認した
- `exhibition_with_odds`は2026-06-01 場23 1Rで6行、63カラム、品質チェックpass、Parquet保存passを確認した
- `dataset_boat_features_v1_pre_race_no_odds.parquet`、`dataset_boat_features_v1_pre_race_with_odds.parquet`、`dataset_boat_features_v1_exhibition_with_odds.parquet`と各`.schema.json`の生成を確認した。生成物はGit管理しない
- `ruff check`、`ruff format --check`、`mypy app`、`pytest tests/features -q`、`pytest -q`の通過を確認した
- README、ロードマップ、Phase 5設計書、構成台帳を現状へ更新した

2026-06-03にPhase 4向けに整理した内容:

- `apps/api/app/models/__init__.py`が存在しない`app.models.race`、`app.models.result`をimportしていた破損を修正した
- Phase 4モデルを`LiveFetchStatus`、`WeatherObservation`、`PreRaceEntryInfo`、`OddsSnapshot`、`OddsSnapshotEntry`へ整理した
- `6c2f1a91b8e7_realign_phase4_live_snapshot_tables.py`を追加し、旧Phase 4 migrationと現行モデルの不整合をrepairした
- `apps/api/app/ingestion/html_fetcher.py`を`httpx`、分類済みRaw HTML保存、SHA-256計算、RawFile記録用パス生成へ整理した
- `apps/api/app/ingestion/live/parse.py`で出走表の`boat_no`上書きバグを修正し、支部、モーター、ボート、展示進入、展示ST、欠場オッズを扱えるようにした
- `apps/api/app/ingestion/live/load.py`で直前情報、気象、オッズsnapshot/entryを冪等Upsertできるようにした
- `scripts/phase4_run_live_pipeline.py`を正式CLI化し、Raw HTML、`raw_files`、SHA-256、取得URL、`ingestion_runs`、`live_fetch_status`を記録できるようにした
- `scripts/phase4_prefect_flow.py`をPhase 4 CLIの薄いwrapperとして更新し、retry/backoff/data-root引数に追従させた
- `scripts/phase4_check_quality.py`を現行schema向けに更新し、出走表、直前情報、気象、単勝オッズ、取得失敗status、parser行数異常を検査できるようにした
- Phase 4専用pytestとして`apps/api/tests/ingestion/live/test_parse.py`と`test_load_db.py`を追加した
- `scripts/phase4_check_fetcher.py`と`scripts/phase4_test_bs4.py`を削除した
- `uv run alembic upgrade head`でhead `6c2f1a91b8e7`まで適用できることを確認した
- `phase4_run_live_pipeline.py --race-date 2026-06-01 --venue-code 23 --race-no 1 --only all`の通常実行成功を確認した
- `phase4_prefect_flow.py`のdry-runがPrefectでCompletedになることを確認した
- `phase4_check_quality.py --race-date 2026-06-01`で24レース検査passを確認した
- `ruff check`、`ruff format --check`、`mypy app`、`pytest`の通過を確認した

削除理由:

- `scripts/phase4_check_fetcher.py`と`scripts/phase4_test_bs4.py`は固定日付/固定パスの手動検証スクリプトで、文字化けもあり、正式CLIと品質チェックに責務が移ったため

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

- `phase2_`、`phase3_`、`phase4_`の接頭辞で責務が明確
- 一時確認やサンプル投入は削除済み
- 既存ドキュメントや実行コマンドへの影響が大きい
- Phase 4のCLI/Flow運用が固まった後に、`scripts/phase2/`、`scripts/phase3/`、`scripts/phase4/`、`scripts/ops/`へ移すほうが安全

`apps/api/app/ingestion/race_cards/`と`apps/api/app/ingestion/race_results/`も統合しない。

理由:

- BファイルとKファイルはレイアウト、Raw行、正規化、保存先が異なる
- 共通化は`race_id.py`、解凍、文字コード、download/raw/run記録側に寄せるほうがよい

## 9. 次に整理する候補

Phase 5以降、または運用前に整理したいもの:

- 複勝、2連単、2連複、3連単、3連複など単勝以外のオッズ取得範囲を決める
- 部品交換を専用カラム化する必要が出た場合のschema追加。現時点では`raw_values.parts_replaced`保持で進める
- 1日全場の通常実行リハーサルを、公式サイトへのアクセス負荷に配慮して低頻度で検証する
- API確認エンドポイントをPhase 7/8の画面要件と合わせて設計する

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
