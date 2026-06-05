from datetime import date
from decimal import Decimal
from collections.abc import Sequence
from typing import Any

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.aggregations import add_rolling_features, get_racer_history_df
from app.features.labels import fetch_label_records, generate_labels_df
from app.features.leakage import validate_no_leakage
from app.models.odds import OddsSnapshotEntry
from app.models.pre_race_info import PreRaceEntryInfo, WeatherObservation
from app.models.race_cards import RaceEntry
from app.models.race_master import Race
from app.models.racer_period_stats import RacerPeriodStat

MODEL_VIEWS = {"pre_race_no_odds", "pre_race_with_odds", "exhibition_with_odds"}
HISTORICAL_FEATURE_PREFIXES = ("recent_", "course_", "venue_")


def _rows_to_df(rows: Sequence[Any]) -> pd.DataFrame:
    return pd.DataFrame([dict(row._mapping) for row in rows])


def _to_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _extract_number(mapping: dict[str, Any] | None, keys: tuple[str, ...]) -> float | None:
    if not isinstance(mapping, dict):
        return None
    for key in keys:
        value = mapping.get(key)
        number = _to_float(value)
        if number is not None:
            return number
    return None


def _term_order(term: Any) -> int:
    if term in ("後期", "2", 2, "second"):
        return 2
    if term in ("前期", "1", 1, "first"):
        return 1
    return 0


def _period_available_date(period_year: int | None, period_term: Any) -> date | None:
    if period_year is None:
        return None
    order = _term_order(period_term)
    if order == 1:
        return date(period_year, 5, 1)
    if order == 2:
        return date(period_year, 11, 1)
    return date(period_year, 1, 1)


def fetch_base_features(
    session: Session,
    from_date: date | None = None,
    to_date: date | None = None,
    venue_code: str | None = None,
    race_no: int | None = None,
) -> pd.DataFrame:
    query = (
        select(
            Race.race_id,
            Race.race_date,
            Race.venue_code,
            Race.race_no,
            Race.grade,
            Race.distance_m,
            RaceEntry.boat_no,
            RaceEntry.racer_registration_no,
            RaceEntry.racer_name,
            RaceEntry.racer_class,
            RaceEntry.branch,
            RaceEntry.motor_no,
            RaceEntry.boat_no_assigned,
        )
        .join(RaceEntry, RaceEntry.race_id == Race.race_id)
        .order_by(Race.race_date, Race.venue_code, Race.race_no, RaceEntry.boat_no)
    )

    if from_date is not None:
        query = query.where(Race.race_date >= from_date)
    if to_date is not None:
        query = query.where(Race.race_date <= to_date)
    if venue_code is not None:
        query = query.where(Race.venue_code == venue_code.zfill(2))
    if race_no is not None:
        query = query.where(Race.race_no == race_no)

    df = _rows_to_df(session.execute(query).fetchall())
    if df.empty:
        return df

    df["race_date"] = pd.to_datetime(df["race_date"])
    return df


