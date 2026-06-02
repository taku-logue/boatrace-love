import os
import time
import requests
from datetime import date

# 公式サイトから「怪しいアクセス」と判定されないための一般的なブラウザ情報
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_html(url: str, sleep_seconds: int = 1) -> str | None:
    """指定したURLからHTMLを取得する。サーバー負荷軽減のためのスリープを含む。"""
    time.sleep(sleep_seconds)
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()
        # ボートレース公式サイトはUTF-8で返してくることが多いですが、念のためエンコーディングを自動判定させます
        response.encoding = response.apparent_encoding
        return response.text
    except Exception as e:
        print(f"❌ HTML取得エラー ({url}): {e}")
        return None

def save_raw_html(html: str, target_date: date, page_type: str, venue_code: str, race_no: int) -> str:
    """取得したHTMLを失わないようにファイルとして保存し、そのパスを返す"""
    date_str = target_date.strftime("%Y%m%d")
    
    # 保存先ディレクトリ (例: /data/raw/html/20260601)
    dir_path = f"/data/raw/html/{date_str}"
    os.makedirs(dir_path, exist_ok=True)

    # ファイル名 (例: racelist_23_01.html)
    filename = f"{page_type}_{str(venue_code).zfill(2)}_{race_no:02d}.html"
    filepath = os.path.join(dir_path, filename)

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(html)
    
    return filepath