from datetime import date
from typing import Optional

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.features.labels import fetch_label_records, generate_labels_df
from app.features.leakage import validate_no_leakage
from app.models.race_cards import RaceEntry
from app.models.race_master import Race
from app.models.racer_period_stats import RacerPeriodStat


def fetch_base_features(
    session: Session, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> pd.DataFrame:
    """出走表からベースとなる特徴量（場、グレード、艇番、選手、モーターなど）を取得する"""
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
    対象レース時点において適用されている「レーサー期別成績」をJOINする。
    未来情報混入（Leakage）を防ぐため、race_dateから適用期（前期/後期）を計算して結合する。
    """
    if df.empty or "racer_registration_no" not in df.columns:
        return df

    # 1. レース日付から適用される「年」と「期」を計算する
    # 適用ルール: 1月〜6月は「前期」、7月〜12月は「後期」
    race_dates = pd.to_datetime(df["race_date"])
    df["period_year"] = race_dates.dt.year
    df["period_term"] = race_dates.dt.month.apply(lambda m: "前期" if m <= 6 else "後期")

    # DBクエリ最適化のため、必要な登番のリストを抽出
    racer_nos = df["racer_registration_no"].dropna().unique().tolist()
    if not racer_nos:
        return df

    # 2. 該当選手の期別成績をDBから取得
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

        # JSONB内から勝率、2連対率、3連対率を安全に抽出（パース時のキー名揺れに対応）
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

    # 3. ベース特徴量にLEFT JOIN
    if not stats_df.empty:
        df = pd.merge(
            df, stats_df, on=["racer_registration_no", "period_year", "period_term"], how="left"
        )
    else:
        df["racer_win_rate"] = None
        df["racer_top2_rate"] = None
        df["racer_top3_rate"] = None

    # 結合に使った中間カラム（period_year, period_term）は消してもよいが分析用に残す
    return df


def build_training_dataset(
    session: Session, from_date: Optional[date] = None, to_date: Optional[date] = None
) -> pd.DataFrame:
    """
    出走表・期別成績（特徴量）とレース結果（教師ラベル）を結合したデータセットを作成する。
    """
    # 1. 出走表からベース特徴量を取得
    features_df = fetch_base_features(session, from_date, to_date)
    if features_df.empty:
        return pd.DataFrame()

    # 2. レーサー期別成績をJOIN（未来情報が混ざらないように期を計算）
    features_df = add_racer_period_stats(session, features_df)

    # 3. 未来情報や目的変数が混入していないか、特徴量DFを検証
    validate_no_leakage(features_df)

    # 4. 教師ラベルの取得と生成
    label_records = fetch_label_records(session, from_date, to_date)
    labels_df = generate_labels_df(label_records)

    # 5. 特徴量とラベルを結合
    if not labels_df.empty:
        dataset_df = pd.merge(features_df, labels_df, on=["race_id", "boat_no"], how="inner")
    else:
        dataset_df = pd.DataFrame()

    return dataset_df
