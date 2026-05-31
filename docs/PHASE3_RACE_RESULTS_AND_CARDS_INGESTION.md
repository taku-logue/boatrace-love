# Phase 3 レース結果・番組表データ蓄積 設計書

作成日: 2026-05-30
更新日: 2026-05-30
ステータス: 進行中
進捗目安: 50%

## 1. Phase 3の目的

Phase 3では、BOAT RACE公式サイトが配布している競走成績と番組表を取得し、レース単位、出走艇単位、払戻単位でDBへ蓄積する。

Phase 2で整備したレーサー期別成績は、選手の履歴特徴量の土台である。Phase 3では、実際のレースで「いつ、どの場の何Rに、誰が、何号艇で出走し、どのような結果になったか」を保存し、Phase 5以降の特徴量生成と学習データ作成につなげる。

Phase 3完了時点で目指す状態:

- 番組表と競走成績を同じ`race_id`で結合できる
- `races`、`race_entries`、`race_results`、`payouts`から過去レースDBを参照できる
- Rawファイル、SHA-256、文字コード、取り込みrun、parser versionを追跡できる
- 同じ処理を再実行しても重複しない
- Docker内で取得、解凍、パース、DB投入、検証まで再現できる
- Phase 5の特徴量生成で使える最低限の正規化済みレースDBがある

## 2. 2026-05-30時点の現状

作業ブランチ:

- `codex/phase3-race-database`

直近コミット:

- `8ed5167 feat(phase3): 番組表および競走成績の自動ダウンロード・パース・DB保存パイプラインを完成再コミット`
- `a7a83ec feat(phase3): 番組表および競走成績の自動ダウンロード・パース・DB保存パイプラインを完成`
- `ca58eae feat(phase3): 番組表および競走成績のテーブル定義、パーサー構築、DBへのUpsert処理を完了`

確認済みの実装:

- `venues`、`races`、`race_entries`、`race_results`、`payouts`、`race_card_raw`、`race_result_raw`のモデルとmigrationが追加されている
- `race_id`生成関数が追加されている
- 番組表Bファイル用のレイアウト、パーサー、正規化、DB Upsert処理が追加されている
- 競走成績Kファイル用のレイアウト、パーサー、正規化、DB Upsert処理が追加されている
- `scripts/phase3_run_all_pipeline.py`で、2026-05-28から2026-05-30までのB/Kファイルをダウンロード、解凍、パース、DB投入する処理が追加されている
- 固定パスのローカルサンプル投入・パーサー確認スクリプトは削除済み

確認済みのDB状態:

| 項目 | 件数 |
|---|---:|
| `races` | 492 |
| `race_entries` | 2,952 |
| `race_results` | 2,832 |
| `payouts` | 2,351 |
| `race_card_raw` | 0 |
| `race_result_raw` | 0 |
| 番組表と結果の両方がある`races` | 472 |
| 主要一意キー重複 | 0 |

DB上のAlembic revision:

```text
2aa075ebabae
```

## 3. 重要な未解決事項

現状は、番組表と競走成績を「パースして正規化テーブルへ入れる」ところまでは進んでいる。ただし、Phase 3完了判定にはまだ到達していない。

特に重要な未解決事項:

- Phase 3 migrationの`down_revision`がPhase 2のrevisionではなく初期migrationを指している
- Phase 3 migrationに`ingestion_runs.completed_at`削除と`racer_period_stats_raw`一意制約削除が混入している
- 現在のリポジトリ内migrationではPhase 2テーブル追加revisionが見えず、新規DB再現性に不安がある
- Phase 3の`download_files`登録がない
- Phase 3の`ingestion_runs`記録がない
- Phase 3の`raw_files`登録、SHA-256保存、文字コードメタデータ保存が未実装
- `race_card_raw`と`race_result_raw`が0件で、Raw行追跡ができていない
- `scripts/phase3_run_all_pipeline.py`の対象期間がコード内に固定されている
- dry-run、日付範囲、場コード絞り込みが未実装
- Prefect Flow化が未実装
- Phase 3用pytestが未実装
- API品質コマンドは通過済み。ただし、Phase 3専用fixture/pytestは未実装
- `apps/api/app/models/__init__.py`にPhase 3モデルがexportされていない
- ルート直下のPhase 3サンプルRawファイルは削除済み。今後は`data/raw/extracted/race_cards/`、`data/raw/extracted/race_results/`を使う

