import os
import subprocess
import shutil

class LzhExtractor:
    """7-Zipを使用してLZHファイルを解凍するクラス"""
    
    @staticmethod
    def extract_lzh(lzh_path: str, extract_dir: str) -> list[str]:
        """
        LZHファイルを指定ディレクトリに解凍し、解凍されたファイルのパスリストを返す。
        """
        if not os.path.exists(lzh_path):
            raise FileNotFoundError(f"LZHファイルが見つかりません: {lzh_path}")

        # 解凍先ディレクトリを作成
        os.makedirs(extract_dir, exist_ok=True)

        # 7-Zipコマンドの構築
        # e: 書庫からファイルを抽出 (パス情報を無視して直下に展開)
        # -y: すべての問い合わせに「はい」と答える
        # -o: 出力ディレクトリの指定
        cmd = [
            "7z",
            "e",
            "-y",
            f"-o{extract_dir}",
            lzh_path
        ]

        try:
            # コマンド実行 (エラーがあれば例外を投げる)
            result = subprocess.run(
                cmd, 
                check=True, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True
            )
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"7-Zipの実行に失敗しました。\nSTDOUT: {e.stdout}\nSTDERR: {e.stderr}")

        # 解凍されたファイルのリストを取得
        extracted_files = []
        for root, _, files in os.walk(extract_dir):
            for file in files:
                extracted_files.append(os.path.join(root, file))
                
        if not extracted_files:
            raise RuntimeError("解凍されましたが、ファイルが見つかりませんでした。")
            
        return extracted_files