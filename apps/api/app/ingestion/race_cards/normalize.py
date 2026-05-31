from typing import Any


def normalize_race_card_fields(raw_fields: dict[str, str]) -> dict[str, Any]:
    """番組表のパース結果を型変換・正規化する"""
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

    # 選手名の全角・半角スペースを除去
    name = raw_fields.get("racer_name", "")
    norm["racer_name"] = name.replace(" ", "").replace("　", "")

    # 数値キャスト
    norm["age"] = to_int(raw_fields.get("age", ""))
    norm["weight"] = to_int(raw_fields.get("weight", ""))
    norm["national_win_rate"] = to_float(raw_fields.get("national_win_rate", ""))
    norm["national_2_rate"] = to_float(raw_fields.get("national_2_rate", ""))
    norm["local_win_rate"] = to_float(raw_fields.get("local_win_rate", ""))
    norm["local_2_rate"] = to_float(raw_fields.get("local_2_rate", ""))
    norm["motor_2_rate"] = to_float(raw_fields.get("motor_2_rate", ""))
    norm["boat_2_rate"] = to_float(raw_fields.get("boat_2_rate", ""))

    return norm
