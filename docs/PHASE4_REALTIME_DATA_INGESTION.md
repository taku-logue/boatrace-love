# Phase 4 当日リアルタイムデータ取得 設計書

作成日: 2026-06-01
更新日: 2026-06-01
ステータス: 未着手
進捗目安: 0%

## 1. Phase 4の目的

Phase 4では、BOAT RACE公式サイトの当日ページから、開催場、当日出走表、直前情報、展示、気象、オッズを取得し、Phase 5以降の特徴量生成と当日予測に使える形で蓄積する。

Phase 3までで、過去の番組表Bファイルと競走成績Kファイルを蓄積する土台はできている。Phase 4では、同じ`race_id`設計を使いながら、レース前に変化する情報を時系列または取得時点付きで保存する。

Phase 4完了時点で目指す状態:

- 当日開催場と対象レースを取得できる
- 当日出走表を`races`、`race_entries`へUpsertできる
- 直前情報、展示、気象をレース/艇単位で保存できる
- オッズを取得時刻付きのsnapshotとして保存できる
- HTML Raw、取得URL、SHA-256、取得run、parser versionを追跡できる
- 取得頻度、User-Agent、リトライ、バックオフを制御できる
- 同じ取得を再実行しても重複しない
- Phase 5の特徴量生成で、過去DBと当日DBを同じ`race_id`で接続できる

## 2. Phase 4の前提

前提となる完了済み/進行中成果物:

- Phase 0: MVPスコープ、評価指標、データ利用方針
- Phase 1: Docker Compose、FastAPI、PostgreSQL、Alembic、Prefect、MLflow
- Phase 2: LZH取得、Raw保存、SHA-256、文字コード、台帳、冪等Upsert
- Phase 3: `race_id`、`races`、`race_entries`、`race_results`、`payouts`、Raw追跡、品質チェック、Prefect Flow

Phase 4で引き継ぐ設計:

- RawはGit管理しない
- 公式サイトへのアクセスは個人利用MVPの範囲に限定する
- 再配布できないデータをdocsやtestsへそのまま入れない
- 取得したHTMLは`raw_files`で追跡する
- 取得処理はまずCLIで固め、必要に応じてPrefect Flowから薄く呼ぶ
- Playwrightは必要なページに限定し、静的HTMLで十分な場合は`httpx`とBeautiful Soupを優先する

## 3. Phase 4で作るもの

Phase 4で作るもの:

- 当日開催場一覧の取得処理
- 当日レース一覧の取得処理
- 当日出走表HTMLの取得、Raw保存、正規化
- 直前情報HTMLの取得、Raw保存、正規化
- 展示タイム、チルト、展示進入、展示STの保存
- 気象、水面、風向、風速、波高、気温、水温の保存
- オッズページの取得、Raw保存、snapshot保存
- 取得run、失敗ログ、リトライ、バックオフ
- 取得頻度制御
- Phase 4用の品質チェック
- Phase 4用のpytest fixture
- Prefect Flow
- 実行手順ドキュメント

## 4. Phase 4でまだ作らないもの

以下はPhase 4では作らない。

- 予測モデル本体
- 買い目生成
- 自動投票
- リアルタイムWebSocket配信
- 本番監視基盤
- 有料/ログインが必要な情報の取得
- 過度に高頻度なオッズ取得
- 公式サイトの再配布に該当するデータ出力

## 5. 取得対象と保存方針

| 取得対象 | 優先度 | Raw保存 | 正規化先候補 | 備考 |
|---|---|---|---|---|
| 当日開催場一覧 | P0 | する | `live_fetch_status`またはrun metadata | 当日の入口。最初に実装する |
| 当日レース一覧 | P0 | する | `races` | `race_id`をPhase 3と同じ形式で生成する |
| 当日出走表 | P0 | する | `races`、`race_entries` | Phase 3の番組表正規化と接続する |
| 直前情報 | P0 | する | `pre_race_infos`、`pre_race_entry_infos` | 展示、チルト、部品交換、進入など |
| 気象/水面 | P0 | する | `weather_observations` | レース単位または取得時刻単位 |
| オッズ | P0 | する | `odds_snapshots`、`odds_snapshot_entries` | 時系列snapshotとして保存 |
| 記者予想 | P2 | する | 未定 | 取得可否と利用条件を確認してから判断 |

