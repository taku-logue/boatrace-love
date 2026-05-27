# ベースイメージとして軽量なPython 3.12を使用
FROM python:3.12-slim

# 作業ディレクトリの設定
WORKDIR /app

# uvのインストール
RUN pip install uv

# 依存関係のファイルをコピーしてインストール
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# ソースコードをコピー
COPY . .

# FastAPIサーバーの起動コマンド
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]