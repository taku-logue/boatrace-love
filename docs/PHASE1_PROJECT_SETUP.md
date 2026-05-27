# Phase 1 プロジェクト初期構成・開発環境構築 設計書

作成日: 2026-05-26
更新日: 2026-05-27

## 1. Phase 1の目的

Phase 1では、Phase 0で決定したMVP方針に基づき、開発・分析・データ取得・API・Web画面を継続的に拡張できる土台を構築する。

このフェーズでは、予測精度を上げることは目的にしない。目的は、以後のデータ取得、DB投入、特徴量生成、学習、推論、バックテスト、画面表示を壊れにくく進められるプロジェクト基盤を作ることである。

## 2. Phase 1で作るもの

Phase 1の成果物は以下。

- モノレポ構成
- Python開発環境
- Next.js + TypeScript開発環境
- PostgreSQL
- Docker Compose
- FastAPIのヘルスチェックAPI
- Next.jsの初期画面
- AlembicによるDBマイグレーション
- SQLAlchemyのDB接続
- Prefectのバッチ実行基盤
- MLflowの実験管理基盤
- Rawデータ保存ディレクトリ
- lint、format、test設定
- `.env`管理方針
- READMEの開発手順

## 3. Phase 1でまだ作らないもの

以下はPhase 1では作らない。

- 本格的な公式データ取得
- LZH解凍処理
- レース結果パーサー
- LightGBM学習処理
- 特徴量生成
- 単勝バックテスト
- 本番デプロイ
- Web公開
- ユーザー認証
- 自動投票

Phase 1では、空の器と最低限の疎通確認に集中する。

## 4. 推奨ディレクトリ構成

```text
BOATRACE=LOVE/
  apps/
    api/
      app/
        api/
        core/
        db/
        models/
        schemas/
        services/
        main.py
      tests/
      alembic/
      alembic.ini
      pyproject.toml
      Dockerfile
    web/
      app/
      components/
      features/
      lib/
      public/
      tests/
      package.json
      next.config.ts
      tsconfig.json
      Dockerfile
  ml/
    pipelines/
    features/
    training/
    evaluation/
    notebooks/
    tests/
    pyproject.toml
  data/
    raw/
      official_downloads/
      lzh/
      extracted/
      html/
      odds/
    processed/
    interim/
    external/
  infra/
    docker/
    db/
      init/
    prefect/
    mlflow/
  docs/
  scripts/
  .env.example
  .gitignore
  docker-compose.yml
  README.md
```

## 5. 前提ソフトウェア

ローカルPCに以下をインストールする。

### 必須

- Git
- Docker Desktop
- Node.js LTS
- pnpm
- Python 3.11以上
- uv
- 7-Zip

### 推奨

- VS Code
- PostgreSQLクライアント
- DBeaver、またはTablePlus
- PowerShell 7

## 6. インストール手順

## 6.0 インストール確認状況

2026-05-26時点で、以下のインストールを確認済み。

| ツール | 確認バージョン | 判定 | 備考 |
|---|---:|---|---|
| Git | `2.43.0` | OK | Git管理に使用可能 |
| Docker | `29.4.3` | OK | Docker Compose連携に使用可能 |
| Docker Compose | `v5.1.4` | OK | Phase 1のローカルサービス起動に使用可能 |
| Node.js | `v24.16.0` | OK | Next.js開発に使用。プロジェクト側でバージョンを固定する |
| pnpm | `11.3.0` | OK | Webパッケージ管理に使用 |
| Python | `3.12.3` | OK | Python 3.11以上の条件を満たす |
| uv | `0.11.16` | OK | Pythonパッケージ管理に使用 |
| 7-Zip | `23.01` | OK | LZH解凍に使用可能 |

現時点でPhase 1開始を妨げる問題はない。

注意点:

- Node.jsとpnpmは、後続で`package.json`の`packageManager`や`.node-version`などに固定し、環境差分を減らす。
- Pythonは`3.12.3`を前提に進める。`pyproject.toml`では`requires-python = ">=3.12,<3.13"`のように固定する。
- Docker Composeのサービス名、ポート、ボリュームはPhase 1実装時に`docker-compose.yml`で明示する。
- 7-ZipはPhase 2のLZH解凍で使うため、Phase 1では疎通確認のみでよい。

