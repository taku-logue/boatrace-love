# Phase 3 レース結果・番組表データ蓄積 設計書

作成日: 2026-05-30
更新日: 2026-06-06
ステータス: MVP完了
進捗目安: 100%

## 1. Phase 3の目的

Phase 3では、BOAT RACE公式サイトが配布している競走成績Kファイルと番組表Bファイルを取得し、レース単位、出走艇単位、払戻単位でDBへ蓄積する。

Phase 2で整備したレーサー期別成績は、選手の履歴特徴量の土台である。Phase 3では、実際のレースで「いつ、どの場の何Rに、誰が、何号艇で出走し、どのような結果になったか」を保存し、Phase 5以降の特徴量生成と学習データ作成につなげる。

Phase 3完了時点で目指す状態:

- 番組表と競走成績を同じ`race_id`で結合できる
- `races`、`race_entries`、`race_results`、`payouts`から過去レースDBを参照できる
- Rawファイル、SHA-256、文字コード、取り込みrun、parser versionを追跡できる
- 同じ処理を再実行しても重複しない
- Docker内で取得、解凍、パース、DB投入、検証まで再現できる
- Phase 5の特徴量生成で使える最低限の正規化済みレースDBがある

## 2. 2026-06-06時点の現状

Phase 3 MVPは完了済み。旧作業ブランチ`codex/phase3-race-database`はmainへ取り込み済みで、ローカルブランチも削除済み。

完了済みの主要変更:

- Phase 2 migration復旧用revisionを追加し、Phase 3 migrationをPhase 2の後続へ接続した
- Phase 3 migrationから`ingestion_runs`や`racer_period_stats_raw`を壊す不要なdropを除去した
- 既存DB向けに`uq_racer_period_stats_raw_file_line`を復旧するrepair migrationを追加した
- `download_files`、`raw_files`、`ingestion_runs`へPhase 3取り込み台帳を記録するようにした
- LZH/TXTのRaw保存、SHA-256保存、文字コードメタデータ保存を実装した
- `race_card_raw`、`race_result_raw`へparser version付きのRaw行保存を実装した
- `scripts/phase3_run_all_pipeline.py`をCLI化し、日付範囲、対象種別、場コード絞り込み、dry-run、skip-downloadに対応した
- Phase 3モデルを`apps/api/app/models/__init__.py`からexportした
- Phase 3用pytestを追加し、URL生成、保存パス、`race_id`、B/Kパース、正規化の基本仕様を固定した
- Docker ComposeのAPIコンテナから`/data`と`/scripts`を参照できるようにした
- SQLベースのPhase 3データ品質チェックを追加し、パイプライン後に自動実行できるようにした
- PostgreSQL実体を使ったUpsert冪等性テストを追加した
- `scripts/phase3_prefect_flow.py`を追加し、Phase 3 CLIをPrefect Flowから実行できるようにした
- 2026-05-30分の台帳付き再実行で品質チェックがissuesなしで通ることを確認した
- Prefect Server `http://127.0.0.1:4200/api`に対してdry-run FlowがCompletedになることを確認した
- HTTP取得のリトライ方針を定義し、timeout、通信エラー、408、429、5xxの指数バックオフ再試行を実装した
- 実データの払戻欄をもとに合成fixtureを拡充し、単勝、複勝、2連単、2連複、拡連複、3連単、3連複を保存できるようにした
- 解凍失敗、パース失敗、品質チェック失敗の自動部分再開は現時点では実装しない判断にした

確認済みのDB状態:

| 項目 | 件数 |
|---|---:|
| `races` | 492 |
| `race_entries` | 2,952 |
| `race_results` | 2,832 |
| `payouts` | 3,250 |
| `race_card_raw` | 1,080 |
| `race_result_raw` | 1,080 |
| Phase 3 `download_files` | `race_cards` 1件、`race_results` 1件 |
| Phase 3 `raw_files` | LZH/TXT各3件ずつ、合計12件 |
| Phase 3 `ingestion_runs` | completed 3件 |
| `race_card_raw`の`download_file_id, line_number`重複 | 0 |
| `race_result_raw`の`download_file_id, line_number`重複 | 0 |

補足:

