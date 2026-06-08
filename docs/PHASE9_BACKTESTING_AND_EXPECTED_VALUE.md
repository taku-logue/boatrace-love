# Phase 9 バックテスト・期待値分析 設計・実装計画

作成日: 2026-06-08
更新日: 2026-06-08
推奨ブランチ: `phase9-backtesting-ev-analysis`
ステータス: P0/MVP完了
進捗: 100%（P0/MVP。P1/P2は後続改善候補）

## 1. 目的

Phase 9では、Phase 7の予測API/推論サービスと、Phase 4で取得した単勝オッズ、Phase 3で投入した払戻結果を結合し、過去レースに対する期待値計算と簡易バックテストを実装する。

MVPでは、予測そのものの高精度化ではなく、以下を再現可能にすることを主目的にする。

- 各艇の予測1着確率と単勝オッズから期待値を計算できる
- 買い条件を明示して、該当候補だけを抽出できる
- 均等買いした場合の投資額、払戻額、回収率、的中率を計算できる
- バックテスト条件と結果をJSON/CSVで保存できる
- Phase 10以降の定期評価や、Web画面の期待値表示へ拡張できる

## 2. 前提

Phase 9は以下の成果物を前提にする。

| Phase | 前提成果物 | Phase 9での用途 |
|---|---|---|
| Phase 3 | `race_results`、`payouts` | 的中判定、払戻額 |
| Phase 4 | `odds_snapshots`、`odds_snapshot_entries` | 単勝オッズ、市場確率 |
| Phase 5 | `build_feature_dataset` | 推論用特徴量生成 |
| Phase 6 | `lgbm_win_v1` model bundle | 1着確率予測 |
| Phase 7 | `PredictionService`、`ModelStore` | race単位の予測再現 |
| Phase 8 | Web dashboard | 後続で期待値表示を載せる画面 |

P0で扱うオッズは`bet_type = "win"`の単勝のみとする。Phase 4時点では単勝以外のオッズ取得は後続候補であり、Phase 9 P0では存在を前提にしない。

## 3. MVP範囲

### 3.1 Phase 9 P0で作るもの

| 成果物 | 内容 |
|---|---|
| 期待値計算ロジック | `expected_value = win_probability * win_odds`を艇別に計算する |
| 買い条件 | 最低期待値、最低/最高オッズ、上位rank、場、R、期間で絞れる |
| バックテストエンジン | 単勝均等買いの投資額、払戻額、収支、回収率、的中率を計算する |
| 結果report | summary JSON、bet candidates CSVを`data/processed/reports/`へ保存する |
| CLI | 日付範囲、model、買い条件、stake、保存先を指定して実行できる |
| pytest | 期待値計算、買い条件、払戻計算、対象0件時の挙動を固定する |
| docs同期 | README、roadmap、構成台帳、Phase 9 docを更新する |

### 3.2 Phase 9 P0で作らないもの

- 2連単、3連単、3連複など単勝以外の券種
- Kelly基準や資金配分最適化
- オッズ取得時刻を締切直前へ厳密に合わせる機能
- 予測snapshotのDB保存
- バックテスト結果のDB永続化
- Web画面の期待値ランキング
- SHAPや特徴量寄与を含めた説明画面
- 税金、購入上限、投票制約を含めた資金管理

これらはP1/P2またはPhase 10以降で扱う。

## 4. 計算方針

### 4.1 単勝期待値

P0では100円単勝1点買いを基準に、以下の簡易期待値を使う。

```text
market_probability = 1 / win_odds
expected_value = win_probability * win_odds
edge = expected_value - 1
```

`expected_value > 1`なら、モデル確率上は単勝期待値がプラスの候補として扱う。ただし、これは控除率、オッズ変動、モデル誤差をすべて織り込んだ保証ではない。

### 4.2 的中判定と払戻

単勝候補の`combination`は艇番文字列とする。

