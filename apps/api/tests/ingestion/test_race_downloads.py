from datetime import date
from pathlib import Path

import pytest

from app.ingestion.race_downloads import (
    build_race_download_target,
    extracted_storage_path,
    filter_records_by_venue,
    iter_dates,
    lzh_storage_path,
    path_for_raw_file_record,
)


def test_build_race_card_download_target():
    target = build_race_download_target("race_cards", date(2026, 5, 30))

    assert target.source_url == "https://www1.mbrace.or.jp/od2/B/202605/b260530.lzh"
    assert target.source_filename == "b260530.lzh"
    assert target.expected_text_filename == "B260530.TXT"
    assert target.period_year == 2026
    assert target.period_term == "2026-05-30"


def test_build_race_result_download_target():
    target = build_race_download_target("race_results", date(2026, 5, 30))

    assert target.source_url == "https://www1.mbrace.or.jp/od2/K/202605/k260530.lzh"
    assert target.source_filename == "k260530.lzh"
    assert target.expected_text_filename == "K260530.TXT"


def test_storage_paths_are_categorized_by_data_type_and_month():
    data_root = Path("/workspace/data")
    card_target = build_race_download_target("race_cards", date(2026, 5, 30))
    result_target = build_race_download_target("race_results", date(2026, 5, 30))

    assert lzh_storage_path(data_root, card_target) == Path(
        "/workspace/data/raw/official_downloads/race_cards/202605/b260530.lzh"
    )
    assert extracted_storage_path(data_root, result_target) == Path(
        "/workspace/data/raw/extracted/race_results/202605/K260530.TXT"
    )


def test_iter_dates_includes_start_and_end():
    assert iter_dates(date(2026, 5, 28), date(2026, 5, 30)) == [
        date(2026, 5, 28),
        date(2026, 5, 29),
        date(2026, 5, 30),
    ]


def test_iter_dates_rejects_reverse_range():
    with pytest.raises(ValueError):
        iter_dates(date(2026, 5, 30), date(2026, 5, 28))


def test_filter_records_by_venue_filters_normalized_records_only():
    races = [
        {"race_id": "20260530_01_01", "venue_code": "01"},
        {"race_id": "20260530_02_01", "venue_code": "02"},
    ]
    entries = [
        {"race_id": "20260530_01_01", "boat_no": 1},
        {"race_id": "20260530_02_01", "boat_no": 1},
    ]

    filtered_races, filtered_entries = filter_records_by_venue(races, entries, "02")

    assert filtered_races == [{"race_id": "20260530_02_01", "venue_code": "02"}]
    assert filtered_entries == [{"race_id": "20260530_02_01", "boat_no": 1}]


def test_path_for_raw_file_record_prefers_repo_relative_data_path():
    data_root = Path("/workspace/data")
    path = Path("/workspace/data/raw/extracted/race_cards/202605/B260530.TXT")

    assert path_for_raw_file_record(path, data_root) == (
        "data/raw/extracted/race_cards/202605/B260530.TXT"
    )