- 正規化済みテーブルの件数は、旧スクリプトで投入済みの2026-05-28から2026-05-30分を含む。
- 取り込み台帳、Rawファイル、Raw行追跡は、新CLIで検証した2026-05-30分について確認済み。
- 2026-05-30分の品質チェック結果は、`race_count` 180、番組表/結果結合率 1.0、issuesなし。
- 2026-05-30分の払戻は、`win`、`place`、`exacta`、`quinella`、`quinella_place`、`trifecta`、`trio`を保存確認済み。
- `--venue-code`は正規化テーブル投入対象を絞り込む。RawファイルとRaw行は公式ファイル単位の証跡として保存する。

DB上のAlembic revision:

```text
d5f2f8a0c1e4
```

## 3. 現在の重要な未解決事項

Phase 3 MVPとして残す未解決事項はない。

以下はPhase 3の完了条件から外し、後続のデータ堅牢化または運用前リハーサルで扱う。

- パーサーfixtureは拡充済みだが、年代差分や返還/不成立などの特殊払戻は未確認
- 2026-05-30以外の日付範囲で、新CLIの台帳付き再実行検証が不足している
- 古い年代のB/Kファイルでレイアウト差分が見つかった場合はfixtureとparser versionを追加する

## 4. Phase 3で作るもの

Phase 3で作るもの:

- 競走成績ダウンロードの対象ファイル生成処理
- 番組表ダウンロードの対象ファイル生成処理
- 対象日付、場、URL、ファイル名、状態を管理するDB台帳
- 競走成績ファイルのダウンロード、Raw保存、SHA-256保存
- 番組表ファイルのダウンロード、Raw保存、SHA-256保存
- LZH解凍処理
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
| `apps/api/app/ingestion/race_id.py` | 完了 | `race_id`生成 |
| `apps/api/app/ingestion/race_downloads.py` | 完了 | B/KファイルURL、保存パス、日付範囲、場コード絞り込み |
| `apps/api/app/ingestion/race_quality.py` | 完了 | Phase 3正規化DBとRaw行の品質チェック |
| `apps/api/app/ingestion/race_cards/layouts.py` | MVP完了 | 番組表Bファイルの固定文字幅レイアウト |
| `apps/api/app/ingestion/race_cards/parse.py` | MVP完了 | 番組表の場、R、出走艇行の抽出 |
| `apps/api/app/ingestion/race_cards/normalize.py` | MVP完了 | 番組表フィールドの数値化 |
| `apps/api/app/ingestion/race_cards/load.py` | 完了 | `races`、`race_entries`、`race_card_raw`へのUpsert |
| `apps/api/app/ingestion/race_results/layouts.py` | MVP完了 | 競走成績Kファイルの固定文字幅レイアウト |
| `apps/api/app/ingestion/race_results/parse.py` | MVP完了 | 結果行、決まり手、払戻の抽出 |
| `apps/api/app/ingestion/race_results/normalize.py` | MVP完了 | ST、着順、F/L/失格などの標準化 |
| `apps/api/app/ingestion/race_results/load.py` | 完了 | `races`、`race_results`、`payouts`、`race_result_raw`へのUpsert |
| `apps/api/app/models/race_master.py` | 完了 | `venues`、`races` |
| `apps/api/app/models/race_cards.py` | 完了 | `race_card_raw`、`race_entries` |
| `apps/api/app/models/race_results.py` | 完了 | `race_result_raw`、`race_results` |
| `apps/api/app/models/payouts.py` | 完了 | `payouts` |
| `scripts/phase3_run_all_pipeline.py` | 完了 | B/Kファイルの自動取得、解凍、DB投入、台帳記録、品質チェック |
| `scripts/phase3_prefect_flow.py` | 完了 | Phase 3 CLIをPrefect Flowから実行 |

## 8. タスク一覧と現在状態

優先度の意味:

| 優先度 | 意味 |
|---|---|
| P0 | Phase 3 MVP完了に必須 |
| P1 | Phase 3 MVP後の堅牢化として実施したい |
| P2 | Phase 4以降または運用前に送ってよい |

## 8.1 P0: 設計・基盤

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-001 | Phase 3用ブランチを作る | 完了 | `codex/phase3-race-database`で作業し、mainへ取り込み済み |
| P3-002 | 競走成績と番組表の取得元URL、ファイル名規則、圧縮形式を確認する | 完了 | B/K LZHのURL規則と保存先を`race_downloads.py`とpytestで固定した |
| P3-003 | `race_id`仕様を確定する | 完了 | 実装とpytestで仕様を固定した |
| P3-004 | Phase 3用Alembic migrationを作成する | 完了 | Phase2 migration復旧、Phase3連鎖修正、repair migrationを適用済み |
| P3-005 | Phase 3モデルをSQLAlchemyへ登録する | 完了 | `models/__init__.py` exportとAlembic importを整理済み |

