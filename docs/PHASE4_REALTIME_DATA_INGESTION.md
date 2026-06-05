# Phase 4 当日リアルタイムデータ取得 設計書

作成日: 2026-06-01
更新日: 2026-06-03
ステータス: MVP完了
進捗目安: 100%

## 1. 目的

Phase 4では、BOAT RACE公式サイトの当日ページから、開催場、当日出走表、直前情報、展示、気象、オッズを取得し、Phase 5以降の特徴量生成と当日予測で使える形に保存する。

Phase 3までの過去番組表Bファイル、競走成績Kファイルと同じ`race_id`を使い、過去DBと当日DBを接続できることを重視する。

## 2. 2026-06-03時点の現状

Phase 4 MVPは完了。

当日開催場一覧、当日出走表、直前情報、展示、気象、単勝オッズを取得し、Raw HTML、取得台帳、正規化テーブルへ保存する導線が揃っている。Phase 5の特徴量生成では、Phase 4で作った`pre_race_entry_infos`、`weather_observations`、`odds_snapshots`、`odds_snapshot_entries`を入力として使える。

実装済み:

- `race_id`はPhase 3と同じ`YYYYMMDD_VV_RR`形式
- 当日開催場一覧、出走表、直前情報、単勝オッズのparserを実装
- `races`、`race_entries`、`pre_race_entry_infos`、`weather_observations`、`odds_snapshots`、`odds_snapshot_entries`へDB保存
- Raw HTMLを`data/raw/html/{race_cards|exhibition|odds}/YYYYMMDD/`へ保存
- Raw HTMLの`raw_files`、SHA-256、取得URL、`ingestion_runs`、`live_fetch_status`を記録
- CLIは対象日、場、R、取得種別、dry-run、sleep、retry/backoff、timeout、data-rootを指定可能
- Prefect FlowはCLI wrapperとして実装済み
- Phase 4 parser pytest、DB Upsert冪等性pytest、品質チェックCLIを追加済み
- `live_fetch_status.metadata`へparser version、期待行数、実際の行数、`parser_error_count`を記録

確認済み:

- `uv run alembic upgrade head`: 成功
- Alembic current: `6c2f1a91b8e7`
- `phase4_run_live_pipeline.py --race-date 2026-06-01 --venue-code 23 --race-no 1 --only all`: 成功
- `phase4_prefect_flow.py --race-date 2026-06-01 --venue-code 23 --race-no 1 --only all --dry-run`: Completed
- `phase4_check_quality.py --race-date 2026-06-01`: 24レース検査でpass、`parser_errors: 0`
- `ruff check`、`ruff format --check`、`mypy app`、`pytest`: pass

現DBで確認した台帳:

- Phase 4 `ingestion_runs`: 1件以上
- Phase 4 HTML `raw_files`: 記録あり
- `live_fetch_status`: `race_cards`、`pre_race`、`odds`のcompleted記録あり
- `live_fetch_status.metadata.parser_error_count`: 直近取得分は0
- `20260601_23_01`の単勝`odds_snapshots`: 2件

## 3. 現在のテーブル設計

既存テーブル:

- `data_sources`
- `ingestion_runs`
- `raw_files`
- `races`
- `race_entries`

Phase 4追加テーブル:

| テーブル | 目的 | 主なキー |
|---|---|---|
| `live_fetch_status` | 当日HTML取得の台帳 | `id` |
| `weather_observations` | 気象/水面snapshot | `(race_id, fetched_at)` |
| `pre_race_entry_infos` | 艇単位の直前情報snapshot | `(race_id, boat_no, fetched_at)` |
| `odds_snapshots` | オッズ取得単位 | `(race_id, bet_type, fetched_at)` |
| `odds_snapshot_entries` | 組番別オッズ | `(race_id, bet_type, fetched_at, combination)` |

補足:

- `2401a26dff2a`で作られた旧Phase 4テーブル案と、Gemini後のモデル定義が食い違っていたため、`6c2f1a91b8e7`でrepair migrationを追加した
- 旧`pre_race_info`や旧`odds_snapshots`が存在するDBでは、可能な範囲で新snapshotテーブルへ移行する
- 旧テーブルが存在しないDBでもmigrationが通るようにしている