- bet candidate: `race_id`, `boat_no`, `combination`
- hit: `payouts.bet_type = "win"`かつ`payouts.combination = combination`
- payout: 的中時は`payout_yen * stake_yen / 100`
- loss: 不的中時は`0`

P0では`stake_yen`を全候補で固定する均等買いにする。

### 4.3 対象レース

P0では、以下を満たすレースだけをバックテスト対象にする。

- Phase 7の`PredictionService`で6艇予測が成功する
- `odds_snapshot_entries`に単勝オッズがある
- `payouts`に単勝払戻がある
- 買い条件を満たす候補が1つ以上ある

対象レースまたは候補が0件の場合も、CLIは失敗ではなくsummaryを出力する。

## 5. 想定ファイル

```text
apps/api/app/backtesting/
  __init__.py
  engine.py
  schemas.py

apps/api/tests/backtesting/
  __init__.py
  test_engine.py

scripts/
  phase9_backtest_win.py

docs/
  PHASE9_BACKTESTING_AND_EXPECTED_VALUE.md
```

DB migrationはP0では追加しない。バックテスト結果は生成物として`data/processed/reports/phase9/`へ保存し、Git管理しない。

## 6. タスク

### P0: MVP必須

| ID | 優先度 | タスク | 完了条件 |
|---|---|---|---|
| P9-001 | P0 | Phase 9作業ブランチを作る | 完了。`phase9-backtesting-ev-analysis`で作業している |
| P9-002 | P0 | Phase 9 docを作る | 完了。この文書を作成した |
| P9-003 | P0 | 期待値計算schemaを定義する | 完了。予測、オッズ、払戻、bet candidate、summaryの型がある |
| P9-004 | P0 | 単勝オッズ取得ロジックを作る | 完了。raceごとの最新単勝オッズを艇番へ紐付けられる |
| P9-005 | P0 | 単勝払戻取得ロジックを作る | 完了。raceごとの的中combinationと払戻額を取得できる |
| P9-006 | P0 | 期待値計算を実装する | 完了。`market_probability`、`expected_value`、`edge`を計算できる |
| P9-007 | P0 | 買い条件filterを実装する | 完了。EV、オッズ、rank、期間/場/Rで候補を絞れる |
| P9-008 | P0 | 均等買いbacktestを実装する | 完了。投資額、払戻額、純損益、回収率、的中率を計算できる |
| P9-009 | P0 | CLIを追加する | 完了。日付範囲、model、stake、条件、出力先を指定して実行できる |
| P9-010 | P0 | report出力を実装する | 完了。summary JSONとbet candidates CSVを保存できる |
| P9-011 | P0 | pytestを追加する | 完了。期待値、filter、払戻、対象0件をテストする |
| P9-012 | P0 | 品質チェックを通す | 完了。`ruff format`、`ruff check`、`mypy app`、`pytest`が成功する |
| P9-013 | P0 | docsを同期する | 完了。README、roadmap、構成台帳、Phase 9 docに実装結果を反映した |

### P1: MVP後の優先改善

| ID | 優先度 | タスク | 完了条件 |
|---|---|---|---|
| P9-101 | P1 | 予測snapshot保存 | backtest時の予測結果を再利用できる |
| P9-102 | P1 | 複数買い条件プリセット | conservative/aggressiveなどをJSONで保存できる |
| P9-103 | P1 | segment評価 | 場、R、グレード、オッズ帯、人気別の回収率を出せる |
| P9-104 | P1 | オッズ時刻選択 | 最新ではなく指定時刻以前のsnapshotを使える |
| P9-105 | P1 | Web期待値表示 | Phase 8 dashboardにEV列と候補表示を追加できる |

### P2: 後続Phase候補