## 8.2 P0: 競走成績取得・保存

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-101 | 競走成績ダウンロードURL生成/検出処理を作る | 完了 | 日付からKファイルURLを生成できる |
| P3-102 | `download_files`へ`race_results`をUpsertする | 完了 | 2026-05-30分の`race_results`登録を確認済み |
| P3-103 | 競走成績ファイルをRaw保存する | 完了 | LZH/TXTを`data/raw/official_downloads/`と`data/raw/extracted/`へ保存する |
| P3-104 | SHA-256を保存する | 完了 | LZH/TXTと`download_files.sha256`へ記録する |
| P3-105 | 解凍処理を実装する | 完了 | Phase2共通の`LzhExtractor`を利用する |
| P3-106 | 文字コード判定を実装する | 完了 | 判定結果を`raw_files.metadata.encoding`へ保存する |

## 8.3 P0: 番組表取得・保存

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-201 | 番組表ダウンロードURL生成/検出処理を作る | 完了 | 日付からBファイルURLを生成できる |
| P3-202 | `download_files`へ`race_cards`をUpsertする | 完了 | 2026-05-30分の`race_cards`登録を確認済み |
| P3-203 | 番組表ファイルをRaw保存する | 完了 | LZH/TXTを`data/raw/official_downloads/`と`data/raw/extracted/`へ保存する |
| P3-204 | SHA-256を保存する | 完了 | LZH/TXTと`download_files.sha256`へ記録する |
| P3-205 | 解凍処理を実装する | 完了 | Phase2共通の`LzhExtractor`を利用する |
| P3-206 | 文字コード判定を実装する | 完了 | 判定結果を`raw_files.metadata.encoding`へ保存する |

## 8.4 P0: パース・正規化・DB投入

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-301 | 競走成績レイアウトを定義する | MVP完了 | 結果行と主要7券種は抽出できる。年代差分、返還/不成立などは後続fixtureで増やす |
| P3-302 | 番組表レイアウトを定義する | MVP完了 | 出走艇行、レース、Raw保存は抽出できる。レース名、締切、距離の追加検証は後続で増やす |
| P3-303 | 競走成績Raw行テーブルへ保存する | 完了 | `race_result_raw` 1,080件、parser version付きで保存確認済み |
| P3-304 | 番組表Raw行テーブルへ保存する | 完了 | `race_card_raw` 1,080件、parser version付きで保存確認済み |
| P3-305 | `races`へUpsertする | 完了 | 492件保存済み。DB実体で冪等性を確認済み |
| P3-306 | `race_entries`へUpsertする | 完了 | 2,952件保存済み。DB実体で冪等性を確認済み |
| P3-307 | `race_results`へUpsertする | 完了 | 2,832件保存済み。品質チェックで結果件数と結合率を確認できる |
| P3-308 | `payouts`へUpsertする | 完了 | 3,250件保存済み。主要7券種と払戻不正値/欠落チェックを実装済み |
| P3-309 | 欠場、失格、F、L、転覆などの表現を標準化する | MVP完了 | 正規化関数とfixtureは拡充済み。実データ由来の例外パターンは後続でさらに増やす |

## 8.5 P1: 運用性

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-401 | 対象日付範囲オプションを作る | 完了 | `--from-date`、`--to-date`で実行できる |
| P3-402 | 場コード絞り込みオプションを作る | 完了 | `--venue-code`で正規化投入対象を絞り込める |
| P3-403 | dry-runを作る | 完了 | DB更新前に対象URLを確認できる |
| P3-404 | Prefect Flow化する | 完了 | `phase3_prefect_flow.py`のdry-run Flow runがCompleted |
| P3-405 | 取り込み結果サマリを出す | 完了 | CLI出力と`ingestion_runs`で実行結果を確認できる |
| P3-406 | 失敗runのリトライ方針を作る | 完了 | HTTP取得リトライ、404方針、failed run再実行方針を文書化した |

## 8.6 P1: データ品質

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-501 | レース数チェックを作る | 完了 | 1日1場最大12R、race_no範囲を検証できる |
| P3-502 | 出走数チェックを作る | 完了 | `race_entries`と`race_results`の件数異常を検出できる |
| P3-503 | 番組表と結果の結合率を確認する | 完了 | 結合率を自動算出し、しきい値未満をwarningにする |
| P3-504 | 着順整合チェックを作る | 完了 | 1着重複、1着欠落を検出できる |
| P3-505 | STと進入の範囲チェックを作る | 完了 | ST、進入、艇番の範囲外を検出できる |
| P3-506 | 払戻チェックを作る | 完了 | 払戻金、券種、組番、人気、払戻欠落を検出できる |

