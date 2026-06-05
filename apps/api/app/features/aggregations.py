import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.race_master import Race
from app.models.race_results import RaceResult


def get_racer_history_df(session: Session) -> pd.DataFrame:
    query = select(
        Race.race_id,
        Race.race_date,
        Race.race_no,
        RaceResult.racer_registration_no,
        RaceResult.boat_no,
        RaceResult.finish_position,
        RaceResult.entry_course,
        Race.venue_code,
    ).join(Race, Race.race_id == RaceResult.race_id)

    results = session.execute(query).fetchall()
    df = pd.DataFrame([dict(row._mapping) for row in results])
    if df.empty:
        return df

    df["race_date"] = pd.to_datetime(df["race_date"])
    sort_cols = [
        col for col in ("racer_registration_no", "race_date", "race_no", "race_id") if col in df
    ]
    df = df.sort_values(sort_cols)
    return df


def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    sort_cols = [
        col for col in ("racer_registration_no", "race_date", "race_no", "race_id") if col in df
    ]
    result = df.copy().sort_values(sort_cols)
    result["_is_win"] = (result["finish_position"] == 1).astype(int)
    result["_is_top2"] = (result["finish_position"] <= 2).astype(int)
    result["_is_top3"] = (result["finish_position"] <= 3).astype(int)

    metric_sources = {
        "win": "_is_win",
        "top2": "_is_top2",
        "top3": "_is_top3",
    }
    for metric_name, source_col in metric_sources.items():
        for window in (30, 60, 90):
            result[f"recent_{metric_name}_rate_{window}"] = result.groupby("racer_registration_no")[
                source_col
            ].transform(lambda series: series.shift(1).rolling(window=window, min_periods=1).mean())

    if "entry_course" in result.columns:
        for metric_name, source_col in metric_sources.items():
            result[f"course_{metric_name}_rate"] = result.groupby(
                ["racer_registration_no", "entry_course"]
            )[source_col].transform(lambda series: series.shift(1).expanding(min_periods=1).mean())

    if "venue_code" in result.columns:
        for metric_name, source_col in metric_sources.items():
            result[f"venue_{metric_name}_rate"] = result.groupby(
                ["racer_registration_no", "venue_code"]
            )[source_col].transform(lambda series: series.shift(1).expanding(min_periods=1).mean())

    return result.drop(columns=["_is_win", "_is_top2", "_is_top3"])