## 6.1 Git

WindowsではGit for Windowsをインストールする。

確認コマンド:

```powershell
git --version
```

## 6.2 Docker Desktop

Docker Desktopをインストールし、WSL2 backendを有効化する。

確認コマンド:

```powershell
docker --version
docker compose version
```

## 6.3 Node.jsとpnpm

Node.js LTSをインストールする。

pnpmはCorepack経由で有効化する。

```powershell
corepack enable
corepack prepare pnpm@latest --activate
node --version
pnpm --version
```

## 6.4 Pythonとuv

Pythonは3.11以上を使用する。パッケージ管理はuvに統一する。

```powershell
python --version
pip install uv
uv --version
```

## 6.5 7-Zip

LZH解凍のため、7-Zipをインストールする。

Windowsでは`7z.exe`へのPATHを通す。

確認コマンド:

```powershell
7z
```

## 7. 外部サービス・ローカルサービス

Phase 1では外部クラウドサービスを必須にしない。MVPは完全ローカル利用に限定する。

### 使用するローカルサービス

- PostgreSQL
- Prefect Server
- MLflow Tracking Server
- FastAPI
- Next.js

### 使わない外部サービス

- Firebase
- AWS本番環境
- GCP本番環境
- Vercel公開環境
- Kubernetes
- 外部認証サービス

## 8. Docker Compose設計

`docker-compose.yml`で以下のサービスを定義する。

| サービス | 役割 | ポート |
|---|---|---:|
| `postgres` | メインDB | 5432 |
| `api` | FastAPI | 8000 |
| `web` | Next.js | 3000 |
| `prefect-server` | バッチ管理 | 4200 |
| `mlflow` | 実験管理 | 5000 |

Phase 1では、各サービスが起動し、疎通できることを完了条件とする。

## 9. 環境変数設計

`.env`はGit管理しない。代わりに`.env.example`を作る。

`.env.example`例:

```env
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
POSTGRES_DB=boatrace_love
POSTGRES_USER=boatrace
POSTGRES_PASSWORD=boatrace_password

DATABASE_URL=postgresql+psycopg://boatrace:boatrace_password@postgres:5432/boatrace_love

API_HOST=0.0.0.0
API_PORT=8000

NEXT_PUBLIC_API_BASE_URL=http://localhost:8000

PREFECT_API_URL=http://prefect-server:4200/api
MLFLOW_TRACKING_URI=http://mlflow:5000

RAW_DATA_DIR=/workspace/data/raw
PROCESSED_DATA_DIR=/workspace/data/processed
```

秘密情報は`.env`にのみ置き、GitHubへコミットしない。

## 10. Python API構成

## 10.1 採用ライブラリ

`apps/api`では以下を導入する。

- fastapi
- uvicorn
- pydantic
- pydantic-settings
- sqlalchemy
- psycopg
- alembic
- pandas
- numpy
- httpx
- beautifulsoup4
- playwright
- prefect
- mlflow
- pandera
- pytest
- ruff
- mypy

Phase 1ではLightGBM、SHAP、Optunaはインストール対象に含めてもよいが、実装ではまだ使わない。

## 10.2 初期API

Phase 1で作るAPIは以下のみ。

- `GET /health`
- `GET /version`
- `GET /db/health`

レスポンス例:

```json
{
  "status": "ok",
  "service": "boatrace-love-api"
}
```

## 10.3 FastAPI構成

```text
apps/api/app/
  main.py
  core/
    config.py
  db/
    session.py
    health.py
  api/
    routes/
      health.py
```

## 11. DB設計の初期化

Phase 1では、本格テーブルの前に最低限の管理テーブルを作る。

初期テーブル:

- `schema_migrations`
- `data_sources`
- `ingestion_runs`
- `raw_files`

### `data_sources`

データ取得元を管理する。

