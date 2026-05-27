# ベースイメージとしてNode.js 24を使用
FROM node:24-slim

# 作業ディレクトリの設定
WORKDIR /app

# 自動ビルド環境であることを明示（途中でYes/Noの質問を出させない）
ENV CI=true

# pnpmのインストール
RUN corepack enable && corepack prepare pnpm@latest --activate

# 依存関係のファイルをコピーしてインストール
COPY package.json pnpm-lock.yaml* ./
# セキュリティチェックを一時的に無視してインストール
RUN pnpm install --ignore-scripts
RUN pnpm exec playwright install --with-deps chromium

# ソースコードをコピー
COPY . .

# Next.jsのビルドと起動
RUN pnpm run build
CMD ["pnpm", "start"]