## 4. Phase 3で作るもの

Phase 3で作るもの:

- 競走成績ダウンロードの対象ファイル検出処理
- 番組表ダウンロードの対象ファイル検出処理
- 対象日付、場、URL、ファイル名、状態を管理するDB台帳
- 競走成績ファイルのダウンロード、Raw保存、SHA-256保存
- 番組表ファイルのダウンロード、Raw保存、SHA-256保存
- 圧縮形式がある場合の解凍処理
- 文字コード判定
- 競走成績パーサー
- 番組表パーサー
- `race_id`設計と生成処理
- レース、出走、結果、払戻、場マスタの正規化テーブル
- 取り込みrunと失敗ログ
- 冪等な一括パイプライン
- dry-runと対象期間絞り込み
- データ品質チェック
- テストと実行手順ドキュメント

## 5. Phase 3でまだ作らないもの

以下はPhase 3では作らない。

- 当日リアルタイム取得
- オッズの時系列スナップショット取得
- 直前情報、展示タイム、チルト、気象のリアルタイム取得
- LightGBMなどの学習処理
- 特徴量生成パイプライン本体
- 予測API
- Web画面でのレース結果閲覧UI
- 買い目生成

## 6. レースID設計

現在の実装では、`apps/api/app/ingestion/race_id.py`で以下の形式の`race_id`を生成している。

```text
{YYYYMMDD}_{venue_code}_{race_no}
```

例:

```text
20260530_23_01
```

生成元:

| 要素 | 型 | 例 | 内容 |
|---|---|---|---|
| `race_date` | date | `2026-05-30` | 開催日 |
| `venue_code` | text | `23` | レース場コード |
| `race_no` | integer | `1` | レース番号 |

DB上では`race_id`に加えて、`race_date`、`venue_code`、`race_no`を個別列として持つ。`races`の一意制約は`(race_date, venue_code, race_no)`。

## 7. 現在の主な実装ファイル

| ファイル | 状態 | 役割 |
|---|---|---|
| `apps/api/app/ingestion/race_id.py` | 一部完了 | `race_id`生成 |
| `apps/api/app/ingestion/race_cards/layouts.py` | 一部完了 | 番組表Bファイルの固定文字幅レイアウト |
| `apps/api/app/ingestion/race_cards/parse.py` | 一部完了 | 番組表の場、R、出走艇行の抽出 |
| `apps/api/app/ingestion/race_cards/normalize.py` | 一部完了 | 番組表フィールドの数値化 |
| `apps/api/app/ingestion/race_cards/load.py` | 一部完了 | `races`、`race_entries`、`race_card_raw`へのUpsert |
| `apps/api/app/ingestion/race_results/layouts.py` | 一部完了 | 競走成績Kファイルの固定文字幅レイアウト |
| `apps/api/app/ingestion/race_results/parse.py` | 一部完了 | 結果行、決まり手、払戻の抽出 |
| `apps/api/app/ingestion/race_results/normalize.py` | 一部完了 | ST、着順、F/L/失格などの標準化 |
| `apps/api/app/ingestion/race_results/load.py` | 一部完了 | `races`、`race_results`、`payouts`、`race_result_raw`へのUpsert |
| `apps/api/app/models/race_master.py` | 一部完了 | `venues`、`races` |
| `apps/api/app/models/race_cards.py` | 一部完了 | `race_card_raw`、`race_entries` |
| `apps/api/app/models/race_results.py` | 一部完了 | `race_result_raw`、`race_results` |
| `apps/api/app/models/payouts.py` | 一部完了 | `payouts` |
| `scripts/phase3_run_all_pipeline.py` | 一部完了 | B/Kファイルの自動取得、解凍、DB投入 |

## 8. タスク一覧と現在状態

優先度の意味:

| 優先度 | 意味 |
|---|---|
| P0 | Phase 3完了に必須。先に解消する |
| P1 | Phase 3内で完了させたい |
| P2 | 余力があれば実施。Phase 4/5へ送ってもよい |

## 8.1 P0: 設計・基盤

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-001 | Phase 3用ブランチを作る | 完了 | `codex/phase3-race-database`で作業中 |
| P3-002 | 競走成績と番組表の取得元URL、ファイル名規則、圧縮形式をサンプル確認する | 一部完了 | B/KのLZHとTXTサンプルはあるが、文書化とfixture化が必要 |
| P3-003 | `race_id`仕様を確定する | 一部完了 | 実装はある。pytestで仕様固定が必要 |
| P3-004 | Phase 3用Alembic migrationを作成する | 要修正 | Phase2 migrationとの連鎖、不要なdrop混入、新規DB再現性を修正する |
| P3-005 | Phase 3モデルをSQLAlchemyへ登録する | 一部完了 | モデルファイルはある。`models/__init__.py` exportとAlembic autogenerate対象確認が必要 |

## 8.2 P0: 競走成績取得・保存

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-101 | 競走成績ダウンロードURL生成/検出処理を作る | 一部完了 | 日付からKファイルURLを生成できる。discovery/台帳化は未実装 |
| P3-102 | `download_files`へ`race_results`をUpsertする | 未完了 | Phase3の`download_files`がDBに登録される |
| P3-103 | 競走成績ファイルをRaw保存する | 未完了 | `raw_files`と`data/raw/official_downloads/race_results/`で追跡できる |
| P3-104 | SHA-256を保存する | 未完了 | 対象KファイルのハッシュがDBに保存される |
| P3-105 | 解凍処理を実装する | 一部完了 | `7z`で解凍できる。Phase2の`LzhExtractor`共通化とエラー処理が必要 |
| P3-106 | 文字コード判定を実装する | 未完了 | 判定結果を`raw_files.metadata.encoding`へ保存する |

## 8.3 P0: 番組表取得・保存

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-201 | 番組表ダウンロードURL生成/検出処理を作る | 一部完了 | 日付からBファイルURLを生成できる。discovery/台帳化は未実装 |
| P3-202 | `download_files`へ`race_cards`をUpsertする | 未完了 | Phase3の`download_files`がDBに登録される |
| P3-203 | 番組表ファイルをRaw保存する | 未完了 | `raw_files`と`data/raw/official_downloads/race_cards/`で追跡できる |
| P3-204 | SHA-256を保存する | 未完了 | 対象BファイルのハッシュがDBに保存される |
| P3-205 | 解凍処理を実装する | 一部完了 | `7z`で解凍できる。Phase2の`LzhExtractor`共通化とエラー処理が必要 |
| P3-206 | 文字コード判定を実装する | 未完了 | 判定結果を`raw_files.metadata.encoding`へ保存する |

## 8.4 P0: パース・正規化・DB投入

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-301 | 競走成績レイアウトを定義する | 一部完了 | 結果行は抽出できる。年代差分、払戻全券種、例外行の検証が必要 |
| P3-302 | 番組表レイアウトを定義する | 一部完了 | 出走艇行は抽出できる。レース名、締切、距離、全場/全日検証が必要 |
| P3-303 | 競走成績Raw行テーブルへ保存する | 未完了 | `race_result_raw`が0件ではなく、parser version付きで保存される |
| P3-304 | 番組表Raw行テーブルへ保存する | 未完了 | `race_card_raw`が0件ではなく、parser version付きで保存される |
| P3-305 | `races`へUpsertする | 一部完了 | 492件保存済み。migrationと品質チェック修正後に完了判定 |
| P3-306 | `race_entries`へUpsertする | 一部完了 | 2,952件保存済み。Raw追跡と品質チェック修正後に完了判定 |
| P3-307 | `race_results`へUpsertする | 一部完了 | 2,832件保存済み。欠損理由と結合率確認が必要 |
| P3-308 | `payouts`へUpsertする | 一部完了 | 2,351件保存済み。券種網羅と人気順の扱いは未確定 |
| P3-309 | 欠場、失格、F、L、転覆などの表現を標準化する | 一部完了 | 正規化関数はある。fixtureテストと実データ検証が必要 |

