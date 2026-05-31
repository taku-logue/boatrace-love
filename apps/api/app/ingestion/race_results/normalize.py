from typing import Any


def normalize_race_result_fields(raw_fields: dict[str, str]) -> dict[str, Any]:
    """競走成績のパース結果を型変換し、欠場・失格などのステータスを判定する"""
    norm: dict[str, Any] = {}

    def to_float(val: str) -> float | None:
        try:
            return float(val.strip())
        except ValueError:
            return None

    def to_int(val: str) -> int | None:
        try:
            return int(val.strip())
        except ValueError:
            return None

    name = raw_fields.get("racer_name", "")
    norm["racer_name"] = name.replace(" ", "").replace("　", "")

    # 着順と異常ステータスの判定
    pos_str = raw_fields.get("finish_position", "").strip()
    if pos_str.isdigit():
        norm["finish_position"] = int(pos_str)
        norm["result_status"] = "normal"
    elif "F" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "f"
    elif "L" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "l"
    elif "失" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "disqualified"
    elif "欠" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "absent"
    elif "落" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "fall"
    elif "転" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "capsize"
    elif "沈" in pos_str:
        norm["finish_position"] = None
        norm["result_status"] = "sink"
    else:
        norm["finish_position"] = None
        norm["result_status"] = "unknown"

    norm["entry_course"] = to_int(raw_fields.get("entry_course", ""))
    norm["exhibition_time"] = to_float(raw_fields.get("exhibition_time", ""))

    # スタートタイミング (Fの場合はマイナス値として扱う)
    st_str = raw_fields.get("start_timing", "").strip()
    if "F" in st_str or "f" in st_str:
        st_val = to_float(st_str.replace("F", "").replace("f", ""))
        norm["start_timing"] = -st_val if st_val is not None else None
    else:
        norm["start_timing"] = to_float(st_str)

    return norm