```sql
CREATE TABLE data_sources (
  id SERIAL PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  base_url TEXT NOT NULL,
  description TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

### `ingestion_runs`

取得処理の実行履歴を管理する。

```sql
CREATE TABLE ingestion_runs (
  id BIGSERIAL PRIMARY KEY,
  source_id INTEGER REFERENCES data_sources(id),
  job_name TEXT NOT NULL,
  status TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  finished_at TIMESTAMPTZ,
  error_message TEXT
);
```

### `raw_files`

Rawファイルの保存場所とハッシュを管理する。

```sql
CREATE TABLE raw_files (
  id BIGSERIAL PRIMARY KEY,
  source_id INTEGER REFERENCES data_sources(id),
  ingestion_run_id BIGINT REFERENCES ingestion_runs(id),
  file_type TEXT NOT NULL,
  source_url TEXT,
  local_path TEXT NOT NULL,
  sha256 TEXT,
  fetched_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);
```

## 12. Alembic設定

`apps/api`にAlembicを導入する。

初期手順:

```powershell
cd apps/api
uv run alembic init alembic
uv run alembic revision -m "create initial metadata tables"
uv run alembic upgrade head
```

Alembicは`DATABASE_URL`を参照する。

マイグレーションは手書きSQLではなく、原則としてAlembicで管理する。

## 13. Next.js構成

## 13.1 採用ライブラリ

`apps/web`では以下を導入する。

- next
- react
- react-dom
- typescript
- tailwindcss
- zod
- @tanstack/react-query
- lucide-react
- eslint
- prettier
- @playwright/test

## 13.2 初期画面

Phase 1のWeb画面は、機能を作り込まず以下だけ表示する。

- アプリ名
- API接続状態
- DB接続状態
- Prefect URL
- MLflow URL

目的は、WebからAPIへ疎通できることを確認することである。

## 13.3 デザイン方針

MVPはローカル分析ダッシュボードであり、ランディングページではない。

初期画面も以下を意識する。

- 情報密度を高める
- 装飾を控える
- 実用的なダッシュボードにする
- 大きなヒーローやマーケティング文言は置かない

## 14. Prefect設定

Phase 1ではPrefect ServerをDocker Composeで起動する。

作るもの:

- Prefect Server
- サンプルFlow
- `GET /health`相当のバッチ疎通確認

サンプルFlow:

```python
from prefect import flow, task

@task
def say_ready() -> str:
    return "prefect ready"

@flow
def phase1_smoke_flow() -> str:
    return say_ready()
```

Phase 2以降で、公式データ取得、LZH解凍、Raw保存、DB投入をFlow化する。

## 15. MLflow設定

Phase 1ではMLflow Tracking ServerをDocker Composeで起動する。

目的:

- 実験管理画面を確認できる
- 将来のLightGBM学習結果を保存できる
- モデルファイル、パラメータ、メトリクスの保存先を固定する

Phase 1で作る確認スクリプト:

- dummy runを1件登録
- パラメータを保存
- メトリクスを保存

例:

```python
import mlflow

mlflow.set_experiment("phase1_smoke_test")

with mlflow.start_run():
    mlflow.log_param("phase", 1)
    mlflow.log_metric("smoke_test", 1.0)
```

## 16. Rawデータ保存設計

Phase 1では、Rawデータ保存ディレクトリと命名規則だけ決める。

```text
data/raw/
  official_downloads/
    racer_period_stats/
    race_results/
    race_cards/
  lzh/
  extracted/
  html/
    race_cards/
    odds/
    exhibition/
  odds/
