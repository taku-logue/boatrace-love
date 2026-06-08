# Phase 7 予測API設計・実装計画

作成日: 2026-06-08
更新日: 2026-06-08
推奨ブランチ: `phase7-prediction-api`
ステータス: MVP実装・検証完了
進捗: 100%（P0/MVP。P1/P2は後続改善候補）

## 1. 目的

Phase 7では、Phase 6で作成した学習済みmodel bundleをFastAPIから利用できるようにし、指定レースの各艇1着確率を返す予測APIを作る。

MVPでは、買い目生成や回収率バックテストまでは扱わない。まずは「DB上の出走情報から学習時と同じ特徴量列を作り、学習済みLightGBM modelで推論し、レース内で合計1になる1着確率をAPI responseとして返す」ことを固定する。

```text
race_id -> inference features -> preprocessing -> model.predict_proba
        -> race-level normalization -> prediction response
```

Phase 7のゴールは、Phase 8のWeb画面が安心して呼べる予測API契約を作ることである。

## 2. 前提

Phase 7は以下の成果物を前提にする。

| Phase | 前提成果物 | Phase 7での用途 |
|---|---|---|
| Phase 2 | `racer_period_stats` | 選手期別特徴量 |
| Phase 3 | `races`、`race_entries`、`race_results` | 出走表、過去成績特徴量、検証用race |
| Phase 4 | `pre_race_entry_infos`、`weather_observations`、`odds_snapshot_entries` | 展示後/オッズ込み予測の追加入力 |
| Phase 5 | `apps/api/app/features/` | 推論用特徴量生成の土台 |
| Phase 6 | `apps/api/app/ml/`、`data/processed/models/` | model load、前処理、推論、確率正規化 |

Phase 6 MVPのmodel bundleは以下を1組として扱う。

```text
data/processed/models/{model_name}/{model_version}/
  model.joblib
  model_metadata.json
  feature_columns.json
  categorical_columns.json
  preprocessing_config.json
```

現時点の基準modelは`lgbm_win_v1`で、主対象のmodel viewは`pre_race_no_odds`とする。

## 3. MVP範囲

### 3.1 Phase 7で作るもの

| 成果物 | 内容 |
|---|---|
| Model store | model bundleを検出、検証、load、cacheする |
| 推論用feature builder | `target_*`や結果系を使わず、指定raceの特徴量を作る |
| Prediction service | 前処理、LightGBM推論、レース内確率正規化、rank付けを行う |
| Pydantic schema | API responseとerror responseの契約を固定する |
| FastAPI router | `/models/latest`と`/races/{race_id}/prediction`を提供する |
| エラーハンドリング | modelなし、raceなし、6艇不足、特徴量不一致を明確に返す |
| pytest | model store、feature整合、service、endpointを固定する |
| README/OpenAPI整備 | Phase 8が参照できるAPI仕様と実行手順を残す |

### 3.2 Phase 7 MVPで作らないもの

以下はPhase 7のP0完了条件には含めない。

- `POST /models/train`
- `GET /backtests`
- 買い目生成
- 期待値ランキング
- 回収率シミュレーション
- SHAPなどの説明可能性API
- DB上の本格的なmodel registry table
- Web画面
- 認証、rate limit、公開API化

これらはPhase 8以降、またはPhase 9のバックテスト/運用設計で扱う。

## 4. API契約

### 4.1 P0 endpoint

| Method | Path | 目的 |
|---|---|---|
| `GET` | `/models/latest` | 利用可能な最新model bundleのmetadataを返す |
| `GET` | `/races/{race_id}/prediction` | 指定raceの各艇1着確率を返す |

既存の`GET /health`、`GET /db/health`、`GET /version`は維持する。

### 4.2 Query parameters

`GET /races/{race_id}/prediction`は以下を受け取る。

