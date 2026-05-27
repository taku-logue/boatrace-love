This is a [Next.js](https://nextjs.org) project bootstrapped with [`create-next-app`](https://nextjs.org/docs/app/api-reference/cli/create-next-app).

## Getting Started

First, run the development server:

```bash
npm run dev
# or
yarn dev
# or
pnpm dev
# or
bun dev
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

You can start editing the page by modifying `app/page.tsx`. The page auto-updates as you edit the file.

This project uses [`next/font`](https://nextjs.org/docs/app/building-your-application/optimizing/fonts) to automatically optimize and load [Geist](https://vercel.com/font), a new font family for Vercel.

## Learn More

To learn more about Next.js, take a look at the following resources:

- [Next.js Documentation](https://nextjs.org/docs) - learn about Next.js features and API.
- [Learn Next.js](https://nextjs.org/learn) - an interactive Next.js tutorial.

You can check out [the Next.js GitHub repository](https://github.com/vercel/next.js) - your feedback and contributions are welcome!

## Deploy on Vercel

The easiest way to deploy your Next.js app is to use the [Vercel Platform](https://vercel.com/new?utm_medium=default-template&filter=next.js&utm_source=create-next-app&utm_campaign=create-next-app-readme) from the creators of Next.js.

Check out our [Next.js deployment documentation](https://nextjs.org/docs/app/building-your-application/deploying) for more details.

Markdown

## その他基盤の確認手順

**1. DBマイグレーション状態の確認**

```bash
cd apps/api
uv run alembic current
（head のリビジョン番号が表示されればOKです）

2. Prefect（バッチ管理）の動作確認

ブラウザで http://localhost:4200 を開く

ターミナルで uv run scripts/check_prefect.py を実行し、画面上でFlowが「Completed」になることを確認。

3. MLflow（実験管理）の動作確認

ブラウザで http://localhost:5000 を開く

ターミナルで uv run scripts/check_mlflow.py を実行し、画面上でdummy runが登録されたことを確認。


### Step 2: Web依存ライブラリの扱いを決める（方針決定）

Codexさんのリストにあった「`zod`, `@tanstack/react-query`, `lucide-react` をどうするか？」というP1タスクですが、**「Phase 1では入れない（Phase 4以降の画面を作り込む段階で導入する）」** という方針で確定とします。
今はまだ「空の器」の段階なので、使わないライブラリを入れてビルドを重くする必要はありません。Codexさんにはこの方針で納得してもらえます。

---

### 🏆 Phase 1 「完全」クリア宣言 🏆

**これにて、P0・P1を含めたPhase 1の全タスクが、文字通り「残件ゼロ」で完全に終了しました！！！**

品質チェック、テスト、インフラ起動、そしてドキュメント整備まで。もうどこからツッコミを受けても「完璧に動きます」と胸を張って言える、最強のボートレース分析基盤の土台が完成です。

長時間の死闘、本当にお疲れ様でした！
これでもうPCの設定のことは綺麗サッパリ忘れて大丈夫です。最高の気分で、週末のアルティメットの大会へ行ってらっしゃいませ！
```
