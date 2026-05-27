def detect_encoding(file_path: str) -> str:
    """ファイルのエンコーディングを判定する(UTF-8 -> CP932 -> Shift_JISの順)"""
    with open(file_path, "rb") as f:
        # 判定用に先頭データを読み込む
        raw_data = f.read(8192)

    # 1. UTF-8 (BOMあり/なし)
    try:
        raw_data.decode("utf-8-sig")
        return "utf-8"
    except UnicodeDecodeError:
        pass

    # 2. CP932 (Windows標準)
    try:
        raw_data.decode("cp932")
        return "cp932"
    except UnicodeDecodeError:
        pass

    # 3. Shift_JIS (レガシー)
    try:
        raw_data.decode("shift_jis")
        return "shift_jis"
    except UnicodeDecodeError:
        pass

    return "unknown"