## 6. 推奨テーブル案

既存テーブルを使うもの:

- `data_sources`
- `ingestion_runs`
- `raw_files`
- `races`
- `race_entries`

Phase 4で追加候補のテーブル:

| テーブル | 目的 | 主な一意制約 |
|---|---|---|
| `live_fetch_status` | 当日ページ取得対象と状態の台帳 | `(race_date, venue_code, race_no, data_kind, source_url)` |
| `pre_race_infos` | レース単位の直前情報 | `(race_id, fetched_at)` |
| `pre_race_entry_infos` | 艇単位の直前情報 | `(race_id, boat_no, fetched_at)` |
| `weather_observations` | 気象、水面状態 | `(race_id, fetched_at)` |
| `odds_snapshots` | オッズ取得単位 | `(race_id, bet_type, fetched_at)` |
| `odds_snapshot_entries` | 組番別オッズ | `(snapshot_id, combination)` |

補足:

- 当日出走表は、可能な限り既存の`races`、`race_entries`へUpsertする。
- 動的に変わる情報は上書きではなく、`fetched_at`付きでsnapshot保存する。
- `raw_files.file_type`は`html`または`json`を使う。
- `raw_files.metadata`には`data_kind`、`race_date`、`venue_code`、`race_no`、`parser_version`、`fetch_method`を入れる。

## 7. ディレクトリ案

Phase 4で追加する候補:

```text
apps/api/app/ingestion/live/
  __init__.py
  discovery.py
  fetch.py
  parse_race_card.py
  parse_pre_race.py
  parse_odds.py
  normalize.py
  load.py
  quality.py

apps/api/tests/ingestion/live/
  test_discovery.py
  test_parse_race_card.py
  test_parse_pre_race.py
  test_parse_odds.py
  test_quality.py

scripts/
  phase4_run_live_pipeline.py
  phase4_prefect_flow.py
```

Raw保存先:

```text
data/raw/html/race_cards/
data/raw/html/exhibition/
data/raw/html/odds/
data/raw/odds/
```

## 8. 取得方式の方針

基本方針:

- まず`httpx`とBeautiful Soupで取得できるか確認する
- JavaScript描画、画面遷移、動的更新が必要なページだけPlaywrightを使う
- 取得ごとにHTML Rawを保存する
- 公式サイトへのアクセス間隔をCLI引数で制御する
- 429、5xx、timeoutはリトライする
- 404や対象レースなしはnot_found扱いにする

CLI引数案:

```bash
--race-date 2026-06-01
--venue-code 23
--race-no 12
--only all|venues|race_cards|pre_race|odds
--dry-run
--skip-fetch
--sleep-seconds 2
--http-retries 3
--http-backoff-seconds 2
--http-timeout-seconds 30
```

## 9. 品質チェック案

Phase 4用の品質チェック:

- 当日開催場一覧が0件ではない
- 1場あたりのレース数が1から12の範囲内
- 当日出走表の艇番が1から6
- 当日出走表の登番が空ではない
- 直前情報の艇番が1から6
- 展示タイムが現実的な範囲内
- チルトが想定範囲内
- 進入が1から6の範囲内
- 気温、水温、風速、波高が現実的な範囲内
- オッズの組番と券種が矛盾しない
- オッズが0以下ではない
- 同じ`race_id`、`bet_type`、`fetched_at`、`combination`で重複しない
- Raw HTMLと正規化行が紐づいている

## 10. タスク一覧と優先順位

優先度の意味:

| 優先度 | 意味 |
|---|---|
| P0 | Phase 4完了に必須。先に解消する |
| P1 | Phase 4内で完了させたい |
| P2 | 余力があれば実施。Phase 5以降へ送ってもよい |

### 10.1 P0: 設計・調査

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-001 | Phase 4用ブランチを作る | 未着手 | `codex/phase4-live-ingestion`などで作業する |
| P4-002 | 当日ページのURL、HTML構造、取得可否を確認する | 未着手 | 開催場一覧、出走表、直前情報、オッズの取得方式を記録する |
| P4-003 | `race_id`接続方針を確定する | 未着手 | Phase 3と同じ`{YYYYMMDD}_{venue_code}_{race_no}`で接続できる |
| P4-004 | Phase 4用DBテーブルを確定する | 未着手 | migration案とモデル案が決まる |
| P4-005 | Raw HTML保存ルールを確定する | 未着手 | `raw_files`と`data/raw/html/`で追跡できる |

### 10.2 P0: 当日開催・出走表

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-101 | 当日開催場一覧を取得する | 未着手 | 対象日付の開催場コード一覧を取得できる |
| P4-102 | 当日レース一覧を取得する | 未着手 | 開催場ごとの1Rから12Rを検出できる |
| P4-103 | 当日出走表HTMLをRaw保存する | 未着手 | `raw_files`と`data/raw/html/race_cards/`で追跡できる |
| P4-104 | 当日出走表をパースする | 未着手 | 艇番、登番、選手名、級別、支部、モーター、ボートを抽出できる |
| P4-105 | `races`、`race_entries`へUpsertする | 未着手 | Phase 3と同じ`race_id`で保存できる |

### 10.3 P0: 直前情報・展示・気象

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-201 | 直前情報HTMLをRaw保存する | 未着手 | `raw_files`と`data/raw/html/exhibition/`で追跡できる |
| P4-202 | 展示タイムを保存する | 未着手 | 艇単位で展示タイムを保存できる |
| P4-203 | チルト、部品交換、展示進入を保存する | 未着手 | 艇単位で直前特徴を保存できる |
| P4-204 | 展示STを保存する | 未着手 | 艇単位で展示STを保存できる |
| P4-205 | 気象、水面情報を保存する | 未着手 | レース単位または取得時刻単位で保存できる |

### 10.4 P0: オッズ

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-301 | オッズページを取得する | 未着手 | 対象レース、対象券種のページを取得できる |
| P4-302 | オッズHTMLをRaw保存する | 未着手 | `raw_files`と`data/raw/html/odds/`で追跡できる |
| P4-303 | オッズsnapshotを保存する | 未着手 | `odds_snapshots`に取得時刻付きで保存できる |
| P4-304 | 組番別オッズを保存する | 未着手 | `odds_snapshot_entries`に券種、組番、オッズを保存できる |
| P4-305 | オッズ取得頻度を制御する | 未着手 | CLI引数とPrefect設定で取得間隔を制御できる |

### 10.5 P1: 運用性

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-401 | Phase 4 CLIを作る | 未着手 | `phase4_run_live_pipeline.py`で対象日、場、R、種別を指定できる |
| P4-402 | dry-runを作る | 未着手 | DB更新前に対象URLと件数を確認できる |
| P4-403 | Prefect Flow化する | 未着手 | Prefect UIでFlow runを確認できる |
| P4-404 | 失敗runのリトライ方針を作る | 未着手 | 失敗対象を再実行で復旧できる |
| P4-405 | 取得頻度とアクセス間隔を制御する | 未着手 | 公式サイトへ過剰アクセスしない |
| P4-406 | HTML構造変更時の検知を作る | 未着手 | parse失敗率や必須項目欠落を検出できる |