## 4. 現在のファイル構成

主なPhase 4実装:

```text
apps/api/app/ingestion/html_fetcher.py
apps/api/app/ingestion/live/
  __init__.py
  load.py
  parse.py

apps/api/app/models/
  odds.py
  pre_race_info.py

apps/api/alembic/versions/
  2401a26dff2a_add_phase4_tables_for_realtime_data.py
  6c2f1a91b8e7_realign_phase4_live_snapshot_tables.py

apps/api/tests/ingestion/live/
  test_load_db.py
  test_parse.py

scripts/
  phase4_run_live_pipeline.py
  phase4_prefect_flow.py
  phase4_check_quality.py
```

Raw HTML保存先:

```text
data/raw/html/race_cards/YYYYMMDD/
data/raw/html/exhibition/YYYYMMDD/
data/raw/html/odds/YYYYMMDD/
```

補足:

- `data/raw/html/20260601/`のような分類なしフォルダは過去のローカル生成物として残っている場合がある
- 今後の正式保存先は分類済みディレクトリに統一する
- `data/raw/**`はGit管理外で、Gitへ入れるのは`.gitkeep`だけ

## 5. 実行コマンド

DB migration:

```bash
cd apps/api
uv run alembic upgrade head
```

CLI dry-run:

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

1R分の通常実行:

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

Prefect dry-run:

```bash
cd apps/api
PREFECT_API_URL=http://127.0.0.1:4200/api uv run python ../../scripts/phase4_prefect_flow.py \
  --race-date 2026-06-01 \
  --venue-code 23 \
  --race-no 1 \
  --only all \
  --dry-run \
  --sleep-seconds 0
```

品質チェック:

```bash
cd apps/api
uv run python ../../scripts/phase4_check_quality.py \
  --race-date 2026-06-01
```

Python品質チェック:

```bash
cd apps/api
uv run ruff check app tests ../../scripts
uv run ruff format --check app tests ../../scripts
uv run mypy app
uv run pytest
```

## 6. タスク一覧

### P0: 必須タスク

| ID | タスク | 状態 | メモ |
|---|---|---|---|
| P4-001 | Phase 4用ブランチを作る | 完了 | 既存の`codex/phase3-race-database`上で継続実装。ユーザー側でコミット/マージ管理 |
| P4-002 | 当日ページのURL、HTML構造、取得可否を確認する | 完了 | 開催場、出走表、直前情報、単勝オッズを確認 |
| P4-003 | `race_id`接続方針を確定する | 完了 | Phase 3と同一形式 |
| P4-004 | Phase 4用DBテーブルを確定する | 完了 | repair migrationで現schemaへ統一 |
| P4-005 | Raw HTML保存ルールを確定する | 完了 | Raw HTML、SHA-256、URL、run、statusを追跡 |
| P4-101 | 当日開催場一覧を取得する | 完了 | `parse_live_active_venues` |
| P4-102 | 当日レース一覧を取得する | 完了 | 1Rから12Rを巡回。存在しないRで停止 |
| P4-103 | 当日出走表HTMLをRaw保存する | 完了 | `data/raw/html/race_cards/` |
| P4-104 | 当日出走表をパースする | 完了 | 艇番、登番、選手名、級別、支部、モーター、ボート |
| P4-105 | `races`、`race_entries`へUpsertする | 完了 | `raw_card_file_id`も接続 |
| P4-201 | 直前情報HTMLをRaw保存する | 完了 | `data/raw/html/exhibition/` |
| P4-202 | 展示タイムを保存する | 完了 | `pre_race_entry_infos` |
| P4-203 | チルト、部品交換、展示進入を保存する | 完了 | チルト/展示進入は専用カラム、部品交換は`raw_values.parts_replaced`に保持 |
| P4-204 | 展示STを保存する | 完了 | F表記は負数へ正規化 |
| P4-205 | 気象、水面情報を保存する | 完了 | `weather_observations` |
| P4-301 | オッズページを取得する | 完了 | Phase 4 MVPは`oddstf`の単勝を対象。複勝/連勝系はPhase 5以降の拡張候補 |
| P4-302 | オッズHTMLをRaw保存する | 完了 | `data/raw/html/odds/` |
| P4-303 | オッズsnapshotを保存する | 完了 | `odds_snapshots` |
| P4-304 | 組番別オッズを保存する | 完了 | `odds_snapshot_entries` |
| P4-305 | オッズ取得頻度を制御する | 完了 | sleep/retry/backoff/timeoutをCLI指定 |

