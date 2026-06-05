import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.race_results import RaceResult
from app.models.race_master import Race

def get_racer_history_df(session: Session) -> pd.DataFrame:
    query = select(
        Race.race_id,
        Race.race_date,
        RaceResult.racer_registration_no,
        RaceResult.finish_position,
        RaceResult.entry_course,
        Race.venue_code,
    ).join(Race, Race.race_id == RaceResult.race_id)
    
    results = session.execute(query).fetchall()
    df = pd.DataFrame([dict(row._mapping) for row in results])
    if df.empty:
        return df
        
    df["race_date"] = pd.to_datetime(df["race_date"])
    df = df.sort_values(["racer_registration_no", "race_date"])
    return df

def add_rolling_features(df: pd.DataFrame) -> pd.DataFrame:
    # 既存の直近30走成績
    def calc_rolling_stats(group: pd.DataFrame) -> pd.DataFrame:
        is_win = (group["finish_position"] == 1).astype(int)
        is_top2 = (group["finish_position"] <= 2).astype(int)
        group["recent_win_rate_30"] = is_win.rolling(window=30, min_periods=1).mean().shift(1)
        group["recent_top2_rate_30"] = is_top2.rolling(window=30, min_periods=1).mean().shift(1)
        return group
    
    df = df.groupby("racer_registration_no", group_keys=False).apply(calc_rolling_stats, include_groups=False)
    
    # P5-302: コース別成績 (過去全レースの累積平均)
    course_stats = df.groupby(["racer_registration_no", "entry_course"]).apply(
        lambda g: pd.Series({
            "course_win_rate": (g["finish_position"] == 1).mean(),
        }), include_groups=False
    ).reset_index()
    
    # P5-303: 当地成績
    venue_stats = df.groupby(["racer_registration_no", "venue_code"]).apply(
        lambda g: pd.Series({
            "venue_win_rate": (g["finish_position"] == 1).mean(),
        }), include_groups=False
    ).reset_index()

    return df.merge(course_stats, on=["racer_registration_no", "entry_course"], how="left") \
             .merge(venue_stats, on=["racer_registration_no", "venue_code"], how="left")