| Parameter | 必須 | Default | 内容 |
|---|---|---|---|
| `model_name` | no | `lgbm_win_v1` | 使用するmodel名 |
| `model_version` | no | `latest` | 使用するmodel version |
| `model_view` | no | `pre_race_no_odds` | 使用する特徴量view |
| `include_features` | no | `false` | debug用に特徴量概要を返すか |

`include_features=true`は開発/検証用途に限定し、実特徴量の全量ではなく欠損flagやschema差分の概要だけを返す。

### 4.3 Response案

```json
{
  "race_id": "20260530_23_01",
  "race_date": "2026-05-30",
  "venue_code": "23",
  "race_no": 1,
  "model_name": "lgbm_win_v1",
  "model_version": "20260607T144526Z",
  "model_view": "pre_race_no_odds",
  "prediction_status": "ok",
  "predicted_at": "2026-06-08T10:30:00+09:00",
  "probability_sum": 1.0,
  "entries": [
    {
      "rank": 1,
      "boat_no": 1,
      "racer_registration_no": "0000",
      "racer_name": "選手名",
      "racer_class": "A1",
      "raw_win_probability": 0.421,
      "win_probability": 0.356,
      "is_missing_period_stats": false,
      "is_missing_pre_race": false,
      "is_missing_weather": false,
      "is_missing_odds": false
    }
  ]
}
```

`win_probability`は同一race内で合計1になるよう正規化した値を返す。`raw_win_probability`はLightGBMのpositive class probabilityをそのまま返す。

### 4.4 Error response案

```json
{
  "error_code": "incomplete_entries",
  "message": "Prediction requires exactly 6 entries for one race.",
  "race_id": "20260530_23_01",
  "details": {
    "entry_count": 5
  }
}
```

主なerror code:

| HTTP | error_code | 内容 |
|---|---|---|
| 404 | `model_not_found` | 指定model bundleが存在しない |
| 404 | `race_not_found` | 指定raceがDBに存在しない |
| 422 | `incomplete_entries` | 6艇揃っていない |
| 422 | `feature_unavailable` | 必要特徴量を生成できない |
| 422 | `preprocessing_mismatch` | 学習時feature listと推論featureが一致しない |
| 422 | `unsupported_model_view` | 未対応のmodel viewが指定された |
| 500 | `prediction_failed` | 予期しない推論失敗 |

## 5. 想定ディレクトリ

Phase 7実装時の候補。

```text
apps/api/app/
  prediction/
    __init__.py
    errors.py
    features.py
    model_store.py
    schemas.py
    service.py
  routers/
    __init__.py
    models.py
    predictions.py

apps/api/tests/
  prediction/
    __init__.py
    test_model_store.py
    test_prediction_features.py
    test_prediction_service.py
    test_prediction_routes.py
```

既存の`apps/api/app/ml/`は学習と推論の共通部品として使う。Phase 7専用のAPI責務は`apps/api/app/prediction/`へ分ける。

## 6. 実装方針

### 6.1 Model store

`model_store.py`は以下を担当する。

- `MODEL_ROOT`配下だけを探索する
- `latest`指定時に最新version directoryを解決する
- 必須artifactの存在を検証する
- `model_metadata.json`を読み、`model_name`、`model_version`、`model_view`を確認する
- `model.joblib`を`load_model`で読み込む
- `preprocessing_config.json`を`FeaturePreprocessor.load`で読み込む
- file mtimeまたはpathをkeyにしてprocess内cacheする

path traversalを避けるため、API parameterから任意pathを直接組み立てない。

### 6.2 推論用feature builder

現在の`build_training_dataset`は最後にlabelを結合するため、当日予測にはそのまま使わない。Phase 7では、以下のどちらかでlabelなしの推論featureを作る。

1. `apps/api/app/features/build.py`からlabel結合前の処理を関数として切り出す
2. `apps/api/app/prediction/features.py`でPhase 5のfeature関数を呼び出す薄いwrapperを作る

優先は1。学習用と推論用で特徴量生成の差分が増えると、Phase 6 model bundleとの整合が壊れやすいため。