## 8.5 P1: 運用性

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-401 | 対象日付範囲オプションを作る | 未完了 | `--from-date`、`--to-date`で実行できる |
| P3-402 | 場コード絞り込みオプションを作る | 未完了 | `--venue-code`で1場だけ検証できる |
| P3-403 | dry-runを作る | 未完了 | DB更新前に対象件数を確認できる |
| P3-404 | Prefect Flow化する | 未完了 | Prefect UIでFlow runを確認できる |
| P3-405 | 取り込み結果サマリを出す | 一部完了 | printはある。run単位の件数、失敗件数、DB記録が必要 |
| P3-406 | 失敗runのリトライ方針を作る | 未完了 | 失敗対象を再実行で復旧できる |

## 8.6 P1: データ品質

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-501 | レース数チェックを作る | 未完了 | 1日1場最大12Rなどを検証できる |
| P3-502 | 出走数チェックを作る | 未完了 | 通常6艇、欠場時例外を判定できる |
| P3-503 | 番組表と結果の結合率を確認する | 一部完了 | 現状472/492レースで両方あり。自動チェック化が必要 |
| P3-504 | 着順整合チェックを作る | 未完了 | 1着重複や着順欠損を検出できる |
| P3-505 | STと進入の範囲チェックを作る | 未完了 | ST、進入、艇番の範囲外を検出できる |
| P3-506 | 払戻チェックを作る | 未完了 | 払戻金、券種、組番の欠落を検出できる |

## 8.7 P1: テスト・品質

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-601 | discoveryテストを作る | 未完了 | fixtureからB/KファイルURLを抽出できる |
| P3-602 | race_idテストを作る | 未完了 | 日付、場、Rから期待`race_id`を生成できる |
| P3-603 | 競走成績パーサーテストを作る | 未完了 | サンプル行から期待フィールドを得られる |
| P3-604 | 番組表パーサーテストを作る | 未完了 | サンプル行から期待フィールドを得られる |
| P3-605 | 正規化テストを作る | 未完了 | ST、着順、欠場、F/L、払戻を標準化できる |
| P3-606 | DB Upsertテストを作る | 未完了 | 再投入しても重複しない |
| P3-607 | ruff/format/mypy/pytestを通す | 完了 | `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通過 |

## 8.8 P2: ドキュメント・整理

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-701 | READMEへPhase 3実行手順を追記する | 一部完了 | 現状メモは追記済み。discovery、pipeline、validateの正式コマンドは未完了 |
| P3-702 | Phase 3のレイアウト確認結果を記録する | 一部完了 | 本文書に現状は記録。実サンプル根拠の追記が必要 |
| P3-703 | Phase 2の探索用スクリプトを整理する | 未完了 | 残す/削除/共通化が明確になる |
| P3-704 | AIエージェント引き継ぎノートを更新する | 一部完了 | 構成台帳は作成済み。Phase 3正式手順の反映は未完了 |

## 9. 完了条件チェック

| 完了条件 | 判定 | 現状 |
|---|---|---|
| 競走成績ダウンロード対象を検出できる | 一部完了 | 日付からKファイルURL生成は可能。`download_files`台帳化は未完了 |
| 番組表ダウンロード対象を検出できる | 一部完了 | 日付からBファイルURL生成は可能。`download_files`台帳化は未完了 |
| 競走成績Rawを保存できる | 未完了 | `raw_files`登録とRaw行保存がない |
| 番組表Rawを保存できる | 未完了 | `raw_files`登録とRaw行保存がない |
| SHA-256を記録できる | 未完了 | Phase3対象のSHA-256がDBにない |
| 文字コードを判定できる | 未完了 | CP932固定読み込み。`encoding`メタデータなし |
| `race_id`が一意に生成できる | 一部完了 | 実装済み、主要重複0件。pytest未実装 |
| 番組表を`race_entries`へ投入できる | 一部完了 | 2,952件保存済み。Raw追跡と品質チェックが未完了 |
| 競走成績を`race_results`へ投入できる | 一部完了 | 2,832件保存済み。欠損理由と品質チェックが未完了 |
| 払戻を`payouts`へ投入できる | 一部完了 | 2,351件保存済み。券種網羅と品質チェックが未完了 |
| 番組表と結果が結合できる | 一部完了 | 472/492レースで両方あり |
| 冪等に再実行できる | 一部完了 | 一意制約とUpsertはある。全パイプラインの再実行検証が必要 |
| 取り込みログを追跡できる | 未完了 | Phase3の`ingestion_runs`がない |
| Docker内で再現できる | 一部完了 | DBには投入済み。正式コマンド、CLI、README整理が必要 |
| 品質チェックが通る | 完了 | `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通過 |
| ドキュメントが更新されている | 一部完了 | 本文書とロードマップを更新中 |

