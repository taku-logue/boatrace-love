from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Literal

RaceFileKind = Literal["race_cards", "race_results"]

OFFICIAL_DATA_BASE_URL = "https://www1.mbrace.or.jp/od2"


@dataclass(frozen=True)
class RaceDownloadTarget:
    data_type: RaceFileKind
    race_date: date
    source_url: str
    source_filename: str
    display_name: str
    official_directory: str

    @property
    def period_year(self) -> int:
        return self.race_date.year

    @property
    def period_term(self) -> str:
        return self.race_date.isoformat()

    @property
    def yyyymm(self) -> str:
        return f"{self.race_date.year}{self.race_date.month:02d}"

    @property
    def expected_text_filename(self) -> str:
        return f"{self.source_filename.removesuffix('.lzh').upper()}.TXT"


def iter_dates(start_date: date, end_date: date) -> list[date]:
    if start_date > end_date:
        raise ValueError("start_date must be earlier than or equal to end_date")

    days = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(days + 1)]


def build_race_download_target(data_type: RaceFileKind, race_date: date) -> RaceDownloadTarget:
    yy = str(race_date.year)[-2:]
    mm = f"{race_date.month:02d}"
    dd = f"{race_date.day:02d}"
    yyyymm = f"{race_date.year}{mm}"

    if data_type == "race_cards":
        official_directory = "B"
        prefix = "b"
        display_label = "Race cards"
    elif data_type == "race_results":
        official_directory = "K"
        prefix = "k"
        display_label = "Race results"
    else:
        raise ValueError(f"Unsupported race file kind: {data_type}")

    source_filename = f"{prefix}{yy}{mm}{dd}.lzh"
    source_url = f"{OFFICIAL_DATA_BASE_URL}/{official_directory}/{yyyymm}/{source_filename}"
    return RaceDownloadTarget(
        data_type=data_type,
        race_date=race_date,
        source_url=source_url,
        source_filename=source_filename,
        display_name=f"{display_label} {race_date.isoformat()}",
        official_directory=official_directory,
    )


def lzh_storage_path(data_root: Path, target: RaceDownloadTarget) -> Path:
    return (
        data_root
        / "raw"
        / "official_downloads"
        / target.data_type
        / target.yyyymm
        / target.source_filename
    )


def extracted_storage_path(data_root: Path, target: RaceDownloadTarget) -> Path:
    return (
        data_root
        / "raw"
        / "extracted"
        / target.data_type
        / target.yyyymm
        / target.expected_text_filename
    )


def path_for_raw_file_record(path: Path, data_root: Path) -> str:
    try:
        return str(path.relative_to(data_root.parent))
    except ValueError:
        return str(path)


def filter_records_by_venue(
    race_records: list[dict[str, Any]],
    dependent_records: list[dict[str, Any]],
    venue_code: str | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if venue_code is None:
        return race_records, dependent_records

    race_ids = {
        str(record["race_id"])
        for record in race_records
        if str(record.get("venue_code")) == venue_code
    }
    return (
        [record for record in race_records if str(record["race_id"]) in race_ids],
        [record for record in dependent_records if str(record.get("race_id")) in race_ids],
    )