推論featureの禁止事項:

- `race_results`由来の結果列を入れない
- `payouts`由来の払戻列を入れない
- `target_*`を入れない
- `exclude_reason`をモデル特徴量へ入れない
- `race_date`、`race_id`、`boat_no`などmetadata列をモデル特徴量へ直接入れない

### 6.3 Prediction service

`service.py`は以下の順序で処理する。

1. model bundleをloadする
2. 指定`race_id`から推論featureを作る
3. 6艇が揃っていることを確認する
4. metadata列とfeature列を分離する
5. 学習時`feature_columns`と列名、列順を一致させる
6. `FeaturePreprocessor.transform`を実行する
7. `predict_positive_probability`で生確率を出す
8. `normalize_probabilities_by_race`で正規化する
9. `win_probability`降順でrankを付ける
10. Pydantic responseへ変換する

## 7. 設定

Phase 7で追加する候補の環境変数。

| Variable | Default | 内容 |
|---|---|---|
| `MODEL_ROOT` | `/data/processed/models` | model bundle探索root |
| `DEFAULT_MODEL_NAME` | `lgbm_win_v1` | default model |
| `DEFAULT_MODEL_VIEW` | `pre_race_no_odds` | default model view |
| `PREDICTION_CACHE_ENABLED` | `true` | process内model cache |

Docker Composeでは、repo内の`data/processed/models`をAPI containerから読める配置にする。

## 8. タスク

### P0: MVP必須

2026-06-08時点でP0はすべて完了。

| ID | タスク | 完了条件 |
|---|---|---|
| P7-001 | Phase 7作業ブランチを作る | `phase7-prediction-api`で作業を開始している |
| P7-002 | model bundle loaderを実装する | 必須artifact欠損、latest解決、metadata読込をpytestで確認する |
| P7-003 | labelなし推論feature builderを実装する | 指定`race_id`で6艇分のfeatureが作れ、`target_*`を含まない |
| P7-004 | Prediction serviceを実装する | model loadから正規化済み確率生成まで単体テストで通る |
| P7-005 | API schemaを実装する | response/error contractがPydanticで固定される |
| P7-006 | `/models/latest`を実装する | 最新model metadataをHTTP 200で返す |
| P7-007 | `/races/{race_id}/prediction`を実装する | 既知のcomplete raceで6艇の予測を返す |
| P7-008 | error handlingを実装する | modelなし、raceなし、6艇不足、feature mismatchをHTTP status込みで返す |
| P7-009 | Docker/API実行手順を整える | API containerからmodel bundleを読んでendpointが動く |
| P7-010 | 品質確認を通す | `ruff format --check`、`ruff check`、`mypy app`、`pytest`が成功する |
| P7-011 | docsを同期する | README、roadmap、構成台帳、Phase 7 docに実装結果と証跡を反映する |

### P1: MVP後の優先改善

| ID | タスク | 完了条件 |
|---|---|---|
| P7-101 | model version明示選択 | `model_version`指定で任意bundleをloadできる |
| P7-102 | `pre_race_with_odds`予測 | 単勝オッズ込みのmodel bundleとfeatureが一致する |
| P7-103 | `exhibition_with_odds`予測 | 展示/気象/オッズ込みのmodel bundleとfeatureが一致する |
| P7-104 | 予測snapshot保存 | prediction request/responseの要約をDBまたはlocal artifactへ記録できる |
| P7-105 | `/races/today`、`/venues/today` | Phase 8画面が今日のレースを一覧できる |
| P7-106 | OpenAPI example拡充 | Swagger UIで主要response exampleを確認できる |

### P2: 後続Phase候補

| ID | タスク | 扱い |
|---|---|---|
| P7-201 | `POST /models/train` | 学習は当面CLI継続。API化は運用方針確定後 |
| P7-202 | `GET /backtests` | Phase 9の回収率検証で扱う |
| P7-203 | 期待値API | オッズ品質、控除率、買い目方針が固まってから扱う |
| P7-204 | SHAP/explain API | model改善段階で追加 |
| P7-205 | DB model registry | file-based model storeで不足が出てから追加 |
| P7-206 | 認証/rate limit | 公開運用を始める時に追加 |

