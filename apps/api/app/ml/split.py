from dataclasses import dataclass

import pandas as pd


class SplitValidationError(ValueError):
    """Raised when a dataset cannot be split safely by race date."""


@dataclass(frozen=True)
class TimeSplit:
    train: pd.DataFrame
    valid: pd.DataFrame
    test: pd.DataFrame


def _validate_split(name: str, df: pd.DataFrame, min_races: int) -> None:
    race_count = df["race_id"].nunique()
    if race_count < min_races:
        raise SplitValidationError(
            f"{name} split has {race_count} races; at least {min_races} are required"
        )


def split_by_race_date(
    df: pd.DataFrame,
    train_ratio: float = 0.6,
    valid_ratio: float = 0.2,
    min_races: int = 1,
) -> TimeSplit:
    required = {"race_id", "race_date"}
    missing = sorted(required - set(df.columns))
    if missing:
        raise SplitValidationError(f"Split columns are missing: {missing}")
    if not 0 < train_ratio < 1 or not 0 < valid_ratio < 1:
        raise SplitValidationError("train_ratio and valid_ratio must be between 0 and 1")
    if train_ratio + valid_ratio >= 1:
        raise SplitValidationError("train_ratio + valid_ratio must be less than 1")
    if min_races < 1:
        raise SplitValidationError("min_races must be at least 1")

    working = df.copy()
    working["race_date"] = pd.to_datetime(working["race_date"], errors="raise").dt.normalize()
    race_date_counts = working.groupby("race_id")["race_date"].nunique()
    if (race_date_counts > 1).any():
        invalid_ids = race_date_counts[race_date_counts > 1].index.tolist()
        raise SplitValidationError(f"race_id maps to multiple race dates: {invalid_ids}")

    dates = sorted(working["race_date"].drop_duplicates().tolist())
    if len(dates) < 3:
        raise SplitValidationError(
            f"At least 3 distinct race dates are required; found {len(dates)}"
        )

    train_date_count = max(1, int(len(dates) * train_ratio))
    valid_date_count = max(1, int(len(dates) * valid_ratio))
    if train_date_count + valid_date_count >= len(dates):
        valid_date_count = 1
        train_date_count = len(dates) - 2

    train_dates = set(dates[:train_date_count])
    valid_dates = set(dates[train_date_count : train_date_count + valid_date_count])
    test_dates = set(dates[train_date_count + valid_date_count :])

    split = TimeSplit(
        train=working.loc[working["race_date"].isin(train_dates)].reset_index(drop=True),
        valid=working.loc[working["race_date"].isin(valid_dates)].reset_index(drop=True),
        test=working.loc[working["race_date"].isin(test_dates)].reset_index(drop=True),
    )
    _validate_split("train", split.train, min_races)
    _validate_split("valid", split.valid, min_races)
    _validate_split("test", split.test, min_races)

    race_sets = [
        set(split.train["race_id"]),
        set(split.valid["race_id"]),
        set(split.test["race_id"]),
    ]
    if race_sets[0] & race_sets[1] or race_sets[0] & race_sets[2] or race_sets[1] & race_sets[2]:
        raise SplitValidationError("The same race_id appears in multiple splits")
    return split
