# BOATRACE=LOVE Web

Next.js製のローカル分析ダッシュボードです。現時点ではPhase 1の疎通確認用画面が中心で、レース詳細UIや予測表示はPhase 8以降で拡張する想定です。

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

- `src/app/page.tsx`: ダッシュボード初期画面
- `src/app/layout.tsx`: App Routerの共通レイアウト
- `src/app/globals.css`: グローバルCSS
- `tests/dashboard.spec.ts`: Playwright E2E
- `playwright.config.ts`: E2E設定
- `package.json`: Web側のnpm scriptsと依存関係

## 品質チェック

```bash
pnpm format:check
pnpm lint
pnpm test:e2e
```