| ID | 優先度 | タスク | 扱い |
|---|---|---|---|
| P9-201 | P2 | 2連単/3連単backtest | 組み合わせ確率モデルまたは近似方針が固まってから |
| P9-202 | P2 | Kelly基準 | 単勝EVの安定性を確認してから |
| P9-203 | P2 | bankroll simulation | 長期資金曲線、最大DDを扱う段階で実施 |
| P9-204 | P2 | calibration反映EV | 確率補正をPhase 6/10側と合わせてから |
| P9-205 | P2 | DB永続化 | report運用・比較画面が必要になってから |

## 7. 完了条件

Phase 9 P0は以下をすべて満たした時点でMVP完了とする。

- [x] Phase 7のmodel bundleを使って、対象raceの1着確率を再現できる
- [x] 単勝オッズと単勝払戻をDBから取得できる
- [x] 艇別に`market_probability`、`expected_value`、`edge`を計算できる
- [x] 買い条件に合う候補だけを抽出できる
- [x] 均等買いの投資額、払戻額、純損益、回収率、的中率を計算できる
- [x] 対象0件でもエラー終了せず、0件summaryを出力できる
- [x] summary JSONとbet candidates CSVを保存できる
- [x] API側のruff、mypy、pytestが成功する
- [x] README、roadmap、構成台帳、この文書が同期されている

## 8. 後続判断

Phase 9 P0完了後、すぐにPhase 10へ進むか、Phase 9を深掘りするかは以下で判断する。

- 対象レース数が少なすぎる場合: Phase 4/3のデータ拡充を優先する
- 単勝EV候補が出るが回収率が不安定な場合: segment評価とcalibrationを優先する
- Webでの確認価値が高い場合: Phase 8 dashboardへEV列を追加する
- 運用で日次評価したい場合: Phase 10の定期ジョブへ進む

## 9. 2026-06-08 実装結果

Phase 9 P0/MVPは完了。

実装内容:

- `apps/api/app/backtesting/`を追加した
- `BacktestConfig`、`WinOdds`、`WinPayout`、`BetCandidate`、`BacktestSummary`、`BacktestResult`を定義した
- `WinBacktestEngine`を追加し、race候補抽出、最新単勝オッズ取得、単勝払戻取得、Phase 7予測、期待値計算、filter、summary集計を実装した
- `scripts/phase9_backtest_win.py`を追加し、日付範囲、場、R、model、stake、EV/オッズ/rank条件、出力先を指定できるようにした
- `data/processed/reports/phase9/`へsummary JSONとbets CSVを保存する導線を実装した
- `apps/api/tests/backtesting/`を追加し、期待値計算、filter、対象0件summary、ROI/的中率集計を固定した

実データ証跡:

- DB上の単勝オッズ: `odds_snapshot_entries` 84行
- DB上の払戻: `payouts` 3370行
- 単勝オッズと単勝払戻が重なるrace: 2026-06-01 場23の12R
- 対象0件確認: `2026-06-01`、場01、1R、`min_expected_value=0`で正常終了し、0件summary/betsを保存した
- 実データbacktest: `2026-06-01`、場23、12R、`min_expected_value=0`
  - evaluated_races: 12
  - evaluated_candidates: 72
  - bet_count: 72
  - hit_count: 12
  - roi: 0.473611
  - net_profit_yen: -3790
- 実データbacktest: `2026-06-01`、場23、12R、`min_expected_value=1.0`
  - evaluated_races: 12
  - evaluated_candidates: 72
  - bet_count: 29
  - hit_count: 1
  - roi: 0.068966
  - net_profit_yen: -2700

検証証跡:

- `uv run ruff format app tests ../../scripts/phase9_backtest_win.py`: 成功
- `uv run ruff check app tests ../../scripts/phase9_backtest_win.py`: 成功
- `uv run mypy app`: 成功
- `uv run pytest`: 78 passed

残タスク:

- P0/MVPの残タスクはなし
- 予測snapshot保存、segment評価、オッズ時刻選択、Web期待値表示、複数券種、Kelly基準、DB永続化はP1/P2で扱う