### 10.6 P1: 品質・テスト

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-501 | HTML fixtureを作る | 未着手 | 再配布にならない合成HTMLでparserをテストできる |
| P4-502 | 当日開催場一覧parserテストを作る | 未着手 | fixtureから開催場を抽出できる |
| P4-503 | 当日出走表parserテストを作る | 未着手 | fixtureから出走表を抽出できる |
| P4-504 | 直前情報parserテストを作る | 未着手 | fixtureから展示、チルト、進入、気象を抽出できる |
| P4-505 | オッズparserテストを作る | 未着手 | fixtureから券種、組番、オッズを抽出できる |
| P4-506 | DB Upsert冪等性テストを作る | 未着手 | 再投入しても重複しない |
| P4-507 | 品質チェックを作る | 未着手 | 範囲外、欠損、重複を検出できる |
| P4-508 | ruff/format/mypy/pytestを通す | 未着手 | API品質コマンドが通過する |

### 10.7 P2: 追加取得

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P4-601 | 記者予想の取得可否を確認する | 未着手 | 利用条件とHTML構造を確認する |
| P4-602 | 記者予想を保存する | 未着手 | 取得してよい場合のみ保存する |
| P4-603 | Playwright取得を最小導入する | 未着手 | 静的取得で不可能なページだけPlaywright化する |
| P4-604 | API確認エンドポイントを作る | 未着手 | 当日取得状態をAPIから確認できる |

## 11. Phase 4完了条件

Phase 4の完了条件:

- 当日開催場一覧を取得できる
- 1場1日分の当日出走表を取得し、`races`、`race_entries`へ保存できる
- 1場1日分の直前情報、展示、気象を保存できる
- 1場1日分のオッズsnapshotを複数回保存できる
- Raw HTML、SHA-256、取得URL、取得runを追跡できる
- 同じ処理を再実行しても重複しない
- Phase 4品質チェックが通る
- Prefect Flow dry-runと最小実行が成功する
- READMEと構成台帳に実行手順が反映されている
- `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通る

## 12. 最初に進める順番

推奨順:

1. 当日ページ構造の調査
2. DBテーブル案とmigration作成
3. Raw HTML保存とfetch共通処理
4. 当日開催場/レース一覧の取得
5. 当日出走表の取得と`races`/`race_entries` Upsert
6. 直前情報と気象の取得
7. オッズsnapshot保存
8. 品質チェック
9. Prefect Flow化
10. README/構成台帳更新

最初の実装単位は、`--race-date`、`--venue-code`、`--only race_cards`で1場の当日出走表だけをdry-run/取得/Raw保存/DB投入できるところまでにする。

## 13. リスクと対応

| リスク | 対応 |
|---|---|
| HTML構造が変わる | Raw HTML保存、parser version、必須項目チェックを入れる |
| 取得頻度が高くなりすぎる | sleep、対象絞り込み、Prefectスケジュールで制御する |
| JavaScript描画が必要 | まずhttpxで検証し、必要ページだけPlaywrightを使う |
| オッズ取得量が多い | 最初は1場1Rまたは1場全Rに限定し、頻度を低くする |
| 当日ページとPhase 3データが不一致 | 同じ`race_id`で接続し、品質チェックで差分を見る |
| Raw HTMLを誤ってGit管理する | `data/raw/**`は引き続きGit管理外にする |

## 14. 参考コマンド案

将来のCLIイメージ:

```bash
cd apps/api
uv run python ../../scripts/phase4_run_live_pipeline.py \
  --race-date 2026-06-01 \
  --venue-code 23 \
  --only race_cards \
  --dry-run
```

1場1日分の最小実行イメージ:

```bash
cd apps/api
uv run python ../../scripts/phase4_run_live_pipeline.py \
  --race-date 2026-06-01 \
  --venue-code 23 \
  --only all \
  --sleep-seconds 2
```

Prefect Flow dry-runイメージ:

```bash
cd apps/api
PREFECT_API_URL=http://127.0.0.1:4200/api uv run python ../../scripts/phase4_prefect_flow.py \
  --race-date 2026-06-01 \
  --venue-code 23 \
  --dry-run
```
