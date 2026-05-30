import sys
import os
from datetime import date

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))
sys.path.append("/app")

from app.db.session import engine
from sqlalchemy.orm import sessionmaker
from app.ingestion.race_cards.parse import parse_race_card_file
from app.ingestion.race_cards.load import upsert_race_cards
from app.ingestion.race_results.parse import parse_race_result_file
from app.ingestion.race_results.load import upsert_race_results

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    # 実際の日付をセット
    target_date = date(2026, 5, 30)
    
    # ⚠️ 解凍したテキストファイルのパスを指定してください（コンテナ内から見たパス）
    b_file_path = "/data/B260530.TXT"
    k_file_path = "/data/K260530.TXT"

    with SessionLocal() as session:
        # FK制約を回避するため、ダミーのID(-1)をセットしてUpsert
        # (本番のパイプラインでは正式なファイルIDが入ります)
        
        if os.path.exists(b_file_path):
            print("🚤 番組表(B) ファイルを処理中...")
            b_races, b_raw, b_entries = parse_race_card_file(b_file_path, -1, -1, target_date)
            upsert_race_cards(session, b_races, [], b_entries) # rawはダミーIDでエラーになるので今回は空配列
            print(f"✅ 番組表: レース数={len(b_races)}, 出走数={len(b_entries)}")
        else:
            print(f"⚠️ {b_file_path} が見つかりません。")

        if os.path.exists(k_file_path):
            print("🏁 競走成績(K) ファイルを処理中...")
            k_races, k_raw, k_results, k_payouts = parse_race_result_file(k_file_path, -1, -1, target_date)
            upsert_race_results(session, k_races, [], k_results, k_payouts)
            print(f"✅ 競走成績: レース数={len(k_races)}, 結果数={len(k_results)}, 払戻数={len(k_payouts)}")
        else:
            print(f"⚠️ {k_file_path} が見つかりません。")

        session.commit()
        print("🎉 すべてのデータがDBに保存されました！")

if __name__ == "__main__":
    main()