## 8.7 P1: テスト・品質

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-601 | discoveryテストを作る | 完了 | B/KファイルURL生成をpytestで確認する |
| P3-602 | race_idテストを作る | 完了 | 日付、場、Rから期待`race_id`を生成できる |
| P3-603 | 競走成績パーサーテストを作る | 完了 | 最小Kファイルfixtureで結果、決まり手、払戻を確認する |
| P3-604 | 番組表パーサーテストを作る | 完了 | 最小Bファイルfixtureでレース、Raw、出走を確認する |
| P3-605 | 正規化テストを作る | 完了 | ST、着順、欠場、F/L、失格、落水、転覆、沈没を確認する |
| P3-606 | DB Upsertテストを作る | 完了 | SQL生成とPostgreSQL実体の両方で冪等性を確認する |
| P3-607 | ruff/format/mypy/pytestを通す | 完了 | `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通過 |

## 8.8 P2: ドキュメント・整理

| ID | タスク | 状態 | 完了条件 |
|---|---|---|---|
| P3-701 | READMEへPhase 3実行手順を追記する | 完了 | dry-run、通常実行、Docker実行例をREADMEへ反映した |
| P3-702 | Phase 3のレイアウト確認結果を記録する | 完了 | 現行B/Kファイルの主要行、払戻、例外方針を本文書に反映した |
| P3-703 | Phase 2/3の探索用スクリプトを整理する | 完了 | 一時確認スクリプトを削除し、実行導線を`phase*_run_all_pipeline.py`へ集約した |
| P3-704 | AIエージェント引き継ぎノートを更新する | 完了 | 構成台帳へPhase 3の現構成と残作業を反映した |

## 9. 完了条件チェック

| 完了条件 | 判定 | 現状 |
|---|---|---|
| 競走成績ダウンロード対象を検出できる | 完了 | 日付からKファイルURLを生成し、dry-runで確認できる |
| 番組表ダウンロード対象を検出できる | 完了 | 日付からBファイルURLを生成し、dry-runで確認できる |
| 競走成績Rawを保存できる | 完了 | LZH/TXT、`raw_files`、`race_result_raw`で追跡できる |
| 番組表Rawを保存できる | 完了 | LZH/TXT、`raw_files`、`race_card_raw`で追跡できる |
| SHA-256を記録できる | 完了 | LZH/TXTと`download_files`に保存済み |
| 文字コードを判定できる | 完了 | `raw_files.metadata.encoding`に保存済み |
| `race_id`が一意に生成できる | 完了 | 実装とpytestで固定済み |
| 番組表を`race_entries`へ投入できる | 完了 | 2,952件保存済み。品質チェックで2026-05-30分は異常なし |
| 競走成績を`race_results`へ投入できる | 完了 | 2,832件保存済み。品質チェックで2026-05-30分は異常なし |
| 払戻を`payouts`へ投入できる | 完了 | 3,250件保存済み。主要7券種と払戻品質チェックを実装済み |
| 番組表と結果が結合できる | 完了 | 2026-05-30分の結合率1.0を自動確認済み |
| 冪等に再実行できる | 完了 | PostgreSQL実体でUpsert冪等性をpytest確認済み |
| 取り込みログを追跡できる | 完了 | `ingestion_runs` completed 2件を確認済み |
| Docker内で再現できる | MVP完了 | Compose設定とコマンドは整備済み。長期間再実行検証は運用前リハーサルで扱う |
| 品質チェックが通る | 完了 | `ruff check`、`ruff format --check`、`mypy app`、`pytest`が通過 |
| ドキュメントが更新されている | 完了 | 本文書、README、ロードマップ、構成台帳を更新した |

## 10. 後続で優先して行うこと

Phase 3 MVP後の堅牢化として優先するもの:

1. 新CLIで複数日・複数場の台帳付き再実行を検証する
   - 1日1場
   - 1日全場
   - 3日全場
   - 1か月
2. 古い年代や例外レースの実例が出たら、parser versionとfixtureを追加する
   - 年代差分
   - 返還や不成立などの特殊払戻
   - 欠場、失格、F/L、転覆などの事故

## 11. リスクと対応

| リスク | 対応 |
|---|---|
| サンプル日付に過適合する | fixtureと実データ検証日を増やす |
| 欠場/失格/F/Lなどの例外が漏れる | fixtureと品質チェックで例外パターンを増やす |
| B/Kファイルの年代差分で壊れる | parser versionと年度別レイアウト分岐を許容する |
| 品質チェックなしで大量投入する | パイプライン後の品質チェックを標準実行にする |
| Prefect化でCLIと処理が二重化する | Prefect FlowはCLIを呼ぶ薄いラッパーにする |
| 一時的なHTTP失敗でrun全体が止まる | timeout、通信エラー、408、429、5xxは指数バックオフで再試行する |

## 12. 失敗時リトライ・再実行方針

Phase 3では、公式ファイルの取得失敗と処理失敗を以下の方針で扱う。

| 失敗種別 | 現在の挙動 | 再実行方針 |
|---|---|---|
| 404 Not Found | リトライせず`download_files.status = not_found`にする | 対象日付に公式ファイルが存在しない扱い。日付を確認して必要なら後日再実行 |
| 408、429、5xx | `--http-retries`回まで指数バックオフで再試行する | 一時障害の可能性が高いため、そのまま再実行してよい |
| timeout、通信エラー、protocol error | `--http-retries`回まで指数バックオフで再試行する | ネットワーク状態を確認し、同じコマンドを再実行 |
| 400、403などの非リトライHTTPエラー | 即時失敗し、`ingestion_runs.status = failed`へ記録する | URL規則、アクセス制限、公式側変更を確認してから再実行 |
| 解凍失敗 | 即時失敗し、現在処理中のtargetをrollbackする | LZHが壊れていないか確認し、必要なら再ダウンロード。既存LZHを使う場合は`--skip-download` |
| パース失敗 | 即時失敗し、現在処理中のtargetをrollbackする | fixtureを追加してparserを修正後、同じ日付で再実行 |
| DB Upsert失敗 | 即時失敗し、現在処理中のtargetをrollbackする | migration/制約/データを修正後、同じ日付で再実行 |
| 品質チェック失敗 | DB投入後にexit code 2で終了する | 品質レポートを確認し、parserまたはデータを修正後に再実行 |

HTTP取得の主なCLIオプション:

```bash
--http-retries 3
--http-backoff-seconds 2
--http-timeout-seconds 30
```

自動部分再開は現時点では実装しない。理由は以下。

- `download_files`、Raw行、正規化テーブルのUpsertが冪等で、同じ日付を再実行できる
- target単位の例外時にrollbackするため、中途半端な正規化行が残りにくい
- HTTP一時失敗はリトライで吸収できる
- 解凍失敗やパース失敗はparserまたはRaw内容の確認が先で、自動再開しても成功しない可能性が高い

自動部分再開を追加する判断基準:

- 長期間投入で、同じ原因の一時失敗が複数回発生する
- 1か月以上の投入中に、失敗targetだけを機械的に再開したい運用負荷が明確になる
- `download_files.status`を使った`--retry-failed-only`が必要になる

## 13. 参考コマンド

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

1場だけ正規化投入する検証:

```bash
cd apps/api
uv run python ../../scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --venue-code 23 \
  --sleep-seconds 0
