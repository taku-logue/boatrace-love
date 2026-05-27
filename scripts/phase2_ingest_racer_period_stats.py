import os
import sys
import httpx
import hashlib
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../apps/api")))

from app.db.session import engine
from app.models.downloads import DownloadFile
from app.models.management import RawFile
# 先ほど作った解凍クラスをインポート
from app.ingestion.archive import LzhExtractor

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def main():
    print("🚤 LZHファイルのダウンロード＆解凍処理を開始します...")
    with SessionLocal() as session:
        # ダウンロードは終わっているが、解凍がまだ（status == 'downloaded'）のファイルを探す
        # ※先ほどの実行で 'downloaded' になった fan2510.lzh が引っかかります
        target = session.query(DownloadFile).filter(DownloadFile.status == 'downloaded').first()

        if not target:
            print("✅ 解凍待ちのファイルはありません！")
            return

        # 関連するRawFile（LZHの実体）もDBから取得
        lzh_raw_file = session.query(RawFile).filter(RawFile.id == target.raw_lzh_file_id).first()
        if not lzh_raw_file:
            print("❌ LZHファイルのDBレコードが見つかりません。")
            return

        print(f"🎯 対象ファイル: {target.display_name} ({target.source_filename}) [年度: {target.period_year}]")
        
        # -----------------------------------------
        # 1. パスの準備
        # -----------------------------------------
        base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
        
        # LZHファイルの絶対パス
        lzh_absolute_path = os.path.join(base_dir, lzh_raw_file.local_path)
        
        # 解凍先ディレクトリのパス (data/raw/extracted/racer_period_stats/年度/期/)
        extracted_dir = os.path.join(base_dir, "data/raw/extracted/racer_period_stats", str(target.period_year), target.period_term)

        # -----------------------------------------
        # 2. 解凍の実行
        # -----------------------------------------
        print(f"📦 解凍中: {lzh_absolute_path}")
        try:
            extracted_files = LzhExtractor.extract_lzh(lzh_absolute_path, extracted_dir)
        except Exception as e:
            print(f"❌ 解凍失敗: {e}")
            target.status = "failed"
            target.error_message = f"解凍エラー: {str(e)}"
            session.commit()
            return

        # 解凍されたTXTファイル（1つだけのはず）を取得
        txt_file_path = extracted_files[0]
        relative_txt_path = os.path.relpath(txt_file_path, start=base_dir)
        print(f"📄 解凍完了: {relative_txt_path}")

        # -----------------------------------------
        # 3. 解凍したTXTファイルのハッシュ計算
        # -----------------------------------------
        with open(txt_file_path, "rb") as f:
            txt_content = f.read()
        txt_hash = hashlib.sha256(txt_content).hexdigest()

        # -----------------------------------------
        # 4. DBの更新（解凍されたテキストの記録）
        # -----------------------------------------
        extracted_raw_file = RawFile(
            source_id=target.source_id,
            file_type="txt",
            source_url=None, # ダウンロードしたものではないのでNone
            local_path=relative_txt_path,
            sha256=txt_hash,
            file_metadata={"extracted_from_lzh": target.source_filename}
        )
        session.add(extracted_raw_file)
        session.flush()

        # DownloadFileのステータスを「解凍完了」に更新
        target.extracted_file_id = extracted_raw_file.id
        target.status = "extracted"
        
        session.commit()
        print("🎉 DBの更新（解凍完了）が成功しました！")

if __name__ == "__main__":
    main()