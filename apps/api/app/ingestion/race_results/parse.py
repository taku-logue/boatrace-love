import re
from datetime import date
from typing import Any

from app.ingestion.race_id import generate_race_id

from .layouts import RACE_RESULT_LAYOUT_V1
from .normalize import normalize_race_result_fields

PAYOUT_LABEL_TO_BET_TYPE = {
    "単勝": "win",
    "複勝": "place",
    "２連単": "exacta",
    "2連単": "exacta",
    "２連複": "quinella",
    "2連複": "quinella",
    "拡連複": "quinella_place",
    "３連単": "trifecta",
    "3連単": "trifecta",
    "３連複": "trio",
    "3連複": "trio",
}
PAYOUT_DETAIL_PATTERN = re.compile(r"([1-6](?:-[1-6]){0,2})\s+(\d+)(?:\s+人気\s+(\d+))?")


def parse_race_result_line(line: str) -> dict[str, str]:
    """競走成績の1行をレイアウト定義に従ってパースする"""
    parsed = {}
    for key, (start, length) in RACE_RESULT_LAYOUT_V1.items():
        if len(line) >= start:
            parsed[key] = line[start : start + length].strip()
        else:
            parsed[key] = ""
    return parsed


def build_payout_record(
    *,
    race_id: str,
    bet_type: str,
    combination: str,
    payout_yen: int,
    popularity: int | None = None,
    source_label: str | None = None,
) -> dict[str, Any]:
    return {
        "race_id": race_id,
        "bet_type": bet_type,
        "combination": combination,
        "payout_yen": payout_yen,
        "popularity": popularity,
        "raw_values": {"source_label": source_label} if source_label else None,
    }


def parse_payout_detail_records(
    *,
    race_id: str,
    bet_type: str,
    source_label: str,
    detail_text: str,
) -> list[dict[str, Any]]:
    records = []
    for match in PAYOUT_DETAIL_PATTERN.finditer(detail_text):
        popularity = int(match.group(3)) if match.group(3) else None
        records.append(
            build_payout_record(
                race_id=race_id,
                bet_type=bet_type,
                combination=match.group(1),
                payout_yen=int(match.group(2)),
                popularity=popularity,
                source_label=source_label,
            )
        )
    return records


def deduplicate_payout_records(
    payout_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    deduped: dict[tuple[str, str, str], dict[str, Any]] = {}
    for record in payout_records:
        key = (
            str(record["race_id"]),
            str(record["bet_type"]),
            str(record["combination"]),
        )
        deduped[key] = record
    return list(deduped.values())


def parse_race_result_file(
    filepath: str, download_file_id: int, raw_file_id: int, race_date: date
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """競走成績ファイル全体を読み込み、DB保存用のレコードリストを生成する"""
    raw_records, result_records, payout_records = [], [], []
    race_records_dict = {}
    current_venue, current_race_no, current_decision = None, None, None
    current_payout_context: str | None = None

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
                        build_payout_record(
                            race_id=race_id,
                            bet_type="trifecta",
                            combination=summary_match.group(2),
                            payout_yen=int(summary_match.group(3)),
                            source_label="summary",
                        ),
                        build_payout_record(
                            race_id=race_id,
                            bet_type="trio",
                            combination=summary_match.group(4),
                            payout_yen=int(summary_match.group(5)),
                            source_label="summary",
                        ),
                        build_payout_record(
                            race_id=race_id,
                            bet_type="exacta",
                            combination=summary_match.group(6),
                            payout_yen=int(summary_match.group(7)),
                            source_label="summary",
                        ),
                        build_payout_record(
                            race_id=race_id,
                            bet_type="quinella",
                            combination=summary_match.group(8),
                            payout_yen=int(summary_match.group(9)),
                            source_label="summary",
                        ),
                    ]
                )
                current_payout_context = None
                continue

            # 3. レース番号の検出
            line_half = raw_text.translate(str.maketrans("０１２３４５６７８９Ｒ", "0123456789R"))
            race_match = re.search(r"^\s*([0-9]{1,2})R", line_half)
            if race_match and current_venue:
                current_race_no = int(race_match.group(1))
                current_decision = None
                current_payout_context = None
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

            # 5. 払戻詳細の検出 (単勝、複勝、2連単、2連複、拡連複、3連単、3連複)
            payout_match = re.search(
                r"(単勝|複勝|２連単|2連単|２連複|2連複|拡連複|３連単|3連単|３連複|3連複)\s+(.+)$",
                raw_text,
            )
            if payout_match and current_venue and current_race_no:
                race_id = generate_race_id(race_date, current_venue, current_race_no)
                label = payout_match.group(1)
                bet_type = PAYOUT_LABEL_TO_BET_TYPE[label]
                payout_records.extend(
                    parse_payout_detail_records(
                        race_id=race_id,
                        bet_type=bet_type,
                        source_label=label,
                        detail_text=payout_match.group(2),
                    )
                )
                current_payout_context = bet_type
                continue

            # 6. 拡連複は後続2行にラベルなしで続く
            if current_payout_context == "quinella_place" and current_venue and current_race_no:
                race_id = generate_race_id(race_date, current_venue, current_race_no)
                continuation_records = parse_payout_detail_records(
                    race_id=race_id,
                    bet_type=current_payout_context,
                    source_label="拡連複",
                    detail_text=raw_text,
                )
                if continuation_records:
                    payout_records.extend(continuation_records)
                    continue
                current_payout_context = None

            # 7. 払戻詳細以外の行へ進んだら払戻コンテキストを閉じる
            if current_payout_context and not PAYOUT_DETAIL_PATTERN.search(raw_text):
                current_payout_context = None

            # 8. 競走結果データの検出
            if current_venue and current_race_no and len(raw_text) > 12:
                current_payout_context = None
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

    return (
        list(race_records_dict.values()),
        raw_records,
        result_records,
        deduplicate_payout_records(payout_records),
    )