```

Docker Compose上のAPIコンテナから実行する場合:

```bash
docker compose exec api uv run python /scripts/phase3_run_all_pipeline.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --dry-run
```

Prefect Flow dry-run:

```bash
cd apps/api
PREFECT_API_URL=http://127.0.0.1:4200/api uv run python ../../scripts/phase3_prefect_flow.py \
  --from-date 2026-05-30 \
  --to-date 2026-05-30 \
  --dry-run \
  --skip-quality \
  --sleep-seconds 0
```

DB件数確認:

```bash
docker compose exec postgres psql -U boatrace -d boatrace_love -c "select count(*) from races;"
docker compose exec postgres psql -U boatrace -d boatrace_love -c "select count(*) from race_entries;"
docker compose exec postgres psql -U boatrace -d boatrace_love -c "select count(*) from race_results;"
docker compose exec postgres psql -U boatrace -d boatrace_love -c "select count(*) from payouts;"
docker compose exec postgres psql -U boatrace -d boatrace_love -c "select count(*) from race_card_raw;"
docker compose exec postgres psql -U boatrace -d boatrace_love -c "select count(*) from race_result_raw;"
```

品質チェック:

```bash
cd apps/api
uv run ruff check app tests ../../scripts
uv run ruff format --check app tests ../../scripts
uv run mypy app
uv run pytest
```