### P1: 運用性・品質

| ID | タスク | 状態 | メモ |
|---|---|---|---|
| P4-401 | Phase 4 CLIを作る | 完了 | 対象日、場、R、種別、dry-runを指定可能 |
| P4-402 | dry-runを作る | 完了 | DB更新前に対象URLを確認 |
| P4-403 | Prefect Flow化する | 完了 | CLI wrapper。dry-run Completed確認済み |
| P4-404 | 失敗runのリトライ方針を作る | 完了 | retry/backoffとfailed statusを実装 |
| P4-405 | 取得頻度とアクセス間隔を制御する | 完了 | `--sleep-seconds` |
| P4-406 | HTML構造変更時の検知を作る | 完了 | 品質チェックで欠損/異常を検知し、取得台帳にparser行数異常を記録 |
| P4-501 | HTML fixtureを作る | 完了 | 合成HTMLでテスト |
| P4-502 | 当日開催場一覧parserテストを作る | 完了 | `test_parse.py` |
| P4-503 | 当日出走表parserテストを作る | 完了 | `test_parse.py` |
| P4-504 | 直前情報parserテストを作る | 完了 | `test_parse.py` |
| P4-505 | オッズparserテストを作る | 完了 | 欠場/---も確認 |
| P4-506 | DB Upsert冪等性テストを作る | 完了 | `test_load_db.py` |
| P4-507 | 品質チェックを作る | 完了 | `phase4_check_quality.py` |
| P4-508 | ruff/format/mypy/pytestを通す | 完了 | 33 tests pass |

### P2: 追加・後続候補

| ID | タスク | 状態 | メモ |
|---|---|---|---|
| P4-601 | 記者予想の取得可否を確認する | 未着手 | 利用条件確認後に判断 |
| P4-602 | 記者予想を保存する | 未着手 | Phase 4 MVP外 |
| P4-603 | Playwright取得を最小導入する | 保留 | 現状の対象は静的HTMLで取得可能 |
| P4-604 | API確認エンドポイントを作る | Phase 7へ移管 | Web画面/API要件と合わせて設計する |

## 7. 残タスク

Phase 4 MVPとして残すもの:

- なし

Phase 4拡張、またはPhase 5以降へ送るもの:

- 複勝、2連単、2連複、3連単、3連複など単勝以外のオッズ取得
- 部品交換を専用カラム化する必要が出た場合のschema追加。現時点では`raw_values.parts_replaced`保持で進める
- 1日全場の通常実行リハーサル。公式サイトへのアクセス負荷を避けるため、Phase 4完了条件からは外し、運用前に低頻度で確認する
- API確認エンドポイント。Phase 7/8の画面要件と合わせて設計する
- 記者予想
- Playwrightが必要なページの取得
- リアルタイムWebSocket配信
- 本番監視基盤

## 8. 完了条件の判定

| 完了条件 | 現状 |
|---|---|
| 当日開催場一覧を取得できる | 達成 |
| 1場1日分の当日出走表を保存できる | 達成 |
| 1場1日分の直前情報、展示、気象を保存できる | 達成 |
| 1場1日分のオッズsnapshotを複数回保存できる | 達成。`20260601_23_01`の単勝snapshot 2件を確認 |
| Raw HTML、SHA-256、取得URL、取得runを追跡できる | 達成 |
| 同じ処理を再実行しても重複しない | 達成 |
| Phase 4品質チェックが通る | 達成 |
| Prefect Flowから起動できる | dry-run達成。公式アクセスを伴う通常Flowは運用前リハーサルへ移管 |
| READMEと構成台帳に実行手順が反映されている | 達成 |
| `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通る | 達成 |