## 9. 完了条件

Phase 7 P0は、以下をすべて満たした時点でMVP完了とする。

- `GET /models/latest`が最新model bundleのmetadataを返す
- `GET /races/{race_id}/prediction`が既知のcomplete raceで6艇分の予測を返す
- 返却される`win_probability`の合計が1.0付近になる
- 推論featureに`target_*`、結果系、払戻系の未来情報が含まれない
- 学習時`feature_columns`と推論feature列が一致しない場合に明示的に失敗する
- modelなし、raceなし、6艇不足がそれぞれ適切なHTTP statusとerror codeで返る
- Docker ComposeのAPI containerからmodel bundleを読んで予測できる
- FastAPIのOpenAPIでendpointとresponse schemaを確認できる
- `ruff format --check`、`ruff check`、`mypy app`、`pytest`が成功する
- README、roadmap、構成台帳、この文書に実装結果と検証証跡が反映されている

## 10. 実装順

最短でPhase 8へつなぐため、次の順番で進める。

1. Phase 6 model bundle契約を確認する
2. model storeを作る
3. labelなし推論feature builderを作る
4. Prediction serviceを作る
5. `/models/latest`を作る
6. `/races/{race_id}/prediction`を作る
7. error handlingとschemaを固める
8. pytestを増やす
9. Docker containerからendpointを確認する
10. docsを実装結果へ更新する

## 11. 実装時の注意

- Phase 7は「予測API」であり「モデル改善」ではない。精度改善はPhase 6後続改善またはPhase 9以降に分ける。
- `build_training_dataset`をそのまま当日予測へ使わない。label生成に依存しない入口を用意する。
- feature列の不足を黙って0埋めしない。学習時と違う列構成は失敗させる。
- model artifactはGit管理しない。APIからは設定されたmodel rootを読む。
- API responseに買い目推奨のような意思決定文言を含めない。Phase 7は確率を返すだけにする。
- 実データでのendpoint確認は、Phase 6で使った既知complete raceから始める。

## 12. 2026-06-08 実装結果

Phase 7 P0/MVPは完了。

実装内容:

- `phase7-prediction-api`ブランチを作成した
- `apps/api/app/features/build.py`へlabelなしの`build_feature_dataset`を追加した
- `apps/api/app/prediction/model_store.py`へfile-based model storeを追加した
- `apps/api/app/prediction/features.py`へ推論feature整形と6艇チェックを追加した
- `apps/api/app/prediction/service.py`へmodel load、preprocessing、推論、確率正規化、rank付けを追加した
- `apps/api/app/prediction/schemas.py`と`errors.py`へAPI response/error contractを追加した
- `apps/api/app/routers/models.py`と`predictions.py`へ`GET /models/latest`、`GET /races/{race_id}/prediction`を追加した
- `apps/api/app/core/config.py`、`.env.example`、`docker-compose.yml`へmodel root/default設定を追加した
- `apps/api/tests/prediction/`へmodel store、feature、service、routerのテストを追加した

確認済み:

- `uv run ruff format .`
- `uv run ruff check .`
- `uv run mypy app`
- `uv run pytest`: 74 passed
- `GET /models/latest`: HTTP 200、`lgbm_win_v1`、`20260607T144526Z`
- `GET /races/20260528_01_01/prediction`: HTTP 200、6 entries、`probability_sum=1.0`
- `docker compose up -d --build api`後、API containerでも同endpointを確認済み

未完了として残すもの:

- `pre_race_with_odds`、`exhibition_with_odds`用model bundleの学習とAPI確認
- 予測snapshot保存
- `/races/today`、`/venues/today`
- OpenAPI example拡充
- `POST /models/train`
- `GET /backtests`
- 期待値API、買い目生成API
