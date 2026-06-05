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
    if df.empty or "racer_registration_no" not in df.columns:
        return df

    race_dates = pd.to_datetime(df["race_date"])
    df["period_year"] = race_dates.dt.year
    df["period_term"] = race_dates.dt.month.apply(lambda m: "前期" if m <= 6 else "後期")

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

        win_rate = nv.get("win_rate") or rv.get("win_rate")
        top2_rate = nv.get("top2_rate") or nv.get("quinella_rate") or rv.get("quinella_rate")
        top3_rate = nv.get("top3_rate") or nv.get("place3_rate") or rv.get("place3_rate")

        stats_data.append(
            {
                "racer_registration_no": r.racer_registration_no,
                "period_year": r.period_year,
                "period_term": r.period_term,
                "racer_win_rate": float(win_rate) if win_rate is not None else None,
                "racer_top2_rate": float(top2_rate) if top2_rate is not None else None,
                "racer_top3_rate": float(top3_rate) if top3_rate is not None else None,
            }
        )

    stats_df = pd.DataFrame(stats_data)

    if not stats_df.empty:
        df = pd.merge(
            df, stats_df, on=["racer_registration_no", "period_year", "period_term"], how="left"
        )
    else:
        for col in ["racer_win_rate", "racer_top2_rate", "racer_top3_rate"]:
            df[col] = None

    return df


def add_pre_race_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    """気象情報と直前情報（展示・チルトなど）を結合する"""
    if df.empty or "race_id" not in df.columns:
        return df

    race_ids = df["race_id"].dropna().unique().tolist()
    if not race_ids:
        return df

    # 1. 気象情報の結合（複数ある場合は fetched_at が最新のものを採用）
    weather_q = select(WeatherObservation).where(WeatherObservation.race_id.in_(race_ids))
    w_results = session.execute(weather_q).scalars().all()
    if w_results:
        w_df = pd.DataFrame(
            [
                {
                    "race_id": r.race_id,
                    "fetched_at": r.fetched_at,
                    "weather": r.weather,
                    "temperature": float(r.temperature) if r.temperature is not None else None,
                    "wind_direction": r.wind_direction,
                    "wind_speed": float(r.wind_speed) if r.wind_speed is not None else None,
                    "water_temperature": float(r.water_temperature)
                    if r.water_temperature is not None
                    else None,
                    "wave_height": float(r.wave_height) if r.wave_height is not None else None,
                }
                for r in w_results
            ]
        )
        w_df = (
            w_df.sort_values("fetched_at").groupby("race_id").tail(1).drop(columns=["fetched_at"])
        )
        df = pd.merge(df, w_df, on="race_id", how="left")

    # 2. 直前情報（展示）の結合
    pre_q = select(PreRaceEntryInfo).where(PreRaceEntryInfo.race_id.in_(race_ids))
    p_results = session.execute(pre_q).scalars().all()
    if p_results:
        p_df = pd.DataFrame(
            [
                {
                    "race_id": r.race_id,
                    "boat_no": r.boat_no,
                    "fetched_at": r.fetched_at,
                    "exhibition_time": float(r.exhibition_time)
                    if r.exhibition_time is not None
                    else None,
                    "tilt_angle": float(r.tilt_angle) if r.tilt_angle is not None else None,
                    "start_exhibition_course": r.start_exhibition_course,
                    "start_exhibition_timing": float(r.start_exhibition_timing)
                    if r.start_exhibition_timing is not None
                    else None,
                }
                for r in p_results
            ]
        )
        p_df = (
            p_df.sort_values("fetched_at")
            .groupby(["race_id", "boat_no"])
            .tail(1)
            .drop(columns=["fetched_at"])
        )
        df = pd.merge(df, p_df, on=["race_id", "boat_no"], how="left")

    return df


def add_odds_features(session: Session, df: pd.DataFrame) -> pd.DataFrame:
    """単勝オッズ情報を結合する"""
    if df.empty or "race_id" not in df.columns:
        return df

    race_ids = df["race_id"].dropna().unique().tolist()
    if not race_ids:
        return df

    odds_q = select(OddsSnapshotEntry).where(
        OddsSnapshotEntry.race_id.in_(race_ids), OddsSnapshotEntry.bet_type == "win"
    )
    o_results = session.execute(odds_q).scalars().all()
    if o_results:
        o_df = pd.DataFrame(
            [
                {
                    "race_id": r.race_id,
                    "boat_no": int(r.combination),  # 単勝は combination が艇番と一致する
                    "fetched_at": r.fetched_at,
                    "win_odds": float(r.odds_value) if r.odds_value is not None else None,
                }
                for r in o_results
            ]
        )
        o_df = (
            o_df.sort_values("fetched_at")
            .groupby(["race_id", "boat_no"])
            .tail(1)
            .drop(columns=["fetched_at"])
        )
        df = pd.merge(df, o_df, on=["race_id", "boat_no"], how="left")

    return df


def build_training_dataset(
    session: Session,
    from_date: Optional[date] = None,
    to_date: Optional[date] = None,
    model_view: str = "pre_race_no_odds",
) -> pd.DataFrame:
    """
    指定されたビュー（model_view）に基づいて特徴量と教師ラベルを結合したデータセットを作成する。
    model_view:
      - 'pre_race_no_odds': 出走表と期別成績のみ（展示・オッズなし）
      - 'pre_race_with_odds': 出走表と期別成績＋オッズ
      - 'exhibition_with_odds': 出走表と期別成績＋展示・気象＋オッズ
    """
    # 1. ベース特徴量の取得
    features_df = fetch_base_features(session, from_date, to_date)
    if features_df.empty:
        return pd.DataFrame()

    # 2. レーサー期別成績をJOIN
    features_df = add_racer_period_stats(session, features_df)

    # 3. ビューに応じた追加特徴量のJOIN
    if model_view in ["exhibition_with_odds"]:
        features_df = add_pre_race_features(session, features_df)

    if model_view in ["pre_race_with_odds", "exhibition_with_odds"]:
        features_df = add_odds_features(session, features_df)

    # 4. 未来情報や目的変数が混入していないか、特徴量DFを検証
    validate_no_leakage(features_df)

    # 5. 教師ラベルの取得と生成
    label_records = fetch_label_records(session, from_date, to_date)
    labels_df = generate_labels_df(label_records)

    # 6. 特徴量とラベルを結合
    if not labels_df.empty:
        dataset_df = pd.merge(features_df, labels_df, on=["race_id", "boat_no"], how="inner")
    else:
        dataset_df = pd.DataFrame()

    return dataset_df
