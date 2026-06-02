import sys
import os
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
sys.path.append("/app")

from app.ingestion.html_fetcher import fetch_html, save_raw_html

def main():
    # テスト対象: 2026年6月1日の唐津(23) 第1レースの出走表
    target_date = date(2026, 6, 1)
    venue_code = "23"
    race_no = 1
    
    # 公式サイトのURL組み立て規則
    date_str = target_date.strftime("%Y%m%d")
    url = f"https://www.boatrace.jp/owpc/pc/race/racelist?rno={race_no}&jcd={venue_code}&hd={date_str}"
    
    print(f"🌐 URLへアクセス中: {url}")
    html = fetch_html(url)
    
    if html:
        print(f"✅ HTMLの取得に成功しました！ (文字数: {len(html)}文字)")
        
        # HTMLをローカルに保存
        filepath = save_raw_html(html, target_date, "racelist", venue_code, race_no)
        print(f"💾 取得したHTMLを保存しました: {filepath}")
        
        # 中身がちゃんと取れているか、最初の300文字だけ表示
        print("\n--- HTMLの先頭300文字 ---")
        print(html[:300])
        print("-------------------------")
    else:
        print("⚠️ HTMLの取得に失敗しました。")

if __name__ == "__main__":
    main()