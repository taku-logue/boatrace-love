import sys
import os
import time
from datetime import date, datetime
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
sys.path.append("/app")

from app.db.session import engine
from app.ingestion.html_fetcher import fetch_html, save_raw_html
from app.ingestion.live.parse import (
    parse_live_race_card_html, 
    parse_live_beforeinfo_html, 
    parse_live_odds_tf_html,
    parse_live_active_venues # 👈 追加
)
from app.ingestion.race_cards.load import upsert_race_cards
from app.ingestion.live.load import upsert_pre_race_info, upsert_odds_snapshots

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def process_live_race_card(session, target_date: date, venue_code: str, race_no: int):
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={venue_code}&hd={date_str}"
    html = fetch_html(url, sleep_seconds=1)
    if html:
        save_raw_html(html, target_date, "racelist", venue_code, race_no)
        race_records, entry_records = parse_live_race_card_html(html, target_date, venue_code, race_no)
        if entry_records:
            upsert_race_cards(session, race_records, [], entry_records)
            return True
    return False

def process_live_beforeinfo(session, target_date: date, venue_code: str, race_no: int):
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.boatrace.jp/owpc/pc/race/beforeinfo?rno={race_no}&jcd={venue_code}&hd={date_str}"
    html = fetch_html(url, sleep_seconds=1)
    if html:
        save_raw_html(html, target_date, "beforeinfo", venue_code, race_no)
        records = parse_live_beforeinfo_html(html, target_date, venue_code, race_no)
        if records:
            upsert_pre_race_info(session, records)

def process_live_odds(session, target_date: date, venue_code: str, race_no: int, fetched_at: datetime):
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.boatrace.jp/owpc/pc/race/oddstf?rno={race_no}&jcd={venue_code}&hd={date_str}"
    html = fetch_html(url, sleep_seconds=1)
    if html:
        save_raw_html(html, target_date, "oddstf", venue_code, race_no)
        records = parse_live_odds_tf_html(html, target_date, venue_code, race_no, fetched_at)
        if records:
            upsert_odds_snapshots(session, records)

def main():
    # ⚠️ テストとして、データが確実に存在する過去の日付を指定しています
    target_date = date(2026, 6, 1)
    date_str = target_date.strftime("%Y%m%d")
    fetched_at = datetime.now()
    
    print(f"🚀 Phase 4: 全自動リアルタイムクローラー起動 ({target_date})")
    
    # 1. まず本日の開催場一覧ページを取得
    index_url = f"https://www.boatrace.jp/owpc/pc/race/index?hd={date_str}"
    print(f"🔍 本日の開催場一覧を取得中...")
    index_html = fetch_html(index_url, sleep_seconds=1)
    
    if not index_html:
        print("❌ 開催場一覧の取得に失敗しました。")
        return
        
    active_venues = parse_live_active_venues(index_html)
    print(f"🏟 本日開催されている場コード一覧: {active_venues}")
    
    if not active_venues:
        print("⚠️ 本日開催されているレース場がありません。")
        return

    # 2. 見つかったすべての場を順番に処理
    with SessionLocal() as session:
        for venue_code in active_venues:
            print(f"\n======== 🏟 場コード: {venue_code} の処理を開始 ========")
            
            # 各場の1R〜12Rをループ
            for race_no in range(1, 13):
                print(f"\n--- 🏁 {venue_code}場 {race_no}R ---")
                
                # 出走表を試しに取得し、データがなければその場は終了（あるいはまだ番組が確定していない）
                has_data = process_live_race_card(session, target_date, venue_code, race_no)
                if not has_data:
                    print(f"ℹ️ {race_no}Rの番組がありません。この場のループを終了します。")
                    break
                
                # 直前情報とオッズも続けて取得
                process_live_beforeinfo(session, target_date, venue_code, race_no)
                process_live_odds(session, target_date, venue_code, race_no, fetched_at)
                
                print(f"✅ {venue_code}場 {race_no}R の全ライブデータ保存完了")
                
            session.commit() # 1場ごとにコミット
            
    print("\n🎉 本日の全開催場・全レースの巡回が完了しました！")

if __name__ == "__main__":
    main()