import warnings
from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)

from bs4 import BeautifulSoup
from datetime import date, datetime
import re
from app.ingestion.race_id import generate_race_id

def parse_live_race_card_html(html: str, race_date: date, venue_code: str, race_no: int):
    """当日の出走表HTMLから出走艇情報を抽出し、DB用のリストを返す"""
    soup = BeautifulSoup(html, "lxml")
    race_id = generate_race_id(race_date, venue_code, race_no)
    
    race_records = [{
        "race_id": race_id,
        "race_date": race_date,
        "venue_code": str(venue_code).zfill(2),
        "race_no": race_no,
    }]
    
    entry_records = []
    
    # 艇ごとの情報を囲む <tbody> を取得（通常6艇分）
    tbodies = soup.select(".table1 tbody.is-fs12")
    
    for i, tbody in enumerate(tbodies[:6], start=1):
        try:
            # 1. 選手名
            name_elem = tbody.select_one(".is-fs18.is-fBold")
            name = name_elem.get_text(strip=True).replace(" ", "").replace("　", "") if name_elem else None
            
            # 2. 登録番号と級別 (公式サイトでは "<div class='is-fs11'>3811 / A1</div>" のような形で入っていることが多い)
            # 全ての is-fs11 の中から、4桁数字から始まるものを探す
            reg_no = None
            racer_class = None
            for fs11 in tbody.select(".is-fs11"):
                text = fs11.get_text(strip=True)
                match = re.search(r"^(\d{4})\s*/\s*([A-B][1-2])", text)
                if match:
                    reg_no = match.group(1)
                    racer_class = match.group(2)
                    break
            
            entry_records.append({
                "race_id": race_id,
                "boat_no": i,
                "racer_registration_no": reg_no,
                "racer_name": name,
                "racer_class": racer_class,
                # モーター番号や支部などは、Phase3のBファイルデータで補完されるため、ここでは最低限にします
                "raw_values": {},
                "normalized_values": {},
            })
        except Exception as e:
            print(f"⚠️ {i}号艇のパースエラー: {e}")
            
    return race_records, entry_records

def parse_live_beforeinfo_html(html: str, race_date: date, venue_code: str, race_no: int):
    """当日の直前情報（展示・気象）HTMLからデータを抽出し、DB用のリストを返す"""
    soup = BeautifulSoup(html, "lxml")
    race_id = generate_race_id(race_date, venue_code, race_no)
    
    # --- 1. 気象情報の抽出 ---
    weather_info = {
        "weather": None,
        "temperature": None,
        "wind_direction": None,
        "wind_speed": None,
        "water_temperature": None,
        "wave_height": None
    }
    
    try:
        # 公式サイトの気象情報エリア (.weather1_bodyUnit などに分散している)
        weather_units = soup.select(".weather1_bodyUnit")
        for unit in weather_units:
            text = unit.get_text(strip=True)
            if "天候" in text:
                # <span class="weather1_bodyUnitLabelTitle">天候</span>晴
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val: weather_info["weather"] = val.get_text(strip=True)
            elif "気温" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val: weather_info["temperature"] = float(val.get_text(strip=True).replace("℃", ""))
            elif "風速" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val: weather_info["wind_speed"] = int(val.get_text(strip=True).replace("m", ""))
            elif "水温" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val: weather_info["water_temperature"] = float(val.get_text(strip=True).replace("℃", ""))
            elif "波高" in text:
                val = unit.select_one(".weather1_bodyUnitLabelData")
                if val: weather_info["wave_height"] = int(val.get_text(strip=True).replace("cm", ""))
            
            # 風向は画像（矢印）のクラス名になっていることが多い
            wind_p = unit.select_one("p[class*='is-wind']")
            if wind_p:
                weather_info["wind_direction"] = wind_p.get("class", [""])[-1] # 例: is-wind11
    except Exception as e:
        print(f"⚠️ 気象情報のパースエラー: {e}")

    # --- 2. 展示タイム・チルト情報の抽出 ---
    records = []
    # 直前情報のテーブル（<tbody>が各艇に対応）
    tbodies = soup.select(".table1 tbody.is-fs12")
    
    for i, tbody in enumerate(tbodies[:6], start=1):
        try:
            # 公式サイトの構造上、チルトや展示タイムは特定の <td> に入っている
            tds = tbody.find_all("td")
            
            tilt = None
            ex_time = None
            
            # チルトは通常4番目か5番目のセル
            for td in tds:
                text = td.get_text(strip=True)
                # "-0.5" や "0.0" などの数値を抽出
                if re.match(r"^-?\d+\.\d+$", text):
                    if tilt is None:
                        tilt = float(text)
                    else:
                        # 2つ目の小数点数値は展示タイムであることが多い
                        ex_time = float(text)
                        break

            records.append({
                "race_id": race_id,
                "boat_no": i,
                "tilt_angle": tilt,
                "exhibition_time": ex_time,
                "start_exhibition_course": None, # スタート展示は少し構造が複雑なので今回はスキップ
                "start_exhibition_timing": None,
                **weather_info, # 辞書を展開して全艇に同じ気象情報をセット
                "raw_values": {},
            })
        except Exception as e:
            print(f"⚠️ {i}号艇の直前情報パースエラー: {e}")

    return records

def parse_live_odds_tf_html(html: str, race_date: date, venue_code: str, race_no: int, fetched_at: datetime):
    """当日の単勝・複勝オッズ(oddstf) HTMLから単勝オッズを抽出し、DB用のリストを返す"""
    soup = BeautifulSoup(html, "lxml")
    race_id = generate_race_id(race_date, venue_code, race_no)
    records = []
    
    try:
        # 強力な目印である「class='oddsPoint'」が付いたtdタグを全探索
        odds_elements = soup.select("td.oddsPoint")
        odds_dict = {}
        
        for elem in odds_elements:
            # そのセルの親である行(tr)を取得
            row = elem.find_parent("tr")
            if not row:
                continue
                
            tds = row.find_all("td")
            if len(tds) >= 3:
                # 1つ目のセルから艇番を取得
                boat_text = tds[0].get_text(strip=True)
                
                if boat_text.isdigit() and 1 <= int(boat_text) <= 6:
                    boat_no = int(boat_text)
                    
                    # 複勝テーブルなどによる重複登録を防ぐ
                    if boat_no in odds_dict:
                        continue
                        
                    # oddsPointのテキスト（オッズの値）を取得
                    odds_text = elem.get_text(strip=True)
                    if odds_text and odds_text != "欠場":
                        try:
                            odds_val = float(odds_text)
                            odds_dict[boat_no] = {
                                "race_id": race_id,
                                "bet_type": "win", # 単勝
                                "combination": str(boat_no),
                                "odds_value": odds_val,
                                "fetched_at": fetched_at,
                                "raw_values": {},
                            }
                        except ValueError:
                            pass
            
            # 1〜6号艇の単勝オッズが揃ったら、(複勝テーブルに進む前に)ループを抜ける
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
    
    # 開催中の場へのリンク（例: /owpc/pc/race/racelist?jcd=23&hd=20260601）を全探索
    links = soup.find_all("a", href=re.compile(r"jcd=\d+"))
    
    for link in links:
        href = link.get("href", "")
        match = re.search(r"jcd=(\d+)", href)
        if match:
            # 場コード（"01"〜"24"）をセットに追加して重複排除
            venues.add(match.group(1).zfill(2))
            
    return sorted(list(venues))