```

ファイル命名規則:

```text
{source}_{data_type}_{target_date}_{venue_code}_{race_no}_{fetched_at}_{sha256_prefix}.{ext}
```

例:

```text
boatrace_odds_20260526_01_11_20260526T091500_abc12345.html
```

## 17. 品質管理

## 17.1 Python

Python側で設定するもの:

- ruff
- mypy
- pytest

代表コマンド:

```powershell
cd apps/api
uv run ruff check .
uv run ruff format .
uv run mypy app
uv run pytest
```

## 17.2 TypeScript

Web側で設定するもの:

- TypeScript strict
- ESLint
- Prettier
- Playwright test

代表コマンド:

```powershell
cd apps/web
pnpm lint
pnpm format
pnpm test:e2e
```

## 18. Git管理

## 18.1 `.gitignore`

最低限、以下を除外する。

```gitignore
.env
.venv/
node_modules/
.next/
__pycache__/
.pytest_cache/
.ruff_cache/
.mypy_cache/
data/raw/
data/interim/
data/processed/
mlruns/
*.lzh
*.zip
*.parquet
```

ただし、`data/`配下のディレクトリ構造は`.gitkeep`で残す。

## 18.2 ブランチ運用

個人開発でも、Phase単位でブランチを分ける。

例:

```text
codex/phase1-project-setup
codex/phase2-data-ingestion
codex/phase3-race-database
```

## 19. READMEに書く内容

Phase 1完了時点のREADMEには以下を記載する。

- プロジェクト概要
- Phase 0の決定事項へのリンク
- 必要ソフトウェア
- `.env`作成方法
- Docker Compose起動方法
- API確認方法
- Web確認方法
- DBマイグレーション方法
- テスト実行方法
- Prefect確認方法
- MLflow確認方法

## 20. Phase 1実装順序

推奨順序は以下。

1. `.gitignore`と`.env.example`を作る
2. ディレクトリ構成を作る
3. Docker Composeを作る
4. PostgreSQLを起動する
5. FastAPIを作る
6. APIからDB接続確認を行う
7. Alembicを導入する
8. 初期管理テーブルを作る
9. Next.jsを作る
10. WebからAPIの`/health`を表示する
11. Prefect Serverを追加する
12. サンプルFlowを動かす
13. MLflow Serverを追加する
14. dummy runを登録する
15. lint、format、testを整える
16. READMEを書く

## 21. Phase 1完了条件

以下をすべて満たせばPhase 1完了とする。

- `docker compose up`で主要サービスが起動する
- PostgreSQLへ接続できる
- FastAPIの`GET /health`が成功する
- FastAPIの`GET /db/health`が成功する
- Alembicで初期テーブルを作成できる
- Next.js画面からAPI接続状態を確認できる
- Prefect Server画面を開ける
- サンプルFlowが実行できる
- MLflow画面を開ける
- dummy runが登録できる
- Pythonのlint、format、testが実行できる
- TypeScriptのlint、format、E2Eテストが実行できる
- `.env.example`が存在する
- READMEに開発手順が書かれている

## 22. Phase 1での判断基準

Phase 1では、便利そうな技術を追加しすぎない。

採用する判断:

- Phase 0の決定事項を守るために必要
- データ取得や検証の再現性が上がる
- 後続フェーズの実装を安定させる
- 運用時の失敗原因を追跡しやすくなる

採用しない判断:

- 本番公開のためだけに必要
- 複数ユーザー運用のためだけに必要
- 自動投票のためだけに必要
- 3連単予測のためだけに必要
- 代替手段がすでにプロジェクト内にある

## 23. Phase 2への引き継ぎ

Phase 1完了後、Phase 2では以下に進む。

- BOAT RACE公式ダウンロードページの取得
- LZHファイル一覧の抽出
- LZHダウンロード
- LZH解凍
- Rawファイル保存
- `raw_files`へのメタデータ登録
- レーサー期別成績のパース
- データ品質チェック

Phase 2で迷わないよう、Phase 1ではデータ取得の中身ではなく、取得したデータを保存・追跡・検証できる器を完成させる。

## 24. 2026-05-27時点の進捗確認

現状、Phase 1は完了。

進捗: 100%

### 24.1 完了条件ベースの判定

| 完了条件 | 判定 | 確認結果 |
|---|---|---|
| `docker compose up`で主要サービスが起動する | 完了 | `postgres`、`api`、`web`、`prefect-server`、`mlflow`がCompose上で起動する。 |
| PostgreSQLへ接続できる | 完了 | `pg_isready`で接続可。 |
| FastAPIの`GET /health`が成功する | 完了 | Compose起動後にHTTP 200を確認。 |
| FastAPIの`GET /db/health`が成功する | 完了 | Compose起動後にHTTP 200を確認。 |
| Alembicで初期テーブルを作成できる | 完了 | `alembic_version`、`data_sources`、`ingestion_runs`、`raw_files`がDBに存在。 |
| Next.js画面からAPI接続状態を確認できる | 完了 | Compose起動後にWeb画面がHTTP 200を返す。 |
| Prefect Server画面を開ける | 完了 | `http://127.0.0.1:4200`でHTTP 200を確認。 |
| サンプルFlowが実行できる | 完了 | `scripts/check_prefect.py`がCompletedで終了。PrefectログにSQLite lock警告が出るため後続で安定化が必要。 |
| MLflow画面を開ける | 完了 | `http://127.0.0.1:5000`でHTTP 200を確認。 |
| dummy runが登録できる | 完了 | `scripts/check_mlflow.py`でdummy run登録済み。 |
| Pythonのlint、format、testが実行できる | 完了 | `ruff check`、`ruff format --check`、`mypy`、`pytest`が成功。 |
| TypeScriptのlint、format、E2Eテストが実行できる | 完了 | `format:check`、`lint`、`test:e2e`が成功。 |
| `.env.example`が存在する | 完了 | PostgreSQL、API、Web、Prefect、MLflow、Raw/Processedディレクトリの値が揃っている。 |
| READMEに開発手順が書かれている | 完了 | 起動、疎通、DBマイグレーション、Prefect、MLflow、品質コマンドの確認手順がある。 |

