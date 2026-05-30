import sys
import os
import time
import requests
import subprocess
from datetime import date, timedelta
import hashlib

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
sys.path.append("/app")

from sqlalchemy.orm import sessionmaker
from app.db.session import engine
# 必要な関数群のインポート
from app.ingestion.race_cards.parse import parse_race_card_file
from app.ingestion.race_cards.load import upsert_race_cards
from app.ingestion.race_results.parse import parse_race_result_file
from app.ingestion.race_results.load import upsert_race_results

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
TMP_DIR = "/data/tmp"

def download_file(url: str, filepath: str) -> bool:
    """URLからファイルをダウンロードする"""
    try:
        response = requests.get(url, stream=True, timeout=10)
        if response.status_code == 200:
            with open(filepath, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            return True
        else:
            return False
    except Exception as e:
        print(f"ダウンロードエラー ({url}): {e}")
        return False

def extract_lzh(lzh_path: str, output_dir: str) -> str | None:
    """7zを使ってLZHを解凍し、出てきたTXTファイルのパスを返す"""
    try:
        # 解凍実行
        result = subprocess.run(
            ["7z", "e", lzh_path, f"-o{output_dir}", "-y"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        
        # 解凍された .TXT ファイルを探す
        for file in os.listdir(output_dir):
            if file.upper().endswith(".TXT"):
                return os.path.join(output_dir, file)
    except Exception:
        pass
    return None

def process_daily_data(session, target_date: date):
    """1日分のBファイルとKファイルを処理する"""
    print(f"\n--- 📅 処理開始: {target_date.strftime('%Y-%m-%d')} ---")
    
    # URLの生成 (公式の規則: YYMMDD)
    # 2026年なら "26", 5月なら "05", 30日なら "30"
    yy = str(target_date.year)[-2:]
    mm = f"{target_date.month:02d}"
    dd = f"{target_date.day:02d}"
    yymm = f"{target_date.year}{mm}"
    
    b_url = f"https://www1.mbrace.or.jp/od2/B/{yymm}/b{yy}{mm}{dd}.lzh"
    k_url = f"https://www1.mbrace.or.jp/od2/K/{yymm}/k{yy}{mm}{dd}.lzh"
    
    b_lzh = os.path.join(TMP_DIR, f"b{yy}{mm}{dd}.lzh")
    k_lzh = os.path.join(TMP_DIR, f"k{yy}{mm}{dd}.lzh")

    # --- 番組表(B)の処理 ---
    if download_file(b_url, b_lzh):
        b_txt = extract_lzh(b_lzh, TMP_DIR)
        if b_txt:
            print("🚤 番組表をDBへ保存中...")
            b_races, b_raw, b_entries = parse_race_card_file(b_txt, -1, -1, target_date)
            upsert_race_cards(session, b_races, [], b_entries)
            print(f"✅ 番組表: レース数={len(b_races)}, 出走数={len(b_entries)}")
            os.remove(b_txt) # お掃除
        os.remove(b_lzh)

    # --- 競走成績(K)の処理 ---
    if download_file(k_url, k_lzh):
        k_txt = extract_lzh(k_lzh, TMP_DIR)
        if k_txt:
            print("🏁 競走成績をDBへ保存中...")
            k_races, k_raw, k_results, k_payouts = parse_race_result_file(k_txt, -1, -1, target_date)
            upsert_race_results(session, k_races, [], k_results, k_payouts)
            print(f"✅ 競走成績: レース数={len(k_races)}, 結果数={len(k_results)}, 払戻数={len(k_payouts)}")
            os.remove(k_txt) # お掃除
        os.remove(k_lzh)

    session.commit()

def main():
    # 作業用の一時フォルダを作成
    os.makedirs(TMP_DIR, exist_ok=True)
    
    # 📝 取得したい期間を設定（例: 2026年5月28日 〜 2026年5月30日）
    start_date = date(2026, 5, 28)
    end_date = date(2026, 5, 30)

    with SessionLocal() as session:
        current_date = start_date
        while current_date <= end_date:
            process_daily_data(session, current_date)
            current_date += timedelta(days=1)
            time.sleep(1) # サーバーへの負荷軽減のためのインターバル

    print("\n🎉 指定期間の全データ処理が完了しました！")

if __name__ == "__main__":
    main()