## 10. 次に優先して行うこと

優先順位順:

1. Alembic migrationを修正する
   - `down_revision`をPhase 2の最新revisionに接続する
   - Phase 2列や制約をdropしない
   - 新規DBでPhase 0からPhase 3まで再現できる状態にする
2. Phase 3専用fixture/pytestを追加する
   - `race_cards/parse.py`と`race_results/parse.py`のimport位置と重複定義を修正する
   - 未使用importを削除する
   - 型注釈を`dict[str, object]`などへ寄せる
3. Phase3パイプラインをPhase2の監査方針に合わせる
   - `download_files`へ`race_cards`、`race_results`をUpsertする
   - LZH/TXTを`raw_files`へ登録する
   - SHA-256と文字コードを保存する
   - `ingestion_runs`へ開始/終了/失敗理由を保存する
4. Raw行テーブルへ保存する
   - `race_card_raw`と`race_result_raw`にparser version付きで行を保存する
   - FKを`-1`などのダミーIDにしない
5. CLI化する
   - `--from-date`
   - `--to-date`
   - `--venue-code`
   - `--dry-run`
6. Phase 3用pytestを追加する
   - `race_id`
   - B/Kファイルパース
   - 正規化
   - Upsert冪等性
7. データ品質チェックを作る
   - レース数
   - 出走数
   - 番組表/結果結合率
   - 着順整合
   - ST/進入範囲
   - 払戻
8. READMEとAI引き継ぎノートに正式実行手順を反映する

## 11. リスクと対応

| リスク | 対応 |
|---|---|
| migrationがPhase2成果物を壊す | 先にmigration連鎖とdrop混入を修正する |
| Rawデータ追跡なしで正規化だけ進む | `raw_files`、Raw行テーブル、parser versionを必須に戻す |
| 取得期間がコード固定で再現性が低い | CLI引数とdry-runを追加する |
| サンプル3日分だけに過適合する | 1日1場、1日全場、1か月、過去範囲の順で検証する |
| 欠場/失格/F/Lなどの例外が漏れる | fixtureと品質チェックで例外パターンを増やす |
| B/Kファイルの年代差分で壊れる | parser versionと年度別レイアウト分岐を許容する |

## 12. 参考コマンド

現在のDB件数確認:

```bash
docker exec boatrace_postgres psql -U boatrace -d boatrace_love -c "select count(*) from races;"
docker exec boatrace_postgres psql -U boatrace -d boatrace_love -c "select count(*) from race_entries;"
docker exec boatrace_postgres psql -U boatrace -d boatrace_love -c "select count(*) from race_results;"
docker exec boatrace_postgres psql -U boatrace -d boatrace_love -c "select count(*) from payouts;"
```

品質チェック:

```bash
cd apps/api
uv run ruff check app tests ../../scripts
uv run ruff format --check app tests ../../scripts
uv run mypy app
uv run pytest
```

現状、以下のAPI品質チェックは通過済み。

```bash
cd apps/api
uv run ruff check app tests ../../scripts
uv run ruff format --check app tests ../../scripts
uv run mypy app
uv run pytest
```

ただし、Phase 3専用fixture/pytestは未実装。
