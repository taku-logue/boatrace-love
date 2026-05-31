import re
from datetime import date
from typing import Any

from app.ingestion.race_id import generate_race_id

from .layouts import RACE_RESULT_LAYOUT_V1
from .normalize import normalize_race_result_fields


def parse_race_result_line(line: str) -> dict[str, str]:
    """競走成績の1行をレイアウト定義に従ってパースする"""
    parsed = {}
    for key, (start, length) in RACE_RESULT_LAYOUT_V1.items():
        if len(line) >= start:
            parsed[key] = line[start : start + length].strip()
        else:
            parsed[key] = ""
    return parsed


def parse_race_result_file(
    filepath: str, download_file_id: int, raw_file_id: int, race_date: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """競走成績ファイル全体を読み込み、DB保存用のレコードリストを生成する"""
    raw_records, result_records, payout_records = [], [], []
    race_records_dict = {}
    current_venue, current_race_no, current_decision = None, None, None

    with open(filepath, "r", encoding="cp932", errors="replace") as f:
        for line_num, line in enumerate(f, start=1):
            raw_text = line.rstrip("\r\n")
            if not raw_text.strip():
                continue

            # 1. 場コードの検出
            venue_match = re.match(r"^([0-9]{2})KBGN", raw_text)
            if venue_match:
                current_venue = venue_match.group(1)
                continue

            # 2. 払戻金サマリーの検出 (3連単, 3連複, 2連単, 2連複)
            summary_match = re.search(
                r"^\s*([0-9]{1,2})R\s+([1-6]-[1-6]-[1-6])\s+(\d+)\s+"
                r"([1-6]-[1-6]-[1-6])\s+(\d+)\s+([1-6]-[1-6])\s+(\d+)\s+"
                r"([1-6]-[1-6])\s+(\d+)",
                raw_text,
            )
            if summary_match and current_venue:
                race_no = int(summary_match.group(1))
                race_id = generate_race_id(race_date, current_venue, race_no)
                payout_records.extend(
                    [
                        {
                            "race_id": race_id,
                            "bet_type": "trifecta",
                            "combination": summary_match.group(2),
                            "payout_yen": int(summary_match.group(3)),
                        },
                        {
                            "race_id": race_id,
                            "bet_type": "trio",
                            "combination": summary_match.group(4),
                            "payout_yen": int(summary_match.group(5)),
                        },
                        {
                            "race_id": race_id,
                            "bet_type": "exacta",
                            "combination": summary_match.group(6),
                            "payout_yen": int(summary_match.group(7)),
                        },
                        {
                            "race_id": race_id,
                            "bet_type": "quinella",
                            "combination": summary_match.group(8),
                            "payout_yen": int(summary_match.group(9)),
                        },
                    ]
                )
                continue

            # 3. レース番号の検出
            line_half = raw_text.translate(str.maketrans("０１２３４５６７８９Ｒ", "0123456789R"))
            race_match = re.search(r"^\s*([0-9]{1,2})R", line_half)
            if race_match and current_venue:
                current_race_no = int(race_match.group(1))
                current_decision = None
                race_id = generate_race_id(race_date, current_venue, current_race_no)
                race_records_dict[race_id] = {
                    "race_id": race_id,
                    "race_date": race_date,
                    "venue_code": current_venue,
                    "race_no": current_race_no,
                    "raw_result_file_id": raw_file_id,
                }
                continue

            # 4. 決まり手の検出 (ヘッダー行の右端「ﾚｰｽﾀｲﾑ」の横にある文字を取得)
            header_match = re.search(r"ﾚｰｽﾀｲﾑ\s+(.+)$", raw_text)
            if header_match:
                current_decision = header_match.group(1).strip()
                continue

            # 5. 単勝の検出 (各レース詳細の下部にある)
            tansho_match = re.search(r"単勝\s+([1-6])\s+(\d+)", raw_text)
            if tansho_match and current_venue and current_race_no:
                race_id = generate_race_id(race_date, current_venue, current_race_no)
                payout_records.append(
                    {
                        "race_id": race_id,
                        "bet_type": "win",
                        "combination": tansho_match.group(1),
                        "payout_yen": int(tansho_match.group(2)),
                    }
                )
                continue

            # 6. 競走結果データの検出
            if current_venue and current_race_no and len(raw_text) > 12:
                boat_str = raw_text[6:8].strip()
                reg_str = raw_text[8:12].strip()
                if boat_str.isdigit() and reg_str.isdigit():
                    parsed_fields = parse_race_result_line(raw_text)
                    normalized = normalize_race_result_fields(parsed_fields)
                    race_id = generate_race_id(race_date, current_venue, current_race_no)

                    raw_records.append(
                        {
                            "download_file_id": download_file_id,
                            "raw_file_id": raw_file_id,
                            "line_number": line_num,
                            "raw_text": raw_text,
                            "raw_fields": parsed_fields,
                            "parse_status": "parsed",
                            "parser_version": "v1.1",
                        }
                    )

                    # 1着の艇のみ、ヘッダーから取得した決まり手をセットする
                    is_first = normalized.get("finish_position") == 1

                    result_records.append(
                        {
                            "race_id": race_id,
                            "boat_no": int(boat_str),
                            "racer_registration_no": reg_str,
                            "finish_position": normalized.get("finish_position"),
                            "entry_course": normalized.get("entry_course"),
                            "start_timing": normalized.get("start_timing"),
                            "decision": current_decision if is_first else None,
                            "result_status": normalized.get("result_status"),
                            "raw_values": parsed_fields,
                            "normalized_values": normalized,
                        }
                    )

    return list(race_records_dict.values()), raw_records, result_records, payout_records
