import pandas as pd
import pytest

from app.ml.split import SplitValidationError, split_by_race_date


def _frame_for_dates(dates: list[str]) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    for date_index, race_date in enumerate(dates):
        for race_no in (1, 2):
            race_id = f"{race_date.replace('-', '')}01{race_no:02d}"
            for boat_no in range(1, 7):
                rows.append(
                    {
                        "race_id": race_id,
                        "race_date": race_date,
                        "boat_no": boat_no,
                        "target_win": int(boat_no == (date_index % 6) + 1),
                    }
                )
    return pd.DataFrame(rows)


def test_split_by_race_date_keeps_chronology_and_races_together() -> None:
    split = split_by_race_date(_frame_for_dates(["2026-05-28", "2026-05-29", "2026-05-30"]))

    assert split.train["race_date"].dt.strftime("%Y-%m-%d").unique().tolist() == ["2026-05-28"]
    assert split.valid["race_date"].dt.strftime("%Y-%m-%d").unique().tolist() == ["2026-05-29"]
    assert split.test["race_date"].dt.strftime("%Y-%m-%d").unique().tolist() == ["2026-05-30"]
    race_sets = [
        set(split.train["race_id"]),
        set(split.valid["race_id"]),
        set(split.test["race_id"]),
    ]
    assert not race_sets[0] & race_sets[1]
    assert not race_sets[0] & race_sets[2]
    assert not race_sets[1] & race_sets[2]


def test_split_by_race_date_rejects_too_few_dates() -> None:
    with pytest.raises(SplitValidationError, match="At least 3 distinct race dates"):
        split_by_race_date(_frame_for_dates(["2026-05-29", "2026-05-30"]))
