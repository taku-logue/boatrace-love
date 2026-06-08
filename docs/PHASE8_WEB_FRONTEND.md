# Phase 8 Webフロントエンド設計・実装計画

作成日: 2026-06-08
更新日: 2026-06-08
推奨ブランチ: `phase8-web-frontend`
ステータス: P0/MVP完了
進捗: 100%（P0/MVP。P1/P2は後続改善候補）

## 1. 目的

Phase 8では、Phase 7で作成した予測APIをNext.js画面から利用し、指定レースの各艇1着確率を比較できるWebダッシュボードを作る。

MVPでは、Web画面の主目的を以下に絞る。

- API/DB/modelの状態を確認できる
- `race_id`を指定して予測を取得できる
- 6艇の予測順位、艇番、選手情報、1着確率を比較できる
- Phase 9以降の期待値、買い目、バックテスト画面へ拡張しやすいUI構造にする

## 2. 前提

Phase 8は以下の成果物を前提にする。

| Phase | 前提成果物 | Phase 8での用途 |
|---|---|---|
| Phase 1 | Next.js App Router、Docker Web、Playwright | Web基盤 |
| Phase 7 | `GET /models/latest` | model状態表示 |
| Phase 7 | `GET /races/{race_id}/prediction` | 予測ランキング表示 |
| Phase 7 | `PredictionResponse` schema | Web側の型定義 |

現時点の確認用raceは`20260528_01_01`を使う。

## 3. MVP範囲

### 3.1 Phase 8で作るもの

| 成果物 | 内容 |
|---|---|
| API client | Next.js server componentからAPIへfetchする薄いhelper |
| 予測ダッシュボード | `race_id`入力、model状態、予測ranking table |
| 状態表示 | API/DB/model/predictionの成功・失敗を画面で確認する |
| レスポンシブUI | desktopでは情報密度を高く、mobileでは縦積みにする |
| E2E test | Playwrightで画面起動と予測表示を確認する |
| docs同期 | README、roadmap、構成台帳、Phase 8 docを更新する |

### 3.2 Phase 8 MVPで作らないもの

- 今日の開催一覧APIが必要な本格race selector
- 場別/日付別のレース一覧
- オッズ推移
- 期待値ランキング
- 買い目生成
- バックテスト画面
- model性能画面
- 選手詳細/モーター詳細の専用画面
- 認証、公開運用、ユーザー設定

これらはPhase 8 P1以降、またはPhase 9以降で扱う。

## 4. 画面構成

### P0 dashboard

```text
BOATRACE=LOVE
  status strip: API / DB / Model
  race search: race_id input

Prediction Board
  race summary
  prediction ranking table
  model metadata panel
```

主テーブルの列:

- Rank
- Boat
- Racer
- Class
- Win probability
- Raw probability
- Missing flags

## 5. API契約

P0で使うAPI:

| Method | Path | 用途 |
|---|---|---|
| `GET` | `/health` | API状態 |
| `GET` | `/db/health` | DB状態 |
| `GET` | `/models/latest` | model状態 |
| `GET` | `/races/{race_id}/prediction` | 予測ranking |

Web側では`API_INTERNAL_BASE_URL`を優先し、未設定時は`http://127.0.0.1:8000`を使う。

## 6. 想定ファイル

```text
apps/web/src/app/
  page.tsx
  globals.css

apps/web/tests/
  dashboard.spec.ts
```

P0では既存の単一pageを拡張する。画面が増えた時点で`components/`、`lib/`へ分割する。

## 7. タスク

### P0: MVP必須

| ID | タスク | 完了条件 |
|---|---|---|
| P8-001 | Phase 8作業ブランチを作る | 完了。`phase8-web-frontend`で作業している |
| P8-002 | Phase 8 docを作る | 完了。この文書を作成した |
| P8-003 | API client helperを作る | 完了。health/db/model/predictionを取得できる |
| P8-004 | 予測dashboard UIを実装する | 完了。`raceId`入力とranking tableが表示される |
| P8-005 | error/empty stateを実装する | 完了。API失敗時もerror blockを表示する |
| P8-006 | Playwright testを更新する | 完了。予測ranking表示をE2Eで確認する |
| P8-007 | Web品質チェックを通す | 完了。整形、lint、Docker build、E2Eが成功する |
| P8-008 | Docker Web表示を確認する | 完了。`http://localhost:3000`で画面表示を確認した |
| P8-009 | docsを同期する | 完了。README、roadmap、構成台帳、Phase 8 docに実装結果を反映した |

