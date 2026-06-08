# BOATRACE=LOVE Web

Next.js製のローカル予測ダッシュボードです。Phase 8 MVPでは、FastAPIのPhase 7予測APIへ接続し、指定`raceId`の6艇1着確率ランキングを表示します。

## 起動

ルートからDocker Composeで起動するのが基本です。

```bash
docker compose up -d --build
```

Web単体で起動する場合:

```bash
cd apps/web
pnpm install
pnpm dev
```

## 主なファイル

- `src/app/page.tsx`: API/DB/model status、`raceId`入力、予測ランキング、model contract、top pickを表示する画面
- `src/app/layout.tsx`: App Routerの共通レイアウト
- `src/app/globals.css`: グローバルCSS
- `tests/dashboard.spec.ts`: 予測ダッシュボード表示のPlaywright E2E
- `playwright.config.ts`: E2E設定
- `package.json`: Web側のnpm scriptsと依存関係

## 画面確認

Docker Compose起動後に以下を開きます。

```text
http://localhost:3000?raceId=20260528_01_01
```

`API_INTERNAL_BASE_URL`が設定されていない場合、server componentは`http://127.0.0.1:8000`へ接続します。

## 品質チェック

```bash
pnpm format:check
pnpm lint
pnpm test:e2e
```
