import os
import sys
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func

# パス設定
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from app.db.session import engine
from app.models.downloads import DownloadFile
from app.models.management import RawFile
from app.models.racer_period_stats import RacerPeriodStatRaw, RacerPeriodStat

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def slice_by_bytes(line_bytes: bytes, start: int, length: int) -> str:
    """バイト列から指定範囲を切り出し、文字列に戻して空白を取り除く"""
    try:
        return line_bytes[start:start+length].decode("cp932").strip()
    except Exception:
        return ""

def main():
    print("⚙️ DBへのパース結果保存を開始します...")
    with SessionLocal() as session:
        # 解凍済み（status == 'extracted'）のファイルを取得
        target = session.query(DownloadFile).filter(DownloadFile.status == 'extracted').first()
        if not target:
            print("✅ パース待ちのファイルはありません。")
            return

        raw_txt_file = session.query(RawFile).filter(RawFile.id == target.extracted_file_id).first()
        if not raw_txt_file:
            print("❌ テキストファイルのDBレコードが見つかりません。")
            return

        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        txt_path = os.path.join(base_dir, raw_txt_file.local_path)

        print(f"📄 読み込みファイル: {txt_path}")

        raw_records = []
        stat_records = []

        with open(txt_path, "r", encoding="cp932") as f:
            for line_num, line in enumerate(f, start=1):
                if not line.strip():
                    continue
                
                line_bytes = line.encode("cp932")
                
                # 必須項目の切り出し
                reg_no = slice_by_bytes(line_bytes, 0, 4)
                name_kanji = slice_by_bytes(line_bytes, 4, 16)
                name_kana = slice_by_bytes(line_bytes, 20, 15)
                branch = slice_by_bytes(line_bytes, 35, 4)
                racer_class = slice_by_bytes(line_bytes, 39, 2)
                
                raw_fields = {
                    "reg_no": reg_no,
                    "name_kanji": name_kanji,
                    "name_kana": name_kana,
                    "branch": branch,
                    "racer_class": racer_class,
                }

                # 生データの履歴用レコード (racer_period_stats_raw)
                raw_records.append({
                    "download_file_id": target.id,
                    "raw_file_id": raw_txt_file.id,
                    "line_number": line_num,
                    "raw_text": line.strip(),
                    "raw_fields": raw_fields,
                    "parse_status": "success",
                    "parser_version": "v1.0"
                })

                # アプリケーション利用用レコード (racer_period_stats)
                stat_records.append({
                    "download_file_id": target.id,
                    "period_year": target.period_year,
                    "period_term": target.period_term,
                    "racer_registration_no": reg_no,
                    "racer_name": name_kanji,
                    "branch": branch,
                    "racer_class": racer_class,
                    "raw_values": raw_fields,
                    "normalized_values": {}
                })

        print(f"💾 {len(raw_records)} 件のデータをDBに一括挿入します...")

        # 1. Rawデータのインサート
        if raw_records:
            session.execute(insert(RacerPeriodStatRaw).values(raw_records))
        
        # 2. StatデータのUpsert（既にあれば更新）
        if stat_records:
            stmt = insert(RacerPeriodStat).values(stat_records)
            stmt = stmt.on_conflict_do_update(
                index_elements=['period_year', 'period_term', 'racer_registration_no'],
                set_={
                    'racer_name': stmt.excluded.racer_name,
                    'branch': stmt.excluded.branch,
                    'racer_class': stmt.excluded.racer_class,
                    'raw_values': stmt.excluded.raw_values,
                    'updated_at': func.now()
                }
            )
            session.execute(stmt)

        # ステータスを完了に更新
        target.status = "completed"
        session.commit()
        print("🎉 データベースへの保存が完了しました！")

if __name__ == "__main__":
    main()