def add_racer_period_stats(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    racer_ids = [
        str(value)
        for value in sorted(df["racer_registration_no"].dropna().unique().tolist())
        if str(value)
    ]
    if not racer_ids:
        return df

    query = select(
        RacerPeriodStat.period_year,
        RacerPeriodStat.period_term,
        RacerPeriodStat.racer_registration_no,
        RacerPeriodStat.racer_class,
        RacerPeriodStat.branch,
        RacerPeriodStat.raw_values,
        RacerPeriodStat.normalized_values,
    ).where(RacerPeriodStat.racer_registration_no.in_(racer_ids))
    stats_df = _rows_to_df(session.execute(query).fetchall())
    if stats_df.empty:
        return df

    stats_df = stats_df.copy()
    stats_df["period_term_order"] = stats_df["period_term"].map(_term_order)
    stats_df["period_available_date"] = [
        _period_available_date(period_year, period_term)
        for period_year, period_term in zip(
            stats_df["period_year"], stats_df["period_term"], strict=False
        )
    ]
    stats_df["racer_period_class"] = stats_df["racer_class"]
    stats_df["racer_period_branch"] = stats_df["branch"]
    stats_df["racer_win_rate"] = [
        _extract_number(
            normalized_values or raw_values,
            ("racer_win_rate", "win_rate", "national_win_rate", "勝率"),
        )
        for normalized_values, raw_values in zip(
            stats_df["normalized_values"], stats_df["raw_values"], strict=False
        )
    ]
    stats_df["racer_top2_rate"] = [
        _extract_number(
            normalized_values or raw_values,
            ("racer_top2_rate", "top2_rate", "two_win_rate", "2連対率"),
        )
        for normalized_values, raw_values in zip(
            stats_df["normalized_values"], stats_df["raw_values"], strict=False
        )
    ]

    base_df = df.copy()
    base_df["_feature_row_id"] = range(len(base_df))
    base_df["_race_date"] = pd.to_datetime(base_df["race_date"]).dt.date

    merged = base_df.merge(
        stats_df[
            [
                "period_year",
                "period_term",
                "period_term_order",
                "period_available_date",
                "racer_registration_no",
                "racer_period_class",
                "racer_period_branch",
                "racer_win_rate",
                "racer_top2_rate",
            ]
        ],
        on="racer_registration_no",
        how="left",
    )
    merged = merged[
        merged["period_available_date"].isna()
        | (merged["period_available_date"] <= merged["_race_date"])
    ]
    merged = merged.sort_values(
        ["_feature_row_id", "period_available_date", "period_year", "period_term_order"],
        na_position="first",
    )
    selected = merged.drop_duplicates("_feature_row_id", keep="last").sort_values("_feature_row_id")

    if "racer_period_class" in selected.columns:
        selected["racer_class"] = selected["racer_class"].fillna(selected["racer_period_class"])
    if "racer_period_branch" in selected.columns:
        selected["branch"] = selected["branch"].fillna(selected["racer_period_branch"])

    return selected.drop(columns=["_feature_row_id", "_race_date"])


def add_missing_flags(df: pd.DataFrame, model_view: str) -> pd.DataFrame:
    if df.empty:
        return df

    result = df.copy()
    result["is_missing_period_stats"] = result.get(
        "racer_win_rate", pd.Series(index=result.index)
    ).isna()

    if model_view == "exhibition_with_odds":
        result["is_missing_pre_race"] = result.get(
            "exhibition_time", pd.Series(index=result.index)
        ).isna()
        result["is_missing_weather"] = result.get(
            "wind_speed", pd.Series(index=result.index)
        ).isna()
    else:
        result["is_missing_pre_race"] = False
        result["is_missing_weather"] = False

    if model_view in {"pre_race_with_odds", "exhibition_with_odds"}:
        result["is_missing_odds"] = result.get("win_odds", pd.Series(index=result.index)).isna()
    else:
        result["is_missing_odds"] = False

    return result


def add_historical_performance_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    history_df = get_racer_history_df(session)
    if history_df.empty:
        return df

    history_df = add_rolling_features(history_df)
    feature_cols = [
        col for col in history_df.columns if col.startswith(HISTORICAL_FEATURE_PREFIXES)
    ]
    if not feature_cols:
        return df

    key_cols = ["race_id", "boat_no"]
    history_features = history_df[key_cols + feature_cols].drop_duplicates(key_cols, keep="last")
    return df.merge(history_features, on=key_cols, how="left")


def add_pre_race_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    race_ids = sorted(df["race_id"].unique().tolist())
    pre_race_query = select(
        PreRaceEntryInfo.race_id,
        PreRaceEntryInfo.boat_no,
        PreRaceEntryInfo.fetched_at,
        PreRaceEntryInfo.exhibition_time,
        PreRaceEntryInfo.tilt_angle,
        PreRaceEntryInfo.start_exhibition_course,
        PreRaceEntryInfo.start_exhibition_timing,
        PreRaceEntryInfo.raw_values,
    ).where(PreRaceEntryInfo.race_id.in_(race_ids))
    pre_df = _rows_to_df(session.execute(pre_race_query).fetchall())

    result = df.copy()
    if not pre_df.empty:
        pre_df = pre_df.sort_values(["race_id", "boat_no", "fetched_at"]).drop_duplicates(
            ["race_id", "boat_no"], keep="last"
        )
        pre_df["exhibition_time"] = pre_df["exhibition_time"].map(_to_float)
        pre_df["tilt_angle"] = pre_df["tilt_angle"].map(_to_float)
        pre_df["start_exhibition_timing"] = pre_df["start_exhibition_timing"].map(_to_float)
        pre_df["parts_replaced_count"] = pre_df["raw_values"].map(_parts_replaced_count)
        pre_df["has_parts_replaced"] = pre_df["parts_replaced_count"] > 0

        result = result.merge(
            pre_df[
                [
                    "race_id",
                    "boat_no",
                    "exhibition_time",
                    "tilt_angle",
                    "start_exhibition_course",
                    "start_exhibition_timing",
                    "parts_replaced_count",
                    "has_parts_replaced",
                ]
            ],
            on=["race_id", "boat_no"],
            how="left",
        )
        result["exhibition_time_rank"] = result.groupby("race_id")["exhibition_time"].rank(
            method="min", ascending=True
        )
        result["exhibition_time_diff"] = result["exhibition_time"] - result.groupby("race_id")[
            "exhibition_time"
        ].transform("mean")

    weather_query = select(
        WeatherObservation.race_id,
        WeatherObservation.fetched_at,
        WeatherObservation.weather,
        WeatherObservation.temperature,
        WeatherObservation.wind_direction,
        WeatherObservation.wind_speed,
        WeatherObservation.water_temperature,
        WeatherObservation.wave_height,
    ).where(WeatherObservation.race_id.in_(race_ids))
    weather_df = _rows_to_df(session.execute(weather_query).fetchall())
    if weather_df.empty:
        return result

    weather_df = weather_df.sort_values(["race_id", "fetched_at"]).drop_duplicates(
        ["race_id"], keep="last"
    )
    for col in ("temperature", "wind_speed", "water_temperature", "wave_height"):
        weather_df[col] = weather_df[col].map(_to_float)

    return result.merge(
        weather_df[
            [
                "race_id",
                "weather",
                "temperature",
                "wind_direction",
                "wind_speed",
                "water_temperature",
                "wave_height",
            ]
        ],
        on="race_id",
        how="left",
    )


def _parts_replaced_count(raw_values: Any) -> int:
    if not isinstance(raw_values, dict):
        return 0
    parts = raw_values.get("parts_replaced")
    if isinstance(parts, list):
        return len(parts)
    if isinstance(parts, str) and parts:
        return 1
    return 0


def add_odds_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    race_ids = sorted(df["race_id"].unique().tolist())
    query = select(
        OddsSnapshotEntry.race_id,
        OddsSnapshotEntry.fetched_at,
        OddsSnapshotEntry.combination,
        OddsSnapshotEntry.odds_value,
    ).where(
        OddsSnapshotEntry.race_id.in_(race_ids),
        OddsSnapshotEntry.bet_type == "win",
    )
    odds_df = _rows_to_df(session.execute(query).fetchall())
    if odds_df.empty:
        return df

    odds_df = odds_df.sort_values(["race_id", "fetched_at"])
    latest = odds_df.groupby("race_id")["fetched_at"].transform("max")
    odds_df = odds_df[odds_df["fetched_at"] == latest].copy()
    odds_df["boat_no"] = pd.to_numeric(odds_df["combination"], errors="coerce").astype("Int64")
    odds_df["win_odds"] = odds_df["odds_value"].map(_to_float)
    odds_df["win_popularity"] = odds_df.groupby("race_id")["win_odds"].rank(
        method="min", ascending=True
    )
    odds_df["market_probability"] = odds_df["win_odds"].map(
        lambda odds: None if odds is None or odds <= 0 else 1.0 / odds
    )

    return df.merge(
        odds_df[
            [
                "race_id",
                "boat_no",
                "win_odds",
                "win_popularity",
                "market_probability",
                "fetched_at",
            ]
        ].rename(columns={"fetched_at": "odds_fetched_at"}),
        on=["race_id", "boat_no"],
        how="left",
    )


def build_training_dataset(
    session: Session,
    from_date: date | None = None,
    to_date: date | None = None,
    model_view: str = "pre_race_no_odds",
    venue_code: str | None = None,
    race_no: int | None = None,
) -> pd.DataFrame:
    if model_view not in MODEL_VIEWS:
        raise ValueError(f"Unknown model_view: {model_view}")

    features_df = fetch_base_features(session, from_date, to_date, venue_code, race_no)
    if features_df.empty:
        return features_df

    features_df = add_racer_period_stats(session, features_df)
    features_df = add_historical_performance_features(session, features_df)
    if model_view == "exhibition_with_odds":
        features_df = add_pre_race_features(session, features_df)
    if model_view in {"pre_race_with_odds", "exhibition_with_odds"}:
        features_df = add_odds_features(session, features_df)

    features_df = add_missing_flags(features_df, model_view)
    validate_no_leakage(features_df)

    label_records = fetch_label_records(session, from_date, to_date)
    labels_df = generate_labels_df(label_records)
    if labels_df.empty:
        return labels_df

    return features_df.merge(labels_df, on=["race_id", "boat_no"], how="inner")
