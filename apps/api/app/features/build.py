from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.labels import fetch_label_records, generate_labels_df
from app.features.leakage import validate_no_leakage
from app.models.odds import OddsSnapshotEntry
from app.models.pre_race_info import PreRaceEntryInfo, WeatherObservation
from app.models.race_cards import RaceEntry
from app.models.race_master import Race
from app.models.racer_period_stats import RacerPeriodStat


def fetch_base_features(
    session: Session, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> pd.DataFrame:
    query = select(
        Race.race_id,
        Race.race_date,
        Race.venue_code,
        Race.race_no,
        Race.grade,
        RaceEntry.boat_no,
        RaceEntry.racer_registration_no,
        RaceEntry.racer_class,
        RaceEntry.branch,
        RaceEntry.motor_no,
        RaceEntry.boat_no_assigned.label("boat_item_no"),
    ).join(RaceEntry, Race.race_id == RaceEntry.race_id)

    if from_date:
        query = query.where(Race.race_date >= from_date)
    if to_date:
        query = query.where(Race.race_date <= to_date)

    results = session.execute(query).fetchall()

    if not results:
        return pd.DataFrame()

    df = pd.DataFrame([dict(row._mapping) for row in results])

    if "motor_no" in df.columns:
        df["motor_no"] = pd.to_numeric(df["motor_no"], errors="coerce")
    if "boat_item_no" in df.columns:
        df["boat_item_no"] = pd.to_numeric(df["boat_item_no"], errors="coerce")

    return df


def add_racer_period_stats(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    """
    対象レース時点において「過去最も新しい」レーサー期別成績を結合する（As-Of Join）。
    """
    if df.empty or "racer_registration_no" not in df.columns:
        return df

    racer_nos = df["racer_registration_no"].dropna().unique().tolist()
    if not racer_nos:
        return df

    query = select(
        RacerPeriodStat.racer_registration_no,
        RacerPeriodStat.period_year,
        RacerPeriodStat.period_term,
        RacerPeriodStat.normalized_values,
        RacerPeriodStat.raw_values,
    ).where(RacerPeriodStat.racer_registration_no.in_(racer_nos))

    results = session.execute(query).fetchall()

    stats_data = []
    for r in results:
        nv = r.normalized_values or {}
        rv = r.raw_values or {}

        # 💡 JSONからの安全な抽出ロジック（0.0対策とキー名揺れ対応）
        def get_rate(keys):
            for k in keys:
                if nv.get(k) is not None:
                    return float(nv.get(k))
                if rv.get(k) is not None:
                    return float(rv.get(k))
            return None

        win_rate = get_rate(["win_rate"])
        top2_rate = get_rate(["two_place_rate", "top2_rate", "quinella_rate"])
        top3_rate = get_rate(["three_place_rate", "top3_rate", "place3_rate"])

        # ボートレースの適用開始日を計算（前期:5/1〜、後期:11/1〜）
        if str(r.period_term) in ("first_half", "前期", "1"):
            applicable_date = pd.Timestamp(year=r.period_year, month=5, day=1)
        else:
            applicable_date = pd.Timestamp(year=r.period_year, month=11, day=1)

        stats_data.append({
            "racer_registration_no": str(r.racer_registration_no),
            "applicable_date": applicable_date,
            "racer_win_rate": win_rate,
            "racer_top2_rate": top2_rate,
            "racer_top3_rate": top3_rate,
        })

    stats_df = pd.DataFrame(stats_data)
    
    if stats_df.empty:
        for col in ["racer_win_rate", "racer_top2_rate", "racer_top3_rate"]:
            df[col] = None
        return df

    # 💡 As-Of結合のための準備（日付でのソート）
    df["race_date_ts"] = pd.to_datetime(df["race_date"])
    df["racer_registration_no"] = df["racer_registration_no"].astype(str)
    
    df = df.sort_values("race_date_ts")
    stats_df = stats_df.sort_values("applicable_date")

    # 🚀 レース日の直前に有効だった成績を自動で結合（未来の成績は絶対に混ざらない！）
    merged_df = pd.merge_asof(
        df,
        stats_df,
        left_on="race_date_ts",
        right_on="applicable_date",
        by="racer_registration_no",
        direction="backward"
    )

    merged_df = merged_df.drop(columns=["race_date_ts", "applicable_date"], errors="ignore")
    return merged_df


def add_pre_race_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "race_id" not in df.columns:
        return df

    race_ids = df["race_id"].dropna().unique().tolist()
    if not race_ids:
        return df

    weather_q = select(WeatherObservation).where(WeatherObservation.race_id.in_(race_ids))
    w_results = session.execute(weather_q).scalars().all()
    if w_results:
        w_df = pd.DataFrame([{
            "race_id": r.race_id,
            "fetched_at": r.fetched_at,
            "weather": r.weather,
            "temperature": float(r.temperature) if r.temperature is not None else None,
            "wind_direction": r.wind_direction,
            "wind_speed": float(r.wind_speed) if r.wind_speed is not None else None,
            "water_temperature": float(r.water_temperature) if r.water_temperature is not None else None,
            "wave_height": float(r.wave_height) if r.wave_height is not None else None,
        } for r in w_results])
        w_df = w_df.sort_values("fetched_at").groupby("race_id").tail(1).drop(columns=["fetched_at"])
        df = pd.merge(df, w_df, on="race_id", how="left")

    pre_q = select(PreRaceEntryInfo).where(PreRaceEntryInfo.race_id.in_(race_ids))
    p_results = session.execute(pre_q).scalars().all()
    if p_results:
        p_df = pd.DataFrame([{
            "race_id": r.race_id,
            "boat_no": r.boat_no,
            "fetched_at": r.fetched_at,
            "exhibition_time": float(r.exhibition_time) if r.exhibition_time is not None else None,
            "tilt_angle": float(r.tilt_angle) if r.tilt_angle is not None else None,
            "start_exhibition_course": r.start_exhibition_course,
            "start_exhibition_timing": float(r.start_exhibition_timing) if r.start_exhibition_timing is not None else None,
        } for r in p_results])
        p_df = p_df.sort_values("fetched_at").groupby(["race_id", "boat_no"]).tail(1).drop(columns=["fetched_at"])
        df = pd.merge(df, p_df, on=["race_id", "boat_no"], how="left")

    return df


def add_odds_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    if df.empty or "race_id" not in df.columns:
        return df

    race_ids = df["race_id"].dropna().unique().tolist()
    if not race_ids:
        return df

    odds_q = select(OddsSnapshotEntry).where(
        OddsSnapshotEntry.race_id.in_(race_ids),
        OddsSnapshotEntry.bet_type == "win"
    )
    o_results = session.execute(odds_q).scalars().all()
    if o_results:
        o_df = pd.DataFrame([{
            "race_id": r.race_id,
            "boat_no": int(r.combination),
            "fetched_at": r.fetched_at,
            "win_odds": float(r.odds_value) if r.odds_value is not None else None,
        } for r in o_results])
        o_df = o_df.sort_values("fetched_at").groupby(["race_id", "boat_no"]).tail(1).drop(columns=["fetched_at"])
        df = pd.merge(df, o_df, on=["race_id", "boat_no"], how="left")

    return df


def build_training_dataset(
    session: Session, 
    from_date: Optional[date] = None, 
    to_date: Optional[date] = None,
    model_view: str = "pre_race_no_odds"
) -> pd.DataFrame:
    features_df = fetch_base_features(session, from_date, to_date)
    if features_df.empty:
        return pd.DataFrame()

    features_df = add_racer_period_stats(session, features_df)

    if model_view in ["exhibition_with_odds"]:
        features_df = add_pre_race_features(session, features_df)
    
    if model_view in ["pre_race_with_odds", "exhibition_with_odds"]:
        features_df = add_odds_features(session, features_df)

    validate_no_leakage(features_df)

    label_records = fetch_label_records(session, from_date, to_date)
    labels_df = generate_labels_df(label_records)

    if not labels_df.empty:
        dataset_df = pd.merge(features_df, labels_df, on=["race_id", "boat_no"], how="inner")
    else:
        dataset_df = pd.DataFrame()

    return dataset_df