import re
import warnings
from datetime import date, datetime
from typing import Any

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

from app.ingestion.race_id import generate_race_id

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


def parse_live_race_card_html(
    html: str, race_date: date, venue_code: str, race_no: int
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    """当日の出走表HTMLから出走艇情報を抽出し、DB用のリストを返す"""
    soup = BeautifulSoup(html, "lxml")
    race_id = generate_race_id(race_date, venue_code, race_no)

    race_records = [
        {
            "race_id": race_id,
            "race_date": race_date,
            "venue_code": str(venue_code).zfill(2),
            "race_no": race_no,
        }
    ]

    entry_records: list[dict[str, Any]] = []
    tbodies = soup.select(".table1 tbody.is-fs12")

    for i, tbody in enumerate(tbodies[:6], start=1):
        try:
            name_elem = tbody.select_one(".is-fs18.is-fBold")
            name: str | None = (
                name_elem.get_text(strip=True).replace(" ", "").replace("　", "")
                if name_elem
                else None
            )

            reg_no: str | None = None
            racer_class: str | None = None
            branch: str | None = None

            for fs11 in tbody.select(".is-fs11"):
                text = fs11.get_text(strip=True)
                match = re.search(r"^(\d{4})\s*/\s*([A-B][1-2])", text)
                if match:
                    reg_no = match.group(1)
                    racer_class = match.group(2)

                branch_match = re.search(r"([一-龠]+)\s*/\s*[一-龠]+\s*\d+歳", text)
                if branch_match:
                    branch = branch_match.group(1)

            motor_no: str | None = None
            boat_no_assigned: str | None = None
            top_tds = tbody.select("tr > td")
            if len(top_tds) > 7:
                motor_text = top_tds[6].get_text(separator="|", strip=True)
                if motor_text:
                    m_str = motor_text.split("|")[0]
                    if m_str.isdigit():
                        motor_no = m_str

                boat_text = top_tds[7].get_text(separator="|", strip=True)
                if boat_text:
                    b_str = boat_text.split("|")[0]
                    if b_str.isdigit():
                        boat_no_assigned = b_str

            entry_records.append(
                {
                    "race_id": race_id,
                    "boat_no": i,
                    "racer_registration_no": reg_no,
                    "racer_name": name,
                    "racer_class": racer_class,
                    "branch": branch,
                    "motor_no": motor_no,
                    "boat_no_assigned": boat_no_assigned,
                    "raw_values": {},
                    "normalized_values": {},
                }
            )
        except Exception as e:
            print(f"⚠️ {i}号艇のパースエラー: {e}")

    return race_records, entry_records


def parse_live_beforeinfo_html(
    html: str, race_date: date, venue_code: str, race_no: int
) -> list[dict[str, Any]]:
    """当日の直前情報（展示・気象・本物のスタート展示進入・部品交換）HTMLからデータを抽出する"""
    soup = BeautifulSoup(html, "lxml")
    race_id = generate_race_id(race_date, venue_code, race_no)

    ex_alignment: dict[int, tuple[int, str]] = {}
    ex_table = soup.select_one("table.is-w238")
    if ex_table:
        ex_rows = ex_table.select("tbody tr")
        for idx, row in enumerate(ex_rows):
            course_no = idx + 1
            num_elem = row.select_one(".table1_boatImage1Number")
            time_elem = row.select_one(".table1_boatImage1Time")
            if num_elem and time_elem:
                try:
                    b_no = int(num_elem.get_text(strip=True))
                    st_txt = time_elem.get_text(strip=True)
                    ex_alignment[b_no] = (course_no, st_txt)
                except ValueError:
                    pass

    weather_info: dict[str, Any] = {
        "weather": None,
        "temperature": None,
        "wind_direction": None,
        "wind_speed": None,
        "water_temperature": None,
        "wave_height": None,
    }

    try:
        weather_units = soup.select(".weather1_bodyUnit")
        for unit in weather_units:
            text = unit.get_text(strip=True)
            if "天候" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val:
                    weather_info["weather"] = val.get_text(strip=True)
            elif "気温" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val:
                    weather_info["temperature"] = float(val.get_text(strip=True).replace("℃", ""))
            elif "風速" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val:
                    weather_info["wind_speed"] = int(val.get_text(strip=True).replace("m", ""))
            elif "水温" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val:
                    weather_info["water_temperature"] = float(
                        val.get_text(strip=True).replace("℃", "")
                    )
            elif "波高" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val:
                    weather_info["wave_height"] = int(val.get_text(strip=True).replace("cm", ""))

            wind_p = unit.select_one("p[class*='is-wind']")
            if wind_p:
                classes = wind_p.get("class")
                if isinstance(classes, list) and classes:
                    weather_info["wind_direction"] = str(classes[-1])
                elif isinstance(classes, str):
                    weather_info["wind_direction"] = classes
    except Exception as e:
        print(f"⚠️ 気象情報のパースエラー: {e}")

    records: list[dict[str, Any]] = []
    tbodies = soup.select(".table1 tbody.is-fs12")

    for i, tbody in enumerate(tbodies[:6], start=1):
        try:
            tds = tbody.find_all("td")

            final_tilt: float | None = None
            final_ex_time: float | None = None

            for td in tds:
                td_text = td.get_text(strip=True)
                if re.match(r"^-?\d+\.\d+$", td_text):
                    numeric_val = float(td_text)
                    if numeric_val < 4.0:
                        final_tilt = numeric_val
                    else:
                        final_ex_time = numeric_val

            st_course: int | None = None
            st_timing_float: float | None = None
            raw_st_txt: str | None = None

            if i in ex_alignment:
                st_course, raw_st_txt = ex_alignment[i]
                if raw_st_txt and raw_st_txt != "L":
                    is_flying = "F" in raw_st_txt
                    cleaned_st = raw_st_txt.replace("F", "").strip()
                    if cleaned_st.startswith("."):
                        cleaned_st = "0" + cleaned_st
                    try:
                        st_timing_float = float(cleaned_st)
                        if is_flying:
                            st_timing_float = -st_timing_float
                    except ValueError:
                        pass

            parts_replaced: list[str] = []
            top_tds = tbody.select("tr > td")
            if len(top_tds) > 7:
                parts_text = top_tds[7].get_text(separator="|", strip=True)
                if parts_text:
                    parts_replaced = [p.strip() for p in parts_text.split("|") if p.strip()]

            raw_vals: dict[str, Any] = {}
            if raw_st_txt:
                raw_vals["start_exhibition_timing_raw"] = raw_st_txt
            if parts_replaced:
                raw_vals["parts_replaced"] = parts_replaced

            item = {
                "race_id": race_id,
                "boat_no": i,
                "tilt_angle": final_tilt,
                "exhibition_time": final_ex_time,
                "start_exhibition_course": st_course,
                "start_exhibition_timing": st_timing_float,
                "raw_values": raw_vals,
            }
            item.update(weather_info)
            records.append(item)
        except Exception as e:
            print(f"⚠️ {i}号艇の直前情報パースエラー: {e}")

    return records


def parse_live_odds_tf_html(
    html: str, race_date: date, venue_code: str, race_no: int, fetched_at: datetime
) -> list[dict[str, Any]]:
    """当日の単勝・複勝オッズ(oddstf) HTMLから単勝オッズを抽出する"""
    soup = BeautifulSoup(html, "lxml")
    race_id = generate_race_id(race_date, venue_code, race_no)
    records: list[dict[str, Any]] = []

    try:
        tbodies = soup.select("tbody")
        odds_dict: dict[int, dict[str, Any]] = {}

        for tbody in tbodies:
            rows = tbody.find_all("tr")
            for row in rows:
                tds = row.find_all("td")

                if len(tds) >= 3:
                    boat_text = tds[0].get_text(strip=True)

                    if boat_text.isdigit() and 1 <= int(boat_text) <= 6:
                        boat_no = int(boat_text)

                        if boat_no in odds_dict:
                            continue

                        odds_elem = tds[2]
                        odds_text = odds_elem.get_text(strip=True)

                        if not odds_text or any(
                            x in odds_text for x in ["欠場", "---", "返還", "不成立"]
                        ):
                            odds_dict[boat_no] = {
                                "race_id": race_id,
                                "bet_type": "win",
                                "combination": str(boat_no),
                                "odds_value": None,
                                "fetched_at": fetched_at,
                                "raw_values": {"status": odds_text or "scratched"},
                            }
                            continue

                        try:
                            odds_val = float(odds_text)
                            odds_dict[boat_no] = {
                                "race_id": race_id,
                                "bet_type": "win",
                                "combination": str(boat_no),
                                "odds_value": odds_val,
                                "fetched_at": fetched_at,
                                "raw_values": {},
                            }
                        except ValueError:
                            odds_dict[boat_no] = {
                                "race_id": race_id,
                                "bet_type": "win",
                                "combination": str(boat_no),
                                "odds_value": None,
                                "fetched_at": fetched_at,
                                "raw_values": {"error_raw_text": odds_text},
                            }

            if len(odds_dict) == 6:
                break

        records = list(odds_dict.values())

    except Exception as e:
        print(f"⚠️ オッズのパースエラー: {e}")

    return records


def parse_live_active_venues(html: str) -> list[str]:
    """当日のレース一覧HTMLから、その日開催されている場コード（jcd）のリストを抽出する"""
    soup = BeautifulSoup(html, "lxml")
    venues = set()

    links = soup.find_all("a", href=re.compile(r"jcd=\d+"))

    for link in links:
        href = link.get("href", "")
        if isinstance(href, str):
            match = re.search(r"jcd=(\d+)", href)
            if match:
                venues.add(match.group(1).zfill(2))

    return sorted(list(venues))
