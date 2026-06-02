from datetime import date, datetime, timezone

from app.ingestion.live.parse import (
    parse_live_active_venues,
    parse_live_beforeinfo_html,
    parse_live_odds_tf_html,
    parse_live_race_card_html,
)


def test_parse_live_active_venues_extracts_unique_codes() -> None:
    html = """
    <a href="/owpc/pc/race/racelist?rno=1&jcd=01&hd=20260601">venue 01</a>
    <a href="/owpc/pc/race/racelist?rno=1&jcd=23&hd=20260601">venue 23</a>
    <a href="/owpc/pc/race/racelist?rno=2&jcd=23&hd=20260601">venue 23 again</a>
    """

    assert parse_live_active_venues(html) == ["01", "23"]


def test_parse_live_race_card_extracts_entries() -> None:
    tbody = """
    <tbody class="is-fs12">
      <tr>
        <td><div class="is-fs18 is-fBold">郷原 章平</div></td>
        <td><div class="is-fs11">4193 / A1</div><div class="is-fs11">福岡 / 福岡 30歳</div></td>
        <td></td><td></td><td></td><td></td>
        <td>11|35.0</td>
        <td>22|40.0</td>
      </tr>
    </tbody>
    """
    html = f"<table class='table1'>{tbody * 6}</table>"

    race_records, entry_records = parse_live_race_card_html(html, date(2026, 6, 1), "23", 1)

    assert race_records == [
        {
            "race_id": "20260601_23_01",
            "race_date": date(2026, 6, 1),
            "venue_code": "23",
            "race_no": 1,
        }
    ]
    assert len(entry_records) == 6
    assert entry_records[0]["boat_no"] == 1
    assert entry_records[0]["racer_registration_no"] == "4193"
    assert entry_records[0]["racer_name"] == "郷原章平"
    assert entry_records[0]["racer_class"] == "A1"
    assert entry_records[0]["branch"] == "福岡"
    assert entry_records[0]["motor_no"] == "11"
    assert entry_records[0]["boat_no_assigned"] == "22"


def test_parse_live_beforeinfo_with_exhibition_alignment() -> None:
    html = """
    <div class="weather1_bodyUnit">気温<span class="weather1_bodyUnitLabelData">26.0℃</span></div>
    <div class="weather1_bodyUnit">風速<span class="weather1_bodyUnitLabelData">2m</span><p class="is-wind3"></p></div>
    <div class="weather1_bodyUnit">水温<span class="weather1_bodyUnitLabelData">24.0℃</span></div>
    <div class="weather1_bodyUnit">波高<span class="weather1_bodyUnitLabelData">3cm</span></div>
    <table class="table1">
      <tbody class="is-fs12"><tr><td>6.60</td><td>-0.5</td><td>リング</td></tr></tbody>
      <tbody class="is-fs12"><tr><td>6.65</td><td>0.0</td><td></td></tr></tbody>
    </table>
    <table class="is-w238">
      <tbody>
        <tr><td><span class="table1_boatImage1Number">1</span><span class="table1_boatImage1Time">.03</span></td></tr>
        <tr><td><span class="table1_boatImage1Number">2</span><span class="table1_boatImage1Time">F.01</span></td></tr>
      </tbody>
    </table>
    """

    records = parse_live_beforeinfo_html(html, date(2026, 6, 1), "01", 1)

    assert len(records) == 2
    assert records[0]["race_id"] == "20260601_01_01"
    assert records[0]["boat_no"] == 1
    assert records[0]["exhibition_time"] == 6.60
    assert records[0]["tilt_angle"] == -0.5
    assert records[0]["start_exhibition_course"] == 1
    assert records[0]["start_exhibition_timing"] == 0.03
    assert records[0]["temperature"] == 26.0
    assert records[0]["wind_direction"] == "is-wind3"

    assert records[1]["boat_no"] == 2
    assert records[1]["start_exhibition_timing"] == -0.01


def test_parse_live_odds_with_scratched_boat() -> None:
    html = """
    <tbody>
      <tr><td>1</td><td>選手A</td><td>2.5</td></tr>
      <tr><td>2</td><td>選手B</td><td>欠場</td></tr>
      <tr><td>3</td><td>選手C</td><td>---</td></tr>
      <tr><td>4</td><td>選手D</td><td>12.3</td></tr>
      <tr><td>5</td><td>選手E</td><td>5.0</td></tr>
      <tr><td>6</td><td>選手F</td><td>8.1</td></tr>
    </tbody>
    """
    fetched_at = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)

    records = parse_live_odds_tf_html(html, date(2026, 6, 1), "01", 1, fetched_at)

    assert len(records) == 6
    assert records[0]["combination"] == "1"
    assert records[0]["odds_value"] == 2.5
    assert records[1]["combination"] == "2"
    assert records[1]["odds_value"] is None
    assert records[1]["raw_values"]["status"] == "欠場"
    assert records[2]["combination"] == "3"
    assert records[2]["odds_value"] is None
    assert records[2]["raw_values"]["status"] == "---"
