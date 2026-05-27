import httpx
import re
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import sessionmaker

import sys
import os
# プロジェクト内のモジュールを読み込むためのパス設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

# Phase 1で作った session.py から engine を読み込み、手動でセッションを作成します
from app.db.session import engine
from app.models.downloads import DownloadFile
from app.models.management import DataSource

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_or_create_source(session) -> int:
    """ボートレース公式データのデータソースIDを取得（なければ作成）"""
    source = session.execute(select(DataSource).where(DataSource.name == "BOAT RACE Official")).scalar_one_or_none()
    if not source:
        source = DataSource(
            name="BOAT RACE Official",
            base_url="https://www.boatrace.jp",
            description="BOAT RACE公式データダウンロードページ"
        )
        session.add(source)
        session.commit()
        session.refresh(source)
    return source.id

def main():
    base_url = "https://www.boatrace.jp/owpc/pc/extra/data/download.html"
    print(f"🚤 公式ダウンロードページにアクセス中: {base_url}")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    try:
        # 同期のhttpxを使用（タイムアウトは30秒）
        response = httpx.get(base_url, headers=headers, timeout=30.0)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ アクセス失敗: {e}")
        return

    soup = BeautifulSoup(response.content, "html.parser")
    links = soup.find_all("a", href=True)
    lzh_links = [a for a in links if "fan" in a["href"] and a["href"].endswith(".lzh")]

    print(f"✅ LZHファイル（期別成績）を {len(lzh_links)} 件見つけました。DBへ登録します...")

    # 同期セッションでデータベースへアクセス
    with SessionLocal() as session:
        source_id = get_or_create_source(session)
        inserted_count = 0

        from sqlalchemy.sql import func

        for a in lzh_links:
            full_url = urljoin(base_url, a['href'])
            filename = full_url.split('/')[-1] # 例: fan2510.lzh
            display_name = " ".join(a.text.split())

            # ファイル名から年度と期を正規表現で抽出
            match = re.search(r'fan(\d{2})(\d{2})\.lzh', filename)
            if not match:
                continue

            year_short = int(match.group(1))
            month = match.group(2)
            
            # 西暦4桁に変換 (2000年代前提)
            period_year = 2000 + year_short
            period_term = "first_half" if month == "10" else "second_half"

            # DBへUpsert（既にあれば更新、なければ挿入）するクエリ
            stmt = insert(DownloadFile).values(
                source_id=source_id,
                data_type="racer_period_stats",
                period_year=period_year,
                period_term=period_term,
                display_name=display_name,
                source_url=full_url,
                source_filename=filename,
                status="discovered"
            ).on_conflict_do_update(
                index_elements=['data_type', 'period_year', 'period_term', 'source_url'],
                set_=dict(
                    last_seen_at=func.now(),
                    display_name=display_name,
                    source_filename=filename
                )
            )

            session.execute(stmt)
            inserted_count += 1 
            
        session.commit()
        print(f"🎉 DBへの登録（Upsert）が完了しました！ (処理件数: {inserted_count}件)")

if __name__ == "__main__":
    main()