### P1: MVP後の優先改善

| ID | タスク | 完了条件 |
|---|---|---|
| P8-101 | race list API連携 | 日付/場からraceを選べる |
| P8-102 | レース詳細panel | 出走表、締切、場、R情報を予測と分けて表示できる |
| P8-103 | mobile表示改善 | 小画面でrankと確率を優先表示できる |
| P8-104 | model status panel拡張 | dataset hash、作成日時、feature countを表示できる |
| P8-105 | UI component分割 | `components/`、`lib/api.ts`へ責務分離する |

### P2: 後続Phase候補

| ID | タスク | 扱い |
|---|---|---|
| P8-201 | 期待値ranking | Phase 9の期待値/バックテストAPI後 |
| P8-202 | 買い目候補UI | 買い目生成方針が固まってから |
| P8-203 | オッズ推移 | odds snapshotの表示API整備後 |
| P8-204 | バックテスト画面 | Phase 9 |
| P8-205 | model性能画面 | segment評価/MLflow表示方針が固まってから |

## 8. 完了条件

Phase 8 P0は以下をすべて満たした時点でMVP完了とする。

- [x] Web画面から`/health`、`/db/health`、`/models/latest`を確認できる
- [x] `raceId`を指定して`/races/{race_id}/prediction`を取得できる
- [x] 6艇のrank、艇番、選手、級別、1着確率を比較できる
- [x] API失敗時にerror stateが表示される
- [x] Desktop/mobile幅で表示が破綻しない
- [x] 整形、lint、Docker build、Playwright E2Eが成功する
- [x] Docker ComposeのWeb containerで表示確認できる
- [x] README、roadmap、構成台帳、この文書が同期されている

## 9. 2026-06-08 実装結果

Phase 8 P0/MVPは完了。

実装内容:

- `apps/web/src/app/page.tsx`をPhase 7予測APIへ接続するダッシュボードへ更新した
- `API_INTERNAL_BASE_URL`を優先し、未設定時は`http://127.0.0.1:8000`を使うserver component fetchにした
- `GET /health`、`GET /db/health`、`GET /models/latest`、`GET /races/{race_id}/prediction`の状態を画面に表示した
- `raceId`入力フォーム、予測ランキングテーブル、model contract、top pick panelを実装した
- API失敗時に画面全体を落とさず、該当panelにerror stateを表示するようにした
- desktopは情報密度を高く、mobileは縦積みかつテーブルのみ内部横スクロールにした
- `apps/web/tests/dashboard.spec.ts`を予測ランキング表示のE2Eへ更新した
- `apps/web/.prettierignore`を追加し、Playwright生成物と依存生成物を整形対象から外した
- `apps/web/.gitignore`へ`.pnpm-store`を追加した

検証証跡:

- `prettier --check src tests README.md package.json playwright.config.ts tsconfig.json next.config.ts eslint.config.mjs`: 成功
- `eslint src tests`: 成功
- `docker compose build web`: 成功
- `docker compose up -d web`: 成功
- `docker run --rm --network host -e PLAYWRIGHT_BASE_URL=http://127.0.0.1:3000 boatracelove-web pnpm test:e2e`: 1 passed
- Browser desktop確認: `BOATRACE=LOVE`、`raceId=20260528_01_01`、6艇table、API/model表示、ページ横スクロールなし
- Browser mobile確認: page width 375px、scroll width 375px、tableのみ内部scroll width 760px

残タスク:

- P0/MVPの残タスクはなし
- 今日の開催一覧、日付/場/Rからのrace selector、期待値、買い目、バックテスト、model性能画面はP1/P2またはPhase 9以降で扱う
