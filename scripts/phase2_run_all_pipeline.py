import os
import sys
import httpx
import hashlib
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.sql import func
import time

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from app.db.session import engine
from app.models.downloads import DownloadFile
from app.models.management import RawFile
from app.models.racer_period_stats import RacerPeriodStatRaw, RacerPeriodStat
from app.ingestion.archive import LzhExtractor

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def slice_by_bytes(line_bytes: bytes, start: int, length: int) -> str:
    try:
        return line_bytes[start : start + length].decode("cp932").strip()
    except Exception:
        return ""


def main():
    print("🚀 残りファイルの全自動処理パイプラインを開始します...")

    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))

    with SessionLocal() as session:
        while True:
            # まだ完了していないファイルを1件取得
            target = session.query(DownloadFile).filter(DownloadFile.status == "discovered").first()

            if not target:
                print("✅ すべてのファイルの処理が完了しました！")
                break

            print(f"\n🎯 処理開始: {target.display_name} ({target.source_filename})")

            try:
                # -----------------------------------------
                # 1. ダウンロード
                # -----------------------------------------
                save_dir = os.path.join(
                    base_dir,
                    "data/raw/official_downloads/racer_period_stats",
                    str(target.period_year),
                    target.period_term,
                )
                os.makedirs(save_dir, exist_ok=True)
                save_path = os.path.join(save_dir, target.source_filename)

                headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
                response = httpx.get(target.source_url, headers=headers, timeout=30.0)
                response.raise_for_status()

                with open(save_path, "wb") as f:
                    f.write(response.content)

                lzh_hash = hashlib.sha256(response.content).hexdigest()
                relative_save_path = os.path.relpath(save_path, start=base_dir)

                raw_file = RawFile(
                    source_id=target.source_id,
                    file_type="lzh",
                    source_url=target.source_url,
                    local_path=relative_save_path,
                    sha256=lzh_hash,
                    file_metadata={"original_filename": target.source_filename},
                )
                session.add(raw_file)
                session.flush()

                # -----------------------------------------
                # 2. 解凍
                # -----------------------------------------
                extracted_dir = os.path.join(
                    base_dir,
                    "data/raw/extracted/racer_period_stats",
                    str(target.period_year),
                    target.period_term,
                )
                extracted_files = LzhExtractor.extract_lzh(save_path, extracted_dir)
                txt_file_path = extracted_files[0]

                with open(txt_file_path, "rb") as f:
                    txt_hash = hashlib.sha256(f.read()).hexdigest()

                relative_txt_path = os.path.relpath(txt_file_path, start=base_dir)

                extracted_raw_file = RawFile(
                    source_id=target.source_id,
                    file_type="txt",
                    local_path=relative_txt_path,
                    sha256=txt_hash,
                    file_metadata={"extracted_from_lzh": target.source_filename},
                )
                session.add(extracted_raw_file)
                session.flush()

                # -----------------------------------------
                # 3. パースとDB保存
                # -----------------------------------------
                raw_records = []
                stat_records = []

                with open(txt_file_path, "r", encoding="cp932") as f:
                    for line_num, line in enumerate(f, start=1):
                        if not line.strip():
                            continue

                        line_bytes = line.encode("cp932")
                        reg_no = slice_by_bytes(line_bytes, 0, 4)
                        name_kanji = slice_by_bytes(line_bytes, 4, 16)

                        # 登録番号が空の場合はスキップ（ヘッダー行などの対策）
                        if not reg_no.isdigit():
                            continue

                        raw_fields = {
                            "reg_no": reg_no,
                            "name_kanji": name_kanji,
                            "name_kana": slice_by_bytes(line_bytes, 20, 15),
                            "branch": slice_by_bytes(line_bytes, 35, 4),
                            "racer_class": slice_by_bytes(line_bytes, 39, 2),
                        }

                        raw_records.append(
                            {
                                "download_file_id": target.id,
                                "raw_file_id": extracted_raw_file.id,
                                "line_number": line_num,
                                "raw_text": line.strip(),
                                "raw_fields": raw_fields,
                                "parse_status": "success",
                                "parser_version": "v1.0",
                            }
                        )

                        stat_records.append(
                            {
                                "download_file_id": target.id,
                                "period_year": target.period_year,
                                "period_term": target.period_term,
                                "racer_registration_no": reg_no,
                                "racer_name": name_kanji,
                                "branch": raw_fields["branch"],
                                "racer_class": raw_fields["racer_class"],
                                "raw_values": raw_fields,
                                "normalized_values": {},
                            }
                        )

                if raw_records:
                    session.execute(insert(RacerPeriodStatRaw).values(raw_records))

                if stat_records:
                    stmt = insert(RacerPeriodStat).values(stat_records)
                    stmt = stmt.on_conflict_do_update(
                        index_elements=["period_year", "period_term", "racer_registration_no"],
                        set_={
                            "racer_name": stmt.excluded.racer_name,
                            "branch": stmt.excluded.branch,
                            "racer_class": stmt.excluded.racer_class,
                            "raw_values": stmt.excluded.raw_values,
                            "updated_at": func.now(),
                        },
                    )
                    session.execute(stmt)

                # ステータス更新
                target.raw_lzh_file_id = raw_file.id
                target.extracted_file_id = extracted_raw_file.id
                target.status = "completed"
                session.commit()

                print(f"✅ 完了: {len(stat_records)} 件のデータを保存しました。")

                # サーバーに負荷をかけないよう1秒待機
                time.sleep(1)

            except Exception as e:
                print(f"❌ エラー発生 ({target.source_filename}): {e}")
                session.rollback()
                target.status = "failed"
                target.error_message = str(e)
                session.commit()
                break  # エラーが起きたら一旦ループを抜ける


if __name__ == "__main__":
    main()