### 24.2 実装済みのもの

- ルート直下に`apps/`、`ml/`、`data/`、`infra/`、`docs/`、`scripts/`がある
- `apps/api/app/main.py`に`GET /health`と`GET /db/health`がある
- `apps/api/app/core/config.py`と`apps/api/app/db/session.py`でDB接続を行っている
- `apps/api/alembic/`と初期マイグレーションがある
- `apps/api/app/models/management.py`に`data_sources`、`ingestion_runs`、`raw_files`のモデルがある
- `apps/web/src/app/page.tsx`にAPI/DB接続状態を表示する初期画面がある
- `docker-compose.yml`に`api`と`web`が追加されている
- `apps/api/pyproject.toml`と`uv.lock`がある
- API DockerfileとWeb Dockerfileがある
- `GET /version`がある
- `scripts/check_prefect.py`にサンプルFlowがある
- `scripts/check_mlflow.py`にdummy run登録処理がある
- `data/raw/`、`data/interim/`、`data/processed/`、`data/external/`の基本ディレクトリと詳細ディレクトリがある
- `data/`配下の空ディレクトリ保持用`.gitkeep`がある

### 24.3 未実装・不足しているもの

Phase 1内の必須タスクに未完了項目はない。

補足:

- `zod`、`@tanstack/react-query`、`lucide-react`はPhase 1の疎通確認画面では未使用のため導入しない。API境界、非同期取得、UI部品が必要になるPhase 2以降で導入する。
- ローカルGitは初期化済み。
- GitHubリポジトリ`taku-logue/boatrace-love`を作成済みで、`origin`として設定済み。
- `main`ブランチの初回pushは完了済み。

### 24.4 次に進める順序

Phase 1は完了したため、次はPhase 2へ進む。

Phase 2開始前に行うこと:

1. Phase 2の作業ブランチを作成する
2. 公式ダウンロードページ取得、LZH一覧抽出、Raw保存の実装に着手する
3. 必要に応じてGitHub IssuesまたはProjectでPhase 2タスクを管理する

### 24.5 Phase 1未完了チェックリスト

Phase 1の必須タスクはすべて完了。

| 優先度 | タスク | 完了条件 |
|---|---|---|
| P0 | Python品質コマンドを整える | 完了 |
| P0 | Web品質コマンドを整える | 完了 |
| P1 | ルートREADMEを補完する | 完了 |
| P1 | Web依存の扱いを決める | 完了。Phase 2以降で必要時に導入する。 |
| P2 | Git管理状態を決める | 完了。ローカルGit初期化と初回コミットまで完了。 |
| 関連 | GitHubリポジトリを作成してpushする | 完了。`taku-logue/boatrace-love`へ`main`をpush済み。 |

Phase 1完了判定: 完了。
