import os
import json

def slice_by_bytes(line_bytes: bytes, start: int, length: int) -> str:
    """バイト列から指定範囲を切り出し、文字列に戻して空白を取り除く"""
    try:
        # 指定されたバイト範囲を切り出し、CP932でデコード
        sliced = line_bytes[start:start+length]
        return sliced.decode("cp932").strip()
    except Exception:
        return ""

def main():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../"))
    txt_file_path = os.path.join(base_dir, "data/raw/extracted/racer_period_stats/2025/first_half/fan2510.txt")

    if not os.path.exists(txt_file_path):
        print(f"❌ ファイルが見つかりません: {txt_file_path}")
        return

    parsed_data = []

    print("⚙️ データのパースを開始します...")
    with open(txt_file_path, "r", encoding="cp932") as f:
        for i in range(10):  # まずはテストとして最初の10行だけ
            line = f.readline()
            if not line:
                break
            
            # 1行をCP932のバイト列に変換
            line_bytes = line.encode("cp932")
            
            # バイト位置を指定して切り出し
            racer_info = {
                "reg_no": slice_by_bytes(line_bytes, 0, 4),        # 登録番号 (4byte)
                "name_kanji": slice_by_bytes(line_bytes, 4, 16),   # 漢字名前 (16byte)
                "name_kana": slice_by_bytes(line_bytes, 20, 15),   # カナ名前 (15byte)
                "branch": slice_by_bytes(line_bytes, 35, 4),       # 支部 (4byte)
                "racer_class": slice_by_bytes(line_bytes, 39, 2),  # 階級 (2byte)
            }
            parsed_data.append(racer_info)

    # 結果をきれいにJSON形式で出力
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()