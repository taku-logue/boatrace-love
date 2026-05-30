from .layouts import RACE_CARD_LAYOUT_V1

def parse_race_card_line(line: str) -> dict[str, str]:
    """番組表の1行をレイアウト定義に従ってパースする"""
    parsed = {}
    for key, (start, length) in RACE_CARD_LAYOUT_V1.items():
        if len(line) >= start:
            # デコード済みの文字列に対してスライスを行う
            parsed[key] = line[start:start+length].strip()
        else:
            parsed[key] = ""
    return parsed
    
import re
from datetime import date
from app.ingestion.race_id import generate_race_id
from .normalize import normalize_race_card_fields

def parse_race_card_file(filepath: str, download_file_id: int, raw_file_id: int, race_date: date):
    """番組表ファイル全体を読み込み、DB保存用のレコードリストを生成する"""
    raw_records, entry_records = [], []
    race_records_dict = {} # リストから辞書に変更（重複排除のため）
    current_venue, current_race_no = None, None

    with open(filepath, "r", encoding="cp932", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            raw_text = line.rstrip("\r\n")
            if not raw_text.strip():
                continue

            # 1. 場コードの検出
            venue_match = re.match(r"^([0-9]{2})BBGN", raw_text)
            if venue_match:
                current_venue = venue_match.group(1)
                continue

            # 2. レース番号の検出
            line_half = raw_text.translate(str.maketrans('０１２３４５６７８９Ｒ', '0123456789R'))
            race_match = re.search(r"^\s*([0-9]{1,2})R", line_half)
            if race_match and current_venue:
                current_race_no = int(race_match.group(1))
                race_id = generate_race_id(race_date, current_venue, current_race_no)
                
                # 辞書に格納して重複を上書き排除
                race_records_dict[race_id] = {
                    "race_id": race_id,
                    "race_date": race_date,
                    "venue_code": current_venue,
                    "race_no": current_race_no,
                    "raw_card_file_id": raw_file_id,
                }
                continue

            # 3. 出走艇データの検出
            if current_venue and current_race_no:
                boat_match = re.match(r"^([1-6])\s+[0-9]{4}", raw_text)
                if boat_match:
                    parsed_fields = parse_race_card_line(raw_text)
                    normalized = normalize_race_card_fields(parsed_fields)
                    race_id = generate_race_id(race_date, current_venue, current_race_no)
                    
                    raw_records.append({
                        "download_file_id": download_file_id,
                        "raw_file_id": raw_file_id,
                        "line_number": line_num,
                        "raw_text": raw_text,
                        "raw_fields": parsed_fields,
                        "parse_status": "parsed",
                        "parser_version": "v1.0"
                    })
                    
                    entry_records.append({
                        "race_id": race_id,
                        "boat_no": int(boat_match.group(1)),
                        "racer_registration_no": parsed_fields.get("reg_no"),
                        "racer_name": normalized.get("racer_name"),
                        "racer_class": parsed_fields.get("racer_class"),
                        "branch": parsed_fields.get("branch"),
                        "motor_no": parsed_fields.get("motor_no"),
                        "boat_no_assigned": parsed_fields.get("boat_no_assigned"),
                        "raw_values": parsed_fields,
                        "normalized_values": normalized,
                    })

    # 辞書のValueだけをリスト化して返す
    return list(race_records_dict.values()), raw_records, entry_records